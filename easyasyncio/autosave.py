import asyncio
from asyncio import CancelledError
from typing import TYPE_CHECKING

from . import logger

if TYPE_CHECKING:
    from .context import Context


class AutoSave:
    name = 'AutoSave'
    interval = 10

    def __init__(self, context: 'Context') -> None:
        super().__init__()
        self.context = context
        if self.context.save_thread:
            del self.context.save_thread
        self.context.save_thread = self

    async def run(self) -> None:
        logger.debug('%s starting...', self.name)
        while self.context.running:
            try:
                await asyncio.sleep(self.interval)
                if not self.context.running:
                    break
                self.save_func()
            except (RuntimeError, CancelledError):
                pass
            except Exception as e:
                logger.exception(e)

    def save_func(self):
        logger.info('saving all data...')
        self.context.data.save()
