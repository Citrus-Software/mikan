# coding: utf-8

import copy
import math
from itertools import groupby

import maya.cmds as mc
import maya.api.OpenMaya as om

from mikan.core.utils import re_get_keys
from mikan.core.logger import create_logger

from mikan.maya import cmdx as mx

from mikan.maya.lib.geometry import Mesh, OBB
from mikan.maya.utils.topology_utils.matrix import (
    matrix_build, matrix_get_row, utils_get_matrix, matrix_get_projected_vector_on_closest_axe,
    matrix_normalize
)


def lru_cache(maxsize=None):
    def lru_cache_deco(func):
        return func

    return lru_cache_deco


MAYA_VERSION = int(mc.about(version=True))
if 2022 <= MAYA_VERSION:
    from functools import lru_cache

log = create_logger('mikan.topology')


class Component(object):
    def __init__(self):
        self.mesh_data = None
        self.id = None

    @classmethod
    def create_empty(cls, mesh_data):
        c = cls()
        c.mesh_data = mesh_data
        return c

    @classmethod
    def create_from_id(cls, mesh_data, i):
        c = cls.create_empty(mesh_data)
        c.id = i
        return c

    def __hash__(self):
        return hash(self.__class__.__name__) ^ hash(self.mesh_data.geo_name) ^ hash(self.id)

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            if self.mesh_data.geo_name == other.mesh_data.geo_name:
                if self.id == other.id:
                    return True
        return False


class Vertex(Component):
    def __init__(self):
        super(Vertex, self).__init__()

    @property
    def pos(self):
        return self.mesh_data.vertex_positions[self.id]

    @property
    def normal(self):
        return self.mesh_data.vertex_normals[self.id]

    @property
    def neighbors(self):  # get_vertex_neighbor_ids
        vertices = [self.mesh_data.vertices[i] for i in self.mesh_data.vertex_id_adjacency_list[self.id]]
        return VertexGroup.create_from_vertices(vertices)

    @property
    def edges(self):
        edges = [self.mesh_data.edges[i] for i in self.mesh_data.vertex_id_to_edge_ids[self.id]]
        return EdgeGroup.create_from_edges(edges)

    @property
    def edge_flows(self):
        efs = []
        for i in self.mesh_data.vertex_id_to_edge_ids[self.id]:
            efs.append(EdgeFlow.create_from_edge(self.mesh_data.edges[i], self))
        return efs

    def __lshift__(self, other):
        # Va >> Vb # get_vertex_shortest_path --> edge flow
        edges_a = self.edges()
        edges_b = other.edges()
        for eA in edges_a:
            for eB in edges_b:
                if eA == eB:
                    return eA
        return None

    def __rshift__(self, other):
        return self.__lshift__(other)

    def name(self):
        return '{}.vtx[{}]'.format(self.mesh_data.geo_name, self.id)

    def generate_matrix(self):
        # utils
        axes = ['x', 'y', 'z']
        i_axe_dir = 1
        i_axe_up = 0
        i_axe_side = 2

        # get dirs
        v_dir = om.MVector(0, -1, 0)
        v_up = self.normal
        v_side = v_up ^ v_dir
        v_dir = v_side ^ v_up

        v_up.normalize()
        v_side.normalize()
        v_dir.normalize()

        # build matrix
        kw = {}
        kw['p'] = self.pos
        kw['orthogonize'] = True
        kw['normalize'] = False
        kw['ref_axe'] = axes[i_axe_dir]
        kw['middle_axe'] = axes[i_axe_up]
        kw['v{}'.format(axes[i_axe_dir].upper())] = v_dir
        kw['v{}'.format(axes[i_axe_up].upper())] = v_up
        kw['v{}'.format(axes[i_axe_side].upper())] = v_side
        m = matrix_build(**kw)

        return m

    def is_inside_cube(self, m, axe_positive=1):
        self.pos

        vx = matrix_get_row(0, m)
        vy = matrix_get_row(1, m)
        vz = matrix_get_row(2, m)
        p = matrix_get_row(3, m)

        pa = p + vx + vy + vz
        pb = p - vx - vz

        va = self.pos - pa
        vb = self.pos - pb

        if 0 < va * (vx * -1) and 0 < va * (vy * -1) and 0 < va * (vz * -1):
            if 0 < vb * (vx) and 0 < vb * (vy) and 0 < vb * (vz):
                return True
        return False


class Edge(Component):
    def __init__(self):
        super(Edge, self).__init__()

    @staticmethod
    def create_from_two_vertices(va, vb):
        e = Edge()
        e.mesh_data = va.mesh_data

        vertex_id_neighbor = e.mesh_data.vertex_id_adjacency_list[va.id]
        edge_id_neighbor = e.mesh_data.vertex_id_to_edge_ids[va.id]

        if not vb.id in vertex_id_neighbor:
            return None

        i = vertex_id_neighbor.index(vb.id)
        e.id = edge_id_neighbor[i]

        return e

    @lru_cache(maxsize=32)
    def _get_vertices_cached(self, _instance):
        vertices = [self.mesh_data.vertices[i] for i in self.mesh_data.edge_id_to_vertex_ids[self.id]]
        return VertexGroup.create_from_vertices(vertices)

    @property
    def vertices(self):
        return self._get_vertices_cached(self)

    @property
    def neighbors(self):  # get_vertex_neighbor_ids
        edges = []
        for vId in self.mesh_data.edge_id_to_vertex_ids[self.id]:
            for eId in self.mesh_data.vertex_id_to_edge_ids[vId]:
                E = self.mesh_data.edges[eId]
                if E != self:
                    edges.append(self.mesh_data.edges[eId])

        eg = EdgeGroup.create_from_edges(edges)
        return eg

    @property
    def pos(self):
        return self.vertices.get_center_position()

    def __getitem__(self, i):
        if isinstance(i, int):
            return self.vertices[i]
        else:
            return VertexGroup.create_from_vertices([self.vertices[iV] for iV in self.ids[i]])

    def __iter__(self):
        for V in self.vertices:
            yield V

    def __contains__(self, elem):  # E in self
        if isinstance(elem, list):
            return all([self.__contains__(E) for E in elem])
        elif isinstance(elem, Vertex):
            return elem in self.vertices
        elif isinstance(elem, VertexGroup):
            return all(V in self.vertices for V in elem)
        return False

    def __floordiv__(self, other):  # //
        # get other vertex
        vertices_a = self.vertices
        vertices_b = other.vertices
        if vertices_a[0] == vertices_b[0] or vertices_a[0] == vertices_b[1]:
            return vertices_a[1]
        elif vertices_a[1] == vertices_b[1] or vertices_a[1] == vertices_b[0]:
            return vertices_a[0]
        return None

    def __sub__(self, other):  # -
        if isinstance(other, Vertex):
            i = self[0].id
            if i == other.id:
                i = self[1].id
            return Vertex.create_from_id(self.mesh_data, i)
        return None

    def index(self, elem):
        if isinstance(elem, Vertex):
            v = elem
            return self.vertices.index(v)

        elif isinstance(elem, Edge):
            e = elem

            vg_a = self.vertices
            vg_b = e.vertices
            indices = []
            if vg_b[0] in vg_a:
                indices.append(vg_a.index(vg_b[0]))
            if vg_b[1] in vg_a:
                indices.append(vg_a.index(vg_b[1]))

            return indices
        return None

    def get_common_vertices(self, other):
        # get common vertex
        vs_a = self.vertices
        vs_b = other.vertices
        if self == other:
            return VertexGroup.create_from_vertices(vs_a[:])
        elif vs_a[0] == vs_b[0] or vs_a[0] == vs_b[1]:
            return VertexGroup.create_from_vertices([vs_a[0]])
        elif vs_a[1] == vs_b[1] or vs_a[1] == vs_b[0]:
            return VertexGroup.create_from_vertices([vs_a[1]])
        return None

    def get_center_position(self):
        pts = [V.pos for V in self]
        bb_center = get_bounding_box_center_from_points(pts)
        return bb_center

    def is_neighbor(self, E):
        is_neighbor = False
        if E[0] in self[0].neighbors and E[1] in self[1].neighbors:
            is_neighbor = True
        elif E[0] in self[1].neighbors and E[1] in self[0].neighbors:
            is_neighbor = True
        return is_neighbor

    def name(self):
        return '%s.e[%s]' % (self.mesh_data.geo_name, self.id)

    def length(self):
        return (self.vertices[0].pos - self.vertices[1].pos).length()


class ComponentGroup(object):
    """ ids must be unique """

    def __init__(self):
        self.mesh_data = None
        self.ids = []

    @classmethod
    def create_empty(cls, mesh_data):
        c = cls()
        c.mesh_data = mesh_data
        return c

    @classmethod
    def create_from_ids(cls, mesh_data, ids):
        cg = cls.create_empty(mesh_data)
        cg.ids = ids
        return cg

    @classmethod
    def create_from_components(cls, components):
        Cg = cls.create_empty(components[0].mesh_data)
        Cg.ids = [C.id for C in components]
        return Cg

    def __len__(self):
        return len(self.ids)

    def __getitem__(self, i):
        raise RuntimeError('__getitem__ to override in class child')

    def __iter__(self):
        for i in range(self.__len__()):
            yield self[i]

    def __iadd__(self, other):
        raise RuntimeError('__iadd__ to override in class child')

    def __add__(self, other):
        cg = copy.deepcopy(self)
        result = cg.__iadd__(other)
        if not result:
            return None
        return cg

    def __isub__(self, other):
        raise RuntimeError('__isub__ to override in class child')

    def __sub__(self, other):
        cg = copy.deepcopy(self)
        cg.__isub__(other)
        return cg

    def __copy__(self):
        cg = self.__class__()
        cg.mesh_data = self.mesh_data
        cg.ids = self.ids
        return cg

    def __deepcopy__(self, memo):
        cg = self.__class__()
        cg.mesh_data = self.mesh_data
        cg.ids = self.ids[:]
        return cg

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return sorted(self.ids) == sorted(other.ids)
        return False

    def __hash__(self):
        return hash(self.__class__.__name__) ^ hash(self.mesh_data.geo_name) ^ hash(self.ids)

    def index(self, c):
        if c.id in self.ids:
            return self.ids.index(c.id)
        return -1

    def reverse(self):
        self.ids.reverse()
        return self


