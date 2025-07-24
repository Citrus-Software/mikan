# coding: utf-8

import math
from itertools import chain
from six.moves import range
from six import string_types

import maya.api.OpenMaya as om
import maya.cmds as mc
from mikan.maya import cmdx as mx

from mikan.core.utils import flatten_list
from mikan.core.logger import create_logger
from .nurbs import get_closest_point_on_curve
from .connect import (
    connect_add, connect_mult, connect_sub, connect_expr,
    connect_driven_curve, connect_matrix, connect_blend_weighted
)

__all__ = [
    'axis_to_vector', 'get_stretch_axis',

    'duplicate_joint', 'mirror_joints', 'orient_joint', 'fix_inverse_scale',
    'create_joints_on_curve',

    'copy_plugs', 'list_future',
    'apply_transform', 'copy_transform', 'get_pivot_offset',
    'find_closest_node', 'matrix_constraint', 'find_target',

    'create_ik_handle', 'stretch_ik', 'stretch_spline_ik', 'create_blend_joint',
    'fix_orient_constraint_flip',
    'create_angle_between', 'create_extract_vector_from_transform',

    'create_cluster', 'reroot_cluster', 'transfer_nonlinear', 'add_nonlinear',

    'set_virtual_parent', 'get_virtual_parent', 'get_virtual_children', 'reorder_vdag_set', 'get_vdag_roots'
]

log = create_logger()


def axis_to_vector(axis):
    _axes = {'x': mx.Vector(1, 0, 0),
             'y': mx.Vector(0, 1, 0),
             'z': mx.Vector(0, 0, 1),
             '+x': mx.Vector(1, 0, 0),
             '+y': mx.Vector(0, 1, 0),
             '+z': mx.Vector(0, 0, 1),
             '-x': mx.Vector(-1, 0, 0),
             '-y': mx.Vector(0, -1, 0),
             '-z': mx.Vector(0, 0, -1)}
    axis = axis.lower()
    if axis in _axes:
        return mx.Vector(_axes[axis])


def get_stretch_axis(joints, bias=0.001):
    axis = None

    for j in joints[1:]:
        if not isinstance(j, mx.Node):
            j = mx.encode(str(j))
        t = j['t'].read()
        t = [abs(t[0]), abs(t[1]), abs(t[2])]
        if t[0] > t[1] and t[0] > t[2] and t[1] + t[2] < 2 * bias:
            axis = ['x', 'y', 'z']
        if t[1] > t[0] and t[1] > t[2] and t[0] + t[2] < 2 * bias:
            axis = ['y', 'x', 'z']
        if t[2] > t[1] and t[2] > t[0] and t[0] + t[1] < 2 * bias:
            axis = ['z', 'x', 'y']

    return axis




# joints -----------------------------------------------------------------------

def duplicate_joint(j, p=None, parent=None, n=None, name=None):
    if not isinstance(j, mx.Node):
        j = mx.encode(str(j))
    if not j.is_a(mx.tJoint):
        raise RuntimeError('"{}" is not a joint'.format(j))

    # args
    if p is not None:
        parent = p
    if n is not None:
        name = n

    _sl = mx.ls(sl=1)

    # duplicate
    with mx.DagModifier() as md:
        d = md.create_node(mx.tJoint, parent=j.parent(), name=name)

    for attr in ('ro', 'jo', 'ra', 's', 'r', 't', 'sh', 'radius'):
        d[attr] = j[attr]

    if parent:
        if d.parent() != parent:
            mc.parent(str(d), str(parent))

        # delete scale transform preservation
        dp = d.parent()
        if dp != parent:
            s = d['s'].read()
            mc.makeIdentity(str(dp), a=1, t=0, r=0, s=1, n=0)
            mc.parent(str(d), str(parent))
            mx.delete(dp)
            d['s'] = s

    # ensure inverse scale connection
    _p = d.parent()
    if _p and _p.is_a(mx.tJoint):
        d['inverseScale'].disconnect()
        _p['s'] >> d['inverseScale']

    # deliver
    mx.cmd(mc.select, _sl)
    return d


def mirror_joints(node, myz=True, mxy=False, mxz=False, nodes=None, _root=None, _dupe=None):
    if not isinstance(node, mx.Node):
        node = mx.encode(str(node))
    node_type = node.type_id

    if not nodes:
        nodes = []

    n = node.name(namespace=False)
    if not _root:
        n += '_dupe'
        _root = node.parent()
        _dupe = _root
    with mx.DagModifier() as md:
        d = md.create_node(node_type, parent=node, name=n)
    nodes.append(d)

    if node_type == mx.tJoint:
        d['ssc'] = node['ssc'].read()
    elif node_type == mx.tLocator:
        d['localPosition'] = node['localPosition'].as_vector() * -1
        d['localScale'] = node['localScale'].read()

    # mirror transformation
    pim = _dupe['wim'][0].as_transform()
    wm = d['wm'][0].as_transform()

    yz = 1
    xz = 1
    xy = 1
    if myz:
        yz = -1
    if mxz:
        xz = -1
    if mxy:
        xy = -1

    mc.parent(str(d), str(_dupe), r=1)

    if node_type == mx.tJoint:
        d['radius'] = node['radius']

        if _dupe.is_a(mx.tJoint):
            if node['inverseScale'].input():
                _dupe['scale'].connect(d['inverseScale'])

    if -1 in (yz, xz, xy):
        s = mx.Tm(mx.Matrix4(((yz, 0, 0, 0), (0, xz, 0, 0), (0, 0, xy, 0), (0, 0, 0, 1))))
        r = mx.Tm(mx.Matrix4(((-1, 0, 0, 0), (0, -1, 0, 0), (0, 0, -1, 0), (0, 0, 0, 1))))
        pos = _root.translation(mx.sWorld)
        p = mx.Tm(translate=pos)
        ip = mx.Tm(translate=-pos)
        m = r * wm * ip * s * p * pim

        if node_type == mx.tJoint:
            if d['ssc'].read():
                ds = mx.TransformationMatrix(scale=d['inverseScale'])
                m = mx.Tm(ds.as_matrix_inverse()) * m * ds

            d['jo'] = node['jo']

        mc.xform(str(d), m=m.as_matrix())

        if node_type == mx.tTransform:
            rp = mc.xform(str(node), q=1, pivots=1)
            rp[0] *= yz
            rp[1] *= xz
            rp[1] *= xy
            mc.xform(str(d), pivots=rp[:3])

    else:
        d['sh'] = node['sh']
        d['s'] = node['s']
        d['r'] = node['r']
        if node_type == mx.tJoint:
            d['jo'] = node['jo']
        d['t'] = node['t']
        if node_type == mx.tTransform:
            rp = mc.xform(str(node), q=1, pivots=1)
            mc.xform(str(d), pivots=rp[:3])

    # copy plugs
    for plug_name in mc.listAttr(str(node), ud=1) or []:
        plug = node[plug_name]
        cls = plug.type_class()
        if plug.is_array:
            continue
        if cls in (mx.Boolean, mx.Long, mx.Double, mx.String):
            attr = cls(plug_name)
            attr['shortName'] = plug.name(long=False)
            attr['keyable'] = plug.keyable
            attr['channelBox'] = plug.channel_box
            if cls != mx.String:
                attr['default'] = plug.default
            d.add_attr(attr)
            d[plug_name] = plug

    # # copy shapes (slow)
    # for shp in node.shapes():
    #     shp_dup = mx.Node(shp._fn.duplicate())
    #     for _shp in shp_dup.shapes():
    #         mc.parent(str(_shp), str(d), r=1, s=1)
    #     mx.delete(shp_dup)

    # recursive mirror
    for c in node.children():
        if c.type_id not in (mx.tTransform, mx.tJoint):
            continue
        mirror_joints(c, myz=myz, mxy=mxy, mxz=mxz, nodes=nodes, _root=_root, _dupe=d)

    return nodes


