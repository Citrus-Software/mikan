# coding: utf-8

import meta_nodal_py as kl
from meta_nodal_py.Imath import V3f, M44f, Euler

import mikan.tangerine.core as mk
from mikan.tangerine.lib.rig import parent_constraint, create_srt_in
from mikan.tangerine.lib.connect import connect_expr
from mikan.tangerine.lib.commands import *
from mikan.core.prefs import Prefs


class Template(mk.Template):

    def build_template(self, data):
        self.node.rename('tpl_{}'.format(self.name))
        root = kl.Joint(self.node, 'tpl_root')
        root.transform.set_value(M44f(V3f(0, data['height'], 0), V3f(0, 0, 0), V3f(1, 1, 1), Euler.XYZ))
        root.scale_compensate.set_value(False)

    def build_rig(self):
        n_world = self.get_name('world')
        n_move = self.get_name('move')
        n_fly = self.get_name('fly')
        n_scale = self.get_name('scale')
        tpl_root = self.get_structure('root')[0]

        do_fly = self.get_opt('fly')
        do_scale = self.get_opt('scale')

        hook = self.get_first_hook()
        world = kl.SceneGraphNode(hook, n_world)
        if do_scale:
            s_move = kl.SceneGraphNode(world, 's_' + n_move)
            move = kl.SceneGraphNode(s_move, n_move)
        else:
            move = kl.SceneGraphNode(world, n_move)
        rig = self.get_rig_hook()

        for node in [world, move]:
            create_srt_in(node, k=1)

        if do_fly:
            if do_scale:
                s_fly = kl.SceneGraphNode(move, 's_' + n_fly)
                root_fly = kl.SceneGraphNode(s_fly, 'root_' + n_fly)
            else:
                root_fly = kl.SceneGraphNode(move, 'root_' + n_fly)
            p = tpl_root.world_transform.get_value().translation()
            root_fly.transform.set_value(M44f(p, V3f(0, 0, 0), V3f(1, 1, 1), Euler.XYZ))
            c_fly = kl.SceneGraphNode(root_fly, 'c_' + n_fly)
            create_srt_in(c_fly, k=1)

        # scale
        if do_scale:
            scale_move = Prefs.get('template/world.character/scale_move', 1)

            add_plug(world, 'scale_factor', float, min_value=0.01, default_value=1, nice_name='Scale Factor')
            add_plug(world, 'scale_offset', float, k=1, min_value=0.01, default_value=1, nice_name='Scale Offset')
            add_plug(world, 'scale_move', bool, k=1, nice_name='Scale Move', default_value=bool(scale_move))

            _srt = create_srt_in(s_move)
            _s0 = _srt.find('scale')
            _srt = create_srt_in(s_fly)
            _s1 = _srt.find('scale')

            _m = connect_expr('factor * offset', factor=world.scale_factor, offset=world.scale_offset)
            _m0 = connect_expr('w==1 ? s : 1', s=_m, w=world.scale_move)
            _m1 = connect_expr('w==1 ? 1 : s', s=_m, w=world.scale_move)
            _s0.x.connect(_m0)
            _s0.y.connect(_m0)
            _s0.z.connect(_m0)
            _s1.x.connect(_m1)
            _s1.y.connect(_m1)
            _s1.z.connect(_m1)

            root_scale = kl.SceneGraphNode(c_fly, 'root_' + n_scale)
            root_scale.set_world_transform(world.transform.get_value())

            c_scale = kl.SceneGraphNode(root_scale, 'c_' + n_scale)
            _srt = create_srt_in(c_scale, k=1)
            _c = _srt.find('scale')
            add_plug(c_scale, 'squash', float, k=1, min_value=0, max_value=1, default_value=1, nice_name='Squash')

            s_scale = kl.SceneGraphNode(c_scale, 's_' + n_scale)
            _srt = create_srt_in(s_scale)
            _s = _srt.find('scale')

            # squash rig
            sqx = connect_expr('pow(abs(c), -0.5)', c=_c.x)
            sqy = connect_expr('pow(abs(c), -0.5)', c=_c.y)
            sqz = connect_expr('pow(abs(c), -0.5)', c=_c.z)
            connect_expr('s = lerp(c, c*sq1*sq2, sq)', s=_s.x, c=_c.x, sq1=sqy, sq2=sqz, sq=c_scale.squash)
            connect_expr('s = lerp(c, c*sq1*sq2, sq)', s=_s.y, c=_c.y, sq1=sqx, sq2=sqz, sq=c_scale.squash)
            connect_expr('s = lerp(c, c*sq1*sq2, sq)', s=_s.z, c=_c.z, sq1=sqx, sq2=sqy, sq=c_scale.squash)

            rev_scale = kl.SceneGraphNode(s_scale, 'rev_' + n_scale)

            c_inv = kl.InverseM44f(c_scale, '_imx')
            c_inv.input.connect(c_scale.transform)
            root_inv = kl.InverseM44f(root_scale, '_imx')
            root_inv.input.connect(root_scale.transform)
            _mmx = kl.MultM44f(rev_scale, '_mmx')
            _mmx.input[1].connect(c_inv.output)
            _mmx.input[0].connect(root_inv.output)

            rev_scale.transform.connect(_mmx.output)

            # follow
            if do_fly:
                add_plug(c_scale, "follow_world", float, k=1, nice_name="Follow World", default_value=0, min_value=0, max_value=1)

                pc_scale = parent_constraint([c_fly, world], root_scale, mo=True)
                connect_expr('w0 = 1-w', w0=pc_scale.w0, w=c_scale.follow_world)
                connect_expr('w1 = w', w1=pc_scale.w1, w=c_scale.follow_world)

        if do_scale:
            loc_fly = kl.SceneGraphNode(rev_scale, 'loc_' + n_fly)
        elif do_fly:
            loc_fly = kl.SceneGraphNode(c_fly, 'loc_' + n_fly)
        else:
            loc_fly = kl.SceneGraphNode(move, 'loc_' + n_fly)
        if do_fly:
            loc_fly.set_world_transform(c_fly.world_transform.get_value())

        # height
        add_plug(world, 'height', float)
        _srt = create_srt_in(loc_fly)
        _srt.find('translate').y.connect(world.height)

        # hook
        hook_root = kl.SceneGraphNode(rig, 'hook_root')
        hook_root.transform.connect(loc_fly.world_transform)

        # register -----------------------------------------------------------------------------------------------------
        self.set_id(hook_root, 'hook', template=False)

        self.set_id(world, 'ctrls.world')
        self.set_id(move, 'ctrls.move')
        if do_fly:
            self.set_id(c_fly, 'ctrls.fly')
        if do_scale:
            self.set_id(c_scale, 'ctrls.scale')

        self.set_id(world, 'space.world')
        self.set_id(move, 'space.move')
        self.set_id(loc_fly, 'space.root')

        # result
        self.set_hook(self.node, world, 'hooks.world')
        self.set_hook(tpl_root, hook_root, 'hooks.root')
