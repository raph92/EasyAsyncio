import asyncio
import time
from collections import Counter
from typing import TYPE_CHECKING

from . import logger

if TYPE_CHECKING:
    from .context import Context


class Stats(Counter):
    """keep track of various stats"""
    start_time = time.time()
    _end_time = None
    data_found = 0
    initial_data_count = 0

    def __init__(self, context) -> None:
        from .context import Context
        self.context: Context = context
        super().__init__()

    @property
    def end_time(self):
        return self._end_time or time.time()

    def get_count_strings(self):
        string = '\n'
        for k, v in self.items():
            string += f'\t\t\t    {k} success count: {v}\n'
            string += f'\t\t\t    {k}\'s processed per second: {v / self.elapsed_time}\n'
        for p in self.context.workers:
            from .consumer import Consumer
            if isinstance(p, Consumer):
                string += f'\t\t\t    {p.name} queue: {p.working + p.queue.qsize()} items left\n'
            else:
                string += f'\t\t\t    {p.name} queue: {p.queue.qsize()} items left\n'
            string += f'\t\t\t    {p.name} workers: {p.max_concurrent}\n'
        return string.rstrip()

    def get_stats_string(self):
        return '\n\t\t\t    elapsed time: {time:.6f} secs'.format(
            time=self.elapsed_time
        ) + self.get_count_strings()

    @property
    def elapsed_time(self):
        return self.end_time - self.start_time


class StatsDisplay:
    name = 'StatsDisplay'
    interval = 15

    def __init__(self, context: 'Context') -> None:
        super().__init__()
        self.context = context
        self.context.stats_thread = self

    async def run(self) -> None:
        logger.debug('%s starting...', self.name)
        while self.context.running:
            if not self.context.loop_manager.running:
                break
            logger.debug(self.context.stats.get_stats_string())
            logger.debug(self.context.data.get_data_string())
            await asyncio.sleep(self.interval)
