"""
This file contains various utilities, including this recipe for an
ordered set http://code.activestate.com/recipes/576694/
"""
import collections


def dict_without(d, *keys):
    """
    Return a dictionary d, ensuring that keys are absent.
    """
    d2 = d.copy()
    for key in keys:
        d2.pop(key)

    return d2


def filter_none(d):
    """
    Remove items in d that are None.
    """

    return dict_without(d, *filter(lambda k: d[k] is None, d.keys()))


class OrderedSet(collections.MutableSet):

    def __init__(self, iterable=None):
        self.end = end = []
        end += [None, end, end]         # sentinel node for doubly linked list
        self.map = {}                   # key --> [key, prev, next]
        if iterable is not None:
            self |= iterable

    def __len__(self):
        return len(self.map)

    def __contains__(self, key):
        return key in self.map

    def add(self, key):
        if key not in self.map:
            end = self.end
            curr = end[1]
            curr[2] = end[1] = self.map[key] = [key, curr, end]

    def discard(self, key):
        if key in self.map:
            key, prev, next = self.map.pop(key)
            prev[2] = next
            next[1] = prev

    def __iter__(self):
        end = self.end
        curr = end[2]
        while curr is not end:
            yield curr[0]
            curr = curr[2]

    def __reversed__(self):
        end = self.end
        curr = end[1]
        while curr is not end:
            yield curr[0]
            curr = curr[1]

    def pop(self, last=True):
        if not self:
            raise KeyError('set is empty')
        key = self.end[1][0] if last else self.end[2][0]
        self.discard(key)
        return key

    def __repr__(self):
        if not self:
            return '%s()' % (self.__class__.__name__,)
        return '%s(%r)' % (self.__class__.__name__, list(self))

    def __eq__(self, other):
        if isinstance(other, OrderedSet):
            return len(self) == len(other) and list(self) == list(other)
        return set(self) == set(other)


if __name__ == '__main__':
    s = OrderedSet('abracadaba')
    t = OrderedSet('simsalabim')
    print(s | t)
    print(s & t)
    print(s - t)
