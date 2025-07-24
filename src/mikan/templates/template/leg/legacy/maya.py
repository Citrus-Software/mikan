# coding: utf-8

import mikan.maya.cmdx as mx

import mikan.maya.core as mk
from mikan.maya.lib.rig import fix_inverse_scale


class Template(mk.Template):

    def build_template(self, data):
        tpl_limb1 = self.node

        with mx.DagModifier() as md:
            tpl_limb2 = md.create_node(mx.tJoint, parent=tpl_limb1, name='tpl_leg2')
            tpl_eff = md.create_node(mx.tJoint, parent=tpl_limb2, name='tpl_foot')
            tpl_dig = md.create_node(mx.tJoint, parent=tpl_eff, name='tpl_toes')
            tpl_dig_end = md.create_node(mx.tJoint, parent=tpl_dig, name='tpl_digits_tip')

            tpl_heel = md.create_node(mx.tJoint, parent=tpl_eff, name='tpl_heel')
            tpl_clav = md.create_node(mx.tJoint, parent=tpl_limb1, name='tpl_pelvis')

            tpl_bank_int = md.create_node(mx.tJoint, parent=tpl_dig, name='tpl_bank_int')
            tpl_bank_ext = md.create_node(mx.tJoint, parent=tpl_dig, name='tpl_bank_ext')

        fix_inverse_scale(list(self.node.descendents()))

        self.set_template_id(tpl_heel, 'heel')
        self.set_template_id(tpl_clav, 'clavicle')

        self.set_template_id(tpl_bank_int, 'bank_int')
        self.set_template_id(tpl_bank_ext, 'bank_ext')

        # geometry
        tpl_limb1['tx'] = 1
        tpl_limb2['t'] = (0, 4, 0.25)
        tpl_eff['t'] = (0, 4, -0.25)
        tpl_dig['t'] = (0, 1.5, -1.5)
        tpl_dig_end['ty'] = 1

        tpl_limb1['joz'] = mx.Degrees(180)
        tpl_eff['jox'] = mx.Degrees(90)

        tpl_clav['tx'] = 0.5
        tpl_heel['t'] = (0, 0, -1.5)

        tpl_bank_int['tx'] = 0.5
        tpl_bank_ext['tx'] = -0.5

    def build_rotate_order(self):
        self.n['c_1']['ro'] = mx.Euler.YXZ
        self.n['c_2']['ro'] = mx.Euler.YXZ
        self.n['c_e']['ro'] = mx.Euler.ZXY
        self.n['c_dg']['ro'] = mx.Euler.YXZ
        self.n['c_eIK']['ro'] = mx.Euler.ZXY
