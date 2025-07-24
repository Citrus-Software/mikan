# coding: utf-8

from mikan.maya import cmds as mc
import mikan.maya.cmdx as mx

import mikan.maya.core as mk
from mikan.maya.core.control import set_bind_pose
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

        elif isinstance(self.data, mx.Node):
            nodes = [self.data]

        if not nodes:
            raise mk.ModArgumentError('node list to reset is empty')

        # reset pose
        for node in nodes:
            set_bind_pose(node, 'reset_pose')
            self.set_id(node, 'reset')