def orient_joint(joints, orient_last=True,
                 aim='y', aim_dir=None,
                 up='z', up_dir=(0, 0, 1), up_auto=None, up_conform=True):
    """
    orient given joints

    :param list, tuple joints: joint list to orient

    :param str aim: primary axis (x, -x, y, -y, z, -z)
    :param dt.Vector, tuple aim_dir: vector for primary axis

    :param str up: secondary axis (x, -x, y, -y, z, -z)
    :param dt.Vector, tuple up_dir: vector for secondary axis

    :param int up_auto: (overrides up_dir, up_tgt)
    - None: not used
    - 0: average of up vector found for each joint
    - 1: each up vector is recalculated for each joint
    - 2: first relevant (non null) up vector
    - 3: last relevant up vector
    :param bool up_conform: conform up vectors general direction

    """

    _joints = []
    if not joints:
        _joints = mx.ls(sl=1, et='joint')
    else:
        for j in flatten_list([joints]):
            if not isinstance(j, mx.Node):
                j = mx.encode(str(j))
            if j.is_a(mx.tJoint):
                _joints.append(j)

    joints = _joints

    aim = axis_to_vector(aim)
    up = axis_to_vector(up)
    if aim_dir:
        aim_dir = mx.Vector(aim_dir)
    if up_dir:
        up_dir = mx.Vector(up_dir)

    with mx.DagModifier() as md:
        tgt_root = md.create_node(mx.tTransform, name='_tgt_root#')
        aim_dummy = md.create_node(mx.tTransform, name='_aim_tmp#', parent=tgt_root)
        up_dummy = md.create_node(mx.tTransform, name='_up_tmp#', parent=tgt_root)
        aim_root = md.create_node(mx.tTransform, name='_aim_root#')
        dummy = md.create_node(mx.tTransform, name='_dummy#', parent=aim_root)
    _ax = mc.aimConstraint(str(aim_dummy), str(dummy), aim=aim, u=up, wuo=str(up_dummy), wut='object')

    # compute up vectors
    up_vectors = []
    if up_auto is not None:
        # get joint vectors
        j_vectors = []
        for i, j in enumerate(joints[:-1]):
            v = joints[i + 1].translation(mx.sWorld)
            v -= joints[i].translation(mx.sWorld)
            j_vectors.append(v)
        # compute up vectors from given joints
        for i, j in enumerate(j_vectors[1:]):
            v = j_vectors[i].cross(j_vectors[i + 1])
            up_vectors.append(v.normal())
        # first two joints should share their up vector
        if up_vectors:
            up_vectors = [up_vectors[0]] + up_vectors

        # conform up vectors general direction (for each and average)
        if up_conform and up_auto < 3:
            for i, j in enumerate(up_vectors[1:]):
                if up_vectors[i - 1] * up_vectors[i] < 0:  # dot
                    up_vectors[i] *= -1

    # compute orient for each joints
    for i, j in enumerate(joints):

        # get position
        _p = j.parent()
        if _p:
            wm = _p['wm'][0].as_matrix()
            mc.xform(str(aim_root), m=wm)
        copy_transform(j, aim_root, t=True)
        copy_transform(j, tgt_root, t=True)

        # get aim and up vectors
        if aim_dir:
            aim_dummy['t'] = aim_dir
        else:
            if len(joints) > 1:
                if i < len(joints) - 1:
                    _aim_tgt = joints[i + 1]
                    copy_transform(_aim_tgt, aim_dummy, t=True)
                else:
                    # keep same direction
                    pass

        up_dummy['t'] = up_dir
        if up_auto is not None:
            if up_auto == 0:
                # average
                v = mx.Vector(0, 0, 0)
                for u in up_vectors:
                    v += u
                up_dummy['t'] = v
            elif up_auto == 1:
                # each
                if i < len(up_vectors):
                    up_dummy['t'] = up_vectors[i]
                else:
                    up_dummy['t'] = up_vectors[-1]
            elif up_auto == 2:
                # first
                up_dummy['t'] = up_vectors[0]
            elif up_auto == 3:
                # last
                up_dummy['t'] = up_vectors[-1]

        # preserve children
        children = {}
        for child in j.children():
            children[child] = child['wm'][0].as_matrix()

        # set joint
        j['r'] = (0, 0, 0)
        j['ra'] = (0, 0, 0)
        j['jo'] = (0, 0, 0)
        if i > 0 and i == len(joints) - 1 and not orient_last:
            pass
        else:
            copy_transform(dummy, j, r=True)

        # finish
        for child in children:
            mc.xform(str(child), m=children[child] * child['pim'][0].as_matrix())

    # exit
    mx.delete(aim_root, tgt_root)


