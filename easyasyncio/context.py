from asyncio import AbstractEventLoop
from typing import TYPE_CHECKING, Set

from aiohttp import ClientSession

from .autosave import AutoSave
from .datamanager import DataManager
from .queuemanager import QueueManager
from .settings import Settings
from .stats import Stats, StatsDisplay

if TYPE_CHECKING:
    from .loopmanager import LoopManager
    from .abstractasyncworker import AbstractAsyncWorker


class Context:
    """The purpose of this class is to access all important objects from one place"""
    settings = Settings()
    queues: QueueManager
    loop: AbstractEventLoop
    workers: 'Set[AbstractAsyncWorker]' = set()
    save_thread: 'AutoSave' = None
    stats_thread: 'StatsDisplay' = None
    loop_manager: 'LoopManager'
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
