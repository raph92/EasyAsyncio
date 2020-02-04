import hashlib
from typing import Iterable, Hashable

from diskcache import Index


class CacheSet:
    """
    A Set-like Cache that wraps :class:`diskcache.Index`
    """

    def __init__(self, iterable=(), directory=None):
        self.index = Index(directory)
        self.update(*iterable)

    def add(self, obj):
        if not isinstance(obj, Hashable):
            raise TypeError(f'{type(obj)} is not Hashable',
                            f'{str(obj)[:100]}...')
        self.index[self._hash(obj)] = obj

    def remove(self, obj):
        try:
            self.index.pop(self._hash(obj))
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

    @staticmethod
    def _hash(obj):
        """
        Since hash() is not guaranteed to give the same result in different
        sessions, we will be using hashlib for more consistent results
        """
        hash_id = hashlib.md5()
        hash_id.update(repr(obj).encode('utf-8'))
        return str(hash_id.hexdigest())

    def __iter__(self):
        return iter(self.index.values())

    def __contains__(self, item):
        if isinstance(item, set):
            item = tuple(item)
        self__hash = self._hash(item)
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