def create_joints_on_curve(curve, n=0, name=None, mode=0, freeze=True):
    """
    create joints along the given curve (not oriented)

    :param curve: curve transform
    :param n: number of bones (2 between each cvs if not specified)
    :param name:
    :param mode: bone length distribution, 0 for parametric, 1 for cvs, 2 for equal
    :param freeze:
    :return:
    """
    if not isinstance(curve, mx.Node):
        curve = mx.encode(str(curve))
    shp = curve.shape()
    if not shp:
        raise RuntimeError('no shape')
    elif not shp.is_a(mx.tNurbsCurve):
        raise RuntimeError('not a curve')

    fn = om.MFnNurbsCurve(shp.dag_path())
    ncv = fn.numCVs
    if fn.form == fn.kPeriodic:
        ncv -= fn.degree

    if n == 0:
        n = 2 * (ncv - 1)

    if not name:
        name = 'j_{}'.format(curve.name())

    if isinstance(mode, string_types):
        mode = {'parametric': 0, 'cvs': 1, 'equal': 2}[mode]

    _garbage = []

    # cvs mode
    if mode == 1:
        with mx.DGModifier() as md:
            uu = md.create_node(mx.tAnimCurveUU)
        _garbage.append(uu)

        cvs_pos = fn.cvPositions(space=mx.sWorld)
        for i in range(ncv):
            v = float(i) / (ncv - 1)
            _p = mx.Vector(cvs_pos[i])
            u = get_closest_point_on_curve(curve, _p, parameter=True)
            mc.setKeyframe(str(uu), v=u, f=v, itt='spline', ott='spline')

    # motion path mode
    if mode == 2:
        with mx.DGModifier() as md:
            mp = md.create_node(mx.tMotionPath)
            npc = md.create_node(mx.tNearestPointOnCurve)
        shp['local'] >> mp['geometryPath']
        shp['local'] >> npc['inputCurve']
        mp['fractionMode'] = 1
        mp['allCoordinates'] >> npc['inPosition']
        _garbage += [mp, npc]

    # build joints
    joints = []
    locs = []

    for i in range(n + 1):
        _name = name
        if '{i}' not in name:
            _name += '{i}'
        _name = _name.format(i=i + 1)

        with mx.DagModifier() as md:
            loc = md.create_node(mx.tTransform, parent=curve, name=_name + '_loc')
            md.create_node(mx.tLocator, parent=loc, name=_name + '_locShape')
        locs.append(loc)

        # parametric based
        with mx.DGModifier() as md:
            poc = md.create_node(mx.tPointOnCurveInfo, name='_poc#')
        shp['local'] >> poc['inputCurve']
        poc['position'] >> loc['translate']

        poc['top'] = True
        pr = float(i) / n
        poc['parameter'] = pr

        # modes
        if mode == 1:
            uu['input'] = float(i) / n
            u = uu['output'].read()
            poc['parameter'] = u
            poc['top'] = False
        elif mode == 2:
            v = float(i) / n
            mp['uValue'] = v
            u = npc['parameter'].read()
            poc['parameter'] = u
            poc['top'] = False

        # keep locator?
        if freeze:
            _garbage.append(loc)
        else:
            loc.add_attr(mx.Double('parameter', shortName='pr', default=poc['parameter'].read()))
            loc.add_attr(mx.Boolean('top', default=poc['top'].read()))
            loc['pr'] >> poc['parameter']
            loc['top'] >> poc['top']

        # create joint
        parent = None
        if i > 0:
            parent = joints[-1]

        with mx.DagModifier() as md:
            j = md.create_node(mx.tJoint, parent=parent, name=_name)
        joints.append(j)
        mc.pointConstraint(str(loc), str(j), n='_px#')

    # exit
    mx.delete(_garbage)

    fix_inverse_scale(joints)
    return joints


def fix_inverse_scale(*args):
    joints = []
    for n in flatten_list(args):
        if not isinstance(n, mx.Node):
            n = mx.encode(str(n))
        joints.append(n)
    joints = [n for n in joints if n.is_a(mx.tJoint)]

    for j in joints:
        parent = j.parent()
        if not parent or not parent.is_a(mx.tJoint):
            continue
        if j['inverseScale'].locked:
            continue

        _is = j['inverseScale'].input(plug=1)
        if _is == parent['scale']:
            continue
        parent['scale'] >> j['inverseScale']
        # log.debug('fixed inverse scale connexion of {}'.format(j))


# plugs ------------------------------------------------------------------------

def copy_plugs(src, dst):
    if not isinstance(src, mx.Node):
        src = mx.encode(str(src))
    if not isinstance(dst, mx.Node):
        dst = mx.encode(str(dst))

    # copy plugs
    for plug_name in mc.listAttr(str(src), ud=1) or []:
        plug = src[plug_name]
        try:
            cls = plug.type_class()
        except:
            log.error('cannot copy plug {} from object {}'.format(plug.name(), src))
            continue

        if plug_name not in dst and cls in (mx.Boolean, mx.Long, mx.Double, mx.String, mx.Double3):
            attr = cls(plug_name)
            attr['shortName'] = plug.name(long=False)
            attr['keyable'] = plug.keyable
            attr['channelBox'] = plug.channel_box
            if cls not in (mx.String, mx.Double3):
                attr['default'] = plug.default
            with mx.DGModifier() as md:
                md.add_attr(dst, attr)

        try:
            with mx.DGModifier() as md:
                md.set_attr(dst[plug_name], plug)
        except:
            pass


def list_future(node, visited=None, depth=0, max_depth=1):
    depth += 1
    if visited is None:
        visited = set()

    if 0 < max_depth < depth or node in visited:
        return []

    visited.add(node)

    future = []
    for _node in node.outputs():
        if _node not in visited:
            future.append(_node)
            future.extend(list_future(_node, visited, depth=depth, max_depth=max_depth))

    return future

# dag rig ----------------------------------------------------------------------

def apply_transform(node, xfo, t=False, r=False, s=False, sh=False):
    if not isinstance(node, mx.Node):
        node = mx.encode(str(node))
    if isinstance(xfo, (om.MMatrix, om.MTransformationMatrix)):
        xfo = mx.Transformation(xfo)

    if not t and not r and not s:
        t = True
        r = True
        s = True
        sh = True

    xfo = xfo * node['pim'][0].as_transform()

    with mx.DagModifier() as md:
        if t:
            md.set_attr(node['t'], xfo.translation())

        if r:
            euler = xfo.rotation()
            ro = node['ro'].read()

            plug = node['r']
            if node.is_a(mx.tJoint):
                plug = node['jo']
                md.set_attr(node['r'], (0, 0, 0))
            elif ro != 0:
                euler = euler.reorder(ro)

            md.set_attr(plug, euler)

        if s:
            scale = [round(_s, 5) for _s in xfo.scale()]
            md.set_attr(node['s'], scale)

        if sh:
            shear = [round(_sh, 5) for _sh in xfo.shear(1)]
            md.set_attr(node['sh'], shear)


def copy_transform(src, dst, t=False, r=False, s=False, sh=False):
    if not isinstance(src, mx.Node):
        src = mx.encode(str(src))
    if not isinstance(dst, mx.Node):
        dst = mx.encode(str(dst))

    if not src.is_a(mx.kTransform) or not dst.is_a(mx.kTransform):
        raise ValueError('arguments provided are not transform nodes')

    apply_transform(dst, src['wm'][0].as_transform(), t=t, r=r, s=s, sh=sh)


def get_pivot_offset(node):
    if not isinstance(node, mx.Node):
        node = mx.encode(str(node))
    parent = node.parent()

    if parent:
        pvt = mx.Transformation()
        pvt.set_translation(mc.xform(str(parent), q=1, rp=1))
        xfo = parent['wm'][0].as_transform()
        xfo1 = pvt * xfo
    else:
        xfo1 = mx.Transformation()

    pvt = mx.Transformation()
    pvt.set_translation(mc.xform(str(node), q=1, rp=1))
    xfo = node['wm'][0].as_transform()
    xfo2 = pvt * xfo

    offset = mx.Vector((xfo2 * xfo1.asMatrixInverse()).translation()) - node['t'].as_vector()
    return offset


