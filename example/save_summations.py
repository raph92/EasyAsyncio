import os
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
            # if i not in set(self.num_cache):
            self.log.info('queuing %s', i)
            await self.queue.put(i)
        self.log.info('calling queue_finished()')
        await self.queue_finished()

    async def do_work(self, number):
        """this logic gets called after an object
        is retrieved from the queue"""
        sum_of_nums = sum(list(range(number)))
        self.log.info('Summation of %s is %s', number, sum_of_nums)
        self.context.stats['test_stat'] += 1
        return sum_of_nums

    @property
    def name(self):
        """
        Name the object or service being provided.
        This will effect how the StatsDisplay displays information about
        this Job.
        """
        return 'PrintNumber'


manager = JobManager()
manager.context.data.register_cache('output', set(), 'output/output.txt')
job = AutoSaveExample('output', input_data=10000, max_concurrent=15)

manager.add_jobs(job)
manager.start()
#
# manager.start_graphics()
