from numbers import Number
from time import time
from typing import Iterable, Hashable

from diskcache import Index

from .helper import hash


class CacheSet:
    """
    A Set-like Cache that wraps :class:`diskcache.Index`
    """

    def __init__(self, iterable=(), directory=None):
        self.index = Index(directory)
        self.update(*iterable)

    def add(self, obj: object):
        if not isinstance(obj, Hashable):
            raise TypeError(f'{type(obj)} is not Hashable',
                            f'{str(obj)[:100]}...')
        self.index[hash(obj)] = obj

    def remove(self, obj):
        try:
            self.index.pop(hash(obj))
        except KeyError:
            raise KeyError(obj)

    def pop(self):
        return self.index.popitem()[1]

    def update(self, *obj):
        for o in obj:
            self.add(o)

    def clear(self):
        self.index.clear()

    def difference(self, other):
        self.__sub__(other)

    def copy(self):
        return set(self).copy()

    def __iter__(self):
        return iter(self.index.values())

    def __contains__(self, item):
        self__hash = hash(item)
        return self__hash in self.index

    def __sub__(self, other: Iterable):
        return set(self) - set(other)

    def __len__(self):
        return len(self.index)

    def __str__(self):
        return f'CacheSet({", ".join(self)})'

    def __repr__(self):
        return str(self)

    @property
    def directory(self):
        return self.index.directory


class EvictingIndex(Index):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def set(self, key, value, expire):
        self.__setitem__(key, value, expire)

    def __getitem__(self, key):
        obj: dict = super().__getitem__(key)
        if not isinstance(obj, dict):
            self.pop(key)
            raise KeyError(key)

        return obj.get('item')

    def __contains__(self, key: object) -> bool:
        if not super().__contains__(key):
            return False
        obj = self.get(key)
        # try:
        #     self._check_expired(key, obj)
        # except ExpiredError:
        #     return False
        return True

    def __setitem__(self, key, value, expire=0):
        if not isinstance(expire, Number):
            raise TypeError('expire must be a number')
        value = dict(item=value, time_added=time(),
                     expire=expire)
        super().__setitem__(key, value)

    def _check_expired(self, key, obj: dict):
        if not (isinstance(obj, dict) and 'expire' in obj):
            self.pop(key)
            raise ExpiredError(key)
        time_added = obj.get('time_added')
        expire = obj.get('expire')
        valid = time_added and expire is not None
        if not valid or time() - time_added > expire:
            self.pop(key)
            raise ExpiredError(key)


class ExpiredError(Exception):
    def __init__(self, *args: object) -> None:
        super().__init__(*args)