def matrix_constraint(*args, **kw):
    nodes = []
    for arg in flatten_list(args):
        if not isinstance(arg, mx.Node):
            arg = mx.encode(str(arg))
        if arg.is_a((mx.tTransform, mx.tJoint)):
            nodes.append(arg)

    if len(nodes) < 2:
        raise RuntimeError('wrong number of objects')

    node = nodes[-1]
    targets = nodes[:-1]
    mmxs = []

    for target in targets:
        with mx.DGModifier() as md:
            mmx = md.create_node(mx.tMultMatrix, name='_mmx#')

        omx = node['wm'][0].as_transform() * target['wim'][0].as_transform()
        if omx != om.MTransformationMatrix():
            with mx.DGModifier() as md:
                cmx = md.create_node(mx.tComposeMatrix, name='_cmx#')
            cmx['inputTranslate'] = omx.translation()
            cmx['inputRotate'] = omx.rotation()
            cmx['inputScale'] = omx.scale()
            cmx['inputShear'] = omx.shear(mx.sTransform)

            cmx['outputMatrix'] >> mmx['i'][0]

        target['wm'][0] >> mmx['i'][1]

        mmxs.append(mmx)

    m = mmxs[0]['o']

    if len(mmxs) == 1:
        node['pim'][0] >> mmxs[0]['i'][2]

    else:
        with mx.DGModifier() as md:
            blend = md.create_node(mx.tWtAddMatrix, name='_bmx#')
        for i, mmx in enumerate(mmxs):
            mmx['o'] >> blend['i'][i]['m']
            blend['i'][i]['w'] = 1. / len(targets)

            mc.aliasAttr('w{}'.format(i), blend['i'][i]['w'].path())
            blend['i'][i]['w'].keyable = True

        with mx.DGModifier() as md:
            mmx = md.create_node(mx.tMultMatrix, name='_mmx#')
        blend['o'] >> mmx['i'][0]
        node['pim'][0] >> mmx['i'][1]
        m = mmx['o']

    srt = {}
    for k in ('s', 'r', 't', 'sh'):
        if k in kw:
            srt[k] = kw[k]
    return connect_matrix(m, node, **srt)


def find_target(node, constraint=None):
    if not isinstance(node, mx.Node):
        node = mx.encode(str(node))

    if constraint is None:
        constraint = mx.kConstraint

    # pair blends
    if node.is_a(mx.kTransform):
        pb = node.input(type=mx.tPairBlend)
        if pb:
            return find_target(pb, constraint=constraint)

    # constraints
    for cnst in node.inputs(type=constraint):
        if cnst.is_a(mx.tParentConstraint):
            ctrl = mc.parentConstraint(str(cnst), q=1, tl=1)
            if ctrl:
                return mx.encode(ctrl[0])
        elif cnst.is_a(mx.tPointConstraint):
            ctrl = mc.pointConstraint(str(cnst), q=1, tl=1)
            if ctrl:
                return mx.encode(ctrl[0])
        elif cnst.is_a(mx.tOrientConstraint):
            ctrl = mc.orientConstraint(str(cnst), q=1, tl=1)
            if ctrl:
                return mx.encode(ctrl[0])

    # from hook
    for xfo in node.inputs(type=mx.tDecomposeMatrix):
        xfo = xfo['imat'].input()
        if xfo is not None:
            if xfo.is_a(mx.kTransform):
                return xfo
            elif xfo.is_a(mx.tMultMatrix):
                return find_target(xfo, constraint=constraint)

    if node.is_a(mx.tMultMatrix):
        for xfo in node.inputs(plugs=True):
            _node = xfo.node()
            if _node.is_a(mx.tMultMatrix):
                return find_target(_node, constraint=constraint)
            elif _node.is_a(mx.kTransform):
                if xfo.name(long=False).startswith('wm'):
                    return xfo.node()


def find_closest_node(node, targets):
    if not isinstance(node, mx.Node):
        node = mx.encode(str(node))

    if not isinstance(targets, list):
        raise TypeError('targets has to be a list of nodes')
    targets = [target if isinstance(target, mx.Node) else mx.encode(str(target)) for target in targets]

    p0 = node.transform(space=mx.sWorld).translation()

    closest = None
    d = float('inf')

    for target in targets:
        p1 = target.transform(space=mx.sWorld).translation()
        _d = (p1 - p0).length()
        if _d < d:
            d = _d
            closest = target

    return closest


def create_ik_handle(*args, **kw):
    ik_handle = mx.cmd(mc.ikHandle, *args, **kw)[0]
    return mx.encode('|' + ik_handle)


