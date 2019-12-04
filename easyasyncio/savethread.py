import time
from abc import abstractmethod
from threading import Thread

from easyasyncio import logger
from .context import Context


class SaveThread(Thread):
    name = 'SaveThread'
    interval = 10

    def __init__(self, context: Context) -> None:
        super().__init__()
        self.context = context
        self.context.save_thread = self

    def run(self) -> None:
        logger.debug('save thread starting...')
        while self.context.running:
            try:
                time.sleep(self.interval)
                if not self.context.loop_manager.running:
                    break
                self.save_func()
            except RuntimeError:
                pass
            except Exception as e:
                logger.exception(e)

    @abstractmethod
    def save_func(self):
        pass
