# coding: utf-8

import meta_nodal_py as kl

import mikan.tangerine.core as mk
from mikan.tangerine.lib.commands import copy_transform
from mikan.tangerine.lib.rig import create_srt_in


class Template(mk.Template):

    def build_template(self, data):
        root = self.node
        root.rename('tpl_{}'.format(self.name))

    def build_rig(self):
        tpl_world = self.root

        n_world = self.get_name('world')
        n_move = self.get_name('move')

        hook = self.get_first_hook()
        world = kl.SceneGraphNode(hook, n_world)
        move = kl.SceneGraphNode(world, n_move)

        copy_transform(tpl_world, world)

        create_srt_in(world, k=1)
        create_srt_in(move, k=1)

        # hook
        if self.get_opt('hook'):
            rig = self.get_rig_hook()
            hook_root = kl.SceneGraphNode(rig, 'hook_move')
            hook_root.transform.connect(move.world_transform)

            mk.Nodes.set_id(hook_root, '::hook')
            self.set_hook(tpl_world, hook_root, 'hooks.root')

        else:
            mk.Nodes.set_id(move, '::hook')
            mk.Nodes.set_id(move, '::rig')
            self.set_hook(tpl_world, move, 'hooks.root')

        # register
        self.set_id(world, 'ctrls.world')
        self.set_id(move, 'ctrls.move')

        self.set_id(world, 'space.world')
        self.set_id(move, 'space.move')
