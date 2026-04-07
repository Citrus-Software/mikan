# coding: utf-8

"""Abstract Deformer Module.

This module provides the base classes for managing deformers in the Mikan framework.
It defines the abstract interface for deformer operations that can be implemented
by different DCC applications (Maya, Tangerine, etc.).

The module supports:
    - Deformer data serialization and deserialization
    - Weight map management with RLE compression
    - Cross-platform deformer abstraction
    - Dynamic deformer class registration via templates

Classes:
    Deformer: Abstract base class for deformer management.
    DeformerError: Exception raised for deformer-related errors.
    WeightMap: Container for vertex weight data with compression support.
    WeightMapInterface: Interface for weight map node management.
    DeformerDumper: YAML dumper for deformer data serialization.
    DeformerLoader: YAML loader for deformer data deserialization.

Examples:
    Creating a deformer from data:
        >>> data = {'deformer': 'skin', 'transform': 'pSphere1'}
        >>> dfm = Deformer(**data)

    Working with weight maps:
        >>> wm = WeightMap([1.0, 0.5, 0.0, 0.0, 0.5, 1.0])
        >>> encoded = wm.encode()
        >>> wm2 = WeightMap(encoded)

    Weight map arithmetic:
        >>> wm1 = WeightMap([1.0, 0.5, 0.0])
        >>> wm2 = WeightMap([0.5, 0.5, 0.5])
        >>> result = wm1 * wm2
"""

import re
import zlib
import yaml
import base64
import struct
import pkgutil
import os.path
import logging
import traceback
import itertools
from six.moves import range
from six import string_types
from copy import copy, deepcopy

has_numpy = False
try:
    import numpy as np

    has_numpy = True
except ImportError:
    pass

