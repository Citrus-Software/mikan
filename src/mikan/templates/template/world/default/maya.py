# coding: utf-8

from mikan.maya import cmds as mc
import mikan.maya.cmdx as mx

import mikan.maya.core as mk
from mikan.maya.lib.rig import copy_transform
from mikan.maya.lib.connect import connect_matrix


class Template(mk.Template):

    def build_template(self, data):
        self.node.rename('tpl_{}'.format(self.name))
        if self.node.is_a(mx.tJoint):
            self.node['drawStyle'] = 2

    def build_rig(self):
        tpl_world = self.root

        n_world = self.get_name('world')
        n_move = self.get_name('move')

        hook = self.get_first_hook()
        with mx.DagModifier() as md:
            world = md.create_node(mx.tTransform, parent=hook, name=n_world)
            move = md.create_node(mx.tTransform, parent=world, name=n_move)

        copy_transform(tpl_world, world, t=True, r=True)

        # hook
        if self.get_opt('hook'):
            rig = self.get_rig_hook()
            with mx.DagModifier() as md:
                hook_root = md.create_node(mx.tTransform, parent=rig, name='hook_move')
            connect_matrix(move['wm'][0], hook_root)

            mk.Nodes.set_id(hook_root, '::hook')
            self.set_hook(tpl_world, hook_root, 'hooks.root')

        else:
            mk.Nodes.set_id(move, '::rig')
            mk.Nodes.set_id(move, '::hook')
            self.set_hook(tpl_world, move, 'hooks.root')

        # register
        self.set_id(world, 'ctrls.world')
        self.set_id(move, 'ctrls.move')

        self.set_id(world, 'space.world')
        self.set_id(move, 'space.move')
