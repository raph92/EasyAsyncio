import logging
from asyncio import AbstractEventLoop
from typing import TYPE_CHECKING, Set

from aiohttp import ClientSession

from easyasyncio import logger
from .datamanager import DataManager
from .queuemanager import QueueManager
from .settings import Settings
from .stats import Stats

if TYPE_CHECKING:
    from .loopmanager import LoopManager
    from .baseasyncioobject import BaseAsyncioObject
    from .savethread import SaveThread


class Context:
    """The purpose of this class is to access all important objects from one place"""
    settings = Settings()
    logger: logging.Logger = logger
    queues: QueueManager
    loop: AbstractEventLoop
    workers: 'Set[BaseAsyncioObject]' = set()
    save_thread: 'SaveThread' = None
    loop_manager: 'LoopManager'
    session: ClientSession
    data = DataManager()

    def __init__(self, loop_manager) -> None:
        self.stats = Stats(self)
        self.loop_manager = loop_manager
        self.loop = self.loop_manager.loop
        self.queues = QueueManager(self)

    @property
    def running(self):
        return self.loop_manager.running
