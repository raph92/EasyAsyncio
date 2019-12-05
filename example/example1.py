import asyncio
import random

from easyasyncio import Producer, LoopManager


class PrintNumbersProducer(Producer):
    """print numbers asynchronously"""

    def __init__(self, data: int, **kwargs):
        super().__init__(data, **kwargs)

    async def fill_queue(self):
        """override this abstract class to fill the queue"""
        for i in range(0, self.data):
            await self.queue.put(i)

    async def work(self, number):
        """implement the business logic here"""
        sleep_time = random.randint(1, 3)
        await asyncio.sleep(sleep_time)
        self.logger.info(number)
        self.increment_stat()

    @property
    def name(self):
        """
        Name the object or service being provided.
        This will effect how the DataHandler displays information about
        this Prosumer.
        """
        return 'print_number'


manager = LoopManager()
manager.add_tasks(PrintNumbersProducer(1000, max_concurrent=15))
manager.start()
