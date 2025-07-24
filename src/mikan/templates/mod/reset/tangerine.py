# coding: utf-8

import meta_nodal_py as kl

import mikan.tangerine.core as mk
from mikan.core import flatten_list


class Mod(mk.Mod):

    def run(self):

        # get nodes
        nodes = []
        if isinstance(self.data, dict):
            nodes = self.data.get('nodes', self.data.get('node', self.node))
            nodes = [n for n in list(flatten_list([nodes])) if n]

        elif isinstance(self.data, list):
            nodes = self.data[:]

        elif isinstance(self.data, kl.Node):
            nodes = [self.data]

        if not nodes:
            raise mk.ModArgumentError('node list to reset is empty')
