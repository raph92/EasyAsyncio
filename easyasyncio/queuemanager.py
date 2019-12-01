from asyncio import Queue
from collections import UserDict
from typing import Dict

from easyasyncio import logger


class QueueManager(UserDict, Dict[str, Queue]):

    def __init__(self, **kwargs: dict):
        super().__init__(**kwargs)

    def new(self, name):
        logger.info('Creating new queue: %s...', name)
        self[name] = Queue()
        return self[name]
