import asyncio
import datetime
import random

from easyasyncio import Producer, LoopManager, Consumer


class AutoSaveExample(Consumer):
    """print numbers asynchronously"""

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)

    async def fill_queue(self):
        for i in range(100):
            if i not in self.context.data['numbers']:
                await self.queue.put(i)
        await self.queue_finished()

    async def work(self, number):
        """this logic gets called after an object is retrieved from the queue"""
        sum(list(range(number)))
        self.increment_stat()
        await asyncio.sleep(random.randint(1, 5))
        self.context.data['numbers'].add(number)

    async def tear_down(self):
        print(self.name, 'done at', datetime.datetime.now())

    @property
    def name(self):
        """
        Name the object or service being provided.
        This will effect how the DataHandler displays information about
        this Prosumer.
        """
        return 'consume_number'


class ExampleProducer(Producer):

    def __init__(self, data, **kwargs):
        super().__init__(data, **kwargs)

    async def fill_queue(self):
        for i in range(self.data):
            await self.queue.put(i)

    async def work(self, num):
        sum(list(range(num)))
        self.increment_stat()
        await asyncio.sleep(random.randint(1, 5))

    async def tear_down(self):
        print(self.name, 'done at', datetime.datetime.now())

    @property
    def name(self):
        return 'produce_number'


manager = LoopManager()
consumer = AutoSaveExample(max_concurrent=15)
producer = ExampleProducer(100, max_concurrent=5)

manager.context.data.register('numbers', set(), './numbers/numbers.txt')

manager.add_tasks(consumer)
manager.start()
