import asyncio
from asyncio import CancelledError
from time import time
from typing import TYPE_CHECKING

from . import logger

if TYPE_CHECKING:
    from .context import Context


class AutoSave:
    name = 'AutoSave'
    interval = 10
    _last_saved = time()

    def __init__(self, context: 'Context') -> None:
        super().__init__()
        self.context = context
        if self.context.save_thread:
            del self.context.save_thread
        self.context.save_thread = self
        self.logger = logger.getChild(type(self).__name__)

    async def run(self) -> None:
        self.logger.debug('%s starting...', self.name)
        while self.context.running:
            try:
                await asyncio.sleep(self.interval, loop=self.context.loop)
                if not self.context.running:
                    break
                await self.save_func()
            except (RuntimeError, CancelledError):
                pass
            except Exception as e:
                self.logger.exception(e)

    async def save_func(self):
        self.logger.debug('autosaving...')
        await self.context.data.save()
        self._last_saved = time()

    @property
    def last_saved(self):
        return time() - self._last_saved
