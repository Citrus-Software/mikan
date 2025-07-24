# coding: utf-8

import copy

import maya.cmds as mc
import maya.api.OpenMaya as om

from mikan.core.utils import flatten_list
from mikan.core.logger import create_logger
from mikan.maya.lib.geometry import OBB

from .topology import (
    MeshTopology, get_bounding_box_center_from_points,
)
from .curve_matrix import (
    resample_matrices_flow, smooth_matrices_flow,
    merge_matrices_flow, matrices_average, smooth_matrices_grid,
)
from .matrix import (
    utils_set_matrix, utils_get_matrix, matrix_get_row, matrix_set_row,
    matrix_orthogonize, matrix_normalize
)

# from mikan.maya.utils.tmp.geminiUI_hack import GeminiUI_hack
# from mikan.maya.utils.tmp.geminiDfm_hack import skin_to_dfg

# from mikan.maya.utils.dynamic.utils import get_maya_dyn_info, set_maya_dyn_info, get_colliding_shape_indices
# from mikan.maya.utils.dynamic.build import dyn_build_collision_internal

# from mikan.templates.mod.dynamic.utils_maya import set_collision_exclusion, get_collision_exclusion

'''
from mikan.maya.utils.ui_auto import FunctionAutoUI

path = "mikan/maya/sandbox/matthieu/tmp/topology_matrix_test.py"

_ui = FunctionAutoUI( path , None, advance_setting_collapse = False  )
_ui.show()
'''


def do_obj(**kw):
    objs_selections = kw.get('objs_selections', [])
    kw.get('___________placement', False)
    pivot_selections = kw.get('pivot_selections', [])
    aim_to_center_objs = kw.get('aim_to_center_objs', True)
    # kw.get('___________global_setup', False)
    kw.get('___________skin', False)
    do_skin = kw.get('do_skin', False)
    # save_as_dfm = kw.get('save_as_dfm', False)
    # kw.get('___________mikan_rig', False)
    # use_mikan_rig = args.get('use_mikan_rig', False)  # generate mikan rig, otherwise create a custom maya rig
    # tpl_type = kw.get('tpl_type', ['bones', 'spline', 'path'][0])
    # name = kw.get('name', 'test')  # name of the template
    # parent = kw.get('parent', 'tpl_world')  # maya object that represent the parent of the rig\nwill place template under it\nwill create a mod hook if its not the root
    # ctrl_shape = kw.get('ctrl_shape', ['circle', 'square', 'sphere', 'cube', 'cylinder'][0])  # choose shape for the ctrl
    # ctrl_color = kw.get('ctrl_color', ['red', 'green', 'blue', 'yellow', 'cyan', 'purple'][3])  # choose color for the ctrl
    kw.get('___________dev', False)
    parent_obj = kw.get('parent_obj', None)
    # -- end auto ui

    use_mikan_rig = False

    to_skin_geometries = MeshTopology.extract_geo_from_components_names(objs_selections)

    # m = None
    # pivot_p = None
    if pivot_selections:
        pivot_geometries = MeshTopology.extract_geo_from_components_names(pivot_selections)

        pivot_matrices = []
        for geo in pivot_geometries:
            topo = MeshTopology(geo)
            eg = topo.create_edge_group(pivot_selections)
            vg = topo.create_vertex_group(pivot_selections)
            if eg:
                egs = eg.group_by_neighbors()

                v_curvature_normal = None
                for _Eg in egs:
                    ef = topo.create_edge_flow_from_edges_group(_Eg)

                    # get similar order - for similar matrix
                    v_curvature_normal_current = ef.get_curvature_normal()
                    if v_curvature_normal and v_curvature_normal * v_curvature_normal_current < 0:
                        ef.reverse()
                    v_curvature_normal = v_curvature_normal_current

                    m = ef.generate_matrix()
                    pivot_matrices.append(m)
            elif vg:
                pivot_matrices.append(vg.generate_matrix())

        pivot_matrix = matrices_average(pivot_matrices)

        m = om.MMatrix(pivot_matrix)

        x_m = matrix_get_row(0, m)
        y_m = matrix_get_row(1, m)
        z_m = matrix_get_row(2, m)
        m = matrix_set_row(0, m, y_m)
        m = matrix_set_row(1, m, x_m)
        m = matrix_set_row(2, m, z_m * -1)

        pivot_p = matrix_get_row(3, pivot_matrix)

        body_pivots = []
        for geo in to_skin_geometries:
            topo = MeshTopology(geo)
            vg = topo.create_vertex_group(objs_selections)
            if vg:
                center_position = vg.get_center_position()
            else:
                center_position = topo.get_center_position()
            body_pivots.append(center_position)

        body_pivot = get_bounding_box_center_from_points(body_pivots)
        v_up = body_pivot - pivot_p

        m = matrix_set_row(1, m, v_up)
        if aim_to_center_objs:
            m = matrix_orthogonize(m, 1, 0)
        else:
            m = matrix_orthogonize(m, 0, 1)

        m = matrix_normalize(m)
    else:
        to_skin_geometries = MeshTopology.extract_geo_from_components_names(objs_selections)
        pts = []
        for geo in to_skin_geometries:
            topo = MeshTopology(geo)
            vg = topo.create_vertex_group(objs_selections)
            if not vg:
                vg = topo.vertices()
            for V in vg:
                pts.append(V.pos)

        m = OBB.from_points(pts).matrix
        m = matrix_normalize(m)
        pivot_p = matrix_get_row(3, m)

    x_m = matrix_get_row(0, m)
    y_m = matrix_get_row(1, m)
    z_m = matrix_get_row(2, m)

    x_dot_max = 0
    y_dot_max = 0
    z_dot_max = 0

    for geo in to_skin_geometries:
        topo = MeshTopology(geo)
        vg = topo.create_vertex_group(objs_selections)
        if vg:
            for V in vg:
                x_dot_max = max(x_dot_max, abs((V.pos - pivot_p) * x_m))
                y_dot_max = max(y_dot_max, abs((V.pos - pivot_p) * y_m))
                z_dot_max = max(z_dot_max, abs((V.pos - pivot_p) * z_m))
        else:
            for V in topo.vertices:
                x_dot_max = max(x_dot_max, abs((V.pos - pivot_p) * x_m))
                y_dot_max = max(y_dot_max, abs((V.pos - pivot_p) * y_m))
                z_dot_max = max(z_dot_max, abs((V.pos - pivot_p) * z_m))

    x_m *= x_dot_max
    y_m *= y_dot_max
    z_m *= z_dot_max

    m = matrix_set_row(0, m, x_m)
    m = matrix_set_row(1, m, y_m)
    m = matrix_set_row(2, m, z_m)

    if use_mikan_rig:
        pass
        # # get unique tpl names
        # tpl_name = GeminiUI_hack.get_unique_tpl_names(name, 1)[0]
        #
        # # parent
        # gUI = GeminiUI_hack()
        #
        # parent_tpl = None
        # if parent:
        #     # get parent tpl
        #     parent_tpl = gUI.get_template_root_name_from_node(parent)
        # else:
        #     template = gUI.tree_get_selected()
        #     parent_tpl = str(template.node)
        #
        # shape_dir_pos = pivot_selections != []
        #
        # joints = [gUI.create_bones(
        #     tpl_name,
        #     [m],
        #     ctrl_shape,
        #     ctrl_color,
        #     parent_tpl,
        #     shape_dir_pos=shape_dir_pos
        # )]
        #
        # if parent and parent != parent_tpl:
        #     obj_tpl_root = 'tpl_' + tpl_name
        #     gUI.create_hook(obj_tpl_root, parent)
        #
        # geo_to_skin = {}
        # if do_skin:
        #     for geo in to_skin_geometries:
        #         Mesh = MeshTopology(geo)
        #
        #         Vertices_names = None
        #         Vg = Mesh.create_vertex_group(objs_selections)
        #         if Vg:
        #             Vertices_names = Vg.names()
        #         skin = _do_skin_single_joint(joints[0][0],
        #                                      geo,
        #                                      vertex_names_isolate=Vertices_names)
        #         geo_to_skin[geo] = skin
        #
        # if geo_to_skin and save_as_dfm:
        #     for geo, skin in geo_to_skin.items():
        #         Mesh = MeshTopology(geo)
        #         vertex_ids_per_chains = []
        #         Vg = Mesh.create_vertex_group(objs_selections)
        #         if Vg:
        #             vertex_ids_per_chains = [Vg.ids]
        #
        #         dfg = skin_to_dfg(skin,
        #                           joints=joints,
        #                           vertex_ids_per_chains=vertex_ids_per_chains,
        #                           convert_tpl_jnt_to_rig_jnt=True)
        #         mc.delete(skin)

    else:
        joints = _debug_build_chain([m])
        if parent_obj:
            mc.parentConstraint(parent_obj, joints[0], mo=True)

        if do_skin:
            for geo in to_skin_geometries:
                topo = MeshTopology(geo)
                vg = topo.create_vertex_group(objs_selections)
                _do_skin_single_joint(
                    joints[0],
                    geo,
                    vertex_names_isolate=vg.names(),
                )

    return True


