# coding: utf-8


import re
import hashlib
import marshal
import itertools
from six.moves import range
from six import string_types
from collections import deque

import maya.mel
import maya.api.OpenMaya as om
import maya.cmds as mc
from mikan.maya import cmdx as mx

from mikan.core.logger import create_logger
from mikan.core.utils import flatten_list, re_get_keys
from mikan.core.utils.mathutils import eigh

from .rig import copy_transform

log = create_logger('mikan.geometry')

__all__ = [
    'Mesh', 'get_meshes',
    'get_sym_map', 'get_sym_map_topology', 'get_mesh_hash',
    'compare_mesh_geometry', 'cleanup_mesh', 'copy_shape', 'reset_shape',
    'get_local_bb',
    'get_nearby_point_indices',
    'NurbsCurve', 'NurbsSurface',
    'MeshMap', 'mesh_remap', 'mesh_reorder',
    'create_mesh_copy', 'create_lattice_proxy', 'cleanup_normals', 'get_hard_edges', 'transfer_invisible_faces',
    'get_transform_from_components', 'get_transform_from_points',
    'OBB', 'QuickHull',
]


class Mesh(object):
    _fn = om.MFnMesh
    _type = mx.tMesh

    def __init__(self, node):
        self.xfo = None
        self.shape = None

        if not isinstance(node, mx.Node):
            node = mx.encode(str(node))

        if node.is_a(self._type):
            self.shape = node
            self.xfo = node.parent()
        elif node.is_a(mx.tTransform):
            self.xfo = node
            for shp in node.shapes(type=self._type):
                if not shp['intermediateObject'].read():
                    self.shape = shp
                    break

    def __repr__(self):
        return "Mesh('{}')".format(self.xfo)

    @property
    def fn(self):
        return self._fn(self.shape.dag_path())

    @property
    def vertices(self):
        return self.fn.numVertices

    @property
    def edges(self):
        return self.fn.numEdges

    def get_density(self):
        len_edges = []

        it = om.MItMeshEdge(self.shape.dag_path())
        while not it.isDone():
            e = it.length()
            len_edges.append(e)
            it.next()

        density = sum(len_edges) / len(len_edges)
        return 1 / density

    def get_points(self, space=mx.sObject):

        if isinstance(space, string_types):
            valid_spaces = {'object': mx.sObject, 'world': mx.sWorld}
            space = valid_spaces.get(space, valid_spaces['object'])

        return self.fn.getPoints(space)

    def set_points(self, points, space=mx.sObject):

        if isinstance(space, string_types):
            valid_spaces = {'object': mx.sObject, 'world': mx.sWorld}
            space = valid_spaces.get(space, valid_spaces['object'])

        fn = self.fn
        bak = fn.getPoints()

        fn.setPoints(points, space)
        mx.commit(lambda: fn.setPoints(bak), lambda: fn.setPoints(points, space))


def get_meshes(nodes=None, ref=False):
    if nodes is None:
        nodes = mx.ls(sl=True)
    if not isinstance(nodes, list):
        nodes = [nodes]

    meshes = []

    for node in nodes:
        if not isinstance(node, mx.Node):
            node = mx.encode(str(node))

        for shp in node.descendents(type=mx.tMesh):
            msh = shp.parent()

            if msh not in meshes:
                if ref:
                    meshes.append(msh)
                else:
                    if not msh.is_referenced():
                        meshes.append(msh)

    return meshes


def get_sym_map(geo, plane='yz', center=(0, 0, 0), epsilon=0.001, decimals=4, space=mx.sTransform, select=True):
    if not isinstance(geo, mx.Node):
        geo = mx.encode(str(geo))
    msh = None
    ffd = None

    decimals = int(decimals)
    if decimals < 1:
        raise RuntimeError('wrong decimals')

    if geo.is_a(mx.tMesh):
        msh = geo
    elif geo.is_a(mx.tLattice):
        ffd = geo
    elif geo.is_a(mx.tTransform):
        for shp in geo.shapes(type=mx.tMesh):
            if not shp['intermediateObject'].read():
                msh = shp
                break
        if not msh:
            for shp in geo.shapes(type=mx.tLattice):
                if not shp['intermediateObject'].read():
                    ffd = shp
                    break

    if ffd:
        proxy = create_lattice_proxy(ffd.parent())
        msh = proxy.shape()

    if not msh:
        return None

    axis = 0
    rev = (-1, 1, 1)
    if plane == 'xy' or plane == 'yx':
        axis = 2
        rev = (1, 1, -1)
    if plane == 'xz' or plane == 'zx':
        axis = 1
        rev = (1, -1, 1)

    fn = om.MFnMesh(msh.dag_path())
    vtx = fn.getPoints(space)

    center = mx.Vector(center)
    vtx_sym = []
    vtx_nosym = []
    symt = {0: {}, 1: {}, -1: {}}

    vtx = [tuple([int(round(x * 10 ** decimals)) for x in mx.Vector(vtx[x])]) for x in range(fn.numVertices)]
    vtx_done = [False] * fn.numVertices
    vtx_pos = []
    vtx_neg = {}
    vtx_mid = []

    for i in range(fn.numVertices):
        if abs(vtx[i][axis]) < epsilon:
            vtx_mid.append(i)
        elif vtx[i][axis] > 0:
            vtx_pos.append(i)
        else:
            _v = (round(vtx[i][0], decimals), round(vtx[i][1], decimals), round(vtx[i][2], decimals))
            _v = (int(_v[0]) * rev[0], int(_v[1]) * rev[1], int(_v[2]) * rev[2])
            vtx_neg[_v] = i

    for i in vtx_pos:
        if vtx[i] in vtx_neg:
            sym = vtx_neg[vtx[i]]
            vtx_sym.append((i, sym))
            vtx_neg.pop(vtx[i])
        else:
            vtx_nosym.append(i)

    for i, j in vtx_sym:
        symt[1][i] = j
        symt[-1][j] = i
        vtx_done[i] = True
        vtx_done[j] = True

    for i in vtx_mid:
        symt[0][i] = i
        vtx_done[i] = True

    for i in vtx_nosym:
        vtx_done[i] = True

    for i, v in enumerate(vtx_done):
        if not v:
            vtx_nosym.append(i)
    symt[None] = vtx_nosym

    log.info('symtable:')
    log.info(' o  {0} middle points'.format(len(vtx_mid)))
    log.info('o|o {0} symmetrical points'.format(len(vtx_sym) * 2))
    log.info('x|o {0} not symmetrical'.format(len(vtx_nosym)))

    if len(vtx_nosym) and select:
        mc.select(cl=1)
        mc.select(['{}.vtx[{}]'.format(str(msh), x) for x in vtx_nosym])
        mc.warning('{0} non symmetrical points'.format(len(vtx_nosym)))

    if ffd:
        mx.delete(proxy)

    return symt