class VertexGroup(ComponentGroup):
    """ ids must be unique """

    def __init__(self):
        super(VertexGroup, self).__init__()

    @classmethod
    def create_from_vertices(cls, vertices):
        return cls.create_from_components(vertices)

    @classmethod
    def create_from_vertex_group(cls, vg):
        return copy.deepcopy(vg)

    @property
    def neighbors(self):  # get_vertex_neighbor_ids
        vg = VertexGroup.create_empty(self.mesh_data)
        for v in self:
            vg_n = v.neighbors
            vg += vg_n
        vg -= self
        return vg

    def grow(self, iteration=1):  # get_vertex_neighbor_ids
        for _ in range(iteration):
            self += self.neighbors

    def __getitem__(self, i):
        if isinstance(i, int):
            return self.mesh_data.vertices[self.ids[i]]
        else:
            return VertexGroup.create_from_vertices([self.mesh_data.vertices[iV] for iV in self.ids[i]])

    def __iadd__(self, other):
        if isinstance(other, list):
            for elem in other:
                self.__iadd__(elem)
        elif isinstance(other, Vertex):
            if other.id not in self.ids:
                self.ids.append(other.id)
        elif isinstance(other, VertexGroup):
            for i in other.ids:
                if i not in self.ids:
                    self.ids.append(i)
        elif isinstance(other, Edge):
            for i in other.vertices.ids:
                if i not in self.ids:
                    self.ids.append(i)
        elif isinstance(other, EdgeGroup) or isinstance(other, EdgeFlow) or isinstance(other, EdgeLoop):

            for e in other:
                for i in e.vertices.ids:
                    if i not in self.ids:
                        self.ids.append(i)
        return self

    def __isub__(self, other):
        if isinstance(other, list):
            for elem in other:
                self.__isub__(elem)
        elif isinstance(other, Vertex):
            if other.id in self.ids:
                self.ids.remove(other.id)
        elif isinstance(other, VertexGroup):
            for i in other.ids:
                if i in self.ids:
                    self.ids.remove(i)
        elif isinstance(other, Edge):
            for i in other.vertices.ids:
                if i in self.ids:
                    self.ids.remove(i)
        elif isinstance(other, (EdgeGroup, EdgeFlow, EdgeLoop)):
            for e in other:
                for i in e.vertices.ids:
                    if i in self.ids:
                        self.ids.remove(i)
        return self

    def __contains__(self, elem):  # E in self
        if isinstance(elem, list):
            return all([self.__contains__(e) for e in elem])
        elif isinstance(elem, Vertex):
            return elem.id in self.ids
        elif isinstance(elem, VertexGroup):
            return all(i in self.ids for i in elem.ids)
        elif isinstance(elem, Edge):
            return all(v.id in self.ids for v in elem.vertices)
        elif isinstance(elem, (EdgeGroup, EdgeFlow, EdgeLoop)):
            return all(v.id in self.ids for e in elem for v in e.vertices)

    def get_center_position(self):
        pts = [v.pos for v in self]
        bb_center = get_bounding_box_center_from_points(pts)
        return bb_center

    def generate_matrix(self):
        pts = [v.pos for v in self]
        m = OBB.from_points(pts).matrix
        m = matrix_normalize(m)
        return m

    def edges(self):
        return EdgeGroup.create_from_edges([e for v in self for e in v.edges])

    def names(self):
        return ['%s.vtx[%s]' % (self.mesh_data.geo_name, i) for i in self.ids]


# vtx_group.remove(edge_group) or list[edge_group]
# vtx_group.remove(vtx_group) or list[Vertex]


class EdgeGroup(ComponentGroup):
    """ ids must be unique """

    def __init__(self):
        super(EdgeGroup, self).__init__()

    @classmethod
    def create_from_edges(cls, edges):
        return cls.create_from_components(edges)

    @classmethod
    def create_from_edge_names(cls, mesh_data, edge_names):
        names = mesh_data.filter_component_names(edge_names, mesh_data.geo_name)
        names = [name for name in names if 'e.[' in name]
        if not names:
            return None
        ids = mesh_data.get_component_ids(names)
        return cls.create_from_ids(mesh_data, ids)

    @classmethod
    def create_from_vertex_group(cls, vg):
        eg = cls.create_empty(vg.mesh_data)
        for iA, Va in enumerate(vg):
            for iB, Vb in enumerate(vg):
                if iA == iB:
                    continue
                E = Edge.create_from_two_vertices(Va, Vb)
                if E:
                    eg += E
        return eg

    @classmethod
    def create_from_edge_group(cls, edge_grp):
        return copy.deepcopy(edge_grp)

    @lru_cache(maxsize=32)
    def _get_vertices_cached(self, _instance):
        return VertexGroup.create_from_vertices([V for E in self for V in E.vertices])

    @property
    def vertices(self):
        return self._get_vertices_cached(self)

    @property
    def neighbors(self):  # get_vertex_neighbor_ids
        eg = EdgeGroup.create_empty(self.mesh_data)
        for E in self:
            eg_n = E.neighbors
            eg += eg_n
        eg -= self
        return eg

    def grow(self, iteration=1):  # get_vertex_neighbor_ids
        for _ in range(iteration):
            self += self.neighbors

    def __getitem__(self, i):
        if isinstance(i, int):
            return self.mesh_data.edges[self.ids[i]]
        else:
            return EdgeGroup.create_from_edges([self.mesh_data.edges[i] for i in self.ids[i]])

    def __iadd__(self, other):
        if isinstance(other, list):
            for elem in other:
                self.__iadd__(elem)
        elif isinstance(other, Vertex):
            not_sharing_vs = self.get_not_sharing_vertices()

            for v in not_sharing_vs:
                e = Edge.create_from_two_vertices(v, other)
                if e and e.id not in self.ids:
                    self.ids.append(e.id)

        elif isinstance(other, VertexGroup):
            not_sharing_vs = self.get_not_sharing_vertices()

            for v in other:
                for n_v in not_sharing_vs:
                    e = Edge.create_from_two_vertices(n_v, v)
                    if e and e.id not in self.ids:
                        self.ids.append(e.id)
        elif isinstance(other, Edge):
            if other.id not in self.ids:
                self.ids.append(other.id)
        elif isinstance(other, (EdgeGroup, EdgeFlow, EdgeLoop)):
            for i in other.ids:
                if i not in self.ids:
                    self.ids.append(i)
        return self

    def __isub__(self, other):
        if isinstance(other, list):
            for elem in other:
                self.__isub__(elem)
        elif isinstance(other, Vertex):
            not_sharing_vs = self.get_not_sharing_vertices()

            for v in not_sharing_vs:
                e = Edge.create_from_two_vertices(v, other)
                if e and e.id in self.ids:
                    self.ids.remove(e.id)

        elif isinstance(other, VertexGroup):
            not_sharing_vs = self.get_not_sharing_vertices()

            for v in other:
                for n_v in not_sharing_vs:
                    e = Edge.create_from_two_vertices(n_v, v)
                    if e and e.id in self.ids:
                        self.ids.remove(e.id)

        elif isinstance(other, Edge):
            if other.id in self.ids:
                self.ids.remove(other.id)
        elif isinstance(other, (EdgeGroup, EdgeFlow, EdgeLoop)):
            for i in other.ids:
                if i in self.ids:
                    self.ids.remove(i)
        return self

    def __contains__(self, elem):  # E in self
        if isinstance(elem, list):
            return all([self.__contains__(e) for e in elem])
        elif isinstance(elem, Vertex):
            return elem.id in self.ids
        elif isinstance(elem, VertexGroup):
            return all(i in self.ids for i in elem.ids)
        elif isinstance(elem, Edge):
            return elem.id in self.ids
        elif isinstance(elem, (EdgeGroup, EdgeFlow, EdgeLoop)):
            return all(e.id in self.ids for e in elem)

    def group_by_neighbors(self):  # regroup_edge_ids_by_neighbor
        e_groups = []
        for e in self:
            e_groups.append(EdgeGroup.create_from_edges([e]))

        max_iter = 500
        for _ in range(max_iter):

            found_neighbor = False

            for i_a, eg_a in enumerate(e_groups):
                for i_b, eg_b in enumerate(e_groups):

                    if i_a == i_b:
                        continue
                    if not eg_a or not eg_b:
                        continue

                    for e_a in eg_a:
                        for eB in eg_b:

                            if eB in eg_a and e_a in eg_b:
                                continue

                            if e_a.get_common_vertices(eB):
                                found_neighbor = True
                                e_groups[i_a] += e_groups[i_b]
                                e_groups[i_b] = None

            if not found_neighbor:
                break

        # # remove_duplicate and inside_others
        # _E_groups = []
        # for iA, EgA in enumerate(E_groups):
        #     is_inside_other = False
        #     is_equal_to_other = False
        #     for iB, EgB in enumerate(E_groups):
        #         if iA == iB: continue
        #
        #         if EgA == EgB:
        #             is_equal_to_other = True
        #             break
        #
        #         if EgA in EgB or EgB in EgA:
        #             is_inside_other = True
        #             break
        #     if not is_inside_other and not is_equal_to_other:
        #         _E_groups.append(EgA)
        #
        # E_groups = _E_groups

        e_groups = list(filter(lambda x: x is not None, e_groups))
        return e_groups

    def get_not_sharing_vertices(self):
        vertices = [v for e in self for v in e.vertices]

        count = {}
        for i_a, va in enumerate(vertices):
            count.setdefault(vertices[i_a], 0)
            count[vertices[i_a]] += 1

        not_sharing_vertices = []
        for v in vertices:
            if count[v] == 1:
                not_sharing_vertices.append(v)

        return not_sharing_vertices

    def get_common_vertices(self, e_flow_other):

        common_vertices = VertexGroup()
        for e_a in self:
            for e_b in e_flow_other:
                if e_a == e_b:
                    continue
                common_vertex = e_a.get_common_vertices(e_b)
                if common_vertex:
                    common_vertices + common_vertex

        return common_vertices

    def get_center_position(self):
        return self.vertices.get_center_position()

    def generate_matrix(self):
        return self.vertices.generate_matrix()

    def sort_with_neighbor(self):

        max_iter = 500
        islands = [[e] for e in self]
        for _ in range(max_iter):
            something_change = False
            for i, _ in enumerate(islands):
                for i_b, e_b in enumerate(self):

                    if i == i_b:
                        continue

                    if e_b in islands[i]:
                        continue

                    e_start = islands[i][0]
                    e_end = islands[i][-1]
                    if e_start.index(e_b):
                        islands[i] = [e_b] + islands[i]
                        something_change = True
                    elif e_end.index(e_b):
                        islands[i] = islands[i] + [e_b]
                        something_change = True

            if not something_change:
                break

        sizes = list(map(len, islands))
        if max(sizes) != len(self):
            return False

        i_max = sizes.index(max(sizes))
        self.ids = [e.id for e in islands[i_max]]

        return True

    def sort_ids_with_neighbor_ref(self, edge_group_ref):

        edge_sorted = []
        for e_ref in edge_group_ref:
            for e in self:

                if e in edge_sorted:
                    continue

                if e.is_neighbor(e_ref):
                    edge_sorted.append(e)

                    # get the remain edges
        for _ in range(500):
            something_happened = False
            for e in self:
                if e not in edge_sorted:
                    for i in range(len(edge_sorted)):
                        if e.is_neighbor(edge_sorted[i]):
                            edge_sorted.insert(i + 1, e)
                            something_happened = True

            if not something_happened:
                break

        self.ids = [e.id for e in edge_sorted]

    def from_vertex_find_connected_edges_in_group(self, v_to_search):
        es_found = []
        for e in self:
            if v_to_search in e:
                es_found.append(e)
        return es_found

    def names(self):
        return ['{}.e[{}]'.format(self.mesh_data.geo_name, i) for i in self.ids]


