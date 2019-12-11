import asyncio
from abc import ABC
from asyncio import CancelledError
from time import time

from .abstractasyncworker import AbstractAsyncWorker
from .producer import Producer


class Consumer(AbstractAsyncWorker, ABC):
    proceeded_by: Producer  # what producer will be started by this Consumer

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)

    async def worker(self, *args):
        self.working += 1  # keeps track of the number of workers
        try:
            async with self.sem:
                data = await self.preprocess(*args)
                result = await self.work(data)
                self.queue.task_done()
                self.results.append(await self.postprocess(result))
        except RuntimeError:
            pass
        finally:
            self.working -= 1

    async def run(self):
        """fill the queue for the worker then start it"""
        self.log.debug('%s starting...', self.name)
        self.status('starting')
        await self.fill_queue()
        try:
            while self.context.running:
                self.status('grabbing data')
                try:
                    data = await self.queue.get()
                except (RuntimeError, CancelledError):
                    self.status('Stopped')
                    return
                else:
                    if data is False:
                        self.log.debug('%s finished creating tasks', self.name)
                        self._done = True
                        break
                    self.status('creating worker')
                    task = self.loop.create_task(self.worker(data))
                    self.tasks.add(task)
        except Exception as e:
            self.log.debug(str(e))
            self.status('Stopped')

        self.status('processing')
        await asyncio.gather(*self.tasks, loop=self.loop)
        await self.tear_down()
        self.end_time = time()
        self.status('finished')
        if self.with_errors:
            self.log.warning('Some errors occurred. See logs')
        self.log.debug('%s is finished: %s', self.name, self.results)
