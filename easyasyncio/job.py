import abc
import asyncio
import datetime
import logging
from abc import abstractmethod
from asyncio import (AbstractEventLoop, Semaphore, Future, Queue,
                     QueueFull, CancelledError)
from collections import deque, Counter
from numbers import Number
from time import time
from typing import (Set, Any, MutableMapping, TYPE_CHECKING, Dict,
                    Optional, Union)

import attr
from aiohttp import ServerDisconnectedError
from diskcache import Deque, Index

from . import helper
from .averagetracker import AverageTracker
from .cachetypes import CacheSet, EvictingIndex
from .context import Context

if TYPE_CHECKING:
    from . import DataManager


class Job(abc.ABC):
    tasks: Set[Future]
    max_concurrent: int
    context: Context
    loop: AbstractEventLoop
    end_time: float
    input_data: Any
    fail_cache_name = 'failed'
    data: 'DataManager'
    formatting = helper.LogFormatting()
    min_idle_time_before_finish = 10

    def __init__(self,
                 input_data=None,
                 max_concurrent=20,
                 max_queue_size=0,
                 cache_name='completed',
                 continuous=False,
                 enable_cache=True,
                 auto_add_results=True,
                 queue_cache_name='resume',
                 product_name='successes',
                 log_level=logging.INFO,
                 auto_requeue=True,
                 exit_on_queue_finish=True,
                 print_successes=True) -> None:
        """

        Args:

            input_data (Any): Starting data to work on that is usually loaded
                from a file
            max_concurrent (int): The maximum number of workers
            max_queue_size (int): The maximum items the queue can hold at once
            cache_name (str): The name of the cache to save completed data to.
                This will default to **self.name**
            continuous (bool): Whether the predecessor of this Job should end
                this Job when its queue is empty
            queue_cache_name (str): The name to save the queue_cache as
            product_name (str): The item that this job produces
            auto_requeue (bool): Automatically re-add certain failed items
                back into queue
            exit_on_queue_finish (bool): Exit when self.queue_finished is
                called
            print_successes (bool): Whether to automatically print success
                information
        See Also: :class:`OutputJob` :class:`ForwardQueuingJob`
            :class:`BackwardQueuingJob`
        """
        self.log_level = log_level
        self.auto_add_results = auto_add_results
        self.input_data = input_data
        self.max_concurrent = max_concurrent
        self.stats = Counter()
        self.tasks = set()
        self.info: Dict[str, Any] = {
            'max_queue_size': ('infinite' if max_queue_size == 0
                               else max_queue_size),
            'max_workers':    max_concurrent,
            'workers':        0
        }
        self.logs: deque[str] = deque(maxlen=50)
        self.log = logging.getLogger(self.name)
        self.with_errors = False
        self.running = False
        self.max_queue_size = max_queue_size
        self.cache_name = cache_name
        self.queue_cache_name = queue_cache_name
        self.cache_enabled = enable_cache
        self.continuous = continuous
        self.result_name = product_name
        self.auto_requeue = auto_requeue
        self.exit_on_queue_finish = exit_on_queue_finish

        self.queue_looped = False
        self.predecessor: 'Optional[Job]' = None
        self.successor: 'Optional[Job]' = None
        self.print_successes = print_successes
        self._to_do_list = []
        self._in_progress = 0
        self.initialized = False
        self.averages = AverageTracker()
        self.averages.track('process_time', 'avg_process_time')
        if len(self.__class__.__name__) > 15:
            self.log.warning(
                '[WARNING] Class names greater than 15 characters '
                'will cause logger formatting bugs.')

    @property
    def queue(self) -> Queue:
        return self.context.queues.get(self.name)

    @property
    def cache(self) -> EvictingIndex:
        return self.data.get_job_cache(self, self.cache_name)

    @property
    def failed_inputs(self) -> CacheSet:
        """
        This cache will store all of the queued item that returned a value that
        is False
        """
        return self.get_data('%s.failed' % self.name)

    @property
    def name(self):
        return self.__class__.__name__

    @property
    def to_do_list(self):
        return [t for t in self._to_do_list if
                not isinstance(t, (QueueLooped, Terminate))]

    @property
    def finished(self):
        predecessor_done = (not self.predecessor or
                            not any(self.predecessor.to_do_list))
        has_successor = self.successor and isinstance(self.successor,
                                                      BackwardQueuingJob)
        successor_done = (not has_successor
                          or not any(self.successor.to_do_list))
        siblings_done = predecessor_done and successor_done
        tasks_done = not len(self.to_do_list) and not self.queue.qsize()
        return siblings_done and tasks_done and not self._in_progress

    def initialize(self, context: Context):
        """
        Set all of the context-dependent variables

        This is called during manager.add_job(...) and needs to be called
        before this class can access any property from **self.context**
        """
        self._initialize_variables(context)
        self._initialize_config()
        self.status('initialized')
        self.log.info('loading cached items...')
        if self.cache_enabled:
            context.data.register_job_cache(self, dict(), self.cache_name)
        self.data.register_cache('%s.failed' % self.name, set(),
                                 './data/failed/%s.txt' % self.name)
        self.initialized = True

    def _initialize_config(self):
        self.context.queues.new(self.name)
        if self.context.manager.showing_graphics:
            self.log.addHandler(JobLogHandler(self, level=self.log_level))

    def _initialize_variables(self, context):
        self.context = context
        self.data = context.data
        self.loop = context.loop

    async def run(self):
        """setup workers and start"""
        self.log.debug('starting...')
        self.running = True
        try:
            self.create_workers()
        except Exception:
            self.log.error('Failed to create workers.')
            raise
        else:
            # fill queue
            self.status('filling queue')
            self.log.debug('creating queue task...')
            await self._create_queue_tasks()
            # process
            self.status('working')
            try:
                await asyncio.gather(*self.tasks, loop=self.loop,
                                     return_exceptions=False)
            except CancelledError:
                pass
            except Exception as e:
                self.log.exception(e)
                raise
        finally:
            self.running = False
            await self.on_finish()

    async def _create_queue_tasks(self):
        is_fqj = isinstance(self, ForwardQueuingJob)
        has_input_data = isinstance(self, OutputJob) and self.input_data
        should_fll_queue = (is_fqj or has_input_data)
        if should_fll_queue:
            queue_task = self.loop.create_task(self.fill_queue())
            self.tasks.add(queue_task)
        queue_watcher_task = self.loop.create_task(self.queue_watcher())
        self.tasks.add(queue_watcher_task)

    async def fill_queue(self):
        """implement the queue filling logic here"""
        if not self.input_data or not any(self.input_data):
            return
        for d in self.input_data:
            if d in self.failed_inputs:
                continue
            await self.add_to_queue(d)
            await asyncio.sleep(0)
        await self.filled_queue()

    def create_workers(self):
        self.status('creating workers')
        self.log.debug('creating workers...')
        for _ in range(self.max_concurrent):
            self.tasks.add(self.loop.create_task(self.worker(_)))

    async def worker(self, num: int):
        """
        Get each item from the queue and pass it to **self.do_work.**

        This is the main event loop for each worker. The worker will wait
        until an item is available in **self.queue**, then do what ever logic
        is present in the abstract method **self.do_work()**
        This method will also handle caching and will pass finished data
        to post_process() for further action

        See Also self.do_work()
        """
        self.info['workers'] += 1
        self.log.debug('[worker%s] started', num)
        while self.context.running:
            result = None
            from_cache = False
            self.status('waiting on queue')
            queued_data = await self.queue.get()
            self.log.debug('[worker%s] retrieved queued data "%s"',
                           num, queued_data)
            self.status('working')
            self._in_progress += 1
            try:
                if isinstance(queued_data, QueueLooped):
                    self.queue_looped = True
                    continue
                if isinstance(queued_data, Terminate): break
                if queued_data in self.failed_inputs: continue
                if self.cache_enabled:
                    result = self.deindex(queued_data)
                    if result:
                        from_cache = True
                t1 = time()
                try:
                    if result is None:
                        result = await self.do_work(queued_data)
                except CancelledError:
                    self.log.debug('work on %s cancelled', queued_data)
                    break
                except Exception as e:
                    await self.handle_exception(
                        ProcessError(e, queued_data))
                else:
                    await self.post_do_work(from_cache, queued_data, result)
                self.track_averages('process_time', time() - t1)
                if not from_cache:
                    self.increment_stat(name='attempted')

                self.update_stats()
            finally:
                self._in_progress -= 1

        self.info['workers'] -= 1
        self.log.debug('[worker%s] terminated', num)

    async def post_do_work(self, from_cache, queued_data, result):
        self.queue.task_done()
        await self.remove_from_todo(queued_data)
        if self.auto_add_results:
            await self._post_process(result)
        if self.cache_enabled and not from_cache:
            self.index(queued_data, result)
        if self.print_successes:
            self.print_success(queued_data, result,
                               from_cache)

    async def handle_exception(self, e: 'ProcessError'):
        if isinstance(e.exception, ServerDisconnectedError):
            self.log.error('server disconnected')
            await self.queue.put(e.input_data)
        elif isinstance(e.exception, FailResponse):
            self.increment_stat(name=e.exception.reason)
            self.failed_inputs.add(e.input_data)
            self.print_failed(e.exception.reason, e.input_data,
                              e.exception.reason)
            self.queue.task_done()
            await self.remove_from_todo(e.input_data)
        elif isinstance(e.exception, RequeueResponse):
            if self.auto_requeue:
                await self.queue.put(e.input_data)
                self.increment_stat(name=e.exception.reason)
            self.print_requeued(e.exception.reason, e.input_data)
        elif isinstance(e.exception, ValidationRequeueResponse):
            await self.queue.put(e.exception.reason)
            self.increment_stat(name=e.exception.reason)
            self.print_requeued(e.exception.reason, e.input_data,
                                e.exception.new_input)
        elif isinstance(e.exception, NoRequeueResponse):
            self.increment_stat(name=e.exception.reason)

            self.print_failed(e.exception.reason, e.input_data)
            # self.log.info(x_mark + '[No Requeue][%s] %s', nrr.reason,
            #               e.input_data)
            self.log.debug('%s NoRequeue reason: %s', e.input_data,
                           e.exception.reason)
            self.queue.task_done()
            await self.remove_from_todo(e.input_data)
        elif isinstance(e.exception, UnknownResponse):
            self.diag_save(e.exception.diagnostics)
            self.print_failed(e.exception.reason, e.input_data)
            if e.exception.extra_info:
                self.log.info('❌%s', e.exception.extra_info)
            self.increment_stat(name=e.exception.reason)
            self.queue.task_done()
            await self.remove_from_todo(e.input_data)
        elif isinstance(e.exception, FutureResponse):
            self.increment_stat(name=e.exception.reason)
            self.print_requeued(e.exception.reason, e.input_data,
                                e.exception.secondary_reason)
            if e.exception.job and e.exception.obj:
                if not isinstance(e.exception.job, Job):
                    job = self.context.get_job(e.exception.job)
                else:
                    job = e.exception.job
                await job.add_to_queue(e.exception.obj)
        elif isinstance(e.exception, Response):
            self.print_failed(e.exception.reason, e.input_data)
            self.increment_stat(name=e.exception.reason)
            self.queue.task_done()
            await self.remove_from_todo(e.input_data)
        elif isinstance(e.exception, CancelledError):
            raise CancelledError()
        else:
            self.increment_stat(name='uncaught-exceptions')
            self.log.exception('worker uncaught exception: %s',
                               dict(queued_data=e.input_data))
            self.with_errors = True
            self.queue.task_done()
            await self.remove_from_todo(e.input_data)

    async def remove_from_todo(self, queued_data):
        try:
            self._to_do_list.remove(queued_data)
        except ValueError:
            pass

    def print_success(self, input_data: object, result: object,
                      from_cache=False):
        formatted_input = self.get_formatted_input(input_data)
        formatted_input = self.formatting.format_input(formatted_input)
        output = self.get_formatted_output(result)
        # self.formatting.update_result_justify(len(output))

        success_colored = helper.color_green(f'[{"Success"}]')
        if from_cache:
            success_colored = helper.color_blue(f'[{"Cached"}]')
        success_colored = success_colored.ljust(
            self.formatting.fail_string_length)
        self.formatting.update_success_string_length(len(success_colored))

        input_colored = helper.color_cyan('Input')
        input_data_formatted = formatted_input.ljust(
            self.formatting.input_justify)
        self.formatting.update_input_justify(len(formatted_input))

        check_mark = (helper.check_mark if not from_cache
                      else helper.cache_check_mark)
        self.log.info(check_mark + '%s %s: %s %s: %s',
                      success_colored,
                      input_colored,
                      input_data_formatted,
                      helper.color_cyan('Output'),
                      output)

    def print_requeued(self, reason: str, queued_data: object,
                       new_input_data: str = ''):
        input_colored = helper.color_cyan('Input')
        queued_data = self.get_formatted_input(queued_data)
        queued_data = self.formatting.format_input(queued_data)
        new_input_colored = ''
        if new_input_data:
            new_input_colored = helper.color_cyan('New Input:')
            queued_data = queued_data.ljust(
                self.formatting.input_justify)
            self.formatting.update_input_justify(len(queued_data))

        requeue_colored = helper.color_orange('[%s]' % reason.capitalize())
        requeue_colored = requeue_colored.ljust(
            max(self.formatting.fail_string_length,
                self.formatting.success_string_length))
        self.formatting.update_fail_string_length(len(requeue_colored))

        formatted = helper.reload_mark + '%s %s: %s %s %s' % (
            requeue_colored,
            input_colored,
            queued_data,
            new_input_colored,
            new_input_data
        )
        self.log.info(formatted)

    def print_failed(self, reason: str, queued_data: object, extra_info=None):
        failed_string = helper.color_red('[%s]' % reason.capitalize())
        self.formatting.update_fail_string_length(len(failed_string))

        queued_data = self.get_formatted_input(queued_data)
        if extra_info:
            queued_data = self.formatting.format_input(queued_data)
        queued_data = queued_data.ljust(self.formatting.input_justify)

        string = '%s %s' % (helper.color_cyan('Input') + ':', queued_data)
        reason_colored = (
            helper.color_cyan('Reason') + ':') if extra_info else ''
        failed_colored = failed_string.ljust(
            max(self.formatting.fail_string_length,
                self.formatting.success_string_length))
        formatted = '%s%s %s %s %s' % (
            helper.x_mark,
            failed_colored,
            string,
            reason_colored,
            extra_info
        )
        self.log.info(formatted)

    @abstractmethod
    async def do_work(self, input_data) -> object:
        """
        Do business logic on each enqueued item and returns the completed data.

        This method should not be called directly.

        This method should return an object or raise type of Response on
        completion.
        If the work fails in a predicted way and is expected to continue to
        fail, this method should raise a FailedResponse.
        If the work fails in a predicted way and needs to be requeued, it
        should raise a RequeueResponse.
        If the work fails in a predicted way and should not be requeued, it
        should raise a NoRequeueResponse
        If the work fails in an unexpected way, it should raise a
        UnknownResponse and have a Diagnostics object passed to it with the
        fail information

        All completed items will be added to the queue if self.cache_enabled is
        set to true. Completed items will then be passed to _post_process for
        further processing.

        See Also :class:`Job.worker`
        """

    async def _post_process(self, obj):
        is_iterable = isinstance(obj, (list, set)) and not isinstance(obj, str)
        if is_iterable:
            for o in obj:
                await self.on_item_completed(o)
                await asyncio.sleep(0)
            self.log.debug('finished postprocessing %s items', len(obj))
        elif isinstance(obj, MutableMapping):
            for t in obj.items():
                await self.on_item_completed(t)
                await asyncio.sleep(0)
            self.log.debug('finished postprocessing %s items', len(obj))
        else:
            await self.on_item_completed(obj)

    @abstractmethod
    async def on_item_completed(self, obj):
        """Called after post-processing is finished"""

    async def on_finish(self):
        """Called when all tasks are finished"""
        self.end_time = time()
        self.status('finished')
        self.log.info('done at %s', datetime.datetime.now())
        self.log.debug('finished!')
        if self.with_errors:
            self.log.warning('Some errors occurred. See logs')

    async def filled_queue(self):
        self.log.debug('finished queueing')
        await self.queue.put(QueueLooped())

    async def terminate(self):
        """Tells this Job to stop watching the queue and close"""
        self.log.debug('called terminate')
        for index in range(self.info['workers']):
            try:
                await self.add_to_queue(Terminate())
            except QueueFull:
                while not self.queue.empty():
                    await self.queue.get()
                await self.add_to_queue(Terminate())

        if isinstance(self, ForwardQueuingJob):
            if isinstance(self.successor, (OutputJob, Job)):
                self.successor.queue_looped = True

    async def add_to_queue(self, obj):
        if isinstance(obj, Terminate):
            optional = obj
        else:
            optional = await self.queue_filter(obj)
        if optional is not None:
            await self.queue.put(optional)
            self._to_do_list.append(optional)

    # noinspection PyMethodMayBeStatic
    async def queue_filter(self, obj):
        """All items added to the queue must fulfil this requirement"""
        if obj in self.failed_inputs:
            return None
        return obj

    def index(self, input_data, result):
        hash_id = helper.smart_hash(input_data)
        self.cache[hash_id] = result

    def deindex(self, input_data):
        hash_id = helper.smart_hash(input_data)
        return self.cache.get(hash_id)

    def increment_stat(self, n=1, name: str = None) -> None:
        """increment the count of whatever this Job is processing"""
        self.stats[name or 'unique-%s' % self.result_name] += n

    def status(self, *strings: str):
        status = ' '.join(
            [str(s) if not isinstance(s, str) else s for s in strings])
        self.info['status'] = status

    async def queue_watcher(self):
        while not self.queue_looped:
            await asyncio.sleep(1)
        self.log.debug('starting queue watcher')
        while self.context.running:
            await asyncio.sleep(0.05)

            if not self.finished:
                continue

            await self.terminate()
            break

    def time_left(self):
        elapsed_time = self.context.stats.elapsed_time
        per_second = self.context.stats[self.name] / elapsed_time
        return round((self.queue.qsize()) / per_second)

    def track_averages(self, name: str, value: Number):
        self.averages.add(name, value)
        if name in self.averages.total_names:
            self.context.stats[self.averages.total_names[name]] += value

    def update_stats(self):
        self.info.update(self.averages.get_stats())

    def get_data(self, name) -> Union[dict, set, list,
                                      CacheSet, Index, EvictingIndex, Deque]:
        return self.data.get(name)

    def diag_save(self, diag: 'Diagnostics', name=None):
        """
        Save useful diagnostic information
        """
        name = name or str(time()).replace('.', '')
        json = dict(content=diag.content, input_data=diag.input_data,
                    extras=diag.extras or {}, timestamp=time())
        path = f'./diagnostics/{self.name}/{name}{diag.extension}'
        self.data.register_file(name, json, path, False, False)
        self.log.info(
            'saved diagnostic info for %s -> %s' % (diag.input_data, path))

    def get_formatted_output(self, obj) -> str:
        if isinstance(obj, (list, set, dict)):
            return f'{len(obj)} {self.result_name}'
        else:
            return str(obj)

    @staticmethod
    def get_formatted_input(obj) -> str:
        return str(obj)

    def __repr__(self):
        return self.name

    def __str__(self):
        return self.name