def get_sym_map_topology(geo, edge_mid, select=True):
    # get api objects
    selection = om.MSelectionList()
    selection.add(geo)
    dag_path = selection.getDagPath(0)
    fn = om.MFnMesh(dag_path)

    # get mesh info
    point_count = fn.numVertices
    edge_count = fn.numEdges
    poly_count = fn.numPolygons

    # init
    edge_first = edge_mid
    vtx_map = []
    vtx_side_map = []
    checked_vtxs = [-1] * point_count
    side_vtxs = [-1] * point_count
    checked_faces = [-1] * poly_count
    checked_edges = [-1] * edge_count

    l_current_face = 0
    r_current_face = 0
    it_face = om.MItMeshPolygon(dag_path)
    it_edge = om.MItMeshEdge(dag_path)
    l_edge_queue = [edge_first]
    r_edge_queue = [edge_first]

    l_face_edges = []
    r_face_edges = []

    # get connected edges from faces
    face_edges = [None] * poly_count
    for i in range(poly_count):
        it_face.setIndex(i)
        face_edges[i] = it_face.getEdges()

    while l_edge_queue or r_edge_queue:

        l_current_edge = l_edge_queue[0]
        r_current_edge = r_edge_queue[0]
        l_edge_queue.pop(0)
        r_edge_queue.pop(0)
        checked_edges[l_current_edge] = r_current_edge
        checked_edges[r_current_edge] = l_current_edge

        if l_current_edge == r_current_edge and l_current_edge != edge_first:
            continue

        # get the left face
        it_edge.setIndex(l_current_edge)
        l_edge_face = it_edge.getConnectedFaces()
        if len(l_edge_face) == 1:
            l_current_face = l_edge_face[0]
        elif checked_faces[l_edge_face[0]] == -1 and checked_faces[l_edge_face[1]] != -1:
            l_current_face = l_edge_face[0]
        elif checked_faces[l_edge_face[1]] == -1 and checked_faces[l_edge_face[0]] != -1:
            l_current_face = l_edge_face[1]
        elif checked_faces[l_edge_face[0]] == -1 and checked_faces[l_edge_face[1]] == -1:
            l_current_face = l_edge_face[0]
            checked_faces[l_current_face] = -2

        # get the right face
        it_edge.setIndex(r_current_edge)
        r_edge_face = it_edge.getConnectedFaces()
        if len(r_edge_face) == 1:
            r_current_face = r_edge_face[0]
        elif checked_faces[r_edge_face[0]] == -1 and checked_faces[r_edge_face[1]] != -1:
            r_current_face = r_edge_face[0]
        elif checked_faces[r_edge_face[1]] == -1 and checked_faces[r_edge_face[0]] != -1:
            r_current_face = r_edge_face[1]
        elif checked_faces[r_edge_face[1]] == -1 and checked_faces[r_edge_face[0]] == -1:
            return om.MStatus.kFailure
        elif checked_faces[r_edge_face[1]] != -1 and checked_faces[r_edge_face[0]] != -1:
            continue

        checked_faces[r_current_face] = l_current_face
        checked_faces[l_current_face] = r_current_face

        l_edge_vtx0, l_edge_vtx1 = fn.getEdgeVertices(l_current_edge)
        r_edge_vtx0, r_edge_vtx1 = fn.getEdgeVertices(r_current_edge)

        if l_current_edge == edge_first:
            l_edge_vtx0, l_edge_vtx1 = fn.getEdgeVertices(l_current_edge)
            r_edge_vtx0, r_edge_vtx1 = fn.getEdgeVertices(r_current_edge)
            checked_vtxs[l_edge_vtx0] = r_edge_vtx0
            checked_vtxs[l_edge_vtx1] = r_edge_vtx1
            checked_vtxs[r_edge_vtx0] = l_edge_vtx0
            checked_vtxs[r_edge_vtx1] = l_edge_vtx1
        else:
            if checked_vtxs[l_edge_vtx0] == -1 and checked_vtxs[r_edge_vtx0] == -1:
                checked_vtxs[l_edge_vtx0] = r_edge_vtx0
                checked_vtxs[r_edge_vtx0] = l_edge_vtx0
            if checked_vtxs[l_edge_vtx1] == -1 and checked_vtxs[r_edge_vtx1] == -1:
                checked_vtxs[l_edge_vtx1] = r_edge_vtx1
                checked_vtxs[r_edge_vtx1] = l_edge_vtx1
            if checked_vtxs[l_edge_vtx0] == -1 and checked_vtxs[r_edge_vtx1] == -1:
                checked_vtxs[l_edge_vtx0] = r_edge_vtx1
                checked_vtxs[r_edge_vtx1] = l_edge_vtx0
            if checked_vtxs[l_edge_vtx1] == -1 and checked_vtxs[r_edge_vtx0] == -1:
                checked_vtxs[l_edge_vtx1] = r_edge_vtx0
                checked_vtxs[r_edge_vtx0] = l_edge_vtx1
        side_vtxs[l_edge_vtx0] = 2
        side_vtxs[l_edge_vtx1] = 2
        side_vtxs[r_edge_vtx0] = 1
        side_vtxs[r_edge_vtx1] = 1

        r_face_edges_count = 0
        for edge in face_edges[r_current_face]:
            if len(r_face_edges) > r_face_edges_count:
                r_face_edges[r_face_edges_count] = edge
            else:
                r_face_edges.append(edge)
            r_face_edges_count += 1

        l_face_edges_count = 0
        for edge in face_edges[l_current_face]:
            if len(l_face_edges) > l_face_edges_count:
                l_face_edges[l_face_edges_count] = edge
            else:
                l_face_edges.append(edge)
            l_face_edges_count += 1

        for i in range(l_face_edges_count):
            if checked_edges[l_face_edges[i]] == -1:

                it_edge.setIndex(l_current_edge)
                if it_edge.connectedToEdge(l_face_edges[i]) and l_current_edge != l_face_edges[i]:

                    l_if_checked_vtx0, l_if_checked_vtx1 = fn.getEdgeVertices(l_face_edges[i])

                    if l_if_checked_vtx0 == l_edge_vtx0 or l_if_checked_vtx0 == l_edge_vtx1:
                        l_checked_vtx = l_if_checked_vtx0
                        l_non_checked_vtx = l_if_checked_vtx1
                    elif l_if_checked_vtx1 == l_edge_vtx0 or l_if_checked_vtx1 == l_edge_vtx1:
                        l_checked_vtx = l_if_checked_vtx1
                        l_non_checked_vtx = l_if_checked_vtx0
                    else:
                        continue

                    for k in range(r_face_edges_count):
                        it_edge.setIndex(r_current_edge)
                        if it_edge.connectedToEdge(r_face_edges[k]) and r_current_edge != r_face_edges[k]:

                            r_face_edge_vtx0, r_face_edge_vtx1 = fn.getEdgeVertices(r_face_edges[k])

                            if r_face_edge_vtx0 == checked_vtxs[l_checked_vtx]:
                                checked_vtxs[l_non_checked_vtx] = r_face_edge_vtx1
                                checked_vtxs[r_face_edge_vtx1] = l_non_checked_vtx
                                side_vtxs[l_non_checked_vtx] = 2
                                side_vtxs[r_face_edge_vtx1] = 1
                                l_edge_queue.append(l_face_edges[i])
                                r_edge_queue.append(r_face_edges[k])
                            if r_face_edge_vtx1 == checked_vtxs[l_checked_vtx]:
                                checked_vtxs[l_non_checked_vtx] = r_face_edge_vtx0
                                checked_vtxs[r_face_edge_vtx0] = l_non_checked_vtx
                                side_vtxs[l_non_checked_vtx] = 2
                                side_vtxs[r_face_edge_vtx0] = 1
                                l_edge_queue.append(l_face_edges[i])
                                r_edge_queue.append(r_face_edges[k])

    x_average1, x_average2 = 0, 0
    for i in range(point_count):
        if checked_vtxs[i] != i and checked_vtxs[i] != -1:
            check_pos_point = fn.getPoint(checked_vtxs[i])
            if side_vtxs[i] == 1:
                x_average1 += check_pos_point.x
            elif side_vtxs[i] == 2:
                x_average2 += check_pos_point.x
    switch_side = x_average2 > x_average1

    # build sym table
    for i in range(point_count):
        vtx_map.append(checked_vtxs[i])
        if checked_vtxs[i] == -1:
            vtx_side_map.append(3)

        elif checked_vtxs[i] != i:
            if not switch_side:
                vtx_side_map.append(side_vtxs[i])
            else:
                if side_vtxs[i] == 2:
                    vtx_side_map.append(1)
                else:
                    vtx_side_map.append(2)
        else:
            vtx_side_map.append(0)

    for i in range(len(vtx_map)):
        if vtx_map[i] == -1:
            vtx_map[i] = i

    # build sym table
    symt = {0: {}, 1: {}, -1: {}, None: []}

    for i in range(len(vtx_map)):
        if vtx_side_map[i] == 1:  # right
            symt[-1][i] = vtx_map[i]
        elif vtx_side_map[i] == 2:  # left
            symt[1][i] = vtx_map[i]
        elif vtx_side_map[i] == 0:  # middle
            symt[0][i] = i
        else:
            symt[None].append(i)

    log.info('symtable:')
    log.info(' o  {0} middle points'.format(len(symt[0])))
    log.info('o|o {0} symmetrical points'.format(len(symt[1]) * 2))
    log.info('x|o {0} not symmetrical points'.format(len(symt[None])))

    if len(symt[None]) and select:
        mc.select(cl=1)
        mc.select(['{}.vtx[{}]'.format(str(geo), x) for x in symt[None]])
        mc.warning('{0} non symmetrical points'.format(len(symt[None])))

    return symt


"""
#run A
import maya.cmds as mc
import maya.api.OpenMaya as ompy

selection = mc.ls( sl = True )
geo = selection[0].split('.e[')[0]
middle_edge = int( selection[0].split('.e[')[1][:-1] )
symt = get_sym_map_topology( geo,middle_edge)

i = 0

#run B
i_sym = i
i_sym = symt[ 0].get( i , i_sym )
i_sym = symt[ 1].get( i , i_sym )
i_sym = symt[-1].get( i , i_sym )
print('====== SELECT {} & {} '.format( i , i_sym) )
mc.select( '{}.vtx[{}]'.format( geo , i ) )
mc.select( '{}.vtx[{}]'.format( geo , i_sym ) , add = True )
i += 1

"""


def get_mesh_hash(msh):
    vtx = []

    if not isinstance(msh, mx.Node):
        msh = mx.encode(msh)
    if not msh.is_a(mx.tMesh):
        msh = msh.shape()

    it = om.MItMeshVertex(msh.object())
    while not it.isDone():
        vtx.extend(sorted(it.getConnectedVertices()))
        it.next()

    m = marshal.dumps(vtx)
    return hashlib.md5(m).hexdigest()


def compare_mesh_geometry(src, dst, space=mx.sObject, tolerance=0.00001):
    """
    Check if two objects have the same vertices position, in world reference or local reference
    :param str src: The Maya source polymesh.
    :param str dst: The Maya destination polymesh.
    :param str space: object or world space
    :param double tolerance: Comparison tolerance.
    :return: True if identical.
    :rtype: bool
    """
    identical = True

    valid_spaces = {'object': mx.sObject, 'world': mx.sWorld}
    if isinstance(space, string_types):
        if space not in valid_spaces:
            log.error('Invalid space {} supplied'.format(space))
        else:
            space = valid_spaces[space]

    if not isinstance(src, mx.Node):
        src = mx.encode(str(src))
    if src.is_a(mx.tMesh):
        src_dag = src.dag_path()
    else:
        src_dag = None
        for shp in src.shapes(type=mx.tMesh):
            if not shp['io'].read():
                src_dag = shp.dag_path()

    if not isinstance(dst, mx.Node):
        dst = mx.encode(str(dst))
    if dst.is_a(mx.tMesh):
        dst_dag = dst.dag_path()
    else:
        dst_dag = None
        for shp in dst.shapes(type=mx.tMesh):
            if not shp['io'].read():
                dst_dag = shp.dag_path()

    if not src_dag:
        log.error('Invalid source {}'.format(src))

    if not dst_dag:
        log.error('Invalid target {}'.format(dst))

    # compare vertices number
    src_fn = om.MFnMesh(src_dag)
    dst_fn = om.MFnMesh(dst_dag)
    if src_fn.numVertices != dst_fn.numVertices:
        log.debug('Vertex count is different')
        return not identical

    # compare points
    src_it = om.MItMeshVertex(src_dag)
    dst_it = om.MItMeshVertex(dst_dag)

    while not dst_it.isDone():
        dst_p = dst_it.position(space)
        index = dst_it.index()
        # src_it.setIndex(index)  # setIndex requires a ptr to previous index
        src_p = src_it.position(space)
        if not src_p.isEquivalent(dst_p, tolerance):
            log.debug('Vertex {} is not identical'.format(index))
            return not identical
        dst_it.next()
        src_it.next()

    return identical


