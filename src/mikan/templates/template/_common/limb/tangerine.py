# coding: utf-8

import math

import meta_nodal_py as kl
from meta_nodal_py.Imath import V3f, M44f, Euler

import mikan.tangerine.core as mk
from mikan.vendor.geomdl.utilities import generate_knot_vector
from mikan.tangerine.lib.commands import *
from mikan.tangerine.lib.connect import *
from mikan.tangerine.lib.rig import *
from mikan.tangerine.lib.nurbs import get_closest_point_on_curve

from mikan.core.prefs import Prefs
from mikan.core.logger import create_logger

log = create_logger()


class Template(mk.Template):

    def build_rig(self):
        # get structures
        hook = self.hook
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
        n['c_1'] = kl.Joint(hook, 'c_' + n_limb1 + n_end)
        n['c_2'] = kl.Joint(n['c_1'], 'c_' + n_limb2 + n_end)
        n['c_e'] = kl.Joint(n['c_2'], 'c_' + n_eff + n_end)
        n['c_dg'] = kl.Joint(n['c_e'], 'c_' + n_digits + n_end)
        n['end_dg'] = kl.Joint(n['c_dg'], 'end_' + n_digits + n_end)

        copy_transform(tpl_limb1, n['c_1'], t=1)
        copy_transform(tpl_limb2, n['c_2'], t=1)
        copy_transform(tpl_limb3, n['c_e'], t=1)
        copy_transform(tpl_digits, n['c_dg'], t=1)
        copy_transform(tpl_tip, n['end_dg'], t=1)

        # orient skeleton
        orient_joint((n['c_1'], n['c_2'], n['c_e']), aim=aim_axis, up=up_axis, up_auto=1)
        plane = self.get_opt('effector_plane')

        if self.get_opt('reverse_lock') and plane == 'ground':
            # orient from ground (foot)
            t1 = tpl_tip.world_transform.get_value().translation()
            t2 = tpl_limb3.world_transform.get_value().translation()

            vp = t1 - t2
            vp = vp.cross(V3f(0, 1, 0))

            t1 = tpl_tip.world_transform.get_value().translation()
            t2 = n['c_e'].world_transform.get_value().translation()
            vd = t1 - t2
            vd.y = 0

            orient_joint(n['c_e'], aim=up_axis2, aim_dir=vd, up=up_axis, up_dir=vp)
            orient_joint((n['c_dg'], n['end_dg']), aim=up_axis2, up=up_axis, up_dir=vp)

            # conform limb
            up0 = n['c_1'].world_transform.get_value().multDirMatrix(axis_to_vector(up_axis))
            if up0.dot(vp) < 0:
                for j in (n['c_1'], n['c_2']):
                    _children = j.get_children()
                    for _c in _children:
                        _c.reparent(hook)
                    _xfo = M44f(V3f(0, 0, 0), V3f(0, 180, 0), V3f(1, 1, 1), Euler.XYZ) * j.transform.get_value()
                    j.transform.set_value(_xfo)
                    for _c in _children:
                        _c.reparent(j)

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
                p1 = tpl_limb1.world_transform.get_value().translation()
                p2 = tpl_limb2.world_transform.get_value().translation()
                p3 = tpl_limb3.world_transform.get_value().translation()
                pe = tpl_digits.world_transform.get_value().translation()
                pt = tpl_tip.world_transform.get_value().translation()
                v1 = (p2 - p1).cross(p3 - p2).normalized()
                v2 = (pe - p3).cross(pt - pe).normalized()
                p = v1.dot(v2)
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
        n['c_1'].reparent(n['root_1'])

        n['root_e'] = duplicate_joint(n['c_e'], p=n['c_2'], n='root_' + n_eff + n_end)
        n['c_e'].reparent(n['root_e'])

        n['root_dg'] = duplicate_joint(n['c_dg'], p=n['c_e'], name='root_' + n_digits + n_end)
        n['c_dg'].reparent(n['root_dg'])

        for c in ('c_1', 'c_2', 'c_e', 'c_dg'):
            create_srt_in(n[c], k=1)

        # deform skeleton
        n['j_1'] = duplicate_joint(n['c_1'], p=n['root_1'], n='j_' + n_limb1 + n_end)
        n['j_2'] = duplicate_joint(n['c_2'], p=n['j_1'], n='j_' + n_limb2 + n_end)
        n['j_e'] = duplicate_joint(n['c_e'], p=n['j_2'], n='j_' + n_eff + n_end)
        n['j_dg'] = duplicate_joint(n['c_dg'], p=n['j_e'], n='j_' + n_digits + n_end)
        self.set_id(n['j_1'], 'j.limb1')
        self.set_id(n['j_2'], 'j.limb2')
        self.set_id(n['j_e'], 'j.limb3')
        self.set_id(n['j_dg'], 'j.digits')

        n['j_1'].transform.connect(n['c_1'].transform)
        n['j_2'].transform.connect(n['c_2'].transform)

        _mmx = kl.MultM44f(n['j_e'], '_mmx')
        _mmx.input[0].connect(n['c_e'].world_transform)
        _imx = kl.InverseM44f(n['j_e'], '_imx')
        _imx.input.connect(n['root_e'].world_transform)
        _mmx.input[1].connect(_imx.output)

        _srt = create_srt_out(n['root_e'], vectors=False)
        create_srt_in(n['j_e'], vectors=False)
        merge_transform(n['j_e'], t_in=_srt.translate, r_in=_mmx.output, s_in=_mmx.output, sh_in=_mmx.output, is_joint=False)

        _srt = create_srt_out(n['root_dg'], vectors=False)
        create_srt_in(n['j_dg'], vectors=False)
        merge_transform(n['j_dg'], t_in=_srt.translate, r_in=n['c_dg'].transform, s_in=n['c_dg'].transform, sh_in=n['c_dg'].transform)

        add_plug(n['c_dg'], 'parent_scale', bool, default_value=True)
        _r = kl.Not(n['root_dg'], '_not')
        _r.input.connect(n['c_dg'].parent_scale)
        n['root_dg'].scale_compensate.connect(_r.output)
        n['j_dg'].scale_compensate.connect(_r.output)

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
        n['root_eIK'] = kl.SceneGraphNode(default_hook, 'root_' + n_eff + '_IK' + n_end)
        copy_transform(n['c_e'], n['root_eIK'], t=1)
        n['c_eIK'] = duplicate_joint(n['c_e'], p=n['root_eIK'], n='c_' + n_eff + '_IK' + n_end)
        create_srt_in(n['c_eIK'], k=1)

        n['root_eIK_offset'] = kl.Joint(default_hook, 'root_' + n_eff + '_IK_offset' + n_end)
        copy_transform(n['c_e'], n['root_eIK_offset'], t=1)
        n['c_eIK_offset'] = duplicate_joint(n['c_e'], p=n['root_eIK_offset'], n='c_' + n_eff + '_IK_offset' + n_end)
        create_srt_in(n['c_eIK_offset'], k=1)

        n['root_eIK_offset'].reparent(n['c_eIK'])

        n['ik'], n['root_ik'], n['eff_root'], n['eff_ik'] = stretch_IK((n['c_1'], n['c_2'], n['root_e']), n['c_eIK'])
        n['ik'].translate_root_in.connect(n['c_1'].find('transform').translate)
        n['ik'].rename('ik_' + n_limb + n_end)
        n['eff_root'].rename('eff_' + n_limb + '_base' + n_end)
        n['eff_ik'].rename('eff_' + n_limb + n_end)

        if self.get_opt('default_stretch'):
            n['c_eIK'].stretch.set_value(1)

        add_plug(n['j_1'], 'squash', float)
        add_plug(n['j_2'], 'squash', float)
        n['j_1'].squash.connect(n['c_1'].squash)
        n['j_2'].squash.connect(n['c_2'].squash)

        if self.do_clavicle and self.do_clavicle_auto:
            reparent_ik_handle(n['ik_ao'], n['c_eIK_offset'])
            n['ik_ao'].find('ik').twist_in.connect(n['ik'].twist_in)

        # switch controller
        n['c_sw'] = kl.SceneGraphNode(hook, 'c_' + n_limb + '_switch' + n_end)

        # deform switch control
        n['sw'] = {}

        for i, chain in enumerate(deform_chains):
            n['sw'][i] = kl.SceneGraphNode(hook, 'sw_' + n_limb + '_weights' + n_chain[i] + n_end)
            self.set_id(n['sw'][i], 'weights.{}'.format(i))
            if i > 0:
                self.set_id(n['sw'][i], 'weights.{}'.format(chain))

        # reverse IK rig
        self.build_reverse_lock()

        # change stretch IK pointConstraint
        n['eff_ik'].transform.get_input().get_node().remove_from_parent()
        point_constraint(n['end_emIK'], n['eff_ik'])

        # reverse lock IK poses
        if self.get_opt('reverse_lock'):
            self.build_reverse_lock_poses()

        # pole vector
        self.build_pole_vector_auto()
        self.build_pole_vector_follow()

        p1 = tpl_limb1.world_transform.get_value().translation()
        p2 = tpl_limb2.world_transform.get_value().translation()
        p3 = tpl_limb3.world_transform.get_value().translation()

        u = p2 - p1
        v = p3 - p1
        u1 = (u * v)
        v1 = (v * v)
        k = u1.length() / v1.length()
        p4 = p1 + (v * k)
        v2 = p2 - p4
        p = p4 + (v2 * (v.length() / v2.length()))

        n['loc_pv'] = kl.SceneGraphNode(n['ao_pv'], 'loc_' + n_limb + '_PV_auto' + n_end)
        n['loc_pv'].set_world_transform(M44f(p, V3f(0, 0, 0), V3f(1, 1, 1), Euler.Default))

        n['loc_pvf'] = kl.SceneGraphNode(n['ao_pvf'], 'loc_' + n_limb + '_PV_follow' + n_end)
        n['loc_pvf'].set_world_transform(M44f(p, V3f(0, 0, 0), V3f(1, 1, 1), Euler.Default))

        hook_pv = n['root_1']
        if self.do_clavicle:
            hook_pv = n['root_clav']
        n['root_pv'] = kl.SceneGraphNode(hook_pv, 'root_' + n_limb + '_PV' + n_end)
        n['c_pv'] = kl.SceneGraphNode(n['root_pv'], 'c_' + n_limb + '_PV' + n_end)

        _px = point_constraint((n['loc_pv'], n['loc_pvf']), n['root_pv'], weights=[1, 0])

        pv_attr = add_plug(n['c_eIK'], 'follow_' + n_eff, float, k=1, min_value=0, max_value=1, nice_name='Follow ' + n_eff.capitalize())
        _px.w1.connect(pv_attr)
        connect_reverse(pv_attr, _px.w0)

        pv_xfo = n['c_pv'].world_transform.get_value()
        pv_xfo *= n['c_1'].world_transform.get_value().inverse()
        n['ik'].initial_root_pole_vector_in.set_value(pv_xfo)
        n['ik'].world_pole_vector_in.connect(n['c_pv'].world_transform)

        if self.do_clavicle:
            if self.do_clavicle_auto:
                n['ik_ao'].find('ik').world_pole_vector_in.connect(n['ik'].world_pole_vector_in)
        else:
            # db = n['eff_root'].t.outputs(type='distanceBetween')[0]
            dist_plug = n['ik'].find('distance').output
            dist_value = dist_plug.get_value()
            # dist = db.d.get()
            # ao_pvsy = sdk(db.d, n['ao_pv'].sy, {0: 0, dist: 1, (dist * 2): 2}, post='linear', key_style='linear')
            _srt = n['ao_pvf'].find('transform').find('scale')
            connect_driven_curve(dist_plug, _srt.y, {0: 0, dist_value: 1, (dist_value * 2): 2}, tangent_mode='linear', post='linear')
            # ao_pvsy.o >> n['ao_pvf'].sy

        # IK switch
        add_plug(n['c_sw'], 'ik_blend', float, k=1, min_value=0, max_value=1, nice_name='IK/FK Blend')
        n['ik'].blend.connect(n['c_sw'].ik_blend)
        n['ik_em'].blend.connect(n['c_sw'].ik_blend)

        lock_attr = n_digits + '_lock'
        add_plug(n['c_eIK'], lock_attr, bool, default_value=self.get_opt('reverse_lock'))
        _b2f = kl.Condition(n['ik_dg'], '_b2f')
        _b2f.condition.connect(n['c_eIK'].get_dynamic_plug(lock_attr))
        _b2f.input1.set_value(1)
        _b2f.input2.set_value(0)
        connect_mult(_b2f.output, n['c_sw'].ik_blend, n['ik_dg'].blend)

        # deform rig
        n['root_2pt'] = duplicate_joint(n['c_2'], p=n['j_1'], n='root_' + n_limb2 + '_tweak' + n_end)
        n['c_2pt'] = kl.Joint(n['root_2pt'], 'c_' + n_limb2 + '_tweak' + n_end)
        create_srt_in(n['c_2pt'], k=1)

        pc = point_constraint(n['j_2'], n['root_2pt'])
        oc = orient_constraint((n['j_1'], n['j_2']), n['root_2pt'])

        mk.Mod.add(n['c_2pt'], 'space', {'targets': ['::hook']})

        n['aim_1'] = duplicate_joint(n['c_1'], p=n['j_1'], n='j_' + n_limb1 + '_aim' + n_end)
        n['aim_2'] = duplicate_joint(n['c_2'], p=n['j_2'], n='j_' + n_limb2 + '_aim' + n_end)
        n['aim_1'].show.set_value(False)
        n['aim_2'].show.set_value(False)

        n['sub_1'] = duplicate_joint(n['aim_1'], p=n['j_1'], n='j_' + n_limb1 + '_deform' + n_end)
        n['sub_2'] = duplicate_joint(n['aim_2'], p=n['j_2'], n='j_' + n_limb2 + '_deform' + n_end)
        _srt_sub1 = create_srt_in(n['sub_1'], vectors=True)
        _srt_sub2 = create_srt_in(n['sub_2'], vectors=True)

        ac1 = aim_constraint(n['c_2pt'], n['aim_1'], aim_vector=[0, (-1, 1)[not aim_axis.startswith('-')], 0], up_vector=V3f(0, 0, 0))
        ac2 = aim_constraint(n['j_e'], n['aim_2'], aim_vector=[0, (-1, 1)[not aim_axis.startswith('-')], 0], up_vector=V3f(0, 0, 0))
        _srt_aim1 = create_srt_out(n['aim_1'])
        _srt_aim2 = create_srt_out(n['aim_2'])
        _srt_sub1.joint_orient_rotate.connect(_srt_aim1.rotate)
        _srt_sub2.joint_orient_rotate.connect(_srt_aim2.rotate)

        point_constraint(n['c_2pt'], n['aim_2'])
        point_constraint(n['c_2pt'], n['sub_2'])

        # auto unroll
        add_plug(n['c_sw'], 'twist_unroll', float, k=1, min_value=0, max_value=1, nice_name='Twist Unroll')
        add_plug(n['c_sw'], 'twist_fix', float, k=1, nice_name='Twist Fix')
        if self.get_opt('advanced_twist', False):
            add_plug(n['c_sw'], 'twist_fix_up', float, k=1, nice_name='Twist Fix Up')
            add_plug(n['c_sw'], 'twist_fix_dn', float, k=1, nice_name='Twist Fix Down')

        n['loc_2'] = kl.SceneGraphNode(n['root_1'], 'loc_' + n_limb2 + n_end)
        n['loc_1'] = kl.SceneGraphNode(n['loc_2'], 'loc_' + n_limb1 + n_end)
        n['loc_e'] = kl.SceneGraphNode(n['loc_2'], 'loc_' + n_eff + n_end)
        n['vp_1'] = kl.SceneGraphNode(n['loc_1'], 'vp_' + n_limb1 + n_end)
        n['vp_2'] = kl.SceneGraphNode(n['loc_2'], 'vp_' + n_limb2 + n_end)

        _p1 = point_constraint(n['c_2pt'], n['loc_2'])
        _p2 = point_constraint(n['j_1'], n['loc_1'])
        _p3 = point_constraint(n['j_e'], n['loc_e'])
        _srt_out1 = create_srt_out(_p1, vectors=False)
        _srt_out3 = create_srt_out(_p3, vectors=False)

        _vp = kl.Cross(n['vp_1'], '_cross')
        _vp.input1.connect(_srt_out1.translate)
        _vp.input2.connect(_srt_out3.translate)

        _db = kl.Distance(n['vp_1'], '_distance')
        _db.input1.connect(_vp.output)

        _if_op = kl.IsGreater(n['vp_1'], '_isg')
        _if_op.input1.set_value(0.001)
        _if_op.input2.connect(_db.output)
        _ifx = kl.Condition(n['vp_1'], '_if')
        _ifx.condition.connect(_if_op.output)
        _ify = kl.Condition(n['vp_1'], '_if')
        _ify.condition.connect(_if_op.output)
        _ifz = kl.Condition(n['vp_1'], '_if')
        _ifz.condition.connect(_if_op.output)

        _vpv = kl.V3fToFloat(_vp, 'output')
        _vpv.vector.connect(_vp.output)
        _v = _vp.output.get_value()
        _ifx.input1.set_value(_v.x)
        _ify.input1.set_value(_v.y)
        _ifz.input1.set_value(_v.z)
        _ifx.input2.connect(_vpv.x)
        _ify.input2.connect(_vpv.y)
        _ifz.input2.connect(_vpv.z)

        _srt1 = create_srt_in(n['vp_1'], vectors=True)
        _srt2 = create_srt_in(n['vp_2'], vectors=True)
        _srt1_t = _srt1.find('translate')
        _srt2_t = _srt2.find('translate')
        _srt1_t.x.connect(_ifx.output)
        _srt1_t.y.connect(_ify.output)
        _srt1_t.z.connect(_ifz.output)
        _srt2_t.x.connect(_ifx.output)
        _srt2_t.y.connect(_ify.output)
        _srt2_t.z.connect(_ifz.output)

        # -- unroll joints
        n['up_1'] = duplicate_joint(n['c_1'], p=n['aim_1'], n='loc_' + n_limb1 + '_up' + n_end)
        n['up_2'] = duplicate_joint(n['c_2'], p=n['aim_2'], n='loc_' + n_limb2 + '_up' + n_end)

        n['upt_1'] = duplicate_joint(n['c_1'], p=n['up_1'], n='loc_' + n_limb1 + '_up_vector' + n_end)
        n['upt_2'] = duplicate_joint(n['c_2'], p=n['up_2'], n='loc_' + n_limb2 + '_up_vector' + n_end)
        copy_transform(n['vp_1'], n['upt_1'], t=1)
        copy_transform(n['vp_2'], n['upt_2'], t=1)

        _unroll1 = aim_constraint(n['vp_1'], n['up_1'], aim_vector=V3f(0, 0, 1))
        _unroll2 = aim_constraint(n['vp_2'], n['up_2'], aim_vector=V3f(0, 0, 1))
        _unroll1 = create_srt_out(_unroll1, ro=Euler.YZX).find('rotate')
        _unroll2 = create_srt_out(_unroll2, ro=Euler.YZX).find('rotate')

        _b1x = kl.Blend(_srt_sub1, '_blend_x')
        _b1y = kl.Blend(_srt_sub1, '_blend_y')
        _b1z = kl.Blend(_srt_sub1, '_blend_z')
        _b2x = kl.Blend(_srt_sub2, '_blend_x')
        _b2y = kl.Blend(_srt_sub2, '_blend_y')
        _b2z = kl.Blend(_srt_sub2, '_blend_z')

        _b1x.input2.connect(_unroll1.x)
        _b1z.input2.connect(_unroll1.z)
        _b2x.input2.connect(_unroll2.x)
        _b2z.input2.connect(_unroll2.z)

        if self.get_opt('advanced_twist'):
            connect_expr('ry = r+fix1+fix2', ry=_b1y.input2, r=_unroll1.y, fix1=n['c_sw'].twist_fix, fix2=n['c_sw'].twist_fix_up)
            connect_expr('ry = r+fix1+fix2', ry=_b2y.input2, r=_unroll2.y, fix1=n['c_sw'].twist_fix, fix2=n['c_sw'].twist_fix_dn)
            _b1y.input1.connect(connect_add(n['c_sw'].twist_fix, n['c_sw'].twist_fix_up))
            _b2y.input1.connect(connect_add(n['c_sw'].twist_fix, n['c_sw'].twist_fix_dn))
        else:
            _b1y.input2.connect(connect_add(_unroll1.y, n['c_sw'].twist_fix, ))
            _b2y.input2.connect(connect_add(_unroll2.y, n['c_sw'].twist_fix, ))
            _b1y.input1.connect(n['c_sw'].twist_fix)
            _b2y.input1.connect(n['c_sw'].twist_fix)

        _b1x.weight.connect(n['c_sw'].twist_unroll)
        _b1y.weight.connect(n['c_sw'].twist_unroll)
        _b1z.weight.connect(n['c_sw'].twist_unroll)
        _b2x.weight.connect(n['c_sw'].twist_unroll)
        _b2y.weight.connect(n['c_sw'].twist_unroll)
        _b2z.weight.connect(n['c_sw'].twist_unroll)

        _srt_sub1.find('rotate').x.connect(_b1x.output)
        _srt_sub1.find('rotate').y.connect(_b1y.output)
        _srt_sub1.find('rotate').z.connect(_b1z.output)
        _srt_sub2.find('rotate').x.connect(_b2x.output)
        _srt_sub2.find('rotate').y.connect(_b2y.output)
        _srt_sub2.find('rotate').z.connect(_b2z.output)

        # flex rig
        sw = n['sw'][0]

        n['loc_2pt_up'] = kl.SceneGraphNode(n['c_2pt'], 'loc_' + n_limb2 + '_tweak_up' + n_end)
        n['loc_2pt_dn'] = kl.SceneGraphNode(n['c_2pt'], 'loc_' + n_limb2 + '_tweak_dn' + n_end)
        create_srt_in(n['loc_2pt_up'])
        create_srt_in(n['loc_2pt_dn'])

        xfo1 = n['c_1']
        xfo2 = n['c_2pt']
        xfo3 = n['root_e']

        imx = kl.InverseM44f(xfo2, '_imx')
        imx.input.connect(xfo2.world_transform)

        mmx = kl.MultM44f(xfo2, '_mmx')
        mmx.input[0].connect(xfo1.world_transform)
        mmx.input[1].connect(imx.output)
        dmx = create_srt_out(mmx)
        v1 = dmx.translate

        mmx = kl.MultM44f(xfo2, '_mmx')
        mmx.input[0].connect(xfo3.world_transform)
        mmx.input[1].connect(imx.output)
        dmx = create_srt_out(mmx)
        v2 = dmx.translate

        angle = create_angle_between(v1, v2)
        angle0 = angle.get_value()
        add_plug(sw, 'flex_offset_start', float, keyable=True, min_value=0, max_value=1, default_value=0.5)
        angle_weight = connect_expr('max(0, 1-(a/(a0*max(1-w, 0.001))))', a=angle, a0=angle0, w=sw.flex_offset_start)

        add_plug(sw, 'flex_offset_upX', float, keyable=True)
        add_plug(sw, 'flex_offset_upY', float, keyable=True)
        add_plug(sw, 'flex_offset_upZ', float, keyable=True)
        add_plug(sw, 'flex_offset_dnX', float, keyable=True)
        add_plug(sw, 'flex_offset_dnY', float, keyable=True)
        add_plug(sw, 'flex_offset_dnZ', float, keyable=True)

        for side in ('up', 'dn'):
            for dim in 'XYZ':
                offset = sw.get_dynamic_plug('flex_offset_' + side + dim)
                translate = n['loc_2pt_' + side].find('transform/translate').get_plug(dim.lower())
                if self.do_flip():
                    offset = connect_mult(offset, -1)
                connect_mult(offset, angle_weight, translate)

        # bend rig
        n['root_1bd'] = kl.SceneGraphNode(n['sub_1'], 'root_' + n_limb1 + '_bend' + n_end)
        create_srt_in(n['root_1bd'])
        n['c_1bd'] = kl.Joint(n['root_1bd'], 'c_' + n_limb1 + '_bend' + n_end)
        create_srt_in(n['c_1bd'], k=1)
        point_constraint((n['j_1'], n['loc_2pt_up']), n['root_1bd'])

        n['root_2bd'] = kl.SceneGraphNode(n['sub_2'], 'root_' + n_limb2 + '_bend' + n_end)
        create_srt_in(n['root_2bd'])
        n['c_2bd'] = kl.Joint(n['root_2bd'], 'c_' + n_limb2 + '_bend' + n_end)
        create_srt_in(n['c_2bd'], k=1)
        point_constraint((n['loc_2pt_dn'], n['j_e']), n['root_2bd'])

        if self.do_flip():
            for _root in ('root_1bd', 'root_2pt', 'root_2bd'):
                _s = n[_root].find('transform/scale')
                if not _s:
                    _srt = n[_root].find('transform')
                    _s = kl.FloatToV3f(_srt, 'scale')
                    _srt.scale.connect(_s.vector)
                _s.x.set_value(-1)
                _s.y.set_value(-1)
                _s.z.set_value(-1)

        # skin rig: effector
        n['sub_e'] = duplicate_joint(n['j_e'], p=n['j_e'], n='j_' + n_eff + '_deform' + n_end)

        n['sk_e'] = duplicate_joint(n['c_e'], p=n['j_e'], n='sk_' + n_eff + n_end)
        n['end_e'] = duplicate_joint(n['c_dg'], p=n['sk_e'], n='end_' + n_eff + n_end)

        n['sk_dg'] = duplicate_joint(n['c_dg'], p=n['j_dg'], n='sk_' + n_digits + n_end)
        n['end_limb'] = duplicate_joint(n['end_dg'], p=n['sk_dg'], n='end_' + n_limb + n_end)

        n['sk_e'].scale_compensate.set_value(False)
        n['sk_dg'].scale_compensate.set_value(False)

        # skin rig: splits
        n['rig_smooth'] = kl.SceneGraphNode(n['root_1'], 'rig_' + n_limb + '_spline' + n_end)
        n['rig_smooth'].show.set_value(False)

        xfo_smooth = kl.SceneGraphNode(find_root(), 'cv_' + n_limb + n_end)
        n['cv_sm'] = kl.SplineCurve(xfo_smooth, 'cv_' + n_limb + n_end)

        p0 = tpl_limb1.world_transform.get_value().translation()
        p1 = tpl_limb2.world_transform.get_value().translation()
        p2 = tpl_limb3.world_transform.get_value().translation()

        cvs = [p0, (p0 + p1) / 2, p1, (p1 + p2) / 2, p2]
        knots = generate_knot_vector(3, 5)
        weights = [1] * 5
        spline_data = kl.Spline(cvs, knots, weights, False)
        n['cv_sm'].spline_in.set_value(spline_data)
        xfo_smooth.reparent(n['rig_smooth'])

        bpms = []
        for j in (n['j_1'], n['c_1bd'], n['c_2pt'], n['c_2bd'], n['j_e']):
            bpm = kl.SceneGraphNode(n['rig_smooth'], 'bpm_' + j.get_name())
            copy_transform(j, bpm)
            bpms.append(bpm)

        skin_data = {
            'deformer': 'skin',
            'transform': xfo_smooth,
            'data': {
                'infs': {0: n['j_1'], 1: n['c_1bd'], 2: n['c_2pt'], 3: n['c_2bd'], 4: n['j_e']},
                'maps': {
                    0: mk.WeightMap("1 0*4"),
                    1: mk.WeightMap("0 1 0*3"),
                    2: mk.WeightMap("0*2 1 0*2"),
                    3: mk.WeightMap("0*3 1 0"),
                    4: mk.WeightMap("0*4 1")
                },
                'bind_pose': dict(zip(range(len(bpms)), bpms))
            }
        }
        dfm_skin = mk.Deformer(**skin_data)
        dfm_skin.build()
        n['cv_sm'] = dfm_skin.geometry

        # smooth outputs
        n['sm_on'] = add_plug(n['c_sw'], 'smooth', float, k=1, min_value=0, max_value=1, nice_name='Smooth')
        n['sm_off'] = connect_reverse(n['sm_on'])

        # arc dirty hack :)
        add_plug(n['c_sw'], 'arc', float, k=1, min_value=0, max_value=1, nice_name='Arc')

        arcmax = 180 - n['c_2'].find('transform/joint_orient_rotate').x.get_value()
        arcd = abs(n['c_2'].find('transform/translate').y.get_value()) / 2
        add_plug(n['j_2'], 'arc')
        _r = create_srt_out(n['j_2']).find('rotate')
        arceff = connect_driven_curve(_r.x, n['j_2'].arc, {0: 0, arcmax: arcd})

        arct = connect_mult(arceff.result, n['c_sw'].arc)

        _srt1 = n['root_1bd'].find('transform')
        _srt2 = kl.SRTToTransformNode(n['root_1bd'], 'offset')
        _offset = kl.FloatToV3f(_srt2, 'translate')
        _srt2.translate.connect(_offset.vector)
        _mmx = kl.MultM44f(n['root_1bd'], '_mmx')
        _mmx.input[0].connect(_srt2.transform)
        _mmx.input[1].connect(_srt1.transform)
        n['root_1bd'].transform.disconnect(restore_default=False)
        n['root_1bd'].transform.connect(_mmx.output)
        _offset.z.connect(arct)

        _srt1 = n['root_2bd'].find('transform')
        _srt2 = kl.SRTToTransformNode(n['root_2bd'], 'offset')
        _offset = kl.FloatToV3f(_srt2, 'translate')
        _srt2.translate.connect(_offset.vector)
        _mmx = kl.MultM44f(n['root_2bd'], '_mmx')
        _mmx.input[0].connect(_srt2.transform)
        _mmx.input[1].connect(_srt1.transform)
        n['root_2bd'].transform.disconnect(restore_default=False)
        n['root_2bd'].transform.connect(_mmx.output)
        _offset.z.connect(arct)

        # shear up
        root_sh_up = duplicate_joint(n['sub_1'], p=n['root_1'], n='root_shear_up')
        n['loc_sh_up'] = duplicate_joint(n['sub_1'], p=root_sh_up, n='loc_shear_up')

        srt = kl.TransformToSRTNode(n['loc_sh_up'], 'srt')
        srt.transform.connect(n['loc_sh_up'].transform)
        qe = kl.EulerToQuatf(srt, '_euler')
        qe.rotate.connect(srt.rotate)
        qe.rotate_order.connect(srt.rotate_order)
        q = kl.QuatfToFloat(qe, '_quat')
        q.quat.connect(qe.quat)
        n['shx_up'] = q.i
        n['shz_up'] = connect_mult(q.k, -1)

        add_plug(n['c_1'], 'qx', float)
        add_plug(n['c_1'], 'qy', float)
        add_plug(n['c_1'], 'qz', float)
        n['c_1'].qx.connect(q.i)
        n['c_1'].qy.connect(q.j)
        n['c_1'].qz.connect(q.k)

        # shear mid
        n['root_sh_m'] = duplicate_joint(n['sub_2'], p=n['sub_1'], n='root_shear_m')
        n['loc_sh_m'] = duplicate_joint(n['sub_2'], p=n['root_sh_m'], n='loc_shear_m')

        srt = kl.TransformToSRTNode(n['loc_sh_m'], 'srt')
        srt.transform.connect(n['loc_sh_m'].transform)
        qe = kl.EulerToQuatf(srt, '_euler')
        qe.rotate.connect(srt.rotate)
        qe.rotate_order.connect(srt.rotate_order)
        q = kl.QuatfToFloat(qe, '_quat')
        q.quat.connect(qe.quat)
        n['shx_m'] = q.i
        n['shz_m'] = connect_mult(q.k, -1)

        add_plug(n['c_2'], 'qx', float)
        add_plug(n['c_2'], 'qy', float)
        add_plug(n['c_2'], 'qz', float)
        n['c_2'].qx.connect(q.i)
        n['c_2'].qy.connect(q.j)
        n['c_2'].qz.connect(q.k)

        # shear dn
        root_sh_dn = duplicate_joint(n['sub_2'], p=n['sub_e'], n='root_shear_dn')
        copy_transform(tpl_limb3, root_sh_dn, t=1)
        n['loc_sh_dn'] = duplicate_joint(root_sh_dn, p=root_sh_dn, n='loc_shear_dn')

        srt = kl.TransformToSRTNode(n['loc_sh_dn'], 'srt')
        srt.transform.connect(n['loc_sh_dn'].transform)
        qe = kl.EulerToQuatf(srt, '_euler')
        qe.rotate.connect(srt.rotate)
        qe.rotate_order.connect(srt.rotate_order)
        q = kl.QuatfToFloat(qe, '_quat')
        q.quat.connect(qe.quat)
        n['shx_dn'] = q.i
        n['shz_dn'] = connect_mult(q.k, -1)

        add_plug(n['c_e'], 'qx', float)
        add_plug(n['c_e'], 'qy', float)
        add_plug(n['c_e'], 'qz', float)
        n['c_e'].qx.connect(q.i)
        # n['c_e'].qy.connect(q.j)
        n['c_e'].qz.connect(q.k)

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
            jend = duplicate_joint(jdup, p=jdup, n=jdup.get_name().split(':')[-1].replace('sk_', 'end_'))
            copy_transform(jpos, jend, t=1)

        for i, sk in enumerate(splits_up[0][:-1]):
            do_limb_twist_end(splits_up[0][i], splits_up[0][i + 1])
        for i, sk in enumerate(splits_dn[0][:-1]):
            do_limb_twist_end(splits_dn[0][i], splits_dn[0][i + 1])
        do_limb_twist_end(splits_up[0][-1], splits_dn[0][0])
        do_limb_twist_end(splits_dn[0][-1], n['c_e'])

        # fix effector qy
        srt = kl.TransformToSRTNode(n['j_tw_dn'], 'srt')
        srt.transform.connect(n['j_tw_dn'].transform)
        qe = kl.EulerToQuatf(srt, '_euler')
        qe.rotate.connect(srt.rotate)
        qe.rotate_order.connect(srt.rotate_order)
        q = kl.QuatfToFloat(qe, '_quat')
        q.quat.connect(qe.quat)

        n['c_e'].qy.connect(q.j)

        # rollbones
        if self.get_opt('blend_joints'):

            rb_limb1 = n['root_1']
            if self.do_clavicle:
                rb_limb1 = n['inf_clav']
            n['rb1'] = create_blend_joint(splits_up[0][0].get_parent(), rb_limb1, n='sk_' + n_limb1 + '_blend' + n_end)
            rb2 = create_blend_joint(splits_dn[0][0].get_parent(), splits_up[0][-1].get_parent(), n='root_' + n_limb2 + '_blend' + n_end)
            n['rbe'] = create_blend_joint(n['sk_e'], splits_dn[0][-1].get_parent(), n='sk_' + n_eff + '_blend' + n_end)

            point_constraint((rb_limb1, n['sub_1']), n['rb1'])

            n['rb2'] = duplicate_joint(n['sub_2'], p=n['sub_2'], n='sk_' + n_limb2 + '_blend' + n_end)
            n['rb2'].reparent(rb2)

            _srt = create_srt_in(n['rb2'])
            connect_expr(
                's = (s1 + s2) * 0.5',
                s=_srt.scale,
                s1=find_srt(n['c_1']).scale,
                s2=find_srt(n['c_2']).scale
            )
            # _srt.find('scale').y.connect(splits_dn[0][0].stretch)
            # _srt.find('scale').x.connect(splits_dn[0][0].squash)
            # _srt.find('scale').z.connect(splits_dn[0][0].squash)

            pc = point_constraint((n['loc_2pt_up'], n['loc_2pt_dn'], n['p2_pt']), rb2)
            pc.w0.connect(n['sm_off'])
            pc.w1.connect(n['sm_off'])
            connect_mult(n['sm_on'], 2, pc.w2)

        # activate ik
        n['c_sw'].ik_blend.set_value(1)

        # channels
        for c in (n['c_2'], n['c_e'], n['c_dg']):
            for dim in 'xyz':
                set_plug(c.find('transform/translate').get_plug(dim), k=0, lock=True)

        for c in (n['c_2pt'], n['c_1bd'], n['c_2bd']):
            for dim in 'xyz':
                set_plug(c.find('transform/rotate').get_plug(dim), k=0, lock=True)
                set_plug(c.find('transform/scale').get_plug(dim), k=0, lock=True)

        set_plug(n['c_1'].find('transform/scale').y, min_value=0.01)
        set_plug(n['c_2'].find('transform/scale').y, min_value=0.01)

        set_plug(n['c_e'].find('transform/scale').x, min_value=0.01)
        set_plug(n['c_e'].find('transform/scale').y, min_value=0.01)
        set_plug(n['c_e'].find('transform/scale').z, min_value=0.01)

        # rotate orders
        self.build_rotate_order()

        # space switch
        if self.get_opt('space_switch'):
            self.build_space_mods()

        # common switch shape
        for c in ('c_clav', 'c_1', 'c_2', 'c_e', 'c_eIK', 'c_dg', 'c_1bd', 'c_2bd', 'c_2pt'):
            if c in n:
                for plug in ('ik_blend', 'arc', 'smooth', 'twist_fix', 'twist_fix_up', 'twist_fix_dn', 'twist_unroll'):
                    sw_plug = n['c_sw'].get_dynamic_plug(plug)
                    if sw_plug:
                        plug = add_plug(n[c], plug, float, k=1)
                        plug.connect(sw_plug)

        # ui functions
        add_plug(n['c_eIK'], 'menu_offset_pivot', kl.Unit)

        # vis group
        grp = mk.Group.create('{} shape{}'.format(self.name, self.get_branch_suffix(' ')))
        for c in ('c_1bd', 'c_2bd', 'c_2pt'):
            grp.add_member(n[c])
        self.set_id(grp.node, 'vis.shape')

        n['c_eIK_offset'].show.set_value(False)
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
                self.set_id(j.get_parent(), 'roots.up{}.{}'.format(id_chain[s], i))
            self.set_id(splits[-1], 'skin.last{}.up'.format(id_chain[s]))
        for s, splits in enumerate(splits_dn):
            for i, j in enumerate(splits):
                self.set_id(j, 'skin.dn{}.{}'.format(id_chain[s], i))
                self.set_id(j.get_parent(), 'roots.dn{}.{}'.format(id_chain[s], i))
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
        self.set_id(n['root_eIK'], 'roots.effector')
        self.set_id(n['root_eIK_offset'], 'roots.effector_offset')

        self.set_id(n['end_dg'], 'tip')

        # ui ik/fk match
        ui_ikfk = kl.Node(n['c_eIK'], 'ui_match_ikfk')
        ui_plug = add_plug(ui_ikfk, 'ui', kl.Unit)

        for c in (n['c_eIK'], n['c_1'], n['c_2'], n['c_e']):
            plug = add_plug(c, 'ui_match_ikfk', kl.Unit)
            plug.connect(ui_plug)

        add_plug(ui_ikfk, 'switch', float)
        add_plug(ui_ikfk, 'twist', float)
        add_plug(ui_ikfk, 'ik', str)
        add_plug(ui_ikfk, 'fk', str, array=True, size=3)

        add_plug(ui_ikfk, 'twist_factor', float, default_value=(1, -1)[self.do_flip()])

        ui_ikfk.switch.connect(n['c_sw'].ik_blend)
        ui_ikfk.twist.connect(n['c_eIK'].twist)

        ui_ikfk.ik.connect(n['c_eIK'].gem_id)
        ui_ikfk.fk[0].connect(n['c_1'].gem_id)
        ui_ikfk.fk[1].connect(n['c_2'].gem_id)
        ui_ikfk.fk[2].connect(n['c_e'].gem_id)

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

        n['root_clav'] = kl.Joint(hook, 'root_' + n_clav + n_end)
        copy_transform(tpl_clav, n['root_clav'], t=1)
        self.set_id(n['root_clav'], 'roots.clavicle')

        n['c_clav'] = kl.Joint(n['root_clav'], 'c_' + n_clav + n_end)
        n['tip_clav'] = kl.Joint(n['c_clav'], 'j_' + n_clav + '_tip' + n_end)
        copy_transform(n['c_1'], n['tip_clav'], t=1)

        aim_axis = self.get_branch_opt('aim_axis')
        up_axis = self.get_branch_opt('up_axis')
        orient_joint((n['c_clav'], n['tip_clav']), aim=aim_axis, up=up_axis, up_dir=[0, -1, 0])

        # conform orient?
        up_axis_vector = axis_to_vector(up_axis)
        a0 = up_axis_vector * n['c_1'].world_transform.get_value()
        a1 = up_axis_vector * n['c_clav'].world_transform.get_value()
        d = a0.dot(a1)
        if d < 0:
            orient_joint((n['c_clav'], n['tip_clav']), aim=aim_axis, up=up_axis, up_dir=[0, 0, 1])

        # rig clav
        n['root_clav'].scale_compensate.set_value(False)

        n['j_clav'] = n['c_clav']
        if self.do_clavicle_auto:
            n['j_clav'].rename('j_' + n_clav + n_end)
            n['c_clav'] = duplicate_joint(n['j_clav'], n='c_' + n_clav + n_end)

            n['srt_clav'] = duplicate_joint(n['j_clav'], n='srt_' + n_clav + n_end)
            n['srt_clav'].transform.connect(n['c_clav'].transform)
        self.set_id(n['j_clav'], 'j.clavicle')

        _srt = create_srt_in(n['c_clav'], k=1)
        if self.do_clavicle_auto:
            p = point_constraint(n['c_clav'], n['j_clav'])
            merge_transform(n['j_clav'], s_in=_srt.transform)

            eff_ik = create_ik_handle([n['j_clav'], n['tip_clav']])
            ik = eff_ik.find('ik')
            p_srt = p.find('srt')
            ik.translate_root_in.connect(p_srt.translate)

            pv = kl.SceneGraphNode(n['c_clav'], 'pv_' + n_clav + n_end)
            pv.transform.set_value(M44f(V3f(1, 0, 0), V3f(0, 0, 0), V3f(1, 1, 1), Euler.XYZ))
            pv_xfo = pv.world_transform.get_value()
            pv_xfo *= n['c_clav'].world_transform.get_value().inverse()
            ik.initial_root_pole_vector_in.set_value(pv_xfo)
            ik.world_pole_vector_in.connect(pv.world_transform)

            reparent_ik_handle(eff_ik, n['c_clav'])

            create_srt_out(n['j_clav'], joint_orient=True)

        # auto translate rig
        n['inf_clav'] = duplicate_joint(n['tip_clav'], p=n['root_clav'], n='inf_' + n_clav + n_end)
        n['sk_clav'] = duplicate_joint(n['j_clav'], p=n['inf_clav'], n='sk_' + n_clav + n_end)
        n['end_clav'] = duplicate_joint(n['tip_clav'], p=n['sk_clav'], n='end_' + n_clav + n_end)

        n['c_clav'].scale_compensate.set_value(False)
        n['inf_clav'].scale_compensate.set_value(False)
        n['sk_clav'].scale_compensate.set_value(False)

        # connect inf clav
        point_constraint(n['tip_clav'], n['inf_clav'])
        point_constraint(n['tip_clav'], n['root_1'])

        merge_transform(n['inf_clav'], s_in=_srt.transform)

        # blend clav
        _bt = kl.BlendTransformsNode(n['inf_clav'], '_blend_transforms')
        _bt.transform2_in.set_value(n['inf_clav'].transform.get_value())
        _bt.shortest_in.set_value(True)

        _sk = kl.SceneGraphNode(n['inf_clav'].get_parent(), '_target')
        _sk.set_world_transform(n['inf_clav'].world_transform.get_value())

        _oc = orient_constraint([n['j_clav']], _sk)

        _quat = kl.EulerToQuatf(n['j_clav'], '_quat')
        _quat.rotate.connect(_srt.rotate)
        _quat.rotate_order.connect(_srt.rotate_order)
        _qf = kl.QuatfToFloat(_quat, '_quatf')
        _qf.quat.connect(_quat.quat)
        _fq = kl.FloatToQuatf(_qf, '_fquat')
        _fq.j.connect(_qf.j)
        _fq.r.connect(_qf.r)
        _qx = kl.QuatfToM44f(_quat, '_quat_xfo')
        _qx.quat.connect(_fq.quat)
        # TODO: convertir la transfo avec un Quat to Euler
        _qeuler = kl.TransformToSRTNode(_qx, '_qeuler')
        _qeuler.transform.connect(_qx.transform)
        _qxfo = kl.SRTToJointTransform(_qeuler, '_qsrt')
        _qxfo.rotate.connect(_qeuler.rotate)
        _qxfo.joint_orient_rotate.set_value(n['inf_clav'].find('transform').joint_orient_rotate.get_value())
        _qxfo.joint_orient_rotate_order.set_value(n['inf_clav'].find('transform').joint_orient_rotate_order.get_value())

        _bt.transform2_in.connect(_qxfo.transform)
        _bt.transform1_in.connect(_oc.constrain_transform)

        dv = Prefs.get('template/common.limb/default_auto_translate', 0)
        plug = add_plug(n['c_clav'], 'auto_translate', float, min_value=0, max_value=1, default_value=dv, k=1, nice_name='Auto Translate')
        _bt.blend_in.connect(plug)

        _srt_inf = kl.JointTransformToSRT(_bt, '_srt')
        _srt_inf.joint_orient.set_value(n['inf_clav'].find('transform').joint_orient_rotate.get_value())
        _srt_inf.joint_orient_rotate_order.set_value(n['inf_clav'].find('transform').joint_orient_rotate_order.get_value())
        _srt_inf.transform.connect(_bt.transform_out)

        plug_in = n['inf_clav'].find('transform').rotate
        plug_in.connect(_srt_inf.rotate)

        if self.do_clavicle_auto:
            n['ao_clav'] = kl.Joint(n['root_clav'], 'j_' + n_clav + '_AO' + n_end)
            n['eff_clav'] = kl.Joint(n['ao_clav'], 'tip_' + n_clav + '_AO' + n_end)
            copy_transform(tpl_clav, n['ao_clav'], t=1)
            copy_transform(n['c_2'], n['eff_clav'], t=1)

            orient_joint((n['ao_clav'], n['eff_clav']), aim=aim_axis, up=up_axis, up_dir=[0, 1, 0])

            _y = create_srt_in(n['eff_clav']).find('translate').y
            _y.set_value(_y.get_value() / 3.0)

            n['o_clav'] = duplicate_joint(n['root_clav'], p=n['ao_clav'], n='o_' + n_clav + n_end)
            self.set_id(n['o_clav'], 'o.clav')
            n['c_clav'].reparent(n['o_clav'])

            n['ao_1'] = duplicate_joint(n['c_1'], p=n['srt_clav'], n='j_' + n_limb1 + '_AO' + n_end)

            n['ao_2'] = duplicate_joint(n['c_2'], p=n['ao_1'], n='j_' + n_limb2 + '_AO' + n_end)
            n['ao_e'] = duplicate_joint(n['c_e'], p=n['ao_2'], n='j_' + n_eff + 'AO' + n_end)

            n['ik_ao'] = create_ik_handle([n['ao_1'], n['ao_2'], n['ao_e']])

            n['loc0_ao'] = kl.SceneGraphNode(n['root_clav'], 'loc_' + n_clav + '_orig_AO' + n_end)
            copy_transform(n['eff_clav'], n['loc0_ao'], t=1)

            n['ik_clav'] = create_ik_handle([n['ao_clav'], n['eff_clav']])

            plug = add_plug(n['c_clav'], 'auto_orient', float, min_value=0, max_value=1, default_value=0, k=1, nice_name='Auto Orient')

            _pt = point_constraint([n['loc0_ao'], n['ao_2'], ], n['ik_clav'])
            _pt.w1.connect(plug)
            connect_reverse(plug, _pt.w0)

    def build_reverse_lock(self):
        n = self.n

        n_eff = self.get_name('effector')
        n_digits = self.get_name('digits')
        n_heel = self.get_name('heel')
        n_end = self.get_branch_suffix()

        do_bank = self.get_opt('bank')

        # scale pivot
        n['s_eIK'] = kl.SceneGraphNode(n['c_eIK_offset'], 's_' + n_eff + '_IK' + n_end)
        pos_xz = n['c_e'].world_transform.get_value().translation()
        pos_xz += n['c_dg'].world_transform.get_value().translation()
        pos_xz /= 2
        pos_y = n['end_dg'].world_transform.get_value().translation()
        xfo = n['s_eIK'].world_transform.get_value()
        xfo = M44f(V3f(pos_xz.x, pos_y.y, pos_xz.z), xfo.rotation(Euler.XYZ), xfo.scaling(), Euler.XYZ)
        n['s_eIK'].set_world_transform(xfo)

        add_plug(n['c_eIK'], 'stomp', float, k=1, min_value=-1, max_value=1, nice_name='Stomp')
        _pow = kl.Pow(n['s_eIK'], '_stomp_pow')
        add_plug(n['c_eIK'], 'stomp_power', float, default_value=-0.5, min_value=-1, max_value=0, nice_name='Stomp Power')
        n['c_eIK'].stomp_power.set_value(self.get_opt('stomp_power'))
        _pow.input2.connect(n['c_eIK'].stomp_power)
        _pow.input1.set_value(1)
        _stomp = connect_driven_curve(n['c_eIK'].stomp, _pow.input1, {0: 1, 1: 0.1, -1: 2}, pre='constant', tangent_mode='linear')

        dim0 = self.get_opt('up_axis').strip('-')
        dim1 = self.get_opt('aim_axis').strip('-')
        dim2 = self.get_opt('up_axis2').strip('-')
        if self.get_opt('effector_plane') == 'z':
            dim0, dim1, dim2 = dim2, dim0, dim1

        _stompv = {}
        _stompv[dim0] = _pow.output
        _stompv[dim1] = _stomp.result
        _stompv[dim2] = _pow.output

        _srt = create_srt_in(n['s_eIK'], vectors=True)
        _s = _srt.find('scale')
        _s.x.connect(_stompv['x'])
        _s.y.connect(_stompv['y'])
        _s.z.connect(_stompv['z'])

        n['s_e'] = kl.SceneGraphNode(n['root_e'], 's_' + n_eff + n_end)
        _srt = create_srt_in(n['s_e'], vectors=False)
        _ox = orient_constraint(n['c_eIK_offset'], n['s_e'])

        _s1 = n['c_eIK'].find('transform/scale')
        _s2 = n['c_eIK_offset'].find('transform/scale')
        _s_x = connect_mult(_s1.x, _s2.x, p=n['s_e'])
        _s_y = connect_mult(_s1.y, _s2.y, p=n['s_e'])
        _s_z = connect_mult(_s1.z, _s2.z, p=n['s_e'])
        _mult_x = connect_mult(_stompv['x'], _s_x, p=n['s_e'])
        _mult_y = connect_mult(_stompv['y'], _s_y, p=n['s_e'])
        _mult_z = connect_mult(_stompv['z'], _s_z, p=n['s_e'])
        _b = kl.BlendV3f(n['s_e'], '_blend')
        _b2 = kl.FloatToV3f(_b, 'input2')
        _b.input2.connect(_b2.vector)
        _b2.x.connect(_mult_x)
        _b2.y.connect(_mult_y)
        _b2.z.connect(_mult_z)
        _b.input1.set_value(V3f(1, 1, 1))
        _b.weight.connect(n['ik'].blend)
        _srt.scale.connect(_b.output)

        n['neg_e'] = kl.SceneGraphNode(n['s_e'], 'rev_' + n_eff + n_end)
        _imx = kl.InverseM44f(_ox, '_imx')
        _imx.input.connect(_ox.constrain_transform)
        n['neg_e'].transform.connect(_imx.output)

        n['c_e'].reparent(n['neg_e'])

        # reverse IK skeleton
        n['j_ehIK'] = kl.Joint(n['s_eIK'], 'j_' + n_heel + '_IK' + n_end)
        n['j_eeIK'] = kl.Joint(n['j_ehIK'], 'j_' + n_eff + '_tip_IK' + n_end)
        n['j_eIK'] = kl.Joint(n['j_eeIK'], 'j_' + n_eff + '_IK' + n_end)
        n['j_emIK'] = kl.Joint(n['j_eIK'], 'j_' + n_eff + '_mid_IK' + n_end)
        n['end_emIK'] = kl.Joint(n['j_emIK'], 'end_' + n_eff + '_mid_IK' + n_end)
        n['j_dgIK'] = kl.Joint(n['j_eIK'], 'j_' + n_digits + '_IK' + n_end)
        n['end_dgIK'] = kl.Joint(n['j_dgIK'], 'end_' + n_digits + '_IK' + n_end)

        copy_transform(self.get_structure('heel')[0], n['j_ehIK'], t=True)
        copy_transform(n['end_dg'], n['j_eeIK'], t=True)
        copy_transform(n['c_dg'], n['j_eIK'], t=True)
        copy_transform(n['c_dg'], n['j_emIK'], t=True)
        copy_transform(n['c_e'], n['end_emIK'], t=True)
        copy_transform(n['c_dg'], n['j_dgIK'], t=True)
        copy_transform(n['end_dg'], n['end_dgIK'], t=True)

        if do_bank:
            n['j_bint'] = kl.Joint(n['j_eIK'], 'j_' + n_eff + '_bank_int_IK' + n_end)
            n['j_bext'] = kl.Joint(n['j_bint'], 'j_' + n_eff + '_bank_ext_IK' + n_end)

            tpl_dig = self.get_structure('digits')[0]
            tpl_bank_int = self.get_structure('bank_int')
            tpl_bank_ext = self.get_structure('bank_ext')

            if not tpl_bank_int:
                tpl_bank_int = kl.Joint(tpl_dig, 'tpl_bank_int')
                tpl_bank_int.transform.set_value(M44f(V3f(0.5, 0, 0), V3f(0, 0, 0), V3f(1, 1, 1), Euler.XYZ))
                self.set_template_id(tpl_bank_int, 'bank_int')
            else:
                tpl_bank_int = tpl_bank_int[0]

            if not tpl_bank_ext:
                tpl_bank_ext = kl.Joint(tpl_dig, 'tpl_bank_ext')
                tpl_bank_ext.transform.set_value(M44f(V3f(-0.5, 0, 0), V3f(0, 0, 0), V3f(1, 1, 1), Euler.XYZ))
                self.set_template_id(tpl_bank_ext, 'bank_ext')
            else:
                tpl_bank_ext = tpl_bank_ext[0]

            copy_transform(tpl_bank_int, n['j_bint'], t=True)
            copy_transform(tpl_bank_ext, n['j_bext'], t=True)

            n['j_emIK'].reparent(n['j_bext'])
            n['j_dgIK'].reparent(n['j_bext'])

        # rig foot lock holder
        n['loc_lockIK'] = kl.SceneGraphNode(n['c_eIK_offset'], 'loc_' + n_eff + '_lock_IK' + n_end)
        n['loc_lockIK'].reparent(n['s_eIK'])
        point_constraint(n['end_emIK'], n['loc_lockIK'])

        n['loc_lock'] = kl.SceneGraphNode(n['c_2'], 'loc_' + n_eff + '_lock' + n_end)
        _srt = create_srt_in(n['loc_lock'])
        _lock_px = point_constraint(n['loc_lockIK'], n['loc_lock'])
        _srt_out = _lock_px.find('srt')

        _srt_t = kl.FloatToV3f(_srt, 'translate')
        _srt_t_out = kl.V3fToFloat(_srt_out, 'translate')
        _srt_t.x.connect(_srt_t_out.x)
        _srt_t.z.connect(_srt_t_out.z)

        _root_srt = create_srt_out(n['root_e'])
        _root_t = _root_srt.find('translate')

        _if = kl.Condition(_srt, '_if')
        _if_op = kl.IsGreater(_srt, '_isg')
        if _root_t.y.get_value() > 0:
            _not = kl.Not(_srt, '_not')
            _not.input.connect(_if_op.output)
            _if.condition.connect(_not.output)
        else:
            _if.condition.connect(_if_op.output)

        _if_op.input2.connect(_root_t.y)
        _if.input1.connect(_root_t.y)

        _if_op.input1.connect(_srt_t_out.y)
        _if.input2.connect(_srt_t_out.y)
        _srt_t.y.connect(_if.output)

        # --
        n['root_lock'] = kl.SceneGraphNode(n['s_e'], 'root_' + n_eff + '_lock' + n_end)
        _px = point_constraint(n['loc_lock'], n['root_lock'])

        _b = kl.BlendTransformsNode(n['root_lock'], 'blend_transforms')
        _b.transform2_in.connect(_px.constrain_transform)
        n['root_lock'].transform.connect(_b.transform_out)

        add_plug(n['c_sw'], 'lock_stretch', bool)
        _if = kl.Condition(_b, '_b2f')
        _if.condition.connect(n['c_sw'].lock_stretch)
        _if.input1.set_value(1)
        connect_mult(_if.output, n['ik'].blend, _b.blend_in)

        if self.get_opt('reverse_lock'):
            n['c_sw'].lock_stretch.set_value(True)

        n['s_lock'] = kl.SceneGraphNode(n['s_eIK'], 's_' + n_eff + '_lock' + n_end)
        n['s_lock'].reparent(n['root_lock'])

        n['s_lockIK'] = kl.SceneGraphNode(n['loc_lockIK'], 's_' + n_eff + '_lock_IK' + n_end)
        _px = point_constraint(n['s_eIK'], n['s_lockIK'])

        _srt_out = kl.TransformToSRTNode(_px, 'srt')
        _srt_out.transform.connect(_px.constrain_transform)
        _srt = create_srt_in(n['s_lock'])

        _srt.translate.connect(_srt_out.translate)

        # stretch/scale offset
        # --
        n['loc_emIK'] = kl.SceneGraphNode(n['j_dgIK'], 'eff_' + n_eff + '_mid' + n_end)
        n['loc_emIK'].reparent(n['j_emIK'])

        n['loc_dgIK'] = kl.SceneGraphNode(n['end_dgIK'], 'eff_' + n_digits + n_end)
        n['loc_dgIK'].reparent(n['j_dgIK'])

        # IKs
        n['eff_ik_em'] = create_ik_handle([n['c_e'], n['root_dg']], parent=n['s_lock'])
        n['ik_em'] = n['eff_ik_em'].find('ik')
        c_srt = n['c_e'].find('transform')
        n['ik_em'].translate_root_in.connect(c_srt.translate)

        mmx = kl.MultM44f(n['eff_ik_em'], '_mmx')
        mmx.input[0].connect(n['loc_emIK'].world_transform)
        imx = kl.InverseM44f(n['eff_ik_em'], '_imx')
        imx.input.connect(n['s_eIK'].world_transform)
        mmx.input[1].connect(imx.output)
        n['eff_ik_em'].transform.connect(mmx.output)

        pv = kl.SceneGraphNode(n['eff_ik_em'], 'pv_' + n_eff + '_mid' + n_end)
        if self.get_opt('reverse_lock'):
            if self.get_opt('effector_plane') == 'z':
                pv.transform.set_value(M44f(V3f(0, 0, 1), V3f(0, 0, 0), V3f(1, 1, 1), Euler.XYZ))
            else:
                pv.transform.set_value(M44f(V3f(0, 1, 0), V3f(0, 0, 0), V3f(1, 1, 1), Euler.XYZ))
        else:
            pv.transform.set_value(M44f(V3f(1, 0, 1), V3f(0, 0, 0), V3f(1, 1, 1), Euler.XYZ))
        pv_xfo = pv.world_transform.get_value()
        pv_xfo *= n['c_e'].world_transform.get_value().inverse()
        n['ik_em'].initial_root_pole_vector_in.set_value(pv_xfo)
        n['ik_em'].world_pole_vector_in.connect(pv.world_transform)

        # --
        n['eff_ik_dg'] = create_ik_handle([n['c_dg'], n['end_dg']], parent=n['s_lock'])
        n['ik_dg'] = n['eff_ik_dg'].find('ik')

        mmx = kl.MultM44f(n['eff_ik_dg'], '_mmx')
        mmx.input[0].connect(n['loc_dgIK'].world_transform)
        imx = kl.InverseM44f(n['eff_ik_dg'], '_imx')
        imx.input.connect(n['s_eIK'].world_transform)
        mmx.input[1].connect(imx.output)
        n['eff_ik_dg'].transform.connect(mmx.output)

        pv = kl.SceneGraphNode(n['eff_ik_dg'], 'pv_' + n_eff + '_mid' + n_end)
        if self.get_opt('reverse_lock'):
            if self.get_opt('effector_plane') == 'z':
                pv.transform.set_value(M44f(V3f(0, 0, 1), V3f(0, 0, 0), V3f(1, 1, 1), Euler.XYZ))
            else:
                pv.transform.set_value(M44f(V3f(0, 1, 0), V3f(0, 0, 0), V3f(1, 1, 1), Euler.XYZ))
        else:
            pv.transform.set_value(M44f(V3f(1, 0, 1), V3f(0, 0, 0), V3f(1, 1, 1), Euler.XYZ))
        pv_xfo = pv.world_transform.get_value()
        pv_xfo *= n['c_dg'].world_transform.get_value().inverse()
        n['ik_dg'].initial_root_pole_vector_in.set_value(pv_xfo)
        n['ik_dg'].world_pole_vector_in.connect(pv.world_transform)
        # todo: scale in et root translate des 2 iks

    def build_reverse_lock_poses(self):
        n = self.n

        n_eff = self.get_name('effector')
        n_digits = self.get_name('digits')
        n_heel = self.get_name('heel')

        do_bank = self.get_opt('bank')

        add_plug(n['c_eIK'], n_eff + '_roll', float, k=1, min_value=-1, max_value=1, nice_name=n_eff.capitalize() + ' Roll')
        add_plug(n['c_eIK'], n_heel + '_roll', float, k=1, min_value=-1, max_value=1, nice_name=n_heel.capitalize() + ' Roll')
        add_plug(n['c_eIK'], 'ball_roll', float, k=1, min_value=-1, max_value=1, nice_name='Ball Roll')
        add_plug(n['c_eIK'], n_digits + '_roll', float, k=1, min_value=-1, max_value=1, nice_name=n_digits.capitalize() + ' Roll')
        add_plug(n['c_eIK'], n_heel + '_pivot', float, k=1, min_value=-1, max_value=1, nice_name=n_heel.capitalize() + ' Pivot')
        add_plug(n['c_eIK'], 'ball_pivot', float, k=1, min_value=-1, max_value=1, nice_name='Ball Pivot')
        add_plug(n['c_eIK'], n_digits + '_pivot', float, k=1, min_value=-1, max_value=1, nice_name=n_digits.capitalize() + ' Pivot')
        if do_bank:
            add_plug(n['c_eIK'], 'bank', k=1, min_value=-1, max_value=1, nice_name='Bank')

        sw = n['sw'][0]
        add_plug(sw, 'roll_amp', float, k=1, default_value=90)
        add_plug(sw, 'roll_offset_roll', float, k=1)
        add_plug(sw, 'roll_offset_mid_roll', float, k=1)
        add_plug(sw, 'roll_offset_height', float, k=1)
        add_plug(sw, 'roll_offset_depth', float, k=1)
        add_plug(sw, 'pivot_amp', float, k=1, default_value=90)
        if do_bank:
            add_plug(sw, 'bank_amp', float, k=1, default_value=90)

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

        ro = str_to_rotate_order(dim0 + dim1 + dim2)
        create_srt_in(n['j_ehIK'], ro=ro)
        create_srt_in(n['j_emIK'], ro=ro)
        create_srt_in(n['j_eIK'], ro=ro)
        create_srt_in(n['j_dgIK'], ro=ro)
        create_srt_in(n['j_eeIK'], ro=ro)
        if do_bank:
            create_srt_in(n['j_bint'], ro=ro)
            create_srt_in(n['j_bext'], ro=ro)

        plugs = {
            'h0': n['j_ehIK'].find('transform/rotate').get_plug(dim0), 'e0': n['j_emIK'].find('transform/rotate').get_plug(dim0),
            'm0': n['j_dgIK'].find('transform/rotate').get_plug(dim0), 't0': n['j_eeIK'].find('transform/rotate').get_plug(dim0),
            'h1': n['j_ehIK'].find('transform/rotate').get_plug(dim1), 'e1': n['j_emIK'].find('transform/rotate').get_plug(dim1),
            'm1': n['j_dgIK'].find('transform/rotate').get_plug(dim1), 't1': n['j_eeIK'].find('transform/rotate').get_plug(dim1),
            'b1': n['j_eIK'].find('transform/rotate').get_plug(dim1),
            'td': n['j_eeIK'].find('transform/translate').get_plug(dim2), 'th': n['j_eeIK'].find('transform/translate').get_plug(dim1),
            'tdv': n['j_eeIK'].find('transform/translate').get_plug(dim2).get_value(), 'thv': n['j_eeIK'].find('transform/translate').get_plug(dim1).get_value(),
            'e_roll': n['c_eIK'].get_dynamic_plug(n_eff + '_roll'), 'h_roll': n['c_eIK'].get_dynamic_plug(n_heel + '_roll'),
            'm_roll': n['c_eIK'].get_dynamic_plug('ball_roll'), 't_roll': n['c_eIK'].get_dynamic_plug(n_digits + '_roll'),
            'h_pvt': n['c_eIK'].get_dynamic_plug(n_heel + '_pivot'), 'm_pvt': n['c_eIK'].get_dynamic_plug('ball_pivot'),
            't_pvt': n['c_eIK'].get_dynamic_plug(n_digits + '_pivot'),
            'amp_roll': sw.get_dynamic_plug('roll_amp'), 'amp_pvt': sw.get_dynamic_plug('pivot_amp'),
            'o_roll': sw.get_dynamic_plug('roll_offset_roll'), 'o_mid_roll': sw.get_dynamic_plug('roll_offset_mid_roll'),
            'o_height': sw.get_dynamic_plug('roll_offset_height'), 'o_depth': sw.get_dynamic_plug('roll_offset_depth')
        }

        if do_bank:
            plugs.update({
                'bkint': n['j_bint'].find('transform/rotate').get_plug(dim2),
                'bkext': n['j_bext'].find('transform/rotate').get_plug(dim2),
                'amp_bk': sw.bank_amp, 'bank': n['c_eIK'].bank
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

        # pv auto rig
        n['ao_pv'] = kl.Joint(n['root_1'], 'j_' + n_limb + '_PV_auto' + n_end)
        n['end_pv'] = kl.Joint(n['ao_pv'], 'end_' + n_limb + '_PV_auto' + n_end)
        copy_transform(n['c_1'], n['ao_pv'], t=1)
        copy_transform(n['c_e'], n['end_pv'], t=1)

        legacy = Prefs.get('template/common.limb/legacy_pv_auto', 1)
        if legacy < 1:
            orient_joint((n['ao_pv'], n['end_pv']), aim='x', aim_dir=[1, 0, 0], up='z', up_dir=[0, 0, 1])
            n['end_pv'].transform.set_value(M44f(V3f(0, -1, 0), V3f(0, 0, 0), V3f(1, 1, 1), Euler.Default))
        else:
            orient_joint((n['ao_pv'], n['end_pv']), aim='-y', aim_dir=[1, 0, 0], up='z', up_dir=[0, 0, 1])
            xfo_ao = n['end_pv'].transform.get_value().translation()

        create_srt_in(n['ao_pv'])

        if not self.get_opt('clavicle'):
            point_constraint(n['eff_root'], n['ao_pv'])
        else:
            n['ao_pv'].reparent(n['root_clav'])

        n['o_pv'] = duplicate_joint(n['ao_pv'], n='root_' + n_limb + '_PV_auto' + n_end)
        n['ao_pv'].reparent(n['o_pv'])

        # pole vector space switch
        pv_space = self.get_opt('pv_space')
        if pv_space:
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
                name = ''
                if '.' in pv_space:
                    name = '_' + pv_space.split('.')[-1]
                plug_name = 'follow' + name

                _oc = orient_constraint(pv_tgt, n['o_pv'], mo=1)

                plug_follow = add_plug(n['c_eIK'], plug_name, float, k=1, default_value=self.get_opt('pv_space_default'), min_value=0, max_value=1)
                _oc.enable_in.connect(plug_follow)

        if legacy < 1:
            aim_constraint(n['end_emIK'], n['ao_pv'], aim_vector=V3f(0, -1, 0), up_vector=V3f(0, 0, 0))
        else:
            aim_constraint(n['end_emIK'], n['ao_pv'], aim_vector=xfo_ao, up_vector=V3f(0, 0, 0))

    def build_pole_vector_follow(self):
        n = self.n

        n_limb = self.get_name('effector')
        n_end = self.get_branch_suffix()

        n['root_pvf'] = kl.Joint(n['c_eIK_offset'], 'root_' + n_limb + '_PV_follow' + n_end)
        n['ao_pvf'] = kl.Joint(n['root_pvf'], 'j_' + n_limb + '_PV_follow' + n_end)
        create_srt_in(n['ao_pvf'])
        n['end_pvf'] = kl.Joint(n['ao_pvf'], 'end_' + n_limb + '_PV_follow' + n_end)

        d = (1, -1)[self.do_flip()]
        # todo: conditionner sur reverse foot

        if not self.get_opt('clavicle'):
            copy_transform(n['c_1'], n['end_pvf'], t=1)
            # orient_joint((n['ao_pvf'], n['end_pvf']), aim='y', up='z', up_dir=[0, 0, 1])
            _x = aim_constraint(n['eff_root'], n['root_pvf'], aim_vector=V3f(0, d, 0), up_vector=V3f(0, 0, 0))
            n['root_pvf'].transform.disconnect(restore_default=False)
            _x.remove_from_parent()
        else:
            copy_transform(n['inf_clav'], n['end_pvf'], t=1)
            # orient_joint((n['ao_pvf'], n['end_pvf']), aim='y', up='z', up_dir=[0, 0, 1])
            _x = aim_constraint(n['inf_clav'], n['root_pvf'], aim_vector=V3f(0, d, 0), up_vector=V3f(0, 0, 0))
            n['root_pvf'].transform.disconnect(restore_default=False)
            _x.remove_from_parent()

        n['end_pvf'].transform.set_value(M44f(V3f(0, d, 0), V3f(0, 0, 0), V3f(1, 1, 1), Euler.Default))

        if not self.get_opt('clavicle'):
            aim_constraint(n['eff_root'], n['ao_pvf'], aim_vector=V3f(0, d, 0), up_vector=V3f(0, 0, 0))
        else:
            aim_constraint(n['root_clav'], n['ao_pvf'], aim_vector=V3f(0, d, 0), up_vector=V3f(0, 0, 0), mo=1)

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
        _srt = create_srt_out(c)
        sqx = connect_mult(_srt.find('scale').x, c.squash)
        sqz = connect_mult(_srt.find('scale').z, c.squash)
        nty = 1

        loc_end = kl.SceneGraphNode(sk, 'loc_' + name + '_tip' + n_end)
        copy_transform(j_tip, loc_end, t=True)

        for i in range(nj + 2):

            # build joints
            if i <= nj:
                for _c in range(nc):
                    j = duplicate_joint(sk, p=sk, n='root_' + name + str(i) + n_chain[_c] + n_end)
                    create_srt_in(j)
                    roots[_c].append(j)

                    j = duplicate_joint(sk, p=roots[_c][-1], n='sk_' + name + str(i) + n_chain[_c] + n_end)
                    sks[_c].append(j)
                    mx = kl.IJKToTransform(j, 'transform')
                    mxs[_c].append(mx)
                    _i = kl.FloatToV3f(mx, 'i')
                    _j = kl.FloatToV3f(mx, 'j')
                    _k = kl.FloatToV3f(mx, 'k')
                    _i.x.set_value(1)
                    _j.y.set_value(1)
                    _k.z.set_value(1)
                    mx.i.connect(_i.vector)
                    mx.j.connect(_j.vector)
                    mx.k.connect(_k.vector)

            # bend points
            if 0 < i <= nj:
                p1 = kl.SceneGraphNode(sk, 'p1_' + name + str(i) + n_end)
                p1s[i] = p1

                if nj > 1:
                    tx = i / ((nj + 1) / 2.) - 1
                    x = 0.7071  # cos(45) dt.cos(dt.Angle(45).asRadians())
                    ty = math.sin(math.acos(tx * x)) - x
                    if i == 1:
                        nty = ty / (1 - abs(tx))
                    w = get_triangle_weights(V3f(tx, ty, 0), V3f(-1, 0, 0), V3f(0, nty, 0), V3f(1, 0, 0))
                    point_constraint((j_base, j_mid, j_tip), p1, weights=w)
                else:
                    point_constraint(j_mid, p1)

            # smooth points
            if 0 < i <= nj or (tw == 'up' and i == nj + 1):
                p2 = kl.SceneGraphNode(n['rig_smooth'], 'p2_' + name + str(i) + n_end)

                _poc = kl.PointOnSplineCurve(p2, '_poc')
                _poc.spline_mesh_in.connect(n['cv_sm'].spline_mesh_out)
                _poc.spline_in.connect(n['cv_sm'].spline_in)
                _poc.geom_world_transform_in.set_value(n['cv_sm'].get_parent().transform.get_value())

                if self.get_opt('smooth_type') == 'length':
                    _poc.length_in.connect(n['cv_sm'].length_out)

                    t1 = n['j_2'].transform.get_value().translation().length()
                    t2 = n['j_e'].transform.get_value().translation().length()
                    m1 = t1 / (t1 + t2)
                    m2 = t2 / (t1 + t2)

                    u = 0
                    if tw == 'up':
                        u = i / float(nj + 1) * m1
                    elif tw == 'dn':
                        u = i / float(nj + 1) * m2 + m1

                    _poc.length_ratio_in.set_value(u)

                else:
                    if i == nj + 1:
                        u = 0.5
                    else:
                        u = get_closest_point_on_curve(n['cv_sm'], p1s[i], parametric=True)

                    _poc.u_in.set_value(u)

                p2.transform.connect(_poc.transform_out)

                if i <= nj:
                    for _c in range(nc):
                        pc = point_constraint((p1s[i], p2), roots[_c][-1])
                        pc.w0.connect(n['sm_off'])
                        pc.w1.connect(n['sm_on'])

                if i == nj + 1:
                    n['p2_pt'] = p2

            # stretch
            if i > 0:
                for _c in range(nc):
                    db = kl.Distance(mxs[_c][i - 1], '_distance')
                    db.input1.connect(roots[_c][i - 1].find('transform').translate)
                    if i <= nj:
                        db.input2.connect(roots[_c][i].find('transform').translate)
                    else:
                        _srt = create_srt_out(loc_end, vectors=False)
                        db.input2.connect(_srt.translate)
                    div = kl.Div(mxs[_c][i - 1], '_div')
                    div.input1.connect(db.output)
                    div.input2.set_value(db.output.get_value())

                    mxs[_c][i - 1].find('j').y.connect(div.output)

                    add_plug(sks[_c][i - 1], 'stretch', float)
                    sks[_c][i - 1].stretch.connect(div.output)

            if i <= nj:
                for _c in range(nc):
                    add_plug(sks[_c][i], 'squash', float)
                    sks[_c][i].squash.connect(sqx)

                    mxs[_c][i].find('i').x.connect(sqx)
                    mxs[_c][i].find('k').z.connect(sqz)

                    sks[_c][i].transform.connect(mxs[_c][i].transform)

        # edge constraints
        if tw == 'up':
            pc = point_constraint((j_tip, n['p2_pt']), loc_end)
            pc.w0.connect(n['sm_off'])
            pc.w1.connect(n['sm_on'])
        else:
            point_constraint(j_tip, loc_end)

        if tw == 'dn':
            for _c in range(nc):
                pc = point_constraint((j_base, n['p2_pt']), roots[_c][0])
                pc.w0.connect(n['sm_off'])
                pc.w1.connect(n['sm_on'])

        # aims
        aim_axis = self.get_branch_opt('aim_axis')
        aim_vector = axis_to_vector(aim_axis)
        for i in range(nj + 1):
            for _c in range(nc):

                if i < nj:
                    aim_constraint(roots[_c][i + 1], roots[_c][i], aim_vector=aim_vector, up_vector=V3f(0, 0, 0))
                else:
                    aim_constraint(loc_end, roots[_c][i], aim_vector=aim_vector, up_vector=V3f(0, 0, 0))

        # update shear rig
        if tw == 'up':
            orient_constraint(roots[0][0], n['loc_sh_up'])
            n['root_sh_m'].reparent(roots[0][-1])
        elif tw == 'dn':
            orient_constraint(roots[0][0], n['loc_sh_m'])
            orient_constraint(roots[0][-1], n['loc_sh_dn'])

        # twists rig
        if tw == 'up':
            j_tw = duplicate_joint(sk, p=p1s[min(p1s)], n='j_' + name + '_twist' + n_end)  # p=roots[1]
            copy_transform(roots[0][1], j_tw, t=1)
            create_srt_out(aim_constraint(c, j_tw, aim_vector=V3f(0, (1, -1)[not aim_axis.startswith('-')], 0), up_vector=V3f(0, 0, 0)))

            end_tw = duplicate_joint(sk, p=j_tw, n='end_' + name + '_twist' + n_end)
            copy_transform(c, end_tw, t=1)
            n['j_tw_up'] = end_tw

            if not self.get_opt('clavicle'):
                tg_tw = kl.Joint(n['root_1'], 'j_' + name + '_twist' + n_end)
                copy_transform(end_tw, tg_tw)
                _srt = create_srt_out(twist_constraint(tg_tw, end_tw), ro=Euler.YZX)
            else:
                tg_tw = kl.Joint(n['j_clav'], 'j_' + name + '_twist' + n_end)
                copy_transform(end_tw, tg_tw)
                _srt = create_srt_out(twist_constraint(tg_tw, end_tw), ro=Euler.YZX)

            add_plug(n['c_sw'], 'twist_up', float, min_value=0, max_value=1, default_value=1)
            n['tw_up'] = connect_mult(_srt.find('rotate').y, n['c_sw'].twist_up)
        elif tw == 'dn':
            j_tw = duplicate_joint(sk, p=p1s[max(p1s)], n='j_' + name + '_twist' + n_end)  # p=roots[1]
            copy_transform(roots[0][-1], j_tw, t=1)
            aim_constraint(n['sub_e'], j_tw, aim_vector=V3f(0, (-1, 1)[not aim_axis.startswith('-')], 0), up_vector=V3f(0, 0, 0))

            end_tw = duplicate_joint(sk, p=j_tw, n='end_' + name + '_twist' + n_end)
            copy_transform(n['sub_e'], end_tw, t=1)
            n['j_tw_dn'] = end_tw

            tg_tw = kl.Joint(n['sub_e'], 'j_' + name + '_twist_target' + n_end)
            copy_transform(end_tw, tg_tw)
            _srt = create_srt_out(twist_constraint(tg_tw, end_tw), ro=Euler.YZX)

            add_plug(n['c_sw'], 'twist_dn', float, min_value=0, max_value=1, default_value=1)
            n['tw_dn'] = connect_mult(_srt.find('rotate').y, n['c_sw'].twist_dn)

        # weights rig
        for _c in range(nc):

            for i in range(nj + 1):
                _attr = 'twist_{}_{}'.format(tw, i)
                add_plug(n['sw'][_c], _attr, float, min_value=0, max_value=1)

            for i in range(nj + 1):
                _attr = 'shear_{}_base_{}'.format(tw, i)
                add_plug(n['sw'][_c], _attr, float, min_value=0, max_value=2)

            for i in range(nj + 1):
                _attr = 'shear_{}_tip_{}'.format(tw, i)
                add_plug(n['sw'][_c], _attr, float, min_value=0, max_value=2)

            for i in range(nj + 1):
                _twist = n['sw'][_c].get_dynamic_plug('twist_{}_{}'.format(tw, i))
                _shear_base = n['sw'][_c].get_dynamic_plug('shear_{}_base_{}'.format(tw, i))
                _shear_tip = n['sw'][_c].get_dynamic_plug('shear_{}_tip_{}'.format(tw, i))

                _srt_in = find_srt(roots[_c][i])
                _srt = kl.SRTToTransformNode(roots[_c][i], 'offset')
                _r = kl.FloatToEuler(_srt, 'rotate')
                _srt.rotate.connect(_r.euler)
                _r.rotate_order.connect(_srt.rotate_order)

                _mmx = kl.MultM44f(_srt_in, '_mmx')
                _mmx.input[0].connect(_srt.transform)
                _mmx.input[1].connect(_srt_in.transform)
                roots[_c][i].transform.connect(_mmx.output)

                if tw == 'up':
                    _twist.set_value((nj - i) / (nj + 1.))
                    connect_mult(n['tw_up'], _twist, _r.y)

                    connect_mult(_shear_base, n['shz_up'], mxs[_c][i].find('i').y)
                    connect_expr('x = b*up + t*-m', x=mxs[_c][i].find('k').y, b=_shear_base, t=_shear_tip, up=n['shx_up'], m=n['shx_m'])
                else:
                    _twist.set_value(float(i) / nj)
                    connect_mult(n['tw_dn'], _twist, _r.y)

                    connect_mult(_shear_tip, n['shz_dn'], mxs[_c][i].find('i').y)
                    connect_expr('x = b*m + t*dn', x=mxs[_c][i].find('k').y, b=_shear_base, t=_shear_tip, m=n['shx_m'], dn=n['shx_dn'])

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
        if isinstance(chain, str):
            chain = [chain]

        chain = ['c' + str(c) if not isinstance(c, str) else c for c in chain]
        chain = [''] + chain
        return chain


# misc math ------------------------------------------------------------------------------------------------------------

def get_triangle_weights(p, v0, v1, v2):
    p0 = project_vector(v0, p, v1, v2)
    p1 = project_vector(v1, p, v0, v2)
    p2 = project_vector(v2, p, v0, v1)

    w0 = (p0 - p).length() / (p0 - v0).length()
    w1 = (p1 - p).length() / (p1 - v1).length()
    w2 = (p2 - p).length() / (p2 - v2).length()

    return w0, w1, w2


def project_vector(u1, u2, v1, v2):
    uv1 = v1 + project(u1 - v1, v2 - v1)
    uv2 = v1 + project(u2 - v1, v2 - v1)

    l = (uv1 - u1).length()
    f = l / project(u2 - u1, uv1 - u1).length()

    return uv1 + (uv2 - uv1) * f


def project(a, b):
    return b * (a.dot(b) / (b.length() ** 2))
