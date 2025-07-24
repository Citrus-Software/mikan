# coding: utf-8

import math

import maya.api.OpenMaya as om
import maya.cmds as mc

from mikan.maya.lib.nurbs import create_path

from .matrix import (
    utils_set_matrix, matrix_get_row, matrix_orthogonize, matrix_set_row, utils_get_matrix
)


def create_curve_from_matrices(matrices, degree=3, periodic=False, curve_mode_bezier=False, y_offset=0):
    axes = ['x', 'y', 'z']
    i_axe_dir = 1
    i_axe_up = 0
    # i_axe_side = 2

    trsf_parent = mc.createNode('transform', n='tmp')

    trsfs_created = []
    locs_created = []
    for i, m in enumerate(matrices):
        loc = mc.spaceLocator()[0]
        mc.parent(loc, trsf_parent)
        trsf_center = mc.createNode('transform', n='curve_driver_center_{}'.format(i), p=loc)
        if curve_mode_bezier:
            trsf_pos = mc.createNode('transform', n='curve_driver_axePos_{}'.format(i), p=trsf_center)
            trsf_neg = mc.createNode('transform', n='curve_driver_axeNeg_{}'.format(i), p=trsf_center)
            mc.setAttr('{}.t{}'.format(trsf_pos, axes[i_axe_dir]), 1)
            mc.setAttr('{}.t{}'.format(trsf_neg, axes[i_axe_dir]), -1)
            trsfs_created += [trsf_neg, trsf_center, trsf_pos]
        else:
            trsfs_created += [trsf_center]

        if 0 < y_offset:
            mc.setAttr('{}.t{}'.format(trsf_center, axes[i_axe_up]), y_offset)
            mc.setAttr('{}.t{}'.format(trsf_pos, axes[i_axe_up]), y_offset)
            mc.setAttr('{}.t{}'.format(trsf_neg, axes[i_axe_up]), y_offset)
        utils_set_matrix(loc, m)

        locs_created.append(loc)

    curve = str(create_path(*trsfs_created, d=degree, periodic=periodic))

    return [curve] + locs_created + [trsf_parent]


def build_points_from_curve(curve, nbr):
    axes = ['x', 'y', 'z']
    i_axe_dir = 1
    # i_axe_up = 0
    # i_axe_side = 2

    chain_lengths = []
    curve = str(curve)
    curve_shape = mc.listRelatives(curve, c=True, s=True)[0]

    curve_info = mc.createNode('curveInfo')
    mc.connectAttr(curve_shape + '.worldSpace', curve_info + '.inputCurve')
    curve_length = mc.getAttr(curve_info + '.arcLength')
    mc.delete(curve_info)
    curve_length *= 0.99

    length_per_section = curve_length / nbr

    for i in range(nbr):
        chain_lengths.append(length_per_section)

    tx = 0
    mc.select(cl=True)
    jnts = [mc.joint()]
    jnt_last = jnts[0]
    for i in range(len(chain_lengths)):
        mc.select(cl=True)
        jnt = mc.joint()
        tx += chain_lengths[i]
        mc.setAttr('{}.t{}'.format(jnt, axes[i_axe_dir]), tx)
        if jnt_last:
            mc.parent(jnt, jnt_last)
        jnt_last = jnt

        jnts.append(jnt)

    handle = mc.ikHandle(
        curve=curve,
        startJoint=jnts[0],
        endEffector=jnts[-1],
        solver='ikSplineSolver',
        createCurve=False,
        parentCurve=False,
        rootOnCurve=True
    )

    out_point = []
    for i in range(len(chain_lengths) + 1):
        m = utils_get_matrix(jnts[i])
        p = matrix_get_row(3, m)
        out_point.append(p)

    mc.delete(handle)
    mc.delete(jnts)

    return out_point