def chain_around_axes(**args):
    pivot_selections = args.get('pivot_selections', [[]])
    ctrl_shape_selections = args.get('ctrl_shape_selections', [[]])
    # up_targets = args.get('up_targets', [])
    # args.get('___________placement', False)
    # up_target_component = args.get('up_target_component', ['x', 'y', 'z', 'p'][0])
    args.get('___________skin', False)
    do_skin = args.get('do_skin', False)
    do_hard_skin_on_ctrl_shape_selections = args.get('do_hard_skin_on_ctrl_shape_selections', True)
    # save_as_dfm = args.get('save_as_dfm', False)
    # args.get('___________mikan_rig', False)
    # use_mikan_rig = args.get('use_mikan_rig', False)
    # name = args.get('name', 'toto')
    # parent = args.get('parent', None)
    # ctrl_shape = args.get('ctrl_shape', ['circle', 'cube', 'cylinder', 'square'][0])
    # ctrl_color = args.get('ctrl_color', ['red', 'green', 'blue', 'yellow', 'cyan', 'purple'][3])
    args.get('___________dev', False)
    debug = args.get('debug', False)
    # -- end auto ui

    use_mikan_rig = False

    body_geometries = MeshTopology.extract_geo_from_components_names(flatten_list(pivot_selections))

    body_pivots = []
    for geo in body_geometries:
        topo = MeshTopology(geo)
        for sel in pivot_selections:
            vg = topo.create_vertex_group(sel)
            if vg:
                center_position = vg.get_center_position()
            else:
                center_position = topo.get_center_position()
            body_pivots.append(center_position)

    matrices = []
    v_up = om.MVector(0, 1, 0)
    v_dir = None
    for i in range(len(body_pivots)):
        p = body_pivots[i]
        if i < len(body_pivots) - 1:
            v_dir = body_pivots[i + 1] - body_pivots[i]

        m = om.MMatrix()
        m = matrix_set_row(0, m, v_up)
        m = matrix_set_row(1, m, v_dir)
        m = matrix_set_row(3, m, p)
        m = matrix_orthogonize(m, 1, 0)
        m = matrix_normalize(m)
        matrices.append(m)

    for i in range(len(body_pivots)):

        if len(ctrl_shape_selections) <= i:
            continue

        m = matrices[i]
        x_m = matrix_get_row(0, m)
        y_m = matrix_get_row(1, m)
        z_m = matrix_get_row(2, m)
        p_m = matrix_get_row(3, m)

        x_dot_max = 0
        y_dot_max = 0
        z_dot_max = 0

        for geo in MeshTopology.extract_geo_from_components_names(ctrl_shape_selections[i]):
            topo = MeshTopology(geo)
            vg = topo.create_vertex_group(ctrl_shape_selections[i])
            if vg:
                for v in vg:
                    x_dot_max = max(x_dot_max, abs((v.pos - p_m) * x_m))
                    y_dot_max = max(y_dot_max, abs((v.pos - p_m) * y_m))
                    z_dot_max = max(z_dot_max, abs((v.pos - p_m) * z_m))
            else:
                for v in topo.vertices:
                    x_dot_max = max(x_dot_max, abs((v.pos - p_m) * x_m))
                    y_dot_max = max(y_dot_max, abs((v.pos - p_m) * y_m))
                    z_dot_max = max(z_dot_max, abs((v.pos - p_m) * z_m))

        x_m *= x_dot_max
        y_m *= y_dot_max
        z_m *= z_dot_max

        m = matrix_set_row(0, m, x_m)
        m = matrix_set_row(1, m, y_m)
        m = matrix_set_row(2, m, z_m)

        matrices[i] = m

    geometries = []
    for i in range(len(ctrl_shape_selections)):
        for geo in MeshTopology.extract_geo_from_components_names(ctrl_shape_selections[i]):
            geometries.append(geo)
    geometries = list(set(geometries))

    if use_mikan_rig:
        pass
        # # get unique tpl names
        # tpl_name = GeminiUI_hack.get_unique_tpl_names(name, 1)[0]
        #
        # # parent
        # gUI = GeminiUI_hack()
        #
        # parent_tpl = None
        # if parent:
        #     parent_tpl = gUI.get_template_root_name_from_node(parent)
        # else:
        #     template = gUI.tree_get_selected()
        #     parent_tpl = str(template.node)
        #
        # joints = [gUI.create_bones(tpl_name,
        #                            matrices,
        #                            ctrl_shape,
        #                            ctrl_color,
        #                            parent_tpl)]
        #
        # if parent and parent != parent_tpl:
        #     obj_tpl_root = 'tpl_' + tpl_name
        #     gUI.create_hook(obj_tpl_root, parent)
        #
        # skins = []
        # if do_skin:
        #
        #     geo_to_skin = {}
        #     for geo in geometries:
        #         skin = _do_skin(joints, geo, debug=debug)
        #         geo_to_skin[geo] = skin
        #         skins.append(skin)
        #
        #     if do_hard_skin_on_ctrl_shape_selections:
        #         for i in range(len(ctrl_shape_selections)):
        #             for geo in MeshTopology.extract_geo_from_components_names(ctrl_shape_selections[i]):
        #
        #                 Mesh = MeshTopology(geo)
        #                 Vg = Mesh.create_vertex_group(ctrl_shape_selections[i])
        #                 if Vg:
        #                     for V in Vg:
        #                         mc.skinPercent(geo_to_skin[geo], '{}.vtx[{}]'.format(geo, V.id), transformValue=[(joints[0][i], 1.0)])
        #                         mc.skinPercent(geo_to_skin[geo], '{}.vtx[{}]'.format(geo, V.id), transformValue=[(joints[0][i], 1.0)])
        #
        # if skins and save_as_dfm:
        #     for skin in skins:
        #         dfg = skin_to_dfg(skin,
        #                           joints=joints,
        #                           vertex_ids_per_chains=[],
        #                           convert_tpl_jnt_to_rig_jnt=True)
        #         mc.delete(skin)

    else:
        joints = _debug_build_chain(matrices)

        if do_skin:
            geo_to_skin = {}
            for geo in geometries:
                geo_to_skin[geo] = _do_skin([joints], geo, debug=debug)

            if do_hard_skin_on_ctrl_shape_selections:
                for i in range(len(ctrl_shape_selections)):
                    for geo in MeshTopology.extract_geo_from_components_names(ctrl_shape_selections[i]):

                        topo = MeshTopology(geo)
                        vg = topo.create_vertex_group(ctrl_shape_selections[i])
                        if vg:
                            for v in vg:
                                mc.skinPercent(geo_to_skin[geo], '{}.vtx[{}]'.format(geo, v.id), transformValue=[(joints[i], 1.0)])
                                mc.skinPercent(geo_to_skin[geo], '{}.vtx[{}]'.format(geo, v.id), transformValue=[(joints[i], 1.0)])
    return True