class ForwardQueuingJob(Job, abc.ABC):
    """
    This :class:`Job` will pass all items completed to its successor for
    further processing
    """

    async def on_item_completed(self, obj):
        # pause if successor has a full queue
        if self.successor.max_queue_size:
            while (self.successor.queue.qsize()
                   >= self.successor.max_queue_size):
                self.status('paused')
                await asyncio.sleep(1)
        await self.queue_successor(obj)
        if self.successor.cache_enabled:
            cached = self.successor.cache.get(helper.smart_hash(obj))
            if not cached:
                self.increment_stat()
            else:
                self.increment_stat(name='uncached-%s' % self.result_name)
        else:
            self.increment_stat()

    async def queue_successor(self, data):
        await self.successor.add_to_queue(data)

    async def filled_queue(self):
        await super().filled_queue()
        self.log.debug('adding QueueLooped() to successor')
        await self.successor.queue.put(QueueLooped())


class BackwardQueuingJob(Job, abc.ABC):
    """
    This :class:`Job` will pass all items completed to its predecessor for
    further processing
    """

    async def on_item_completed(self, obj):
        if self.predecessor and self.predecessor.max_queue_size:
            while (self.predecessor.queue.qsize()
                   >= self.predecessor.max_queue_size):
                self.status('paused')
                await asyncio.sleep(1)
        await self.queue_predecessor(obj)
        self.increment_stat(name=self.result_name)

    async def queue_predecessor(self, data):
        await self.predecessor.add_to_queue(data)