def cleanup_mesh(msh):
    msh = Mesh(msh)

    # kill history
    mc.delete(mc.deformer(str(msh.xfo), type='geometryFilter'))
    mx.delete(msh.xfo, ch=1)

    # check default UV set name
    if msh.shape['uvst'][0]['uvsn'].read() != 'map1':
        with mx.DGModifier() as md:
            for i in msh.shape['uvst'].array_indices:
                if msh.shape['uvst'][i]['uvsn'].read() == 'map1':
                    md.set_attr(msh.shape['uvst'][i]['uvsn'], 'map1_backup')
            md.set_attr(msh.shape['uvst'][0]['uvsn'], 'map1')

    # cleanup tmp color sets
    fn = om.MFnMesh(msh.shape.object())
    color_sets = fn.getColorSetNames()
    for c in color_sets:
        if c.endswith('Temp'):
            mc.polyColorSet(str(msh.shape), delete=True, colorSet=c)

    # fix render stats
    if not msh.shape['motionBlur']:
        with mx.DGModifier() as md:
            md.set_attr(msh.shape['castsShadows'], True)
            md.set_attr(msh.shape['receiveShadows'], True)
            md.set_attr(msh.shape['holdOut'], False)
            md.set_attr(msh.shape['motionBlur'], True)
            md.set_attr(msh.shape['primaryVisibility'], True)
            md.set_attr(msh.shape['smoothShading'], True)
            md.set_attr(msh.shape['visibleInReflections'], True)
            md.set_attr(msh.shape['visibleInRefractions'], True)


def copy_shape(src, dst, space=mx.sObject):
    if not isinstance(src, mx.Node):
        src = mx.encode(str(src))
    if not isinstance(dst, mx.Node):
        dst = mx.encode(str(dst))
    src_fn = om.MFnMesh(src.dag_path())
    dst_fn = om.MFnMesh(dst.dag_path())

    if isinstance(space, string_types):
        valid_spaces = {'object': mx.sObject, 'world': mx.sWorld}
        space = valid_spaces.get(space, valid_spaces['object'])

    vtx_bak = dst_fn.getPoints()
    vtx = src_fn.getPoints(space)

    dst_fn.setPoints(vtx, space)
    mx.commit(lambda: dst_fn.setPoints(vtx_bak), lambda: dst_fn.setPoints(vtx, space))


def reset_shape(msh):
    if not isinstance(msh, mx.Node):
        msh = mx.encode(msh)
    if not msh.is_a(mx.tMesh):
        msh = msh.shape()

    fn = om.MFnMesh(msh.dag_path())

    vertices = fn.getPoints(mx.sObject)
    polygon_counts = []
    polygon_connects = []

    it = om.MItMeshPolygon(msh.dag_path())
    while not it.isDone():
        polygon_counts.append(it.polygonVertexCount())
        for i in range(it.polygonVertexCount()):
            polygon_connects.append(it.vertexIndex(i))
        try:
            it.next()
        except:
            it.next(None)

    fn.createInPlace(vertices, polygon_counts, polygon_connects)

    for v in range(fn.numVertices):
        msh['pnts'][v] = (0, 0, 0)


def get_nearby_point_indices(source_points, reference_points, radius=0.0):
    """
    Returns the indices of points in `source_points` that are within a certain
    distance (`radius`) from at least one point in `reference_points`.

    Args:
        source_points (List[MPoint]): The list of points to test.
        reference_points (List[MPoint]): The list of reference points.
        radius (float): Maximum distance to consider a point as 'nearby'.
                        If radius <= 0, all source point indices are returned.

    Returns:
        List[int]: Indices of points in `source_points` that are within the given
                   radius of any point in `reference_points`.
    """
    if radius <= 0.0:
        return list(range(len(source_points)))

    nearby_indices = []
    for i, point in enumerate(source_points):
        p_vec = om.MVector(point)
        for ref_point in reference_points:
            r_vec = om.MVector(ref_point)
            if (r_vec - p_vec).length() < radius:
                nearby_indices.append(i)
                break  # No need to check more reference points for this one

    return nearby_indices


def is_visible(node):
    if not node['v']:
        return False

    while True:
        node = node.parent()
        if not node:
            break
        if not node['v']:
            return False

    return True


def get_local_bb(node, hidden=True):
    if not isinstance(node, mx.Node):
        node = mx.encode(str(node))

    bb = mx.BoundingBox()
    wim = node['wim'][0].as_matrix()

    it = node.descendents()
    if node.shape():
        it = itertools.chain([node], it)

    for xfo in it:
        if not hidden and not is_visible(xfo):
            continue
        for shp in xfo.shapes(type=mx.tMesh):
            if shp['io'].read():
                continue
            bbx = shp.bounding_box
            wm = xfo['wm'][0].as_matrix()
            bbx.transformUsing(wm * wim)
            bb.expand(bbx)

    return bb


class NurbsCurve(object):
    _fn = om.MFnNurbsCurve
    _type = mx.tNurbsCurve

    def __init__(self, node):
        self.xfo = None
        self.shape = None

        if not isinstance(node, mx.Node):
            node = mx.encode(str(node))

        if node.is_a(self._type):
            self.shape = node
            self.xfo = node.parent()
        elif node.is_a(mx.tTransform):
            self.xfo = node
            for shp in node.shapes(type=self._type):
                if not shp['intermediateObject'].read():
                    self.shape = shp
                    break

    def __repr__(self):
        return "NurbsCurve('{}')".format(self.xfo)

    @property
    def cvs(self):
        fn = self._fn(self.shape.object())
        return fn.numCVs

    @property
    def degree(self):
        fn = self._fn(self.shape.object())
        return fn.degree

    def get_points(self, space=mx.sObject):

        if isinstance(space, string_types):
            valid_spaces = {'object': mx.sObject, 'world': mx.sWorld}
            space = valid_spaces.get(space, valid_spaces['object'])

        fn = self._fn(self.shape.dag_path())
        return fn.cvPositions(space)

    def set_points(self, points, space=mx.sObject):

        if isinstance(space, string_types):
            valid_spaces = {'object': mx.sObject, 'world': mx.sWorld}
            space = valid_spaces.get(space, valid_spaces['object'])

        fn = self._fn(self.shape.object())
        bak = fn.cvPositions()

        fn.setCVPositions(points, space)
        fn.updateCurve()

        def _undo_set_points(_points):
            fn.setCVPositions(_points)
            fn.updateCurve()

        def _redo_set_points(_points, _space):
            fn.setCVPositions(_points, _space)
            fn.updateCurve()

        mx.commit(lambda: _undo_set_points(bak), lambda: _redo_set_points(points, space))


class NurbsSurface(object):
    _fn = om.MFnNurbsSurface
    _type = mx.tNurbsSurface

    def __init__(self, node):
        self.xfo = None
        self.shape = None

        if not isinstance(node, mx.Node):
            node = mx.encode(str(node))

        if node.is_a(self._type):
            self.shape = node
            self.xfo = node.parent()
        elif node.is_a(mx.tTransform):
            self.xfo = node
            for shp in node.shapes(type=self._type):
                if not shp['intermediateObject'].read():
                    self.shape = shp
                    break

    def __repr__(self):
        return "NurbsSurface('{}')".format(self.xfo)

    def get_points(self, space=mx.sObject):

        if isinstance(space, string_types):
            valid_spaces = {'object': mx.sObject, 'world': mx.sWorld}
            space = valid_spaces.get(space, valid_spaces['object'])

        fn = self._fn(self.shape.dag_path())
        return fn.cvPositions(space)

    def set_points(self, points, space=mx.sObject):

        if isinstance(space, string_types):
            valid_spaces = {'object': mx.sObject, 'world': mx.sWorld}
            space = valid_spaces.get(space, valid_spaces['object'])

        fn = self._fn(self.shape.object())
        bak = fn.cvPositions()

        fn.setCVPositions(points, space)
        fn.updateSurface()

        def _undo_set_points(_points):
            fn.setCVPositions(_points)
            fn.updateSurface()

        def _redo_set_points(_points, _space):
            fn.setCVPositions(_points, _space)
            fn.updateSurface()

        mx.commit(lambda: _undo_set_points(bak), lambda: _redo_set_points(points, space))