def build_matrices_from_curve(curve, nbr, matrices_refs=None):
    axes = ['x', 'y', 'z']
    i_axe_dir = 1
    # i_axe_up = 0
    # i_axe_side = 2

    chain_lengths = []
    if matrices_refs:

        # get chain points
        chain_points = get_intersect_points_between_maya_curve_and_planes(
            curve,
            [matrix_get_row(i_axe_dir, m) for m in matrices_refs],
            [matrix_get_row(3, m) for m in matrices_refs],
            if_miss_return_closest=True,
        )

        # get chain lengths
        for i in range(0, len(chain_points) - 1):
            dist = (chain_points[i + 1] - chain_points[i]).length()
            dist = max(dist, 0.01)
            chain_lengths.append(dist)

    else:
        curve = str(curve)
        curve_shape = mc.listRelatives(curve, c=True, s=True)[0]

        curve_info = mc.createNode('curveInfo')
        mc.connectAttr(curve_shape + '.worldSpace', curve_info + '.inputCurve')
        curve_length = mc.getAttr(curve_info + '.arcLength')
        mc.delete(curve_info)
        curve_length *= 0.99

        length_per_section = curve_length / nbr

        for i in range(nbr):
            chain_lengths.append(length_per_section)

    tx = 0
    mc.select(cl=True)
    jnts = [mc.joint()]
    jnt_last = jnts[0]
    for i in range(len(chain_lengths)):
        mc.select(cl=True)
        jnt = mc.joint()
        tx += chain_lengths[i]
        mc.setAttr('{}.t{}'.format(jnt, axes[i_axe_dir]), tx)
        if jnt_last:
            mc.parent(jnt, jnt_last)
        jnt_last = jnt

        jnts.append(jnt)

    # if matrices_refs and do_error:
    #    mc.error([curve]+jnts)
    handle = mc.ikHandle(
        curve=curve,
        startJoint=jnts[0],
        endEffector=jnts[-1],
        solver='ikSplineSolver',
        createCurve=False,
        parentCurve=False,
        rootOnCurve=True,
    )

    out_matrices = []
    for i in range(len(chain_lengths) + 1):
        out_matrices.append(utils_get_matrix(jnts[i]))

    mc.delete(handle)
    mc.delete(jnts)

    return out_matrices


def get_intersect_points_between_maya_curve_and_planes(
        maya_curve,
        plane_vectors,
        plane_points,
        if_miss_return_closest=True,
        sample_curve_nbr=50,
):
    curve_points = build_points_from_curve(maya_curve, sample_curve_nbr)

    intersect_points = []

    for plane_point, plane_vector in zip(plane_points, plane_vectors):

        intersect_point = None
        dot_last = None
        for p in curve_points:
            dot = (p - plane_point) * plane_vector
            if dot_last and dot_last * dot < 0:
                intersect_point = p
                break

            dot_last = dot

        if not intersect_point and if_miss_return_closest:
            p_first = curve_points[0]
            p_last = curve_points[-1]
            if (p_last - plane_point).length() < (p_first - plane_point).length():
                intersect_point = p_last
            else:
                intersect_point = p_first

        if intersect_point and intersect_point not in intersect_points:
            intersect_points.append(intersect_point)

    return intersect_points


def get_matrices_from_curves(
        curve,
        curve_up,
        curve_side,
        nbr,
        dist_incr=None,
        keep_last_sample=True,
        matrices_refs=None,
):
    # axes = ['x', 'y', 'z']
    i_axe_dir = 1
    i_axe_up = 0
    i_axe_side = 2

    if dist_incr:
        curve = str(curve)
        curve_shape = mc.listRelatives(curve, c=True, s=True)[0]

        curve_info = mc.createNode('curveInfo')
        mc.connectAttr(curve_shape + '.worldSpace', curve_info + '.inputCurve')
        curve_length = mc.getAttr(curve_info + '.arcLength')
        mc.delete(curve_info)
        curve_length *= 0.99

        nbr = math.floor(curve_length / dist_incr)

    if nbr == 0:
        nbr = 1

    matrices_ref = build_matrices_from_curve(curve, nbr, matrices_refs=matrices_refs)
    matrices_up = build_matrices_from_curve(curve_up, nbr, matrices_refs=matrices_refs)
    matrices_side = build_matrices_from_curve(curve_side, nbr, matrices_refs=matrices_refs)

    matrices = []
    v_dir = None
    v_up = None
    v_side = None

    out_nbr = len(matrices_ref) - 1
    if keep_last_sample:
        out_nbr = len(matrices_ref)

    for i in range(out_nbr):
        m = matrices_ref[i]
        p = matrix_get_row(3, m)
        p_up = matrix_get_row(3, matrices_up[i])
        p_side = matrix_get_row(3, matrices_side[i])

        if i < len(matrices_ref) - 1:
            p_dir = matrix_get_row(3, matrices_ref[i + 1])
            v_dir = p_dir - p

            v_up = p_up - p
            v_side = p_side - p

            # Adjust vSide
            vy_normalized = om.MVector(v_dir)
            vx_normalized = om.MVector(v_up)
            vz_normalized = om.MVector(v_side)
            vy_normalized.normalize()
            vx_normalized.normalize()
            vz_normalized.normalize()

            vz_ortho = vx_normalized ^ vy_normalized
            vz_ortho.normalize()
            dot = vz_ortho * vz_normalized
            if dot < 0:
                v_side *= -1

        m = matrix_set_row(i_axe_dir, m, v_dir)
        m = matrix_set_row(i_axe_up, m, v_up)
        m = matrix_set_row(i_axe_side, m, v_side)
        m = matrix_orthogonize(m, i_axe_dir, i_axe_up, project_old_length_on_new_axe=True)
        matrices.append(m)

    return matrices


