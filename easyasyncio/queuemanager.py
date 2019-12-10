from asyncio import Queue
from collections import UserDict
from typing import TYPE_CHECKING, Any

from . import logger

if TYPE_CHECKING:
    from .context import Context


class QueueManager(UserDict):
    """easy access queues for all producers and consumers"""

    def __init__(self, context: 'Context'):
        super().__init__()
        self.context = context

    def __getitem__(self, key: str) -> 'Queue[Any]':
        if key not in self:
            self[key] = Queue()
        return super().__getitem__(key)

    def new(self, name: str) -> 'Queue[Any]':
        logger.info('Creating new queue: %s...', name)
        self[name] = Queue()
        return self[name]
