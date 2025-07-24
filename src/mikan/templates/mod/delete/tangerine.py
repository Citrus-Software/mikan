# coding: utf-8

import meta_nodal_py as kl

from mikan.core import flatten_list
import mikan.tangerine.core as mk


class Mod(mk.Mod):

    def run(self):

        # get nodes
        nodes = [self.node]
        if self.data:
            nodes = flatten_list([self.data])

        # delete
        for node in nodes:
            if not isinstance(node, kl.Node):
                continue
            if node.get_parent():
                node.remove_from_parent()