class MeshMap(object):
    CLOCKWISE = 1
    COUNTERCLOCKWISE = -1
    NO_DIRECTION = 0

    def __init__(self, msh, f, v0, v1):
        if not isinstance(msh, mx.Node):
            msh = mx.encode(str(msh))
        self.msh = msh
        self.fn = om.MFnMesh(msh.dag_path())

        self.face_traversal = [False] * self.fn.numPolygons

        self.cv_mapping = [-1] * self.fn.numVertices
        self.cv_mapping_inverse = [-1] * self.fn.numVertices

        self.new_polygon_counts = []
        self.new_polygon_connects = []

        self.orig_vertices = self.fn.getPoints(mx.sObject)
        self.new_vertices = []

        self.poly_it = om.MItMeshPolygon(msh.dag_path())
        self.edge_it = om.MItMeshEdge(msh.dag_path())

        self.direction = self.NO_DIRECTION
        self.traverse_stack = deque([(int(f), v0, v1)])
        while len(self.traverse_stack) > 0:
            current_edge = self.traverse_stack.popleft()
            self.traverse_face(*current_edge)

        if self.__bool__():
            log.info('"{}" traverse successful'.format(self.msh))
        else:
            raise RuntimeError('"{}" traverse failed: multiple shells'.format(self.msh))

    def __bool__(self):
        return len(self.orig_vertices) == len(self.new_vertices)

    __nonzero__ = __bool__

    def traverse_face(self, f, v0, v1):
        # skip if already processed
        if self.face_traversal[f]:
            return True

        # get vtx/edge data
        self.poly_it.setIndex(f)
        edge_orig = list(self.poly_it.getEdges())
        vtx_orig = list(self.poly_it.getVertices())
        vtx_cnt = len(vtx_orig)

        # sort v0, v1 direction
        self.direction = 0
        vtx_sorted = [-1] * vtx_cnt
        edge_sorted = [-1] * vtx_cnt

        vidx = -1
        for i in range(vtx_cnt):
            if vtx_orig[i] == v0:
                vidx = i
                if vtx_orig[(i + 1) % vtx_cnt] == v1:
                    self.direction = self.CLOCKWISE
                elif vtx_orig[(i - 1) % vtx_cnt] == v1:
                    self.direction = self.COUNTERCLOCKWISE
                break

        if self.direction == self.NO_DIRECTION:
            raise RuntimeError('vertices are not adjacent')

        for i in range(vtx_cnt):
            vtx_sorted[i] = vtx_orig[(vidx + i * self.direction) % vtx_cnt]
            if self.direction == self.CLOCKWISE:
                edge_sorted[i] = edge_orig[(vidx + i * self.direction) % vtx_cnt]
            else:
                edge_sorted[i] = edge_orig[(vidx - 1 + i * self.direction) % vtx_cnt]

        # add any new cvs
        for i in range(vtx_cnt):
            index = vtx_sorted[i]
            if self.cv_mapping[index] == -1:
                self.new_vertices.append(self.orig_vertices[index])
                self.cv_mapping[index] = len(self.new_vertices) - 1
                self.cv_mapping_inverse[len(self.new_vertices) - 1] = index

        # add the new face count
        self.new_polygon_counts.append(vtx_cnt)

        # add the new polyConnects
        for i in range(vtx_cnt):
            self.new_polygon_connects.append(self.cv_mapping[vtx_sorted[i]])

        # mark current face as complete
        self.face_traversal[f] = True

        # recurse over edges
        stack = deque()
        for i in range(len(edge_sorted)):
            next_edge = edge_sorted[i]
            next_vtx0, next_vtx1 = self.fn.getEdgeVertices(next_edge)

            # find vertex that starts next edge
            base_idx = -1
            swap = True
            for j in range(len(vtx_sorted)):
                if vtx_sorted[j] == next_vtx0:
                    base_idx = j
                    break

            if base_idx == -1:
                raise RuntimeError('cannot find next edge')

            # look forward/backward to find edge other point
            # indicates edges direction
            # needed to guide next recursion level
            # keep normals consistent
            if vtx_sorted[(base_idx + 1) % vtx_cnt] == next_vtx1:
                pass
            elif vtx_sorted[(base_idx - 1) % vtx_cnt] == next_vtx1:
                swap = False

            self.edge_it.setIndex(next_edge)
            connected_faces = list(self.edge_it.getConnectedFaces())

            # single face is the current one, recurse others
            if len(connected_faces) > 1:
                if connected_faces[0] == f:
                    next_face = connected_faces[1]
                else:
                    next_face = connected_faces[0]

                if swap:
                    next_vtx0, next_vtx1 = next_vtx1, next_vtx0

                if not self.face_traversal[next_face]:
                    stack.append((next_face, next_vtx0, next_vtx1))

        self.traverse_stack.extendleft(reversed(stack))
        return True


def mesh_reorder(msh, f, v0, v1):
    if not isinstance(msh, mx.Node):
        msh = mx.encode(str(msh))

    m = MeshMap(msh, f, v0, v1)

    # duplicate mesh and reorder vertex
    new = mc.duplicate(str(msh), rr=1, rc=1)
    new = mx.encode(new[0])
    mc.delete(mc.deformer(str(new), type='geometryFilter'))
    mx.delete(new, ch=1)
    new.rename(msh.name(namespace=False) + '_REORDERED')

    fn = om.MFnMesh(new.dag_path())
    fn.createInPlace(
        m.new_vertices,
        m.new_polygon_counts,
        m.new_polygon_connects
    )

    mc.transferAttributes(str(msh), str(new), sampleSpace=1, transferUVs=2, transferColors=2)
    if m.direction == m.COUNTERCLOCKWISE:
        mc.polyNormal(str(new), normalMode=0, userNormalMode=0, ch=0)

    mx.delete(new, ch=1)
    mc.select(str(new))
    return new


def mesh_remap(_msh, _f, _v0, _v1, msh, f, v0, v1):
    # check inputs
    _msh = Mesh(_msh)
    msh = Mesh(msh)
    if _msh.vertices != msh.vertices:
        raise RuntimeError('Meshes do not have the same number of vertices.')
    msh = msh.xfo
    _msh = _msh.xfo

    # remap mesh vertex order to another
    msrc = MeshMap(_msh, _f, _v0, _v1)
    mdst = MeshMap(msh, f, v0, v1)

    del msrc.new_polygon_counts[:]
    del msrc.new_polygon_connects[:]

    poly_iter = om.MItMeshPolygon(_msh.dag_path())
    while not poly_iter.isDone():
        msrc.new_polygon_counts.append(poly_iter.polygonVertexCount())
        for i in range(poly_iter.polygonVertexCount()):
            msrc.new_polygon_connects.append(poly_iter.vertexIndex(i))
        try:
            poly_iter.next()
        except:
            poly_iter.next(None)

    for i in range(mdst.fn.numVertices):
        mdst.new_vertices[msrc.cv_mapping_inverse[i]] = mdst.orig_vertices[mdst.cv_mapping_inverse[i]]

    new = mc.duplicate(str(msh), rr=1, rc=1)
    new = mx.encode(new[0])
    mc.delete(mc.deformer(str(new), type='geometryFilter'))
    mx.delete(new, ch=1)
    new.rename(msh.name(namespace=False) + '_REMAPPED')

    fn = om.MFnMesh(new.dag_path())
    fn.createInPlace(
        mdst.new_vertices,
        msrc.new_polygon_counts,
        msrc.new_polygon_connects
    )

    mc.transferAttributes(str(msh), str(new), sampleSpace=1, transferUVs=2, transferColors=2)
    try:
        mc.transferShadingSets(str(msh), str(new))
    except:
        pass

    mx.delete(new, ch=1)
    mc.select(str(new))
    return new


def create_mesh_copy(geo, shading=False, uvs=True):
    if not isinstance(geo, mx.Node):
        geo = mx.encode(str(geo))

    _xfo = None
    _shp = None
    if geo.is_a(mx.tTransform):
        _xfo = geo
        for shp in geo.shapes(type=mx.tMesh):
            if not shp['io'].read():
                _shp = shp
                break
    else:
        _xfo = geo.parent()
        _shp = geo

    if not _xfo or not _shp:
        raise RuntimeError('/!\\ cannot create mesh copy from {}'.format(geo))

    with mx.DagModifier() as md:
        xfo = md.create_node(mx.tTransform, parent=_xfo.parent(), name='{}__copy__'.format(_xfo.name()))
    xfo['t'] = _xfo['t']
    xfo['r'] = _xfo['r']
    xfo['s'] = _xfo['s']
    xfo['sh'] = _xfo['sh']
    xfo['rp'] = _xfo['rp']
    xfo['sp'] = _xfo['sp']
    xfo['rpt'] = _xfo['rpt']
    xfo['spt'] = _xfo['spt']

    fn = om.MFnMesh()
    fn.copy(_shp.object(), xfo.object())

    if not uvs:
        uv_sets = fn.getUVSetNames()
        for uv_set in uv_sets[1:]:
            fn.deleteUVSet(uv_set)
        if uv_sets[0] != 'map1':
            fn.renameUVSet(uv_sets[0], 'map1')
        fn.clearUVs('map1')

    shp = xfo.shape()
    shp.rename('{}Shape'.format(xfo.name()))

    for attr in ['displayInvisibleFaces']:
        shp[attr] = _shp[attr]

    if shading:
        mx.cmd(mc.sets, xfo, e=True, forceElement='initialShadingGroup')

    return xfo


def create_lattice_proxy(node):
    if not isinstance(node, mx.Node):
        node = mx.encode(str(node))

    for lat in node.shapes(type=mx.tLattice):
        u = lat['uDivisions'].read()
        t = lat['tDivisions'].read()
        s = lat['sDivisions'].read()

        # combine planes
        planes = []
        for _u in range(u):
            p = mc.polyPlane(ch=0, sh=t - 1, sw=s - 1)
            p = mx.encode(p[0])
            planes.append(p)

        prx = mx.cmd(mc.polyUnite, planes, ch=0)
        prx = mx.encode(prx[0])
        prx.rename('prx_{}'.format(node.name()))

        # copy transform
        parent = node.parent()
        if parent:
            mc.parent(str(prx), str(parent))
        copy_transform(node, prx)
        prx['r'] = node['r']
        mc.delete(mc.deformer(str(prx), type='geometryFilter'))
        mx.delete(prx, ch=1)

        _t = node.translation(mx.sWorld)

        mc.move(_t.x, _t.y, _t.z,
                str(node) + '.scalePivot',
                str(node) + '.rotatePivot',
                absolute=True)

        # copy tweaks
        for _u in range(u):
            for _t in range(t):
                for _s in range(s):
                    pos = mc.xform('{}.pt[{}][{}][{}]'.format(lat, _s, _t, _u), q=1, t=1, ws=1)
                    mc.xform('{}.vtx[{}]'.format(prx, ((_t + t * _u) * s) + _s), t=pos, ws=1)

        if prx.parent():
            mc.parent(str(prx), w=1)
        return prx


