# coding: utf-8

import math

import meta_nodal_py as kl
from meta_nodal_py.Imath import M44f
from tang_core.anim import set_animated_plug_value

from mikan.core.logger import create_logger
from mikan.tangerine.lib.commands import *

__all__ = ['anim_match_space', 'anim_match_FK', 'anim_match_IK']

log = create_logger()


def anim_match_space(node, space_id):
    if isinstance(node, str):
        node = find_path(node)
        if not node:
            return

    with find_doc().modify("Space match") as modifier:
        current_frame = modifier.document.current_frame

        ctrl = node.ui.get_outputs()[0].get_node()

        n = node.targets.get_value()
        plugs = []
        for i in range(n):
            plug = node.get_dynamic_plug(f'plug{i}').get_input()
            plugs.append(plug)

        wm_ctrl = ctrl.world_transform.get_value(current_frame)

        for plug in plugs:
            if plug:
                set_animated_plug_value(plug, 0.0, modifier)

        if plugs[space_id]:
            set_animated_plug_value(plugs[space_id], 1.0, modifier)

        wim = ctrl.parent_world_transform.get_value(current_frame).inverse()
        srt = ctrl.find('transform')
        xfo = wm_ctrl * wim
        t = xfo.translation()
        ro = srt.rotate_order.get_value(current_frame)
        r = xfo.rotation(ro)

        if isinstance(srt, kl.SRTToJointTransform):
            joro = srt.joint_orient_rotate_order.get_value()
            jo = srt.joint_orient_rotate.get_value()

            _jo = M44f().setRotation(jo, joro)
            _r = M44f().setRotation(r, ro)
            xfo = _r * _jo.inverse()
            r = xfo.rotation(ro)

        srt_plugs = [ctrl.get_dynamic_plug(plug_name) for plug_name in ('tx', 'ty', 'tz', 'rx', 'ry', 'rz')]
        srt_values = [t.x, t.y, t.z, r.x, r.y, r.z]

        for plug, value in zip(srt_plugs, srt_values):
            if plug:
                set_animated_plug_value(plug, value, modifier)


def anim_match_FK(node):
    if isinstance(node, str):
        node = find_path(node)
        if not node:
            return

    with find_doc().modify("FK match") as modifier:
        current_frame = modifier.document.current_frame

        xfos = []
        srts = []
        switch = node.switch.get_input()

        plug_fk = node.fk
        _vector = node.find('fk')  # legacy
        if _vector:
            plug_fk = _vector.input

        fks = [plug_fk[i].get_input().get_node() for i in range(plug_fk.get_size()) if plug_fk[i].get_input()]
        for c in fks:
            srt = c.find('transform')
            srts.append(srt)
            xfo = c.world_transform.get_value(current_frame)
            xfos.append(xfo)

        set_animated_plug_value(switch, 0.0, modifier)

        for xfo, srt, fk in zip(xfos, srts, fks):
            wim = fk.parent_world_transform.get_value(current_frame).inverse()
            xfo = xfo * wim

            ro = srt.rotate_order.get_value(current_frame)
            r = xfo.rotation(ro)

            if isinstance(srt, kl.SRTToJointTransform):
                joro = srt.joint_orient_rotate_order.get_value()
                jo = srt.joint_orient_rotate.get_value()

                _jo = M44f().setRotation(jo, joro)
                _r = M44f().setRotation(r, ro)
                xfo = _r * _jo.inverse()
                r = xfo.rotation(ro)

            srt_plugs = [fk.rx, fk.ry, fk.rz]
            srt_values = [r.x, r.y, r.z]

            for plug, value in zip(srt_plugs, srt_values):
                set_animated_plug_value(plug, value, modifier)


def anim_match_IK(node):
    if isinstance(node, str):
        node = find_path(node)
        if not node:
            return

    with find_doc().modify("IK match") as modifier:
        frame = modifier.document.current_frame

        xfos = []
        srts = []
        switch = node.switch.get_input()
        twist = node.twist.get_input()

        plug_fk = node.fk
        _vector = node.find('fk')  # legacy
        if _vector:
            plug_fk = _vector.input

        fks = [plug_fk[i].get_input().get_node() for i in range(plug_fk.get_size()) if plug_fk[i].get_input()]
        for c in fks:
            srt = c.find('transform')
            srts.append(srt)
            xfo = c.world_transform.get_value(frame)
            xfos.append(xfo)

        ik = node.ik.get_input().get_node()

        # match effector
        xfo = fks[-1].world_transform.get_value(frame)

        wim = ik.parent_world_transform.get_value(frame).inverse()
        srt = ik.find('transform')
        xfo = xfo * wim
        t = xfo.translation()
        ro = srt.rotate_order.get_value()
        r = xfo.rotation(ro)

        if isinstance(srt, kl.SRTToJointTransform):
            joro = srt.joint_orient_rotate_order.get_value()
            jo = srt.joint_orient_rotate.get_value()

            _jo = M44f().setRotation(jo, joro)
            _r = M44f().setRotation(r, ro)
            xfo = _r * _jo.inverse()
            r = xfo.rotation(ro)

        srt_plugs = [ik.tx, ik.ty, ik.tz, ik.rx, ik.ry, ik.rz]
        srt_values = [t.x, t.y, t.z, r.x, r.y, r.z]

        for plug, value in zip(srt_plugs, srt_values):
            set_animated_plug_value(plug, value, modifier)
        set_animated_plug_value(twist, 0.0, modifier)

        # match twist
        u0 = fks[0].world_transform.get_value(frame).translation()
        u1 = fks[-1].world_transform.get_value(frame).translation()
        v0 = fks[1].world_transform.get_value(frame).translation()

        # important to make set_animated_plug_value dirtification
        # and make later get_value() works
        modifier.renew_invalidation_token()
        set_animated_plug_value(switch, 1.0, modifier)

        v1 = fks[1].world_transform.get_value(frame).translation()

        w = u1 - u0
        n0 = w.cross(v0 - u0)
        n1 = w.cross(v1 - u0)
        n = n0.length() * n1.length()

        if n == 0:
            angle = 0
        else:
            cos = n0.dot(n1) / n
            if cos > 1:
                cos = 1
            elif cos < -1:
                cos = -1
            angle = math.acos(cos)
            angle = 180 * angle / math.pi

            sign = n0.cross(n1).dot(w)
            if sign < 0:
                angle *= -1
            angle *= node.twist_factor.get_value(frame)

        modifier.renew_invalidation_token()
        set_animated_plug_value(twist, angle, modifier)
