# coding: utf-8

from mikan.maya import cmds as mc
import mikan.maya.cmdx as mx

import mikan.maya.core as mk
from mikan.maya.lib.rig import fix_inverse_scale


class Template(mk.Template):

    def build_template(self, data):
        self.node['t'] = data['transform']

    def build_rig(self):
        # init
        hook = self.get_hook()

        n_end = self.get_branch_suffix()
        n_loc = self.name

        tpl_loc = self.root

        # build nodes
        node_type = mx.tTransform if not self.get_opt('joint') else mx.tJoint
        loc = mx.create_node(node_type, parent=hook, name=n_loc + n_end)

        loc['ro'] = mx.Euler.orders[self.get_opt('rotate_order')]
        mc.xform(str(loc), m=tpl_loc['wm'][0].as_matrix() * hook['wim'][0].as_matrix())
        if not self.get_opt('copy_orient'):
            loc['r'] = (0, 0, 0)

        if self.get_opt('joint'):
            mc.makeIdentity(str(loc), a=1, r=1)
            fix_inverse_scale(loc)

        if self.do_flip() and self.get_opt('flip_orient'):
            mc.xform(str(loc), r=1, os=1, ro=(180, 0, 0))

        if self.get_opt('locator'):
            with mx.DagModifier() as md:
                shp = md.create_node(mx.tLocator, parent=loc, name=n_loc + n_end + 'Shape')
            shp['localScale'] = (0.1, 0.1, 0.1)

        # copy shapes
        if self.get_opt('copy_shapes'):
            shp = mk.Shape(loc)
            shp.copy(self.node)  # local copy from template node
            if self.do_flip():
                mk.Shape(loc).scale(-1)

        # ids
        self.set_id(loc, 'node')
        self.set_hook(tpl_loc, loc, 'node')

        if self.get_opt('do_ctrl'):
            self.set_id(loc, 'ctrls.node')
        if self.get_opt('do_skin'):
            self.set_id(loc, 'skin.node')
