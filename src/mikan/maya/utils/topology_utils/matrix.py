# coding: utf-8

"""
DEPRECATED — Matrix Utilities (maya.cmds-based)

This module provides utility functions for working with transformation matrices in Maya
using `maya.cmds`. It is retained for backward compatibility but is **no longer actively maintained**.

⚠️ This module is deprecated and will be removed in a future release.
Please use the `cmdx`-based matrix module instead, which offers better performance,
type safety, and a more modern API.
"""

import maya.api.OpenMaya as om
import maya.cmds as mc


def utils_get_matrix(obj):
    if '.vtx' in obj:
        pos = mc.xform(obj, q=True, t=True, ws=True)
        m = om.MMatrix(
            [1, 0, 0, 0,
             0, 1, 0, 0,
             0, 0, 1, 0,
             pos[0], pos[1], pos[2], 1])
    else:
        matrix_num = mc.xform(obj, q=True, m=True, ws=True)
        m = om.MMatrix(
            [matrix_num[0], matrix_num[1], matrix_num[2], matrix_num[3],
             matrix_num[4], matrix_num[5], matrix_num[6], matrix_num[7],
             matrix_num[8], matrix_num[9], matrix_num[10], matrix_num[11],
             matrix_num[12], matrix_num[13], matrix_num[14], matrix_num[15]])

    return m


def utils_set_matrix(obj, matrix_num):
    mc.xform(obj, m=(matrix_num[0], matrix_num[1], matrix_num[2], matrix_num[3],
                     matrix_num[4], matrix_num[5], matrix_num[6], matrix_num[7],
                     matrix_num[8], matrix_num[9], matrix_num[10], matrix_num[11],
                     matrix_num[12], matrix_num[13], matrix_num[14], matrix_num[15]), ws=True)


def matrix_orthogonize(matrix, ref_axis, middle_axis, project_old_length_on_new_axe=False):
    normal_axis = 0
    if ref_axis == 0 and middle_axis == 2: normal_axis = 1
    if ref_axis == 2 and middle_axis == 0: normal_axis = 1
    if ref_axis == 0 and middle_axis == 1: normal_axis = 2
    if ref_axis == 1 and middle_axis == 0: normal_axis = 2

    v_ref = matrix_get_row(ref_axis, matrix)
    v_middle = matrix_get_row(middle_axis, matrix)
    v_normal = matrix_get_row(normal_axis, matrix)

    d_middle = v_middle.length()
    d_normal = v_normal.length()
    v_normal_modif = v_ref ^ v_middle
    v_normal_modif.normalize()
    v_normal_modif = v_normal_modif * d_normal

    if ref_axis == 0 and middle_axis == 2: v_normal_modif *= -1
    if ref_axis == 1 and middle_axis == 0: v_normal_modif *= -1
    if ref_axis == 2 and middle_axis == 1: v_normal_modif *= -1
    v_middle_modif = v_normal_modif ^ v_ref
    v_middle_modif.normalize()
    v_middle_modif *= d_middle

    if v_middle_modif * v_middle < 0:
        v_middle_modif *= -1

    if project_old_length_on_new_axe:
        v_middle_modif.normalize()
        v_middle_modif *= v_middle * v_middle_modif
        v_normal_modif.normalize()
        v_normal_modif *= v_normal * v_normal_modif

    matrix_new = matrix
    matrix_new = matrix_set_row(ref_axis, matrix_new, v_ref)
    matrix_new = matrix_set_row(middle_axis, matrix_new, v_middle_modif)
    matrix_new = matrix_set_row(normal_axis, matrix_new, v_normal_modif)

    return matrix_new


def matrix_get_row(row, m):
    return om.MVector(m.getElement(row, 0), m.getElement(row, 1), m.getElement(row, 2))


def matrix_set_row(row, m, v):
    m_out = om.MMatrix(m)
    m_out.setElement(row, 0, v.x)
    m_out.setElement(row, 1, v.y)
    m_out.setElement(row, 2, v.z)
    return m_out


def matrix_normalize_axe(row, m):
    v = matrix_get_row(row, m)
    v.normalize()
    return matrix_set_row(row, m, v)


def matrix_normalize(m):
    m_normalized = om.MMatrix(m)
    m_normalized = matrix_normalize_axe(0, m_normalized)
    m_normalized = matrix_normalize_axe(1, m_normalized)
    m_normalized = matrix_normalize_axe(2, m_normalized)
    return m_normalized


