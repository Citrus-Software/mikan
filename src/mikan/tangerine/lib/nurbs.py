# coding: utf-8

import math

import meta_nodal_py as kl
from meta_nodal_py.Imath import V3f, M44f, Euler

from mikan.vendor.geomdl import BSpline
from mikan.vendor.geomdl.fitting import approximate_curve
from mikan.vendor.geomdl.utilities import generate_knot_vector
from mikan.vendor.geomdl.operations import split_curve, length_curve
from mikan.core.abstract.deformer import WeightMap

from mikan.tangerine.lib.commands import copy_transform

from mikan.core.logger import create_logger

__all__ = [
    'create_path', 'get_closest_point_on_curve',
    'get_curve_length', 'rebuild_curve', 'create_curve_weightmaps'
]

log = create_logger()


def create_path(nodes, d=1, periodic=False, parent=None):
    from mikan.tangerine.core import Shape, Deformer

    if not isinstance(nodes, list):
        raise ValueError('not a point list')

    geo = kl.SceneGraphNode(parent, 'path')
    shp = kl.SplineCurve(geo, 'shape')
    Shape.set_shape_ghost(shp)
    Shape.set_shape_color(shp, 'gray')

    # geometry
    points = []
    for node in nodes:
        xfo = node.world_transform.get_value()
        points.append(xfo.translation())

    if periodic:
        points += points[:d]

    xfo = geo.world_transform.get_value().invert()
    for i, cp in enumerate(points):
        xcp = M44f(cp, V3f(0, 0, 0), V3f(1, 1, 1), Euler.Default)
        points[i] = (xcp * xfo).translation()

    knots = generate_knot_vector(d, len(points))
    if periodic or d == 1:
        knots = list(range(-d, len(knots) - d))
    weights = [1] * len(points)

    data = kl.Spline(points, knots, weights, periodic)
    shp.spline_in.set_value(data)

    shp.sampling_in.set_value((len(points) + 1) * (d ** 2))
    shp.world_transform.connect(geo.world_transform)

    # deform
    infs = {}
    for node in nodes:
        if node not in infs:
            infs[len(infs)] = node
    inv_infs = {v: k for k, v in infs.items()}

    maps = {}
    for inf in infs:
        maps[inf] = [0.0] * len(points)
    for i, node in enumerate(nodes):
        maps[inv_infs[node]][i] = 1.0

    for i in maps:
        maps[i] = WeightMap(maps[i])

    bpms = {}
    for inf in infs:
        bpm = kl.SceneGraphNode(geo, 'bpm_' + infs[inf].get_name())
        copy_transform(infs[inf], bpm)
        bpms[inf] = bpm

    for inf in inv_infs:
        if not isinstance(inf, kl.Joint):
            j = kl.Joint(inf, 'cvj_' + inf.get_name())
            infs[inv_infs[inf]] = j

    skin_data = {
        'deformer': 'skin',
        'transform': geo,
        'data': {
            'infs': infs,
            'maps': maps,
            'bind_pose': bpms,
        }
    }
    skin_dfm = Deformer(**skin_data)
    skin_dfm.build()
    skin_fk = skin_dfm.node
    skin_fk.geom_world_transform.connect(geo.world_transform)

    # exit
    return geo


def get_closest_point_on_curve(curve, loc, parametric=False, local=False, length=False):
    if isinstance(loc, kl.SceneGraphNode):
        loc = loc.world_transform.get_value()
        # todo: local xfo?
    elif type(loc) in (list, tuple):
        loc = M44f(V3f(*loc), V3f(0, 0, 0), V3f(1, 1, 1), Euler.XYZ)
    elif isinstance(loc, V3f):
        loc = M44f(loc, V3f(0, 0, 0), V3f(1, 1, 1), Euler.XYZ)

    closest = kl.Closest(curve, 'closest')
    closest.legacy.set_value(2)
    closest.spline_in.connect(curve.spline_in)
    closest.spline_mesh_in.connect(curve.spline_mesh_out)
    closest.transform_in.set_value(loc)
    closest.sampling_in.connect(curve.sampling_in)
    closest.length_in.connect(curve.length_out)    
    if not local:
        closest.geom_world_transform_in.connect(curve.world_transform)

    if parametric:
        u = closest.u_out.get_value()
        closest.remove_from_parent()
        return u
    if length:
        u = closest.u_out.get_value()
        closest.remove_from_parent()
        d = get_curve_length(curve)
        dp = get_curve_length(curve, u)
        return dp / d

    pos = closest.transform_out.get_value().translation()
    xfo = M44f(pos, V3f(0, 0, 0), V3f(1, 1, 1), Euler.XYZ)

    closest.remove_from_parent()
    return xfo