def stretch_ik(joints, ctrl):
    root = joints[0].parent()

    # attributes
    for attr in ['twist', 'twistOffset', 'soft', 'stretch', 'squash', 'squashRate', 'softDistance', 'distance', 'factor', 'min_stretch']:
        if attr in ctrl:
            ctrl.delete_attr(ctrl[attr])

    ctrl.add_attr(mx.Double('twist', keyable=True))
    ctrl.add_attr(mx.Double('twist_offset'))

    ctrl.add_attr(mx.Double('stretch', keyable=True, min=0, max=1))
    ctrl.add_attr(mx.Double('squash', keyable=True, min=0, max=1))
    ctrl.add_attr(mx.Double('squash_rate', keyable=True, min=-1, max=1))
    ctrl['squash_rate'].channel_box = True

    ctrl.add_attr(mx.Double('min_stretch', keyable=True, min=0.1, max=1, default=1))
    ctrl.add_attr(mx.Double('soft', keyable=True, min=0, max=1))
    ctrl.add_attr(mx.Double('soft_distance', keyable=True, default=0.1, min=0, max=1))
    ctrl['soft_distance'].channel_box = True

    ctrl.add_attr(mx.Double('distance'))
    ctrl.add_attr(mx.Double('factor'))

    # guess axis
    axis = get_stretch_axis(joints)
    if not axis:
        raise RuntimeError('joints not oriented, can\'t compute chain stretch')

    t_axis = 't{}'.format(axis[0])
    s_axis = 's{}'.format(axis[0])

    # IK handle
    ik = mc.ikHandle(sj=str(joints[0]), ee=str(joints[-1]), sol='ikRPsolver')[0]
    ik = mx.encode(ik)
    ik['snapEnable'] = False
    ik.rename('ik_stretch')

    # ctrl effector
    eff_root = mx.create_node(mx.tTransform, name='eff_root#')
    eff_real = mx.create_node(mx.tTransform, name='eff_real#')

    mc.pointConstraint(str(joints[0]), str(eff_root), n='_px#')

    copy_transform(joints[-1], eff_real, t=True)
    mc.parentConstraint(str(ctrl), str(eff_real), mo=1, n='_prx#')

    ikc = mc.pointConstraint(str(eff_root), str(eff_real), str(ik), n='_px#')[0]
    ikc = mx.encode(ikc)
    ikc['w0'] = 0

    if root:
        mc.parent(str(eff_root), str(root))
        mc.parent(str(eff_real), str(root))
        mc.parent(str(ik), str(root))

    # twist
    _add = connect_add(ctrl['twist'], ctrl['twist_offset'])

    if joints[-1][t_axis].read() > 0:
        _add >> ik['twist']
    else:
        connect_mult(_add, -1, ik['twist'])

    # squash power
    _spow = connect_mult(ctrl['squash_rate'], -1.5)
    _spow = connect_add(_spow, -0.5)

    # distance probe
    _len = mx.create_node(mx.tDistanceBetween, name='_len#')
    eff_root['t'] >> _len['point1']
    eff_real['t'] >> _len['point2']
    _len['distance'] >> ctrl['distance']
    _len = _len['distance']

    # joints attr
    for j in joints[0:-1]:
        for attr in ('stretch', 'squash'):
            if attr in j:
                j.delete_attr(j[attr])
            j.addAttr(mx.Double(attr))
            j[attr].channel_box = True

    dchain = 0
    for j in joints[1:]:
        dchain += abs(j[t_axis].read())

    # node network
    nj = len(joints)

    _d0 = mx.create_node(mx.tBlendWeighted, name='_dchain#')
    for i in range(nj - 1):
        joints[i][s_axis] >> _d0['weight'][i]
        _d0['input'][i] = abs(joints[i + 1][t_axis].read())
    _d0 = _d0['output']

    _fc = connect_expr('lerp(1, m, stretch)', m=ctrl['min_stretch'], stretch=ctrl['stretch'])
    _d0 = connect_mult(_d0, _fc)

    # d > d0
    _w = mx.create_node(mx.tCondition, name='_if#')
    _len >> _w['firstTerm']
    _w['op'] = 2  # >
    _d0 >> _w['secondTerm']

    # w.r = d > d0 ? d0/d : 1
    _div = mx.create_node(mx.tMultiplyDivide, name='_div#')
    _d0 >> _div['input1X']
    _div['op'] = 2  # /
    _len >> _div['input2X']
    _div['outputX'] >> _w['colorIfTrueR']
    _w['colorIfFalseR'] = 1

    # w.g = d > d0 ? r + stretch * d/d0 : 1
    _len >> _div['input1Y']
    _d0 >> _div['input2Y']
    connect_expr('w = lerp(1, dy, stretch)', w=_w['colorIfTrueG'], dy=_div['outputY'], stretch=ctrl['stretch'])
    _w['colorIfFalseG'] = 1

    _f0 = _w['outColorG']
    _w = _w['outColorR']

    _soft = mx.create_node(mx.tCondition, name='_soft#')  # R: w, B: f_soft
    ctrl['soft'] >> _soft['firstTerm']
    _soft['op'] = 2  # >
    _soft['secondTerm'] = 0

    _ds = connect_mult(ctrl['soft_distance'], _d0)
    _da = connect_sub(_d0, _ds)

    _deff = connect_expr('d >= da ? da + ds * 1 - e ^ (-(d-da) / ds) : d', d=_len, da=_da, ds=_ds, e=math.e)
    _wsoft = connect_expr('deff / d', deff=_deff, d=_len)
    _w = connect_expr('lerp(w, wsoft, soft)', w=_w, wsoft=_wsoft, soft=ctrl['soft'])
    _fsoft = connect_expr('1 / w', w=_w)
    _w = connect_expr('lerp(w, 1, stretch)', w=_w, stretch=ctrl['stretch'])

    _w >> _soft['colorIfTrueR']
    _fsoft >> _soft['colorIfTrueB']
    _soft['colorIfFalse'] = (1, 1, 1)

    _w = _soft['outColorR']
    _fsoft = _soft['outColorB']

    _w >> ikc['w1']
    connect_sub(1, _w, ikc['w0'])

    _fsoft = connect_expr('lerp(1, fsoft, stretch)', fsoft=_fsoft, stretch=ctrl['stretch'])
    _f = connect_expr(
        'stretch > 0 ? lerp(f0, fsoft, soft) : 1',
        stretch=ctrl['stretch'], soft=ctrl['soft'],
        f0=_f0, fsoft=_fsoft
    )
    _f = connect_expr('lerp(1, f, ik)', ik=ik['ikBlend'], f=_f)
    _fc = connect_mult(_f, _fc)

    for i in range(nj - 1):
        _saim = connect_mult(_f, joints[i][s_axis])
        _sup = connect_expr(
            'squash > 0 ? lerp(1, saim^spow, squash) : 1',
            squash=ctrl['squash'], saim=_saim, spow=_spow
        )
        connect_mult(joints[i + 1][t_axis].read(), _fc, joints[i + 1][t_axis])
        _saim >> joints[i]['stretch']
        _sup >> joints[i]['squash']

    return ik, eff_root, eff_real


