import abc
import asyncio
from abc import abstractmethod
from asyncio import AbstractEventLoop
from logging import Logger

from .context import Context


class BaseAsyncioObject(abc.ABC):
    workers = set()
    max_concurrent = 10
    context: Context
    logger: Logger
    loop: AbstractEventLoop
    queue: asyncio.Queue

    @abstractmethod
    async def worker(self):
        pass

    def append(self, n=1):
        """increment the count of whatever this prosumer is processing"""
        self.context.stats[self] += n

    def initialize(self, context):
        self.context = context
        self.logger = context.logger
        self.loop = context.loop
        self.context.workers.add(self)
        self.queue = context.queues.new(self.name)

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
