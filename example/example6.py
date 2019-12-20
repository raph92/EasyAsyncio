import asyncio
import os
import random
import sys

sys.path.insert(1, os.path.join(sys.path[0], '..'))
from easyasyncio import JobManager, Producer
from diskcache import Deque


class AutoSaveExample(Producer):
    """print numbers asynchronously"""

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.num_cache = Deque([], 'cache/numbers')

    async def fill_queue(self):
        for i in range(10000):
            if i not in self.num_cache:
                await self.queue.put(i)
        await self.queue_finished()

    async def do_work(self, number):
        """this logic gets called after an object
        is retrieved from the queue"""
        sum(list(range(number)))
        self.increment_stat()
        await asyncio.sleep(random.randint(1, 5))
        self.num_cache.append(number)
        self.context.stats['test_stat'] += 1
        self.log.info('Processed %s', number)

    @property
    def name(self):
        """
        Name the object or service being provided.
        This will effect how the StatsDisplay displays information about
        this Prosumer.
        """
        return 'PrintNumber'


manager = JobManager()
consumer = AutoSaveExample(max_concurrent=15)

manager.add_jobs(consumer)
manager.start()
#
manager.start_graphics()
