# coding: utf-8

from six import with_metaclass, iteritems

from mikan.core.utils import ordered_dict
from mikan.core.tree import Tree, SuperTree, Branch
from mikan.core.logger import create_logger

__all__ = ['Nodes']

log = create_logger()


class MetaNodes(type):

    @property
    def current_asset(cls):
        return cls._current_asset

    @current_asset.setter
    def current_asset(cls, value):
        cls._current_asset = value


class Nodes(with_metaclass(MetaNodes)):
    """Main class used to retrieve nodes by their mikan id."""

    assets = ordered_dict()
    namespaces = ordered_dict()
    geometries = ordered_dict()
    nodes = Tree()
    shapes = Tree()

    _current_asset = None

    @classmethod
    def flush(cls):
        cls.assets.clear()
        cls.nodes.clear()
        cls.shapes.clear()
        cls.geometries.clear()
        cls.current_asset = None

    @classmethod
    def rebuild(cls):
        cls.flush()

    @classmethod
    def get_id(cls, tag, as_dict=False, as_list=False, asset=None):
        """Returns node or list of nodes from a given tag.

        Arguments:
            tag (str):
            as_dict (bool, default: False):
            as_list (bool, default: False):
            asset (optional):

        Returns:
              Node, Node[], {tag: Node}:

        """
        if not any(cls.nodes.values()):
            cls.rebuild()

        if ':::' in tag:
            return cls.get_id_children(tag, as_dict=as_dict)

        tag, sep, plug = tag.partition('@')

        tree = cls.nodes
        if '#' in tag:
            asset, sep, tag = tag.partition('#')
            if asset not in cls.nodes:
                raise KeyError('/!\\ cannot resolve asset "{}" to get tag "{}"'.format(asset, tag))
            tree = cls.nodes[asset]

        elif asset is not None:
            if asset not in cls.nodes:
                raise KeyError('/!\\ asset "{}" does not exist'.format(asset))
            tree = cls.nodes[asset]

        elif cls.current_asset is not None and cls.current_asset in cls.nodes:
            tree = cls.nodes[cls.current_asset]

        if isinstance(tree, SuperTree):
            nodes = tree.get(tag)

        else:
            nodes = ordered_dict()
            branches = 0
            for branch in tree:
                key = branch
                if isinstance(tree, Branch):
                    key = tree._key + '.' + branch
                _nodes = cls.nodes[key].get(tag)
                if _nodes:
                    branches += 1
                    nodes[key] = _nodes
            if branches == 1:
                nodes = list(nodes.values())[0]

        if plug:
            if not nodes:
                raise KeyError('/!\\ cannot resolve tag "{}" to get plug "{}"'.format(tag, plug))
            nodes = cls.get_nodes_plug(nodes, plug)

        if as_dict:
            if nodes is None:
                return {}
            elif not isinstance(nodes, dict):
                return {tag: nodes}

        else:
            if isinstance(nodes, dict):
                _nodes = ordered_dict()
                for node in SuperTree.flatten(nodes):
                    if node not in _nodes:
                        _nodes[node] = True
                return list(_nodes)

        if as_list and not isinstance(nodes, list):
            return [nodes]

        return nodes

    @classmethod
    def get_id_children(cls, tag, as_dict=False):
        """placeholder"""
        return []

    @classmethod
    def get_nodes_plug(cls, nodes, plug):
        if isinstance(nodes, list):
            return [cls.get_node_plug(node, plug) for node in nodes if node is not None]
        elif isinstance(nodes, dict):
            for key, _nodes in iteritems(nodes):
                nodes[key] = cls.get_nodes_plug(_nodes, plug)
            return nodes
        else:
            return cls.get_node_plug(nodes, plug)

    @classmethod
    def set_id(cls, node, tag):
        """placeholder"""
        if not any(cls.nodes.values()):
            cls.rebuild()

        cls.nodes[cls.current_asset][tag] = node

    @classmethod
    def check_nodes(cls):
        """placeholder"""
