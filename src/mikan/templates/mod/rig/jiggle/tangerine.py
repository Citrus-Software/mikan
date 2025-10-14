# coding: utf-8

import meta_nodal_py as kl
from tang_core.document.get_document import get_document

import mikan.tangerine.core as mk
from mikan.tangerine.lib.commands import add_plug
from mikan.tangerine.lib.rig import aim_constraint
from mikan.tangerine.lib.connect import connect_expr
from mikan.tangerine.lib.dynamic import set_plug_temporal_cache_override_value
from mikan.core import cleanup_str, create_logger

log = create_logger()


class Mod(mk.Mod):

    def run(self):

        # args
        rig = mk.Nodes.get_id('::rig')
        if not rig:
            raise mk.ModArgumentError('cannot build dynamic without world')

        if mk.Nodes.get_id('::jiggle') is None:
            dyn = kl.SceneGraphNode(rig, 'jiggle')
            mk.Nodes.set_id(dyn, '::jiggle')
        else:
            dyn = mk.Nodes.get_id('::jiggle')

        ctrl = self.data.get('ctrl')
        if not ctrl:
            raise mk.ModArgumentError('no controller defined')

        ctrl_main = self.data.get('ctrl_main', ctrl)
        ctrl_dyn = self.data.get('ctrl_dyn', ctrl)

        driven_node = self.data.get('dyn')
        if not driven_node:
            raise mk.ModArgumentError('no driven node defined')

        target = self.data.get('target')
        if not target:
            raise mk.ModArgumentError('no target defined')

        # # bake ctrl
        # bake = kl.SceneGraphNode(ctrl.get_parent(), ctrl.get_name() + '_bake')
        # add_plug(bake, 'gem_id', str)
        # for gem_id in ctrl.gem_id.get_value().split(';'):
        #     if 'ctrls.' in gem_id:
        #         mk.Nodes.set_id(bake, gem_id.replace('ctrls.', 'ctrls.dyn.'))

        # base name
        name = self.data.get('name')
        sfx = self.get_template_id()
        if '.' in sfx:
            sfx = '_' + '_'.join(sfx.split('.')[1:])
        else:
            sfx = ''
        if not name:
            name = ctrl.get_name()
        name += sfx
        name = cleanup_str(name)

        # world
        world = dyn
        if 'world' in self.data:
            world = self.data('world')

        # particle
        target_node = kl.SceneGraphNode(ctrl, 'dyn_target')
        wt = target.world_transform.get_value()
        target_node.set_world_transform(wt)

        body = kl.Body(dyn, 'body_' + name)
        # body.initial_transform_in.set_value(body.get_transform_for_world_transform(wt))

        imx = kl.InverseM44f(body, '_imx')
        imx.input.connect(world.world_transform)

        mmx_parent = kl.MultM44f(body, "_mmx_parent")
        mmx_parent.input[0].connect(dyn.world_transform)
        mmx_parent.input[1].connect(imx.output)
        parent_world_transform = mmx_parent.output

        mmx_target = kl.MultM44f(body, '_mmx_target')
        mmx_target.input[0].connect(target_node.world_transform)
        mmx_target.input[1].connect(imx.output)
        target_world_transform = mmx_target.output

        mmx_body = kl.MultM44f(body, '_mmx_body')
        mmx_body.input[0].connect(body.transform)
        mmx_body.input[1].connect(parent_world_transform)
        world_transform = mmx_body.output

        body.parent_world_transform_in.connect(parent_world_transform)
        body.previous_world_transform.connect_delta(world_transform, -1, body.initial_world_transform_in)
        body.target_in.connect(target_world_transform)
        body.initial_transform_in.connect(target_world_transform)

        # params
        weight = self.data.get('weight', 1)
        start_frame = self.data.get('start_frame', 1)
        goal = self.data.get('goal', 0.5)
        damp = self.data.get('damp', 0.5)

        if not ctrl_main.get_dynamic_plug('dynamic'):
            add_plug(ctrl_main, 'dynamic', bool, k=1, min_value=0, max_value=1)
        if not ctrl_main.get_dynamic_plug('weight'):
            add_plug(ctrl_main, 'weight', float, k=1, default_value=weight, min_value=0, max_value=1)
        if not ctrl_main.get_dynamic_plug('start_frame'):
            add_plug(ctrl_main, 'start_frame', int, k=0, default_value=start_frame)

        if not ctrl_dyn.get_dynamic_plug('goal'):
            add_plug(ctrl_dyn, 'goal', float, k=1, default_value=goal, min_value=0, max_value=1)
        if not ctrl_dyn.get_dynamic_plug('damp'):
            add_plug(ctrl_dyn, 'damp', float, k=1, default_value=damp, min_value=0, max_value=1)

        if not ctrl.get_dynamic_plug('dyn_baked'):
            add_plug(ctrl, 'dyn_baked', bool, exportable=True, keyable=False, lock=True)

        body.stiff_in.connect(ctrl_dyn.goal)
        body.damp_in.connect(ctrl_dyn.damp)

        _wm = body.world_transform.get_value()
        _wim = driven_node.world_transform.get_value().inverse()
        _aim = (_wm * _wim).translation().normalized()

        _ac = aim_constraint(
            body, driven_node,
            maintain_offset=True,
            aim_vector=_aim,
            up_vector=[0, 0, 0],
        )

        connect_expr(
            'c = dyn*(1-baked)*w',
            c=_ac.enable_in,
            dyn=ctrl_main.dynamic,
            baked=ctrl.dyn_baked,
            w=ctrl_main.weight
        )

        # register
        if not ctrl.get_dynamic_plug('dyn_node'):
            add_plug(ctrl, 'dyn_node', str)
        ctrl.dyn_node.connect(driven_node.gem_id)

        # for callback after_load_asset
        set_plug_temporal_cache_override_value(get_document(), ctrl_main.dynamic, 0.0
        if ctrl_main.dynamic.get_type() is float else False)
