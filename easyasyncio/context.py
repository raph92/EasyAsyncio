from typing import TYPE_CHECKING, Set

from aiohttp import ClientSession

from .autosave import AutoSave
from .datamanager import DataManager
from .queuemanager import QueueManager
from .stats import Stats, StatsDisplay

if TYPE_CHECKING:
    from .jobmanager import JobManager
    from .job import Job


class Context:
    """The purpose of this class is to access all important
    objects from one place"""
    queues: QueueManager
    jobs: 'Set[Job]' = set()
    save_thread: 'AutoSave' = None
    stats_thread: 'StatsDisplay' = None
    session: ClientSession = None

    data = DataManager()

    def __init__(self, job_manager: 'JobManager') -> None:
        self.stats = Stats(self)
        self.manager = job_manager
        self.queues = QueueManager(self)
        self.save_thread = AutoSave(self)
        self.stats_thread = StatsDisplay(self)

    @property
    def running(self):
        return not self.loop_manager.closing

    @property
    def loop(self):
        return self.loop_manager.loop

    @property
    def loop_manager(self):
        return self.manager
