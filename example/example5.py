import asyncio
import datetime
import random

from easyasyncio import Producer, LoopManager, Consumer


class ConsumerNumberExample(Consumer):
    """print numbers asynchronously"""

    async def fill_queue(self):
        pass

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)

    async def work(self, number):
        """this logic gets called after an object is retrieved from the queue"""
        sum(list(range(number)))
        self.increment_stat()
        await asyncio.sleep(random.randint(1, 5))
        self.log.info('printed %s', number)
        return number

    async def tear_down(self):
        self.log.info(self.name, 'done at', datetime.datetime.now())

    @property
    def name(self):
        """
        Name the object or service being provided.
        This will effect how the StatsDisplay displays information about
        this Prosumer.
        """
        return 'consume_number'


class ExampleProducer(Producer):

    def __init__(self, data, **kwargs):
        super().__init__(data, **kwargs)

    async def fill_queue(self):
        for i in range(self.input_data):
            await self.queue.put(i)
        await self.queue_finished()

    async def work(self, num):
        sum(list(range(num)))
        self.increment_stat()
        await self.queue_successor(num)

    async def tear_down(self):
        self.log.info(self.name, 'done at', datetime.datetime.now())

    @property
    def name(self):
        return 'produce_number'


manager = LoopManager()

consumer = ConsumerNumberExample(max_concurrent=5)
producer = ExampleProducer(10, max_concurrent=5)
producer.add_successor(consumer)
manager.add_tasks(producer, consumer)
manager.start()

manager.start_graphics()
