# coding: utf-8

import maya.cmds as mc

from .topology import MeshTopology
from .curve_matrix import resample_matrices_flow


def maya_test_edge_loop_grow_selection():
    selection = mc.ls(sl=True, flatten=True)
    mesh_name = MeshTopology.extract_geo_from_components_names(selection)[0]
    mesh_data = MeshTopology(mesh_name)
    loops_flows = mesh_data.create_edge_loop_flows_from_edge_names(selection)

    loops_flows.build_debug_maya()


def build_edge_loop_matrices_from_edge_names_list(**kw):
    edge_name_list = kw.get('edge_name_list', [])
    kw.get('_____________________Edge_loop_analyze', '')
    topo_change_tolerance = kw.get('topo_change_tolerance', range(0, 11)[3])
    reverse_direction = kw.get('reverse_direction', False)  # create_locator_on_selection
    base_target = kw.get('base_target', '')

    kw.get('_____________________Edge_loop_to_matrices', '')
    up_targets = kw.get('up_targets', '')
    up_target_component = kw.get('up_target_component', ['x', 'y', 'z', 'p'][0])
    orient_follow_topo = kw.get('orient_follow_topo', False)

    kw.get('_____________________remap_matrices', '')
    match_topo_loop_position = kw.get('match_topo_loop_position', False)
    override_nbr_output = kw.get('override_nbr_output', range(-1, 200)[0])
    match_landmark_mode = kw.get('match_landmark_mode', False)

    kw.get('_____________________debug', '')
    debug = kw.get('debug', False)
    # -- end auto ui

    geometries = MeshTopology.extract_geo_from_components_names(edge_name_list)
    out_matrices = []
    for geo in geometries:
        topo = MeshTopology(geo)
        elfs = topo.create_edge_loop_flows_from_edge_names(
            edge_name_list,
            topo_change_tolerance,
            reverse_direction,
            base_target
        )

        out_matrices_a = []
        for elf in elfs:
            elf_matrices = elf.generate_matrices(
                up_targets=up_targets,
                up_target_component=up_target_component,
                orient_follow_topo=orient_follow_topo
            )

            elf_matrices = resample_matrices_flow(
                elf_matrices,
                match_topo_loop_position=match_topo_loop_position,
                override_nbr_output=override_nbr_output,
                is_loop=elf.is_loop(),
                has_landmarks=1 < len(elf.user_input_ids),
                match_landmark_mode=match_landmark_mode,
                debug=False)

            out_matrices_a.append(elf_matrices)

        out_matrices.append(out_matrices_a)

    return out_matrices


def build_edge_flow_grid_matrices():
    pass