def matrix_set_axe_scale(row, m, scale):
    v = matrix_get_row(row, m)
    v.normalize()
    v *= scale
    return matrix_set_row(row, m, v)


def matrix_build(
        p=None,
        vX=None,
        vY=None,
        vZ=None,
        m_base=None,
        normalize=False,
        orthogonize=False,
        ref_axe=None,
        middle_axe=None,
        last_axe=None,
        adjuste_side_to_right_hand_matrix=True,
):
    m = om.MMatrix()
    m.setToIdentity()
    if m_base:
        m = m_base

    if p: m = matrix_set_row(3, m, p)
    if vX: m = matrix_set_row(0, m, vX)
    if vY: m = matrix_set_row(1, m, vY)
    if vZ: m = matrix_set_row(2, m, vZ)

    # deduce last axe
    axes = ['x', 'y', 'z']
    if last_axe == None:
        possible_axes = axes[:]

        if ref_axe and ref_axe in possible_axes:
            possible_axes.remove(ref_axe)
        if middle_axe and middle_axe in possible_axes:
            possible_axes.remove(middle_axe)

        if vX and 'x' in possible_axes and 1 < len(possible_axes):
            possible_axes.remove('x')
        if vY and 'y' in possible_axes and 1 < len(possible_axes):
            possible_axes.remove('y')
        if vZ and 'z' in possible_axes and 1 < len(possible_axes):
            possible_axes.remove('z')

        if len(possible_axes) == 1:
            last_axe = possible_axes[0]

    if middle_axe is None:
        possible_axes = axes[:]

        if ref_axe and ref_axe in possible_axes:
            possible_axes.remove(ref_axe)
        if last_axe and last_axe in possible_axes:
            possible_axes.remove(last_axe)

        if len(possible_axes) == 1:
            middle_axe = possible_axes[0]

    # Adjust vSideaxes

    if adjuste_side_to_right_hand_matrix:

        i_last_axe = axes.index(last_axe)
        vSide = matrix_get_row(i_last_axe, m)

        vSide_normalized = om.MVector(vSide)
        vSide_normalized.normalize()

        vSide_orhto = None
        if last_axe == 'x':
            vY_normalized = om.MVector(vY)
            vZ_normalized = om.MVector(vZ)
            vY_normalized.normalize()
            vZ_normalized.normalize()
            vSide_orhto = vY_normalized ^ vZ_normalized
        elif last_axe == 'y':
            vZ_normalized = om.MVector(vZ)
            vX_normalized = om.MVector(vX)
            vZ_normalized.normalize()
            vX_normalized.normalize()
            vSide_orhto = vZ_normalized ^ vX_normalized
        elif last_axe == 'z':
            vY_normalized = om.MVector(vY)
            vX_normalized = om.MVector(vX)
            vY_normalized.normalize()
            vX_normalized.normalize()
            vSide_orhto = vX_normalized ^ vY_normalized

        vSide_orhto.normalize()

        dot = vSide_orhto * vSide_normalized
        if dot < 0:
            vSide *= -1

        matrix_set_row(i_last_axe, m, vSide)

    if orthogonize:
        m = matrix_orthogonize(m, axes.index(ref_axe), axes.index(middle_axe), project_old_length_on_new_axe=normalize == False)

    if normalize:
        m = matrix_normalize(m)
    return m


def matrix_get_closest_axe_from_vector(m, vAxe, skip_axe=None):
    dot_max = 0.0
    i_axe_closest = -1
    for i in range(3):
        if skip_axe != None and i == skip_axe:
            continue
        v = matrix_get_row(i, m)
        dot = abs(v * vAxe)
        if dot_max < dot:
            dot_max = dot
            i_axe_closest = i

    return i_axe_closest


def matrix_get_projected_vector_on_closest_axe(m, v, skip_v=None):
    i_closest_axe_to_skip = None
    if skip_v:
        i_closest_axe_to_skip = matrix_get_closest_axe_from_vector(m, skip_v)

    i_closest_axe = matrix_get_closest_axe_from_vector(m, v, skip_axe=i_closest_axe_to_skip)
    v_new = matrix_get_row(i_closest_axe, m)
    if v_new * v < 0:
        v_new *= -1.0
    return v_new
