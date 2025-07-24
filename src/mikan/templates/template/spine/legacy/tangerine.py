# coding: utf-8

import json

import meta_nodal_py as kl
from meta_nodal_py.Imath import V3f, M44f, Euler

import mikan.tangerine.core as mk
from mikan.vendor.geomdl.utilities import generate_knot_vector
from mikan.tangerine.lib.nurbs import rebuild_curve
from mikan.tangerine.lib.commands import *
from mikan.tangerine.lib.connect import *
from mikan.tangerine.lib.rig import *


class Template(mk.Template):

    def build_template(self, data):
        root = self.node
        root.rename('tpl_spine'.format(self.name))

        spine1 = kl.Joint(root, 'tpl_spine1')
        spine2 = kl.Joint(spine1, 'tpl_spine2')
        spine_tip = kl.Joint(spine2, 'tpl_spine_tip')

        spine1.transform.set_value(M44f(V3f(0, 1, 0.05), V3f(0, 0, 0), V3f(1, 1, 1), Euler.XYZ))
        spine2.transform.set_value(M44f(V3f(0, 1.5, -0.2), V3f(0, 0, 0), V3f(1, 1, 1), Euler.XYZ))
        spine_tip.transform.set_value(M44f(V3f(0, 1, 0.15), V3f(0, 0, 0), V3f(1, 1, 1), Euler.XYZ))

        hips = kl.Joint(root, 'tpl_hips')
        hips.transform.set_value(M44f(V3f(0, -0.5, 0), V3f(0, 0, 0), V3f(1, 1, 1), Euler.XYZ))
        self.set_template_id(hips, 'hips')

        cv_spine = kl.SceneGraphNode(find_root(), 'cv_' + self.name)
        geo_spine = kl.SplineCurve(cv_spine, 'cv_' + self.name + 'Shape')
        self.set_template_id(cv_spine, 'curve')

        cvs = [root.world_transform.get_value().translation()] * 7
        knots = generate_knot_vector(3, 7)
        weights = [1] * 7
        spline_data = kl.Spline(cvs, knots, weights, False)
        geo_spine.spline_in.set_value(spline_data)
        cv_spine.reparent(root)

        skin_data = {
            'deformer': 'skin',
            'transform': cv_spine,
            'data': {
                'infs': {0: root, 1: spine1, 2: spine2, 3: spine_tip},
                'maps': {
                    0: mk.WeightMap("1 0.75 0*5"),
                    1: mk.WeightMap("0 0.25 1 0.5 0 0 0"),
                    2: mk.WeightMap("0 0 0 0.5 1 0.25 0"),
                    3: mk.WeightMap("0*5 0.75 1")
                },
                'bind_pose': dict(zip(range(4), [root] * 4))
            }
        }
        skin_dfm = mk.Deformer(**skin_data)
        skin_dfm.build()

    def build_rig(self):

        # get structures
        hook = self.hook
        rig_hook = mk.Nodes.get_id('::rig')
        if not rig_hook:
            rig_hook = self.get_first_hook()
        tpl_root = self.get_structure('root')[0]
        tpl_chain = self.get_structure('chain')
        tpl_hips = self.get_structure('hips')[0]
        tpl_spine1 = self.get_structure('spine1')[0]
        tpl_spine2 = self.get_structure('spine2')[0]

        # naming
        n_end = self.get_branch_suffix()
        n_cog = self.get_name('cog')
        n_spine = self.get_name('spine')
        n_pelvis = self.get_name('pelvis')
        n_shoulder = self.get_name('shoulder')

        # ctrl rig
        root_cog = kl.Joint(hook, 'root_' + n_cog + n_end)
        c_cog = kl.Joint(root_cog, 'c_' + n_cog + n_end)
        j_cog = kl.Joint(c_cog, 'j_' + n_cog + n_end)
        create_srt_in(c_cog, k=1)

        j_spine0 = kl.Joint(j_cog, 'j_' + n_spine + '0' + n_end)
        j_spine1 = kl.Joint(j_spine0, 'j_' + n_spine + '1' + n_end)
        j_spine2 = kl.Joint(j_spine1, 'j_' + n_spine + '2' + n_end)
        _j = kl.Joint(j_spine2, 'j_' + n_spine + '_tip' + n_end)

        root_cog.scale_compensate.set_value(False)
        copy_transform(tpl_hips, root_cog, t=1)
        copy_transform(tpl_spine1, j_spine1, t=1)
        copy_transform(tpl_spine2, j_spine2, t=1)
        copy_transform(tpl_chain[-1], _j, t=1)

        if self.get_opt('orient_spine'):
            orient_joint([j_spine0, j_spine1, j_spine2], aim='y', up='x', up_dir=(0, 0, 1))
        _j.remove_from_parent()

        root_spine1 = kl.Joint(j_spine1, 'root_' + n_spine + '1' + n_end)
        c_spine1 = kl.Joint(root_spine1, 'c_' + n_spine + '1' + n_end)
        root_spine1.reparent(j_spine0)
        j_spine1.reparent(c_spine1)
        create_srt_in(c_spine1, k=1)

        root_spine2 = kl.Joint(j_spine2, 'root_' + n_spine + '2' + n_end)
        c_spine2 = kl.Joint(root_spine2, 'c_' + n_spine + '2' + n_end)
        root_spine2.reparent(j_spine1)
        j_spine2.reparent(c_spine2)
        create_srt_in(c_spine2, k=1)

        root_spineIK = kl.Joint(rig_hook, 'root_' + n_spine + 'IK' + n_end)
        c_spineIK = kl.Joint(root_spineIK, 'c_' + n_spine + 'IK' + n_end)
        tip_spineIK = kl.Joint(c_spineIK, 'tip_' + n_spine + 'IK' + n_end)
        copy_transform(tpl_chain[-1], root_spineIK, t=1)
        root_spineIK.reparent(j_spine2)
        create_srt_in(c_spineIK, k=1)

        if self.get_opt('orient_shoulders'):
            copy_transform(j_spine2, c_spineIK, r=1)

        root_pelvisIK = kl.Joint(rig_hook, 'root_' + n_pelvis + 'IK' + n_end)
        c_pelvisIK = kl.Joint(root_pelvisIK, 'c_' + n_pelvis + 'IK' + n_end)
        copy_transform(tpl_root, root_pelvisIK, t=1)
        root_pelvisIK.reparent(j_cog)
        _srt_pelvisIK = create_srt_in(c_pelvisIK, k=1)

        if self.get_opt('orient_pelvis'):
            copy_transform(j_spine0, c_pelvisIK, r=1)

        opt_pivots = self.get_opt('pivots')
        if opt_pivots == 'spine1':
            copy_transform(j_spine1, root_pelvisIK, t=1)
        elif opt_pivots == 'centered':
            t1 = tpl_spine1.world_transform.get_value().translation()
            t2 = tpl_spine2.world_transform.get_value().translation()
            root_pelvisIK.set_world_transform(M44f((t1 + t2) / 2.0, V3f(0, 0, 0), V3f(1, 1, 1), Euler.XYZ))
            # root_spineIK.set_world_transform(M44f((t1 + t2) / 2.0, V3f(0, 0, 0), V3f(1, 1, 1), Euler.XYZ))
            # copy_transform(tpl_chain[-1], tip_spineIK, t=1)

        # c_cog.sy >> j_spine0.sy
        _s = create_srt_in(j_spine0).find('scale')
        _s.y.connect(c_cog.find('transform/scale').y)

        # c_spine1.sy >> j_spine1.sy
        _s = create_srt_in(j_spine1).find('scale')
        _s.y.connect(c_spine1.find('transform/scale').y)

        # c_spine2.sy >> j_spine2.sy
        _s = create_srt_in(j_spine2).find('scale')
        _s.y.connect(c_spine2.find('transform/scale').y)

        # rotate orders
        for c in (c_cog, c_spine1, c_spine2, c_spineIK, c_pelvisIK):
            _xfo = c.find('transform')
            _xfo.rotate_order.set_value(Euler.XZY)

        set_plug(c_cog.find('transform/scale').x, k=0, min_value=1, max_value=1, lock=True)
        set_plug(c_cog.find('transform/scale').z, k=0, min_value=1, max_value=1, lock=True)

        # spline IK rig
        j_spineIK_dn = kl.Joint(c_pelvisIK, 'j_' + n_spine + 'IK_dn' + n_end)
        j_spineIK_tw = kl.Joint(j_spineIK_dn, 'j_' + n_spine + 'IK_tw' + n_end)
        end_spineIK_tw = kl.Joint(j_spineIK_tw, 'end_' + n_spine + 'IK_tw' + n_end)

        copy_transform(tpl_root, j_spineIK_dn, t=1)
        copy_transform(tpl_spine1, j_spineIK_tw, t=1)
        copy_transform(tpl_spine2, end_spineIK_tw, t=1)

        orient_joint([j_spineIK_dn, j_spineIK_tw, end_spineIK_tw], aim='y', up='x', up_dir=(1, 0, 0))

        j_spineIK_aim = kl.Joint(j_spineIK_tw, 'j_' + n_spine + 'IK_aim' + n_end)
        j_spineIK_aim.reparent(j_spineIK_dn)
        j_spineIK_tw.reparent(j_spineIK_aim)

        root_spineIK_mid = kl.Joint(j_spineIK_tw, 'root_' + n_spine + 'IK_mid' + n_end)

        xyz = Euler.XYZ
        t1 = tpl_spine1.world_transform.get_value().translation()
        t2 = tpl_spine2.world_transform.get_value().translation()
        root_spineIK_mid.set_world_transform(M44f((t1 + t2) / 2.0, V3f(0, 0, 0), V3f(1, 1, 1), xyz))

        c_spineIK_mid = kl.SceneGraphNode(root_spineIK_mid, 'c_' + n_spine + 'IK_mid' + n_end)
        create_srt_in(c_spineIK_mid, k=1)
        j_spineIK_mid = kl.Joint(c_spineIK_mid, 'j_' + n_spine + 'IK_mid' + n_end)

        j_spineIK_up = kl.Joint(tip_spineIK, 'j_' + n_spine + 'IK_up' + n_end)
        end_spineIK_up = kl.Joint(j_spineIK_up, 'end_' + n_spine + 'IK_up' + n_end)

        copy_transform(tpl_spine2, end_spineIK_up, t=1)
        orient_joint([j_spineIK_up, end_spineIK_up], aim='-y', up='x', up_dir=(1, 0, 0))

        aim_constraint(end_spineIK_up, j_spineIK_aim, aim_vector=(0, 1, 0), up_vector=(0, 0, 0))
        tx = twist_constraint(end_spineIK_up, j_spineIK_tw, twist_vector=(0, 1, 0))
        # srt = create_srt_out(j_spineIK_tw, vectors=False, ro=RotateOrder.yzx)
        # connect_mult(j_spineIK_tw.ry, -0.5, root_spineIK_mid.ry)
        tx.enable_in.set_value(0.5)

        default_curvature = self.get_opt('curvature')
        add_plug(c_spineIK_mid, 'curvature', float, k=1, default_value=default_curvature, min_value=0, max_value=1, step=0.05, nice_name='Curvature')
        loc_spineIK_mid1 = kl.SceneGraphNode(j_spineIK_dn, 'loc_' + n_spine + 'IK_mid1' + n_end)
        loc_spineIK_mid2 = kl.SceneGraphNode(j_spineIK_up, 'loc_' + n_spine + 'IK_mid2' + n_end)

        copy_transform(tpl_spine1, loc_spineIK_mid1, t=1)
        xfo0 = loc_spineIK_mid1.transform.get_value()
        copy_transform(tpl_spine2, loc_spineIK_mid1, t=1)
        xfo1 = loc_spineIK_mid1.transform.get_value()

        blend = kl.BlendTransformsNode(loc_spineIK_mid1, 'blend_transform')
        blend.transform1_in.set_value(xfo0)
        blend.transform2_in.set_value(xfo1)
        blend.blend_in.connect(c_spineIK_mid.curvature)
        loc_spineIK_mid1.transform.connect(blend.transform_out)

        copy_transform(tpl_spine2, loc_spineIK_mid2, t=1)
        xfo0 = loc_spineIK_mid2.transform.get_value()
        copy_transform(tpl_spine1, loc_spineIK_mid2, t=1)
        xfo1 = loc_spineIK_mid2.transform.get_value()

        blend = kl.BlendTransformsNode(loc_spineIK_mid2, 'blend_transform')
        blend.transform1_in.set_value(xfo0)
        blend.transform2_in.set_value(xfo1)
        blend.blend_in.connect(c_spineIK_mid.curvature)
        loc_spineIK_mid2.transform.connect(blend.transform_out)

        point_constraint([loc_spineIK_mid1, loc_spineIK_mid2], root_spineIK_mid)

        # curve rig
        cv_spine = kl.SceneGraphNode(find_root(), 'cv_' + n_spine)
        geo_spine = kl.SplineCurve(cv_spine, 'cv_' + n_spine + 'Shape')

        p0 = tpl_root.world_transform.get_value().translation()
        p1 = tpl_spine1.world_transform.get_value().translation()
        p2 = tpl_spine2.world_transform.get_value().translation()
        p3 = tpl_chain[-1].world_transform.get_value().translation()

        cvs = [p0, p0, p1, p2, p3, p3]
        knots = generate_knot_vector(2, len(cvs))
        weights = [1] * len(cvs)
        spline_data = kl.Spline(cvs, knots, weights, False)
        geo_spine.spline_in.set_value(spline_data)
        cv_spine.reparent(hook)
        cv_spine.show.set_value(False)

        rebuild_curve(geo_spine, 3, 7)

        trim = len(find_root().get_full_name()) + 1
        joint_names = {}
        joints = []
        for j in [j_spineIK_dn, j_spineIK_mid, j_spineIK_up]:
            joint_names[j.get_name()] = len(joint_names)
            joints.append(j.get_full_name()[trim:])

        # hack skin
        bpm_skin_curve = kl.SceneGraphNode(hook, 'bpm_' + n_spine + '_curve' + n_end)
        bpm_spineIK_dn = kl.SceneGraphNode(j_spineIK_dn, 'bpm_' + n_spine + 'IK_dn' + n_end)
        bpm_spineIK_mid = kl.SceneGraphNode(j_spineIK_mid, 'bpm_' + n_spine + 'IK_mid' + n_end)
        bpm_spineIK_up = kl.SceneGraphNode(j_spineIK_up, 'bpm_' + n_spine + 'IK_up' + n_end)
        for node in (bpm_spineIK_dn, bpm_spineIK_mid, bpm_spineIK_up):
            node.reparent(bpm_skin_curve)

        # load weights
        skin_data = {
            'deformer': 'skin',
            'transform': cv_spine,
            'data': {
                'infs': {0: j_spineIK_dn, 1: j_spineIK_mid, 2: j_spineIK_up},
                'maps': {
                    0: mk.WeightMap("1*2 0.75 0*4"),
                    1: mk.WeightMap("0*2 0.25 1 0.25 0*2"),
                    2: mk.WeightMap("0*4 0.75 1*2")
                },
                'bind_pose': {0: bpm_spineIK_dn, 1: bpm_spineIK_mid, 2: bpm_spineIK_up}
            }
        }
        dfm_skin = mk.Deformer(**skin_data)
        dfm_skin.build()
        cv_spine_geo = dfm_skin.geometry

        # build ik chain
        root_spine = kl.Joint(c_pelvisIK, 'root_' + n_spine)

        num_sk = self.get_opt('bones')
        bone_length = self.get_opt('bones_length')
        ik_chain = create_joints_on_curve(cv_spine_geo, num_sk, mode=bone_length, name='ik_{n}{{i}}{e}'.format(n=n_spine, e=n_end))
        ik_chain[0].reparent(root_spine)

        orient_joint(ik_chain, aim='y', up='x', up_dir=(1, 0, 0))
        copy_transform(tip_spineIK, ik_chain[-1], t=1, r=1)

        # stretch spline IK
        spline_ik = stretch_spline_IK(cv_spine_geo, ik_chain)
        spline_ik.set_parent(hook)

        # twist
        spline_ik.up_vector_in.set_value(V3f(1, 0, 0))
        spline_ik.start_up_vector_space_in.connect(j_spineIK_dn.world_transform)
        spline_ik.start_up_vector_in_space_in.set_value(V3f(1, 0, 0))
        spline_ik.end_up_vector_space_in.connect(j_spineIK_up.world_transform)
        spline_ik.end_up_vector_in_space_in.set_value(V3f(1, 0, 0))

        # switch attrs
        c_switch = kl.SceneGraphNode(root_cog, 'c_' + n_spine + '_switch')
        add_plug(c_switch, 'stretch', float, k=1, default_value=0, min_value=0, max_value=1, nice_name='Stretch')
        add_plug(c_switch, 'squash', float, k=1, default_value=0, min_value=0, max_value=1, nice_name='Squash')
        add_plug(c_switch, 'slide', float, k=1, default_value=0, min_value=-1, max_value=1, nice_name='Slide')
        spline_ik.stretch.connect(c_switch.stretch)
        spline_ik.squash.connect(c_switch.squash)
        spline_ik.slide.connect(c_switch.slide)

        add_plug(c_switch, 'stretch_mode', int, enum=['scale', 'translate'], nice_name='Stretch Mode')
        c_switch.stretch_mode.set_value({'scale': 0, 'translate': 1}[self.get_opt('stretch_mode')])

        for c in (c_cog, c_pelvisIK, c_spineIK, c_spineIK_mid, c_spine1, c_spine2):
            add_plug(c, '_stretch', float, k=1)
            add_plug(c, '_squash', float, k=1)
            add_plug(c, '_slide', float, k=1)
            add_plug(c, '_stretch_mode', int, k=1)
            c._stretch.connect(c_switch.stretch)
            c._squash.connect(c_switch.squash)
            c._slide.connect(c_switch.slide)
            c._stretch_mode.connect(c_switch.stretch_mode)

        add_plug(c_switch, 'stretch_spline_up', bool, default_value=True)
        add_plug(c_switch, 'stretch_spline_dn', bool, default_value=True)
        j_spineIK_up.scale_compensate.connect(c_switch.stretch_spline_up)
        j_spineIK_dn.scale_compensate.connect(c_switch.stretch_spline_dn)

        if self.get_opt('default_stretch'):
            c_switch.stretch.set_value(1)

        # skin joints
        root_pelvis = kl.Joint(c_pelvisIK, 'root_' + n_pelvis + n_end)
        sk_pelvis = kl.Joint(root_pelvis, 'sk_' + n_pelvis + n_end)
        end_pelvis = kl.Joint(find_root(), 'end_' + n_pelvis + n_end)

        copy_transform(tpl_root, root_pelvis, t=1)
        copy_transform(tpl_hips, end_pelvis, t=1)
        end_pelvis.reparent(sk_pelvis)

        c_pelvis = kl.SceneGraphNode(root_pelvis, 'c_' + n_pelvis + n_end)
        _srt_pelvis = create_srt_in(c_pelvis, k=1)
        _srt = create_srt_in(sk_pelvis)
        _srt.translate.connect(_srt_pelvis.translate)
        _srt.rotate.connect(_srt_pelvis.rotate)

        connect_mult(_srt_pelvis.find('scale').x, _srt_pelvisIK.find('scale').x, _srt.find('scale').x)
        connect_mult(_srt_pelvis.find('scale').y, _srt_pelvisIK.find('scale').y, _srt.find('scale').y)
        connect_mult(_srt_pelvis.find('scale').z, _srt_pelvisIK.find('scale').z, _srt.find('scale').z)

        sk_chain = []
        for i, ik in enumerate(ik_chain):
            sk = kl.Joint(ik, ik.get_name().replace('ik_', 'sk_'))
            safe_connect(c_switch.stretch_mode, sk.scale_compensate)
            sk_chain.append(sk)
            if i < len(ik_chain) - 1:
                _j = kl.Joint(ik_chain[i + 1], ik.get_name().replace('ik_', 'end_'))
                _j.reparent(sk_chain[-1])

        o_spine0 = [n for n in sk_chain[-2].get_children() if isinstance(n, kl.Joint)][0]
        o_spine0 = kl.Joint(o_spine0, 'o_' + n_spine + str(len(ik_chain) - 1))
        o_spine0.reparent(ik_chain[-2])
        orient_joint(o_spine0, aim_tgt=None, aim='y', aim_dir=(0, 1, 0), up='z', up_dir=[0, 0, 1])

        o_spine = kl.Joint(o_spine0, 'o_' + n_spine + str(len(ik_chain)))
        o_spine.reparent(ik_chain[-1])

        _oc = orient_constraint([o_spine0, c_spineIK], o_spine, mo=1)

        _oc.w1.connect(c_switch.stretch)
        connect_reverse(c_switch.stretch, _oc.w0)

        # tmp srt hack
        _oc = orient_constraint(o_spine, sk_chain[-1])
        _srt_out = create_srt_out(_oc, vectors=False)
        create_srt_in(sk_chain[-1], vectors=False).rotate.connect(_srt_out.rotate)

        '''
        if self.get_opt('orient_shoulders'):
            pm.delete(pm.orientConstraint(c_spineIK, o_spine))
        '''

        skx = []
        skz = []
        for sk in sk_chain:
            _srt = create_srt_in(sk)
            skx.append(_srt.find('scale').x)
            skz.append(_srt.find('scale').z)

        blend_smooth_remap([c.find('transform/scale').x for c in (c_pelvisIK, c_spine1, c_spine2, c_spineIK)], skx)
        blend_smooth_remap([c.find('transform/scale').z for c in (c_pelvisIK, c_spine1, c_spine2, c_spineIK)], skz)

        for i, ik in enumerate(ik_chain):
            if ik.get_dynamic_plug('squash'):
                sk = sk_chain[i]
                _s = sk.find('transform/scale')
                connect_mult(ik.squash, _s.x.get_input(), _s.x)
                connect_mult(ik.squash, _s.z.get_input(), _s.z)

        sk_chain[-1].find('transform/scale').y.connect(c_spineIK.find('transform/scale').y)

        # scale limits
        for c in (c_spineIK, c_pelvisIK, c_pelvis):
            _s = c.find('transform/scale')
            for dim in 'xyz':
                set_plug(_s.get_plug(dim), min_value=0.01)

        _srt = c_spineIK_mid.find('transform')
        for attr in ('scale', 'rotate'):
            for dim in 'xyz':
                plug = _srt.find(attr).get_plug(dim)
                set_plug(plug, k=0, lock=1)

        # spine hooks
        hook_pelvis = kl.SceneGraphNode(rig_hook, 'hook_' + n_pelvis + n_end)
        hook_pelvis.transform.connect(end_pelvis.world_transform)
        s_pelvis = kl.Joint(hook_pelvis, 's_' + n_pelvis + n_end)
        _srt = create_srt_in(s_pelvis, vectors=False)
        _srt.scale.connect(sk_pelvis.find('transform').scale)

        hook_shoulders = kl.SceneGraphNode(rig_hook, 'hook_' + n_shoulder + 's' + n_end)
        hook_shoulders.transform.connect(o_spine.world_transform)
        s_shoulders = kl.Joint(hook_shoulders, 's_' + n_shoulder + 's' + n_end)
        _srt = create_srt_in(s_shoulders, vectors=False)
        _srt.scale.connect(sk_chain[-1].find('transform').scale)

        # vis group
        grp = mk.Group.create('{}{} shape'.format(self.name, self.get_branch_suffix(' ')))
        for c in (c_spineIK_mid, c_pelvis):
            grp.add_member(c)
        self.set_id(grp.node, 'vis.shape')

        # tag nodes
        self.set_hook(tpl_hips, s_pelvis, 'hooks.pelvis')
        self.set_hook(tpl_chain[-1], s_shoulders, 'hooks.shoulders')
        for i in range(len(tpl_chain) - 1):
            self.set_hook(tpl_chain[i], ik_chain[i], 'hooks.spine.{}'.format(i))

        self.set_id(root_cog, 'roots.cog')
        self.set_id(root_spine1, 'roots.spine1')
        self.set_id(root_spine1, 'roots.spine2')
        self.set_id(root_pelvisIK, 'roots.pelvisIK')
        self.set_id(root_pelvis, 'roots.pelvis')
        self.set_id(root_spineIK, 'roots.spineIK')
        self.set_id(root_spineIK_mid, 'roots.spine_mid')

        self.set_id(hook_pelvis, 'roots.hooks.pelvis')
        self.set_id(hook_shoulders, 'roots.hooks.shoulders')
        self.set_id(cv_spine, 'node.curve')
        self.set_id(bpm_skin_curve, 'node.bpm')

        if self.get_opt('do_ctrl'):
            self.set_id(c_cog, 'ctrls.cog')
            self.set_id(c_spine1, 'ctrls.spine1')
            self.set_id(c_spine2, 'ctrls.spine2')
            self.set_id(c_pelvisIK, 'ctrls.pelvisIK')
            self.set_id(c_pelvis, 'ctrls.pelvis')
            self.set_id(c_spineIK, 'ctrls.spineIK')
            self.set_id(c_spineIK_mid, 'ctrls.spine_mid')
            self.set_id(c_switch, 'ctrls.switch')

        if self.get_opt('do_skin'):
            self.set_id(sk_pelvis, 'skin.pelvis')
            for i, sk in enumerate(sk_chain):
                self.set_id(sk, 'skin.{}'.format(i))
                self.set_id(sk, 'skin.chain.{}'.format(i))
            self.set_id(sk_chain[-1], 'skin.tip')

        for i, j in enumerate(ik_chain):
            self.set_id(j, 'ik.{}'.format(i))

        self.set_id(c_cog, 'space.cog')
        self.set_id(end_pelvis, 'space.pelvis')
        self.set_id(ik_chain[-1], 'space.shoulders')
