from collections import UserDict


class DataManager(UserDict):
    def __init__(self, *args, **kwargs: dict) -> None:
        super().__init__(*args, **kwargs)

    def register(self, name, init):
        # todo
        pass

    def get_data_string(self):
        string = '\n'
        for k, v in self.items():
            string += f'\t\t\t    {k}: {v}\n'
        return string.rstrip()
