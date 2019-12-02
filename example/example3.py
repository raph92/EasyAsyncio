import asyncio
import random

from easyasyncio import Prosumer, LoopManager, Consumer


class ConsumerNumberExample(Consumer):
    """print numbers asynchronously"""

    async def worker(self):
        return await super().worker()

    async def work(self, number):
        """this logic gets called after an object is retrieved from the queue"""
        sleep_time = random.randint(1, 3)
        await asyncio.sleep(sleep_time)
        self.logger.info(number)
        return True

    @property
    def name(self):
        """
        Name the object or service being provided.
        This will effect how the DataHandler displays information about
        this Prosumer.
        """
        return 'consume_number'


class Producer(Prosumer):

    async def fill_queue(self):
        for i in range(self.data):
            self.queue.put_nowait(i)

    async def work(self, num):
        await self.context.queues['consume_number'].put(num)

    @property
    def name(self):
        return 'produce_number'


manager = LoopManager()
consumer = ConsumerNumberExample()
producer = Producer(30)
manager.add_tasks(consumer)

manager.start()