def resample_matrices_flow(
        matrices,
        override_nbr_output=None,
        debug=False,
        is_loop=False,
        keep_last_sample=False,
        matrices_refs=None,
):
    # utils
    # axes = ['x', 'y', 'z']
    # i_axe_dir = 1
    i_axe_up = 0
    i_axe_side = 2

    # out_matrices = matrices

    p_ups = [matrix_get_row(i_axe_up, m) + matrix_get_row(3, m) for m in matrices]
    p_sides = [matrix_get_row(i_axe_side, m) + matrix_get_row(3, m) for m in matrices]

    m_ups = list(map(lambda m, p: matrix_set_row(3, m, p), matrices, p_ups))
    m_sides = list(map(lambda m, p: matrix_set_row(3, m, p), matrices, p_sides))

    curve = create_curve_from_matrices(matrices, periodic=is_loop)
    curve_up = create_curve_from_matrices(m_ups, periodic=is_loop)
    curve_side = create_curve_from_matrices(m_sides, periodic=is_loop)

    nbr_ctrl = len(matrices) - 1
    dist_incr = None
    if override_nbr_output:
        if isinstance(override_nbr_output, float):
            dist_incr = override_nbr_output
            nbr_ctrl = None
        else:
            nbr_ctrl = override_nbr_output

    out_matrices = get_matrices_from_curves(
        curve[0],
        curve_up[0],
        curve_side[0],
        nbr_ctrl,
        dist_incr,
        keep_last_sample=keep_last_sample,
        matrices_refs=matrices_refs,
    )
    if not debug:
        for to_delete in [curve, curve_up, curve_side]:
            mc.delete(to_delete)

    return out_matrices