def do_surface(**kw):
    input_selection = kw.get('input_selection', [])  # edge flow or 2 vertices - shortest path
    dist_between_ctrls = kw.get('dist_between_ctrls', -0.1)  #
    kw.get('___________placement', False)
    orient_up_targets = kw.get('orient_up_targets', [])  # maya transforms as ref for the up\nclosest chain element <-> up_targets association will be created \nworks with orient_up_target_component
    orient_up_target_component = kw.get('orient_up_target_component', ['x', 'y', 'z', 'p'][3])  # wich component of orient_up_targets is ref for the up \nworks with orient_up_target_component
    orient_deduce_from_shape = kw.get('orient_deduce_from_shape', False)
    scale_base_on_mesh = kw.get('scale_base_on_mesh', True)
    scale_vertices = kw.get('scale_vertices', [])
    positions_smooth = kw.get('positions_smooth', range(0, 5, 1)[0])
    orients_smooth = kw.get('orients_smooth', range(0, 5, 1)[0])
    scales_smooth = kw.get('scales_smooth', range(0, 5, 1)[0])
    kw.get('___________global_setup', False)
    only_foward_policy = kw.get('only_forward_policy', False)
    start_override_target = kw.get('start_override_target', '')  # maya transform that will indicate the start of the chain
    kw.get('___________skin', False)
    do_skin = kw.get('do_skin', False)
    # save_as_dfm = kw.get('save_as_dfm', False)
    # kw.get('___________mikan_rig', False)
    # use_mikan_rig = kw.get('use_mikan_rig', False)  # generate mikan rig, otherwise create a custom maya rig
    # tpl_type = kw.get('tpl_type', ['bones', 'spline', 'path'][0])
    # name = kw.get('name', 'test')  # name of the template
    # parent = kw.get('parent', 'tpl_world')  # maya object that represent the parent of the rig\nwill place template under it\nwill create a mod hook if its not the root
    # ctrl_shape = kw.get('ctrl_shape', ['circle', 'square', 'sphere', 'cube', 'cylinder'][0])  # choose shape for the ctrl
    # ctrl_color = kw.get('ctrl_color', ['red', 'green', 'blue', 'yellow', 'cyan', 'purple'][3])  # choose color for the ctrl
    kw.get('___________dev', False)
    debug = kw.get('debug', False)
    # -- end auto ui

    use_mikan_rig = False

    geometries = MeshTopology.extract_geo_from_components_names(input_selection)

    geo = geometries[0]
    topo = MeshTopology(geo)

    if '.vtx[]' in input_selection[0]:
        ef = topo.create_shortest_path(input_selection[0], input_selection[1], only_forward_policy=only_foward_policy)
    else:
        eg = topo.create_edge_group(input_selection)
        ef = topo.create_edge_flow_from_edges_group(eg)

    if start_override_target:
        p_start = matrix_get_row(3, utils_get_matrix(start_override_target))
        ef.reverse_if_point_is_closest_to_end(p_start)

    matrices = ef.generate_matrices(
        up_targets=orient_up_targets,
        up_target_component=orient_up_target_component,
        deduce_orient_from_shape=orient_deduce_from_shape,
    )

    if positions_smooth:
        matrices = smooth_matrices_flow(
            matrices,
            positions_smooth,
            pin_ids=[0, len(matrices) - 1],
            position=True,
            rotation=False,
            scale=False,
        )

    if orients_smooth:
        matrices = smooth_matrices_flow(
            matrices,
            orients_smooth,
            pin_ids=[],
            position=False,
            rotation=True,
            scale=False,
        )

    if scales_smooth:
        matrices = smooth_matrices_flow(
            matrices,
            scales_smooth,
            pin_ids=[],
            position=False,
            rotation=False,
            scale=True,
        )

    if dist_between_ctrls is not None and dist_between_ctrls > 0:
        matrices = resample_matrices_flow(
            matrices,
            override_nbr_output=dist_between_ctrls,
            is_loop=False,
            debug=debug)

    vertices_to_process = topo.vertices[:]
    if scale_vertices:
        vertices_to_process = []
        for v in topo.vertices[:]:
            if v.name() in scale_vertices:
                vertices_to_process.append(v)

    i_matrix_to_vertices = [[] for _ in range(len(matrices))]
    if scale_base_on_mesh:
        # fix scale - get matrix_to_vertices
        i_matrix_to_vertices = _sort_vertices_in_each_chain_matrices(vertices_to_process, matrices)
        matrices = _scale_matrices_to_match_geo(matrices, i_matrix_to_vertices)

    if use_mikan_rig:
        pass
        # # get unique tpl names
        # tpl_name = GeminiUI_hack.get_unique_tpl_names(name, 1)[0]
        #
        # # parent
        # gUI = GeminiUI_hack()
        #
        # parent_tpl = None
        # if parent:
        #     parent_tpl = gUI.get_template_root_name_from_node(parent)
        # else:
        #     template = gUI.tree_get_selected()
        #     parent_tpl = str(template.node)
        #
        # joints = []
        # joints.append(gUI.create_bones(tpl_name,
        #                                matrices,
        #                                ctrl_shape,
        #                                ctrl_color,
        #                                parent_tpl))
        #
        # if parent and parent != parent_tpl:
        #     obj_tpl_root = 'tpl_' + tpl_name
        #     gUI.create_hook(obj_tpl_root, parent)
        #
        # skins = []
        # if do_skin:
        #     skin = _do_skin(joints, geo, debug=debug)
        #
        #     if skin and save_as_dfm:
        #         dfg = skin_to_dfg(skin,
        #                           joints=joints,
        #                           vertex_ids_per_chains=[[V.id for V in _Vertices] for _Vertices in i_matrix_to_vertices],
        #                           convert_tpl_jnt_to_rig_jnt=True)
        #     mc.delete(skin)

    else:
        joints = []
        joints.append(_debug_build_chain(matrices))

        if do_skin:
            _do_skin(joints, geo, debug=debug)

    return [[v.name() for v in vertices] for vertices in i_matrix_to_vertices]


def _sort_vertices_in_each_chain_matrices(vertices_to_process, matrices):
    axe_dir = 1

    i_matrix_to_vertices = [[] for i in range(len(matrices))]

    _Vertices = vertices_to_process[:]
    for i in reversed(range(len(matrices))):
        m = matrices[i]
        _Vertices_next = _Vertices[:]
        for v in _Vertices:
            p = matrix_get_row(3, m)
            dot = (v.pos - p) * matrix_get_row(axe_dir, m)
            if 0 < dot:
                i_matrix_to_vertices[i].append(v)
                _Vertices_next.remove(v)
        _Vertices = _Vertices_next[:]
    return i_matrix_to_vertices


def _scale_matrices_to_match_geo(matrices, i_matrix_to_vertices):
    axe_up = 0
    axe_side = 2
    for i, m in enumerate(matrices):
        p = matrix_get_row(3, m)
        v_up = matrix_get_row(axe_up, m)
        v_side = matrix_get_row(axe_side, m)
        v_up.normalize()
        v_side.normalize()
        up_size_max = 0
        side_size_max = 0
        for v in i_matrix_to_vertices[i]:
            up_size_max = max(up_size_max, abs((v.pos - p) * v_up))
            side_size_max = max(side_size_max, abs((v.pos - p) * v_side))

        v_up *= up_size_max
        v_side *= side_size_max

        matrices[i] = matrix_set_row(axe_up, matrices[i], v_up)
        matrices[i] = matrix_set_row(axe_side, matrices[i], v_side)
    return matrices


