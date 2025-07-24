# coding: utf-8

import maya.cmds as mc
import mikan.maya.cmdx as mx

for node in mx.ls(sl=1, type='transform'):
    mc.select(cl=1)

    shp = node.shape()
    if not shp.is_a(mx.tNurbsCurve):
        continue

    name = node.name().split('_', 1)[-1]

    joints = []
    for i, cv in enumerate(mc.ls('{}.cv[*]'.format(node), fl=1)):
        with mx.DagModifier() as md:
            j = md.create_node(mx.tJoint, name='loc_' + name + '_' + str(i + 1))
        j['t'] = mc.xform(cv, q=True, t=True, ws=True)
        joints.append(j)

    for i, j in enumerate(joints[1:]):
        mc.parent(str(j), str(joints[i]))
