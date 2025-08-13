# coding: utf-8

import math

import meta_nodal_py as kl
from meta_nodal_py.Imath import V3f, M44f, Euler

import mikan.tangerine.core as mk
from mikan.tangerine.lib.commands import *
from mikan.tangerine.lib.connect import *
from mikan.tangerine.lib.rig import *
from mikan.templates.template._common.limb.tangerine import get_triangle_weights

from mikan.core.logger import create_logger

log = create_logger()


class Template(mk.Template):

    def build_template(self, data):
        tpl_limb1 = self.node

        tpl_limb2 = kl.Joint(tpl_limb1, 'tpl_leg2')
        tpl_limb3 = kl.Joint(tpl_limb2, 'tpl_ankle_quad')
        tpl_eff = kl.Joint(tpl_limb3, 'tpl_foot')
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
        tpl_limb2.transform.set_value(M44f(V3f(0, 2.645, 0.25), V3f(0, 0, 0), V3f(1, 1, 1), Euler.XYZ))
        tpl_limb3.transform.set_value(M44f(V3f(0, 2.595, -1.25), V3f(0, 0, 0), V3f(1, 1, 1), Euler.XYZ))
        tpl_eff.transform.set_value(M44f(V3f(0, 2.759, 0), V3f(90, 0, 0), V3f(1, 1, 1), Euler.XYZ))
        tpl_dig.transform.set_value(M44f(V3f(0, 1.5, -1.5), V3f(0, 0, 0), V3f(1, 1, 1), Euler.XYZ))
        tpl_dig_end.transform.set_value(M44f(V3f(0, 1, 0), V3f(0, 0, 0), V3f(1, 1, 1), Euler.XYZ))

        tpl_clav.transform.set_value(M44f(V3f(0.5, 0, 0), V3f(0, 0, 0), V3f(1, 1, 1), Euler.XYZ))
        tpl_heel.transform.set_value(M44f(V3f(0, 0, -1.5), V3f(0, 0, 0), V3f(1, 1, 1), Euler.XYZ))

        tpl_bank_int.transform.set_value(M44f(V3f(0.5, 0, 0), V3f(0, 0, 0), V3f(1, 1, 1), Euler.XYZ))
        tpl_bank_ext.transform.set_value(M44f(V3f(-0.5, 0, 0), V3f(0, 0, 0), V3f(1, 1, 1), Euler.XYZ))

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
        n['c_1'] = kl.Joint(hook, 'c_' + n_limb1 + n_end)
        n['c_2'] = kl.Joint(n['c_1'], 'c_' + n_limb2 + n_end)
        n['c_3'] = kl.Joint(n['c_2'], 'c_' + n_limb3 + n_end)
        n['c_e'] = kl.Joint(n['c_3'], 'c_' + n_eff + n_end)
        n['c_dg'] = kl.Joint(n['c_e'], 'c_' + n_digits + n_end)
        n['end_dg'] = kl.Joint(n['c_dg'], 'end_' + n_digits + n_end)

        copy_transform(tpl_limb1, n['c_1'])
        copy_transform(tpl_limb2, n['c_2'])
        copy_transform(tpl_limb3, n['c_3'])
        copy_transform(tpl_limb4, n['c_e'])
        copy_transform(tpl_digits, n['c_dg'])
        copy_transform(tpl_tip, n['end_dg'])

        # orient skeleton
        orient_joint((n['c_1'], n['c_2'], n['c_3'], n['c_e']), aim=aim_axis, up=up_axis, up_auto=1)

        if self.get_opt('reverse_lock'):
            t1 = tpl_tip.world_transform.get_value().translation()
            t2 = tpl_limb4.world_transform.get_value().translation()

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
                for j in (n['c_1'], n['c_2'], n['c_3']):
                    _children = j.get_children()
                    for _c in _children:
                        _c.reparent(hook)
                    _xfo = M44f(V3f(0, 0, 0), V3f(0, 180, 0), V3f(1, 1, 1), Euler.XYZ) * j.transform.get_value()
                    j.transform.set_value(_xfo)
                    for _c in _children:
                        _c.reparent(j)

        else:
            orient_joint((n['c_e'], n['c_dg'], n['end_dg']), aim=aim_axis, up=up_axis2)

        # rig skeleton
        n['o_1'] = duplicate_joint(n['c_1'], name='o_' + n_limb1 + n_end, p=hook)

        n['root_1'] = duplicate_joint(n['o_1'], name='root_' + n_limb1 + n_end, p=n['o_1'].get_parent())
        n['o_1'].reparent(n['root_1'])
        n['c_1'].reparent(n['root_1'])

        orient_joint(n['root_1'], aim_dir=[0, 1, 0], up_dir=[0, 0, 1])

        n['root_e'] = duplicate_joint(n['c_e'], name='root_' + n_eff + n_end, p=n['c_e'].get_parent())
        n['c_e'].reparent(n['root_e'])

        n['root_dg'] = duplicate_joint(n['c_dg'], p=n['c_dg'].get_parent(), name='root_' + n_digits + n_end)
        n['c_dg'].reparent(n['root_dg'])

        n['c_dg'].scale_compensate.set_value(False)

        add_plug(n['c_dg'], 'parent_scale', bool, k=0, default_value=True)
        _not = kl.Not(n['c_dg'], '_not')
        _not.input.connect(n['c_dg'].parent_scale)
        n['root_dg'].scale_compensate.connect(_not.output)

        # deform skeleton
        n['j_1'] = duplicate_joint(n['c_1'], p=n['root_1'], n='j_' + n_limb1 + n_end)
        n['j_2'] = duplicate_joint(n['c_2'], p=n['j_1'], n='j_' + n_limb2 + n_end)
        n['j_3'] = duplicate_joint(n['c_3'], p=n['j_2'], n='j_' + n_limb3 + n_end)
        n['j_e'] = duplicate_joint(n['c_e'], p=n['j_3'], n='j_' + n_eff + n_end)
        n['j_dg'] = duplicate_joint(n['c_dg'], p=n['j_e'], n='j_' + n_digits + n_end)

        for c in ('c_1', 'c_2', 'c_3', 'c_e', 'c_dg'):
            create_srt_in(n[c], k=1)

        n['j_1'].transform.connect(n['c_1'].transform)
        n['j_2'].transform.connect(n['c_2'].transform)
        n['j_3'].transform.connect(n['c_3'].transform)

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
        n['root_eIK'] = kl.SceneGraphNode(default_hook, 'root_' + n_eff + '_IK' + n_end)
        copy_transform(n['c_e'], n['root_eIK'], t=1)
        n['x_eIK'] = kl.SceneGraphNode(n['root_eIK'], 'x_' + n_eff + 'IK' + n_end)
        n['c_eIK'] = duplicate_joint(n['c_e'], p=n['root_eIK'], n='c_' + n_eff + '_IK' + n_end)
        create_srt_in(n['c_eIK'], keyable=True)

        n['root_eIK_offset'] = kl.Joint(default_hook, 'root_' + n_eff + '_IK_offset' + n_end)
        copy_transform(n['c_e'], n['root_eIK_offset'], t=1)
        n['c_eIK_offset'] = duplicate_joint(n['c_e'], p=n['root_eIK_offset'], n='c_' + n_eff + '_IK_offset' + n_end)
        create_srt_in(n['c_eIK_offset'], keyable=True)

        n['root_eIK_offset'].reparent(n['c_eIK'])

        if self.get_opt('space_switch'):
            self.build_space_mods()

        eff_parent = None
        if self.do_clavicle:
            eff_parent = hook
            if type(eff_parent) == kl.Joint:
                eff_parent = hook.get_parent()

        n['ik'], n['ik_eff'], n['eff_root'], n['eff_ik'] = stretch_IK(_sub_chain, n['c_eIK'], eff_parent=eff_parent)
        if quad_type == 'down':
            n['ik'].translate_root_in.connect(n['c_1'].find('transform').translate)
        else:
            n['ik'].translate_root_in.connect(n['c_2'].find('transform').translate)
        n['eff_ik'].transform.disconnect(restore_default=False)
        n['eff_ik'].find('parent_constrain').remove_from_parent()

        n['eff_root'].rename('eff_' + n_eff + '_base' + n_end)
        n['eff_ik'].rename('eff_' + n_eff + n_end)
        if quad_type == 'up':
            n['eff_root'].reparent(n['root_1'])
            n['eff_ik'].reparent(n['root_1'])

        if self.get_opt('default_stretch'):
            n['c_eIK'].stretch.set_value(1)

        if quad_type == 'down':
            add_plug(n['j_1'], 'squash', float)
            add_plug(n['j_2'], 'squash', float)
            n['j_1'].squash.connect(n['c_1'].squash)
            n['j_2'].squash.connect(n['c_2'].squash)
        else:
            add_plug(n['j_2'], 'squash', float)
            add_plug(n['j_3'], 'squash', float)
            n['j_2'].squash.connect(n['c_2'].squash)
            n['j_3'].squash.connect(n['c_3'].squash)

        if self.do_clavicle:
            if self.do_clavicle_auto:
                reparent_ik_handle(n['ik_ao'], n['c_eIK_offset'])
                n['ik_ao'].find('ik').twist_in.connect(n['ik'].twist_in)

        # switch controller
        n['c_sw'] = kl.SceneGraphNode(hook, 'c_' + n_limb + '_switch' + n_end)

        # deform switch control
        n['sw'] = {}

        _nc = 1  # self.get_opt('deform_chains')
        for _c in range(_nc):
            n['sw'][_c] = kl.SceneGraphNode(hook, 'sw_' + n_limb + '_weights' + n_chain[_c] + n_end)
            self.set_id(n['sw'][_c], 'weights.{}'.format(_c))

        # reverse IK rig
        self.build_reverse_lock()
        n['loc_lock'].transform.disconnect(restore_default=False)
        n['loc_lock'].find('point_constrain').remove_from_parent()
        n['loc_lock'].reparent(n['c_3'])
        point_constraint(n['loc_lockIK'], n['loc_lock'])
        # c.maintain_offset.set_value(True)
        # c.initial_parent_world_transform.set_value(n['c_3'].world_transform.get_value())
        # c.input_world.disconnect(restore_default=False)
        # c.input_world.connect(n['c_3'].world_transform)
        # m1 = c.input_target_world_transform.get_input().get_node().world_transform.get_value()
        # m2 = n['c_3'].world_transform.get_value().inverse()
        # m3 = m1 * m2
        # c.offset.set_value(m3)
        # n['loc_lock'].tx.set(0)
        # n['loc_lock'].tz.set(0)
        # n['loc_lock'].r.set(0, 0, 0)
        # TODO: check this part (diff maya)

        # change limb IK pointConstraint
        if quad_type == 'up':
            point_constraint(n['end_emIK'], n['eff_ik'])

        # reverse lock IK poses
        if self.get_opt('reverse_lock'):
            self.build_reverse_lock_poses()

        # quad pole vector IK
        j_quadPV = duplicate_joint(n['c_1'], p=n['c_1'].get_parent(), n='j_' + n_limb + '_quad_PV' + n_end)
        _ax = aim_constraint(n['c_e'], j_quadPV, aim_vector=[0, 1, 0], up_vector=[0, 0, 1], up_vector_world=[1, 0, 0])
        j_quadPV.transform.disconnect(restore_default=False)
        _ax.remove_from_parent()

        if self.do_clavicle:
            parent_constraint(n['c_clav'], j_quadPV, mo=1)

        end_quadPV = duplicate_joint(n['c_e'], p=j_quadPV, n='end_' + n_limb + '_quad_PV' + n_end)
        _t = end_quadPV.transform.get_value().translation()
        _r = end_quadPV.transform.get_value().rotation(Euler.XYZ)
        _s = end_quadPV.transform.get_value().scaling()
        end_quadPV.transform.set_value(M44f(V3f(_t.x, _t.y / 3, _t.z), _r, _s, Euler.XYZ))

        ik_quadPV = create_ik_handle([j_quadPV, end_quadPV], parent=n['end_emIK'])
        if quad_type == 'up':
            ik_quadPV.find('ik').translate_root_in.connect(n['c_1'].find('transform').translate)
            ik_quadPV.find('ik').world_pole_vector_in.set_value(M44f(V3f(1, 0, 0), V3f(0, 0, 0), V3f(1, 0, 0), Euler.XYZ))
        ik_quadPV.rename("ik_" + n_limb + "_PV" + n_end)

        ik_quadPV.transform.set_value(M44f(V3f(0, 0, 0), V3f(0, 0, 0), V3f(1, 1, 1), Euler.XYZ))

        # quad hacks
        _tw = n['ik'].twist_in.get_input()
        ik_quadPV.find('ik').twist_in.connect(_tw)
        n['ik'].twist_in.disconnect(restore_default=False)

        _db = kl.Distance(n['root_1'], '_len')

        if quad_type == 'down':
            _srt = kl.TransformToSRTNode(n['eff_root'], 'srt_out')
            _srt.transform.connect(n['eff_root'].transform)
            _db.input1.connect(_srt.translate)
        else:
            eff_quadroot = kl.SceneGraphNode(hook, 'eff_' + n_limb + '_quad_root' + n_end)

            _srt = create_srt_out(eff_quadroot, vectors=False)
            _srt.transform.connect(eff_quadroot.transform)
            imx = kl.InverseM44f(eff_quadroot, '_imx')
            imx.input.connect(eff_quadroot.parent_world_transform)

            mmx = kl.MultM44f(eff_quadroot, '_mmx', 3)
            mmx.input[0].connect(n['c_1'].find('transform').transform)
            mmx.input[1].connect(n['c_1'].parent_world_transform)
            mmx.input[2].connect(imx.output)

            eff_quadroot.transform.connect(mmx.output)
            _srt = create_srt_out(eff_quadroot)
            _db.input1.connect(_srt.translate)

        # eff_quad
        eff_quad = kl.SceneGraphNode(hook, 'eff_' + n_limb + '_quad' + n_end)
        point_constraint(n['end_emIK'], eff_quad)

        _srt = kl.JointTransformToSRT(eff_quad, 'srt_out')
        _srt.transform.connect(eff_quad.transform)
        _db.input2.connect(_srt.translate)

        # pole vector
        self.build_pole_vector_auto()
        self.build_pole_vector_follow()

        if quad_type == 'up':
            copy_transform(n['c_1'], n['o_pv'])
            n['ao_pv'].transform.disconnect(restore_default=False)
            _c = n['ao_pv'].find('aim_constrain')
            _c.remove_from_parent()
            if not self.get_opt('clavicle'):
                _c = n['ao_pv'].find('point_constrain')
                _c.remove_from_parent()

            point_constraint(n['c_1'], n['ao_pv'])
            aim_constraint(n['end_emIK'], n['ao_pv'], aim_vector=V3f(0, -1, 0), up_vector=V3f(0, 0, 0))

        if not self.do_clavicle:
            if quad_type == 'up':  # up
                # n['ik_pvf'].reparent(n['eff_quadroot'])
                # n['ik_pvf'].transform.set_value(M44f(V3f(0, 0, 0), V3f(0, 0, 0), V3f(1, 1, 1), Euler.XYZ))
                _ax = n['root_pvf'].find('aim_constrain')
                if _ax:
                    n['root_pvf'].transform.disconnect(restore_default=False)
                    _ax.remove_from_parent()
                d = (1, -1)[self.do_flip()]
                aim_constraint(n['c_1'], n['root_pvf'], aim_vector=V3f(0, d, 0), up_vector=V3f(0, 0, 0))
        else:
            # n['ik_pvf'].reparent(n['root_clav'])
            # copy_transform(n['ik_pvf'], n['c_1'])
            # point_constraint(n['c_clav'], n['ik_pvf'], mo=1)
            _ax = n['ao_pvf'].find('aim_constrain')
            if _ax:
                n['ao_pvf'].transform.disconnect(restore_default=False)
                _ax.remove_from_parent()
            d = (1, -1)[self.do_flip()]
            aim_constraint(n['inf_clav'], n['ao_pvf'], aim_vector=V3f(0, d, 0), up_vector=V3f(0, 0, 0))

        if quad_type == 'down':
            p1 = n['c_1'].world_transform.get_value().translation()
            p2 = n['c_2'].world_transform.get_value().translation()
            p3 = n['c_3'].world_transform.get_value().translation()
        else:
            p1 = n['c_2'].world_transform.get_value().translation()
            p2 = n['c_3'].world_transform.get_value().translation()
            p3 = n['c_e'].world_transform.get_value().translation()

        u = p2 - p1
        v = p3 - p1
        u1 = (u * v)
        v1 = (v * v)
        k = u1.length() / v1.length()
        p4 = p1 + (v * k)
        v2 = p2 - p4
        p = p4 + (v2 * (v.length() / v2.length()))

        s_pv = kl.SceneGraphNode(n['ao_pv'], 's_' + n_eff + 'PV_auto' + n_end)
        s_pvf = kl.SceneGraphNode(n['ao_pvf'], 's_' + n_eff + 'PV_follow' + n_end)
        n['end_pvf'].reparent(s_pvf)

        n['loc_pv'] = kl.SceneGraphNode(s_pv, 'loc_' + n_limb + '_PV_auto' + n_end)
        n['loc_pv'].set_world_transform(M44f(p, V3f(0, 0, 0), V3f(1, 1, 1), Euler.XYZ))

        n['loc_pvf'] = kl.SceneGraphNode(s_pvf, 'loc_' + n_limb + '_PV_follow' + n_end)
        copy_transform(n['loc_pv'], n['loc_pvf'])

        hook_pv = n['root_1']
        if self.do_clavicle:
            hook_pv = n['root_clav']
        n['root_pv'] = kl.SceneGraphNode(hook_pv, 'root_' + n_limb + '_PV' + n_end)
        n['c_pv'] = kl.SceneGraphNode(n['root_pv'], 'c_' + n_limb + '_PV' + n_end)

        _px = point_constraint((n['loc_pv'], n['loc_pvf']), n['root_pv'])

        pv_attr = 'follow_' + n_eff
        plug = add_plug(n['c_eIK'], pv_attr, float, k=1, min_value=0, max_value=1)
        _px.w1.connect(plug)
        connect_reverse(plug, _px.w0)

        if quad_type == 'down':
            ik_quadPV.find('ik').world_pole_vector_in.connect(n['c_pv'].world_transform)
            ik_quadPV.find('ik').initial_root_pole_vector_in.set_value(n['c_pv'].world_transform.get_value())
            # TODO check if it's needed for up

        if self.do_clavicle:
            if self.do_clavicle_auto:
                # TODO: ao clav pole vector (replace by aim up)
                # n['ik_ao'].world_pole_vector_in.connect(n['loc_pv'].world_transform)
                pass
        else:
            dist = _db.output.get_value()
            _srt_pv = create_srt_in(s_pv)
            connect_driven_curve(_db.output, _srt_pv.find('scale').y, {0: 0, dist: 1, (dist * 2.0): 2}, post='linear', tangent_mode='linear')
            _srt_pvf = create_srt_in(s_pvf)
            _srt_pvf.find('scale').y.connect(_srt_pv.find('scale').y.get_input())

        dist = _db.output.get_value()
        s_pvq = kl.SceneGraphNode(j_quadPV, 's_' + n_eff + 'PV_quad' + n_end)
        _srt_pvq = create_srt_in(s_pvq)
        connect_driven_curve(dist, _srt_pvq.find('scale').y, {0: 0, dist: 1, (dist * 2): 2}, post='linear', tangent_mode='linear')

        n['pvq'] = kl.SceneGraphNode(j_quadPV, 'loc_' + n_limb + '_PV_quad' + n_end)
        copy_transform(n['loc_pv'], n['pvq'])
        n['ik'].world_pole_vector_in.connect(n['pvq'].world_transform)

        # quad attrs
        add_plug(n['c_eIK'], 'quad_twist', float, step=1, k=1, nice_name='Quad Twist')
        if self.do_flip():
            n['ik'].twist_in.connect(n['c_eIK'].quad_twist)
        else:
            connect_mult(n['c_eIK'].quad_twist, -1, n['ik'].twist_in)

        # quad IK
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
            _quad_ikend = kl.Joint(n['c_1'], '_' + n_limb + '_quad_ik_end')
            copy_transform(n['c_2'], _quad_ikend)
            _quad_stretch = n['end_emIK']

        root_quad = duplicate_joint(_quad_orient, name='root_' + n_limb + '_quad' + n_end, p=n['o_1'])
        j_quad = duplicate_joint(_quad_orient, name='j_' + n_limb + '_quad' + n_end, p=root_quad)
        if quad_type == 'down':
            point_constraint(n['end_emIK'], j_quad)
        else:
            j_quad.reparent(n['c_1'].get_parent())

        end_quad = duplicate_joint(_quad_orient, name='end_' + n_limb + '_quad' + n_end, p=j_quad)
        copy_transform(_quad_locend, end_quad)

        o_quad = kl.SceneGraphNode(j_quad, 'o_' + n_limb + '_quad' + n_end)
        loc_quad = kl.SceneGraphNode(o_quad, 'loc_' + n_limb + '_quad' + n_end)

        copy_transform(end_quad, loc_quad)

        _srt = create_srt_in(loc_quad)
        _t = _srt.find('translate')
        if quad_type == 'down':
            _s = n['c_3'].find('transform/scale')
        else:
            _s = n['c_1'].find('transform/scale')
        connect_mult(_s.y, _t.y.get_value(), _t.y)

        # change main IK pointConstraint
        if quad_type == 'down':
            point_constraint(loc_quad, n['eff_ik'])

        # quad IK handle
        ikq = create_ik_handle((_quad_ikstart, _quad_ikend), parent=o_quad)
        ikq.rename('ik_' + n_limb + '_quad' + n_end)
        if quad_type == 'down':
            point_constraint(n['end_emIK'], ikq)
        else:
            ikq.find('ik').translate_root_in.connect(n['c_1'].find('transform').translate)

        _srt = create_srt_in(o_quad, ro=Euler.YZX)
        add_plug(n['c_eIK'], 'quad_roll', float, step=1, k=1, nice_name='Quad Roll')
        add_plug(n['c_eIK'], 'quad_pivot', float, step=1, k=1, nice_name='Quad Pivot')
        _srt.find('rotate').x.connect(n['c_eIK'].quad_roll)
        _srt.find('rotate').z.connect(n['c_eIK'].quad_pivot)

        # IK revquad
        troot_quad = kl.SceneGraphNode(_quad_orient, 'troot_' + n_limb + '_quad' + n_end)
        troot_quad.reparent(j_quadPV)
        if quad_type == 'up':  # up
            point_constraint(n['end_emIK'], troot_quad)
        else:
            point_constraint(n['eff_root'], troot_quad)  # n['c_1'] proxy

        t_quad = kl.Joint(_quad_orient, 't_' + n_limb + '_quad' + n_end)
        copy_transform(_quad_stretch, t_quad, t=True)
        _t = t_quad.transform.get_value().translation()
        _r = t_quad.transform.get_value().rotation(Euler.XYZ)
        _s = t_quad.transform.get_value().scaling()
        t_quad.transform.set_value(M44f(V3f(0, _t.y, 0), _r, _s, Euler.XYZ))
        t_quad.reparent(troot_quad)

        add_plug(n['c_eIK'], 'quad_lock', float, k=1, min_value=0, max_value=1, nice_name='Quad Lock')

        if quad_type == 'down':
            orient_constraint(n['c_eIK_offset'], j_quad, mo=1)
        else:
            create_srt_in(j_quad)
        _x_xfo = j_quad.transform.get_input()
        j_quad.transform.disconnect(restore_default=False)

        ikqa = create_ik_handle((j_quad, end_quad), parent=t_quad)
        if quad_type == 'up':
            ikqa.find('ik').translate_root_in.connect(n['c_1'].find('transform').translate)
            ikqa.find('ik').world_pole_vector_in.set_value(M44f(V3f(1, 0, 0),
                                                                V3f(0, 0, 0),
                                                                V3f(1, 0, 0),
                                                                Euler.XYZ))
        ikqa.rename('ik_' + n_limb + 'quad_auto' + n_end)

        # quad lock
        _ik_xfo = j_quad.transform.get_input()
        j_quad.transform.disconnect(restore_default=False)
        bx = kl.BlendTransformsNode(n['c_eIK'], 'blend_transforms')
        bx.shortest_in.set_value(True)
        bx.transform1_in.connect(_ik_xfo)
        bx.transform2_in.connect(_x_xfo)
        bx.blend_in.connect(n['c_eIK'].quad_lock)
        j_quad.transform.connect(bx.transform_out)
        ikqa.transform.set_value(M44f(V3f(0, 0, 0), V3f(0, 0, 0), V3f(1, 1, 1), Euler.XYZ))

        # stretch IK revquad
        pb_expr = kl.BlendTransformsNode(t_quad, '_pb')
        pb_expr.transform2_in.set_value(t_quad.transform.get_value())
        t_quad.transform.connect(pb_expr.transform_out)

        add_plug(n['c_eIK'], 'quad_slide_min', float, default_value=0, min_value=0)
        add_plug(n['c_eIK'], 'quad_slide_max', float, default_value=1, min_value=1)

        add_plug(_quad_ikstart, 'stretch', float, default_value=1)
        add_plug(_quad_ikstart, 'squash', float, default_value=1)

        # quad stretch expr
        network = kl.SceneGraphNode(t_quad, 'expr_' + n_limb + '_quad_stretch' + n_end)

        _s1 = n['c_1'].find('transform/scale').y
        _s2 = n['c_2'].find('transform/scale').y
        _s3 = n['c_3'].find('transform/scale').y
        _t1 = connect_mult(abs(n['c_2'].find('transform/translate').y.get_value()), _s1)
        _t2 = connect_mult(abs(n['c_3'].find('transform/translate').y.get_value()), _s2)
        _t3 = connect_mult(abs(n['root_e'].find('srt/translate').y.get_value()), _s3)
        _dchain = connect_expr('t1 + t2 + t3', t1=_t1, t2=_t2, t3=_t3)

        _qmin = n['c_eIK'].quad_slide_min
        _qmax = n['c_eIK'].quad_slide_max
        _d = _db.output
        _d0 = _db.output.get_value()

        _if_g = kl.IsGreater(network, '_is_greater')
        _if_g.input1.connect(_d)
        _if_g.input2.set_value(_d0)

        _if = kl.Condition(network, '_if')
        _if.condition.connect(_if_g.output)

        _0 = connect_sub(_d, _d0)
        _1 = connect_sub(connect_mult(_dchain, _qmax), _d0)
        _w1 = connect_sub(1, connect_div(_0, _1))

        _if0_g = kl.IsGreater(network, '_is_greater')  # if w1<0: w1=0
        _if0_g.input1.connect(_w1)
        _if0_g.input2.set_value(0)

        _if0 = kl.Condition(network, '_if')
        _if0.condition.connect(_if0_g.output)
        _if0.input1.connect(_w1)
        _if0.input2.set_value(0)
        _w1 = _if0.output

        _2 = connect_mult(-_d0, connect_sub(1, _qmin))
        _w0 = connect_sub(1, connect_div(_0, _2))

        _if.input1.connect(_w1)
        _if.input2.connect(_w0)
        pb_expr.blend_in.connect(_if.output)

        # IK switch
        add_plug(n['c_sw'], 'ik_blend', float, k=1, min_value=0, max_value=1, default_value=1)
        mult = connect_mult(n['c_sw'].ik_blend, 1, n['ik'].blend)
        ikq.find('ik').blend.connect(mult)
        n['ik_em'].blend.connect(mult)

        lock_attr = n_digits + '_lock'
        plug = add_plug(n['c_eIK'], lock_attr, float, default_value=self.get_opt('reverse_lock'))
        connect_mult(plug, n['c_sw'].ik_blend, n['ik_dg'].blend)

        # deform rig
        n['root_2pt'] = duplicate_joint(n['c_2'], name='root_' + n_limb2 + '_tweak' + n_end)
        n['c_2pt'] = kl.SceneGraphNode(n['root_2pt'], 'c_' + n_limb2 + '_tweak' + n_end)
        create_srt_in(n['c_2pt'], k=1)

        if self.do_flip():
            _t = n['root_2pt'].transform.get_value().translation()
            _r = n['root_2pt'].transform.get_value().rotation(Euler.XYZ)
            n['root_2pt'].transform.set_value(M44f(_t, _r, V3f(-1, -1, -1), Euler.XYZ))

        pc = point_constraint(n['c_2'], n['root_2pt'])
        oc = orient_constraint((n['c_1'], n['c_2']), n['root_2pt'])

        mk.Mod.add(n['c_2pt'], 'space', {'targets': ['::hook']})

        n['root_3pt'] = duplicate_joint(n['c_3'], name='root_' + n_limb3 + '_tweak' + n_end)
        n['c_3pt'] = kl.SceneGraphNode(n['root_3pt'], 'c_' + n_limb3 + '_tweak' + n_end)
        create_srt_in(n['c_3pt'], k=1)

        if self.do_flip():
            _t = n['root_3pt'].transform.get_value().translation()
            _r = n['root_3pt'].transform.get_value().rotation(Euler.XYZ)
            n['root_3pt'].transform.set_value(M44f(_t, _r, V3f(-1, -1, -1), Euler.XYZ))

        pc = point_constraint((n['c_3']), n['root_3pt'])
        oc = orient_constraint((n['c_2'], n['c_3']), n['root_3pt'])

        mk.Mod.add(n['c_3pt'], 'space', {'targets': ['::hook']})

        # skin rig: main joints
        n['aim_1'] = duplicate_joint(n['c_1'], p=n['j_1'], n='j_' + n_limb1 + '_aim' + n_end)
        n['aim_2'] = duplicate_joint(n['c_2'], p=n['j_2'], n='j_' + n_limb2 + '_aim' + n_end)
        n['aim_3'] = duplicate_joint(n['c_3'], p=n['j_3'], n='j_' + n_limb3 + '_aim' + n_end)
        n['sub_1'] = duplicate_joint(n['aim_1'], p=n['j_1'], n='j_' + n_limb1 + '_deform' + n_end)
        n['sub_2'] = duplicate_joint(n['aim_2'], p=n['j_2'], n='j_' + n_limb2 + '_deform' + n_end)
        n['sub_3'] = duplicate_joint(n['aim_3'], p=n['j_3'], n='j_' + n_limb3 + '_deform' + n_end)

        _srt1 = create_srt_in(n['sub_1'])
        _srt2 = create_srt_in(n['sub_2'])
        _srt3 = create_srt_in(n['sub_3'])
        aim_constraint(n['c_2pt'], n['sub_1'], aim_vector=[0, (-1, 1)[not aim_axis.startswith('-')], 0])
        aim_constraint(n['c_3pt'], n['sub_2'], aim_vector=[0, (-1, 1)[not aim_axis.startswith('-')], 0])
        aim_constraint(n['c_e'], n['sub_3'], aim_vector=[0, (-1, 1)[not aim_axis.startswith('-')], 0])
        point_constraint(n['c_2pt'], n['sub_2'])
        point_constraint(n['c_3pt'], n['sub_3'])

        # skin rig: effector
        n['sub_e'] = duplicate_joint(n['j_e'], p=n['j_e'], n='j_' + n_eff + '_deform' + n_end)

        n['sk_e'] = duplicate_joint(n['c_e'], n='sk_' + n_eff + n_end, p=n['c_e'])
        duplicate_joint(n['c_dg'], n='end_' + n_eff + n_end, p=n['sk_e'])
        n['sk_dg'] = duplicate_joint(n['c_dg'], n='sk_' + n_digits + n_end, p=n['c_dg'])
        n['j_dge'] = duplicate_joint(n['end_dg'], n='j_' + n_eff + 'Tip' + n_end, p=n['sk_dg'])
        n['sk_e'].scale_compensate.set_value(False)
        n['sk_dg'].scale_compensate.set_value(False)

        # twist fix
        add_plug(n['c_sw'], 'twist_fix1', float, k=1, nice_name='Twist Fix 1')
        add_plug(n['c_sw'], 'twist_fix2', float, k=1, nice_name='Twist Fix 2')

        # flex rig
        sw = n['sw'][0]

        n['loc_2pt_up'] = kl.SceneGraphNode(n['c_2pt'], 'loc_' + n_limb2 + '_tweak_up' + n_end)
        n['loc_2pt_dn'] = kl.SceneGraphNode(n['c_2pt'], 'loc_' + n_limb2 + '_tweak_dn' + n_end)
        create_srt_in(n['loc_2pt_up'])
        create_srt_in(n['loc_2pt_dn'])

        xfo1 = n['c_1']
        xfo2 = n['c_2pt']
        xfo3 = n['c_3']

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
        add_plug(sw, 'flex_offset1_start', float, keyable=True, min_value=0, max_value=1, default_value=0.5)
        angle_weight = connect_expr('max(0, 1-(a/(a0*max(1-w, 0.001))))', a=angle, a0=angle0, w=sw.flex_offset1_start)

        add_plug(sw, 'flex_offset1_upX', float, keyable=True)
        add_plug(sw, 'flex_offset1_upY', float, keyable=True)
        add_plug(sw, 'flex_offset1_upZ', float, keyable=True)
        add_plug(sw, 'flex_offset1_dnX', float, keyable=True)
        add_plug(sw, 'flex_offset1_dnY', float, keyable=True)
        add_plug(sw, 'flex_offset1_dnZ', float, keyable=True)

        for side in ('up', 'dn'):
            for dim in 'XYZ':
                offset = sw.get_dynamic_plug('flex_offset1_' + side + dim)
                translate = n['loc_2pt_' + side].find('transform/translate').get_plug(dim.lower())
                connect_mult(offset, angle_weight, translate)

        n['loc_3pt_up'] = kl.SceneGraphNode(n['c_3pt'], 'loc_' + n_limb3 + '_tweak_up' + n_end)
        n['loc_3pt_dn'] = kl.SceneGraphNode(n['c_3pt'], 'loc_' + n_limb3 + '_tweak_dn' + n_end)
        create_srt_in(n['loc_3pt_up'])
        create_srt_in(n['loc_3pt_dn'])

        xfo1 = n['c_2']
        xfo2 = n['c_3pt']
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
        add_plug(sw, 'flex_offset2_start', float, keyable=True, min_value=0, max_value=1, default_value=0.5)
        angle_weight = connect_expr('max(0, 1-(a/(a0*max(1-w, 0.001))))', a=angle, a0=angle0, w=sw.flex_offset2_start)

        add_plug(sw, 'flex_offset2_upX', float, keyable=True)
        add_plug(sw, 'flex_offset2_upY', float, keyable=True)
        add_plug(sw, 'flex_offset2_upZ', float, keyable=True)
        add_plug(sw, 'flex_offset2_dnX', float, keyable=True)
        add_plug(sw, 'flex_offset2_dnY', float, keyable=True)
        add_plug(sw, 'flex_offset2_dnZ', float, keyable=True)

        for side in ('up', 'dn'):
            for dim in 'XYZ':
                offset = sw.get_dynamic_plug('flex_offset2_' + side + dim)
                translate = n['loc_3pt_' + side].find('transform/translate').get_plug(dim.lower())
                connect_mult(offset, angle_weight, translate)

        # bend rig
        n['root_1bd'] = kl.SceneGraphNode(n['sub_1'], 'root_' + n_limb1 + '_bend' + n_end)
        n['c_1bd'] = kl.SceneGraphNode(n['root_1bd'], 'c_' + n_limb1 + '_bend' + n_end)
        create_srt_in(n['c_1bd'], k=1)

        n['root_2bd'] = kl.SceneGraphNode(n['sub_2'], 'root_' + n_limb2 + '_bend' + n_end)
        n['c_2bd'] = kl.SceneGraphNode(n['root_2bd'], 'c_' + n_limb2 + '_bend' + n_end)
        create_srt_in(n['c_2bd'], k=1)

        n['root_3bd'] = kl.SceneGraphNode(n['sub_3'], 'root_' + n_limb3 + '_bend' + n_end)
        n['c_3bd'] = kl.SceneGraphNode(n['root_3bd'], 'c_' + n_limb3 + '_bend' + n_end)
        create_srt_in(n['c_3bd'], k=1)

        if self.do_flip():
            _t = n['root_1bd'].transform.get_value().translation()
            _r = n['root_1bd'].transform.get_value().rotation(Euler.XYZ)
            n['root_1bd'].transform.set_value(M44f(_t, _r, V3f(-1, -1, -1), Euler.XYZ))
            _t = n['root_2bd'].transform.get_value().translation()
            _r = n['root_2bd'].transform.get_value().rotation(Euler.XYZ)
            n['root_2bd'].transform.set_value(M44f(_t, _r, V3f(-1, -1, -1), Euler.XYZ))
            _t = n['root_3bd'].transform.get_value().translation()
            _r = n['root_3bd'].transform.get_value().rotation(Euler.XYZ)
            n['root_3bd'].transform.set_value(M44f(_t, _r, V3f(-1, -1, -1), Euler.XYZ))

        point_constraint((n['c_1'], n['loc_2pt_up']), n['root_1bd'])
        point_constraint((n['loc_2pt_dn'], n['loc_3pt_up']), n['root_2bd'])
        point_constraint((n['loc_3pt_dn'], n['c_e']), n['root_3bd'])

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

        # shear quad
        n['root_sh_q'] = duplicate_joint(n['sub_3'], p=n['sub_2'], n='root_shear_q')
        n['loc_sh_q'] = duplicate_joint(n['sub_3'], p=n['root_sh_q'], n='loc_shear_q')

        srt = kl.TransformToSRTNode(n['loc_sh_q'], 'srt')
        srt.transform.connect(n['loc_sh_q'].transform)
        qe = kl.EulerToQuatf(srt, '_euler')
        qe.rotate.connect(srt.rotate)
        qe.rotate_order.connect(srt.rotate_order)
        q = kl.QuatfToFloat(qe, '_quat')
        q.quat.connect(qe.quat)
        n['shx_q'] = q.i
        n['shz_q'] = connect_mult(q.k, -1)

        add_plug(n['c_3'], 'qx', float)
        add_plug(n['c_3'], 'qy', float)
        add_plug(n['c_3'], 'qz', float)
        n['c_3'].qx.connect(q.i)
        n['c_3'].qy.connect(q.j)
        n['c_3'].qz.connect(q.k)

        # shear dn
        root_sh_dn = duplicate_joint(n['sub_3'], p=n['sub_e'], n='root_shear_dn')
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

        def build_twist_joints_end(jdup, jpos):
            jend = duplicate_joint(jdup, n=jdup.get_name().split(':')[-1].replace('sk_', 'end_'), p=jdup)
            copy_transform(jpos, jend)

        for i, sk in enumerate(n['sk_su'][0][:-1]):
            build_twist_joints_end(n['sk_su'][0][i], n['sk_su'][0][i + 1])

        for i, sk in enumerate(n['sk_sm'][0][:-1]):
            build_twist_joints_end(n['sk_sm'][0][i], n['sk_sm'][0][i + 1])

        for i, sk in enumerate(n['sk_sd'][0][:-1]):
            build_twist_joints_end(n['sk_sd'][0][i], n['sk_sd'][0][i + 1])

        build_twist_joints_end(n['sk_su'][0][-1], n['sk_sm'][0][0])
        build_twist_joints_end(n['sk_sm'][0][-1], n['sk_sd'][0][0])
        build_twist_joints_end(n['sk_sd'][0][-1], n['c_e'])

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
            n['rb1'] = create_blend_joint(n['sk_su'][0][0], rb_limb1, p=n['sub_1'], name='sk_' + n_limb1 + '_blend' + n_end)
            n['rb2'] = create_blend_joint(n['sk_sm'][0][0], n['sk_su'][0][-1], p=n['sub_2'], name='o_' + n_limb2 + '_blend' + n_end)
            n['rb3'] = create_blend_joint(n['sk_sd'][0][0], n['sk_sm'][0][-1], p=n['sub_3'], name='o_' + n_limb3 + '_blend' + n_end)
            n['rbe'] = create_blend_joint(n['sk_e'], n['sk_sd'][0][-1], p=n['j_e'], name='sk_' + n_eff + '_blend' + n_end)
            n['rb1'].find('transform').scale.connect(create_srt_out(n['sk_su'][0][0]).scale)

            n['sk_rb2'] = duplicate_joint(n['sub_2'], p=n['sub_2'], n='sk_' + n_limb2 + '_blend' + n_end)
            n['sk_rb2'].reparent(n['rb2'])

            # create_srt_in(n['sk_rb2']).scale.connect(create_srt_out(n['sk_sm'][0][0]).scale)
            point_constraint((n['loc_2pt_up'], n['loc_2pt_dn']), n['rb2'])

            n['sk_rb3'] = duplicate_joint(n['sub_3'], p=n['sub_3'], n='sk_' + n_limb3 + '_blend' + n_end)
            n['sk_rb3'].reparent(n['rb3'])

            # create_srt_in(n['sk_rb3']).scale.connect(create_srt_out(n['sk_sd'][0][0]).scale)
            point_constraint((n['loc_3pt_up'], n['loc_3pt_dn']), n['rb3'])

        # channels
        for c in (n['c_2'], n['c_3'], n['c_e'], n['c_dg']):
            for dim in 'xyz':
                set_plug(c.find('transform/translate').get_plug(dim), k=0, lock=True)

        for c in (n['c_2pt'], n['c_3pt'], n['c_1bd'], n['c_2bd'], n['c_3bd']):
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

        # common switch shape
        for c in ('c_clav', 'c_1', 'c_2', 'c_3', 'c_e', 'c_eIK', 'c_eIK_offset', 'c_dg', 'c_1bd', 'c_2bd', 'c_3bd', 'c_2pt', 'c_3pt'):
            if c in n:
                for plug in ('ik_blend', 'twist_fix1', 'twist_fix2'):
                    add_plug(n[c], plug, float, k=1)
                    n[c].get_dynamic_plug(plug).connect(n['c_sw'].get_dynamic_plug(plug))

        n['c_eIK_offset'].show.set_value(False)
        grp = mk.Group.create('{} offset{}'.format(self.name, self.get_branch_suffix(' ')))
        for c in ['c_eIK_offset']:
            grp.add_member(n[c])
        self.set_id(grp.node, 'vis.offset')

        # vis group
        grp = mk.Group.create('{}{} shape'.format(self.name, self.get_branch_suffix(' ')))
        for c in ('c_1bd', 'c_2bd', 'c_3bd', 'c_2pt', 'c_3pt'):
            grp.add_member(n[c])
        self.set_id(grp.node, 'vis.shape')

        # hooks
        self.set_hook(tpl_limb1, n['sub_1'], 'hooks.limb1')
        self.set_hook(tpl_limb2, n['sub_2'], 'hooks.limb2')
        self.set_hook(tpl_limb2, n['sub_3'], 'hooks.limb3')
        self.set_hook(tpl_limb3, n['sk_e'], 'hooks.effector')
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
            self.set_id(j.get_parent(), 'roots.up.{}'.format(i))
        self.set_id(n['sk_su'][0][-1], 'skin.last.up')

        for i, j in enumerate(n['sk_sd'][0]):
            self.set_id(j, 'skin.dn.{}'.format(i))
            self.set_id(j.get_parent(), 'roots.dn.{}'.format(i))
        self.set_id(n['sk_sd'][0][-1], 'skin.last.dn')

        for i, j in enumerate(n['sk_sm'][0]):
            self.set_id(j, 'skin.mid.{}'.format(i))
            self.set_id(j.get_parent(), 'roots.mid.{}'.format(i))
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

        self.set_id(n['root_eIK'], 'roots.effector')

        self.set_id(n['end_dg'], 'tip')

        # ui ik/fk match
        ui_ikfk = kl.Node(n['c_eIK'], 'ui_match_ikfk')
        ui_plug = add_plug(ui_ikfk, 'ui', kl.Unit)

        for c in (n['c_eIK'], n['c_1'], n['c_2'], n['c_3'], n['c_e']):
            plug = add_plug(c, 'ui_match_ikfk', kl.Unit)
            plug.connect(ui_plug)

        add_plug(ui_ikfk, 'switch', float)
        add_plug(ui_ikfk, 'twist', float)
        add_plug(ui_ikfk, 'ik', str)
        add_plug(ui_ikfk, 'fk', str, array=True, size=4)

        add_plug(ui_ikfk, 'twist_factor', float, default_value=(1, -1)[self.do_flip()])

        ui_ikfk.switch.connect(n['c_sw'].ik_blend)
        ui_ikfk.twist.connect(n['c_eIK'].twist)

        ui_ikfk.ik.connect(n['c_eIK'].gem_id)
        ui_ikfk.fk[0].connect(n['c_1'].gem_id)
        ui_ikfk.fk[1].connect(n['c_2'].gem_id)
        ui_ikfk.fk[2].connect(n['c_3'].gem_id)
        ui_ikfk.fk[3].connect(n['c_e'].gem_id)

    def build_twist_joints(self, nj, tw, name, c, sk, j_base, j_mid, j_tip):
        n = self.n

        n_end = self.get_branch_suffix()

        nc = 1
        n_chain = ['']

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
                    j = duplicate_joint(c, p=sk, n='root_' + name + str(i) + n_chain[_c] + n_end)
                    create_srt_in(j)
                    roots[_c].append(j)

                    j = duplicate_joint(c, p=roots[_c][-1], n='sk_' + name + str(i) + n_chain[_c] + n_end)
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

                for _c in range(nc):
                    point_constraint(p1, roots[_c][i])

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
        point_constraint(j_tip, loc_end)

        if tw == 'mid':
            for _c in range(nc):
                point_constraint(j_base, roots[_c][0])
        elif tw == 'dn':
            for _c in range(nc):
                point_constraint(j_base, roots[_c][0])

        # aims
        for i in range(nj + 1):
            for _c in range(nc):
                aim_axis = self.get_branch_opt('aim_axis')
                aim_vector = axis_to_vector(aim_axis)
                if i < nj:
                    aim_constraint(roots[_c][i + 1], roots[_c][i], aim_vector=aim_vector, up_vector=V3f(0, 0, 0))
                else:
                    aim_constraint(loc_end, roots[_c][i], aim_vector=aim_vector, up_vector=V3f(0, 0, 0))

        # update shear rig
        if tw == 'up':
            orient_constraint(roots[0][0], n['loc_sh_up'])
            n['root_sh_m'].reparent(roots[0][-1])
        elif tw == 'mid':
            orient_constraint(roots[0][0], n['loc_sh_m'])
            n['root_sh_q'].reparent(roots[0][-1])
        elif tw == 'dn':
            orient_constraint(roots[0][0], n['loc_sh_q'])
            orient_constraint(roots[0][-1], n['loc_sh_dn'])

        # twists rig
        if tw == 'up':
            j_tw = duplicate_joint(c, p=p1s[min(p1s)], n='j_' + name + '_twist' + n_end)  # p=roots[1]
            copy_transform(roots[0][1], j_tw, t=1)
            create_srt_out(aim_constraint(c, j_tw, aim_vector=V3f(0, (1, -1)[not aim_axis.startswith('-')], 0), up_vector=V3f(0, 0, 0)))

            end_tw = duplicate_joint(c, p=j_tw, n='end_' + name + '_twist' + n_end)
            copy_transform(c, end_tw, t=1)
            n['j_tw_up'] = end_tw

            if not self.get_opt('clavicle'):
                tg_tw = kl.Joint(n['root_1'], 'j_' + name + '_twist' + n_end)
                copy_transform(end_tw, tg_tw)
            else:
                tg_tw = kl.Joint(n['j_clav'], 'j_' + name + '_twist' + n_end)
                copy_transform(end_tw, tg_tw)
            _srt_in = create_srt_in(end_tw, ro=Euler.YZX, jo_ro=Euler.YZX)

            twist_constraint(tg_tw, end_tw)
            _tw_in = _srt_in.rotate.get_input()
            _tw_e = kl.EulerToFloat(_tw_in.get_node(), 'rotate')
            _tw_e.euler.connect(_tw_in)

            _srt_in.rotate.connect(_srt_in.find('rotate').euler)
            _srt_in.find('rotate').x.connect(_tw_e.x)
            _tw = connect_sub(_tw_e.y, n['c_sw'].twist_fix1, _srt_in.find('rotate'))
            _srt_in.find('rotate').z.connect(_tw_e.z)

            add_plug(n['c_sw'], 'twist_up', float, min_value=0, max_value=1, default_value=1)
            n['tw_up'] = connect_mult(_tw, n['c_sw'].twist_up)

        elif tw == 'mid':
            j_tw = duplicate_joint(c, p=p1s[max(p1s)], n='j_' + name + '_twist' + n_end)  # p=roots[1]
            copy_transform(roots[0][-1], j_tw, t=1)
            aim_constraint(j_tip, j_tw, aim_vector=V3f(0, (-1, 1)[not aim_axis.startswith('-')], 0), up_vector=V3f(0, 0, 0))

            end_tw = duplicate_joint(c, p=j_tw, n='end_' + name + '_twist' + n_end)
            copy_transform(j_tip, end_tw, t=1)

            tg_tw = kl.Joint(j_tip, 'j_' + name + '_twist_target' + n_end)
            copy_transform(end_tw, tg_tw)
            _srt_in = create_srt_in(end_tw, ro=Euler.YZX, jo_ro=Euler.YZX)

            twist_constraint(tg_tw, end_tw)
            _tw_in = _srt_in.rotate.get_input()
            _tw_e = kl.EulerToFloat(_tw_in.get_node(), 'rotate')
            _tw_e.euler.connect(_tw_in)

            _srt_in.rotate.connect(_srt_in.find('rotate').euler)
            _srt_in.find('rotate').x.connect(_tw_e.x)
            _tw = connect_sub(_tw_e.y, n['c_sw'].twist_fix1, _srt_in.find('rotate'))
            _srt_in.find('rotate').z.connect(_tw_e.z)

            add_plug(n['c_sw'], 'twist_mid', float, min_value=0, max_value=1, default_value=1)
            n['tw_mid'] = connect_mult(_tw, n['c_sw'].twist_mid)

            _srt = create_srt_in(tg_tw)
            _srt.find('rotate').y.connect(n['c_sw'].twist_fix2)

        else:  # dn
            j_tw = duplicate_joint(c, p=p1s[max(p1s)], n='j_' + name + '_twist' + n_end)  # p=roots[1]
            copy_transform(roots[0][-1], j_tw, t=1)
            aim_constraint(j_tip, j_tw, aim_vector=V3f(0, (-1, 1)[not aim_axis.startswith('-')], 0), up_vector=V3f(0, 0, 0))

            end_tw = duplicate_joint(c, p=j_tw, n='end_' + name + '_twist' + n_end)
            copy_transform(j_tip, end_tw, t=1)
            n['j_tw_dn'] = end_tw

            tg_tw = kl.Joint(j_tip, 'j_' + name + '_twist_target' + n_end)
            copy_transform(end_tw, tg_tw)
            _srt_in = create_srt_in(end_tw, ro=Euler.YZX, jo_ro=Euler.YZX)

            twist_constraint(tg_tw, end_tw)
            _tw_in = _srt_in.rotate.get_input()
            _tw_e = kl.EulerToFloat(_tw_in.get_node(), 'rotate')
            _tw_e.euler.connect(_tw_in)

            _srt_in.rotate.connect(_srt_in.find('rotate').euler)
            _srt_in.find('rotate').x.connect(_tw_e.x)
            _tw = connect_sub(_tw_e.y, n['c_sw'].twist_fix2, _srt_in.find('rotate'))
            _srt_in.find('rotate').z.connect(_tw_e.z)

            add_plug(n['c_sw'], 'twist_dn', float, min_value=0, max_value=1, default_value=1)
            n['tw_dn'] = connect_mult(_tw, n['c_sw'].twist_dn)

        # weights rig
        for _c in range(nc):

            for i in range(nj + 1):
                _attr = 'twist_{}_{}'.format(tw, i)
                add_plug(n['sw'][_c], _attr, float, min_value=0, max_value=1)

            for i in range(nj + 1):
                _attr = 'shear_{}_base_{}'.format(tw, i)
                add_plug(n['sw'][_c], _attr, float, min_value=0, max_value=2, default_value=0)

            for i in range(nj + 1):
                _attr = 'shear_{}_tip_{}'.format(tw, i)
                add_plug(n['sw'][_c], _attr, float, min_value=0, max_value=2, default_value=0)

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
                    connect_add(n['c_sw'].twist_fix1, connect_mult(n['tw_up'], _twist), _r.y)

                    connect_mult(_shear_base, n['shz_up'], mxs[_c][i].find('i').y)
                    connect_expr('x = b*up + t*-m', x=mxs[_c][i].find('k').y, b=_shear_base, t=_shear_tip, up=n['shx_up'], m=n['shx_m'])

                elif tw == 'mid':
                    _twist.set_value(float(i) / nj)
                    connect_add(n['c_sw'].twist_fix1, connect_mult(n['tw_mid'], _twist), _r.y)

                    connect_expr('x = b*m + t*-q', x=mxs[_c][i].find('k').y, b=_shear_base, t=_shear_tip, m=n['shx_m'], q=n['shx_q'])

                else:  # dn
                    _twist.set_value(float(i) / nj)
                    connect_add(n['c_sw'].twist_fix2, connect_mult(n['tw_dn'], _twist), _r.y)

                    connect_mult(_shear_tip, n['shz_dn'], mxs[_c][i].find('i').y)
                    connect_expr('x = b*q + t*dn', x=mxs[_c][i].find('k').y, b=_shear_base, t=_shear_tip, q=n['shx_q'], dn=n['shx_dn'])

        return sks

    def build_rotate_order(self):
        set_plug(self.n['c_1'].find('transform').rotate_order, Euler.YXZ)
        set_plug(self.n['c_2'].find('transform').rotate_order, Euler.YXZ)
        set_plug(self.n['c_3'].find('transform').rotate_order, Euler.YXZ)
        set_plug(self.n['c_e'].find('transform').rotate_order, Euler.XZY)
        set_plug(self.n['c_dg'].find('transform').rotate_order, Euler.YXZ)
        set_plug(self.n['c_eIK'].find('transform').rotate_order, Euler.XZY)
        set_plug(self.n['c_eIK_offset'].find('transform').rotate_order, Euler.XZY)
