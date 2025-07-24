# coding: utf-8

import math

from mikan.core.prefs import Prefs
import meta_nodal_py as kl
from meta_nodal_py.Imath import V3f, M44f, Euler

from .commands import *
from .connect import *
from .nurbs import get_closest_point_on_curve
from mikan.core.logger import create_logger

log = create_logger()

__all__ = [
    'create_srt_in', 'create_srt_out', 'find_srt',
    'point_constraint', 'parent_constraint', 'orient_constraint', 'twist_constraint',
    'aim_constraint', 'scale_constraint', 'merge_transform', 'matrix_constraint', 'find_target', 'find_closest_node',
    'str_to_rotate_order', 'axis_to_vector', 'get_stretch_axis',
    'duplicate_joint', 'mirror_joints', 'orient_joint', 'create_blend_joint', 'create_joints_on_curve',
    'create_ik_handle', 'reparent_ik_handle', 'stretch_IK', 'stretch_spline_IK',
    'create_extract_vector_from_transform', 'create_angle_between',
    'compare_transform',
    'set_virtual_parent',
]


def _flatten(l):
    for el in l:
        if type(el) in (tuple, list) and not isinstance(el, str):
            for sub in _flatten(el):
                yield sub
        else:
            yield el


# transform ------------------------------------------------------------------------------------------------------------

def create_srt_in(node, ro=Euler.XYZ, vectors=True, keyable=None, k=None, jo_ro=Euler.XYZ):
    # args
    if k is not None:
        keyable = k

    kl_node = kl.SRTToTransformNode
    jo = False

    if isinstance(node, kl.Joint):
        kl_node = kl.SRTToJointTransform
        jo = True

    # srt
    srt = None

    plug = node.transform.get_input()
    if plug:
        plug_node = plug.get_node()
        if isinstance(plug_node, kl_node):
            srt = plug_node
            ro = srt.rotate_order.get_value()
        else:
            # TODO: préparer une exception
            # raise RuntimeError('already connected')
            pass

    xfo = node.transform.get_value()
    t = xfo.translation()
    r = xfo.rotation(ro)
    s = xfo.scaling()
    sh = xfo.shearing()

    if not srt:
        srt = kl_node(node, 'transform')
        srt.translate.set_value(t)
        if jo:
            srt.rotate_order.set_value(ro)
            srt.joint_orient_rotate_order.set_value(jo_ro)
            srt.joint_orient_rotate.set_value(r)
        else:
            srt.rotate_order.set_value(ro)
            srt.rotate.set_value(r)
        srt.scale.set_value(s)
        node.transform.connect(srt.transform)

    # set_plug(srt.rotate_order, k=0)

    if vectors:
        vt = srt.translate.get_input()
        if not vt:
            vt = kl.FloatToV3f(srt, 'translate')
            vt.x.set_value(t.x)
            vt.y.set_value(t.y)
            vt.z.set_value(t.z)
            set_plug(vt.x, nice_name='Translate X')
            set_plug(vt.y, nice_name='Translate Y')
            set_plug(vt.z, nice_name='Translate Z')
            srt.translate.connect(vt.vector)
        else:
            vt = vt.get_node()
        if keyable:
            set_plug(vt.x, k=1)
            set_plug(vt.y, k=1)
            set_plug(vt.z, k=1)

        vr = srt.rotate.get_input()
        if not vr:
            vr = kl.FloatToEuler(srt, 'rotate')
            if not jo:
                vr.x.set_value(r.x)
                vr.y.set_value(r.y)
                vr.z.set_value(r.z)
            vr.rotate_order.connect(srt.rotate_order)
            set_plug(vr.x, nice_name='Rotate X')
            set_plug(vr.y, nice_name='Rotate Y')
            set_plug(vr.z, nice_name='Rotate Z')
            srt.rotate.connect(vr.euler)
        else:
            vr = vr.get_node()
        if keyable:
            set_plug(vr.x, k=1)
            set_plug(vr.y, k=1)
            set_plug(vr.z, k=1)

        if jo:
            vj = srt.joint_orient_rotate.get_input()
            if not vj:
                vj = kl.FloatToEuler(srt, 'joint_orient_rotate')
                jo_xfo = M44f(V3f(0, 0, 0), r, V3f(1, 1, 1), ro)
                jo = jo_xfo.rotation(jo_ro)
                vj.x.set_value(jo.x)
                vj.y.set_value(jo.y)
                vj.z.set_value(jo.z)
                vj.rotate_order.connect(srt.joint_orient_rotate_order)
                set_plug(vj.x, nice_name='Joint Orient X')
                set_plug(vj.y, nice_name='Joint Orient Y')
                set_plug(vj.z, nice_name='Joint Orient Z')
                srt.joint_orient_rotate.connect(vj.euler)
            else:
                vj = vj.get_node()
            set_plug(vj.x, k=0)
            set_plug(vj.y, k=0)
            set_plug(vj.z, k=0)

        vs = srt.scale.get_input()
        if not vs:
            vs = kl.FloatToV3f(srt, 'scale')
            vs.x.set_value(s.x)
            vs.y.set_value(s.y)
            vs.z.set_value(s.z)
            set_plug(vs.x, nice_name='Scale X')
            set_plug(vs.y, nice_name='Scale Y')
            set_plug(vs.z, nice_name='Scale Z')
            srt.scale.connect(vs.vector)
        else:
            vs = vs.get_node()
        if keyable:
            set_plug(vs.x, k=1)
            set_plug(vs.y, k=1)
            set_plug(vs.z, k=1)

        vsh = srt.shear.get_input()
        if not vsh:
            vsh = kl.FloatToV3f(srt, 'shear')
            vsh.x.set_value(sh.x)
            vsh.y.set_value(sh.y)
            vsh.z.set_value(sh.z)
            set_plug(vsh.x, nice_name='Shear X')
            set_plug(vsh.y, nice_name='Shear Y')
            set_plug(vsh.z, nice_name='Shear Z')
            srt.shear.connect(vsh.vector)
        else:
            vsh = vsh.get_node()
        if keyable:
            set_plug(vsh.x, k=1)
            set_plug(vsh.y, k=1)
            set_plug(vsh.z, k=1)

    return srt


def create_srt_out(node, ro=Euler.XYZ, jo_ro=Euler.XYZ, vectors=True, joint_orient=False):
    # args
    kl_node = kl.TransformToSRTNode
    jo = False
    if joint_orient:
        kl_node = kl.JointTransformToSRT
        jo = True

    # srt
    srt = None

    if kl.is_plug(node):
        plug_out = node
        node = plug_out.get_node()
    else:
        plug_out = None
        if isinstance(node, kl.SceneGraphNode):
            plug_out = node.transform
        elif isinstance(node, kl.Constrain):
            plug_out = node.constrain_transform
        elif type(node) in (kl.BlendTransformsNode, kl.BlendWeightedTransforms, kl.PointOnSplineCurve):
            plug_out = node.transform_out
        elif type(node) in (kl.MultM44f, kl.InverseM44f):
            plug_out = node.output

        if not plug_out:
            raise RuntimeError('node not yet implemented, request assistance')

    for child in node.get_children():
        if isinstance(child, kl_node):
            plug = child.transform.get_input()
            if plug and plug.get_node() == node:
                srt = child
                break

    if not srt:
        srt = kl_node(node, 'srt')
        srt.transform.connect(plug_out)

    srt.rotate_order.set_value(ro)
    if jo:
        srt.joint_orient_rotate_order.set_value(jo_ro)
        r = plug_out.get_value().rotation(jo_ro)
        srt.joint_orient.set_value(r)

    if vectors:
        vt = srt.find('translate')
        if not vt:
            vt = kl.V3fToFloat(srt, 'translate')
            vt.vector.connect(srt.translate)

        vr = srt.find('rotate')
        if not vr:
            vr = kl.EulerToFloat(srt, 'rotate')
            vr.euler.connect(srt.rotate)
            vr.rotate_order.connect(srt.rotate_order)

        if jo:
            vj = srt.find('joint_orient')
            if not vj:
                vj = kl.FloatToEuler(srt, 'joint_orient')
                vj.rotate_order.connect(srt.joint_orient_rotate_order)
                vj.x.set_value(r.x)
                vj.y.set_value(r.y)
                vj.z.set_value(r.z)
                srt.joint_orient.connect(vj.euler)

        vs = srt.find('scale')
        if not vs:
            vs = kl.V3fToFloat(srt, 'scale')
            vs.vector.connect(srt.scale)

        vsh = srt.find('shear')
        if not vsh:
            vsh = kl.V3fToFloat(srt, 'shear')
            vsh.vector.connect(srt.shear)

    return srt


def find_srt(node, ro=Euler.XYZ, vectors=True):
    if node.transform.is_connected():
        plug_in = node.transform.get_input().get_node()
        if type(plug_in) in (kl.SRTToJointTransform, kl.SRTToTransformNode):
            if plug_in.get_name() == 'transform':
                return create_srt_in(node, vectors=vectors, ro=ro)

        elif type(plug_in) is kl.BlendTransformsNode:
            if plug_in.transform1_in.is_connected():
                _plug_in = plug_in.transform1_in.get_input().get_node()
                if type(_plug_in) in (kl.SRTToJointTransform, kl.SRTToTransformNode):
                    return _plug_in
            elif plug_in.transform2_in.is_connected():
                _plug_in = plug_in.transform2_in.get_input().get_node()
                if type(_plug_in) in (kl.SRTToJointTransform, kl.SRTToTransformNode):
                    return _plug_in

    for plug_out in node.transform.get_outputs():
        plug_out_node = plug_out.get_node()
        if isinstance(plug_out_node, (kl.JointTransformToSRT, kl.TransformToSRTNode)):
            return create_srt_out(node, vectors=vectors)

    return create_srt_out(node, vectors=vectors, ro=ro)


