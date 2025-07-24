# coding: utf-8

from mikan.maya import cmds as mc
import mikan.maya.cmdx as mx

import mikan.maya.core as mk
from mikan.core import flatten_list


class Mod(mk.Mod):

    def run(self):

        # get nodes
        nodes = [self.node]
        if self.data:
            nodes = list(flatten_list([self.data]))

        # hide
        with mx.DagModifier() as md:
            for node in nodes:
                if not isinstance(node, mx.DagNode):
                    continue
                if node.exists:
                    md.set_attr(node['v'], False)

                # hide keyable plugs
                if node.is_referenced():
                    continue

                for attr in mc.listAttr(str(node), ud=1, k=1) or []:
                    try:
                        md.set_keyable(node[attr], False)
                        node[attr].channel_box = True
                    except:
                        pass
