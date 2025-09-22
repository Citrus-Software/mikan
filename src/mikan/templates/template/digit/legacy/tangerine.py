# coding: utf-8

import meta_nodal_py as kl
from meta_nodal_py.Imath import V3f, M44f

from mikan.core import re_is_int
import mikan.tangerine.core as mk
from mikan.tangerine.lib import *
from mikan.tangerine.lib.rig import *


class Template(mk.Template):

    def build_template(self, data):
        tpl_root = self.node
        tpl_root.rename('tpl_{}{}'.format(self.name, (1, 0)[self.get_opt('meta')]))
        tpl_root.ty.set(0.3)

        tpl_digits = [tpl_root]
        for i in range(data['number'] + 1):
            j = kl.Joint(tpl_digits[-1], 'tpl_{}{}'.format(self.name, i + 1))
            tpl_digits[-1].scale >> j.inverseScale
            tpl_digits.append(j)
            j.ty.set((0.75 ** (i + 1)) * data['length'])

    def build_rig(self):

        # opts
        hook = self.get_hook()

        tpl_chain = self.get_structure('chain')
        if len(tpl_chain) < 2:
            raise RuntimeError('/!\\ template chain must have at least 2 joints')

        tpl_digit = tpl_chain[:-1]
        tpl_end = tpl_chain[-1]

        n_end = self.get_branch_suffix()
        n_chain = self.name

        do_meta = self.get_opt('meta') and len(tpl_digit) > 1
        do_shear = self.get_opt('shear')
        rotate_order = self.get_opt('rotate_order')

        # rename meta
        suffixes = []

        for i, tpl in enumerate(tpl_digit):
            sfx = str(i + 1)
            if do_meta:
                sfx = str(i)
            if re_is_int.match(self.name[-1]):
                sfx = '_' + sfx
            if do_meta and i == 0:
                sfx = '_meta'

            suffixes.append(sfx if len(tpl_digit) > 1 else '')

        # add inf
        chain, chain_sub, chain_trail = self.get_chain()
        if 'inf' not in chain:
            chain.insert(0, 'inf')

        # orient chain
        ref_joints = []
        for i, tpl in enumerate(tpl_chain):
            j = kl.Joint(hook, 'ref_joint')
            if i > 0:
                j.reparent(ref_joints[-1])
            ref_joints.append(j)

            copy_transform(tpl, j, t=1, r=1)
            if self.get_opt('orient') == 'parent':
                copy_transform(hook, j, r=1)

        if self.get_opt('orient') == 'auto':
            aim_axis = self.get_branch_opt('aim_axis')
            up_axis = self.get_opt('up_axis')

            up_dir = self.get_opt('up_dir')
            if up_dir == 'auto':
                up_auto = self.get_opt('up_auto')
                up_auto = {'average': 0, 'each': 1, 'first': 2, 'last': 3}[up_auto]
                orient_joint(ref_joints, aim=aim_axis, up=up_axis, up_auto=up_auto)
            else:
                up_dir = axis_to_vector(up_dir)
                orient_joint(ref_joints, aim=aim_axis, up=up_axis, up_dir=up_dir)

            # get twist axis (rotate order)
            if 'y' in aim_axis:
                bi_axis = 'z'
                if 'z' in up_axis:
                    bi_axis = 'x'
            elif 'x' in aim_axis:
                bi_axis = 'y'
                if 'y' in up_axis:
                    bi_axis = 'z'
            else:
                bi_axis = 'x'
                if 'x' in up_axis:
                    bi_axis = 'y'

        elif rotate_order == 'auto':
            # guess axis from given chain
            _axis = get_stretch_axis(tpl_chain)
            if not _axis:
                raise RuntimeError('/!\\ cannot find orientation from template')
            aim_axis, up_axis, bi_axis = _axis
            if self.do_flip():
                aim_axis = self.branch_opt(aim_axis)
                up_axis = self.branch_opt(up_axis)

        if rotate_order == 'auto':
            rotate_order = aim_axis[-1] + up_axis[-1] + bi_axis[-1]
        rotate_order = str_to_rotate_order(rotate_order)

        # build nodes
        nodes = self.build_chain(ref_joints[:-1], chain=chain, do_flip=False, suffixes=suffixes, rotate_order=rotate_order, do_skin=not do_shear)

        # chain tip
        end = kl.Joint(nodes[-1]['sk'], 'end_' + self.name + self.get_branch_suffix())
        end.scale_compensate.set_value(False)
        copy_transform(tpl_end, end, t=1)
        self.set_hook(tpl_end, end, 'hooks.tip')

        if not do_shear:
            self.set_id(nodes[-1]['sk'], 'hooks.last')
        self.set_id(end, 'tip')

        # hooks
        for i, tpl in enumerate(tpl_digit):
            self.set_hook(tpl, nodes[i]['sk'], 'hooks.{}'.format(i))

        # build digits hook
        target_parent = None
        tag = self.get_opt('target_parent')

        if '::' not in tag:
            branch_id = self.get_branch_id()
            for tpl_parent in self.get_all_parents():
                if branch_id in tpl_parent.get_branch_ids():
                    _tag_parent = '{}{}::{}'.format(tpl_parent.name, branch_id, tag)
                else:
                    _tag_parent = '{}::{}'.format(tpl_parent.name, tag)

                target_parent = mk.Nodes.get_id(_tag_parent)
                if target_parent:
                    break
        else:
            target_parent = mk.Nodes.get_id(tag)

        if target_parent and tag:

            sw = kl.SceneGraphNode(hook, 'sw_' + self.name + '_weights' + n_end)
            self.set_id(sw, 'weights')

            weights = self.get_opt('target_weights')
            if weights is None or len(weights) == 0:
                weights = [1] * len(nodes)
                if do_meta:
                    weights[0] = 0
            weights = weights[:len(nodes)]

            parent = nodes[0]['root']
            target_hook = kl.Joint(parent, 'loc_' + self.name + '_tgt_hook' + n_end)

            _mmx = kl.MultM44f(target_hook, '_mmx')
            _mmx.input[0].connect(target_parent.world_transform)
            _inv = kl.InverseM44f(nodes[0]['root'], '_inv')
            _inv.input.connect(nodes[0]['root'].world_transform)
            _mmx.input[1].connect(_inv.output)
            target_hook.transform.connect(_mmx.output)

            target = kl.SceneGraphNode(target_hook, 'loc_' + self.name + '_tgt' + n_end)
            copy_transform(tpl_end, target, t=1)

            aim_axis = self.get_branch_opt('aim_axis')

            for i, w in enumerate(weights):
                if i > 0 and weights[i - 1] == 1:
                    break

                nodes[i]['aim'] = duplicate_joint(nodes[i]['root'], p=parent, n='aim_' + self.name + suffixes[i] + n_end)
                if i > 0:
                    nodes[i]['aim'].reparent(nodes[i - 1]['aim'])

                if w == 0:
                    continue

                srt_aim = create_srt_in(nodes[i]['aim'], vectors=False)
                jo = srt_aim.joint_orient_rotate.get_value()
                aim = aim_constraint(target, nodes[i]['aim'], mo=1, aim_vector=axis_to_vector(aim_axis), up_vector=V3f(0, 0, 0))
                aim.enable_in.set_value(w)
                srt_aim.joint_orient_rotate.set_value(jo)

                srt_inf = create_srt_in(nodes[i]['inf'], vectors=False)
                srt_inf.rotate.connect(srt_aim.rotate)

                sw_name = 'target_weight{}'.format(i)
                sw_plug = add_plug(sw, sw_name, float, keyable=True, min_value=0, max_value=1, default_value=w)
                aim.enable_in.connect(sw_plug)

        # shear rig
        if do_shear:

            # switch
            sw = kl.SceneGraphNode(hook, 'sw_' + n_chain + '_switch' + n_end)
            self.set_id(sw, 'switch')

            # chain loop
            for i, n in enumerate(nodes):
                # rename sk
                n_chain = self.name + suffixes[i]
                n['sk'].rename('j_' + n_chain + n_end)

                # new skin joints
                n['sk_base'] = kl.Joint(n['sk'], 'sk_' + n_chain + '_base' + n_end)
                self.set_id(n['sk_base'], 'skin.{}'.format(i))
                self.set_id(n['sk_base'], 'skin.base.{}'.format(i))
                n['sk'].gem_id.set_value(n['sk'].gem_id.get_value().replace(n['sk_base'].gem_id.get_value(), ''))

                n['sk_tip'] = kl.Joint(n['sk'], 'sk_' + n_chain + '_tip' + n_end)
                self.set_id(n['sk_tip'], 'skin.tip.{}'.format(i))

                # quaternion probe
                srt = kl.TransformToSRTNode(n['sk'], 'srt')
                srt.transform.connect(n['sk'].transform)
                qe = kl.EulerToQuatf(srt, '_euler')
                qe.rotate.connect(srt.rotate)
                qe.rotate_order.connect(srt.rotate_order)
                n['q'] = kl.QuatfToFloat(qe, '_quat')
                n['q'].quat.connect(qe.quat)

                # scale
                n['sk_base'].scale_compensate.set_value(0)
                n['sk_tip'].scale_compensate.set_value(0)

            self.set_id(nodes[-1]['sk_base'], 'hooks.last')

            # default values
            sh_base_dv = [0] * len(nodes)
            sh_tip_dv = [0] * len(nodes)

            dv = self.get_opt('shear_values')
            if isinstance(dv, (int, float)):
                sh_base_dv = [dv] * len(nodes)
                sh_tip_dv = [dv] * len(nodes)
            elif isinstance(dv, list):
                if len(dv) == len(nodes):
                    sh_base_dv = dv
                    sh_tip_dv = dv[1:]
                elif len(dv) == 2:
                    sh_base_dv = [dv[0]] * len(nodes)
                    sh_tip_dv = [dv[1]] * (len(nodes) - 1)
                elif len(dv) == len(nodes) * 2 - 1:
                    sh_base_dv = dv[::2]
                    sh_tip_dv = dv[1::2]

            # connect loop
            for i, n in enumerate(nodes):
                _shear_base = 'shear_{}_base'.format(suffixes[i])
                _shear_base = add_plug(sw, _shear_base, float, default_value=sh_base_dv[i], min_value=0, max_value=2)

                if i < len(tpl_digit) - 1:
                    _shear_tip = 'shear_{}_tip'.format(suffixes[i])
                    _shear_tip = add_plug(sw, _shear_tip, float, default_value=sh_tip_dv[i], min_value=0, max_value=2)

                # connect
                _qx = connect_mult(n['q'].i, _shear_base)
                _qz = connect_mult(n['q'].k, _shear_base)
                _qz = connect_mult(_qz, -1)

                _ijk = kl.IJKToTransform(n['sk'], '_ijk')
                _i = kl.FloatToV3f(_ijk, 'i')
                _i.x.set_value(1)
                _ijk.i.connect(_i.vector)
                _k = kl.FloatToV3f(_ijk, 'k')
                _k.z.set_value(1)
                _ijk.k.connect(_k.vector)

                connect_expr('v = qx < 0 ? qx : qx * 0.5', v=_k.y, qx=_qx)
                _i.y.connect(_qz)

                n['sk_base'].transform.connect(_ijk.transform)

                if i < len(tpl_digit) - 1:
                    _qx = connect_mult(nodes[i + 1]['q'].i, _shear_tip)
                    _qz = connect_mult(nodes[i + 1]['q'].k, _shear_tip)
                    _qx = connect_mult(_qx, -1)

                    _ijk = kl.IJKToTransform(n['sk'], '_ijk')
                    _i = kl.FloatToV3f(_ijk, 'i')
                    _i.x.set_value(1)
                    _ijk.i.connect(_i.vector)
                    _k = kl.FloatToV3f(_ijk, 'k')
                    _k.z.set_value(1)
                    _ijk.k.connect(_k.vector)

                    connect_expr('v = qx > 0 ? qx : qx * 0.5', v=_k.y, qx=_qx)
                    _i.y.connect(_qz)

                    n['sk_tip'].transform.connect(_ijk.transform)

                    # point
                    mmx = kl.MultM44f(nodes[i]['sk'], '_mmx')
                    mmx.input[0].connect(nodes[i + 1]['sk'].world_transform)
                    imx = kl.InverseM44f(nodes[i]['sk'], '_imx')
                    imx.input.connect(nodes[i]['sk'].world_transform)
                    mmx.input[1].connect(imx.output)

                    srt = create_srt_out(mmx, vectors=False)
                    _ijk.translate.connect(srt.translate)
