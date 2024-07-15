from bisect import bisect_left
from collections.abc import Mapping

from six import text_type

__all__ = ["Trie"]


class ABCTrie(Mapping):
    """Abstract base class for tries"""

    def keys(self, prefix=None):
        # pylint:disable=arguments-differ
        keys = super(Trie, self).keys()

        if prefix is None:
            return set(keys)

        return {x for x in keys if x.startswith(prefix)}

    def has_keys_with_prefix(self, prefix):
        for key in self.keys():
            if key.startswith(prefix):
                return True

        return False

    def longest_prefix(self, prefix):
        if prefix in self:
            return prefix

        for i in range(1, len(prefix) + 1):
            if prefix[:-i] in self:
                return prefix[:-i]

        raise KeyError(prefix)

    def longest_prefix_item(self, prefix):
        lprefix = self.longest_prefix(prefix)
        return (lprefix, self[lprefix])


class Trie(ABCTrie):
    def __init__(self, data):
        if not all(isinstance(x, text_type) for x in data.keys()):
            raise TypeError("All keys must be strings")

        self._data = data
        self._keys = sorted(data.keys())
        self._cachestr = ""
        self._cachepoints = (0, len(data))

    def __contains__(self, key):
        return key in self._data

    def __len__(self):
        return len(self._data)

    def __iter__(self):
        return iter(self._data)

    def __getitem__(self, key):
        return self._data[key]

    def keys(self, prefix=None):
        if prefix is None or prefix == "" or not self._keys:
            return set(self._keys)

        if prefix.startswith(self._cachestr):
            lo, hi = self._cachepoints
            start = i = bisect_left(self._keys, prefix, lo, hi)
        else:
            start = i = bisect_left(self._keys, prefix)

        keys = set()
        if start == len(self._keys):
            return keys

        while self._keys[i].startswith(prefix):
            keys.add(self._keys[i])
            i += 1

        self._cachestr = prefix
        self._cachepoints = (start, i)

        return keys

    def has_keys_with_prefix(self, prefix):
        if prefix in self._data:
            return True

        if prefix.startswith(self._cachestr):
            lo, hi = self._cachepoints
            i = bisect_left(self._keys, prefix, lo, hi)
        else:
            i = bisect_left(self._keys, prefix)

        if i == len(self._keys):
            return False

        return self._keys[i].startswith(prefix)
