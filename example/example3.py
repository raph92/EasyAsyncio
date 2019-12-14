import asyncio

from easyasyncio import Producer, JobManager, Consumer


class ConsumerNumberExample(Consumer):
    """print numbers asynchronously"""

    def __init__(self) -> None:
        super().__init__()

    async def do_work(self, number):
        """this logic gets called after an object is retrieved from the queue"""
        await asyncio.sleep(1)
        self.logger(number)
        self.increment_stat()

    @property
    def name(self):
        """
        Name the object or service being provided.
        This will effect how the StatsDisplay displays information about
        this Prosumer.
        """
        return 'consume_number'


class ExampleProducer(Producer):

    def __init__(self, data):
        super().__init__(data)

    async def fill_queue(self):
        for i in range(self.input_data):
            await self.queue.put(i)
        await self.queue_finished()

    async def do_work(self, num):
        await self.queue_successor(num)
        self.increment_stat()

    async def on_finish(self):
        await self.successor.queue_finished()

    @property
    def name(self):
        return 'produce_number'


manager = JobManager(False)
consumer = ConsumerNumberExample()
producer = ExampleProducer(100)
producer.add_successor(consumer)
consumer.max_concurrent = 5
manager.add_jobs(consumer, producer)

manager.start()

manager.start_graphics()
