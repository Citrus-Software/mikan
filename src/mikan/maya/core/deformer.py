# coding: utf-8

"""Maya Deformer Management Module.

This module provides a comprehensive framework for managing deformers in Maya,
including reading, writing, transferring weights, and organizing deformer data.
It serves as the base implementation for Maya-specific deformers in the mikan rigging system.

The module supports:
    - Deformer data serialization and deserialization
    - Weight map management and transfer
    - Deformer layering and grouping
    - NURBS-based weight mapping
    - Cross-geometry weight transfer

Classes:
    Deformer: Main class for individual deformer management.
    DeformerGroup: Container for managing multiple deformers as a group.
    WeightMapInterface: Interface for weight map node management.
    NurbsWeightMap: NURBS-based weight mapping system.

Examples:
    Creating a deformer from an existing Maya node:
        >>> dfm = Deformer.create(geometry, deformer_node, read=True)
        >>> dfm.read_deformer()

    Creating a deformer group from selected geometries:
        >>> group = DeformerGroup.create(selected_nodes, read=True)
        >>> group.write()

    Transferring weights between geometries:
        >>> new_dfm = dfm.transfer(target_geometry, mirror=True, axis='x')
"""

import uuid
import yaml
import time
import traceback
from copy import deepcopy
from six.moves import range
from six import string_types, iteritems

import maya.OpenMaya as om1
import maya.api.OpenMaya as om
import maya.api.OpenMayaAnim as oma
from mikan.maya import cmdx as mx
import maya.cmds as mc

from mikan.core import abstract, re_is_float, longest_common_suffix, longest_common_prefix
from mikan.core.abstract.deformer import DeformerError
from mikan.core.logger import create_logger, timed_code
from mikan.core.tree import SuperTree
from mikan.core.utils import ordered_load
from mikan.core.utils.mathutils import SplineRemap, NurbsCurveRemap, NurbsSurfaceRemap
from .node import Nodes, parse_nodes
from ..lib.configparser import ConfigParser
from ..lib.geometry import create_mesh_copy, create_lattice_proxy

__all__ = [
    'WeightMap', 'Deformer', 'DeformerGroup', 'WeightMapInterface', 'DeformerError',
    'NurbsWeightMap'
]

WeightMap = abstract.WeightMap

log = create_logger()


