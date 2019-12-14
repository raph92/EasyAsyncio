from abc import ABC

from .job import Job
from .producer import Producer


class Consumer(Job, ABC):
    proceeded_by: Producer  # what producer will be started by this Consumer

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
