# coding: utf-8

"""Abstract Node Registry Module.

This module provides the node registry system for the Mikan framework.
It manages node identification, retrieval, and organization across assets
and namespaces during rig building and manipulation.

The module supports:
    - Node registration and retrieval by Mikan IDs
    - Asset-scoped node organization
    - Hierarchical tag-based node lookup
    - Plug/attribute access through node references

Classes:
    MetaNodes: Metaclass providing class-level property access for current_asset.
    Nodes: Main registry class for node identification and retrieval.

Examples:
    Retrieving a node by ID:
        >>> node = Nodes.get_id('arm.fk.ctrl')
        >>> nodes = Nodes.get_id('arm.*.ctrl', as_list=True)

    Setting a node ID:
        >>> Nodes.set_id(my_node, 'arm.ik.ctrl')

    Getting a node with plug access:
        >>> plug = Nodes.get_id('arm.fk.ctrl@rotateX')
"""

from six import with_metaclass, iteritems

from mikan.core.utils import ordered_dict
from mikan.core.tree import Tree, SuperTree, Branch
from mikan.core.logger import create_logger

__all__ = ['Nodes']

log = create_logger()


class MetaNodes(type):
    """Metaclass providing class-level property access for Nodes.

    Enables the current_asset property to be accessed and set at the
    class level rather than on instances.

    Attributes:
        current_asset: Property for getting/setting the active asset context.
    """

    @property
    def current_asset(cls):
        """Get the current asset context.

        Returns:
            The currently active asset, or None if not set.
        """
        return cls._current_asset

    @current_asset.setter
    def current_asset(cls, value):
        """Set the current asset context.

        Args:
            value: The asset to set as current context.
        """
        cls._current_asset = value


class Nodes(with_metaclass(MetaNodes)):
    """Main registry class for node identification and retrieval.

    Provides a centralized system for registering and retrieving nodes
    by their Mikan IDs. Nodes are organized hierarchically by asset
    and can be accessed using dot-notation tags.

    Attributes:
        assets (OrderedDict): Registry of asset objects.
        namespaces (OrderedDict): Registry of namespace mappings.
        geometries (OrderedDict): Registry of geometry nodes.
        nodes (Tree): Hierarchical tree of registered nodes by ID.
        shapes (Tree): Hierarchical tree of shape nodes.
        current_asset: The currently active asset context for node operations.

    Examples:
        Basic node retrieval:
            >>> ctrl = Nodes.get_id('arm.fk.ctrl')

        Retrieving multiple nodes:
            >>> ctrls = Nodes.get_id('arm.*.ctrl', as_list=True)

        Asset-scoped retrieval:
            >>> node = Nodes.get_id('character#arm.fk.ctrl')

    Note:
        This is an abstract base class. Use software-specific implementations
        like mikan.maya.core.node.Nodes for actual node operations.
    """

    assets = ordered_dict()
    namespaces = ordered_dict()
    geometries = ordered_dict()
    nodes = Tree()
    shapes = Tree()

    _current_asset = None

    @classmethod
    def flush(cls):
        """Clear all registries and reset the current asset.

        Removes all registered assets, nodes, shapes, and geometries.
        Resets current_asset to None.
        """
        cls.assets.clear()
        cls.nodes.clear()
        cls.shapes.clear()
        cls.geometries.clear()
        cls.current_asset = None

    @classmethod
    def rebuild(cls):
        """Rebuild the node registry from the current scene.

        Flushes existing data and re-scans the scene for nodes.
        Must be implemented by software-specific subclasses.

        Note:
            Base implementation only calls flush(). Override in subclasses
            to add scene scanning logic.
        """
        cls.flush()

    @classmethod
    def get_id(cls, tag, as_dict=False, as_list=False, asset=None):
        """Retrieve nodes by their Mikan ID tag.

        Looks up nodes in the registry using hierarchical dot-notation tags.
        Supports wildcards, asset prefixes, and plug access.

        Args:
            tag (str): The tag to look up. Supports:
                - Simple tags: 'arm.fk.ctrl'
                - Asset prefix: 'character#arm.fk.ctrl'
                - Children: 'arm.fk:::'
                - Plug access: 'arm.fk.ctrl@rotateX'
            as_dict (bool): If True, return results as {tag: node} dict.
            as_list (bool): If True, always return results as a list.
            asset: Optional asset to scope the lookup to.

        Returns:
            Node, list, or dict: Depending on matches and flags:
                - Single node if one match and no flags
                - List of nodes if multiple matches or as_list=True
                - Dict of {tag: node} if as_dict=True

        Raises:
            KeyError: If asset or tag cannot be resolved.

        Examples:
            >>> node = Nodes.get_id('arm.fk.ctrl')
            >>> nodes = Nodes.get_id('arm.*.ctrl', as_list=True)
            >>> plug = Nodes.get_id('arm.fk.ctrl@rotateX')
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

            if as_list:
                if not nodes:
                    return []
                if not isinstance(nodes, list):
                    return [nodes]

        return nodes

    @classmethod
    def get_id_children(cls, tag, as_dict=False):
        """Retrieve child nodes under a given tag.

        Args:
            tag (str): Parent tag with ':::' suffix to get children.
            as_dict (bool): If True, return results as dict.

        Returns:
            list: List of child nodes (empty in base implementation).

        Note:
            This is a placeholder. Override in subclasses.
        """
        return []

    @classmethod
    def get_nodes_plug(cls, nodes, plug):
        """Get plug/attribute access for nodes.

        Recursively applies plug access to nodes or collections of nodes.

        Args:
            nodes: Single node, list of nodes, or dict of nodes.
            plug (str): Attribute/plug name to access.

        Returns:
            Plug reference(s) matching the input structure.
        """
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
        """Register a node with a Mikan ID tag.

        Args:
            node: The DCC node to register.
            tag (str): The tag to associate with the node.

        Note:
            Registers the node under the current_asset context.
        """
        if not any(cls.nodes.values()):
            cls.rebuild()

        cls.nodes[cls.current_asset][tag] = node

    @classmethod
    def check_nodes(cls):
        """Validate registered nodes still exist in the scene.

        Note:
            This is a placeholder. Override in subclasses.
        """