class OutputJob(Job, abc.ABC):
    """This :class:`Job` will pass all completed items to an output file"""

    def __init__(self, output: Optional[str] = 'output', **kwargs) -> None:
        self.output = output
        super().__init__(**kwargs)

    def initialize(self, context: Context):
        super().initialize(context)
        self.log.info('starting with %s items in output',
                      len(self.get_data(self.output)))
        if self.outputs is None:
            raise Exception('output has not been registered with '
                            'DataManager#register or '
                            'DataManager#register_cache')

    @property
    def outputs(self):
        return self.get_data(self.output)

    async def on_item_completed(self, o):
        if not self.output:
            self.log.info(o)
        if o not in self.outputs:
            self.increment_stat()
        else:
            self.increment_stat(name='duplicate-%s' % self.result_name)
            return
        if isinstance(self.outputs, (CacheSet, set)):
            self.outputs.add(o)
        elif isinstance(self.outputs, (Deque, list)):
            self.outputs.append(o)
        elif isinstance(self.outputs, (Index, MutableMapping, EvictingIndex)):
            key, value = o
            self.outputs[key] = value


class JobLogHandler(logging.Handler):
    """This will handle all messages passed via :class:`Job.log`"""

    def __init__(self, worker: Job,
                 level=logging.DEBUG) -> None:
        super().__init__(level)
        self.worker = worker

    def emit(self, record: logging.LogRecord) -> None:
        self.worker.logs.append(record.getMessage())