# constraints ----------------------------------------------------------------------------------------------------------

def _get_input_constraint(plug_in, constraints=None):
    if constraints is None:
        constraints = []

    plug = plug_in.get_input()
    if plug:
        node = plug.get_node()

        if type(node) in (kl.SRTToJointTransform, kl.SRTToTransformNode):
            constraints = _get_input_constraint(node.translate, constraints)
            constraints = _get_input_constraint(node.rotate, constraints)
            constraints = _get_input_constraint(node.scale, constraints)

        elif isinstance(node, kl.TransformToSRTNode):
            constraints = _get_input_constraint(node.transform, constraints)

        elif isinstance(node, kl.BlendWeightedTransforms):
            for i in range(node.transform_in.get_size()):
                plug_in = node.transform_in[i]
                constraints = _get_input_constraint(plug_in, constraints)

        elif isinstance(node, kl.BlendTransformsNode):
            constraints = _get_input_constraint(node.transform1_in, constraints)
            constraints = _get_input_constraint(node.transform2_in, constraints)

        elif type(node) in (kl.FloatToEuler, kl.FloatToV3f):
            constraints = _get_input_constraint(node.x, constraints)
            constraints = _get_input_constraint(node.y, constraints)
            constraints = _get_input_constraint(node.z, constraints)
        elif isinstance(node, kl.V3fToFloat):
            constraints = _get_input_constraint(node.vector, constraints)
        elif isinstance(node, kl.EulerToFloat):
            constraints = _get_input_constraint(node.euler, constraints)

        elif isinstance(node, kl.Constrain):
            if node not in constraints:
                constraints.append(node)

    return constraints


