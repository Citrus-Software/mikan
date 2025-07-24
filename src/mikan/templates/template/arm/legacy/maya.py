# coding: utf-8

import mikan.maya.cmdx as mx

import mikan.maya.core as mk
from mikan.maya.lib.rig import fix_inverse_scale
from mikan.core.prefs import Prefs


class Template(mk.Template):

    def build_template(self, data):
        tpl_limb1 = self.node
        with mx.DagModifier() as md:
            tpl_limb2 = md.create_node(mx.tJoint, parent=tpl_limb1)
            tpl_eff = md.create_node(mx.tJoint, parent=tpl_limb2)
            tpl_dig = md.create_node(mx.tJoint, parent=tpl_eff)
            tpl_dig_end = md.create_node(mx.tJoint, parent=tpl_dig)

            tpl_heel = md.create_node(mx.tJoint, parent=tpl_eff)
            tpl_clav = md.create_node(mx.tJoint, parent=tpl_limb1)

        fix_inverse_scale(list(self.node.descendents()))

        self.set_template_id(tpl_clav, 'clavicle')
        self.set_template_id(tpl_heel, 'heel')
        tpl_heel['v'] = False

        # geometry
        tpl_limb1['tx'] = 1.5
        tpl_limb2['t'] = (0, 3, -0.25)
        tpl_eff['t'] = (0, 3, 0.25)
        tpl_dig['t'] = (0, 1, 0)
        tpl_dig_end['t'] = (0, 1, -0.25)

        tpl_limb1['joz'] = mx.Degrees(-90)
        tpl_eff['joy'] = mx.Degrees(-90)

        tpl_clav['ty'] = -1
        tpl_heel['t'] = (0, 0, 0)

    def build_rotate_order(self):
        ro_legacy = Prefs.get('template/arm.legacy/rotate_orders', 1)
        ro_ik = 'xyz'
        if ro_legacy == 0:
            ro_ik = 'zxy'

        self.n['c_1']['ro'] = mx.Euler.YXZ  # formerly yzx
        self.n['c_2']['ro'] = mx.Euler.YXZ
        self.n['c_e']['ro'] = mx.Euler.ZXY  # formerly xyz
        self.n['c_dg']['ro'] = mx.Euler.YXZ  # formerly xyz
        self.n['c_eIK']['ro'] = mx.Euler.orders[ro_ik]
        self.n['c_eIK_offset']['ro'] = mx.Euler.orders[ro_ik]

    def build_space_mods(self):
        mk.Mod.add(
            self.n['c_eIK'], 'space',
            {
                'rest_name': 'root',
                'targets': ['*::space.world', '*::space.move', self.get_hook(tag=True), '*::space.pelvis', '*::space.head']
            }
        )
