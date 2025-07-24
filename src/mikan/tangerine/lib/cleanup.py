# coding: utf-8

import meta_nodal_py as kl
from meta_nodal_py.Imath import V3f
from tang_core.document.get_document import get_document
from tang_core.anim import is_exportable, set_exportable
from ast import literal_eval

from ..core.node import Nodes
from ..lib.commands import *

from mikan.core.logger import log

__all__ = ['cleanup_rig_ctrls', 'cleanup_rig_shapes', 'cleanup_linear_anim_curves']


# rig ------------------------------------------------------------------------------------------------------------------


def cleanup_rig_shapes(root=None):
    pass


def cleanup_rig_ctrls():
    ctrls = Nodes.get_id('*::ctrls')
    if not ctrls:
        return
    ctrls = list(dict.fromkeys(ctrls))

    # 'show' attributes should not be keyable but exportable (hence visible)
    for ctrl in ctrls:
        set_plug(ctrl.show, nice_name='Show', keyable=False, exportable=True)

    # matrix rig connection on ctrl (tx, ty, tz, etc)
    def add_dynamic_plug(c, attr, v):
        if hasattr(ctrl, attr):
            raise ValueError("dynamic plug " + attr + " already exists in " + c.get_name())
        return c.add_dynamic_plug(attr, v)

    def connect_new_dynamic_plug_if_not_connected(f, c, attr, check_exportable_and_bind_pose=True):
        if not f.is_connected():
            user_info = f.get_all_user_infos()
            if 'locked' in user_info:
                return
            p = add_dynamic_plug(c, attr, f.get_value())
            if check_exportable_and_bind_pose:
                if 'exp' not in user_info:
                    log.error(f.get_full_name() + " is not exportable")
                if 'bind_pose' not in user_info:
                    log.error(f.get_full_name() + " has no bind_pose")
            p.set_all_user_infos(user_info)
            f.set_all_user_infos({})
            f.connect(p)
            return p
        else:
            log.error(f.get_full_name() + ' is already connected')

    for ctrl in ctrls:

        # check SRT rig
        if ctrl.transform.is_connected():
            srt = ctrl.transform.get_input().get_node()
            while True:
                if isinstance(srt, kl.SRTToTransformNode):
                    # translate
                    if srt.translate.is_connected():
                        f2v_t = srt.translate.get_input().get_node()
                        if isinstance(f2v_t, kl.FloatToV3f):
                            connect_new_dynamic_plug_if_not_connected(f2v_t.x, ctrl, 'tx')
                            connect_new_dynamic_plug_if_not_connected(f2v_t.y, ctrl, 'ty')
                            connect_new_dynamic_plug_if_not_connected(f2v_t.z, ctrl, 'tz')
                        else:
                            log.error(ctrl.get_name() + ' translate is not commonly rigged')
                    else:
                        log.error(ctrl.get_name() + ' translate is not connected')
                    # scale
                    if srt.scale.is_connected():
                        f2v_s = srt.scale.get_input().get_node()
                        if isinstance(f2v_s, kl.FloatToV3f):
                            connect_new_dynamic_plug_if_not_connected(f2v_s.x, ctrl, 'sx')
                            connect_new_dynamic_plug_if_not_connected(f2v_s.y, ctrl, 'sy')
                            connect_new_dynamic_plug_if_not_connected(f2v_s.z, ctrl, 'sz')
                        else:
                            log.error(ctrl.get_name() + ' scale is not commonly rigged')
                    else:
                        log.error(ctrl.get_name() + ' scale is not connected')
                    # rotate
                    if srt.rotate.is_connected():
                        f2e = srt.rotate.get_input().get_node()
                        if isinstance(f2e, kl.FloatToEuler):
                            connect_new_dynamic_plug_if_not_connected(f2e.x, ctrl, 'rx')
                            connect_new_dynamic_plug_if_not_connected(f2e.y, ctrl, 'ry')
                            connect_new_dynamic_plug_if_not_connected(f2e.z, ctrl, 'rz')
                        else:
                            log.error(ctrl.get_name() + ' rotate is not commonly rigged')
                    else:
                        log.error(ctrl.get_name() + ' rotate is not connected')
                    # rotate order
                    connect_new_dynamic_plug_if_not_connected(srt.rotate_order, ctrl, 'ro', check_exportable_and_bind_pose=False)

                    # joint orient
                    if isinstance(srt, kl.SRTToJointTransform):
                        # joint orient rotate
                        if srt.joint_orient_rotate.is_connected():
                            f2e = srt.joint_orient_rotate.get_input().get_node()
                            if isinstance(f2e, kl.FloatToEuler):
                                connect_new_dynamic_plug_if_not_connected(f2e.x, ctrl, 'jx', check_exportable_and_bind_pose=False)
                                connect_new_dynamic_plug_if_not_connected(f2e.y, ctrl, 'jy', check_exportable_and_bind_pose=False)
                                connect_new_dynamic_plug_if_not_connected(f2e.z, ctrl, 'jz', check_exportable_and_bind_pose=False)
                            else:
                                log.error(ctrl.get_name() + ' joint orient rotate is not commonly rigged')
                        else:
                            log.error(ctrl.get_name() + ' joint orient rotate is not connected')
                        # joint orient rotate order
                        connect_new_dynamic_plug_if_not_connected(srt.joint_orient_rotate_order, ctrl, 'jo', check_exportable_and_bind_pose=False)

                elif isinstance(srt, kl.BlendTransformsNode):
                    srt = srt.transform1_in.get_input().get_node()
                    continue
                else:
                    log.error(ctrl.get_name() + '.transform is not commonly rigged')
                break

        # check plugs
        for plug in ctrl.get_dynamic_plugs():
            _input = plug.get_input()
            if _input:
                # check invalid proxy
                desc = _input.get_all_user_infos()
                if not desc.get('exp'):
                    continue

                if _input.get_node() not in ctrls:
                    log.warning(f'/!\\ removed invalid proxy plug {_input.get_node().get_name()}.{_input.get_name()}')
                    desc.pop('exp', None)
                    desc.pop('keyable', None)
                    _input.set_all_user_infos(desc)

                # check exportable connection
                if is_exportable(plug):
                    set_exportable(plug, False)

        # move temporal_cache_override infos and tag to upper controller
        from mikan.tangerine.lib.dynamic import set_plug_temporal_cache_override_value, \
            unset_plug_temporal_cache_override_value, get_plug_temporal_cache_override_value_if_any
        doc = get_document()
        temporal_cache_override_nodes = [node for node in doc._tagger.nodes_from_tag("temporal_cache_override")]
        for controller in temporal_cache_override_nodes:
            for plug in controller.get_dynamic_plugs():
                value = get_plug_temporal_cache_override_value_if_any(plug)
                if value:
                    if plug.is_connected():
                        input_plug = plug.get_plug_input()  # recurse get_input calls
                        if input_plug.is_eval():
                            node = input_plug.get_node()
                            input_plug = node.converted_input
                            value = input_plug.get_type()(literal_eval(value))
                            if input_plug.is_connected():
                                input_plug = input_plug.get_plug_input()  # recurse get_input calls
                        if is_exportable(input_plug) and \
                                get_plug_temporal_cache_override_value_if_any(input_plug) is None:
                            set_plug_temporal_cache_override_value(doc, input_plug, value)
                        unset_plug_temporal_cache_override_value(doc, plug)

        # inverse gizmo
        w = ctrl.world_transform.get_value()
        p = ctrl.parent_world_transform.get_value()

        ti = V3f(*[p.get(0, i) for i in range(3)])
        tj = V3f(*[p.get(1, i) for i in range(3)])
        tk = V3f(*[p.get(2, i) for i in range(3)])
        ri = V3f(*[w.get(0, i) for i in range(3)])
        rj = V3f(*[w.get(1, i) for i in range(3)])
        rk = V3f(*[w.get(2, i) for i in range(3)])

        det0 = 1 if ti.cross(tj).dot(tk) > 0 else -1  # det
        det1 = 1 if ri.cross(rj).dot(rk) > 0 else -1  # det

        if det0 * det1 < 0:
            log.debug(f'inversed gizmo for: {ctrl}')

            for plug_name in ('tx', 'ty', 'tz'):
                plug = ctrl.get_dynamic_plug(plug_name)
                desc = plug.get_all_user_infos()
                desc["axis_inv"] = "yes"
                plug.set_all_user_infos(desc)

        # SplineCurve optim to share topology among all spline meshes:
        for iterator in doc.root().node_iterator():
            node = iterator.node
            if isinstance(node, kl.SplineCurve):
                if node.legacy.get_stored_value() < 2:
                    node.legacy.set_value(2)
                    p = node.spline_in
                    while True:
                        s = p.get_stored_value()
                        if s is not None:
                            node.wrap_in.set_value(s.get_wrap())
                            break
                        if p.is_connected():
                            p = p.get_plug_input()
                            continue
                        n = p.get_node()
                        if isinstance(n, kl.Deformer):
                            p = n.spline_in
                            continue
                        if isinstance(n, kl.SplineCurveReader):
                            node.wrap_in.connect(n.wrap_out)
                            break
                        raise NotImplementedError


