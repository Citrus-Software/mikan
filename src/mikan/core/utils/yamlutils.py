# coding: utf-8

import sys
import yaml
from collections import OrderedDict
from yaml.representer import SafeRepresenter
from ..utils import ordered_dict

is_python_3 = (sys.version_info[0] == 3)

__all__ = ['YamlDumper', 'YamlLoader', 'ordered_dump', 'ordered_load']

try:
    class YamlLoader(yaml.CLoader):
        pass
except:
    class YamlLoader(yaml.Loader):
        pass

try:
    class YamlDumper(yaml.CDumper):
        pass
except:
    class YamlDumper(yaml.Dumper):
        pass


def _construct_mapping(loader, node):
    loader.flatten_mapping(node)
    return ordered_dict(loader.construct_pairs(node))


YamlLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _construct_mapping
)

if not is_python_3:
    YamlDumper.add_representer(unicode, SafeRepresenter.represent_unicode)
else:
    YamlDumper = yaml.Dumper


def _dict_representer(dumper, data):
    return dumper.represent_mapping(
        yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
        data.items()
    )


YamlDumper.add_representer(dict, _dict_representer)
YamlDumper.add_representer(OrderedDict, _dict_representer)


def ordered_load(stream, Loader=YamlLoader):
    return yaml.load(stream, Loader)


def ordered_dump(data, stream=None, Dumper=YamlDumper, **kwds):
    return yaml.dump(data, stream, Dumper, **kwds)
