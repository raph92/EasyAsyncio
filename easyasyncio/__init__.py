import datetime
import logging
import os

import logzero

if not os.path.exists('logs/'):
    os.mkdir('logs')
logzero.logfile(f'./logs/{datetime.datetime.now().strftime("%y-%m-%d-%H:%M:%S")}.log',
                maxBytes=2e6, backupCount=5)
logger: logging.Logger = logzero.logger
logzero.loglevel(logging.INFO)

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
