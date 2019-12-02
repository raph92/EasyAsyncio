import asyncio
from abc import ABC

from .baseasyncioobject import BaseAsyncioObject
from .producer import Producer


class Consumer(BaseAsyncioObject, ABC):
    proceeded_by: Producer  # what producer will be started by this Consumer

    def __init__(self) -> None:
        super().__init__()

    async def worker(self, *args):
        try:
            async with self.sem:
                data = await self.preprocess(*args)
                result = await self.work(data)
                self.queue.task_done()
                self.results.append(await self.postprocess(result))
        except RuntimeError:
            pass

    async def run(self):
        """fill the queue for the worker then start it"""
        self.logger.info('%s starting...', self.name)
        try:
            while self.context.running:
                self.logger.debug('%s awaiting object from queue', self.name)
                data = await self.queue.get()
                self.logger.debug('%s un-queued data: %s', self.name, data)
                if data is False:
                    self.logger.debug('%s breaking', self.name)
                    self._done = True
                    break
                task = self.loop.create_task(self.worker(data))
                self.tasks.add(task)
        except Exception as e:
            self.logger.exception(e)
        await asyncio.gather(*self.tasks)
        self.logger.info('%s is finished: %s', self.name, self.results)
