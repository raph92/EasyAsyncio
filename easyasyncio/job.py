import abc
import asyncio
import logging
from abc import abstractmethod
from asyncio import (AbstractEventLoop, Semaphore, Future, Queue,
                     QueueFull, CancelledError)
from collections import deque, Counter
from time import time
from typing import (Set, Optional, Any, MutableMapping, Union)

from aiohttp import ServerDisconnectedError
from diskcache import Deque, Index

from .cachetypes import CacheSet
from .context import Context


class Job(abc.ABC):
    tasks: Set[Future]
    max_concurrent: int
    context: Context
    loop: AbstractEventLoop
    sem: Semaphore
    end_time: float
    input_data: Any

    def __init__(self,
                 input_data=None,
                 max_concurrent=20,
                 max_queue_size=0,
                 predecessor: 'Optional[Job]' = None,
                 successor: 'Optional[Job]' = None,
                 output: str = '',
                 caching=True,
                 cache_name='',
                 continuous=False) -> None:
        """

        Args:
            input_data (Any): Starting data to work on that is usually loaded
                from a file
            max_concurrent (int): The maximum number of workers
            max_queue_size (int): The maximum items the queue can hold at once
            predecessor (Job, Optional): The queue that passes completed data
                to this Job
            successor (Job): The Job that will receive this Job's completed
                data
            output (str): The name of the key to the output file
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
        See Also: :class:`OutputJob` :class:`ForwardQueuingJob`
            :class:`BackwardQueuingJob`
        """
        self.input_data = input_data
        self.max_concurrent = max_concurrent
        self.output = output
        self.stats = Counter()
        self.tasks = set()
        self.info = dict()
        self.info['max_queue_size'] = ('infinite' if max_queue_size == 0
                                       else max_queue_size)
        self.info['max_workers'] = max_concurrent
        self.predecessor = predecessor
        self.successor = successor
        if predecessor:
            predecessor.add_successor(self)
            self.info['supersedes'] = predecessor.name
        if successor:
            successor.add_predecessor(self)
            self.info['precedes'] = successor.name
        self._status = ''
        self.logs: deque[str] = deque(maxlen=50)
        self.log = logging.getLogger(self.name)
        self.with_errors = False
        self.running = False
        self._queue_size = max_queue_size
        self.caching = caching
        if caching:
            self.cache_name = cache_name or self.name
        self.continuous = continuous

    @property
    def queue(self) -> Queue:
        return self.context.queues.get(self.name)

    @property
    def cache(self) -> CacheSet:
        return self.context.data.get(self.cache_name)

    @property
    @abstractmethod
    def name(self):
        pass

    def initialize(self, context: Context):
        self.context = context
        self.loop = context.loop
        self.context.jobs.add(self)
        self.sem = Semaphore(self.max_concurrent, loop=self.loop)
        self.context.queues.new(self.name, self._queue_size)
        self.log.addHandler(JobLogHandler(self))
        self.status('initialized')
        if self.caching:
            context.data.register_cache(self.cache_name, set(), display=False)

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
            await asyncio.gather(*self.tasks, loop=self.loop,
                                 return_exceptions=False)
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
        """get each item from the queue and pass it to self.work"""
        self.log.debug('worker %s started', num)
        while self.context.running:
            queued_data = await self.queue.get()
            if self.caching and queued_data in self.cache and queued_data is not False:
                self.increment_stat(name='skipped')
                continue
            if queued_data is False:
                self.log.debug('worker %s terminating', num)
                break
            self.log.debug('[worker%s] retrieved queued data "%s"',
                           num, queued_data)
            try:
                result = await self.do_work(queued_data)
            except CancelledError:
                self.log.debug('work on %s cancelled', queued_data)
                break
            except ServerDisconnectedError:
                self.log.error('server disconnected')
                await self.queue.put(queued_data)
            except Exception as e:
                self.increment_stat(name='exceptions')
                self.log.exception('')
                raise
            self.queue.task_done()
            do_not_cont = queued_data is False or isinstance(result,
                                                             type(None))
            if do_not_cont:
                return
            if self.caching:
                self.cache.add(queued_data)
            if result is not False:
                await self.post_process(result)
                if isinstance(result, (list, set, dict)):
                    self.increment_stat(len(result), 'successes')
                else: self.increment_stat(name='successes')
            self.increment_stat()

    @abstractmethod
    async def do_work(self, *args) -> object:
        """do business logic on each enqueued item"""

    async def post_process(self, obj):
        if (isinstance(obj,
                       (list, set, dict, Iterable)) and not isinstance(
                obj, str)):
            for o in obj:
                await self.on_item_completed(o)
        elif isinstance(obj, MutableMapping):
            for t in obj.items():
                await self.on_item_completed(t)
        else:
            await self.on_item_completed(obj)

    async def on_item_completed(self, obj):
        """Called after post-processing is finished"""
        self.log.info('obj')

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
        for _ in self.tasks:
            try:
                await self.queue.put(False)
            except QueueFull:
                while not self.queue.empty():
                    await self.queue.get()

    def increment_stat(self, n=1, name: str = None) -> None:
        """increment the count of whatever this Job is processing"""
        if not name:
            name = 'processed'
        self.stats[name] += n

    async def queue_successor(self, data):
        await self.successor.queue.put(data)

    def add_successor(self, successor: 'Job'):
        """
        The next async worker that will work on the data that
        this async worker gathers
        """
        assert successor != self
        self.successor = successor
        self.successor.predecessor = self
        self.info['precedes'] = successor.name

    def add_predecessor(self, predecessor: 'Job'):
        """
        The next async worker that will work on the data that
        this async worker gathers
        """
        assert predecessor != self
        self.predecessor = predecessor
        self.predecessor.successor = self
        self.info['supersedes'] = predecessor.name

    async def queue_predecessor(self, data):
        await self.predecessor.queue.put(data)

    def status(self, *strings: str):
        status = ' '.join(
                [str(s) if not isinstance(s, str) else s for s in strings])
        self.info['status'] = status

    def time_left(self):
        elapsed_time = self.context.stats.elapsed_time
        per_second = self.context.stats[self.name] / elapsed_time
        return round((self.queue.qsize()) / per_second)

    def get_data(self, name):
        return self.context.data.get(name)

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
        super().__init__(successor=successor, **kwargs)

    async def on_item_completed(self, obj):
        await self.queue_successor(obj)

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
        super().__init__(predecessor=predecessor, **kwargs)

    async def on_item_completed(self, obj):
        await self.queue_predecessor(obj)


class OutputJob(Job, abc.ABC):
    """This :class:`Job` will pass all completed items to an output file"""

    def __init__(self, output: str, **kwargs) -> None:
        super().__init__(output=output, **kwargs)

    async def on_item_completed(self, o):
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
