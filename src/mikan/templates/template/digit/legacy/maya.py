# coding: utf-8

from six.moves import range

from mikan.maya import cmds as mc
import mikan.maya.cmdx as mx

from mikan.core import re_is_int
import mikan.maya.core as mk
from mikan.maya.lib.connect import *
from mikan.maya.lib.rig import (
    copy_transform, orient_joint, axis_to_vector, get_stretch_axis,
    duplicate_joint, fix_inverse_scale
)


class Template(mk.Template):

    def build_template(self, data):
        tpl_root = self.node
        tpl_root['ty'] = 0.3

        tpl_digits = [tpl_root]
        for i in range(data['number'] + 1):
            with mx.DagModifier() as md:
                j = md.create_node(mx.tJoint, parent=tpl_digits[-1])
            tpl_digits[-1]['scale'] >> j['inverseScale']
            tpl_digits.append(j)
            j['ty'] = (0.75 ** (i + 1)) * data['length']

    def rename_template(self):
        chain = self.get_structure('chain')
        last = len(chain) - 1

        for i, j in enumerate(chain):
            if i == 0:
                continue
            if j.is_referenced():
                continue
            sfx = 'tip' if i == last else i + 1
            j.rename('tpl_{}_{}'.format(self.name, sfx))

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
        chain, chain_sub = self.get_chain()
        if 'inf' not in chain:
            chain.insert(0, 'inf')

        # orient chain
        ref_joints = []
        for i, tpl in enumerate(tpl_chain):
            j = mx.create_node(mx.tJoint, parent=hook, name='dummy_{}{}'.format(n_chain, i))
            if i > 0:
                mc.parent(str(j), str(ref_joints[-1]))
            ref_joints.append(j)

            copy_transform(tpl, j, t=True, r=True)

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
        rotate_order = rotate_order.upper()

        # build nodes
        nodes = self.build_chain(ref_joints[:-1], chain=chain, do_flip=False, suffixes=suffixes, rotate_order=rotate_order, do_skin=not do_shear)

        # mx.delete(ref_joints)
        for j in ref_joints:
            j.add_attr(mx.Message('kill_me'))

        # skin gizmo
        end = mx.create_node(mx.tJoint, parent=nodes[-1]['sk'], name='end_' + self.name + self.get_branch_suffix())
        nodes[-1]['sk']['scale'] >> end['inverseScale']
        end['ssc'] = False
        copy_transform(tpl_end, end, t=True)
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
                    _tag = '{}{}::{}'.format(tpl_parent.name, branch_id, tag)
                else:
                    _tag = '{}::{}'.format(tpl_parent.name, tag)

                target_parent = mk.Nodes.get_id(_tag)
                if target_parent:
                    break
        else:
            target_parent = mk.Nodes.get_id(tag)

        # target rig
        if target_parent and tag:

            root_sw = mx.create_node(mx.tTransform, parent=hook, name='root_' + self.name + '_switch' + n_end)
            mc.reorder(str(root_sw), front=1)
            root_sw['v'] = False
            sw = mk.Control.create_control_shape(root_sw, n='sw_' + self.name + '_weights' + n_end)
            self.set_id(sw, 'weights')

            weights = self.get_opt('target_weights')
            if weights is None or len(weights) == 0:
                weights = [1] * len(nodes)
                if do_meta:
                    weights[0] = 0
            weights = weights[:len(nodes)]

            parent = nodes[0]['root']
            target_hook = mx.create_node(mx.tJoint, parent=parent, name='loc_' + self.name + '_tgt_hook' + n_end)

            target_hook['drawStyle'] = 2
            parent['scale'] >> target_hook['inverseScale']

            _mmx = mx.create_node(mx.tMultMatrix, name='_mmx#')
            target_parent['wm'][0] >> _mmx['i'][0]
            nodes[0]['root']['wim'][0] >> _mmx['i'][1]
            connect_matrix(_mmx['o'], target_hook)

            target = mx.create_node(mx.tTransform, parent=target_hook, name='loc_' + self.name + '_tgt' + n_end)
            copy_transform(tpl_end, target, t=True)

            aim_axis = self.get_branch_opt('aim_axis')

            for i, w in enumerate(weights):
                if i > 0 and weights[i - 1] == 1:
                    break

                nodes[i]['aim'] = duplicate_joint(nodes[i]['root'], p=parent, n='aim_' + self.name + suffixes[i] + n_end)
                if i > 0:
                    mc.parent(str(nodes[i]['aim']), str(nodes[i - 1]['aim']))

                if w == 0:
                    continue

                mc.aimConstraint(str(target), str(nodes[i]['aim']), mo=1, wut='None', aim=axis_to_vector(aim_axis))

                blend = mx.create_node(mx.tPairBlend, name='_pb#')
                for dim in 'xyz':
                    plug = nodes[i]['aim']['r' + dim]
                    blend['ir' + dim + '2'] = plug.read()
                    plug.input(plug=True) >> blend['ir' + dim + '2']
                    plug.disconnect(destination=False)
                    blend['or' + dim] >> plug
                    blend['or' + dim] >> nodes[i]['inf']['r' + dim]

                sw_name = 'target_weight{}'.format(i)
                sw.add_attr(mx.Double(sw_name, keyable=True, min=0, max=1, default=w))
                sw[sw_name] >> blend['weight']

            for i, data in enumerate(nodes):
                mc.parent(str(sw), str(data['c']), r=1, s=1, add=1)

        # shear rig
        if do_shear:

            # switch
            root_sw = mx.create_node(mx.tTransform, parent=hook, name='root_' + n_chain + '_switch' + n_end)
            mc.reorder(str(root_sw), front=1)

            root_sw['v'] = False
            for attr in ['t', 'r', 's', 'v']:
                root_sw[attr].lock()

            sw = mk.Control.create_control_shape(root_sw, n='sw_' + n_chain + '_switch' + n_end)

            # chain loop
            for i, n in enumerate(nodes):
                # common switch shp
                mc.parent(str(sw), str(n['c']), r=1, s=1, add=1)

                # rename sk
                n_chain = self.name + suffixes[i]
                n['sk'].rename('j_' + n_chain + n_end)

                # new skin joints
                n['sk_base'] = mx.create_node(mx.tJoint, parent=n['sk'], name='sk_' + n_chain + '_base' + n_end)
                self.set_id(n['sk_base'], 'skin.{}'.format(i))
                self.set_id(n['sk_base'], 'skin.base.{}'.format(i))
                n['sk']['gem_id'] = n['sk']['gem_id'].read().replace(n['sk_base']['gem_id'].read(), '')

                n['sk_tip'] = mx.create_node(mx.tJoint, parent=n['sk'], name='sk_' + n_chain + '_tip' + n_end)
                self.set_id(n['sk_tip'], 'skin.tip.{}'.format(i))

                # quaternion probe
                n['q'] = mx.create_node(mx.tDecomposeMatrix, name='_quat#')
                n['sk']['matrix'] >> n['q']['inputMatrix']

                # scale
                n['sk_base']['ssc'] = False
                n['sk_tip']['ssc'] = False

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
                sw.add_attr(mx.Double(_shear_base, min=0, max=2, default=sh_base_dv[i]))
                _shear_base = sw[_shear_base]
                _shear_base.channel_box = True

                if i < len(tpl_digit) - 1:
                    _shear_tip = 'shear_{}_tip'.format(suffixes[i])
                    sw.add_attr(mx.Double(_shear_tip, min=0, max=2, default=sh_tip_dv[i]))
                    _shear_tip = sw[_shear_tip]
                    _shear_tip.channel_box = True

                # connect
                _qx = connect_mult(n['q']['outputQuatX'], _shear_base)
                _qz = connect_mult(n['q']['outputQuatZ'], _shear_base)
                _qz = connect_mult(_qz, -1)

                _ijk = mx.create_node(mx.tFourByFourMatrix, name='_ijk#')
                connect_expr('v = qx < 0 ? qx : qx * 0.5', v=_ijk['in21'], qx=_qx)
                _qz >> _ijk['in01']

                connect_matrix(_ijk['o'], n['sk_base'])

                if i < len(tpl_digit) - 1:
                    _qx = connect_mult(nodes[i + 1]['q']['outputQuatX'], _shear_tip)
                    _qz = connect_mult(nodes[i + 1]['q']['outputQuatZ'], _shear_tip)
                    _qx = connect_mult(_qx, -1)

                    _ijk = mx.create_node(mx.tFourByFourMatrix, name='_ijk#')
                    connect_expr('v = qx > 0 ? qx : qx * 0.5', v=_ijk['in21'], qx=_qx)
                    _qz >> _ijk['in01']

                    connect_matrix(_ijk['o'], n['sk_tip'])

                    # point
                    mmx = mx.create_node(mx.tMultMatrix, name='_mmx#')
                    nodes[i + 1]['sk']['wm'][0] >> mmx['i'][0]
                    nodes[i]['sk']['wim'][0] >> mmx['i'][1]

                    dmx = mx.create_node(mx.tDecomposeMatrix, name='_dmx#')
                    mmx['o'] >> dmx['imat']

                    dmx['outputTranslateX'] >> _ijk['in30']
                    dmx['outputTranslateY'] >> _ijk['in31']
                    dmx['outputTranslateZ'] >> _ijk['in32']

        # cleanup
        fix_inverse_scale(list(nodes[0]['root'].descendents()))
