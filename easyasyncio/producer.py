import abc
import asyncio
from abc import abstractmethod
from asyncio import CancelledError
from time import time
from typing import Any, Coroutine

from .abstractasyncworker import AbstractAsyncWorker


class Producer(AbstractAsyncWorker, metaclass=abc.ABCMeta):
    start = False  # whether this Producer will start instantly or not

    def __init__(self, data: Any = None,
                 **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.data = data

    @abstractmethod
    async def fill_queue(self) -> None:
        """implement the queue filling logic here"""

    async def worker(self, num: int) -> Coroutine:
        """get each item from the queue and pass it to self.work"""
        self.log.debug('%s worker %s started', self.name, num)
        while self.context.running:
            try:
                data = await self.queue.get()
            except (RuntimeError, CancelledError) as e:
                return e
            if data is False:
                self.log.debug('%s worker %s terminating', self.name, num)
                break
            self.log.debug('%s worker %s retrieved queued data %s', self.name,
                           num, data)
            data = await self.preprocess(data)
            result = await self.work(data)
            self.queue.task_done()
            self.results.append(await self.postprocess(result))

    async def queue_finished(self):
        for _ in self.tasks:
            await self.queue.put(False)

    async def run(self):
        self.log.debug('%s starting...', self.name)
        try:
            self.status('filling queue')
            await self.fill_queue()
            self.log.debug('%s finished populating queue', self.name)
        except Exception as e:
            self.log.debug(str(e))
            raise e
        else:
            self.status('creating workers')
            for _ in range(self.max_concurrent):
                self.tasks.add(self.loop.create_task(self.worker(_)))
            self.log.debug('%s finished creating workers', self.name)
            self.status('processing')
            await self.queue_finished()
            await asyncio.gather(*self.tasks, loop=self.loop)
            await self.tear_down()
            self.end_time = time()
            self.status('finished')
            self.log.debug('%s is finished: %s', self.name, self.results)
            if self.with_errors:
                self.log.warning('Some errors occurred. See logs')
