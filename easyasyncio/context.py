from typing import TYPE_CHECKING, Set

from aiohttp import ClientSession

from .autosave import AutoSave
from .datamanager import DataManager
from .queuemanager import QueueManager
from .settings import Settings
from .stats import Stats, StatsDisplay

if TYPE_CHECKING:
    from .jobmanager import JobManager
    from .job import Job


class Context:
    """The purpose of this class is to access all important
    objects from one place"""
    settings = Settings()
    queues: QueueManager
    jobs: 'Set[Job]' = set()
    save_thread: 'AutoSave' = None
    stats_thread: 'StatsDisplay' = None
    loop_manager: 'JobManager'
    session: ClientSession

    data = DataManager()

    def __init__(self, loop_manager) -> None:
        self.stats = Stats(self)
        self.loop_manager = loop_manager
        self.queues = QueueManager(self)
        self.save_thread = AutoSave(self)
        self.stats_thread = StatsDisplay(self)

    @property
    def running(self):
        return not self.loop_manager.closing

    @property
    def loop(self):
        return self.loop_manager.loop