from mikan.core.logger import create_logger, timed_code
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
    """Abstract base class for deformer management.

    This class provides the core interface for managing deformers across different
    DCC applications. It handles deformer registration, data management, weight maps,
    and serialization. Software-specific implementations should inherit from this class.

    Attributes:
        modules (dict): Registry of available deformer modules.
        classes (dict): Cache of instantiated deformer classes.
        software (str): Identifier for the DCC software (e.g., 'maya').
        deformer (str): Type of deformer (e.g., 'skin', 'blendShape', 'cluster').
        deformer_data (OrderedDict): Default configuration data for the deformer type.
        node_class: Expected node type for this deformer (used for type checking).
        default_decimals (int): Default precision for weight values.
        root: Root node for path resolution.
        root_id (str): Identifier for the root node.
        transform: Transform node being deformed.
        transform_id (str): Identifier for the transform node.
        id (str): Unique identifier for this deformer instance.
        node: The deformer node itself.
        geometry: The shape node being deformed.
        geometry_id (str): Identifier for the geometry.
        order (str): Deformer stack order.
        input (tuple): Input connection (node, transform).
        input_id (str): Identifier for input connection.
        output (tuple): Output connection (node, transform).
        output_id (str): Identifier for output connection.
        data (dict): Dictionary containing all deformer data.
        decimals (int): Precision for weight values.
        protected (bool): Whether this deformer is protected from modification.
        ini: Configuration parser for data storage.
        ui_data (dict): Data for UI representation.
        modes (set): Active modes for the deformer.

    Examples:
        Creating a deformer from stored data:
            >>> data = {
            ...     'deformer': 'skin',
            ...     'transform': 'pSphere1',
            ...     'data': {'maps': {}, 'infs': {}}
            ... }
            >>> dfm = Deformer(**data)

        Copying a deformer:
            >>> dfm_copy = dfm.copy()

    Note:
        This is an abstract base class. Use software-specific implementations
        like mikan.maya.core.deformer.Deformer for actual deformer operations.
    """

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
        """Create a shallow copy of the deformer.

        Creates a new deformer instance with the same configuration.
        The deformer data is deep-copied to ensure independence.

        Returns:
            Deformer: A new deformer instance with copied data.

        Examples:
            >>> from copy import copy
            >>> dfm_copy = copy(dfm)
        """
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
        """Create a deep copy of the deformer.

        Delegates to __copy__ since deformer data is already deep-copied.

        Args:
            memo (dict): Memoization dictionary for recursive copies.

        Returns:
            Deformer: A new deformer instance with copied data.
        """
        return copy(self)

    def copy(self):
        """Create a copy of the deformer.

        Returns:
            Deformer: A new deformer instance with copied data.

        Examples:
            >>> dfm_copy = dfm.copy()
        """
        return copy(self)

    @classmethod
    def get_class(cls, name):
        """Get or create a deformer class for the specified deformer type.

        Retrieves a cached deformer class or dynamically loads and instantiates
        it from the corresponding template module.

        Args:
            name (str): Name of the deformer type (e.g., 'skin', 'blendShape').

        Returns:
            type: The deformer class for the specified type, or None if not found.

        Examples:
            >>> SkinDeformer = Deformer.get_class('skin')
            >>> dfm = SkinDeformer(transform='pSphere1')
        """
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
        """Get the appropriate deformer class for a given node.

        Iterates through registered deformer modules to find a class
        that matches the given node type.

        Args:
            node: A DCC node to find a matching deformer class for.

        Returns:
            type: The matching deformer class, or None if no match found.

        Examples:
            >>> dfm_cls = Deformer.get_cls_from_node(skin_node)
            >>> if dfm_cls:
            ...     dfm = dfm_cls.create(geometry, skin_node)
        """
        for name in cls.modules:
            _cls = cls.get_class(name)
            if _cls and _cls.is_node(node):
                return _cls

    @classmethod
    def is_node(cls, node):
        """Check if a node is a valid deformer of this type.

        Args:
            node: Node to check.

        Returns:
            bool: True if node matches the expected node_class type.
        """
        if cls.node_class and isinstance(node, cls.node_class):
            return True
        return False

    @classmethod
    def get_all_modules(cls, module=mikan.templates.deformer):
        """Discover and register all available deformer modules.

        Scans the templates.deformer package for deformer implementations,
        loads their configuration from deformer.yml files, and registers
        them in the modules dictionary.

        Args:
            module: The parent module to scan for deformer packages.
                Defaults to mikan.templates.deformer.

        Note:
            This method is called automatically at module import time.
        """
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
        """Get default data values from deformer configuration.

        Extracts default values from the deformer_data configuration,
        creating a fresh copy for each deformer instance.

        Returns:
            OrderedDict: Dictionary of default data values.
        """
        default_data = ordered_dict()

        defaults = self.deformer_data.get('data', {})
        for key in defaults:
            key_data = defaults[key]
            if 'value' in key_data:
                default_data[key] = deepcopy(key_data['value'])

        return default_data

    def get_parser_excluded_keys(self):
        """Get keys that should be excluded from parsing.

        Returns:
            list: List of data keys marked with parser=False in configuration.
        """
        keys = []

        defaults = self.deformer_data.get('data', {})
        for key in defaults:
            key_data = defaults[key]
            if 'parser' in key_data and not key_data['parser']:
                keys.append(key)

        return keys

    def encode_deformer_data(self):
        """Encode deformer data to YAML string format.

        Serializes deformer data, excluding default values and transform
        information, into a YAML-formatted string.

        Returns:
            str: YAML-formatted string containing deformer data.

        Examples:
            >>> yaml_str = dfm.encode_deformer_data()
        """
        data = deepcopy(self.data)
        data.pop('transform', None)

        default = self.get_default_data()
        for k in list(data):
            if k in default:
                if data[k] == default[k]:
                    data.pop(k)

        return yaml.dump({'data': data}, Dumper=DeformerDumper, default_flow_style=False)

    def build(self, **kw):
        """Build the deformer node in the DCC application.

        Creates the actual deformer node and applies stored data.
        Must be implemented by software-specific subclasses.

        Args:
            **kw: Additional keyword arguments for deformer creation.

        Note:
            This is a placeholder. Override in subclasses.
        """

    def bind(self, modes=None, source=None):
        """Bind the deformer to the scene.

        Resolves node references, creates or updates the deformer node,
        and applies all stored data. Handles errors and logs status.

        Args:
            modes (set, optional): Active modes for binding behavior.
            source (str, optional): Source identifier for logging.

        Returns:
            int: Status code indicating result:
                - STATUS_DONE: Successfully bound or updated
                - STATUS_DELAY: Waiting for unresolved dependencies
                - STATUS_INVALID: Transform not found
                - STATUS_ERROR: DeformerError occurred
                - STATUS_CRASH: Unexpected exception occurred

        Examples:
            >>> status = dfm.bind(modes={'mirror'}, source='template.yml')
            >>> if status == Deformer.STATUS_DONE:
            ...     print('Deformer bound successfully')
        """
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
            self.post_build()

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
        """Update an existing deformer with current data.

        Called when binding to an already existing deformer node.
        Writes the current data to the node.
        """
        self.write()

    def parse_nodes(self):
        """Parse and resolve node references in deformer data.

        Resolves string identifiers to actual DCC nodes.
        Must be implemented by software-specific subclasses.

        Note:
            This is a placeholder. Override in subclasses.
        """

    def delay_parser(self):
        """Check if parsing should be delayed due to unresolved dependencies.

        Returns:
            bool: True if there are unresolved module or connection references.
        """
        if self.unresolved:
            for n in self.unresolved:
                if '::mod.' in n or '::!mod.' in n or '->' in n:
                    return True
        return False

    def find_root(self):
        """Find and set the root node for path resolution.

        Must be implemented by software-specific subclasses.

        Note:
            This is a placeholder. Override in subclasses.
        """

    def find_transform(self):
        """Find and set the transform node from transform_id.

        Must be implemented by software-specific subclasses.

        Note:
            This is a placeholder. Override in subclasses.
        """

    def find_node(self):
        """Find the deformer node by its ID.

        Searches for an existing deformer node matching this instance's ID.

        Returns:
            bool: True if the node was found and set, False otherwise.
        """
        if self.id and self.transform:
            geo_ids = self.get_ids()
            if self.id in geo_ids:
                self.node = geo_ids[self.id]
                return True
        return False

    def find_geometry(self):
        """Find and set the geometry shape node.

        Must be implemented by software-specific subclasses.

        Note:
            This is a placeholder. Override in subclasses.
        """

    @property
    def need_geometry(self):
        """Check if this deformer type requires geometry.

        Returns:
            bool: True if geometry is required (not a virtual deformer).
        """
        return not self.deformer_data.get('virtual', False)

    @staticmethod
    def get_deformer_ids(xfo, root=None):
        """Get all deformer IDs for a transform node.

        Args:
            xfo: Transform node to query.
            root: Optional root node for path resolution.

        Returns:
            dict: Mapping of deformer IDs to deformer nodes.

        Note:
            This is a placeholder. Override in subclasses.
        """
        return {}

    def get_ids(self):
        """Get all deformer IDs for this deformer's transform.

        Returns:
            dict: Mapping of deformer IDs to deformer nodes.
        """
        return self.get_deformer_ids(self.transform, self.root)

    def set_id(self):
        """Set a unique ID for this deformer on its node.

        Must be implemented by software-specific subclasses.

        Note:
            This is a placeholder. Override in subclasses.
        """

    def set_protected(self):
        """Mark this deformer as protected from modification.

        Must be implemented by software-specific subclasses.

        Note:
            This is a placeholder. Override in subclasses.
        """

    def post_build(self):
        """Update deformer after build

        Must be implemented by software-specific subclasses.

        Note:
            This is a placeholder. Override in subclasses.
        """

    def read(self):
        """Read deformer data from the DCC node.

        Populates self.data with information from the deformer node.
        Must be implemented by software-specific subclasses.

        Note:
            This is a placeholder. Override in subclasses.
        """

    def read_deformer(self):
        """Read and round deformer data.

        Convenience method that reads data and applies rounding to weights.
        """
        self.read()
        self.round()

    def get_size(self):
        """Get the number of points affected by this deformer.

        Returns:
            int: Number of vertices/CVs in the deformed geometry.
        """
        return 0

    def write(self):
        """Write deformer data to the DCC node.

        Applies stored data to the deformer node.
        Must be implemented by software-specific subclasses.

        Note:
            This is a placeholder. Override in subclasses.
        """

    @staticmethod
    def hook(dfm, xfo, hook):
        """Create a connection hook for deformer chaining.

        Args:
            dfm: Deformer to hook.
            xfo: Transform node.
            hook: Hook specification.

        Note:
            This is a placeholder. Override in subclasses.
        """

    @staticmethod
    def get_hook_id(plug, xfo=None):
        """Get the hook identifier for a connection plug.

        Args:
            plug: Connection plug to identify.
            xfo: Optional transform for context.

        Returns:
            str: Hook identifier string.

        Note:
            This is a placeholder. Override in subclasses.
        """

    def create_weightmap(self, wm, **data):
        """Create a WeightMapInterface for managing weights.

        Args:
            wm (WeightMap, optional): Existing weight map or None to create empty.
            **data: Additional data to pass to the interface.

        Returns:
            WeightMapInterface: Interface wrapping the weight map.

        Examples:
            >>> wmi = dfm.create_weightmap(None)
            >>> wmi = dfm.create_weightmap(existing_wm, name='mask')
        """
        if wm is None:
            n = self.get_size()
            wm = WeightMap([0.0] * n)
        return WeightMapInterface(wm, **data)

    def get_weightmaps(self):
        """Get all weight maps from the deformer.

        Returns:
            list: List of WeightMapInterface objects.

        Note:
            This is a placeholder. Override in subclasses.
        """
        return []

    def set_weightmaps(self, maps):
        """Set weight maps on the deformer.

        Args:
            maps (list): List of WeightMapInterface objects to apply.

        Note:
            This is a placeholder. Override in subclasses.
        """

    def get_indexed_maps(self):
        """Get weight maps indexed by integer keys.

        Returns:
            tuple: (ids, maps) where ids is a sorted list of integer indices
                and maps is the corresponding list of WeightMap objects.

        Examples:
            >>> ids, maps = dfm.get_indexed_maps()
            >>> for idx, wm in zip(ids, maps):
            ...     print(f'Map {idx}: {len(wm)} weights')
        """
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
        """Remap indexed maps to contiguous indices starting from 0.

        Useful after removing influences to compact the index space.
        Also remaps related data like infs, bind_pose, and bind_pose_root.
        """
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

    def normalize(self, only_excess=False, tolerance=1e-6):
        """Normalize weight maps so weights sum to 1.0 per vertex.

        Args:
            only_excess (bool): If True, only normalize vertices where weight sum exceeds 1.0.
                If False, normalize all vertices.
            tolerance (float): The acceptable margin of error for floating-point comparisons.

        Examples:
            >>> dfm.normalize()  # Normalize all
            >>> dfm.normalize(only_excess=True)  # Only fix over-weighted
        """
        ids, maps = self.get_indexed_maps()

        if has_numpy:
            if isinstance(maps[0].weights, np.ndarray):
                weight_matrix = np.vstack([m.weights for m in maps]).astype(np.float64, copy=False)
            else:
                flat_stream = itertools.chain.from_iterable(m.weights for m in maps)
                weight_matrix = np.fromiter(flat_stream, dtype=np.float64, count=len(maps) * len(maps[0].weights)).reshape(len(maps), -1)

            sums = np.sum(weight_matrix, axis=0)
            divisors = np.where(sums == 0, 1.0, sums)

            if only_excess:
                divisors = np.where(sums > (1.0 + tolerance), divisors, 1.0)

            weight_matrix /= divisors
            for i, m in enumerate(maps):
                m.weights = weight_matrix[i]

        else:
            weights = list(zip(*[x.weights for x in maps]))

            for i, w in enumerate(weights):
                s = sum(w)
                if s == 0 or (only_excess and s <= (1.0 + tolerance)):
                    continue
                weights[i] = tuple(x / s for x in w)

            for m, w_transposed in zip(maps, zip(*weights)):
                m.weights = list(w_transposed)

    def round(self):
        """Round weight values to the configured decimal precision.

        Applies rounding while maintaining weight normalization by
        distributing rounding error to the largest delta value.
        """
        ids, maps = self.get_indexed_maps()
        if not maps:
            return

        if has_numpy and isinstance(maps[0].weights, np.ndarray):
            w = np.array([m.weights for m in maps], dtype=np.float32)
            r = np.round(w, self.decimals)

            s = np.round(np.sum(w, axis=0), self.decimals)
            s_r = np.round(np.sum(r, axis=0), self.decimals)

            delta = np.round(s - s_r, self.decimals)
            diff = w - r
            v_indices = np.arange(w.shape[1])

            mask_pos = delta > 0
            if np.any(mask_pos):
                v_pos = v_indices[mask_pos]
                idx_max = np.argmax(diff[:, v_pos], axis=0)
                r[idx_max, v_pos] += delta[mask_pos]

            mask_neg = delta < 0
            if np.any(mask_neg):
                v_neg = v_indices[mask_neg]
                idx_min = np.argmin(diff[:, v_neg], axis=0)
                r[idx_min, v_neg] += delta[mask_neg]

            r = np.round(r, self.decimals)
            for i, m in enumerate(maps):
                m.weights = r[i]

        else:
            decimals = self.decimals
            weights_per_vert = zip(*[m.weights for m in maps])
            new_weights = []

            for w in weights_per_vert:
                s = round(sum(w), decimals)
                r = [round(x, decimals) for x in w]

                delta = round(s - sum(r), decimals)
                if delta != 0:
                    d = [orig - rnd for orig, rnd in zip(w, r)]
                    if delta > 0:
                        idx = d.index(max(d))
                    else:
                        idx = d.index(min(d))

                    r[idx] = round(r[idx] + delta, decimals)

                new_weights.append(r)

            for i, col in enumerate(zip(*new_weights)):
                maps[i].weights = list(col)


