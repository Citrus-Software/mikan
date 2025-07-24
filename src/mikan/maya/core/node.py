# coding: utf-8

import re
import itertools
from six import string_types, iteritems

import maya.cmds as mc
from mikan.maya import cmdx as mx

from mikan.core import abstract
from mikan.core.tree import SuperTree
from mikan.core.utils import flatten_list, ordered_dict
from mikan.core.logger import create_logger, timed_code
from ..lib.configparser import ConfigParser

__all__ = ['Nodes', 'parse_nodes']

log = create_logger()


class Nodes(abstract.Nodes):

    @classmethod
    def rebuild(cls):
        mx.clear_instances()
        cls.flush()

        paths = {}
        cls.rebuild_assets()
        for _node, k in iteritems(cls.assets):
            cls.nodes[k] = SuperTree()
            cls.shapes[k] = SuperTree()
            paths[_node.path() + '|'] = k

        cls.nodes[''] = SuperTree()
        cls.shapes[''] = SuperTree()

        # get all ids
        for node in mx.ls('*.gem_id', r=1, o=1):
            asset = cls.get_asset_id(node, paths)
            if node in cls.assets:
                cls.nodes[asset]['::asset'] = node
                continue
            for key in node['gem_id'].read().split(';'):
                if key and '::' not in key:
                    cls.nodes[asset][key + '::template'] = node
                cls.nodes[asset][key] = node

        for node in mx.ls('*.gem_shape', r=1, o=1):
            asset = cls.get_asset_id(node, paths)
            for key in node['gem_shape'].read().split(';'):
                if key not in cls.shapes[asset]:
                    cls.shapes[asset][key] = node

    @classmethod
    def rebuild_assets(cls):

        # index all asset nodes
        nodes = []
        for node in mc.ls('*.gem_type', r=1, o=1):
            if mc.getAttr(node + '.gem_type') == 'asset':
                nodes.append(node)
        nodes.sort()

        _nodes = []
        _nodes_new = []
        for node in nodes:
            node = mx.encode(node)
            if 'gem_index' in node:
                _nodes.append(node)
            else:
                _nodes_new.append(node)
        nodes = _nodes + _nodes_new

        # build asset tree
        try:
            old_assets = cls.assets.copy()
        except:
            old_assets = ordered_dict()
        cls.assets.clear()

        for node in nodes:
            if 'gem_id' not in node:
                continue
            name = node['gem_id'].read()
            if 'gem_index' not in node:
                with mx.DagModifier() as md:
                    md.add_attr(node, mx.Long('gem_index'))

            n = node['gem_index'].read()
            while True:
                k = '{}.{}'.format(name, n)
                if k in cls.assets.values():
                    n += 1
                else:
                    if node['gem_index'].read() != n:
                        with mx.DagModifier() as md:
                            md.set_attr(node['gem_index'], n)
                    break

            cls.assets[node] = k

            cls.geometries[k] = [node]
            if 'gem_geometries' in node:
                from .deformer import Deformer
                paths = str(node['gem_geometries'].read()).strip()
                if paths:
                    for path in paths.split(';'):
                        try:
                            geo = Deformer.get_node(path)
                            cls.geometries[k].append(geo)
                        except:
                            log.warning('/!\\ failed to resolve asset {} geometry path: {}'.format(k, path))

            if node.is_referenced():
                ns = node.namespace()
                for _node in mx.ls('|{}:*'.format(ns)):
                    if _node != node:
                        cls.geometries[k].append(_node)

        # rebuild check
        for node, k in iteritems(old_assets):
            if cls.assets.get(node) != k:
                cls.rebuild()
                return

    @classmethod
    def set_asset_id(cls, node, name):
        if not isinstance(node, mx.Node):
            node = mx.encode(str(node))

        if 'gem_id' not in node:
            with mx.DagModifier() as md:
                md.add_attr(node, mx.String('gem_id'))
        node['gem_id'] = name

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
        try:
            for _node, k in iteritems(cls.assets):
                paths[_node.path() + '|'] = k
        except:
            Nodes.rebuild()
            for _node, k in iteritems(cls.assets):
                paths[_node.path() + '|'] = k
        return paths

    @classmethod
    def get_asset_id(cls, node, paths=None, recursive=None):
        if node is None:
            return ''
        if paths is None:
            paths = cls.get_asset_paths()
        if recursive is None:
            recursive = []

        if not isinstance(node, mx.Node):
            node = mx.encode(str(node))

        if node.is_a(mx.kTransform):
            dags = itertools.chain([node], node.inputs(type=mx.kTransform))
        else:
            dags = node.inputs(type=mx.kTransform)

        asset = ''
        for dag in dags:
            dag_path = dag.path() + '|'
            for path in paths:
                if dag_path.startswith(path):
                    return paths[path]

        for node in node.inputs():
            if node.is_a(mx.kTransform):
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

        if not isinstance(node, mx.Node):
            node = mx.encode(str(node))

        if 'gem_id' not in node:
            node.add_attr(mx.String('gem_id'))

        gem_id = node['gem_id'].read()

        ids = [k for k in gem_id.split(';') if k]
        if tag not in ids:
            ids.append(tag)
            gem_id = ';'.join(ids)

            node['gem_id'] = gem_id

        asset = cls.current_asset
        if asset is None:
            asset = cls.get_asset_id(node)

        cls.nodes[asset][tag] = node

    @classmethod
    def remove_id(cls, tag):
        if not any(cls.nodes.values()):
            cls.rebuild()

        # clear dictionnary
        asset = cls.current_asset
        try:
            node = cls.nodes[asset][tag]
        except Exception:
            return

        del cls.nodes[asset][tag]

        # cleanup node id
        if not isinstance(node, mx.Node):
            return

        gem_id = node['gem_id'].read()

        ids = [k for k in gem_id.split(';') if k]
        if tag in ids:
            ids.remove(tag)
            gem_id = ';'.join(ids)

            node['gem_id'] = gem_id

    @staticmethod
    def get_node_id(node, find=None):
        if not isinstance(node, mx.Node):
            node = mx.encode(str(node))

        if 'gem_id' in node:
            gem_id = node['gem_id'].read()
            ids = gem_id.split(';')
            node_id = ids[0]
            if find and str(find) in gem_id:
                for _id in ids:
                    if find in _id:
                        node_id = _id
                        break
            return node_id
        raise RuntimeError('{} has no id'.format(node))

    @staticmethod
    def get_node_plug(node, plug_name, add=True):

        # deprecation
        if len(plug_name) == 2 and plug_name[0] in 'srt' and plug_name[1] in 'xyz':
            log.warning('/!\\ plug "{}" from node "{}" is invalid and will only work for Maya. Use "{}.{}" instead.'.format(plug_name, node, plug_name[0], plug_name[1]))

        elif (plug_name.startswith('translate') or plug_name.startswith('rotate') or plug_name.startswith('scale')) and plug_name[-1] in 'XYZ':
            log.warning('/!\\ plug "{}" from node "{}" is invalid and will only work for Maya. Use "{}.{}" instead.'.format(plug_name, node, plug_name[0], plug_name[-1].lower()))

        # conform DAG plugs
        elif len(plug_name) == 3 and plug_name[1] == '.' and plug_name[0] in 'srt' and plug_name[2] in 'xyz':
            plug_name = plug_name.replace('.', '')

        elif len(plug_name) == 4 and plug_name[2] == '.' and plug_name[0:1] in 'rp' and plug_name[3] in 'xyz':
            plug_name = plug_name.replace('.', '')

        if plug_name in {'show', 'vis', 'visibility'}:
            plug_name = 'v'

        # get plug
        if not isinstance(node, mx.Node):
            node = mx.encode(str(node))

        if isinstance(node, mx.DagNode):
            if plug_name in {'xfo', 'ixfo', 'pxfo', 'pixfo', 'wxfo', 'wixfo'}:
                plug_name = plug_name.replace('xfo', 'm')
            elif plug_name in {'m', 'im', 'pm', 'pim', 'wm', 'wim'}:
                plug = node[plug_name]
                if plug_name[0] in {'w', 'p'}:
                    plug = plug[0]
                return plug

        if plug_name not in node:
            if add:
                k = False
                if not plug_name.startswith('_') and 'gem_id' in node and '::ctrls.' in node['gem_id'].read():
                    k = True
                with mx.DagModifier() as md:
                    md.add_attr(node, mx.Double(plug_name, keyable=k))
            else:
                return

        return node[plug_name]

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

        names = [root_id] + [tpl.name for tpl in children]
        names = set(names)

        asset_id = Nodes.get_asset_id(tpl_root.node)
        if asset_id:
            tpl_asset = Nodes.get_id(asset_id + '#::template')
            if tpl_asset:
                for node in tpl_asset.descendents():
                    if not node.is_a(mx.kTransform):
                        continue
                    if 'gem_type' in node and node['gem_type'] == Template.type_name:
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

    @staticmethod
    def rename_id(gem_id, old, new):
        if old not in gem_id:
            return gem_id
        head, sep, tail = gem_id.partition('::')
        head_path = head.split('.')
        if head_path[0] == old:
            head_path[0] = new
        elif '#' in head_path[0] and len(head_path) > 1 and head_path[1] == old:
            head_path[1] = new
        else:
            return gem_id
        return '.'.join(head_path) + sep + tail

    @staticmethod
    def rename_plug_ids(plug, old, new):
        if not plug.editable:
            return

        ids = []
        for gem_id in plug.read().split(';'):
            ids.append(Nodes.rename_id(gem_id, old, new))
        with mx.DagModifier() as md:
            md.set_attr(plug, ';'.join(ids))

    @staticmethod
    def rename_cfg_ids(node, old, new):
        cfg = ConfigParser(node)

        for flag in ['mod', 'deformer']:
            for ini in cfg[flag]:
                data = Nodes.rename_yaml_ids(ini.read(), old, new)
                if data:
                    ini.write(data)

    @staticmethod
    def rename_yaml_ids(data, old, new):
        if not data:
            data = ''
        changed = False

        lines = []
        for line in data.splitlines():
            if '::' not in line or old not in line:
                lines.append(line)
                continue

            parts = re.split(r'(\s+)', line)
            for i, part in enumerate(parts):
                if '::' in part and old in part:
                    _prefix = ''
                    for prefix in ('\t', '{', '['):
                        if part.startswith(prefix):
                            part = part[1:]
                    parts[i] = _prefix + Nodes.rename_id(part, old, new)
            new_line = ''.join(parts)
            lines.append(new_line)

            if new_line != line:
                changed = True
        if changed:
            return '\n'.join(lines)

    @classmethod
    def check_nodes(cls):
        for asset, supertree in iteritems(cls.nodes):
            for key, tree in iteritems(supertree.tree):
                if isinstance(tree, mx.Node):
                    if tree.destroyed or tree.removed:
                        cls.rebuild()
                        return
                else:
                    for key, node in iteritems(tree):
                        if node.destroyed or node.removed:
                            cls.rebuild()
                            return

            for key, node in iteritems(supertree.dict):
                if node.destroyed or node.removed:
                    cls.rebuild()
                    return

        if not any(cls.nodes.values()):
            cls.rebuild()

    @classmethod
    def cleanup(cls):
        for asset, supertree in iteritems(cls.nodes):
            for _key in list(supertree.tree):
                tree = supertree.tree[_key]
                if isinstance(tree, mx.Node):
                    if tree.destroyed or tree.removed:
                        del supertree.tree[_key]
                else:
                    for key in list(tree):
                        node = tree[key]
                        if node.destroyed or node.removed:
                            del tree[key]

            for key in list(supertree.dict):
                node = supertree.dict[key]
                if node.destroyed or node.removed:
                    del supertree.dict[key]


def parse_nodes(data, failed=None, exclude=None, root=None, silent=False):
    if failed is None:
        failed = []
    if exclude is None:
        exclude = []

    if isinstance(data, dict):
        new_data = type(data)()
        for k, v in iteritems(data):
            if k in exclude:
                new_data[k] = v
                continue
            if isinstance(k, string_types) and ('::' in k or '->' in k):
                k = parse_node(k, failed=failed, silent=silent)
                if isinstance(k, list):
                    if len(k) == 1:
                        k = k[0]
                    else:
                        k = tuple(k)
            new_data[k] = parse_nodes(v, failed=failed, root=root, silent=silent)
        return new_data

    elif isinstance(data, list):
        return [parse_nodes(e, failed=failed, root=root, silent=silent) for e in data]

    elif isinstance(data, string_types):
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
            if nodes[0] is None:
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
