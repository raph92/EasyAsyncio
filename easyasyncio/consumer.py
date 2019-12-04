import asyncio
from abc import ABC

from .baseasyncioobject import BaseAsyncioObject
from .producer import Producer


class Consumer(BaseAsyncioObject, ABC):
    proceeded_by: Producer  # what producer will be started by this Consumer
    working = 0

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)

    async def worker(self, *args):
        self.working += 1
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
        self.logger.info('%s starting...', self.name)
        self.status('starting')
        await self.fill_queue()
        try:
            while self.context.running:
                self.status('waiting for queue object')
                try:
                    data = await self.queue.get()
                except RuntimeError as e:
                    return
                else:
                    if data is False:
                        self.logger.debug('%s breaking', self.name)
                        self._done = True
                        break
                    self.status('creating worker for', data)
                    task = self.loop.create_task(self.worker(data))
                    self.tasks.add(task)
        except Exception as e:
            self.logger.exception(e)
        self.status('finished with queue. Waiting for tasks to finish')
        await asyncio.gather(*self.tasks)
        await self.tear_down()
        self.status('finished')
        self.logger.info('%s is finished: %s', self.name, self.results)