def merge_transform(node,
                    t_in=None, r_in=None, s_in=None, sh_in=None,
                    t_axes='xyz', r_axes='xyz', s_axes='xyz',
                    constraints=None, force_blend=False, override=False, is_joint=None):
    """Merge given SRT plug of any type to current node transform."""

    # args
    if is_joint is None:
        is_joint = isinstance(node, kl.Joint)

    # find srt
    plug_in = node.transform.get_input()
    if not plug_in:
        # create new SRT
        srt = create_srt_in(node, vectors=False)
    elif type(plug_in.get_node()) in (kl.SRTToTransformNode, kl.SRTToJointTransform):
        srt = plug_in.get_node()
    else:
        # create new SRT
        srt = create_srt_in(node, vectors=False)
        # reconnect former connexion to srt
        node.transform.connect(srt.transform)
        plug_node = plug_in.get_node()
        # translation
        if type(plug_node) not in (kl.OrientConstrain, kl.TwistConstrain, kl.AimConstrain, kl.ScaleConstrain):
            _xfo = plug_node.find('srt')
            if not _xfo:
                _xfo = create_srt_out(plug_in, joint_orient=is_joint)
            srt.translate.connect(_xfo.translate)
        # rotation
        if type(plug_node) not in (kl.PointConstrain, kl.ScaleConstrain):
            _xfo = plug_node.find('srt')
            if not _xfo:
                _xfo = create_srt_out(plug_in, joint_orient=is_joint)
            srt.rotate.connect(_xfo.rotate)
            _xfo.rotate_order.connect(srt.rotate_order)
        # scaling
        if type(plug_node) not in (kl.OrientConstrain, kl.TwistConstrain, kl.AimConstrain, kl.PointConstrain, kl.ParentConstrain):
            _xfo = plug_node.find('srt')
            if not _xfo:
                _xfo = create_srt_out(plug_in, joint_orient=is_joint)
            srt.scale.connect(_xfo.scale)
        # shearing
        if type(plug_node) in (kl.MultM44f, kl.InverseM44f):
            _xfo = plug_node.find('srt')
            if not _xfo:
                _xfo = create_srt_out(plug_in, joint_orient=is_joint)
            srt.shear.connect(_xfo.shear)
        # joint orient
        if is_joint:
            if not _xfo.joint_orient_rotate_order.is_connected():
                _xfo.joint_orient_rotate_order.set_value(srt.joint_orient_rotate_order.get_value())
            if not _xfo.rotate_order.is_connected():
                _xfo.rotate_order.set_value(srt.rotate_order.get_value())
            if not _xfo.joint_orient.is_connected():
                _xfo.joint_orient.set_value(srt.joint_orient_rotate.get_value())

    # merge translation
    translate_types = (kl.PointConstrain, kl.ParentConstrain)

    if t_in:
        t0_in = srt.translate.get_input()
        tx0_out = []
        ty0_out = []
        tz0_out = []

        if t0_in:
            t0_node = t0_in.get_node()

            # srt out?
            if isinstance(t0_node, kl.FloatToV3f):
                tx0_out = t0_node.x.get_outputs()
                ty0_out = t0_node.y.get_outputs()
                tz0_out = t0_node.z.get_outputs()

            # blend?
            do_blend = False
            if type(t0_node) in (kl.TransformToSRTNode, kl.JointTransformToSRT):
                if t0_node.transform.get_input():
                    t0_in = t0_node.transform.get_input()
                    do_blend = True
            if isinstance(t0_node, kl.BlendWeightedTransforms):
                if type(t0_node.get_parent()) in translate_types:
                    do_blend = True
            if type(t0_node) in translate_types or force_blend:
                do_blend = True
            if do_blend and not override:
                if node.get_dynamic_plug('blend_translate'):
                    raise RuntimeError('/!\\ cannot merge translate input connections, already blended')
                blend = kl.BlendTransformsNode(srt, 'blend_translate')
                if isinstance(t0_node, kl.FloatToV3f):
                    _t0_in = kl.SRTToTransformNode(t0_node, 'srt')
                    _t0_in.translate.connect(t0_in)
                    t0_in = _t0_in.transform
                blend.transform1_in.connect(t0_in)
                blend.transform2_in.connect(t_in)
                _blend = add_plug(node, 'blend_translate', float, min_value=0, max_value=1, default_value=1)
                blend.blend_in.connect(_blend)
                t_in = blend.transform_out
                log.debug(f'blend translate input connections of {node}')

        # merge srt
        t_in_node = t_in.get_node()
        if type(t_in_node) not in (kl.TransformToSRTNode, kl.FloatToV3f):
            _xfo = t_in_node.find('srt')
            if not _xfo:
                if is_joint:
                    _xfo = kl.JointTransformToSRT(t_in_node, 'srt')
                else:
                    _xfo = kl.TransformToSRTNode(t_in_node, 'srt')
                _xfo.transform.connect(t_in)
            t_in = _xfo.translate

        # chop axes
        if t_axes != 'xyz':
            t_in_v3f = kl.V3fToFloat(t_in.get_node(), 'translate')
            t_in_v3f.vector.connect(t_in)

            t_in_merge = kl.FloatToV3f(srt, 'translate_merge')
            for dim in t_axes:
                t_in_merge.get_plug(dim).connect(t_in_v3f.get_plug(dim))

            t0_in = srt.translate.get_input()
            if t0_in:
                t0_in_v3f = kl.V3fToFloat(t0_in.get_node(), 'translate')
                t0_in_v3f.vector.connect(t0_in)

                for dim in 'xyz':
                    if dim not in t_axes:
                        t_in_merge.get_plug(dim).connect(t0_in_v3f.get_plug(dim))

            t_in = t_in_merge.vector

        # reconnect
        srt.translate.connect(t_in)

        # reconnect former translate output
        if tx0_out or ty0_out or tz0_out:
            t_out = srt.translate.get_input()
            if not isinstance(t_out, kl.FloatToV3f):
                t_out = kl.V3fToFloat(srt, 'translate_out')
                t_out.vector.connect(srt.translate)
            for _tx in tx0_out:
                _tx.connect(t_out.x)
            for _ty in ty0_out:
                _ty.connect(t_out.y)
            for _tz in tz0_out:
                _tz.connect(t_out.z)

    # merge rotation
    rotate_types = (kl.OrientConstrain, kl.AimConstrain, kl.ParentConstrain)

    if r_in:
        r0_in = srt.rotate.get_input()
        rx0_out = []
        ry0_out = []
        rz0_out = []

        if r0_in:
            r0_node = r0_in.get_node()

            # srt out?
            if isinstance(r0_node, kl.FloatToEuler):
                rx0_out = r0_node.x.get_outputs()
                ry0_out = r0_node.y.get_outputs()
                rz0_out = r0_node.z.get_outputs()

            # blend?
            do_blend = False
            if type(r0_node) in (kl.TransformToSRTNode, kl.JointTransformToSRT):
                if r0_node.transform.get_input():
                    r0_in = r0_node.transform.get_input()
                    do_blend = True
            if isinstance(r0_node, kl.BlendWeightedTransforms):
                if type(r0_node.get_parent()) in rotate_types:
                    do_blend = True
            if type(r0_node) in rotate_types or force_blend:
                do_blend = True
            if do_blend and not override:
                if node.get_dynamic_plug('blend_rotate'):
                    raise RuntimeError('/!\\ cannot merge rotate input connections, already blended')
                blend = kl.BlendTransformsNode(srt, 'blend_rotate')
                if isinstance(r0_node, kl.FloatToEuler):
                    if is_joint:
                        _r0_in = kl.SRTToJointTransform(r0_node, 'srt')
                    else:
                        _r0_in = kl.SRTToTransformNode(r0_node, 'srt')
                    _r0_in.rotate.connect(r0_in)
                    _r0_in.rotate_order.connect(r0_node.rotate_order)
                    if is_joint:
                        _r0_in.joint_orient_rotate.connect(srt.joint_orient_rotate)
                        _r0_in.joint_orient_rotate_order.connect(srt.joint_orient_rotate_order)
                    r0_in = _r0_in.transform
                blend.transform1_in.connect(r0_in)
                blend.transform2_in.connect(r_in)
                _blend = add_plug(node, 'blend_rotate', float, min_value=0, max_value=1, default_value=1)
                blend.blend_in.connect(_blend)
                r_in = blend.transform_out
                log.debug(f'blend rotate input connections of {node}')

        # merge srt
        r_in_node = r_in.get_node()
        if type(r_in_node) in (kl.TransformToSRTNode, kl.FloatToEuler):
            r_in_node.rotate_order.connect(srt.rotate_order)
        else:
            _xfo = r_in_node.find('srt')
            if not _xfo:
                if is_joint:
                    _xfo = kl.JointTransformToSRT(r_in_node, 'srt')
                else:
                    _xfo = kl.TransformToSRTNode(r_in_node, 'srt')
                _xfo.transform.connect(r_in)
            _xfo.rotate_order.connect(srt.rotate_order)
            if is_joint:
                _xfo.joint_orient.connect(srt.joint_orient_rotate)
                _xfo.joint_orient_rotate_order.connect(srt.joint_orient_rotate_order)
            r_in = _xfo.rotate

        # chop axes
        if r_axes != 'xyz':
            r_in_v3f = kl.EulerToFloat(r_in.get_node(), 'euler')
            r_in_v3f.euler.connect(r_in)
            r_in_v3f.rotate_order.connect(r_in.get_node().rotate_order)

            r_in_merge = kl.FloatToEuler(srt, 'euler_merge')
            r_in_merge.rotate_order.connect(srt.rotate_order)
            for dim in r_axes:
                r_in_merge.get_plug(dim).connect(r_in_v3f.get_plug(dim))

            r0_in = srt.rotate.get_input()
            if r0_in:
                r0_in_v3f = kl.EulerToFloat(r0_in.get_node(), 'euler')
                r0_in_v3f.euler.connect(r0_in)
                r0_in_v3f.rotate_order.connect(r0_in.get_node().rotate_order)

                for dim in 'xyz':
                    if dim not in r_axes:
                        r_in_merge.get_plug(dim).connect(r0_in_v3f.get_plug(dim))

            r_in = r_in_merge.euler

        # reconnect
        srt.rotate.connect(r_in)

        # reconnect former rotate output
        if rx0_out or ry0_out or rz0_out:
            r_out = srt.rotate.get_input()
            if not isinstance(r_out, kl.FloatToEuler):
                r_out = kl.EulerToFloat(srt, 'rotate_out')
                r_out.euler.connect(srt.rotate)
                r_out.rotate_order.connect(srt.rotate_order)
            for _rx in rx0_out:
                _rx.connect(r_out.x)
            for _ry in ry0_out:
                _ry.connect(r_out.y)
            for _rz in rz0_out:
                _rz.connect(r_out.z)

    # merge translation
    scale_types = [kl.ScaleConstrain]

    if s_in:
        s0_in = srt.translate.get_input()
        sx0_out = []
        sy0_out = []
        sz0_out = []

        if s0_in:
            s0_node = s0_in.get_node()

            # srt out?
            if isinstance(s0_node, kl.FloatToV3f):
                sx0_out = s0_node.x.get_outputs()
                sy0_out = s0_node.y.get_outputs()
                sz0_out = s0_node.z.get_outputs()

            # blend?
            do_blend = False
            if type(s0_node) in (kl.TransformToSRTNode, kl.JointTransformToSRT):
                if s0_node.transform.get_input():
                    s0_in = s0_node.transform.get_input()
                    do_blend = True
            if isinstance(s0_node, kl.BlendWeightedTransforms):
                if type(s0_node.get_parent()) in scale_types:
                    do_blend = True
            if type(s0_node) in scale_types or force_blend:
                do_blend = True
            if do_blend and not override:
                if node.get_dynamic_plug('blend_translate'):
                    raise RuntimeError('/!\\ cannot merge scale input connections, already blended')
                blend = kl.BlendTransformsNode(srt, 'blend_scale')
                if isinstance(s0_node, kl.FloatToV3f):
                    _s0_in = kl.SRTToTransformNode(s0_node, 'srt')
                    _s0_in.scale.connect(s0_in)
                    s0_in = _s0_in.transform
                blend.transform1_in.connect(s0_in)
                blend.transform2_in.connect(s_in)
                _blend = add_plug(node, 'blend_scale', float, min_value=0, max_value=1, default_value=1)
                blend.blend_in.connect(_blend)
                s_in = blend.transform_out
                log.debug(f'blend scale input connections of {node}')

        # merge srt
        s_in_node = s_in.get_node()
        if type(s_in_node) not in (kl.TransformToSRTNode, kl.FloatToV3f):
            _xfo = s_in_node.find('srt')
            if not _xfo:
                if is_joint:
                    _xfo = kl.JointTransformToSRT(s_in_node, 'srt')
                else:
                    _xfo = kl.TransformToSRTNode(s_in_node, 'srt')
                _xfo.transform.connect(s_in)
            s_in = _xfo.scale

        # chop axes
        if s_axes != 'xyz':
            s_in_v3f = kl.V3fToFloat(s_in.get_node(), 'scale')
            s_in_v3f.vector.connect(s_in)

            s_in_merge = kl.FloatToV3f(srt, 'scale_merge')
            for dim in s_axes:
                s_in_merge.get_plug(dim).connect(s_in_v3f.get_plug(dim))

            s0_in = srt.scale.get_input()
            if s0_in:
                s0_in_v3f = kl.V3fToFloat(s0_in.get_node(), 'scale')
                s0_in_v3f.vector.connect(s0_in)

                for dim in 'xyz':
                    if dim not in s_axes:
                        s_in_merge.get_plug(dim).connect(s0_in_v3f.get_plug(dim))

            s_in = s_in_merge.vector

        # reconnect
        srt.scale.connect(s_in)

        # reconnect former scale output
        if sx0_out or sy0_out or sz0_out:
            s_out = srt.scale.get_input()
            if not isinstance(s_out, kl.FloatToV3f):
                s_out = kl.V3fToFloat(srt, 'scale_out')
                s_out.vector.connect(srt.scale)
            for _sx in sx0_out:
                _sx.connect(s_out.x)
            for _sy in sy0_out:
                _sy.connect(s_out.y)
            for _sz in sz0_out:
                _sz.connect(s_out.z)

    # reconnect shearing
    if sh_in:
        # sh0_in = srt.shear.get_input()

        sh_in_node = sh_in.get_node()
        if type(sh_in_node) in (kl.TransformToSRTNode, kl.FloatToV3f):
            srt.shear.connect(sh_in)
        else:
            _xfo = sh_in_node.find('srt')
            if not _xfo:
                _xfo = kl.TransformToSRTNode(sh_in_node, 'srt')
                _xfo.transform.connect(sh_in)
            srt.shear.connect(_xfo.shear)

    # update aim constraints
    if constraints is None:
        constraints = _get_input_constraint(node.transform)
    elif type(constraints) not in (tuple, list):
        constraints = [constraints]

    t_in = srt.translate.get_input()
    if t_in:
        t_in = t_in.get_node()
        if isinstance(t_in, kl.TransformToSRTNode):
            t_in = t_in.transform.get_input()

            for cnst in constraints:
                if isinstance(cnst, kl.AimConstrain):
                    if t_in != cnst.input_transform.get_input():
                        cnst.input_transform.connect(t_in)

    # exit
    return srt


def _init_constraint(constraint, targets, weights=None, world=None, maintain_offset=False):
    if world is not None:
        constraint.input_world.connect(world.world_transform)

    if weights is None:
        weights = [1] * len(targets)

    if len(targets) == 1:
        constraint.set_target(targets[0], maintain_offset)
    else:
        for i, target in enumerate(targets):
            constraint.set_target(target, maintain_offset, i)

            add_plug(constraint, f'w{i}', float, default_value=weights[i])
            target_weight = constraint.get_target_weight_plug(i)
            target_weight.connect(constraint.get_dynamic_plug(f'w{i}'))


