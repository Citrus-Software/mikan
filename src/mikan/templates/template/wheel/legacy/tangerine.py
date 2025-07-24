# coding: utf-8

import meta_nodal_py as kl
from meta_nodal_py.Imath import V3f, M44f, Euler
from tang_core.document.get_document import get_document

import mikan.tangerine.core as mk
from mikan.tangerine.lib.rig import (
    copy_transform, create_srt_in, create_srt_out, find_srt,
    point_constraint, aim_constraint
)
from mikan.tangerine.lib.connect import connect_expr
from mikan.tangerine.lib.commands import add_plug
from mikan.tangerine.lib.dynamic import set_plug_temporal_cache_override_value


class Template(mk.Template):

    def build_template(self, data):
        tpl_axis = kl.Joint(self.node, 'tpl_axis')
        tpl_ground = kl.Joint(tpl_axis, 'tpl_ground')

        tpl_axis.transform.set_M44f(V3f(0.5, 0, 0), V3f(0, 0, 0), V3f(1, 1, 0), Euler.XYZ)
        tpl_ground.transform.set_M44f(V3f(0, -3.5, 0), V3f(0, 0, 0), V3f(1, 1, 0), Euler.XYZ)

        self.set_template_id(tpl_axis, 'axis')
        self.set_template_id(tpl_ground, 'ground')

    def build_rig(self):
        # init
        hook = self.get_hook()
        rig_hook = mk.Nodes.get_id('::rig')

        n_end = self.get_branch_suffix()
        n_loc = self.name

        tpl_swivel = self.get_structure('swivel')[0]
        tpl_wheel = self.get_structure('axis')[0]
        tpl_ground = self.get_structure('ground')[0]

        do_flip = self.do_flip()

        # get world
        move = mk.Nodes.get_id('world::space.move')
        if move:
            world = move
        elif self.get_opt('hook'):
            world = mk.Nodes.get_id(self.get_opt('hook'))
        else:
            world = mk.Nodes.get_id('world::ctrls.world')

        # create hierarchy
        root_swivel = kl.SceneGraphNode(hook, 'root_' + self.name + '_swivel' + n_end)
        copy_transform(tpl_swivel, root_swivel)
        if do_flip:
            _xfo = root_swivel.transform.get_value()
            _xfo = M44f(V3f(0, 0, 0), V3f(180, 0, 0), V3f(1, 1, 1), Euler.ZYX) * _xfo
            root_swivel.transform.set_value(_xfo)

        loc_swivel = kl.Joint(root_swivel, 'loc_' + self.name + '_swivel' + n_end)

        root_wheel_base = kl.SceneGraphNode(loc_swivel, 'root_' + self.name + '_base' + n_end)
        copy_transform(tpl_ground, root_wheel_base, t=True)

        c_wheel_base = kl.SceneGraphNode(root_wheel_base, 'c_' + self.name + '_base' + n_end)
        create_srt_in(c_wheel_base, keyable=1)
        loc_wheel_squash = kl.SceneGraphNode(c_wheel_base, 'loc_' + self.name + '_squash' + n_end)

        loc_ray = kl.SceneGraphNode(loc_wheel_squash, 'loc_' + self.name + '_ray' + n_end)
        copy_transform(tpl_wheel, loc_ray, t=True)
        loc_ray.show.set_value(False)

        rev_wheel = kl.SceneGraphNode(c_wheel_base, 'rev_' + self.name + n_end)
        _inv = kl.InverseM44f(rev_wheel, 'inv')

        world_parent = world.get_parent()
        inv_world = kl.InverseM44f(world_parent, 'inv_world')
        inv_world.input.connect(world_parent.transform)

        def mult_inv_world_output(sg_node):
            # return sg_node.world_transform
            _mult_inv_world = kl.MultM44f(inv_world, sg_node.get_name() + '_mult_inv_world')
            _mult_inv_world.input[0].connect(sg_node.world_transform)
            _mult_inv_world.input[1].connect(inv_world.output)
            return _mult_inv_world.output

        _inv.input.connect(mult_inv_world_output(c_wheel_base))
        rev_wheel.transform.connect(_inv.output)

        loc_wheel_world = kl.SceneGraphNode(rev_wheel, 'loc_' + self.name + '_world' + n_end)
        point_constraint(c_wheel_base, loc_wheel_world)
        create_srt_out(loc_wheel_world)

        loc_ray_world = kl.SceneGraphNode(loc_wheel_world, 'loc_' + self.name + '_ray_world' + n_end)
        point_constraint(loc_ray, loc_ray_world)
        create_srt_out(loc_ray_world, vectors=False)

        loc_trail_world = kl.SceneGraphNode(rev_wheel, 'loc_' + self.name + '_trail_world' + n_end)
        create_srt_in(loc_trail_world, vectors=False)

        loc_trail_local = kl.SceneGraphNode(c_wheel_base, 'loc_' + self.name + '_trail_local' + n_end)
        point_constraint(loc_trail_world, loc_trail_local)
        create_srt_out(loc_trail_local, vectors=False)

        loc_wheel_trail = kl.SceneGraphNode(loc_wheel_squash, 'loc_' + self.name + '_trail' + n_end)
        _srt = create_srt_in(loc_wheel_trail)
        _srt.find('translate').z.set_value(-1)

        loc_wheel_drive = kl.SceneGraphNode(loc_wheel_squash, 'loc_' + self.name + '_drive' + n_end)
        _srt = create_srt_in(loc_wheel_drive)
        _srt.rotate_order.set_value(Euler.XZY)
        aim_constraint(
            loc_wheel_trail,
            loc_wheel_drive,
            aim_vector=[0, 0, -1],
            up_vector=[0, 1, 0],
            up_vector_world=[0, 1, 0],
            up_object=c_wheel_base,
            axes='y'
        )

        ray_db = kl.Distance(rev_wheel, '_distance')
        _srt = create_srt_out(loc_ray)
        ray_db.input2.connect(_srt.translate)

        loc_dir = kl.SceneGraphNode(loc_wheel_drive, 'loc_' + self.name + '_dir' + n_end)
        _t = create_srt_in(loc_dir).find('translate')
        _t.y.connect(ray_db.output)
        _t.z.connect(ray_db.output)

        loc_drift = kl.SceneGraphNode(loc_wheel_drive, 'dyn_' + self.name + '_drift' + n_end)
        _srt_loc_drift = create_srt_in(loc_drift)
        _srt_loc_drift.find('translate').y.connect(ray_db.output)

        root_wheel = kl.SceneGraphNode(loc_drift, 'root_' + self.name + n_end)
        c_wheel = kl.SceneGraphNode(root_wheel, 'c_' + self.name + n_end)
        create_srt_in(c_wheel, keyable=True)
        sk_wheel = kl.Joint(c_wheel, 'sk_' + self.name + '_center' + n_end)

        dyn_motor = kl.SceneGraphNode(c_wheel, 'dyn_' + self.name + '_motor' + n_end)
        _srt_motor = create_srt_in(dyn_motor, keyable=True)

        c_spin = kl.SceneGraphNode(dyn_motor, 'c_spin_' + self.name + n_end)
        create_srt_in(c_spin, keyable=True)
        sk_spin = kl.Joint(c_spin, 'sk_' + self.name + n_end)

        # attributes and expression
        add_plug(c_wheel_base, 'delta', float)
        add_plug(c_wheel_base, 'direction', float)
        add_plug(c_wheel_base, 'drift', float)
        add_plug(c_wheel_base, 'wheel_ray', float)
        add_plug(c_wheel_base, 'oldX', float)
        add_plug(c_wheel_base, 'oldY', float)
        add_plug(c_wheel_base, 'oldZ', float)

        add_plug(c_wheel_base, 'start_frame', int, k=1, default_value=1)
        _pf = add_plug(c_wheel_base, 'friction', float, k=0, default_value=1, min_value=0, max_value=1)
        add_plug(c_wheel_base, 'drift_friction', float, k=1, default_value=0, min_value=0, max_value=1)
        add_plug(c_wheel_base, 'noise', float, k=1, min_value=0, max_value=1)
        add_plug(c_wheel_base, 'noise_freq', float, k=1, default_value=0.5, min_value=0, max_value=1)
        add_plug(c_wheel_base, 'squash', float, k=0, default_value=1, min_value=0, max_value=1)
        add_plug(c_wheel_base, 'weight', float, k=0, default_value=0, min_value=0, max_value=1)
        add_plug(c_wheel_base, 'drive_auto', float, k=1, min_value=0, max_value=1)
        add_plug(c_wheel_base, 'drive_free', float, k=1, default_value=0)

        _pr = add_plug(c_wheel, "auto_rotate", float, min_value=0.0, max_value=1.0, default_value=1.0, k=1)
        _pf.connect(_pr)

        # for callback after_load_asset
        set_plug_temporal_cache_override_value(get_document(), _pr, 0.0)

        # -- expression
        expr = kl.SceneGraphNode(c_wheel_base, 'expr_' + n_loc)

        time = kl.CurrentFrame(expr, 'time')
        frame = time.result

        c = find_srt(loc_wheel_world).translate
        c_old = kl.PreviousV3f(loc_wheel_world, '_previous')
        c_old.input.connect(c)
        c_old.init.set_value(c.get_value())

        _srt = find_srt(loc_trail_world)
        _srt.translate.connect(c_old.output)

        t = find_srt(loc_trail_local).translate
        t_len = connect_expr('len(t)', t=t, parent=expr)
        t = connect_expr('norm(t)', t=t, parent=expr)

        auto = c_wheel_base.drive_auto
        free = c_wheel_base.drive_free
        free = connect_expr('auto>0 ? free : 0', auto=auto, free=free, parent=expr)

        d = connect_expr('free | (t.z <= 0 ? on : off) == on ? 1 : -1', free=free, t=t, parent=expr)
        t = connect_expr('d * t', d=d, t=t, parent=expr)

        d = connect_expr('t_len < 0.0001 ? 0 : d', t_len=t_len, d=d, parent=expr)
        c_wheel_base.direction.connect(d)

        drift = connect_expr('abs(dot(t, [0, 0, -1]))', t=t, parent=expr)
        drift_side = connect_expr('t.x <= 0 ? 1 : -1', t=t, parent=expr)

        t = connect_expr('lerp([0, 0, -1], t, auto)', t=t, auto=auto, parent=expr)  # $t = $auto * $t + (1 - $auto) * <<0, 0, -1>>;
        drift = connect_expr('lerp(drift, 1, auto)', drift=drift, auto=auto, parent=expr)  # $drift = (1 - $auto) * $drift + $auto;

        _srt = find_srt(loc_wheel_trail)
        _srt.translate.connect(t)

        # motor rotation
        delta = connect_expr('len(c - old)', c=c, old=c_old.output, parent=expr)  # float $delta = mag($c - $old);

        _srt = find_srt(loc_ray_world, vectors=False)
        ray = connect_expr('len(ray)', ray=_srt.translate, parent=expr)

        friction = c_wheel_base.friction
        w = c_wheel_base.weight

        r = connect_expr(
            'delta / (2 * pi * ray) * 360 * drift * friction * d * (1-0.4*w)',
            delta=delta, ray=ray, drift=drift, friction=friction, d=d, w=w, parent=expr
        )

        acc = kl.Accumulate(expr, '_motor')
        acc.delta.connect(r)

        _r = connect_expr('frame >= start ? acc : 0', frame=frame, start=c_wheel_base.start_frame, acc=acc.accumulator, parent=expr)
        _srt_motor.find('rotate').x.connect(_r)

        drift_friction = connect_expr(
            '(1 - drift) * delta / ray * drift_side * dp * -10',
            drift=drift, delta=delta, ray=ray, drift_side=drift_side, dp=c_wheel_base.drift_friction
        )  # float $drift_friction = (1 - $drift) * $delta / $ray * $drift_side * $dp * -10;

        _r = connect_expr('frame >= start ? acc : 0', frame=frame, start=c_wheel_base.start_frame, acc=drift_friction, parent=expr)
        _srt_motor.find('rotate').z.connect(_r)

        freq = connect_expr('freq == 0 ? 100 : 1 / freq * 5', freq=c_wheel_base.noise_freq)
        noise = connect_expr('n>0 ? n * noise(rx/freq) * 10 : 0', n=c_wheel_base.noise, freq=freq, rx=_srt_motor.find('rotate').x)

        _srt_motor.find('rotate').y.connect(noise)

        c_wheel_base.wheel_ray.connect(ray)
        c_wheel_base.delta.connect(delta)
        c_wheel_base.drift.connect(connect_expr('1 - drift', drift=drift, parent=expr))

        # registering
        self.set_id(root_wheel_base, 'roots.bank')
        self.set_id(root_wheel, 'roots.wheel')

        self.set_id(c_wheel_base, 'ctrls.bank')
        self.set_id(c_wheel, 'ctrls.wheel')
        self.set_id(c_spin, 'ctrls.spin')

        self.set_id(sk_wheel, 'skin.wheel')
        self.set_id(sk_spin, 'skin.spin')
