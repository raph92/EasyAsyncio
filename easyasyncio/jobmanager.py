import asyncio
import collections
import logging
import signal
import time
from asyncio import Future, AbstractEventLoop, QueueFull
from threading import Thread
from typing import Set

from aiohttp import ClientSession

from . import logger
from .context import Context
from .job import Job, WorkerLoggingHandler
from .settings import HEADERS
from .tui import on_screen_ready


class JobManager(Thread):
    """
    The vision is that this class will handle the top level task gathering,
    run_until_complete, etc
    """
    session: ClientSession
    running = False
    shutting_down = False
    cancelling_all_tasks = False
    post_saving = False
    finished = False
    showing_graphics = False
    jobs: Set[Future] = set()
    scheduled_tasks: Set[Future] = set()
    loop: AbstractEventLoop = None
    status = 'Starting...'
    logs = collections.deque(maxlen=50)
    succeeded = False

    def __init__(self, auto_save=True, use_session=False):
        super().__init__()
        self.auto_save = auto_save
        # self.loop.set_debug(True)
        self.loop = asyncio.get_event_loop()
        self.context = Context(self)
        self.use_session = use_session
        signal.signal(signal.SIGINT, self.cancel_all_tasks)
        signal.signal(signal.SIGTERM, self.cancel_all_tasks)
        self.logger = logger.getChild('JobManager')
        # self.logger.addHandler(LoopManagerLoggingHandler(self))

    def start_graphics(self):
        self.showing_graphics = True

        file_handler = logging.getLogger('').handlers[0]
        self.logger.propagate = False
        self.logger.addHandler(file_handler)
        self.context.stats_thread.logger.propagate = False

        logging.getLogger('').addHandler(LoopManagerLoggingHandler(self))

        for w in self.context.jobs:
            w.log.propagate = False
            w.log.addHandler(WorkerLoggingHandler(self))
            w.log.addHandler(file_handler)
        try:
            on_screen_ready(self)
        except Exception as e:
            self.logger.exception(e)

    def run(self):
        self.running = True
        if not any(self.jobs):
            raise Exception('No jobs to start.')
        try:
            if self.auto_save:
                self.scheduled_tasks.add(self.loop.create_task(
                        self.context.save_thread.run()))
            self.scheduled_tasks.add(self.loop.create_task(
                    self.context.stats_thread.run()))
            self.status = 'Running'
            self.logger.info('Starting %s jobs', len(self.jobs))
            self.context.stats.start_time = time.time()
            if self.use_session:
                self.context.session = ClientSession(loop=self.loop,
                                                     headers=HEADERS)
            self.loop.run_until_complete(
                    asyncio.gather(*self.jobs, loop=self.loop))
            if not self.cancelling_all_tasks:
                self.succeeded = True
            self.finished = True
        except asyncio.CancelledError:
            self.logger.debug('All tasks have been canceled')
        except Exception as e:
            self.logger.exception(e)
        finally:
            self.context.stats._end_time = time.time()
            self.stop()

    def add_jobs(self, *jobs: 'Job'):
        for job in jobs:
            if not job:
                continue
            assert isinstance(job, Job)
            job.initialize(self.context)
            t = self.loop.create_task(job.run())
            self.jobs.add(t)

    def stop(self) -> None:
        if self.shutting_down:
            return
        self.shutting_down = True
        self.logger.debug('Ending program...')
        if self.status != 'Finished':
            self.status = 'Stopping...'
        try:
            if (self.use_session and self.context.session and
                    not self.context.session.closed):
                self.loop.create_task(self.context.session.close())
            self.cancel_all_tasks(None, None)
            for task in self.scheduled_tasks:
                task.cancel()
        except RuntimeError:
            pass
        finally:
            self.post_shutdown()
            for worker in [w for w in self.context.jobs if w.running]:
                stopped = 'finished' if self.finished else 'manually stopped'
                worker.log.info(stopped)
                worker.status(stopped)
            if self.succeeded:
                self.status = 'Finished!'
                self.logger.info('Success! All tasks have completed!')
            self.logger.info('Exiting.')

    def cancel_all_tasks(self, _, _2) -> None:
        if self.cancelling_all_tasks:
            return
        self.cancelling_all_tasks = True
        for worker in self.context.jobs:
            self._cancel_workers(worker)
        try:
            for task in asyncio.all_tasks(loop=self.loop):
                task.cancel()
        except AttributeError:
            # python 3.6 support
            for worker in self.context.jobs:
                for task in worker.tasks:
                    task.cancel()
            for task in self.jobs:
                task.cancel()

    @staticmethod
    def _cancel_workers(worker):
        for task in worker.tasks:
            try:
                task.cancel()
            except RuntimeError:
                pass
        try:
            worker.queue.put_nowait(False)
        except QueueFull:
            for _ in range(worker.queue.qsize()):
                worker.queue.get_nowait()
            worker.queue.put_nowait(False)

    def post_shutdown(self) -> None:
        self.logger.debug('post_shutdown saving started')
        if self.post_saving:
            return
        self.post_saving = True
        if self.context.save_thread:
            try:
                self.save()
            except Exception as e:
                self.logger.exception(e)
        try:
            self.context.stats_thread.display()
        except Exception as e:
            self.logger.exception(e)
        finally:
            if self.status == 'Stopping...':
                self.status = 'Shutdown'

            self.logger.debug('post_shutdown saving finished')

    def save(self) -> None:
        self.context.save_thread.save()

    @property
    def closing(self):
        return (self.finished
                or self.cancelling_all_tasks
                or self.shutting_down
                or not self.running)


class LoopManagerLoggingHandler(logging.Handler):
    def __init__(self, manager: JobManager,
                 level=logging.INFO) -> None:
        super().__init__(level)
        self.manager = manager

    def emit(self, record: logging.LogRecord) -> None:
        self.manager.logs.append(record.getMessage())
