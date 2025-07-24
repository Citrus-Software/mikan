# coding: utf-8

import meta_nodal_py as kl
from meta_nodal_py.Imath import V3f, M44f, Euler

import mikan.tangerine.core as mk
from mikan.tangerine.lib import *
from mikan.tangerine.lib.rig import *
from mikan.tangerine.lib.nurbs import create_curve_weightmaps, rebuild_curve
from mikan.vendor.geomdl.utilities import generate_knot_vector
from mikan.core.prefs import Prefs


class Template(mk.Template):

    def build_template(self, data):
        root = self.node
        root.rename('tpl_neck'.format(self.name))

        head = kl.Joint(root, 'tpl_head')
        head_tip = kl.Joint(head, 'tpl_head_tip')

        root.transform.set_value(M44f(V3f(0, 0.1, 0), V3f(0, 0, 0), V3f(1, 1, 1), Euler.XYZ))
        head.transform.set_value(M44f(V3f(0, 1, 0.1), V3f(0, 0, 0), V3f(1, 1, 1), Euler.XYZ))
        head_tip.transform.set_value(M44f(V3f(0, 3, 0), V3f(0, 0, 0), V3f(1, 1, 1), Euler.XYZ))

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

        # build chain
        n = {}
        chain = []

        self.n = n
        n['chain'] = chain

        for i, tpl in enumerate(tpl_chain):
            nodes = {}
            chain.append(nodes)

            n_joint = '{}{}'.format(n_neck, i + 1)

            parent = hook
            if i > 0:
                parent = chain[i - 1]['ctrl']

            nodes['ctrl'] = kl.Joint(parent, 'c_' + n_joint + n_end)
            copy_transform(tpl, nodes['ctrl'], t=1)

        orient_joint([nodes['ctrl'] for nodes in chain], aim=aim_axis, up=up_axis, up_dir=(1, 0, 0))

        # build control rig
        for i, tpl in enumerate(tpl_chain):
            nodes = chain[i]
            n_joint = '{}{}'.format(n_neck, i + 1)

            nodes['root'] = kl.Joint(hook, 'root_' + n_joint + n_end)
            copy_transform(tpl, nodes['root'], t=1)

            nodes['ctrl'].reparent(nodes['root'])
            if i > 0:
                nodes['root'].reparent(chain[i - 1]['ctrl'])

        # modify head
        n['c_h'] = chain[-1]['ctrl']
        n['c_h'].rename('c_' + n_head + n_end)
        chain[-1]['root'].rename('root_' + n_head + n_end)

        orient_joint([chain[-1]['root'], chain[-1]['ctrl']], aim=aim_axis, up=up_axis, aim_dir=(0, 1, 0), up_dir=(1, 0, 0))

        _j = duplicate_joint(chain[-1]['root'], p=chain[-1]['root'].get_parent(), name='o_' + n_head + n_end)
        chain[-1]['root'].reparent(_j)
        chain[-1]['root'] = _j

        # IK offset
        n['c_last'] = n['c_h']

        if do_offset:
            n['root_ho'] = kl.Joint(n['c_h'], 'root_' + n_head + '_offset' + n_end)
            n['c_ho'] = kl.Joint(n['root_ho'], 'c_' + n_head + '_offset' + n_end)

            n['c_last'] = n['c_ho']

        # switch
        c_switch = kl.SceneGraphNode(chain[0]['root'], 'c_' + n_neck + '_switch' + n_end)

        # ik spline rig
        j_neckIK_dn = kl.Joint(chain[0]['root'], 'j_' + n_neck + 'IK_dn' + n_end)
        end_neckIK_dn = kl.Joint(j_neckIK_dn, 'end_' + n_neck + 'IK_dn' + n_end)
        j_neckIK_up = kl.Joint(n['c_last'], 'j_' + n_neck + 'IK_up' + n_end)
        end_neckIK_up = kl.Joint(j_neckIK_up, 'end_' + n_neck + 'IK_up' + n_end)

        cps = [tpl_chain[0].world_transform.get_value().translation()]
        if len(tpl_chain) == 2:
            v1 = tpl_chain[0].world_transform.get_value().translation()
            v2 = tpl_chain[1].world_transform.get_value().translation()
            end_neckIK_dn.set_world_transform(M44f((v1 + v2) / 2, V3f(0, 0, 0), V3f(1, 1, 1), Euler.XYZ))
            end_neckIK_up.set_world_transform(M44f((v1 + v2) / 2, V3f(0, 0, 0), V3f(1, 1, 1), Euler.XYZ))
            cps.append(end_neckIK_dn.world_transform.get_value().translation())
        else:
            copy_transform(chain[1]['root'], end_neckIK_dn, t=1)
            copy_transform(chain[-2]['root'], end_neckIK_up, t=1)
            for nodes in chain[1:-1]:
                cps.append(nodes['root'].world_transform.get_value().translation())
        cps.append(tpl_chain[-1].world_transform.get_value().translation())

        orient_joint((j_neckIK_dn, end_neckIK_dn), aim='y', up='x', up_dir=(1, 0, 0))
        orient_joint((j_neckIK_up, end_neckIK_up), aim='-y', up='x', up_dir=(1, 0, 0))

        orient_constraint((chain[0]['ctrl']), j_neckIK_dn, mo=1)
        aim_constraint((chain[-1]['ctrl']), j_neckIK_dn, aim_vector=axis_to_vector(aim_axis), up_vector=(0, 0, 0), mo=1)

        j_neckIK_dn.blend_rotate.set_value(self.get_opt('rigidity_dn'))
        if self.get_opt('rigidity'):
            add_plug(c_switch, 'rigidity_dn', float, keyable=True, min_value=0, max_value=1)
            connect_reverse(c_switch.rigidity_dn, j_neckIK_dn.blend_rotate)

        if len(tpl_chain) > 2:
            aim_constraint([c['ctrl'] for c in chain[1:-1]], j_neckIK_up, aim_vector=axis_to_vector(aim_axis) * -1, up_vector=(0, 0, 0), force_blend=True)
        else:
            aim_constraint(end_neckIK_dn, j_neckIK_up, aim_vector=axis_to_vector(aim_axis) * -1, up_vector=(0, 0, 0), force_blend=True)

        xfo = j_neckIK_up.transform.get_value()
        r = xfo.rotation(Euler.XYZ)
        r_vector = j_neckIK_up.find('transform/rotate')
        r_vector.x.set_value(r[0])
        r_vector.y.set_value(r[1])
        r_vector.z.set_value(r[2])

        j_neckIK_up.blend_rotate.set_value(self.get_opt('rigidity_up'))
        if self.get_opt('rigidity'):
            add_plug(c_switch, 'rigidity_up', float, keyable=True, min_value=0, max_value=1)
            connect_reverse(c_switch.rigidity_up, j_neckIK_up.blend_rotate)

        j_neckIK_aim = kl.Joint(j_neckIK_dn, 'j_' + n_neck + 'IK_aim' + n_end)
        j_neckIK_aim.reparent(chain[0]['root'])
        aim_constraint(end_neckIK_up, j_neckIK_aim, aim_vector=(0, 1, 0), up_vector=(0, 0, 0))

        # skin curve
        cv_neck = kl.SceneGraphNode(find_root(), 'cv_' + n_neck)
        spline_neck = kl.SplineCurve(cv_neck, 'cv_' + n_neck + 'Shape')
        self.set_template_id(cv_neck, 'curve')

        knots = generate_knot_vector(2, len(cps))
        weights = [1] * len(cps)
        spline_data = kl.Spline(cps, knots, weights, False)
        spline_neck.spline_in.set_value(spline_data)
        cv_neck.reparent(chain[0]['root'])
        cv_neck.show.set_value(False)

        infs = [j_neckIK_dn, j_neckIK_up]
        maps = [mk.WeightMap("1 0.5 0"), mk.WeightMap("0 0.5 1")]

        # -- rebuild curve
        if len(tpl_chain) > 2:
            spans = len(tpl_chain) * 2 - 1
            rebuild_curve(spline_neck, 3, spans)

            # update maps
            maps = create_curve_weightmaps(spline_neck, infs)

        bpm_skin_curve = kl.SceneGraphNode(chain[0]['root'], 'bpm_' + n_neck + '_curve' + n_end)
        bpm_neckIK_dn = kl.SceneGraphNode(j_neckIK_dn, 'bpm_' + n_neck + 'IK_dn' + n_end)
        bpm_neckIK_up = kl.SceneGraphNode(j_neckIK_up, 'bpm_' + n_neck + 'IK_up' + n_end)
        bpm_neckIK_dn.reparent(bpm_skin_curve)
        bpm_neckIK_up.reparent(bpm_skin_curve)
        bpm_skin_curve.show.set_value(False)

        bpms = [bpm_neckIK_dn, bpm_neckIK_up]

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
        skin_dfm.normalize()
        skin_dfm.build()
        cv_neck_geo = skin_dfm.geometry

        # ik joints
        num_bones = self.get_opt('bones')
        bone_length = self.get_opt('bones_length')
        ik_chain = create_joints_on_curve(cv_neck_geo, num_bones, mode=bone_length, name='ik_{n}{{i}}{e}'.format(n=n_neck, e=n_end))
        ik_chain[0].reparent(chain[0]['root'])  # j_neckIK_aim

        orient_joint(ik_chain, aim=aim_axis, up=up_axis, up_dir=(1, 0, 0))
        copy_transform(n['c_h'], ik_chain[-1], r=1)

        # rig ik
        spline_ik = stretch_spline_IK(cv_neck_geo, ik_chain)
        spline_ik.set_parent(chain[0]['root'])
        spline_ik.rename('ik_' + n_neck)

        # twist
        spline_ik.up_vector_in.set_value(V3f(1, 0, 0))
        spline_ik.start_up_vector_space_in.connect(j_neckIK_aim.world_transform)
        spline_ik.start_up_vector_in_space_in.set_value(V3f(1, 0, 0))
        spline_ik.end_up_vector_space_in.connect(j_neckIK_up.world_transform)
        spline_ik.end_up_vector_in_space_in.set_value(V3f(1, 0, 0))

        # -- twist
        j_neckIK_aim = kl.Joint(j_neckIK_dn, 'j_' + n_neck + 'IK_aim' + n_end)
        aim_constraint(end_neckIK_up, j_neckIK_aim, aim_vector=(0, 1, 0), up_vector=(0, 0, 0))

        j_neckIK_tw = kl.Joint(j_neckIK_aim, 'j_' + n_neck + 'IK_tw' + n_end)
        end_neckIK_tw = kl.Joint(j_neckIK_tw, 'end_' + n_neck + 'IK_tw' + n_end)

        bl = kl.BlendTransformsNode(end_neckIK_tw, '_blend')
        bl.transform1_in.connect(tpl_chain[0].world_transform)
        bl.transform2_in.connect(tpl_head.world_transform)
        bl.blend_in.set_value(0.5)
        end_neckIK_tw.set_world_transform(bl.transform_out.get_value())
        bl.remove_from_parent()

        tx = twist_constraint(end_neckIK_up, j_neckIK_tw, twist_vector=(0, 1, 0))
        tx.enable_in.set_value(0.5)

        # neck mid-cluster
        root_neckIK_mid = kl.SceneGraphNode(j_neckIK_tw, 'root_' + n_neck + 'IK_mid' + n_end)
        c_neckIK_mid = kl.SceneGraphNode(root_neckIK_mid, 'c_' + n_neck + 'IK_mid' + n_end)
        create_srt_in(c_neckIK_mid, k=1)

        if len(tpl_chain) > 2:
            point_constraint((end_neckIK_dn, end_neckIK_up), root_neckIK_mid)
        else:
            point_constraint((j_neckIK_dn, end_neckIK_dn, j_neckIK_up, end_neckIK_up), root_neckIK_mid)

        wm = mk.WeightMap("0 2 0")
        if len(tpl_chain) > 2:
            _maps = create_curve_weightmaps(spline_neck, [j_neckIK_dn, root_neckIK_mid, j_neckIK_up])
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

        # create srt
        for _ch in chain:
            create_srt_in(_ch['ctrl'], k=1)
        if do_offset:
            create_srt_in(n['c_ho'], k=1)

        legacy = Prefs.get('template/neck.legacy/rotate_orders', 1)
        if legacy == 1:
            find_srt(n['c_h']).rotate_order.set_value(Euler.XZY)
            if do_offset:
                find_srt(n['c_ho']).rotate_order.set_value(Euler.XZY)

        # stretch attributes
        add_plug(c_switch, 'stretch', float, k=1, default_value=0, min_value=0, max_value=1, nice_name='Stretch')
        add_plug(c_switch, 'squash', float, k=1, default_value=0, min_value=0, max_value=1, nice_name='Squash')
        add_plug(c_switch, 'slide', float, k=1, default_value=0, min_value=-1, max_value=1, nice_name='Slide')
        spline_ik.stretch.connect(c_switch.stretch)
        spline_ik.squash.connect(c_switch.squash)
        spline_ik.slide.connect(c_switch.slide)

        if self.get_opt('default_stretch'):
            c_switch.stretch.set_value(1)

        add_plug(c_switch, 'stretch_mode', int, enum=['scale', 'translate'], nice_name='Stretch Mode')
        c_switch.stretch_mode.set_value({'scale': 0, 'translate': 1}[self.get_opt('stretch_mode')])

        for c in [_ch['ctrl'] for _ch in chain] + [c_neckIK_mid]:
            if self.get_opt('rigidity'):
                add_plug(c, '_rigidity_dn', float, k=1, default_value=0, min_value=0, max_value=1)
                add_plug(c, '_rigidity_up', float, k=1, default_value=0, min_value=0, max_value=1)
                c._rigidity_dn.connect(c_switch.rigidity_dn)
                c._rigidity_up.connect(c_switch.rigidity_up)

            add_plug(c, '_stretch', float, k=1, default_value=0, min_value=0, max_value=1)
            add_plug(c, '_squash', float, k=1, default_value=0, min_value=0, max_value=1)
            add_plug(c, '_slide', float, k=1, default_value=0, min_value=0, max_value=1)
            c._stretch.connect(c_switch.stretch)
            c._squash.connect(c_switch.squash)
            c._slide.connect(c_switch.slide)

        # skin skeleton
        sk_chain = []
        for i, ik in enumerate(ik_chain[:-1]):
            sk = kl.Joint(ik, ik.get_name().replace('ik_', 'sk_'))
            sk_chain.append(sk)
            safe_connect(c_switch.stretch_mode, sk.scale_compensate)

            _end = kl.Joint(sk, ik.get_name().replace('ik_', 'end_'))
            copy_transform(ik_chain[i + 1], _end, t=1)

        skx = []
        skz = []
        for sk in sk_chain:
            _srt = create_srt_in(sk)
            skx.append(_srt.find('scale').x)
            skz.append(_srt.find('scale').z)
        _srt = create_srt_in(_end)
        skx.append(_srt.find('scale').x)
        skz.append(_srt.find('scale').z)
        _end.transform.disconnect(False)

        blend_smooth_remap([c.find('transform/scale').x for c in (chain[0]['ctrl'], c_neckIK_mid, n['c_h'])], skx)
        blend_smooth_remap([c.find('transform/scale').z for c in (chain[0]['ctrl'], c_neckIK_mid, n['c_h'])], skz)

        for i, ik in enumerate(ik_chain):
            if ik.get_dynamic_plug('squash'):
                sk = sk_chain[i]
                _s = sk.find('transform/scale')
                connect_mult(ik.squash, _s.x.get_input(), _s.x)
                connect_mult(ik.squash, _s.z.get_input(), _s.z)

        n['j_h'] = kl.Joint(ik_chain[-1], 'j_' + n_head + n_end)
        n['sk_h'] = kl.Joint(n['j_h'], 'sk_' + n_head + n_end)
        n['end_h'] = kl.Joint(n['sk_h'], 'end_' + n_head + n_end)
        copy_transform(tpl_tip, n['end_h'], t=1)
        orient_joint(n['j_h'], aim=aim_axis, up=up_axis, aim_dir=(0, 1, 0), up_dir=(1, 0, 0))

        create_srt_in(n['j_h'])
        orient_constraint(n['c_last'], n['j_h'])

        # stretch and squash ctrl
        self._make_scale()

        # space switch nodes
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
                    'rest_name': 'neck',
                    'targets': ['*::space.world'],
                    'point': True,
                }
            )

        # # face cam
        # self._make_cam()

        # hooks
        hook_head = kl.SceneGraphNode(rig_hook, 'hook_' + n_head + n_end)
        hook_head.transform.connect(n['sk_h'].world_transform)

        # vis group
        grp = mk.Group.create('{}{} shape'.format(n_neck, self.get_branch_suffix(' ')))
        grp.add_member(c_neckIK_mid)
        self.set_id(grp.node, 'vis.shape')

        if do_offset:
            n['c_ho'].show.set_value(False)
            grp = mk.Group.create('{}{} offset'.format(n_neck, self.get_branch_suffix(' ')))
            grp.add_member(n['c_ho'])
            self.set_id(grp.node, 'vis.offset')

        # tags
        for i, tpl in enumerate(tpl_chain):
            self.set_hook(tpl, ik_chain[i], 'hooks.neck.{}'.format(i))

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

    def _make_scale(self):
        n = self.n

        n_end = self.get_branch_suffix()
        n_head = self.get_name('head')

        do_offset = self.get_opt('offset_ctrl')

        # build
        n['c_s'] = kl.SceneGraphNode(n['j_h'], 'c_' + n_head + '_scale' + n_end)
        n['s_s'] = kl.SceneGraphNode(n['c_s'], 's_' + n_head + '_scale' + n_end)
        n['neg_s'] = kl.SceneGraphNode(n['s_s'], 'neg_' + n_head + '_scale' + n_end)

        _srt = kl.SRTToTransformNode(n['s_s'], 'transform')
        s = kl.FloatToV3f(_srt, 'scale')
        s.x.set_value(1)
        s.y.set_value(1)
        s.z.set_value(1)
        _srt.scale.connect(s.vector)
        n['s_s'].transform.connect(_srt.transform)
        n['sk_h'].reparent(n['neg_s'])

        add_plug(n['c_h'], 'scale_factor', float, min_value=0.1, default_value=1)
        add_plug(n['c_h'], 'scale_offset', float, min_value=0.1, default_value=1)

        n['sk_h'].scale_compensate.set_value(False)
        _s = connect_mult(n['c_h'].scale_factor, n['c_h'].scale_offset)
        _srt_c = create_srt_in(n['c_h']).find('scale')
        _srt_sk = create_srt_in(n['sk_h']).find('scale')

        if do_offset:
            _srt_co = create_srt_in(n['c_ho']).find('scale')
            connect_expr('s = h * ho * f', s=_srt_sk.x, h=_srt_c.x, ho=_srt_co.x, f=_s)
            connect_expr('s = h * ho * f', s=_srt_sk.y, h=_srt_c.y, ho=_srt_co.y, f=_s)
            connect_expr('s = h * ho * f', s=_srt_sk.z, h=_srt_c.z, ho=_srt_co.z, f=_s)
        else:
            connect_expr('s = h * f', s=_srt_sk.x, h=_srt_c.x, f=_s)
            connect_expr('s = h * f', s=_srt_sk.y, h=_srt_c.y, f=_s)
            connect_expr('s = h * f', s=_srt_sk.z, h=_srt_c.z, f=_s)

        add_plug(n['c_h'], 'height', float)
        add_plug(n['c_s'], 'squash', float, min_value=0, max_value=1, default_value=1)

        # squash rig
        create_srt_in(n['c_s'], k=1)
        c = n['c_s'].find('transform').find('scale')
        abs_sqx = kl.Abs(n['c_s'], '_abs_x')
        abs_sqy = kl.Abs(n['c_s'], '_abs_y')
        abs_sqz = kl.Abs(n['c_s'], '_abs_z')
        abs_sqx.input.connect(c.x)
        abs_sqy.input.connect(c.y)
        abs_sqz.input.connect(c.z)

        sqrt_sqx = kl.Pow(n['c_s'], '_sqrt_x')
        sqrt_sqy = kl.Pow(n['c_s'], '_sqrt_y')
        sqrt_sqz = kl.Pow(n['c_s'], '_sqrt_z')
        sqrt_sqx.input2.set_value(0.5)
        sqrt_sqy.input2.set_value(0.5)
        sqrt_sqz.input2.set_value(0.5)

        sqrt_sqx.input1.connect(abs_sqx.output)
        sqrt_sqy.input1.connect(abs_sqy.output)
        sqrt_sqz.input1.connect(abs_sqz.output)

        div_sqx = kl.Div(n['c_s'], '_div_x')
        div_sqy = kl.Div(n['c_s'], '_div_y')
        div_sqz = kl.Div(n['c_s'], '_div_z')
        div_sqx.input1.set_value(1)
        div_sqy.input1.set_value(1)
        div_sqz.input1.set_value(1)

        div_sqx.input2.connect(sqrt_sqx.output)
        div_sqy.input2.connect(sqrt_sqy.output)
        div_sqz.input2.connect(sqrt_sqz.output)

        sqx = div_sqx.output
        sqy = div_sqy.output
        sqz = div_sqz.output

        sub_cx = kl.Sub(n['c_s'], '_sub_x')
        sub_cy = kl.Sub(n['c_s'], '_sub_y')
        sub_cz = kl.Sub(n['c_s'], '_sub_z')
        sub_cx.input1.set_value(1)
        sub_cy.input1.set_value(1)
        sub_cz.input1.set_value(1)

        sub_cx.input2.connect(n['c_s'].squash)
        sub_cy.input2.connect(n['c_s'].squash)
        sub_cz.input2.connect(n['c_s'].squash)

        mult_cx1 = kl.Mult(n['c_s'], '_mult_x')
        mult_cy1 = kl.Mult(n['c_s'], '_mult_y')
        mult_cz1 = kl.Mult(n['c_s'], '_mult_z')

        mult_cx1.input1.connect(sub_cx.output)
        mult_cx1.input2.connect(c.x)
        mult_cy1.input1.connect(sub_cy.output)
        mult_cy1.input2.connect(c.y)
        mult_cz1.input1.connect(sub_cz.output)
        mult_cz1.input2.connect(c.z)

        mult_cx2 = kl.Mult(n['c_s'], '_mult_x')
        mult_cy2 = kl.Mult(n['c_s'], '_mult_y')
        mult_cz2 = kl.Mult(n['c_s'], '_mult_z')

        mult_cx2.input1.connect(c.x)
        mult_cy2.input1.connect(c.y)
        mult_cz2.input1.connect(c.z)
        mult_cx2.input2.connect(sqy)
        mult_cy2.input2.connect(sqx)
        mult_cz2.input2.connect(sqx)

        mult_cx3 = kl.Mult(n['c_s'], '_mult_x')
        mult_cy3 = kl.Mult(n['c_s'], '_mult_y')
        mult_cz3 = kl.Mult(n['c_s'], '_mult_z')

        mult_cx3.input1.connect(mult_cx2.output)
        mult_cy3.input1.connect(mult_cy2.output)
        mult_cz3.input1.connect(mult_cz2.output)
        mult_cx3.input2.connect(sqz)
        mult_cy3.input2.connect(sqy)
        mult_cz3.input2.connect(sqy)

        mult_cx4 = kl.Mult(n['c_s'], '_mult_x')
        mult_cy4 = kl.Mult(n['c_s'], '_mult_y')
        mult_cz4 = kl.Mult(n['c_s'], '_mult_z')

        mult_cx4.input1.connect(mult_cx3.output)
        mult_cy4.input1.connect(mult_cy3.output)
        mult_cz4.input1.connect(mult_cz3.output)
        mult_cx4.input2.connect(n['c_s'].squash)
        mult_cy4.input2.connect(n['c_s'].squash)
        mult_cz4.input2.connect(n['c_s'].squash)

        add_cx = kl.Add(n['c_s'], '_add_x')
        add_cy = kl.Add(n['c_s'], '_add_y')
        add_cz = kl.Add(n['c_s'], '_add_z')

        add_cx.input1.connect(mult_cx1.output)
        add_cy.input1.connect(mult_cy1.output)
        add_cz.input1.connect(mult_cz1.output)
        add_cx.input2.connect(mult_cx4.output)
        add_cy.input2.connect(mult_cy4.output)
        add_cz.input2.connect(mult_cz4.output)

        s.x.connect(add_cx.output)
        s.y.connect(add_cy.output)
        s.z.connect(add_cz.output)

        c_inv = kl.InverseM44f(n['c_s'], '_imx')
        c_inv.input.connect(n['c_s'].transform)

        root_inv = kl.InverseM44f(n['c_s'], '_imx')
        root_inv.input.connect(n['c_s'].transform)
        n['neg_s'].transform.connect(c_inv.output)
        c_node_mmx = kl.MultM44f(n['c_s'], '_mmx')
        c_node_mmx.input[1].connect(c_inv.output)
        c_node_mmx.input[0].connect(root_inv.output)

        # tags
        self.set_id(n['c_s'], 'ctrls.scale')
