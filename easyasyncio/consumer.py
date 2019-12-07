import asyncio
from abc import ABC
from asyncio import CancelledError

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
        self.logger('%s starting...', self.name)
        self.status('starting')
        await self.fill_queue()
        try:
            while self.context.running:
                self.status('waiting for queue object')
                try:
                    data = await self.queue.get()
                except (RuntimeError, CancelledError):
                    return

                else:
                    if data is False:
                        self.logger('%s finished creating tasks', self.name)
                        self._done = True
                        break
                    self.status('creating worker for', data)
                    task = self.loop.create_task(self.worker(data))
                    self.tasks.add(task)
        except Exception as e:
            self.logger(str(e))
        self.status('processing')
        await asyncio.gather(*self.tasks, loop=self.loop)
        await self.tear_down()
        self.status('finished')
        self.logger('%s is finished: %s', self.name, self.results)