def _get_merge_matrices_longest_path(
        matrices_flows,
        override_nbr_output,
        keep_last_sample,
        reverse_dir=False,
        iF_start=0,
):
    i_axe_dir = 1
    # get start matrix
    iF = iF_start
    iM = 0
    if reverse_dir:
        iF = len(matrices_flows) - 1
        iM = len(matrices_flows[iF]) - 1

    ids_explored = [iF]
    max_iter = 500
    for _ in range(max_iter):
        m = matrices_flows[iF][iM]
        p = matrix_get_row(3, m)

        min_dist = 999999.0
        ids_closest = None
        for _iF in range(len(matrices_flows)):

            is_already_explored = _iF in ids_explored

            if is_already_explored:
                continue

            for _iM in range(len(matrices_flows[_iF])):

                # check if its behind                    
                m_to_test = matrices_flows[_iF][_iM]
                p_to_test = matrix_get_row(3, m_to_test)
                v = p_to_test - p
                v.normalize()
                v_dir = matrix_get_row(i_axe_dir, m)
                v_dir.normalize()

                test_matrix_is_in_front = 0 < v * v_dir
                if reverse_dir:
                    if test_matrix_is_in_front:
                        continue
                else:
                    if not test_matrix_is_in_front:
                        continue

                        # test if its has same dir
                v_dir_test = matrix_get_row(i_axe_dir, m_to_test)
                v_dir_test.normalize()

                v_dir_lasts = matrix_get_row(i_axe_dir, m)
                v_dir_lasts.normalize()

                has_same_dir = 0 < v_dir_lasts * v_dir_test
                if not has_same_dir:
                    continue

                # get closest dist      
                dist = (p - p_to_test).length()
                if dist < min_dist:
                    min_dist = dist
                    ids_closest = (_iF, _iM)

        if not ids_closest:
            break

        iF = ids_closest[0]
        iM = 0
        if reverse_dir:
            iM = len(matrices_flows[iF]) - 1
        ids_explored.append(iF)

    # get matrices path

    matrices_path_ids = [(iF, iM)]

    for _ in range(max_iter):
        iF = matrices_path_ids[-1][0]
        iM = matrices_path_ids[-1][1]

        # fill until the end of the branch
        if reverse_dir:
            for i in reversed(range(0, iM)):
                matrices_path_ids.append((iF, i))
        else:
            for i in range(iM + 1, len(matrices_flows[iF])):
                matrices_path_ids.append((iF, i))

        # get closest
        iF = matrices_path_ids[-1][0]
        iM = matrices_path_ids[-1][1]
        m = matrices_flows[iF][iM]
        p = matrix_get_row(3, m)

        min_dist = 999999.0
        ids_closest = None
        for _iF in range(len(matrices_flows)):

            is_already_explored = _iF in list(set([elem[0] for elem in matrices_path_ids]))

            if is_already_explored:
                continue

            for _iM in range(len(matrices_flows[_iF])):

                # test if its in front
                m_to_test = matrices_flows[_iF][_iM]
                p_to_test = matrix_get_row(3, m_to_test)
                v = p_to_test - p
                v.normalize()
                v_dir = matrix_get_row(i_axe_dir, m)
                v_dir.normalize()

                test_matrix_is_in_front = 0 < v * v_dir

                if reverse_dir:
                    if test_matrix_is_in_front:
                        continue
                else:
                    if not test_matrix_is_in_front:
                        continue

                # test if its has same dir   
                v_dir_test = matrix_get_row(i_axe_dir, m_to_test)
                v_dir_test.normalize()

                v_dir_lasts = om.MVector()
                lasts_to_check = 3
                lasts_to_check = min(lasts_to_check, len(matrices_path_ids))
                for j in range(lasts_to_check):
                    lasts_iF = matrices_path_ids[j * -1][0]
                    lasts_iM = matrices_path_ids[j * -1][1]
                    _vDir = matrix_get_row(i_axe_dir, matrices_flows[lasts_iF][lasts_iM])
                    _vDir.normalize()
                    v_dir_lasts += _vDir
                v_dir_lasts.normalize()

                has_same_dir = 0 < v_dir_lasts * v_dir_test
                if not has_same_dir:
                    continue

                    # get closest dist
                dist = (p - p_to_test).length()
                if dist < min_dist:
                    min_dist = dist
                    ids_closest = (_iF, _iM)

        if not ids_closest:
            break

        matrices_path_ids.append(ids_closest)

    matrices_path = []
    for iF, iM in matrices_path_ids:
        matrices_path.append(matrices_flows[iF][iM])

    if reverse_dir:
        matrices_path.reverse()

    matrices_path = smooth_matrices_flow(matrices_path)

    # smooth
    matrices_path = smooth_matrices_flow(
        matrices_path,
        4,
        pin_ids=[0, len(matrices_path) - 1],
        position=True,
        rotation=False,
        scale=False,
    )

    matrices_path = smooth_matrices_flow(
        matrices_path,
        4,
        pin_ids=[],
        position=False,
        rotation=True,
        scale=False,
    )

    matrices_path_resampled = resample_matrices_flow(
        matrices_path,
        override_nbr_output=override_nbr_output,
        debug=False,
        is_loop=False,
        keep_last_sample=keep_last_sample,
    )
    return matrices_path_resampled


