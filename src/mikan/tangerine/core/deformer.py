# coding: utf-8

import yaml
from copy import deepcopy

import meta_nodal_py as kl

from mikan.core import abstract
from mikan.core.logger import create_logger
from mikan.core.abstract.deformer import DeformerError
from ..lib.configparser import ConfigParser
from ..lib.commands import *

from .node import Nodes, parse_nodes

WeightMap = abstract.WeightMap
WeightMapInterface = abstract.WeightMapInterface

__all__ = ['Deformer', 'DeformerError', 'WeightMap']

log = create_logger()


class Deformer(abstract.Deformer):
    software = 'tangerine'

    def __repr__(self):
        if self.transform or self.transform_id:
            if self.transform:
                node_name = Deformer.get_unique_name(self.transform, root=self.root)
            else:
                node_name = self.transform_id
            if self.id:
                return f"Deformer('{self.deformer}', id='{self.id}', transform='{node_name}')"
            else:
                return f"Deformer('{self.deformer}', transform='{node_name}')"
        else:
            return f"Deformer('{self.deformer}')"

    def encode_data(self):
        data = f'deformer: {self.deformer}\n'
        _d = deepcopy(self.data)

        if self.transform:
            node_name = Deformer.get_unique_name(self.transform, root=self.root)
            data += f'transform: {node_name}\n'
            if 'transform' in _d:
                del _d['transform']

        if self.node:
            data += f'id: {self.set_id()}\n'
        elif self.id:
            data += f'id: {self.id}\n'

        if self.geometry_id:
            data += f'geometry_id: {self.geometry_id}\n'

        if self.order:
            data += f'order: {self.order}\n'
        if self.input_id:
            data += f'input_id: {self.input_id}\n'
        if self.output_id:
            data += f'output_id: {self.output_id}\n'

        if self.protected:
            data += 'protected: true\n'
        if self.decimals != self.default_decimals:
            data += f'decimals: {self.decimals}\n'

        data += yaml.dump({'data': _d}, Dumper=abstract.DeformerDumper, default_flow_style=False)

        try:
            data = f'#!{self.priority}\n{data}'
        except:
            pass

        return data

    @classmethod
    def parse(cls, ini):

        # get data
        root = None
        if ConfigParser.is_section(ini):
            raw_data = ini.read()

            node = ini.parser.node
            while node:
                if node.get_dynamic_plug('gem_deformers'):
                    root = node.gem_deformers.get_value()
                    break
                else:
                    node = node.get_parent()
                    if isinstance(node, kl.RootNode):
                        node = None
        else:
            raw_data = str(ini)

        data = yaml.load(raw_data, abstract.DeformerLoader)
        if root:
            data['root'] = root

        if ConfigParser.is_section(ini):
            data['ini'] = ini

        return data

    def parse_nodes(self):
        del self.unresolved[:]

        # get root
        if self.root is None and self.root_id:
            try:
                node = Deformer.get_node(self.root_id)
            except:
                node = None
                self.unresolved.append(self.root_id)
            if node:
                self.root = node

        # get transform (check under group root if any)
        if self.transform is None and self.transform_id:
            try:
                node = Deformer.get_node(self.transform_id, root=self.root)
            except:
                node = None
            if node:
                self.transform = node

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

    @staticmethod
    def create(geo, deformer, root=None):
        pass

    def reorder(self):
        if not any((self.order, self.output[0], self.input[0])):
            return

        plug_out = self.get_output()
        plug_dst = plug_out.get_outputs()[0]

        plug_in = self.get_input()
        plug_src = plug_in.get_input()

        if self.order == 'isolated':
            plug_dst.connect(plug_src)

        elif self.order == 'front':
            node_src = Deformer._get_deformed_geo(self.node, self.transform, source=True)
            plug_front = Deformer.get_deformer_output(node_src, self.transform)
            if not plug_front:
                log.error(f'/!\\ couldn\'t find origin connexion of {self.geometry}')
                return

            # find former source output
            former_plug_dst = None
            for _output in plug_front.get_outputs():
                _output_node = _output.get_node()
                if _output_node.get_parent() == self.geometry:
                    former_plug_dst = _output
                    break

            # reconnect deformer input/output
            if former_plug_dst:
                former_plug_dst.connect(plug_out)
            plug_in.connect(plug_front)

            plug_dst.connect(plug_src)

        node, xfo = self.output
        if node is not None:
            # connect source to disconnected stream
            if plug_dst.can_connect(plug_src):  # check cycles
                plug_dst.connect(plug_src)
            else:
                log.critical(f'/!\\ input reorder aborted to prevent cycle ({self.output_id})')

        node, xfo = self.input
        if node is not None:
            if isinstance(node, (kl.Deformer, kl.Geometry)):
                dfm_output = Deformer.get_deformer_output(node, xfo)
                if plug_in.can_connect(dfm_output):  # check cycles
                    plug_in.connect(dfm_output)
                else:
                    log.critical(f'/!\\ input reorder aborted to prevent cycle ({self.input_id})')
            elif kl.is_plug(node):
                if plug_in.can_connect(node):  # check cycles
                    plug_in.connect(node)
                else:
                    log.critical(f'/!\\ input reorder aborted to prevent cycle ({self.input_id})')

        node, xfo = self.output
        if node is not None:
            if isinstance(node, (kl.Deformer, kl.Geometry)):
                dfm_input = Deformer.get_deformer_input(node, xfo)
                if dfm_input.can_connect(plug_out):  # check cycles
                    dfm_input.connect(plug_out)
                else:
                    log.critical(f'/!\\ output reorder aborted to prevent cycle ({self.output_id})')
            elif kl.is_plug(node):
                if node.can_connect(plug_out):  # check cycles
                    node.connect(plug_out)
                else:
                    log.critical(f'/!\\ output reorder aborted to prevent cycle ({self.output_id})')

    @staticmethod
    def get_geo_deformers(geo):
        # get all deformer from history
        deformers = []

        for shape in geo.get_children():
            if isinstance(shape, kl.Geometry):
                for node in shape.get_children():
                    cls = Deformer.get_cls_from_node(node)
                    if cls and node not in deformers:
                        deformers.append(node)

        return deformers

    @staticmethod
    def _get_deformed_geo(node, transform, source=False):
        if isinstance(node, (kl.Deformer, kl.SubdivMesh)):
            parent = node.get_parent()

            if not source:
                if isinstance(parent, kl.Geometry):
                    return parent
            else:
                xfo = parent.get_parent()
                for child in xfo.get_children():
                    if type(child) == kl.Node and child.get_name() == 'source':
                        return child

        elif isinstance(node, kl.Geometry):
            return node

        elif type(node) == kl.Node:
            return node

    @staticmethod
    def get_deformer_output(node, transform):
        shape = Deformer._get_deformed_geo(node, transform)
        if not shape:
            return
        if isinstance(node, kl.Deformer):
            if node.mesh_out.get_outputs() or node.mesh_in.get_input():
                return node.mesh_out
            if node.spline_out.get_outputs() or node.spline_in.get_input():
                return node.spline_out
        elif isinstance(node, kl.SubdivMesh):
            return node.mesh_out
        elif isinstance(node, kl.SplineCurve):
            return node.spline_in
        elif isinstance(node, kl.Geometry):
            return node.mesh_in
        elif type(node) == kl.Node:
            if node.get_dynamic_plug('mesh_out'):
                return node.mesh_out
            elif node.get_dynamic_plug('spline_out'):
                return node.spline_out

    @staticmethod
    def get_deformer_input(node, transform):
        shape = Deformer._get_deformed_geo(node, transform)
        if not shape:
            return
        if isinstance(node, kl.Deformer):
            mesh_out = node.mesh_out.get_outputs()
            if mesh_out:
                return node.mesh_in
            spline_out = node.spline_out.get_outputs()
            if spline_out:
                return node.spline_in
        elif isinstance(node, kl.SubdivMesh):
            return node.animated_mesh_in
        elif isinstance(node, kl.Geometry):
            if type(node) == kl.Geometry:
                return node.mesh_in
            elif isinstance(node, kl.SplineCurve):
                return node.spline_in
        elif type(node) == kl.Node:
            if node.get_dynamic_plug('mesh_in'):
                return node.mesh_in
            elif node.get_dynamic_plug('spline_in'):
                return node.spline_in

    def get_input(self):
        if self.transform:
            return Deformer.get_deformer_input(self.node, self.transform)

    def get_output(self):
        if self.transform:
            plug_out = Deformer.get_deformer_output(self.node, self.transform)
            return plug_out

    @staticmethod
    def get_deformer_ids(xfo, root=None):
        ids = {}
        name = Deformer.get_unique_name(xfo, root=root)

        for node in Deformer.get_geo_deformers(xfo):
            if node.get_dynamic_plug('gem_deformer'):
                for tag in (node.gem_deformer.get_value() or '').split(';'):
                    if tag.startswith(name):
                        ids[tag.split('->')[-1]] = node

        for node in [shp for shp in xfo.get_children() if isinstance(shp, kl.Geometry)]:
            if node.get_dynamic_plug('gem_deformer'):
                for tag in (node.gem_deformer.get_value() or '').split(';'):
                    ids[tag.split('->')[-1]] = node

        if 'shape' not in ids:
            for node in xfo.get_children():
                if isinstance(node, kl.Geometry) and node.show.get_value():
                    ids['shape'] = node
                    break

        if 'source' not in ids:
            for node in xfo.get_children():
                if type(node) == kl.Node and node.get_name() == 'source':
                    ids['source'] = node

                elif isinstance(node, kl.Geometry) and not node.show.get_value():
                    if node not in ids.values():
                        ids['source'] = node
                        break

        if 'source' not in ids and 'shape' in ids:
            # build proxy
            geo_cls = type(ids['shape'])
            value_type = None
            plug_name = None

            if geo_cls == kl.Geometry:
                value_type = kl.Mesh
                plug_name = 'mesh'
            elif geo_cls == kl.SplineCurve:
                value_type = kl.Spline
                plug_name = 'spline'

            if value_type:
                source = kl.Node(xfo, 'source')
                shape_in = Deformer.get_deformer_input(ids['shape'], xfo)

                plug = add_plug(source, plug_name + '_out', value_type)
                source_out = shape_in.get_input()
                if source_out:
                    plug.connect(source_out)
                else:
                    plug.set_value(shape_in.get_value())
                shape_in.connect(plug)

                ids['source'] = source

        ids['xfo'] = xfo
        return ids

    @staticmethod
    def get_geometry_id(tag, root=None, add_hook=False):
        """Resolve a geometry id from a string of form transform->deformer/geometry(@hook)

        Arguments:
            tag (str): the geometry id to resolve
            root (kl.Node, optional): root node to help resolve path

        Returns:
            (kl.Node|kl.Plug, kl.Node): a tuple containing the object
            resolved from the id and its associated transform node
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
            if tag in dfm_ids:
                dfm = dfm_ids[tag]
                if hook:
                    if isinstance(dfm, kl.SceneGraphNode):
                        return Nodes.get_node_plug(dfm, hook, add=add_hook), xfo
                    return Deformer.get_deformer_plug(dfm, xfo, hook), xfo
                else:
                    return dfm, xfo
            else:
                return None, xfo
        else:
            return xfo, xfo

    def set_geometry_id(self, node, key):
        if not node.get_dynamic_plug('gem_deformer'):
            add_plug(node, 'gem_deformer', str)

        transform = self.transform
        if isinstance(node, kl.Geometry):
            transform = node.get_parent()
        elif isinstance(node, kl.SceneGraphNode):
            transform = node

        name = Deformer.get_unique_name(transform, root=self.root)
        tags = (node.gem_deformer.get_value() or '').split(';')

        # find if already set (node under same self.transform)
        for tag in tags:
            if tag.startswith(f'{name}->{key}'):
                return tag.split('->')[-1]

        # assign new
        indices = []
        for tag in self.get_ids():
            if tag.startswith(key + '.'):
                try:
                    indices.append(int(tag.split('.')[-1]))
                except:
                    pass
        if not indices:
            indices.append(-1)

        if '.' in key:
            tag = f'{name}->{key}'
        else:
            tag = f'{name}->{key}.{max(indices) + 1}'

        # write ids
        tags.append(tag)
        if '' in tags:
            tags.remove('')
        node.gem_deformer.set_value(';'.join(tags))
        return tag.split('->')[-1]

    def set_id(self):
        if not self.node:
            return ''

        if self.id:
            self.set_geometry_id(self.node, self.id)
        else:
            self.id = self.set_geometry_id(self.node, self.deformer)

        return self.id

    def find_root(self):
        if isinstance(self.root, kl.SceneGraphNode):
            self.root_id = Deformer.get_unique_name(self.root)
        elif isinstance(self.root, str):
            self.root_id = self.root
            self.root = None

    def find_transform(self):
        if isinstance(self.transform, kl.SceneGraphNode):
            self.transform_id = Deformer.get_unique_name(self.transform, root=self.root)
        else:
            self.transform_id = self.transform
            self.transform = None

    def find_geometry(self):
        if self.geometry_id:
            node, xfo = self.get_geometry_id(self.geometry_id, self.root)
            if isinstance(node, kl.Geometry):
                self.geometry = node
                return node

        for child in self.transform.get_children():
            if type(child) in (kl.Geometry, kl.SplineCurve):
                self.geometry = child
                break

        if self.node:
            if isinstance(self.node, kl.Deformer):
                _p = self.node.get_parent()
                while True:
                    if isinstance(_p, kl.Geometry):
                        self.geometry = _p
                        break
                    _p = _p.get_parent()
            elif isinstance(self.node, kl.Geometry):
                self.geometry = self.node

        else:
            for node in self.transform.get_children():
                if not isinstance(node, kl.Geometry) or not node.show.get_value():
                    continue
                if node.get_dynamic_plug('gem_deformer') and '->data.' in node.gem_deformer.get_value():
                    continue
                self.geometry = node
                break

        if not self.geometry:
            raise RuntimeError(f'/!\\ failed to find the deformable geometry of {self.transform}')

    @staticmethod
    def get_deformer_plug(dfm, xfo, hook):
        cls = Deformer.get_cls_from_node(dfm)
        if cls:
            return cls.hook(dfm, xfo, hook)

    @staticmethod
    def get_unique_name(node, root=None):
        for k, n in Deformer._nodes.items():
            if n == node:
                return k

        # TODO: check si le root est bien un parent du node?

    @staticmethod
    def get_node(node_name, root=None):
        """Resolve a node from a list of ids and node paths

        Args:
            node_name (str): list of ids and paths separated by spaces
            root (kl.Node, optional): root to restrict the search for the node when using paths

        Returns:
            pm.PyNode: resolved node

        Raises:
            RuntimeError: if nothing is found
        """

        if not Deformer._nodes:
            Deformer.cache_nodes()

        if isinstance(node_name, kl.Node):
            return node_name

        root_node = find_root()
        trim = len(root_node.get_full_name())

        # find root
        if isinstance(root, str):
            root = Deformer.get_node(root)
        root_name = '/'
        if root:
            root_name = root.get_full_name()[trim:] + '/'

        # exclude other asset geometries
        exclude_roots = []
        if Nodes.current_asset is not None and len(Nodes.assets) > 1:
            for k in Nodes.geometries:
                if k == Nodes.current_asset:
                    continue
                exclude_roots += Nodes.geometries[k]

        # search loop
        name_loop = []
        for n in node_name.split():
            if '::' not in n:
                n = n.replace('|', '/')
            name_loop.append(n)
            if '::' not in n and ':' in n:
                n = '/'.join([_n.split(':')[-1] for _n in n.split('/')])
                name_loop.append(n)

        resolved = None
        overflow = False

        for n in name_loop:
            if '::' in n:
                n = Nodes.get_id(n)
                if n:
                    return n

            else:
                if n.startswith('/'):
                    n = n[1:]

                node = Deformer._nodes.get(n)
                if isinstance(node, list):
                    nodes = node
                else:
                    nodes = [node] if node is not None else []

                if '/' in n:
                    _nodes = []
                    for _node in Deformer._nodes.values():
                        if not isinstance(_node, list):
                            _node = [_node]
                        for _node0 in _node:
                            if _node0.get_full_name().endswith(n) and _node0 not in _nodes:
                                _nodes.append(_node0)
                    nodes = _nodes

                # filter excluded geometries
                if len(nodes) > 1:
                    for _node in nodes[:]:
                        for path_node in exclude_roots:
                            path = path_node.get_full_name()[trim:] + '/'

                            if _node == path_node or _node.get_full_name()[trim:].startswith(path):
                                nodes.remove(_node)
                                break

                # filter root path
                if len(nodes) > 1:
                    _nodes = []
                    for _node in nodes:
                        _node_name = _node.get_full_name()[trim:]
                        if _node_name.startswith(root_name):
                            _nodes.append(_node)
                    nodes = _nodes

                if len(nodes) > 1:
                    overflow = True

                if len(nodes) == 1:
                    resolved = nodes[0]
                    break

        if not resolved:
            msg = f'no object name "{node_name}"'
            if overflow:
                msg = f'too many geometries named "{node_name}"'

            if root:
                msg += f' under root "{root_name}"'

            raise RuntimeError(msg)

        else:
            return resolved

    @staticmethod
    def get_node_id(node, find=None):
        if node.get_dynamic_plug('gem_id'):
            gem_id = node.gem_id.get_value() or ''
            if find and str(find) in gem_id:
                for tag in gem_id.split(';'):
                    if find in tag:
                        return tag + ' ' + str(node)
            return gem_id.split(';')[0] + ' ' + str(node)
        return str(node)

    _nodes = {}

    @classmethod
    def cache_nodes(cls):
        log.info('cache scene nodes for Deformer')
        cls._nodes = ls(as_dict=True)

    def get_size(self):
        if isinstance(self.geometry, kl.SplineCurve):
            return self.geometry.spline_in.get_value().get_vertices_count()
        else:
            return self.geometry.mesh_in.get_value().get_vertices_count()
