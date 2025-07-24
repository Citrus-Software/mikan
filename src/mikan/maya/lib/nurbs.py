# coding: utf-8

import math
from six.moves import range

import maya.api.OpenMaya as om
import maya.cmds as mc
from mikan.maya import cmdx as mx

from mikan.core.utils import flatten_list
from mikan.core.abstract import WeightMap

__all__ = [
    'create_path', 'get_closest_point_on_curve',
    'get_curve_length', 'get_curve_length_from_param',
    'create_curve_weightmaps',
    'uniform_edges', 'smooth_edges'
]


def create_path(*args, **kw):
    """ crée une curve reliant les nodes donnés entre eux """

    if not args:
        locs = mx.ls(sl=1, type='transform')
    else:
        locs = []
        for n in flatten_list(args):
            if not isinstance(n, mx.Node):
                n = mx.encode(str(n))
            if n.is_a((mx.tTransform, mx.tJoint)):
                locs.append(n)

    d = kw.get('d')
    if not d:
        d = 1

    points = [(x, 0, 0) for x in range(len(locs))]
    if not bool(kw.get('periodic')):
        cv = mc.curve(n='cv_path#', d=d, p=points)
    else:
        points = points + points[0:d]
        knots = [x - d + 1 for x in range(len(points) + d - 1)]
        cv = mc.curve(n='cv_path#', d=d, per=True, p=points, k=knots)

        locs = locs + locs[0:d]
    cv = mx.encode(cv)

    dmxs = dict()
    for i in range(len(locs)):
        dmx = dmxs.get(str(locs[i]))
        if not dmx:
            with mx.DGModifier() as md:
                dmx = md.create_node(mx.tDecomposeMatrix, name='_dmx#')
                mmx = md.create_node(mx.tMultMatrix, name='_mmx#')
            locs[i]['wm'][0] >> mmx['i'][0]
            cv['pim'][0] >> mmx['i'][1]
            mmx['o'] >> dmx['imat']
            dmxs[str(locs[i])] = dmx
        dmx['ot'] >> cv.shape()['cp'][i]

    cv['template'] = True
    return cv


def get_closest_point_on_curve(curve, point, parameter=False, length=False):
    if not isinstance(curve, mx.Node):
        curve = mx.encode(str(curve))

    if isinstance(point, mx.Node) and point.is_a(mx.kTransform):
        point = point['wm'][0].as_transform().translation()
    else:
        point = mx.Vector(point)
    point = om.MPoint(point[0], point[1], point[2])

    if curve.is_a(mx.tNurbsCurve):
        shape = curve
    else:
        shape = curve.shape()
    fn = om.MFnNurbsCurve(shape.dag_path())

    p, u = fn.closestPoint(point, space=mx.sWorld)
    if parameter:
        return u
    if length:
        d = get_curve_length(curve)
        dp = get_curve_length_from_param(curve, u)
        return dp / d
    return mx.Vector(p)


def get_curve_length(curve):
    if not isinstance(curve, mx.Node):
        curve = mx.encode(str(curve))

    if curve.is_a(mx.tNurbsCurve):
        shape = curve
    else:
        shape = curve.shape()

    fn = om.MFnNurbsCurve(shape.object())
    return fn.length()


def get_curve_length_from_param(curve, u):
    if not isinstance(curve, mx.Node):
        curve = mx.encode(str(curve))

    if curve.is_a(mx.tNurbsCurve):
        shape = curve
    else:
        shape = curve.shape()

    fn = om.MFnNurbsCurve(shape.object())
    return fn.findLengthFromParam(u)