def point_constraint(targets, node, maintain_offset=False, mo=None, axes='xyz', weights=None, force_blend=False):
    # args
    if isinstance(targets, kl.Node):
        targets = [targets]
    if len(targets) == 0:
        raise ValueError
    if mo is not None:
        maintain_offset = bool(mo)
    world = node.get_parent()

    # apply safe constraint
    plug_out = node.transform.get_input()
    cnst = kl.PointConstrain(node, 'point_constrain', len(targets))
    _init_constraint(cnst, targets, weights=weights, world=world, maintain_offset=maintain_offset)

    # merge constraint
    if plug_out or force_blend or axes != 'xyz':
        cnst_out = node.transform.get_input()
        if plug_out:
            node.transform.connect(plug_out)
        else:
            node.transform.disconnect(False)
            create_srt_in(node)

        merge_transform(node, t_in=cnst_out, t_axes=axes, force_blend=force_blend)

    return cnst


def parent_constraint(targets, node, maintain_offset=False, mo=None, weights=None,
                      translate_axes='xyz', rotate_axes='xyz', skip_rotation=False, skip_translation=False,
                      bw_size=None, force_blend=False):
    # args
    if isinstance(targets, kl.Node):
        targets = [targets]
    if len(targets) == 0:
        raise ValueError
    if mo is not None:
        maintain_offset = bool(mo)
    world = node.get_parent()

    # apply safe constraint
    plug_out = node.transform.get_input()
    cnst = kl.ParentConstrain(node, 'parent_constrain', len(targets), bw_size if bw_size is not None else len(targets))
    _init_constraint(cnst, targets, weights=weights, world=world, maintain_offset=maintain_offset)

    # merge constraint
    if plug_out or force_blend or translate_axes != 'xyz' or rotate_axes != 'xyz':
        cnst_out = node.transform.get_input()
        if plug_out:
            node.transform.connect(plug_out)
        else:
            node.transform.disconnect(False)
            create_srt_in(node)

        if skip_translation:
            merge_transform(node, r_in=cnst_out, r_axes=rotate_axes, force_blend=force_blend)
        elif skip_rotation:
            merge_transform(node, t_in=cnst_out, t_axes=translate_axes, force_blend=force_blend)
        else:
            merge_transform(node,
                            t_in=cnst_out, r_in=cnst_out,
                            t_axes=translate_axes, r_axes=rotate_axes,
                            force_blend=force_blend)

    return cnst


def orient_constraint(targets, node, maintain_offset=False, mo=None, axes='xyz', weights=None,
                      bw_size=None, force_blend=False):
    # args
    if isinstance(targets, kl.Node):
        targets = [targets]
    if len(targets) == 0:
        raise ValueError
    if mo is not None:
        maintain_offset = bool(mo)
    world = node.get_parent()

    # apply safe constraint
    plug_out = node.transform.get_input()
    cnst = kl.OrientConstrain(node, 'orient_constrain', len(targets), bw_size if bw_size is not None else len(targets))
    _init_constraint(cnst, targets, weights=weights, world=world, maintain_offset=maintain_offset)

    # merge constraint
    if plug_out or force_blend or axes != 'xyz':
        cnst_out = node.transform.get_input()
        if plug_out:
            node.transform.connect(plug_out)
        else:
            node.transform.disconnect(False)
            create_srt_in(node)

        merge_transform(node, r_in=cnst_out, r_axes=axes, force_blend=force_blend)
        # if isinstance(srt, kl.SRTToJointTransform):
        #     if srt.joint_orient_rotate.get_input():
        #         v = srt.joint_orient_rotate.get_input().get_node()
        #         v.x.set_value(0)
        #         v.y.set_value(0)
        #         v.z.set_value(0)
        #     else:
        #         srt.joint_orient_rotate.set_value(V3f(0, 0, 0))

    return cnst


def twist_constraint(
        targets, node, maintain_offset=False, mo=None, axes='xyz', weights=None,
        twist_vector=V3f(0, 1, 0)):
    # args
    if isinstance(targets, kl.Node):
        targets = [targets]
    if len(targets) == 0:
        raise ValueError
    if mo is not None:
        maintain_offset = bool(mo)
    if not isinstance(twist_vector, V3f):
        twist_vector = V3f(*twist_vector)
    world = node.get_parent()

    # apply safe constraint
    plug_out = node.transform.get_input()
    cnst = kl.TwistConstrain(node, 'twist_constrain', len(targets))
    cnst.axis.set_value(twist_vector)
    _init_constraint(cnst, targets, weights=weights, world=world, maintain_offset=maintain_offset)

    # merge constraint
    if plug_out or axes != 'xyz':
        cnst_out = node.transform.get_input()
        node.transform.connect(plug_out)

        merge_transform(node, r_in=cnst_out, r_axes=axes)
        # if isinstance(srt, kl.SRTToJointTransform):
        #     if srt.joint_orient_rotate.get_input():
        #         v = srt.joint_orient_rotate.get_input().get_node()
        #         v.x.set_value(0)
        #         v.y.set_value(0)
        #         v.z.set_value(0)
        #     else:
        #         srt.joint_orient_rotate.set_value(V3f(0, 0, 0))

    return cnst


def aim_constraint(
        targets, node, maintain_offset=False, mo=None, axes='xyz', weights=None, force_blend=False,
        aim_vector=V3f(1, 0, 0),
        up_vector=V3f(0, 1, 0),
        up_vector_world=V3f(0, 0, 0),
        up_vector_object=V3f(0, 0, 0),
        up_object=None):
    # args
    if isinstance(targets, kl.Node):
        targets = [targets]
    if len(targets) == 0:
        raise ValueError
    if mo is not None:
        maintain_offset = bool(mo)
    if not isinstance(aim_vector, V3f):
        aim_vector = V3f(*aim_vector)
    if not isinstance(up_vector, V3f):
        up_vector = V3f(*up_vector)
    if not isinstance(up_vector_world, V3f):
        up_vector_world = V3f(*up_vector_world)
    if not isinstance(up_vector_object, V3f):
        up_vector_object = V3f(*up_vector_object)

    world = node.get_parent()

    # apply safe constraint
    plug_out = node.transform.get_input()
    cnst = kl.AimConstrain(node, 'aim_constrain', len(targets))

    cnst.aim_vector.set_value(aim_vector)
    cnst.up_vector.set_value(up_vector)
    cnst.up_vector_world.set_value(up_vector_world)
    cnst.up_vector_in_space.set_value(up_vector_object)
    if up_object is not None:
        cnst.up_vector_space.connect(up_object.world_transform)
        if maintain_offset:
            cnst.initial_up_vector_space.set_value(up_object.world_transform.get_value())

    if up_vector_world.length():
        log.warning('/!\ up vector world does not work with maintain offset yet')

    _init_constraint(cnst, targets, weights=weights, world=world, maintain_offset=maintain_offset)

    # merge constraint
    if plug_out or force_blend or axes != 'xyz':
        cnst_out = node.transform.get_input()
        if plug_out:
            node.transform.connect(plug_out)
        else:
            node.transform.disconnect(False)
            create_srt_in(node)

        merge_transform(node, r_in=cnst_out, r_axes=axes, force_blend=force_blend)
        # if isinstance(srt, kl.SRTToJointTransform):
        #     if srt.joint_orient_rotate.get_input():
        #         v = srt.joint_orient_rotate.get_input().get_node()
        #         v.x.set_value(0)
        #         v.y.set_value(0)
        #         v.z.set_value(0)
        #     else:
        #         srt.joint_orient_rotate.set_value(V3f(0, 0, 0))

    return cnst


def scale_constraint(targets, node, maintain_offset=False, mo=None, axes='xyz', weights=None, force_blend=False):
    # args
    if isinstance(targets, kl.Node):
        targets = [targets]
    if len(targets) == 0:
        raise ValueError
    if mo is not None:
        maintain_offset = bool(mo)
    world = node.get_parent()

    # apply safe constraint
    plug_out = node.transform.get_input()
    cnst = kl.ScaleConstrain(node, 'scale_constrain', len(targets))
    _init_constraint(cnst, targets, weights=weights, world=world, maintain_offset=maintain_offset)

    # merge constraint
    if plug_out or force_blend or axes != 'xyz':
        cnst_out = node.transform.get_input()
        if plug_out:
            node.transform.connect(plug_out)
        else:
            node.transform.disconnect(False)
            create_srt_in(node)

        merge_transform(node, s_in=cnst_out, s_axes=axes, force_blend=force_blend)

    return cnst


def matrix_constraint(target, node):
    parent = node.get_parent()
    root = isinstance(parent, kl.RootNode)

    offset = node.world_transform.get_value() * target.world_transform.get_value().inverse()

    if not root:
        _inv = kl.InverseM44f(node, 'inv')
        _inv.input.connect(node.parent_world_transform)

        _mmx = kl.MultM44f(node, '_mmx', 3)
        _mmx.input[0].set_value(offset)
        _mmx.input[1].connect(target.world_transform)
        _mmx.input[2].connect(_inv.output)
    else:
        _mmx = kl.MultM44f(node, '_mmx', 2)
        _mmx.input[0].set_value(offset)
        _mmx.input[1].connect(target.world_transform)

    node.transform.connect(_mmx.output)
    return node


