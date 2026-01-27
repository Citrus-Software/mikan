# coding: utf-8

import re
import sys
from fnmatch import fnmatch
from abc import abstractmethod
from copy import copy, deepcopy
from collections import defaultdict, OrderedDict

try:
    from collections.abc import Mapping, MutableMapping, MutableSet
except ImportError:
    from collections import Mapping, MutableMapping, MutableSet

__all__ = ['Tree', 'SuperTree']

is_python_3 = (sys.version_info[0] == 3)
ordered_dict = dict
if sys.version_info[0] != 3:
    ordered_dict = OrderedDict


class OrderedSet(MutableSet):

    def __init__(self, iterable=None):
        self._map = ordered_dict()
        if iterable is not None:
            self |= iterable

    def __contains__(self, key):
        return key in self._map

    def add(self, value):
        if value not in self._map:
            self._map[value] = None

    def discard(self, value):
        if value in self._map:
            del self._map[value]

    def __iter__(self):
        return iter(self._map)

    def __len__(self):
        return len(self._map)

    def __repr__(self):
        return 'OrderedSet({})'.format(list(self._map))


class BaseTree(MutableMapping):

    def __init__(self, sep='.'):
        self._key_sep = sep

    def rare_keys(self):
        branches = set()
        for key in self.keys():
            if self._key_sep not in key:
                yield key
                continue
            key = key.split(self._key_sep, 1)[0]
            if key not in branches:
                yield key
                branches.add(key)

    def rare_values(self):
        for key in self.rare_keys():
            yield self[key]

    def rare_items(self):
        for key in self.rare_keys():
            yield key, self[key]

    @property
    def sep(self):
        return self._key_sep

    @abstractmethod
    def copy(self):
        pass

    def rare_copy(self):
        return BaseTree.rarefy(self)

    @abstractmethod
    def branch(self, key):
        pass

    @staticmethod
    def rarefy(tree):
        """
        rarefy(Tree({'a.b.c' : 1}))
        {'a': {'b': {'c': 1}}}
        rarefy({'a.b.c' : 1})
        {'a': {'b': {'c': 1}}}
        """
        result = {}
        for key, value in tree.items():
            target = result
            if tree.sep in key:
                keyparts = key.split(tree.sep)
                key = keyparts.pop()
                for keypart in keyparts:
                    target = target.setdefault(keypart, {})
            if isinstance(value, Mapping):
                value = BaseTree.rarefy(value)
            target[key] = value

        return result

    @staticmethod
    def flatten(d, sep='.'):
        """
        nested = {'a': {'b': {'c': 1}}}
        Tree(nested)                        # without flatten
        Tree({'a': {'b': {'c': 1}}})
        Tree(flatten(nested))               # with flatten
        Tree({'a.b.c': 1})
        """
        for key, value in d.items():
            if isinstance(value, Mapping):
                for subkey, subvalue in BaseTree.flatten(value, sep=sep):
                    yield str(key) + sep + str(subkey), subvalue
            else:
                yield str(key), value

    def get(self, item, default=None):
        try:
            return self[item]
        except KeyError:
            return default


_void = object()


class Tree(BaseTree):

    def __init__(self, data=None, sep='.'):
        BaseTree.__init__(self, sep=sep)

        self._branches = defaultdict(OrderedSet)
        self._items = {}
        if data:
            self.update(data)

    def __setitem__(self, key, value):
        if key in self._branches:
            del self[key]
        self._items[key] = value
        if self._key_sep in key:
            path = key.split(self._key_sep)
            for i in range(1, len(path)):
                lead = self._key_sep.join(path[:i])
                tail = self._key_sep.join(path[i:])
                if lead in self._items:
                    del self[lead]
                self._branches[lead].add(tail)

    def __getitem__(self, key):
        try:
            return self._items[key]
        except KeyError:
            if '*' in key:
                tree = Subtree()
                for _key in self._items:
                    if fnmatch(_key, key):
                        tree[_key] = self._items[_key]
                if not tree:
                    raise KeyError(key)
                elif len(tree) == 1:
                    return list(tree._items.values())[0]
                else:
                    return tree
            else:
                if key not in self._branches:
                    raise KeyError(key)
                return self.branch(key)

    def __delitem__(self, key):
        try:
            del self._items[key]
            if self._key_sep in key:
                path = key.split(self._key_sep)
                for i in range(1, len(path)):
                    lead = self._key_sep.join(path[:i])
                    tail = self._key_sep.join(path[i:])
                    self._branches[lead].discard(tail)
                    if not self._branches[lead]:
                        del self._branches[lead]
        except KeyError:
            if key not in self._branches:
                raise
            self.branch(key).clear()

    def __iter__(self):
        return iter(self._items)

    def __len__(self):
        return len(self._items)

    def __repr__(self):
        return '{0}({1!r})'.format(self.__class__.__name__, self._items)

    def __copy__(self):
        """ Returns a shallow copy of the tree.  The result has the same type. """
        return self.__class__(self)

    def __deepcopy__(self, memo):
        """ Returns a shallow copy of the tree.  The result has the same type. """
        tree = self.__class__()
        tree._branches = deepcopy(self._branches)
        tree._items = deepcopy(self._items)
        return tree

    copy = __copy__

    def branch(self, key):
        """ Returns a :class:`BranchProxy` object for specified ``key`` """
        return Branch(key, self)

    def branches(self):
        for key in self._branches:
            yield self.branch(key)

    def pop(self, key, default=_void):
        """
        Removes specified key and returns the corresponding value.
        If key is not found, ``default`` is returned if given,
        otherwise KeyError is raised.

        If extracted value is a branch, it will be converted to :class:`Tree`.

        """
        try:
            value = self[key]
        except KeyError:
            if default is _void:
                raise
            return default
        else:
            if isinstance(value, Branch):
                value = value.copy()
            del self[key]
            return value


