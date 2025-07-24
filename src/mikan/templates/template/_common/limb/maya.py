# coding: utf-8

import math
from six.moves import range
from six import string_types

from mikan.maya import cmds as mc
import mikan.maya.cmdx as mx

import mikan.maya.core as mk
from mikan.core.prefs import Prefs
from mikan.maya.lib.rig import (
    copy_transform, orient_joint, duplicate_joint, stretch_ik, axis_to_vector,
    create_blend_joint, fix_inverse_scale, create_ik_handle
)
from mikan.maya.lib.connect import *
from mikan.maya.lib.nurbs import create_path, get_closest_point_on_curve


class Template(mk.Template):

    def rename_template(self):

        for s in ('clavicle', 'limb2', 'limb3', 'digits', 'tip', 'heel', 'bank_int', 'bank_ext'):
            j = self.get_structure(s)
            if not j or j[0].is_referenced():
                continue

            sfx = s
            if s == 'clavicle':
                sfx = 'clav'
            j[0].rename('tpl_{}_{}'.format(self.name, sfx))

    def build_rig(self):
        # get structures
        hook = self.hook
        rig_hook = mk.Nodes.get_id('::rig')
        if not rig_hook:
            rig_hook = self.get_first_hook()
        default_hook = mk.Nodes.get_id('::hook')
        if not default_hook:
            default_hook = self.get_first_hook()

        tpl_limb1 = self.get_structure('limb1')[0]
        tpl_limb2 = self.get_structure('limb2')[0]
        tpl_limb3 = self.get_structure('limb3')[0]
        tpl_digits = self.get_structure('digits')[0]
        tpl_tip = self.get_structure('tip')[0]

        # naming
        n_end = self.get_branch_suffix()
        n_limb = self.name
        n_limb1 = self.get_name('limb1')
        n_limb2 = self.get_name('limb2')
        n_eff = self.get_name('effector')
        n_digits = self.get_name('digits')

        deform_chains = self.get_chains()
        n_chain = ['_' + str(x) if x else x for x in deform_chains]
        id_chain = ['.' + str(x) if x else x for x in deform_chains]

        # opts
        self.do_clavicle = self.get_opt('clavicle')
        self.do_clavicle_auto = self.get_opt('clavicle_auto')
        aim_axis = self.get_branch_opt('aim_axis')
        up_axis = self.get_opt('up_axis')
        up_axis2 = self.get_branch_opt('up_axis2')

        # vars
        n = {}
        self.n = n

        # build skeleton
        n['c_1'] = mx.create_node(mx.tJoint, name='c_' + n_limb1 + n_end)
        n['c_2'] = mx.create_node(mx.tJoint, parent=n['c_1'], name='c_' + n_limb2 + n_end)
        n['c_e'] = mx.create_node(mx.tJoint, parent=n['c_2'], name='c_' + n_eff + n_end)
        n['c_dg'] = mx.create_node(mx.tJoint, parent=n['c_e'], name='c_' + n_digits + n_end)
        n['end_dg'] = mx.create_node(mx.tJoint, parent=n['c_dg'], name='end_' + n_digits + n_end)

        copy_transform(tpl_limb1, n['c_1'], t=True)
        copy_transform(tpl_limb2, n['c_2'], t=True)
        copy_transform(tpl_limb3, n['c_e'], t=True)
        copy_transform(tpl_digits, n['c_dg'], t=True)
        copy_transform(tpl_tip, n['end_dg'], t=True)

        # orient skeleton
        orient_joint((n['c_1'], n['c_2'], n['c_e']), aim=aim_axis, up=up_axis, up_auto=1)
        plane = self.get_opt('effector_plane')

        if self.get_opt('reverse_lock') and plane == 'ground':
            # orient from ground (foot)
            vp = tpl_tip.translation(mx.sWorld) - tpl_limb3.translation(mx.sWorld)
            vp = vp ^ mx.Vector(0, 1, 0)  # cross

            vd = tpl_tip.translation(mx.sWorld) - n['c_e'].translation(mx.sWorld)
            vd[1] = 0

            orient_joint(n['c_e'], aim=up_axis2, aim_dir=vd, up=up_axis, up_dir=vp)
            orient_joint((n['c_dg'], n['end_dg']), aim=up_axis2, up=up_axis, up_dir=vp)

            # conform limb
            up0 = axis_to_vector(up_axis) * n['c_1'].transform(mx.sWorld).as_matrix()
            if up0 * vp < 0:  # dot
                for j in (n['c_1'], n['c_2']):
                    _children = list(j.children())
                    for _c in _children:
                        mc.parent(str(_c), w=1)
                    j['r' + aim_axis[-1]] = mx.Degrees(180)
                    mc.makeIdentity(str(j), a=1)
                    for _c in _children:
                        mc.parent(str(_c), str(j))

        else:
            # free orient (hand)
            up_dir = (0, 0, 1)
            up_auto = None
            _up = up_axis2
            if plane == 'x':
                up_dir = (1, 0, 0)
            elif plane == 'y':
                up_dir = (0, 1, 0)

            if plane == 'auto':
                up_auto = 1
                p1 = tpl_limb1.translation(mx.sWorld)
                p2 = tpl_limb2.translation(mx.sWorld)
                p3 = tpl_limb3.translation(mx.sWorld)
                pe = tpl_digits.translation(mx.sWorld)
                pt = tpl_tip.translation(mx.sWorld)
                v1 = ((p2 - p1) ^ (p3 - p2)).normal()
                v2 = ((pe - p3) ^ (pt - pe)).normal()
                p = v1 * v2
                if p > 0.707:
                    _up = up_axis
                elif p < -0.707:
                    _up = up_axis
                    if not _up.startswith('-'):
                        _up = '-' + _up
                    else:
                        _up = _up.replace('-', '')

            orient_joint((n['c_e'], n['c_dg'], n['end_dg']), aim=aim_axis, up=_up, up_dir=up_dir, up_auto=up_auto)

        # rig skeleton
        n['root_1'] = duplicate_joint(n['c_1'], p=hook, n='root_' + n_limb1 + n_end)
        orient_joint(n['root_1'], aim_dir=[0, 1, 0], up_dir=[0, 0, 1])
        mc.parent(str(n['c_1']), str(n['root_1']))

        n['root_e'] = duplicate_joint(n['c_e'], p=n['c_2'], n='root_' + n_eff + n_end)
        mc.parent(str(n['c_e']), str(n['root_e']))

        n['root_dg'] = duplicate_joint(n['c_dg'], p=n['c_e'], name='root_' + n_digits + n_end)
        mc.parent(str(n['c_dg']), str(n['root_dg']))

        # deform skeleton
        n['j_1'] = duplicate_joint(n['c_1'], p=n['root_1'], n='j_' + n_limb1 + n_end)
        n['j_2'] = duplicate_joint(n['c_2'], p=n['j_1'], n='j_' + n_limb2 + n_end)
        n['j_e'] = duplicate_joint(n['c_e'], p=n['j_2'], n='j_' + n_eff + n_end)
        n['j_dg'] = duplicate_joint(n['c_dg'], p=n['j_e'], n='j_' + n_digits + n_end)
        self.set_id(n['j_1'], 'j.limb1')
        self.set_id(n['j_2'], 'j.limb2')
        self.set_id(n['j_e'], 'j.limb3')
        self.set_id(n['j_dg'], 'j.digits')

        connect_matrix(n['c_1']['m'], n['j_1'], xyz=True)
        n['j_1']['jo'] = (0, 0, 0)

        for attr in ('t', 'rx', 'ry', 'rz', 'sx', 'sy', 'sz', 'ro'):
            n['c_2'][attr] >> n['j_2'][attr]
        mc.reorder(str(n['c_2']), front=1)

        _mmx = mx.create_node(mx.tMultMatrix, name='_mmx#')
        n['c_e']['wm'][0] >> _mmx['i'][0]
        n['root_e']['wim'][0] >> _mmx['i'][1]

        _jo = n['j_e']['jo'].read()
        connect_matrix(_mmx['o'], n['j_e'], t=0, xyz=True)
        n['root_e']['t'] >> n['j_e']['t']
        n['j_e']['jo'] = _jo

        connect_matrix(n['c_dg']['m'], n['j_dg'], t=0, xyz=True)
        n['root_dg']['t'] >> n['j_dg']['t']

        n['c_dg'].add_attr(mx.Boolean('parent_scale', keyable=False, default=True))
        _r = connect_reverse(n['c_dg']['parent_scale'], n['j_dg']['ssc'])
        _r >> n['root_dg']['ssc']

        # auto orient clavicle rig
        targets = []
        if self.do_clavicle:
            self.build_clav_auto()
            targets.append('{}{}::j.clavicle'.format(self.name, self.get_branch_id()))

        if hook != default_hook:
            targets.append('::hook')
        if len(targets) > 0:
            mk.Mod.add(n['c_1'], 'space', {'targets': targets, 'orient': True})

        # IK stretch
        n['root_eIK'] = mx.create_node(mx.tTransform, parent=default_hook, name='root_' + n_eff + '_IK' + n_end)
        copy_transform(n['c_e'], n['root_eIK'], t=True)
        n['c_eIK'] = duplicate_joint(n['c_e'], p=n['root_eIK'], n='c_' + n_eff + '_IK' + n_end)

        n['root_eIK_offset'] = mx.create_node(mx.tJoint, parent=default_hook, name='root_' + n_eff + '_IK_offset' + n_end)
        copy_transform(n['c_e'], n['root_eIK_offset'], t=True)
        n['c_eIK_offset'] = duplicate_joint(n['c_e'], p=n['root_eIK_offset'], n='c_' + n_eff + '_IK_offset' + n_end)

        mc.parent(str(n['root_eIK_offset']), str(n['c_eIK']))

        n['ik'], n['eff_root'], n['eff_ik'] = stretch_ik((n['c_1'], n['c_2'], n['root_e']), n['c_eIK'])
        n['ik'].rename('ik_' + n_limb + n_end)
        n['eff_root'].rename('eff_' + n_limb + '_base' + n_end)
        n['eff_ik'].rename('eff_' + n_limb + n_end)

        if self.get_opt('default_stretch'):
            n['c_eIK']['stretch'] = 1

        n['j_1'].add_attr(mx.Double('squash', keyable=True))
        n['j_2'].add_attr(mx.Double('squash', keyable=True))
        n['c_1']['squash'] >> n['j_1']['squash']
        n['c_2']['squash'] >> n['j_2']['squash']

        if self.do_clavicle and self.do_clavicle_auto:
            mc.parent(str(n['ik_ao']), str(n['c_eIK_offset']))
            n['ik']['twist'].input(plug=True) >> n['ik_ao']['twist']

        # switch controller
        n['root_sw'] = mx.create_node(mx.tTransform, parent=rig_hook, name='root_' + n_limb + '_switch' + n_end)
        mc.reorder(str(n['root_sw']), front=1)

        n['root_sw']['v'] = False
        for attr in ['t', 'r', 's', 'v']:
            n['root_sw'][attr].lock()

        n['c_sw'] = mk.Control.create_control_shape(n['root_sw'], n='c_' + n_limb + '_switch' + n_end)

        # deform switch control
        n['sw'] = {}

        for i, chain in enumerate(deform_chains):
            n['sw'][i] = mk.Control.create_control_shape(n['root_sw'], n='sw_' + n_limb + '_weights' + n_chain[i] + n_end)
            self.set_id(n['sw'][i], 'weights.{}'.format(i))
            if i > 0:
                self.set_id(n['sw'][i], 'weights.{}'.format(chain))
            mc.reorder(str(n['sw'][i]), front=1)

        # reverse IK rig
        self.build_reverse_lock()

        # change stretch IK pointConstraint
        mx.delete(mc.ls(mc.listConnections(str(n['eff_ik']), s=1, d=0), type='constraint'))
        mc.pointConstraint(str(n['end_emIK']), str(n['eff_ik']), n='_px#')

        # reverse lock IK poses
        if self.get_opt('reverse_lock'):
            self.build_reverse_lock_poses()

        # pole vector
        self.build_pole_vector_auto()
        self.build_pole_vector_follow()
        # return
        p1 = n['c_1'].translation(mx.sWorld)
        p2 = n['c_2'].translation(mx.sWorld)
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

        mc.poleVectorConstraint(str(n['c_pv']), str(n['ik']), n='_pvx#')

        if self.do_clavicle:
            if self.do_clavicle_auto:
                mc.poleVectorConstraint(str(n['c_pv']), str(n['ik_ao']), n='_pvx#')
        else:
            db = n['eff_root']['t'].output(type=mx.tDistanceBetween)
            dist = db['d'].read()
            connect_driven_curve(db['d'], n['ao_pv']['sy'], {0: 0, dist: 1, (dist * 2): 2}, post='linear', key_style='linear')
            n['ao_pv']['sy'].input(plug=True) >> n['ao_pvf']['sy']

        # IK switch
        n['c_sw'].add_attr(mx.Double('ik_blend', keyable=True, min=0, max=1, default=1))
        n['c_sw']['ik_blend'] >> n['ik']['ikBlend']
        n['c_sw']['ik_blend'] >> n['ik_em']['ikBlend']

        lock_attr = n_digits + '_lock'
        n['c_eIK'].add_attr(mx.Boolean(lock_attr, default=self.get_opt('reverse_lock')))

        connect_mult(n['c_eIK'][lock_attr], n['c_sw']['ik_blend'], n['ik_dg']['ikBlend'])

        # deform rig
        n['root_2pt'] = duplicate_joint(n['c_2'], p=n['j_1'], n='root_' + n_limb2 + '_tweak' + n_end)
        n['c_2pt'] = mx.create_node(mx.tTransform, parent=n['root_2pt'], name='c_' + n_limb2 + '_tweak' + n_end)

        if self.do_flip():
            n['root_2pt']['s'] = (-1, -1, -1)

        mc.pointConstraint(str(n['j_2']), str(n['root_2pt']), n='_px#')
        _ox = mc.orientConstraint(str(n['j_1']), str(n['j_2']), str(n['root_2pt']), n='_ox#')
        _ox = mx.encode(_ox[0])
        _ox['interpType'] = 2

        mk.Mod.add(n['c_2pt'], 'space', {'targets': ['::hook']})

        # auto unroll
        n['loc_2'] = mx.create_node(mx.tTransform, parent=n['root_1'], name='loc_' + n_limb2 + n_end)
        n['loc_1'] = mx.create_node(mx.tTransform, parent=n['loc_2'], name='loc_' + n_limb1 + n_end)
        n['loc_e'] = mx.create_node(mx.tTransform, parent=n['loc_2'], name='loc_' + n_eff + n_end)
        n['vp_1'] = mx.create_node(mx.tTransform, parent=n['loc_1'], name='vp_' + n_limb1 + n_end)
        n['vp_2'] = mx.create_node(mx.tTransform, parent=n['loc_2'], name='vp_' + n_limb2 + n_end)

        mc.pointConstraint(str(n['c_2pt']), str(n['loc_2']), n='_px#')
        mc.pointConstraint(str(n['j_1']), str(n['loc_1']), n='_px#')
        mc.pointConstraint(str(n['j_e']), str(n['loc_e']), n='_px#')

        _vp = mx.create_node(mx.tVectorProduct, name='_cross#')
        n['loc_1']['t'] >> _vp['input1']
        n['loc_e']['t'] >> _vp['input2']
        _vp['operation'] = 2  # cross

        _db = mx.create_node(mx.tDistanceBetween, name='_len#')
        _vp['output'] >> _db['point1']

        _if = mx.create_node('condition', name='_if#')
        _db['d'] >> _if['ft']
        _if['op'] = 4  # lesser than
        _if['st'] = 0.001
        _vp['output'] >> _if['cf']
        _if['ct'] = _vp['output']

        _if['oc'] >> n['vp_1']['t']
        _if['oc'] >> n['vp_2']['t']

        n['aim_1'] = duplicate_joint(n['c_1'], p=n['j_1'], n='j_' + n_limb1 + '_aim' + n_end)
        n['aim_2'] = duplicate_joint(n['c_2'], p=n['j_2'], n='j_' + n_limb2 + '_aim' + n_end)
        n['sub_1'] = duplicate_joint(n['aim_1'], p=n['j_1'], n='j_' + n_limb1 + '_deform' + n_end)
        n['sub_2'] = duplicate_joint(n['aim_2'], p=n['j_2'], n='j_' + n_limb2 + '_deform' + n_end)
        mc.reorder(str(n['sub_1']), front=1)
        mc.reorder(str(n['sub_2']), front=1)

        ac1 = mc.aimConstraint(str(n['c_2pt']), str(n['aim_1']), aim=[0, (-1, 1)[not aim_axis.startswith('-')], 0], wut='none', n='_ax#')
        ac2 = mc.aimConstraint(str(n['j_e']), str(n['aim_2']), aim=[0, (-1, 1)[not aim_axis.startswith('-')], 0], wut='none', n='_ax#')
        ac1 = mx.encode(ac1[0])
        ac2 = mx.encode(ac2[0])

        n['up_1'] = duplicate_joint(n['c_1'], p=n['aim_1'], n='loc_' + n_limb1 + '_up' + n_end)
        n['up_2'] = duplicate_joint(n['c_2'], p=n['aim_2'], n='loc_' + n_limb2 + '_up' + n_end)
        n['up_1']['ro'] = mx.Euler.YZX
        n['up_2']['ro'] = mx.Euler.YZX
        n['up_1']['v'] = False
        n['up_2']['v'] = False

        n['upt_1'] = duplicate_joint(n['c_1'], p=n['up_1'], n='loc_' + n_limb1 + '_up_vector' + n_end)
        n['upt_2'] = duplicate_joint(n['c_2'], p=n['up_2'], n='loc_' + n_limb2 + '_up_vector' + n_end)
        copy_transform(n['vp_1'], n['upt_1'], t=True)
        copy_transform(n['vp_2'], n['upt_2'], t=True)

        _unroll1 = create_ik_handle(sj=n['up_1'], ee=n['upt_1'], sol='ikSCsolver', n='ik_' + n_limb1 + '_unroll' + n_end)
        _unroll2 = create_ik_handle(sj=n['up_2'], ee=n['upt_2'], sol='ikSCsolver', n='ik_' + n_limb2 + '_unroll' + n_end)
        _unroll1['snapEnable'] = False
        _unroll2['snapEnable'] = False
        mc.parent(str(_unroll1), str(n['aim_1']))
        mc.parent(str(_unroll2), str(n['aim_2']))
        _unroll1['v'] = False
        _unroll2['v'] = False

        mc.pointConstraint(str(n['vp_1']), str(_unroll1), n='_px#')
        mc.pointConstraint(str(n['vp_2']), str(_unroll2), n='_px#')

        mc.pointConstraint(str(n['c_2pt']), str(n['aim_2']), n='_px#')
        mc.pointConstraint(str(n['c_2pt']), str(n['sub_2']), n='_px#')

        # twist fix
        n['c_sw'].add_attr(mx.Double('twist_unroll', keyable=True, min=0, max=1))
        n['c_sw'].add_attr(mx.Double('twist_fix', keyable=True))
        if self.get_opt('advanced_twist', False):
            n['c_sw'].add_attr(mx.Double('twist_fix_up', keyable=True))
            n['c_sw'].add_attr(mx.Double('twist_fix_dn', keyable=True))

        n['aim_1']['r'] >> n['sub_1']['jo']
        n['aim_2']['r'] >> n['sub_2']['jo']

        _pb1 = mx.create_node(mx.tPairBlend, name='_pb#')
        _pb2 = mx.create_node(mx.tPairBlend, name='_pb#')

        n['up_1']['rx'] >> _pb1['irx2']
        n['up_1']['rz'] >> _pb1['irz2']
        n['up_2']['rx'] >> _pb2['irx2']
        n['up_2']['rz'] >> _pb2['irz2']

        if self.get_opt('advanced_twist'):
            connect_expr('ry = r+fix1+fix2', ry=_pb1['iry2'], r=n['up_1']['ry'], fix1=n['c_sw']['twist_fix'], fix2=n['c_sw']['twist_fix_up'])
            connect_expr('ry = r+fix1+fix2', ry=_pb2['iry2'], r=n['up_2']['ry'], fix1=n['c_sw']['twist_fix'], fix2=n['c_sw']['twist_fix_dn'])
            connect_add(n['c_sw']['twist_fix'], n['c_sw']['twist_fix_up'], _pb1['iry1'])
            connect_add(n['c_sw']['twist_fix'], n['c_sw']['twist_fix_dn'], _pb2['iry1'])
        else:
            connect_add(n['up_1']['ry'], n['c_sw']['twist_fix'], _pb1['iry2'])
            connect_add(n['up_2']['ry'], n['c_sw']['twist_fix'], _pb2['iry2'])
            n['c_sw']['twist_fix'] >> _pb1['iry1']
            n['c_sw']['twist_fix'] >> _pb2['iry1']

        n['c_sw']['twist_unroll'] >> _pb1['w']
        n['c_sw']['twist_unroll'] >> _pb2['w']

        _pb1['outRotate'] >> n['sub_1']['r']
        _pb2['outRotate'] >> n['sub_2']['r']

        # flex rig
        sw = n['sw'][0]
        sw.add_attr(mx.Divider('flex'))

        n['loc_2pt_up'] = mx.create_node(mx.tTransform, parent=n['c_2pt'], name='loc_' + n_limb2 + '_tweak_up' + n_end)
        n['loc_2pt_dn'] = mx.create_node(mx.tTransform, parent=n['c_2pt'], name='loc_' + n_limb2 + '_tweak_dn' + n_end)

        xfo1 = n['c_1']
        xfo2 = n['c_2pt']
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
        sw.add_attr(mx.Double('flex_offset_start', keyable=True, min=0, max=1, default=0.5))
        angle_weight = connect_expr('max(0, 1-(a/(a0*max(1-w, 0.001))))', a=angle['angle'], a0=angle0, w=sw['flex_offset_start'])

        sw.add_attr(mx.Double('flex_offset_upX', keyable=True))
        sw.add_attr(mx.Double('flex_offset_upY', keyable=True))
        sw.add_attr(mx.Double('flex_offset_upZ', keyable=True))
        sw.add_attr(mx.Double('flex_offset_dnX', keyable=True))
        sw.add_attr(mx.Double('flex_offset_dnY', keyable=True))
        sw.add_attr(mx.Double('flex_offset_dnZ', keyable=True))

        for side in ('up', 'dn'):
            for dim in 'XYZ':
                connect_mult(sw['flex_offset_' + side + dim], angle_weight, n['loc_2pt_' + side]['translate' + dim])

        # bend rig
        n['root_1bd'] = mx.create_node(mx.tTransform, parent=n['sub_1'], name='root_' + n_limb1 + '_bend' + n_end)
        n['c_1bd'] = mx.create_node(mx.tTransform, parent=n['root_1bd'], name='c_' + n_limb1 + '_bend' + n_end)
        n['c_1bd']['displayHandle'] = True
        _px1 = mc.pointConstraint(str(n['j_1']), str(n['loc_2pt_up']), str(n['root_1bd']), n='_px#')

        n['root_2bd'] = mx.create_node(mx.tTransform, parent=n['sub_2'], name='root_' + n_limb2 + '_bend' + n_end)
        n['c_2bd'] = mx.create_node(mx.tTransform, parent=n['root_2bd'], name='c_' + n_limb2 + '_bend' + n_end)
        n['c_2bd']['displayHandle'] = True
        _px2 = mc.pointConstraint(str(n['loc_2pt_dn']), str(n['j_e']), str(n['root_2bd']), n='_px#')

        if self.do_flip():
            n['root_1bd']['s'] = (-1, -1, -1)
            n['root_2bd']['s'] = (-1, -1, -1)

        # skin rig: effector
        n['sub_e'] = duplicate_joint(n['j_e'], p=n['j_e'], n='j_' + n_eff + '_deform' + n_end)

        n['sk_e'] = duplicate_joint(n['c_e'], p=n['j_e'], n='sk_' + n_eff + n_end)
        n['end_e'] = duplicate_joint(n['c_dg'], p=n['sk_e'], n='end_' + n_eff + n_end)
        mc.reorder(str(n['sk_e']), front=1)

        n['sk_dg'] = duplicate_joint(n['c_dg'], p=n['j_dg'], n='sk_' + n_digits + n_end)
        n['end_limb'] = duplicate_joint(n['end_dg'], p=n['sk_dg'], n='end_' + n_limb + n_end)
        mc.reorder(str(n['sk_dg']), front=1)

        n['sk_e']['ssc'] = False
        n['sk_dg']['ssc'] = False

        mc.reorder(str(n['sub_e']), front=1)

        # skin rig: splits
        n['rig_smooth'] = mx.create_node(mx.tTransform, parent=n['root_1'], name='rig_' + n_limb + '_spline' + n_end)
        n['rig_smooth']['v'] = False

        n['cv_sm'] = create_path(n['j_1'], n['c_1bd'], n['c_2pt'], n['c_2bd'], n['j_e'], d=3)
        mc.parent(str(n['cv_sm']), str(n['rig_smooth']), r=1)
        n['cv_sm'].rename('cv_' + n_limb + n_end)

        # smooth outputs
        n['c_sw'].add_attr(mx.Double('smooth', keyable=True, min=0, max=1))
        n['sm_on'] = n['c_sw']['smooth']
        n['sm_off'] = connect_reverse(n['sm_on'])

        # arc dirty hack :)
        n['c_sw'].addAttr(mx.Double('arc', keyable=True, min=0, max=1))

        arcmax = 180 - mx.Radians(n['c_2']['jox'].read()).asDegrees()
        arcd = abs(n['c_2']['ty'].read()) / 2
        n['j_2'].add_attr(mx.Double('arc'))
        arceff = connect_driven_curve(n['j_2']['rx'], n['j_2']['arc'], {0: 0, arcmax: arcd})

        arc_value = arceff['o']
        if self.do_flip():
            arc_value = connect_mult(arc_value, -1)

        arct = connect_mult(arc_value, n['c_sw']['arc'])
        arct >> mx.encode(_px1[0])['offsetZ']
        arct >> mx.encode(_px2[0])['offsetZ']

        connect_mult(ac1['offsetY'], -1, n['root_1bd']['ry'])
        connect_mult(ac2['offsetY'], -1, n['root_2bd']['ry'])

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

        # shear dn
        root_sh_dn = duplicate_joint(n['sub_2'], p=n['sub_e'], n='root_shear_dn')
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
        splits_up = self.build_twist_joints(
            nj=self.get_opt('twist_joints_up'),
            tw='up', name=n_limb1,
            c=n['j_1'], sk=n['sub_1'],
            j_base=n['j_1'], j_mid=n['c_1bd'], j_tip=n['loc_2pt_up'])

        splits_dn = self.build_twist_joints(
            nj=self.get_opt('twist_joints_dn'),
            tw='dn', name=n_limb2,
            c=n['j_2'], sk=n['sub_2'],
            j_base=n['loc_2pt_dn'], j_mid=n['c_2bd'], j_tip=n['j_e'])

        def do_limb_twist_end(jdup, jpos):
            jend = duplicate_joint(jdup, p=jdup, n=jdup.name(namespace=False).replace('sk_', 'end_'))
            copy_transform(jpos, jend, t=True)

        for i, sk in enumerate(splits_up[0][:-1]):
            do_limb_twist_end(splits_up[0][i], splits_up[0][i + 1])
        for i, sk in enumerate(splits_dn[0][:-1]):
            do_limb_twist_end(splits_dn[0][i], splits_dn[0][i + 1])
        do_limb_twist_end(splits_up[0][-1], splits_dn[0][0])
        do_limb_twist_end(splits_dn[0][-1], n['c_e'])

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
            n['rb1'] = create_blend_joint(splits_up[0][0].parent(), rb_limb1, n='sk_' + n_limb1 + '_blend' + n_end)
            rb2 = create_blend_joint(splits_dn[0][0].parent(), splits_up[0][-1].parent(), n='root_' + n_limb2 + '_blend' + n_end)
            n['rbe'] = create_blend_joint(n['sk_e'], splits_dn[0][-1].parent(), n='sk_' + n_eff + '_blend' + n_end)

            mc.parent(str(n['rb1']), str(n['sub_1']))
            mc.pointConstraint(str(rb_limb1), str(n['sub_1']), str(n['rb1']))
            mc.reorder(str(n['rb1']), f=1)

            mc.parent(str(rb2), str(n['sub_2']))
            mc.reorder(str(rb2), f=1)
            n['rb2'] = duplicate_joint(n['sub_2'], p=n['sub_2'], n='sk_' + n_limb2 + '_blend' + n_end)
            mc.parent(str(n['rb2']), str(rb2))

            connect_expr('s = (s1 + s2) * 0.5', s=n['rb2']['s'], s1=n['c_1']['s'], s2=n['c_2']['s'])

            pc = mc.pointConstraint(str(n['loc_2pt_up']), str(n['loc_2pt_dn']), str(n['p2_pt']), str(rb2), n='_px#')
            pc = mx.encode(pc[0])
            n['sm_off'] >> pc['w0']
            n['sm_off'] >> pc['w1']
            connect_mult(n['sm_on'], 2, pc['w2'])

            mc.parent(str(n['rbe']), str(n['j_e']))
            mc.reorder(str(n['rbe']), f=1)

        # fix inverse scale hierarchy
        fix_inverse_scale(list(n['root_eIK'].descendents()))
        fix_inverse_scale(list(n['root_1'].descendents()))
        if self.do_clavicle:
            fix_inverse_scale(n['root_clav'], list(n['root_clav'].descendents()))

        # channels
        for c in (n['c_2'], n['c_e'], n['c_dg']):
            for dim in 'xyz':
                c['t' + dim].keyable = False
                c['t' + dim].lock()

        for c in (n['c_2pt'], n['c_1bd'], n['c_2bd']):
            for attr in 'sr':
                for dim in 'xyz':
                    c[attr + dim].keyable = False
                    c[attr + dim].lock()

        n['c_1'].set_limit(mx.kScaleMinY, 0.01)
        n['c_2'].set_limit(mx.kScaleMinY, 0.01)

        n['c_e'].set_limit(mx.kScaleMinX, 0.01)
        n['c_e'].set_limit(mx.kScaleMinY, 0.01)
        n['c_e'].set_limit(mx.kScaleMinZ, 0.01)

        # rotate orders
        self.build_rotate_order()

        # space switch
        if self.get_opt('space_switch'):
            self.build_space_mods()

        # common switch shape
        for c in ('c_clav', 'c_1', 'c_2', 'c_e', 'c_eIK', 'c_dg', 'c_1bd', 'c_2bd', 'c_2pt'):
            if c in n:
                for _c in range(len(deform_chains)):
                    mc.parent(str(n['sw'][_c]), str(n[c]), r=1, s=1, add=1)
                mk.Control.set_control_shape(n['c_sw'], n[c])

        for _c in range(len(deform_chains)):
            n['sw'][_c]['ihi'] = True

        # skin gizmo
        for i, sk in enumerate(splits_up[0]):
            sk['radius'] = 0.5
        for i, sk in enumerate(splits_dn[0]):
            sk['radius'] = 0.5

        n['rb1']['radius'] = 1.5
        n['rb2']['radius'] = 1.5
        n['rbe']['radius'] = 1.5

        n['sk_dg']['drawStyle'] = 2

        # ui functions
        n['c_eIK'].add_attr(mx.Message('menu_offset_pivot'))

        # ui ik/fk match
        ui_ikfk = mx.create_node(mx.tNetwork, name='ui_match_IKFK' + n_limb + n_end)
        for c in (n['c_eIK'], n['c_1'], n['c_2'], n['c_e']):
            c.add_attr(mx.Message('menu_match_ikfk'))
            ui_ikfk['msg'] >> c['menu_match_ikfk']

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
        n['c_e']['msg'] >> ui_ikfk['fk'][2]

        # vis group
        grp = mk.Group.create('{} shape{}'.format(self.name, self.get_branch_suffix(' ')))
        for c in ('c_1bd', 'c_2bd', 'c_2pt'):
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
        self.set_hook(tpl_limb3, n['sk_e'], 'hooks.effector')
        self.set_hook(tpl_digits, n['sk_dg'], 'hooks.digits')
        if self.do_clavicle:
            self.set_hook(self.get_structure('clavicle')[0], n['sk_clav'], 'hooks.clavicle')

        # tag nodes
        self.set_id(n['c_1'], 'ctrls.limb1')
        self.set_id(n['c_2'], 'ctrls.limb2')
        self.set_id(n['c_e'], 'ctrls.limb3')
        self.set_id(n['c_eIK'], 'ctrls.ik')
        self.set_id(n['c_eIK_offset'], 'ctrls.ik_offset')
        self.set_id(n['c_dg'], 'ctrls.digits')
        self.set_id(n['c_1bd'], 'ctrls.bend1')
        self.set_id(n['c_2bd'], 'ctrls.bend2')
        self.set_id(n['c_2pt'], 'ctrls.tweak')
        self.set_id(n['c_sw'], 'ctrls.switch')
        if self.do_clavicle:
            self.set_id(n['c_clav'], 'ctrls.clavicle')

        for s, splits in enumerate(splits_up):
            for i, j in enumerate(splits):
                self.set_id(j, 'skin.up{}.{}'.format(id_chain[s], i))
                self.set_id(j.parent(), 'roots.up{}.{}'.format(id_chain[s], i))
            self.set_id(splits[-1], 'skin.last{}.up'.format(id_chain[s]))
        for s, splits in enumerate(splits_dn):
            for i, j in enumerate(splits):
                self.set_id(j, 'skin.dn{}.{}'.format(id_chain[s], i))
                self.set_id(j.parent(), 'roots.dn{}.{}'.format(id_chain[s], i))
            self.set_id(splits[-1], 'skin.last{}.dn'.format(id_chain[s]))
        if self.do_clavicle:
            self.set_id(n['sk_clav'], 'skin.clavicle')
        if self.get_opt('blend_joints'):
            self.set_id(n['rb1'], 'skin.bj1')
            self.set_id(n['rb2'], 'skin.bj2')
            self.set_id(n['rbe'], 'skin.bje')
        self.set_id(n['sk_e'], 'skin.limb3')
        self.set_id(n['sk_dg'], 'skin.digits')

        self.set_id(n['root_1'], 'roots.1')
        self.set_id(n['root_e'], 'roots.e')
        self.set_id(n['root_dg'], 'roots.dg')
        self.set_id(n['root_pv'], 'roots.pv')
        self.set_id(n['root_sw'], 'roots.switch')
        self.set_id(n['root_eIK'], 'roots.effector')
        self.set_id(n['root_eIK_offset'], 'roots.effector_offset')

        self.set_id(n['end_dg'], 'tip')

    def build_clav_auto(self):
        n = self.n
        hook = self.get_hook()

        n_limb = self.name
        n_clav = self.get_name('clavicle')
        n_limb1 = self.get_name('limb1')
        n_limb2 = self.get_name('limb2')
        n_eff = self.get_name('effector')
        n_end = self.get_branch_suffix()

        tpl_clav = self.get_structure('clavicle')[0]

        n['root_clav'] = mx.create_node(mx.tJoint, parent=hook, name='root_' + n_clav + n_end)
        copy_transform(tpl_clav, n['root_clav'], t=True)
        self.set_id(n['root_clav'], 'roots.clavicle')

        n['c_clav'] = mx.create_node(mx.tJoint, parent=n['root_clav'], name='c_' + n_clav + n_end)
        n['tip_clav'] = mx.create_node(mx.tJoint, parent=n['c_clav'], name='j_' + n_clav + '_tip' + n_end)
        copy_transform(n['c_1'], n['tip_clav'], t=True)

        aim_axis = self.get_branch_opt('aim_axis')
        up_axis = self.get_branch_opt('up_axis')
        orient_joint((n['c_clav'], n['tip_clav']), aim=aim_axis, up=up_axis, up_dir=[0, -1, 0])

        # conform orient?
        up_axis_vector = axis_to_vector(up_axis)
        a0 = up_axis_vector * n['c_1'].transform(space=mx.sWorld).as_matrix()
        a1 = up_axis_vector * n['c_clav'].transform(space=mx.sWorld).as_matrix()
        d = a0 * a1
        if d < 0:
            orient_joint((n['c_clav'], n['tip_clav']), aim=aim_axis, up=up_axis, up_dir=[0, 0, 1])

        # rig clav
        mc.reorder(str(n['root_clav']), r=-1)
        n['root_clav']['ssc'] = False

        n['j_clav'] = n['c_clav']
        if self.do_clavicle_auto:
            n['j_clav'].rename('j_' + n_clav + n_end)
            n['c_clav'] = duplicate_joint(n['j_clav'], n='c_' + n_clav + n_end)

            n['srt_clav'] = duplicate_joint(n['j_clav'], n='srt_' + n_clav + n_end)
            n['c_clav']['t'] >> n['srt_clav']['t']
            n['c_clav']['r'] >> n['srt_clav']['r']
            n['c_clav']['s'] >> n['srt_clav']['s']

            mc.pointConstraint(str(n['c_clav']), str(n['j_clav']), n='_px#')
            n['c_clav']['s'] >> n['j_clav']['s']

        self.set_id(n['j_clav'], 'j.clavicle')

        # auto translate rig
        n['inf_clav'] = duplicate_joint(n['tip_clav'], p=n['root_clav'], n='inf_' + n_clav + n_end)
        n['sk_clav'] = duplicate_joint(n['j_clav'], p=n['inf_clav'], n='sk_' + n_clav + n_end)
        n['end_clav'] = duplicate_joint(n['tip_clav'], p=n['sk_clav'], n='end_' + n_clav + n_end)

        n['sk_clav']['ssc'] = False

        # connect inf clav
        mc.pointConstraint(str(n['tip_clav']), str(n['inf_clav']), n='_px#')
        mc.pointConstraint(str(n['tip_clav']), str(n['root_1']), n='_px#')

        n['c_clav']['s'] >> n['inf_clav']['s']

        _oc = mc.orientConstraint(str(n['j_clav']), str(n['inf_clav']), n='_ox#')
        _oc = mx.encode(_oc[0])
        _pb = mx.create_node(mx.tPairBlend, name='_blend#')
        for dim in 'XYZ':
            _oc['constraintRotate' + dim] >> _pb['inRotate' + dim + '1']
            _pb['outRotate' + dim] >> n['inf_clav']['rotate' + dim]

        _quat = mx.create_node(mx.tEulerToQuat, name='_quat#')
        _euler = mx.create_node(mx.tQuatToEuler, name='_euler#')
        n['j_clav']['rotate'] >> _quat['inputRotate']
        n['j_clav']['rotateOrder'] >> _quat['inputRotateOrder']
        _quat['outputQuatY'] >> _euler['inputQuatY']
        _quat['outputQuatW'] >> _euler['inputQuatW']
        _euler['outputRotateY'] >> _pb['inRotateY2']

        dv = Prefs.get('template/common.limb/default_auto_translate', 0)
        n['c_clav'].add_attr(mx.Double('auto_translate', keyable=True, default=dv, min=0, max=1))
        n['c_clav']['auto_translate'] >> _pb['weight']
        _pb['rotInterpolation'] = 1  # quaternion

        if self.do_clavicle_auto:
            n['ao_clav'] = mx.create_node(mx.tJoint, parent=n['root_clav'], name='j_' + n_clav + '_AO' + n_end)
            n['eff_clav'] = mx.create_node(mx.tJoint, parent=n['ao_clav'], name='end_' + n_clav + '_AO' + n_end)
            copy_transform(tpl_clav, n['ao_clav'], t=True)
            copy_transform(n['c_2'], n['eff_clav'], t=True)

            orient_joint((n['ao_clav'], n['eff_clav']), aim=aim_axis, up=up_axis, up_dir=[0, 1, 0])
            n['eff_clav']['ty'] = n['eff_clav']['ty'].read() / 3

            n['o_clav'] = duplicate_joint(n['root_clav'], p=n['ao_clav'], n='o_' + n_clav + n_end)

            self.set_id(n['o_clav'], 'o.clav')
            mc.parent(str(n['c_clav']), str(n['o_clav']))

            n['ao_1'] = duplicate_joint(n['c_1'], p=n['srt_clav'], n='j_' + n_limb1 + '_AO' + n_end)
            n['ao_2'] = duplicate_joint(n['c_2'], p=n['ao_1'], n='j_' + n_limb2 + '_AO' + n_end)
            n['ao_e'] = duplicate_joint(n['c_e'], p=n['ao_2'], n='j_' + n_eff + 'AO' + n_end)
            n['ik_ao'] = create_ik_handle(sj=n['ao_1'], ee=n['ao_e'], sol='ikRPsolver', n='ik_' + n_limb + '_AO' + n_end)
            n['ik_ao']['snapEnable'] = False

            n['loc0_ao'] = mx.create_node(mx.tTransform, parent=n['root_clav'], name='loc_' + n_clav + '_orig_AO' + n_end)
            copy_transform(n['eff_clav'], n['loc0_ao'], t=True)

            n['ik_clav'] = create_ik_handle(sj=n['j_clav'], ee=n['tip_clav'], sol='ikSCsolver', n='ik_' + n_clav + n_end)
            n['ik_clav']['snapEnable'] = False
            mc.parent(str(n['ik_clav']), str(n['c_clav']))

            n['ik_aosw'] = create_ik_handle(sj=n['ao_clav'], ee=n['eff_clav'], sol='ikSCsolver', n='ik_' + n_limb1 + '_switchAO' + n_end)
            n['ik_aosw']['snapEnable'] = False
            mc.parent(str(n['ik_aosw']), str(n['root_clav']))

            n['c_clav'].add_attr(mx.Double('auto_orient', keyable=True, min=0, max=1))
            _px = mc.pointConstraint(str(n['loc0_ao']), str(n['ao_2']), str(n['ik_aosw']), n='_px#')
            _px = mx.encode(_px[0])

            connect_reverse(n['c_clav']['auto_orient'], _px['w0'])
            n['c_clav']['auto_orient'] >> _px['w1']

    def build_reverse_lock(self):
        n = self.n

        n_eff = self.get_name('effector')
        n_digits = self.get_name('digits')
        n_heel = self.get_name('heel')
        n_end = self.get_branch_suffix()

        do_bank = self.get_opt('bank')

        # scale pivot
        n['s_eIK'] = mx.create_node(mx.tTransform, parent=n['c_eIK_offset'], name='s_' + n_eff + '_IK' + n_end)
        pos_xz = (n['c_e'].translation(mx.sWorld) + n['c_dg'].translation(mx.sWorld)) / 2
        pos_y = n['end_dg'].translation(mx.sWorld)

        pos = mx.Transformation(translate=mx.Vector(pos_xz[0], pos_y[1], pos_xz[2]))
        pos *= n['s_eIK']['pim'][0].as_transform()
        n['s_eIK']['t'] = pos.translation()

        n['c_eIK'].add_attr(mx.Double('stomp', keyable=True, min=-1, max=1))
        n['c_eIK'].add_attr(mx.Double('stomp_power', min=-1, max=0, default=-0.5))
        n['c_eIK']['stomp_power'] = self.get_opt('stomp_power')
        _stomp = connect_driven_curve(n['c_eIK']['stomp'], None, {0: 1, 1: 0.1, -1: 2}, pre='constant', key_style='linear')
        _pow = connect_expr('stomp ^ p', stomp=_stomp['o'], p=n['c_eIK']['stomp_power'])

        dim0 = self.get_opt('up_axis').strip('-')
        dim1 = self.get_opt('aim_axis').strip('-')
        dim2 = self.get_opt('up_axis2').strip('-')
        if self.get_opt('effector_plane') == 'z':
            dim0, dim1, dim2 = dim2, dim0, dim1

        _stomp['o'] >> n['s_eIK']['s' + dim1]
        _pow >> n['s_eIK']['s' + dim0]
        _pow >> n['s_eIK']['s' + dim2]

        n['s_e'] = mx.create_node(mx.tTransform, parent=n['root_e'], name='s_' + n_eff + n_end)
        mc.orientConstraint(str(n['c_eIK_offset']), str(n['s_e']), n='_ox#')

        _mult1 = mx.create_node(mx.tMultiplyDivide, name='_mult#')
        n['c_eIK']['s'] >> _mult1['input1']
        n['c_eIK_offset']['s'] >> _mult1['input2']

        _mult2 = mx.create_node(mx.tMultiplyDivide, name='_mult#')
        _stomp['o'] >> _mult2['i1' + dim1]
        _pow >> _mult2['i1' + dim0]
        _pow >> _mult2['i1' + dim2]
        _mult1['output'] >> _mult2['input2']

        _b = mx.create_node(mx.tBlendColors, name='_blend#')
        _mult2['output'] >> _b['color1']
        _b['color2'] = (1, 1, 1)
        n['ik']['ikBlend'] >> _b['blender']
        _b['output'] >> n['s_e']['s']

        n['neg_e'] = mx.create_node(mx.tTransform, parent=n['s_e'], name='rev_' + n_eff + n_end)
        n['neg_e']['ro'] = mx.Euler.ZYX
        _neg = mx.create_node(mx.tMultiplyDivide, name='_neg#')
        _neg['i2'] = (-1, -1, -1)
        n['s_e']['r'] >> _neg['i1']
        _neg['o'] >> n['neg_e']['r']

        mc.parent(str(n['c_e']), str(n['neg_e']))

        # reverse IK skeleton
        n['j_ehIK'] = mx.create_node(mx.tJoint, parent=n['s_eIK'], name='j_' + n_heel + '_IK' + n_end)
        n['j_eeIK'] = mx.create_node(mx.tJoint, parent=n['j_ehIK'], name='j_' + n_eff + '_tip_IK' + n_end)
        n['j_eIK'] = mx.create_node(mx.tJoint, parent=n['j_eeIK'], name='j_' + n_eff + '_IK' + n_end)
        n['j_emIK'] = mx.create_node(mx.tJoint, parent=n['j_eIK'], name='j_' + n_eff + '_mid_IK' + n_end)
        n['end_emIK'] = mx.create_node(mx.tJoint, parent=n['j_emIK'], name='end_' + n_eff + '_mid_IK' + n_end)
        n['j_dgIK'] = mx.create_node(mx.tJoint, parent=n['j_eIK'], name='j_' + n_digits + '_IK' + n_end)
        n['end_dgIK'] = mx.create_node(mx.tJoint, parent=n['j_dgIK'], name='end_' + n_digits + '_IK' + n_end)

        copy_transform(self.get_structure('heel')[0], n['j_ehIK'], t=True)
        copy_transform(n['end_dg'], n['j_eeIK'], t=True)
        copy_transform(n['c_dg'], n['j_eIK'], t=True)
        copy_transform(n['c_dg'], n['j_emIK'], t=True)
        copy_transform(n['c_e'], n['end_emIK'], t=True)
        copy_transform(n['c_dg'], n['j_dgIK'], t=True)
        copy_transform(n['end_dg'], n['end_dgIK'], t=True)

        if do_bank:
            n['j_bint'] = mx.create_node(mx.tJoint, parent=n['j_eIK'], name='j_' + n_eff + '_bank_int_IK' + n_end)
            n['j_bext'] = mx.create_node(mx.tJoint, parent=n['j_bint'], name='j_' + n_eff + '_bank_ext_IK' + n_end)

            tpl_dig = self.get_structure('digits')[0]
            tpl_bank_int = self.get_structure('bank_int')
            tpl_bank_ext = self.get_structure('bank_ext')

            if not tpl_bank_int:
                if not self.root.is_referenced():
                    tpl_bank_int = mx.create_node(mx.tJoint, parent=tpl_dig, name='tpl_bank_int')
                    tpl_bank_int['tx'] = 0.5
                    self.set_template_id(tpl_bank_int, 'bank_int')
                else:
                    raise RuntimeError('can\'t update bank template on {} from {}'.format(self.root, self.name))
            else:
                tpl_bank_int = tpl_bank_int[0]

            if not tpl_bank_ext:
                if not self.root.is_referenced():
                    tpl_bank_ext = mx.create_node(mx.tJoint, parent=tpl_dig, name='tpl_bank_ext')
                    tpl_bank_ext['tx'] = -0.5
                    self.set_template_id(tpl_bank_ext, 'bank_ext')
                else:
                    raise RuntimeError('can\'t update bank template on {} from {}'.format(self.root, self.name))
            else:
                tpl_bank_ext = tpl_bank_ext[0]

            copy_transform(tpl_bank_int, n['j_bint'], t=True)
            copy_transform(tpl_bank_ext, n['j_bext'], t=True)

            mc.parent(str(n['j_emIK']), str(n['j_bext']))
            mc.parent(str(n['j_dgIK']), str(n['j_bext']))

        # IKs
        n['ik_em'] = create_ik_handle(sj=n['c_e'], ee=n['root_dg'], sol='ikSCsolver', n='ik_' + n_eff + '_mid' + n_end)
        n['ik_em']['snapEnable'] = False

        n['ik_dg'] = create_ik_handle(sj=n['c_dg'], ee=n['end_dg'], sol='ikSCsolver', n='ik_' + n_digits + n_end)
        n['ik_dg']['snapEnable'] = False

        # stretch/scale offset
        n['loc_lockIK'] = mx.create_node(mx.tTransform, parent=n['c_eIK_offset'], name='loc_' + n_eff + '_lock_IK' + n_end)
        mc.parent(str(n['loc_lockIK']), str(n['s_eIK']))
        mc.pointConstraint(str(n['end_emIK']), str(n['loc_lockIK']), n='_px#')

        n['loc_lock'] = mx.create_node(mx.tTransform, parent=n['c_2'], name='loc_' + n_eff + '_lock' + n_end)
        _lock_px = mc.pointConstraint(str(n['loc_lockIK']), str(n['loc_lock']), skip=['x', 'z'], n='_px#')
        _lock_px = mx.encode(_lock_px[0])

        _lock_px['constraintTranslateY'] // n['loc_lock']['ty']
        if n['root_e']['ty'].read() > 0:
            _if = connect_expr('ct < t ? t : ct', ct=_lock_px['constraintTranslateY'], t=n['root_e']['ty'])
        else:
            _if = connect_expr('ct > t ? t : ct', ct=_lock_px['constraintTranslateY'], t=n['root_e']['ty'])
        _if >> n['loc_lock']['ty']

        n['root_lock'] = mx.create_node(mx.tTransform, parent=n['s_e'], name='root_' + n_eff + '_lock' + n_end)
        _px = mc.pointConstraint(str(n['loc_lock']), str(n['root_lock']), n='_px#')
        _px = mx.encode(_px[0])

        _b = mx.create_node(mx.tPairBlend, name='_blend#')
        for dim in 'XYZ':
            _px['constraintTranslate' + dim] >> _b['inTranslate' + dim + '2']
            _b['outTranslate' + dim] >> n['root_lock']['translate' + dim]

        n['c_sw'].add_attr(mx.Boolean('lock_stretch'))
        connect_mult(n['c_sw']['lock_stretch'], n['ik']['ikBlend'], _b['w'])

        if self.get_opt('reverse_lock'):
            n['c_sw']['lock_stretch'] = True

        n['s_lock'] = mx.create_node(mx.tTransform, parent=n['root_lock'], name='s_' + n_eff + '_lock' + n_end)
        copy_transform(n['s_eIK'], n['s_lock'])

        n['s_lockIK'] = mx.create_node(mx.tTransform, parent=n['loc_lockIK'], name='s_' + n_eff + '_lock_IK' + n_end)
        mc.pointConstraint(str(n['s_eIK']), str(n['s_lockIK']), n='_px#')
        n['s_lockIK']['t'] >> n['s_lock']['t']

        n['loc_emIK'] = mx.create_node(mx.tTransform, parent=n['j_emIK'], name='eff_' + n_eff + '_mid' + n_end)
        copy_transform(n['ik_em'], n['loc_emIK'])
        mmx = mx.create_node(mx.tMultMatrix, name='_mmx#')
        n['loc_emIK']['wm'][0] >> mmx['i'][0]
        n['s_eIK']['wim'][0] >> mmx['i'][1]
        dmx = mx.create_node(mx.tDecomposeMatrix, name='_dmx#')
        mmx['o'] >> dmx['imat']

        mc.parent(str(n['ik_em']), str(n['s_lock']))
        dmx['outputTranslate'] >> n['ik_em']['t']
        dmx['outputRotate'] >> n['ik_em']['r']

        n['loc_dgIK'] = mx.create_node(mx.tTransform, parent=n['j_dgIK'], name='eff_' + n_digits + n_end)
        copy_transform(n['ik_dg'], n['loc_dgIK'])
        mmx = mx.create_node(mx.tMultMatrix, name='_mmx#')
        n['loc_dgIK']['wm'][0] >> mmx['i'][0]
        n['s_eIK']['wim'][0] >> mmx['i'][1]
        dmx = mx.create_node(mx.tDecomposeMatrix, name='_dmx#')
        mmx['o'] >> dmx['imat']

        mc.parent(str(n['ik_dg']), str(n['s_lock']))
        dmx['outputTranslate'] >> n['ik_dg']['t']
        dmx['outputRotate'] >> n['ik_dg']['r']

        # heel fk joint
        # n['j_heel'] = mx.create_node(mx.tJoint, parent=n['j_3'], name='j_' + n_heel + n_end)
        # copy_transform(n['j_ehIK'], n['j_heel'], t=True, r=True)
        # self.set_id(n['j_heel'], 'j.heel')
        #
        # mc.parentConstraint(str(n['j_ehIK']), str(n['j_heel']))

    def build_reverse_lock_poses(self):
        n = self.n

        n_eff = self.get_name('effector')
        n_digits = self.get_name('digits')
        n_heel = self.get_name('heel')

        do_bank = self.get_opt('bank')

        n['c_eIK'].add_attr(mx.Double(n_eff + '_roll', keyable=True, min=-1, max=1))
        n['c_eIK'].add_attr(mx.Double(n_heel + '_roll', keyable=True, min=-1, max=1))
        n['c_eIK'].add_attr(mx.Double('ball_roll', keyable=True, min=-1, max=1))
        n['c_eIK'].add_attr(mx.Double(n_digits + '_roll', keyable=True, min=-1, max=1))
        n['c_eIK'].add_attr(mx.Double(n_heel + '_pivot', keyable=True, min=-1, max=1))
        n['c_eIK'].add_attr(mx.Double('ball_pivot', keyable=True, min=-1, max=1))
        n['c_eIK'].add_attr(mx.Double(n_digits + '_pivot', keyable=True, min=-1, max=1))
        if do_bank:
            n['c_eIK'].add_attr(mx.Double('bank', keyable=True, min=-1, max=1))

        sw = n['sw'][0]
        sw.add_attr(mx.Divider('poses'))

        sw.add_attr(mx.Double('roll_amp', keyable=True, default=90))
        sw.add_attr(mx.Double('roll_offset_roll', keyable=True, default=0))
        sw.add_attr(mx.Double('roll_offset_mid_roll', keyable=True, default=0))
        sw.add_attr(mx.Double('roll_offset_height', keyable=True, default=0))
        sw.add_attr(mx.Double('roll_offset_depth', keyable=True, default=0))
        sw.add_attr(mx.Double('pivot_amp', keyable=True, default=90))
        if do_bank:
            sw.add_attr(mx.Double('bank_amp', keyable=True, default=90))

        dim0 = self.get_opt('up_axis').strip('-')
        dim1 = self.get_opt('aim_axis').strip('-')
        dim2 = self.get_opt('up_axis2').strip('-')
        up = '' if '-' in self.get_opt('up_axis') else '-'
        up_pvt = up
        up_bank = up
        flip = '-' if self.do_flip() else ''
        flip = '-' if up != flip else ''

        if self.get_opt('effector_plane') == 'z':
            dim0, dim1, dim2 = dim2, dim0, dim1
            up = '-' if '-' in self.get_opt('up_axis') else ''
            up_pvt = '' if '-' in self.get_opt('up_axis') else '-'

        ro = (dim0 + dim1 + dim2).lower()
        n['j_ehIK']['ro'] = mx.Euler.orders[ro]
        n['j_emIK']['ro'] = mx.Euler.orders[ro]
        n['j_dgIK']['ro'] = mx.Euler.orders[ro]
        n['j_eeIK']['ro'] = mx.Euler.orders[ro]

        plugs = {
            'h0': n['j_ehIK']['r' + dim0], 'e0': n['j_emIK']['r' + dim0], 'm0': n['j_dgIK']['r' + dim0], 't0': n['j_eeIK']['r' + dim0],
            'h1': n['j_ehIK']['r' + dim1], 'e1': n['j_emIK']['r' + dim1], 'm1': n['j_dgIK']['r' + dim1], 't1': n['j_eeIK']['r' + dim1],
            'b1': n['j_eIK']['r' + dim1],
            'td': n['j_eeIK']['t' + dim2], 'th': n['j_eeIK']['t' + dim1], 'tdv': n['j_eeIK']['t' + dim2].read(), 'thv': n['j_eeIK']['t' + dim1].read(),
            'e_roll': n['c_eIK'][n_eff + '_roll'], 'h_roll': n['c_eIK'][n_heel + '_roll'], 'm_roll': n['c_eIK']['ball_roll'], 't_roll': n['c_eIK'][n_digits + '_roll'],
            'h_pvt': n['c_eIK'][n_heel + '_pivot'], 'm_pvt': n['c_eIK']['ball_pivot'], 't_pvt': n['c_eIK'][n_digits + '_pivot'],
            'amp_roll': sw['roll_amp'], 'amp_pvt': sw['pivot_amp'],
            'o_roll': sw['roll_offset_roll'], 'o_mid_roll': sw['roll_offset_mid_roll'],
            'o_height': sw['roll_offset_height'], 'o_depth': sw['roll_offset_depth']
        }

        if do_bank:
            plugs.update({
                'bkint': n['j_bint']['r' + dim2], 'bkext': n['j_bext']['r' + dim2],
                'amp_bk': sw['bank_amp'], 'bank': n['c_eIK']['bank'],
            })

        connect_expr('h0 = e_roll < 0 ? {}amp_roll * e_roll : 0'.format(up), **plugs)

        e0 = connect_expr('e_roll > 0 ? {}(amp_roll + o_mid_roll)* e_roll: 0'.format(up), **plugs)
        e1 = connect_expr('{}(amp_roll + o_mid_roll) * h_roll'.format(up), **plugs)
        connect_add(e0, e1, plugs['e0'])

        connect_expr('m0 = {}amp_roll * m_roll'.format(up), **plugs)
        _offset = connect_expr('e_roll > 0 ? {}o_roll * e_roll : 0'.format(up), **plugs)
        _offset2 = connect_expr('{}o_roll * h_roll'.format(up), **plugs)
        connect_expr('t0 = {}amp_roll * t_roll + offset + offset2'.format(up), offset=_offset, offset2=_offset2, **plugs)

        _offset = connect_expr('e_roll > 0 ? {}o_height * e_roll : 0'.format(flip), **plugs)
        connect_expr('th = thv + offset + {}o_height * h_roll'.format(flip), offset=_offset, **plugs)

        _offset = connect_expr('e_roll > 0 ? {}o_depth * e_roll : 0'.format(flip), **plugs)
        connect_expr('td = offset + tdv + {}o_depth * h_roll'.format(flip), offset=_offset, **plugs)

        connect_expr('h1 = {}amp_pvt * h_pvt'.format(up_pvt), **plugs)
        connect_expr('b1 = {}amp_pvt * m_pvt'.format(up_pvt), **plugs)
        connect_expr('t1 = {}amp_pvt * t_pvt'.format(up_pvt), **plugs)

        if do_bank:
            connect_expr('bkint = bank<0 ? {}amp_bk * -bank : 0'.format(up_bank), **plugs)
            connect_expr('bkext = bank>0 ? {}amp_bk * -bank : 0'.format(up_bank), **plugs)

    def build_pole_vector_auto(self):
        n = self.n

        n_limb = self.name
        n_end = self.get_branch_suffix()

        # attr sep
        n['c_eIK'].add_attr(mx.Divider('pole_vector'))

        # pv auto rig
        n['ao_pv'] = mx.create_node(mx.tJoint, parent=n['root_1'], name='j_' + n_limb + '_PV_auto' + n_end)
        copy_transform(n['c_1'], n['ao_pv'], t=True)
        mc.delete(mc.aimConstraint(str(n['c_e']), str(n['ao_pv']), aim=[0, 1, 0], u=[0, 0, 1], wu=[0, 0, 1], wut='vector'))
        mc.makeIdentity(str(n['ao_pv']), a=1)

        n['end_pv'] = mx.create_node(mx.tJoint, parent=n['ao_pv'], name='end_' + n_limb + '_PV_auto' + n_end)
        n['end_pv']['ty'] = 1

        orient_joint(n['ao_pv'], aim='x', aim_dir=[1, 0, 0], up='z', up_dir=[0, 0, 1])

        if not self.do_clavicle:
            mc.pointConstraint(str(n['c_1']), str(n['ao_pv']), n='_px#')
        else:
            mc.parent(str(n['ao_pv']), str(n['root_clav']))

        # pole vector space switch
        pv_space = self.get_opt('pv_space')
        if pv_space:
            n['o_pv'] = duplicate_joint(n['ao_pv'], n='root_' + n_limb + '_PV_auto' + n_end)
            mc.parent(str(n['ao_pv']), str(n['o_pv']))

            pv_tgt = None
            if '::' not in pv_space:
                branch_id = self.get_branch_id()
                for tpl_parent in self.get_all_parents():
                    if branch_id in tpl_parent.get_branch_ids():
                        _pv_space = '{}{}::{}'.format(tpl_parent.name, branch_id, pv_space)
                    else:
                        _pv_space = '{}::{}'.format(tpl_parent.name, pv_space)
                    pv_tgt = mk.Nodes.get_id(_pv_space)
                    if pv_tgt:
                        break
            else:
                pv_tgt = mk.Nodes.get_id(pv_space)

            if pv_tgt:
                _oc = mc.orientConstraint(str(pv_tgt), str(n['o_pv']), n='_ox#', mo=1)
                _oc = mx.encode(_oc[0])
                _pb = mx.create_node(mx.tPairBlend, name='_blend#')
                for dim in 'XYZ':
                    _oc['constraintRotate' + dim] >> _pb['inRotate' + dim + '2']
                    _pb['outRotate' + dim] >> n['o_pv']['rotate' + dim]

                name = ''
                if '.' in pv_space:
                    name = '_' + pv_space.split('.')[-1]
                plug_name = 'follow' + name

                n['c_eIK'].add_attr(mx.Double(plug_name, keyable=True, default=self.get_opt('pv_space_default'), min=0, max=1))
                n['c_eIK'][plug_name] >> _pb['w']

        n['ik_pv'] = create_ik_handle(sj=str(n['ao_pv']), ee=str(n['end_pv']), sol='ikRPsolver', n='ik_' + n_limb + '_PV_auto' + n_end)
        n['ik_pv']['snapEnable'] = False
        n['ik_pv']['poleVector'] = (0, 0, 0)
        mc.parent(str(n['ik_pv']), str(n['end_emIK']))
        n['ik_pv']['t'] = (0, 0, 0)

    def build_pole_vector_follow(self):
        n = self.n

        n_limb = self.get_name('effector')
        n_end = self.get_branch_suffix()

        n['ao_pvf'] = mx.create_node(mx.tJoint, parent=n['c_eIK_offset'], name='j_' + n_limb + '_PV_follow' + n_end)
        if not self.get_opt('clavicle'):
            mc.delete(mc.aimConstraint(str(n['c_1']), str(n['ao_pvf']), aim=[0, 1, 0], u=[0, 0, 1], wu=[0, 0, 1], wut='vector'))
        else:
            mc.delete(mc.aimConstraint(str(n['c_clav']), str(n['ao_pvf']), aim=[0, 1, 0], u=[0, 0, 1], wu=[0, 0, 1], wut='vector'))

        mc.makeIdentity(str(n['ao_pvf']), a=1)
        n['ao_pvf']['inverseScale'].disconnect()
        n['c_eIK_offset']['s'] >> n['ao_pvf']['inverseScale']

        n['end_pvf'] = mx.create_node(mx.tJoint, parent=n['ao_pvf'], name='end_' + n_limb + '_PV_follow' + n_end)
        n['end_pvf']['ty'] = 1

        n['ik_pvf'] = create_ik_handle(sj=str(n['ao_pvf']), ee=str(n['end_pvf']), sol='ikRPsolver', n='ik_' + n_limb + '_PV_follow' + n_end)
        n['ik_pvf']['snapEnable'] = False
        n['ik_pvf']['poleVector'] = (0, 0, 0)

        if not self.get_opt('clavicle'):
            mc.parent(str(n['ik_pvf']), str(n['eff_root']))
            n['ik_pvf']['t'] = (0, 0, 0)
        else:
            if self.do_clavicle_auto:
                mc.parent(str(n['ik_pvf']), str(n['srt_clav']))
            else:
                mc.parent(str(n['ik_pvf']), str(n['inf_clav']))
            copy_transform(self.get_structure('limb1')[0], n['ik_pvf'], t=True)

    def build_twist_joints(self, nj, tw, name, c, sk, j_base, j_mid, j_tip):
        n = self.n

        n_end = self.get_branch_suffix()

        deform_chains = self.get_chains()
        n_chain = ['_' + str(x) if x else x for x in deform_chains]
        nc = len(deform_chains)

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
                    j = duplicate_joint(sk, p=sk, n='root_' + name + str(i) + n_chain[_c] + n_end)
                    roots[_c].append(j)

                    j = duplicate_joint(sk, p=roots[_c][-1], n='sk_' + name + str(i) + n_chain[_c] + n_end)
                    sks[_c].append(j)
                    mxs[_c].append(mx.create_node(mx.tFourByFourMatrix, name='_mx#'))

            # bend points
            if 0 < i <= nj:
                p1 = mx.create_node(mx.tTransform, parent=sk, name='p1_' + name + str(i) + n_end)
                p1s[i] = p1

                if nj > 1:
                    pc1 = mc.pointConstraint(str(j_base), str(j_mid), str(j_tip), str(p1), n='_px#')
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
            if 0 < i <= nj or (tw == 'up' and i == nj + 1):
                p2 = mx.create_node(mx.tTransform, parent=n['rig_smooth'], name='p2_' + name + str(i) + n_end)

                _pc = mx.create_node(mx.tMotionPath)
                n['cv_sm'].shape()['local'] >> _pc['geometryPath']

                if self.get_opt('smooth_type') == 'length':
                    _pc['fractionMode'] = 1
                    axis = self.get_opt('aim_axis')[-1]
                    t1 = n['j_2']['t' + axis].read()
                    t2 = n['j_e']['t' + axis].read()
                    m1 = t1 / (t1 + t2)
                    m2 = t2 / (t1 + t2)

                    u = 0
                    if tw == 'up':
                        u = i / float(nj + 1) * m1
                    elif tw == 'dn':
                        u = i / float(nj + 1) * m2 + m1

                    if u > 1:
                        u = 1.0

                else:
                    if i == nj + 1:
                        u = 1
                    else:
                        u = get_closest_point_on_curve(n['cv_sm'], p1s[i], parameter=True)

                _pc['u'] = u
                _pc['allCoordinates'] >> p2['t']

                if i <= nj:
                    for _c in range(nc):
                        pc = mc.pointConstraint(str(p1s[i]), str(p2), str(roots[_c][-1]), n='_px#')
                        pc = mx.encode(pc[0])
                        n['sm_off'] >> pc['w0']
                        n['sm_on'] >> pc['w1']

                if i == nj + 1:
                    n['p2_pt'] = p2

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
        else:
            mc.pointConstraint(str(j_tip), str(loc_end), n='_px#')

        if tw == 'dn':
            for _c in range(nc):
                pc = mc.pointConstraint(str(j_base), str(n['p2_pt']), str(roots[_c][0]), n='_px#')
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
        elif tw == 'dn':
            mc.orientConstraint(str(roots[0][0]), str(n['loc_sh_m']))
            mc.orientConstraint(str(roots[0][-1]), str(n['loc_sh_dn']))

        # twists rig
        if tw == 'up':
            j_tw = duplicate_joint(sk, p=p1s[min(p1s)], n='j_' + name + '_twist' + n_end)  # p=roots[1]
            n['j_tw_up'] = j_tw
            copy_transform(roots[0][1], j_tw, t=True)
            end_tw = duplicate_joint(sk, p=j_tw, n='end_' + name + '_twist' + n_end)
            n['c_sw'].add_attr(mx.Double('twist_up', min=0, max=1, default=1))
            n['tw_up'] = connect_mult(j_tw['ry'], n['c_sw']['twist_up'])
        elif tw == 'dn':
            j_tw = duplicate_joint(sk, p=p1s[max(p1s)], n='j_' + name + '_twist' + n_end)  # p=roots[1]
            n['j_tw_dn'] = j_tw
            end_tw = duplicate_joint(sk, p=j_tw, n='end_' + name + '_twist' + n_end)
            copy_transform(roots[0][-1], j_tw, t=True)
            copy_transform(j_tip, end_tw, t=True)
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
        elif tw == 'dn':
            mc.parent(str(ik_tw), str(n['sub_e']))
            copy_transform(n['sub_e'], ik_tw, t=True)

        # weights rig
        for _c in range(nc):
            if name not in n['sw'][_c]:
                n['sw'][_c].add_attr(mx.Divider(name))

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
                    connect_mult(n['tw_up'], _twist, _aim['offsetY'])

                    connect_mult(_shear_base, n['shz_up'], mxs[_c][i]['in01'])
                    connect_expr('x = b*up + t*-m', x=mxs[_c][i]['in21'], b=_shear_base, t=_shear_tip, up=n['shx_up'], m=n['shx_m'])
                else:
                    _twist.write(float(i) / nj)
                    connect_mult(n['tw_dn'], _twist, _aim['offsetY'])

                    connect_mult(_shear_tip, n['shz_dn'], mxs[_c][i]['in01'])
                    connect_expr('x = b*m + t*dn', x=mxs[_c][i]['in21'], b=_shear_base, t=_shear_tip, m=n['shx_m'], dn=n['shx_dn'])

        return sks

    def build_rotate_order(self):
        """ placeholder """

    def build_space_mods(self):
        mk.Mod.add(
            self.n['c_eIK'], 'space',
            {
                'rest_name': 'root',
                'targets': [self.get_hook(tag=True), '*::space.world', '*::space.move']
            }
        )

    def get_chains(self):
        chain = self.get_opt('add_chains')
        if not chain:
            chain = []
        if isinstance(chain, string_types):
            chain = [chain]

        chain = ['c' + str(c) if not isinstance(c, str) else c for c in chain]
        chain = [''] + chain
        return chain


