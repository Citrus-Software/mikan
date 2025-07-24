# coding: utf-8

from mikan.maya import cmds as mc
import mikan.maya.cmdx as mx

import mikan.maya.core as mk

from mikan.core import flatten_list
from mikan.core.logger import create_logger

log = create_logger()


class Mod(mk.Mod):

    def run(self):

        # get nodes
        if isinstance(self.data, list):
            nodes = list(flatten_list([self.data]))
            nodes = [node for node in nodes if isinstance(node, mx.Node) or node is None]
            if len(nodes) == 1:
                nodes = [self.node] + nodes
        else:
            nodes = self.data.get('nodes', self.data.get('node', self.node))
            nodes = [n for n in list(flatten_list([nodes])) if isinstance(n, mx.Node) or n is None]

        if not nodes:
            raise mk.ModArgumentError('no arguments provided')

        # get parent
        if isinstance(self.data, dict) and 'parent' in self.data:
            parent = self.data['parent']
        else:
            parent = nodes[-1]
            nodes = [n for n in nodes[:-1] if isinstance(n, mx.Node)]

        if not nodes:
            raise mk.ModArgumentError('no valid nodes to parent provided')

        if not isinstance(parent, mx.DagNode):
            raise mk.ModArgumentError('invalid parent')

        # parent
        for node in nodes:
            if node.parent() != parent:
                mc.parent(str(node), str(parent))
