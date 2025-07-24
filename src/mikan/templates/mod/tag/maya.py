# coding: utf-8

from six import string_types

import mikan.maya.cmdx as mx

import mikan.maya.core as mk
from mikan.core import flatten_list
from mikan.core.logger import create_logger

log = create_logger()


class Mod(mk.Mod):

    def run(self):

        # get nodes
        nodes = self.data.get('nodes', self.data.get('node', self.node))
        nodes = [n for n in list(flatten_list([nodes])) if n]
        if not nodes:
            raise mk.ModArgumentError('node not found')

        # add tag
        if 'add' in self.data:
            pattern = self.data['add']
            if not isinstance(pattern, string_types):
                raise mk.ModArgumentError('invalid add pattern')
            pattern = '{}::{}'.format(self.get_template_id(), pattern)
            if len(nodes) == 1:
                mk.Nodes.set_id(nodes[0], pattern)
            else:
                for i, node in enumerate(nodes):
                    mk.Nodes.set_id(node, '{}.{}'.format(pattern, i))

        # remove tags
        if 'remove' in self.data:
            pattern = self.data['remove']
            if not isinstance(pattern, string_types):
                raise mk.ModArgumentError('invalid remove pattern')
            for node in nodes:
                if 'gem_id' in node:
                    gem_id = node['gem_id'].read()
                    for tag in gem_id.split(';'):
                        if pattern in tag:
                            mk.Nodes.remove_id(tag)

                            if '::ctrls.' in tag:
                                for shp in node.shapes(type=mx.tNurbsCurve):
                                    shp['v'] = False

        # closest
        # TODO: closest
