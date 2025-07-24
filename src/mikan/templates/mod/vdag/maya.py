# coding: utf-8

import mikan.maya.cmdx as mx

import mikan.maya.core as mk
from mikan.core import flatten_list
from mikan.core.logger import create_logger
from mikan.maya.lib.rig import set_virtual_parent, find_closest_node

log = create_logger()


class Mod(mk.Mod):

    def run(self):
        do_filter = bool(self.data.get('filter', True))

        # get nodes
        nodes = self.data.get('nodes', self.data.get('node', self.node))
        nodes = [n for n in list(flatten_list([nodes])) if isinstance(n, mx.DagNode)]
        if not nodes:
            raise mk.ModArgumentError('node not found')

        # vdag modes
        if 'parent' in self.data:
            parent = self.data['parent']
            if not isinstance(parent, mx.DagNode):
                raise mk.ModArgumentError('invalid parent')

            parent_patterns = Mod.get_patterns(parent)
            for node in nodes:
                if do_filter and not Mod.get_patterns(node).intersection(parent_patterns):
                    self.log_error('couldn\'t find valid virtual parent for {} with matching patterns'.format(node))
                    continue
                set_virtual_parent(node, parent)

        if 'closest' in self.data:
            closest = self.data['closest']
            closest = [n for n in list(flatten_list([closest])) if isinstance(n, mx.DagNode)]
            if not nodes:
                raise mk.ModArgumentError('no closest targets found')

            for node in nodes:
                node_patterns = Mod.get_patterns(node)
                _closest = [n for n in closest if node_patterns.intersection(Mod.get_patterns(n))]
                if not _closest:
                    self.log_error('couldn\'t find valid virtual parent for {} with matching patterns'.format(node))
                    continue

                parent = find_closest_node(node, _closest)
                set_virtual_parent(node, parent)

    @staticmethod
    def get_patterns(node):
        patterns = set()
        for tag in node['gem_id'].read().split(';'):
            if '::' not in tag:
                continue
            pattern = tag.split('::')[-1].split('.')[0]
            patterns.add(pattern)
        return patterns