def find_target(node):
    cnst = node.transform.get_input()
    if not cnst:
        log.debug(f'/!\\ no target found for node "{node}"')
        return
    cnst = cnst.get_node()

    # parentConstraint?
    if isinstance(cnst, kl.ParentConstrain):
        _ctrl = cnst.input_target_world_transform.get_input()
        if _ctrl:
            ctrl = _ctrl.get_node()
            if isinstance(ctrl, kl.SceneGraphNode):
                return ctrl

    elif isinstance(cnst, kl.SRTToTransformNode):
        _srt = cnst.translate.get_input()
        if _srt:
            _srt = _srt.get_node()
            if isinstance(_srt, kl.TransformToSRTNode):
                _xfo = _srt.transform.get_input()
                if _xfo:
                    _xfo = _xfo.get_node()
                    if isinstance(_xfo, kl.ParentConstrain):
                        _ctrl = _xfo.input_target_world_transform.get_input()
                        if _ctrl:
                            ctrl = _ctrl.get_node()
                            if isinstance(ctrl, kl.SceneGraphNode):
                                return ctrl

    # direct hook
    if isinstance(cnst, kl.MultM44f):
        _ctrl = cnst.input[cnst.input.get_size() - 2].get_input()
        if _ctrl:
            ctrl = _ctrl.get_node()
            if isinstance(ctrl, kl.SceneGraphNode):
                return ctrl

    # no result :(
    log.debug(f'/!\\ no target found for node "{node}"')


def find_closest_node(node, targets):
    if not isinstance(node, kl.SceneGraphNode):
        raise TypeError('node is not a SceneGraphNode')

    if not isinstance(targets, list) or not all([isinstance(t, kl.SceneGraphNode) for t in targets]):
        raise TypeError('targets has to be a list of SceneGraphNode')

    p0 = node.world_transform.get_value().translation()

    closest = None
    d = float('inf')

    for target in targets:
        p1 = target.world_transform.get_value().translation()
        _d = (p1 - p0).length()
        if _d < d:
            d = _d
            closest = target

    return closest


def str_to_rotate_order(ro_str):
    rotate_orders = {"xyz": Euler.XYZ,
                     "xzy": Euler.XZY,
                     "yzx": Euler.YZX,
                     "yxz": Euler.YXZ,
                     "zxy": Euler.ZXY,
                     "zyx": Euler.ZYX,
                     "default": Euler.Default
                     }
    ro_str = ro_str.lower()
    if ro_str in rotate_orders:
        return rotate_orders[ro_str]


def axis_to_vector(axis):
    _axes = {'x': V3f(1, 0, 0),
             'y': V3f(0, 1, 0),
             'z': V3f(0, 0, 1),
             '+x': V3f(1, 0, 0),
             '+y': V3f(0, 1, 0),
             '+z': V3f(0, 0, 1),
             '-x': V3f(-1, 0, 0),
             '-y': V3f(0, -1, 0),
             '-z': V3f(0, 0, -1)}
    axis = axis.lower()
    if axis in _axes:
        return _axes[axis]


def get_stretch_axis(joints, bias=0.001):
    axis = None

    for j in joints[1:]:
        t = j.transform.get_value().translation()
        x = abs(t.x)
        y = abs(t.y)
        z = abs(t.z)
        if x > y and x > z and y + z < 2 * bias:
            axis = ['x', 'y', 'z']
        if y > x and y > z and x + z < 2 * bias:
            axis = ['y', 'x', 'z']
        if z > y and z > x and x + y < 2 * bias:
            axis = ['z', 'x', 'y']
    return axis


def duplicate_joint(j, p=None, parent=None, n=None, name=None):
    if not isinstance(j, kl.Joint):
        raise RuntimeError(f'"{j}" is not a joint')

    # args
    if p is not None:
        parent = p
    if n is not None:
        name = n

    # duplicate
    d = kl.Joint(j.get_parent(), name)
    copy_transform(j, d)
    d.bind_pose.set_value(j.bind_pose.get_value())

    if parent:
        d.reparent(parent)

    return d


def mirror_joints(node, myz=True, mxy=False, mxz=False, nodes=None, _root=None, _dupe=None):
    if not nodes:
        nodes = []

    name = node.get_name().split(':')[-1]
    node_type = type(node)
    if not _root:
        name += '_dupe'
        _root = node.get_parent()
        _dupe = _root
    d = node_type(_dupe, name)
    if node_type == kl.Joint:
        d.scale_compensate.set_value(node.scale_compensate.get_value())
    nodes.append(d)

    # mirror transformation
    pim = _dupe.world_transform.get_value().inverse()
    wm = node.world_transform.get_value()
    if isinstance(node, kl.Joint):
        dm = node.delta_transform.get_value().inverse()  # /!\ not invert
        wm = dm * wm

    yz = 1
    xz = 1
    xy = 1
    if myz:
        yz = -1
    if mxz:
        xz = -1
    if mxy:
        xy = -1

    if -1 in (yz, xz, xy):
        r = M44f(V3f(0, 0, 0), V3f(0, 0, 0), V3f(-1, -1, -1), Euler.XYZ)
        s = M44f(V3f(0, 0, 0), V3f(0, 0, 0), V3f(yz, xz, xy), Euler.XYZ)
        pos = _root.world_transform.get_value().translation()
        p = M44f(pos, V3f(0, 0, 0), V3f(1, 1, 1), Euler.XYZ)
        ip = M44f(pos * -1, V3f(0, 0, 0), V3f(1, 1, 1), Euler.XYZ)

        d.transform.set_value(r * wm * ip * s * p * pim)
    else:
        copy_transform(node, d)

    # copy attrs
    for plug in node.get_dynamic_plugs():
        plug_name = plug.get_name()
        plug_value = plug.get_value()
        d.add_dynamic_plug(plug_name, plug_value)
        d.get_dynamic_plug(plug_name)

    # duplicate children
    for child in node.get_children():
        if not isinstance(child, kl.Joint) and not isinstance(child, kl.SceneGraphNode):
            continue
        mirror_joints(child, myz=myz, mxy=mxy, mxz=mxz, nodes=nodes, _root=_root, _dupe=d)

    return nodes


def orient_joint(joints, orient_last=True,
                 aim='y', aim_dir=None, aim_tgt=None,
                 up='z', up_dir=(0, 0, 1), up_tgt=None, up_auto=None, up_conform=True):
    """
    orient given joints

    :param list, tuple joints: joint list to orient

    :param str aim: primary axis (x, -x, y, -y, z, -z)
    :param dt.Vector aim_dir: vector for primary axis
    :param None, Joint, SceneGraphNode aim_tgt: structure to get nodes for aim (overrides aim_dir)

    :param str up: secondary axis (x, -x, y, -y, z, -z)
    :param dt.Vector up_dir: vector for secondary axis
    :param None, Joint, SceneGraphNode up_tgt: structure to get nodes for up (overrides up_dir)

    :param int up_auto (overrides up_dir, up_tgt)
    - None: not used
    - 0: average of up vector found for each joint
    - 1: each up vector is recalculated for each joint
    - 2: first relevant (non null) up vector
    - 3: last relevant up vector
    :param bool up_conform: conform up vectors general direction

    """

    # sl = find_doc().node_selection.get_value()
    if isinstance(joints, kl.SceneGraphNode):
        joints = [joints]
    else:
        joints = [j for j in joints if type(j) in (kl.Joint, kl.SceneGraphNode)]

    # store initial world transform
    initial_xfo = {}
    for j in joints:
        for _j in [n for n in j.get_children() if type(n) in (kl.Joint, kl.SceneGraphNode)]:
            initial_xfo[_j] = _j.world_transform.get_value()

    new_xfo = {}

    aim = axis_to_vector(aim)
    up = axis_to_vector(up)
    if aim_dir:
        if type(aim_dir) in (list, tuple):
            aim_dir = V3f(*aim_dir)
    if up_dir:
        if type(up_dir) in (list, tuple):
            up_dir = V3f(*up_dir)

    aim_root = kl.SceneGraphNode(find_root(), '_aim_root')
    aim_dummy = kl.SceneGraphNode(aim_root, '_aim_tmp')
    up_dummy = kl.SceneGraphNode(aim_root, '_up_tmp')
    dummy = kl.SceneGraphNode(aim_root, '_dummy')
    dummy_joint = kl.SceneGraphNode(aim_root, '_dummy_joint')
    aim_constraint([aim_dummy], dummy, aim_vector=aim, up_vector=up, up_object=up_dummy)

    # compute up vectors auto
    up_vectors = []
    if up_auto is not None:
        # get joint vectors
        j_vectors = []
        for i, j in enumerate(joints[:-1]):
            v = joints[i + 1].world_transform.get_value().translation()
            _v = joints[i].world_transform.get_value().translation()
            v -= _v
            j_vectors.append(v)
        # compute up vectors from given joints
        for i, j in enumerate(j_vectors[1:]):
            v = j_vectors[i].cross(j_vectors[i + 1])
            up_vectors.append(v.normalized())
        # first two joints should share their up vector
        if up_vectors:
            up_vectors = [up_vectors[0]] + up_vectors

        # conform up vectors general direction (for each and average)
        if up_conform and up_auto < 2:
            for i, j in enumerate(up_vectors[1:]):
                if up_vectors[i - 1].dot(up_vectors[i]) < 0:
                    up_vectors[i] *= -1

    # compute orient for each joints
    for i, j in enumerate(joints):
        # get position
        p = j.world_transform.get_value().translation()
        xfo = M44f(p, V3f(0, 0, 0), V3f(1, 1, 1), Euler.XYZ)
        aim_root.transform.set_value(xfo)

        # get aim and up vectors
        if aim_dir:
            xfo = M44f(aim_dir, V3f(0, 0, 0), V3f(1, 1, 1), Euler.XYZ)
            aim_dummy.transform.set_value(xfo)
        else:
            if aim_tgt is None and len(joints) > 1:
                if i < len(joints) - 1:
                    _aim_tgt = joints[i + 1]
                    p = _aim_tgt.world_transform.get_value().translation()
                    xfo = M44f(p, V3f(0, 0, 0), V3f(1, 1, 1), Euler.XYZ)
                    aim_dummy.set_world_transform(xfo)
                else:
                    # keep same direction
                    pass
            elif type(aim_tgt) in (kl.Joint, kl.SceneGraphNode):
                p = aim_tgt.world_transform.get_value().translation()
                xfo = M44f(p, V3f(0, 0, 0), V3f(1, 1, 1), Euler.XYZ)
                aim_dummy.set_world_transform(xfo)

        xfo = M44f(up_dir, V3f(0, 0, 0), V3f(1, 1, 1), Euler.XYZ)
        up_dummy.transform.set_value(xfo)

        if up_auto is not None:
            if up_auto == 0:
                # average
                v = V3f(0, 0, 0)
                for u in up_vectors:
                    v += u
                xfo = M44f(v, V3f(0, 0, 0), V3f(1, 1, 1), Euler.XYZ)
                up_dummy.transform.set_value(xfo)
            elif up_auto == 1:
                # each
                if i < len(up_vectors):
                    xfo = M44f(up_vectors[i], V3f(0, 0, 0), V3f(1, 1, 1), Euler.XYZ)
                    up_dummy.transform.set_value(xfo)
                else:
                    xfo = M44f(up_vectors[-1], V3f(0, 0, 0), V3f(1, 1, 1), Euler.XYZ)
                    up_dummy.transform.set_value(xfo)
            elif up_auto == 2:
                # first
                xfo = M44f(up_vectors[0], V3f(0, 0, 0), V3f(1, 1, 1), Euler.XYZ)
                up_dummy.transform.set_value(xfo)
            elif up_auto == 3:
                # last
                xfo = M44f(up_vectors[-1], V3f(0, 0, 0), V3f(1, 1, 1), Euler.XYZ)
                up_dummy.transform.set_value(xfo)

        elif type(up_tgt) in (kl.Joint, kl.SceneGraphNode):
            p = up_tgt.world_transform.get_value().translation()
            xfo = M44f(p, V3f(0, 0, 0), V3f(1, 1, 1), Euler.XYZ)
            up_dummy.set_world_transform(xfo)

        # set joint
        if i > 0 and i == len(joints) - 1 and not orient_last:
            pass
        else:
            copy_transform(j, dummy_joint)
            copy_transform(dummy, dummy_joint, r=1)
            new_xfo[j] = dummy_joint.world_transform.get_value()

    for j in joints:
        children = [n for n in j.get_children() if type(n) in (kl.Joint, kl.SceneGraphNode)]

        j.set_world_transform(new_xfo[j])

        for child in children:
            if child not in joints:
                child.set_world_transform(initial_xfo[child])

    # exit
    aim_root.remove_from_parent()