def cleanup_normals(*args):
    nodes = []
    for node in flatten_list(args):
        if not isinstance(node, mx.Node):
            node = mx.encode(str(node))
        nodes.append(node)
    if not args:
        nodes = mx.ls(sl=1)

    meshes = []
    for node in nodes:
        for msh in node.descendents(type=mx.tMesh):
            p = msh.parent()
            if p.is_referenced() or msh.is_referenced():
                continue
            if p not in meshes:
                meshes.append(p)

    sl = mc.ls(sl=1)
    mc.select(cl=1)

    for msh in meshes:
        try:
            fn = om.MFnMesh(msh.shape().object())
            fn.numVertices
        except:
            log.warning('cannot fix normals of "{}"'.format(msh))
            continue

        # conform
        mc.polyNormal(str(msh), normalMode=2, userNormalMode=0, ch=0)

        # get hard edges
        edges = []
        if fn.isNormalLocked(0):
            edges = get_hard_edges(msh)

        # unlock
        mc.polyNormalPerVertex(str(msh), ufn=True)

        if edges:
            mc.polySoftEdge(str(msh), a=180, ch=0)
            mc.polySoftEdge(edges, a=0, ch=0)

        # opposite trick
        for shp in msh.descendents(type=mx.tMesh):
            if not shp['io'].read():
                if not shp['doubleSided'].read() and shp['opposite'].read():
                    mc.polyNormal(str(shp.parent()), normalMode=0, userNormalMode=0, ch=0)
            shp['opposite'] = False

    mc.select(sl)


def get_hard_edges(msh, as_int=False):
    if not isinstance(msh, mx.Node):
        msh = mx.encode(str(msh))

    if msh.is_a(mx.tTransform):
        msh = msh.shape(type=mx.tMesh)

    if not msh.is_a(mx.tMesh):
        raise ValueError('{} is not a mesh'.format(msh))

    fn = om.MFnMesh(msh.object())

    nv = fn.numVertices

    if fn.isNormalLocked(0):
        edges = []
        for i in range(nv):
            vertice = '{}.vtx[{}]'.format(msh, i)

            vf_info = mc.polyInfo(vertice, vf=True)[0]
            vfs = []
            for vf in vf_info.split()[2:]:
                vfs.append('{}.vtxFace[{}][{}]'.format(msh, i, vf))

            vf_old = mx.Vector(mc.polyNormalPerVertex(vfs[-1], query=True, xyz=True))

            for vf in vfs[:-1]:
                vf_new = mx.Vector(mc.polyNormalPerVertex(vf, query=True, xyz=True))

                comp = vf_old - vf_new
                if comp.length() != 0:
                    for he in mc.polyListComponentConversion(vf, te=True):
                        if he not in edges:
                            edges.append(he)
                vf_old = vf_new

    else:
        sl = mc.ls(sl=True)
        mc.select(str(msh))
        mc.polySelectConstraint(m=3, t=0x8000, sm=1)
        edges = mc.filterExpand(ex=1, sm=32)
        maya.mel.eval('source polygonConstraint;')
        maya.mel.eval("resetPolySelectConstraint();")
        mc.select(sl)

    if as_int:
        edges = list(map(lambda e: int(re_get_keys.findall(e)[0]), edges))

    return edges


def transfer_invisible_faces(src, dst):
    if not isinstance(src, mx.Node):
        src = mx.encode(str(src))
    if not isinstance(dst, mx.Node):
        dst = mx.encode(str(dst))

    if src.is_a(mx.tTransform):
        for shp in src.shapes(type=mx.tMesh):
            if not shp['intermediateObject'].read():
                src = shp
                break
    if dst.is_a(mx.tTransform):
        for shp in dst.shapes(type=mx.tMesh):
            if not shp['intermediateObject'].read():
                dst = shp
                break

    if not src.is_a(mx.tMesh) and not dst.is_a(mx.tMesh):
        raise ValueError('invalid meshes')

    fn_src = om.MFnMesh(src.object())
    inv = fn_src.getInvisibleFaces()

    if inv:
        inv = set(inv)
        fn_dst = om.MFnMesh(dst.dag_path())
        points = fn_dst.getPoints(mx.sWorld)
        new_inv = set()

        it = om.MItMeshPolygon(dst.object())
        while not it.isDone():

            is_inv = []
            pts = it.getVertices()
            for i in pts:
                closest, face = fn_src.getClosestPoint(points[i])
                if face in inv:
                    is_inv.append(1)
                else:
                    is_inv.append(0)

            is_inv = sum(is_inv) / len(is_inv)
            if is_inv > 0.5:
                new_inv.add(it.index())

            try:
                it.next()
            except:
                it.next(None)

        # transfer
        old_inv = set(fn_dst.getInvisibleFaces())

        show = old_inv.difference(new_inv)
        hide = new_inv.difference(old_inv)

        if hide:
            mc.polyHole(mc.ls([dst.path() + '.f[{}]'.format(i) for i in list(hide)]), assignHole=1)
        if show:
            mc.polyHole(mc.ls([dst.path() + '.f[{}]'.format(i) for i in list(show)]), assignHole=0)

        dst['displayInvisibleFaces'] = False
        dst['displayInvisibleFaces'] = True

    else:
        fn_dst = om.MFnMesh(dst.dag_path())
        old_inv = fn_dst.getInvisibleFaces()

        if old_inv:
            mc.polyHole([dst.path() + '.f[{}]'.format(i) for i in old_inv], assignHole=0)

        dst['displayInvisibleFaces'] = src['displayInvisibleFaces']


def get_vertex_face_vectors(msh, normalize=True, indices=None):
    """ Prototype/Snippet to get vertex tangents from a mesh """
    if not isinstance(msh, mx.Node):
        msh = mx.encode(str(msh))
    if msh.is_a(mx.tTransform):
        msh = msh.shape()

    fn = om.MFnMesh(msh.dag_path())
    tangents = fn.getTangents(mx.sWorld)
    binormals = fn.getBinormals(mx.sWorld)

    ntbs = []

    for i in range(len(tangents)):
        if indices is not None and i not in indices:
            continue

        tangent = mx.Vector(tangents[i])
        binormal = mx.Vector(binormals[i])

        if normalize:
            binormal.normalize()
            tangent.normalize()

        normal = tangent ^ binormal  # cross
        if normalize:
            normal.normalize()

        ntbs.append((normal, tangent, binormal))

    return ntbs


def vectors_to_matrix(x=(1, 0, 0), y=(0, 1, 0), z=(0, 0, 1), pos=(0, 0, 0)):
    """ Function to convert an orthogonal basis defined from seperate vectors + position to a matrix """
    return mx.Matrix4([x[0], x[1], x[2], 0, y[0], y[1], y[2], 0, z[0], z[1], z[2], 0, pos[0], pos[1], pos[2], 1])


def get_transform_from_points(obj, ids=None):
    """
    Computes a transformation matrix based on the extremal points of a mesh.

    If no point indices are provided, the function automatically determines the pairs of points
    that span the longest distances along each axis (X, Y, Z). It then constructs a local
    coordinate system using these vectors and returns the corresponding transformation matrix.

    Args:
        obj (mx.Node or str): The object to evaluate. Can be a mesh node or a transform
            containing a mesh. If a string is passed, it will be encoded as an `mx.Node`.
        ids (list[tuple[int, int]], optional): A list of 3 tuples (x, y, z), each containing
            two vertex indices that define the direction vectors of the transform. If None,
            the function computes them automatically based on the mesh's bounding box.

    Returns:
        tuple[mx.Matrix4, list[tuple[int, int] or None]]:
            - A transformation matrix (`mx.Matrix4`) constructed from the chosen point pairs.
            - A list of the point index pairs used to compute each axis. If a direction is
              inferred using a cross product, the corresponding entry will be `None`.

    Raises:
        TypeError: If the input object is not a mesh or a transform containing a mesh.
        RuntimeError: If the geometry is degenerate (e.g., a line or flat plane).

    Notes:
        - The origin of the resulting matrix is set to the first point in the mesh.
        - The resulting vectors are not normalized; they preserve the original scale of the mesh.
        - If the geometry is flat or linear, one or more axes will be derived using cross products.
    """
    mesh = Mesh(obj)
    if not mesh.shape:
        raise TypeError('not a mesh')

    points = [mx.Vector(p) for p in mesh.get_points()]

    if ids is None:
        # Factorized min/max detection per axis
        extremes = {
            'x': {'min': (0, points[0].x), 'max': (0, points[0].x)},
            'y': {'min': (0, points[0].y), 'max': (0, points[0].y)},
            'z': {'min': (0, points[0].z), 'max': (0, points[0].z)},
        }

        for i, p in enumerate(points):
            for axis, val in zip(('x', 'y', 'z'), (p.x, p.y, p.z)):
                if val < extremes[axis]['min'][1]:
                    extremes[axis]['min'] = (i, val)
                elif val > extremes[axis]['max'][1]:
                    extremes[axis]['max'] = (i, val)

        ids = [
            (extremes['x']['min'][0], extremes['x']['max'][0]),
            (extremes['y']['min'][0], extremes['y']['max'][0]),
            (extremes['z']['min'][0], extremes['z']['max'][0]),
        ]

        x = points[ids[0][1]] - points[ids[0][0]]
        y = points[ids[1][1]] - points[ids[1][0]]
        z = points[ids[2][1]] - points[ids[2][0]]
        vectors = [x, y, z]

        # Flat or degenerate volume? Use scalar triple product (x ^ y) ⋅ z
        triple_product = (x ^ y) * z
        epsilon = 1e-6  # Precision threshold for floating-point comparisons
        if abs(triple_product) < epsilon:
            # Geometry is flat or a line — determine degenerate axis
            xy = x * y
            xz = x * z
            yz = y * z

            min_val, axis = min([(abs(val), idx) for idx, val in enumerate((yz, xz, xy))])
            if min_val == 1:
                raise RuntimeError('geometry is a line')
            ids[axis] = None

    else:
        vectors = [None, None, None]
        if ids[0]:
            vectors[0] = points[ids[0][1]] - points[ids[0][0]]
        if ids[1]:
            vectors[1] = points[ids[1][1]] - points[ids[1][0]]
        if ids[2]:
            vectors[2] = points[ids[2][1]] - points[ids[2][0]]

    # Fill in missing vectors using cross products — ensures a full frame
    if not ids[0]:
        vectors[0] = vectors[1] ^ vectors[2]
    if not ids[1]:
        vectors[1] = vectors[0] ^ vectors[2]
    if not ids[2]:
        vectors[2] = vectors[0] ^ vectors[1]

    # Construct transformation matrix with non-normalized basis vectors
    xfo = mx.Matrix4(
        [
            vectors[0].x, vectors[0].y, vectors[0].z, 0,
            vectors[1].x, vectors[1].y, vectors[1].z, 0,
            vectors[2].x, vectors[2].y, vectors[2].z, 0,
            points[0].x, points[0].y, points[0].z, 1,
        ]
    )
    return xfo, ids


