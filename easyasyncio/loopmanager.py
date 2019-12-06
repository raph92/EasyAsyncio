import asyncio
import signal
import time
from asyncio import Future
from typing import Set

from aiohttp import ClientSession

from . import logger
from .abstractasyncworker import AbstractAsyncWorker
from .context import Context


class LoopManager:
    """
    The vision is that this class will handle the top level task gathering, run_until_complete, etc
    """
    running = True
    worker_tasks: Set[Future] = set()
    scheduled_tasks: Set[Future] = set()
    session: ClientSession

    def __init__(self, auto_save=True):
        self.auto_save = auto_save
        self.loop = asyncio.get_event_loop()
        # self.loop.set_debug(True)
        self.context = Context(self)
        signal.signal(signal.SIGINT, self.cancel_all_tasks)
        signal.signal(signal.SIGTERM, self.cancel_all_tasks)

    def start(self, use_session=False):
        succeeded = False
        try:
            if self.auto_save:
                self.scheduled_tasks.add(asyncio.ensure_future(self.context.save_thread.run()))
            self.scheduled_tasks.add(asyncio.ensure_future(self.context.stats_thread.run()))
            self.context.stats.start_time = time.time()
            if use_session:
                self.loop.run_until_complete(self.use_with_session())
            else:
                self.loop.run_until_complete(asyncio.gather(*self.worker_tasks))
            succeeded = True
        except asyncio.CancelledError:
            logger.info('All tasks have been canceled')
        except Exception as e:
            logger.exception(e)
        finally:
            self.context.stats._end_time = time.time()
            self.stop()
            if succeeded:
                logger.info('Success! All tasks have completed!')

    async def use_with_session(self):
        async with ClientSession() as session:
            self.context.session = session
            await asyncio.gather(*self.worker_tasks)

    def add_tasks(self, *asyncio_objects: 'AbstractAsyncWorker'):
        for obj in asyncio_objects:
            assert isinstance(obj, AbstractAsyncWorker)
            obj.initialize(self.context)
            t = asyncio.ensure_future(obj.run())
            self.worker_tasks.add(t)

    def stop(self):
        logger.info('Ending program...')
        self.running = False
        logger.info(self.context.stats.get_stats_string())
        logger.info(self.context.data.get_data_string())
        try:
            for task in self.scheduled_tasks:
                task.cancel()
        except RuntimeError:
            pass
        finally:
            self.post_shutdown()

    def cancel_all_tasks(self, _, _2):
        logger.info('Cancelling all tasks, this may take a moment...')
        # logger.warning('The program may or may not close immediately, this is a known bug and I am working on a fix')
        for worker in self.context.workers:
            worker.queue.put_nowait(False)
            for task in worker.tasks:
                task.cancel()
                worker.queue.put(False)
        try:
            for task in asyncio.all_tasks():
                task.cancel()
        except AttributeError:
            # python 3.6 support
            for worker in self.context.workers:
                for task in worker.tasks:
                    task.cancel()
            for task in self.worker_tasks:
                task.cancel()

    def post_shutdown(self):
        if self.context.save_thread:
            t = asyncio.ensure_future(self.context.save_thread.save_func())
            logger.debug('post_shutdown saving started')
            self.loop.run_until_complete(t)
            logger.debug('post_shutdown saving finished')
