# coding: utf-8

import re
import sys
import unicodedata
from functools import reduce
from itertools import takewhile
from contextlib import contextmanager
from collections import OrderedDict
from six import string_types

from mikan.vendor.unidecode import unidecode

__all__ = [
    'is_python_3',
    're_add', 're_slash', 're_pipe', 're_is_int', 're_is_float', 're_get_keys',
    'ordered_dict', 'get_slice', 'longest_common_prefix', 'longest_common_suffix', 'cleanup_str', 'filter_str',
    'flatten_list', 'flatten_dict', 'unique', 'nullcontext',
    'SingletonMetaClass', 'singleton'
]

is_python_3 = (sys.version_info[0] == 3)

re_add = re.compile(r'[^+]+')
re_slash = re.compile(r'[^/]+')
re_pipe = re.compile(r'[^|]+')
re_is_int = re.compile(r'^-?\d+$')
re_is_float = re.compile(r'^[-+]?[0-9]*\.?[0-9]+$')
re_get_keys = re.compile(r'\[([A-Za-z0-9_:-]+)\]')

ordered_dict = dict
if not is_python_3:
    ordered_dict = OrderedDict


def get_slice(item):
    return slice(*[{True: lambda n: None, False: int}[x == ''](x) for x in (item.split(':') + ['', '', ''])[:3]])


def longest_common_prefix(xs):
    """Longest prefix shared by all strings in xs"""
    if not xs:
        return ''
    if len(xs) == 1:
        return xs[0]
    xs.sort()
    shortest = xs[0]
    prefix = ''
    for i in range(len(shortest)):
        if xs[len(xs) - 1][i] == shortest[i]:
            prefix += xs[len(xs) - 1][i]
        else:
            break
    return prefix


def longest_common_suffix(xs):
    """Longest suffix shared by all strings in xs"""

    def all_same(cs):
        h = cs[0]
        return all(h == c for c in cs[1:])

    def first_char_prepended(s, cs):
        return cs[0] + s

    return reduce(
        first_char_prepended,
        takewhile(
            all_same,
            zip(*(reversed(x) for x in xs))
        ),
        ''
    )


def cleanup_str(text, sub='_'):
    try:
        text = str(text)
        text = text.decode('latin-1')
    except:
        pass

    nfkd_form = unicodedata.normalize('NFKD', text)
    ascii_string = nfkd_form.encode('ASCII', 'ignore').decode('utf-8')
    clean_string = re.sub(r'\W+', sub, ascii_string)

    return clean_string


def filter_str(text, r='_'):
    text = unidecode(text)
    if r is not None:
        text = re.sub(r'\W+', r, text)
    return text


def flatten_list(l):
    for el in l:
        if type(el) in (tuple, list) and not isinstance(el, string_types):
            for sub in flatten_list(el):
                yield sub
        else:
            yield el


def flatten_dict(obj, objects=None):
    if objects is None:
        objects = []

    for k in sorted(obj):
        v = obj[k]
        if isinstance(v, dict):
            flatten_dict(v, objects)
        else:
            objects.append(v)
    return objects


def unique(elements):
    return list(ordered_dict.fromkeys(elements))


def _unique3(elements):
    return list(dict.fromkeys(elements))


if is_python_3:
    unique = _unique3


@contextmanager
def nullcontext(enter_result=None):
    yield enter_result


# ----- singleton

class SingletonMetaClass(type):
    def __init__(cls, name, bases, dict):
        super(SingletonMetaClass, cls).__init__(name, bases, dict)
        original_new = cls.__new__

        def my_new(cls, *args, **kwds):
            if cls.instance == None:
                cls.instance = original_new(cls, *args, **kwds)
            return cls.instance

        cls.instance = None
        cls.__new__ = staticmethod(my_new)


def singleton(cls):
    instances = {}

    def get_instance(*args, **kwargs):
        if cls not in instances:
            instances[cls] = cls(*args, **kwargs)
        return instances[cls]

    return get_instance
