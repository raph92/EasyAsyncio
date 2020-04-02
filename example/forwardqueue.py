import asyncio
import datetime
import logging
import random

from easyasyncio import JobManager, Job
from easyasyncio.job import ForwardQueuingJob


class QueueJob(ForwardQueuingJob):

    def __init__(self, successor: Job, **kwargs) -> None:
        super().__init__(successor, **kwargs)

    async def do_work(self, num):
        # do something meaningful here
        await asyncio.sleep(0.01)
        self.log.debug('sending "%s" to successor', num)
        return list(range(num + 1))

    async def on_finish(self):
        await super().on_finish()
        self.log.info('done at %s', datetime.datetime.now())


class PrintJob(Job):
    """print numbers asynchronously"""

    async def on_item_completed(self, obj):
        print(obj)

    async def do_work(self, number):
        """this logic gets called after an
        object is retrieved from the queue"""
        await asyncio.sleep(random.randint(0, 5))
        return number

    async def on_finish(self):
        await super().on_finish()
        self.log.info('done at %s', datetime.datetime.now())


manager = JobManager()

consumer = PrintJob(max_concurrent=15,
                    max_queue_size=5, log_level=logging.DEBUG,
                    print_successes=True)
producer = QueueJob(consumer,
                    input_data=range(10, 11),
                    max_concurrent=15, log_level=logging.DEBUG,
                    print_successes=True)

manager.add_jobs(producer, consumer)
manager.start()

# manager.start_graphics()
