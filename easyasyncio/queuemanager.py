from asyncio import Queue
from typing import Dict, TYPE_CHECKING

if TYPE_CHECKING:
    from .context import Context


class QueueManager(Dict[str, Queue]):
    """easy access queues for all producers and consumers"""

    def __init__(self, context: 'Context', **kwargs: dict):
        super().__init__(**kwargs)
        self.context = context
        self.logger = context.logger

    def __getitem__(self, key: str) -> 'Queue':
        if key not in self:
            self[key] = Queue()
        return super().__getitem__(key)

    def new(self, name):
        self.logger.info('Creating new queue: %s...', name)
        self[name] = Queue()
        return self[name]
