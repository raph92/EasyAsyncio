import asyncio
from abc import ABC

from .baseasyncioobject import BaseAsyncioObject


class Consumer(BaseAsyncioObject, ABC):

    def __init__(self) -> None:
        super().__init__()

    async def worker(self):
        """get each item from the queue and pass it to self.work"""
        while self.context.running:
            data = await self.queue.get()
            if data is None:
                break
            result = await self.work(data)
            if result:
                self.append()
            self.queue.task_done()

    async def run(self):
        """fill the queue for the worker then start it"""
        self.logger.info('%s starting...', self.name)
        for _ in range(self.max_concurrent):
            self.workers.add(self.loop.create_task(self.worker()))
        await asyncio.gather(*self.workers)
        if not self.context.running:
            return
        await self.queue.join()
        self.logger.info('%s is finished', self.name)
