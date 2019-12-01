import asyncio
import signal
import time
from asyncio import Task
from typing import Set

from aiohttp import ClientSession

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
    session: ClientSession

    def __init__(self):
        self.loop = asyncio.get_event_loop()
        self.context = Context(self)
        signal.signal(signal.SIGINT, self.cancel_all_tasks)
        signal.signal(signal.SIGTERM, self.cancel_all_tasks)

    def start(self, use_session=False):
        try:
            self.context.stats.start_time = time.time()
            if use_session:
                self.loop.run_until_complete(self.use_with_session())
            else:
                self.loop.run_until_complete(asyncio.gather(*self.tasks))
            logger.info('All tasks have completed!')
        except asyncio.CancelledError:
            print('All tasks have been canceled')
        except Exception as e:
            logger.exception(e)
        finally:
            self.context.stats._end_time = time.time()
            self.stop()

    # async def _run(self, start_function, use_session):
    #     if use_session:
    #         if start_function:
    #             self.loop.run_until_complete(start_function())
    #         else:
    #             self.loop.run_until_complete(asyncio.gather(*self.tasks))

    async def use_with_session(self):
        async with ClientSession() as session:
            self.context.session = session
            await asyncio.gather(*self.tasks)

    def add_tasks(self, *prosumers: 'Prosumer'):
        for prosumer in prosumers:
            assert isinstance(prosumer, Prosumer)
            prosumer.initialize(self.context)
            t = self.loop.create_task(prosumer.run())
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
