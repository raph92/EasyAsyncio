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

    async def run(self) -> None:
        if not self.context.loop_manager.showing_graphics:
            logger.debug('%s starting...', self.name)
        while self.context.running:
            try:
                await asyncio.sleep(self.interval, loop=self.context.loop)
                if not self.context.running:
                    break
                await self.save_func()
            except (RuntimeError, CancelledError):
                pass
            except Exception as e:
                logger.exception(e)

    async def save_func(self):
        if not self.context.loop_manager.showing_graphics:
            logger.debug('autosaving...')
        await self.context.data.save()
        self._last_saved = time()

    @property
    def last_saved(self):
        return time() - self._last_saved
