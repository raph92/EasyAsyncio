import abc
import asyncio
import logging
from abc import abstractmethod
from asyncio import AbstractEventLoop, Semaphore, Future, Queue, CancelledError
from collections import deque
from time import time
from typing import Set, Optional

from .context import Context


class AbstractAsyncWorker(abc.ABC):
    tasks: Set[Future]
    max_concurrent: int
    context: Context
    loop: AbstractEventLoop
    sem: Semaphore
    end_time = None

    def __init__(self, max_concurrent=20) -> None:
        self.tasks = set()
        self.max_concurrent = max_concurrent
        self.stats = set()
        self.results = []
        self._done = False
        self.successor: 'Optional[AbstractAsyncWorker]' = None
        self._status = ''
        self.logs: deque[str] = deque(maxlen=50)
        self.working = 0
        self.log = logging.getLogger(type(self).__name__)
        self.log.addHandler(WorkerLoggingHandler(self))
        self.with_errors = False
        self.running = False

    @property
    def queue(self) -> Queue:
        return self.context.queues.get(self.name)

    @property
    @abstractmethod
    def name(self):
        pass

    def initialize(self, context: Context):
        self.context = context
        self.loop = context.loop
        self.context.workers.add(self)
        self.sem = Semaphore(self.max_concurrent)
        self.context.queues.new(self.name)
        self.status('initialized')

    async def run(self):
        """setup workers and start"""
        self.log.debug('starting...')
        self.running = True
        try:
            self.status('filling queue')
            self.log.debug('creating queue...')
            # create workers
            self.create_workers()
        except Exception as e:
            self.log.exception(e)
        else:
            # fill queue
            await self.fill_queue()
            # process
            await asyncio.gather(*self.tasks, loop=self.loop)
        finally:
            self.running = False
            # finish
            await self.tear_down()

    @abstractmethod
    async def fill_queue(self):
        """implement the queue filling logic here"""
        pass

    def create_workers(self):
        self.status('creating workers')
        self.log.debug('creating workers...')
        for _ in range(self.max_concurrent):
            self.tasks.add(self.loop.create_task(self.worker(_)))

    async def pre_process(self, item):
        """do any pre-processing to the queue item here"""
        return item

    async def worker(self, num: int):
        """get each item from the queue and pass it to self.work"""
        self.log.debug('worker %s started', num)
        while self.context.running:
            try:
                data = await self.queue.get()
            except (RuntimeError, CancelledError) as e:
                return e
            if data is False:
                self.log.debug('worker %s terminating', num)
                break
            self.log.debug('worker %s retrieved queued data %s',
                           num, data)
            data = await self.pre_process(data)
            result = await self.work(data)
            self.queue.task_done()
            self.results.append(await self.post_process(result))
            self.status('finished')

    @abstractmethod
    async def work(self, *args):
        """do business logic on each enqueued item"""

    async def post_process(self, item):
        """do any postprocessing to the resulting item here"""
        return item

    async def tear_down(self):
        """this is called after all tasks are completed"""
        self.end_time = time()
        self.status('finished')
        self.log.debug('finished: %s', self.results)
        if self.with_errors:
            self.log.warning('Some errors occurred. See logs')

    async def queue_finished(self):
        """called when all tasks are finished with queue"""
        self.log.debug('finished queueing')
        for _ in self.tasks:
            await self.queue.put(False)

    def increment_stat(self, n=1, name: str = None) -> None:
        """increment the count of whatever this prosumer is processing"""
        if not name:
            name = self.name
        self.stats.add(name)
        self.context.stats[name] += n

    async def queue_successor(self, data):
        await self.successor.queue.put(data)

    def add_successor(self, successor: 'AbstractAsyncWorker'):
        """
        The next async worker that will work on the data that
        this async worker gathers
        """
        assert successor != self
        self.successor = successor

    def status(self, *strings: str):
        self._status = ' '.join(
                [str(s) if not isinstance(s, str) else s for s in strings])

    def logger(self, string: str, *args):
        self.log.info(string)

    def time_left(self):
        elapsed_time = self.context.stats.elapsed_time
        per_second = self.context.stats[self.name] / elapsed_time
        return round((self.queue.qsize() + self.working) / per_second)

    def __repr__(self):
        return self.name

    def __str__(self):
        return self.name


class WorkerLoggingHandler(logging.Handler):
    def __init__(self, worker: AbstractAsyncWorker,
                 level=logging.DEBUG) -> None:
        super().__init__(level)
        self.worker = worker

    def emit(self, record: logging.LogRecord) -> None:
        self.worker.logs.append(record.getMessage())
