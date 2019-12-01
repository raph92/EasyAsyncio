import logging
from asyncio import AbstractEventLoop
from typing import TYPE_CHECKING, Set

import logzero

from .queuemanager import QueueManager
from .settings import Settings
from .stats import Stats

if TYPE_CHECKING:
    from easyasyncio import LoopManager
    from .prosumer import Prosumer


class Context:
    """The purpose of this class is to access all important objects from one place"""
    settings = Settings()
    logger: logging.Logger = logzero.logger
    running = True
    queues = QueueManager()
    loop: AbstractEventLoop
    prosumers: 'Set[Prosumer]' = set()
    loop_manager: 'LoopManager'

    def __init__(self, loop_manager) -> None:
        self.stats = Stats(self)
        self.loop_manager = loop_manager
        self.loop = self.loop_manager.loop
