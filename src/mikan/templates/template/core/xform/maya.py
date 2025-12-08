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

        # prefix
        prefix = self.get_opt('prefix')
        if not prefix.endswith('_'):
            prefix += '_'

        do_ctrl = self.get_opt('do_ctrl')
        do_skin = self.get_opt('do_skin')

        if do_ctrl:
            prefix = 'c_'
        elif do_skin:
            prefix = 'sk_'

        # build nodes
        do_joint = self.get_opt('joint')
        local_orient = self.get_opt('local_orient')

        root = None
        if self.get_opt('root'):
            node_type = mx.tTransform if not do_joint else mx.tJoint
            root = mx.create_node(node_type, parent=hook, name='root_' + n_loc + n_end)
            hook = root

        node_type = mx.tTransform if not do_joint and not local_orient else mx.tJoint
        loc = mx.create_node(node_type, parent=hook, name=prefix + n_loc + n_end)

        orient_node = loc
        if root:
            orient_node = root

        mc.xform(str(orient_node), m=tpl_loc['wm'][0].as_matrix() * hook['wim'][0].as_matrix())
        if not self.get_opt('copy_orient'):
            orient_node['r'] = (0, 0, 0)

        if root and self.get_opt('local_orient'):
            loc['jo'] = root['r'].read()
            root['r'] = (0, 0, 0)

        if do_joint:
            mc.makeIdentity(str(orient_node), a=1, r=1)
            fix_inverse_scale(loc)

        if self.do_flip() and self.get_opt('flip_orient'):
            mc.xform(str(loc), r=1, os=1, ro=(180, 0, 0))

        ro = mx.Euler.orders[self.get_opt('rotate_order')]
        if root:
            mc.setAttr(root['ro'].path(), ro)
        mc.setAttr(loc['ro'].path(), ro)

        # shapes
        if self.get_opt('locator'):
            with mx.DagModifier() as md:
                shp = md.create_node(mx.tLocator, parent=loc, name=prefix + n_loc + n_end + 'Shape')
            shp['localScale'] = (0.1, 0.1, 0.1)

        if self.get_opt('copy_shapes'):
            shp = mk.Shape(loc)
            shp.copy(self.node)  # local copy from template node
            if self.do_flip():
                mk.Shape(loc).scale(-1)

        # ids
        self.set_id(loc, 'node')
        self.set_hook(tpl_loc, loc, 'node')

        if root:
            self.set_id(root, 'roots.node')

        if do_ctrl:
            self.set_id(loc, 'ctrls.node')
        if do_skin:
            self.set_id(loc, 'skin.node')
