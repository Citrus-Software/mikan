# coding: utf-8

import re
import zlib
import yaml
import base64
import pkgutil
import os.path
import logging
import traceback
from six.moves import range
from six import string_types
from copy import copy, deepcopy

from mikan.core.logger import create_logger
from mikan.core import is_python_3
from mikan.core.utils import YamlDumper, YamlLoader, ordered_load, ordered_dict

from .monitor import JobMonitor

import mikan.templates.deformer

__all__ = [
    'Deformer', 'DeformerError',
    'WeightMap', 'WeightMapInterface',
    'DeformerDumper', 'DeformerLoader'
]

log = create_logger()


class Deformer(JobMonitor):
    modules = {}
    classes = {}
    software = None

    deformer = None
    deformer_data = ordered_dict()
    node_class = None
    default_decimals = 5

    def __new__(cls, **data):
        if 'deformer' not in data:
            raise RuntimeError('invalid data')
        new_cls = cls.get_class(data['deformer'])
        if not new_cls:
            return  # hotfix
        return super(Deformer, new_cls).__new__(new_cls)

    def __init__(self, **data):

        # build data
        self.root_id = None
        self.root = data.get('root')
        self.find_root()

        self.transform_id = None
        self.transform = data.get('transform')
        self.find_transform()

        self.id = data.get('id')
        self.node = data.get('node')
        if not self.node:
            self.find_node()

        self.geometry = None
        self.geometry_id = data.get('geometry_id')
        if self.node:
            self.find_geometry()

        self.order = data.get('order')
        self.input = None, None
        self.input_id = data.get('input_id')
        self.output = None, None
        self.output_id = data.get('output_id')

        # deformer data
        self.ini = data.pop('ini', None)
        self.data = self.get_default_data()
        self.data.update(data.get('data', {}))

        # conf
        self.decimals = data.get('decimals', self.default_decimals)
        self.protected = data.get('protected', False)

        # ui data
        self.ui_data = {}

        # monitor
        JobMonitor.__init__(self)
        self.modes = None

    def __copy__(self):
        data = {}
        data['deformer'] = self.deformer
        data['data'] = deepcopy(self.data)

        if self.transform:
            data['transform'] = self.transform
        elif self.transform_id:
            data['transform'] = self.transform_id
        if self.id:
            data['id'] = self.id
        if self.geometry_id:
            data['geometry_id'] = self.geometry_id

        if self.order:
            data['order'] = self.order
        if self.input_id:
            data['input_id'] = self.input_id
        if self.output_id:
            data['output_id'] = self.output_id

        if self.protected:
            data['protected'] = True
        if self.decimals != self.default_decimals:
            data['decimals'] = self.decimals

        return self.__class__(**data)

    def __deepcopy__(self, memo):
        return copy(self)

    def copy(self):
        return copy(self)

    @classmethod
    def get_class(cls, name):
        if name in cls.classes:
            return cls.classes[name]

        module = cls.modules[name]

        for importer, modname, ispkg in pkgutil.iter_modules(module.__path__):
            if modname == cls.software:
                _modname = module.__name__ + '.' + modname
                cls_module = importer.find_module(_modname).load_module(_modname)
                new_cls = cls_module.Deformer
                new_cls.deformer = name
                new_cls.deformer_data = module.deformer_data

                cls.classes[name] = new_cls
                return new_cls

    @classmethod
    def get_cls_from_node(cls, node):
        for name in cls.modules:
            _cls = cls.get_class(name)
            if _cls and _cls.is_node(node):
                return _cls

    @classmethod
    def is_node(cls, node):
        if cls.node_class and isinstance(node, cls.node_class):
            return True
        return False

    @classmethod
    def get_all_modules(cls, module=mikan.templates.deformer):
        for importer, modname, ispkg in pkgutil.iter_modules(module.__path__):
            if not ispkg:
                continue
            _modname = module.__name__ + '.' + modname
            package = importer.find_module(_modname).load_module(_modname)

            package.deformer_data = ordered_dict()

            path = package.__path__[0] + os.path.sep + 'deformer.yml'
            if os.path.exists(path):
                try:
                    with open(path, 'r') as stream:
                        package.deformer_data = ordered_load(stream)
                except Exception as e:
                    log.error('failed to load Deformer "{}" deformer.yml: {}'.format(modname, e))

            cls.modules[modname] = package

    def get_default_data(self):
        default_data = ordered_dict()

        defaults = self.deformer_data.get('data', {})
        for key in defaults:
            key_data = defaults[key]
            if 'value' in key_data:
                default_data[key] = deepcopy(key_data['value'])

        return default_data

    def get_parser_excluded_keys(self):
        keys = []

        defaults = self.deformer_data.get('data', {})
        for key in defaults:
            key_data = defaults[key]
            if 'parser' in key_data and not key_data['parser']:
                keys.append(key)

        return keys

    def encode_deformer_data(self):
        data = deepcopy(self.data)
        data.pop('transform', None)

        default = self.get_default_data()
        for k in list(data):
            if k in default:
                if data[k] == default[k]:
                    data.pop(k)

        return yaml.dump({'data': data}, Dumper=DeformerDumper, default_flow_style=False)

    def build(self, **kw):
        """placeholder"""

    def bind(self, modes=None, source=None):

        if modes is None:
            modes = set()
        self.modes = modes

        source_str = ''
        if source is not None:
            source_str = '  # source: ' + str(source)

        self.clear_logs()

        # recursively lookup for nodes
        self.parse_nodes()
        if self.delay_parser():
            return Deformer.STATUS_DELAY

        if self.transform is None:
            self.log_warning('-- cancel bind: {}'.format(self) + source_str)
            self.log_warning('cannot find {}'.format(self.transform_id))
            self.log_summary()
            return Deformer.STATUS_INVALID

        if self.need_geometry:
            try:
                self.find_geometry()
            except:
                pass
            if not self.geometry:
                self.unresolved.append('{}->shape'.format(self.transform_id))
                return Deformer.STATUS_DELAY

        # bind
        try:
            if self.id:
                if self.id in self.get_ids():
                    self.find_node()
                    self.update()
                    log.debug('-- update bind: {}'.format(self) + source_str)
                    return Deformer.STATUS_DONE
            self.build()
            self.set_id()
            self.set_protected()

            if not self.logs and not self.unresolved:
                log.debug('-- bind: {}'.format(self) + source_str)
            else:
                self.log_warning('-- bind: {}'.format(self) + source_str, 0)

            self.log_summary()
            return Deformer.STATUS_DONE

        except DeformerError as e:
            self.log_warning('-- failed to bind: {}'.format(self) + source_str, 0)
            self.log_error('{}'.format(e.args[0]))
            self.log_summary()
            return Deformer.STATUS_ERROR

        except Exception:
            self.log_warning('-- failed to bind: {}'.format(self) + source_str, 0)
            msg = traceback.format_exc().strip('\n')
            self.log(logging.CRITICAL, msg)
            self.log_summary()
            return Deformer.STATUS_CRASH

    def update(self):
        self.write()

    def parse_nodes(self):
        """placeholder"""

    def delay_parser(self):
        if self.unresolved:
            for n in self.unresolved:
                if '::mod.' in n or '::!mod.' in n or '->' in n:
                    return True
        return False

    def find_root(self):
        """placeholder"""

    def find_transform(self):
        """placeholder"""

    def find_node(self):
        if self.id and self.transform:
            geo_ids = self.get_ids()
            if self.id in geo_ids:
                self.node = geo_ids[self.id]
                return True
        return False

    def find_geometry(self):
        """placeholder"""

    @property
    def need_geometry(self):
        return not self.deformer_data.get('virtual', False)

    @staticmethod
    def get_deformer_ids(xfo, root=None):
        """placeholder"""
        return {}

    def get_ids(self):
        return self.get_deformer_ids(self.transform, self.root)

    def set_id(self):
        """placeholder"""

    def set_protected(self):
        """placeholder"""

    def read(self):
        """placeholder"""

    def read_deformer(self):
        self.read()
        self.round()

    def get_size(self):
        return 0

    def write(self):
        """placeholder"""

    @staticmethod
    def hook(dfm, xfo, hook):
        """placeholder"""

    @staticmethod
    def get_hook_id(plug, xfo=None):
        """placeholder"""

    def create_weightmap(self, wm, **data):
        if wm is None:
            n = self.get_size()
            wm = WeightMap([0.0] * n)
        return WeightMapInterface(wm, **data)

    def get_weightmaps(self):
        """placeholder"""
        return []

    def set_weightmaps(self, maps):
        """placeholder"""

    def get_indexed_maps(self):
        if 'maps' not in self.data:
            return [], []
        ids = []
        for i in self.data['maps']:
            if isinstance(i, int):
                ids.append(i)
        ids.sort()
        maps = [self.data['maps'][i] for i in ids]
        return ids, maps

    def remap_indexed_maps(self):
        if 'maps' not in self.data:
            return

        ids = []
        for k in list(self.data['maps']):
            if isinstance(k, int):
                ids.append(k)
        ids.sort()
        remap = dict(zip(ids, range(len(ids))))

        for key in ('maps', 'infs', 'bind_pose', 'bind_pose_root'):
            if key in self.data and isinstance(self.data[key], dict):
                values = {}
                for k in remap:
                    if k in self.data[key]:
                        values[remap[k]] = self.data[key][k]
                self.data[key] = values

    def normalize(self, only_excess=False):
        ids, maps = self.get_indexed_maps()
        weights = list(zip(*[x.weights for x in maps]))

        for i, w in enumerate(weights):
            s = sum(w)
            if s == 0:
                continue
            if not only_excess or (only_excess and s > 1):
                weights[i] = [x / s for x in w]

        weights = zip(*weights)
        for i, w in enumerate(weights):
            maps[i].weights = list(w)

    def round(self):
        ids, maps = self.get_indexed_maps()
        weights = list(zip(*[x.weights for x in maps]))

        for i, w in enumerate(weights):
            s = round(sum(w), self.decimals)
            r = list(map(lambda x: round(x, self.decimals), w))
            d = list(map(lambda x, y: x - y, w, r))

            delta = round(s - sum(r), self.decimals)
            if delta > 0:
                r[d.index(max(d))] += delta
            if delta < 0:
                r[d.index(min(d))] += delta

            weights[i] = r

        weights = zip(*weights)
        for i, w in enumerate(weights):
            maps[i].weights = list(w)