def get_transform_from_components(cps):
    # check args
    nodes = set(mc.ls(cps, o=1))
    if len(nodes) != 1:
        raise ValueError('different shapes!')

    msh = mx.encode(list(nodes)[0])
    if msh.is_a(mx.tTransform):
        msh = msh.shape()
    if not msh.is_a(mx.tMesh):
        raise ValueError('mesh!')
    fn = om.MFnMesh(msh.object())

    cps = mc.ls(cps, flatten=True)

    # get points
    pts = []
    for cp in cps:
        _pts = mc.polyListComponentConversion(cp, fv=1, fe=1, ff=1, tv=1)  # to vertices
        pts += mc.ls(_pts, fl=True)
    pos = [mx.Vector(mc.xform(p, q=1, t=1, ws=1)) for p in pts]

    # transform from triangle
    if len(pts) == 3:
        v0 = pos[1] - pos[0]
        v1 = pos[2] - pos[0]
        v2 = pos[2] - pos[1]
        v0.normalize()
        v1.normalize()
        v2.normalize()
        d0 = abs(v0 * v1)  # dot
        d1 = abs(v0 * v2)  # dot
        d2 = abs(v1 * v2)  # dot
        if d0 <= d1 and d0 <= d2:
            t = v0
            b = v1
        elif d1 <= d0 and d1 <= d2:
            t = v0
            b = v2
        else:
            t = v1
            b = v2
        n = t ^ b  # cross
        n.normalize()
        b = n ^ t
        b.normalize()
        return vectors_to_matrix(t, n, b)

    # get tangent and binormal from edges
    edges = mc.polyListComponentConversion(pts, fv=1, te=1, internal=1)  # to contained edges
    edges = mc.ls(edges, flatten=True)
    n = None

    if len(edges) <= 1:
        # if not enough edges, get normal from vertex face
        vtfs = mc.polyListComponentConversion(cps, fv=1, fe=1, ff=1, tvf=1)  # to vertex faces
        tan_ids = set()
        for vtf in mc.ls(vtfs, fl=True):
            fv_id = re.findall(r"\[(\d+)\]", vtf)
            v, f = map(int, fv_id)
            tan_ids.add(fn.getTangentId(f, v))

        vtf_data = get_vertex_face_vectors(msh, indices=list(tan_ids))
        normals, tangents, binormals = zip(*vtf_data)

        n = mx.Vector()
        for _n in normals:
            n += _n
        n.normalize()

    # get transform
    if len(pts) == 2:

        if n is None:
            e = pos[1] - pos[0]
            x = e * mx.Vector(1, 0, 0)
            y = e * mx.Vector(0, 1, 0)
            z = e * mx.Vector(0, 0, 1)
            if x <= y and x <= z:
                n = mx.Vector(1, 0, 0)
            elif y <= x and y <= z:
                n = mx.Vector(0, 1, 0)
            else:
                n = mx.Vector(0, 0, 1)

        t = pos[1] - pos[0]
        t.normalize()
        b = t ^ n
        b.normalize()
        return vectors_to_matrix(t, n, b)

    if edges:
        # get transform from contained edges
        edge_vectors = [mc.xform(e, q=1, t=1, ws=1) for e in edges]
        edge_vectors = [mx.Vector(e[3:]) - mx.Vector(e[:3]) for e in edge_vectors]
    else:
        # get transform from point cloud
        edges = itertools.combinations(pos, 2)
        edge_vectors = [p1 - p0 for p0, p1 in edges]
    edge_vectors = [e.normalize() for e in edge_vectors]

    d = float('inf')
    best_edges = None
    for v0, v1 in itertools.combinations(edge_vectors, 2):
        d0 = abs(v0 * v1)  # dot
        if d0 < d:
            best_edges = v0, v1
            d = d0

    t, b = best_edges
    n = t ^ b  # cross
    n.normalize()
    b = n ^ t
    b.normalize()
    return vectors_to_matrix(t, n, b)


class OBB(object):
    """
    Oriented Bounding Box (OBB) with methods to access dimensions, transformation, and geometry.
    """

    def __init__(self, center, extents, eigen_vectors, points):
        self._center = center
        self._obb_extents = extents
        self.eigen_vectors = eigen_vectors  # [x_axis, y_axis, z_axis]
        self.points = points

        self.bound_points = self._compute_bounding_points()
        self._matrix = self._compute_matrix()

    @property
    def width(self):
        return (self.bound_points[1] - self.bound_points[0]).length()

    @property
    def height(self):
        return (self.bound_points[2] - self.bound_points[0]).length()

    @property
    def depth(self):
        return (self.bound_points[6] - self.bound_points[0]).length()

    @property
    def volume(self):
        return self.width * self.height * self.depth

    @property
    def matrix(self):
        return self._matrix

    @property
    def center(self):
        return self._center

    @property
    def transform(self):
        return mx.TransformationMatrix(self.matrix)

    @property
    def srt(self):
        tm = self.transform
        s = tm.scale()
        r = tm.rotation()
        t = tm.translation()
        return s, r, t

    def _compute_bounding_points(self):
        c = self._center
        e = self._obb_extents
        ev = self.eigen_vectors

        return [
            c - ev[0] * e.x + ev[1] * e.y + ev[2] * e.z,
            c + ev[0] * e.x + ev[1] * e.y + ev[2] * e.z,
            c - ev[0] * e.x + ev[1] * e.y - ev[2] * e.z,
            c + ev[0] * e.x + ev[1] * e.y - ev[2] * e.z,
            c - ev[0] * e.x - ev[1] * e.y - ev[2] * e.z,
            c + ev[0] * e.x - ev[1] * e.y - ev[2] * e.z,
            c - ev[0] * e.x - ev[1] * e.y + ev[2] * e.z,
            c + ev[0] * e.x - ev[1] * e.y + ev[2] * e.z
        ]

    def _compute_matrix(self):
        """
        Build a 4x4 transformation matrix from axes, center, and extents.

        Returns:
            om.MMatrix
        """

        ev = self.eigen_vectors  # axes
        e = self._obb_extents  # extents
        c = self._center  # center

        # Construct the matrix in Maya's row-major format
        m = [
            ev[1].x * e.y * 2, ev[1].y * e.y * 2, ev[1].z * e.y * 2, 0.0,
            ev[2].x * e.z * 2, ev[2].y * e.z * 2, ev[2].z * e.z * 2, 0.0,
            ev[0].x * e.x * 2, ev[0].y * e.x * 2, ev[0].z * e.x * 2, 0.0,
            c.x, c.y, c.z, 1.0
        ]

        matrix = om.MMatrix(m)

        # Flip orientation if determinant is negative
        if om.MTransformationMatrix(matrix).asMatrix().det4x4() < 0:
            for i in range(8, 11):
                m[i] *= -1  # Flip right vector

        # Reorder to match Maya's expected layout (column-major)
        m_reordered = m[8:12] + m[0:4] + m[4:8] + m[12:]
        return om.MMatrix(m_reordered)

    # builder -----------------------------------------------------------------

    @staticmethod
    def from_mesh(node, method=0):
        try:
            mesh = Mesh(node)
            if not mesh.shape:
                raise RuntimeError('Object has no valid mesh shape.')
        except:
            raise RuntimeError('Invalid input node.')

        points = [mx.Vector(p) for p in mesh.get_points(space=mx.sWorld)]
        triangles = mesh.fn.getTriangles()[1]

        if method == 0:
            return OBB.from_points(points)
        elif method == 1:
            return OBB._from_triangles(points, triangles)
        elif method == 2:
            return OBB._from_hull(points)
        else:
            raise ValueError('Unsupported method (0, 1, or 2 expected).')

    @staticmethod
    def from_points(points):
        cov, mean = OBB.compute_covariance_matrix(points)
        axes = OBB.compute_obb_axes(cov)
        center, extents = OBB.compute_extents_and_center(points, axes)
        return OBB(center, extents, axes, points)

    @staticmethod
    def _from_triangles(points, triangles):
        mu = mx.Vector()
        am = 0.0
        cxx = cxy = cxz = cyy = cyz = czz = 0.0

        for i in range(0, len(triangles), 3):
            p, q, r = points[triangles[i]], points[triangles[i + 1]], points[triangles[i + 2]]
            mui = (p + q + r) / 3.0
            ai = ((q - p) ^ (r - p)).length() * 0.5
            mu += mui * ai
            am += ai

            cxx += (9 * mui.x ** 2 + p.x ** 2 + q.x ** 2 + r.x ** 2) * (ai / 12.0)
            cxy += (9 * mui.x * mui.y + p.x * p.y + q.x * q.y + r.x * r.y) * (ai / 12.0)
            cxz += (9 * mui.x * mui.z + p.x * p.z + q.x * q.z + r.x * r.z) * (ai / 12.0)
            cyy += (9 * mui.y ** 2 + p.y ** 2 + q.y ** 2 + r.y ** 2) * (ai / 12.0)
            cyz += (9 * mui.y * mui.z + p.y * p.z + q.y * q.z + r.y * r.z) * (ai / 12.0)
            czz += (9 * mui.z ** 2 + p.z ** 2 + q.z ** 2 + r.z ** 2) * (ai / 12.0)

        mu /= am
        cov = [
            [cxx / am - mu.x ** 2, cxy / am - mu.x * mu.y, cxz / am - mu.x * mu.z],
            [cxy / am - mu.x * mu.y, cyy / am - mu.y ** 2, cyz / am - mu.y * mu.z],
            [cxz / am - mu.x * mu.z, cyz / am - mu.y * mu.z, czz / am - mu.z ** 2]
        ]
        axes = OBB.compute_obb_axes(cov)
        center, extents = OBB.compute_extents_and_center(points, axes)
        return OBB(center, extents, axes, points)

    @staticmethod
    def _from_hull(points):
        raw_points = [[p.x, p.y, p.z] for p in points]
        hull = QuickHull(raw_points)
        return OBB._from_triangles(points, [i for f in hull.faces for i in f])

    def create_bounding_box_geo(self, name='obb_geo'):
        obb_cube = mc.polyCube(constructionHistory=False, name=name)[0]

        for i, pt in enumerate(self.bound_points):
            mc.xform('{}.vtx[{}]'.format(obb_cube, i), translation=[pt.x, pt.y, pt.z])
        return obb_cube

    # utils -------------------------------------------------------------------

    @staticmethod
    def compute_covariance_matrix(points):
        """
        Compute covariance matrix and mean of a list of om.MVector points.

        Returns:
            (covariance_matrix, mean_point)
        """
        n = len(points)
        if n == 0:
            raise ValueError("Empty point list provided.")

        mean = sum(points, om.MVector()) / float(n)

        # Initialize covariance components
        cxx = cxy = cxz = cyy = cyz = czz = 0.0

        for p in points:
            dx = p.x - mean.x
            dy = p.y - mean.y
            dz = p.z - mean.z

            cxx += dx * dx
            cxy += dx * dy
            cxz += dx * dz
            cyy += dy * dy
            cyz += dy * dz
            czz += dz * dz

        # Normalize
        cov_matrix = [
            [cxx / n, cxy / n, cxz / n],
            [cxy / n, cyy / n, cyz / n],
            [cxz / n, cyz / n, czz / n]
        ]

        return cov_matrix, mean

    @staticmethod
    def compute_obb_axes(cov_matrix):
        """
        Perform eigen decomposition of covariance matrix to obtain OBB axes.

        Returns:
            (axes: list of om.MVector [right, up, forward])
        """
        eig_vals, eig_vecs = eigh(cov_matrix)

        # Columns of eig_vecs are eigenvectors
        axes = [om.MVector(eig_vecs[0][i], eig_vecs[1][i], eig_vecs[2][i]) for i in range(3)]
        for axis in axes:
            axis.normalize()

        return axes

    @staticmethod
    def compute_extents_and_center(points, axes):
        """
        Project points into the eigenvector space to find bounding extents and center.

        Returns:
            (center_in_world: om.MVector, extents: om.MVector)
        """
        min_proj = om.MVector(1e10, 1e10, 1e10)
        max_proj = om.MVector(-1e10, -1e10, -1e10)

        for p in points:
            proj = om.MVector(axes[0] * p, axes[1] * p, axes[2] * p)
            min_proj = om.MVector(
                min(min_proj.x, proj.x),
                min(min_proj.y, proj.y),
                min(min_proj.z, proj.z)
            )
            max_proj = om.MVector(
                max(max_proj.x, proj.x),
                max(max_proj.y, proj.y),
                max(max_proj.z, proj.z)
            )

        center_local = (max_proj + min_proj) * 0.5
        extents = (max_proj - min_proj) * 0.5

        # Transform center from local to world space
        world_center = om.MVector(
            axes[0].x * center_local.x + axes[1].x * center_local.y + axes[2].x * center_local.z,
            axes[0].y * center_local.x + axes[1].y * center_local.y + axes[2].y * center_local.z,
            axes[0].z * center_local.x + axes[1].z * center_local.y + axes[2].z * center_local.z
        )

        return world_center, extents


