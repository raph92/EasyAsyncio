import abc
import asyncio
from abc import abstractmethod

from .context import Context


class Prosumer(metaclass=abc.ABCMeta):
    tasks = set()
    max_concurrent = 10

    def __init__(self, data, context: Context):
        self.data = data
        self.context = context
        self.logger = context.logger
        self.loop = context.loop
        self.context.prosumers.add(self)
        self.queue = context.queues.new(self.name)

    @property
    @abstractmethod
    def name(self):
        pass

    async def run(self):
        """fill the queue for the worker then start it"""
        await self.fill_queue()
        for _ in range(min(self.queue.qsize(), self.max_concurrent)):
            self.tasks.add(self.loop.create_task(self.worker()))
        await asyncio.gather(*self.tasks)
        await self.queue.join()
        self.logger.info('%s is finished', self.name)

    @abstractmethod
    async def fill_queue(self):
        """implement the queue filling logic here"""
        pass

    async def worker(self):
        """get each item from the queue and pass it to self.work"""
        while self.context.running:
            if self.queue.empty():
                break
            data = await self.queue.get()
            result = await self.work(data)
            if result:
                self.append()
            self.queue.task_done()

    @abstractmethod
    async def work(self, *args):
        """do business logic on each enqueued item"""
        pass

    def append(self, n=1):
        """increment the count of whatever this prosumer is processing"""
        self.context.stats[self] += n

    def __repr__(self):
        return self.name

    def __str__(self):
        return self.name
