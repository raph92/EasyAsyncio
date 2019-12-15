import logging
import os
from collections import UserDict
from typing import Sized, Iterable, Dict

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
    do_not_display = []  # data items not to show
    save_kwargs: 'Dict[str, Dict]' = dict()
    load_kwargs: 'Dict[str, Dict]' = dict()

    def __init__(self, *args, **kwargs: dict) -> None:
        super().__init__(*args, **kwargs)
        self.logger = logging.getLogger(type(self).__name__)

    def register(self, name, initial_data, path_to_file=directory,
                 display=True, load=True, save_kwargs: dict = None,
                 load_kwargs: dict = None):
        """
        Register and load a data file. This file will be accessible to every AsyncWorker through context.data[name]
        """
        # whether to display this key's value in get_data_string()
        self.logger.debug('registering "%s" -> "%s"', name, path_to_file)
        if not display:
            self.do_not_display.append(name)
        if save_kwargs:
            self.save_kwargs[name] = save_kwargs
        if load_kwargs:
            self.load_kwargs[name] = load_kwargs
        else:
            load_kwargs = {}
        loaded_data = None
        file_path, file_name = os.path.split(path_to_file)
        if not file_path:
            file_path = '.'
        _, file_type = os.path.splitext(file_name)
        self.filemanager.register_file(file_name, file_path, short_name=name)
        if load and self.filemanager.exists(name):
            loaded_data = self.filemanager.smart_load(name, **load_kwargs)
            self.logger.debug('loaded data for "%s" -> %s', name,
                              (str(loaded_data)[:75] + '...') if len(
                                      str(loaded_data)) > 75 else str(
                                  loaded_data))
        self[name] = initial_data
        if loaded_data:
            self.load(initial_data, loaded_data, name)

    def load(self, data, loaded_data, name):
        if isinstance(loaded_data, Iterable) and not isinstance(
                loaded_data, dict):
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

    def get_data_string(self) -> str:
        string = ''
        string += f'\n\t\t    <{"TOTALS".center(55, "-")}>\n'
        for k, v in self.items():
            if k in self.do_not_display:
                continue
            # only print the length of iterable values
            if isinstance(v, Sized) and not isinstance(v, str):
                string += f'\t\t\t    {k}: {len(v)}\n'
        string += f'\t\t    <{"END TOTALS".center(55, "-")}>\n'
        return string.rstrip()

    def save(self):
        try:
            for name, value in self.items():
                # check if this key has a file name
                if name not in self.filemanager:
                    continue
                # if value is empty continue
                if not value:
                    continue
                save_kwargs = self.save_kwargs.get(name, {})
                self.filemanager.smart_save(name, value,
                                            **save_kwargs)
        except Exception as e:
            self.logger.exception(e)
