import time
from abc import abstractmethod
from threading import Thread

from easyasyncio import logger
from .context import Context


class AutoSave(Thread):
    def __init__(self, context: Context) -> None:
        super().__init__()
        self.context = context

    def run(self) -> None:
        logger.debug('save thread starting...')
        while self.context.running:
            time.sleep(self.context.settings.auto_save_interval)
            if not self.context.running:
                break
            self.save_func()

    @abstractmethod
    def save_func(self):
        pass