def stretch_spline_ik(curve, joints, mode=0, connect_scale=True, curves=None):
    if not isinstance(curve, mx.Node):
        curve = mx.encode(str(curve))
    shape = curve.shape()
    if not shape:
        raise RuntimeError('no shape')
    elif not shape.is_a(mx.tNurbsCurve):
        raise RuntimeError('not a curve')

    # secondary curves
    shapes = []
    for _cv in flatten_list([curves]):
        if not _cv:
            continue
        if not isinstance(_cv, mx.Node):
            _cv = mx.encode(str(_cv))
        if _cv.is_a(mx.tTransform) and _cv.shape():
            _cv = _cv.shape()
        if _cv.is_a(mx.tNurbsCurve):
            shapes.append(_cv)

    # args
    axis = get_stretch_axis(joints)
    if not axis:
        raise RuntimeError("joints not oriented, can't compute chain stretch")

    vAim = axis[0]
    vUp = [axis[1], axis[2]]

    # ikHandle
    ik = mc.ikHandle(sj=str(joints[0]), ee=str(joints[-1]), c=str(curve), sol='ikSplineSolver', ccv=False, scv=False, tws='easeInOut', pcv=False)[0]
    ik = mx.encode(ik)
    ik['snapEnable'] = False

    for attr in ('stretch', 'squash', 'slide'):
        if attr in curve:
            curve.delete_attr(curve[attr])

    curve.add_attr(mx.Double('stretch', min=0, max=1, keyable=True))
    curve.add_attr(mx.Double('squash', min=0, max=1, keyable=True))
    curve.add_attr(mx.Double('slide', min=-1, max=1, keyable=True))
    curve.add_attr(mx.Double('squashRate', min=-1, max=1, keyable=True))

    # tmp slide graph
    with mx.DGModifier() as md:
        graph1 = md.create_node(mx.tAnimCurveUU, name='_uu#')
    mc.setKeyframe(str(graph1), f=0, v=0)
    mc.setKeyframe(str(graph1), f=.5, v=.2222)
    mc.setKeyframe(str(graph1), f=1, v=1)
    mc.keyTangent(str(graph1), f=(0,), outAngle=.0666)
    mc.keyTangent(str(graph1), f=(.5,), outAngle=2.4)
    mc.keyTangent(str(graph1), f=(1,), outAngle=4.9)

    with mx.DGModifier() as md:
        graph2 = md.create_node(mx.tAnimCurveUU, name='_uu#')
    mc.setKeyframe(str(graph2), f=0, v=0)
    mc.setKeyframe(str(graph2), f=.5, v=.7777)
    mc.setKeyframe(str(graph2), f=1, v=1)
    mc.keyTangent(str(graph2), f=(0,), outAngle=4.9)
    mc.keyTangent(str(graph2), f=(.5,), outAngle=2.4)
    mc.keyTangent(str(graph2), f=(1.,), outAngle=.0666)

    with mx.DGModifier() as md:
        graph = md.create_node(mx.tTime)
    graph.add_attr(mx.Double('input1', keyable=True))
    graph.add_attr(mx.Double('input2', keyable=True))
    graph.add_attr(mx.Double('output1', keyable=True))
    graph.add_attr(mx.Double('output2', keyable=True))

    graph['input1'] >> graph1['i']
    graph['input2'] >> graph2['i']
    graph1['o'] >> graph['output1']
    graph2['o'] >> graph['output2']

    # find parameters
    parameters = {}

    for _shape in [shape] + shapes:
        p = []
        pmax = curve.shape()['max'].read()
        for j in joints:
            jp = j['wm'][0].as_transform().translation()
            _p = get_closest_point_on_curve(_shape, jp, parameter=True)
            if _p > pmax:
                _p = pmax
            p.append(_p)
        parameters[_shape] = p

    for j, _cv in enumerate(shapes):
        n = 'parameters{}'.format(j + 2)
        if n in curve:
            curve.delete_attr(curve[n])
        curve.add_attr(mx.Double(n, min=0, max=1, keyable=True))

    # stretch graph
    poc = []
    db = []
    d = []
    t = []
    p = parameters[shape]

    for i, joint in enumerate(joints):
        with mx.DGModifier() as md:
            _poc = md.create_node(mx.tPointOnCurveInfo, name='_poc#')
        poc.append(_poc)
        if p[i] < pmax:
            poc[i]['pr'] = p[i]
        else:
            poc[i]['top'] = True
            poc[i]['pr'] = 1
        shape['local'] >> poc[i]['ic']

        t.append(joint['t' + vAim].read())

    for i, joint in enumerate(joints[:-1]):
        # distance
        with mx.DGModifier() as md:
            _db = md.create_node(mx.tDistanceBetween, name='_len#')
        db.append(_db)
        poc[i]['p'] >> db[i]['point1']
        poc[i + 1]['p'] >> db[i]['point2']

        d.append(db[i]['d'].read())

        # slide
        pmax = p[-1]
        if i > 0:
            graph['input1'] = float(i) / (len(joints) - 1)
            graph['input2'] = float(i) / (len(joints) - 1)
            v1 = pmax * graph['output1'].read()
            v2 = pmax * graph['output2'].read()
            connect_driven_curve(curve['slide'], poc[i]['pr'], {-1: v1, 0: p[i], 1: v2})

        # stretch attr
        for attr in ('stretch', 'squash'):
            if attr in joint:
                joint.delete_attr(joint[attr])
            joint.add_attr(mx.Double(attr, keyable=True))
            joint[attr].channel_box = True

        # switch parameters
        if len(shapes) and i > 0:
            for j, _cv in enumerate(shapes):
                n = 'parameters{}'.format(j + 2)
                _w = connect_mult(parameters[_cv][i] - p[i], curve[n])
                connect_blend_weighted(_w, poc[i]['pr'])

    mx.delete(graph, graph1, graph2)

    # squash power
    spow = connect_expr('-1.5 * rate - 0.5', rate=curve['squashRate'])
    _rev_squash = connect_sub(1, curve['squash'])
    _rev_stretch = connect_sub(1, curve['stretch'])

    _saim = None
    _spow = None
    for i, joint in enumerate(joints[:-1]):
        n = i % 3 + 1
        if n == 1:
            with mx.DGModifier() as md:
                _saim = md.create_node(mx.tMultiplyDivide, name='_div#')
                _spow = md.create_node(mx.tMultiplyDivide, name='_pow#')
            _saim['op'] = 2
            _spow['op'] = 3
        _n = ('X', 'Y', 'Z')[n - 1]

        db[i]['d'] >> _saim['input1' + _n]
        _saim['input2' + _n] = d[i]
        spow >> _spow['input2' + _n]

        if mode == 0:
            # scale mode
            _s = connect_expr('r + aim * s', r=_rev_stretch, aim=_saim['output' + _n], s=curve['stretch'])
            _s >> _spow['input1' + _n]
        else:
            # translate mode
            _saim['output' + _n] >> _spow['input1' + _n]
            _s = connect_expr('r + aim * s', r=_rev_stretch, aim=_saim['output' + _n], s=curve['stretch'])
            _st = connect_mult(t[i + 1], _s)
            _st >> joints[i + 1]['t' + vAim]

        _s >> joint['stretch']

        _sup = connect_expr('r + sq * spow', r=_rev_squash, sq=curve['squash'], spow=_spow['output' + _n])
        _sup >> joint['squash']

        if connect_scale:
            if mode == 0:
                joint['stretch'] >> joint['s' + vAim]
            joint['squash'] >> joint['s' + vUp[0]]
            joint['squash'] >> joint['s' + vUp[1]]

    return ik


def create_blend_joint(j, jparent, **kw):
    name = kw.get('name')
    if not name:
        name = kw.get('n')
    if not name:
        name = '{}_blend'.format(j)

    rb = duplicate_joint(j, p=j, n=name)
    rb['ssc'] = False  # scale legacy
    mc.reorder(str(rb), f=1)

    j_name = j.name(namespace=False)
    with mx.DagModifier() as md:
        offset = md.create_node(mx.tTransform, parent=j, name='_{}_offset'.format(j_name))
    mc.parent(str(offset), str(jparent))

    oc = mc.orientConstraint(str(offset), str(j), str(rb), n='_ox#')
    oc = mx.encode(oc[0])
    fix_orient_constraint_flip(oc)

    return rb


