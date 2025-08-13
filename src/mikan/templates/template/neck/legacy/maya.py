# coding: utf-8

from six.moves import range

from mikan.maya import cmds as mc
import mikan.maya.cmdx as mx

import mikan.maya.core as mk
from mikan.core.prefs import Prefs
from mikan.maya.lib.connect import *
from mikan.maya.lib.rig import (
    copy_transform, orient_joint, axis_to_vector, stretch_spline_ik,
    fix_orient_constraint_flip, fix_inverse_scale, create_joints_on_curve
)
from mikan.maya.lib.nurbs import create_curve_weightmaps


class Template(mk.Template):

    def build_template(self, data):
        root = self.node

        with mx.DagModifier() as md:
            head = md.create_node(mx.tJoint, parent=root)
            head_tip = md.create_node(mx.tJoint, parent=head)

        root['t'] = (0, 0.1, 0)
        head['t'] = (0, 1, 0.1)
        head_tip['t'] = (0, 3, 0)

    def rename_template(self):
        chain = self.get_structure('chain')
        last = len(chain) - 1

        for i, j in enumerate(chain):
            if i == 0:
                continue
            if j.is_referenced():
                continue

            sfx = i + 1
            if i == last:
                sfx = 'tip'
            elif i == last - 1:
                sfx = 'head'
            j.rename('tpl_{}_{}'.format(self.name, sfx))

    def build_rig(self):

        # init
        hook = self.hook
        rig_hook = mk.Nodes.get_id('::rig')
        if not rig_hook:
            rig_hook = self.get_first_hook()

        n_end = self.get_branch_suffix()
        n_neck = self.name
        n_head = self.get_name('head')

        tpl_chain = self.get_structure('chain[:-1]')
        tpl_head = self.get_structure('head[0]')
        tpl_tip = self.get_structure('end[0]')

        aim_axis = self.get_opt('aim_axis')
        up_axis = self.get_opt('up_axis')

        do_offset = self.get_opt('offset_ctrl')

        # switch ctrl
        root_switch = mx.create_node(mx.tTransform, parent=rig_hook, name='root_' + n_neck + '_switch' + n_end)
        mc.reorder(str(root_switch), front=1)

        root_switch['v'] = False
        for attr in ['t', 'r', 's', 'v']:
            root_switch[attr].lock()

        c_switch = mk.Control.create_control_shape(root_switch, n='c_' + n_neck + '_switch' + n_end)

        # build chain
        n = {}
        chain = []

        self.n = n
        n['chain'] = chain

        for i, tpl in enumerate(tpl_chain):
            nodes = {}
            chain.append(nodes)

            n_chain = '{}{}'.format(n_neck, i + 1)

            parent = hook
            if i > 0:
                parent = chain[i - 1]['ctrl']

            nodes['ctrl'] = mx.create_node(mx.tJoint, parent=parent, name='c_' + n_chain + n_end)
            copy_transform(tpl, nodes['ctrl'], t=True)

        n['c_h'] = chain[-1]['ctrl']
        n['c_h'].rename('c_' + n_head + n_end)

        orient_joint([nodes['ctrl'] for nodes in chain], aim=aim_axis, up=up_axis, up_dir=(1, 0, 0))
        orient_joint(n['c_h'], aim=aim_axis, up=up_axis, aim_dir=(0, 1, 0), up_dir=(1, 0, 0))

        legacy = Prefs.get('template/neck.legacy/rotate_orders', 1)
        if legacy == 1:
            n['c_h']['ro'] = mx.Euler.XZY

        # IK offset
        n['c_last'] = n['c_h']

        if do_offset:
            n['root_ho'] = mx.create_node(mx.tJoint, parent=n['c_h'], name='root_' + n_head + '_offset' + n_end)
            n['c_ho'] = mx.create_node(mx.tJoint, parent=n['root_ho'], name='c_' + n_head + '_offset' + n_end)
            if legacy == 1:
                n['c_ho']['ro'] = mx.Euler.XZY

            n['c_last'] = n['c_ho']

        # build control rig
        for i, tpl in enumerate(tpl_chain):
            nodes = chain[i]
            n_chain = '{}{}'.format(n_neck, i + 1)

            nodes['root'] = mx.create_node(mx.tJoint, parent=hook, name='root_' + n_chain + n_end)
            copy_transform(tpl, nodes['root'], t=True)
            fix_inverse_scale(nodes['root'])

            mc.parent(str(nodes['ctrl']), str(nodes['root']))
            if i > 0:
                mc.parent(str(nodes['root']), str(chain[i - 1]['ctrl']))

        # ik spline rig
        j_neckIK_dn = mx.create_node(mx.tJoint, parent=chain[0]['root'], name='j_' + n_neck + 'IK_dn' + n_end)
        end_neckIK_dn = mx.create_node(mx.tJoint, parent=j_neckIK_dn, name='end_' + n_neck + 'IK_dn' + n_end)
        j_neckIK_up = mx.create_node(mx.tJoint, parent=n['c_last'], name='j_' + n_neck + 'IK_up' + n_end)
        end_neckIK_up = mx.create_node(mx.tJoint, parent=j_neckIK_up, name='end_' + n_neck + 'IK_up' + n_end)

        cps = [tpl_chain[0].translation(mx.sWorld)]
        if len(tpl_chain) == 2:
            mc.delete(mx.cmd(mc.pointConstraint, tpl_chain, end_neckIK_dn))
            mc.delete(mx.cmd(mc.pointConstraint, tpl_chain, end_neckIK_up))
            cps.append(end_neckIK_dn.translation(mx.sWorld))
        else:
            copy_transform(chain[1]['root'], end_neckIK_dn, t=True)
            copy_transform(chain[-2]['root'], end_neckIK_up, t=True)
            for nodes in chain[1:-1]:
                cps.append(nodes['root'].translation(mx.sWorld))
        cps.append(tpl_chain[-1].translation(mx.sWorld))

        orient_joint((j_neckIK_dn, end_neckIK_dn), aim='y', up='x', up_dir=(1, 0, 0))
        orient_joint((j_neckIK_up, end_neckIK_up), aim='-y', up='x', up_dir=(1, 0, 0))

        mc.orientConstraint(str(chain[0]['ctrl']), str(j_neckIK_dn), mo=1, n='_ox#')
        blend = mx.create_node(mx.tPairBlend, name='_pb#')
        for dim in 'xyz':
            plug = j_neckIK_dn['r' + dim]
            plug_input = plug.input(plug=True)
            if plug_input.node().is_a(mx.tUnitConversion):
                plug_input = plug_input.node()['input'].input(plug=True)
            plug_input >> blend['ir' + dim + '2']
            plug.disconnect(destination=False)

        mc.aimConstraint(str(chain[-1]['ctrl']), str(j_neckIK_dn), aim=axis_to_vector(aim_axis), wut='none', mo=1, n='_ax#')
        for dim in 'xyz':
            plug = j_neckIK_dn['r' + dim]
            plug_input = plug.input(plug=True)
            if plug_input.node().is_a(mx.tUnitConversion):
                plug_input = plug_input.node()['input'].input(plug=True)
            plug_input >> blend['ir' + dim + '1']
            plug.disconnect(destination=False)

            blend['or' + dim] >> plug

        blend['weight'] = self.get_opt('rigidity_dn')
        if self.get_opt('rigidity'):
            c_switch.add_attr(mx.Double('rigidity_dn', keyable=True, min=0, max=1, default=self.get_opt('rigidity_dn')))
            c_switch['rigidity_dn'] >> blend['weight']

        if len(tpl_chain) > 2:
            mc.aimConstraint([str(c['ctrl']) for c in chain[1:-1]], str(j_neckIK_up), aim=axis_to_vector(aim_axis) * -1, wut='none', n='_ax#', mo=1)
        else:
            mc.aimConstraint(str(end_neckIK_dn), str(j_neckIK_up), aim=axis_to_vector(aim_axis) * -1, wut='none', n='_ax#', mo=1)

        blend = mx.create_node(mx.tPairBlend, name='_pb#')
        for dim in 'xyz':
            plug = j_neckIK_up['r' + dim]
            blend['ir' + dim + '2'] = plug
            plug_input = plug.input(plug=True)
            if plug_input.node().is_a(mx.tUnitConversion):
                plug_input = plug_input.node()['input'].input(plug=True)
            plug_input >> blend['ir' + dim + '1']
            plug.disconnect(destination=False)
            blend['or' + dim] >> plug

        blend['weight'] = self.get_opt('rigidity_up')
        if self.get_opt('rigidity'):
            c_switch.add_attr(mx.Double('rigidity_up', keyable=True, min=0, max=1, default=self.get_opt('rigidity_up')))
            c_switch['rigidity_up'] >> blend['weight']

        # skin curve
        cv_neck = mc.curve(d=2, p=cps)
        cv_neck = mx.encode(cv_neck)
        mc.parent(str(cv_neck), str(nodes['root']))
        cv_neck.shape()['dispCV'] = 1
        cv_neck['v'] = False

        infs = [j_neckIK_dn, j_neckIK_up]
        maps = [mk.WeightMap("1 0.5 0"), mk.WeightMap("0 0.5 1")]

        # -- rebuild curve
        if len(tpl_chain) > 2:
            spans = len(tpl_chain) * 2 - 4
            mc.rebuildCurve(str(cv_neck), d=3, s=spans, ch=0)

            # update maps
            maps = create_curve_weightmaps(cv_neck, infs)

        bpm_skin_curve = mx.create_node(mx.tTransform, parent=nodes['root'], name='bpm_' + n_neck + '_curve' + n_end)
        bpm_spineIK_dn = mx.create_node(mx.tJoint, parent=j_neckIK_dn, name='bpm_' + n_neck + 'IK_dn' + n_end)
        bpm_spineIK_up = mx.create_node(mx.tJoint, parent=j_neckIK_up, name='bpm_' + n_neck + 'IK_up' + n_end)
        mc.parent(str(bpm_spineIK_dn), str(bpm_spineIK_up), str(bpm_skin_curve))
        bpm_skin_curve['v'] = False

        bpms = [bpm_spineIK_dn, bpm_spineIK_up]

        skin_data = {
            'deformer': 'skin',
            'transform': cv_neck,
            'data': {
                'infs': dict(enumerate(infs)),
                'maps': dict(enumerate(maps)),
                'bind_pose': dict(enumerate(bpms)),
            }
        }
        skin_dfm = mk.Deformer(**skin_data)
        skin_dfm.build()
        skin_dfm.set_protected(True)

        cv_neck['wm'][0] >> skin_dfm.node['geomMatrix']

        # ik joints
        num_bones = self.get_opt('bones')
        bone_length = self.get_opt('bones_length')
        bone_length = {'parametric': 0, 'cvs': 1, 'equal': 2}[bone_length]
        ik_chain = create_joints_on_curve(cv_neck, num_bones, mode=bone_length, name='ik_{n}{{i}}{e}'.format(n=n_neck, e=n_end))
        mc.parent(str(ik_chain[0]), str(chain[0]['root']))

        orient_joint(ik_chain, aim=aim_axis, up=up_axis, up_dir=(1, 0, 0))
        copy_transform(n['c_h'], ik_chain[-1], r=True)

        # rig ik
        ik_spline = stretch_spline_ik(cv_neck, ik_chain, mode=0, connect_scale=True)
        mc.parent(str(ik_spline), str(chain[0]['root']))
        ik_spline.rename('ik_' + n_neck)

        # -- twist
        j_tw = mx.create_node(mx.tJoint, parent=chain[0]['root'], name='j_' + n_neck + '_twist' + n_end)
        end_tw = mx.create_node(mx.tJoint, parent=j_tw, name='end_' + n_neck + '_twist' + n_end)
        mc.delete(mc.pointConstraint(str(tpl_chain[0]), str(tpl_head), str(end_tw)))
        orient_joint((j_tw, end_tw), aim='y', up='-x')
        j_tw['ro'] = mx.Euler.YZX
        j_tw['v'] = False

        ik_tw = mc.ikHandle(sj=str(j_tw), ee=str(end_tw), sol='ikSCsolver')
        ik_tw = mx.encode(ik_tw[0])
        copy_transform(n['c_h'], ik_tw, t=True)
        mc.parent(str(ik_tw), str(n['c_last']))
        connect_mult(j_tw['ry'], (num_bones - 1.0) / num_bones, ik_spline['twist'])

        # neck mid-cluster
        root_neckIK_mid = mx.create_node(mx.tTransform, parent=j_neckIK_dn, name='root_' + n_neck + 'IK_mid' + n_end)
        c_neckIK_mid = mx.create_node(mx.tTransform, parent=root_neckIK_mid, name='c_' + n_neck + 'IK_mid' + n_end)

        if len(tpl_chain) > 2:
            mx.cmd(mc.pointConstraint, end_neckIK_dn, end_neckIK_up, root_neckIK_mid, n='_px#')
        else:
            mx.cmd(mc.pointConstraint, j_neckIK_dn, end_neckIK_dn, j_neckIK_up, end_neckIK_up, root_neckIK_mid, n='_px#')

        _o = mx.cmd(mc.orientConstraint, j_neckIK_dn, j_neckIK_up, root_neckIK_mid, n='_ox#')
        _o = mx.encode(_o[0])
        fix_orient_constraint_flip(_o)

        wm = mk.WeightMap("0 2 0")
        if len(tpl_chain) > 2:
            _maps = create_curve_weightmaps(cv_neck, [j_neckIK_dn, root_neckIK_mid, j_neckIK_up])
            wm = _maps[1]

        clst_data = {
            'deformer': 'cluster',
            'transform': cv_neck,
            'data': {
                'handle': c_neckIK_mid,
                'bind_pose': root_neckIK_mid,
                'maps': {
                    0: wm,
                }
            },
        }
        clst_dfm = mk.Deformer(**clst_data)
        clst_dfm.build()
        clst_dfm.set_protected(True)

        # stretch attributes
        c_switch.add_attr(mx.Double('stretch', keyable=True, min=0, max=1))
        c_switch.add_attr(mx.Double('squash', keyable=True, min=0, max=1))
        c_switch.add_attr(mx.Double('slide', keyable=True, min=-1, max=1))
        c_switch['stretch'] >> cv_neck['stretch']
        c_switch['squash'] >> cv_neck['squash']
        c_switch['slide'] >> cv_neck['slide']

        if self.get_opt('default_stretch'):
            c_switch['stretch'] = 1

        c_switch.add_attr(mx.Enum('stretch_mode', keyable=False, fields=['scale', 'translate']))
        c_switch['stretch_mode'] = {'scale': 0, 'translate': 1}[self.get_opt('stretch_mode')]
        c_switch['stretch_mode'].channel_box = True

        # skin skeleton
        sk_chain = []
        for i, ik in enumerate(ik_chain[:-1]):
            sk = mx.create_node(mx.tJoint, parent=ik, name=ik.name().replace('ik_', 'sk_'))
            sk_chain.append(sk)

            c_switch['stretch_mode'] >> sk['ssc']
            ik['s'] >> sk_chain[-1]['inverseScale']

            mc.reorder(str(sk), front=1)
            _end = mx.create_node(mx.tJoint, parent=sk, name=ik.name().replace('ik_', 'end_'))
            copy_transform(ik_chain[i + 1], _end, t=True)

        skx = []
        skz = []
        for sk in sk_chain:
            skx.append(sk['sx'])
            skz.append(sk['sz'])
        skx.append(_end['sx'])
        skz.append(_end['sz'])

        bwx = blend_smooth_remap([chain[0]['ctrl']['sx'], c_neckIK_mid['sx'], n['c_h']['sx']], skx)
        bwz = blend_smooth_remap([chain[0]['ctrl']['sz'], c_neckIK_mid['sz'], n['c_h']['sz']], skz)

        for i, ik in enumerate(ik_chain):
            if 'squash' in ik:
                connect_mult(ik['squash'], bwx[i]['o'], sk_chain[i]['sx'])
                connect_mult(ik['squash'], bwz[i]['o'], sk_chain[i]['sz'])

        n['j_h'] = mx.create_node(mx.tJoint, parent=ik_chain[-1], name='j_' + n_head + n_end)
        n['sk_h'] = mx.create_node(mx.tJoint, parent=n['j_h'], name='sk_' + n_head + n_end)
        n['end_h'] = mx.create_node(mx.tJoint, parent=n['sk_h'], name='end_' + n_head + n_end)
        copy_transform(tpl_tip, n['end_h'], t=True)
        orient_joint(n['j_h'], aim=aim_axis, up=up_axis, aim_dir=(0, 1, 0), up_dir=(1, 0, 0))

        mc.orientConstraint(str(n['c_last']), str(n['j_h']), n='_ox#')

        # stretch and squash ctrl
        self._make_scale()

        # space switch mods
        if self.get_opt('space_switch'):
            mk.Mod.add(
                n['c_h'], 'space',
                {
                    'rest_name': 'neck',
                    'targets': [self.get_hook(tag=True), '*::space.cog', '*::space.root', '*::space.world'],
                    'orient': True,
                    'default': [0, 0, 1, 0]
                }
            )

            mk.Mod.add(
                n['c_h'], 'space',
                {
                    'rest_name': 'root',
                    'targets': ['*::space.world'],
                    'point': True,
                }
            )

        # # face cam
        # self._make_cam()

        # switch
        for nodes in chain:
            mk.Control.set_control_shape(c_switch, nodes['ctrl'])
        mk.Control.set_control_shape(c_switch, c_neckIK_mid)

        # hooks
        hook_head = mx.create_node(mx.tTransform, parent=rig_hook, name='hook_' + n_head + n_end)
        connect_matrix(n['sk_h']['wm'][0], hook_head)

        # cleanup
        fix_inverse_scale(list(n['chain'][0]['root'].descendents()))

        # vis group
        grp = mk.Group.create('{}{} shape'.format(n_neck, self.get_branch_suffix(' ')))
        grp.add_member(c_neckIK_mid)
        self.set_id(grp.node, 'vis.shape')

        if do_offset:
            n['c_ho']['v'] = False
            grp = mk.Group.create('{} offset{}'.format(n_neck, self.get_branch_suffix(' ')))
            grp.add_member(n['c_ho'])
            self.set_id(grp.node, 'vis.offset')

        # tags
        self.set_hook(tpl_chain[0], ik_chain[0], 'hooks.neck.0')
        # for i, tpl in enumerate(tpl_chain):
        #     self.set_hook(tpl, ik_neck[i], 'hooks.neck.{}'.format(i))

        self.set_hook(tpl_head, hook_head, 'hooks.head')
        self.set_hook(tpl_tip, hook_head, 'hooks.head')

        for i in range(len(tpl_chain) - 1):
            self.set_id(chain[i]['root'], 'roots.{}'.format(i))

        self.set_id(n['c_h'], 'ctrls.head')
        if do_offset:
            self.set_id(n['c_ho'], 'ctrls.head_offset')
        self.set_id(c_neckIK_mid, 'ctrls.mid')
        for i in range(len(tpl_chain) - 1):
            self.set_id(chain[i]['ctrl'], 'ctrls.fk.{}'.format(i))
            self.set_id(chain[i]['ctrl'], 'ctrls.neck{}'.format(i))  # legacy id
        self.set_id(c_switch, 'ctrls.switch')

        self.set_id(n['sk_h'], 'skin.head')
        for i, sk in enumerate(sk_chain):
            self.set_id(sk, 'skin.neck{}'.format(i))
        self.set_id(sk_chain[-1], 'skin.last')

        self.set_id(n['sk_h'], 'space.head')
        self.set_id(n['j_h'], 'j.head')

        self.set_id(n['end_h'], 'tip')

    def _make_cam(self):
        n = self.n

        rootcam = mx.create_node(mx.tTransform, name='root_facePanel', parent=n['hook_h'])
        mc.parentConstraint(str(n['sk_h']), str(rootcam), n='_prx#')

        cam = mx.create_node(mx.tTransform, name='cam_facePanel', parent=rootcam)
        mx.create_node(mx.tCamera, parent=cam, name='cam_facePanelShape')

        cam['t'] = (0, 0, 10)

        cam['orthographic'] = True
        cam['renderable'] = False
        cam['overscan'] = True
        cam['v'] = False

        n['c_h'].add_attr(mx.Message('camPanel', array=True, indexMatters=False))
        n['c_h']['camPanel'].apend(cam['msg'])

        cam.add_attr(mx.String('name'))
        cam['name'] = 'face panel'

    def _make_scale(self):
        n = self.n

        n_end = self.get_branch_suffix()
        n_head = self.get_name('head')

        do_offset = self.get_opt('offset_ctrl')

        # build
        n['c_s'] = mx.create_node(mx.tTransform, parent=n['j_h'], name='c_' + n_head + '_scale' + n_end)
        n['s_s'] = mx.create_node(mx.tTransform, parent=n['c_s'], name='s_' + n_head + '_scale' + n_end)
        n['neg_s'] = mx.create_node(mx.tTransform, parent=n['s_s'], name='neg_' + n_head + '_scale' + n_end)
        mc.parent(str(n['sk_h']), str(n['neg_s']))

        n['c_h'].add_attr(mx.Double('scale_factor', min=0.1, default=1))
        n['c_h'].add_attr(mx.Double('scale_offset', min=0.1, default=1))
        n['c_h']['scale_factor'].channel_box = True

        n['sk_h']['ssc'] = False
        _s = connect_mult(n['c_h']['scale_factor'], n['c_h']['scale_offset'])

        if do_offset:
            connect_expr('s = h * ho * f', s=n['sk_h']['sx'], h=n['c_h']['sx'], ho=n['c_ho']['sx'], f=_s)
            connect_expr('s = h * ho * f', s=n['sk_h']['sy'], h=n['c_h']['sy'], ho=n['c_ho']['sy'], f=_s)
            connect_expr('s = h * ho * f', s=n['sk_h']['sz'], h=n['c_h']['sz'], ho=n['c_ho']['sz'], f=_s)
        else:
            connect_expr('s = h * f', s=n['sk_h']['sx'], h=n['c_h']['sx'], f=_s)
            connect_expr('s = h * f', s=n['sk_h']['sy'], h=n['c_h']['sy'], f=_s)
            connect_expr('s = h * f', s=n['sk_h']['sz'], h=n['c_h']['sz'], f=_s)

        n['c_h'].add_attr(mx.Double('height'))
        n['c_h']['height'].channel_box = True
        n['c_h']['height'] >> n['sk_h']['ty']

        n['c_s'].add_attr(mx.Double('squash', keyable=True, default=1, min=0, max=1))
        connect_matrix(n['c_s']['im'], n['neg_s'])

        # squash rig
        _spow = mx.create_node(mx.tMultiplyDivide, name='_pow#')
        _spow['op'] = 3  # power
        _kx = connect_driven_curve(n['c_s']['sx'], _spow['input1X'], {-1: 1, 0: 0, 1: 1}, key_style='spline', pre='linear', post='linear')
        _ky = connect_driven_curve(n['c_s']['sy'], _spow['input1Y'], {-1: 1, 0: 0, 1: 1}, key_style='spline', pre='linear', post='linear')
        _kz = connect_driven_curve(n['c_s']['sz'], _spow['input1Z'], {-1: 1, 0: 0, 1: 1}, key_style='spline', pre='linear', post='linear')
        mc.keyTangent(str(_kx), f=(0,), itt='linear', ott='linear')
        mc.keyTangent(str(_ky), f=(0,), itt='linear', ott='linear')
        mc.keyTangent(str(_kz), f=(0,), itt='linear', ott='linear')
        _spow['input2'] = (-0.5, -0.5, -0.5)

        _md1 = mx.create_node(mx.tMultiplyDivide, name='_mult#')
        _md2 = mx.create_node(mx.tMultiplyDivide, name='_mult#')
        _md3 = mx.create_node(mx.tMultiplyDivide, name='_mult#')

        _spow['outputY'] >> _md3['input1X']
        _spow['outputX'] >> _md3['input1Y']
        _spow['outputX'] >> _md3['input1Z']
        _spow['outputZ'] >> _md3['input2X']
        _spow['outputZ'] >> _md3['input2Y']
        _spow['outputY'] >> _md3['input2Z']

        n['c_s']['sx'] >> _md2['input1X']
        n['c_s']['sy'] >> _md2['input1Y']
        n['c_s']['sz'] >> _md2['input1Z']
        _md3['output'] >> _md2['input2']

        n['c_s']['squash'] >> _md1['input1X']
        n['c_s']['squash'] >> _md1['input1Y']
        n['c_s']['squash'] >> _md1['input1Z']
        _md2['output'] >> _md1['input2']

        _rev = connect_reverse(n['c_s']['squash'])
        _md4 = mx.create_node(mx.tMultiplyDivide, name='_mult#')
        _rev >> _md4['input1X']
        _rev >> _md4['input1Y']
        _rev >> _md4['input1Z']
        n['c_s']['sx'] >> _md4['input2X']
        n['c_s']['sy'] >> _md4['input2Y']
        n['c_s']['sz'] >> _md4['input2Z']

        _s = mx.create_node(mx.tPlusMinusAverage, name='_add#')
        _md1['output'] >> _s['input3D'][0]
        _md4['output'] >> _s['input3D'][1]

        _s['output3Dx'] >> n['s_s']['sx']
        _s['output3Dy'] >> n['s_s']['sy']
        _s['output3Dz'] >> n['s_s']['sz']

        # tags
        self.set_id(n['c_s'], 'ctrls.scale')
