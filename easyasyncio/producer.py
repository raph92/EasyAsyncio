import abc
from typing import Any

from .job import Job


class Producer(Job, metaclass=abc.ABCMeta):
    start = False  # whether this Producer will start instantly or not

    def __init__(self, input_data: Any = None,
                 **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.input_data = input_data
