from logzero import setup_logger

logger = setup_logger(name='EasyAsyncio')
from .context import Context
from .loopmanager import LoopManager
from .prosumer import Prosumer
from .queuemanager import QueueManager
from .stats import Stats

__all__ = [
    'Context',
    'LoopManager',
    'Prosumer',
    'QueueManager',
    'Stats',
    'logger'
]