class Subtree(Tree):
    pass


class Branch(BaseTree):

    def __init__(self, key, parent):
        self._key_sep = parent._key_sep
        self._key = key
        self._parent = parent

    def _itemkey(self, key):
        return self._key_sep.join((self._key, key))

    def keys(self):
        if self._key not in self._parent._branches:
            return set()
        return self._parent._branches[self._key]

    def __getitem__(self, key):
        return self._parent[self._itemkey(key)]

    def __setitem__(self, key, value):
        self._parent[self._itemkey(key)] = value

    def __delitem__(self, key):
        del self._parent[self._itemkey(key)]

    def __iter__(self):
        return iter(self.keys())

    def __len__(self):
        return len(self.keys())

    def __repr__(self):
        return '{0}({1!r}): {2!r}'.format(
            self.__class__.__name__,
            self._key,
            dict(self),
        )

    @property
    def key(self):
        return self._key

    def branch(self, key):
        """ Returns a :class:`BranchProxy` object for specified ``key`` """
        return self._parent.branch(self._itemkey(key))

    def copy(self):
        """
        Returns a shallow copy of the branch.  The result has the same type
        as the branch owner, i.e. :class:`Tree` or derrived from one.
        """
        return self._parent.__class__(self)

    def pop(self, key, default=_void):
        """
        Removes specified key and returns the corresponding value.
        If key is not found, ``default`` is returned if given,
        otherwise KeyError is raised.

        If extracted value is a branch, it will be converted to :class:`Tree`.
        """
        return self._parent.pop(self._itemkey(key), default)


class SuperTree(object):

    def __init__(self, key_sep='::'):
        self.tree = Tree()
        self.dict = dict()

        self._key_sep = key_sep

    def __setitem__(self, key, value):
        mainkey, sep, subkey = key.partition(self._key_sep)

        if mainkey not in self.tree:
            self.tree[mainkey] = Tree()
        if subkey:
            self.tree[mainkey][subkey] = value
        else:
            self.dict[mainkey] = value

    def __getitem__(self, key):
        mainkey, sep, subkey = key.partition(self._key_sep)

        if subkey:
            subtree = self.tree[mainkey]
            if type(subtree) is Tree:
                v = subtree[subkey]
                if type(v) in (Branch, Subtree):
                    return v.rare_copy()
                else:
                    return v
            elif type(subtree) in [Branch, Subtree]:
                newtree = Tree()
                for k, i in subtree.items():
                    try:
                        newtree[k] = i[subkey]
                    except:
                        pass

                if not newtree._items:
                    return None
                elif len(newtree._items) != 1:
                    return newtree.rare_copy()
                else:
                    v = list(newtree._items.values())[0]
                    if type(v) in [Branch, Subtree]:
                        return v.rare_copy()
                    else:
                        return v
        else:
            return self.dict[mainkey]

    def __delitem__(self, key):
        mainkey, sep, subkey = key.partition(self._key_sep)

        if subkey:
            subtree = self.tree[mainkey]
            if isinstance(subtree, Tree):
                del subtree[subkey]
            elif isinstance(subtree, Branch):
                subtrees = subtree.rare_copy()
                for k in subtrees:
                    try:
                        del subtrees[k][subkey]
                    except:
                        pass
        else:
            del self.dict[mainkey]

    def __iter__(self):
        return iter(self.tree._items)

    def __len__(self):
        return len(self.tree._items)

    def __repr__(self):
        return '{0}({1!r})'.format(self.__class__.__name__, self.tree)

    def __copy__(self):
        tree = SuperTree(key_sep=self._key_sep)
        tree.tree = copy(self.tree)
        tree.dict = copy(self.dict)
        return tree

    def __deepcopy__(self, memo):
        tree = SuperTree(key_sep=self._key_sep)
        tree.tree = deepcopy(self.tree)
        tree.dict = deepcopy(self.dict)
        return tree

    copy = __copy__

    def clear(self):
        self.tree.clear()
        self.dict.clear()

    def get(self, item, default=None, as_list=False):
        try:
            if not as_list:
                return self[item]
            else:
                if isinstance(self[item], dict):
                    return SuperTree.flatten(self[item])
                return [self[item]]

        except KeyError:
            return default

    def keys(self):
        keys = []
        for key in self:
            for subkey in self.tree[key]:
                keys.append(key + self._key_sep + subkey)
        return keys

    @staticmethod
    def flatten(obj, objects=None):
        if objects is None:
            objects = []

        try:
            iter(obj)
        except TypeError:
            objects.append(obj)
            return objects

        for k in sorted(obj, key=_int_key):
            v = obj[k]
            if isinstance(v, dict):
                SuperTree.flatten(v, objects)
            else:
                objects.append(v)
        return objects

    # todo: rare keys for supertree
    # def rare_keys(self):
    #     return []


_find_index = re.compile(r'\d+')


def _int_key(key):
    i = _find_index.findall(key)
    if i:
        return 0, int(i[-1])
    else:
        return 1, key
