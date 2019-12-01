from collections import UserDict


class DataManager(UserDict):
    def __init__(self, *args, **kwargs: dict) -> None:
        super().__init__(*args, **kwargs)