def do_tubes(**kw):
    input_selection = kw.get('input_selection', [])  # edge loop or meshes
    dist_between_ctrls = kw.get('dist_between_ctrls', -0.1)  # distance that separate ctrl to each other\nnegative value mean one ctrl per loop
    kw.get('___________ctrl_placement', False)
    orient_deduce_from_shape = kw.get('orient_deduce_from_shape', ['', 'edge_loop', 'all_edge_loops', 'global_mesh'][1])  # the shape of the edge loop will influence the orientation\nWorks well with square shapes
    orient_up_targets = kw.get('orient_up_targets', [])  # maya transforms as ref for the up\nclosest chain element <-> up_targets association will be created \nworks with orient_up_target_component
    orient_up_target_component = kw.get('orient_up_target_component', ['x', 'y', 'z', 'p'][3])  # wich component of orient_up_targets is ref for the up \nworks with orient_up_target_component
    orients_follow_topo = kw.get('orients_follow_topo', True)  # orientation will follow the edge flow throught the chain
    positions_smooth = kw.get('positions_smooth', range(0, 20, 1)[0])  # smooth positions of the chain
    orients_smooth = kw.get('orients_smooth', range(0, 20, 1)[0])  # smooth orient of the chain
    scales_smooth = kw.get('scales_smooth', range(0, 20, 1)[0])  # smooth scales of the chain
    kw.get('___________global_setup', False)
    edge_loop_2_branches_sides_operation = kw.get('edge_loop_2_branches_sides_operation', ['merge', 'merge_and_loop', 'keep_longest', 'keep_shortest'][0])  # from the edge loop input, what to do with the two branches
    start_override_target = kw.get('start_override_target', '')  # maya transform that will indicate the start of the chain
    merge_output_by_nbr = kw.get('merge_output_by_nbr', range(1, 5, 1)[0])  # merge each N chain together
    kw.get('___________skin', False)
    do_skin = kw.get('do_skin', False)  # do a skin of the mesh
    # save_as_dfm = kw.get('save_as_dfm', False)  # save that skin as dfn
    # kw.get('___________mikan_rig', False)
    # use_mikan_rig = kw.get('use_mikan_rig', False)  # generate mikan rig, otherwize create a custom maya rig
    # tpl_type = kw.get('tpl_type', ['bones', 'spline', 'path'][0])
    # name = kw.get('name', 'test')  # name of the template
    # parent = kw.get('parent', 'tpl_world')  # maya object that represent the parent of the rig\nwill place template under it\nwill create a mod hook if its not the root
    # ctrl_shape = kw.get('ctrl_shape', ['circle', 'square', 'sphere', 'cube', 'cylinder'][0])  # choose shape for the ctrl
    # ctrl_color = kw.get('ctrl_color', ['red', 'green', 'blue', 'yellow', 'cyan', 'purple'][3])  # choose color for the ctrl
    # path_driver_nbr = kw.get('path_driver_nbr', range(3, 10, 1)[0])  # only if tpl is path
    # kw.get('___________dynamic', False)
    # setup_dynamic = kw.get('setup_dynamic', False)
    kw.get('___________dev', False)
    topo_max_change = kw.get('topo_max_change', range(0, 10)[3])  # allow some messy topologie
    close_loop_max_step = kw.get('close_loop_max_step', range(0, 10)[3])  # allow some messy topologie
    debug = kw.get('debug', False)  # debug
    # -- end ui auto

    use_mikan_rig = False

    # dyn_collision_suffix = "_dynCol"

    log = create_logger('do_tubes')
    log.info('Start')

    geometries = MeshTopology.extract_geo_from_components_names(input_selection)

    log.info('{} geometries found'.format(len(geometries)))
    log.info('Get topologie info...')

    geo_to_elfs = {}
    for i, geo in enumerate(geometries):
        topo = MeshTopology(geo)
        eg = topo.create_edge_group(input_selection)

        els = []
        if eg:
            egs = eg.group_by_neighbors()

            for _eg in egs:
                el = topo.create_edge_loop_from_edges_group(_eg)
                els.append(el)

            log.info('\t%s/%s - %s selected Edge Loop for %s' % (i + 1, len(geometries), len(els), geo))
        else:
            el = topo.create_edge_loop_from_mesh()
            els.append(el)
            log.info('\t%s/%s - no selected Edge Loop for %s' % (i + 1, len(geometries), geo))

        # edge loop to edge loop flow
        elfs = []
        for el in els:
            elf = topo.create_edge_loop_flow_from_edge_loop(
                el,
                topo_max_change=topo_max_change,
                close_loop_max_step=close_loop_max_step,
                outputs_override=edge_loop_2_branches_sides_operation,
            )

            # reverse
            if start_override_target:
                p_start = matrix_get_row(3, utils_get_matrix(start_override_target))
                elf.reverse_if_point_is_closest_to_end_loop(p_start)

            elfs.append(elf)

        geo_to_elfs[geo] = elfs

        # Check if Elfs shared the same elements
    for geo in geo_to_elfs:
        elfs = geo_to_elfs[geo]
        for i in range(len(elfs)):
            for j in range(len(elfs)):
                if i == j:
                    continue
                if not elfs[i] or not elfs[j]:
                    continue

                if elfs[i].get_common_Edge_loops(elfs[j]):
                    success = elfs[i].build_bridge(elfs[j])
                    if success:
                        log.info('Build bridge for %s' % (geo))
                        elfs[j] = None
        geo_to_elfs[geo] = [elf for elf in elfs if elf]

    log.info('Get Matrices...')

    geo_to_matrices_lists = {}
    geo_to_matrices_resampled_lists = {}
    geo_to_curvature_normals = {}
    for i_geo, geo in enumerate(geo_to_elfs):

        out_matrices = []
        out_matrices_resampled = []
        curvature_normals = []
        for i_elf, elf in enumerate(geo_to_elfs[geo]):
            log.info('\t%s/%s - %s - Edge Loop flow %s/%s - Generate matrices...' % (i_geo + 1, len(geometries), geo, i_elf + 1, len(geo_to_elfs[geo])))

            matrices_from_elf = elf.generate_matrices(
                up_targets=orient_up_targets,
                up_target_component=orient_up_target_component,
                orient_follow_topo=orients_follow_topo,
                deduce_orient_from_shape=orient_deduce_from_shape,
            )

            log.info('\t\t%s matrices was generated' % len(matrices_from_elf))

            curvature_normals.append(elf.get_curvature_normal())

            matrices_resampled = matrices_from_elf
            if 0 < dist_between_ctrls:
                matrices_resampled = resample_matrices_flow(
                    matrices_from_elf,
                    override_nbr_output=dist_between_ctrls,
                    is_loop=elf.is_loop(),
                    debug=debug,
                )
                log.info('\t\tResample matrices Done, %s matrices remained' % len(matrices_resampled))

            if edge_loop_2_branches_sides_operation == 'merge_and_loop':
                log.info('\t\t\tMake it loop...')

                if start_override_target:
                    p_start = matrix_get_row(3, utils_get_matrix(start_override_target))
                else:
                    el_user_input = elf[elf.user_input_ids[0]]
                    p_start = el_user_input.get_center_position()

                matrices_resampled = _matrices_flow_merge_and_loop(
                    matrices_resampled,
                    p_start,
                    matrix_end_override=matrices_from_elf[-1],
                )

                matrices_from_elf = _matrices_flow_merge_and_loop(
                    matrices_from_elf,
                    p_start,
                )

                log.info('\t\t\tLoop done (add one matrix) total matrices %s' % len(matrices_resampled))

            out_matrices_resampled.append(matrices_resampled)
            out_matrices.append(matrices_from_elf)

        if merge_output_by_nbr > 1:
            out_matrices_resampled = merge_matrices_flow(out_matrices_resampled, merge_output_by_nbr)
            out_matrices = merge_matrices_flow(out_matrices, merge_output_by_nbr)
            log.info('\tMerge output {0} by {0} Done : {1} Matrices_flows remained'.format(merge_output_by_nbr, len(out_matrices)))

        if positions_smooth:

            for i in range(len(out_matrices_resampled)):
                out_matrices_resampled[i] = smooth_matrices_flow(
                    out_matrices_resampled[i],
                    positions_smooth,
                    pin_ids=[0, len(out_matrices_resampled) - 1],
                    position=True,
                    rotation=False,
                    scale=False,
                )

            for i in range(len(out_matrices)):
                out_matrices[i] = smooth_matrices_flow(
                    out_matrices[i],
                    positions_smooth,
                    pin_ids=[0, len(out_matrices) - 1],
                    position=True,
                    rotation=False,
                    scale=False,
                )

            log.info('\tSmooth position with %s iter Done' % positions_smooth)

        if orients_smooth:

            for i in range(len(out_matrices_resampled)):
                out_matrices_resampled[i] = smooth_matrices_flow(
                    out_matrices_resampled[i],
                    orients_smooth,
                    pin_ids=[],
                    position=False,
                    rotation=True,
                    scale=False,
                )

            for i in range(len(out_matrices)):
                out_matrices[i] = smooth_matrices_flow(
                    out_matrices[i],
                    orients_smooth,
                    pin_ids=[],
                    position=False,
                    rotation=True,
                    scale=False,
                )

            log.info('\tSmooth orientation with %s iter Done' % orients_smooth)

        if scales_smooth:

            for i in range(len(out_matrices_resampled)):
                out_matrices_resampled[i] = smooth_matrices_flow(
                    out_matrices_resampled[i],
                    scales_smooth,
                    pin_ids=[],
                    position=False,
                    rotation=True,
                    scale=False,
                )

            for i in range(0, len(out_matrices)):
                out_matrices[i] = smooth_matrices_flow(
                    out_matrices[i],
                    scales_smooth,
                    pin_ids=[],
                    position=False,
                    rotation=True,
                    scale=False,
                )

            log.info('\tSmooth scale with %s iter Done' % scales_smooth)

        if merge_output_by_nbr > 1:
            log.info('Readjust matrix scale to mesh...')
            # topo = MeshTopology(geo)

            j = 0
            for i in range(0, len(out_matrices_resampled)):
                vertices_to_process = []
                for k in range(merge_output_by_nbr):
                    vertices_to_process += [V for V in geo_to_elfs[geo][j + k].vertices]
                j += merge_output_by_nbr

                i_matrix_to_vertices = _sort_vertices_in_each_chain_matrices(vertices_to_process, out_matrices_resampled[i])
                out_matrices_resampled[i] = _scale_matrices_to_match_geo(out_matrices_resampled[i], i_matrix_to_vertices)

        geo_to_matrices_lists[geo] = out_matrices
        geo_to_matrices_resampled_lists[geo] = out_matrices_resampled
        geo_to_curvature_normals[geo] = curvature_normals

    if use_mikan_rig:
        pass
        # log.info('Build mikan template...')
        #
        # # get unique tpl names
        # tpl_nbr = len([m for geo in geo_to_matrices_resampled_lists for m in flatten_list(geo_to_matrices_resampled_lists[geo])])
        # tpl_names = GeminiUI_hack.get_unique_tpl_names(name, tpl_nbr)
        #
        # gUI = GeminiUI_hack()
        # parent_tpl = None
        # if parent:
        #     parent_tpl = gUI.get_template_root_name_from_node(parent)
        # else:
        #     template = gUI.tree_get_selected()
        #     parent_tpl = str(template.node)
        #
        # log.info('\tParent found : %s' % parent_tpl)
        #
        # iNames = 0
        # geo_to_skin = {}
        # geo_to_joints = {}
        # for iGeo, geo in enumerate(geo_to_matrices_resampled_lists):
        #
        #     joints = []
        #     for iM, matrices in enumerate(geo_to_matrices_resampled_lists[geo]):
        #
        #         tpl_name = tpl_names[iNames]
        #
        #         if tpl_type == 'bones':
        #             joints.append(gUI.create_bones(tpl_name,
        #                                            matrices,
        #                                            ctrl_shape,
        #                                            ctrl_color,
        #                                            parent_tpl))
        #         elif tpl_type == 'spline':
        #             joints.append(gUI.create_spline(tpl_name,
        #                                             matrices,
        #                                             ctrl_shape,
        #                                             ctrl_color,
        #                                             parent_tpl))
        #         elif tpl_type == 'path':
        #             curve_base_points = [matrix_getRow(3, m) for m in geo_to_matrices_lists[geo][iM]]
        #             is_loop = geo_to_Elfs[geo][iM].is_loop()
        #             if edge_loop_2_branches_sides_operation == 'merge_and_loop':
        #                 is_loop = True
        #             joints.append(gUI.create_path(tpl_name,
        #                                           parent_tpl,
        #                                           matrices,
        #                                           curve_base_points,
        #                                           ctrl_shape,
        #                                           ctrl_color,
        #                                           nbr_driver=path_driver_nbr,
        #                                           vUp_ref=geo_to_curvature_normals[geo][iM],
        #                                           loop=is_loop))
        #
        #         log.info('\t%s/%s - %s - %s built %s/%s ' % (iGeo + 1,
        #                                                      len(geometries),
        #                                                      geo,
        #                                                      tpl_type,
        #                                                      iM + 1,
        #                                                      len(geo_to_matrices_resampled_lists[geo])))
        #
        #         obj_tpl_root = 'tpl_' + tpl_name
        #         if parent and parent != parent_tpl:
        #             gUI.create_hook(obj_tpl_root, parent)
        #             log.info('\t\tHook create between %s and the parent %s' % (obj_tpl_root, parent))
        #
        #         if setup_dynamic:
        #
        #             gUI.make_tpl_dyn(obj_tpl_root, passif=False, remove=False)
        #
        #             dyn_info = get_maya_dyn_info()
        #
        #             ins = ['j_{}{}'.format(tpl_name, k + 1) for k in range(len(joints[-1]))]
        #             outs = ['sk_{}{}'.format(tpl_name, k + 1) for k in range(len(joints[-1]))]
        #             ctrls = ['c_{}{}'.format(tpl_name, k + 1) for k in range(len(joints[-1]))]
        #             if len(joints[-1]) == 1:
        #                 ins = ['j_{}'.format(tpl_name)]
        #                 outs = ['sk_{}'.format(tpl_name)]
        #                 ctrls = ['c_{}'.format(tpl_name)]
        #                 # set rig info
        #             dyn_info.setdefault('rig_info', {})
        #             dyn_info['rig_info'].setdefault(tpl_name, {})
        #             dyn_info['rig_info'][tpl_name]['root'] = None
        #             dyn_info['rig_info'][tpl_name]['in'] = ins
        #             dyn_info['rig_info'][tpl_name]['out'] = outs
        #             dyn_info['rig_info'][tpl_name]['ctrl'] = ctrls
        #             dyn_info['rig_info'][tpl_name]['ctrl_to_out'] = {ctrl: [out] for ctrl, out in zip(ctrls, outs)}
        #             dyn_info['rig_info'][tpl_name]['out_branches'] = {}
        #
        #             dyn_info['rig_info'][tpl_name]['in_branches'] = []
        #             dyn_info['rig_info'][tpl_name]['out_to_dyn_ctrl'] = {}
        #             dyn_info['rig_info'][tpl_name]['actif'] = True
        #
        #             # set override attrs
        #             dyn_info.setdefault('modif', {})
        #             dyn_info['modif'].setdefault('override_ctrls_attrs_values', {})
        #             dyn_info['modif']['override_ctrls_attrs_values'].setdefault(ctrls[0], {})
        #             dyn_info['modif']['override_ctrls_attrs_values'][ctrls[0]]['animationPinPosition'] = 1
        #
        #             set_maya_dyn_info(dyn_info)
        #
        #             # build collision shapes
        #             is_circle_coef = geo_to_Elfs[geo][iM][0].is_circle()
        #
        #             for k, out in enumerate(outs):
        #                 col_name = '{}{}{}'.format(out, dyn_collision_suffix, k)
        #                 col = dyn_build_collision_internal(col_name, ins[k])
        #                 m = matrices[k]
        #                 vY = matrix_getRow(1, m)
        #                 p_new = matrix_getRow(3, m) + vY / 2.0
        #
        #                 m = matrix_setRow(3, m, p_new)
        #
        #                 if 0.5 < is_circle_coef:
        #                     # cylinder
        #                     mc.setAttr('%s.gem_collider' % col, 3)
        #                     m = matrix_setRow(1, m, matrix_getRow(1, m) * 0.5)
        #                 else:
        #                     # cube
        #                     mc.setAttr('%s.gem_collider' % col, 1)
        #                     m = matrix_setRow(0, m, matrix_getRow(0, m) * 2)
        #                     m = matrix_setRow(2, m, matrix_getRow(2, m) * 2)
        #
        #                 utils_set_matrix(col, m)
        #
        #         iNames += 1
        #
        #     geo_to_joints[geo] = joints
        #     skin = None
        #     if do_skin:
        #
        #         skin = _do_skin(joints,
        #                         geo,
        #                         joints_matrices=geo_to_matrices_resampled_lists[geo],
        #                         vertex_ids_per_chains=[[V.id for V in Elf.vertices] for Elf in geo_to_Elfs[geo]],
        #                         debug=debug)
        #         geo_to_skin[geo] = skin
        #         log.info('\t\t\tSkin Done')
        #
        #         if skin and save_as_dfm:
        #             dfg = skin_to_dfg(skin,
        #                               joints=joints,
        #                               vertex_ids_per_chains=[[V.id for V in Elf.vertices] for Elf in geo_to_Elfs[geo]],
        #                               convert_tpl_jnt_to_rig_jnt=True)
        #             mc.delete(skin)
        #             log.info('\t\t\tConvert skin into Dfm Done')
        #
        # """
        # disable_collision_for_colliding_shape_at_init_pose  = args.get( 'disable_collision_for_colliding_shape_at_init_pose', True)
        # if setup_dynamic and disable_collision_for_colliding_shape_at_init_pose:
        #
        #     # get collision shapes info
        #     dyn_collision_shapes = mc.ls( '*%s*' % dyn_collision_suffix , type = 'transform')
        #     dyn_collision_shapes_matrices = [ utils_get_matrix(trsf) for trsf in dyn_collision_shapes]
        #     dyn_collision_shapes_types = [ mc.getAttr( '%s.gem_collider' % trsf ) for trsf in dyn_collision_shapes]
        #
        #     # check if there is collision
        #     colliding_pair_indices = get_colliding_shape_indices(dyn_collision_shapes_matrices,
        #                                                          dyn_collision_shapes_types)
        #
        #     # check if collision are already written
        #     colliding_pair_names_old = get_collision_exclusion()
        #     colliding_pair_names_to_add = []
        #     for id_pair in colliding_pair_indices:
        #         nA = dyn_collision_shapes[id_pair[0]]
        #         nB = dyn_collision_shapes[id_pair[1]]
        #         if {nA,nB} not in colliding_pair_names_old:
        #             colliding_pair_names_to_add.append({nA,nB})
        #
        #     # set none existing collision pair exclusion
        #     for name_pair in colliding_pair_names_to_add:
        #         set_collision_exclusion( name_pair)
        # """
        #
        # log.info('Build gemini template Done')

    else:
        log.info('Build custom maya rig...')
        for geo in geo_to_matrices_resampled_lists:
            joints = []
            for matrices in geo_to_matrices_resampled_lists[geo]:
                joints.append(_debug_build_chain(matrices))
            if do_skin:
                _do_skin(joints, geo, debug=debug)
        log.info('Build custom maya rig Done')

    return True


