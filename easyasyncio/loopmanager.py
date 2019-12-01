import asyncio
import signal
import time
from asyncio import Task
from typing import Set

from easyasyncio import logger
from .context import Context
from .prosumer import Prosumer


class LoopManager:
    """
    The vision is that this class will handle the top level task gathering, run_until_complete,
    etc
    """
    running = True
    tasks: Set[Task] = set()

    def __init__(self):
        self.loop = asyncio.get_event_loop()
        self.context = Context(self)
        signal.signal(signal.SIGINT, self.cancel_all_tasks)
        signal.signal(signal.SIGTERM, self.cancel_all_tasks)

    def start(self, start_function: callable = None):
        try:
            self.context.stats.start_time = time.time()
            if start_function:
                self.loop.run_until_complete(start_function())
            else:
                self.loop.run_until_complete(self._run())
            logger.info('All tasks have completed!')
        except asyncio.CancelledError:
            print('All tasks have been canceled')
        except Exception as e:
            logger.exception(e)
        finally:
            self.context.stats._end_time = time.time()
            self.stop()

    async def _run(self):
        await asyncio.gather(*self.tasks)

    def add_tasks(self, *prosumers: 'Prosumer'):
        for obj in prosumers:
            assert isinstance(obj, Prosumer)
            t = self.loop.create_task(obj.run())
            self.tasks.add(t)

    def stop(self):
        logger.info('Closing...')
        self.running = False
        logger.info(self.context.stats.get_stats_string())
        self.loop.close()

    @staticmethod
    def cancel_all_tasks(_, _2):
        logger.info('Cancelling all tasks, this may take a moment...')
        for task in asyncio.all_tasks():
            task.cancel()