class HullEdge:
    """Represents an edge between two vertices in the convex hull."""

    def __init__(self, a, b):
        """Initialize edge with two vertex indices.

        Args:
            a (int): Index of first vertex
            b (int): Index of second vertex
        """
        self.a = a
        self.b = b

    def __eq__(self, other):
        """Check equality regardless of vertex order."""
        if not isinstance(other, HullEdge):
            return False
        return {self.a, self.b} == {other.a, other.b}

    def __hash__(self):
        """Allow edges to be stored in sets, ignoring ordering."""
        return hash(tuple(sorted((self.a, self.b))))

    def __repr__(self):
        return "HullEdge({}, {})".format(self.a, self.b)


class HullFace:
    """Represents a triangular face in the convex hull."""

    def __init__(self, a, b, c, vertices):
        """Initialize face with three vertex indices.

        Args:
            a, b, c (int): Vertex indices
            vertices (list): Reference to the vertices list
        """
        self.a = a
        self.b = b
        self.c = c
        self.vertices = vertices

        # Compute plane equation
        self.normal = self._compute_normal()
        self.plane_offset = self._compute_plane_offset()

        # Points that are in front of this face and need to be processed
        self.unassigned_points = set()

    def _compute_normal(self):
        """Compute outward-pointing normal vector."""
        v1 = self.vertices[self.a] - self.vertices[self.b]
        v2 = self.vertices[self.b] - self.vertices[self.c]
        normal = v1 ^ v2
        length = normal.length()
        if length > 0:
            normal /= length
        return normal

    def _compute_plane_offset(self):
        """Compute the plane offset (distance from origin)."""
        return self.normal * self.vertices[self.a]

    def signed_distance_to_point(self, point_index):
        """Calculate signed distance from point to this face's plane.

        Args:
            point_index (int): Index of the point

        Returns:
            float: Signed distance (positive = in front, negative = behind)
        """
        point_vector = self.vertices[point_index] - self.vertices[self.a]
        return self.normal * point_vector

    def is_point_in_front(self, point_index, tolerance=1e-10):
        """Check if point is in front of this face.

        Args:
            point_index (int): Index of the point
            tolerance (float): Numerical tolerance

        Returns:
            bool: True if point is in front
        """
        return self.signed_distance_to_point(point_index) > tolerance

    def get_edges(self):
        """Get all three edges of this face."""
        return [
            HullEdge(self.a, self.b),
            HullEdge(self.b, self.c),
            HullEdge(self.c, self.a)
        ]

    def get_vertices(self):
        """Get all three vertex indices."""
        return [self.a, self.b, self.c]

    def assign_unassigned_points(self, point_indices=None):
        """Find and assign points that are in front of this face.

        Args:
            point_indices (iterable, optional): Specific points to check.
                If None, checks all points.
        """
        if point_indices is None:
            point_indices = range(len(self.vertices))

        self.unassigned_points.clear()
        for point_index in point_indices:
            if self.is_point_in_front(point_index):
                self.unassigned_points.add(point_index)

    def find_furthest_point(self, point_indices=None):
        """Find the point furthest from this face's plane.

        Args:
            point_indices (iterable, optional): Specific points to check.
                If None, checks unassigned points.

        Returns:
            int or None: Index of furthest point
        """
        if point_indices is None:
            point_indices = self.unassigned_points

        if not point_indices:
            return None

        max_distance = -1
        furthest_point = None

        for point_index in point_indices:
            distance = abs(self.signed_distance_to_point(point_index))
            if distance > max_distance:
                max_distance = distance
                furthest_point = point_index

        return furthest_point

    def fix_normal_orientation(self, interior_points):
        """Ensure normal points outward relative to interior points.

        Args:
            interior_points (iterable): Indices of known interior points
        """
        for point_index in interior_points:
            distance = self.signed_distance_to_point(point_index)
            if abs(distance) < 1e-10:
                continue

            if distance > 0:  # Normal points inward
                self.normal *= -1
                self.plane_offset = -self.plane_offset
            return

    def __eq__(self, other):
        """Check equality based on having the same vertices."""
        if not isinstance(other, HullFace):
            return False
        return {self.a, self.b, self.c} == {other.a, other.b, other.c}

    def __hash__(self):
        """Allows faces to be stored in sets, ignoring ordering."""
        return hash(tuple(sorted((self.a, self.b, self.c))))

    def __getitem__(self, i):
        if not isinstance(i, int) or not 0 <= i <= 2:
            raise IndexError('face vertices are 0, 1 or 2')
        if i == 0:
            return self.a
        elif i == 1:
            return self.b
        elif i == 2:
            return self.c

    def __iter__(self):
        for i in range(3):
            yield self[i]

    def __repr__(self):
        return "HullFace({}, {}, {})".format(self.a, self.b, self.c)