def fix_orient_constraint_flip(cnst):
    if not isinstance(cnst, mx.Node):
        cnst = mx.encode(str(cnst))
    if not cnst.is_a((mx.tOrientConstraint, mx.tParentConstraint)):
        raise RuntimeError('%s is not an orient constraint!' % cnst)

    targets = {}
    for t in cnst['tg'].array_indices:
        targets[t] = cnst['tg'][t]['tr'].input()

        # maintain offset hack
        if cnst.is_a(mx.tParentConstraint):
            tot = cnst['tg'][t]['tot'].read()
            tor = cnst['tg'][t]['tor'].read()
            if any(tor) or any(tot):
                cnst['tg'][t]['tot'] = (0, 0, 0)
                cnst['tg'][t]['tor'] = (0, 0, 0)

                with mx.DagModifier() as md:
                    offset = md.create_node(mx.tTransform, parent=targets[0], name='o_{}'.format(targets[t].name()))
                offset['t'] = tot
                offset['r'] = tor
                # FIXME: ça marche pas en vrai ça

                targets[t] = offset

        elif cnst.is_a(mx.tOrientConstraint):
            if any(cnst['offset'].read()):
                node = cnst['cpim'].input()
                with mx.DagModifier() as md:
                    offset = md.create_node(mx.tTransform, parent=node, name='o_{}'.format(targets[t].name()))
                mc.parent(str(offset), str(targets[t]))
                offset['t'] = (0, 0, 0)
                targets[t] = offset

    for t in cnst['tg'].array_indices:
        # clean constraint input
        cnst['tg'][t]['tpm'].disconnect()
        targets[0]['wm'][0] >> cnst['tg'][t]['tpm']

        for attr in ['tt', 'tr', 'ts', 'tro', 'tjo']:
            try:
                plug = cnst['tg'][t][attr]
                plug.disconnect()
            except:
                pass

        cnst['tg'][t]['tr'] = (0, 0, 0)
        if cnst.is_a(mx.tParentConstraint):
            cnst['tg'][t]['tt'] = (0, 0, 0)
            cnst['tg'][t]['ts'] = (1, 1, 1)

        # matrix hack
        if t > 0:
            mmx = None
            dmx = None

            outwm = targets[t].input(type=mx.tMultMatrix)
            if outwm:
                inwim = outwm[0]['i'][1].input()
                if inwim:
                    if inwim == targets[0]:
                        mmx = outwm[0]
                        dmx = mmx['matrixSum'].input()

            if not mmx:
                with mx.DGModifier() as md:
                    mmx = md.create_node(mx.tMultMatrix, name='_mmx#')
                    dmx = md.create_node(mx.tDecomposeMatrix, name='_dmx#')
                targets[0]['wim'][0] >> mmx['i'][1]
                targets[t]['wm'][0] >> mmx['i'][0]
                mmx['o'] >> dmx['imat']

            dmx['outputRotate'] >> cnst['tg'][t]['tr']
            if cnst.is_a(mx.tParentConstraint):
                dmx['outputTranslate'] >> cnst['tg'][t]['tr']
                dmx['outputScale'] >> cnst['tg'][t]['ts']

    # clean constraint
    cnst['interpType'] = 2
    if cnst.is_a(mx.tOrientConstraint):
        cnst['offset'] = (0, 0, 0)


def create_angle_between(vector1, vector2, output=None):
    with mx.DGModifier() as md:
        ab = md.create_node(mx.tAngleBetween, name='_angle#')

    vector1 >> ab['vector1']
    vector2 >> ab['vector2']

    if isinstance(output, mx.Plug):
        ab['angle'] >> output

    return ab['angle']


def create_extract_vector_from_transform(node, axis, world_matrix=True, parent_matrix_obj=None, output=None):
    v_base = axis
    if not isinstance(axis, mx.Vector):
        if axis in [1, 'x', 'X']:
            v_base = mx.Vector(1, 0, 0)
        elif axis in [2, 'y', 'Y']:
            v_base = mx.Vector(0, 1, 0)
        elif axis in [3, 'z', 'Z']:
            v_base = mx.Vector(1, 0, 1)
        elif axis in [-1, '-x', '-X']:
            v_base = mx.Vector(-1, 0, 0)
        elif axis in [-2, '-y', '-Y']:
            v_base = mx.Vector(0, -1, 0)
        elif axis in [-3, '-z', '-Z']:
            v_base = mx.Vector(1, 0, -1)

    with mx.DGModifier() as md:
        vp = md.create_node(mx.tVectorProduct, name='_axis#')
    vp['op'] = 3
    vp['input1'] = v_base

    # GET THE RIGHT MATRIX
    if world_matrix:
        matrix_out = node['worldMatrix'][0]
    else:
        matrix_out = node['matrix']

    # OVERRIDE MATRIX OUT WITH parent_matrix_obj SETUP
    if world_matrix and parent_matrix_obj:
        with mx.DGModifier() as md:
            imx = md.create_node(mx.tInverseMatrix, name='_im#')
            mmx = md.create_node(mx.tMultMatrix, name='_mmx#')

        parent_matrix_obj['worldMatrix'][0] >> imx['inputMatrix']

        matrix_out >> mmx['matrixIn'][0]
        imx['outputMatrix'] >> mmx['matrixIn'][1]

        matrix_out = mmx['matrixSum']

    # EXTRACT VECTOR FROM MATRIX
    matrix_out >> vp['matrix']

    if isinstance(output, mx.Plug):
        vp['output'] >> output

    return vp['output']


# clusters ---------------------------------------------------------------------

def create_cluster(handle, dfm='cluster', root=None):
    # args
    if dfm not in ('cluster', 'softMod'):
        raise ValueError('invalid deformer type')

    if not isinstance(handle, mx.Node):
        handle = mx.encode(str(handle))

    if 'gem_id' in handle:
        from ..core.node import Nodes  # avoid circular import

        ids = handle['gem_id'].read()
        for i in ids.split(';'):
            if '::ctrls.' in i:
                sk = Nodes.get_id(i.replace('::ctrls.', '::skin.'))
                if sk and sk.is_a(mx.kTransform):
                    handle = sk

            for key in ['::ctrls.', '::skin.']:
                if key in i:
                    _root = Nodes.get_id(i.replace(key, '::roots.'))
                    if _root and root is None:
                        root = _root

    # build
    clst = handle.output(type=dfm)
    if clst:
        raise RuntimeError('{} is already connected to a cluster deformer'.format(handle))

    mc.select(cl=1)
    clst = mc.deformer(typ=dfm)
    clst = mx.encode(clst[0])

    handle['pm'][0] >> clst['preMatrix']
    handle['m'] >> clst['weightedMatrix']
    handle['pim'][0] >> clst['bindPreMatrix']
    handle['wm'][0] >> clst['matrix']

    if dfm == 'softMod':
        clst['falloffAroundSelection'] = False
        clst['falloffRadius'] = 1

        with mx.DGModifier() as md:
            dmx = md.create_node(mx.tDecomposeMatrix, name='_dmx')
        root['wm'][0] >> dmx['imat']
        dmx['outputTranslate'] >> clst['falloffCenter']

    if root:
        reroot_cluster(handle, root)

    # rename nodes
    _name = handle.name(namespace=False).split('_')
    if len(_name) > 1 and len(_name[0]) <= 4:
        _name = _name[1:]

    dfm_name = 'clst'
    if dfm == 'softMod':
        dfm_name = 'soft'

    clst.rename('{}_{}'.format(dfm_name, '_'.join(_name)))
    clst_set = clst.output(type=mx.tObjectSet)
    if clst_set:
        clst_set.rename('{}_{}Set'.format(dfm_name, '_'.join(_name)))

    # exit
    return clst


