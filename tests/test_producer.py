import asyncio
from random import random

import pytest

from easyasyncio import Producer, LoopManager


class ProducerTest(Producer):
    """print numbers asynchronously"""

    def __init__(self, data: int, **kwargs):
        super().__init__(data, **kwargs)

    async def fill_queue(self):
        """override this abstract method to fill the queue"""
        for i in range(0, self.input_data):
            await self.queue.put(i)

    async def work(self, number):
        """
        This logic here will be applied to every item in the queue
        """
        sleep_time = random.randint(1, 3)
        await asyncio.sleep(sleep_time)
        self.logger(number)
        self.increment_stat()

    @property
    def name(self):
        """
        Name the object or service being provided.
        This will effect how the StatsDisplay displays information about this Producer.
        """
        return 'print_number'


@pytest.mark.asyncio
async def test_queue():
    manager = LoopManager(False)
    producer = ProducerTest(10)
    manager.add_tasks(producer)
    await producer.fill_queue()
    assert producer.queue.qsize() == 10