class QuickHull:
    """3D QuickHull algorithm implementation."""

    def __init__(self, points):
        """Initialize QuickHull with a list of 3D points.

        Args:
            points (list): List of 3D points (will be converted to mx.Vector)
        """
        if len(points) < 4:
            raise ValueError("At least 4 points are required for 3D convex hull")

        self.vertices = [mx.Vector(p) for p in points]
        self.faces = []
        self.hull_vertex_indices = set()

        self._build_hull()

    def _build_hull(self):
        """Build the convex hull using QuickHull algorithm."""
        # Phase 1: Create initial tetrahedron
        tetrahedron_vertices = self._create_initial_tetrahedron()

        # Phase 2: Expand hull by processing remaining points
        self._expand_hull(tetrahedron_vertices)

        # Phase 3: Extract final hull vertices
        self._extract_hull_vertices()

    def _create_initial_tetrahedron(self):
        """Create initial tetrahedron from 4 extreme points.

        Returns:
            list: Indices of the 4 tetrahedron vertices
        """
        # Find initial edge (longest between extreme points)
        initial_edge = QuickHull.find_initial_edge(self.vertices)
        if not initial_edge:
            raise RuntimeError("Could not find initial edge")

        vertex_0 = initial_edge.a
        vertex_1 = initial_edge.b

        # Find third point (furthest from initial edge)
        vertex_2 = QuickHull.find_furthest_point_from_edge(initial_edge, self.vertices)
        if vertex_2 is None:
            raise RuntimeError("Could not find third vertex")

        # Create initial triangle and find fourth point
        initial_face = HullFace(vertex_0, vertex_1, vertex_2, self.vertices)
        vertex_3 = initial_face.find_furthest_point(range(len(self.vertices)))
        if vertex_3 is None:
            raise RuntimeError("Could not find fourth vertex")

        tetrahedron_vertices = [vertex_0, vertex_1, vertex_2, vertex_3]

        # Create the 4 faces of the tetrahedron
        self.faces = [
            HullFace(vertex_0, vertex_1, vertex_2, self.vertices),
            HullFace(vertex_0, vertex_1, vertex_3, self.vertices),
            HullFace(vertex_0, vertex_3, vertex_2, self.vertices),
            HullFace(vertex_1, vertex_2, vertex_3, self.vertices)
        ]

        # Fix normal orientations
        for face in self.faces:
            face.fix_normal_orientation(tetrahedron_vertices)

        # Assign unassigned points to faces
        for face in self.faces:
            face.assign_unassigned_points()

        return tetrahedron_vertices

    def _expand_hull(self, interior_points):
        """Expand hull by processing unassigned points.

        Args:
            interior_points (list): Known interior points for normal orientation
        """
        while True:
            # Find a face with unassigned points
            active_face = None
            for face in self.faces:
                if face.unassigned_points:
                    active_face = face
                    break

            if not active_face:
                break  # No more points to process

            # Find the furthest point from this face
            eye_point = active_face.find_furthest_point()
            if eye_point is None:
                continue

            # Find horizon edges and visible faces
            horizon_edges, visible_faces = self._find_horizon(eye_point)

            # Remove visible faces
            for face in visible_faces:
                self.faces.remove(face)

            # Collect all unassigned points from visible faces
            all_unassigned = set()
            for face in visible_faces:
                all_unassigned.update(face.unassigned_points)

            # Create new faces from horizon edges to eye point
            for edge in horizon_edges:
                new_face = HullFace(edge.a, edge.b, eye_point, self.vertices)
                new_face.fix_normal_orientation(interior_points)
                new_face.assign_unassigned_points(all_unassigned.copy())
                self.faces.append(new_face)

    def _find_horizon(self, eye_point):
        """Find horizon edges visible from eye point.

        Args:
            eye_point (int): Index of the eye point

        Returns:
            tuple: (horizon_edges, visible_faces)
        """
        horizon_edges = set()
        visible_faces = []

        def explore_face(face, visited):
            """Recursively explore visible faces."""
            if face in visited:
                return

            if not face.is_point_in_front(eye_point):
                return

            visited.add(face)
            visible_faces.append(face)

            # Check each edge of this face
            for edge in face.get_edges():
                adjacent_face = self._find_adjacent_face(face, edge)
                if adjacent_face and adjacent_face not in visited:
                    if not adjacent_face.is_point_in_front(eye_point):
                        # This edge is on the horizon
                        horizon_edges.add(edge)
                    else:
                        # Continue exploring
                        explore_face(adjacent_face, visited)

        # Start exploration from faces that can see the eye point
        visited = set()
        for face in self.faces:
            if face.is_point_in_front(eye_point):
                explore_face(face, visited)
                break

        return horizon_edges, visible_faces

    def _find_adjacent_face(self, current_face, edge):
        """Find face adjacent to current_face along the given edge.

        Args:
            current_face (HullFace): The current face
            edge (HullEdge): The shared edge

        Returns:
            Face or None: Adjacent face, or None if not found
        """
        for face in self.faces:
            if face is current_face:
                continue
            if edge in face.get_edges():
                return face
        return None

    def _extract_hull_vertices(self):
        """Extract unique vertex indices from all faces."""
        self.hull_vertex_indices.clear()
        for face in self.faces:
            self.hull_vertex_indices.update(face.get_vertices())

    def get_faces(self):
        """Get all faces of the convex hull.

        Returns:
            list: List of Face objects
        """
        return self.faces[:]

    def get_vertices(self):
        """Get vertices that form the convex hull.

        Returns:
            list: List of vertex indices
        """
        return list(self.hull_vertex_indices)

    def get_triangles(self):
        """Get triangle data for mesh generation.

        Returns:
            list: List of (vertex_a, vertex_b, vertex_c) tuples
        """
        return [(face.a, face.b, face.c) for face in self.faces]

    @staticmethod
    def find_extreme_points(vertices):
        """Find extreme points along each axis.

        Args:
            vertices (list): List of 3D vertices

        Returns:
            tuple: Indices of (x_min, x_max, y_min, y_max, z_min, z_max)
        """
        if not vertices:
            return None

        x_min = x_max = y_min = y_max = z_min = z_max = 0
        min_x = max_x = vertices[0].x
        min_y = max_y = vertices[0].y
        min_z = max_z = vertices[0].z

        for i, vertex in enumerate(vertices):
            if vertex.x < min_x:
                min_x, x_min = vertex.x, i
            if vertex.x > max_x:
                max_x, x_max = vertex.x, i
            if vertex.y < min_y:
                min_y, y_min = vertex.y, i
            if vertex.y > max_y:
                max_y, y_max = vertex.y, i
            if vertex.z < min_z:
                min_z, z_min = vertex.z, i
            if vertex.z > max_z:
                max_z, z_max = vertex.z, i

        return x_min, x_max, y_min, y_max, z_min, z_max

    @staticmethod
    def find_initial_edge(vertices):
        """Find the longest edge between extreme points.

        Args:
            vertices (list): List of 3D vertices

        Returns:
            HullEdge: The edge with maximum distance
        """
        extremes = QuickHull.find_extreme_points(vertices)
        if not extremes:
            return None

        max_distance = -1
        best_edge = None

        for i in range(6):
            for j in range(i + 1, 6):
                distance = (vertices[extremes[i]] - vertices[extremes[j]]).length()
                if distance > max_distance:
                    max_distance = distance
                    best_edge = HullEdge(extremes[i], extremes[j])

        return best_edge

    @staticmethod
    def find_furthest_point_from_edge(edge, vertices):
        """Find point furthest from an edge line.

        Args:
            edge (HullEdge): The edge
            vertices (list): List of vertices

        Returns:
            int or None: Index of furthest point
        """
        max_distance = -1
        furthest_point = None

        for i in range(len(vertices)):
            if i in (edge.a, edge.b):
                continue

            # Calculate perpendicular distance to edge line
            p0 = vertices[i] - vertices[edge.a]
            p1 = vertices[i] - vertices[edge.b]
            cross = p0 ^ p1
            edge_length = (vertices[edge.b] - vertices[edge.a]).length()

            if edge_length == 0:
                continue

            distance = cross.length() / edge_length
            if distance > max_distance:
                max_distance = distance
                furthest_point = i

        return furthest_point

    def generate_mesh(self, mesh_name="convex_hull"):
        """Create a Maya mesh from QuickHull results.

        Args:
            mesh_name (str): Base name for the mesh (will be made unique)

        Returns:
            str: Final name of the created mesh
        """
        # Get triangles and vertices from QuickHull
        triangles = self.get_triangles()
        vertices = self.vertices

        if not triangles:
            raise RuntimeError("No triangles found in QuickHull result")

        # Prepare Maya mesh data
        points = []
        vertex_connections = []
        polygon_counts = []
        vertex_index_map = {}

        # Build vertex list and index mapping
        # Only include vertices that are actually used in triangles
        used_vertices = set()
        for triangle in triangles:
            used_vertices.update(triangle)

        # Create mapping from original indices to new compact indices
        for i, original_index in enumerate(sorted(used_vertices)):
            vertex_index_map[original_index] = i
            vertex = vertices[original_index]
            points.append(om.MPoint(vertex.x, vertex.y, vertex.z))

        # Build triangle connections using new indices
        for triangle in triangles:
            vertex_a, vertex_b, vertex_c = triangle
            vertex_connections.extend([
                vertex_index_map[vertex_a],
                vertex_index_map[vertex_b],
                vertex_index_map[vertex_c]
            ])
            polygon_counts.append(3)  # Each triangle has 3 vertices

        # Create the mesh
        mesh_fn = om.MFnMesh()
        mesh_obj = mesh_fn.create(points, polygon_counts, vertex_connections)

        # Get the mesh DAG path and name
        mesh_dag = om.MDagPath.getAPathTo(mesh_obj)
        mesh_path = mesh_dag.fullPathName()

        # Apply post-processing
        # Recalculate normals to ensure they point outward
        mc.polyNormal(mesh_path, normalMode=2, userNormalMode=0, ch=0)

        # Add to default shading group
        mc.sets(mesh_path, add="initialShadingGroup")

        # Select and rename the mesh
        mc.select(mesh_path)
        return mc.rename(mesh_path, "{}#".format(mesh_name))
