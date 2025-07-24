# coding: utf-8

import meta_nodal_py as kl

import mikan.tangerine.core as mk
from mikan.core import flatten_list
from mikan.core.logger import create_logger

log = create_logger()


class Mod(mk.Mod):

    def run(self):

        # get nodes
        if isinstance(self.data, list):
            nodes = list(flatten_list([self.data]))
            nodes = [node for node in nodes if isinstance(node, kl.SceneGraphNode) or node is None]
            if len(nodes) == 1:
                nodes = [self.node] + nodes
        else:
            nodes = self.data.get('nodes', self.data.get('node', self.node))
            nodes = [n for n in list(flatten_list([nodes])) if isinstance(n, kl.SceneGraphNode) or n is None]

        if not nodes:
            raise mk.ModArgumentError('no arguments provided')

        # get parent
        if isinstance(self.data, dict) and 'parent' in self.data:
            parent = self.data['parent']
        else:
            parent = nodes[-1]
            nodes = [n for n in nodes[:-1] if isinstance(n, kl.SceneGraphNode)]

        if not nodes:
            raise mk.ModArgumentError('no valid nodes to parent provided')

        if not isinstance(parent, kl.SceneGraphNode):
            raise mk.ModArgumentError('invalid parent')

        # parent
        for node in nodes:
            if node.get_parent() != parent:
                node.reparent(parent)