class Deformer(abstract.Deformer):
    """Maya-specific deformer management class.

    This class provides a complete interface for managing Maya deformers,
    including reading/writing deformer data, weight maps, membership, and connectivity.
    It inherits from abstract.Deformer and implements Maya-specific functionality.

    Attributes:
        deformer (str): Type of deformer (e.g., 'skin', 'blendShape', 'cluster').
        transform (mx.Node): Transform node being deformed.
        transform_id (str): Unique identifier for the transform.
        node (mx.Node): The deformer node itself.
        id (str): Unique identifier for this deformer instance.
        geometry (mx.Node): The shape node being deformed.
        geometry_id (str): Unique identifier for the geometry.
        root (mx.Node): Root node for path resolution.
        data (dict): Dictionary containing all deformer data (weights, maps, etc.).
        protected (bool): Whether this deformer is protected from modification.
        order (str): Deformer stack order ('default', 'front', 'isolated').
        input (tuple): Input connection (node, transform).
        input_id (str): Identifier for input connection.
        output (tuple): Output connection (node, transform).
        output_id (str): Identifier for output connection.
        decimals (int): Precision for weight values.
        ini (ConfigParser): Configuration parser for data storage.
        unresolved (list): List of unresolved node references.
        priority (int): Evaluation priority for the deformer.

    Examples:
        Create a deformer from existing Maya nodes:
            >>> geo = mx.encode('pSphere1')
            >>> skin_node = mx.encode('skinCluster1')
            >>> dfm = Deformer.create(geo, skin_node, read=True)

        Create a deformer from stored data:
            >>> data = {
            ...     'deformer': 'skin',
            ...     'transform': 'pSphere1',
            ...     'data': {'maps': {}, 'infs': {}}
            ... }
            >>> dfm = Deformer(**data)
            >>> dfm.build()

        Transfer deformer to another geometry:
            >>> target = mx.encode('pSphere2')
            >>> new_dfm = dfm.transfer(target, mirror=True, axis='x')

    Note:
        When creating custom deformers, inherit from this class and override:
        - node_class: Maya node type constant
        - read(): Method to read deformer-specific data
        - write(): Method to write deformer-specific data
        - build(): Method to create the deformer node
    """

    software = 'maya'

    shape_types = (
        mx.tMesh,
        mx.tNurbsCurve,
        mx.tLattice,
        mx.tNurbsSurface
    )

    def __repr__(self):
        if self.transform or self.transform_id:
            if self.transform:
                node_name = Deformer.get_unique_name(self.transform, root=self.root)
            else:
                node_name = self.transform_id
            if self.id:
                return "Deformer('{}', id='{}', transform='{}')".format(self.deformer, self.id, node_name)
            else:
                return "Deformer('{}', transform='{}')".format(self.deformer, node_name)
        else:
            return "Deformer('{}')".format(self.deformer)

    def __eq__(self, other):
        if isinstance(other, Deformer):
            return self.node == other.node
        return False

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return self.node.__hash__() ^ hash(Deformer)

    @classmethod
    def is_node(cls, node):
        """Check if a node is a valid deformer of the type Deformer.node_class.

        Args:
            node (mx.Node or str): Node to check.

        Returns:
            bool: True if node is a valid deformer type.
        """
        if not isinstance(node, mx.Node):
            node = mx.encode(str(node))
        if cls.node_class and node.is_a(cls.node_class):
            return True
        return False

    def encode_data(self):
        """Encode deformer data to YAML string format.

        Serializes all deformer information including transform, ID, geometry, order, connections,
        and protection status into a YAML-formatted string suitable for storage.

        Returns:
            str: YAML-formatted string containing all deformer data.

        Examples:
            >>> data_str = dfm.encode_data()
            >>> print(data_str)
            #!100
            deformer: skin
            transform: pSphere1
            id: skin.0
            ...
        """
        data = 'deformer: {}\n'.format(self.deformer)

        if self.transform:
            node_name = self.get_unique_name(self.transform, self.root)
            data += 'transform: {}\n'.format(node_name)
        elif self.transform_id:
            data += 'transform: {}\n'.format(self.transform_id)

        if self.node:
            data += 'id: {}\n'.format(self.set_id())
        elif self.id:
            data += 'id: {}\n'.format(self.id)

        if self.geometry_id:
            data += 'geometry_id: {}\n'.format(self.geometry_id)

        if self.order and self.order != 'default':
            data += 'order: {}\n'.format(self.order)
        if self.input_id:
            data += 'input_id: {}\n'.format(self.input_id)
        if self.output_id:
            data += 'output_id: {}\n'.format(self.output_id)

        if self.protected:
            data += 'protected: true\n'
        if self.decimals != self.default_decimals:
            data += 'decimals: {}\n'.format(self.decimals)

        data += self.encode_deformer_data()

        try:
            data = '#!{}\n{}'.format(self.priority, data)
        except:
            pass

        return data

    def update_ini(self):
        """Update the backup node with current deformer data.

        Writes the current state of the deformer back to its associated configuration parser (from backup node),
        preserving comments.
        """
        if self.ini is None:
            return

        data = self.encode_data()

        lines = self.ini.get_lines()
        lines = [l for l in lines if l.strip().startswith('#')]
        data = '\n'.join(lines) + '\n' + data

        self.ini.write(data)

    @classmethod
    def parse(cls, ini):
        """Parse deformer data from configuration section.

        Args:
            ini (ConfigParser or str): Configuration section or raw YAML string.

        Returns:
            dict: Parsed deformer data dictionary.

        Examples:
            >>> cfg = ConfigParser(node)
            >>> ini = cfg['deformer'][0]
            >>> data = Deformer.parse(ini)
            >>> dfm = Deformer(**data)
        """
        # get data
        root = None
        if ConfigParser.is_section(ini):
            raw_data = ini.read()

            node = ini.parser.node
            while node:
                if 'gem_deformers' in node:
                    root = node['gem_deformers'].read()
                    break
                else:
                    node = node.parent()
        else:
            raw_data = str(ini)

        data = yaml.load(raw_data, abstract.DeformerLoader)
        if root:
            data['root'] = root

        if ConfigParser.is_section(ini):
            data['ini'] = ini

        return data

    def parse_root(self, namespace=None):
        if self.root is None and self.root_id:
            try:
                node = Deformer.get_node(self.root_id, namespace=namespace)
            except:
                return False

            self.root = node
        return True

    def parse_transform(self, namespace=None):
        if self.transform is None and self.transform_id:
            try:
                node = Deformer.get_node(self.transform_id, root=self.root, namespace=namespace)
            except:
                return False

            self.transform = node
        return True

    def parse_nodes(self):
        """Resolve all node references in deformer data.

        Attempts to resolve all string node references (root, transform, input, output) to actual Maya node objects.
        Unresolved references are added to the unresolved list.

        Note:
            This method is typically called after loading deformer data from storage
            but before building or updating the deformer.
        """
        del self.unresolved[:]

        # get root
        if not self.parse_root():
            self.unresolved.append(self.root_id)

        # get transform (check under group root if any)
        self.parse_transform()

        # parse input/output
        if self.input_id:
            try:
                node, xfo = self.get_geometry_id(self.input_id, root=self.root)
            except:
                node = None
                xfo = None
            if node is not None:
                self.input = node, xfo
            else:
                self.unresolved.append(self.input_id)

        if self.output_id:
            try:
                node, xfo = self.get_geometry_id(self.output_id, root=self.root)
            except:
                node = None
                xfo = None
            if node is not None:
                self.output = node, xfo
            else:
                self.unresolved.append(self.output_id)

        # parse data
        self.data = parse_nodes(self.data, failed=self.unresolved, exclude=self.get_parser_excluded_keys(), root=self.root)

    def update_transform(self, transform=None):
        """Update the target transform for this deformer.

        Changes the deformer's target geometry and resets all cached node
        references. This is useful when retargeting a deformer to a different
        piece of geometry.

        Args:
            transform (mx.Node or str, optional): New transform node. If None, resets to None.
        """
        if transform is not None and not isinstance(transform, mx.Node):
            transform = mx.encode(str(transform))

        self.node = None
        self.id = None

        self.transform = transform
        self.transform_id = None
        self.geometry = None
        self.geometry_id = None
        self.output = None, None
        self.output_id = None
        self.input = None, None
        self.input_id = None

    def read_deformer(self):
        """Read all deformer data from the Maya scene.

        Reads membership, deformer-specific data, and rounds values to the specified precision.
        This is the main entry point for extracting deformer information from an existing Maya deformer node.

        Examples:
            >>> dfm = Deformer.create(geo, skin_node, read=False)
            >>> dfm.read_deformer()
            >>> print(len(dfm.data['maps']))
        """
        self.read_membership()
        self.read()
        self.round()

    @staticmethod
    def create(geo, deformer, root=None, read=True):
        """Create a Deformer instance from existing Maya nodes.

        Factory method that creates the appropriate Deformer subclass instance based on the deformer node type.
        Automatically determines the correct geometry and validates the deformer connection.

        Args:
            geo (mx.Node or str): Geometry transform or shape node.
            deformer (mx.Node or str): Deformer node.
            root (mx.Node or str, optional): Root node for path resolution.
            read (bool): If True, immediately read deformer data from scene.

        Returns:
            Deformer: Instance of appropriate Deformer subclass.

        Raises:
            RuntimeError: If geometry type is invalid or deformer is not connected to the specified geometry.

        Examples:
            >>> dfm = Deformer.create('pSphere1', 'skinCluster1', read=True)
            >>> print(dfm.deformer)
            skin
        """
        if not isinstance(geo, mx.Node):
            geo = mx.encode(str(geo))
        if not isinstance(deformer, mx.Node):
            deformer = mx.encode(str(deformer))

        cls = Deformer.get_cls_from_node(deformer)
        if cls:
            shp = None
            if geo.is_a(mx.tTransform):
                xfo = geo
                for _shp in geo.shapes():
                    if not _shp['io'].read():
                        shp = _shp
                        break
            else:
                shp = geo
                xfo = shp.parent()

            if not shp.is_a(Deformer.shape_types):
                raise RuntimeError('"{0}" is not a valid geometry'.format(geo))
            if not deformer.is_a((mx.kGeometryFilter, mx.kPolyModifier)):
                raise RuntimeError('"{0}" is not a valid deformer'.format(deformer))

            history = mc.listHistory(str(shp)) or []
            if str(deformer) not in history:
                raise RuntimeError('"{0}" is not a deformer of "{1}"'.format(deformer, shp))

            data = {
                'deformer': cls.__module__.split('.')[-2],
                'transform': xfo,
                'node': deformer
            }

            if root:
                data['root'] = root
            dfm = Deformer(**data)
            dfm.set_id()
            if read:
                dfm.read_deformer()
            return dfm

    def update(self):
        """Write all deformer data back to the Maya scene.

        Updates the Maya deformer node with the current data stored in this instance,
        including membership and deformer-specific attributes.

        Examples:
            >>> dfm.data['maps'][0].weights[10] = 0.5
            >>> dfm.update()
        """
        self.write_membership()
        self.write()

    def reorder(self):
        """Reorder the deformer in the deformation stack.

        Adjusts the deformer's position in the deformation chain based on the order attribute ('front', 'isolated', or default).
        Handles reconnecting input/output plugs as needed.

        Note:
            Requires order, input, and output to be set.
            Called internally during deformer build.
        """
        if any(filter(lambda x: x is None, (self.order, self.output[0], self.input[0]))):
            return

        plug_out = self.get_output()
        plug_dst = plug_out.output(plug=True)

        plug_in = self.get_input()
        plug_src = plug_in.input(plug=True)

        if self.order == 'isolated':
            plug_src >> plug_dst

        elif self.order == 'front':
            node_src = Deformer._get_deformed_geo(self.node, self.transform, source=True)
            plug_src = Deformer.get_deformer_output(node_src, self.transform)
            plug_src >> plug_in

        node, xfo = self.output
        if node is not None:
            # reconnect source to disconnected stream
            plug_src >> plug_dst

        node, xfo = self.input
        if node is not None:
            if isinstance(node, mx.Node) and (node.is_a(mx.kGeometryFilter) or node.is_a(Deformer.shape_types)):
                Deformer.get_deformer_output(node, xfo) >> plug_in
            elif isinstance(node, mx.Plug):
                node >> plug_in

        node, xfo = self.output
        if node is not None:
            if isinstance(node, mx.Node) and (node.is_a(mx.kGeometryFilter) or node.is_a(Deformer.shape_types)):
                plug_out >> Deformer.get_deformer_input(node, xfo)
            elif isinstance(node, mx.Plug):
                plug_out >> node

    @staticmethod
    def get_geo_deformers(geo, mikan=True, check=False):
        """Get all deformers affecting a geometry.

        Retrieves all deformer nodes in the geometry's history,
        optionally filtering to only mikan-compatible deformers.

        Args:
            geo (mx.Node or str): Geometry node to query.
            mikan (bool): If True, only return mikan-compatible deformers.
            check (bool): If True, validate that deformers have members.

        Returns:
            list: List of deformer nodes (mx.Node).
        """
        # get all valid mikan deformers from history
        if not isinstance(geo, mx.Node):
            geo = mx.encode(str(geo))

        deformers = []

        shp = None
        for _shp in geo.shapes():
            if not _shp['io'].read():
                shp = _shp
                break

        if shp:
            history = mc.listHistory(str(shp)) or []
            history = mc.ls(history, type=('geometryFilter', 'polyModifier'))[::-1]
            history = [mx.encode(x) for x in history]

            for deformer in history:

                if deformer.is_a(mx.kGeometryFilter):
                    fn = oma.MFnGeometryFilter(deformer.object())
                    orig = [mx.Node(x) for x in fn.getInputGeometry()]
                    orig_geos = [_shp.parent() for _shp in orig]
                    if geo not in orig_geos:
                        continue

                    if check and not Deformer.get_deformer_members(deformer, shp):  # check validity
                        continue

                else:
                    orig = mc.ls(mc.listHistory(str(deformer)), type='deformableShape')
                    orig_geos = [mx.encode(_shp).parent() for _shp in orig]
                    if geo not in orig_geos:
                        continue

                if mikan:
                    cls = Deformer.get_cls_from_node(deformer)
                    if cls and deformer not in deformers:
                        deformers.append(deformer)
                else:
                    deformers.append(deformer)

        return deformers

    @staticmethod
    def _get_deformed_geo(node, transform, source=False):
        if not isinstance(node, mx.Node):
            node = mx.encode(str(node))
        if not isinstance(transform, mx.Node):
            transform = mx.encode(str(transform))

        if node.is_a(mx.kGeometryFilter):
            fn = oma.MFnGeometryFilter(node.object())
            if not source:
                for shape in fn.getOutputGeometry():
                    shape = mx.Node(shape)
                    if shape.parent() == transform:
                        return shape
            else:
                for shape in fn.getInputGeometry():
                    shape = mx.Node(shape)
                    if shape.parent() == transform:
                        return shape

        elif node.is_a(mx.kPolyModifier):
            ids = Deformer.get_deformer_ids(transform)
            if source and 'source' in ids and ids['source'].is_a(mx.tMesh):
                return ids['source']
            elif 'shape' in ids and ids['source'].is_a(mx.tMesh):
                return ids['shape']

        elif node.is_a(Deformer.shape_types):
            return node

        log.error('cannot find deformed geo for {}/{}'.format(node, transform))

    @staticmethod
    def get_deformer_output(node, transform):
        """Get the output plug of a deformer or geometry node.

        Args:
            node (mx.Node or str): Deformer or geometry node.
            transform (mx.Node or str): Transform node for context.

        Returns:
            mx.Plug: Output plug of the node.
        """
        if not isinstance(node, mx.Node):
            node = mx.encode(str(node))
        if not isinstance(transform, mx.Node):
            transform = mx.encode(str(transform))

        shape = Deformer._get_deformed_geo(node, transform)
        if not shape:
            return
        if node.is_a(mx.kGeometryFilter):
            io = shape['io'].read()
            if io:
                shape['io'] = False
            fn = oma.MFnGeometryFilter(node.object())
            i = int(fn.indexForOutputShape(shape.object()))
            if io:
                shape['io'] = True
            return node['outputGeometry'][i]
        elif node.is_a(mx.kPolyModifier):
            return node['output']
        elif node.is_a(Deformer.shape_types):
            if node.is_a(mx.tMesh):
                return node['worldMesh'][0]
            elif node.is_a((mx.tNurbsCurve, mx.tNurbsSurface)):
                if node['worldSpace'][0].output() is not None:
                    return node['worldSpace'][0]
                return node['local']

        log.error('cannot find deformer output of {}/{}'.format(node, transform))

    @staticmethod
    def get_deformer_input(node, transform):
        """Get the input plug of a deformer or geometry node.

        Args:
            node (mx.Node or str): Deformer or geometry node.
            transform (mx.Node or str): Transform node for context.

        Returns:
            mx.Plug: Input plug of the node.
        """
        if not isinstance(node, mx.Node):
            node = mx.encode(str(node))
        if not isinstance(transform, mx.Node):
            transform = mx.encode(str(transform))

        shape = Deformer._get_deformed_geo(node, transform)
        if not shape:
            return

        if node.is_a(mx.kGeometryFilter):
            io = shape['io'].read()
            if io:
                shape['io'] = False
            fn = oma.MFnGeometryFilter(node.object())
            i = int(fn.indexForOutputShape(shape.object()))
            if io:
                shape['io'] = True
            gid = node['input'][i]['groupId'].input(plug=True)
            if gid:
                gp = gid.output(type=mx.tGroupParts)
                if gp:
                    return gp['inputGeometry']
            return node['input'][i]['inputGeometry']

        elif node.is_a(mx.kPolyModifier):
            return node['inputPolymesh']

        elif node.is_a(Deformer.shape_types):
            if node.is_a(mx.tMesh):
                return node['inMesh']
            elif node.is_a((mx.tNurbsCurve, mx.tNurbsSurface)):
                return node['create']

        log.error('cannot find deformer input of {}/{}'.format(node, transform))

    @staticmethod
    def get_input_id(plug):
        """Get the deformer ID from a plug's input connection.

        Traverses the input connection chain to find the source deformer or geometry and returns its identifier string.

        Args:
            plug (mx.Plug): Plug to trace input from.

        Returns:
            str or None: Identifier string in format 'transform->id', or None.

        Examples:
            >>> plug = skin_node['input'][0]['inputGeometry']
            >>> input_id = Deformer.get_input_id(plug)
            >>> print(input_id)
            pSphere1->source
        """
        # get deformer id from given plug input
        if not isinstance(plug, mx.Plug):
            raise ValueError('invalid plug given ({})'.format(plug))

        plug_in = plug.input(plug=True)
        if not isinstance(plug_in, mx.Plug):
            return

        node = plug_in.node()
        cls = Deformer.get_cls_from_node(node)

        if node.is_a(mx.tGroupParts):
            return Deformer.get_input_id(node['inputGeometry'])

        elif node.is_a(Deformer.shape_types):
            xfo = node.parent()
            _xfo = Deformer.get_unique_name(xfo)

            # check assigned id
            for k, v in iteritems(Deformer.get_deformer_ids(xfo)):
                if node == v:

                    if 'layer.' in k:
                        # bypass deformer editing layer
                        plug_in = Deformer.get_deformer_input(node, xfo)
                        return Deformer.get_input_id(plug_in)

                    return '{}->{}'.format(_xfo, k)

        else:
            # check if deformer output
            if node.is_a(mx.kGeometryFilter) and plug_in.name().startswith('outputGeometry'):
                fn = oma.MFnGeometryFilter(node.object())
                shape_index = plug_in.plug().logicalIndex()
                shape_in = fn.inputShapeAtIndex(shape_index)
                shape_in = mx.Node(shape_in)
                xfo = shape_in.parent()
                _xfo = Deformer.get_unique_name(xfo)

                if cls:
                    for k, v in iteritems(Deformer.get_deformer_ids(xfo)):
                        if node == v:
                            return '{}->{}'.format(_xfo, k)

                    log.debug('/!\\ deformer "{}" has not been registered yet'.format(node))
                    return

                # traverse input graph if not mikan deformer
                return Deformer.get_input_id(node['input'][shape_index]['inputGeometry'])

            # check hook
            if cls:
                hook_id = cls.get_hook_id(plug_in)
                if hook_id:
                    return hook_id

        log.debug('/!\\ no deformer input id from "" found'.format(plug))

    @staticmethod
    def get_output_id(plug):
        """Get the deformer ID from a plug's output connection.

        Traverses the output connection chain to find the destination deformer or geometry and returns its identifier string.

        Args:
            plug (mx.Plug): Plug to trace output from.

        Returns:
            str or None: Identifier string in format 'transform->id', or None.

        Examples:
            >>> plug = skin_node['outputGeometry'][0]
            >>> output_id = Deformer.get_output_id(plug)
            >>> print(output_id)
            pSphere1->shape
        """
        # get deformer id from given plug output
        if not isinstance(plug, mx.Plug):
            raise ValueError('invalid plug given ({})'.format(plug))

        plug_out = plug.output(plug=True)
        if not isinstance(plug_out, mx.Plug):
            return

        node = plug_out.node()
        cls = Deformer.get_cls_from_node(node)

        if node.is_a(mx.tGroupParts):
            return Deformer.get_input_id(node['inputGeometry'])

        elif node.is_a(Deformer.shape_types):
            xfo = node.parent()
            _xfo = Deformer.get_unique_name(xfo)

            # check assigned id
            for k, v in iteritems(Deformer.get_deformer_ids(xfo)):
                if node == v:

                    if 'layer.' in k:
                        # bypass deformer editing layer
                        plug_in = Deformer.get_deformer_input(node, xfo)
                        return Deformer.get_input_id(plug_in)

                    return '{}->{}'.format(_xfo, k)

        else:
            # check if deformer input
            if node.is_a(mx.kGeometryFilter) and 'input' in plug_out.name():
                fn = oma.MFnGeometryFilter(node.object())

                try:
                    shape_index = plug_out.plug().logicalIndex()
                except:
                    _node = plug_out.node()
                    p = plug_out.plug().parent()
                    shape_index = mx.Plug(node, p).plug().logicalIndex()

                shape_in = fn.inputShapeAtIndex(shape_index)
                shape_in = mx.Node(shape_in)
                xfo = shape_in.parent()
                _xfo = Deformer.get_unique_name(xfo)

                if cls:
                    for k, v in iteritems(Deformer.get_deformer_ids(xfo)):
                        if node == v:
                            return '{}->{}'.format(_xfo, k)

                    log.debug('/!\\ deformer "{}" has not been registered yet'.format(node))
                    return

                # traverse input graph if not mikan deformer
                return Deformer.get_output_id(node['outputGeometry'][shape_index])

            # check hook
            if cls:
                hook_id = cls.get_hook_id(plug_out)
                if hook_id:
                    return hook_id

        log.debug('/!\\ no deformer input id from "" found'.format(plug))

    def get_input(self):
        """Get the input plug for this deformer.

        Returns:
            mx.Plug or None: Input plug of the deformer node.
        """
        if self.transform:
            return Deformer.get_deformer_input(self.node, self.transform)

    def get_output(self):
        """Get the output plug for this deformer.

        Returns:
            mx.Plug or None: Output plug of the deformer node.
        """
        if self.transform:
            plug_out = Deformer.get_deformer_output(self.node, self.transform)
            return plug_out

    @staticmethod
    def get_deformer_ids(xfo, root=None):
        """Get all registered deformer and geometry IDs for a transform.

        Retrieves a dictionary of all tagged nodes (deformers, shapes, sources) associated with a transform,

        Args:
            xfo (mx.Node or str): Transform node to query.
            root (mx.Node or str, optional): Root node for path resolution.

        Returns:
            dict: Dictionary mapping ID strings to nodes. Always includes:
                - 'xfo': The transform node itself
                - 'shape': The main visible shape (if exists)
                - 'source': The original/intermediate shape (if exists)
                Plus any custom tagged nodes (e.g., 'skin.0', 'blend.1').

        Examples:
            >>> ids = Deformer.get_deformer_ids('pSphere1')
            >>> print(list(ids))
            ['xfo', 'shape', 'source', 'skin.0']
            >>> skin_node = ids['skin.0']
        """
        if not isinstance(xfo, mx.Node):
            xfo = mx.encode(str(xfo))

        ids = {}

        # geometry ids
        if 'gem_deformer_tags' in xfo:
            tag_node = xfo['gem_deformer_tags'].input()
            if tag_node is not None and 'gem_tags' in tag_node:
                for i in tag_node['gem_tags'].array_indices:
                    node = tag_node['gem_tags'][i]['node'].input()
                    if node is not None:
                        tag = tag_node['gem_tags'][i]['tag'].read()
                        if tag:
                            ids[tag] = node

        # legacy ids
        name = Deformer.get_unique_name(xfo, root=root)

        for node in Deformer.get_geo_deformers(xfo):
            if 'gem_deformer' in node:
                for tag in (node['gem_deformer'].read() or '').split(';'):
                    tag = tag.rpartition(':')[-1]
                    if tag.startswith(name.rpartition(':')[-1]):
                        tag = tag.split('->')[-1]
                        if tag:
                            ids[tag] = node

        # shape ids
        for node in xfo.shapes():
            if 'gem_deformer' in node:
                for tag in (node['gem_deformer'].read() or '').split(';'):
                    tag = tag.rpartition(':')[-1]
                    tag = tag.split('->')[-1]
                    if tag:
                        ids[tag] = node

        # default ids
        if 'shape' not in ids:
            for node in xfo.shapes():
                if node.is_a(Deformer.shape_types):
                    if not node['io'].read():
                        ids['shape'] = node
                        break

        if 'source' not in ids:
            for node in xfo.shapes():
                if node.is_a(Deformer.shape_types):
                    if node['io'].read():
                        if list(node.outputs()):
                            ids['source'] = node
                            break

        ids['xfo'] = xfo
        return ids

    @staticmethod
    def get_geometry_id(tag, root=None, add_hook=False):
        """Resolve a geometry ID to its corresponding node or plug.

        Parses a geometry identifier string and resolves it to the actual Maya node or plug.
        Supports hooks for custom plug access.

        Args:
            tag (str): Geometry ID in format 'transform->id[@hook]'.
                Examples: 'pSphere1->shape', 'pCube1->skin.0@enable'.
            root (mx.Node or str, optional): Root node for path resolution.
            add_hook (bool): If True, create hook plug if it doesn't exist.

        Returns:
            tuple: (node, transform) where node is the resolved mx.Node or mx.Plug,
                and transform is the associated transform node.
                Returns (None, None) if resolution fails.
        """
        hook = None
        if '@' in tag:
            tag, sep, hook = tag.partition('@')

        xfo, sep, tag = tag.partition('->')
        xfo = Deformer.get_node(xfo, root)

        if not xfo:
            return None, None

        if tag:
            dfm_ids = Deformer.get_deformer_ids(xfo, root)

            # force source if missing
            if tag == 'source' and 'source' not in dfm_ids and 'shape' in dfm_ids:
                mc.delete(mc.deformer(str(xfo), type='tweak'))
                dfm_ids = Deformer.get_deformer_ids(xfo, root)

            # find node
            if tag in dfm_ids:
                dfm = dfm_ids[tag]
                if hook:
                    if dfm.is_a(mx.tTransform):
                        return Nodes.get_node_plug(dfm, hook, add=add_hook), xfo
                    return Deformer.get_deformer_plug(dfm, xfo, hook), xfo
                else:
                    return dfm, xfo
            else:
                return None, xfo
        else:
            return xfo, xfo

    def set_geometry_id(self, node, key):
        """Register a node with a geometry ID tag.

        Assigns a unique identifier to a node so it can be referenced later.
        Handles both DAG nodes (using attributes) and DG nodes (using a tag network node).

        Args:
            node (mx.Node): Node to register.
            key (str): Base key for the ID (e.g., 'skin', 'blend', 'ffd').

        Returns:
            str: The assigned ID tag.
        """
        transform = self.transform
        if node.is_a(Deformer.shape_types):
            transform = node.parent()
        elif node.is_a(mx.kTransform):
            transform = node

        # check if already registered
        tags = self.get_ids()

        for k in tags:
            if k in {'shape', 'source'}:
                continue
            if tags[k] == node:
                return k

        # assign new id
        if '.' in key:
            tag = key
        else:
            indices = []
            for k in tags:
                if k.startswith(key + '.'):
                    try:
                        indices.append(int(k.split('.')[-1]))
                    except:
                        pass
            if not indices:
                indices.append(-1)

            tag = '{}.{}'.format(key, max(indices) + 1)

        # register node
        if 'gem_deformer' not in node:
            with mx.DGModifier() as md:
                md.add_attr(node, mx.String('gem_deformer'))

        if not node.is_a(mx.kDagNode):

            # check tag node
            if 'gem_deformer_tags' not in transform:
                with mx.DagModifier() as md:
                    md.add_attr(transform, mx.Message('gem_deformer_tags'))

            tag_node = transform['gem_deformer_tags'].input()
            if tag_node is None:
                with mx.DGModifier() as md:
                    tag_node = md.create_node(mx.tNetwork, name='deformer_tags#')
                    md.set_attr(tag_node['ihi'], False)

                    children = mx.Message('node'), mx.String('tag')
                    md.add_attr(tag_node, mx.Compound('gem_tags', array=True, children=children))

                    md.connect(tag_node['msg'], transform['gem_deformer_tags'])

            # write and connect id
            i = max(tag_node['gem_tags'].array_indices or [-1]) + 1

            with mx.DGModifier() as md:
                md.set_attr(tag_node['gem_tags'][i]['tag'], tag)
                md.connect(node['gem_deformer'], tag_node['gem_tags'][i]['node'])

        else:
            # write id
            with mx.DGModifier() as md:
                md.set_attr(node['gem_deformer'], tag)

        return tag

    def set_id(self):
        """Set or update the deformer's unique ID.

        Assigns a unique identifier to the deformer node. If an ID is already set in self.id, uses that;
        otherwise generates a new one based on the deformer type.

        Returns:
            str: The assigned ID, or empty string if node doesn't exist.
        """
        if not isinstance(self.node, mx.Node) or not self.node.exists:
            return ''

        if self.id:
            self.set_geometry_id(self.node, self.id)
        else:
            self.id = self.set_geometry_id(self.node, self.deformer)

        return self.id

    def get_id(self):
        """Get the full deformer ID including transform path.

        Returns:
            str or None: Full ID in format 'transform->id', or None if no node exists.

        Examples:
            >>> dfm.get_id()
            'pSphere1->skin.0'
        """
        if self.node is None:
            return

        if 'gem_deformer' not in self.node:
            self.set_id()

        name = Deformer.get_unique_name(self.transform, root=self.root)
        return '{}->{}'.format(name, self.id)

    def set_protected(self, protected=None):
        """Set the protected status of the deformer.

        Protected deformers are marked to prevent accidental modification during batch operations.

        Args:
            protected (bool, optional): Protection status. If None, uses self.protected value.
        """
        if not self.node:
            return

        if protected is None:
            protected = self.protected

        attr = 'gem_protected'
        has_attr = attr in self.node
        if protected:
            if not has_attr:
                self.node.add_attr(mx.Boolean(attr, default=True, keyable=True))
            self.node[attr] = protected
        elif has_attr:
            try:
                self.node.delete_attr(attr)
            except:
                self.node[attr] = protected

    def find_root(self):
        """Resolve the root node reference.

        Updates self.root and self.root_id based on available information.

        Note:
            Called internally during deformer setup.
        """
        if isinstance(self.root, mx.DagNode):
            self.root_id = Deformer.get_unique_name(self.root)
        elif isinstance(self.root, string_types):
            self.root_id = self.root
            self.root = None

    def find_transform(self):
        """Resolve the transform node reference.

        Updates self.transform and self.transform_id based on available information.

        Note:
            Called internally during deformer setup.
        """
        if isinstance(self.transform, mx.DagNode):
            self.transform_id = Deformer.get_unique_name(self.transform, root=self.root)
        else:
            self.transform_id = self.transform
            self.transform = None

    def find_geometry(self):
        """Find and set the geometry shape node for this deformer.

        Locates the appropriate shape node being deformed, handling intermediate shapes and special cases.

        Raises:
            RuntimeError: If no valid deformable geometry is found.

        Note:
            Sets self.geometry to the found shape node.
        """
        if self.geometry_id:
            node, xfo = self.get_geometry_id(self.geometry_id, self.root)
            if node.is_a(Deformer.shape_types):
                self.geometry = node
                return node

        if self.node:
            if self.node.is_a(mx.kGeometryFilter):
                fn = oma.MFnGeometryFilter(self.node.object())
                for shape in fn.getOutputGeometry():
                    shape = mx.Node(shape)
                    if shape.parent() == self.transform:
                        self.geometry = shape
                        return shape
            elif self.node.is_a(mx.kPolyModifier):
                for shape in mc.listHistory(str(self.node), future=True) or []:
                    shape = mx.encode(shape)
                    if shape.is_a(Deformer.shape_types) and shape.parent() == self.transform:
                        self.geometry = shape
                        return shape
            elif self.node.is_a(Deformer.shape_types):
                self.geometry = self.node

        else:
            for shp in self.transform.shapes():

                # skip intermediate shape
                if shp['io'].read():
                    continue

                # skip data shape
                if 'gem_deformer' in shp and 'data.' in shp['gem_deformer'].read():
                        continue

                # found!
                self.geometry = shp
                break

        if not self.geometry:
            raise RuntimeError('/!\\ failed to find the deformable geometry of "{}"'.format(self.transform))

    @staticmethod
    def get_deformer_plug(dfm, xfo, hook):
        """Get a custom plug from a deformer using a hook name.

        Calls the deformer class's hook() method to retrieve custom plugs.

        Args:
            dfm (mx.Node): Deformer node.
            xfo (mx.Node): Transform node.
            hook (str): Hook name (e.g., 'matrix', 'envelope').

        Returns:
            mx.Plug or None: The requested plug, or None if not found.
        """
        if not isinstance(xfo, mx.Node):
            xfo = mx.encode(str(xfo))
        if not isinstance(dfm, mx.Node):
            dfm = mx.encode(str(dfm))
        cls = Deformer.get_cls_from_node(dfm)
        if cls:
            return cls.hook(dfm, xfo, hook)

    @staticmethod
    def get_unique_name(node, root=None):
        """Get the shortest unique path for a node.

        Returns the shortest path that uniquely identifies a node within a given hierarchy,
        excluding nodes from other assets.

        Args:
            node (mx.Node or str): Node to get path for.
            root (mx.Node or str, optional): Root node to restrict search.

        Returns:
            str: Shortest unique path with '/' separators.
        """
        if not isinstance(node, mx.Node):
            node = mx.encode(str(node))
        if root is not None and not isinstance(root, mx.Node):
            root = mx.encode(str(root))

        # exclude other asset geometries
        exclude_roots = []
        if Nodes.current_asset is not None and len(Nodes.assets) > 1:
            for k in Nodes.geometries:
                if k == Nodes.current_asset:
                    continue
                exclude_roots += Nodes.geometries[k]

        # exclude node outside given root
        root_path = ''
        if root is not None:
            root_path = root.path() + '|'

        # check for dupes
        other_paths = []
        for _node in mc.ls(node.name(namespace=True)):
            _node = mx.encode(_node)
            if _node == node:
                continue
            _path = _node.path() + '|'

            skip = False
            for exclude_root in exclude_roots:
                if _path.startswith(exclude_root.path() + '|'):
                    skip = True
                    break
            if skip:
                continue

            if root_path and not _path.startswith(root_path):
                continue

            other_paths.append(_node.path())

        # find the shortest path
        node_path = node.name(namespace=True)
        if other_paths:
            previous_path = None

            while other_paths:
                node_path = node.path()

                sfx = longest_common_suffix([node_path] + other_paths)
                n = sfx.count('|') + 1
                if n < node_path.count('|'):
                    node_path = '|'.join(node_path.split('|')[-n:])

                if node_path == previous_path:
                    break

                previous_path = node_path
                other_paths = [p for p in other_paths if p.endswith(node_path)]

        return node_path.replace('|', '/')

    @staticmethod
    def get_node(node_name, root=None, namespace=None):
        """Resolve a node from its name or path.

        Searches for a node by name, handling namespaces, multiple paths, and asset filtering.
        Supports space-separated alternatives.

        Args:
            node_name (str): Node name or path. Can include multiple space-separated alternatives.
            root (mx.Node or str, optional): Root to restrict search.
            namespace (str, optional): Namespace to prepend to search.

        Returns:
            mx.Node: The resolved node.

        Raises:
            RuntimeError: If node is not found or multiple matches exist.

        Examples:
            >>> node = Deformer.get_node('pSphere1')
            >>> node = Deformer.get_node('arm.L::skin.0 sk_shoulder_L', root=root)
            >>> node = Deformer.get_node('group/pSphere1', namespace='geo')
        """
        if isinstance(node_name, mx.Node):
            return node_name

        # find root
        if isinstance(root, string_types):
            root = mx.encode(root.replace('/', '|'))
        root_path = ''
        if root:
            root_path = root.path() + '|'

        # exclude other asset geometries
        exclude_roots = []
        if Nodes.current_asset is not None and len(Nodes.assets) > 1:
            for k in Nodes.geometries:
                if k == Nodes.current_asset:
                    continue
                exclude_roots += Nodes.geometries[k]

        # search loop
        if namespace and ':' not in namespace:
            namespace += ':'

        name_loop = []
        for n in node_name.split():
            if '::' not in n:
                n = n.replace('/', '|')

            if namespace and ':' not in n:
                n = '|'.join([namespace + _n for _n in n.split('|')])
                name_loop.append(n)

            name_loop.append(n)

            if '::' not in n and ':' in n:
                n = '|'.join([_n.split(':')[-1] for _n in n.split('|')])
                name_loop.append(n)

        resolved = None
        overflow = False

        for n in name_loop:
            if '::' in n:
                n = Nodes.get_id(n)
                if n:
                    return n

            else:
                nodes = mc.ls(n, type='transform')
                if not nodes and n.startswith('|'):
                    nodes = mc.ls(n.strip('|'), type='transform')
                if not nodes:
                    nodes = mc.ls(n, r=1, type='transform')
                nodes = [mx.encode(x) for x in nodes]

                # filter excluded geometries
                if len(nodes) > 1:
                    for _node in nodes[:]:
                        for path_node in exclude_roots:
                            path = path_node.path() + '|'

                            if _node == path_node or _node.path().startswith(path):
                                nodes.remove(_node)
                                break

                # filter root path
                if len(nodes) > 1:
                    if root_path:
                        _nodes = []
                        for node in nodes:
                            if node.path().startswith(root_path):
                                _nodes.append(node)
                        nodes = _nodes

                if len(nodes) > 1:
                    overflow = True

                if len(nodes) == 1:
                    resolved = nodes[0]
                    break

        if not resolved:
            msg = 'no object name "{}"'.format(node_name)
            if overflow:
                msg = 'too many geometries named "{}"'.format(node_name)

            if root:
                msg += ' under root "{}"'.format(root)

            raise RuntimeError(msg)

        else:
            return resolved

    @staticmethod
    def get_node_id(node, find=None):
        """Get the ID string from a node's gem_id attribute.

        Called internally during data dump.

        Args:
            node (mx.Node): Node to query.
            find (str, optional): Specific ID pattern to search for.

        Returns:
            str: ID string plus node name.

        Examples:
            >>> id_str = Deformer.get_node_id(joint_node, find='::skin.')
            >>> print(id_str)
            arm.L::skin.0 sk_shoulder_L
        """
        if 'gem_id' in node:
            if find and str(find) in node['gem_id'].read():
                for tag in node['gem_id'].read().split(';'):
                    if find in tag:
                        return tag + ' ' + str(node)
            return node['gem_id'].read().split(';')[0] + ' ' + str(node)
        return str(node)

    # deformer internal data -------------------------------------------------------------------------------------------

    @staticmethod
    def get_deformer_members(dfm, geo):
        """Get the component members affected by a deformer.

        Retrieves the vertices/CVs/points that are in the deformer's deformer set.
        Handles both legacy deformer sets and modern component tag expressions.

        Args:
            dfm (mx.Node): Deformer node.
            geo (mx.Node): Geometry shape node.

        Returns:
            om.MFnComponent or None: Component function set for the members,
                or None if all components or retrieval failed.
        """
        fn = oma.MFnGeometryFilter(dfm.object())

        try:
            dfm_set = mx.Node(fn.deformerSet)
            fn_set = om.MFnSet(dfm_set.object())
            sl = fn_set.getMembers(flatten=True)
            it = om.MItSelectionList(sl)

            while not it.isDone():
                mobj = it.getDependNode()
                itemType = it.itemType()

                if itemType == om.MItSelectionList.kDagSelectionItem:
                    if it.hasComponents():
                        mdag, cps = it.getComponent()
                        node = mx.DagNode(mobj)

                        if node == geo or node.parent() == geo.parent():
                            if cps.hasFn(om.MFn.kSingleIndexedComponent):
                                return om.MFnSingleIndexedComponent(cps)
                            elif cps.hasFn(om.MFn.kDoubleIndexedComponent):
                                return om.MFnDoubleIndexedComponent(cps)
                            elif cps.hasFn(om.MFn.kTripleIndexedComponent):
                                return om.MFnTripleIndexedComponent(cps)

                it.next()

        except:
            dfm_id = fn.indexForOutputShape(geo.object())
            if 'componentTagExpression' in dfm:
                tag = dfm['input'][dfm_id]['componentTagExpression'].read()

                injection_node = mc.deformableShape(str(geo), ti=True)[0]
                geo = mx.encode(injection_node)

                plug = None
                if geo.is_a(mx.tMesh):
                    plug = geo['outMesh']
                elif geo.is_a(mx.tNurbsSurface):
                    plug = geo['local']
                elif geo.is_a(mx.tNurbsCurve):
                    plug = geo['local']
                elif geo.is_a(mx.tLattice):
                    plug = geo['latticeOutput']

                data_handle = plug.plug().asMDataHandle()
                data_fn = om.MFnGeometryData(data_handle.data())
                tags = data_fn.componentTags()

                if tag == '*' or tag not in tags:
                    cps = Deformer.get_components_mobject(geo)
                else:
                    cps = data_fn.componentTagContents(tag)

                if cps.hasFn(om.MFn.kSingleIndexedComponent):
                    return om.MFnSingleIndexedComponent(cps)
                elif cps.hasFn(om.MFn.kDoubleIndexedComponent):
                    return om.MFnDoubleIndexedComponent(cps)
                elif cps.hasFn(om.MFn.kTripleIndexedComponent):
                    return om.MFnTripleIndexedComponent(cps)
            else:
                msg = traceback.format_exc().strip('\n')
                log.critical(msg)

        log.debug('/!\\ failed to find deformed set members of {} from {}'.format(geo, dfm))

    def get_members(self):
        """Get the component members for this deformer.

        Returns:
            om.MFnComponent or None: Component function set.
        """
        return Deformer.get_deformer_members(self.node, self.geometry)

    def get_membership(self):
        """Get the membership map for this deformer.

        Creates a binary weight map indicating which components are affected by the deformer (1) and which are not (0).

        Returns:
            list or None: List of 0/1 values for each component, or None if all components are affected.
        """
        # get membership map
        cp_fn = self.get_members()
        if cp_fn is None or cp_fn.isComplete:
            return
        ids = self.get_components_indices(cp_fn, self.geometry)

        total_size = self.get_size()
        mmap = [0] * total_size
        for i in ids:
            if i < total_size:
                mmap[i] = 1
        return mmap

    def read_membership(self):
        """Read membership from Maya scene and store in data.

        Reads which components are in the deformer set and stores as a WeightMap in self.data['membership'].

        Note:
            Only applies to geometry filter deformers.
        """
        if not self.node.is_a(mx.kGeometryFilter):
            return

        mmap = self.get_membership()
        if mmap:
            self.data['membership'] = abstract.WeightMap(mmap)
        else:
            self.data.pop('membership', None)

    def write_membership(self):
        """Write membership data to Maya scene.

        Updates the deformer set in Maya to match the membership map stored in self.data['membership'].
        Handles both legacy deformer sets and modern component tag expressions.

        Note:
            Only applies to geometry filter deformers.
        """
        if not self.node.is_a(mx.kGeometryFilter):
            return

        # check component mode
        do_tag = False
        fn = oma.MFnGeometryFilter(self.node.object())
        try:
            dfm_set = mx.Node(fn.deformerSet)
        except RuntimeError:
            try:
                om.MFnGeometryData.componentTags
                do_tag = True
            except AttributeError:
                raise RuntimeError('/!\\ failed to retrieve deformer set of {}'.format(self.node))

        # assign membership map
        cps_all = Deformer.get_components_mobject(self.geometry)

        fn_set = None
        if not do_tag:
            fn_set = om.MFnSet(dfm_set.object())

        mmap = self.data.get('membership')
        if mmap:
            indices = []
            for i, v in enumerate(self.data['membership'].weights):
                if v:
                    indices.append(i)

            cps_obj = Deformer.get_components_mobject(self.geometry, indices)

            if do_tag:
                injection_node = mc.deformableShape(str(self.geometry), ti=True)[0]
                geo = mx.encode(injection_node)

                self.set_id()
                tag = self.id.replace('.', '_')
                tag_id = None
                for i in geo['gtag'].array_indices:
                    if geo['gtag'][i]['gtagnm'].read() == tag:
                        tag_id = i
                        break

                if tag_id is None:
                    _ids = geo['gtag'].array_indices
                    if _ids:
                        tag_id = _ids[-1] + 1
                    else:
                        tag_id = 0
                    geo['gtag'][tag_id]['gtagnm'] = tag

                fn_cp = om.MFnComponentListData()
                cpl = fn_cp.create()
                fn_cp.add(cps_obj)

                geo['gtag'][tag_id]['gtagcmp'].plug().setMObject(cpl)

                dfm_id = fn.indexForOutputShape(self.geometry.object())
                with mx.DGModifier() as md:
                    md.set_attr(self.node['input'][dfm_id]['componentTagExpression'], tag)

            else:
                # TODO: check matching membership?
                sl = om.MSelectionList()
                sl.add((self.geometry.dag_path(), cps_obj))
                fn_set.addMembers(sl)

                sl = om.MSelectionList()
                sl.add((self.geometry.dag_path(), cps_all))
                sl.toggle(self.geometry.dag_path(), cps_obj)
                if sl.length():
                    fn_set.removeMembers(sl)

        else:
            # assign all points
            if do_tag:
                # if mc.ls(mc.listHistory(str(self.transform)), type='polyModifier'):
                if self.geometry.is_a(mx.tMesh):
                    injection_node = mc.deformableShape(str(self.geometry), tagInjectionNode=True)
                    if not injection_node:
                        injection_node = mc.deformableShape(str(self.geometry), originalGeometry=True)
                    if injection_node and injection_node[0]:
                        geo = mx.encode(injection_node[0].split('.')[0])
                    else:
                        geo = self.geometry

                    tag_id = None
                    for i in geo['gtag'].array_indices:
                        if geo['gtag'][i]['gtagnm'].read() == 'void':
                            tag_id = i
                            break

                    if tag_id is None:
                        _ids = geo['gtag'].array_indices
                        if _ids:
                            tag_id = _ids[-1] + 1
                        else:
                            tag_id = 0
                        geo['gtag'][tag_id]['gtagnm'] = 'void'

                dfm_id = fn.indexForOutputShape(self.geometry.object())
                with mx.DGModifier() as md:
                    md.set_attr(self.node['input'][dfm_id]['componentTagExpression'], '*')

            else:
                cp_fn = self.get_members()
                if cp_fn and not cp_fn.isComplete:
                    try:
                        sl = om.MSelectionList()
                        sl.add((self.geometry.dag_path(), cps_all))
                        fn_set.addMembers(sl)
                    except:
                        pass

    @staticmethod
    def get_shape_components_size(shp):
        """Get the total number of components in a shape.

        Args:
            shp (mx.Node or str): Shape node.

        Returns:
            int: Total number of components (vertices, CVs, or points).

        Raises:
            ValueError: If shape type is not supported.

        Examples:
            >>> mesh = mx.encode('pSphereShape1')
            >>> count = Deformer.get_shape_components_size(mesh)
            >>> print(f"Mesh has {count} vertices")
        """
        if not isinstance(shp, mx.Node):
            shp = mx.encode(str(shp))

        if shp.is_a(mx.tMesh):
            fn = om.MFnMesh(shp.object())
            return fn.numVertices

        elif shp.is_a(mx.tNurbsCurve):
            fn = om.MFnNurbsCurve(shp.object())
            n = fn.numCVs
            if fn.form == fn.kPeriodic:
                n -= fn.degree
            return n

        elif shp.is_a(mx.tNurbsSurface):
            fn = om.MFnNurbsSurface(shp.object())
            u = fn.numCVsInU
            v = fn.numCVsInV
            if fn.formInU == fn.kPeriodic:
                u -= fn.degreeInU
            if fn.formInV == fn.kPeriodic:
                v -= fn.degreeInV
            return u * v

        elif shp.is_a(mx.tLattice):
            s = shp['sDivisions'].read()
            t = shp['tDivisions'].read()
            u = shp['uDivisions'].read()
            return s * t * u

        else:
            raise ValueError('shape type {} not supported'.format(shp.type_name))

    @staticmethod
    def get_components_indices(fn, shp):
        """Convert component function set to flat index list.

        Converts component indices from their native format (single, double, or triple indexed)
        to a flat list of integer indices.

        Args:
            fn (om.MFnComponent): Component function set.
            shp (mx.Node): Shape node for context.

        Returns:
            list: Flat list of integer component indices.

        Raises:
            ValueError: If shape type is not supported.
        """
        if isinstance(fn, om.MFnSingleIndexedComponent):
            return list(fn.getElements())

        elif isinstance(fn, om.MFnDoubleIndexedComponent):
            if fn.isComplete:
                u, v = fn.getCompleteData()
            else:
                if shp.is_a(mx.tNurbsSurface):
                    _fn = om.MFnNurbsSurface(shp.object())
                    u = _fn.numCVsInU
                    v = _fn.numCVsInV
                    if _fn.formInU == _fn.kPeriodic:
                        u -= _fn.degreeInU
                    if _fn.formInV == _fn.kPeriodic:
                        v -= _fn.degreeInV
                else:
                    raise ValueError('shape type {} not supported'.format(shp.type_name))

            ids = []
            for i in fn.getElements():
                ids.append(i[0] + u * i[1])
            return ids

        elif isinstance(fn, om.MFnTripleIndexedComponent):
            if fn.isComplete:
                s, t, u = fn.getCompleteData()
            else:
                if shp.is_a(mx.tLattice):
                    s = shp['sDivisions'].read()
                    t = shp['tDivisions'].read()
                else:
                    raise ValueError('shape type {} not supported'.format(shp.type_name))

            ids = []
            for i in fn.getElements():
                ids.append(((i[1] + t * i[2]) * s) + i[0])
            return ids

    @staticmethod
    def get_components_mobject(shp, ids=None):
        """Create a component MObject for specified indices.

        Creates a Maya API component object for the given shape and indices.
        If no indices are provided, creates a complete component set.

        Args:
            shp (mx.Node or str): Shape node.
            ids (list, optional): List of component indices. If None, creates a complete set.

        Returns:
            om.MObject: Component MObject.

        Examples:
            >>> # Create component for specific vertices
            >>> comp = Deformer.get_components_mobject(mesh, [0, 5, 10])

            >>> # Create complete component set
            >>> all_comp = Deformer.get_components_mobject(mesh)
        """
        if not isinstance(shp, mx.Node):
            shp = mx.encode(str(shp))

        if shp.is_a(mx.tNurbsSurface):
            cps = om.MFnDoubleIndexedComponent()
            mobj = cps.create(om.MFn.kSurfaceCVComponent)

            fn = om.MFnNurbsSurface(shp.object())
            u = fn.numCVsInU
            v = fn.numCVsInV
            if fn.formInU == fn.kPeriodic:
                u -= fn.degreeInU
            if fn.formInV == fn.kPeriodic:
                v -= fn.degreeInV

            if ids is None:
                cps.setCompleteData(u, v)
            else:
                for i in ids:
                    cps.addElement(i % u, i / u)

        elif shp.is_a(mx.tLattice):
            cps = om.MFnTripleIndexedComponent()
            mobj = cps.create(om.MFn.kLatticeComponent)

            s = shp['sDivisions'].read()
            t = shp['tDivisions'].read()
            u = shp['uDivisions'].read()
            if ids is None:
                cps.setCompleteData(s, t, u)
            else:
                for i in ids:
                    cp = [0, 0, 0]
                    cp[2] = i / (s * t)
                    cp[1] = (i % (s * t)) / s
                    cp[0] = (i % (s * t)) % s
                    cps.addElement(*cp)

        else:
            ktype = om.MFn.kComponent
            if shp.is_a(mx.tMesh):
                ktype = om.MFn.kMeshVertComponent
            elif shp.is_a(mx.tNurbsCurve):
                ktype = om.MFn.kCurveCVComponent
            cps = om.MFnSingleIndexedComponent()
            mobj = cps.create(ktype)

            if ids is None:
                if shp.is_a(mx.tMesh):
                    fn = om.MFnMesh(shp.object())
                    cps.setCompleteData(fn.numVertices)
                elif shp.is_a(mx.tNurbsCurve):
                    fn = om.MFnNurbsCurve(shp.object())
                    n = fn.numCVs
                    if fn.form == fn.kPeriodic:
                        n -= fn.degree
                    cps.setCompleteData(n)
            else:
                cps.addElements(ids)

        return mobj

    def get_size(self):
        """Get the total component count for this deformer's geometry.

        Returns:
            int: Number of components.
        """
        if not self.geometry:
            try:
                self.find_geometry()
            except:
                if 'maps' in self.data and self.data['maps']:
                    maps = list(self.data['maps'].values())
                    return len(maps[0].weights)
                return 0
        return Deformer.get_shape_components_size(self.geometry)

    # map edit --------------------------------------------------------------------------------------------------------

    def transfer(self, xfo, flip=False, mirror=False, axis='x'):
        """Transfer deformer data to another geometry.

        Creates a new deformer instance with data transferred from this deformer to a target geometry.
        Supports flipping and mirroring across an axis.

        Args:
            xfo (mx.Node or str): Target transform node.
            flip (bool): If True, flip data across the specified axis.
            mirror (bool): If True, mirror data across the specified axis.
            axis (str): Axis for flip/mirror operation ('x', 'y', or 'z').

        Returns:
            Deformer: New deformer instance with transferred data.

        Raises:
            RuntimeError: If axis is invalid or geometry type not supported.

        Note:
            Uses temporary skin clusters and closest point transfer.
            The returned deformer has not been built yet. Call build() to create the actual Maya node.

        Examples:
            >>> source_dfm = Deformer.create(source_geo, skin_node)
            >>> target_geo = mx.encode('target_mesh')
            >>> new_dfm = source_dfm.transfer(target_geo)
            >>> new_dfm.build()

            >>> # Transfer with mirroring
            >>> mirrored_dfm = source_dfm.transfer(target_geo, mirror=True, axis='x')
        """
        _sl = mc.ls(sl=1)

        if not isinstance(xfo, mx.Node):
            xfo = mx.encode(str(xfo))

        # init new deformer
        dfm = self.copy()
        dfm.id = None
        dfm.transform = xfo
        dfm.transform_id = None
        dfm.geometry = None
        dfm.geometry_id = None
        dfm.node = None
        dfm.find_geometry()

        if flip or mirror:
            if axis not in ['x', 'y', 'z']:
                raise RuntimeError('wrong axis')

        # build temp transfer geometries
        with mx.DagModifier() as md:
            root = md.create_node(mx.tTransform, name='__transfer__')
            srcd_root = md.create_node(mx.tTransform, parent=root)
            dstd_root = md.create_node(mx.tTransform, parent=root)

        srcd = create_mesh_copy(self.transform)
        if dfm.geometry.is_a(mx.tLattice):
            dstd = create_lattice_proxy(dfm.transform)
        elif dfm.geometry.is_a((mx.tNurbsCurve, mx.tNurbsSurface)):
            # TODO: extrude/convert to polygon
            raise RuntimeError('nurbs not yet implemented')
        else:
            dstd = create_mesh_copy(dfm.transform)

        mc.parent(str(srcd), str(srcd_root))
        mc.parent(str(dstd), str(dstd_root))

        if mirror:
            mc.parent(str(dstd), str(srcd_root))
            dstdm = mc.duplicate(str(dstd), rr=1, rc=1)
            dstdm = mx.encode(dstdm[0])
            mc.parent(str(dstdm), str(dstd_root))
        if flip or mirror:
            dstd_root['s' + axis] = -1

        # build temp transfer deformers
        with mx.DagModifier() as md:
            dummy = md.create_node(mx.tJoint, parent=root)

        _data = {'deformer': 'skin', 'transform': srcd, 'data': {'infs': {0: dummy}, 'normalize': 2}}
        skin0 = Deformer(**_data)
        skin0.build()

        _data = {'deformer': 'skin', 'transform': dstd, 'data': {'infs': {0: dummy}, 'normalize': 2}}
        skin1 = Deformer(**_data)
        skin1.build()

        skin0.node['envelope'] = 0
        skin1.node['envelope'] = 0

        if mirror:
            _data = {'deformer': 'skin', 'transform': dstdm, 'data': {'infs': {0: dummy}, 'normalize': 2}}
            skin2 = Deformer(**_data)
            skin2.build()
            skin2.node['envelope'] = 0

        def convert_weightmap(wm):
            skin0.data['maps'][0] = wm.copy()
            skin0.write()

            mc.copySkinWeights(str(srcd), str(dstd), nm=1, sa='closestPoint', ia='oneToOne')
            skin1.read()

            if mirror:
                mc.copySkinWeights(str(srcd), str(dstdm), nm=1, sa='closestPoint', ia='oneToOne')
                skin2.read()

                # TODO: ??? revoir l'algo de merge mirror
                for vtx, w1 in enumerate(skin1.data['maps'][0].weights):
                    w2 = skin2.data['maps'][0].weights[vtx]
                    if w2 > w1:
                        skin1.data['maps'][0].weights[vtx] = w2

            return skin1.data['maps'][0].copy()

        # transfer maps
        for i in list(self.data.get('maps', [])):
            dfm.data['maps'][i] = convert_weightmap(self.data['maps'][i])

        if 'membership' in self.data:
            dfm.data['membership'] = convert_weightmap(self.data['membership'])

        if 'delta' in self.data:
            for i in self.data['delta']:
                for b in self.data['delta'][i]:
                    # unpack xyz
                    delta = self.data['delta'][i][b].weights
                    wx = delta[0::3]
                    wy = delta[1::3]
                    wz = delta[2::3]
                    dx = min(wx)
                    dy = min(wy)
                    dz = min(wz)
                    wx = convert_weightmap(WeightMap(wx) - dx) + dx
                    wy = convert_weightmap(WeightMap(wy) - dy) + dy
                    wz = convert_weightmap(WeightMap(wz) - dz) + dz
                    dfm.data['delta'][i][b].weights = [item for sublist in zip(wx, wy, wz) for item in sublist]

        # cleanup
        mx.delete(root)
        mc.select(_sl)
        return dfm

    top_layer = float('inf')

    @classmethod
    def get_layers(cls, xfo, root=None):
        """Get all deformer editing layers for a geometry.

        Deformer layers allow non-destructive editing by creating intermediate shape nodes.
        This method retrieves all layer shapes and identifies the top (final) layer.

        Args:
            xfo (mx.Node or str): Transform node.
            root (mx.Node or str, optional): Root for path resolution.

        Returns:
            dict: Dictionary mapping layer numbers to shape nodes. The top layer is keyed by cls.top_layer (infinity).

        Examples:
            >>> layers = Deformer.get_layers(geo)
            >>> for layer_num, shape in layers.items():
            ...     if layer_num == Deformer.top_layer:
            ...         print(f"Top layer: {shape}")
            ...     else:
            ...         print(f"Layer {layer_num}: {shape}")
        """
        ids = cls.get_deformer_ids(xfo, root)
        layers = {}
        top_layer = cls.top_layer

        for k in ids:
            if k.startswith('layer.'):
                layer = k.replace('layer.', '')
                layers[int(layer)] = ids[k]

        # find top layer
        layer_shapes = layers.values()
        if ids['shape'] in layer_shapes:
            shapes = mc.listHistory(str(ids['shape']), future=True) or []
            shapes = mx.ls(shapes, type='deformableShape')
            for shape in shapes:
                if shape in layer_shapes:
                    continue
                if shape != ids['shape'] and shape.parent() == ids['shape'].parent():
                    layers[top_layer] = shape
                    break
        else:
            layers[top_layer] = ids['shape']

        return layers

    @classmethod
    def get_current_layer(cls, xfo, root=None):
        """Get the currently visible layer number.

        Args:
            xfo (mx.Node or str): Transform node.
            root (mx.Node or str, optional): Root for path resolution.

        Returns:
            int or float: Layer number, or cls.top_layer if top layer is active.

        Examples:
            >>> current = Deformer.get_current_layer(geo)
            >>> if current == Deformer.top_layer:
            ...     print("Viewing final result")
            ... else:
            ...     print(f"Editing layer {current}")
        """
        ids = cls.get_deformer_ids(xfo, root)
        if 'shape' not in ids:
            return

        shp = ids['shape']
        for k in ids:
            if k.startswith('layer.') and ids[k] == shp:
                layer = k.replace('layer.', '')
                return int(layer)

        return cls.top_layer

    @classmethod
    def toggle_layers(cls, xfo, root=None, layer=None, top=False, lodv=False):
        """Toggle visibility of deformer editing layers.

        Controls which layer shape is visible by setting intermediate object flags.
        Allows switching between edit layers and the final result.

        Args:
            xfo (mx.Node or str): Transform node.
            root (mx.Node or str, optional): Root for path resolution.
            layer (int or float, optional): Layer number to show. If None, cycles to next layer.
            top (bool): If True, force display of top (final) layer.
            lodv (bool): If True, use level of detail visibility instead of intermediate flag for top layer.

        Examples:
            >>> # Show final result
            >>> Deformer.toggle_layers(geo, top=True)

            >>> # Cycle to next layer
            >>> Deformer.toggle_layers(geo)

            >>> # Show specific layer
            >>> Deformer.toggle_layers(geo, layer=0)
        """
        layers = cls.get_layers(xfo, root)
        top_layer = cls.top_layer

        if top and top_layer not in layers:
            for i, layer in iteritems(layers):
                if Deformer.get_deformer_output(layer, layer.parent()) is not None:
                    layers[top_layer] = layers.pop(i)
                    with mx.DGModifier() as md:
                        md.set_attr(layer['gem_deformer'], '')
                        md.delete_attr(layer['gem_deformer'])
                        md.set_attr(layer['io'], False)

        if top_layer not in layers:
            log.error('/!\\ couldn\'t find top shape')

        # force top layer
        if top or layer is float('inf'):
            for k in layers:
                if k == top_layer:
                    layers[top_layer]['lodv'] = True
                    layers[top_layer]['io'] = False
                else:
                    layers[k]['io'] = True
            return

        # find layer to show if undefined
        if layer is None or layer not in layers:
            keys = sorted(layers)
            layer = None
            for k in keys:
                if not layers[k]['io'].read():
                    layer = k
                    break

            if layer == keys[-1]:
                layer = keys[0]
            else:
                layer = keys[keys.index(layer) + 1]

        # show/hide layers
        for k in layers:
            if k == layer:
                # show
                layers[k]['io'] = False
                layers[k]['lodv'] = True
            else:
                # hide
                if k == top_layer:
                    if lodv:
                        layers[k]['lodv'] = False
                    else:
                        layers[k]['io'] = True
                else:
                    layers[k]['io'] = True

    @classmethod
    def remove_layers(cls, xfo, root=None):
        """Remove all deformer editing layers from a geometry.

        Deletes all intermediate layer shapes and restores the geometry to its final state.
        Fixes membership issues that may occur in Maya 2018+.

        Args:
            xfo (mx.Node or str): Transform node.
            root (mx.Node or str, optional): Root for path resolution.
        """
        if not isinstance(xfo, mx.Node):
            xfo = mx.encode(str(xfo))

        cls.toggle_layers(xfo, top=True)

        layer_ids = []
        for k, dfm in iteritems(cls.get_deformer_ids(xfo, root=root)):
            if k.startswith('layer.'):
                layer_ids.append(dfm)

        if layer_ids:
            mx.delete(layer_ids)

        # fix 2018 membership
        for node in cls.get_geo_deformers(xfo):

            fn = oma.MFnGeometryFilter(node.object())
            try:
                dfm_set = mx.Node(fn.deformerSet)
            except:
                continue

            dfm = Deformer.create(xfo, node, read=False)
            if dfm.get_members() is None:
                shp = [shp for shp in xfo.shapes() if not shp['io'].read()][0]
                dfm_set.add(str(shp) + '.pt[*]')

    @classmethod
    def inject_layers(cls, xfo, root=None):
        """Inject editing layers into the deformer stack.

        Creates intermediate shape nodes for each skin cluster,
        enabling non-destructive layer-based editing of deformer weights.

        Args:
            xfo (mx.Node or str): Transform node.
            root (mx.Node or str, optional): Root for path resolution.

        Note:
            Only affects skin cluster deformers. Other deformer types are not layered.

        Examples:
            >>> # Enable layer editing for skin clusters
            >>> Deformer.inject_layers(geo)
            >>>
            >>> # Now you can toggle between layers
            >>> Deformer.toggle_layers(geo, layer=0)
        """
        if not isinstance(xfo, mx.Node):
            xfo = mx.encode(str(xfo))

        ids = cls.get_deformer_ids(xfo, root=root)
        skin_nodes = []

        for k, dfm in iteritems(ids):
            if k.startswith('layer.'):
                log.warning('/!\\ {} is already layered'.format(xfo))
                return

            if k.startswith('skin.'):
                skin_nodes.append(k)

        shape = ids['shape']
        nodetype = mc.nodeType(str(shape))

        skin_nodes.sort()
        for i in range(len(skin_nodes)):
            skin_nodes[i] = ids[skin_nodes[i]]

        for skin in skin_nodes[:-1]:
            dfm = Deformer.create(xfo, skin, read=False)

            with mx.DagModifier() as md:
                shp_layer = md.create_node(nodetype, parent=xfo)

            plug_in_bf = cls.get_deformer_input(shp_layer, xfo)
            plug_out_bf = cls.get_deformer_output(skin, xfo)

            plug_in_af = plug_out_bf.output(plug=True)
            plug_out_af = cls.get_deformer_output(shp_layer, xfo)

            with mx.DGModifier() as md:
                md.set_attr(shp_layer['io'], True)
                md.connect(plug_out_bf, plug_in_bf)
                md.connect(plug_out_af, plug_in_af)

            dfm.set_geometry_id(shp_layer, 'layer')