def edge_is_in(e, components):
    for cp in components:
        if isinstance(cp, Edge):
            if e == cp:
                return True
        elif isinstance(cp, EdgeGroup) or isinstance(cp, EdgeFlow) or isinstance(cp, EdgeLoop):
            if e in cp:
                return True
    return False


def vertex_is_in(v, components):
    for cp in components:
        if isinstance(cp, Edge):
            if v in cp.vertices:
                return True
        elif isinstance(cp, EdgeGroup) or isinstance(cp, EdgeFlow) or isinstance(cp, EdgeLoop):
            if v in cp.vertices:
                return True
        elif isinstance(cp, Vertex):
            if v == cp:
                return True
        elif isinstance(cp, VertexGroup):
            if v in cp:
                return True
    return False


def get_connected_path_from_two_edge_flow_lists(edge_flows_a, edge_flows_b, paths_association_2_by_2):
    # are they connected to themselves
    connected_paths = []
    for ef in edge_flows_a + edge_flows_b:
        if ef.is_loop():
            connected_paths.append(ef)

    # get connected paths   
    if not connected_paths:
        if paths_association_2_by_2:
            if len(edge_flows_a) != len(edge_flows_b):
                return None
            for i in range(len(edge_flows_a)):
                ef_a = edge_flows_a[i]
                ef_b = edge_flows_b[i]
                if ef_a.vertices[-1] in ef_b.vertices or ef_b.vertices[-1] in ef_a.vertices:
                    connected_path = ef_a + copy.deepcopy(ef_b).reverse()
                    if connected_path:
                        connected_paths.append(connected_path)
        else:
            for ef_a in edge_flows_a:
                for ef_b in edge_flows_b:
                    if ef_a.vertices[-1] in ef_b.vertices or ef_b.vertices[-1] in ef_a.vertices:
                        connected_path = ef_a + copy.deepcopy(ef_b).reverse()
                        if connected_path:
                            connected_paths.append(connected_path)

    if not connected_paths:
        return None

    # sort connected paths - shortest vtx
    shortest_connected_path = []

    nbr_edges_min = min([len(ef) for ef in connected_paths])
    for ef in connected_paths:
        if len(ef) == nbr_edges_min:
            shortest_connected_path.append(ef)

    if not shortest_connected_path:
        return None

    if len(shortest_connected_path) == 1:
        return shortest_connected_path[0]

    # sort connected paths - shortest length from middle axe
    same_end_vertex_dict = {}
    for ef in shortest_connected_path:
        same_end_vertex_dict.setdefault(ef.vertices[-1], [])
        same_end_vertex_dict[ef.vertices[-1]].append(ef)

    if len(shortest_connected_path) != len(list(same_end_vertex_dict.keys())):

        grown_branches_new = []
        for v in same_end_vertex_dict:
            ef_shortest = None
            for ef in same_end_vertex_dict[v]:
                if ef_shortest:
                    if ef.max_dist_from_middle_axe() < ef_shortest.max_dist_from_middle_axe():
                        ef_shortest = ef
                else:
                    ef_shortest = ef
            grown_branches_new.append(ef_shortest)

        shortest_connected_path = grown_branches_new

    if not shortest_connected_path:
        return None

    return shortest_connected_path[0]


