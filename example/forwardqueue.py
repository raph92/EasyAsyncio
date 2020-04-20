import asyncio
import logging

from easyasyncio import JobManager, Job
from easyasyncio.job import ForwardQueuingJob


class AddOneJob(ForwardQueuingJob):

    async def do_work(self, num):
        # do something meaningful here
        await asyncio.sleep(0.01)
        self.log.debug('sending "%s" to successor', num)
        return num + 1


class AddTwoJob(ForwardQueuingJob):

    async def do_work(self, num):
        # do something meaningful here
        await asyncio.sleep(0.01)
        self.log.debug('sending "%s" to successor', num)
        return num + 2


class TimesTwoJob(ForwardQueuingJob):

    async def do_work(self, num):
        # do something meaningful here
        await asyncio.sleep(0.01)
        self.log.debug('sending "%s" to successor', num)
        return num * 2


class PrintJob(Job):
    """print numbers asynchronously"""

    async def on_item_completed(self, obj):
        print(obj)

    async def do_work(self, number):
        """this logic gets called after an
        object is retrieved from the queue"""
        await asyncio.sleep(0.01)
        return number


manager = JobManager()

print_job = PrintJob(max_concurrent=15, log_level=logging.DEBUG,
                     print_successes=False)
times_two = TimesTwoJob(input_data=[],
                        max_concurrent=15, log_level=logging.DEBUG)
add_two = AddTwoJob(input_data=[],
                    max_concurrent=15, log_level=logging.DEBUG)
add_one = AddOneJob(input_data=range(1, 50 + 1),
                    max_concurrent=15, log_level=logging.DEBUG)

manager.add_jobs(add_one, add_two, times_two, print_job)
manager.start()

# manager.start_graphics()
