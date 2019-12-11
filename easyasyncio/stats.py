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

    def __init__(self, context: 'Context') -> None:
        super().__init__()
        from .context import Context
        self.context: Context = context
        self.logger = logger.getChild(type(self).__name__)

    @property
    def end_time(self) -> float:
        return self._end_time or time.time()

    def get_count_strings(self) -> str:
        string = '\n'
        string += '\t\t\t    <-----STATS----->'
        string += '\n\t\t\t\t    elapsed time: {time:.6f} secs\n'.format(
                time=self.elapsed_time)
        if self.items():
            for k, v in self.items():
                if k in [s for p in self.context.workers for s in p.stats]:
                    continue
                string += f'\t\t\t\t    {k} count: {v}\n'
                string += (f'\t\t\t\t    {k}\'s count per second: '
                           f'{v / self.elapsed_time}\n')
        string += '\t\t\t    </-----STATS----->\n\n'
        for p in self.context.workers:
            from .consumer import Consumer
            top_worker_section_string = f'<-----WORKER {p.name}----->\n'
            string += '\t\t\t    ' + top_worker_section_string
            if isinstance(p, Consumer):
                string += f'\t\t\t\t    {p.name} queue: {p.working + p.queue.qsize()} items left\n'
            else:
                string += f'\t\t\t\t    {p.name} queue: {p.queue.qsize()} items left\n'
            string += f'\t\t\t\t    {p.name} workers: {p.max_concurrent}\n'
            string += f'\t\t\t\t    {p.name} status: {p._status}\n'
            for s in p.stats:
                string += f'\t\t\t\t    {s} count: {self[s]}\n'
                string += f'\t\t\t\t    {s}\'s count per second: {self[s] / self.elapsed_time}\n'

            i = 1 if len(top_worker_section_string) % 2 != 0 else 4
            string += (f'\t\t\t    </'
                       f'{"-" * int((len(top_worker_section_string) / 3 - i))}'
                       f'WORKER'
                       f'{"-" * int((len(top_worker_section_string) / 3))}----->\n\n')
        return string.rstrip()

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
            await self.display()
            if not self.context.running:
                break

    async def display(self):
        self.logger.info('%s\n',
                         self.context.stats.get_stats_string()
                         + self.context.data.get_data_string())