class DeformerError(Exception):
    """Exception raised for deformer-related errors.

    Raised when a deformer operation fails in an expected way,
    such as missing geometry or invalid configuration.

    Examples:
        >>> raise DeformerError('Geometry not found for skinCluster')
    """


Deformer.get_all_modules()

RLE_PATTERN = re.compile(r'([0-9.eE+-]+)(?:\*(\d+))?')


class WeightMap(object):
    """Container for vertex weight data with compression support.

    Stores per-vertex weight values and provides serialization using
    run-length encoding (RLE) with optional zlib compression.

    Attributes:
        weights (list): List of weight values (float or int).
        lock (bool): Whether this weight map is locked from editing.
        partition (str): Partition identifier for weight partitioning.

    Examples:
        Creating from a list:
            >>> wm = WeightMap([1.0, 0.5, 0.0, 0.0, 0.5, 1.0])

        Creating from encoded string:
            >>> encoded = wm.encode()
            >>> wm2 = WeightMap(encoded)

        Weight map arithmetic:
            >>> wm1 = WeightMap([1.0, 0.5, 0.0])
            >>> wm2 = WeightMap([0.5, 0.5, 0.5])
            >>> result = wm1 * wm2  # Element-wise multiply
            >>> result = wm1 + wm2  # Element-wise add
    """

    def __init__(self, weights, lock=False, partition=None):
        """Initialize a WeightMap.

        Args:
            weights (list or str): Weight values as a list of numbers,
                or an encoded string from encode().
            lock (bool): Whether to lock this weight map.
            partition (str, optional): Partition identifier.
        """
        if isinstance(weights, string_types):
            self.decode(weights)
        else:
            # always copy weights when new
            if has_numpy and isinstance(weights, np.ndarray):
                self.weights = np.copy(weights)
            else:
                self.weights = list(weights)

        self.lock = lock
        self.partition = partition

    def __getitem__(self, i):
        """Get weight value at index.

        Args:
            i (int): Vertex index.

        Returns:
            float: Weight value at the index.
        """
        return self.weights[i]

    def __setitem__(self, i, value):
        """Set weight value at index.

        Args:
            i (int): Vertex index.
            value (float): Weight value to set.
        """
        self.weights[i] = value

    def copy(self):
        """Create a copy of this weight map.

        Returns:
            WeightMap: New weight map with copied data.
        """
        return WeightMap(self.weights, lock=self.lock, partition=self.partition)

    def encode(self, decimals=6, compress=True, max_rle_groups=16, mask=False):
        """Encode weight map to a string representation.

        Uses run-length encoding (RLE) with optional zlib compression
        for efficient storage of weight data.

        Args:
            decimals (int): Number of decimal places for rounding.
            compress (bool): Whether to apply zlib compression for long strings.
            max_rle_groups (int): Maximum packet values to serialize with rle encoding before compression.

        Returns:
            str: Encoded weight map string (RLE or base64-compressed).

        Examples:
            >>> wm = WeightMap([1.0, 1.0, 1.0, 0.5, 0.0])
            >>> wm.encode()
            '1*3 0.5 0'
        """
        wm = self.weights
        if not mask:
            if has_numpy:
                wm = np.round(wm, decimals)
            else:
                wm = list(map(lambda w: round(w, decimals), wm))

        # check complexity
        do_binary = False

        groups = []
        groups_append = groups.append
        for val, group in itertools.groupby(wm):
            groups_append((val, sum(1 for _ in group)))
            if len(groups) > max_rle_groups:
                do_binary = True
                break

        # serialize
        if do_binary and compress:
            if mask:
                if has_numpy:
                    raw_bin = b'msk:' + np.array(wm, dtype=np.uint8).tobytes()
                else:
                    wm_ints = [int(v) for v in wm]
                    raw_bin = b'msk:' + struct.pack('<{}B'.format(len(wm)), *wm_ints)
            else:
                if has_numpy:
                    raw_bin = b'f32:' + np.array(wm, dtype=np.float32).tobytes()
                else:
                    raw_bin = b'f32:' + struct.pack('<{}f'.format(len(wm)), *wm)

            return base64.b64encode(zlib.compress(raw_bin, 1)).decode('ascii')

        # rle encoding
        rle_data = [
            (val, sum(1 for _ in group))
            for val, group in itertools.groupby(wm)
        ]

        parts = []
        for val, count in rle_data:
            s_val = '{0:.{1}f}'.format(val, decimals).rstrip('0').rstrip('.')
            if not s_val:
                s_val = '0'
            if count > 1:
                parts.append('{0}*{1}'.format(s_val, count))
            else:
                parts.append(s_val)

        return ' '.join(parts)

    def decode(self, data):
        """Decode weight map from a string representation.

        Handles both RLE format and base64-compressed data.

        Args:
            data (str): Encoded weight map string.

        Examples:
            >>> wm = WeightMap.__new__(WeightMap)
            >>> wm.decode('1*3 0.5 0')
            >>> wm.weights
            [1, 1, 1, 0.5, 0]
        """
        self.weights = []
        if not data:
            return

        raw_data = None
        if data[0] == 'e':
            try:
                raw_data = zlib.decompress(base64.b64decode(data))
            except:
                pass

        if raw_data:
            # float32
            if raw_data.startswith(b'f32:'):
                payload = raw_data[4:]
                count = len(payload) // 4
                self.weights = list(struct.unpack('<{}f'.format(count), payload))
                return

            # mask
            elif raw_data.startswith(b'msk:'):
                payload = raw_data[4:]
                count = len(payload)
                unpacked = struct.unpack('<{}B'.format(count), payload)
                self.weights = [int(v) for v in unpacked]
                return

            # legacy RLE
            else:
                raw_data = raw_data.decode('ascii')
        else:
            # RLE
            raw_data = data

        # unpack RLE
        weights_extend = self.weights.extend
        weights_append = self.weights.append

        for match in RLE_PATTERN.finditer(raw_data):
            val_str, count_str = match.groups()
            val = float(val_str)

            if count_str:
                weights_extend([val] * int(count_str))
            else:
                weights_append(val)

    def normalize(self):
        """Normalize weights to range [0, 1] based on maximum value.

        Scales all weights so the maximum becomes 1.0.
        """
        f = 1. / max(self.weights)
        for i in range(len(self.weights)):
            self.weights[i] *= f

    def mirror(self, sym, direction=1):
        """Mirror weights using symmetry mapping.

        Args:
            sym (dict): Symmetry mapping with direction keys.
            direction (int): Direction of mirror (1 or -1).
        """
        for i in sym[direction]:
            j = sym[direction][i]
            self.weights[j] = self.weights[i]

    def flip(self, sym):
        """Flip weights across symmetry axis.

        Args:
            sym (dict): Symmetry mapping.
        """
        for i in sym[1]:
            j = sym[1][i]
            self.weights[i], self.weights[j] = self.weights[j], self.weights[i]

    def __len__(self):
        """Get the number of weights.

        Returns:
            int: Number of weight values.
        """
        return len(self.weights)

    def __mul__(self, other):
        """Multiply weights element-wise.

        Args:
            other (WeightMap or float): Value to multiply by.

        Returns:
            WeightMap: New weight map with multiplied values.

        Raises:
            RuntimeError: If weight maps have different lengths.
        """
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
        """Add weights element-wise.

        Args:
            other (WeightMap or float): Value to add.

        Returns:
            WeightMap: New weight map with added values.

        Raises:
            RuntimeError: If weight maps have different lengths.
        """
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
        """Subtract weights element-wise.

        Args:
            other (WeightMap or float): Value to subtract.

        Returns:
            WeightMap: New weight map with subtracted values.

        Raises:
            RuntimeError: If weight maps have different lengths.
        """
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
    """Interface for managing weight map nodes in DCC applications.

    Wraps a WeightMap with additional metadata and tracks modifications.

    Attributes:
        weightmap (WeightMap): The underlying weight map data.
        data (dict): Additional metadata (name, node reference, etc.).
        modified (bool): Whether the weight map has been modified.

    Examples:
        >>> wmi = WeightMapInterface(WeightMap([1.0, 0.5, 0.0]), name='mask')
        >>> wmi.weightmap[0] = 0.8
        >>> wmi.modified = True
    """

    def __init__(self, wm, **data):
        """Initialize a WeightMapInterface.

        Args:
            wm (WeightMap): The weight map to wrap.
            **data: Additional metadata to store.
        """
        self.weightmap = wm
        self.data = data

        self.modified = False

    def get_node(self):
        """Get the DCC node associated with this weight map.

        Returns:
            Node reference or None.

        Note:
            This is a placeholder. Override in subclasses.
        """


class DeformerDumper(YamlDumper):
    """Custom YAML dumper for deformer data serialization.

    Handles WeightMap serialization using the !weightmap tag.
    """


class DeformerLoader(YamlLoader):
    """Custom YAML loader for deformer data deserialization.

    Handles WeightMap deserialization from the !weightmap tag.
    """


def _weight_map_representer(dumper, data):
    """YAML representer for WeightMap objects.

    Args:
        dumper: YAML dumper instance.
        data (WeightMap): Weight map to serialize.

    Returns:
        YAML scalar node with !weightmap tag.
    """
    return dumper.represent_scalar('!weightmap', data.encode(), style='plain')


def _weight_map_constructor(loader, node):
    """YAML constructor for WeightMap objects.

    Args:
        loader: YAML loader instance.
        node: YAML node to deserialize.

    Returns:
        WeightMap: Deserialized weight map.
    """
    value = loader.construct_scalar(node)
    return WeightMap(value)


DeformerDumper.add_representer(WeightMap, _weight_map_representer)
DeformerLoader.add_constructor('!weightmap', _weight_map_constructor)
