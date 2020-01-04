import asyncio
from typing import Optional

from easyasyncio import JobManager, Job
from easyasyncio.job import ForwardQueuingJob, OutputJob


class ConsumerNumberExample(OutputJob):
    """print numbers asynchronously"""

    def __init__(self, output: Optional[str] = '', **kwargs) -> None:
        super().__init__(output, **kwargs)

    async def fill_queue(self):
        pass

    async def do_work(self, number):
        """this logic gets called after an object
         is retrieved from the queue"""
        await asyncio.sleep(1)
        return number

    @property
    def name(self):
        """
        Name the object or service being provided.
        This will effect how the StatsDisplay displays information about
        this Job.
        """
        return 'consume_number'


class ExampleProducer(ForwardQueuingJob):

    def __init__(self, successor: Job, **kwargs) -> None:
        super().__init__(successor, **kwargs)

    async def fill_queue(self):
        for i in self.input_data:
            await self.queue.put(i)
        await self.queue_finished()

    async def do_work(self, num):
        return num

    async def on_finish(self):
        await self.successor.queue_finished()

    @property
    def name(self):
        return 'produce_number'


manager = JobManager(False)
consumer = ConsumerNumberExample(enable_cache=True)
producer = ExampleProducer(consumer, input_data=range(100),
                           enable_cache=False)
consumer.max_concurrent = 5
manager.add_jobs(consumer, producer)

manager.start()

# manager.start_graphics()
