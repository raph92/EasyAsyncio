import asyncio
import os
import sys

sys.path.insert(1, os.path.join(sys.path[0], '..'))
from easyasyncio import JobManager, Job
from diskcache import Deque


class AutoSaveExample(Job):
    """print numbers asynchronously"""
    num_cache = Deque([], 'cache/cached_numbers')
    output = Deque([], 'cache/output')

    async def fill_queue(self):
        self.log.info('starting to queue')
        for i in set(range(10000)) - set(self.num_cache):
            # if i not in set(self.num_cache):
            self.log.info('adding %s', i)
            await self.queue.put(i)
            await asyncio.sleep(0.00001)
        self.log.info('calling queue_finished()')
        await self.queue_finished()

    async def do_work(self, number):
        """this logic gets called after an object
        is retrieved from the queue"""
        sum_of_nums = sum(list(range(number)))
        self.log.info('Summation of %s is %s', number, sum_of_nums)
        self.output.append(sum_of_nums)
        self.increment_stat()
        self.num_cache.append(number)
        self.context.stats['test_stat'] += 1

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
manager.context.data.register('output', set(Deque('cache/output')),
                              './output/summations.txt')
manager.context.data.save()