def create_curve_weightmaps(curve, infs, method='quadratic', threshold=0.0001):
    """
    generate curve weight maps (ripped from Olivier Georges)
    :param str curve: curve node
    :param list infs: influences of the desired binding
    :param str method: linear or quadratic d_falloff (linear adapted for degree one curves, quadratic for curve with a higher continuity)
    :param float threshold: weights under this threshold are considered null
    :return: weightmaps
    """
    if not isinstance(curve, mx.Node):
        curve = mx.encode(str(curve))

    _infs = []
    for inf in infs:
        if not isinstance(inf, mx.Node):
            inf = mx.encode(str(inf))
        if inf.is_a(mx.kTransform):
            _infs.append(inf)
    infs = _infs

    epsilon = .001

    shape = None
    if curve.is_a(mx.tNurbsCurve):
        shape = curve
    elif curve.is_a(mx.tTransform):
        shape = curve.shape()
    if not shape.is_a(mx.tNurbsCurve):
        raise RuntimeError('not a curve')

    if len(infs) < 2:
        raise RuntimeError('must have at least 2 influences')

    fn = om.MFnNurbsCurve(shape.dag_path())
    n = fn.numCVs
    if fn.form == fn.kPeriodic:
        n -= fn.degree

    u_infs = []
    for inf in infs:
        pos = inf.translation(mx.sWorld)
        u = get_closest_point_on_curve(shape, pos, parameter=True)
        u_infs.append((inf, round(u, 6)))

    u_infs = sorted(u_infs, key=lambda x: x[1], reverse=False)

    u_lens = []
    for i in range(len(u_infs)):
        if i == 0:
            u_lens.append(abs(u_infs[i + 1][1] - u_infs[i][1]))
        else:
            u_lens.append(abs(u_infs[i][1] - u_infs[i - 1][1]))

    cvs_pos = [mx.Vector(cv) for cv in fn.cvPositions(space=mx.sWorld)]

    u_cvs = []
    for i in range(n):
        u = get_closest_point_on_curve(shape, cvs_pos[i], parameter=True)
        if u is not None:
            u_cvs.append(round(u, 6))
        else:
            raise RuntimeError('unable to retreive u for {}.cv[{}]'.format(curve, i))

    maps = {}
    for inf in infs:
        maps[inf] = WeightMap([0] * n)

    for i, u_cv in enumerate(u_cvs):
        inf_dist_u = []
        for j, (inf, u_inf) in enumerate(u_infs):
            d_falloff = u_lens[j]
            if fn.form == om.MFnNurbsCurve.kOpen:  # open
                if u_cv > u_inf:  # for cv greater than u_inf the d_falloff of the next influence is used if this d_falloff is greater than the current one
                    if j < (len(u_infs) - 1):
                        if u_lens[j + 1] > d_falloff:
                            d_falloff = u_lens[j + 1]
                    else:
                        inf_dist_u.append([inf, .0, u_inf])  # for the last influence on an open curve, cv greater than u_inf are weighted at 1.0 to the last inf
                elif u_cv < u_inf:  # for the first influence on an open curve, cv least than u_inf are weighted at 1.0 to the first inf
                    if j == 0:
                        inf_dist_u.append([inf, .0, u_inf])

            else:  # periodic/closed
                u_inf_first = u_inf
                u_inf_last = u_infs[-1][1]
                # We need to compute the d_falloff of the last influence to check if the current cv is influenced, and in this case, add the last influence
                # the case is valid only for cv between these two influences -> (u_cv <= u_inf_first or u_cv >= u_inf_last)
                if j == 0 and (u_cv <= u_inf_first or u_cv >= u_inf_last):
                    min_value = shape['minValue'].read()
                    max_value = shape['maxValue'].read()

                    # Compute the d_falloff of the last influence, distance U between last inf and first inf
                    d_falloff_last = u_inf_first + ((max_value - min_value) - u_inf_last)
                    if d_falloff_last > d_falloff:
                        d_falloff = d_falloff_last

                    # Calculate if the cv is influenced by the last influence
                    if u_cv >= u_inf_last:
                        u_len = u_cv - u_inf_last
                    else:
                        u_len = u_cv + ((max_value - min_value) - u_inf_last)

                    if u_len <= d_falloff:
                        inf_dist_u.append([u_infs[-1][0], u_len, u_inf_last])

                    # Calculate if the cv is influenced by the first influence
                    if u_cv > u_inf_first:  # u_cv >= u_inf_first before fix for Closed
                        u_len = u_inf_first + ((max_value - min_value) - u_cv)
                    else:
                        u_len = abs(u_cv - u_inf_first)

                    if u_len <= d_falloff:
                        inf_dist_u.append([inf, u_len, u_inf_first])

                    break  # We don't need to compute the weight for the other influences

            u_len = abs(u_cv - u_inf)

            if u_len < d_falloff:
                inf_dist_u.append([inf, u_len, u_inf])

        # sort the list base on the uDistance (smallest to greatest)
        inf_dist_u = sorted(inf_dist_u, key=lambda x: x[1], reverse=False)[0:2]  # The logical way to weight a cv in the u space is that it can only be influenced by 2 joint at once

        inf_weights = []
        w_sum = 0.0
        for inf, d, u in inf_dist_u:
            if d <= epsilon:
                w = 1.0
                del inf_weights[:]
                w_sum = 1.0
                inf_weights.append([inf, w])
                break
            else:
                if method == 'quadratic':
                    w = 1.0 / math.pow(d, 2)
                elif method == 'linear':
                    w = 1.0 / d
            w_sum += w
            inf_weights.append([inf, w])

        # normalization
        for k, (inf, w) in enumerate(inf_weights):
            w = round((w / w_sum), 3)
            if w < threshold:
                w = .0
            inf_weights[k] = [inf, w]

        # write maps
        for inf, w in inf_weights:
            maps[inf][i] = w

    return [maps[inf] for inf in infs]


