from asyncio import Queue
from collections import UserDict
from typing import TYPE_CHECKING

from . import logger

if TYPE_CHECKING:
    from .context import Context


class QueueManager(UserDict):
    """easy access queues for all producers and consumers"""

    def __init__(self, context: 'Context', **kwargs: dict):
        super().__init__(**kwargs)
        self.context = context

    def __getitem__(self, key: str) -> 'Queue':
        if key not in self:
            self[key] = Queue()
        return super().__getitem__(key)

    def new(self, name):
        logger.info('Creating new queue: %s...', name)
        self[name] = Queue()
        return self[name]
