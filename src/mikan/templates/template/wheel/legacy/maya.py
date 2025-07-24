# coding: utf-8

from mikan.maya import cmds as mc
import mikan.maya.cmdx as mx

import mikan.maya.core as mk
from mikan.maya.lib.connect import connect_matrix
from mikan.maya.lib.rig import copy_transform


class Template(mk.Template):

    def build_template(self, data):
        with mx.DagModifier() as md:
            tpl_axis = md.create_node(mx.tJoint, parent=self.node)
            tpl_ground = md.create_node(mx.tJoint, parent=tpl_axis)

        tpl_axis['t'] = (0.5, 0, 0)
        tpl_ground['t'] = (0, -3.5, 0)

        self.set_template_id(tpl_axis, 'axis')
        self.set_template_id(tpl_ground, 'ground')

    def rename_template(self):
        axis = self.get_structure('axis')[0]
        axis.rename('tpl_{}_axis'.format(self.name))

    def build_rig(self):

        # init
        hook = self.get_hook()

        n_end = self.get_branch_suffix()
        n_loc = self.name

        tpl_swivel = self.get_structure('swivel')[0]
        tpl_wheel = self.get_structure('axis')[0]
        tpl_ground = self.get_structure('ground')[0]

        do_flip = self.do_flip()

        # get world
        move = mk.Nodes.get_id('world::space.move')
        if move:
            ref = move
        elif self.get_opt('hook'):
            ref = mk.Nodes.get_id(self.get_opt('hook'))
        else:
            ref = mk.Nodes.get_id('world::ctrls.world')

        # create hierarchy
        root_swivel = mx.create_node(mx.tTransform, parent=hook, name='root_' + self.name + '_swivel' + n_end)
        copy_transform(tpl_swivel, root_swivel)
        if do_flip:
            mc.rotate(180, 0, 0, str(root_swivel), r=1, os=1)

        loc_swivel = mx.create_node(mx.tJoint, parent=root_swivel, name='loc_' + self.name + '_swivel' + n_end)

        root_wheel_base = mx.create_node(mx.tTransform, parent=loc_swivel, name='root_' + self.name + '_base' + n_end)
        copy_transform(tpl_ground, root_wheel_base, t=True)

        c_wheel_base = mx.create_node(mx.tTransform, parent=root_wheel_base, name='c_' + self.name + '_base' + n_end)
        loc_wheel_squash = mx.create_node(mx.tTransform, parent=c_wheel_base, name='loc_' + self.name + '_squash' + n_end)

        loc_ray = mx.create_node(mx.tTransform, parent=loc_wheel_squash, name='loc_' + self.name + '_ray' + n_end)
        copy_transform(tpl_wheel, loc_ray, t=True)
        loc_ray['v'] = False

        rev_wheel = mx.create_node(mx.tTransform, parent=c_wheel_base, name='rev_' + self.name + n_end)
        connect_matrix(c_wheel_base['wim'][0], rev_wheel)

        loc_wheel_world = mx.create_node(mx.tTransform, parent=rev_wheel, name='loc_' + self.name + '_world' + n_end)
        mc.pointConstraint(str(c_wheel_base), str(loc_wheel_world))

        loc_ray_world = mx.create_node(mx.tTransform, parent=loc_wheel_world, name='loc_' + self.name + '_ray_world' + n_end)
        mc.pointConstraint(str(loc_ray), str(loc_ray_world))

        loc_trail_world = mx.create_node(mx.tTransform, parent=rev_wheel, name='loc_' + self.name + '_trail_world' + n_end)
        loc_trail_world.add_attr(mx.Double3('old', keyable=True))
        loc_trail_world['tz'] = -1

        loc_trail_local = mx.create_node(mx.tTransform, parent=c_wheel_base, name='loc_' + self.name + '_trail_local' + n_end)
        mc.pointConstraint(str(loc_trail_world), str(loc_trail_local))

        loc_trail = mx.create_node(mx.tTransform, parent=loc_wheel_squash, name='loc_' + self.name + '_trail' + n_end)
        loc_trail['tz'] = -1

        loc_drive = mx.create_node(mx.tTransform, parent=loc_wheel_squash, name='loc_' + self.name + '_drive' + n_end)
        loc_drive['ro'] = mx.Euler.XZY
        mc.aimConstraint(
            str(loc_trail), str(loc_drive),
            aimVector=[0, 0, -1], upVector=[0, 1, 0],
            worldUpVector=[0, 1, 0], worldUpObject=str(c_wheel_base), worldUpType='objectRotation',
            skip=['x', 'z']
        )

        ray_db = mx.create_node(mx.tDistanceBetween, name='_ray#')
        loc_ray['t'] >> ray_db['point2']

        loc_dir = mx.create_node(mx.tTransform, parent=loc_drive, name='loc_' + self.name + '_dir' + n_end)
        ray_db['d'] >> loc_dir['ty']
        ray_db['d'] >> loc_dir['tz']

        loc_drift = mx.create_node(mx.tTransform, parent=loc_drive, name='dyn_' + self.name + '_drift' + n_end)
        ray_db['d'] >> loc_drift['ty']

        root_wheel = mx.create_node(mx.tTransform, parent=loc_drift, name='root_' + self.name + n_end)
        c_wheel = mx.create_node(mx.tTransform, parent=root_wheel, name='c_' + self.name + n_end)
        sk_wheel = mx.create_node(mx.tJoint, parent=c_wheel, name='sk_' + self.name + '_center' + n_end)

        loc_motor = mx.create_node(mx.tTransform, parent=c_wheel, name='dyn_' + self.name + '_motor' + n_end)

        c_spin = mx.create_node(mx.tTransform, parent=loc_motor, name='c_spin_' + self.name + n_end)
        sk_spin = mx.create_node(mx.tJoint, parent=c_spin, name='sk_' + self.name + n_end)

        # attributes and expression
        c_wheel_base.add_attr(mx.Double('delta'))
        c_wheel_base.add_attr(mx.Double('direction'))
        c_wheel_base.add_attr(mx.Double('drift'))
        c_wheel_base.add_attr(mx.Double('wheel_ray'))
        c_wheel_base.add_attr(mx.Double('oldX'))
        c_wheel_base.add_attr(mx.Double('oldY'))
        c_wheel_base.add_attr(mx.Double('oldZ'))

        c_wheel_base.add_attr(mx.Long('start_frame', keyable=True, default=1))
        c_wheel_base.add_attr(mx.Double('friction', default=1, min=0, max=1))
        c_wheel_base.add_attr(mx.Double('drift_friction', keyable=True, min=0, max=1))

        c_wheel_base.add_attr(mx.Double('drive_auto', keyable=True, min=0, max=1))
        c_wheel_base.add_attr(mx.Boolean('drive_free', keyable=True))

        c_wheel_base.add_attr(mx.Double('noise', keyable=True, min=0, max=1))
        c_wheel_base.add_attr(mx.Double('noise_freq', keyable=True, default=0.5, min=0, max=1))

        c_wheel_base.add_attr(mx.Double('squash', default=1, min=0, max=1))
        c_wheel_base.add_attr(mx.Double('weight', min=0, max=1))

        c_wheel.add_attr(mx.Double('auto_rotate', keyable=True, default=1, min=0, max=1))

        c_wheel['auto_rotate'] >> c_wheel_base['friction']
        c_wheel_base['friction'].keyable = False

        # expression rig
        _expr = '''// ttWheel expression v2

vector $c = <<{loc_wheel_world}.tx, {loc_wheel_world}.ty, {loc_wheel_world}.tz>>;

if (frame <= {c_wheel_base}.start_frame) {{
  {loc_motor}.rx = 0;
  {loc_drift}.rz = 0;
  {c_wheel_base}.oldX = $c.x;
  {c_wheel_base}.oldY = $c.y;
  {c_wheel_base}.oldZ = $c.z;
  {loc_trail_world}.tx = $c.x;
  {loc_trail_world}.ty = $c.y;
  {loc_trail_world}.tz = $c.z;
}} else {{

vector $old = <<{c_wheel_base}.oldX, {c_wheel_base}.oldY, {c_wheel_base}.oldZ>>;

// drive rotation
{loc_trail_world}.translateX = $c.x;
{loc_trail_world}.translateY = $c.y;
{loc_trail_world}.translateZ = $c.z;

vector $t = <<{loc_trail_local}.tx, {loc_trail_local}.ty, {loc_trail_local}.tz>>;
float $dmag = mag($t);
$t = unit($t);

float $auto = {c_wheel_base}.drive_auto;
float $free = {c_wheel_base}.drive_free;
if($auto < 0.5)
  $free = 0;

int $d = 1;
if (!$free && $t.z > 0) {{
  $d = -1;
  $t = $t * -1;
}}
if ($dmag < 0.0001)
  $d = 0;
{c_wheel_base}.direction = $d;

float $drift = abs(dot($t, <<0, 0, -1>>));
float $drift_side = 1;
if ($t.x>0) $drift_side = -1;

$t = $auto * $t + (1 - $auto) * <<0, 0, -1>>;
$drift = (1 - $auto) * $drift + $auto;

{loc_trail}.tx = $t.x;
{loc_trail}.ty = $t.y;
{loc_trail}.tz = $t.z;


// motor rotation
float $delta = mag($c - $old);
float $ray = mag(<<{loc_ray_world}.tx, {loc_ray_world}.ty, {loc_ray_world}.tz>>);
float $friction = {c_wheel_base}.friction;

float $rotw = $delta / (2 * 3.141592 * $ray) * 360 * $drift * $friction * $d * (1 - 0.4 * {c_wheel_base}.weight);
{loc_motor}.rx += $rotw;

float $dp = {c_wheel_base}.drift_friction;
float $drift_friction = (1 - $drift) * $delta / $ray * $drift_side * $dp * -10;
{loc_drift}.rz = $drift_friction;

float $freq = {c_wheel_base}.noise_freq;
if ($freq == 0)
  $freq = 100;
else
  $freq = 1 / $freq * 5;
float $noise = {c_wheel_base}.noise * noise({loc_motor}.rx / $freq) * 10;
{loc_drift}.ry = $noise;


// frame, infos
{c_wheel_base}.wheel_ray = $ray;
{c_wheel_base}.delta = $delta;
{c_wheel_base}.drift = 1 - $drift;

{c_wheel_base}.oldX = $c.x;
{c_wheel_base}.oldY = $c.y;
{c_wheel_base}.oldZ = $c.z;
}}'''

        mc.select(clear=True)
        _time = mc.currentTime(q=1)
        mc.currentTime(0)

        expr = _expr.format(**locals())
        mc.expression(s=expr)
        mc.currentTime(_time)

        # registering
        self.set_id(root_wheel_base, 'roots.bank')
        self.set_id(root_wheel, 'roots.wheel')

        self.set_id(c_wheel_base, 'ctrls.bank')
        self.set_id(c_wheel, 'ctrls.wheel')
        self.set_id(c_spin, 'ctrls.spin')

        self.set_id(sk_wheel, 'skin.wheel')
        self.set_id(sk_spin, 'skin.spin')