def reroot_cluster(*args):
    nodes = []
    for arg in flatten_list(args):
        if not isinstance(arg, mx.Node):
            arg = mx.encode(str(arg))
        nodes.append(arg)
    if not nodes:
        nodes = mx.ls(sl=1)

    if len(nodes) != 2:
        raise RuntimeError('wrong arguments')

    handle = nodes[0]
    root = nodes[1]

    for handle, root in [[handle, root]]:
        clst = handle['wm'][0].output(type='cluster')
        soft = handle['wm'][0].output(type='softMod')

        node = None
        if clst:
            node = clst
        elif soft:
            node = soft

        if node:
            root['wm'][0] >> node['preMatrix']
            root['wim'][0] >> node['bindPreMatrix']
            handle['wm'][0] >> node['matrix']

            with mx.DGModifier() as md:
                mmx = md.create_node(mx.tMultMatrix, name='_mmx#')
            handle['wm'][0] >> mmx['i'][0]
            root['wim'][0] >> mmx['i'][1]
            mmx['o'] >> node['weightedMatrix']

            mmx['ihi'] = False

            if node.is_a(mx.tSoftMod):
                center = node['falloffCenter'].input()
                if center and center.is_a(mx.tDecomposeMatrix):
                    with mx.DGModifier() as md:
                        dmx = md.create_node(mx.tDecomposeMatrix, name='_dmx')
                    root['wm'][0] >> dmx['imat']
                    dmx['outputTranslate'] >> node['falloffCenter']

                    mx.delete(center)


# non linear -------------------------------------------------------------------

def transfer_nonlinear(*args):
    nodes = []
    for arg in flatten_list(args):
        if not isinstance(arg, mx.Node):
            arg = mx.encode(str(arg))
        nodes.append(arg)
    if not nodes:
        nodes = mx.ls(sl=1)

    if len(nodes) != 2:
        raise RuntimeError('wrong arguments')

    handle = nodes[0].shape()
    nonlinear = handle['deformerData'].output(type='nonLinear')
    mc.parent(str(handle), str(nodes[1]), r=True, s=True)
    nodes[1]['wm'][0] >> nonlinear[0]['matrix']


def add_nonlinear(ctrl, dfm):
    # args
    if dfm not in ('bend', 'flare', 'sine', 'squash', 'twist', 'wave'):
        raise RuntimeError('non linear type is invalid')

    if not isinstance(ctrl, mx.Node):
        ctrl = mx.encode(str(ctrl))

    if 'gem_id' not in ctrl:
        mc.warning('/!\\ controller must be generated from mikan')

    # processing
    handle = ctrl.output(type=dfm)
    if handle:
        raise RuntimeError('{} is already connected to a deformer'.format(ctrl))

    with mx.DagModifier() as md:
        shp = md.create_node('deform{}'.format(dfm.capitalize()), parent=ctrl)
    with mx.DGModifier() as md:
        node = md.create_node(mx.tNonLinear)

    shp['deformerData'] >> node['deformerData']
    ctrl['wm'][0] >> node['matrix']

    _name = ctrl.name(namespace=False).split('_')
    if len(_name) > 1 and len(_name[0]) <= 4:
        _name = _name[1:]
    node.rename('{}_{}'.format(dfm, '_'.join(_name)))

    maya_version = int(mc.about(version=True))
    if maya_version < 2022:
        with mx.DGModifier() as md:
            dfm_set = md.create_node(mx.tObjectSet)
        node['message'] >> dfm_set['ub'][0]
        dfm_set.rename('{}_{}Set'.format(dfm, '_'.join(_name)))

    attrs = {
        'bend': (
            'curvature',
            'lowBound',
            'highBound'),
        'flare': (
            'curve',
            'startFlareX',
            'startFlareZ',
            'endFlareX',
            'endFlareZ',
            'lowBound',
            'highBound'),
        'sine': (
            'amplitude',
            'wavelength',
            'offset',
            'dropoff',
            'lowBound',
            'highBound'),
        'squash': (
            'factor',
            'expand',
            'maxExpandPos',
            'startSmoothness',
            'endSmoothness',
            'lowBound',
            'highBound'),
        'twist': (
            'startAngle',
            'endAngle',
            'lowBound',
            'highBound'),
        'wave': (
            'amplitude',
            'wavelength',
            'offset',
            'dropoff',
            'dropoffPosition',
            'minRadius',
            'maxRadius')
    }

    for attr in attrs[dfm]:
        mc.addAttr(str(node), ln=attr, proxy='{}.{}'.format(shp, attr))

    return node


# vdag -----------------------------------------------------------------------------------------------------------------

def set_virtual_parent(node, parent):
    if not isinstance(node, mx.Node):
        node = mx.encode(str(node))
    if not isinstance(parent, mx.Node):
        parent = mx.encode(str(parent))

    if node == parent:
        return

    if 'gem_dag_children' not in node:
        node.add_attr(mx.String('gem_dag_children', array=True, indexMatters=False))
    if 'gem_dag_children' not in parent:
        parent.add_attr(mx.String('gem_dag_children', array=True, indexMatters=False))

    parent['gem_dag_children'].append(node['gem_id'])


def get_virtual_parent(node):
    if not isinstance(node, mx.Node):
        node = mx.encode(str(node))

    if 'gem_id' in node:
        for plug in node['gem_id'].outputs(plugs=True):
            if plug.name() == 'gem_dag_children':
                return plug.node()


def get_virtual_children(node):
    if not isinstance(node, mx.Node):
        node = mx.encode(str(node))

    children = []
    if 'gem_dag_children' in node:
        for i in node['gem_dag_children'].array_indices:
            child = node['gem_dag_children'][i].input()
            if child:
                children.append(child)

    return children


def get_vdag_roots(nodes):
    roots = []

    for node in nodes:
        parent = get_virtual_parent(node)
        if parent not in nodes:
            parent = None
        if not parent:
            roots.append(node)

    return roots


def expand_vdag_tree(node, branch=None, nodes=None):
    if branch is None:
        branch = []

    branch.append(node)
    children = get_virtual_children(node)
    children.sort(key=lambda child: get_vdag_max_depth(child))
    for child in children:
        if nodes and child not in nodes:
            continue
        expand_vdag_tree(child, branch=branch, nodes=nodes)

    return branch


def get_vdag_max_depth(node, depth=0):
    children = get_virtual_children(node)
    if not children:
        return depth

    depths = []
    for child in children:
        depths.append(get_vdag_max_depth(child, depth + 1))
        return max(depths)


def reorder_vdag_set(nodes):
    if not isinstance(nodes, set):
        nodes = set(nodes)

    roots = get_vdag_roots(nodes)

    trees = []
    for root in roots:
        tree = expand_vdag_tree(root, nodes=nodes)

        for node in tree:
            nodes.remove(node)

        trees.append(tree)

    trees.sort(key=lambda branch: len(branch), reverse=True)
    skin_set = list(chain(*trees))

    return skin_set