def get_curve_length(curve, u=None):
    if u is None:
        return curve.length_out.get_value()
    if u == 0:
        return 0

    spline = curve.spline_in.get_value()
    u /= spline.get_max_u()
    if u >= 1:
        return curve.length_out.get_value()

    degree = spline.get_degree()
    cps = spline.get_control_points()
    cps = [(cp[0], cp[1], cp[2]) for cp in cps]
    knots = spline.get_knots()

    cv = BSpline.Curve()
    cv.degree = degree
    cv.ctrlpts = cps
    cv.knotvector = knots

    try:
        split = split_curve(cv, u)
        d = length_curve(split[0])
    except:
        if u < 0.5:
            d = 0
        else:
            d = curve.length_out.get_value()
        log.warning(f'/!\\ failed to compute correct arc length for curve {curve} at u={u}')
    return d


def rebuild_curve(curve, degree=3, num_cvs=None, legacy=0):
    if not isinstance(curve, kl.SplineCurve):
        raise RuntimeError('not a curve')

    poc = kl.PointOnSplineCurve(curve, '_poc')
    poc.spline_mesh_in.connect(curve.spline_mesh_out)
    poc.spline_in.connect(curve.spline_in)
    # poc.geom_world_transform_in.connect(curve.world_transform)
    poc.length_in.connect(curve.length_out)

    spline = curve.spline_in.get_value()
    cps = spline.get_control_points()
    _degree = spline.get_degree()
    sampling = (len(cps) + 1) * (_degree ** 2)
    sampling *= 10

    plot = []
    for i in range(sampling):
        d = i / (sampling - 1)
        poc.length_ratio_in.set_value(d)
        pos = poc.transform_out.get_value().translation()
        plot.append([pos.x, pos.y, pos.z])

    # TODO: voir avec seb pourquoi le plot arrive pas jusqu'au dernier cv
    if spline.get_wrap() == 0:
        plot.append([cps[-1].x, cps[-1].y, cps[-1].z])

    if num_cvs is None:
        num_cvs = len(cps) - 1

    cv = approximate_curve(plot, degree, ctrlpts_size=num_cvs)
    cps = [V3f(*cp) for cp in cv.ctrlpts]

    knots = generate_knot_vector(degree, len(cps))
    weights = [1] * len(cps)

    spline = kl.Spline(cps, knots, weights, False)
    curve.spline_in.set_value(spline)

    # exit
    poc.remove_from_parent()


def create_curve_weightmaps(curve, infs, method='quadratic', threshold=0.01):
    if not isinstance(curve, kl.SplineCurve):
        raise RuntimeError('not a curve')
    if len(infs) < 2:
        raise RuntimeError('must have at least 2 influences')

    # epsilon is the distance max between cv and joint to put weight to 1
    epsilon = .001

    spline = curve.spline_in.get_value()
    cv_count = spline.get_control_points_count()
    form = spline.get_wrap()
    # TODO: remove wrapped cps if wrapped

    # get U from all joints
    u_infs = []
    for inf in infs:
        u = get_closest_point_on_curve(curve, inf, parametric=True)
        u_infs.append((inf, round(u, 6)))

    u_infs = sorted(u_infs, key=lambda x: x[1], reverse=False)

    # compute distance between joints from their U
    u_lens = []
    for i in range(len(u_infs)):
        if i == 0:
            u_lens.append(abs(u_infs[i + 1][1] - u_infs[i][1]))
        else:
            u_lens.append(abs(u_infs[i][1] - u_infs[i - 1][1]))

    # get U from all cvs of the curve
    u_cvs = []
    for i in range(cv_count):
        cv_pos = spline.get_control_points()[i]
        result = get_closest_point_on_curve(curve, cv_pos, parametric=True, local=True)
        if result is not None:
            u = result
            u_cvs.append(round(u, 6))
        else:
            raise RuntimeError(f'unable to retreive u for cv {i}')

    maps = {}
    for inf in infs:
        maps[inf] = WeightMap([0] * cv_count)

    # Store u for joints closed to cv
    for i, u_cv in enumerate(u_cvs):
        inf_dist_u = []
        for j, (inf, u_inf) in enumerate(u_infs):
            d_falloff = u_lens[j]
            if form == 0:  # open
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
                    min_value = 0  # u_min
                    max_value = 1  # u_max (toujours 1 avec le closest, à checker)

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

        # Sum all the U of joints that are closed to cvs
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
