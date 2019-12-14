import asyncio
import datetime
import random

from easyasyncio import JobManager, Job


class PrintJob(Job):
    """print numbers asynchronously"""

    async def fill_queue(self):
        pass

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)

    async def do_work(self, number):
        """this logic gets called after an
        object is retrieved from the queue"""
        sum(list(range(number)))
        self.increment_stat()
        await asyncio.sleep(random.randint(1, 5))
        self.log.info('printed %s', number)
        return number

    async def on_finish(self):
        self.log.info('done at %s', datetime.datetime.now())

    @property
    def name(self):
        """
        Name the object or service being provided.
        This will effect how the StatsDisplay displays information about
        this Prosumer.
        """
        return 'PrintNumJob'


class QueueJob(Job):

    def __init__(self, data, **kwargs):
        super().__init__(data, **kwargs)

    async def fill_queue(self):
        for i in range(self.input_data):
            await self.queue.put(i)
        await self.queue_finished()

    async def do_work(self, num):
        sum(list(range(num)))
        self.increment_stat()
        self.log.debug('adding %s to successor', num)
        await self.queue_successor(num)
        self.log.debug('done adding %s to successor', num)

    async def on_finish(self):
        self.log.info('done at %s', datetime.datetime.now())
        await self.successor.queue_finished()

    @property
    def name(self):
        return 'QueueNumJob'


manager = JobManager()

producer = QueueJob(100, max_concurrent=5)
consumer = PrintJob(max_concurrent=5,
                    predecessor=producer,
                    max_queue_size=5)
manager.add_jobs(producer, consumer)
manager.start()

# manager.start_graphics()
