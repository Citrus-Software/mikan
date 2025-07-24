# coding: utf-8

import meta_nodal_py as kl

from mikan.core import abstract
from mikan.core.tree import SuperTree
from mikan.core.utils import flatten_list
from mikan.core.logger import create_logger, timed_code
from mikan.tangerine.lib.commands import ls, add_plug
from mikan.tangerine.lib.rig import create_srt_in, find_srt, create_srt_out

__all__ = ['Nodes', 'parse_nodes']

log = create_logger()


class Nodes(abstract.Nodes):

    @classmethod
    def rebuild(cls):
        cls.flush()

        paths = {}
        cls.rebuild_assets()
        for _node, k in cls.assets.items():
            cls.nodes[k] = SuperTree()
            cls.shapes[k] = SuperTree()
            paths[_node.get_full_name() + '/'] = k

        cls.nodes[''] = SuperTree()
        cls.shapes[''] = SuperTree()

        # get all ids
        nodes = ls()
        for node in nodes:
            if not node.get_dynamic_plug('gem_id'):
                continue
            asset = cls.get_asset_id(node, paths)
            if node in cls.assets:
                cls.nodes[asset]['::asset'] = node
                continue
            for key in node.gem_id.get_value().split(';'):
                if key and '::' not in key:
                    cls.nodes[asset][key + '::template'] = node
                cls.nodes[asset][key] = node

        for node in nodes:
            if not node.get_dynamic_plug('gem_shape'):
                continue
            asset = cls.get_asset_id(node, paths)
            for key in node.gem_shape.get_value().split(';'):
                if key not in cls.shapes:
                    cls.shapes[asset][key] = node

    @classmethod
    def rebuild_assets(cls):
        nodes = ls()
        asset_nodes = []

        # index all asset nodes
        for node in nodes:
            if node.get_dynamic_plug('gem_type'):
                if node.gem_type.get_value() == 'asset':
                    asset_nodes.append(node)
        asset_nodes = sorted(asset_nodes, key=lambda x: x.get_full_name())

        _nodes = []
        _nodes_new = []
        for node in asset_nodes:
            if node.get_dynamic_plug('gem_index'):
                _nodes.append(node)
            else:
                _nodes_new.append(node)
        asset_nodes = _nodes + _nodes_new

        # build asset tree
        try:
            old_assets = cls.assets.copy()
        except:
            old_assets = {}
        cls.assets.clear()

        for node in asset_nodes:
            if not node.get_dynamic_plug('gem_id'):
                continue
            name = node.gem_id.get_value()
            if not node.get_dynamic_plug('gem_index'):
                add_plug(node, 'gem_index', int)

            n = node.gem_index.get_value()
            while True:
                k = f'{name}.{n}'
                if k in cls.assets.values():
                    n += 1
                else:
                    if node.gem_index.get_value() != n:
                        node.gem_index.set_value(n)
                    break

            cls.assets[node] = k

            cls.geometries[k] = [node]
            if node.get_dynamic_plug('gem_geometries'):
                from .deformer import Deformer
                paths = node.gem_geometries.get_value().strip()
                if paths:
                    for path in paths.split(';'):
                        try:
                            geo = Deformer.get_node(path)
                            cls.geometries[k].append(geo)
                        except:
                            log.warning(f'/!\\ failed to resolve asset {k} geometry path: {path}')

        # rebuild check
        for node, k in old_assets.items():
            if cls.assets.get(node) != k:
                cls.rebuild()
                return

    @classmethod
    def set_asset_id(cls, node, name):

        if not node.get_dynamic_plug('gem_id'):
            add_plug(node, 'gem_id', str)
        node.gem_id.set_value(name)

        if not any(cls.nodes.values()):
            cls.rebuild()
        cls.rebuild_assets()

        k = cls.assets[node]
        if k not in cls.nodes:
            cls.nodes[k] = SuperTree()
            cls.nodes[k]['::asset'] = node
        if k not in cls.shapes:
            cls.shapes[k] = SuperTree()

    @classmethod
    def get_asset_paths(cls):
        paths = {}
        for _node, k in cls.assets.items():
            paths[_node.get_full_name() + '/'] = k
        return paths

    @classmethod
    def get_asset_id(cls, node, paths=None, recursive=None):
        if node is None:
            return ''
        if paths is None:
            paths = cls.get_asset_paths()
        if recursive is None:
            recursive = []

        dags = []
        if isinstance(node, kl.SceneGraphNode):
            dags = [node]
        for _plug in node.get_plugs():
            _input = _plug.get_input()
            if _input:
                _node = _input.get_node()
                if isinstance(_node, kl.SceneGraphNode):
                    dags.append(_node)

        asset = ''
        for dag in dags:
            dag_path = dag.get_full_name() + '/'
            for path in paths:
                if dag_path.startswith(path):
                    return paths[path]

        inputs = []
        for _plug in node.get_plugs():
            _input = _plug.get_input()
            if _input:
                inputs.append(_input.get_node())
        for node in inputs:
            if isinstance(node, kl.SceneGraphNode):
                continue
            if node in recursive:
                continue
            recursive.append(node)
            asset = cls.get_asset_id(node, paths, recursive=recursive)
            if asset:
                return asset

        return asset

    @classmethod
    def set_id(cls, node, tag):
        if not any(cls.nodes.values()):
            cls.rebuild()

        if not node.get_dynamic_plug('gem_id'):
            add_plug(node, 'gem_id', str)

        gem_id = node.gem_id.get_value()

        ids = [k for k in gem_id.split(';') if k]
        if tag not in ids:
            ids.append(tag)
            gem_id = ';'.join(ids)

            node.gem_id.set_value(gem_id)

        asset = cls.current_asset
        if asset is None:
            asset = cls.get_asset_id(node)

        cls.nodes[asset][tag] = node

    @staticmethod
    def get_node_id(node, find=None, deformer=False):
        if node.get_dynamic_plug('gem_id'):
            gem_id = node.gem_id.get_value()
            ids = gem_id.split(';')
            node_id = ids[0]
            if find and str(find) in gem_id:
                for _id in ids:
                    if find in _id:
                        node_id = _id
                        break
            if deformer:
                return node_id + ' ' + node.get_name()
            return node_id
        raise RuntimeError(f'{node} has no id')

    @staticmethod
    def get_node_plug(node, plug_name, add=True):

        # conform DAG plugs
        srt_vectors = {'s': 'scale', 'r': 'rotate', 't': 'translate', 'j': 'joint_orient_rotate'}

        if len(plug_name) == 3 and plug_name[1] == '.' and plug_name[0] in 'srtj' and plug_name[2] in 'xyz':
            # find srt
            if not node.transform.is_connected():
                create_srt_in(node)
            srt = find_srt(node)

            # find srt vector
            vector = None

            if isinstance(srt, (kl.SRTToTransformNode, kl.SRTToJointTransform)):
                # srt in
                vector_plug = srt.get_plug(srt_vectors[plug_name[0]])
                vector_in = vector_plug.get_input()
                if kl.is_plug(vector_in):
                    vector = vector_in.get_node()

                # hacked srt (IK/FK switch)
                transform_in = node.transform.get_input().get_node()
                if srt != transform_in:
                    vector = None

            else:
                vector = srt.find(srt_vectors[plug_name[0]])

            if vector:
                # check vector in
                if isinstance(vector, kl.FloatToV3f):
                    if not vector.vector.get_outputs():
                        vector = None
                elif isinstance(vector, kl.FloatToEuler):
                    if not vector.euler.get_outputs():
                        vector = None
                # check vector out
                elif isinstance(vector, kl.V3fToFloat):
                    if not vector.vector.get_input():
                        vector = None
                elif isinstance(vector, kl.EulerToFloat):
                    if not vector.euler.get_input():
                        vector = None
                # invalid node
                else:
                    vector = None

            if not vector:
                srt_out = create_srt_out(node)
                srt_out.rotate_order.connect(srt.rotate_order)
                vector = srt_out.find(srt_vectors[plug_name[0]])

            return vector.get_plug(plug_name[2])

        if isinstance(node, kl.SceneGraphNode):
            if plug_name in 'srt':
                if not node.transform.is_connected():
                    create_srt_in(node)
                srt = find_srt(node)
                return srt.get_plug(srt_vectors[plug_name])

            if plug_name in {'xfo', 'ixfo', 'pxfo', 'pixfo', 'wxfo', 'wixfo'}:
                plug_name = plug_name.replace('xfo', 'm')

            if plug_name in {'m', 'im', 'pm', 'pim', 'wm', 'wim'}:
                plug = node.transform
                if plug_name[0] == 'p':
                    plug = node.parent_world_transform
                elif plug_name[0] == 'w':
                    plug = node.world_transform

                if 'i' in plug_name:
                    imx = None
                    for o in plug.get_outputs():
                        o = o.get_node()
                        if isinstance(o, kl.InverseM44f):
                            imx = o
                            break
                    if not imx:
                        imx = kl.InverseM44f(node, '_imx')
                        imx.input.connect(plug)
                    return imx.output
                return plug

        if plug_name in ('v', 'vis', 'visibility'):
            plug_name = 'show'

        # get plug
        plug = node.get_plug(plug_name)
        if not plug:
            if add:
                k = False
                if not plug_name.startswith('_') and node.get_dynamic_plug('gem_id') and '::ctrls.' in node.gem_id.get_value():
                    k = True
                return add_plug(node, plug_name, float, k=k)
            else:
                return

        return plug

    @classmethod
    def get_id_children(cls, tag, as_dict=False):
        from .template import Template  # avoid circular import

        root_id, sep, key = tag.partition(':::')
        asset_id, sep, root_id = root_id.rpartition('#')
        root_id, sep, root_branch = root_id.partition('.')
        root_branch = sep + root_branch
        root = cls.get_id(root_id)
        if not root:
            return []

        tpl_root = Template(root)
        children = tpl_root.get_all_children()
        _children = set(children)

        with timed_code(f'get tag {tag}', force=1):
            names = [root_id] + [tpl.name for tpl in children]
            names = set(names)

            asset_id = Nodes.get_asset_id(tpl_root.node)
            if asset_id:
                tpl_asset = Nodes.get_id(asset_id + '#::template')
                if tpl_asset:
                    for i in tpl_asset.depth_first_skippable_iterator():
                        node = i.node
                        if not (isinstance(node, kl.SceneGraphNode) or type(node) == kl.Node):
                            i.skip_children()
                            continue

                        if node.get_dynamic_plug('gem_type') and node.gem_type.get_value() == Template.type_name:
                            tpl = Template(node)

                            group = tpl.get_opt('group')
                            if group in names:
                                if tpl not in _children:
                                    children.append(tpl)
                                    _children.add(tpl)
                                for tpl in tpl.get_all_children():
                                    if tpl not in _children:
                                        children.append(tpl)
                                        _children.add(tpl)

        nodes = []
        for tpl in [tpl_root] + children:
            _tag = tpl.name + root_branch + '::' + key
            _nodes = cls.get_id(_tag, as_dict)
            if _nodes:
                nodes.append(_nodes)

        if as_dict:
            nodes_dict = {}
            for _nodes in nodes:
                nodes_dict.update(_nodes)
        else:
            return list(flatten_list(nodes))