class DeformerGroup(object):

    def __init__(self, node=None, filtered=False, disabled=False, dry=False, name=None):
        self.deformers = SuperTree('->')
        self.data = []
        self.node = None
        self.root = None
        self.geometries = []
        self.filtered = filtered
        self._name = name

        if node is not None:
            if not isinstance(node, mx.Node):
                node = mx.encode(str(node))
        self.node = node

        self.date = None
        if not self.node:
            self.date = time.time()

        if self.node is not None and 'gem_deformers' not in self.node:
            raise RuntimeError('/!\\ invalid node')

        # parse node data
        if self.node:
            try:
                self.root = Deformer.get_node(self.node['gem_deformers'].read())
            except:
                pass

            if not dry:
                with timed_code('parsing {}'.format(node), level='DEBUG'):
                    self.parse(disabled=disabled)

            if 'gem_id' in self.node:
                self.filtered = True

    def __len__(self):
        return len(self.deformers.get('*->*', as_list=True) or [])

    def __contains__(self, item):
        if isinstance(item, int):
            if item < len(self):
                return True
            return False

        if isinstance(item, Deformer):
            return item in self.data

        if isinstance(item, str):
            return item in self.deformers.keys()

        return False

    def __getitem__(self, key):
        if isinstance(key, int):
            deformers = self.deformers.get('*->*', as_list=True) or []
            return deformers[key]

        return self.deformers[key]

    def __delitem__(self, key):
        if isinstance(key, (str, int)) and key in self:
            dfm = self[key]
            self.data.remove(dfm)

            del self.deformers[key]

        else:
            raise KeyError(key)

    def copy(self):
        group = DeformerGroup()

        group.deformers = deepcopy(self.deformers)
        group.data = deepcopy(self.data)
        group.root = self.root
        group.geometries = deepcopy(self.geometries)
        group.filtered = self.filtered
        group._name = 'copy'
        return group

    @property
    def name(self):
        name = ''
        if self.node is not None and self.node.exists:
            name = self.node.name(namespace=False)
        elif self.root is not None and self.root.exists:
            name = self.root.name()

        if name:
            if self._name is not None:
                name += ' ' + self._name
            return name
        elif self._name:
            return self._name

        raise RuntimeError('/!\\ DeformerGroup has no name')

    def rename(self, name):
        if self.node is None:
            raise RuntimeError('/!\\ DeformerGroup has no node')
        if self.node.is_referenced():
            return
        if not name.startswith('_'):
            name = '_' + name

        node_name = self.node.name(namespace=True)
        ns = node_name.split(':')[0] + ':' if ':' in node_name else ''
        self.node.rename(ns + name)

    def remove(self):
        try:
            mx.delete(self.node)
        except:
            pass

    def duplicate(self):
        grp = self.copy()
        if self.node:
            node = mc.duplicate(str(self.node), rr=1)
            grp.node = mx.encode(node[0])

            if 'gem_id' in grp.node:
                mc.deleteAttr(str(grp.node) + '.gem_id')

                parent = grp.node.parent()
                if parent:
                    mc.parent(str(grp.node), w=1)

        return grp

    def get_hierarchy(self, node=None):
        if node is None:
            node = self.node
            yield node

        for ch in node.children(type=mx.tTransform):
            if 'gem_deformers' not in ch:
                yield ch
                for gch in self.get_hierarchy(ch):
                    yield gch

    def parse(self, disabled=False):
        from .asset import Helper
        deformers = []

        # recursive hierarchy loop
        for node in self.get_hierarchy():
            helper = Helper(node)
            if not helper.has_enable():
                helper.set_enable(True)

            # check for disabled linked deformers
            if disabled and helper.disabled():
                continue

            # load stored deformers
            cfg = ConfigParser(node)
            for ini in cfg['deformer']:
                data = Deformer.parse(ini)
                dfm = Deformer(**data)

                self.data.append(dfm)

                node_name = dfm.transform_id
                if dfm.transform:
                    node_name = Deformer.get_unique_name(dfm.transform, root=self.root)
                self.deformers['{}->{}'.format(node_name, dfm.id)] = dfm

                deformers.append((dfm, ini))

        return deformers

    def update(self):
        from .asset import Helper

        for dfm, ini in self.parse():
            if Helper(ini.parser.node).disabled():
                continue
            if ini.parser.node.is_referenced():
                log.warning('/!\\ can\'t update {}, data are referenced'.format(dfm))
                continue

            try:
                dfm.parse_nodes()
                dfm.find_node()
                dfm.find_geometry()
            except:
                log.error('/!\\ no geometry found for: {}'.format(dfm))
                continue

            if dfm.transform:
                log.info('update data of {}'.format(dfm))

                dfm.read_membership()
                dfm.read()
                dfm.round()

                # update notes
                data = dfm.encode_data()
                ini.write(data)

    def read(self, protected=False, read=True):

        # get all linked group
        groups = DeformerGroup.get_all_filtered_groups() if self.filtered else []

        # read all deformer from root (overwrite current loaded deformers)
        geometries = self.get_geometries(self.geometries, ref=True)
        for geo in geometries:
            # switch layer to top if any
            layer = Deformer.get_current_layer(geo)
            Deformer.toggle_layers(geo, top=True)

            # get all deformer from history
            shp = None
            for _shp in geo.shapes():
                if not _shp['io'].read():
                    shp = _shp
                    break

            if shp is None:
                continue

            for deformer in Deformer.get_geo_deformers(geo, check=True):
                path = Deformer.get_unique_name(geo, root=self.root)

                # skip protected deformers
                if not protected and 'gem_protected' in deformer and deformer['gem_protected'].read():
                    log.debug('skip reading protected deformer: {}'.format(deformer))
                    continue

                # skip if linked
                if self.filtered and 'gem_deformer' in deformer:

                    # get tag str from nodes
                    tag = None

                    # get id
                    tag_node = deformer['gem_deformer'].output()
                    if tag_node is not None:
                        tag_plug = deformer['gem_deformer'].output(plug=True)
                        i = tag_plug.plug().parent().logicalIndex()
                        tag = path + '->' + tag_node['gem_tags'][i]['tag'].read()

                    # legacy id
                    else:
                        for _tag in deformer['gem_deformer'].read().split(';'):
                            if _tag.startswith(path):
                                tag = _tag

                    found = False
                    if tag:
                        for grp in groups:
                            if grp.deformers.get(tag):
                                found = True
                                break
                    if found:
                        continue

                # read data
                dfm = Deformer.create(shp, deformer, root=self.root, read=read)

                if dfm.geometry.is_a(mx.tLattice):
                    dfm.priority = -100

                tag = '{}->{}'.format(path, dfm.set_id())
                self.data.append(dfm)
                self.deformers[tag] = dfm

            Deformer.toggle_layers(geo, layer=layer)

    @staticmethod
    def create(nodes=None, filtered=False, read=True):

        _nodes = []
        if isinstance(nodes, (list, tuple)):
            for node in nodes:
                if not isinstance(node, mx.Node):
                    node = mx.encode(str(node))
                _nodes.append(node)
        elif nodes is not None:
            if not isinstance(nodes, mx.Node):
                nodes = mx.encode(str(nodes))
            _nodes.append(nodes)

        nodes = _nodes
        grp = DeformerGroup(None, filtered=filtered)
        grp.geometries = nodes

        if not nodes:
            return grp

        # find root
        if len(nodes) == 1:
            grp.root = nodes[0]
        else:
            root_path = longest_common_prefix([x.path() for x in grp.geometries])
            root_path = '|'.join(root_path.split('|')[:-1])
            if root_path:
                grp.root = mx.encode(root_path)

        # build data
        grp.read(read=read)

        return grp

    def write(self, recursive=True):

        if self.node is not None:
            raise RuntimeError('/!\\ already written')

        if self.root is None:
            root_path = ''
            grp_name = 'group'
        elif not self.root.exists:
            raise RuntimeError('deformer group root "{}" doesn\'t exist anymore'.format(self.root))
        else:
            root_path = Deformer.get_unique_name(self.root)
            grp_name = self.root.name(namespace=False)

        with mx.DagModifier() as md:
            self.node = md.create_node(mx.tTransform, name='_dfm_{}'.format(grp_name))
        self.node.addAttr(mx.String('gem_deformers'))
        self.node['gem_deformers'] = root_path
        if self.filtered:
            self.set_id()

        self.node.add_attr(mx.Double('gem_time'))
        self.node['gem_time'] = time.time()

        cfg = ConfigParser(self.node)

        for dfm in self.data:
            dfm.set_id()
            data = dfm.encode_data()

            # multiple storage nodes
            if recursive:
                if dfm.transform and dfm.transform.exists:
                    path = dfm.transform.path()
                    path = path[len(self.root.path()) + 1:]
                    path = '|'.join(['dfm_' + n.split(':')[-1] for n in path.split('|')])
                else:
                    path = 'dfm_' + dfm.transform_id

                if dfm.transform == self.root:
                    dfm_node = self.node
                else:
                    dfm_node = self.create_store_path(path)
                cfg = ConfigParser(dfm_node)

            ini = cfg.append('deformer')
            ini.write(data)
            dfm.ini = ini

    def create_store_path(self, path):
        if not self.node.exists:
            raise RuntimeError('DeformerGroup node does not exists anymore!')

        root_path = self.node.path()
        node = root_path + '|' + path
        if mc.objExists(node):
            return node

        names = path.split('|')

        for n in names:
            node = root_path + '|' + n
            if not mc.objExists(node):
                with mx.DagModifier() as md:
                    parent = mx.encode(root_path)
                    node = md.create_node(mx.tTransform, parent=parent, name=node.split('|')[-1])
            root_path += '|' + n

        return node

    def set_id(self):
        if 'gem_id' in self.node and '::deformers.' in self.node['gem_id'].read():
            return
        tag = '::deformers.{}'.format(str(uuid.uuid1()).split('-')[0])
        Nodes.set_id(self.node, tag)
        return tag

    def get_id(self):
        if not self.node or 'gem_id' not in self.node:
            return
        tags = self.node['gem_id'].read()
        for tag in tags.split(';'):
            if '::deformers.' in tag:
                return tag

    @staticmethod
    def get_all_filtered_groups():
        groups = []

        for node in mx.ls('*.gem_deformers', o=1, r=1):
            if 'gem_id' in node:
                groups.append(DeformerGroup(node, disabled=True))

        return groups

    def set_filtered(self):
        if not self.node or 'gem_deformers' not in self.node:
            return
        if self.filtered or 'gem_id' in self.node:
            return

        tags = []
        for xfo in self.deformers.tree:
            for tag in self.deformers.tree[xfo]:
                tags.append('{}->{}'.format(xfo, tag))

        for grp in DeformerGroup.get_all_filtered_groups():
            for tag in tags:
                if grp.deformers.get(tag):
                    return

        self.set_id()

    @staticmethod
    def get_geometries(root, ref=False):

        _sel = mc.ls(sl=1)
        mx.cmd(mc.select, root, hi=1)
        nodes = mx.ls(sl=True)
        mc.select(_sel)

        geometries = []
        for node in nodes:
            if node.is_a(mx.tTransform):
                if not node.shape() or not node.is_a((mx.tMesh, mx.tNurbsCurve, mx.tNurbsSurface, mx.tLattice)):
                    continue
            elif node.is_a((mx.tMesh, mx.tNurbsCurve, mx.tNurbsSurface, mx.tLattice)):
                node = node.parent()
            else:
                continue

            if node not in geometries:
                if ref or not node.is_referenced():
                    geometries.append(node)
        return geometries


