# coding: utf-8

import meta_nodal_py as kl
from meta_nodal_py.Imath import V3f, M44f, Euler

from mikan.core.utils import re_is_int
from mikan.core.logger import create_logger

import mikan.tangerine.core as mk
from mikan.tangerine.lib import *
from mikan.tangerine.lib.nurbs import create_path, get_closest_point_on_curve

from mikan.vendor.geomdl.utilities import generate_knot_vector

log = create_logger()


class Template(mk.Template):

    def build_template(self, data):
        self.node.rename('tpl_{}1'.format(self.name))

        number = data['number']
        bones = [self.node]

        for i in range(number):
            j = kl.Joint(bones[-1], 'tpl_{}{}'.format(self.name, i + 2))
            bones.append(j)

        bones[0].transform.set_value(M44f(V3f(*data['root']), V3f(0, 0, 0), V3f(1, 1, 1), Euler.XYZ))
        for j in bones[1:]:
            j.transform.set_value(M44f(V3f(*data['transform']), V3f(0, 0, 0), V3f(1, 1, 1), Euler.XYZ))

        bones[-1].rename('tpl_{}_tip'.format(self.name))

    def build_rig(self):
        # init
        hook = self.get_hook()

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
            j = kl.Joint(hook, 'ref_joint')
            copy_transform(tpl, j, t=1, r=1)
            if i > 0:
                j.reparent(ref_joints[-1])
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
            rotate_order = aim_axis[-1] + up_axis[-1] + bi_axis[-1]
        rotate_order = str_to_rotate_order(rotate_order)

        # main root
        hook = self.get_hook()
        rig_root = kl.SceneGraphNode(hook, 'root_' + n_chain)

        copy_transform(ref_joints[0], rig_root)
        self.set_id(rig_root, 'root')

        # FK ctrls
        fk_nodes = []

        for i, ref in enumerate(ref_joints):
            fk = {}
            fk_nodes.append(fk)

            n_sfx = '{sep}{i}'.format(i=i + 1, sep='' if not re_is_int.match(n_chain[-1]) else '_')

            fk['root'] = kl.SceneGraphNode(rig_root, 'root_' + n_chain + n_sfx + n_end)
            copy_transform(ref, fk['root'])
            create_srt_in(fk['root'], ro=rotate_order)

            fk['c'] = kl.SceneGraphNode(fk['root'], 'c_' + n_chain + n_sfx + n_end)
            create_srt_in(fk['c'], ro=rotate_order, keyable=True)

            # shape reference nodes
            shp = kl.SceneGraphNode(rig_root, 'shp_{}{}'.format(n_chain, i))
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

        ref_joints[0].remove_from_parent()

        # splines
        rig_hook = mk.Nodes.get_id('::rig')
        if not rig_hook:
            rig_hook = self.get_first_hook()

        cvs = []
        for i, fk in enumerate(fk_nodes):
            cvs.append(fk['c'].world_transform.get_value().translation())

        d = 2
        if num_fk < 3:
            d = num_fk - 1
        _cv_sk = kl.SceneGraphNode(rig_hook, 'cv_{}_fk{}'.format(self.name, n_end))
        _cv_fk_geo = kl.SplineCurve(_cv_sk, 'cv_{}_fk{}Shape'.format(self.name, n_end))
        knots = generate_knot_vector(d, len(cvs))
        weights = [1] * len(cvs)
        spline_fk_data = kl.Spline(cvs, knots, weights, False)
        _cv_fk_geo.spline_in.set_value(spline_fk_data)

        cv_fk = kl.SceneGraphNode(fk_nodes[0]['root'], 'cv_{}_fk{}'.format(self.name, n_end))
        mk.Shape(cv_fk).copy(_cv_sk, world=True)
        _cv_sk.remove_from_parent()
        cv_fk_geo = mk.Shape(cv_fk).get_shapes()[0]
        cv_fk.show.set_value(False)

        spline = cv_fk_geo.spline_in.get_value()
        sampling = (len(spline.get_control_points()) + 1) * (spline.get_degree() ** 2)
        cv_fk_geo.sampling_in.set_value(int(sampling * 10))

        self.set_id(cv_fk, 'curve.fk')

        # skin joints
        num_sk = self.get_opt('bones')
        bone_length = self.get_opt('bones_length')
        j_chain = create_joints_on_curve(cv_fk_geo, num_sk, mode=bone_length, name='ik_{n}{{i}}{e}'.format(n=self.name, e=n_end))
        j_chain[0].reparent(rig_root)
        cv_fk.remove_from_parent()

        for i, j in enumerate(j_chain):
            self.set_id(j, 'chain.{}'.format(i))

        up_dir = self.get_opt('up_dir')
        if up_dir == 'auto':
            orient_joint(j_chain, aim=aim_axis, up=up_axis, up_auto=1)
        else:
            up_dir = axis_to_vector(up_dir)
            orient_joint(j_chain, aim=aim_axis, up=up_axis, up_dir=up_dir)

        # controller paths
        aim_axis_vector = axis_to_vector(aim_axis)
        up_axis_vector = axis_to_vector(up_axis)

        j_chain_locs = []
        for j in j_chain:
            loc = kl.Joint(j, 'loc_' + j.get_name()[2:])
            _xfo = M44f()
            _xfo.setTranslation(up_axis_vector)
            loc.transform.set_value(_xfo)
            j_chain_locs.append(loc)

        path1 = create_path(j_chain, d=2, parent=rig_root)
        path2 = create_path(j_chain_locs, d=2, parent=rig_root)
        shp1 = mk.Shape(path1).get_shapes()[0]
        shp2 = mk.Shape(path2).get_shapes()[0]

        # follow rig
        cls = mk.Mod.get_class('path')

        for i, fk in enumerate(fk_nodes):
            # u_max = path1.shape()['max'].read()
            u = 0
            if i == len(fk_nodes) - 1:
                u = 1
            elif i > 0:
                u = get_closest_point_on_curve(shp1, fk['root'], parametric=True)

            loc_up = cls.create_path(
                fk['root'], shp2,
                do_orient=True, parent=rig_root, name='path_{}_up{}'.format(n_chain, i),
                u=u, percent=True,
                fwd_vector=aim_axis_vector, up_vector=up_axis_vector
            )

            loc = cls.create_path(
                fk['root'], shp1,
                do_orient=True, parent=rig_root, name='path_{}{}'.format(n_chain, i),
                u=u, percent=True,
                fwd_vector=aim_axis_vector, up_vector=up_axis_vector, up_object=loc_up,
            )

            fk['root'].set_parent(loc)
            fk['root'].transform.set_value(M44f())

            add_plug(fk['c'], 'parameter', float, keyable=True, min_value=0, max_value=1)
            add_plug(fk['c'], 'falloff', float, keyable=True, min_value=0, max_value=1, default_value=0.1)
            fk['c'].parameter.set_value(loc.u.get_value())
            fk['c'].falloff.set_value(1 / (len(fk_nodes) - 1))

            loc.u.connect(fk['c'].parameter)
            loc_up.u.connect(fk['c'].parameter)

            # inverse transform
            srt = kl.SRTToTransformNode(fk['root'], '_srt')
            srt_out = fk['c'].transform.get_input().get_node()

            srt.translate.connect(srt_out.translate)
            srt.rotate.connect(srt_out.rotate)
            srt.rotate_order.connect(srt_out.rotate_order)

            imx = kl.InverseM44f(fk['root'], '_imx')
            imx.input.connect(srt.transform)

            fk['root'].transform.connect(imx.output)

        # skin joints
        do_skin = self.get_opt('do_skin') and self.get_opt('tweakers') == 'off'
        pfx = 'sk_'
        if not do_skin:
            pfx = 'j_'

        sk_chain = []
        for i, j in enumerate(j_chain):
            name = j.get_name()[2:]
            sk = kl.Joint(j, pfx + name)

            if do_skin:
                self.set_id(sk, 'skin.{}'.format(i))
            self.set_id(j, 'j.{}'.format(i))

            sk_chain.append(sk)
            if i < num_sk:
                _j = kl.Joint(j_chain[i + 1], 'end_' + name)
                _j.reparent(sk_chain[-1])

        # sliding
        for i, j in enumerate(j_chain[:-1]):
            add_plug(j, 'parameter', float, keyable=True)

            u = get_closest_point_on_curve(shp1, j, parametric=True)
            # u /= path1.shape()['maxValue'].read()
            j.parameter.set_value(u)

        for k, fk in enumerate(fk_nodes):
            min_u = j_chain[1].parameter.get_value()
            min_u *= 1.5
            set_plug(fk['c'].falloff, min_value=min_u)

            weights = []
            for i, j in enumerate(j_chain[:-1]):
                y = connect_expr('(t-c)/f', t=j.parameter, c=fk['c'].parameter, f=fk['c'].falloff)

                crv = kl.CurveFloat()
                crv.set_keys_with_tangent_mode([[0, -1, 3], [1, 0, 3], [0, 1, 3]])

                _sdk = kl.DrivenFloat(j, '_sdk')
                _sdk.curve.set_value(crv)
                _sdk.driver.connect(y)

                weights.append(_sdk.result)

            bw = kl.Add(fk['c'], '_bw')
            if len(weights) > 2:
                bw.add_inputs(len(weights) - 2)
            for i, w in enumerate(weights):
                bw_in = bw.get_plug('input{}'.format(i + 1))
                bw_in.connect(w)

            for i, w in enumerate(weights):
                attr = 'weight{}'.format(k)
                w_plug = add_plug(j_chain[i], attr, float, keyable=True)

                wj = connect_expr('s>0 ? w/s : 0', s=bw.output, w=w)
                w_plug.connect(wj)

        quats = []
        for k, fk in enumerate(fk_nodes):
            srt_c = find_srt(fk['c'])
            q = kl.EulerToQuatf(srt_c, '_quat')
            q.rotate.connect(srt_c.rotate)
            q.rotate_order.connect(srt_c.rotate_order)

            qxfo = kl.QuatfToM44f(q, '_xfo')
            qxfo.quat.connect(q.quat)

            quats.append(qxfo)

        for j in j_chain[:-1]:

            # rotation
            slerps = []

            for k, fk in enumerate(fk_nodes):
                srt_c = find_srt(fk['c'])
                slerp = kl.BlendTransformsNode(srt_c, '_slerp')

                slerp.transform2_in.connect(quats[k].transform)
                slerp.slerp_in.set_value(True)
                # slerp.shortest_in.set_value(True)

                w = j.get_dynamic_plug('weight{}'.format(k))
                slerp.blend_in.connect(w.get_input())

                slerps.append(slerp)

            # mq = slerps[-1].transform_out
            # for i in range(len(fk_nodes) - 1)[::-1]:
            #     prod = mx.create_node('quatProd', name='_mquat#')
            #     mq >> prod['input1Quat']
            #     slerps[i]['outputQuat'] >> prod['input2Quat']
            #     mq = prod['outputQuat']

            mmx = kl.MultM44f(j, '_mmx', len(slerps))
            for i, slerp in enumerate(reversed(slerps)):
                mmx.input[i].connect(slerp.transform_out)

            merge_transform(j, r_in=mmx.output)

            # scale
            if self.get_opt('do_scale'):
                blends = []

                for k, fk in enumerate(fk_nodes):
                    srt_c = find_srt(fk['c'])
                    blend = kl.BlendV3f(srt_c, '_blend')

                    blend.input2.connect(srt_c.scale)
                    blend.input1.set_value(V3f(1, 1, 1))

                    w = j.get_dynamic_plug('weight{}'.format(k))
                    blend.weight.connect(w.get_input())

                    v3f = kl.V3fToFloat(blend, '_vector')
                    v3f.vector.connect(blend.output)

                    blends.append(v3f)

                srt_j = find_srt(j)
                mb_in = kl.FloatToV3f(srt_j, 'scale')

                for dim in 'xyz':
                    mb = blends[-1].get_plug(dim)
                    for i in range(len(fk_nodes) - 1)[::-1]:
                        mult = kl.Mult(mb_in, '_mult')
                        mult.input1.connect(mb)
                        mult.input2.connect(blends[i].get_plug(dim))
                        mb = mult.output

                    mb_in.get_plug(dim).connect(mb)

                merge_transform(j, s_in=mb_in.vector)

            else:
                for k, fk in enumerate(fk_nodes):
                    srt = find_srt(fk['c'])
                    vf = srt.scale.get_input().get_node()
                    set_plug(vf.x, keyable=False, exportable=False)
                    set_plug(vf.y, keyable=False, exportable=False)
                    set_plug(vf.z, keyable=False, exportable=False)

            # translate
            if self.get_opt('do_translate'):
                blends = []

            else:
                for k, fk in enumerate(fk_nodes):
                    srt = find_srt(fk['c'])
                    vf = srt.translate.get_input().get_node()
                    set_plug(vf.x, keyable=False, exportable=False)
                    set_plug(vf.y, keyable=False, exportable=False)
                    set_plug(vf.z, keyable=False, exportable=False)

        # # tweakers
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
        #         root = kl.Joint(parent, 'root_' + n_chain + '_tweaker' + str(i + 1))
        #         c = kl.Joint(root, 'c_' + n_chain + '_tweaker' + str(i + 1))
        #         create_srt_in(c, keyable=True)
        #
        #         mmx = kl.MultM44f(root, '_mmx')
        #         mmx.input[0].connect(j.world_transform)
        #         imx = kl.InverseM44f(root, '_imx')
        #         imx.input.connect(offset.world_transform)
        #         mmx.input[1].connect(imx.output)
        #         root.transform.connect(mmx.output)
        #
        #         if chained:
        #             parent = c
        #
        #         sk = kl.Joint(c, 'sk_' + n_chain + str(i + 1))
        #         if i < len(offsets) - 2:
        #             end = kl.Joint(sk, 'end_' + n_chain + str(i + 1))
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