def resample_matrices_flows(
        matrices_flows,
        override_nbr_output=None,
        debug=False,
        is_loops=None,
        keep_last_sample=False,
        align_ctrls=False,
        merge_into_one_chain=False,
):
    # utils
    axes = ['x', 'y', 'z']
    i_axe_dir = 1
    i_axe_up = 0
    i_axe_side = 2

    matrices_path_resampled = []
    if align_ctrls or merge_into_one_chain:

        max_nbr_path = None
        max_nbr = 0
        for i in range(len(matrices_flows)):
            path = _get_merge_matrices_longest_path(
                matrices_flows,
                override_nbr_output,
                keep_last_sample,
                reverse_dir=False,
                iF_start=i,
            )
            nbr = len(path)
            if max_nbr < nbr:
                max_nbr = nbr
                max_nbr_path = path

        max_nbr_reverse_path = None
        max_nbr = 0
        for i in range(len(matrices_flows)):
            path = _get_merge_matrices_longest_path(
                matrices_flows,
                override_nbr_output,
                keep_last_sample,
                reverse_dir=True,
                iF_start=i,
            )
            nbr = len(path)
            if max_nbr < nbr:
                max_nbr = nbr
                max_nbr_reverse_path = path

        matrices_path_resampled = merge_matrices_flow_closest_best_match(max_nbr_path, max_nbr_reverse_path)

    matrices_flows_resampled = []
    if merge_into_one_chain:
        matrices_flows_resampled = [matrices_path_resampled]
    else:
        for i, matrices in enumerate(matrices_flows):
            matrices_resampled = resample_matrices_flow(
                matrices,
                override_nbr_output=override_nbr_output,
                debug=debug,
                is_loop=is_loops[i],
                keep_last_sample=keep_last_sample,
                matrices_refs=matrices_path_resampled,
            )
            matrices_flows_resampled.append(matrices_resampled)

    return matrices_flows_resampled  # [matrices_path_resampled for i, matrices in enumerate(matrices_flows)]


def smooth_matrices_flow(
        matrices,
        smooth_iter=1,
        position=True,
        rotation=True,
        scale=True,
        pin_ids=None,
):
    for _ in range(smooth_iter):
        for i in range(0, len(matrices)):

            if isinstance(pin_ids, (tuple, list)) and i in pin_ids:
                continue

            m = matrices[i]
            matrices_to_average = [m]
            if 0 <= i - 1:
                matrices_to_average.append(matrices[i - 1])
            if i < len(matrices) - 1:
                matrices_to_average.append(matrices[i + 1])
            m_av = matrices_average(matrices_to_average)

            if not position:
                m_av = matrix_set_row(3, m_av, matrix_get_row(3, m))

            if not rotation:
                for iAxe in [0, 1, 2]:
                    v_axe = matrix_get_row(iAxe, m)
                    v_av_axe = matrix_get_row(iAxe, m_av)
                    v_axe.normalize()
                    v_axe *= v_av_axe.length()

                    m_av = matrix_set_row(iAxe, m_av, v_axe)

            if not scale:
                for iAxe in [0, 1, 2]:
                    v_axe = matrix_get_row(iAxe, m)
                    v_av_axe = matrix_get_row(iAxe, m_av)
                    v_av_axe.normalize()
                    v_av_axe *= v_axe.length()

                    m_av = matrix_set_row(iAxe, m_av, v_av_axe)

            m_av = matrix_orthogonize(m_av, 1, 0)
            matrices[i] = m_av

    return matrices


def smooth_matrices_grid(
        matrices,
        smooth_iter=1,
        position=True,
        rotation=True,
        scale=True,
        pin_ids=[]
):
    for _ in range(smooth_iter):
        for i in range(0, len(matrices)):
            for j in range(0, len(matrices[i])):

                if isinstance(pin_ids, (list, tuple)) and (i, j) in pin_ids:
                    continue

                m = matrices[i][j]
                matrices_to_average = [m]
                if 0 <= i - 1:
                    if j < len(matrices[i - 1]):
                        matrices_to_average.append(matrices[i - 1][j])
                if i < len(matrices) - 1:
                    if j < len(matrices[i + 1]):
                        matrices_to_average.append(matrices[i + 1][j])
                if 0 <= j - 1:
                    matrices_to_average.append(matrices[i][j - 1])
                if j < len(matrices[i]) - 1:
                    matrices_to_average.append(matrices[i][j + 1])

                m_av = matrices_average(matrices_to_average)

                if not position:
                    m_av = matrix_set_row(3, m_av, matrix_get_row(3, m))

                if not rotation:
                    for iAxe in [0, 1, 2]:
                        v_axe = matrix_get_row(iAxe, m)
                        v_av_axe = matrix_get_row(iAxe, m_av)
                        v_axe.normalize()
                        v_axe *= v_av_axe.length()

                        m_av = matrix_set_row(iAxe, m_av, v_axe)

                if not scale:
                    for iAxe in [0, 1, 2]:
                        v_axe = matrix_get_row(iAxe, m)
                        v_av_axe = matrix_get_row(iAxe, m_av)
                        v_av_axe.normalize()
                        v_av_axe *= v_axe.length()

                        m_av = matrix_set_row(iAxe, m_av, v_av_axe)

                m_av = matrix_orthogonize(m_av, 1, 0)
                matrices[i][j] = m_av

    return matrices


