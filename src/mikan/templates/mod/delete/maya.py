# coding: utf-8

import mikan.maya.cmdx as mx

import mikan.maya.core as mk
from mikan.core import flatten_list


class Mod(mk.Mod):

    def run(self):

        # get nodes
        nodes = [self.node]
        if self.data:
            nodes = flatten_list([self.data])

        # delete
        for node in nodes:
            if node.exists:
                node.add_attr(mx.Message('kill_me'))
                if not self.modes:
                    mx.delete(node)