class EdgeFlow(EdgeGroup):
    def __init__(self):
        super(EdgeFlow, self).__init__()
        self.first_vertex_id = None

    @classmethod
    def create_from_two_edges_flows_with_shortest_path(
            cls,
            ef_as,
            ef_bs,
            skip_components=None,
            only_forward_policy=False,
            paths_association_2_by_2=False,
            max_step=None,
    ):

        if skip_components is None:
            skip_components = []

        paths_a_n_b = [ef_as, ef_bs]

        max_iter = 500
        for _i_step in range(max_iter):

            if max_step is not None and max_step <= _i_step:
                break

            for i in range(len(paths_a_n_b)):

                # compute to skip element
                paths_vertex_skip = [v for e_flow in paths_a_n_b[i] for v in e_flow.vertices]
                paths_vertex_skip = list(set(paths_vertex_skip))

                # Grow path
                e_flow_grown = []
                for e_flow in paths_a_n_b[i]:
                    e_flows_possible_grows = e_flow.get_possible_grow(
                        skip_Components=skip_components + paths_vertex_skip,
                        only_foward_policy=only_forward_policy)

                    if not e_flows_possible_grows:
                        e_flows_possible_grows = [e_flow]
                    elif paths_association_2_by_2 and 1 < len(e_flows_possible_grows):

                        is_on_loop_plane_coefs = [max(0.0, 1.0 - _Ef.get_last_vertex_shift()) for _Ef in e_flows_possible_grows]
                        i_best = is_on_loop_plane_coefs.index(max(is_on_loop_plane_coefs))
                        e_flows_possible_grows = [e_flows_possible_grows[i_best]]
                        """
                        # algo to pick up the best path
                        has_curvature_value = E_flow.get_has_curvature_value() 
  
                        has_same_dir_coefs  = [ _Ef.get_last_dirs_dot()           for _Ef in E_flows_possible_grows ]
                        is_on_loop_plane_coefs = [ max(0.0, 1.0 - _Ef.get_last_vertex_shift()) for _Ef in E_flows_possible_grows ]
                        
                        is_valid_coefs = []
                        for j, _ in enumerate(E_flows_possible_grows):
                            coef = has_same_dir_coefs[j] * ( 1.0 - has_curvature_value ) + is_on_loop_plane_coefs[j] * has_curvature_value
                            is_valid_coefs.append(coef)
                        
                        i_best = is_valid_coefs.index(max(is_valid_coefs))
                        E_flows_possible_grows = [ E_flows_possible_grows[i_best]]
                        """

                        """
                        if len(E_flow) < 2 :
                            max_dot = -1
                            E_flow_same_dir_grow = None
                            for _Ef in E_flows_possible_grows:
                                dot = _Ef.get_last_dirs_dot()
                                if max_dot < dot :
                                    max_dot = dot
                                    E_flow_same_dir_grow = _Ef
                        else:    
                            min_shift = 999999
                            E_flow_same_dir_grow = None
                            for _Ef in E_flows_possible_grows:
                                shift = _Ef.get_last_vertex_shift()
                                if shift < min_shift :
                                    min_shift = shift
                                    E_flow_same_dir_grow = _Ef                                
                        
                        E_flows_possible_grows = [E_flow_same_dir_grow]
                        """

                    e_flow_grown += e_flows_possible_grows

                # merge if same_end_vertex:

                same_end_vertex_dict = {}
                for Ef in e_flow_grown:
                    same_end_vertex_dict.setdefault(Ef.vertices[-1], [])
                    same_end_vertex_dict[Ef.vertices[-1]].append(Ef)

                if len(e_flow_grown) != len(list(same_end_vertex_dict.keys())):

                    grown_branches_new = []
                    for v in same_end_vertex_dict:
                        ef_shortest = None
                        for Ef in same_end_vertex_dict[v]:
                            if ef_shortest:
                                if Ef.max_dist_from_middle_axe() < ef_shortest.max_dist_from_middle_axe():
                                    ef_shortest = Ef
                            else:
                                ef_shortest = Ef
                        grown_branches_new.append(ef_shortest)

                    e_flow_grown = grown_branches_new

                paths_a_n_b[i] = e_flow_grown[:]

                # extract_connected_paths
                connected_path = get_connected_path_from_two_edge_flow_lists(paths_a_n_b[0], paths_a_n_b[1], paths_association_2_by_2)
                if connected_path:
                    return connected_path

        return None

    @classmethod
    def create_from_two_vertices_with_shortest_path(cls, va, vb, skip_components=None, only_forward_policy=False, max_step=None):

        if skip_components is None:
            skip_components = []

        ef_as = [EdgeFlow.create_from_edge(ea, va) for ea in va.edges if not edge_is_in(ea, skip_components)]
        ef_bs = [EdgeFlow.create_from_edge(eb, vb) for eb in vb.edges if not edge_is_in(eb, skip_components)]

        connected_path = cls.create_from_two_edges_flows_with_shortest_path(
            ef_as,
            ef_bs,
            skip_components=skip_components,
            only_forward_policy=only_forward_policy,
            max_step=max_step,
        )

        return connected_path

    @classmethod
    def create_from_edge_groups_with_shortest_path(cls, efs, skip_components=None):

        if skip_components is None:
            skip_components = []

        # sort
        for i in range(len(efs)):
            efs[i].sort_with_neighbor()

        shortest_bridge_infos = []
        skip_components_path = []
        skip_end_ids = []
        for _ in range(500):
            _shortest_paths = []
            _start_ids = []
            _end_ids = []
            something_happened = False
            for i_a, ef_a in enumerate(efs):
                for i_b, ef_b in enumerate(efs):
                    if i_a == i_b:
                        continue
                    for v_ids in [[0, 0], [-1, -1], [0, -1], [-1, 0]]:

                        if [i_a, v_ids[0]] in skip_end_ids or [i_b, v_ids[1]] in skip_end_ids:
                            continue

                        va = ef_a.vertices[v_ids[0]]
                        vb = ef_b.vertices[v_ids[1]]
                        ef = cls.create_from_two_vertices_with_shortest_path(
                            va,
                            vb,
                            skip_components=skip_components + skip_components_path,
                        )
                        _shortest_paths.append(ef)
                        _start_ids.append([i_a, v_ids[0]])
                        _end_ids.append([i_b, v_ids[1]])
                        something_happened = True

            sizes = map(len, _shortest_paths)
            i_min = sizes.index(min(sizes))

            shortest_bridge_infos.append(
                {"shortest_path": _shortest_paths[i_min],
                 "start_ids": _start_ids[i_min],
                 "end_ids": _end_ids[i_min],
                 }
            )

            skip_components_path.append(_shortest_paths[i_min])
            skip_end_ids.append(_start_ids[i_min])
            skip_end_ids.append(_end_ids[i_min])
            if not something_happened:
                break

        # build path
        growing_island = copy.deepcopy(efs[0])
        growing_island_i_ef_start = [0, 0]
        growing_island_i_ef_end = [0, -1]
        bridge_used = []
        efs_used = [efs[0]]

        for _ in range(500):

            something_happened = False
            for shortest_bridge_info in shortest_bridge_infos:
                bridge = shortest_bridge_info["start_ids"]
                bridge_i_ef_start = shortest_bridge_info["start_ids"]
                bridge_i_ef_end = shortest_bridge_info["end_ids"]

                if bridge in bridge_used:
                    continue

                if bridge_i_ef_start == growing_island_i_ef_start:
                    bridge_used.append(copy.deepcopy(bridge))
                    growing_island = bridge.reverse() + growing_island
                    growing_island_i_ef_start = bridge_i_ef_end
                    something_happened = True

                elif bridge_i_ef_start == growing_island_i_ef_end:
                    bridge_used.append(copy.deepcopy(bridge))
                    growing_island = growing_island + bridge
                    growing_island_i_ef_end = bridge_i_ef_end
                    something_happened = True

                elif bridge_i_ef_end == growing_island_i_ef_start:
                    bridge_used.append(copy.deepcopy(bridge))
                    growing_island = bridge + growing_island
                    growing_island_i_ef_start = bridge_i_ef_start
                    something_happened = True

                elif bridge_i_ef_end == growing_island_i_ef_end:
                    bridge_used.append(copy.deepcopy(bridge))
                    growing_island += growing_island + bridge[::-1]
                    growing_island_i_ef_end = bridge_i_ef_start
                    something_happened = True

            for i, ef in enumerate(efs):
                if ef in efs_used:
                    continue

                if growing_island_i_ef_start[0] == i:

                    efs_used.append(ef)
                    if growing_island_i_ef_start[1] == 0:
                        growing_island = ef.reverse() + growing_island
                        growing_island_i_ef_start = [i, -1]
                        something_happened = True
                    else:
                        growing_island = ef + growing_island
                        growing_island_i_ef_start = [i, 0]
                        something_happened = True

                elif growing_island_i_ef_end[0] == i:

                    efs_used.append(ef)
                    if growing_island_i_ef_end[1] == 0:
                        growing_island = growing_island + ef
                        growing_island_i_ef_end = [i, -1]
                        something_happened = True
                    else:
                        growing_island = growing_island + ef.reverse()
                        growing_island_i_ef_end = [i, 0]
                        something_happened = True

            if not something_happened:
                break

        return growing_island

    @classmethod
    def create_from_edges(cls, edges):
        eg = super(EdgeFlow, cls).create_from_edges(edges)
        ef = cls.create_empty(eg.mesh_data)
        ef.ids = eg.ids[:]
        if not 1 < len(ef):
            raise RuntimeError('list has one element, use create_from_Edge instead')
        if not ef.has_only_neighbors_edges():
            return None
        ef.sort_with_neighbor()
        return ef

    @classmethod
    def create_from_edge(cls, e, v):
        ef = cls.create_empty(e.mesh_data)
        ef.ids = [e.id]
        ef.first_vertex_id = v.id
        return ef

    @classmethod
    def create_from_edge_names(cls, mesh_data, edge_names):
        eg = super(EdgeFlow, cls).create_from_edge_names(mesh_data, edge_names)
        ef = cls.create_empty(eg.mesh_data)
        ef.ids = eg.ids[:]
        if 1 < len(ef) and not ef.has_only_neighbors_edges():
            return None
        ef.sort_with_neighbor()
        return ef

    @classmethod
    def create_from_edge_group(cls, edge_grp):
        eg = super(EdgeFlow, cls).create_from_edge_group(edge_grp)
        ef = cls.create_empty(eg.mesh_data)
        ef.ids = eg.ids[:]
        if 1 < len(ef) and not ef.has_only_neighbors_edges():
            return None
        ef.sort_with_neighbor()
        return ef

    def _get_vertices(self):
        if len(self) == 1:
            if self.first_vertex_id is not None:
                vg = self[0].vertices
                if vg.ids[1] == self.first_vertex_id:
                    vg.reverse()
                return vg
            else:
                raise RuntimeError('class edge flow must have more than one edge, wrong constuct')

        vg = VertexGroup.create_empty(self.mesh_data)
        # Get first vertices
        e_first = self[0]
        e_second = self[1]

        start_vertex_id = 0
        if e_first[start_vertex_id] in e_second:
            start_vertex_id = 1

        vg += e_first[start_vertex_id]

        for e in self:
            for v in e.vertices:
                if not v in vg:
                    vg += v

        return vg

    @lru_cache(maxsize=32)
    def _get_vertices_cached(self, _instance):
        return self._get_vertices()

    @property
    def vertices(self):
        return self._get_vertices_cached(self)

    def has_only_neighbors_edges(self):
        not_sharing_vertices = self.get_not_sharing_vertices()
        is_flow = False
        if len(self.ids) > 1 and len(not_sharing_vertices) < 3:
            is_flow = True
        return is_flow

    def is_loop(self):
        if self.has_only_neighbors_edges():
            if self.vertices[0] in self.vertices[-1].neighbors:
                return True
        return False

    def get_possible_grow(self, skip_components=None, only_forward_policy=True):
        if skip_components is None:
            skip_components = []

        grown_branches = []
        for v_end_neighbor in self.vertices[-1].neighbors:
            if vertex_is_in(v_end_neighbor, skip_components):
                continue

            new_branch = self + v_end_neighbor
            if only_forward_policy:
                if new_branch.get_last_vertex_shift() < 0.5:
                    grown_branches.append(new_branch)
            else:
                grown_branches.append(new_branch)

        return grown_branches

    def __deepcopy__(self, memo):
        cg = super(EdgeFlow, self).__deepcopy__(memo)
        cg.first_vertex_id = self.first_vertex_id
        return cg

    def __contains__(self, elem):
        return super().__contains__(elem)

    def __iadd__(self, other):
        """ only add at the end if possible """

        max_iter = 500

        if isinstance(other, list):
            for _ in range(max_iter):
                len_before = len(self)
                for elem in other:
                    self.__iadd__(elem)
                len_after = len(self)
                if len_before == len_after:
                    break

        elif isinstance(other, Vertex):
            v = other
            for e in v.edges:
                if self.vertices[-1] in e:
                    self += e
                    break

        elif isinstance(other, VertexGroup):
            vg = other
            for _ in range(max_iter):
                len_before = len(self)
                for v in vg:
                    self += v
                len_after = len(self)
                if len_before == len_after:
                    break

        elif isinstance(other, Edge):
            e = other

            is_connected_to_last = self.vertices[-1] in e
            is_not_in_flow = e.id not in self.ids
            if is_connected_to_last and is_not_in_flow:
                self.ids.append(e.id)

        elif isinstance(other, (EdgeFlow, EdgeLoop)):
            ef = other
            if self.vertices[-1] in ef.vertices:
                if ef.vertices.index(self.vertices[-1]) > len(ef.vertices) / 2:
                    ef.reverse()
                for e in ef:
                    self += e
            else:
                return None

        elif isinstance(other, EdgeGroup):
            eg = other
            for _ in range(max_iter):
                len_before = len(self)
                for e in eg:
                    self += e
                len_after = len(self)
                if len_before == len_after:
                    break

        return self

    def __hash__(self):
        return hash(self.__class__.__name__) ^ hash(self.mesh_data.geo_name) ^ hash(tuple(self.ids)) ^ hash(self.first_vertex_id)

    def length(self):
        length_acc = 0
        for e in self:
            length_acc += e.length()
        return length_acc

    def start_end_vector_dir(self):
        v_dir = self.vertices[-1].pos - self.vertices[0].pos
        return v_dir

    def max_dist_from_middle_axe(self):
        v_first = self.vertices[0]
        v_dir = self.start_end_vector_dir()
        v_dir.normalize()

        max_dist = 0
        for v in self.vertices:
            if v == v_first:
                continue
            v = v.pos - v_first.pos
            a = v.angle(v_dir)
            dist = math.sin(a) * v.length()
            max_dist = max(max_dist, dist)

        return max_dist

    def get_last_dirs_dot(self):
        v = self.vertices[-1].pos - self.vertices[-2].pos
        v_last = self.vertices[-2].pos - self.vertices[-3].pos
        v.normalize()
        v_last.normalize()
        return v * v_last

    def get_last_vertex_shift(self):
        """
        take the global normal of plan form by all the point
        project on him the vector of the last two vertices
        return the length of that projection
        ->The goal is to see if the final point belong to the loop
        """

        has_curvature_value = self.get_has_curvature_value(skip_last_vertex=True)

        edge_flow_plane_normal = self.get_curvature_normal()
        if not edge_flow_plane_normal:
            edge_flow_plane_normal = om.MVector(0, 0, 0)

        v_first = self.vertices[1].pos - self.vertices[0].pos
        vertices_normal = (self.vertices[1].normal + self.vertices[0].normal) / 2.0
        vertices_and_normal_plane_normal = v_first ^ vertices_normal

        normal = edge_flow_plane_normal * has_curvature_value
        normal += vertices_and_normal_plane_normal * (1 - has_curvature_value)

        v_last = self.vertices[-1].pos - self.vertices[-2].pos
        v_last.normalize()
        normal.normalize()
        last_vertex_shift = abs(v_last * normal)

        return last_vertex_shift

    def get_curvature_normal(self):
        n_av = om.MVector(0, 0, 0)
        vertices = self.vertices
        if len(vertices) < 3:
            return None
        for i in range(len(vertices) - 2):
            v_a = vertices[i].pos - vertices[i + 1].pos
            v_b = vertices[i + 2].pos - vertices[i + 1].pos
            v_a.normalize()
            v_b.normalize()
            n = v_a ^ v_b
            n.normalize()
            n *= 1.0 - abs(v_a * v_b)
            n_av.x += n.x
            n_av.y += n.y
            n_av.z += n.z

        n_av.x /= len(vertices) - 1
        n_av.y /= len(vertices) - 1
        n_av.z /= len(vertices) - 1
        n_av.normalize()
        return n_av

    def get_has_curvature_value(self, skip_last_vertex=True):
        """
        0 -> 1
        0 is straigth line
        1 is 90 degree turn
        """
        if len(self) == 1 or (skip_last_vertex and len(self) < 3):
            return 0.0

        v_start = self.vertices[1].pos - self.vertices[0].pos
        v_start.normalize()

        dot_min = 1
        for i in range(1, len(self.vertices) - 1):

            is_last_one = i + 1 == len(self.vertices) - 1
            if skip_last_vertex and is_last_one:
                continue

            v = (self.vertices[i + 1].pos - self.vertices[i].pos).normalize()
            dot = abs(v * v_start)
            dot_min = min(dot_min, dot)
            if dot_min == 0:
                break
        return 1.0 - dot_min

    def is_circle(self):

        p_center = self.get_center_position()

        min_ray = 9999.0
        max_ray = 0
        av_ray = 0
        for i in range(len(self.vertices)):
            dist = (self.vertices[i].pos - p_center).length()
            min_ray = min(min_ray, dist)
            max_ray = max(max_ray, dist)
            av_ray += dist
        av_ray /= len(self.vertices)
        max_variation = min(1.0, (max_ray - min_ray) / av_ray)
        same_ray_coef = 1.0 - max_variation

        max_angle = 0
        for i in range(len(self.vertices) - 1):
            vA = self.vertices[i].pos - p_center
            vB = self.vertices[i + 1].pos - p_center

            angle = vA.angle(vB)
            max_angle = max(max_angle, angle)

        min_value = 65
        max_value = 90
        v_clamped = min(max_value, max(min_value, math.degrees(max_angle)))
        v = (v_clamped - min_value) / (max_value - min_value)
        max_angle_variation = 1.0 - v

        return min(1.0, same_ray_coef * max_angle_variation)

    def reverse_if_point_is_closest_to_end(self, p):
        if (self.vertices[-1].pos - p).length() < (self.vertices[0].pos - p).length():
            self.reverse()

    def generate_matrix(self, deduce_orient_from_shape=False):

        axes = ['x', 'y', 'z']
        i_axe_dir = 1
        i_axe_up = 0
        i_axe_side = 2

        v_curvature_normal = self.get_curvature_normal()

        v_up_ref = om.MVector(0, 1, 0)
        if deduce_orient_from_shape:
            m_ref = super(EdgeFlow, self).generate_matrix()
            v_up_from_shape = matrix_get_projected_vector_on_closest_axe(m_ref, v_up_ref, skip_v=v_curvature_normal)
            v_up_from_shape.normalize()
            is_circle_coef = self.is_circle()
            v_up_ref = v_up_from_shape * (1.0 - is_circle_coef) + v_up_ref * is_circle_coef

        v_side = v_up_ref ^ v_curvature_normal
        v_side.normalize()
        v_up_ref = v_curvature_normal ^ v_side
        v_up_ref.normalize()
        p = self.get_center_position()

        kw = {}
        kw['p'] = p
        kw['orthogonize'] = True
        kw['normalize'] = True
        kw['ref_axe'] = axes[i_axe_dir]
        kw['middle_axe'] = axes[i_axe_up]
        kw['v{}'.format(axes[i_axe_dir].upper())] = v_curvature_normal
        kw['v{}'.format(axes[i_axe_up].upper())] = v_up_ref
        kw['v{}'.format(axes[i_axe_side].upper())] = v_side

        m = matrix_build(**kw)

        return m

    def generate_matrices(
            self,
            up_targets=None,
            up_target_component='',
            deduce_orient_from_shape=False,
    ):

        # utils
        axes = ['x', 'y', 'z']
        i_axe_dir = 1
        i_axe_up = 0
        i_axe_side = 2

        vertices = self.vertices

        # get dirs
        v_dirs = []
        for i in range(0, len(vertices) - 1):
            v_dirs.append(vertices[i + 1].pos - vertices[i].pos)
        v_dirs.append(v_dirs[-1])

        v_up_from_shape = None
        if deduce_orient_from_shape:
            m_from_shape = self.generate_matrix(deduce_orient_from_shape)
            v_up_from_shape = matrix_get_row(1, m_from_shape)

        # get vector ups points 
        v_ups = []
        for i, V in enumerate(vertices):

            v_up = V.normal
            if deduce_orient_from_shape:
                v_up = v_up_from_shape
            v_up.normalize()
            v_ups.append(v_up)

        if up_targets:
            # get vUp taget
            p_ups = list(map(lambda x: matrix_get_row(3, utils_get_matrix(x)), up_targets))

            closest_v_id = -1
            closest_up_id = -1
            min_dist = 9999.0
            for up_id, p in enumerate(p_ups):
                for V_id, V in enumerate(vertices):
                    dist = (p - V.pos).length()
                    if dist < min_dist:
                        min_dist = dist
                        closest_v_id = V_id
                        closest_up_id = up_id

            v_up = p_ups[closest_up_id] - vertices[closest_v_id].pos
            if up_target_component in 'xyz':
                _m = utils_get_matrix(up_targets[closest_up_id])
                if up_target_component == 'x':
                    v_up = matrix_get_row(0, _m)
                elif up_target_component == 'y':
                    v_up = matrix_get_row(1, _m)
                elif up_target_component == 'z':
                    v_up = matrix_get_row(2, _m)

            # get vUp back to first Loop
            v_tmp = v_up
            for i in range(closest_v_id, len(vertices)):
                v_tmp = v_dirs[i] ^ v_tmp
                v_tmp = v_tmp ^ v_dirs[i]
                v_ups[i] = v_tmp
            v_tmp = v_up
            for i in reversed(range(0, closest_v_id + 1)):
                v_tmp = v_dirs[i] ^ v_tmp
                v_tmp = v_tmp ^ v_dirs[i]
                v_ups[i] = v_tmp

                # get points side
        v_sides = []
        for i, _ in enumerate(vertices):
            v_side = v_ups[i] ^ v_dirs[i]
            v_ups[i] = v_dirs[i] ^ v_side
            v_ups[i].normalize()

            v_side.normalize()
            v_side *= v_dirs[i].length()
            # vSide *= self.Els[i].get_thickness_from_center(vSide)
            v_sides.append(v_side)

        # add scale to up
        for i, V in enumerate(vertices):
            v_ups[i] *= v_dirs[i].length()

        # build matrix
        vertex_matrices = []
        for i in range(0, len(vertices)):
            kw = {}
            kw['p'] = vertices[i].pos
            kw['orthogonize'] = True
            kw['normalize'] = False
            kw['ref_axe'] = axes[i_axe_dir]
            kw['middle_axe'] = axes[i_axe_up]
            kw['v{}'.format(axes[i_axe_dir].upper())] = v_dirs[i]
            kw['v{}'.format(axes[i_axe_up].upper())] = v_ups[i]
            kw['v{}'.format(axes[i_axe_side].upper())] = v_sides[i]

            m = matrix_build(**kw)

            vertex_matrices.append(m)

        return vertex_matrices