class WeightMapInterface(abstract.WeightMapInterface):

    def get_node(self):
        if 'node' not in self.data:
            return

        node = self.data['node']

        if isinstance(node, str):
            for name in node.split():
                if '::' in name:
                    _node = Nodes.get_id(name)
                    if _node:
                        return _node
                else:
                    if mc.objExists(name):
                        return mx.encode(name)
                    return name

        elif isinstance(node, mx.Node):
            return node

    def get_node_tag(self, subkey=None):

        data = self.data
        if subkey:
            if subkey not in data:
                raise ValueError()
            data = data[subkey]

        node = data.get('node')
        if isinstance(node, mx.Node):
            node_tag = Deformer.get_node_id(node, find='::skin.')
        else:
            node_tag = [data.get('tag'), data.get('name')]
            node_tag = [x for x in node_tag if x is not None]
            node_tag = ' '.join(node_tag)

        return node_tag

    @staticmethod
    def get_node_interface(node):
        data = {'node': None, 'tag': None, 'name': None}

        node_tag = node
        if isinstance(node, mx.Node):
            node_tag = Deformer.get_node_id(node, find='::skin.')

        for k in str(node_tag).split():
            if '::' in k:
                data['tag'] = k
            else:
                data['name'] = k

        return data

    def set_node_interface(self, node, subkey=None):
        if subkey is None:
            self.data.update(self.get_node_interface(node))
        else:
            data = self.data.get(subkey)
            if not isinstance(data, dict):
                self.data[subkey] = {}
            self.data[subkey].update(self.get_node_interface(node))


