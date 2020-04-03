import asyncio
import logging

from easyasyncio import JobManager, Job
from easyasyncio.job import ForwardQueuingJob


class AddOneJob(ForwardQueuingJob):

    def __init__(self, successor: Job, **kwargs) -> None:
        super().__init__(successor, **kwargs)

    async def do_work(self, num):
        # do something meaningful here
        await asyncio.sleep(0.01)
        self.log.debug('sending "%s" to successor', num)
        return num + 1


class AddTwoJob(ForwardQueuingJob):

    def __init__(self, successor: Job, **kwargs) -> None:
        super().__init__(successor, **kwargs)

    async def do_work(self, num):
        # do something meaningful here
        await asyncio.sleep(0.01)
        self.log.debug('sending "%s" to successor', num)
        return num + 2


class TimesTwoJob(ForwardQueuingJob):

    def __init__(self, successor: Job, **kwargs) -> None:
        super().__init__(successor, **kwargs)

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

print_job = PrintJob(max_concurrent=15,
                     max_queue_size=5, log_level=logging.DEBUG,
                     print_successes=False)
times_two = TimesTwoJob(print_job,
                        input_data=[],
                        max_concurrent=15, log_level=logging.DEBUG)
add_two = AddTwoJob(times_two,
                    input_data=[],
                    max_concurrent=15, log_level=logging.DEBUG)
add_one = AddOneJob(add_two,
                    input_data=range(1, 50 + 1),
                    max_concurrent=15, log_level=logging.DEBUG)

manager.add_jobs(print_job, times_two, add_two, add_one)
manager.start()

# manager.start_graphics()