class QueueLooped:
    pass


class Terminate:
    pass


class Response(Exception):
    reason: str

    def __init__(self, reason, *args: object) -> None:
        super().__init__(*args)
        self.reason = reason


class RequeueResponse(Response):
    """Processing did not return meaningful data, and it will be added to the
     queue for reprocessing."""

    def __init__(self, reason='requeued', *args: object) -> None:
        super().__init__(reason, *args)


class FutureResponse(Response):
    """The input data was sent to another worker and will be returned later."""

    def __init__(self, reason='awaiting', secondary_reason='',
                 obj: object = None, job: Union[int, Job] = None,
                 *args) -> None:
        super().__init__(reason, *args)
        self.secondary_reason = secondary_reason
        self.obj = obj
        self.job = job


class FailResponse(Response):
    """Processing failed and will consistently fail so it will not be added
    back to the queue and will not be processed in the future."""

    def __init__(self, reason='failed', extra_info='', *args: object) -> None:
        super().__init__(reason, *args)
        self.extra_info = extra_info


class ValidationRequeueResponse(Response):
    """Processing received an invalid input that was fixed and requeued.
    The original queued_data will be added to the failed list and the new one
    will be added to the back of the queue"""

    def __init__(self, new_input, reason='requeue', *args: object) -> None:
        super().__init__(reason, *args)
        self.new_input = new_input


class NoRequeueResponse(Response):
    """Processing did not return a value, but will not be requeued during this
    session. However it will be added on the next run."""

    def __init__(self, reason='temporarily-failed', *args: object) -> None:
        super().__init__(str(reason), *args)


class UnknownResponse(Response):
    def __init__(self, diagnostics: 'Diagnostics', reason='unknown',
                 extra_info='', *args: object) -> None:
        super().__init__(reason, *args)
        self.diagnostics = diagnostics
        self.extra_info = extra_info


class ProcessError(Exception):

    def __init__(self, exception: Exception, input_data: object,
                 *args: object) -> None:
        super().__init__(*args)
        self.exception = exception
        self.input_data = input_data


@attr.s(auto_attribs=True)
class Diagnostics:
    """Save response information for diagnostics and debugging"""
    content: object
    input_data: object
    extras: dict = {}
    extension: str = '.json'