class DeformerError(Exception):
    pass


Deformer.get_all_modules()


class WeightMap(object):
    def __init__(self, weights, lock=False, partition=None):
        if isinstance(weights, string_types):
            self.decode(weights)
        else:
            # always copy weights when new
            self.weights = list(weights)

        self.lock = lock
        self.partition = partition

    def __getitem__(self, i):
        return self.weights[i]

    def __setitem__(self, i, value):
        self.weights[i] = value

    def copy(self):
        return WeightMap(self.weights, lock=self.lock, partition=self.partition)

    def encode(self, decimals=6, compress=True):
        rle = []

        for v in self.weights:
            if isinstance(v, float):
                v = round(v, decimals)
            if len(rle):
                if v == rle[-1][0]:
                    rle[-1][1] += 1
                else:
                    rle.append([v, 1])
            else:
                rle.append([v, 1])

        wmr = ''
        for v in rle:
            d = '{0:.{1}f}'.format(v[0], decimals).rstrip('0').rstrip('.')
            if v[1] == 1:
                wmr += d
            else:
                wmr += '{0}*{1}'.format(d, v[1])
            wmr += ' '
        wmr = wmr[:-1]

        if compress and len(wmr) > 80:
            wmz = base64.b64encode(zlib.compress(wmr.encode('utf-8'), 9)).decode('utf-8')
            return wmz
        else:
            return wmr

    def decode(self, weights):
        self.weights = []

        isb64 = re.compile('^([A-Za-z0-9+/]{4})*([A-Za-z0-9+/]{4}|[A-Za-z0-9+/]{3}=|[A-Za-z0-9+/]{2}==)$')
        if isb64.match(weights):
            weights = zlib.decompress(base64.b64decode(weights)).split()
        else:
            weights = weights.split()
            if is_python_3:
                weights = [str.encode(w, 'utf-8') for w in weights]

        for v in weights:
            n = 1
            if b'*' in v:
                v, n = v.split(b'*')
                n = int(n)

            if b'.' in v:
                v = float(v)
            else:
                v = int(v)

            self.weights += [v] * n

    def normalize(self):
        f = 1. / max(self.weights)
        for i in range(len(self.weights)):
            self.weights[i] *= f

    def mirror(self, sym, direction=1):
        for i in sym[direction]:
            j = sym[direction][i]
            self.weights[j] = self.weights[i]

    def flip(self, sym):
        for i in sym[1]:
            j = sym[1][i]
            self.weights[i], self.weights[j] = self.weights[j], self.weights[i]

    def __len__(self):
        return len(self.weights)

    def __mul__(self, other):
        new = self.copy()
        if isinstance(other, WeightMap):
            if len(self) != len(other):
                raise RuntimeError('weightmaps are different')
            for i, w in enumerate(new.weights):
                new[i] *= other[i]

        elif isinstance(other, (int, float)):
            for i, w in enumerate(new.weights):
                new[i] *= other
        return new

    def __add__(self, other):
        new = self.copy()
        if isinstance(other, WeightMap):
            if len(self) != len(other):
                raise RuntimeError('weightmaps are different')
            for i, w in enumerate(new.weights):
                new[i] += other[i]

        elif isinstance(other, (int, float)):
            for i, w in enumerate(new.weights):
                new[i] += other
        return new

    def __sub__(self, other):
        new = self.copy()
        if isinstance(other, WeightMap):
            if len(self) != len(other):
                raise RuntimeError('weightmaps are different')
            for i, w in enumerate(new.weights):
                new[i] -= other[i]

        elif isinstance(other, (int, float)):
            for i, w in enumerate(new.weights):
                new[i] -= other
        return new


class WeightMapInterface(object):

    def __init__(self, wm, **data):
        self.weightmap = wm
        self.data = data

        self.modified = False

    def get_node(self):
        """placeholder"""


# hack yaml io
class DeformerDumper(YamlDumper):
    pass


class DeformerLoader(YamlLoader):
    pass


def _weight_map_representer(dumper, data):
    return dumper.represent_scalar('!weightmap', data.encode(), style='plain')


def _weight_map_constructor(loader, node):
    value = loader.construct_scalar(node)
    return WeightMap(value)


DeformerDumper.add_representer(WeightMap, _weight_map_representer)
DeformerLoader.add_constructor('!weightmap', _weight_map_constructor)