class EdgeLoop(EdgeFlow):
    """ one edge loop stored as vertex ids """

    def __init__(self):
        super(EdgeLoop, self).__init__()
        self.vertex_id_up = 0  # up must be the first one
        self.vertex_id_side = None

    @classmethod
    def create_from_edges(cls, edges):
        el = super(EdgeLoop, cls).create_from_edges(edges)
        if el.first_vertex_id is None:
            not_sharing_vertices = el.get_not_sharing_vertices()
            if not_sharing_vertices:
                el.first_vertex_id = el.get_not_sharing_vertices()[0].id
            else:
                el.first_vertex_id = el[0].vertices[0].id

        if not el:
            return None
        if not el.is_loop():
            return None
        return el

    @classmethod
    def create_from_edge_names(cls, mesh_data, edge_names):
        el = super(EdgeLoop, cls).create_from_edge_names(mesh_data, edge_names)
        if el.first_vertex_id is None:
            not_sharing_vertices = el.get_not_sharing_vertices()
            if not_sharing_vertices:
                el.first_vertex_id = el.get_not_sharing_vertices()[0].id
            else:
                el.first_vertex_id = el[0].vertices[0].id

        if not el:
            return None
        if not el.is_loop():
            return None
        return el

    @classmethod
    def create_from_edge_group(cls, edge_grp, close_loop_max_step=None):
        el = super(EdgeLoop, cls).create_from_edge_group(edge_grp)
        if el.first_vertex_id is None:
            not_sharing_vertices = el.get_not_sharing_vertices()
            if not_sharing_vertices:
                el.first_vertex_id = el.get_not_sharing_vertices()[0].id
            else:
                el.first_vertex_id = el[0].vertices[0].id

        if not el:
            return None
        if not el.is_loop():
            if close_loop_max_step:
                ef_a = EdgeFlow.create_from_edge(el[0], el.vertices[1])
                ef_b = EdgeFlow.create_from_edge(el[-1], el.vertices[-2])

                ef = EdgeFlow.create_from_two_edges_flows_with_shortest_path(
                    [ef_a],
                    [ef_b],
                    skip_components=el.vertices,
                    only_forward_policy=True,
                    max_step=close_loop_max_step,
                )
                if ef:
                    el += ef
                else:
                    return None

            else:
                return None
        return el

    @classmethod
    def create_from_edge_flow(cls, edge_grp, close_loop_max_step=0):
        el = cls.create_from_edge_group(edge_grp, close_loop_max_step=close_loop_max_step)
        if el and el.first_vertex_id is None:
            el.first_vertex_id = el.get_not_sharing_vertices()[0].id

        return el

    @property
    def vup(self):
        return self.vertices[self.vertex_id_up]

    @property
    def vside(self):
        return self.vertices[self.vertex_id_side]

    @property
    def p_center(self):
        return self.get_center_position()

    @property
    def v_up(self):
        return self.vup.pos - self.p_center

    @property
    def v_side(self):
        return self.vside.pos - self.p_center

    @property
    def v_dirs(self):
        v_dirs = []
        for V in self.vertices:
            v_dirs.append(V.pos - self.p_center)
        return v_dirs

    @property
    def v_dir(self):
        return self.v_up ^ self.v_side

    def sort_ids_with_vertex_as_up(self, v):

        es = self.from_vertex_find_connected_edges_in_group(v)
        # get the order
        i_start = None

        i_ea = self.index(es[0])
        i_eb = self.index(es[1])

        if i_eb - i_ea == 1:
            i_start = i_eb
        elif i_ea - i_eb == 1:
            i_start = i_ea
        elif 1 < i_ea - i_eb:
            i_start = i_eb
        elif 1 < i_eb - i_ea:
            i_start = i_ea

        self.ids = self.ids[i_start:] + self.ids[0:i_start]

    def sort_ids_with_vertex_id_as_up(self, i):
        v = self.vertices[i]
        self.sort_ids_with_vertex_as_up(v)

    def sort_ids_with_vector_up_and_dir(self, v_ray_start, v_ray_counter_dir):

        vertex_id_start = self.get_angular_closest_vertex_id_from_vector_and_center(v_ray_start)
        self.sort_ids_with_vertex_id_as_up(vertex_id_start)
        v_dir = self.vertices[1].pos - self.vertices[0].pos
        if (v_ray_start ^ v_ray_counter_dir) * v_dir < 0:
            self.reverse()

    def get_angular_closest_vertex_id_from_vector_and_point(self, v, p):

        id_max = -1
        max_dot = 0
        for i, V in enumerate(self.vertices):
            v_test = (V.pos - p)
            v_test.normalize()
            dot = v_test * v
            if max_dot < dot:
                max_dot = dot
                id_max = i

        return id_max

    def get_angular_closest_vertex_id_from_vector_and_center(self, v):
        return self.get_angular_closest_vertex_id_from_vector_and_point(v, self.get_center_position())

    def get_thickness_from_center(self, v_angle):
        i = self.get_angular_closest_vertex_id_from_vector_and_center(v_angle)
        v_delta = self.vertices[i].pos - self.get_center_position()
        return v_delta.length()

    def get_neighbor(self, skip_ids=None, close_loop_max_step=1):

        vg_n = self.vertices.neighbors
        eg = EdgeGroup.create_from_vertex_group(vg_n)
        egs = eg.group_by_neighbors()

        els = []
        for _eg in egs:
            # _Eg.sort_ids_with_neighbor_ref( self )
            el = EdgeLoop.create_from_edge_group(_eg, close_loop_max_step=close_loop_max_step)
            if el:
                els.append(el)

        return els

    def generate_matrix(self, deduce_orient_from_shape=False):
        return super(EdgeLoop, self).generate_matrix(deduce_orient_from_shape=True)


