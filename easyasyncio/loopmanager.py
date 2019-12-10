import asyncio
import signal
import time
from asyncio import Future, AbstractEventLoop
from threading import Thread
from typing import Set

from aiohttp import ClientSession

from . import logger
from .abstractasyncworker import AbstractAsyncWorker
from .context import Context
from .tui import on_screen_ready


class LoopManager(Thread):
    """
    The vision is that this class will handle the top level task gathering, run_until_complete, etc
    """
    session: ClientSession
    running = True
    shutting_down = False
    cancelling_all_tasks = False
    post_saving = False
    finished = False
    showing_graphics = False
    worker_tasks: Set[Future] = set()
    scheduled_tasks: Set[Future] = set()
    loop: AbstractEventLoop = None
    status = 'Starting...'

    def __init__(self, auto_save=True, use_session=False):
        super().__init__()
        self.auto_save = auto_save
        # self.loop.set_debug(True)
        self.loop = asyncio.get_event_loop()
        self.context = Context(self)
        self.use_session = use_session
        signal.signal(signal.SIGINT, self.cancel_all_tasks)
        signal.signal(signal.SIGTERM, self.cancel_all_tasks)

    def start_graphics(self):
        try:
            self.showing_graphics = True
            on_screen_ready(self)
        except:
            pass

    def run(self):
        succeeded = False
        try:
            if self.auto_save:
                self.scheduled_tasks.add(self.loop.create_task(self.context.save_thread.run()))
            self.scheduled_tasks.add(self.loop.create_task(self.context.stats_thread.run()))
            self.context.stats.start_time = time.time()
            self.status = 'Running'
            if self.use_session:
                self.loop.run_until_complete(self.use_with_session())
            else:
                self.loop.run_until_complete(asyncio.gather(*self.worker_tasks, loop=self.loop))
            succeeded = True
            self.finished = True
        except asyncio.CancelledError:
            if not self.showing_graphics:
                logger.info('All tasks have been canceled')
        except Exception as e:
            if not self.showing_graphics:
                logger.exception(e)
        finally:
            self.context.stats._end_time = time.time()
            self.stop()
            if succeeded:
                self.status = 'Finished!'
                if not self.showing_graphics:
                    print('Success! All tasks have completed!')

    async def use_with_session(self):
        async with ClientSession(loop=self.loop) as session:
            self.context.session = session
            await asyncio.gather(*self.worker_tasks, loop=self.loop)

    def add_tasks(self, *asyncio_objects: 'AbstractAsyncWorker'):
        for obj in asyncio_objects:
            if not obj:
                continue
            assert isinstance(obj, AbstractAsyncWorker)
            obj.initialize(self.context)
            t = self.loop.create_task(obj.run())
            self.worker_tasks.add(t)

    def stop(self) -> None:
        if self.shutting_down:
            return
        if not self.showing_graphics:
            logger.info('Ending program...')
        if self.status != 'Finished':
            self.status = 'Stopping...'
        self.shutting_down = True
        try:
            self.cancel_all_tasks(None, None)
            for task in self.scheduled_tasks:
                task.cancel()
        except RuntimeError:
            pass
        finally:
            self.post_shutdown()
            for worker in self.context.workers:
                stopped = 'finished' if self.finished else 'manually stopped'
                worker.logger(stopped)
                worker.status(stopped)

    def cancel_all_tasks(self, _, _2) -> None:
        if self.cancelling_all_tasks:
            return
        self.cancelling_all_tasks = True
        for worker in self.context.workers:
            worker.queue.put_nowait(False)
            for task in worker.tasks:
                task.cancel()
                worker.queue.put_nowait(False)
        try:
            for task in asyncio.all_tasks(loop=self.loop):
                task.cancel()
        except AttributeError:
            # python 3.6 support
            for worker in self.context.workers:
                for task in worker.tasks:
                    task.cancel()
            for task in self.worker_tasks:
                task.cancel()

    def post_shutdown(self) -> None:
        if not self.showing_graphics:
            logger.debug('post_shutdown saving started')
        try:
            if self.post_saving:
                return
            self.post_saving = True
            if self.context.save_thread:
                t = self.loop.create_task(self.context.save_thread.save_func())
                self.loop.run_until_complete(t)
        except:
            pass
        finally:
            if self.status == 'Stopping...':
                self.status = 'Shutdown'
            if not self.showing_graphics:
                logger.debug('post_shutdown saving finished')

    def save(self) -> None:
        self.loop.create_task(self.context.save_thread.save_func())
