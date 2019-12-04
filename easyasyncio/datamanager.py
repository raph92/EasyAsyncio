from collections import UserDict
from typing import Iterable, Sized


class DataManager(UserDict):
    def __init__(self, *args, **kwargs: dict) -> None:
        super().__init__(*args, **kwargs)

    def register(self, name, init):
        # todo
        pass

    def get_data_string(self):
        string = '\n'
        for k, v in self.items():
            if isinstance(v, Iterable) and isinstance(v, Sized):
                string += f'\t\t\t    {k} count: {len(v)}\n'
            else:
                string += f'\t\t\t    {k}: {v}\n'
        return string.rstrip()
