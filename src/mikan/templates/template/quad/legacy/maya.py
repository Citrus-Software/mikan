# coding: utf-8

import math
from six.moves import range

from mikan.maya import cmds as mc
import mikan.maya.cmdx as mx

import mikan.maya.core as mk
from mikan.maya.lib.rig import (
    copy_transform, orient_joint, duplicate_joint, stretch_ik, create_ik_handle,
    create_blend_joint, axis_to_vector, fix_inverse_scale
)
from mikan.maya.lib.connect import *
from mikan.maya.lib.nurbs import create_path
from mikan.templates.template._common.limb.maya import get_triangle_weights


class Template(mk.Template):

    def rename_template(self):

        for s in ('clavicle', 'limb2', 'limb3', 'limb4', 'digits', 'tip', 'heel', 'bank_int', 'bank_ext'):
            j = self.get_structure(s)
            if not j or j[0].is_referenced():
                continue

            sfx = s
            if s == 'clavicle':
                sfx = 'clav'
            j[0].rename('tpl_{}_{}'.format(self.name, sfx))

    def build_template(self, data):
        tpl_limb1 = self.node
        tpl_limb1.rename('tpl_leg1'.format(self.name))

        with mx.DagModifier() as md:
            tpl_limb2 = md.create_node(mx.tJoint, parent=tpl_limb1)
            tpl_limb3 = md.create_node(mx.tJoint, parent=tpl_limb2)
            tpl_eff = md.create_node(mx.tJoint, parent=tpl_limb3)
            tpl_dig = md.create_node(mx.tJoint, parent=tpl_eff)
            tpl_dig_end = md.create_node(mx.tJoint, parent=tpl_dig)
            tpl_heel = md.create_node(mx.tJoint, parent=tpl_eff)
            tpl_clav = md.create_node(mx.tJoint, parent=tpl_limb1)

            tpl_bank_int = md.create_node(mx.tJoint, parent=tpl_dig, name='tpl_bank_int')
            tpl_bank_ext = md.create_node(mx.tJoint, parent=tpl_dig, name='tpl_bank_ext')

        fix_inverse_scale(list(self.node.descendents()))

        self.set_template_id(tpl_heel, 'heel')
        self.set_template_id(tpl_clav, 'clavicle')

        self.set_template_id(tpl_bank_int, 'bank_int')
        self.set_template_id(tpl_bank_ext, 'bank_ext')

        # geometry
        tpl_limb1['tx'] = 1
        tpl_limb2['t'] = (0, 2.645, 0.25)
        tpl_limb3['t'] = (0, 2.595, -1.25)
        tpl_eff['t'] = (0, 2.759, 0)
        tpl_dig['t'] = (0, 1.5, -1.5)
        tpl_dig_end['ty'] = 1

        tpl_limb1['joz'] = mx.Degrees(180)
        tpl_eff['jox'] = mx.Degrees(90)

        tpl_clav['tx'] = 0.5
        tpl_heel['t'] = (0, 0, -1.5)

        tpl_bank_int['tx'] = 0.5
        tpl_bank_ext['tx'] = -0.5

    def build_rig(self):
        # get structures
        hook = self.hook
        default_hook = mk.Nodes.get_id('::hook')
        if not default_hook:
            default_hook = self.get_first_hook()

        tpl_limb1 = self.get_structure('limb1')[0]
        tpl_limb2 = self.get_structure('limb2')[0]
        tpl_limb3 = self.get_structure('limb3')[0]
        tpl_limb4 = self.get_structure('limb4')[0]
        tpl_digits = self.get_structure('digits')[0]
        tpl_tip = self.get_structure('tip')[0]

        # naming
        n_end = self.get_branch_suffix()
        n_limb = self.name
        n_limb1 = self.get_name('limb1')
        n_limb2 = self.get_name('limb2')
        n_limb3 = self.get_name('limb3')
        n_eff = self.get_name('effector')
        n_digits = self.get_name('digits')
        n_chain = ['']

        # opts
        self.do_clavicle = self.get_opt('clavicle')
        self.do_clavicle_auto = self.get_opt('clavicle_auto')
        quad_type = self.get_opt('quad_type')
        aim_axis = self.get_branch_opt('aim_axis')
        up_axis = self.get_opt('up_axis')
        up_axis2 = self.get_branch_opt('up_axis2')

        # vars
        n = {}
        self.n = n

        # build skeleton
        n['c_1'] = mx.create_node(mx.tJoint, name='c_' + n_limb1 + n_end)
        n['c_2'] = mx.create_node(mx.tJoint, parent=n['c_1'], name='c_' + n_limb2 + n_end)
        n['c_3'] = mx.create_node(mx.tJoint, parent=n['c_2'], name='c_' + n_limb3 + n_end)
        n['c_e'] = mx.create_node(mx.tJoint, parent=n['c_3'], name='c_' + n_eff + n_end)
        n['c_dg'] = mx.create_node(mx.tJoint, parent=n['c_e'], name='c_' + n_digits + n_end)
        n['end_dg'] = mx.create_node(mx.tJoint, parent=n['c_dg'], name='end_' + n_digits + n_end)

        copy_transform(tpl_limb1, n['c_1'], t=True)
        copy_transform(tpl_limb2, n['c_2'], t=True)
        copy_transform(tpl_limb3, n['c_3'], t=True)
        copy_transform(tpl_limb4, n['c_e'], t=True)
        copy_transform(tpl_digits, n['c_dg'], t=True)
        copy_transform(tpl_tip, n['end_dg'], t=True)

        # orient skeleton
        orient_joint((n['c_1'], n['c_2'], n['c_3'], n['c_e']), aim=aim_axis, up=up_axis, up_auto=1)

        if self.get_opt('reverse_lock'):
            # orient from ground (foot)
            vp = tpl_tip.translation(mx.sWorld) - tpl_limb4.translation(mx.sWorld)
            vp = vp ^ mx.Vector(0, 1, 0)  # cross

            vd = tpl_tip.translation(mx.sWorld) - n['c_e'].translation(mx.sWorld)
            vd[1] = 0

            orient_joint(n['c_e'], aim=up_axis2, aim_dir=vd, up=up_axis, up_dir=vp)
            orient_joint((n['c_dg'], n['end_dg']), aim=up_axis2, up=up_axis, up_dir=vp)

            # conform limb
            up0 = axis_to_vector(up_axis) * n['c_1'].transform(mx.sWorld).as_matrix()
            if up0 * vp < 0:  # dot
                for j in (n['c_1'], n['c_2'], n['c_3']):
                    _children = list(j.children())
                    for _c in _children:
                        mc.parent(str(_c), w=1)
                    j['r' + aim_axis[-1]] = mx.Degrees(180)
                    mc.makeIdentity(str(j), a=1)
                    for _c in _children:
                        mc.parent(str(_c), str(j))

        else:
            # free orient (hand, never used)
            orient_joint((n['c_e'], n['c_dg'], n['end_dg']), aim=aim_axis, up=up_axis2)

        # rig skeleton
        n['o_1'] = duplicate_joint(n['c_1'], p=hook, n='o_' + n_limb1 + n_end)
        mc.parent(str(n['c_1']), str(n['o_1']))

        n['root_1'] = duplicate_joint(n['o_1'], p=n['o_1'].parent(), n='root_' + n_limb1 + n_end)
        orient_joint(n['root_1'], aim_dir=[0, 1, 0], up_dir=[0, 0, 1])
        mc.parent(str(n['o_1']), str(n['root_1']))
        mc.parent(str(n['c_1']), str(n['root_1']))

        orient_joint(n['root_1'], aim_dir=[0, 1, 0], up_dir=[0, 0, 1])

        n['root_e'] = duplicate_joint(n['c_e'], p=n['c_e'].parent(), n='root_' + n_eff + n_end)
        mc.parent(str(n['c_e']), str(n['root_e']))

        n['root_dg'] = duplicate_joint(n['c_dg'], p=n['c_dg'].parent(), n='root_' + n_digits + n_end)
        mc.parent(str(n['c_dg']), str(n['root_dg']))

        n['c_dg']['ssc'] = False

        n['c_dg'].add_attr(mx.Boolean('parent_scale', keyable=False, default=True))
        _r = connect_reverse(n['c_dg']['parent_scale'], n['c_dg']['ssc'])
        _r >> n['root_dg']['ssc']

        # deform skeleton
        n['j_1'] = duplicate_joint(n['c_1'], p=n['root_1'], n='j_' + n_limb1 + n_end)
        n['j_2'] = duplicate_joint(n['c_2'], p=n['j_1'], n='j_' + n_limb2 + n_end)
        n['j_3'] = duplicate_joint(n['c_3'], p=n['j_2'], n='j_' + n_limb3 + n_end)
        n['j_e'] = duplicate_joint(n['c_e'], p=n['j_3'], n='j_' + n_eff + n_end)
        n['j_dg'] = duplicate_joint(n['c_dg'], p=n['j_e'], n='j_' + n_digits + n_end)
        self.set_id(n['j_1'], 'j.limb1')
        self.set_id(n['j_2'], 'j.limb2')
        self.set_id(n['j_3'], 'j.limb3')
        self.set_id(n['j_e'], 'j.limb4')
        self.set_id(n['j_dg'], 'j.digits')

        connect_matrix(n['c_1']['m'], n['j_1'], xyz=True)
        n['j_1']['jo'] = (0, 0, 0)

        for attr in ('t', 'rx', 'ry', 'rz', 'sx', 'sy', 'sz', 'ro'):
            n['c_2'][attr] >> n['j_2'][attr]
        mc.reorder(str(n['c_2']), front=1)

        for attr in ('t', 'rx', 'ry', 'rz', 'sx', 'sy', 'sz', 'ro'):
            n['c_3'][attr] >> n['j_3'][attr]
        mc.reorder(str(n['c_3']), front=1)

        if hook != default_hook:
            mk.Mod.add(n['c_1'], 'space', {'targets': ['::hook'], 'orient': True})

        # compatibility _common.limb
        n['j_e'] = n['c_e']
        n['j_dg'] = n['c_dg']

        # auto orient clavicle rig
        if self.do_clavicle:
            self.build_clav_auto()

        # quad chain
        _sub_chain = (n['c_1'], n['c_2'], n['c_3'])
        if quad_type == 'up':
            _sub_chain = (n['c_2'], n['c_3'], n['root_e'])

        # IK stretch
        n['root_eIK'] = mx.create_node(mx.tTransform, parent=default_hook, name='root_' + n_eff + '_IK' + n_end)
        copy_transform(n['c_e'], n['root_eIK'], t=True)
        n['x_eIK'] = mx.create_node(mx.tTransform, parent=n['root_eIK'], name='x_' + n_eff + 'IK' + n_end)
        n['c_eIK'] = duplicate_joint(n['c_e'], p=n['x_eIK'], n='c_' + n_eff + '_IK' + n_end)

        n['root_eIK_offset'] = mx.create_node(mx.tJoint, parent=default_hook, name='root_' + n_eff + '_IK_offset' + n_end)
        copy_transform(n['c_e'], n['root_eIK_offset'], t=True)
        n['c_eIK_offset'] = duplicate_joint(n['c_e'], p=n['root_eIK_offset'], n='c_' + n_eff + '_IK_offset' + n_end)

        mc.parent(str(n['root_eIK_offset']), str(n['c_eIK']))

        if self.get_opt('space_switch'):
            self.build_space_mods()

        n['ik'], n['eff_root'], n['eff_ik'] = stretch_ik(_sub_chain, n['c_eIK'])
        n['ik'].rename('ik_' + n_limb + n_end)
        n['eff_root'].rename('eff_' + n_limb + '_base' + n_end)
        n['eff_ik'].rename('eff_' + n_limb + n_end)
        if quad_type == 'up':
            mc.parent(str(n['eff_root']), str(n['root_1']))
            mc.parent(str(n['eff_ik']), str(n['root_1']))

        if self.get_opt('default_stretch'):
            n['c_eIK']['stretch'] = 1

        if quad_type == 'down':
            n['j_1'].add_attr(mx.Double('squash', keyable=True))
            n['j_2'].add_attr(mx.Double('squash', keyable=True))
            n['c_1']['squash'] >> n['j_1']['squash']
            n['c_2']['squash'] >> n['j_2']['squash']
        else:
            n['j_2'].add_attr(mx.Double('squash', keyable=True))
            n['j_3'].add_attr(mx.Double('squash', keyable=True))
            n['c_2']['squash'] >> n['j_2']['squash']
            n['c_3']['squash'] >> n['j_3']['squash']

        if self.do_clavicle:
            if self.do_clavicle_auto:
                mc.parent(str(n['ik_ao']), str(n['c_eIK']))
                n['ik']['twist'].input(plug=True) >> n['ik_ao']['twist']

            _hook = hook
            if _hook.is_a(mx.tJoint):
                _hook = hook.parent()
            mc.parent(str(n['eff_root']), str(_hook))
            mc.parent(str(n['eff_ik']), str(_hook))

        # switch controller
        n['root_sw'] = mx.create_node(mx.tTransform, parent=hook, name='root_' + n_limb + '_switch' + n_end)
        mc.reorder(str(n['root_sw']), front=1)

        n['root_sw']['v'] = False
        for attr in ['t', 'r', 's', 'v']:
            n['root_sw'][attr].lock()

        n['c_sw'] = mk.Control.create_control_shape(n['root_sw'], n='c_' + n_limb + '_switch' + n_end)

        # deform switch control
        n['sw'] = {}

        _nc = 1  # self.get_opt('deform_chains')
        for _c in range(_nc):
            n['sw'][_c] = mk.Control.create_control_shape(n['root_sw'], n='sw_' + n_limb + '_weights' + n_chain[_c] + n_end)
            self.set_id(n['sw'][_c], 'weights.{}'.format(_c))
            mc.reorder(str(n['sw'][_c]), front=1)

        # reverse IK rig
        self.build_reverse_lock()
        mc.parent(str(n['loc_lock']), str(n['c_3']))
        n['loc_lock']['tx'] = 0
        n['loc_lock']['tz'] = 0
        n['loc_lock']['r'] = (0, 0, 0)

        # change limb IK pointConstraint
        if quad_type == 'up':
            mx.delete(list(n['eff_ik'].inputs(type=mx.kConstraint)))
            mc.pointConstraint(str(n['end_emIK']), str(n['eff_ik']), n='_px#')

        # reverse lock IK poses
        if self.get_opt('reverse_lock'):
            self.build_reverse_lock_poses()

        # quad pole vector IK
        j_quadPV = duplicate_joint(n['c_1'], p=hook, n='j_' + n_limb + '_quad_PV' + n_end)
        mc.delete(mc.aimConstraint(str(n['c_e']), str(j_quadPV), aim=[0, 1, 0], u=[0, 0, 1], wu=[1, 0, 0], wut='vector'))
        mc.makeIdentity(str(j_quadPV), a=1)

        if not self.do_clavicle:
            mc.pointConstraint(str(n['c_1']), str(j_quadPV), n='_px#')
        else:
            mc.parentConstraint(str(n['c_clav']), str(j_quadPV), mo=1, n='_prx#')

        end_quadPV = duplicate_joint(n['c_e'], p=j_quadPV, n='end_' + n_limb + '_quad_PV' + n_end)
        end_quadPV['ty'] = end_quadPV['ty'].read() / 3

        ik_quadPV = create_ik_handle(sj=str(j_quadPV), ee=str(end_quadPV), sol='ikRPsolver', n='ik_' + n_limb + '_quad_PV_' + n_limb1 + n_end)
        ik_quadPV['snapEnable'] = False
        ik_quadPV['poleVector'] = (0, 0, 0)

        mc.parent(str(ik_quadPV), str(n['end_emIK']))
        ik_quadPV['t'] = (0, 0, 0)

        # quad hacks
        n['ik']['twist'].input(plug=True) >> ik_quadPV['twist']
        n['ik']['twist'].disconnect(destination=False)

        _db = mx.create_node(mx.tDistanceBetween, name='_len#')

        if quad_type == 'down':
            n['eff_root']['m'] >> _db['inMatrix1']
        else:
            eff_quadroot = mx.create_node(mx.tTransform, parent=hook, name='eff_' + n_limb + '_quad_root' + n_end)
            eff_quadroot['m'] >> _db['inMatrix1']
            mc.pointConstraint(str(n['c_1']), str(eff_quadroot))

        eff_quad = mx.create_node(mx.tTransform, parent=hook, name='eff_' + n_limb + '_quad' + n_end)
        mc.pointConstraint(str(n['end_emIK']), str(eff_quad), n='_px#')

        eff_quad['m'] >> _db['inMatrix2']

        # pole vector
        self.build_pole_vector_auto()
        self.build_pole_vector_follow()

        if not self.do_clavicle:
            if quad_type == 'up':
                mc.parent(str(n['ik_pvf']), str(eff_quadroot))
                n['ik_pvf']['t'] = (0, 0, 0)
        else:
            mc.parent(str(n['ik_pvf']), str(n['root_clav']))
            copy_transform(n['ik_pvf'], n['c_1'], t=True)
            mc.pointConstraint(str(n['c_clav']), str(n['ik_pvf']), mo=1)

        if quad_type == 'down':
            p1 = n['c_1'].translation(mx.sWorld)
            p2 = n['c_2'].translation(mx.sWorld)
            p3 = n['c_3'].translation(mx.sWorld)
        else:
            p1 = n['c_2'].translation(mx.sWorld)
            p2 = n['c_3'].translation(mx.sWorld)
            p3 = n['c_e'].translation(mx.sWorld)

        u = p2 - p1
        v = p3 - p1
        u1 = (u * v)
        v1 = (v * v)
        k = u1 / v1
        p4 = p1 + (v * k)
        v2 = p2 - p4
        p = p4 + v2 * (v.length() / v2.length())

        n['loc_pv'] = mx.create_node(mx.tTransform, parent=n['ao_pv'], name='loc_' + n_limb + '_PV_auto' + n_end)
        pos = mx.Transformation(translate=p)
        pos *= n['loc_pv']['pim'][0].as_transform()
        n['loc_pv']['t'] = pos.translation()

        n['loc_pvf'] = mx.create_node(mx.tTransform, parent=n['ao_pvf'], name='loc_' + n_limb + '_PV_follow' + n_end)
        copy_transform(n['loc_pv'], n['loc_pvf'], t=True)

        hook_pv = n['root_1']
        if self.do_clavicle:
            hook_pv = n['root_clav']
        n['root_pv'] = mx.create_node(mx.tTransform, parent=hook_pv, name='root_' + n_limb + '_PV' + n_end)
        n['c_pv'] = mx.create_node(mx.tTransform, parent=n['root_pv'], name='c_' + n_limb + '_PV' + n_end)

        _px = mc.pointConstraint(str(n['loc_pv']), str(n['loc_pvf']), str(n['root_pv']), n='_px#')
        _px = mx.encode(_px[0])

        pv_attr = 'follow_' + n_eff
        n['c_eIK'].add_attr(mx.Double(pv_attr, keyable=True, min=0, max=1))
        n['c_eIK'][pv_attr] >> _px['w1']
        connect_reverse(n['c_eIK'][pv_attr], _px['w0'])

        mc.poleVectorConstraint(str(n['c_pv']), str(ik_quadPV), n='_pvx#')

        if self.do_clavicle:
            if self.do_clavicle_auto:
                mc.poleVectorConstraint(str(n['loc_pv']), str(n['ik_ao']), n='_pvx#')
        else:
            dist = _db['d'].read()
            connect_driven_curve(_db['d'], n['ao_pv']['sy'], {0: 0, dist: 1, (dist * 2): 2}, post='linear', key_style='linear')
            n['ao_pv']['sy'].input(plug=True) >> n['ao_pvf']['sy']

        dist = _db['d'].read()
        connect_driven_curve(_db['d'], j_quadPV['sy'], {0: 0, dist: 1, (dist * 2): 2}, post='linear', key_style='linear')

        pvq = mx.create_node(mx.tTransform, parent=j_quadPV, name='loc_' + n_limb + '_PV_quad' + n_end)
        copy_transform(n['loc_pv'], pvq, t=True)
        mc.poleVectorConstraint(str(pvq), str(n['ik']), n='_pvx#')

        # quad attrs
        n['c_eIK'].add_attr(mx.Divider('quad'))

        n['c_eIK'].add_attr(mx.Double('quad_twist', keyable=True))
        if self.do_flip():
            n['c_eIK']['quad_twist'] >> n['ik']['twist']
        else:
            connect_mult(n['c_eIK']['quad_twist'], -1, n['ik']['twist'])

        # quad IK chain
        _quad_orient = n['c_3']
        _quad_locstart = n['end_emIK']
        _quad_locend = n['c_3']
        _quad_ikstart = n['c_3']
        _quad_ikend = n['root_e']
        _quad_stretch = n['c_1']

        if quad_type == 'up':
            _quad_orient = n['c_1']
            _quad_locstart = n['c_1']
            _quad_locend = n['c_2']
            _quad_ikstart = n['c_1']
            _quad_ikend = n['c_2']
            _quad_stretch = n['end_emIK']

        j_quad = duplicate_joint(_quad_orient, p=n['o_1'], n='j_' + n_limb + '_quad' + n_end)
        _0 = mx.create_node(mx.tAnimCurveUA)
        mc.setKeyframe(str(_0), v=0, f=0)
        _0['output'] >> j_quad['rx']
        _0['output'] >> j_quad['ry']
        _0['output'] >> j_quad['rz']
        mc.pointConstraint(str(_quad_locstart), str(j_quad), n='_px#')

        end_quad = duplicate_joint(_quad_orient, p=j_quad, n='end_' + n_limb + '_quad' + n_end)
        copy_transform(_quad_locend, end_quad, t=True)

        o_quad = mx.create_node(mx.tTransform, parent=j_quad, name='o_' + n_limb + '_quad' + n_end)
        loc_quad = mx.create_node(mx.tTransform, parent=o_quad, name='loc_' + n_limb + '_quad' + n_end)

        copy_transform(end_quad, loc_quad, t=True)

        if quad_type == 'down':
            connect_mult(n['c_3']['sy'], loc_quad['ty'].read(), loc_quad['ty'])
        else:
            connect_mult(n['c_1']['sy'], loc_quad['ty'].read(), loc_quad['ty'])

        # change main IK pointConstraint
        if quad_type == 'down':
            mx.delete(list(n['eff_ik'].inputs(type=mx.kConstraint)))
            mc.pointConstraint(str(loc_quad), str(n['eff_ik']))

        # quad IK handle
        ikq = create_ik_handle(sj=str(_quad_ikstart), ee=str(_quad_ikend), sol='ikSCsolver')
        mc.parent(str(ikq), str(o_quad))
        if quad_type == 'down':
            mc.pointConstraint(str(n['end_emIK']), str(ikq))

        ikq['snapEnable'] = False
        ikq.rename('ik_' + n_limb + '_quad' + n_end)

        o_quad['ro'] = mx.Euler.YZX
        n['c_eIK'].add_attr(mx.Double('quad_roll', keyable=True))
        n['c_eIK'].add_attr(mx.Double('quad_pivot', keyable=True))
        n['c_eIK']['quad_roll'] >> o_quad['rx']
        n['c_eIK']['quad_pivot'] >> o_quad['rz']

        # IK revquad
        troot_quad = mx.create_node(mx.tTransform, parent=_quad_orient, name='troot_quad' + n_end)
        mc.parent(str(troot_quad), str(j_quadPV))
        if quad_type == 'up':  # up
            mc.pointConstraint(str(n['end_emIK']), str(troot_quad), n='_px#')
        else:
            mc.pointConstraint(str(n['c_1']), str(troot_quad), n='_px#')

        t_quad = mx.create_node(mx.tTransform, parent=_quad_orient, name='t_quad' + n_end)
        mc.delete(mc.pointConstraint(str(_quad_stretch), str(t_quad), sk=['x', 'z']))
        mc.parent(str(t_quad), str(troot_quad))

        n['c_eIK'].add_attr(mx.Double('quad_lock', keyable=True, min=0, max=1))
        if quad_type == 'down':
            mc.orientConstraint(str(n['c_eIK_offset']), str(j_quad), mo=1)

        ikqa = create_ik_handle(sj=str(j_quad), ee=str(end_quad), sol='ikSCsolver')
        ikqa['snapEnable'] = False
        ikqa.rename('ik_' + n_limb + '_quad_auto' + n_end)

        mc.parent(str(ikqa), str(t_quad))
        ikqa['t'] = (0, 0, 0)

        connect_reverse(n['c_eIK']['quad_lock'], ikqa['ikBlend'])

        # stretch IK revquad
        pb = mx.create_node(mx.tPairBlend, name='_pb#')
        pb['inTranslate2'] = t_quad['t']
        pb['outTranslate'] >> t_quad['t']

        n['c_eIK'].add_attr(mx.Double('quad_slide_min', default=0, min=0))
        n['c_eIK'].add_attr(mx.Double('quad_slide_max', default=1, min=1))
        n['c_eIK']['quad_slide_min'].channel_box = True
        n['c_eIK']['quad_slide_max'].channel_box = True

        _quad_ikstart.add_attr(mx.Double('stretch', default=1))
        _quad_ikstart.add_attr(mx.Double('squash', default=1))

        # quad stretch network
        _s1 = n['c_1']['sy']
        _s2 = n['c_2']['sy']
        _s3 = n['c_3']['sy']
        _t1 = connect_mult(abs(n['c_2']['ty'].read()), _s1)
        _t2 = connect_mult(abs(n['c_3']['ty'].read()), _s2)
        _t3 = connect_mult(abs(n['root_e']['ty'].read()), _s3)
        _dchain = connect_expr('t1 + t2 + t3', t1=_t1, t2=_t2, t3=_t3)

        _qmin = n['c_eIK']['quad_slide_min']
        _qmax = n['c_eIK']['quad_slide_max']
        _d = _db['distance']
        _d0 = _d.read()

        _w1 = connect_expr('1 - (d - d0) / (chain * qmax - d0)', d=_d, d0=_d0, chain=_dchain, qmax=_qmax)
        _w1 = connect_expr('w1 < 0 ? 0 : w1', w1=_w1)
        _w0 = connect_expr('1 - (d - d0) / (-d0 * (1 - qmin))', d=_d, d0=_d0, qmin=_qmin)

        connect_expr('w = d > d0 ? w1 : w0', w=pb['w'], d=_d, d0=_d0, w1=_w1, w0=_w0)

        # IK switch
        n['c_sw'].add_attr(mx.Double('ik_blend', keyable=True, min=0, max=1, default=1))
        mult = connect_mult(n['c_sw']['ik_blend'], 1, n['ik']['ikBlend'])
        mult >> ikq['ikBlend']
        mult >> n['ik_em']['ikBlend']

        lock_attr = n_digits + '_lock'
        n['c_eIK'].add_attr(mx.Boolean(lock_attr, default=self.get_opt('reverse_lock')))
        connect_mult(n['c_eIK'][lock_attr], n['c_sw']['ik_blend'], n['ik_dg']['ikBlend'])

        # deform rig
        n['root_2pt'] = duplicate_joint(n['c_2'], n='root_' + n_limb2 + '_tweak' + n_end)
        n['c_2pt'] = mx.create_node(mx.tTransform, parent=n['root_2pt'], name='c_' + n_limb2 + '_tweak' + n_end)
        n['c_2pt']['displayHandle'] = True

        if self.do_flip():
            n['root_2pt']['s'] = (-1, -1, -1)

        mc.pointConstraint(str(n['j_2']), str(n['root_2pt']), n='_px#')
        oc = mc.orientConstraint(str(n['j_1']), str(n['j_2']), str(n['root_2pt']), n='_ox#')
        oc = mx.encode(oc[0])
        oc['interpType'] = 2

        mk.Mod.add(n['c_2pt'], 'space', {'targets': ['::hook']})

        n['root_3pt'] = duplicate_joint(n['c_3'], n='root_' + n_limb3 + '_tweak' + n_end)
        n['c_3pt'] = mx.create_node(mx.tTransform, parent=n['root_3pt'], name='c_' + n_limb3 + '_tweak' + n_end)
        n['c_3pt']['displayHandle'] = True

        if self.do_flip():
            n['root_3pt']['s'] = (-1, -1, -1)

        mc.pointConstraint(str(n['c_3']), str(n['root_3pt']), n='_px#')
        oc = mc.orientConstraint(str(n['c_2']), str(n['c_3']), str(n['root_3pt']), n='_ox#')
        oc = mx.encode(oc[0])
        oc['interpType'] = 2

        mk.Mod.add(n['c_3pt'], 'space', {'targets': ['::hook']})

        # skin rig: skin joints
        n['aim_1'] = duplicate_joint(n['c_1'], p=n['j_1'], n='j_' + n_limb1 + '_aim' + n_end)
        n['aim_2'] = duplicate_joint(n['c_2'], p=n['j_2'], n='j_' + n_limb2 + '_aim' + n_end)
        n['aim_3'] = duplicate_joint(n['c_3'], p=n['j_3'], n='j_' + n_limb3 + '_aim' + n_end)
        n['sub_1'] = duplicate_joint(n['aim_1'], p=n['j_1'], n='j_' + n_limb1 + '_deform' + n_end)
        n['sub_2'] = duplicate_joint(n['aim_2'], p=n['j_2'], n='j_' + n_limb2 + '_deform' + n_end)
        n['sub_3'] = duplicate_joint(n['aim_3'], p=n['j_3'], n='j_' + n_limb3 + '_deform' + n_end)
        mc.reorder(str(n['sub_1']), front=1)
        mc.reorder(str(n['sub_2']), front=1)
        mc.reorder(str(n['sub_3']), front=1)

        ac1 = mc.aimConstraint(str(n['c_2pt']), str(n['sub_1']), aim=[0, (-1, 1)[not aim_axis.startswith('-')], 0], wut='none', n='_ax#')
        ac2 = mc.aimConstraint(str(n['c_3pt']), str(n['sub_2']), aim=[0, (-1, 1)[not aim_axis.startswith('-')], 0], wut='none', n='_ax#')
        ac3 = mc.aimConstraint(str(n['c_e']), str(n['sub_3']), aim=[0, (-1, 1)[not aim_axis.startswith('-')], 0], wut='none', n='_ax#')
        ac1 = mx.encode(ac1[0])
        ac2 = mx.encode(ac2[0])
        ac3 = mx.encode(ac3[0])

        mc.pointConstraint(str(n['c_2pt']), str(n['sub_2']), n='_px#')
        mc.pointConstraint(str(n['c_3pt']), str(n['sub_3']), n='_px#')

        # skin rig: effector
        n['sub_e'] = duplicate_joint(n['j_e'], p=n['j_e'], n='j_' + n_eff + '_deform' + n_end)

        n['sk_e'] = duplicate_joint(n['c_e'], n='sk_' + n_eff + n_end, p=n['c_e'])
        duplicate_joint(n['c_dg'], n='end_' + n_eff + n_end, p=n['sk_e'])
        mc.reorder(str(n['sk_e']), front=1)
        n['sk_dg'] = duplicate_joint(n['c_dg'], n='sk_' + n_digits + n_end, p=n['c_dg'])
        n['j_dge'] = duplicate_joint(n['end_dg'], n='j_' + n_eff + 'Tip' + n_end, p=n['sk_dg'])
        mc.reorder(str(n['sk_dg']), front=1)

        n['sk_e']['ssc'] = False
        n['sk_dg']['ssc'] = False

        # twist fix
        n['c_sw'].add_attr(mx.Double('twist_fix1', keyable=True))
        n['c_sw'].add_attr(mx.Double('twist_fix2', keyable=True))

        # flex rig
        sw = n['sw'][0]
        sw.add_attr(mx.Divider('flex'))

        n['loc_2pt_up'] = mx.create_node(mx.tTransform, parent=n['c_2pt'], name='loc_' + n_limb2 + '_tweak_up' + n_end)
        n['loc_2pt_dn'] = mx.create_node(mx.tTransform, parent=n['c_2pt'], name='loc_' + n_limb2 + '_tweak_dn' + n_end)

        xfo1 = n['c_1']
        xfo2 = n['c_2pt']
        xfo3 = n['c_3']

        mmx = mx.create_node(mx.tMultMatrix, name='_mmx')
        xfo1['wm'][0] >> mmx['i'][0]
        xfo2['wim'][0] >> mmx['i'][1]
        dmx = mx.create_node(mx.tDecomposeMatrix, name='_dmx')
        mmx['o'] >> dmx['imat']
        v1 = dmx['outputTranslate']

        mmx = mx.create_node(mx.tMultMatrix, name='_mmx')
        xfo3['wm'][0] >> mmx['i'][0]
        xfo2['wim'][0] >> mmx['i'][1]
        dmx = mx.create_node(mx.tDecomposeMatrix, name='_dmx')
        mmx['o'] >> dmx['imat']
        v2 = dmx['outputTranslate']

        angle = mx.create_node(mx.tAngleBetween, name='_angle')
        v1 >> angle['vector1']
        v2 >> angle['vector2']
        angle0 = mx.Radians(angle['angle'].read()).asDegrees()
        sw.add_attr(mx.Double('flex_offset1_start', keyable=True, min=0, max=1, default=0.5))
        angle_weight = connect_expr('max(0, 1-(a/(a0*max(1-w, 0.001))))', a=angle['angle'], a0=angle0, w=sw['flex_offset1_start'])

        sw.add_attr(mx.Double('flex_offset1_upX', keyable=True))
        sw.add_attr(mx.Double('flex_offset1_upY', keyable=True))
        sw.add_attr(mx.Double('flex_offset1_upZ', keyable=True))
        sw.add_attr(mx.Double('flex_offset1_dnX', keyable=True))
        sw.add_attr(mx.Double('flex_offset1_dnY', keyable=True))
        sw.add_attr(mx.Double('flex_offset1_dnZ', keyable=True))

        for side in ('up', 'dn'):
            for dim in 'XYZ':
                connect_mult(sw['flex_offset1_' + side + dim], angle_weight, n['loc_2pt_' + side]['translate' + dim])

        n['loc_3pt_up'] = mx.create_node(mx.tTransform, parent=n['c_3pt'], name='loc_' + n_limb3 + '_tweak_up' + n_end)
        n['loc_3pt_dn'] = mx.create_node(mx.tTransform, parent=n['c_3pt'], name='loc_' + n_limb3 + '_tweak_dn' + n_end)

        xfo1 = n['c_2']
        xfo2 = n['c_3pt']
        xfo3 = n['root_e']

        mmx = mx.create_node(mx.tMultMatrix, name='_mmx')
        xfo1['wm'][0] >> mmx['i'][0]
        xfo2['wim'][0] >> mmx['i'][1]
        dmx = mx.create_node(mx.tDecomposeMatrix, name='_dmx')
        mmx['o'] >> dmx['imat']
        v1 = dmx['outputTranslate']

        mmx = mx.create_node(mx.tMultMatrix, name='_mmx')
        xfo3['wm'][0] >> mmx['i'][0]
        xfo2['wim'][0] >> mmx['i'][1]
        dmx = mx.create_node(mx.tDecomposeMatrix, name='_dmx')
        mmx['o'] >> dmx['imat']
        v2 = dmx['outputTranslate']

        angle = mx.create_node(mx.tAngleBetween, name='_angle')
        v1 >> angle['vector1']
        v2 >> angle['vector2']
        angle0 = mx.Radians(angle['angle'].read()).asDegrees()
        sw.add_attr(mx.Double('flex_offset2_start', keyable=True, min=0, max=1, default=0.5))
        angle_weight = connect_expr('max(0, 1-(a/(a0*max(1-w, 0.001))))', a=angle['angle'], a0=angle0, w=sw['flex_offset2_start'])

        sw.add_attr(mx.Double('flex_offset2_upX', keyable=True))
        sw.add_attr(mx.Double('flex_offset2_upY', keyable=True))
        sw.add_attr(mx.Double('flex_offset2_upZ', keyable=True))
        sw.add_attr(mx.Double('flex_offset2_dnX', keyable=True))
        sw.add_attr(mx.Double('flex_offset2_dnY', keyable=True))
        sw.add_attr(mx.Double('flex_offset2_dnZ', keyable=True))

        for side in ('up', 'dn'):
            for dim in 'XYZ':
                connect_mult(sw['flex_offset2_' + side + dim], angle_weight, n['loc_3pt_' + side]['translate' + dim])

        # bend rig
        n['root_1bd'] = mx.create_node(mx.tTransform, parent=n['sub_1'], name='root_' + n_limb1 + '_bend' + n_end)
        n['c_1bd'] = mx.create_node(mx.tTransform, parent=n['root_1bd'], name='c_' + n_limb1 + '_bend' + n_end)
        n['c_1bd']['displayHandle'] = True
        mc.pointConstraint(str(n['c_1']), str(n['loc_2pt_up']), str(n['root_1bd']), n='_px#')

        n['root_2bd'] = mx.create_node(mx.tTransform, parent=n['sub_2'], name='root_' + n_limb2 + '_bend' + n_end)
        n['c_2bd'] = mx.create_node(mx.tTransform, parent=n['root_2bd'], name='c_' + n_limb2 + '_bend' + n_end)
        n['c_2bd']['displayHandle'] = True
        mc.pointConstraint(str(n['loc_2pt_dn']), str(n['loc_3pt_up']), str(n['root_2bd']), n='_px#')

        n['root_3bd'] = mx.create_node(mx.tTransform, parent=n['sub_3'], name='root_' + n_limb3 + '_bend' + n_end)
        n['c_3bd'] = mx.create_node(mx.tTransform, parent=n['root_3bd'], name='c_' + n_limb3 + '_bend' + n_end)
        n['c_3bd']['displayHandle'] = True
        mc.pointConstraint(str(n['loc_3pt_dn']), str(n['c_e']), str(n['root_3bd']), n='_px#')

        n['rig_smooth'] = mx.create_node(mx.tTransform, parent=n['root_1'], name='rig_' + n_limb + '_spline' + n_end)
        n['rig_smooth']['v'] = False

        n['cv_sm'] = create_path(n['j_1'], n['c_1bd'], n['c_2pt'], n['c_2bd'], n['c_3pt'], n['c_3bd'], n['j_e'], d=3)
        mc.parent(str(n['cv_sm']), str(n['rig_smooth']), r=1)
        n['cv_sm'].rename('cv_' + n_limb + n_end)

        # smooth outputs
        n['c_sw'].add_attr(mx.Double('smooth', keyable=True, min=0, max=1))
        n['sm_on'] = n['c_sw']['smooth']
        n['sm_off'] = connect_reverse(n['sm_on'])

        if self.do_flip():
            n['root_1bd']['s'] = (-1, -1, -1)
            n['root_2bd']['s'] = (-1, -1, -1)
            n['root_3bd']['s'] = (-1, -1, -1)

        # shear up
        root_sh_up = duplicate_joint(n['sub_1'], p=n['root_1'], n='root_shear_up')
        n['loc_sh_up'] = duplicate_joint(n['sub_1'], p=root_sh_up, n='loc_shear_up')
        n['sh_up'] = mx.create_node(mx.tDecomposeMatrix, name='_quat#')
        n['loc_sh_up']['matrix'] >> n['sh_up']['inputMatrix']
        n['shx_up'] = n['sh_up']['outputQuatX']
        n['shz_up'] = connect_mult(n['sh_up']['outputQuatZ'], -1)

        n['c_1'].add_attr(mx.Double('qx'))
        n['c_1'].add_attr(mx.Double('qy'))
        n['c_1'].add_attr(mx.Double('qz'))
        n['sh_up']['outputQuatX'] >> n['c_1']['qx']
        n['sh_up']['outputQuatY'] >> n['c_1']['qy']
        n['sh_up']['outputQuatZ'] >> n['c_1']['qz']

        # shear mid
        n['root_sh_m'] = duplicate_joint(n['sub_2'], p=n['sub_1'], n='root_shear_m')
        n['loc_sh_m'] = duplicate_joint(n['sub_2'], p=n['root_sh_m'], n='loc_shear_m')
        n['sh_m'] = mx.create_node(mx.tDecomposeMatrix, name='_quat#')
        n['loc_sh_m']['matrix'] >> n['sh_m']['inputMatrix']
        n['shx_m'] = n['sh_m']['outputQuatX']
        n['shz_m'] = connect_mult(n['sh_m']['outputQuatZ'], -1)

        n['c_2'].add_attr(mx.Double('qx'))
        n['c_2'].add_attr(mx.Double('qy'))
        n['c_2'].add_attr(mx.Double('qz'))
        n['sh_m']['outputQuatX'] >> n['c_2']['qx']
        n['sh_m']['outputQuatY'] >> n['c_2']['qy']
        n['sh_m']['outputQuatZ'] >> n['c_2']['qz']

        # shear quad
        n['root_sh_q'] = duplicate_joint(n['sub_3'], p=n['sub_2'], n='root_shear_q')
        n['loc_sh_q'] = duplicate_joint(n['sub_3'], p=n['root_sh_q'], n='loc_shear_q')
        n['sh_q'] = mx.create_node(mx.tDecomposeMatrix, name='_quat#')
        n['loc_sh_q']['matrix'] >> n['sh_q']['inputMatrix']
        n['shx_q'] = n['sh_q']['outputQuatX']
        n['shz_q'] = connect_mult(n['sh_q']['outputQuatZ'], -1)

        n['c_3'].add_attr(mx.Double('qx'))
        n['c_3'].add_attr(mx.Double('qy'))
        n['c_3'].add_attr(mx.Double('qz'))
        n['sh_q']['outputQuatX'] >> n['c_3']['qx']
        n['sh_q']['outputQuatY'] >> n['c_3']['qy']
        n['sh_q']['outputQuatZ'] >> n['c_3']['qz']

        # shear dn
        root_sh_dn = duplicate_joint(n['sub_3'], p=n['sub_e'], n='root_shear_dn')
        root_sh_dn['t'] = (0, 0, 0)
        n['loc_sh_dn'] = duplicate_joint(root_sh_dn, p=root_sh_dn, n='loc_shear_dn')
        n['sh_dn'] = mx.create_node(mx.tDecomposeMatrix, name='_quat#')
        n['loc_sh_dn']['matrix'] >> n['sh_dn']['inputMatrix']
        n['shx_dn'] = n['sh_dn']['outputQuatX']
        n['shz_dn'] = connect_mult(n['sh_dn']['outputQuatZ'], -1)

        n['c_e'].add_attr(mx.Double('qx'))
        n['c_e'].add_attr(mx.Double('qy'))
        n['c_e'].add_attr(mx.Double('qz'))
        n['sh_dn']['outputQuatX'] >> n['c_e']['qx']
        # n['sh_dn']['outputQuatY'] >> n['c_e']['qy']
        n['sh_dn']['outputQuatZ'] >> n['c_e']['qz']

        # splits
        n['sk_su'] = self.build_twist_joints(
            nj=self.get_opt('splits_up'),
            tw='up', name=n_limb1,
            c=n['c_1'], sk=n['j_1'],
            j_base=n['c_1'], j_mid=n['c_1bd'], j_tip=n['loc_2pt_up'])

        n['sk_sm'] = self.build_twist_joints(
            nj=self.get_opt('splits_mid'),
            tw='mid', name=n_limb2,
            c=n['c_2'], sk=n['j_2'],
            j_base=n['loc_2pt_dn'], j_mid=n['c_2bd'], j_tip=n['loc_3pt_up'])

        n['sk_sd'] = self.build_twist_joints(
            nj=self.get_opt('splits_down'),
            tw='dn', name=n_limb3,
            c=n['c_3'], sk=n['j_3'],
            j_base=n['loc_3pt_dn'], j_mid=n['c_3bd'], j_tip=n['c_e'])

        def do_limb_twist_end(jdup, jpos):
            jend = duplicate_joint(jdup, p=jdup, n=jdup.name(namespace=False).replace('sk_', 'end_'))
            copy_transform(jpos, jend, t=True)

        for i, sk in enumerate(n['sk_su'][0][:-1]):
            do_limb_twist_end(n['sk_su'][0][i], n['sk_su'][0][i + 1])
        for i, sk in enumerate(n['sk_sm'][0][:-1]):
            do_limb_twist_end(n['sk_sm'][0][i], n['sk_sm'][0][i + 1])
        for i, sk in enumerate(n['sk_sd'][0][:-1]):
            do_limb_twist_end(n['sk_sd'][0][i], n['sk_sd'][0][i + 1])
        do_limb_twist_end(n['sk_su'][0][-1], n['sk_sm'][0][0])
        do_limb_twist_end(n['sk_sm'][0][-1], n['sk_sd'][0][0])
        do_limb_twist_end(n['sk_sd'][0][-1], n['c_e'])

        # fix effector qy
        _q = mx.create_node(mx.tEulerToQuat, name='_quat#')
        n['j_tw_dn']['r'] >> _q['inputRotate']
        n['j_tw_dn']['ro'] >> _q['inputRotateOrder']
        _q['outputQuatY'] >> n['c_e']['qy']

        # rollbones
        if self.get_opt('blend_joints'):

            rb_limb1 = n['root_1']
            if self.do_clavicle:
                rb_limb1 = n['inf_clav']
            n['rb1'] = create_blend_joint(n['sk_su'][0][0].parent(), rb_limb1, n='sk_' + n_limb1 + '_blend' + n_end)
            n['rb2'] = create_blend_joint(n['sk_sm'][0][0].parent(), n['sk_su'][0][-1].parent(), n='o_' + n_limb2 + '_blend' + n_end)
            n['rb3'] = create_blend_joint(n['sk_sd'][0][0].parent(), n['sk_sm'][0][-1].parent(), n='o_' + n_limb3 + '_blend' + n_end)
            n['rbe'] = create_blend_joint(n['sk_e'], n['sk_sd'][0][-1].parent(), n='sk_' + n_eff + '_blend' + n_end)

            mc.parent(str(n['rb1']), str(n['sub_1']))
            mc.reorder(str(n['rb1']), f=1)
            n['sk_su'][0][0]['s'] >> n['rb1']['s']

            mc.parent(str(n['rb2']), str(n['sub_2']))
            mc.reorder(str(n['rb2']), f=1)
            n['sk_rb2'] = duplicate_joint(n['sub_2'], p=n['sub_2'], n='sk_' + n_limb2 + '_blend' + n_end)
            mc.parent(str(n['sk_rb2']), str(n['rb2']))

            n['sk_sm'][0][0]['s'] >> n['sk_rb2']['s']
            pc = mc.pointConstraint(str(n['loc_2pt_up']), str(n['loc_2pt_dn']), str(n['p2_pt']), str(n['rb2']), n='_px#')
            pc = mx.encode(pc[0])
            n['sm_off'] >> pc['w0']
            n['sm_off'] >> pc['w1']
            n['sm_on'] >> pc['w2']

            mc.parent(str(n['rb3']), str(n['sub_3']))
            mc.reorder(str(n['rb3']), f=1)

            n['sk_rb3'] = duplicate_joint(n['rb3'], p=n['rb3'], n='sk_' + n_limb3 + '_blend' + n_end)

            n['sk_sd'][0][0]['s'] >> n['sk_rb3']['s']
            pc = mc.pointConstraint(str(n['loc_3pt_up']), str(n['loc_3pt_dn']), str(n['p3_pt']), str(n['rb3']), n='_px#')
            pc = mx.encode(pc[0])
            n['sm_off'] >> pc['w0']
            n['sm_off'] >> pc['w1']
            n['sm_on'] >> pc['w2']

            mc.parent(str(n['rbe']), str(n['j_e']))
            mc.reorder(str(n['rbe']), f=1)

        # fix inverse scale hierarchy
        fix_inverse_scale(list(n['root_eIK'].descendents()))
        fix_inverse_scale(list(n['root_1'].descendents()))
        if self.do_clavicle:
            fix_inverse_scale(n['root_clav'], list(n['root_clav'].descendents()))

        # channels
        for c in (n['c_2'], n['c_3'], n['c_e'], n['c_dg']):
            for dim in 'xyz':
                c['t' + dim].keyable = False
                c['t' + dim].lock()

        for c in (n['c_2pt'], n['c_3pt'], n['c_1bd'], n['c_2bd'], n['c_3bd']):
            for attr in 'sr':
                for dim in 'xyz':
                    c[attr + dim].keyable = False
                    c[attr + dim].lock()

        n['c_1'].set_limit(mx.kScaleMinY, 0.01)
        n['c_2'].set_limit(mx.kScaleMinY, 0.01)
        n['c_3'].set_limit(mx.kScaleMinY, 0.01)

        n['c_e'].set_limit(mx.kScaleMinX, 0.01)
        n['c_e'].set_limit(mx.kScaleMinY, 0.01)
        n['c_e'].set_limit(mx.kScaleMinZ, 0.01)

        # rotate orders
        self.build_rotate_order()

        # common switch shape
        for c in ('c_clav', 'c_1', 'c_2', 'c_3', 'c_e', 'c_eIK', 'c_eIK_offset', 'c_dg', 'c_1bd', 'c_2bd', 'c_2pt'):
            if c in n:
                mc.parent(str(n['sw'][0]), str(n[c]), r=1, s=1, add=1)
                mk.Control.set_control_shape(n['c_sw'], n[c])

        n['sw'][0]['ihi'] = True

        # skin gizmo
        for i, sk in enumerate(n['sk_su'][0]):
            sk['radius'] = 0.5
        for i, sk in enumerate(n['sk_sm'][0]):
            sk['radius'] = 0.5
        for i, sk in enumerate(n['sk_sd'][0]):
            sk['radius'] = 0.5

        n['rb1']['radius'] = 1.5
        n['rb2']['radius'] = 1.5
        n['rb3']['radius'] = 1.5
        n['rbe']['radius'] = 1.5

        n['sk_dg']['drawStyle'] = 2

        # ui functions
        n['c_eIK'].add_attr(mx.Message('menu_offset_pivot'))

        # ui ik/fk match
        ui_ikfk = mx.create_node(mx.tNetwork, name='ui_match_IKFK' + n_limb + n_end)
        for c in (n['c_eIK'], n['c_1'], n['c_2'], n['c_e']):
            c.add_attr(mx.Message('ui_match_IK_FK'))
            ui_ikfk['msg'] >> c['ui_match_IK_FK']

        ui_ikfk.add_attr(mx.Double('switch'))
        ui_ikfk.add_attr(mx.Double('twist'))
        ui_ikfk.add_attr(mx.Message('ik'))
        ui_ikfk.add_attr(mx.Message('fk', array=True, indexMatters=False))

        ui_ikfk.add_attr(mx.Double('twist_factor', default=(1, -1)[self.do_flip()]))

        n['c_sw']['ik_blend'] >> ui_ikfk['switch']
        n['c_eIK']['twist'] >> ui_ikfk['twist']

        n['c_eIK']['msg'] >> ui_ikfk['ik']

        n['c_1']['msg'] >> ui_ikfk['fk'][0]
        n['c_2']['msg'] >> ui_ikfk['fk'][1]
        n['c_3']['msg'] >> ui_ikfk['fk'][2]
        n['c_e']['msg'] >> ui_ikfk['fk'][3]

        # vis group
        grp = mk.Group.create('{}{} shape'.format(self.name, self.get_branch_suffix(' ')))
        for c in ('c_1bd', 'c_2bd', 'c_3bd', 'c_2pt', 'c_3pt'):
            grp.add_member(n[c])
        self.set_id(grp.node, 'vis.shape')

        n['c_eIK_offset']['v'] = False
        grp = mk.Group.create('{} offset{}'.format(self.name, self.get_branch_suffix(' ')))
        for c in ['c_eIK_offset']:
            grp.add_member(n[c])
        self.set_id(grp.node, 'vis.offset')

        # hooks
        self.set_hook(tpl_limb1, n['sub_1'], 'hooks.limb1')
        self.set_hook(tpl_limb2, n['sub_2'], 'hooks.limb2')
        self.set_hook(tpl_limb3, n['sub_3'], 'hooks.limb3')
        self.set_hook(tpl_limb4, n['sk_e'], 'hooks.effector')
        self.set_hook(tpl_digits, n['sk_dg'], 'hooks.digits')
        if self.do_clavicle:
            self.set_hook(self.get_structure('clavicle')[0], n['sk_clav'], 'hooks.clavicle')

        # tag nodes
        self.set_id(n['c_1'], 'ctrls.limb1')
        self.set_id(n['c_2'], 'ctrls.limb2')
        self.set_id(n['c_3'], 'ctrls.limb3')
        self.set_id(n['c_e'], 'ctrls.limb4')
        self.set_id(n['c_eIK'], 'ctrls.ik')
        self.set_id(n['c_eIK_offset'], 'ctrls.ik_offset')
        self.set_id(n['c_dg'], 'ctrls.digits')
        self.set_id(n['c_1bd'], 'ctrls.bend1')
        self.set_id(n['c_2bd'], 'ctrls.bend2')
        self.set_id(n['c_3bd'], 'ctrls.bend3')
        self.set_id(n['c_2pt'], 'ctrls.tweak1')
        self.set_id(n['c_3pt'], 'ctrls.tweak2')
        self.set_id(n['c_sw'], 'ctrls.switch')
        if self.do_clavicle:
            self.set_id(n['c_clav'], 'ctrls.clavicle')

        for i, j in enumerate(n['sk_su'][0]):
            self.set_id(j, 'skin.up.{}'.format(i))
            self.set_id(j.parent(), 'roots.up.{}'.format(i))
        self.set_id(n['sk_su'][0][-1], 'skin.last.up')

        for i, j in enumerate(n['sk_sd'][0]):
            self.set_id(j, 'skin.dn.{}'.format(i))
            self.set_id(j.parent(), 'roots.dn.{}'.format(i))
        self.set_id(n['sk_sd'][0][-1], 'skin.last.dn')

        for i, j in enumerate(n['sk_sm'][0]):
            self.set_id(j, 'skin.mid.{}'.format(i))
            self.set_id(j.parent(), 'roots.mid.{}'.format(i))
        self.set_id(n['sk_sm'][0][-1], 'skin.last.mid')

        if self.do_clavicle:
            self.set_id(n['sk_clav'], 'skin.clavicle')
        if self.get_opt('blend_joints'):
            self.set_id(n['rb1'], 'skin.bj1')
            self.set_id(n['sk_rb2'], 'skin.bj2')
            self.set_id(n['sk_rb3'], 'skin.bj3')
            self.set_id(n['rbe'], 'skin.bje')

        self.set_id(n['sk_e'], 'skin.effector')
        self.set_id(n['sk_dg'], 'skin.digits')

        self.set_id(n['root_sw'], 'roots.switch')
        self.set_id(n['root_eIK'], 'roots.effector')

        self.set_id(n['end_dg'], 'tip')

    def build_twist_joints(self, nj, tw, name, c, sk, j_base, j_mid, j_tip):
        n = self.n

        n_end = self.get_branch_suffix()

        nc = 1
        n_chain = ['']

        roots = [[] for _c in range(nc)]
        p1s = {}
        sks = [[] for _c in range(nc)]
        mxs = [[] for _c in range(nc)]
        sqx = connect_mult(c['sx'], c['squash'])
        sqz = connect_mult(c['sz'], c['squash'])
        nty = 1

        loc_end = mx.create_node(mx.tTransform, parent=sk, name='loc_' + name + '_tip' + n_end)
        copy_transform(j_tip, loc_end, t=True)

        for i in range(nj + 2):

            # build joints
            if i <= nj:
                for _c in range(nc):
                    j = duplicate_joint(c, n='root_' + name + str(i) + n_chain[_c] + n_end, p=sk)
                    roots[_c].append(j)

                    j = duplicate_joint(c, p=roots[_c][-1], n='sk_' + name + str(i) + n_chain[_c] + n_end)
                    sks[_c].append(j)
                    mxs[_c].append(mx.create_node(mx.tFourByFourMatrix, name='_mx#'))

            # bend points
            if 0 < i <= nj:
                p1 = mx.create_node(mx.tTransform, parent=sk, name='p1_' + name + str(i) + n_end)
                p1s[i] = p1

                if nj > 1:
                    pc1 = mc.pointConstraint(str(j_base), str(j_mid), str(j_tip), str(p1))
                    pc1 = mx.encode(pc1[0])
                    tx = i / ((nj + 1) / 2.) - 1
                    x = 0.7071  # cos(45) dt.cos(dt.Angle(45).asRadians())
                    ty = math.sin(math.acos(tx * x)) - x
                    if i == 1:
                        nty = ty / (1 - abs(tx))
                    w = get_triangle_weights([tx, ty, 0], [-1, 0, 0], [0, nty, 0], [1, 0, 0])
                    pc1['w0'] = w[0]
                    pc1['w1'] = w[1]
                    pc1['w2'] = w[2]
                else:
                    mc.pointConstraint(str(j_mid), str(p1), n='_px#')

            # smooth points
            if 0 < i <= nj or (tw in ('up', 'mid') and i == nj + 1):
                p2 = mx.create_node(mx.tTransform, parent=n['rig_smooth'], name='p2_' + name + str(i) + n_end)

                _pc = mx.create_node(mx.tMotionPath)
                n['cv_sm'].shape()['local'] >> _pc['geometryPath']

                axis = self.get_opt('aim_axis')[-1]
                t1 = n['j_2']['t' + axis].read()
                t2 = n['j_3']['t' + axis].read()
                t3 = n['root_e']['t' + axis].read()
                m1 = t1 / (t1 + t2 + t3)
                m2 = t2 / (t1 + t2 + t3)
                m3 = t3 / (t1 + t2 + t3)
                _pc['fractionMode'] = 1
                if tw == 'up':
                    u = i / float(nj + 1) * m1
                elif tw == 'mid':
                    u = i / float(nj + 1) * m2 + m1
                elif tw == 'dn':
                    u = i / float(nj + 1) * m3 + m2 + m1

                if u > 1:
                    u = 1.0
                _pc['u'] = u
                _pc['allCoordinates'] >> p2['t']

                if i <= nj:
                    for _c in range(nc):
                        pc = mc.pointConstraint(str(p1s[i]), str(p2), str(roots[_c][-1]), n='_px#')
                        pc = mx.encode(pc[0])
                        n['sm_off'] >> pc['w0']
                        n['sm_on'] >> pc['w1']

                if i == nj + 1:
                    if tw == 'up':
                        n['p2_pt'] = p2
                    elif tw == 'mid':
                        n['p3_pt'] = p2

            # stretch
            if i > 0:
                for _c in range(nc):
                    db = mx.create_node(mx.tDistanceBetween, name='_len#')
                    roots[_c][i - 1]['t'] >> db['p1']
                    if i <= nj:
                        roots[_c][i]['t'] >> db['p2']
                    else:
                        loc_end['t'] >> db['p2']
                    div = mx.create_node(mx.tMultiplyDivide, name='_div#')
                    div['op'] = 2  # /
                    db['d'] >> div['i1x']
                    div['i2x'] = db['d']

                    div['ox'] >> mxs[_c][i - 1]['in11']

                    sks[_c][i - 1].add_attr(mx.Double('stretch'))
                    div['ox'] >> sks[_c][i - 1]['stretch']

            if i <= nj:
                for _c in range(nc):
                    sks[_c][i].add_attr(mx.Double('squash'))
                    sqx >> sks[_c][i]['squash']

                    sqx >> mxs[_c][i]['in00']
                    sqz >> mxs[_c][i]['in22']
                    connect_matrix(mxs[_c][i]['o'], sks[_c][i])

        # edge constraints
        if tw == 'up':
            pc = mc.pointConstraint(str(j_tip), str(n['p2_pt']), str(loc_end), n='_px#')
            pc = mx.encode(pc[0])
            n['sm_off'] >> pc['w0']
            n['sm_on'] >> pc['w1']
        elif tw == 'mid':
            pc = mc.pointConstraint(str(j_tip), str(n['p3_pt']), str(loc_end), n='_px#')
            pc = mx.encode(pc[0])
            n['sm_off'] >> pc['w0']
            n['sm_on'] >> pc['w1']
        else:
            mc.pointConstraint(str(j_tip), str(loc_end), n='_px#')

        if tw == 'mid':
            for _c in range(nc):
                pc = mc.pointConstraint(str(j_base), str(n['p2_pt']), str(roots[_c][0]), n='_px#')
                pc = mx.encode(pc[0])
                n['sm_off'] >> pc['w0']
                n['sm_on'] >> pc['w1']
        if tw == 'dn':
            for _c in range(nc):
                pc = mc.pointConstraint(str(j_base), str(n['p3_pt']), str(roots[_c][0]), n='_px#')
                pc = mx.encode(pc[0])
                n['sm_off'] >> pc['w0']
                n['sm_on'] >> pc['w1']

        # aims
        for i in range(nj + 1):
            for _c in range(nc):
                aim_axis = self.get_branch_opt('aim_axis')
                aim_axis = axis_to_vector(aim_axis)
                if i < nj:
                    mc.aimConstraint(str(roots[_c][i + 1]), str(roots[_c][i]), aim=aim_axis, wut='none', n='_ax#')
                else:
                    mc.aimConstraint(str(loc_end), str(roots[_c][i]), aim=aim_axis, wut='none', n='_ax#')

        # update shear rig
        if tw == 'up':
            mc.orientConstraint(str(roots[0][0]), str(n['loc_sh_up']))
            mc.parent(str(n['root_sh_m']), str(roots[0][-1]))
        elif tw == 'mid':
            mc.orientConstraint(str(roots[0][0]), str(n['loc_sh_m']))
            mc.parent(str(n['root_sh_q']), str(roots[0][-1]))
        elif tw == 'dn':
            mc.orientConstraint(str(roots[0][0]), str(n['loc_sh_q']))
            mc.orientConstraint(str(roots[0][-1]), str(n['loc_sh_dn']))

        # twists rig
        if tw == 'up':
            j_tw = duplicate_joint(c, p=p1s[min(p1s)], n='j_' + name + '_twist' + n_end)
            n['j_tw_up'] = j_tw
            copy_transform(roots[0][1], j_tw, t=True)
            end_tw = duplicate_joint(c, p=j_tw, n='end_' + name + '_twist' + n_end)
            n['c_sw'].add_attr(mx.Double('twist_up', min=0, max=1, default=1))
            n['tw_up'] = connect_mult(j_tw['ry'], n['c_sw']['twist_up'])
        else:
            j_tw = duplicate_joint(c, p=p1s[max(p1s)], n='j_' + name + '_twist' + n_end)
            n['j_tw_dn'] = j_tw
            end_tw = duplicate_joint(c, p=j_tw, n='end_' + name + '_twist' + n_end)
            copy_transform(roots[0][-1], j_tw, t=True)
            copy_transform(j_tip, end_tw, t=True)
            if tw == 'mid':
                n['c_sw'].add_attr(mx.Double('twist_mid', min=0, max=1, default=1))
                n['tw_mid'] = connect_mult(j_tw['ry'], n['c_sw']['twist_mid'])
            elif tw == 'dn':
                n['c_sw'].add_attr(mx.Double('twist_dn', min=0, max=1, default=1))
                n['tw_dn'] = connect_mult(j_tw['ry'], n['c_sw']['twist_dn'])
        j_tw['ro'] = mx.Euler.YZX

        ik_tw = create_ik_handle(sj=str(j_tw), ee=str(end_tw), sol='ikSCsolver', n='ik_' + name + '_twist' + n_end)
        ik_tw['snapEnable'] = False

        if tw == 'up':
            if not self.get_opt('clavicle'):
                mc.parent(str(ik_tw), str(n['root_1']))
            else:
                mc.parent(str(ik_tw), str(n['j_clav']))
            mc.pointConstraint(str(c), str(ik_tw), n='_px#')
        elif tw == 'mid':
            mc.parent(str(ik_tw), str(n['c_3']))
            copy_transform(n['c_3'], ik_tw, t=True)
        elif tw == 'dn':
            mc.parent(str(ik_tw), str(n['c_e']))
            copy_transform(n['c_e'], ik_tw, t=True)

        # weights rig
        for _c in range(nc):
            _attr = '__{}'.format(name)
            n['sw'][_c].add_attr(mx.Divider(_attr))

            for i in range(nj + 1):
                _attr = 'twist_{}_{}'.format(tw, i)
                n['sw'][_c].add_attr(mx.Double(_attr, min=0, max=1))
                n['sw'][_c][_attr].channel_box = True

            for i in range(nj + 1):
                _attr = 'shear_{}_base_{}'.format(tw, i)
                n['sw'][_c].add_attr(mx.Double(_attr, min=0, max=2, default=0))
                n['sw'][_c][_attr].channel_box = True

            for i in range(nj + 1):
                _attr = 'shear_{}_tip_{}'.format(tw, i)
                n['sw'][_c].add_attr(mx.Double(_attr, min=0, max=2, default=0))
                n['sw'][_c][_attr].channel_box = True

            for i in range(nj + 1):
                _twist = n['sw'][_c]['twist_{}_{}'.format(tw, i)]
                _shear_base = n['sw'][_c]['shear_{}_base_{}'.format(tw, i)]
                _shear_tip = n['sw'][_c]['shear_{}_tip_{}'.format(tw, i)]

                _aim = roots[_c][i]['ry'].input()

                if tw == 'up':
                    _twist.write((nj - i) / (nj + 1.))
                    connect_expr('y = t*tw + (1-t)*t1', y=_aim['offsetY'], t=_twist, tw=n['tw_up'], t1=n['c_sw']['twist_fix1'])

                    connect_mult(_shear_base, n['shz_up'], mxs[_c][i]['in01'])
                    connect_expr('x = b*up + t*-m', x=mxs[_c][i]['in21'], b=_shear_base, t=_shear_tip, up=n['shx_up'], m=n['shx_m'])

                elif tw == 'mid':
                    _twist.write(float(i) / nj)
                    connect_expr('y = t*tw + (1-t)*t1 + t*t2', y=_aim['offsetY'], t=_twist, tw=n['tw_mid'], t1=n['c_sw']['twist_fix1'], t2=n['c_sw']['twist_fix2'])

                    connect_expr('x = b*m + t*-q', x=mxs[_c][i]['in21'], b=_shear_base, t=_shear_tip, m=n['shx_m'], q=n['shx_q'])

                else:  # dn
                    _twist.write(float(i) / nj)
                    connect_expr('y = t*tw + (1-t)*t2', y=_aim['offsetY'], t=_twist, tw=n['tw_dn'], t2=n['c_sw']['twist_fix2'])

                    connect_mult(_shear_tip, n['shz_dn'], mxs[_c][i]['in01'])
                    connect_expr('x = b*q + t*dn', x=mxs[_c][i]['in21'], b=_shear_base, t=_shear_tip, q=n['shx_q'], dn=n['shx_dn'])

        return sks

    def build_rotate_order(self):
        self.n['c_1']['ro'] = mx.Euler.YXZ
        self.n['c_2']['ro'] = mx.Euler.YXZ
        self.n['c_3']['ro'] = mx.Euler.YXZ
        self.n['c_e']['ro'] = mx.Euler.XZY
        self.n['c_dg']['ro'] = mx.Euler.YXZ
        self.n['c_eIK']['ro'] = mx.Euler.XZY
        self.n['c_eIK_offset']['ro'] = mx.Euler.XZY
