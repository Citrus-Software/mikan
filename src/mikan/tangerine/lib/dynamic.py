from tang_core.set_transform_value import set_transform_value_on_controller
from tang_core.anim import is_anim_node
from tang_core.callbacks import Callbacks
from meta_nodal_py import Condition, IsGreater

from mikan.tangerine import Group, Asset
from ast import literal_eval


def is_dynamic_controller(node):
    if node.get_dynamic_plug('dyn_node'):
        return True
    return False


def is_baked_dynamic_controller(node):
    if node.get_dynamic_plug('dyn_baked') and node.dyn_baked.get_value():
        return True
    return False


def filter_dynamic_controllers(nodes):
    return [n for n in nodes if is_dynamic_controller(n)]


def filter_baked_dynamic_controllers(nodes):
    return [n for n in nodes if is_baked_dynamic_controller(n)]


def bake_dynamic_controllers(dynamic_controllers, document):
    if not document.temporal_cache:
        document.broadcast('[error] Cannot Bake Dynamics if temporal cache is not enabled')
        return

    document.synch_compute_all_frames()  # force engine to finish compute if needed for optim

    # do get value before create modifier
    start = document.start_frame
    end = document.end_frame
    baked_transforms = {}

    for dyn_ctrl in dynamic_controllers:
        parent = dyn_ctrl.get_parent()
        dyn = dyn_ctrl.dyn_node.get_input().get_node()
        try:
            # True if we rely on cache computed above
            fast_dyn = not dyn.world_transform.is_eval_dirty(end)
            fast_parent = not parent.world_transform.is_eval_dirty(end)
        except AttributeError:  # tang too old: is_eval_dirty not bound yet
            # do not rely on cache for get_value below
            fast_dyn = False
            fast_parent = False
        xfo = [dyn.world_transform.get_value(frame, fast=fast_dyn) *
               parent.world_transform.get_value(frame, fast=fast_parent).inverse()
               for frame in range(start, end + 1)]
        baked_transforms[dyn_ctrl] = xfo

    with document.modify("Bake Dynamic Controllers") as modifier:
        for dyn_ctrl, transforms in baked_transforms.items():
            modifier.set_plug_value(dyn_ctrl.dyn_baked, True)
            for frame in range(start, end + 1):
                # FIXME: it always use Base anim below
                set_transform_value_on_controller(dyn_ctrl, transforms[frame - start], modifier, frame, force_key=True)


def restore_dynamic_controllers(baked_dynamic_controllers, document):
    with document.modify("Restore Dynamic Controllers") as modifier:
        for dyn_ctrl in baked_dynamic_controllers:
            # FIXME: it always use Base anim below
            for axe in ('tx', 'ty', 'tz', 'rx', 'ry', 'rz', 'sx', 'sy', 'sz', 'hx', 'hy', 'hz'):
                plug = getattr(dyn_ctrl, axe, None)
                if plug is None:
                    continue
                if plug.is_connected():
                    anim = plug.get_input().get_node()
                    if not is_anim_node(anim):
                        continue  # FIXME: controller is in a layer, it cannot be restored
                    modifier.delete_node(anim)
                    del anim  # actually delete the anim node
                bind_pose = plug.get_user_info('bind_pose')
                modifier.set_plug_value(plug, literal_eval(bind_pose) if bind_pose != "" else 0)

            modifier.set_plug_value(dyn_ctrl.dyn_baked, False)


# helper for pipeline
def bake_assets_dynamic_controllers(asset_nodes, document):
    dynamic_controllers = []
    for asset in asset_nodes:
        try:
            grp_all_node = asset.gem_group.get_input().get_node()
        except AttributeError:
            continue  # not an asset node
        grp_all_group = Group(grp_all_node)
        for ctrl in grp_all_group.get_all_nodes():
            if is_dynamic_controller(ctrl):
                dynamic_controllers.append(ctrl)

    bake_dynamic_controllers(dynamic_controllers, document)


def get_plug_temporal_cache_override_value_if_any(plug):
    desc = plug.get_all_user_infos()
    if 'temporal_cache_override_value' in desc:
        return desc['temporal_cache_override_value']
    return None


def set_plug_temporal_cache_override_value(document, plug, value):
    temp_cache_tag = document.tagger.create_tag("temporal_cache_override", show_in_gui=False)
    document.tagger.tag_node(temp_cache_tag, plug.get_node())
    plug.set_user_info("temporal_cache_override_value", str(value))


def unset_plug_temporal_cache_override_value(document, plug):
    plug.remove_user_info("temporal_cache_override_value")
    for p in plug.get_node().get_dynamic_plugs():
        if p.get_user_info("temporal_cache_override_value"):
            return
    document.tagger.untag_node("temporal_cache_override", plug.get_node())


def after_load_asset(document, asset_node):
    # new version:
    # - rely on plug user_info existence "temporal_cache_override_value" = "False"
    # - user feedback in view Channels
    # - support wheels, jiggle, and any future temporal template

    rig_has_changed = False

    for controller in document.tagger.nodes_from_tag("temporal_cache_override"):
        if Callbacks().get_asset_node(document, controller) != asset_node:
            continue
        for plug in controller.get_dynamic_plugs():
            value = plug.get_user_info('temporal_cache_override_value')
            if value:
                outputs = plug.get_outputs()
                v = literal_eval(value)
                temporal_cache_override = Condition(controller, 'temporal_cache_override')
                temporal_cache_override.condition.connect(asset_node.temporal_cache)
                if v.__class__ is bool:
                    temporal_cache_cast_in = Condition(controller, 'temporal_cache_cast_in')
                    temporal_cache_cast_in.condition.connect(plug)
                    temporal_cache_cast_in.input1.set_value(1.0)
                    temporal_cache_cast_in.input2.set_value(0.0)
                    plug = temporal_cache_cast_in.output
                    v = float(v)
                    temporal_cache_cast_out = IsGreater(controller, 'temporal_cache_cast_out')
                    temporal_cache_cast_out.input1.connect(temporal_cache_override.output)
                    temporal_cache_cast_out.input2.set_value(0.0)
                    temporal_cache_override_output = temporal_cache_cast_out.output
                else:
                    temporal_cache_override_output = temporal_cache_override.output
                if v.__class__ is not float:
                    raise ValueError("temporal_cache_override_value should be bool or float")
                temporal_cache_override.input1.connect(plug)
                temporal_cache_override.input2.set_value(v)
                for output in outputs:
                    output.disconnect(restore_default=True)
                    output.connect(temporal_cache_override_output)
                rig_has_changed = True

    # old version:
    # - rely on "dynamics" tag and aim_constrain rig (jiggle template)
    # - no user feedback in view Channels
    # - wheel template unsupported (jiggle only)
    for aim_constrain in document._tagger.nodes_from_tag("dynamics"):
        if Callbacks().get_asset_node(document, aim_constrain) != asset_node:
            continue
        enable_in = aim_constrain.enable_in
        enable_in_input = enable_in.get_input()
        enable_in_input.disconnect(restore_default=True)
        temporal_cache_override = Condition(aim_constrain, 'temporal_cache_override')
        temporal_cache_override.condition.connect(asset_node.temporal_cache)
        temporal_cache_override.input1.connect(enable_in_input)
        temporal_cache_override.input2.set_value(False)
        enable_in.connect(temporal_cache_override.output)
        rig_has_changed = True

    return rig_has_changed