def get_linear_anim_curves(filter=None, check_infinity=True):
    linear_anim_curves = []

    anim_curves = []
    doc = get_document()
    for iterator in doc.root().node_iterator():
        node = iterator.node
        if isinstance(node, kl.DrivenFloat):
            anim_curves.append(node)

    for anm in anim_curves:
        if filter and not anm.is_a(filter):
            continue

        if check_infinity:
            if anm.post_cycle.get_value() != kl.Cycle.linear:
                continue
            if anm.pre_cycle.get_value() != kl.Cycle.linear:
                continue

        # get number of keyframes on curve
        curve = anm.curve.get_value()
        n_keys = curve.key_count()
        if n_keys <= 1:
            continue

        values = []
        tangents = set()
        for k, kf in curve.get_keys_map().items():
            values.append(k)
            values.append(kf.v)
            tangents.add(kf.left_tangent_mode)
            tangents.add(kf.right_tangent_mode)

        # compute linear equation (y=ax+b) a and b
        x0 = values[0]
        y0 = values[1]
        x1 = values[2]
        y1 = values[3]

        if y1 == y0:
            a = 0
        else:
            a = (y1 - y0) / (x1 - x0)
        b = y0 - a * x0

        # check linearity along other steps
        x0 = x1
        y0 = y1
        linear = True
        for k in range(4, len(values), 2):
            x1 = values[k]
            y1 = values[k + 1]

            if y1 == y0:
                ap = 0
            else:
                ap = (y1 - y0) / (x1 - x0)
            bp = y0 - ap * x0
            if ap != a or bp != b:
                linear = False
                break
            # next step
            x0 = x1
            y0 = y1

        if not linear:
            continue

        # check tangents
        if set(tangents).difference({kl.TangentMode.spline}):
            continue

        # store the linear animCurve with its (a, b) parameters
        linear_anim_curves.append((anm, a, b))

    return linear_anim_curves


def cleanup_linear_anim_curves():
    n = 0

    for curve, a, b in get_linear_anim_curves():
        # only use linear equation with b=0
        if b != 0:
            continue

        plug_out = curve.driver.get_input()
        plug_ins = curve.result.get_outputs()
        if plug_out is None or not plug_ins:
            continue

        # replace node
        mult = kl.Mult(curve.get_parent(), '_linear')
        mult.input2.set_value(a)

        # disconnect animCurve
        for plug_in in plug_ins:
            plug_in.connect(mult.output)
        mult.input1.connect(plug_out)

        # remove the resulting unused animCurve
        curve.remove_from_parent()
        n += 1

    log.debug('optimized {} linear anim curves'.format(n))
