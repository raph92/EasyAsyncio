import asyncio

from easyasyncio import Producer, LoopManager, Consumer


class ConsumerNumberExample(Consumer):
    """print numbers asynchronously"""

    def __init__(self) -> None:
        super().__init__()

    async def work(self, number):
        """this logic gets called after an object is retrieved from the queue"""
        await asyncio.sleep(1)
        self.logger.info(number)
        self.append()

    @property
    def name(self):
        """
        Name the object or service being provided.
        This will effect how the DataHandler displays information about
        this Prosumer.
        """
        return 'consume_number'


class ExampleProducer(Producer):

    def __init__(self, data):
        super().__init__(data)

    async def fill_queue(self):
        for i in range(self.data):
            await self.queue.put(i)

    async def work(self, num):
        self.logger.debug('%s adding %s to consume_number queue', self.name, num)
        await self.context.queues['consume_number'].put(num)
        self.append()

    async def tear_down(self):
        await self.context.queues['consume_number'].put(False)

    @property
    def name(self):
        return 'produce_number'


manager = LoopManager()
consumer = ConsumerNumberExample()
producer = ExampleProducer(100)
consumer.max_concurrent = 5
manager.add_tasks(consumer, producer)

manager.start()
