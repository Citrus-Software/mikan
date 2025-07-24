# coding: utf-8

import math
from six.moves import range

import maya.cmds as mc
from mikan.maya import cmdx as mx

__all__ = ['anim_match_space', 'anim_match_FK', 'anim_match_IK']


def anim_match_space(node, space_id):
    ctrl = node['msg'].output(type=mx.kTransform)
    with mx.DagModifier() as md:
        dummy_parent = md.create_node(mx.tTransform, parent=ctrl.parent())
        dummy = md.create_node(mx.tJoint, parent=dummy_parent)
        dummy['ro'] = ctrl['ro']
        dummy_lock = md.create_node(mx.tTransform)

    mx.delete(*mx.encode_cmd(mc.parentConstraint, ctrl, dummy_lock))
    mx.cmd(mc.parentConstraint, dummy_lock, dummy)

    plugs = {}
    for i in node['targets'].array_indices:
        plug = node['targets'][i]['plug'].input(plug=True)
        if plug is not None:
            plugs[i] = plug

    with mx.DGModifier() as md:
        for i in plugs:
            if i == space_id:
                md.set_attr(plugs[i], 1)
            else:
                md.set_attr(plugs[i], 0)

    if ctrl.is_a(mx.tJoint):
        dummy['jo'] = ctrl['jo']

    cnst = node['constraint'].input()

    xfo = 'tr'
    if cnst.is_a(mx.tPointConstraint):
        xfo = 't'
    elif cnst.is_a(mx.tOrientConstraint):
        xfo = 'r'

    with mx.DagModifier() as md:
        for x in xfo:
            v = dummy[x].read()
            for i in range(3):
                xfo_plug = ctrl[x + 'xyz'[i]]
                try:
                    md.set_attr(xfo_plug, v[i])
                except:
                    pass

    mx.delete(dummy_parent, dummy_lock)


def anim_match_FK(node):
    switch = node['switch'].input(plug=True)

    values = {}
    for i in node['fk'].array_indices:
        c = node['fk'][i].input()
        values[c] = c['r'].read()

    with mx.DGModifier() as md:
        md.set_attr(switch, 0)
        for c in values:
            md.set_attr(c['r'], values[c])


def anim_match_IK(node):
    switch = node['switch'].input(plug=True)
    twist = node['twist'].input(plug=True)

    c_ik = node['ik'].input()
    c_fk = []
    for i in node['fk'].array_indices:
        c_fk.append(node['fk'][i].input())

    #  get values
    u0 = c_fk[0]['wm'][0].as_transform().translation()
    u1 = c_fk[-1]['wm'][0].as_transform().translation()
    v0 = c_fk[1]['wm'][0].as_transform().translation()

    # match effector
    xfo = c_fk[-1]['wm'][0].as_transform()
    pim = c_ik['pim'][0].as_transform()
    xfo = xfo * pim

    mc.xform(str(c_ik), m=xfo.as_matrix())

    # match twist
    with mx.DGModifier() as md:
        md.set_attr(twist, 0)
        md.set_attr(switch, 1)

    v1 = c_fk[1]['wm'][0].as_transform().translation()

    w = u1 - u0
    n0 = w ^ (v0 - u0)
    n1 = w ^ (v1 - u0)
    n = n0.length() * n1.length()

    if n == 0:
        angle = 0
    else:
        cos = (n0 * n1) / n
        if cos > 1:
            cos = 1
        elif cos < -1:
            cos = -1
        angle = math.acos(cos)
        angle = 180 * angle / math.pi

        sign = (n0 ^ n1) * w
        if sign < 0:
            angle *= -1
        angle *= node['twist_factor'].read()

    with mx.DagModifier() as md:
        md.set_attr(twist, angle)