# -- modeling tools ----------------------------------------------------------------------------------------------------

def resolve_chains(pairs):
    adjacency = {}

    # Construire l'adjacence
    for a, b in pairs:
        if a not in adjacency:
            adjacency[a] = []
        if b not in adjacency:
            adjacency[b] = []
        adjacency[a].append(b)
        adjacency[b].append(a)

    # Trouver toutes les chaînes
    chains = []

    while adjacency:
        # Trouver un sommet de départ (un sommet avec un degré 1 si possible)
        start = None
        for node in adjacency:
            if len(adjacency[node]) == 1:
                start = node
                break

        # Si aucun sommet terminal n'est trouvé, prendre un sommet arbitraire
        if start is None:
            start = next(iter(adjacency))

        # Construire une chaîne avec une recherche en profondeur
        chain = []
        visited = set()

        def dfs(node):
            visited.add(node)
            chain.append(node)
            for neighbor in adjacency[node]:
                if neighbor not in visited:
                    dfs(neighbor)

        dfs(start)
        chains.append(chain)

        # Supprimer les nodes visités de l'adjacence
        for node in chain:
            del adjacency[node]

    return chains


def get_ordered_edge_loops_vertices(edges):
    edges = mc.ls(edges, flatten=True)
    edges = [e for e in edges if '.e[' in e]

    mesh = mx.encode(edges[0])
    fn = om.MFnMesh(mesh.dag_path())

    vtx_edges = []

    for e in edges:
        i = int(e.split('[')[-1][:-1])
        vtx_ids = fn.getEdgeVertices(i)
        vtx_edges.append(vtx_ids)

    chains = resolve_chains(vtx_edges)

    msh = edges[0].split('.')[0]
    return [[msh + '.vtx[{}]'.format(vtx) for vtx in chain] for chain in chains]


def uniform_edges(weight=1):
    # get selected edges
    selection = mc.ls(sl=True, flatten=True)
    geometries = mc.ls(sl=True, o=True)
    edges = [e for e in selection if '.e[' in e]

    # get chains
    chains = get_ordered_edge_loops_vertices(edges)

    if not chains:
        mc.warning("Sélectionnez des edges pour continuer.")
        return

    for vertices in chains:
        if len(vertices) <= 2:
            continue

        points = []
        for vtx in vertices:
            pos = mc.xform(vtx, query=True, translation=True, worldSpace=True)
            points.append(pos)

        curve = mc.curve(degree=3, editPoint=points)  # EP curve pour pas faire "fondre" la shape

        # update vertices position
        fn = om.MFnNurbsCurve(mx.encode(curve).dag_path())
        length = fn.length()
        n = len(points)

        for i in range(n):
            d = length * i / (n - 1)  # calcul de la position sur la curve
            u = fn.findParamFromLength(d)

            if 1 > weight >= 0:
                u0 = get_closest_point_on_curve(curve, points[i], parameter=True)
                u = (1 - weight) * u0 + weight * u

            pos = list(fn.getPointAtParam(u))[0:3]
            mc.xform(vertices[i], translation=pos, worldSpace=True)

        mc.delete(curve)

    mc.hilite(geometries)
    mc.selectMode(component=True)
    mc.selectType(edge=True)
    mc.select(edges)


def smooth_edges(weight=1, rate=2):
    # get selected edges
    selection = mc.ls(sl=True, flatten=True)
    geometries = mc.ls(sl=True, o=True)
    edges = [e for e in selection if '.e[' in e]

    # get chains
    chains = get_ordered_edge_loops_vertices(edges)

    if not chains:
        mc.warning("Sélectionnez des edges pour continuer.")
        return

    for vertices in chains:
        if len(vertices) <= 2:
            continue

        points = []
        for vtx in vertices:
            pos = mc.xform(vtx, query=True, translation=True, worldSpace=True)
            points.append(pos)

        spans = len(vertices) // rate

        curve = mc.curve(degree=3, editPoint=points)  # EP curve pour pas faire "fondre" la shape
        mc.rebuildCurve(curve, ch=0, rpo=1, rt=0, end=1, kr=0, kcp=0, kep=1, d=3, s=spans)

        # update vertices position
        n = len(points)

        for i in range(n):
            pos = get_closest_point_on_curve(curve, points[i])
            mc.xform(vertices[i], translation=pos, worldSpace=True)

        mc.delete(curve)

    mc.hilite(geometries)
    mc.selectMode(component=True)
    mc.selectType(edge=True)
    mc.select(edges)
