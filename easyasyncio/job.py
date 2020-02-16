import abc
import asyncio
import logging
from abc import abstractmethod
from asyncio import (AbstractEventLoop, Semaphore, Future, Queue,
                     QueueFull, CancelledError)
from collections import deque, Counter
from time import time
from typing import (Set, Any, MutableMapping, Union, TYPE_CHECKING, Dict,
                    Optional)

from aiohttp import ServerDisconnectedError
from diskcache import Deque, Index

from .cachetypes import CacheSet
from .context import Context

if TYPE_CHECKING:
    from . import DataManager


class Job(abc.ABC):
    tasks: Set[Future]
    max_concurrent: int
    context: Context
    loop: AbstractEventLoop
    sem: Semaphore
    end_time: float
    input_data: Any
    success_cache_name = 'success'
    fail_cache_name = 'failed'
    data: 'DataManager'

    def __init__(self,
                 input_data=None,
                 max_concurrent=20,
                 max_queue_size=0,
                 cache_name='completed',
                 cache_finished_items=True,
                 continuous=False,
                 cache_queued_items=False,
                 enable_cache=True,
                 auto_add_results=True,
                 queue_cache_name='resume',
                 product_name='successes',
                 log_level=logging.INFO,
                 auto_requeue=True,
                 exit_on_queue_finish=True,
                 skip_completed=True,
                 uncache_completed=True) -> None:
        """

        Args:

            input_data (Any): Starting data to work on that is usually loaded
                from a file
            max_concurrent (int): The maximum number of workers
            max_queue_size (int): The maximum items the queue can hold at once

            cache_finished_items (bool): Whether or not this Job should cache
                finished items automatically. This will prevent the program
                from working on the same items multiple times
            cache_name (str): The name of the cache to save completed data to.
                This will default to **self.name**
            continuous (bool): Whether the predecessor of this Job should end
                this Job when its queue is empty
            cache_queued_items (bool): Whether all items added to the queue
                should also be cached for resuming when the Job is restarted
            queue_cache_name (str): The name to save the queue_cache as
            product_name (str): The item that this job produces
            auto_requeue (bool): Automatically re-add certain failed items
                back into queue
            exit_on_queue_finish (bool): Exit when self.queue_finished is
                called
            skip_completed (bool): Skip items from queue that are in the
                completed_cache
            uncache_completed (bool): Remove processed items from queue_cache
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
        self._queue_size = max_queue_size
        self.cache_finished_items = cache_finished_items
        self.cache_name = cache_name
        self.use_resume = cache_queued_items
        self.queue_cache_name = queue_cache_name
        self.cache_enabled = enable_cache
        if not enable_cache:
            self.cache_finished_items = False
            self.use_resume = False
        self.continuous = continuous
        self.result_name = product_name
        self.auto_requeue = auto_requeue
        self.exit_on_queue_finish = exit_on_queue_finish
        self.skip_completed = skip_completed
        self.uncache_completed = uncache_completed

    @property
    def queue(self) -> Queue:
        return self.context.queues.get(self.name)

    @property
    def completed_cache(self) -> CacheSet:
        """
        A cache built for avoiding duplicates.
        All processed items from the queue will be added here
        """
        return self.data.get_job_cache(self, self.cache_name)

    @property
    def queue_cache(self) -> CacheSet:
        """
        A cache built for resuming any progress made when any Job is
        restarted. On load, the program will queue all of the resume_cache
        items that are not in **self.completed_cache**
        """
        return self.data.get_job_cache(self, self.queue_cache_name)

    @property
    def success_cache(self) -> CacheSet:
        """
        A cache built for resuming any progress made when any Job is
        restarted. This cache will store all of the queued item that
        successfully returned a value that is not **False** or **None**
        """
        return self.data.get_job_cache(self, self.success_cache_name)

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

    def initialize(self, context: Context):
        """
        Set all of the context-dependent variables

        This is called during manager.add_job(...) and needs to be called
        before this class can access any property from **self.context**
        """
        self.context = context
        self.data = context.data
        self.loop = context.loop
        self.context.jobs.add(self)
        self.sem = Semaphore(self.max_concurrent, loop=self.loop)
        self.context.queues.new(self.name, self._queue_size)
        self.log.addHandler(JobLogHandler(self, level=self.log_level))
        self.status('initialized')
        self.log.info('loading cached items...')
        if self.cache_enabled:
            if self.cache_finished_items:
                context.data.register_job_cache(self, set(), self.cache_name)
            if self.use_resume:
                context.data.register_job_cache(self, set(),
                                                self.queue_cache_name)
            context.data.register_job_cache(self, set(),
                                            self.success_cache_name)
        self.data.register_cache('%s.failed' % self.name, set(),
                                 './data/failed/%s.txt' % self.name)

    async def run(self):
        """setup workers and start"""
        self.log.debug('starting...')
        self.running = True
        try:
            # create workers
            self.create_workers()
        except Exception:
            self.log.error('Failed to create workers.')
            raise
        else:
            # fill queue
            self.status('filling queue')
            self.log.debug('creating queue task...')
            queue_task = self.loop.create_task(self.fill_queue())
            self.tasks.add(queue_task)
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
            # finish
            await self.on_finish()

    @abstractmethod
    async def fill_queue(self):
        """implement the queue filling logic here"""
        pass

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
            queued_data = await self.queue.get()
            if queued_data is False:
                if not self.exit_on_queue_finish:
                    continue
                break
            if (self.cache_finished_items and self.skip_completed and
                    queued_data in self.completed_cache):
                self.increment_stat(name='skipped')
                continue

            self.log.debug('[worker%s] retrieved queued data "%s"',
                           num, queued_data)
            try:
                result = await self.do_work(queued_data)
            except CancelledError:
                self.log.debug('work on %s has been cancelled', queued_data)
                break
            except ServerDisconnectedError:
                self.log.error('server disconnected')
                await self.queue.put(queued_data)
            except Exception:
                self.increment_stat(name='exceptions')
                self.log.error('worker uncaught exception', exc_info=1,
                               extra=dict(queued_data=queued_data))
                await self.queue.put(queued_data)
                self.failed_inputs.add(queued_data)
                self.with_errors = True
            else:
                await self._on_work_processed(queued_data, result)
            finally:
                self.queue.task_done()
                self.increment_stat(name='attempted')

        self.info['workers'] -= 1
        self.log.debug('[worker%s] terminated', num)

    async def _on_work_processed(self, input_data, result):
        try:
            self.failed_inputs.remove(input_data)
        except KeyError:
            pass
        if result is None:
            if self.auto_requeue:
                await self.queue.put(input_data)
                self.increment_stat(name='requeued')
            return
        if result is not False:  # success
            # only use post-processing if the result is not a boolean
            self.cache(input_data, self.success_cache)
            if result is not True and self.auto_add_results:
                await self._post_process(result)
            if isinstance(result, (list, set, dict)):
                self.increment_stat(len(result), self.result_name)
            else: self.increment_stat(name=self.result_name)
        else:  # failure
            self.failed_inputs.add(input_data)
            self.increment_stat(name='failed')

        self.decache(input_data, self.queue_cache)
        self.cache(input_data, self.completed_cache)

    def cache(self, data: object, cache: CacheSet):
        if not self.cache_enabled:
            return
        if cache is self.success_cache:
            self.success_cache.add(data)
        elif self.cache_finished_items and cache == self.completed_cache:
            self.completed_cache.add(data)
        elif self.use_resume and cache == self.queue_cache:
            self.queue_cache.add(data)

    def decache(self, data: object, cache: CacheSet):
        if not self.cache_enabled:
            return
        try:
            if cache is self.success_cache:
                self.success_cache.remove(data)
            elif self.cache_finished_items and cache == self.completed_cache:
                self.completed_cache.remove(data)
            elif (self.use_resume and cache == self.queue_cache
                  and self.uncache_completed):
                self.queue_cache.remove(data)
        except KeyError:
            pass

    @abstractmethod
    async def do_work(self, input_data) -> object:
        """
        Do business logic on each enqueued item and returns the completed data.

        This method should return an object or **True** on completion.
        If the work fails in a predicted way, this method should return False.
        If the work fails in an unexpected way, this method should not return
        anything.

        When an object is returned, the queued_data will be added to the cache.
        The object will also be sent to **self.post_process()** to be either
        queued or "outputted" depending on the type of Job.

        When a **True** is returned, the queued_data will also be cached, but
        there will be no further processing done to it.

        When a **False** is returned, the queued_data will be cached as well,
        no further processing will be done.

        When **None** is returned, the queued_data will not be cached.

        See Also :class:`Job.worker`
        """

    async def _post_process(self, obj):
        if (isinstance(obj,
                       (list, set)) and not isinstance(
                obj, str)):
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

    async def on_item_completed(self, obj):
        """Called after post-processing is finished"""
        self.log.info(obj)

    async def on_finish(self):
        """Called when all tasks are finished"""
        self.end_time = time()
        self.status('finished')
        self.log.debug('finished!')
        if self.with_errors:
            self.log.warning('Some errors occurred. See logs')

    async def queue_finished(self):
        """Tells this Job to stop watching the queue and close"""
        self.log.debug('finished queueing')
        for _ in range(self.info['workers']):
            try:
                await self.queue.put(False)
            except QueueFull:
                while not self.queue.empty():
                    await self.queue.get()

    async def requeue(self, obj, reason=''):
        await self.queue.put(obj)
        if 'requeued' not in self.info:
            self.info['requeued'] = Counter()
        self.info.get('requeued')[reason or 'unspecified'] += 1

    def increment_stat(self, n=1, name: str = None) -> None:
        """increment the count of whatever this Job is processing"""
        if not name:
            name = self.result_name
        self.stats[name] += n

    def get_uncached(self, items: Union[list, set, CacheSet, Deque, range]):
        """
        Args:
            items: A collection of items to be processed

        Returns: all objects from **items** which have not yet been
        cached/processed
        """
        if not self.cache_finished_items:
            raise Exception('An attempt to access a disabled cache was made.')
        return set(items).difference(set(self.completed_cache)) or set()

    def status(self, *strings: str):
        status = ' '.join(
                [str(s) if not isinstance(s, str) else s for s in strings])
        self.info['status'] = status

    def time_left(self):
        elapsed_time = self.context.stats.elapsed_time
        per_second = self.context.stats[self.name] / elapsed_time
        return round((self.queue.qsize()) / per_second)

    def get_data(self, name):
        return self.data.get(name)

    def diag_save(self, content, input_data, name=None, ext='.json',
                  extras=None):
        """
        Save useful diagnostic information
        """
        name = name or str(time()).replace('.', '')
        json = dict(content=content, input_data=input_data,
                    extras=extras or {}, timestamp=time())
        path = f'./diagnostics/{self.name}/{name}{ext}'
        self.data.register(name, json, path, False, False)
        self.log.debug(
                'saved diagnostic info for %s -> %s' % (input_data, path))

    def __repr__(self):
        return self.name

    def __str__(self):
        return self.name


class ForwardQueuingJob(Job, abc.ABC):
    """
    This :class:`Job` will pass all items completed to its successor for
    further processing
    """

    def __init__(self, successor: Job, **kwargs) -> None:
        """

        Args:
            successor (Job): The Job that will receive this Job's completed
                data
        """
        super().__init__(**kwargs)
        self.successor = successor
        self.info['precedes'] = successor
        self.use_resume = False

    async def on_item_completed(self, obj):
        await self.queue_successor(obj)

    async def queue_successor(self, data):
        await self.successor.queue.put(data)
        if self.successor.use_resume:
            self.successor.queue_cache.add(data)

    async def on_finish(self):
        await super().on_finish()
        if not self.continuous:
            await self.successor.queue_finished()


class BackwardQueuingJob(Job, abc.ABC):
    """
    This :class:`Job` will pass all items completed to its predecessor for
    further processing
    """

    def __init__(self, predecessor: Job, **kwargs) -> None:
        """

        Args:
            predecessor (Job, Optional): The queue that passes completed data
                to this Job
            **kwargs:
        """
        kwargs.setdefault('cache_queued_items', True)
        super().__init__(**kwargs)
        self.predecessor = predecessor
        self.info['supersedes'] = predecessor.name

    async def on_item_completed(self, obj):
        await self.queue_predecessor(obj)

    async def queue_predecessor(self, data):
        await self.predecessor.queue.put(data)
        if self.predecessor.use_resume:
            self.predecessor.queue_cache.add(data)


class OutputJob(Job, abc.ABC):
    """This :class:`Job` will pass all completed items to an output file"""

    def __init__(self, output: Optional[str] = '', **kwargs) -> None:
        self.output = output
        super().__init__(cache_queued_items=True, **kwargs)

    async def on_item_completed(self, o):
        if not self.output:
            raise Exception('Output name is not set')
        cache = self.get_data(self.output)
        if isinstance(cache, (CacheSet, set)):
            cache.add(o)
        elif isinstance(cache, (Deque, list)):
            cache.append(o)
        elif isinstance(cache, (Index, MutableMapping)):
            key, value = o
            cache[key] = value


class JobLogHandler(logging.Handler):
    """This will handle all messages passed via :class:`Job.log`"""

    def __init__(self, worker: Job,
                 level=logging.DEBUG) -> None:
        super().__init__(level)
        self.worker = worker

    def emit(self, record: logging.LogRecord) -> None:
        self.worker.logs.append(record.getMessage())
