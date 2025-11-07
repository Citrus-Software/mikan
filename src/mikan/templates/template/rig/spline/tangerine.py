# coding: utf-8

import meta_nodal_py as kl
from meta_nodal_py.Imath import V3f, M44f, Euler

from mikan.core.logger import create_logger
from mikan.core.utils.mathutils import NurbsCurveRemap

import mikan.tangerine.core as mk
from mikan.tangerine.lib import *
from mikan.tangerine.lib.nurbs import *

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
        rig_hook = mk.Nodes.get_id('::rig')
        if not rig_hook:
            rig_hook = self.get_first_hook()

        n_chain = self.name
        n_end = self.get_branch_suffix()

        tpl_chain = self.get_structure('chain')
        if len(tpl_chain) < 2:
            raise RuntimeError('/!\\ template chain must have at least 2 joints')

        chain, chain_sub, chain_trail = self.get_chain()

        num_ik = self.get_opt('iks')
        num_fk = len(tpl_chain)

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

        # build nodes
        fk_joints = []
        ik_joints = []
        cvs = []

        # FK ctrls
        fk_nodes = self.build_chain(ref_joints, rotate_order=rotate_order, do_skin=False, register=False)
        ref_joints[0].remove_from_parent()

        for i, n in enumerate(fk_nodes):

            fk_joints.append(n['sk'])
            cvs.append(n['sk'].world_transform.get_value().translation())

            # register
            self.set_id(n['root'], 'roots.{}'.format(i))

            if self.get_opt('do_ctrl'):
                self.set_id(n['c'], 'ctrls.fk.{}'.format(i))
                if i < len(tpl_chain):
                    self.set_id(n['c'], 'ctrls.fk.last')

            if chain or chain_sub:
                for chain_id in chain + chain_sub:
                    self.set_id(n[chain_id], '{}s.fk.{}'.format(chain_id, i))
                    if i < len(tpl_chain):
                        self.set_id(n[chain_id], '{}s.fk.last'.format(chain_id))

            self.set_id(n['sk'], 'joints.fk.{}'.format(i))
            self.set_hook(tpl_chain[i], n['sk'], 'hooks.{}'.format(i))

        # IK ctrls
        _tpl_ik = []
        _sfx = []

        for i in range(num_ik):
            _sfx.append('IK_{}'.format(i + 1))
            _tpl_ik.append(kl.Joint(hook, '_tpl_spline{}'.format(i + 1)))
            if i > 0:
                _tpl_ik[-1].reparent(_tpl_ik[-2])

        ik_nodes = self.build_chain(_tpl_ik, rotate_order=rotate_order, do_skin=False, register=False, suffixes=_sfx)
        _tpl_ik[0].remove_from_parent()

        for i, n in enumerate(ik_nodes):
            ik_joints.append(n['sk'])

            # register
            self.set_id(n['root'], 'roots.ik.{}'.format(i))

            if self.get_opt('do_ctrl'):
                self.set_id(n['c'], 'ctrls.ik.{}'.format(i))

            if chain or chain_sub:
                for chain_id in chain + chain_sub:
                    self.set_id(n[chain_id], '{}s.ik.{}'.format(chain_id, i))

            self.set_id(n['sk'], 'joints.ik.{}'.format(i))

        # switch
        c_switch = kl.SceneGraphNode(fk_nodes[0]['root'], 'c_{}_switch{}'.format(self.name, n_end))
        self.set_id(c_switch, 'ctrls.switch')

        # splines
        d = 3
        if num_fk < 4:
            d = num_fk - 1
        _cv_fk = kl.SceneGraphNode(rig_hook, 'cv_{}_fk{}'.format(self.name, n_end))
        _cv_fk_geo = kl.SplineCurve(_cv_fk, 'cv_{}_fk{}Shape'.format(self.name, n_end))
        knots = generate_knot_vector(d, len(cvs))
        weights = [1] * len(cvs)
        spline_fk_data = kl.Spline(cvs, knots, weights, False)
        _cv_fk_geo.spline_in.set_value(spline_fk_data)

        cv_fk = kl.SceneGraphNode(fk_nodes[0]['root'], 'cv_{}_fk{}'.format(self.name, n_end))
        mk.Shape(cv_fk).copy(_cv_fk, world=True)
        _cv_fk.remove_from_parent()
        cv_fk_geo = mk.Shape(cv_fk).get_shapes()[0]
        cv_fk.show.set_value(False)

        spline = cv_fk_geo.spline_in.get_value()
        sampling = (len(spline.get_control_points()) + 1) * (spline.get_degree() ** 2)
        cv_fk_geo.sampling_in.set_value(int(sampling * 10))

        cv_ik = kl.SceneGraphNode(fk_nodes[0]['root'], 'cv_{}_ik{}'.format(self.name, n_end))
        cv_ik_shp = mk.Shape(cv_ik)
        cv_ik_shp.copy(cv_fk, world=True)
        cv_ik_geo = cv_ik_shp.get_shapes()[0]

        self.set_id(cv_fk, 'curve.fk')
        self.set_id(cv_ik, 'curve.ik')

        rebuild_curve(cv_ik_geo, 3, num_ik * 2)
        cv_ik.show.set_value(False)
        spline_ik_data = cv_ik_geo.spline_in.get_value()

        u_fk = []
        for i in range(num_fk):
            if i == 0:
                u = 0
            elif i == num_fk - 1:
                u = 1
            else:
                pos = fk_joints[i].world_transform.get_value().translation()
                u = get_closest_point_on_curve(cv_fk_geo, pos, parametric=1)
            u_fk.append(u)

        # secondary spline up
        remap = NurbsCurveRemap(num_fk, degree=d)

        up_vectors = []
        for fk in fk_nodes:
            m = fk['c'].world_transform.get_value()
            pim = cv_ik.world_transform.get_value().inverse()
            up_vectors.append((m * pim).multDirMatrix(axis_to_vector(up_axis)))

        cv_up = kl.SceneGraphNode(fk_nodes[0]['root'], 'cv_{}_up{}'.format(self.name, n_end))
        cv_up_shp = mk.Shape(cv_up)
        cv_up_shp.copy(cv_ik, world=True)
        cv_up_geo = cv_up_shp.get_shapes()[0]

        cvs = spline_ik_data.get_control_points()

        for i in range(len(cvs)):
            v = V3f()

            if i == 0:
                _u = 0
            elif i == len(cvs) - 1:
                _u = 1
            else:
                _u = get_closest_point_on_curve(cv_fk_geo, cvs[i], parametric=True, local=True)
            weights = remap.get(_u)
            for j, w in enumerate(weights):
                v += up_vectors[j] * w

            v.normalize()
            v *= cv_up_geo.length_out.get_value() / 2

            if self.do_flip():
                v *= -1

            cvs[i] += v

        knots = generate_knot_vector(spline_ik_data.get_degree(), len(cvs))
        weights = [1] * len(cvs)
        spline_up_data = kl.Spline(cvs, knots, weights, False)

        cv_up_geo.spline_in.set_value(spline_up_data)
        cv_up.show.set_value(False)

        # hook IK controls
        add_plug(c_switch, 'uniform_ik', float, k=1, min_value=0, max_value=1, nice_name='Uniform IKs')
        c_switch.uniform_ik.set_value(self.get_opt('uniform_ik'))

        for i in range(num_ik):
            if i == 0:
                u = 0
            elif i == num_ik - 1:
                u = 1
            else:
                pos = (spline_ik_data.get_control_points()[(i - 1) * 2 + 2] + spline_ik_data.get_control_points()[(i - 1) * 2 + 3]) / 2
                u = get_closest_point_on_curve(cv_fk_geo, pos, parametric=1, local=True)
            d0 = cv_fk_geo.length_out.get_value()

            hook_ik = kl.Joint(fk_nodes[0]['root'], 'hook_{}IK_{}'.format(self.name, i + 1))
            fk = 0
            for _fk, _u in enumerate(u_fk):
                if u >= _u:
                    fk = _fk

            mmx = kl.MultM44f(hook_ik, '_mmx')
            imx = kl.InverseM44f(hook_ik, '_imx')
            imx.input.connect(hook_ik.parent_world_transform)
            mmx.input[1].connect(imx.output)
            mmx.input[0].connect(fk_joints[fk].world_transform)
            hook_ik.transform.connect(mmx.output)

            root = ik_nodes[i]['root']
            root.reparent(hook_ik)

            poc = kl.PointOnSplineCurve(cv_fk, 'poc')
            poc.spline_mesh_in.connect(cv_fk_geo.spline_mesh_out)
            poc.spline_in.connect(cv_fk_geo.spline_in)
            poc.geom_world_transform_in.connect(cv_fk.transform)

            if i == 0:
                poc.u_in.set_value(0)
            elif i == num_ik - 1:
                poc.u_in.set_value(1)
            else:
                mp = kl.PointOnSplineCurve(cv_fk, 'path')
                d = get_curve_length(cv_fk_geo, u)

                mp.length_in.connect(cv_fk_geo.length_out)
                mp.length_ratio_in.set_value(d / d0)
                mp.spline_mesh_in.connect(cv_fk_geo.spline_mesh_out)
                mp.spline_in.connect(cv_fk_geo.spline_in)
                mp.geom_world_transform_in.connect(cv_fk.transform)

                npc = kl.Closest(cv_fk, 'ucoord')
                npc.legacy.set_value(2)
                npc.spline_in.connect(cv_fk_geo.spline_in)
                npc.spline_mesh_in.connect(cv_fk_geo.spline_mesh_out)
                npc.transform_in.connect(mp.transform_out)

                connect_expr(
                    'poc = lerp(u, npc, w)',
                    poc=poc.u_in, u=u, npc=npc.u_out, w=c_switch.uniform_ik
                )

            p = kl.SceneGraphNode(fk_nodes[0]['root'], 'p_{}_ik{}{}'.format(self.name, i, n_end))
            p.transform.connect(poc.transform_out)
            point_constraint(p, root)

            aim = kl.SceneGraphNode(p, 'aim')
            _srt = create_srt_in(aim)
            _srt.translate.connect(poc.tangent_out)

            aim_constraint(aim, root, aim_vector=axis_to_vector(aim_axis), up_vector=V3f())

        # bpm
        bpm_root = kl.SceneGraphNode(fk_nodes[0]['root'], 'bpm_{}'.format(self.name))
        bpm_root.show.set_value(False)

        fk_bpm = []
        for i, j in enumerate(fk_joints):
            bpm = kl.Joint(bpm_root, 'bpm_{}_fk{}'.format(self.name, i))
            copy_transform(j, bpm)
            fk_bpm.append(bpm)

        ik_bpm = []
        for i, j in enumerate(ik_joints):
            bpm = kl.Joint(bpm_root, 'bpm_{}_ik{}'.format(self.name, i))
            copy_transform(j, bpm)
            ik_bpm.append(bpm)

        # skin fk
        fk_maps = []
        for i in range(num_fk):
            fk_maps.append(mk.WeightMap([0] * num_fk))
            fk_maps[i][i] = 1

        fk_easing = self.get_opt('fk_easing')
        if fk_easing in ['in', 'in-out']:
            fk_maps[0][1] = 1
            fk_maps[1][1] = 0
        if fk_easing in ['out', 'in-out']:
            fk_maps[-1][num_fk - 2] = 1
            fk_maps[num_fk - 2][num_fk - 2] = 0

        skin_data = {
            'deformer': 'skin',
            'transform': cv_fk,
            'data': {
                'infs': dict(zip(range(num_fk), fk_joints)),
                'maps': dict(zip(range(num_fk), fk_maps)),
                'bind_pose': dict(zip(range(num_fk), fk_bpm)),
            }
        }
        skin_dfm = mk.Deformer(**skin_data)
        skin_dfm.normalize()
        skin_dfm.build()
        # skin_dfm.set_protected(True)
        skin_fk = skin_dfm.node
        skin_fk.geom_world_transform.connect(cv_fk.world_transform)

        # skin ik
        ik_maps = create_curve_weightmaps(cv_ik_geo, ik_joints)

        skin_data = {
            'deformer': 'skin',
            'transform': cv_ik,
            'data': {
                'infs': dict(zip(range(num_ik), ik_joints)),
                'maps': dict(zip(range(num_ik), ik_maps)),
                'bind_pose': dict(zip(range(num_ik), ik_bpm)),
            }
        }
        skin_dfm = mk.Deformer(**skin_data)
        skin_dfm.normalize()
        skin_dfm.build()
        # skin_dfm.set_protected(True)
        skin_ik = skin_dfm.node
        skin_ik.geom_world_transform.connect(cv_ik.world_transform)

        # skin up
        skin_data = {
            'deformer': 'skin',
            'transform': cv_up,
            'data': {
                'infs': dict(zip(range(num_ik), ik_joints)),
                'maps': dict(zip(range(num_ik), ik_maps)),
                'bind_pose': dict(zip(range(num_ik), ik_bpm)),
            }
        }
        skin_dfm = mk.Deformer(**skin_data)
        skin_dfm.normalize()
        skin_dfm.build()
        # skin_dfm.set_protected(True)
        skin_up = skin_dfm.node
        skin_up.geom_world_transform.connect(cv_up.world_transform)

        # spline IK
        num_sk = self.get_opt('bones')
        bone_length = self.get_opt('bones_length')
        ik_chain = create_joints_on_curve(cv_fk_geo, num_sk, mode=bone_length, name='ik_{n}{{i}}{e}'.format(n=self.name, e=n_end))
        ik_chain[0].reparent(ik_joints[0].get_parent())

        for i, j in enumerate(ik_chain):
            self.set_id(j, 'chain.{}'.format(i))

        up_dir = self.get_opt('up_dir')
        if up_dir == 'auto':
            orient_joint(ik_chain, aim=aim_axis, up=up_axis, up_auto=1)
        else:
            up_dir = axis_to_vector(up_dir)
            orient_joint(ik_chain, aim=aim_axis, up=up_axis, up_dir=up_dir)

        ik_handle = stretch_spline_IK(cv_ik_geo, ik_chain)

        add_plug(c_switch, 'twist', float, k=1, default_value=0, nice_name='Twist')
        add_plug(c_switch, 'stretch', float, k=1, default_value=0, min_value=0, max_value=1, nice_name='Stretch')
        add_plug(c_switch, 'squash', float, k=1, default_value=0, min_value=0, max_value=1, nice_name='Squash')
        add_plug(c_switch, 'slide', float, k=1, default_value=0, min_value=-1, max_value=1, nice_name='Slide')
        ik_handle.stretch.connect(c_switch.stretch)
        ik_handle.squash.connect(c_switch.squash)
        ik_handle.slide.connect(c_switch.slide)

        if self.get_opt('default_stretch'):
            c_switch.stretch.set_value(1)

        # skin joints
        do_skin = self.get_opt('do_skin') and self.get_opt('tweakers') == 'off'
        pfx = 'sk_'
        if not do_skin:
            pfx = 'j_'

        sk_chain = []
        for i, ik in enumerate(ik_chain):
            j = kl.Joint(ik, ik.get_name().replace('ik_', pfx))
            sk = j

            if do_skin:
                self.set_id(sk, 'skin.{}'.format(i))
            self.set_id(j, 'j.{}'.format(i))

            sk_chain.append(j)
            if i < len(ik_chain) - 1:
                _j = kl.Joint(ik_chain[i + 1], ik.get_name().replace('ik_', 'end_'))
                _j.reparent(sk_chain[-1])

        # -- connect scale
        skx = []
        skz = []
        for sk in sk_chain:
            _srt = create_srt_in(sk)
            skx.append(_srt.find('scale').get_plug(up_axis[-1]))
            skz.append(_srt.find('scale').get_plug(bi_axis[-1]))

        blend_smooth_remap([c.find('transform/scale').get_plug(up_axis[-1]) for c in [n['c'] for n in fk_nodes]], skx)
        blend_smooth_remap([c.find('transform/scale').get_plug(bi_axis[-1]) for c in [n['c'] for n in fk_nodes]], skz)

        for i, ik in enumerate(ik_chain):
            if ik.get_dynamic_plug('squash'):
                sk = sk_chain[i]
                _s = sk.find('transform/scale')
                connect_mult(ik.squash, _s.get_plug(up_axis[-1]).get_input(), _s.get_plug(up_axis[-1]))
                connect_mult(ik.squash, _s.get_plug(bi_axis[-1]).get_input(), _s.get_plug(bi_axis[-1]))

            sk_chain[i].scale_compensate.set_value(0)

        # -- scale last?
        # TODO: option
        # sk_chain[-1].find('transform/scale').get_plug(aim_axis[-1]).connect(ik_ctrls[-1].find('transform/scale').get_plug(aim_axis[-1]))

        # twist ik legacy
        up_vector = axis_to_vector(up_axis)
        bi_vector = axis_to_vector(bi_axis)
        ik_handle.up_vector_in.set_value(up_vector)
        ik_handle.start_up_vector_space_in.connect(ik_joints[0].world_transform)
        ik_handle.end_up_vector_space_in.connect(ik_joints[-1].world_transform)

        start_up_vector = up_vector
        end_up_vector = up_vector
        _up0 = ik_joints[0].world_transform.get_value().multDirMatrix(up_vector)
        _up1 = ik_joints[-1].world_transform.get_value().multDirMatrix(up_vector)
        # conform end up?
        if _up0.dot(_up1) < 0:
            end_up_vector *= -1

        start_bi_vector = bi_vector
        end_bi_vector = bi_vector
        _up0 = ik_joints[0].world_transform.get_value().multDirMatrix(bi_vector)
        _up1 = ik_joints[-1].world_transform.get_value().multDirMatrix(bi_vector)
        # conform end up?
        if _up0.dot(_up1) < 0:
            end_bi_vector *= -1

        ik_handle.start_up_vector_in_space_in.set_value(start_up_vector)
        ik_handle.end_up_vector_in_space_in.set_value(end_up_vector)

        add_plug(c_switch, 'twist_plane', int, keyable=True, enum=[up_axis, bi_axis, 'off'])
        for c in [n['c'] for n in fk_nodes] + [n['c'] for n in ik_nodes]:
            add_plug(c, '_twist_plane', int, k=1)
            c._twist_plane.connect(c_switch.twist_plane)

        up_v = kl.FloatToV3f(ik_handle, 'up_vector')
        start_up_v = kl.FloatToV3f(ik_handle, 'start_up_vector')
        end_up_v = kl.FloatToV3f(ik_handle, 'end_up_vector')
        ik_handle.up_vector_in.connect(up_v.vector)
        ik_handle.start_up_vector_in_space_in.connect(start_up_v.vector)
        ik_handle.end_up_vector_in_space_in.connect(end_up_v.vector)

        connect_driven_curve(c_switch.twist_plane, up_v.x, {0: start_up_vector[0], 1: start_bi_vector[0], 2: 0})
        connect_driven_curve(c_switch.twist_plane, up_v.y, {0: start_up_vector[1], 1: start_bi_vector[1], 2: 0})
        connect_driven_curve(c_switch.twist_plane, up_v.z, {0: start_up_vector[2], 1: start_bi_vector[2], 2: 0})

        connect_driven_curve(c_switch.twist_plane, start_up_v.x, {0: start_up_vector[0], 1: start_bi_vector[0], 2: 0})
        connect_driven_curve(c_switch.twist_plane, start_up_v.y, {0: start_up_vector[1], 1: start_bi_vector[1], 2: 0})
        connect_driven_curve(c_switch.twist_plane, start_up_v.z, {0: start_up_vector[2], 1: start_bi_vector[2], 2: 0})

        connect_driven_curve(c_switch.twist_plane, end_up_v.x, {0: end_up_vector[0], 1: end_bi_vector[0], 2: 0})
        connect_driven_curve(c_switch.twist_plane, end_up_v.y, {0: end_up_vector[1], 1: end_bi_vector[1], 2: 0})
        connect_driven_curve(c_switch.twist_plane, end_up_v.z, {0: end_up_vector[2], 1: end_bi_vector[2], 2: 0})

        # -- ik secondary up
        _wim = connect_expr('inverse(wm)', wm=cv_ik.world_transform)

        up_locs = []
        for i, ik in enumerate(ik_chain):
            _wm = connect_expr('wm * wim', wm=ik.world_transform, wim=_wim)

            npc = kl.Closest(cv_ik, 'closest')
            npc.legacy.set_value(2)
            npc.spline_in.connect(cv_ik_geo.spline_in)
            npc.spline_mesh_in.connect(cv_ik_geo.spline_mesh_out)
            npc.transform_in.connect(_wm)

            poc = kl.PointOnSplineCurve(cv_up, 'poc')
            poc.spline_mesh_in.connect(cv_up_geo.spline_mesh_out)
            poc.spline_in.connect(cv_up_geo.spline_in)
            poc.geom_world_transform_in.connect(cv_up.transform)
            poc.u_in.connect(npc.u_out)

            loc = kl.SceneGraphNode(cv_up, f'loc_{n_chain}_up{i + 1}')
            loc.transform.connect(poc.transform_out)

            up_locs.append(loc)

        # -- ik twist
        _up = axis_to_vector(up_axis)
        if self.do_flip():
            _up *= -1

        for i, sk in enumerate(sk_chain):
            target_aim = axis_to_vector(aim_axis)
            if i < len(ik_chain) - 1:
                target = ik_chain[i + 1]
            else:
                target = ik_chain[i - 1]
                target_aim *= -1

            _aim = aim_constraint(target, sk, aim_vector=target_aim, up_vector=_up, up_object=up_locs[i])

            _srt = find_srt(sk)
            _srt.rotate_order.set_value(rotate_order)

        # orient last
        orient_constraint(ik_joints[-1], sk_chain[-1], maintain_offset=True, force_blend=True)
        sk_chain[-1].blend_rotate.connect(c_switch.stretch)

        # additional twist
        add_plug(c_switch, 'twist_offset_base', float, keyable=True)
        add_plug(c_switch, 'twist_offset_tip', float, keyable=True)

        sk_aims = []
        for sk in sk_chain:
            _srt = find_srt(sk)

            _euler = kl.EulerToFloat(_srt, '_euler')
            _euler.euler.connect(_srt.rotate.get_input())

            _rotate = _srt.find('rotate')
            _rotate.x.connect(_euler.x)
            _rotate.y.connect(_euler.y)
            _rotate.z.connect(_euler.z)

            _srt.rotate.connect(_rotate.euler)

            sk_aims.append(_rotate.get_plug(aim_axis[-1]))

        tws = []
        for n in ik_nodes[1:-1]:
            expr = 'c'
            for k in chain + chain_sub:
                expr += '+' + k

            plugs = {}
            for k in n:
                _n = n[k].find('transform/rotate')
                if not _n:
                    continue
                plugs[k] = _n.get_plug(aim_axis[-1])

            tw = connect_expr(expr, **plugs)
            tws.append(tw)

        ctrls = [c_switch.twist_offset_base, c_switch.twist_offset_tip]
        blend_smooth_remap(ctrls, sk_aims)

        """
        r = kl.FloatToEuler(srt, 'rotate_twist')
        r.rotate_order.connect(srt.rotate_order)
        rs = {'x': r.x, 'y': r.y, 'z': r.z}

        if self.do_flip():
            ik_handle.twist_in.connect(c_switch.twist)
            rs[aim_axis[-1]].connect(c_switch.twist)
        else:
            _tw = connect_mult(c_switch.twist, -1, ik_handle.twist_in)
            rs[aim_axis[-1]].connect(_tw)

        rx = kl.SRTToTransformNode(r, 'transform')
        rx.rotate.connect(r.euler)
        rx.rotate_order.connect(r.rotate_order)

        mmx = kl.MultM44f(sk_chain[-1], 'transform_twist')
        mmx.input[0].connect(rx.transform)
        mmx.input[1].connect(sk_chain[-1].transform.get_input())
        sk_chain[-1].transform.connect(mmx.output)

        # -- ik twist
        sky = []
        for sk in sk_chain:
            sky.append(sk.find('transform/rotate').get_plug(aim_axis[-1]))

        add_plug(c_switch, 'twist_offset_base', float, keyable=True)
        add_plug(c_switch, 'twist_offset_tip', float, keyable=True)
        for c in [n['c'] for n in fk_nodes] + [n['c'] for n in ik_nodes]:
            add_plug(c, '_twist_offset_base', float, k=1)
            add_plug(c, '_twist_offset_tip', float, k=1)
            c._twist_offset_base.connect(c_switch.twist_offset_base)
            c._twist_offset_tip.connect(c_switch.twist_offset_tip)

        tws = []
        for n in ik_nodes[1:-1]:
            expr = 'c'
            for k in chain + chain_sub:
                expr += '+' + k

            plugs = {}
            for k in n:
                _n = n[k].find('transform/rotate')
                if not _n:
                    continue
                plugs[k] = _n.get_plug(aim_axis[-1])

            tw = connect_expr(expr, **plugs)
            tws.append(tw)

        ctrls = [c_switch.twist_offset_base] + tws + [c_switch.twist_offset_tip]
        blend_smooth_remap(ctrls, sky)
        """

        # switch proxy attributes
        for c in [n['c'] for n in fk_nodes] + [n['c'] for n in ik_nodes]:
            add_plug(c, '_uniform_ik', float, k=1)
            add_plug(c, '_stretch', float, k=1)
            add_plug(c, '_squash', float, k=1)
            add_plug(c, '_slide', float, k=1)

            add_plug(c, '_twist', float, k=1)
            add_plug(c, '_twist_offset_base', float, k=1)
            add_plug(c, '_twist_offset_tip', float, k=1)

            c._uniform_ik.connect(c_switch.uniform_ik)
            c._stretch.connect(c_switch.stretch)
            c._squash.connect(c_switch.squash)
            c._slide.connect(c_switch.slide)

            c._twist.connect(c_switch.twist)
            c._twist_offset_base.connect(c_switch.twist_offset_base)
            c._twist_offset_tip.connect(c_switch.twist_offset_tip)

        # tweakers
        do_tweakers = self.get_opt('tweakers')
        if do_tweakers != 'off':
            chained = do_tweakers == 'chained'

            tweakers = []

            parent = ik_nodes[0]['j']
            offsets = [ik_nodes[0]['j']] + sk_chain

            for i, j in enumerate(sk_chain):
                offset = offsets[i]
                if not chained:
                    offset = offsets[0]

                root = kl.Joint(parent, 'root_' + n_chain + '_tweaker' + str(i + 1))
                c = kl.Joint(root, 'c_' + n_chain + '_tweaker' + str(i + 1))
                create_srt_in(c, keyable=True)

                mmx = kl.MultM44f(root, '_mmx')
                mmx.input[0].connect(j.world_transform)
                imx = kl.InverseM44f(root, '_imx')
                imx.input.connect(offset.world_transform)
                mmx.input[1].connect(imx.output)
                root.transform.connect(mmx.output)

                if chained:
                    parent = c

                sk = kl.Joint(c, 'sk_' + n_chain + str(i + 1))
                if i < len(offsets) - 2:
                    end = kl.Joint(sk, 'end_' + n_chain + str(i + 1))
                    copy_transform(offsets[i + 2], end)

                tweaker = {}
                tweaker['root'] = root
                tweaker['c'] = c
                tweaker['sk'] = sk
                tweakers.append(tweaker)

            for i, tweaker in enumerate(tweakers):
                self.set_id(tweaker['root'], 'roots.tweaker.{}'.format(i))
                self.set_id(tweaker['c'], 'ctrls.tweaker.{}'.format(i))
                self.set_id(tweaker['sk'], 'skin.{}'.format(i))
