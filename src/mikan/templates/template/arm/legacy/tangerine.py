# coding: utf-8

import meta_nodal_py as kl
from meta_nodal_py.Imath import V3f, M44f, Euler

import mikan.tangerine.core as mk
from mikan.core.prefs import Prefs
from mikan.tangerine.lib.commands import *


class Template(mk.Template):

    def build_template(self, data):
        tpl_limb1 = self.node
        # tpl_limb1.rename('tpl_arm1'.format(self.name))
        tpl_limb2 = kl.Joint.create(tpl_limb1, 'tpl_arm2')
        tpl_eff = kl.Joint.create(tpl_limb2, 'tpl_hand')
        tpl_dig = kl.Joint.create(tpl_eff, 'tpl_fingers')
        tpl_dig_end = kl.Joint.create(tpl_dig, 'tpl_fingers_tip')

        tpl_heel = kl.Joint.create(tpl_eff, 'tpl_paw')
        self.set_template_id(tpl_heel, 'heel')
        tpl_heel.show.set_value(False)

        tpl_clav = kl.Joint.create(tpl_limb1, 'tpl_clav')
        self.set_template_id(tpl_clav, 'clavicle')

        # geometry
        tpl_limb1.transform.set_value(M44f(V3f(1.5, 0, 0), V3f(0, 0, -90), V3f(1, 1, 1), Euler.XYZ))
        tpl_limb2.transform.set_value(M44f(V3f(0, 3, -0.25), V3f(0, 0, 0), V3f(1, 1, 1), Euler.XYZ))
        tpl_eff.transform.set_value(M44f(V3f(0, 3, 0.25), V3f(0, -90, 0), V3f(1, 1, 1), Euler.XYZ))
        tpl_dig.transform.set_value(M44f(V3f(0, 1, 0), V3f(0, 0, 0), V3f(1, 1, 1), Euler.XYZ))
        tpl_dig_end.transform.set_value(M44f(V3f(0, 1, -0.25), V3f(0, 0, 0), V3f(1, 1, 1), Euler.XYZ))

        tpl_clav.transform.set_value(M44f(V3f(0, -1, 0), V3f(0, 0, 0), V3f(1, 1, 1), Euler.XYZ))
        tpl_heel.transform.set_value(M44f(V3f(0, 0, 0), V3f(0, 0, 0), V3f(1, 1, 1), Euler.XYZ))

    def build_rotate_order(self):
        ro_legacy = Prefs.get('template/arm.legacy/rotate_orders', 1)
        ro_ik = Euler.XYZ
        if ro_legacy == 0:
            ro_ik = Euler.ZXY

        set_plug(self.n['c_1'].find('transform').rotate_order, Euler.YXZ)
        set_plug(self.n['c_2'].find('transform').rotate_order, Euler.YXZ)
        set_plug(self.n['c_e'].find('transform').rotate_order, Euler.ZXY)
        set_plug(self.n['c_dg'].find('transform').rotate_order, Euler.YXZ)
        set_plug(self.n['c_eIK'].find('transform').rotate_order, ro_ik)
        set_plug(self.n['c_eIK_offset'].find('transform').rotate_order, ro_ik)

    def build_space_mods(self):
        mk.Mod.add(
            self.n['c_eIK'], 'space',
            {
                'rest_name': 'root',
                'targets': ['*::space.world', '*::space.move', self.get_hook(tag=True), '*::space.pelvis', '*::space.head']
            }
        )
