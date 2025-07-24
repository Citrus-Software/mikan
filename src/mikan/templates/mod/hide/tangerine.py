# coding: utf-8

import meta_nodal_py as kl

import mikan.tangerine.core as mk
from mikan.core import flatten_list
from mikan.tangerine.lib.commands import set_plug


class Mod(mk.Mod):

    def run(self):

        # get nodes
        nodes = [self.node]
        if self.data:
            nodes = list(flatten_list([self.data]))

        # hide
        for node in nodes:
            if not isinstance(node, kl.SceneGraphNode):
                continue
            if node.get_parent():
                node.show.set_value(False)

            # hide keyable plugs
            for plug in node.get_dynamic_plugs():
                set_plug(plug, k=False)
