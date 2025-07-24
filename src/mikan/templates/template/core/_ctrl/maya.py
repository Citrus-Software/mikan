# coding: utf-8

from mikan.maya import cmds as mc
import mikan.maya.cmdx as mx

import mikan.maya.core as mk
from mikan.maya.lib.rig import copy_transform


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
        with mx.DagModifier() as md:
            root = md.create_node(mx.tTransform, parent=hook, name='root_{}{}'.format(n_loc, n_end))

        rotate_order = self.get_opt('rotate_order').lower()
        rotate_order = mx.Euler.orders[rotate_order]
        root['ro'] = rotate_order

        # xfo
        copy_transform(tpl_loc, root)

        if self.do_flip() and self.get_opt('flip_orient'):
            mc.xform(str(root), r=1, os=1, ro=(180, 0, 0))

        local_orient = self.get_opt('local_orient')
        if not local_orient:
            with mx.DagModifier() as md:
                ctrl = md.create_node(mx.tTransform, parent=root, name='c_{}{}'.format(n_loc, n_end))
        else:
            with mx.DagModifier() as md:
                ctrl = md.create_node(mx.tJoint, parent=root, name='c_{}{}'.format(n_loc, n_end))
            mc.parent(str(ctrl), str(hook), r=1)
            _r = root['r'].read()
            root['r'] = (0, 0, 0)
            mc.parent(str(ctrl), str(root), r=1)
            ctrl['jo'] = _r
            ctrl['ro'] = rotate_order

            ctrl['ssc'] = 0
            ctrl['drawStyle'] = 2

        if self.get_opt('locator'):
            with mx.DagModifier() as md:
                shp = md.create_node(mx.tLocator, parent=ctrl, name='shp_{}{}'.format(n_loc, n_end))
            shp['localScale'] = (0.1, 0.1, 0.1)

        # copy shapes
        if self.get_opt('copy_shapes'):
            # local copy from template node
            if not self.do_flip():
                src = self.node
                mk.Shape(ctrl).copy(src)
            else:
                with mx.DagModifier() as md:
                    src = md.create_node(mx.tTransform, parent=ctrl, name='dummy_shape')
                mk.Shape(src).copy(self.node)
                if self.do_flip():
                    src['s'] = (-1, -1, -1)
                    mc.makeIdentity(str(src), a=1)
                    _src = mk.Shape(src)
                    for shp in _src.get_shapes():
                        if 'gem_color' in shp:
                            rgb = mk.Shape.color_to_rgb(shp['gem_color'].read())
                            rgb = mk.Shape.get_color_flip(rgb)
                            shp['gem_color'] = mk.Shape.rgb_to_hex(rgb)
                    _src.restore_color(force=True)
                mk.Shape(ctrl).copy(src)
                # mx.delete(src)
                src.add_attr(mx.Message('kill_me'))

        # ids
        self.set_id(root, 'root')
        self.set_id(root, 'roots.0')
        self.set_id(ctrl, 'ctrl')
        if self.get_opt('do_ctrl'):
            self.set_id(ctrl, 'ctrls.0')
        self.set_hook(tpl_loc, ctrl, 'ctrl')