def create_blend_joint(j, jparent, **kw):
    name = kw.get('name', kw.get('n', f'{j.get_name()}_blend'))
    p = kw.get('parent', kw.get('p'))

    rb = duplicate_joint(j, p=j, n=name)
    if p:
        rb.reparent(p)
    rb.scale_compensate.set_value(False)  # scale legacy
    create_srt_in(rb)
    offset = kl.SceneGraphNode(j, f'_{j.get_name()}_offset')
    offset.reparent(jparent)

    _x = orient_constraint((offset, j), rb)
    blend = _x.find('blend_weighted_transforms')
    blend.transform_shortest_in.set_value(True)

    return rb


def create_ik_handle(joints, parent=None, transform=None):
    if parent is None:
        parent = joints[0].get_parent()
    eff = kl.SceneGraphNode(parent, 'effector')

    if transform is None:
        transform = joints[-1]
    eff.set_world_transform(transform.world_transform.get_value())

    ik = kl.IK(len(joints), eff, 'ik')
    ik.root_parent_is_joint_in.set_value(isinstance(joints[0].get_parent(), kl.Joint))
    ik.blend.set_value(0)

    for i, joint in enumerate(joints):
        joint.bind_pose.set_value(joint.world_transform.get_value())
        ik.joints_bind_pose_in[i].connect(joint.bind_pose)

    ik.world_target_in.connect(eff.transform)
    ik.blend.set_value(1)
    ik.translate_root_in.set_value(joints[0].transform.get_value().translation())
    if joints[0].find('point_constrain') or joints[0].find('parent_constrain'):
        if joints[0].find('point_constrain'):
            srt = create_srt_out(joints[0].find('point_constrain'))
        else:
            srt = create_srt_out(joints[0].find('parent_constrain'))
        ik.translate_root_in.connect(srt.translate)

    ik.parent_root_in.connect(joints[0].get_parent().transform)
    ik.initial_world_parent_root_in.set_value(joints[0].get_parent().world_transform.get_value())
    ik.world_parent_root_in.connect(joints[0].get_parent().world_transform)
    ik.world_in.connect(parent.world_transform)

    for i in range(len(joints) - 1):

        if joints[i].find('transform') is None:
            _srt = kl.SRTToTransformNode(joints[i], 'transform')
            joints[i].transform.connect(_srt.transform)

        blend_xfo = kl.BlendTransformsNode(joints[i], 'blend_transforms')
        blend_xfo.transform1_in.connect(joints[i].find('transform').transform)
        blend_xfo.transform2_in.connect(ik.joints_transform_out[i])
        blend_xfo.blend_in.connect(ik.blend)

        joints[i].transform.connect(blend_xfo.transform_out)

        ik.scale_vector_in[i].connect(joints[i].find('transform').scale)

    return eff


def reparent_ik_handle(eff, parent):
    for child in eff.get_children():
        if type(child) == kl.IK:
            eff.reparent(parent)
            child.world_in.connect(parent.world_transform)
            return child
            # TODO: set new root_parent_is_joint_in
            # ik.root_parent_is_joint_in.set_value(isinstance(root_joint.get_parent()?, kl.Joint))


