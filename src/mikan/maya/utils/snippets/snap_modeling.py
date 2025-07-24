# coding: utf-8

import maya.cmds as mc
from mikan.maya import cmdx as mx

from mikan.maya.lib.nurbs import get_closest_point_on_curve

cps = []
nurbs = []

for obj in mc.ls(sl=1, fl=1):
    if '.' in obj:
        cps.append(obj)
    else:
        node = mx.encode(obj)
        shape = node.shape(type=mx.tNurbsCurve)
        if shape:
            nurbs.append(node)

for vtx in cps:
    pos = mc.xform(vtx, q=1, t=1, ws=1)
    pos = mx.Vector(pos)

    closest = None
    d = float('inf')
    snap = None

    for cv in nurbs:
        p = get_closest_point_on_curve(cv, pos)
        dp = (p - pos).length()
        if dp < d:
            closest = cv
            d = dp
            snap = p

    mc.xform(vtx, ws=1, t=snap)
