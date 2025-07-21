# coding: utf-8

import sys
import yaml
from collections import OrderedDict
from yaml.representer import SafeRepresenter
from ..utils import ordered_dict

is_python_3 = (sys.version_info[0] == 3)

__all__ = ['YamlDumper', 'YamlLoader', 'ordered_dump', 'ordered_load']

try:
    BaseLoader = yaml.CSafeLoader
except AttributeError:
    BaseLoader = yaml.SafeLoader

try:
    BaseDumper = yaml.CSafeDumper
except AttributeError:
    BaseDumper = yaml.SafeDumper


class YamlLoader(BaseLoader):
    pass


class YamlDumper(BaseDumper):
    pass


# safe unicode
if not is_python_3:
    yaml.add_representer(unicode, SafeRepresenter.represent_unicode, Dumper=YamlDumper)


# safe ordered dict
def _construct_ordered_mapping(loader, node):
    loader.flatten_mapping(node)
    return ordered_dict(loader.construct_pairs(node))


if not is_python_3:
    YamlLoader.add_constructor(
        yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
        _construct_ordered_mapping,
    )


def _dict_representer(dumper, data):
    return dumper.represent_mapping(
        yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
        data.items()
    )


if not is_python_3:
    yaml.add_representer(dict, _dict_representer, Dumper=YamlDumper)
    yaml.add_representer(OrderedDict, _dict_representer, Dumper=YamlDumper)


# clean number list
def _number_sequence_representer(dumper, data):
    if all(isinstance(i, (float, int)) for i in data):
        return dumper.represent_sequence(
            yaml.resolver.BaseResolver.DEFAULT_SEQUENCE_TAG,
            data,
            flow_style=True,
        )
    return dumper.represent_sequence(
        yaml.resolver.BaseResolver.DEFAULT_SEQUENCE_TAG,
        data,
    )


yaml.add_representer(list, _number_sequence_representer, Dumper=YamlDumper)


# custom loader/dumper
def ordered_load(stream, Loader=YamlLoader):
    return yaml.load(stream, Loader=Loader)


def ordered_dump(data, stream=None, Dumper=YamlDumper, **kwds):
    return yaml.dump(data, stream, Dumper=Dumper, **kwds)