def stretch_IK(joints, ctrl, eff_parent=None):
    root = joints[0].get_parent()
    sg_root = kl.SceneGraphNode(ctrl, 'stretch_network')

    # attributes
    add_plug(ctrl, 'twist', float, k=1, step=1, nice_name='Twist')
    add_plug(ctrl, 'twist_offset', float, k=1, step=1, nice_name='Twist Offset')

    add_plug(ctrl, 'stretch', float, k=1, min_value=0, max_value=1, nice_name='Stretch')
    add_plug(ctrl, 'squash', float, k=1, min_value=0, max_value=1, nice_name='Squash')
    add_plug(ctrl, 'squash_rate', float, k=1, min_value=-1, max_value=1, nice_name='Squash Rate')
    # set_plug(ctrl.squash_rate, cb=1)

    add_plug(ctrl, 'min_stretch', float, k=1, default_value=1, min_value=0.1, max_value=1, nice_name='Min Stretch')
    add_plug(ctrl, 'soft', float, k=1, min_value=0, max_value=1, nice_name='Soft')
    add_plug(ctrl, 'soft_distance', float, k=1, default_value=0.1, min_value=0, max_value=1, nice_name='Soft Distance')
    # set_plug(ctrl.soft_distance, cb=1)

    add_plug(ctrl, 'distance', float)
    add_plug(ctrl, 'factor', float)

    # get main axis
    axis = get_stretch_axis(joints)
    if not axis:
        raise RuntimeError('joints not oriented, can\'t compute chain stretch')

    # effectors
    eff_root = kl.SceneGraphNode(root, 'eff_root')
    if eff_parent is None:
        _eff_parent = root
    else:
        _eff_parent = eff_parent
    eff_real = kl.SceneGraphNode(_eff_parent, 'eff_real')

    eff_ik = create_ik_handle(joints, transform=joints[-1])
    ik_handle = eff_ik.find('ik')

    # rig effector
    srt_eff_root = create_srt_in(eff_root, vectors=False)
    srt_eff_root.translate.connect(joints[0].find('transform').translate)
    if eff_parent is not None:
        _eff_root = eff_root
        _eff_root.rename('_eff_root')
        eff_root = kl.SceneGraphNode(eff_parent, 'eff_root')
        point_constraint(_eff_root, eff_root)
        srt_eff_root = create_srt_out(eff_root, vectors=False)

    srt_eff_real = create_srt_out(eff_real, vectors=False)

    copy_transform(joints[-1], eff_real, t=1)
    parent_constraint(ctrl, eff_real, mo=1)

    ikc = point_constraint((eff_root, eff_real), eff_ik)
    ikc.w0.set_value(0)

    # twist
    _add = connect_add(ctrl.twist, ctrl.twist_offset, p=sg_root)
    if getattr(joints[-1].transform.get_value().translation(), axis[0]) > 0:
        ik_handle.twist_in.connect(_add)
    else:
        connect_mult(_add, -1, ik_handle.twist_in, p=sg_root)

    # squash power
    _spow = connect_mult(ctrl.squash_rate, -1.5, p=sg_root)
    _spow = connect_add(_spow, -0.5)

    # distance probe
    _len = kl.Distance(ik_handle, 'distance')
    _len.input1.connect(srt_eff_root.translate)
    _len.input2.connect(srt_eff_real.translate)
    _len = _len.output

    ctrl.distance.connect(_len)

    # joints attr
    for j in joints[0:-1]:
        add_plug(j, 'stretch', float)
        add_plug(j, 'squash', float)

    dchain = 0
    for j in joints[1:]:
        dchain += j.transform.get_value().translation().length()

    # node network
    nj = len(joints)

    _rev_stretch = connect_sub(1, ctrl.stretch, p=sg_root)
    _rev_soft = connect_sub(1, ctrl.soft, p=sg_root)
    _rev_squash = connect_sub(1, ctrl.squash, p=sg_root)

    _ds = []
    for i in range(nj - 1):
        _s = joints[i].find('transform/scale').get_plug(axis[0])
        _t = joints[i + 1].transform.get_value().translation().length()
        _ds.append(connect_mult(_t, _s, p=sg_root))

    _d0 = _ds[0]
    if len(_ds) > 1:
        _d0 = connect_sum(_ds, n='init_distance', p=sg_root)

    _fc = connect_add(_rev_stretch, connect_mult(ctrl.min_stretch, ctrl.stretch, p=sg_root))
    _d0 = connect_mult(_d0, _fc, p=sg_root, n='_dchain0')

    _if = kl.IsGreater(sg_root, '_isg')
    _if.input1.connect(_len)
    _if.input2.connect(_d0)
    _w1 = kl.Condition(sg_root, '_if')
    _w1.condition.connect(_if.output)
    _w2 = kl.Condition(sg_root, '_if')
    _w2.condition.connect(_if.output)

    connect_div(_d0, _len, _w1.input1)
    _w1.input2.set_value(1)

    _div = connect_div(_len, _d0)
    connect_add(_rev_stretch, connect_mult(ctrl.stretch, _div, p=sg_root), _w2.input1)
    _w2.input2.set_value(1)
    _f0 = _w2.output

    _w = _w1.output

    _if = kl.IsGreater(sg_root, '_isg')
    _if.input1.connect(ctrl.soft)
    _if.input2.set_value(0)
    _soft1 = kl.Condition(sg_root, '_soft')
    _soft1.condition.connect(_if.output)
    _soft3 = kl.Condition(sg_root, '_soft')
    _soft3.condition.connect(_if.output)

    _ds = connect_mult(ctrl.soft_distance, _d0, p=sg_root)
    _da = connect_sub(_d0, _ds)

    _if = kl.IsGreaterOrEqual(sg_root, '_isge')
    _if.input1.connect(_len)
    _if.input2.connect(_da)
    _deff = kl.Condition(sg_root, '_if')
    _deff.condition.connect(_if.output)
    _deff.input2.connect(_len)

    _div = kl.Div(sg_root, '_div')
    _div.input1.connect(connect_mult(-1, connect_sub(_len, _da)))
    _div.input2.connect(_ds)
    _exp = connect_power(math.e, _div.output)
    _deff.input1.connect(connect_add(connect_mult(_ds, connect_sub(1, _exp)), _da))
    _deff = _deff.output

    _wsoft = connect_div(_deff, _len)

    _w = connect_add(connect_mult(_rev_soft, _w), connect_mult(ctrl.soft, _wsoft, p=sg_root))
    _fsoft = connect_div(1, _w)
    _w = connect_add(ctrl.stretch, connect_mult(_rev_stretch, _w), p=sg_root)

    _soft1.input1.connect(_w)
    _soft1.input2.set_value(1)
    _soft3.input1.connect(_fsoft)
    _soft3.input2.set_value(1)

    _w = _soft1.output
    _fsoft = _soft3.output

    ikc.w1.connect(_w)
    connect_sub(1, _w, ikc.w0)

    _if = kl.IsGreater(sg_root, '_isg')
    _if.input1.connect(ctrl.stretch)
    _if.input2.set_value(0)
    _f = kl.Condition(sg_root, '_if')
    _f.condition.connect(_if.output)
    _f.input2.set_value(1)

    _fsoft = connect_add(_rev_stretch, connect_mult(_fsoft, ctrl.stretch))
    connect_add(connect_mult(_f0, _rev_soft), connect_mult(_fsoft, ctrl.soft), _f.input1)

    _f = _f.output
    _f = connect_add(connect_mult(ik_handle.blend, _f), connect_sub(1, ik_handle.blend))

    for i in range(nj - 1):
        _s = joints[i].find('transform/scale')
        _saim = connect_mult(_f, _s.get_plug(axis[0]), p=sg_root)

        _if = kl.IsGreater(sg_root, '_isg')
        _if.input1.connect(ctrl.squash)
        _if.input2.set_value(0)
        _sup = kl.Condition(sg_root, '_if')
        _sup.condition.connect(_if.output)
        _sup.input2.set_value(1)

        _pow = connect_power(_saim, _spow)
        connect_add(_rev_squash, connect_mult(ctrl.squash, _pow, p=sg_root), _sup.input1)
        _sup = _sup.output
        _sup1 = connect_mult(_sup, _s.get_plug(axis[1]))
        _sup2 = connect_mult(_sup, _s.get_plug(axis[2]))

        joints[i].stretch.connect(_saim)
        joints[i].squash.connect(_sup)

        _vs = kl.FloatToV3f(sg_root, 'scale')
        _vs.get_plug(axis[0]).connect(connect_mult(_saim, _fc))
        _vs.get_plug(axis[1]).connect(_sup1)
        _vs.get_plug(axis[2]).connect(_sup2)
        ik_handle.scale_vector_in[i].connect(_vs.vector)

    return ik_handle, eff_ik, eff_root, eff_real


def stretch_spline_IK(curve, joints, mode=0, connect_scale=True, curves=[]):
    if not isinstance(curve, kl.SplineCurve):
        raise RuntimeError('not a curve')
    cv = curve.get_parent()

    # args
    axis = get_stretch_axis(joints)
    if not axis:
        raise RuntimeError("joints not oriented, can't compute chain stretch")

    # update tesselation
    spline = curve.spline_in.get_value()
    sampling = 10 * (len(spline.get_control_points()) + 1) * (spline.get_degree() ** 2)
    curve.sampling_in.set_value(sampling)
    if sampling > 1000:
        curve.sampling_in.set_all_user_infos({"max": "20000"})

    # IK
    spline_ik = kl.SplineIK(len(joints), joints[0], 'spline_ik')
    spline_ik.legacy.set_value(1)
    spline_ik.maya_twist_in.set_value(not Prefs.get('tangerine/spline_ik_twist_legacy', False))
    jnt0 = joints[0]

    spline_ik.world_in.connect(jnt0.parent_world_transform)
    spline_ik.world_parent_root_in.connect(jnt0.parent_world_transform)
    spline_ik.parent_root_in.connect(jnt0.get_parent().transform)
    spline_ik.world_spline_in.connect(curve.get_parent().world_transform)
    spline_ik.spline_in.connect(curve.spline_in)
    spline_ik.spline_initial_length_in.set_value(curve.length_out.get_value())
    spline_ik.spline_mesh_in.connect(curve.spline_mesh_out)
    spline_ik.root_parent_is_joint_in.set_value(isinstance(jnt0.get_parent(), kl.Joint))
    spline_ik.initial_world_parent_root_in.set_value(jnt0.parent_world_transform.get_value())

    for j in joints:
        j.bind_pose.set_value(j.world_transform.get_value())

    idx = 0
    for j in joints:
        spline_ik.joints_bind_pose_in[idx].connect(j.bind_pose)
        j.transform.connect(spline_ik.joints_transform_out[idx])
        idx += 1

    # scale in
    add_plug(spline_ik, 'stretch', float, min_value=0, max_value=1)
    add_plug(spline_ik, 'squash', float, min_value=0, max_value=1)
    add_plug(spline_ik, 'slide', float, min_value=-1, max_value=1)
    add_plug(spline_ik, 'squash_rate', float, min_value=-1, max_value=1)

    # tmp slide graph
    graph1 = kl.CurveFloat()
    graph1.set_keys_with_tangent_mode([[0, 0, 1], [.222, .5, 1], [1, 1, 3]])

    graph2 = kl.CurveFloat()
    graph2.set_keys_with_tangent_mode([[0, 0, 3], [.777, .5, 1], [1, 1, 1]])

    # stretch graph
    poc = []
    poc_srt = []
    db = []

    for i, joint in enumerate(joints):
        poc.append(kl.PointOnSplineCurve(curve, 'poc'))
        poc_srt.append(create_srt_out(poc[-1], vectors=False))
        poc[-1].spline_in.connect(curve.spline_in)
        poc[-1].spline_mesh_in.connect(curve.spline_mesh_out)

        u = get_closest_point_on_curve(curve, joint, parametric=True) if i < len(joints) - 1 else 1
        poc[-1].u_in.set_value(u)

        _sg = kl.SceneGraphNode(cv, 'poc_srt')
        _sg.transform.connect(poc[-1].transform_out)

    for i, joint in enumerate(joints[:-1]):
        # distance
        _len = kl.Distance(poc[i], 'length')
        poc_srt[i + 1].transform.connect(poc[i + 1].transform_out)
        poc_srt[i].transform.connect(poc[i].transform_out)
        _len.input1.connect(poc_srt[i + 1].translate)
        _len.input2.connect(poc_srt[i].translate)

        db.append(_len)

        # slide
        _cycle = kl.Cycle.constant
        pmax = 1
        if i > 0:
            v = poc[i].u_in.get_value()
            v1 = graph1.cubic_interpolate(v, _cycle, _cycle)
            v2 = graph2.cubic_interpolate(v, _cycle, _cycle)
            v1 *= pmax
            v2 *= pmax

            crv = kl.CurveFloat()
            crv.set_keys_with_tangent_mode([[v1, -1, 3], [v, 0, 3], [v2, 1, 3]])

            _sdk = kl.DrivenFloat(poc[i], '_sdk')
            _sdk.curve.set_value(crv)
            _sdk.driver.connect(spline_ik.slide)
            poc[i].u_in.connect(_sdk.result)

        # stretch attr
        if joint.get_dynamic_plug('stretch'):
            joint.remove_dynamic_plug('stretch')
        add_plug(joint, 'stretch', float)

        if joint.get_dynamic_plug('squash'):
            joint.remove_dynamic_plug('squash')
        add_plug(joint, 'squash', float)

    # squash power
    spow = connect_expr('-0.15 * rate - 0.5', rate=spline_ik.squash_rate)

    _stretch = spline_ik.stretch
    _squash = spline_ik.squash
    _rev_squash = connect_sub(1, _squash)
    _rev_stretch = connect_sub(1, _stretch)

    for i, joint in enumerate(joints[:-1]):
        _saim = kl.Div(joint, 'stretch')
        _spow = kl.Pow(joint, 'squash')

        _saim.input1.connect(db[i].output)
        _saim.input2.set_value(db[i].output.get_value())
        _spow.input2.connect(spow)

        # scale mode
        _s = connect_add(_rev_stretch, connect_mult(_saim.output, _stretch))
        _spow.input1.connect(_s)

        joint.stretch.connect(_s)
        _sup = connect_add(_rev_squash, connect_mult(_squash, _spow.output))
        joint.squash.connect(_sup)

        # vector
        _scale = kl.FloatToV3f(joint, 'scale')
        _scale.get_plug(axis[0]).connect(_s)
        _scale.get_plug(axis[1]).connect(_sup)
        _scale.get_plug(axis[2]).connect(_sup)
        spline_ik.scale_vector_in[i].connect(_scale.vector)

    # snap last joint to stretch
    loc_tip = kl.SceneGraphNode(cv, 'loc_tip')
    loc_tip.transform.connect(poc[-1].transform_out)

    px = point_constraint(loc_tip, joints[-1])

    blend_xfo = kl.BlendTransformsNode(joints[-1], 'blend_transforms')
    blend_xfo.transform1_in.connect(spline_ik.joints_transform_out[i])
    blend_xfo.transform2_in.connect(px.constrain_transform)

    connect_expr(
        "blend = stretch == 1 ? 1 : 0",
        stretch=_stretch,
        blend=blend_xfo.blend_in
    )

    joints[-1].transform.connect(blend_xfo.transform_out)

    return spline_ik


