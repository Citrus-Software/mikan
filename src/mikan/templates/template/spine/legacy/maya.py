# coding: utf-8

from six.moves import range

from mikan.maya import cmds as mc
import mikan.maya.cmdx as mx

import mikan.maya.core as mk
from mikan.maya.lib.connect import *
from mikan.maya.lib.nurbs import *
from mikan.maya.lib.rig import (
    copy_transform, create_joints_on_curve, orient_joint, stretch_spline_ik,
    fix_orient_constraint_flip, fix_inverse_scale, axis_to_vector
)


class Template(mk.Template):

    def build_template(self, data):
        root = self.node

        with mx.DagModifier() as md:
            spine1 = md.create_node(mx.tJoint, parent=root)
            spine2 = md.create_node(mx.tJoint, parent=spine1)
            spine_tip = md.create_node(mx.tJoint, parent=spine2)

        spine1['t'] = (0, 1, 0.05)
        spine2['t'] = (0, 1.5, -0.2)
        spine_tip['t'] = (0, 1, 0.15)

        with mx.DagModifier() as md:
            hips = md.create_node(mx.tJoint, parent=root)
        hips['ty'] = -0.5
        self.set_template_id(hips, 'hips')

        fix_inverse_scale(list(self.node.descendents()))

    def rename_template(self):

        for s in ('hips', 'spine1', 'spine2', 'tip'):
            j = self.get_structure(s)
            if not j or j[0].is_referenced():
                continue

            sfx = s
            if s.startswith('spine'):
                sfx = s.replace('spine', 'chain')
            j[0].rename('tpl_{}_{}'.format(self.name, sfx))

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
        tpl_tip = self.get_structure('tip')[0]

        # naming
        n_end = self.get_branch_suffix()
        n_cog = self.get_name('cog')
        n_spine = self.get_name('spine')
        n_pelvis = self.get_name('pelvis')
        n_shoulder = self.get_name('shoulder')

        # ctrl rig
        root_cog = mx.create_node(mx.tJoint, parent=hook, name='root_' + n_cog + n_end)
        fix_inverse_scale(root_cog)
        root_cog['ssc'] = False
        c_cog = mx.create_node(mx.tJoint, parent=root_cog, name='c_' + n_cog + n_end)
        j_cog = mx.create_node(mx.tJoint, parent=c_cog, name='j_' + n_cog + n_end)

        j_spine0 = mx.create_node(mx.tJoint, parent=j_cog, name='j_' + n_spine + '0' + n_end)
        j_spine1 = mx.create_node(mx.tJoint, parent=j_spine0, name='j_' + n_spine + '1' + n_end)
        j_spine2 = mx.create_node(mx.tJoint, parent=j_spine1, name='j_' + n_spine + '2' + n_end)
        _j = mx.create_node(mx.tJoint, parent=j_spine2, name='dummy_' + n_spine + '_tip' + n_end)

        copy_transform(tpl_hips, root_cog, t=True)
        copy_transform(tpl_root, j_spine0, t=True)
        copy_transform(tpl_spine1, j_spine1, t=True)
        copy_transform(tpl_spine2, j_spine2, t=True)
        copy_transform(tpl_tip, _j, t=True)

        if self.get_opt('orient_spine'):
            orient_joint([j_spine0, j_spine1, j_spine2], aim='y', up='x', up_dir=(0, 0, 1))

        _j.add_attr(mx.Message('kill_me'))

        root_spine1 = mx.create_node(mx.tJoint, parent=j_spine1, name='root_' + n_spine + '1' + n_end)
        c_spine1 = mx.create_node(mx.tJoint, parent=root_spine1, name='c_' + n_spine + '1' + n_end)
        mc.parent(str(root_spine1), str(j_spine0))
        mc.parent(str(j_spine1), str(c_spine1))

        root_spine2 = mx.create_node(mx.tJoint, parent=j_spine2, name='root_' + n_spine + '2' + n_end)
        c_spine2 = mx.create_node(mx.tJoint, parent=root_spine2, name='c_' + n_spine + '2' + n_end)
        mc.parent(str(root_spine2), str(j_spine1))
        mc.parent(str(j_spine2), str(c_spine2))

        fix_inverse_scale(j_spine1, j_spine2)

        root_spineIK = mx.create_node(mx.tJoint, name='root_' + n_spine + 'IK' + n_end)
        c_spineIK = mx.create_node(mx.tJoint, parent=root_spineIK, name='c_' + n_spine + 'IK' + n_end)
        tip_spineIK = mx.create_node(mx.tJoint, parent=c_spineIK, name='tip_' + n_spine + 'IK' + n_end)
        copy_transform(tpl_tip, root_spineIK, t=True)
        mc.parent(str(root_spineIK), str(j_spine2))

        if self.get_opt('orient_shoulders'):
            copy_transform(j_spine2, c_spineIK, r=True)

        root_pelvisIK = mx.create_node(mx.tJoint, name='root_' + n_pelvis + 'IK' + n_end)
        c_pelvisIK = mx.create_node(mx.tJoint, parent=root_pelvisIK, name='c_' + n_pelvis + 'IK' + n_end)
        copy_transform(tpl_root, root_pelvisIK, t=True)
        mc.parent(str(root_pelvisIK), str(j_cog))

        if self.get_opt('orient_pelvis'):
            copy_transform(j_spine0, c_pelvisIK, r=True)

        opt_pivots = self.get_opt('pivots')
        if opt_pivots == 'spine1':
            copy_transform(j_spine1, root_pelvisIK, t=True)
        elif opt_pivots == 'centered':
            mc.delete(mc.pointConstraint(str(j_spine1), str(j_spine2), str(root_pelvisIK)))

        c_cog['sy'] >> j_spine0['sy']
        c_spine1['sy'] >> j_spine1['sy']
        c_spine2['sy'] >> j_spine2['sy']

        # rotate orders
        for c in (c_cog, c_spine1, c_spine2, c_spineIK, c_pelvisIK):
            c['ro'] = mx.Euler.XZY
            c['ro'].channel_box = True
        for attr in ('sx', 'sz'):
            c_cog[attr].keyable = False
            c_cog[attr].locked = True

        # spline IK rig
        j_spineIK_dn = mx.create_node(mx.tJoint, parent=c_pelvisIK, name='j_' + n_spine + 'IK_dn' + n_end)
        c_pelvisIK['s'] >> j_spineIK_dn['inverseScale']
        j_spineIK_tw = mx.create_node(mx.tJoint, parent=j_spineIK_dn, name='j_' + n_spine + 'IK_tw' + n_end)
        end_spineIK_tw = mx.create_node(mx.tJoint, parent=j_spineIK_tw, name='end_' + n_spine + 'IK_tw' + n_end)
        copy_transform(tpl_root, j_spineIK_dn, t=True)
        copy_transform(tpl_spine1, j_spineIK_tw, t=True)
        copy_transform(tpl_spine2, end_spineIK_tw, t=True)
        orient_joint([j_spineIK_dn, j_spineIK_tw, end_spineIK_tw], aim='y', up='x', up_dir=(1, 0, 0))

        root_spineIK_mid = mx.create_node(mx.tJoint, parent=j_spineIK_tw, name='root_' + n_spine + 'IK_mid' + n_end)
        j_spineIK_tw['s'] >> root_spineIK_mid['inverseScale']
        mc.delete(mc.pointConstraint(str(tpl_spine1), str(tpl_spine2), str(root_spineIK_mid)))

        c_spineIK_mid = mx.create_node(mx.tTransform, parent=root_spineIK_mid, name='c_' + n_spine + 'IK_mid' + n_end)
        j_spineIK_mid = mx.create_node(mx.tJoint, parent=c_spineIK_mid, name='j_' + n_spine + 'IK_mid' + n_end)

        j_spineIK_up = mx.create_node(mx.tJoint, parent=tip_spineIK, name='j_' + n_spine + 'IK_up' + n_end)
        end_spineIK_up = mx.create_node(mx.tJoint, parent=j_spineIK_up, name='end_' + n_spine + 'IK_up' + n_end)
        copy_transform(tpl_spine2, end_spineIK_up, t=True)
        orient_joint([j_spineIK_up, end_spineIK_up], aim='-y', up='x', up_dir=(1, 0, 0))

        _ik = mc.ikHandle(sj=str(j_spineIK_tw), ee=str(end_spineIK_tw), sol='ikSCsolver')
        _ik = mx.encode(_ik[0])
        mc.parent(str(_ik), str(end_spineIK_up))
        j_spineIK_tw['ro'] = mx.Euler.YZX
        connect_mult(j_spineIK_tw['ry'], -0.5, root_spineIK_mid['ry'])

        default_curvature = self.get_opt('curvature')
        c_spineIK_mid.add_attr(mx.Double('curvature', keyable=True, min=0, max=1, default=default_curvature))
        loc_spineIK_mid1 = mx.create_node(mx.tTransform, parent=j_spineIK_dn, name='loc_' + n_spine + 'IK_mid1' + n_end)
        loc_spineIK_mid2 = mx.create_node(mx.tTransform, parent=j_spineIK_up, name='loc_' + n_spine + 'IK_mid2' + n_end)

        copy_transform(tpl_spine1, loc_spineIK_mid1, t=True)
        p0 = loc_spineIK_mid1['t'].read()
        copy_transform(tpl_spine2, loc_spineIK_mid1, t=True)
        p1 = loc_spineIK_mid1['t'].read()
        connect_driven_curve(c_spineIK_mid['curvature'], loc_spineIK_mid1['tx'], {0: p0[0], 1: p1[0]}, pre='constant', post='constant')
        connect_driven_curve(c_spineIK_mid['curvature'], loc_spineIK_mid1['ty'], {0: p0[1], 1: p1[1]}, pre='constant', post='constant')
        connect_driven_curve(c_spineIK_mid['curvature'], loc_spineIK_mid1['tz'], {0: p0[2], 1: p1[2]}, pre='constant', post='constant')

        copy_transform(tpl_spine2, loc_spineIK_mid2, t=True)
        p0 = loc_spineIK_mid2['t'].read()
        copy_transform(tpl_spine1, loc_spineIK_mid2, t=True)
        p1 = loc_spineIK_mid2['t'].read()
        connect_driven_curve(c_spineIK_mid['curvature'], loc_spineIK_mid2['tx'], {0: p0[0], 1: p1[0]}, pre='constant', post='constant')
        connect_driven_curve(c_spineIK_mid['curvature'], loc_spineIK_mid2['ty'], {0: p0[1], 1: p1[1]}, pre='constant', post='constant')
        connect_driven_curve(c_spineIK_mid['curvature'], loc_spineIK_mid2['tz'], {0: p0[2], 1: p1[2]}, pre='constant', post='constant')

        mc.pointConstraint(str(loc_spineIK_mid1), str(loc_spineIK_mid2), str(root_spineIK_mid), n='_px#')

        # curve rig
        cv_spine = create_path(tpl_root, tpl_root, tpl_spine1, tpl_spine2, tpl_tip, tpl_tip, d=2)
        mc.parent(str(cv_spine), str(hook), r=1)
        for cv in cv_spine.shape().inputs(plugs=True, connections=True):
            cv[1].read()
        mx.delete(list(cv_spine.shape().inputs()))
        cv_spine = mc.rebuildCurve(str(cv_spine), d=3, s=4)[0]
        cv_spine = mx.encode(cv_spine)
        cv_spine.shape()['dispCV'] = 1
        cv_spine['v'] = False

        bpm_skin_curve = mx.create_node(mx.tTransform, parent=hook, name='bpm_' + n_spine + '_curve' + n_end)
        bpm_spineIK_dn = mx.create_node(mx.tJoint, parent=j_spineIK_dn, name='bpm_' + n_spine + 'IK_dn' + n_end)
        bpm_spineIK_mid = mx.create_node(mx.tJoint, parent=j_spineIK_mid, name='bpm_' + n_spine + 'IK_mid' + n_end)
        bpm_spineIK_up = mx.create_node(mx.tJoint, parent=j_spineIK_up, name='bpm_' + n_spine + 'IK_up' + n_end)
        mx.cmd(mc.parent, bpm_spineIK_dn, bpm_spineIK_mid, bpm_spineIK_up, bpm_skin_curve)
        bpm_skin_curve['v'] = False

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
                'mi': 2,
                'mmi': False,
                'bind_pose': {
                    0: bpm_spineIK_dn,
                    1: bpm_spineIK_mid,
                    2: bpm_spineIK_up
                }
            }
        }
        skin_dfm = mk.Deformer(**skin_data)
        skin_dfm.build()
        skin_dfm.set_protected(True)
        skin_curve = skin_dfm.node

        cv_spine['wm'][0] >> skin_curve['geomMatrix']

        # ik joints
        num_bones = self.get_opt('bones')
        bone_length = self.get_opt('bones_length')
        bone_length = {'parametric': 0, 'cvs': 1, 'equal': 2}[bone_length]
        ik_spine = create_joints_on_curve(cv_spine, num_bones, mode=bone_length, name='ik_{n}{{i}}{e}'.format(n=n_spine, e=n_end))
        mc.parent(str(ik_spine[0]), str(c_pelvisIK))

        orient_joint(ik_spine, aim='y', up='x', up_dir=(1, 0, 0))
        copy_transform(c_spineIK, ik_spine[-1], r=True)

        ik_spline = stretch_spline_ik(cv_spine, ik_spine, mode=0, connect_scale=True)
        mc.parent(str(ik_spline), str(root_cog))
        ik_spline.rename('ik_' + n_spine)

        # twist spline IK
        ik_spline['dTwistControlEnable'] = True

        if 'dForwardAxis' in ik_spline:
            ik_spline['dWorldUpType'] = 4  # obj rotation up start/end
            _axis = {'x': 0, '+x': 0, '-x': 1, 'y': 2, '+y': 2, '-y': 3, 'z': 4, '+z': 4, '-z': 5}
            _axis_up = {'y': 0, '+y': 0, '-y': 1, 'z': 3, '+z': 3, '-z': 4, 'x': 6, '+x': 6, '-x': 7}
            ik_spline['dForwardAxis'] = _axis['y']
            ik_spline['dWorldUpAxis'] = _axis_up['x']
            ik_spline['dWorldUpVector'] = axis_to_vector('x')
            ik_spline['dWorldUpVectorEnd'] = axis_to_vector('x')
            ik_spline['dTwistValueType'] = 1  # start/end
        else:
            # maya 2015 caca
            ik_spline['dWorldUpType'] = 7  # relative
            ik_spline['dTwistValueType'] = 0
            if 'z' not in ik_spline:
                ik_spline['dWorldUpAxis'] = 3
            else:
                ik_spline['dWorldUpAxis'] = 0

        c_pelvisIK['wm'][0] >> ik_spline['dWorldUpMatrix']
        c_spineIK['wm'][0] >> ik_spline['dWorldUpMatrixEnd']

        # stretch attrs
        root_switch = mx.create_node(mx.tTransform, parent=rig_hook, name='root_' + n_spine + '_switch' + n_end)
        mc.reorder(str(root_switch), front=1)

        root_switch['v'] = False
        for attr in ['t', 'r', 's', 'v']:
            root_switch[attr].lock()

        c_switch = mk.Control.create_control_shape(root_switch, n='c_' + n_spine + '_switch' + n_end)
        c_switch.add_attr(mx.Double('stretch', keyable=True, min=0, max=1))
        c_switch.add_attr(mx.Double('squash', keyable=True, min=0, max=1))
        c_switch.add_attr(mx.Double('slide', keyable=True, min=-1, max=1))
        c_switch['stretch'] >> cv_spine['stretch']
        c_switch['squash'] >> cv_spine['squash']
        c_switch['slide'] >> cv_spine['slide']

        if self.get_opt('default_stretch'):
            c_switch['stretch'] = 1

        c_switch.add_attr(mx.Enum('stretch_mode', keyable=False, fields=['scale', 'translate']))
        c_switch['stretch_mode'] = {'scale': 0, 'translate': 1}[self.get_opt('stretch_mode')]
        c_switch['stretch_mode'].channel_box = True

        c_switch.add_attr(mx.Boolean('stretch_spline_up', keyable=True))
        c_switch.add_attr(mx.Boolean('stretch_spline_dn', keyable=True))
        connect_reverse(c_switch['stretch_spline_up'], j_spineIK_up['ssc'])
        connect_reverse(c_switch['stretch_spline_dn'], j_spineIK_dn['ssc'])

        # skin skeleton
        root_pelvis = mx.create_node(mx.tJoint, parent=c_pelvisIK, name='root_' + n_pelvis + n_end)
        c_pelvisIK['s'] >> root_pelvis['inverseScale']
        sk_pelvis = mx.create_node(mx.tJoint, parent=root_pelvis, name='sk_' + n_pelvis + n_end)
        end_pelvis = mx.create_node(mx.tJoint, parent=sk_pelvis, name='end_' + n_pelvis + n_end)
        copy_transform(tpl_root, root_pelvis, t=True)
        copy_transform(tpl_hips, end_pelvis, t=True)
        mc.reorder(str(root_pelvis), front=1)

        c_pelvis = mx.create_node(mx.tTransform, parent=root_pelvis, name='c_' + n_pelvis + n_end)
        c_pelvis['t'] >> sk_pelvis['t']
        c_pelvis['r'] >> sk_pelvis['r']

        _md = mx.create_node(mx.tMultiplyDivide, name='_mult#')
        c_pelvis['s'] >> _md['i1']
        c_pelvisIK['s'] >> _md['i2']
        _md['o'] >> sk_pelvis['s']

        sk_chain = []
        for i, ik in enumerate(ik_spine):
            sk = mx.create_node(mx.tJoint, parent=ik, name=ik.name().replace('ik_', 'sk_'))
            sk_chain.append(sk)

            c_switch['stretch_mode'] >> sk['ssc']
            ik['s'] >> sk_chain[-1]['inverseScale']

            mc.reorder(str(sk_chain[i]), front=1)
            if i < len(ik_spine) - 1:
                _j = mx.create_node(mx.tJoint, parent=ik_spine[i + 1], name=str(ik).replace('ik_', 'end_'))
                mc.parent(str(_j), str(sk_chain[-1]))

        o_spine = mc.duplicate(str(sk_chain[-2].child()), rr=1, rc=1)[0]
        o_spine = mx.encode(o_spine)
        mc.parent(str(o_spine), str(ik_spine[-2]))
        o_spine.rename('o_' + n_spine + str(len(ik_spine)))
        orient_joint(o_spine, aim='y', aim_dir=(0, 1, 0), up='z', up_dir=[0, 0, 1])
        if self.get_opt('orient_shoulders'):
            copy_transform(c_spineIK, o_spine, r=True)

        skx = []
        skz = []
        for sk in sk_chain:
            skx.append(sk['sx'])
            skz.append(sk['sz'])

        bwx = blend_smooth_remap([c_pelvisIK['sx'], c_spine1['sx'], c_spine2['sx'], c_spineIK['sx']], skx)
        bwz = blend_smooth_remap([c_pelvisIK['sz'], c_spine1['sz'], c_spine2['sz'], c_spineIK['sz']], skz)

        for i, ik in enumerate(ik_spine):
            if 'squash' in ik:
                connect_mult(ik['squash'], bwx[i]['o'], sk_chain[i]['sx'])
                connect_mult(ik['squash'], bwz[i]['o'], sk_chain[i]['sz'])

        c_spineIK['sy'] >> sk_chain[-1]['sy']

        _oc = mc.orientConstraint(str(o_spine), str(c_spineIK), str(ik_spine[-1]), n='_ox#', mo=1)
        _oc = mx.encode(_oc[0])
        fix_orient_constraint_flip(_oc)

        c_switch['stretch'] >> _oc['w1']
        connect_reverse(c_switch['stretch'], _oc['w0'])

        # scale limits
        for lim in (mx.kScaleMinX, mx.kScaleMinY, mx.kScaleMinZ):
            c_spineIK.set_limit(lim, 0.01)
            c_pelvisIK.set_limit(lim, 0.01)
            c_pelvis.set_limit(lim, 0.01)

        for attr in 'sr':
            for dim in ('', 'x', 'y', 'z'):
                c_spineIK_mid[attr + dim].keyable = False
                c_spineIK_mid[attr + dim].lock()

        # spine hooks
        hook_pelvis = mx.create_node(mx.tTransform, parent=rig_hook, name='hook_' + n_pelvis + n_end)
        connect_matrix(end_pelvis['wm'][0], hook_pelvis)
        s_pelvis = mx.create_node(mx.tJoint, parent=hook_pelvis, name='s_' + n_pelvis + n_end)
        sk_pelvis['s'] >> s_pelvis['s']
        s_pelvis['inverseScale'].disconnect()
        s_pelvis['drawStyle'] = 2

        hook_shoulders = mx.create_node(mx.tTransform, parent=rig_hook, name='hook_' + n_shoulder + 's' + n_end)
        connect_matrix(ik_spine[-1]['wm'][0], hook_shoulders)
        s_shoulders = mx.create_node(mx.tJoint, parent=hook_shoulders, name='s_' + n_shoulder + 's' + n_end)
        sk_chain[-1]['s'] >> s_shoulders['s']
        s_shoulders['inverseScale'].disconnect()
        s_shoulders['drawStyle'] = 2

        # fix inverse scale
        fix_inverse_scale(list(root_cog.descendents()))

        # assign switch
        for c in (c_spine1, c_spine2, c_pelvisIK, c_spineIK, c_spineIK_mid):
            mk.Control.set_control_shape(c_switch, c)

        # skin gizmo
        sk_pelvis['radius'] = 2

        # vis group
        grp = mk.Group.create('{}{} shape'.format(self.name, self.get_branch_suffix(' ')))
        for c in (c_spineIK_mid, c_pelvis):
            grp.add_member(c)
        self.set_id(grp.node, 'vis.shape')

        # tag nodes
        self.set_hook(tpl_hips, s_pelvis, 'hooks.pelvis')
        self.set_hook(tpl_tip, s_shoulders, 'hooks.shoulders')
        for i in range(len(tpl_chain) - 1):
            self.set_hook(tpl_chain[i], ik_spine[i], 'hooks.spine.{}'.format(i))

        self.set_id(root_cog, 'roots.cog')
        self.set_id(root_spine1, 'roots.spine1')
        self.set_id(root_spine1, 'roots.spine2')
        self.set_id(root_switch, 'roots.switch')
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

        for i, j in enumerate(ik_spine):
            self.set_id(j, 'ik.{}'.format(i))

        self.set_id(c_cog, 'space.cog')
        self.set_id(end_pelvis, 'space.pelvis')
        self.set_id(ik_spine[-1], 'space.shoulders')