# edit class -----------------------------------------------------------------------------------------------------------


'''
# EP Curve to BSpline

cvfn = om1.MFnNurbsCurve()
pts = om1.MPointArray()
for cp in cps:
    pts.append(*cp)
mobj = cvfn.createWithEditPoints(pts, 3, om1.MFnNurbsCurve.kOpen, False, False, True)

cvs = om1.MPointArray()
cvfn.getCVs(cvs)
cps = [[cvs[x][0], cvs[x][1]] for x in range(cvfn.numCVs())]

sel = om1.MSelectionList()
sel.add(mobj)
obj = []
sel.getSelectionStrings(obj)
pm.delete(obj)

self.spline = NURBS.Curve()
self.spline.degree = 3
self.spline.ctrlpts = cps
self.spline.knotvector = generate_knot_vector(3, len(cps))
'''


class NurbsWeightMap(object):
    def __init__(self, nrb=None):

        if nrb is None:
            nrb = mx.ls(sl=1, et='transform')
            if nrb:
                nrb = nrb[0]
        elif not isinstance(nrb, mx.Node):
            nrb = mx.encode(str(nrb))

        shp = None
        if nrb and nrb.is_a(mx.tTransform):
            shp = nrb.shape()

        if not shp and not shp.is_a(mx.tNurbsCurve) and not shp.is_a(mx.tNurbsSurface):
            raise RuntimeError('argument is not a nurbs')

        self.nrb = nrb
        self.shp = shp
        self.cfg = ConfigParser(nrb)
        data = ordered_load(self.cfg['nmap'].read())
        if not isinstance(data, dict):
            raise RuntimeError('data not valid!')

        # validate binding correspondence
        self.infs = []
        self.mapping = {}

        self.remap = None
        self.remap_u = None
        self.remap_v = None

        self.auto = data.get('auto', False)
        self.switch = data.get('switch', False)

        for k, inf_list in iteritems(data):
            if k == 'u':
                k = 0

            if isinstance(k, (int, float)):

                # copy list
                if isinstance(inf_list, (int, float)):
                    self.mapping[float(k)] = float(inf_list)
                    continue

                # parse influences
                u = []
                for e in inf_list:
                    cv = []
                    for inf in e.strip().split('+'):
                        inf = inf.strip()
                        f = 1
                        if '*' in inf:
                            _inf = [x.strip() for x in inf.split('*')]
                            inf = None
                            if re_is_float.match(_inf[0]):
                                f = float(_inf[0])
                                inf = _inf[1]
                            elif re_is_float.match(_inf[1]):
                                f = float(_inf[1])
                                inf = _inf[0]

                        # store influence and assign id
                        if inf not in self.infs:
                            self.infs.append(inf)
                        inf = self.infs.index(inf)

                        # build mapping by ids
                        cv.append((inf, f))

                    # conform weight
                    infs, weights = zip(*cv)
                    weights = [w / float(sum(weights)) for w in weights]
                    cv = list(zip(infs, weights))

                    u.append(cv)

                self.mapping[float(k)] = u

        # conform parameters
        for k, _map in iteritems(self.mapping):
            if isinstance(_map, float):
                if _map in self.mapping:
                    self.mapping[k] = self.mapping[_map][:]
                else:
                    raise RuntimeError('/!\\ invalid index to copy ({} is not defined)'.format(_map))

        max_len_u = 0
        for k, _map in iteritems(self.mapping):
            if len(_map) > max_len_u:
                max_len_u = len(_map)
        for k, _map in iteritems(self.mapping):
            if 1 < len(_map) < max_len_u:
                raise RuntimeError('/!\\ remap grid is invalid')
        for k, _map in iteritems(self.mapping):
            if len(_map) == 1:
                self.mapping[k] = _map * max_len_u

        # remap v?
        if len(self.mapping) > 1:
            v = list(self.mapping)
            v.sort()

            nv = len(v)
            max_v = max(v)

            do_remap_v = False
            for x in [(nv - 1) * x / max_v for x in v]:
                if x != int(x):
                    do_remap_v = True

            if do_remap_v:
                _input = [x / max_v for x in v]
                _output = [float(x) / (nv - 1) for x in range(nv)]
                self.remap_v = SplineRemap(_input, _output)

            _mapping = {}
            for i, k in enumerate(v):
                _mapping[i] = self.mapping[k]
            self.mapping = _mapping

        # build
        degree_v = None
        if self.shp.is_a(mx.tNurbsSurface):
            fn = om.MFnNurbsSurface(self.shp.object())
            degree_u = fn.degreeInU
            degree_v = fn.degreeInV
            if self.switch:
                degree_u = fn.degreeInV
                degree_v = fn.degreeInU
        else:
            fn = om.MFnNurbsCurve(self.shp.object())
            degree_u = fn.degree

        periodic_v = False
        if self.shp.is_a(mx.tNurbsSurface):
            periodic_u = fn.formInU == fn.kPeriodic
            periodic_v = fn.formInV == fn.kPeriodic
            if self.switch:
                periodic_u = fn.formInV == fn.kPeriodic
                periodic_v = fn.formInU == fn.kPeriodic
        else:
            periodic_u = fn.form == fn.kPeriodic

        degree_u = data.get('degree_u', data.get('degree', degree_u))
        degree_v = data.get('degree_v', degree_v)

        # remaps
        nu = len(self.mapping[0])
        nv = len(self.mapping)
        if nu > 1:
            if degree_u >= nu:
                degree_u = nu - 1
        if nv > 1:
            if degree_v >= nv:
                degree_v = nv - 1

        if self.shp.is_a(mx.tNurbsSurface):
            self.remap = NurbsSurfaceRemap(nu, nv, (degree_u, degree_v), (periodic_u, periodic_v))
        else:
            self.remap = NurbsCurveRemap(nu, degree_u, periodic_u)

    def convert(self, geo, space=mx.sWorld, orig=False, tolerance=.00000001):

        # tmp projection target world space
        nrb = mc.duplicate(str(self.nrb), rr=1, rc=1)
        nrb = mx.encode(nrb[0])
        for attr in ('s', 'r', 't'):
            for dim in ('', 'x', 'y', 'z'):
                nrb[attr + dim].unlock()
        if nrb.parent():
            mc.parent(str(nrb), w=1)
        mc.makeIdentity(str(nrb), a=1)
        _shp = nrb.shape()

        # projection points
        if not isinstance(geo, mx.Node):
            geo = mx.encode(str(geo))
        if geo and geo.is_a(mx.tTransform):
            for shp in geo.shapes():
                if shp['io'].read() == int(orig):
                    geo = shp
                    break

        if not geo.is_a((mx.tMesh, mx.tNurbsCurve, mx.tNurbsSurface, mx.tLattice)):
            raise RuntimeError('not a valid geometry for conversion')

        # get point positions
        if geo.is_a(mx.tMesh):
            fn = om.MFnMesh(geo.dag_path())
            pts = fn.getPoints(space)
        elif geo.is_a(mx.tLattice):
            _u = geo['uDivisions'].read()
            _t = geo['tDivisions'].read()
            _s = geo['sDivisions'].read()
            pts = []
            for u in range(_u):
                for t in range(_t):
                    for s in range(_s):
                        pts.append(mc.xform('{}.pt[{}][{}][{}]'.format(geo, s, t, u), q=1, t=1, ws=1))
        else:
            pts = mc.ls('{}.cv[*]'.format(geo), fl=1)
            pts = [mc.pointPosition(pt, w=1) for pt in pts]

        n = len(pts)

        # get uv mapping
        u = []
        v = []

        if _shp.is_a(mx.tNurbsCurve):
            pts = [mx.Point(p) for p in pts]

            fn = om.MFnNurbsCurve(_shp.dag_path())

            mu = _shp['max'].read()
            for i in range(n):
                p, pu = fn.closestPoint(pts[i], space=space, tolerance=tolerance)
                u.append(pu / mu)
        else:
            # MFnNurbsSurface.closestPoint est complètement à la ramasse dans Maya 2018
            # on va devoir utiliser l'api 1 pour cette partie

            pts = [om1.MPoint(*p) for p in pts]

            mobj = mx._encode1(str(_shp))
            mdag = om1.MDagPath.getAPathTo(mobj)
            fn = om1.MFnNurbsSurface(mdag)

            u_util = om1.MScriptUtil()
            u_util.createFromDouble(0)
            u_param = u_util.asDoublePtr()

            v_util = om1.MScriptUtil()
            v_util.createFromDouble(0)
            v_param = v_util.asDoublePtr()

            mu = _shp['maxValueU'].read()
            mv = _shp['maxValueV'].read()

            for i in range(n):
                fn.closestPoint(pts[i], u_param, v_param, tolerance, space)
                pu = om1.MScriptUtil.getDouble(u_param)
                pv = om1.MScriptUtil.getDouble(v_param)

                _u = pu / mu
                _v = pv / mv
                _u = max(min(_u, 1), 0)
                _v = max(min(_v, 1), 0)
                if not self.switch:
                    u.append(_u)
                    v.append(_v)
                else:
                    u.append(_v)
                    v.append(_u)

        mx.delete(nrb)

        # remap projections if needed
        if self.remap_u:
            u = [self.remap_u.get(_u) for _u in u]
        if self.remap_v:
            v = [self.remap_v.get(_v) for _v in v]

        # init deformer
        dfm_data = {
            'deformer': 'skin',
            'transform': geo.parent(),
            'data': {
                'mmi': False
            }
        }
        dfm = Deformer(**dfm_data)

        for i, inf in enumerate(self.infs):
            dfm.data['maps'][i] = WeightMap([0.0] * n)
            dfm.data['infs'][i] = inf

        # build maps
        nu = len(self.mapping[0])
        nv = len(self.mapping)

        infs = []
        for _v in range(nv):
            for _u in range(nu):
                infs.append(self.mapping[_v][_u])

        for vtx in range(n):
            if not v:
                weights = self.remap.get(u[vtx])
            else:
                weights = self.remap.get(u[vtx], v[vtx])

            for i, _infs in enumerate(infs):
                w = weights[i]
                for inf, f in _infs:
                    dfm.data['maps'][inf].weights[vtx] += w * f

        dfm.normalize()
        return dfm