def _matrices_flow_merge_and_loop(
        matrices_to_process,
        start_override_point,
        matrix_end_override=None,
):
    m_end = matrices_to_process[-1]
    if matrix_end_override:
        m_end = matrix_end_override

    # get end matrices 
    m = m_end
    y_m = matrix_get_row(3, matrices_to_process[0]) - matrix_get_row(3, m_end)
    m = matrix_set_row(1, m, y_m)
    m = matrix_orthogonize(m, 1, 0)
    matrices_to_process.append(m)

    # split with start point
    i_start = -1
    min_dist = 9999999
    for i, m in enumerate(matrices_to_process):
        p = matrix_get_row(3, m)
        dist = (p - start_override_point).length()
        if dist < min_dist:
            min_dist = dist
            i_start = i
    matrices_to_process = matrices_to_process[i_start:] + matrices_to_process[:i_start]
    return matrices_to_process


def do_cloth(**kw):
    edge_flow_a = kw.get('edge_flow_a', [])
    output_nbr_a = kw.get('output_nbr_a', range(1, 10)[1])
    dist_between_ctrls = kw.get('dist_between_ctrls', -0.1)
    kw.get('___________ctrl_placement', False)
    positions_smooth = kw.get('positions_smooth', range(0, 20, 1)[0])  # smooth positions of the chain
    orients_smooth = kw.get('orients_smooth', range(0, 20, 1)[0])  # smooth orient of the chain
    scales_smooth = kw.get('scales_smooth', range(0, 20, 1)[0])  # smooth scales of the chain
    kw.get('___________global_setup', False)
    dir_target = kw.get('dir_target', '')  # maya transforms as ref for the up\nclosest chain element <-> up_targets association will be created \nworks with orient_up_target_component
    dir_target_component = kw.get('dir_target_component', ['x', 'y', 'z', 'p'][3])  # wich component of orient_up_targets is ref for the up \nworks with orient_up_target_component
    skip_vertices = kw.get('skip_vertices', [])
    kw.get('___________skin', False)
    do_skin = kw.get('do_skin', False)
    # save_as_dfm = kw.get('save_as_dfm', False)
    # kw.get('___________gemini_rig', False)
    # use_mikan_rig = kw.get('use_gemini_rig', False)  # generate gemini rig, otherwise create a custom maya rig
    # tpl_type = kw.get('tpl_type', ['bones', 'spline', 'path'][0])
    # name = kw.get('name', 'test')  # name of the template
    # parent = kw.get('parent', 'tpl_world')  # maya object that represent the parent of the rig\nwill place template under it\nwill create a mod hook if its not the root
    # ctrl_shape = kw.get('ctrl_shape', ['circle', 'square', 'sphere', 'cube', 'cylinder'][0])  # choose shape for the ctrl
    # ctrl_color = kw.get('ctrl_color', ['red', 'green', 'blue', 'yellow', 'cyan', 'purple'][3])  # choose color for the ctrl
    kw.get('___________dev', False)
    debug = kw.get('debug', False)
    debug_build_mesh = kw.get('debug_build_mesh', False)
    # -- end ui auto

    use_mikan_rig = False

    geometries = MeshTopology.extract_geo_from_components_names(edge_flow_a)
    geo = geometries[0]

    topo = MeshTopology(geo)
    eg = topo.create_edge_group(edge_flow_a)
    egs = eg.group_by_neighbors()

    ef_main = topo.create_edge_flow_from_edges_group(egs[0])

    v_flow_force_dir = None
    if dir_target:
        _m = utils_get_matrix(dir_target)
        if dir_target_component in 'xyz':
            if dir_target_component == 'x':
                v_flow_force_dir = matrix_get_row(0, _m)
            elif dir_target_component == 'y':
                v_flow_force_dir = matrix_get_row(1, _m)
            elif dir_target_component == 'z':
                v_flow_force_dir = matrix_get_row(2, _m)
        else:
            v_flow_force_dir = matrix_get_row(3, _m) - ef_main.vertices.get_center_position()

    efs = []
    skip_components = copy.deepcopy(ef_main.vertices)
    for v in ef_main.vertices:
        for e in v.edges:
            if e not in ef_main:
                _ef = topo.create_edge_flow_from_edge(e, v)
                if v_flow_force_dir:
                    v_flow_start = (_ef.vertices[1].pos - _ef.vertices[0].pos)
                    dot = v_flow_force_dir * v_flow_start
                    if dot < 0:
                        continue
                efs.append(_ef)
                skip_components += _ef.vertices

    stop_branches = []
    for _ in range(500):

        # get all possibilities
        something_happened = False
        efs_grown = []
        for ef in efs:
            efs_possible_grows = ef.get_possible_grow(
                skip_Components=skip_components,
                only_foward_policy=True,
            )
            dot_max = -1
            ef_same_dir = None
            for _ef in efs_possible_grows:
                _vg = _ef.vertices

                if skip_vertices and _vg[-1].name() in skip_vertices:
                    continue

                v_after = (_vg[-1].pos - _vg[-2].pos)
                v_before = (_vg[-2].pos - _vg[0].pos)
                v_after.normalize()
                v_before.normalize()
                dot = v_after * v_before
                if dot_max < dot and 0.1 < dot:
                    dot_max = dot
                    ef_same_dir = _ef
                    something_happened = True

            if ef_same_dir:
                efs_grown.append(ef_same_dir)
            else:
                stop_branches.append(ef)

        # get one path per end vertex, remove others
        all_possible_grows = {}
        for ef in efs_grown:
            all_possible_grows.setdefault(ef.vertices[-1], [])
            all_possible_grows[ef.vertices[-1]].append(ef)

        grown_paths = []
        grown_paths = [None for i in range(len(all_possible_grows))]
        for i, v in enumerate(all_possible_grows):
            dot_max = -1
            for ef in all_possible_grows[v]:
                _vg = ef.vertices
                v_after = (_vg[-1].pos - _vg[-2].pos)
                v_before = (_vg[-2].pos - _vg[0].pos)

                v_after.normalize()
                v_before.normalize()
                dot = v_after * v_before
                if dot_max < dot and 0.1 < dot:
                    dot_max = dot
                    grown_paths[i] = ef

            for ef in all_possible_grows[v]:
                if ef != grown_paths[i]:
                    stop_branches.append(ef)

        # next step
        efs = grown_paths

        for ef in grown_paths:
            skip_components += ef.vertices
        for ef in stop_branches:
            skip_components += ef.vertices

        if not something_happened:
            break

    # sort according to the main path
    efs_sorted = []
    for i_v in range(0, len(ef_main.vertices), output_nbr_a):

        v = ef_main.vertices[i_v]

        efs_from_v = []
        for ef in efs:
            if ef and ef not in efs_sorted and v in ef.vertices:
                efs_from_v.append(ef)
        for ef in stop_branches:
            if ef and ef not in efs_sorted and v in ef.vertices:
                efs_from_v.append(ef)

        # take the longest
        ef_biggest = None
        max_size = 0
        for ef in efs_from_v:
            if max_size < len(ef):
                max_size = len(ef)
                ef_biggest = ef
        efs_sorted.append(ef_biggest)

    out_matrices = []
    if dist_between_ctrls > 0:
        for ef in efs_sorted:
            matrices = ef.generate_matrices()
            matrices = resample_matrices_flow(
                matrices,
                override_nbr_output=dist_between_ctrls,
                is_loop=False,
                debug=False,
                keep_last_sample=True,
            )

            if matrices:
                out_matrices.append(matrices)

    if positions_smooth:
        out_matrices = smooth_matrices_grid(
            out_matrices,
            smooth_iter=positions_smooth,
            pin_ids=[(iM, 0) for iM in range(len(out_matrices))],
            position=True,
            rotation=False,
            scale=False,
        )

    if orients_smooth:
        out_matrices = smooth_matrices_grid(
            out_matrices,
            smooth_iter=orients_smooth,
            pin_ids=[],
            position=False,
            rotation=True,
            scale=False,
        )

    if scales_smooth:
        out_matrices = smooth_matrices_grid(
            out_matrices,
            smooth_iter=scales_smooth,
            pin_ids=[],
            position=False,
            rotation=False,
            scale=True,
        )

    ms = out_matrices
    # fix z axis length      
    for i in range(len(ms)):
        for j in range(len(ms[i])):
            vz = matrix_get_row(2, ms[i][j])
            vz.normalize()

            p = matrix_get_row(3, ms[i][j])

            dots = []

            if 0 < i and j < len(ms[i - 1]):
                pa = matrix_get_row(3, ms[i - 1][j])
                dots.append(abs(vz * (pa - p)))

            if i < len(ms) - 1 and j < len(ms[i + 1]):
                pb = matrix_get_row(3, ms[i + 1][j])
                dots.append(abs(vz * (pb - p)))

            if dots:
                dot_min = min(dots)

                ms[i][j] = matrix_set_row(2, ms[i][j], vz * dot_min * 0.5)

                # fix x axis length

    vertices_to_process = topo.vertices[:]
    for i in range(len(ms)):
        for j in range(len(ms[i])):
            dist_max = 0

            vertices_processed = []
            for v in vertices_to_process:
                if v.is_inside_cube(ms[i][j], axe_positive=1):
                    v = v.pos - matrix_get_row(3, ms[i][j])
                    vx = matrix_get_row(0, ms[i][j])
                    vx.normalize()
                    dist = abs(v * vx)

                    if dist_max < dist:
                        dist_max = dist

                    vertices_processed.append(v)

            for v in vertices_processed:
                vertices_to_process.remove(v)

            vx = matrix_get_row(0, ms[i][j])
            vx.normalize()
            vx *= dist_max
            ms[i][j] = matrix_set_row(0, ms[i][j], vx)

    out_matrices = ms

    # reduce scale of the last
    for i in range(len(ms)):
        for j in range(3):
            v = matrix_get_row(j, ms[i][-1])
            v.normalize()
            v *= 0.01
            ms[i][-1] = matrix_set_row(j, ms[i][-1], v)

    # dyn compatible
    out_matrices_extend = [[om.MMatrix(m) for m in matrices] for matrices in out_matrices]
    out_matrices_is_extend = [[False for _ in matrices] for matrices in out_matrices]
    for i, ms in enumerate(out_matrices):

        if i == 0:
            ms_neighbors = [out_matrices[1]]
            if ef_main.is_loop():
                ms_neighbors = [out_matrices[-1], out_matrices[1]]
        elif i == len(out_matrices) - 1:
            ms_neighbors = [out_matrices[-2]]
            if ef_main.is_loop():
                ms_neighbors = [out_matrices[-2], out_matrices[0]]
        else:
            ms_neighbors = [out_matrices[i - 1], out_matrices[i + 1]]

        ms_n_ref = None
        max_dist = 0
        for ms_n in ms_neighbors:
            if len(ms) < len(ms_n):
                dist = (matrix_get_row(3, ms_n[-1]) - matrix_get_row(3, ms[-1])).length()
                if max_dist < dist:
                    max_dist = dist
                    ms_n_ref = ms_n

        if ms_n_ref:

            # remove last
            out_matrices_extend[i].pop()

            # build new last - position
            i_before_last = len(ms) - 2
            i_last = len(ms) - 1

            p = matrix_get_row(3, ms[i_last])
            p_last = matrix_get_row(3, ms[i_before_last])

            v_delta_ref = matrix_get_row(3, ms_n_ref[i_last]) - matrix_get_row(3, ms_n_ref[i_before_last])
            v_delta = p - p_last
            v_delta.normalize()
            v_delta *= v_delta * v_delta_ref

            m = om.MMatrix(ms_n_ref[i_last])
            m = matrix_set_row(3, m, p_last + v_delta)

            # build new last - orient
            # vZ = matrix_getRow(3,ms_n_ref[i_last]) - matrix_getRow(3,ms[i_last])
            # vZ.normalize()
            # vZ *= matrix_getRow(2,m).length()
            # m = matrix_setRow(2,m,vZ)
            # m = matrix_orthogonize( m, 1, 2, True)

            # add new last
            out_matrices_extend[i].append(m)

            # get vZ_offset_from_neighbor
            m_last = m
            p_last = matrix_get_row(3, m_last)

            m_ref_last = ms_n_ref[i_last]
            p_ref_last = matrix_get_row(3, m_ref_last)

            v_to_project = p_last - p_ref_last

            vz_ref_last = matrix_get_row(2, m_ref_last)
            vz_ref_last.normalize()
            vz_ref_last *= vz_ref_last * v_to_project
            vz_offset_from_neighbor = vz_ref_last

            for j in range(len(ms), len(ms_n_ref)):
                m = om.MMatrix(ms_n_ref[j])
                p = matrix_get_row(3, ms_n_ref[j]) + vz_offset_from_neighbor
                m = matrix_set_row(3, m, p)

                # vZ = matrix_getRow(2,m)
                # vZ_new = om.MVector(vZ_delta)
                # vZ_new.normalize()
                # vZ_new *= abs*vZ_delta.length() - vZ.length()
                # m = matrix_setRow(2,m,vZ_new)

                out_matrices_extend[i].append(m)
                out_matrices_is_extend[i].append(True)

            # # modify aim of the last trsf
            # p_last = matrix_getRow(3,out_matrices_extend[i][len(ms)-1] )
            # p_next = matrix_getRow(3,out_matrices_extend[i][len(ms)  ] )
            # vY_new = p_next-p_last
            # out_matrices_extend[i][len(ms)-1] = matrix_setRow(1,out_matrices_extend[i][len(ms)-1], vY_new)
            # out_matrices_extend[i][len(ms)-1] = matrix_orthogonize( out_matrices_extend[i][len(ms)-1], 1, 2, True)

    ms = out_matrices_extend

    normal_max_dist = 0
    normal_av_dist = 0
    nbr = 0
    for i in range(len(ms)):
        for j in range(len(ms[i])):
            dist = matrix_get_row(0, ms[i][j]).length()
            normal_max_dist = max(normal_max_dist, dist)
            normal_av_dist += dist
            nbr += 1
    normal_av_dist /= nbr

    if debug_build_mesh:
        trsf_parent = mc.createNode('transform', n='debug_build_mesh')
        ms_debug = ms[:]
        if ef_main.is_loop():
            ms_debug.append(ms[0])

        for i in range(len(ms) - 1):
            for j in range(len(ms[i]) - 1):

                matrices = []
                matrices.append(ms[i][j])
                if len(ms[i + 1]) <= j:
                    continue
                matrices.append(ms[i + 1][j])
                if len(ms[i + 1]) <= j + 1:
                    continue
                matrices.append(ms[i + 1][j + 1])
                matrices.append(ms[i][j + 1])

                if out_matrices_is_extend[i + 1][j + 1] and out_matrices_is_extend[i][j + 1]:
                    continue

                m = matrices_average(matrices)
                points = [matrix_get_row(3, _m) for _m in matrices]
                v_ab = points[0] - points[1]
                v_cb = points[2] - points[1]

                v_ad = points[0] - points[3]
                v_cd = points[2] - points[3]

                _normal_max_dist = max([matrix_get_row(0, _m).length() for _m in matrices])

                n_b = v_ab ^ v_cb
                n_d = v_cd ^ v_ad
                n_b.normalize()
                n_d.normalize()
                n = n_b + n_d
                n.normalize()
                # n *= _normal_max_dist
                n *= normal_av_dist

                m = matrix_set_row(0, m, n)
                m = matrix_orthogonize(m, 0, 1)

                cube = mc.polyCube()[0]
                utils_set_matrix(cube, m)
                mc.parent(cube, trsf_parent)

                i_vts = [[6, 7], [0, 1], [2, 3], [4, 5]]
                for k in range(4):
                    pa = points[k] - n
                    mc.xform('{}.vtx[{}]'.format(cube, i_vts[k][0]), t=pa, ws=True)
                    pb = points[k] + n
                    mc.xform('{}.vtx[{}]'.format(cube, i_vts[k][1]), t=pb, ws=True)

    if use_mikan_rig:
        pass
        # # get unique tpl names
        # tpl_nbr = len(list(flatten_list(ms)))
        # tpl_names = GeminiUI_hack.get_unique_tpl_names(name, tpl_nbr)
        #
        # # parent
        # gUI = GeminiUI_hack()
        # parent_tpl = None
        # if parent:
        #     parent_tpl = gUI.get_template_root_name_from_node(parent)
        # else:
        #     template = gUI.tree_get_selected()
        #     parent_tpl = str(template.node)
        #
        # i = 0
        #
        # joints = []
        # for matrices in ms:
        #
        #     joints.append(
        #         gUI.create_bones(
        #             tpl_names[i],
        #             matrices,
        #             ctrl_shape,
        #             ctrl_color,
        #             parent_tpl,
        #         )
        #     )
        #     i += 1
        #
        #     if parent and parent != parent_tpl:
        #         obj_tpl_root = 'tpl_' + tpl_names[i]
        #         gUI.create_hook(obj_tpl_root, parent)
        #
        # skin = None
        # if do_skin:
        #     skin = _do_skin(
        #         joints,
        #         geo,
        #         joints_matrices=ms,
        #         vertex_ids_per_chains=[],
        #         debug=debug,
        #     )
        #
        # if skin and save_as_dfm:
        #     dfg = skin_to_dfg(
        #         skin,
        #         joints=joints,
        #         vertex_ids_per_chains=[],
        #         convert_tpl_jnt_to_rig_jnt=True,
        #     )
        #     mc.delete(skin)
    else:
        joints = []
        for matrices in out_matrices_extend:
            joints.append(_debug_build_chain(matrices))
        if do_skin:
            _do_skin(joints, geo, debug=debug)


