import os
import random
import sys

sys.path.insert(1, os.path.join(sys.path[0], '..'))
from easyasyncio.job import OutputJob
from easyasyncio import JobManager


class AutoSaveExample(OutputJob):
    """
    Gets all of the summations from 1 to `input_data` and saves the result
    to output.txt.
    """

    async def fill_queue(self):
        self.log.info('starting to queue')
        for i in self.get_uncached(range(1, self.input_data + 1)):
            self.log.info('queuing %s', i)
            await self.queue.put(i)
        self.log.info('calling queue_finished()')
        await self.queue_finished()

    async def do_work(self, number):
        """this logic gets called after an object
        is retrieved from the queue"""
        sum_of_nums = sum(list(range(1, number)))
        self.log.info('Summation of %s is %s', number, sum_of_nums)
        self.context.stats['test_stat'] += 1
        try:
            if random.randint(0, 700) == 5:
                raise Exception('Test exception')
        except:
            self.diag_save(sum_of_nums, number)
        return sum_of_nums


manager = JobManager()
manager.context.data.register_cache('output', set(), 'output/output.txt')
job = AutoSaveExample('output', input_data=5000, max_concurrent=15)

manager.add_jobs(job)
manager.start()
#
# manager.start_graphics()
