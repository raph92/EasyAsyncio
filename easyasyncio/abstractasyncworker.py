import abc
from abc import abstractmethod
from asyncio import AbstractEventLoop, Semaphore, Future, Queue
from collections import deque
from typing import Set, Optional

from . import start_date
from .context import Context


# noinspection PyMethodMayBeStatic
class AbstractAsyncWorker(abc.ABC):
    tasks: Set[Future]
    max_concurrent: int
    context: Context
    loop: AbstractEventLoop
    sem: Semaphore
    end_time = None

    def __init__(self, max_concurrent=10) -> None:
        self.tasks = set()
        self.max_concurrent = max_concurrent
        self.stats = set()
        self.results = []
        self._done = False
        self.successor: 'Optional[AbstractAsyncWorker]' = None
        self._status = ''
        self.logs: deque[str] = deque(maxlen=50)
        self.working = 0

    @property
    def queue(self) -> Queue:
        return self.context.queues.get(self.name)

    def increment_stat(self, n=1, name=None):
        """increment the count of whatever this prosumer is processing"""
        if not name:
            name = self.name
        self.stats.add(name)
        self.context.stats[name] += n

    def initialize(self, context: Context):
        self.context = context
        self.loop = context.loop
        self.context.workers.add(self)
        self.sem = Semaphore(self.max_concurrent)
        self.context.queues.new(self.name)
        self.context.data.register(f'{self.name}_logs', list(), f'logs/{start_date}/{self.name}.logs',
                                   False, False)
        self.status('initialized')

    async def preprocess(self, item):
        """do any pre-processing to the queue item here"""
        return item

    async def postprocess(self, item):
        """do any postprocessing to the resulting item here"""
        return item

    async def queue_finished(self):
        """called when all tasks are finished with queue"""
        self.logger(self.name + ' finished queueing')
        await self.queue.put(False)

    async def fill_queue(self):
        pass

    def status(self, *strings: str):
        self._status = ' '.join([str(s) if not isinstance(s, str) else s for s in strings])

    async def tear_down(self):
        """this is called after all tasks are completed"""
        pass

    async def queue_successor(self, data):
        await self.successor.queue.put(data)

    def add_successor(self, successor: 'AbstractAsyncWorker'):
        """
        The next async worker that will work on the data that this async worker gathers
        """
        assert successor != self
        self.successor = successor

    @abstractmethod
    async def run(self):
        """setup workers and start"""
        pass

    @abstractmethod
    async def work(self, *args):
        """do business logic on each enqueued item"""
        pass

    @property
    @abstractmethod
    def name(self):
        pass

    def __repr__(self):
        return self.name

    def __str__(self):
        return self.name

    def logger(self, string: str, *args):
        from datetime import datetime
        try:
            string = string.replace('%s', '{}').format(*args)
        except:
            pass
        message = f'[{datetime.now().strftime("%H:%M:%S")}] {string}'
        self.logs.append(message)
        self.context.data[f'{self.name}_logs'].append(message)
        # logger.info(message)

    def time_left(self):
        elapsed_time = self.context.stats.elapsed_time
        per_second = self.context.stats[self.name] / elapsed_time
        return round((self.queue.qsize() + self.working) / per_second)
