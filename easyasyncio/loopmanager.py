import asyncio
import signal
import time
from asyncio import Task
from typing import Set, TYPE_CHECKING

from aiohttp import ClientSession

from easyasyncio import logger
from .baseasyncioobject import BaseAsyncioObject
from .context import Context

if TYPE_CHECKING:
    pass


class LoopManager:
    """
    The vision is that this class will handle the top level task gathering, run_until_complete, etc
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
            logger.info('All tasks have been canceled')
        except Exception as e:
            logger.exception(e)
        finally:
            self.context.stats._end_time = time.time()
            self.stop()
            self.post_shutdown()

    async def use_with_session(self):
        async with ClientSession() as session:
            self.context.session = session
            await asyncio.gather(*self.tasks)

    def add_tasks(self, *asyncio_objects: 'BaseAsyncioObject'):
        for prosumer in asyncio_objects:
            assert isinstance(prosumer, BaseAsyncioObject)
            prosumer.initialize(self.context)
            t = self.loop.create_task(prosumer.run())
            self.tasks.add(t)

    def stop(self):
        logger.info('Closing...')
        self.running = False
        logger.info(self.context.stats.get_stats_string())
        self.loop.close()

    def cancel_all_tasks(self, _, _2):
        logger.info('Cancelling all tasks, this may take a moment...')
        logger.warning('The program may or may not close immediately, this is a known bug and I am working on a fix')
        for worker in self.context.workers:
            for _ in range(worker.max_concurrent):
                worker.queue.put_nowait(False)
        for task in asyncio.all_tasks():
            task.cancel()

    def post_shutdown(self):
        if self.context.save_thread:
            self.context.save_thread.save_func()