class EdgeLoopFlow(ComponentGroup):
    """
    multiple edge loops stored as vertex ids
    forming a flow (are adjacent to each other)
    """

    def __init__(self):
        super(EdgeLoopFlow, self).__init__()

        self.els = []
        self.user_input_ids = []

        # #loops info
        # self.Loop_first = None
        # self.Loops_group = None
        #
        # # get extra info
        # self.is_part_mesh = None
        # self.is_loop = None
        # self.iBase = None
        # self.landmarks = None
        #
        # # extra data
        # self.vDirs = None

    @classmethod
    def create_from_edge_loop(
            cls,
            el,
            topo_max_change=3,
            close_loop_max_step=1,
            topo_max_change_at_once=3,
            follow_topo=True,
            v_up_ref=(0, 1, 0),
            outputs_override=None,
    ):

        # reorder incoming Edge loop
        if v_up_ref:
            el.sort_ids_with_vector_up_and_dir(
                om.MVector(v_up_ref[0], v_up_ref[1], v_up_ref[2]),
                el.get_curvature_normal(),
            )

        # Get both branch and grow
        el_neighbors = el.get_neighbor()
        el_branches = [None, None]
        topo_last_size = [None, None]
        if 0 < len(el_neighbors):
            el_branches[0] = [el, el_neighbors[0]]
            topo_last_size[0] = len(el_neighbors[0])
        if 1 < len(el_neighbors):
            el_branches[1] = [el, el_neighbors[1]]
            topo_last_size[1] = len(el_neighbors[1])

        topo_changes_count = [0, 0]

        max_iter = 500
        for _ in range(max_iter):

            something_happened = False
            for i in range(2):

                if not el_branches[i]:
                    continue

                el_neighbors_test = el_branches[i][-1].get_neighbor(close_loop_max_step=close_loop_max_step)

                # filter processed El
                el_neighbors_new = []
                for n in el_neighbors_test:

                    is_already_processed = False
                    for El_branch in el_branches:
                        if not El_branch:
                            continue
                        if n in El_branch:
                            is_already_processed = True
                            break

                    if not is_already_processed:
                        el_neighbors_new.append(n)

                # filter topo change     
                for n in el_neighbors_new:
                    # topo check
                    vtx_nbr_delta = abs(len(n) - topo_last_size[i])

                    if topo_max_change_at_once < vtx_nbr_delta:
                        continue

                    if vtx_nbr_delta != 0:
                        topo_changes_count[i] += 1

                    topo_last_size[i] = len(n)

                    if topo_max_change < topo_changes_count[i]:
                        continue
                    # topo check                      
                    el_branches[i].append(n)
                    something_happened = True
                    break

            if not something_happened:
                break

        # Merge Branches

        user_input_loop_id = 0
        edge_loop_flow = []
        if el_branches[0] is None:
            edge_loop_flow = el_branches[1]
        elif el_branches[1] is None:
            edge_loop_flow = el_branches[0]
        elif el_branches[0][-1] in el_branches[1][-1].get_neighbor(close_loop_max_step=close_loop_max_step):
            # is loop
            edge_loop_flow = el_branches[0] + list(reversed(el_branches[1][1:]))
            user_input_loop_id = len(el_branches[0])
        else:

            if not outputs_override or outputs_override in ['merge', 'merge_and_loop']:
                if len(el_branches[0]) < len(el_branches[1]):
                    edge_loop_flow = list(reversed(el_branches[0])) + el_branches[1][1:]
                    user_input_loop_id = len(el_branches[0])
                else:
                    edge_loop_flow = list(reversed(el_branches[1])) + el_branches[0][1:]
                    user_input_loop_id = len(el_branches[1])
            elif outputs_override in 'keep_longest':
                user_input_loop_id = 0
                if len(el_branches[0]) < len(el_branches[1]):
                    edge_loop_flow = el_branches[1][:]
                else:
                    edge_loop_flow = el_branches[0][:]
            elif outputs_override in 'keep_shortest':
                user_input_loop_id = 0
                if len(el_branches[0]) < len(el_branches[1]):
                    edge_loop_flow = el_branches[0][:]
                else:
                    edge_loop_flow = el_branches[1][:]

        # Create instance
        elf = cls.create_empty(el.mesh_data)
        elf.els = edge_loop_flow
        elf.user_input_ids = [elf.els.index(el)]

        # for i in range(0,len(Elf)):
        #     if not Elf[i].is_loop():
        #         print('test')
        #         #Elf[i].close_with_closest_path()

        for i in range(1, len(elf)):
            elf[i].sort_ids_with_neighbor_ref(elf[i - 1])

        # for i in range(0,len(Elf)):
        #     if not Elf[i].is_loop():
        #         print('test')
        #         #Elf[i].close_with_closest_path()

        if not follow_topo and v_up_ref:
            elf.update_ups(om.MVector(
                v_up_ref[0], v_up_ref[1], v_up_ref[2]),
                loop_id_ref=user_input_loop_id,
                follow_topo=follow_topo,
            )
            elf.update_sides()

        return elf

    @lru_cache(maxsize=32)
    def _get_vertices_cached(self, _instance):
        vg = VertexGroup.create_empty(self.mesh_data)
        for el in self.els:
            vg += el.vertices
        return vg

    @property
    def vertices(self):
        return self._get_vertices_cached(self)

    def __getitem__(self, i):
        if isinstance(i, int):
            return self.els[i]
        else:
            return [self.els[iE] for iE in self.ids[i]]

    def __iter__(self):
        for el in self.els:
            yield el

    def __len__(self):
        return len(self.els)

    def __hash__(self):
        return hash(self.__class__.__name__) ^ hash(self.mesh_data.geo_name) ^ hash(tuple(self.els))

    def contain_whole_mesh(self):
        return self.mesh_data.vertices_nbr == len(self.vertices)

    def is_loop(self):
        return self.els[0] in self.els[-1].get_neighbor()

    def get_index_when_topo_change(self, ids_to_test, max_change=3):

        has_topology_changed = False
        change_start_index = None
        changes_count = 0
        last_size = -1
        for j in ids_to_test:
            size = len(self.els[j])
            if last_size != -1 and size != last_size:
                changes_count += 1
                if change_start_index is None:
                    change_start_index = j
            else:
                changes_count = 0
                change_start_index = None

            if max_change < changes_count:
                has_topology_changed = True
                break

            last_size = size

        if not has_topology_changed:
            change_start_index = None

        return change_start_index

    def clean_range_topo_change(self, max_topo_change_allowed=3):

        i_base = self.user_input_ids[0]
        loops_nbr = len(self.els)
        base_to_start = list(reversed(range(0, i_base)))
        base_to_end = list(range(i_base, loops_nbr))

        i_start = self.get_index_when_topo_change(base_to_start, max_topo_change_allowed)
        i_end = self.get_index_when_topo_change(base_to_end, max_topo_change_allowed)

        i_start = i_start or 0
        i_end = i_end or loops_nbr

        self.els = self.els[i_start:i_end]

    def loop_reorder_from_id(self, id_start):

        edge_loop_size = len(self.els)
        for j, l_id in enumerate(self.user_input_ids):
            l_id -= id_start
            if l_id < 0:
                l_id = edge_loop_size + l_id
            self.user_input_ids[j] = l_id

        self.els = self.els[id_start:] + self.els[:id_start]

    def loop_reorder_from_first_user_input_id(self):
        id_start = self.user_input_ids[0]
        self.loop_reorder_from_id(id_start)

    def loop_reorder_from_edge_loop_closest_to_point(self, point):
        id_start, _ = self.get_closest_loop_info([point])
        self.loop_reorder_from_id(id_start)

    def reverse(self):

        for el in self.els:
            el.reverse()

        self.els.reverse()

        for i, user_input_id in enumerate(self.user_input_ids):
            self.user_input_ids[i] = len(self.els) - 1 - user_input_id

        self.update_sides()

        return self

    def reverse_if_point_is_closest_to_end_loop(self, p):
        if (self[-1].vertices[0].pos - p).length() < (self[0].vertices[0].pos - p).length():
            self.reverse()

    def reorder_from_position(self, pos):
        do_reverse = False
        if pos:
            first_dist = (pos - self.els[0].get_center_position()).length()
            last_dist = (pos - self.els[-1].get_center_position()).length()
            do_reverse = last_dist < first_dist

        if do_reverse:
            self.reverse()

    def get_centers_delta_vectors(self, copy_last=True):
        v_dirs = [self.els[i + 1].p_center - self.els[i].p_center for i in range(len(self.els) - 1)]
        if copy_last:
            v_dirs.append(v_dirs[-1])
        return v_dirs

    def get_closest_loop_info(self, pts):
        return points_arrays_get_closest_ids([El.p_center for El in self.els], pts)

    def transform_vector_on_loops_range(
            self,
            src_vector,
            range_id=None,
            adjust_length_with_geo=True,
    ):

        v_dirs = self.get_centers_delta_vectors()
        nbr = len(self.els)

        if not range_id:
            range_id = range(nbr)

        # get_vectors
        v = src_vector
        vectors = []
        for i in range_id:

            v_side = v ^ v_dirs[i]
            v = v_dirs[i] ^ v_side
            v.normalize()
            if adjust_length_with_geo:
                v *= self.els[i].get_thickness_from_center(v)

            vectors.append(om.MVector(v))

        return vectors

    def _update_ups_on_range(self, v_ref, range_id, follow_topo=True):

        if not range_id:
            return False

        v_dirs = self.get_centers_delta_vectors()
        self.els[range_id[0]].sort_ids_with_vector_up_and_dir(v_ref, v_dirs[0])

        if follow_topo:

            size_last = 0
            v_up_last = v_ref
            for i_r, i in enumerate(range_id):

                self.els[i].vertex_id_up = 0

                if i_r == 0 or len(self.els[i]) != size_last:
                    self.els[i].sort_ids_with_vector_up_and_dir(v_up_last, v_dirs[i])
                else:
                    self.els[i].sort_ids_with_neighbor_ref(self.els[range_id[i_r - 1]])

                size_last = len(self.els[i])
                v_up_last = self.els[i].vUp
        else:
            vectors = self.transform_vector_on_loops_range(
                v_ref,
                range_id=range_id,
                adjust_length_with_geo=True,
            )
            for i in range_id:
                self.els[i].sort_ids_with_vector_up_and_dir(vectors[i], v_dirs[i])

        return True

    def update_ups(self, v_ref, loop_id_ref, follow_topo=True):
        range_to_start = list(reversed(range(0, loop_id_ref)))
        range_to_end = list(range(loop_id_ref, len(self.els)))
        self._update_ups_on_range(v_ref, range_to_start, follow_topo=follow_topo)
        self._update_ups_on_range(v_ref, range_to_end, follow_topo=follow_topo)

    def update_sides(self, v_ups=None):

        if v_ups is None:
            v_ups = [self.els[i].v_up for i in range(len(self.els))]

        v_dirs = self.get_centers_delta_vectors()
        for i, _ in enumerate(self.els):
            v_side = v_ups[i] ^ v_dirs[i]
            v_side.normalize()
            v_id = self.els[i].get_angular_closest_vertex_id_from_vector_and_center(v_side)
            self.els[i].vertex_id_side = v_id

    def get_common_edge_loops(self, elf):
        common_els = []
        for el in elf.els:
            if el in self.els:
                common_els.append(el)
        return common_els

    def build_bridge(self, elf):

        el_b_user = elf.els[elf.user_input_ids[0]]

        i_start = self.user_input_ids[0]
        i_end = None
        if el_b_user in self.els:
            i_end = self.els.index(el_b_user)

        if i_end:
            self.els = self.els[i_start:i_end]
            self.user_input_ids = [0, len(self.els) - 1]
            return True

        return False

    def get_curvature_normal(self):
        n_av = om.MVector(0, 0, 0)
        center_positions = [el.get_center_position() for el in self.els]
        if len(center_positions) < 3:
            return None
        for i in range(len(center_positions) - 2):
            va = center_positions[i] - center_positions[i + 1]
            vb = center_positions[i + 2] - center_positions[i + 1]
            va.normalize()
            vb.normalize()
            n = va ^ vb
            n.normalize()
            n *= 1.0 - abs(va * vb)
            n_av.x += n.x
            n_av.y += n.y
            n_av.z += n.z

        n_av.x /= len(center_positions) - 1
        n_av.y /= len(center_positions) - 1
        n_av.z /= len(center_positions) - 1
        n_av.normalize()
        return n_av

    def generate_matrices(
            self,
            up_targets=None,
            up_target_component='',
            orient_follow_topo=False,
            deduce_orient_from_shape='',
    ):
        # utils
        axes = ['x', 'y', 'z']
        i_axe_dir = 1
        i_axe_up = 0
        i_axe_side = 2

        # get dirs
        v_dirs = self.get_centers_delta_vectors(copy_last=True)

        # get v up first 
        if up_targets:

            # get association loop <-> up_targets
            p_ups = list(map(lambda x: matrix_get_row(3, utils_get_matrix(x)), up_targets))
            i_loop, i_up = self.get_closest_loop_info(p_ups)

            # get vUp from up_targets
            v_up = p_ups[i_up] - self.els[i_loop].p_center
            if up_target_component in 'xyz':
                _m = utils_get_matrix(up_targets[i_up])
                if up_target_component == 'x':
                    v_up = matrix_get_row(0, _m)
                elif up_target_component == 'y':
                    v_up = matrix_get_row(1, _m)
                elif up_target_component == 'z':
                    v_up = matrix_get_row(2, _m)

            # modif up if
            if deduce_orient_from_shape == 'edge_loop':
                m_ref = self.els[i_loop].generate_matrix()
                v_up = matrix_get_projected_vector_on_closest_axe(m_ref, v_up, skip_v=v_dirs[i_loop])
            elif deduce_orient_from_shape == 'all_edge_loops':
                m_ref = self.vertices.generate_matrix()
                v_up = matrix_get_projected_vector_on_closest_axe(m_ref, v_up, skip_v=v_dirs[i_loop])
            elif deduce_orient_from_shape == 'global_mesh':
                m_ref = self.mesh_data.vertices().generate_matrix()
                v_up = matrix_get_projected_vector_on_closest_axe(m_ref, v_up, skip_v=v_dirs[i_loop])

            # get vUp back to first Loop
            v_up_first = self.transform_vector_on_loops_range(v_up, list(range(i_loop, -1, -1)), adjust_length_with_geo=True)[-1]

            self.update_ups(v_up_first, loop_id_ref=0, follow_topo=orient_follow_topo)
            self.update_sides()

        else:
            v_up = om.MVector(0, 1, 0)

            i_loop = self.user_input_ids[0]
            # modif up if 
            if deduce_orient_from_shape == 'edge_loop':
                m_ref = self.els[i_loop].generate_matrix()
                v_up = matrix_get_projected_vector_on_closest_axe(m_ref, v_up, skip_v=v_dirs[i_loop])
            elif deduce_orient_from_shape == 'all_edge_loops':
                m_ref = self.vertices.generate_matrix()
                v_up = matrix_get_projected_vector_on_closest_axe(m_ref, v_up, skip_v=v_dirs[i_loop])
            elif deduce_orient_from_shape == 'global_mesh':
                m_ref = self.mesh_data.vertices().generate_matrix()
                v_up = matrix_get_projected_vector_on_closest_axe(m_ref, v_up, skip_v=v_dirs[i_loop])

                # get vUp back to first Loop
            v_up_first = self.transform_vector_on_loops_range(v_up, list(range(i_loop, -1, -1)), adjust_length_with_geo=True)[-1]

            self.update_ups(v_up_first, loop_id_ref=0, follow_topo=orient_follow_topo)
            self.update_sides()

        # get vector ups points
        # v_ups = []
        # v_sides = []
        if orient_follow_topo:
            v_ups = [El.v_up for El in self.els]
        else:
            v_ups = self.transform_vector_on_loops_range(v_up_first, adjust_length_with_geo=True)
            self.update_sides(v_ups)

        # get points side
        v_sides = []
        for i, _ in enumerate(self.els):
            v_side = v_ups[i] ^ v_dirs[i]
            # v_ups[i] = vDirs[i] ^ vSide

            v_side.normalize()
            # v_ups[i].normalize()
            v_side *= self.els[i].get_thickness_from_center(v_side)
            v_sides.append(v_side)

        # build matrix
        edge_loops_matrices = []
        for i in range(len(self.els)):
            kw = {}
            kw['p'] = self.els[i].p_center
            kw['orthogonize'] = True
            kw['normalize'] = False
            kw['ref_axe'] = axes[i_axe_dir]
            kw['middle_axe'] = axes[i_axe_up]
            kw['v{}'.format(axes[i_axe_dir].upper())] = v_dirs[i]
            kw['v{}'.format(axes[i_axe_up].upper())] = v_ups[i]
            kw['v{}'.format(axes[i_axe_side].upper())] = v_sides[i]

            m = matrix_build(**kw)

            edge_loops_matrices.append(m)

        return edge_loops_matrices

    @staticmethod
    def multi_merge_if_common_edge_loop(elfs):

        for a, elf_a in enumerate(elfs):
            for b, elf_b in enumerate(elfs):

                if a == b:
                    continue

                if elf_a == elf_b:

                    for b_user_input_id in elf_b.user_input_ids:

                        a_user_input_id = elfs[a].index(elf_b[b_user_input_id])

                        if a_user_input_id not in elfs[a].user_input_ids:
                            elfs[a].user_input_ids.append(a_user_input_id)

                    elfs[b] = None

        # Clean
        elfs = list(filter(lambda x: bool(x), elfs))

        return elfs

    def names(self):
        return ['{}.e[{}]'.format(self.mesh_data.geo_name, i) for el in self.els for i in el.ids]


