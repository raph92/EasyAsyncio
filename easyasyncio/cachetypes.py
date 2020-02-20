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

    def add(self, obj):
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
        if isinstance(item, set):
            item = tuple(item)
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