def merge_matrices_flow(matrices_list, merge_output_by_nbr):
    out_matrices_merged = [[] for i in range(len(matrices_list) // merge_output_by_nbr)]
    for k in range(len(matrices_list[0])):

        for i in range(0, len(matrices_list), merge_output_by_nbr):

            is_beyond_first_size = False
            for j in range(merge_output_by_nbr):
                if len(matrices_list[i + j]) <= k:
                    is_beyond_first_size = True

            if is_beyond_first_size:
                continue

            matrices_to_average = []
            for j in range(merge_output_by_nbr):
                matrices_to_average.append(matrices_list[i + j][k])

            m_av = matrices_average(matrices_to_average)
            out_matrices_merged[i].append(m_av)

    return out_matrices_merged


def merge_matrices_flow_closest_best_match(matrices_list_a, matrices_list_b):
    # get closest
    closest_couples = []
    for _ in range(500):

        something_happened = False
        min_dist = 9999.0
        for jA in range(len(matrices_list_a)):
            for jB in range(len(matrices_list_b)):
                if (jA, jB) in closest_couples:
                    continue
                pA = matrix_get_row(3, matrices_list_a[jA])
                pB = matrix_get_row(3, matrices_list_b[jB])
                dist = (pA - pB).length()
                if dist < min_dist:
                    min_dist = dist
                    closest_couples += [(jA, jB)]
                    something_happened = True

        if not something_happened:
            break

    # sort and fill missing element
    closest_couple_sorted = []

    must_add_list_b_missing_element = len(closest_couples) == len(matrices_list_a)

    if must_add_list_b_missing_element:

        for j in range(len(matrices_list_b)):

            found_couple = None
            for couple in closest_couples:
                if j == couple[1]:
                    found_couple = couple
                    break

            if found_couple:
                closest_couple_sorted.append(found_couple)
            else:
                closest_couple_sorted.append((None, j))

    else:
        for j in range(len(matrices_list_a)):

            found_couple = None
            for couple in closest_couples:
                if j == couple[0]:
                    found_couple = couple
                    break

            if found_couple:
                closest_couple_sorted.append(found_couple)
            else:
                closest_couple_sorted.append((j, None))
                # get matrices
    out_matrices = []

    for couple in closest_couple_sorted:
        jA = couple[0]
        jB = couple[1]
        if not jA:
            out_matrices.append(matrices_list_b[jB])
        elif not jB:
            out_matrices.append(matrices_list_a[jA])
        else:
            out_matrices.append(matrices_average([matrices_list_a[jA], matrices_list_b[jB]]))

    return out_matrices


def matrices_average(matrices):
    x_av = om.MVector()
    y_av = om.MVector()
    z_av = om.MVector()
    p_av = om.MVector()
    for i in range(len(matrices)):
        x_av += matrix_get_row(0, matrices[i])
        y_av += matrix_get_row(1, matrices[i])
        z_av += matrix_get_row(2, matrices[i])
        p_av += matrix_get_row(3, matrices[i])
    x_av /= len(matrices)
    y_av /= len(matrices)
    z_av /= len(matrices)
    p_av /= len(matrices)

    m_av = om.MMatrix()
    m_av = matrix_set_row(0, m_av, x_av)
    m_av = matrix_set_row(1, m_av, y_av)
    m_av = matrix_set_row(2, m_av, z_av)
    m_av = matrix_set_row(3, m_av, p_av)
    return m_av
