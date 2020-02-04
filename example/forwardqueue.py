import asyncio
import datetime
import random

from easyasyncio import JobManager, Job
from easyasyncio.job import ForwardQueuingJob


class QueueJob(ForwardQueuingJob):
    async def fill_queue(self):
        for i in range(self.input_data):
            await self.queue.put(i)
        await self.queue_finished()

    async def do_work(self, num):
        # do something meaning full here
        await asyncio.sleep(0.01)
        self.log.debug('sending "%s" to successor', num)
        return num

    async def on_finish(self):
        await super().on_finish()
        self.log.info('done at %s', datetime.datetime.now())

    @property
    def name(self):
        return 'QueueNumJob'


class PrintJob(Job):
    """print numbers asynchronously"""

    async def fill_queue(self):
        pass

    async def do_work(self, number):
        """this logic gets called after an
        object is retrieved from the queue"""
        await asyncio.sleep(random.random())
        return number

    async def on_finish(self):
        self.log.info('done at %s', datetime.datetime.now())

    @property
    def name(self):
        """
        Name the object or service being provided.
        This will effect how the StatsDisplay displays information about
        this Job.
        """
        return 'PrintNumJob'


manager = JobManager()

consumer = PrintJob(max_concurrent=15,
                    max_queue_size=5)
producer = QueueJob(consumer,
                    input_data=100,
                    max_concurrent=15,
                    caching=False)

manager.add_jobs(producer, consumer)
manager.start()

manager.start_graphics()
