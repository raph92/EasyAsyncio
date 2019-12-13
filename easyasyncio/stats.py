import asyncio
import time
import typing
from typing import TYPE_CHECKING

from . import logger

if TYPE_CHECKING:
    from .context import Context


class Stats(typing.Counter[int]):
    """keep track of various stats"""
    start_time = time.time()
    _end_time = None
    data_found = 0
    initial_data_count = 0
    do_not_calculate_per_second = set()

    def __init__(self, context: 'Context') -> None:
        super().__init__()
        from .context import Context
        self.context: Context = context
        self.logger = logger.getChild(type(self).__name__)

    @property
    def end_time(self) -> float:
        return self._end_time or time.time()

    def set(self, name: str, value: int, calculate_per_second=False):
        self[name] = value
        if not calculate_per_second:
            self.do_not_calculate_per_second.add(name)

    def get_count_strings(self) -> str:
        string = '\n'
        for worker in self.context.workers:
            string = self.get_worker_stats(worker, string)
        string += '\t\t\t    <-----STATS----->'
        string += '\n\t\t\t\t    elapsed time: {time:.6f} secs\n'.format(
                time=self.elapsed_time)
        if self.items():
            for k, v in self.items():
                if k in [s for p in self.context.workers for s in p.stats]:
                    continue
                string += f'\t\t\t\t    {k}: {v}\n'
                if k not in self.do_not_calculate_per_second:
                    string += (f'\t\t\t\t    {k}\'s per second: '
                               f'{v / self.elapsed_time: .2f}\n')
        string += '\t\t\t    </-----STATS----->\n\n'
        return string.rstrip()

    def get_worker_stats(self, worker, string):
        from .consumer import Consumer
        top_worker_section_string = f'<-----WORKER {worker.name}----->\n'
        string += '\t\t\t    ' + top_worker_section_string
        if isinstance(worker, Consumer):
            string += (f'\t\t\t\t    {worker.name} queue: '
                       f'{worker.working + worker.queue.qsize()} items left\n')
        else:
            string += (f'\t\t\t\t    {worker.name} queue: '
                       f'{worker.queue.qsize()} items left\n')
        string += f'\t\t\t\t    {worker.name} workers: {worker.max_concurrent}\n'
        string += f'\t\t\t\t    {worker.name} status: {worker._status}\n'
        for s in worker.stats:
            string += f'\t\t\t\t    {s}: {self[s]}\n'
            if s not in self.do_not_calculate_per_second:
                string += (f'\t\t\t\t    {s}\'s per second: '
                           f'{self[s] / self.elapsed_time: .2f}\n')
        i = 1 if len(top_worker_section_string) % 2 != 0 else 4
        string += (f'\t\t\t    </'
                   f'{"-" * int((len(top_worker_section_string) / 3 - i))}'
                   f'WORKER'
                   f'{"-" * int((len(top_worker_section_string) / 3))}'
                   f'----->\n\n')
        return string

    def get_stats_string(self) -> str:
        string = ('\n\t\t    <---------------------'
                  'SESSION STATS--------------------->')
        string += self.get_count_strings()
        string += ('\n\t\t    </---------------------'
                   'SESSION STATS--------------------->\n')

        return string

    @property
    def elapsed_time(self) -> float:
        return self.end_time - self.start_time


class StatsDisplay:
    name = 'StatsDisplay'
    interval = 15

    def __init__(self, context: 'Context') -> None:
        super().__init__()
        self.context = context
        if self.context.stats_thread:
            del self.context.stats_thread
        self.context.stats_thread = self
        self.logger = logger.getChild(type(self).__name__)

    async def run(self) -> None:
        self.logger.debug('%s starting...', self.name)
        while self.context.running:
            await asyncio.sleep(self.interval, loop=self.context.loop)
            self.display()
            if not self.context.running:
                break

    def display(self):
        self.logger.info('%s\n',
                         self.context.stats.get_stats_string()
                         + self.context.data.get_data_string())
