from logzero import setup_logger

logger = setup_logger(name='EasyAsyncio')
from .context import Context
from .loopmanager import LoopManager
from .abstractasyncworker import AbstractAsyncWorker
from .producer import Producer
from .consumer import Consumer
from .queuemanager import QueueManager
from .datamanager import DataManager
from .constants import Constants
from .stats import Stats
from .autosave import AutoSave

__all__ = [
    'Context',
    'LoopManager',
    'AbstractAsyncWorker',
    'Producer',
    'Consumer',
    'QueueManager',
    'DataManager',
    'Constants',
    'Stats',
    'AutoSave',
    'logger',
]
