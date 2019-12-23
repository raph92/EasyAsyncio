from typing import Iterable

from diskcache import Index


class CacheSet(Iterable):
    def __init__(self, iterable=(), directory=None):
        self.index = Index(directory)
        self.update(*iterable)

    def add(self, obj):
        self.index[hash(obj)] = obj

    def remove(self, obj):
        hash_ = hash(obj)
        if hash_ not in self.index:
            raise KeyError(obj)
        del self.index[hash_]

    def pop(self):
        return self.index.popitem()[1]

    def update(self, *obj):
        for o in obj:
            self.add(o)

    def difference(self, other):
        set(self) - set(other)

    def copy(self):
        return set(self).copy()

    def __iter__(self):
        return iter(self.index.values())

    def __contains__(self, item):
        return hash(item) in self.index

    def __sub__(self, other: Iterable):
        return set(self) - set(other)
