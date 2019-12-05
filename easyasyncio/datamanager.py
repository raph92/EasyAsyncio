import os
from collections import UserDict
from typing import Sized, Iterable

from easyfilemanager import FileManager


def _numericize(loaded_data):
    """
    If a number can be turned into a number, turn it into a number
    This avoids duplicates such as 1 and "1"
    """
    new_iterable = []
    for i in loaded_data:
        var = i
        try:
            var = int(i)
        except:
            pass
        finally:
            new_iterable.append(var)
    return new_iterable


class DataManager(UserDict):
    filemanager = FileManager()
    directory = '.'
    do_not_display_list = []  # data items not to show

    def __init__(self, *args, **kwargs: dict) -> None:
        super().__init__(*args, **kwargs)

    def register(self, name, initial_data, path=directory, ignore=False):
        """
        Register and load a data file. This file will be accessible to every AsyncWorker through context.data[name]
        """
        if ignore:
            self.do_not_display_list.append(name)
        loaded_data = None
        file_path, file_name = os.path.split(path)
        self.filemanager.register_file(file_name, file_path, short_name=name)
        if self.filemanager.exists(name):
            loaded_data = self.filemanager.smart_load(name)
        self[name] = initial_data
        if type and loaded_data:
            data = self[name]
            if isinstance(loaded_data, Iterable):
                new_iterable = _numericize(loaded_data)
                loaded_data = new_iterable
            if isinstance(data, set):
                self[name].update(loaded_data)
            elif isinstance(data, list):
                for d in loaded_data:
                    self[name].append(d)
            elif isinstance(data, dict):
                self[name].update(loaded_data)

    def file_update(self, name, data):
        self[name] = data

    def get_data_string(self):
        string = '\n'
        for k, v in self.items():
            if k in self.do_not_display_list:
                continue
            # only print the length of iterable values
            if isinstance(v, Sized) and not isinstance(v, str):
                string += f'\t\t\t    {k} count: {len(v)}\n'
            else:
                string += f'\t\t\t    {k}: {v}\n'
        return string.rstrip()

    def save(self):
        for i in self:
            if i in self.filemanager:
                self.filemanager.smart_save(i, self.get(i))
