import os
import random
import sys

sys.path.insert(1, os.path.join(sys.path[0], '..'))
from easyasyncio.job import OutputJob, Diagnostics, UnknownResponse
from easyasyncio import JobManager


class AutoSaveExample(OutputJob):
    """
    Gets all of the summations from 1 to `input_data` and saves the result
    to output.txt.
    """

    async def do_work(self, number):
        """this logic gets called after an object
        is retrieved from the queue"""
        sum_of_nums = sum(list(range(1, number)))
        # self.log.info('Summation of %s is %s', number, sum_of_nums)
        self.context.stats['test_stat'] += 1
        try:
            if random.randint(0, 700) == 5:
                raise Exception()
        except:
            raise UnknownResponse(Diagnostics(sum_of_nums, number),
                                  'testerror', extra_info='Test exception')
        if random.randint(0, 5) == 5:
            randint = random.randint(5001, 10000)
            self.log.info('adding %s to queue', randint)
            await self.queue.put(randint)
            self.increment_stat(name='post-fill')
        return sum_of_nums


manager = JobManager()
manager.context.data.register_cache('output', set(), 'output/output.txt')
job = AutoSaveExample('output', input_data=range(1, 3000), max_concurrent=15,
                      print_successes=True, product_name='summation')

manager.add_jobs(job)
manager.start()
#
# manager.start_graphics()