# curve rig ------------------------------------------------------------------------------------------------------------

def create_joints_on_curve(curve, n=0, name=None, mode=0):
    """
    create joints along the given curve (not oriented)

    :param curve: curve transform
    :param n: number of bones (2 between each cvs if not specified)
    :param name:
    :param mode: bone length distribution, 0 for parametric, 1 for cvs, 2 for equal
    :return:
    """
    if not isinstance(curve, kl.SplineCurve):
        raise RuntimeError('not a curve')

    spline = curve.spline_in.get_value()
    cps = spline.get_control_points()
    ncv = len(cps)
    if n == 0:
        n = 2 * (ncv - 1)

    if not name:
        name = f'j_{curve.get_name()}'

    if isinstance(mode, str):
        mode = {'parametric': 0, 'cvs': 1, 'equal': 2}[mode]

    _garbage = []

    # cvs mode
    if mode == 1:
        uu = kl.Node(curve, 'uu')
        add_plug(uu, 'input', float)
        add_plug(uu, 'output', float)
        _garbage.append(uu)

        for i in range(ncv):
            v = float(i) / (ncv - 1)
            u = get_closest_point_on_curve(curve, cps[i], parametric=True, local=True)
            if i == ncv - 1:  # closest point on curve bug
                u = 1.0  # spline.get_max_u()?
            connect_driven_curve(uu.input, uu.output, {v: u})

    # probe
    poc = kl.PointOnSplineCurve(curve, 'poc')  # TODO: avoid using a temp node
    poc.spline_in.connect(curve.spline_in)
    poc.spline_mesh_in.connect(curve.spline_mesh_out)
    poc.geom_world_transform_in.connect(curve.world_transform)
    _garbage += [poc]

    # motion path mode
    if mode == 2:
        poc.length_in.connect(curve.length_out)

    # build joints
    joints = []
    for i in range(n + 1):

        # parametric based
        u = float(i) / n
        poc.u_in.set_value(u)

        # modes
        if mode == 1:
            uu.input.set_value(float(i) / n)
            u = uu.output.get_value()
            poc.u_in.set_value(u)
        elif mode == 2:
            poc.length_ratio_in.set_value(u)

        # create joint
        pos = poc.transform_out.get_value().translation()
        xfo = M44f(pos, V3f(0, 0, 0), V3f(1, 1, 1), Euler.XYZ)

        _name = name
        if '{i}' not in name:
            _name += '{i}'

        j = kl.Joint(find_root(), _name.format(i=i + 1))
        j.set_world_transform(xfo)
        if i > 0:
            j.reparent(joints[-1])
        joints.append(j)

    # exit
    for _ in _garbage:
        _.remove_from_parent()
    return joints


def create_extract_vector_from_transform(node, axe, world_matrix=True, parent_matrix_obj=None, output=None):
    v_base = axe
    if not isinstance(axe, V3f):
        if axe in (1, 'x', 'X'):
            v_base = V3f(1, 0, 0)
        elif axe in (2, 'y', 'Y'):
            v_base = V3f(0, 1, 0)
        elif axe in (3, 'z', 'Z'):
            v_base = V3f(1, 0, 1)
        elif axe in (-1, '-x', '-X'):
            v_base = V3f(-1, 0, 0)
        elif axe in (-2, '-y', '-Y'):
            v_base = V3f(0, -1, 0)
        elif axe in (-3, '-z', '-Z'):
            v_base = V3f(1, 0, -1)

    mult_dir = kl.MultDir(node, '_mult_dir')
    mult_dir.rotate_only_in.set_value(True)
    mult_dir.dir_in.set_value(v_base)

    # get matrix
    if world_matrix:
        matrix_out = node.world_transform
    else:
        matrix_out = node.transform

    # local matrix?
    if world_matrix and parent_matrix_obj:
        im = kl.InverseM44f(node, '_im#')
        im.input[0].connect(parent_matrix_obj.world_transform)

        mm = kl.MultM44f(node, '_mmx', 2)
        mm.input[0].connect(matrix_out)
        mm.input[1].connect(im.output)

        matrix_out = mm.output

    # extract vector from matrix
    mult_dir.matrix_in.connect(matrix_out)

    if output:
        output.connect(mult_dir.dir_out)

    return mult_dir.dir_out


def create_angle_between(vector1, vector2, output=None):
    normalize1 = kl.Normalize(vector1.get_node(), '_normalize1')
    normalize2 = kl.Normalize(vector2.get_node(), '_normalize2')

    normalize1.input.connect(vector1)
    normalize2.input.connect(vector2)

    # dot
    dot_product = kl.Dot(vector1.get_node(), '_dot')
    dot_product.input1.connect(normalize1.output)
    dot_product.input2.connect(normalize2.output)

    # acos
    acos = kl.Acos(vector1.get_node(), '_acos')
    acos.input.connect(dot_product.output)

    if output:
        output.connect(acos.output)

    return acos.output


def compare_transform(xfo1, xfo2, decimals=4):
    for i in range(4):
        for j in range(4):
            v0 = round(xfo1.get(i, j), decimals)
            v1 = round(xfo2.get(i, j), decimals)
            if v0 != v1:
                return False
    return True


# vdag -----------------------------------------------------------------------------------------------------------------

def set_virtual_parent(node, parent):
    if parent == node:
        return

    # connect child
    if not node.get_dynamic_plug('gem_dag_children'):
        add_plug(node, 'gem_dag_children', str, array=True)
    if not parent.get_dynamic_plug('gem_dag_children'):
        add_plug(parent, 'gem_dag_children', str, array=True)

    plug = parent.gem_dag_children
    i = get_next_available(plug)
    plug[i].connect(node.gem_id)

    # connect parent
    if not node.get_dynamic_plug('gem_dag_parents'):
        add_plug(node, 'gem_dag_parents', str, array=True)
    if not parent.get_dynamic_plug('gem_dag_parents'):
        add_plug(parent, 'gem_dag_parents', str, array=True)

    plug = parent.gem_dag_parents
    i = get_next_available(plug)
    plug[i].connect(parent.gem_id)
