import asyncio

from easyasyncio import Producer, LoopManager, Consumer


class CharConsumer(Consumer):
    """print numbers asynchronously"""

    def __init__(self) -> None:
        super().__init__()

    async def work(self, char):
        """this logic gets called after an object is retrieved from the queue"""
        await asyncio.sleep(1, 5)
        self.logger.info(char)
        self.increment_stat()

    @property
    def name(self):
        """
        Name the object or service being provided.
        This will effect how the DataHandler displays information about
        this Prosumer.
        """
        return 'consume_char'


class CharProducer(Producer):

    def __init__(self, data: str):
        super().__init__(list(data))

    async def fill_queue(self):
        for i in self.data:
            await self.queue.put(i)

    async def work(self, char):
        self.logger.debug('%s adding %s to consume_number queue', self.name, char)
        await self.context.queues['consume_char'].put(char)
        self.increment_stat()

    async def tear_down(self):
        await self.context.queues['consume_char'].put(False)

    @property
    def name(self):
        return 'produce_char'


manager = LoopManager()
producer = CharProducer('Hello Worlddddddddddddddddddddddddddddd')
consumer = CharConsumer()
# producer.add_successor(consumer)
consumer.max_concurrent = 5
manager.add_tasks(producer, consumer)

manager.start()
