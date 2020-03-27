import gc
import logging
import os
from collections import UserDict
from typing import Sized, Iterable, Dict, Union, TYPE_CHECKING

from diskcache import Index, Deque
from easyfilemanager import FileManager

from easyasyncio.cachetypes import CacheSet, EvictingIndex

if TYPE_CHECKING:
    from easyasyncio import Job


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
        except (ValueError, TypeError):
            pass
        finally:
            new_iterable.append(var)
    return new_iterable


class DataManager(UserDict):
    filemanager = FileManager()
    directory = '.'
    do_not_display = []  # data items not to show in StatDisplay
    do_not_save = []
    save_kwargs: 'Dict[str, Dict]' = {}
    load_kwargs: 'Dict[str, Dict]' = {}

    def __init__(self, *args, **kwargs: dict) -> None:
        super().__init__(*args, **kwargs)
        self.logger = logging.getLogger(type(self).__name__)

    def register(self, name, initial_data, path_to_file=directory,
                 display=True, load=True, save=True, save_kwargs: dict = None,
                 load_kwargs: dict = None):
        """
        Register and load a data file. This file will be accessible to every
        AsyncWorker through context.data[name]
        """
        # whether to display this key's value in get_data_string()
        self.logger.debug('registering "%s" -> "%s"', name, path_to_file)
        if not display:
            self.do_not_display.append(name)
        if not save:
            self.do_not_save.append(name)
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

    def register_cache(self, name, data_type, path_to_file=None, display=True,
                       load=True, save=True, save_kwargs: dict = None,
                       load_kwargs: dict = None, directory='.') -> None:
        """
        The purpose of this function is to avoid having all objects loaded
        in memory and instead use a diskcache for storing/accessing objects.

        This function will create a cache at './cache/**name**' and register
        the file passed to `path_to_file` for autosaving.

        If `path_to_file` is None, then data will only be saved to the cache

        This data will be accessed by `JobManager.context.data.get(name)` and
        will return one of the following: :class:`Index`, :class:`CacheSet`,
        or :class:`Deque`.

        This data will be saved using ``save()``
        Args:
            directory: The name of the folder in ./cache/ to save this cache to
            name: The name to access this cache by `self.get(name)`
            data_type: The kind of cache to save data to (set, list, dict)
            path_to_file: An optional file to save cached data to on exit
            display: Whether to show this in the StatDisplay
            load:  Whether to load existing data in `path_to_file `into the cache
            save: Whether to auto save data
            save_kwargs: Kwargs to pass when saving via `FileManager`
            load_kwargs: Kwargs to pass when loading via `FileManager`

        Returns:

        """

        self.logger.debug('registering "%s" -> "%s"', name, path_to_file)
        if not display: self.do_not_display.append(name)
        if not save: self.do_not_save.append(name)
        if save_kwargs: self.save_kwargs[name] = save_kwargs
        if load_kwargs: self.load_kwargs[name] = load_kwargs
        else: load_kwargs = {}
        loaded_data = None
        if path_to_file:
            file_path, file_name = os.path.split(path_to_file)
            if not file_path: file_path = '.'
            self.filemanager.register_file(file_name, file_path,
                                           short_name=name)

            if load and self.filemanager.exists(name):
                loaded_data = self.filemanager.smart_load(name, **load_kwargs)
                self.logger.debug('loaded data for "%s" -> %s', name,
                                  (str(loaded_data)[:75] + '...') if len(
                                      str(loaded_data)) > 75 else str(
                                      loaded_data))
        self._create_cache(data_type, loaded_data, name, directory)
        del loaded_data
        gc.collect()

    def register_job_cache(self, job: 'Job', data_type: Union[set, list, dict],
                           name: str) -> None:
        full_name = f'{job.name}/{name}'
        self.register_cache(full_name, data_type, directory=job.name,
                            display=False, load=False)

    def _create_cache(self, initial_data, loaded_data, name, directory):
        if '/' in name:
            path_name = name.split('/')[1]
        else: path_name = name
        path = os.path.join('cache', directory, path_name)
        if isinstance(initial_data, set):
            if loaded_data: loaded_data = _numericize(loaded_data)
            self[name] = CacheSet(loaded_data or set(), path)
            self.logger.debug('creating new CacheSet for %s', name)
        elif isinstance(initial_data, list):
            self[name] = Deque(loaded_data or [], path)
            self.logger.debug('creating new Deque for %s', name)
        elif isinstance(initial_data, dict):
            self[name] = EvictingIndex(path, **(loaded_data or {}))
            self.logger.debug('creating new Index for %s', name)

    def load(self, data, loaded_data, name):
        if isinstance(loaded_data, Iterable) and not isinstance(
            loaded_data, dict):
            new_iterable = _numericize(loaded_data)
            loaded_data = new_iterable
        if isinstance(data, set):
            self[name].update(loaded_data)
        elif isinstance(data, list):
            self[name].extend(loaded_data)
        elif isinstance(data, dict):
            self[name].update(loaded_data)

    def get_job_cache(self, job: 'Job', name: str):
        return self.get(f'{job.name}/{name}')

    def file_update(self, name, data):
        self[name] = data

    def get_data_string(self) -> str:
        string = ''
        string += f'\n\t\t    <{"TOTALS".center(55, "-")}>\n'
        for k, v in self.items():
            if k in self.do_not_display:
                continue
            # only print the length of iterable values
            if isinstance(v, Sized) and not isinstance(v, (str, bytes)):
                string += f'\t\t\t    {k}: {len(v)}\n'
        string += f'\t\t    <{"END TOTALS".center(55, "-")}>\n'
        return string.rstrip()

    def save(self):
        for name, value in self.items():
            # check if this key has a file name
            if name not in self.filemanager or name in self.do_not_save:
                continue
            # if value is empty continue
            if not value:
                continue
            save_kwargs = self.save_kwargs.get(name, {})
            try:
                self.filemanager.smart_save(name, value,
                                            **save_kwargs)
            except Exception as e:
                self.logger.exception(e)

    def save_caches(self):
        self.logger.debug('saving cache files')
        for name, value in self.items():
            save_kwargs = self.save_kwargs.get(name, {})
            if name not in self.filemanager or name in self.do_not_save:
                continue
            if isinstance(value, (CacheSet, Deque)):
                self.filemanager.smart_save(name, list(value), mode='w+',
                                            **save_kwargs)
            elif isinstance(value, (Index, EvictingIndex)):
                self.filemanager.smart_save(name, dict(value),
                                            **save_kwargs)

    def clean(self):
        """
        Save storage space by clearing the caches when the data
        is already stored as a file
        """
        for name, value in self.items():
            if name not in self.filemanager:
                continue
            if isinstance(value, (CacheSet, Deque, Index)):
                value.clear()
                import shutil
                shutil.rmtree(value.directory)