# misc math ------------------------------------------------------------------------------------------------------------

def get_triangle_weights(p, v0, v1, v2):
    p = mx.Vector(p)
    v0 = mx.Vector(v0)
    v1 = mx.Vector(v1)
    v2 = mx.Vector(v2)

    p0 = project_vector(v0, p, v1, v2)
    p1 = project_vector(v1, p, v0, v2)
    p2 = project_vector(v2, p, v0, v1)

    w0 = (p0 - p).length() / (p0 - v0).length()
    w1 = (p1 - p).length() / (p1 - v1).length()
    w2 = (p2 - p).length() / (p2 - v2).length()

    return w0, w1, w2


def project_vector(u1, u2, v1, v2):
    u1 = mx.Vector(u1)
    u2 = mx.Vector(u2)
    v1 = mx.Vector(v1)
    v2 = mx.Vector(v2)

    uv1 = v1 + project(u1 - v1, v2 - v1)
    uv2 = v1 + project(u2 - v1, v2 - v1)

    l = (uv1 - u1).length()
    f = l / project(u2 - u1, uv1 - u1).length()

    return uv1 + f * (uv2 - uv1)


def project(a, b):
    a = mx.Vector(a)
    b = mx.Vector(b)
    return b * (a * b / (b.length() ** 2))
