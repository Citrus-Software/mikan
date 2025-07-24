# coding: utf-8

from itertools import chain

import maya.cmds as mc
import mikan.maya.cmdx as mx

from mikan.core.lib.rbf import RBF
from mikan.core.logger import create_logger
from mikan.maya.lib.geometry import Mesh

log = create_logger()


def retarget_template(roots, msh_src=None, msh_dst=None, do_shapes=True):
    # build rbf
    msh_src_list = [msh_src] if not isinstance(msh_src, (list, tuple)) else msh_src
    msh_dst_list = [msh_dst] if not isinstance(msh_dst, (list, tuple)) else msh_dst

    src_points = []
    for msh_src in msh_src_list:
        src_points += Mesh(msh_src).get_points(space=mx.sWorld)

    dst_points = []
    for msh_dst in msh_dst_list:
        dst_points += Mesh(msh_dst).get_points(space=mx.sWorld)

    src_points = [mx.Vector(p) for p in src_points]
    dst_points = [mx.Vector(p) for p in dst_points]
    delta_points = [d - s for (s, d) in zip(src_points, dst_points)]

    rbf_coef = RBF.get_coefficients(src_points, src_points, delta_points, radius=1, kernel_mode=0)

    # build retarget commands
    if not isinstance(roots, (list, tuple)):
        roots = [roots]

    cmds = []

    for root in roots:
        if not isinstance(root, mx.Node):
            root = mx.encode(str(root))

        for node in chain([root], root.descendents()):
            if node.name(namespace=False).startswith('_') or '__' in node.path():
                continue
            if node.is_a(mx.kConstraint):
                continue
            if not node.is_a(mx.kTransform):
                continue

            shape = node.shape()
            if shape and shape.is_a(mx.tNurbsCurve):
                if not do_shapes:
                    continue
                xfo = node['wm'][0].as_matrix()
                p = mx.Vector(list(xfo)[12:15])
                k = 0.2
                x = mx.Vector((k, 0, 0)) * xfo
                y = mx.Vector((0, k, 0)) * xfo
                z = mx.Vector((0, 0, k)) * xfo
                points = [p + x, p - x, p + y, p - y, p + z, p - z]

                output = RBF.evaluate(src_points, points, rbf_coef, radius=1, kernel_mode=0)
                output = [mx.Vector(o) for o in output]
                for i in range(len(points)):
                    points[i] += output[i]

                xfo = [0] * 16
                xfo[-1] = 1
                p = (points[0] + points[1] + points[2] + points[3] + points[4] + points[5]) / 6

                xfo[0:3] = (points[0] - p) / k
                xfo[4:7] = (points[2] - p) / k
                xfo[8:11] = (points[4] - p) / k
                xfo[12:15] = p
                xfo = mx.Matrix4(xfo)

                cmd = ('xfo', node, xfo)

            else:
                point = node['wm'][0].as_transform().translation()
                output = RBF.evaluate(src_points, [point], rbf_coef, radius=1, kernel_mode=0)
                point = mx.Vector(point) + mx.Vector(output[0])
                cmd = ('point', node, point)

            cmds.append(cmd)

    # execute retarget commands
    for cmd, node, data in cmds:
        if cmd == 'point':
            mc.move(data[0], data[1], data[2], str(node), ws=1)
        elif cmd == 'xfo':
            try:
                r = node['r'].read()
                pim = node['pim'][0].as_matrix()
                mc.xform(str(node), m=data * pim)
                node['sh'] = [0, 0, 0]
                node['r'] = r
            except:
                pass
