from abc import ABC

from .abstractasyncworker import AbstractAsyncWorker
from .producer import Producer


class Consumer(AbstractAsyncWorker, ABC):
    proceeded_by: Producer  # what producer will be started by this Consumer

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
