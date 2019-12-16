import abc
import asyncio
import logging
from abc import abstractmethod
from asyncio import (AbstractEventLoop, Semaphore, Future, Queue,
                     QueueFull)
from collections import deque, Counter
from time import time
from typing import Set, Optional, Any

from .context import Context


class Job(abc.ABC):
    tasks: Set[Future]
    max_concurrent: int
    context: Context
    loop: AbstractEventLoop
    sem: Semaphore
    end_time: float
    input_data: Any

    def __init__(self, input_data=None,
                 max_concurrent=20,
                 max_queue_size=0,
                 predecessor: 'Optional[Job]' = None) -> None:
        self.input_data = input_data
        self.max_concurrent = max_concurrent
        self.stats = Counter()
        self.tasks = set()
        self.info = dict()
        self.results = []
        self.info['max_queue_size'] = ('infinite' if max_queue_size == 0
                                       else max_queue_size)
        self.info['max_workers'] = max_concurrent
        self._done = False
        self.predecessor = predecessor
        self.successor: 'Optional[Job]' = None
        if predecessor:
            predecessor.add_successor(self)
            self.info['supersedes'] = predecessor.name
        self._status = ''
        self.logs: deque[str] = deque(maxlen=50)
        self.working = 0
        self.log = logging.getLogger(self.name)
        self.with_errors = False
        self.running = False
        self._queue_size = max_queue_size

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
        self.context.jobs.add(self)
        self.sem = Semaphore(self.max_concurrent, loop=self.loop)
        self.context.queues.new(self.name, self._queue_size)
        self.status('initialized')

    async def run(self):
        """setup workers and start"""
        self.log.debug('starting...')
        self.running = True
        try:
            # create workers
            self.create_workers()
        except Exception as e:
            self.log.exception(e)
        else:
            # fill queue
            self.status('filling queue')
            self.log.debug('creating queue...')
            await self.fill_queue()
            # process
            self.status('working')
            await asyncio.gather(*self.tasks, loop=self.loop)
        finally:
            self.running = False
            # finish
            await self._on_finish()

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
            try:
                data = await self.queue.get()
            except (RuntimeError, CancelledError) as e:
                return e
            if data is False:
                self.log.debug('worker %s terminating', num)
                break
            self.log.debug('worker %s retrieved queued data %s',
                           num, data)
            result = await self.do_work(data)
            self.queue.task_done()
            self.results.append(result)

    @abstractmethod
    async def do_work(self, *args):
        """do business logic on each enqueued item"""

    async def _on_finish(self):
        self.end_time = time()
        self.status('finished')
        self.log.debug('finished: %s', self.results)
        if self.with_errors:
            self.log.warning('Some errors occurred. See logs')

    async def queue_finished(self):
        """called when all tasks are finished with queue"""
        self.log.debug('finished queueing')
        for _ in self.tasks:
            try:
                await self.queue.put(False)
            except QueueFull:
                while not self.queue.empty():
                    await self.queue.get()

    def increment_stat(self, n=1, name: str = None) -> None:
        """increment the count of whatever this prosumer is processing"""
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

    async def queue_predecessor(self, data):
        await self.predecessor.queue.put(data)

    def status(self, *strings: str):
        status = ' '.join(
                [str(s) if not isinstance(s, str) else s for s in strings])
        self.info['status'] = status

    def time_left(self):
        elapsed_time = self.context.stats.elapsed_time
        per_second = self.context.stats[self.name] / elapsed_time
        return round((self.queue.qsize() + self.working) / per_second)

    def __repr__(self):
        return self.name

    def __str__(self):
        return self.name


class WorkerLoggingHandler(logging.Handler):
    def __init__(self, worker: Job,
                 level=logging.DEBUG) -> None:
        super().__init__(level)
        self.worker = worker

    def emit(self, record: logging.LogRecord) -> None:
        self.worker.logs.append(record.getMessage())
