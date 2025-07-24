# coding: utf-8

from six.moves import range

from mikan.maya import cmds as mc
import mikan.maya.cmdx as mx

from mikan.core.utils import re_is_int
from mikan.core.logger import create_logger

import mikan.maya.core as mk
from mikan.maya.lib.connect import *
from mikan.maya.lib.nurbs import *
from mikan.maya.lib.rig import (
    copy_transform, orient_joint, create_joints_on_curve,
    axis_to_vector, get_stretch_axis, fix_inverse_scale
)

log = create_logger()


class Template(mk.Template):

    def build_template(self, data):
        number = data['number']
        bones = [self.node]

        with mx.DagModifier() as md:
            for i in range(number):
                j = md.create_node(mx.tJoint, parent=bones[-1], name='tpl_{}{}'.format(self.name, i + 2))
                bones.append(j)

        bones[0]['t'] = data['root']
        for j in bones[1:]:
            j['t'] = data['transform']

        bones[-1].rename('tpl_{}_tip'.format(self.name))

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

        # names
        n_chain = self.name
        n_end = self.get_branch_suffix()

        tpl_chain = self.get_structure('chain')
        num_fk = len(tpl_chain)
        if num_fk < 2:
            raise RuntimeError('/!\\ template chain must have at least 2 joints')

        # orient chain
        ref_joints = []
        for i, tpl in enumerate(tpl_chain):
            j = mx.create_node(mx.tJoint, name='dummy_{}{}'.format(n_chain, i))
            copy_transform(tpl, j, t=True, r=True)
            if i > 0:
                mc.parent(str(j), str(ref_joints[-1]))
            ref_joints.append(j)

        if self.get_opt('orient') == 'auto':
            aim_axis = self.get_branch_opt('aim')
            up_axis = self.get_opt('up')

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

        else:
            # guess axis from given chain
            _axis = get_stretch_axis(tpl_chain)
            if not _axis:
                raise RuntimeError('/!\\ cannot find orientation from template')
            aim_axis, up_axis, bi_axis = _axis
            if self.do_flip():
                aim_axis = self.branch_opt(aim_axis)
                up_axis = self.branch_opt(up_axis)

        rotate_order = self.get_opt('rotate_order')
        if rotate_order == 'auto':
            rotate_order = aim_axis[-1].lower() + up_axis[-1].lower() + bi_axis[-1].lower()

        # main root
        hook = self.get_hook()
        rig_root = mx.create_node(mx.tJoint, parent=hook, name='root_' + n_chain)

        copy_transform(ref_joints[0], rig_root)
        rig_root['drawStyle'] = 2

        self.set_id(rig_root, 'root')

        # FK ctrls
        fk_nodes = []

        for i, ref in enumerate(ref_joints):
            fk = {}
            fk_nodes.append(fk)

            n_sfx = '{sep}{i}'.format(i=i + 1, sep='' if not re_is_int.match(n_chain[-1]) else '_')

            fk['root'] = mx.create_node(mx.tTransform, parent=rig_root, name='root_' + n_chain + n_sfx + n_end)
            fk['root']['ro'] = rotate_order
            copy_transform(ref, fk['root'])

            fk['c'] = mx.create_node(mx.tTransform, parent=fk['root'], name='c_' + n_chain + n_sfx + n_end)
            fk['c']['ro'] = rotate_order

            # shape reference nodes
            shp = mx.create_node(mx.tTransform, parent=rig_root, name='shp_{}{}'.format(n_chain, i))
            copy_transform(fk['root'], shp)
            self.set_id(shp, 'shapes.fk.{}'.format(i))
            if i == len(tpl_chain) - 1:
                self.set_id(shp, 'shapes.fk.last')

            # register
            self.set_id(fk['root'], 'roots.fk.{}'.format(i))

            if self.get_opt('do_ctrl'):
                self.set_id(fk['c'], 'ctrls.fk.{}'.format(i))
                if i == len(tpl_chain) - 1:
                    self.set_id(fk['c'], 'ctrls.fk.last')

            self.set_hook(tpl_chain[i], fk['c'], 'hooks.{}'.format(i))

        # mx.delete(ref_joints)
        for j in ref_joints:
            j.add_attr(mx.Message('kill_me'))

        # splines
        cvs = []
        for i, fk in enumerate(fk_nodes):
            cvs.append(fk['c'].translation(mx.sWorld))

        d = 2
        if num_fk < 3:
            d = num_fk - 1
        cv_sk = mc.curve(d=d, p=cvs, n='cv_{}_fk{}'.format(self.name, n_end))
        cv_sk = mx.encode(cv_sk)
        mc.parent(str(cv_sk), str(fk_nodes[0]['root']))

        # spline joints
        num_sk = self.get_opt('bones')
        bone_length = self.get_opt('bones_length')
        j_chain = create_joints_on_curve(cv_sk, num_sk, mode=bone_length, name='j_{n}{{i}}{e}'.format(n=self.name, e=n_end))
        mc.parent(str(j_chain[0]), str(rig_root))
        mc.delete(str(cv_sk))

        for i, j in enumerate(j_chain):
            self.set_id(j, 'chain.{}'.format(i))

        up_dir = self.get_opt('up_dir')
        if up_dir == 'auto':
            orient_joint(j_chain, aim=aim_axis, up=up_axis, up_auto=1)
        else:
            up_dir = axis_to_vector(up_dir)
            orient_joint(j_chain, aim=aim_axis, up=up_axis, up_dir=up_dir)

        # controller paths
        j_chain_locs = []
        for j in j_chain:
            loc = mx.create_node(mx.tTransform, parent=j, name='loc_' + j.name()[2:])
            loc['t' + up_axis] = 1
            j_chain_locs.append(loc)

        path1 = create_path(j_chain, d=2)
        path2 = create_path(j_chain_locs, d=2)
        mc.parent(str(path1), str(path2), str(rig_root), r=1)

        # follow rig
        aim_axis_vector = axis_to_vector(aim_axis)
        up_axis_vector = axis_to_vector(up_axis)

        cls = mk.Mod.get_class('path')

        for i, fk in enumerate(fk_nodes):
            u_max = path1.shape()['max'].read()
            u = 0
            if i == len(fk_nodes) - 1:
                u = u_max
            elif i > 0:
                u = get_closest_point_on_curve(path1.shape(), fk['root'], parameter=True)

            loc_up = cls.create_path(
                fk['root'], path2.shape(),
                do_orient=True, parent=rig_root, name='path_{}_up{}'.format(n_chain, i),
                u=u, percent=True,
                fwd_vector=aim_axis_vector, up_vector=up_axis_vector
            )

            loc = cls.create_path(
                fk['root'], path1.shape(),
                do_orient=True, parent=rig_root, name='path_{}{}'.format(n_chain, i),
                u=u, percent=True,
                fwd_vector=aim_axis_vector, up_vector=up_axis_vector, up_object=loc_up,
            )

            mc.parent(str(fk['root']), str(loc))
            fk['root']['t'] = [0, 0, 0]
            fk['root']['r'] = [0, 0, 0]

            fk['c'].add_attr(mx.Double('parameter', keyable=True, min=0, max=1))
            fk['c'].add_attr(mx.Double('falloff', keyable=True, min=0, max=1, default=0.1))
            fk['c']['parameter'] = loc['u'].read()
            fk['c']['falloff'] = 1 / (len(fk_nodes) - 1)

            fk['c']['parameter'] >> loc['u']
            fk['c']['parameter'] >> loc_up['u']

            # inverse transform
            srt = mx.create_node(mx.tComposeMatrix, '_srt#')
            fk['c']['t'] >> srt['inputTranslate']
            fk['c']['r'] >> srt['inputRotate']
            fk['c']['ro'] >> srt['inputRotateOrder']
            imx = mx.create_node(mx.tInverseMatrix, '_inverse#')
            srt['outputMatrix'] >> imx['inputMatrix']

            connect_matrix(imx['outputMatrix'], fk['root'])

        # skin joints
        do_skin = self.get_opt('do_skin') and self.get_opt('tweakers') == 'off'
        pfx = 'sk_'
        if not do_skin:
            pfx = 'j_'

        sk_chain = []
        for i, j in enumerate(j_chain):
            name = j.name()[2:]
            sk = mx.create_node(mx.tJoint, parent=j, name=pfx + name)

            if do_skin:
                self.set_id(sk, 'skin.{}'.format(i))
            self.set_id(j, 'j.{}'.format(i))

            sk_chain.append(sk)
            j['s'] >> sk_chain[-1]['inverseScale']
            mc.reorder(str(sk_chain[i]), front=1)
            if i < len(j_chain) - 1:
                _j = mx.create_node(mx.tJoint, parent=j_chain[i + 1], name='end_' + name)
                mc.parent(str(_j), str(sk_chain[-1]))

            sk['ssc'] = False

        # sliding
        for i, j in enumerate(j_chain[:-1]):
            j.add_attr(mx.Double('parameter', keyable=True))

            u = get_closest_point_on_curve(path1.shape(), j, parameter=True)
            u /= path1.shape()['maxValue'].read()
            j['parameter'] = u

        for k, fk in enumerate(fk_nodes):
            min_u = j_chain[1]['parameter'].read()
            min_u *= 1.5
            mc.addAttr(fk['c']['falloff'].path(), e=True, min=min_u)

            weights = []
            for i, j in enumerate(j_chain[:-1]):
                y = connect_expr('(t-c)/f', t=j['parameter'], c=fk['c']['parameter'], f=fk['c']['falloff'])

                u = mx.create_node(mx.tAnimCurveUU, name='_uu#')
                mc.setKeyframe(str(u), f=-1, v=0)
                mc.setKeyframe(str(u), f=0, v=1)
                mc.setKeyframe(str(u), f=1, v=0)

                y >> u['input']

                weights.append(u['output'])

            bw = mx.create_node(mx.tBlendWeighted)
            for i, w in enumerate(weights):
                w >> bw['input'][i]

            for i, w in enumerate(weights):
                attr = 'weight{}'.format(k)
                j_chain[i].add_attr(mx.Double(attr, keyable=True))

                wj = connect_expr('s>0 ? w/s : 0', s=bw['output'], w=w)
                wj >> j_chain[i][attr]

        quats = []
        for k, fk in enumerate(fk_nodes):
            q = mx.create_node(mx.tEulerToQuat, name='_quat#')
            fk['c']['r'] >> q['inputRotate']
            fk['c']['ro'] >> q['inputRotateOrder']
            quats.append(q)

        for j in j_chain[:-1]:

            # rotation
            slerps = []

            for k, fk in enumerate(fk_nodes):
                slerp = mx.create_node('quatSlerp', name='_slerp#')
                slerp['input1Quat'] = (0, 0, 0, 1)
                slerp['angleInterpolation'] = 1
                quats[k]['outputQuat'] >> slerp['input2Quat']

                w = j['weight{}'.format(k)]
                w.input(plug=True) >> slerp['t']
                slerps.append(slerp)

            mq = slerps[-1]['outputQuat']
            for i in range(len(fk_nodes) - 1)[::-1]:
                prod = mx.create_node('quatProd', name='_mquat#')
                mq >> prod['input1Quat']
                slerps[i]['outputQuat'] >> prod['input2Quat']
                mq = prod['outputQuat']

            euler = mx.create_node('quatToEuler', name='_euler#')
            mq >> euler['inputQuat']
            j['ro'] >> euler['inputRotateOrder']
            euler['outputRotate'] >> j['r']

            # scale
            if self.get_opt('do_scale'):
                blends = []

                for k, fk in enumerate(fk_nodes):
                    blend = mx.create_node(mx.tBlendColors, name='_blend#')
                    fk['c']['s'] >> blend['color1']
                    blend['color2'] = (1, 1, 1)

                    w = j['weight{}'.format(k)]
                    w.input(plug=True) >> blend['blender']
                    blends.append(blend)

                mb = blends[-1]['output']
                for i in range(len(fk_nodes) - 1)[::-1]:
                    prod = mx.create_node(mx.tMultiplyDivide, name='_mult#')
                    mb >> prod['input1']
                    blends[i]['output'] >> prod['input2']
                    mb = prod['output']

                mb >> j['s']

            else:
                for k, fk in enumerate(fk_nodes):
                    for dim in 'xyz ':
                        fk['c']['s' + dim.strip()].keyable = False
                        fk['c']['s' + dim.strip()].lock()

            # translate
            if self.get_opt('do_translate'):
                blends = []

            else:
                for k, fk in enumerate(fk_nodes):
                    for dim in 'xyz ':
                        fk['c']['t' + dim.strip()].keyable = False
                        fk['c']['t' + dim.strip()].lock()

        # weight viz
        # for i, j in enumerate(j_chain[:-1]):
        #     loc = mx.create_node(mx.tTransform, parent=j)
        #     loc['displayRotatePivot'] = 1
        #
        #     j['weight1'] >> loc['tz']

        # tweakers
        # do_tweakers = self.get_opt('tweakers')
        # if do_tweakers != 'off':
        #     chained = do_tweakers == 'chained'
        #
        #     tweakers = []
        #
        #     parent = ik_nodes[0]['j']
        #     offsets = [ik_nodes[0]['j']] + sk_chain
        #
        #     for i, j in enumerate(sk_chain):
        #         offset = offsets[i]
        #         if not chained:
        #             offset = offsets[0]
        #
        #         mmx = mx.create_node(mx.tMultMatrix, name='_mmx#')
        #         j['wm'][0] >> mmx['i'][0]
        #         offset['wim'][0] >> mmx['i'][1]
        #
        #         root = mx.create_node(mx.tJoint, parent=parent, name='root_' + n_chain + '_tweaker' + str(i + 1))
        #         c = mx.create_node(mx.tJoint, parent=root, name='c_' + n_chain + '_tweaker' + str(i + 1))
        #         root['drawStyle'] = 2
        #         c['drawStyle'] = 2
        #
        #         connect_matrix(mmx['o'], root)
        #         if chained:
        #             parent = c
        #
        #         sk = mx.create_node(mx.tJoint, parent=c, name='sk_' + n_chain + str(i + 1))
        #         if i < len(offsets) - 2:
        #             end = mx.create_node(mx.tJoint, parent=sk, name='end_' + n_chain + str(i + 1))
        #             copy_transform(offsets[i + 2], end)
        #
        #         tweaker = {}
        #         tweaker['root'] = root
        #         tweaker['c'] = c
        #         tweaker['sk'] = sk
        #         tweakers.append(tweaker)
        #
        #     for i, tweaker in enumerate(tweakers):
        #         self.set_id(tweaker['root'], 'roots.tweaker.{}'.format(i))
        #         self.set_id(tweaker['c'], 'ctrls.tweaker.{}'.format(i))
        #         self.set_id(tweaker['sk'], 'skin.{}'.format(i))

        # cleanup
        fix_inverse_scale(list(fk_nodes[0]['root'].descendents(type=mx.tJoint)))