class MeshTopology(object):
    """
    edge_name edge_names
    edge_id edge_ids
    vertex_name vertex_names
    vertex_id vertex_ids
    edge_ids_group
    edge_ids_neighbor_group
    edge_ids_flow
    edge_ids_loop
    vertex_id_loop
    """

    # do singleton?
    def __init__(self, geo_name):
        self.geo_name = geo_name

        selection_maya_api = om.MSelectionList()
        selection_maya_api.add(self.geo_name)
        dp_geo = selection_maya_api.getDagPath(0)
        it_vtx = om.MItMeshVertex(dp_geo)
        it_edges = om.MItMeshEdge(dp_geo)
        self.mesh_api_iter_vtx = it_vtx
        self.mesh_api_iterEdges = it_edges
        self.vertices_nbr = self.mesh_api_iter_vtx.count()
        self.edges_nbr = self.mesh_api_iterEdges.count()

        points = Mesh(geo_name).get_points(space=mx.sWorld)
        self.vertex_positions = [om.MVector(p[0], p[1], p[2]) for p in points]

        self.vertex_id_adjacency_list = self.maya_api_get_vertex_ids_adjacency_list()
        self.vertex_id_to_edge_ids = self.maya_api_get_vertex_id_to_edge_ids_list()
        self.edge_id_to_vertex_ids = self.maya_api_get_edge_id_to_vertex_ids_list()

        self.vertex_normals = mesh_get_vertex_normals(geo_name)

        self.vertices = [Vertex.create_from_id(self, i) for i in range(self.vertices_nbr)]
        self.edges = [Edge.create_from_id(self, i) for i in range(self.edges_nbr)]

    def vertices(self):
        return VertexGroup.create_from_vertices(self.vertices)

    @classmethod
    def create_empty(cls):
        pass

    @classmethod
    def create_from_meshes(cls):
        pass

    @staticmethod
    def extract_geo_from_components_names(elements):
        return list(set([e.split('.')[0] for e in elements]))

    @staticmethod
    def filter_component_names(edge_names, geo_name):
        return list(filter(lambda e: e.split('.')[0] == geo_name, edge_names))

    @staticmethod
    def get_component_ids(edge_names):
        ids = []
        for e in edge_names:
            if re_get_keys.findall(e):
                ids.append(int(re_get_keys.findall(e)[0]))
        return ids

    def maya_api_edge_id_to_vertex_ids(self, i_edge):
        self.mesh_api_iterEdges.setIndex(i_edge)
        return [self.mesh_api_iterEdges.vertexId(0), self.mesh_api_iterEdges.vertexId(1)]

    def maya_api_convert_edge_id_to_vertex_ids(self, i):
        self.mesh_api_iterEdges.setIndex(i)
        return [self.mesh_api_iterEdges.vertexId(iE) for iE in [0, 1]]

    def maya_api_convert_vertex_id_to_edge_ids(self, i):
        self.mesh_api_iter_vtx.setIndex(i)
        edge_ids = self.mesh_api_iter_vtx.getConnectedEdges()
        return edge_ids

    def maya_api_get_vertex_id_to_edge_ids_list(self, use_ref_for_order=True):

        tn_indices = []

        for i in range(self.vertices_nbr):

            edge_ids = self.maya_api_convert_vertex_id_to_edge_ids(i)

            if use_ref_for_order:
                vtx_ids = self.vertex_id_adjacency_list[i]

                edge_ids_ordered = []
                for vid in vtx_ids:
                    for edge_id in edge_ids:
                        if edge_id in edge_ids_ordered:
                            continue
                        e_va_id, e_vb_id = self.maya_api_convert_edge_id_to_vertex_ids(edge_id)
                        if e_va_id == vid:
                            edge_ids_ordered.append(edge_id)
                            break
                        elif e_vb_id == vid:
                            edge_ids_ordered.append(edge_id)
                            break

                edge_ids = edge_ids_ordered[:]

            tn_indices.append(edge_ids)

        return tn_indices

    def maya_api_get_edge_id_to_vertex_ids_list(self):
        tn_indices = []

        for i in range(self.edges_nbr):
            edge_ids = self.maya_api_convert_edge_id_to_vertex_ids(i)
            tn_indices.append(edge_ids)

        return tn_indices

    def maya_api_get_vertex_id_to_neighbors(self, i):
        self.mesh_api_iter_vtx.setIndex(i)
        vertices_grown_raw = self.mesh_api_iter_vtx.getConnectedVertices()
        return [vtx_id for vtx_id in vertices_grown_raw]

    def get_middle_vertex(self):
        p = self.get_center_position()

        v_middle = None
        min_dist = 9999999
        for v in self.vertices:
            dist = (v.pos - p).length()
            if dist < min_dist:
                min_dist = dist
                v_middle = v

        return v_middle

    def maya_api_get_vertex_ids_adjacency_list(self):
        tn_indexes = []

        for i in range(self.mesh_api_iter_vtx.count()):
            tn_indexes.append(self.maya_api_get_vertex_id_to_neighbors(i))
            self.mesh_api_iter_vtx.next()

        return tn_indexes

    def create_vertex(self, vertex_name):
        names = self.filter_component_names([vertex_name], self.geo_name)
        if not names:
            return None
        names = [name for name in names if '.vtx[' in name]
        if not names:
            return None
        vertex_id = self.get_component_ids(names)[0]
        return Vertex.create_from_id(self, vertex_id)

    def create_edge(self, edge_name):
        names = self.filter_component_names([edge_name], self.geo_name)
        if not names:
            return None
        names = [name for name in names if '.e[' in name]
        if not names:
            return None
        edge_id = self.get_component_ids(names)[0]
        return Edge.create_from_id(self, edge_id)

    def create_vertex_group(self, vertex_names):
        if not vertex_names:
            return VertexGroup.create_empty(self)
        names = self.filter_component_names(vertex_names, self.geo_name)
        if not names:
            return None
        names = [name for name in names if '.vtx[' in name]
        if not names:
            return None
        vertex_ids = self.get_component_ids(names)
        return VertexGroup.create_from_ids(self, vertex_ids)

    def create_edge_group(self, edge_names):
        if not edge_names:
            return EdgeGroup.create_empty(self)
        names = self.filter_component_names(edge_names, self.geo_name)
        if not names:
            return None
        names = [name for name in names if '.e[' in name]
        if not names:
            return None
        edge_ids = self.get_component_ids(names)
        return EdgeGroup.create_from_ids(self, edge_ids)

    def create_shortest_path(self, vertex_name_a, vertex_name_b, only_forward_policy=False):
        va = self.create_vertex(vertex_name_a)
        vb = self.create_vertex(vertex_name_b)
        return EdgeFlow.create_from_two_vertices_with_shortest_path(va, vb, only_forward_policy=only_forward_policy)

    def create_edge_loop_from_vertex(self, vertex_name_a):
        va = self.create_vertex(vertex_name_a)
        vg = va.neighbors

        opposite_vertices = []
        for _ in range(2):
            dot_min = 1
            opposite_vertex_coupe = None
            for v_test_a in vg:
                for v_test_b in vg:
                    if v_test_a == v_test_b:
                        continue
                    if v_test_a in opposite_vertices:
                        continue
                    if v_test_b in opposite_vertices:
                        continue
                    v_dir_a = (v_test_a.pos - va.pos)
                    v_dir_b = (v_test_b.pos - va.pos)
                    v_dir_a.normalize()
                    v_dir_b.normalize()
                    dot = v_dir_a * v_dir_b
                    if dot < dot_min:
                        dot_min = dot
                        opposite_vertex_coupe = [v_test_a, v_test_b]
            if opposite_vertex_coupe:
                opposite_vertices += opposite_vertex_coupe

        opposite_efs = []
        for i in range(0, len(opposite_vertices), 2):
            _E = Edge.create_from_two_vertices(opposite_vertices[i + 0], va)
            opposite_efs.append(EdgeFlow.create_from_edge(_E, va))
            _E = Edge.create_from_two_vertices(opposite_vertices[i + 1], va)
            opposite_efs.append(EdgeFlow.create_from_edge(_E, va))

        ef = EdgeFlow.create_from_two_edges_flows_with_shortest_path(
            [ef for i, ef in enumerate(opposite_efs) if not i % 2],
            [ef for i, ef in enumerate(opposite_efs) if i % 2],
            only_forward_policy=True,
            paths_association_2_by_2=True,
        )

        return EdgeLoop.create_from_edge_flow(ef)

    def create_edge_loop_from_mesh(self):
        v = self.get_middle_vertex()  # to do
        return self.create_edge_loop_from_vertex(v.name())

    @staticmethod
    def create_edge_loop_from_edges_group(eg, close_loop_max_step=99):
        return EdgeLoop.create_from_edge_group(eg, close_loop_max_step=close_loop_max_step)

    @staticmethod
    def create_edge_flow_from_edges_group(eg):
        return EdgeFlow.create_from_edge_group(eg)

    @staticmethod
    def create_edge_flow_from_edge(e, v):
        return EdgeFlow.create_from_edge(e, v)

    @staticmethod
    def create_edge_loop_flow_from_edge_loop(
            el,
            topo_max_change=3,
            close_loop_max_step=1,
            follow_topo=True,
            v_up_ref=(0, 1, 0),
            outputs_override=None,
    ):
        return EdgeLoopFlow.create_from_edge_loop(
            el,
            topo_max_change=topo_max_change,
            close_loop_max_step=close_loop_max_step,
            follow_topo=follow_topo,
            v_up_ref=v_up_ref,
            outputs_override=outputs_override,
        )

    def create_edge_loop_flows_from_edge_names(
            self,
            edge_name_list,
            topo_change_tolerance=3,
            reverse_direction=None,
            base_target='',
    ):
        base_position = None
        if base_target and base_target != '':
            base_position = matrix_get_row(3, utils_get_matrix(base_target))

        eg = EdgeGroup.create_from_edge_names(self, edge_name_list)
        egs = eg.group_by_neighbors()

        elfs = []
        for eg in egs:
            el = EdgeLoop.create_from_edge_group(eg, close_loop_max_step=99)
            elf = EdgeLoopFlow.create_from_edge_loop(el, topo_max_change=topo_change_tolerance)
            elfs.append(elf)

        for i, _ in enumerate(elfs):
            elf.clean_range_topo_change(max_topo_change_allowed=topo_change_tolerance)
            if base_position:
                elfs[i].reorder_from_position(base_position)
            if reverse_direction:
                elfs[i].reverse()

        elfs = EdgeLoopFlow.multi_merge_if_common_edge_loop(elfs)

        return elfs

    def get_center_position(self):
        pts = [V.pos for V in self.vertices]
        bb_center = get_bounding_box_center_from_points(pts)
        return bb_center


