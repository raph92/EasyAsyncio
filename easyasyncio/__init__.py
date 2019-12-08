import datetime
import logging
import os

import logzero

logger: logging.Logger = logzero.logger
logzero.loglevel(logging.DEBUG)
start_date = datetime.datetime.now().strftime("%y-%m-%d-%H%M%S")
_path = f'./logs/{start_date}/logs.log'
if not os.path.exists(os.path.split(_path)[0]):
    os.makedirs(os.path.split(_path)[0])
logzero.logfile(_path,
                maxBytes=2e6, backupCount=5)

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
    'start_date'
]
