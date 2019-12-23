import asyncio
import time
import typing
from typing import TYPE_CHECKING

from . import logger

if TYPE_CHECKING:
    from .context import Context

spacer4 = '\t\t\t\t    '
spacer3 = '\t\t\t    '


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
        for worker in self.context.jobs:
            string = self.get_worker_stats(worker, string)
        string += f'{spacer3}<{"STATS".center(29, "-")}>'
        string += f'\n{spacer4}elapsed time: {self.elapsed_time:.6f} secs\n'
        if self.items():
            for k, v in self.items():
                if k in [s for p in self.context.jobs for s in p.stats]:
                    continue
                string += f'{spacer4}{k}: {v}\n'
                if k not in self.do_not_calculate_per_second:
                    string += (f'{spacer4}{k} per second: '
                               f'{v / self.elapsed_time: .2f}\n')
        string += f'{spacer3}<{"END STATS".center(29, "-")}>\n\n'
        return string.rstrip()

    def get_worker_stats(self, worker, string):
        worker_stats_str = f'<{f"JOB {worker.name}".center(29, "-")}>\n'
        string += f'{spacer3}' + worker_stats_str
        string += (f'{spacer4}queue: '
                   f'{worker.queue.qsize()} items left\n')
        for key, value in worker.info.items():
            string += f'{spacer4}{key}: {value}\n'
        for key, value in worker.stats.items():
            string += f'{spacer4}{key}: {value}\n'
            if key not in self.do_not_calculate_per_second:
                string += (f'{spacer4}{key} per second: '
                           f'{value / self.elapsed_time: .2f}\n')
        string += f'{spacer3}<{"END JOB".center(29, "-")}>\n'
        return string

    def get_stats_string(self) -> str:
        string = f'\n\t\t    <{"SESSION".center(55, "-")}>'
        string += self.get_count_strings()
        string += f'\n\t\t    <{"END SESSION".center(55, "-")}>\n'

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
