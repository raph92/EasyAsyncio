import time
from collections import Counter
from threading import Thread

from easyasyncio import logger, Context


class Stats(Counter):
    """keep track of various stats"""
    start_time: float
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
        for p in self.context.prosumers:
            string += f'\t\t\t    {p.name} queue: {p.queue.qsize()} items left\n'
            string += f'\t\t\t    {p.name} workers: {len(p.tasks)}\n'
        return string.rstrip()

    def get_stats_string(self):
        return '\n\t\t\t    elapsed time: {time:.6f} secs'.format(
            time=self.elapsed_time
        ) + self.get_count_strings()

    @property
    def elapsed_time(self):
        return self.end_time - self.start_time


class StatsThread(Thread):
    name = 'StatsThread'
    interval = 15

    def __init__(self, context: Context) -> None:
        super().__init__()
        self.context = context

    def run(self) -> None:
        while self.context.running:
            time.sleep(self.interval)
            if not self.context.loop_manager.running:
                break
            logger.debug(self.context.stats.get_stats_string())