def sublists_remove_duplicate(list_of_list):
    return list(map(lambda e: sorted(list(set(e))), list_of_list))


def list_remove_empty_list(list_of_list):
    return list(filter(lambda e: e != [], list_of_list))


def list_remove_duplicate(list_of_list):
    list_of_list.sort()
    return list(k for k, _ in groupby(list_of_list))


def list_remove_inside_others(list_of_list):
    def is_inside_others(list_a):
        for list_b in list_of_list:
            if set(list_a) & set(list_b) == set(list_a) and not set(list_a) == set(list_b):
                return True
        return False

    return list(filter(lambda l: is_inside_others(l) == False, list_of_list))


def points_arrays_get_closest_ids(pts_a, pts_b):
    id_combinations = [(i, j) for i in range(len(pts_a)) for j in range(len(pts_b))]
    dists = list(map(lambda x: (pts_a[x[0]] - pts_b[x[1]]).length(), id_combinations))
    min_id = dists.index(min(dists))
    return id_combinations[min_id]


def get_bounding_box_from_points(pts):
    bb = []
    bb.append(om.MVector(99999.0, 99999.0, 99999.0))
    bb.append(om.MVector(-99999.0, -99999.0, -99999.0))

    for p in pts:
        bb[0].x = min(bb[0].x, p.x)
        bb[0].y = min(bb[0].y, p.y)
        bb[0].z = min(bb[0].z, p.z)
        bb[1].x = max(bb[1].x, p.x)
        bb[1].y = max(bb[1].y, p.y)
        bb[1].z = max(bb[1].z, p.z)
    return bb


def get_bounding_box_center_from_points(pts):
    bb = get_bounding_box_from_points(pts)
    center = (bb[0] + bb[1]) / 2
    return center


def mesh_get_vertex_normals(geo):
    if not isinstance(geo, mx.Node):
        geo = mx.encode(str(geo))
    msh = None

    if geo.is_a(mx.tMesh):
        msh = geo
    elif geo.is_a(mx.tTransform):
        for shp in geo.shapes(type=mx.tMesh):
            if not shp['intermediateObject'].read():
                msh = shp
                break

    dict_indices = string_extension_vtx_get_dict_indices([str(geo)])
    if not dict_indices:
        indices = []
    else:
        indices = dict_indices[str(geo)]

    it_vtx = om.MItMeshVertex(msh.dag_path())

    vertex_normals = []
    it_vtx.reset()

    for i in range(it_vtx.count()):

        if indices and i not in indices:
            continue

        n_av = om.MVector(0, 0, 0)
        v_normals = it_vtx.getNormals()
        for n in v_normals:
            n_av.x += n.x
            n_av.y += n.y
            n_av.z += n.z
        n_av.x /= len(v_normals)
        n_av.y /= len(v_normals)
        n_av.z /= len(v_normals)
        vertex_normals.append(n_av)
        it_vtx.next()

    return vertex_normals


def string_extension_vtx_get_dict_indices(geos):
    obj_indices = {}

    for geo in geos:
        if '.vtx[' in geo:

            obj = geo.split(".vtx[")[0]

            if not (obj in list(obj_indices)):
                obj_indices[obj] = []

            ext_index = geo.split(".vtx[")[1][:-1]
            if ':' in ext_index:
                range_index = [int(str_i) for str_i in ext_index.split(":")]
                obj_indices[obj] += range(range_index[0], range_index[1])
            else:
                obj_indices[obj].append(int(ext_index))

            obj_indices[obj] = list(set(obj_indices[obj]))

        else:
            if not (geo in list(obj_indices)):
                obj_indices[geo] = []

            obj_indices[geo] += range(0, mc.polyEvaluate(geo, v=True))
            obj_indices[geo] = list(set(obj_indices[geo]))

    return obj_indices