def _debug_build_chain(matrices):
    mc.select(clear=True)
    last_jnt = None

    built_jnts = []
    for m in matrices:
        mc.select(clear=True)
        jnt = mc.joint()
        mc.setAttr('{}.radius'.format(jnt), 0.31)
        mc.setAttr('{}.overrideEnabled'.format(jnt), True)
        mc.setAttr('{}.overrideColor'.format(jnt), 13)
        mc.setAttr('{}.displayLocalAxis'.format(jnt), True)

        coords = [
            (1.0, 0.0, -1.0),
            (1.0, 0.0, 1.0),
            (-1.0, 0.0, 1.0),
            (-1.0, 0.0, -1.0),
            (1.0, 0.0, -1.0),
            (1.0, 1.0, -1.0),
            (1.0, 1.0, 1.0),
            (1.0, 0.0, 1.0),
            (1.0, 1.0, 1.0),
            (-1.0, 1.0, 1.0),
            (-1.0, 0.0, 1.0),
            (-1.0, 1.0, 1.0),
            (-1.0, 1.0, -1.0),
            (-1.0, 0.0, -1.0),
            (-1.0, 1.0, -1.0),
            (1.0, 1.0, -1.0)
        ]
        curve_trsf = mc.curve(d=1, p=coords)
        curve_shape = mc.listRelatives(curve_trsf, shapes=True, fullPath=True)[0]
        mc.parent(curve_shape, jnt, s=True, r=True)
        mc.delete(curve_trsf)
        utils_set_matrix(jnt, m)
        if last_jnt:
            jnt = mc.parent(jnt, last_jnt)[0]
        last_jnt = jnt
        built_jnts.append(jnt)
    return built_jnts


