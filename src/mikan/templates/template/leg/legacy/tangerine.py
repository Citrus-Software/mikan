# coding: utf-8

import meta_nodal_py as kl
from meta_nodal_py.Imath import V3f, M44f, Euler

import mikan.tangerine.core as mk
from mikan.tangerine.lib.commands import *


class Template(mk.Template):

    def build_template(self, data):
        tpl_limb1 = self.node

        tpl_limb2 = kl.Joint(tpl_limb1, 'tpl_leg2')
        tpl_eff = kl.Joint(tpl_limb2, 'tpl_foot')
        tpl_dig = kl.Joint(tpl_eff, 'tpl_toes')
        tpl_dig_end = kl.Joint(tpl_dig, 'tpl_digits_tip')

        tpl_heel = kl.Joint(tpl_eff, 'tpl_heel')
        tpl_clav = kl.Joint(tpl_limb1, 'tpl_pelvis')

        tpl_bank_int = kl.Joint(tpl_dig, 'tpl_bank_int')
        tpl_bank_ext = kl.Joint(tpl_dig, 'tpl_bank_ext')

        self.set_template_id(tpl_heel, 'heel')
        self.set_template_id(tpl_clav, 'clavicle')

        self.set_template_id(tpl_bank_int, 'bank_int')
        self.set_template_id(tpl_bank_ext, 'bank_ext')

        # geometry
        tpl_limb1.transform.set_value(M44f(V3f(1, 0, 0), V3f(0, 0, 180), V3f(1, 1, 1), Euler.XYZ))
        tpl_limb2.transform.set_value(M44f(V3f(0, 4, 0.25), V3f(0, 0, 0), V3f(1, 1, 1), Euler.XYZ))
        tpl_eff.transform.set_value(M44f(V3f(0, 4, -0.25), V3f(90, 0, 0), V3f(1, 1, 1), Euler.XYZ))
        tpl_dig.transform.set_value(M44f(V3f(0, 1.5, -1.5), V3f(0, 0, 0), V3f(1, 1, 1), Euler.XYZ))
        tpl_dig_end.transform.set_value(M44f(V3f(0, 1, 0), V3f(0, 0, 0), V3f(1, 1, 1), Euler.XYZ))

        tpl_clav.transform.set_value(M44f(V3f(0.5, 0, 0), V3f(0, 0, 0), V3f(1, 1, 1), Euler.XYZ))
        tpl_heel.transform.set_value(M44f(V3f(0, 0, -1.5), V3f(0, 0, 0), V3f(1, 1, 1), Euler.XYZ))

        tpl_bank_int.transform.set_value(M44f(V3f(0.5, 0, 0), V3f(0, 0, 0), V3f(1, 1, 1), Euler.XYZ))
        tpl_bank_ext.transform.set_value(M44f(V3f(-0.5, 0, 0), V3f(0, 0, 0), V3f(1, 1, 1), Euler.XYZ))

    def build_rotate_order(self):
        set_plug(self.n['c_1'].find('transform').rotate_order, Euler.YXZ)
        set_plug(self.n['c_2'].find('transform').rotate_order, Euler.YXZ)
        set_plug(self.n['c_e'].find('transform').rotate_order, Euler.ZXY)
        set_plug(self.n['c_dg'].find('transform').rotate_order, Euler.YXZ)
        set_plug(self.n['c_eIK'].find('transform').rotate_order, Euler.ZXY)