def parse_nodes(data, failed=None, exclude=None, root=None, silent=False):
    if failed is None:
        failed = []
    if exclude is None:
        exclude = []

    if isinstance(data, dict):
        new_data = type(data)()
        for k, v in data.items():
            if k in exclude:
                new_data[k] = v
                continue
            if isinstance(k, str) and ('::' in k or '->' in k):
                k = parse_node(k, failed=failed, silent=silent)
                if isinstance(k, list):
                    if len(k) == 1:
                        k = k[0]
                    else:
                        k = tuple(k)
            new_data[k] = parse_nodes(v, failed=failed, root=root, silent=silent)
        return new_data

    elif isinstance(data, list):
        return [parse_nodes(e, failed=failed, silent=silent) for e in data]

    elif isinstance(data, str):
        if '::' in data or '->' in data:
            return parse_node(data, failed=failed, root=root, silent=silent)

    return data


def parse_node(tag, failed=None, root=None, silent=False, add_hook=True):
    from .deformer import Deformer

    if failed is None:
        failed = []

    if '::' in tag:
        try:
            if len(tag.split()) > 1:
                result = Deformer.get_node(tag, root)
            else:
                result = Nodes.get_id(tag)
            if result is None:
                raise KeyError()
            return result
        except:
            failed.append(tag)
            return

    elif '->' in tag:
        try:
            nodes = Deformer.get_geometry_id(tag, root=root, add_hook=add_hook)
            if not nodes[0]:
                raise RuntimeError('failed to resolve id')
        except Exception as e:
            if log.level <= 10 and not silent:
                log.error(e)
            failed.append(tag)
            if '@' in tag or tag.endswith('->xfo'):
                return
            else:
                return [None, None]

        if '@' in tag:
            return nodes[0]
        if tag.endswith('->xfo') or tag.endswith('->'):
            return nodes[1]
        return nodes


# hack kernel node copy/deepcopy

def _copy(self):
    return self


def _deepcopy(self, obj):
    return self


kl.Node.__copy__ = _copy
kl.Node.__deepcopy__ = _deepcopy
kl.Plug_base.__copy__ = _copy
kl.Plug_base.__deepcopy__ = _deepcopy