import math
from gemini.maya.utils.combineSkin import combine_skinned_meshes


def _build_skinned_mesh_from_joints(joints, matrices_override=None, debug=False):
    matrices = []

    if not isinstance(matrices_override, (list, tuple)):
        for jnt in joints:
            matrices.append(utils_get_matrix(jnt))
    else:
        matrices = matrices_override[:]

    # add cube
    cube_dummy_matrices = []
    for i in range(len(matrices)):
        m = matrices[i]
        v_x = matrix_get_row(0, m)
        v_y = matrix_get_row(1, m)
        v_z = matrix_get_row(2, m)
        p = matrix_get_row(3, matrices[i])

        m_cube = om.MMatrix(m)
        p_cube = p + v_y * 0.5
        m_cube = matrix_set_row(3, m_cube, p_cube)

        m_cube = matrix_set_row(0, m_cube, v_x * 2)
        m_cube = matrix_set_row(2, m_cube, v_z * 2)
        cube_dummy_matrices.append(m_cube)

    dummy_cubes = []
    for m in cube_dummy_matrices:
        cube_trsf = mc.polyCube(n='dummy')[0]
        utils_set_matrix(cube_trsf, m)
        dummy_cubes.append(cube_trsf)

    dummy_cubes_intermediate = []
    for i, m in enumerate(matrices[:-1]):
        cube_trsf = mc.polyCube(n='dummy')[0]
        utils_set_matrix(cube_trsf, m)
        dummy_cubes_intermediate.append(cube_trsf)

    cube_scr_indices = [0, 1, 7, 6]
    cube_dst_indices = [2, 3, 5, 4]
    for i in range(len(dummy_cubes) - 1):
        c = dummy_cubes[i]
        c_next = dummy_cubes[i + 1]
        for j in range(4):
            i_cs = cube_scr_indices[j]
            i_cd = cube_dst_indices[j]
            p = mc.xform('{}.vtx[{}]'.format(c_next, i_cs), q=True, ws=True, t=True)
            mc.xform('{}.vtx[{}]'.format(c, i_cd), ws=True, t=p)

    angle_max_possible = 10
    for i in range(0, len(dummy_cubes) - 1):
        p_ctrl = matrix_get_row(3, matrices[i])
        c = dummy_cubes[i]
        c_next = dummy_cubes[i + 1]

        if i < len(dummy_cubes_intermediate):
            c_inter = dummy_cubes_intermediate[i]

        for j in range(4):
            i_cs = cube_scr_indices[j]
            i_cd = cube_dst_indices[j]

            p_ref = mc.xform('{}.vtx[{}]'.format(c_next, i_cs), q=True, ws=True, t=True)
            p_ref = om.MVector(*p_ref)

            dist_to_offset = (p_ref - p_ctrl).length() * math.sin(math.radians(angle_max_possible))

            p_src = mc.xform('{}.vtx[{}]'.format(c, i_cs), q=True, ws=True, t=True)
            p_src = om.MVector(*p_src)

            p_dst = mc.xform('{}.vtx[{}]'.format(c_next, i_cd), q=True, ws=True, t=True)
            p_dst = om.MVector(*p_dst)

            v_src = p_src - p_ref
            v_dst = p_dst - p_ref

            v_src.normalize()
            v_dst.normalize()

            p_src_new = p_ref + v_src * dist_to_offset
            p_dst_new = p_ref + v_dst * dist_to_offset

            mc.xform('{}.vtx[{}]'.format(c, i_cd), ws=True, t=(p_src_new.x, p_src_new.y, p_src_new.z))
            mc.xform('{}.vtx[{}]'.format(c_next, i_cs), ws=True, t=(p_dst_new.x, p_dst_new.y, p_dst_new.z))
            if i < len(dummy_cubes_intermediate):
                mc.xform('{}.vtx[{}]'.format(c_inter, i_cs), ws=True, t=(p_src_new.x, p_src_new.y, p_src_new.z))
                mc.xform('{}.vtx[{}]'.format(c_inter, i_cd), ws=True, t=(p_dst_new.x, p_dst_new.y, p_dst_new.z))

    # skin cube
    for i in range(0, len(dummy_cubes)):
        _jnts = [joints[i]]
        selection = _jnts + [dummy_cubes[i]]
        mc.select(selection)
        mc.skinCluster(_jnts, dummy_cubes[i], toSelectedBones=True, maximumInfluences=2)
        mc.select(cl=True)

    for i in range(len(dummy_cubes_intermediate)):
        c_inter = dummy_cubes_intermediate[i]
        _jnts = [joints[i], joints[i + 1]]
        selection = _jnts + [c_inter]
        mc.select(selection)
        sk = mc.skinCluster(_jnts, c_inter, toSelectedBones=True, maximumInfluences=2)[0]
        mc.select(cl=True)
        for j in range(4):
            i_cs = cube_scr_indices[j]
            i_cd = cube_dst_indices[j]
            mc.skinPercent(sk, '{}.vtx[{}]'.format(c_inter, i_cs), transformValue=[(joints[i], 1.0), (joints[i + 1], 0.0)])
            mc.skinPercent(sk, '{}.vtx[{}]'.format(c_inter, i_cd), transformValue=[(joints[i], 0.0), (joints[i + 1], 1.0)])

            # combine cube
    to_combine = dummy_cubes + dummy_cubes_intermediate

    if len(to_combine) == 1:
        combined_mesh = to_combine[0]
    elif 1 < len(to_combine):
        combined_mesh = combine_skinned_meshes(to_combine)[0][0]
        if not debug:
            mc.delete(to_combine)
    else:
        raise RuntimeError('must be a least one dummy cube')

    return combined_mesh


