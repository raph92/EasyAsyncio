import abc
import asyncio
from abc import abstractmethod
from asyncio import CancelledError

from .abstractasyncworker import AbstractAsyncWorker


class Producer(AbstractAsyncWorker, metaclass=abc.ABCMeta):
    start = False  # whether this Producer will start instantly or not

    def __init__(self, data, **kwargs):
        super().__init__(**kwargs)
        self.data = data

    @abstractmethod
    async def fill_queue(self):
        """implement the queue filling logic here"""
        pass

    async def worker(self, num):
        """get each item from the queue and pass it to self.work"""
        self.logger('%s worker %s started', self.name, num)
        while self.context.running:
            try:
                data = await self.queue.get()
            except (RuntimeError, CancelledError):
                return
            if data is False:
                self.logger('%s worker %s terminating', self.name, num)
                break
            # self.logger('%s worker %s retrieved queued data %s', self.name, num, data)
            data = await self.preprocess(data)
            async with self.sem:
                result = await self.work(data)
                self.queue.task_done()
                self.results.append(await self.postprocess(result))

    async def queue_finished(self):
        for _ in self.tasks:
            await self.queue.put(False)

    async def run(self):
        self.logger('%s starting...', self.name)
        try:
            self.status('populating queue')
            await self.fill_queue()
            self.logger(self.name + ' finished populating queue')
        except Exception as e:
            self.logger(str(e))
            raise e
        else:
            self.status('creating workers')
            for _ in range(self.max_concurrent):
                self.tasks.add(self.loop.create_task(self.worker(_)))
            self.logger(self.name + ' finished creating workers')
            self.status('processing')
            await self.queue_finished()
            await asyncio.gather(*self.tasks, loop=self.loop)
            await self.tear_down()
            self.status('finished')
            self.logger('%s is finished: %s', self.name, self.results)