def _do_skin_single_joint(joint, geo, vertex_names_isolate=None):
    mc.select([joint, geo])

    geo_shape = mc.listRelatives(geo, fullPath=True, s=True)[0]
    skin = (mc.listConnections(geo_shape, s=True, type='skinCluster') or [None])[0]
    if skin:
        topo = MeshTopology(geo)
        vg = topo.create_vertex_group(vertex_names_isolate)
        if 0 < len(vg):
            if joint not in mc.skinCluster(skin, q=True, influence=True):
                mc.skinCluster(skin, e=True, addInfluence=joint, weight=0)
            for V in vg:
                mc.skinPercent(skin, '{}.vtx[{}]'.format(geo, V.id), transformValue=[(joint, 1.0)])

    else:
        skin = mc.skinCluster(geo, [joint], toSelectedBones=True, maximumInfluences=2)[0]
    mc.select(cl=True)

    return skin


def _do_skin(
        joints=None,
        geo_name=None,
        joints_matrices=None,
        vertex_ids_per_chains=None,
        debug=False,
):
    if joints is None:
        joints = [[]]

    skinned_meshs = []
    weight_data = []
    for i, jnts in enumerate(joints):

        geo_dummy = mc.duplicate(geo_name)[0]
        if mc.listRelatives(geo_dummy, p=True):
            geo_dummy = mc.parent(geo_dummy, w=True)[0]

        jnts_ms = None
        if joints_matrices:
            jnts_ms = joints_matrices[i]

        skinned_mesh = _build_skinned_mesh_from_joints(jnts, matrices_override=jnts_ms, debug=debug)

        if vertex_ids_per_chains:
            # copy skin
            mc.select(jnts + [geo_dummy])
            _skin = mc.skinCluster(geo_dummy, jnts, toSelectedBones=True, maximumInfluences=2)[0]
            mc.select(cl=True)
            mc.copySkinWeights(skinned_mesh, geo_dummy, noMirror=True, surfaceAssociation="closestPoint", influenceAssociation=["oneToOne"])

            # get weight
            jnt_to_vertex_id_weights = {}
            for jnt in jnts:
                jnt_to_vertex_id_weights[jnt] = []
                for vId in vertex_ids_per_chains[i]:
                    w = mc.skinPercent(_skin, '{}.vtx[{}]'.format(geo_dummy, vId), transform=jnt, query=True)
                    jnt_to_vertex_id_weights[jnt].append(w)

            weight_data.append(jnt_to_vertex_id_weights)

        skinned_meshs.append(skinned_mesh)

        mc.delete(geo_dummy)

    if len(skinned_meshs) == 1:
        combined_mesh = skinned_meshs[0]
    else:
        combined_mesh = combine_skinned_meshes(skinned_meshs)[0][0]
        mc.delete(skinned_meshs)

    # copy to geo_name
    joints_to_skin_with = list(flatten_list(joints))  # [:-1]

    skin = _get_skinCluster(geo_name)
    if skin:
        for jnt in joints_to_skin_with:
            mc.skinCluster(skin, e=True, addInfluence=jnt, weight=0)
    else:
        mc.select(joints_to_skin_with + [geo_name])
        skin = mc.skinCluster(geo_name, joints_to_skin_with, toSelectedBones=True, maximumInfluences=2)[0]
        mc.select(cl=True)
        mc.copySkinWeights(combined_mesh, geo_name, noMirror=True, surfaceAssociation="closestPoint", influenceAssociation=["oneToOne"])

    if vertex_ids_per_chains:
        for i, jnts in enumerate(joints):
            for j, vId in enumerate(vertex_ids_per_chains[i]):
                transform_value = [(jnt, weight_data[i][jnt][j]) for jnt in jnts]
                mc.skinPercent(skin, '{}.vtx[{}]'.format(geo_name, vId), transformValue=transform_value)

    if not debug:
        mc.delete(combined_mesh)

    return skin


def _get_skinCluster(geo_name):
    geo_shape = mc.listRelatives(geo_name, s=True)[0]
    skin = (mc.listConnections(geo_shape + '.inMesh', s=True, d=False, type='skinCluster') or [None])[0]
    return skin
