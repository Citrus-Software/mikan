# coding: utf-8

import maya.api.OpenMaya as om
from six import string_types

import maya.cmds as mc

from mikan.core.lib.rbf import RBF
from mikan.core.logger import create_logger, get_date_str
from mikan.maya.lib.geometry import Mesh, NurbsCurve, NurbsSurface, get_nearby_point_indices

from mikan.core.abstract.deformer import WeightMap

log = create_logger('mikan.retarget')
log.setLevel('DEBUG')


def retarget_model(
        model_origin, model_target,
        to_transfers, to_transfers_target=[],
        keep_origin=False, get_children=True,
        radius_exclusion=0.0, matrix_axe_mult=[1, 1, 1], matrix_axe_prio=[1, 2, 0],
):
    """
    Transfer model/curve/transform/hierarchy between one model two the other.

    Arguments:
        model_origin: Un mesh. Généralement le body d'un personnage. Doit avoir la même topologie que model_target.
        model_target: Un mesh. Généralement le body d'un personnage. Doit avoir la même topologie que model_origin.
        to_transfers: Les objets que vous voulez transférer du model_origin au model_target.
        to_transfers_target: Les objets de destination du transfert
        keep_origin: Supprime les objets source (si ils sont différents des targets)
        get_children: Transfert aussi les enfants des objets à transférer
        radius_exclusion:
        matrix_axe_mult:
        matrix_axe_prio:

    Author:
        Matthieu Cantat

    More information on: https://ovm.io/assets-wiki/11e757fa-d78f-3a00-bd8c-0242ac130002/11eb0df9-cce5-a6c6-a40d-0242ac180009
    """

    log.debug('__________________________________________________ START')

    if not all((model_origin, model_target)):
        raise ValueError('geometry missing')

    log.debug('__________________________________________________ TO TRANSFERS')

    to_transfers_compute_type = []
    to_transfers_points = []
    to_transfers_points_size = []
    to_transfers_trsf_infos = []

    if not to_transfers:
        return

    log.debug('\tINIT TRANSFER')

    ns_dupli = '__safe_dupli__'
    to_transfers_dupli = []
    if not to_transfers_target:
        log.debug('\t\tTO TRANSFERS DUPLICATION')
        for to_transfer in to_transfers:
            to_transfer_dupli = duplicate_hierarchy(to_transfer, ns=ns_dupli)
            to_transfers_dupli.append(to_transfer_dupli)

    to_transfers_children = []
    to_transfers_children_dupli = []

    if get_children:
        log.debug('\t\tTO TRANSFERS GET CHILDREN')

    for to_transfer, to_transfer_dupli in zip(to_transfers, to_transfers_dupli):
        children = get_hierarchy_transforms(to_transfer, include_root=False)
        to_transfers_children += children
        if not to_transfers_target:
            # children_targets = string_dag_path_add_namespace(children, ns_dupli)
            children_targets = get_hierarchy_transforms(to_transfer_dupli, include_root=False)
            to_transfers_children_dupli += children_targets

    to_transfers += to_transfers_children
    to_transfers_target += to_transfers_dupli + to_transfers_children_dupli

    log.debug('\tEXTRACT INFO')

    for to_transfer in to_transfers:

        t_type = get_transfer_type(to_transfer)

        to_transfer_points = []
        trsf_matrix_axe_length = [1, 1, 1]
        trsf_matrix = []
        trsf_pivot = []

        if t_type == 'point':
            to_transfer_points = [to_transfer]

        elif t_type == 'vector':
            to_transfer_points = [to_transfer, to_transfer[0] + to_transfer[1]]

        elif t_type == 'matrix':
            to_transfer_points = matrix_to_points(to_transfer, scale_axes=matrix_axe_mult)
            trsf_matrix_axe_length = matrix_to_axe_lengths(to_transfer)

        elif t_type == 'matrix_value':
            pass

        elif t_type in ['transform', 'joint', 'mesh', 'nurbsCurve', 'nurbsSurface']:

            trsf_matrix = mc.xform(to_transfer, q=True, m=True, ws=True)
            if trsf_matrix[12:-1] != [0, 0, 0]:
                to_transfer_points = matrix_to_points(trsf_matrix, scale_axes=matrix_axe_mult)
                trsf_matrix_axe_length = matrix_to_axe_lengths(trsf_matrix)
            r'''
            trsf_pivot = pm.xform( to_transfers[i] , q = True , piv = True , ws = True)
            if( trsf_pivot[0:3] != trsf_matrix[12:-1] ) and ( trsf_pivot[3:6] != trsf_matrix[12:-1] ):
                to_transfer_points.append( trsf_pivot[0:3] )
                to_transfer_points.append( trsf_pivot[3:6] )
            '''
            if t_type == 'mesh':
                to_transfer_points += Mesh(to_transfer).get_points()

            elif t_type == 'nurbsCurve':
                to_transfer_points += NurbsCurve(to_transfer).get_points()

            elif t_type == 'nurbsSurface':
                to_transfer_points += NurbsSurface(to_transfer).get_points()

        elif t_type == 'transform_value':
            pass

        to_transfers_points += to_transfer_points
        to_transfers_compute_type.append(t_type)
        to_transfers_points_size.append(len(to_transfer_points))
        to_transfers_trsf_infos.append([trsf_matrix_axe_length, trsf_matrix, trsf_pivot])

    log.debug('__________________________________________________ ORIGIN / TARGET TRANSFER INFO')

    log.debug('key_transfer NOT GIVEN ---> GET POINTS POSITIONS')

    model_target = string_copy_extension_vtx(model_origin, model_target)
    model_origin = string_copy_extension_vtx(model_target, model_origin)

    cage_base_points = Mesh(model_origin).get_points()
    cage_points = Mesh(model_target).get_points()

    cage_ids = get_nearby_point_indices(cage_base_points, to_transfers_points, radius_exclusion)

    cage_points = [[cage_points[i][0], cage_points[i][1], cage_points[i][2]]
                   for i in cage_ids]
    cage_base_points = [[cage_base_points[i][0], cage_base_points[i][1], cage_base_points[i][2]]
                        for i in cage_ids]
    cage_delta_points = [[cage_points[i][j] - cage_base_points[i][j]
                          for j in range(0, 3)] for i in range(0, len(cage_points))]

    if not to_transfers_points:
        return

    rbf_coef = RBF.get_coefficients(
        cage_base_points,
        cage_base_points,
        cage_delta_points,
        radius=1,
        kernel_mode=0
    )

    log.debug('__________________________________________________ APPLY TRANSFER INFO TO to_transfers_point')

    delta_points = RBF.evaluate(
        cage_base_points,
        to_transfers_points,
        rbf_coef,
        radius=1,
        kernel_mode=0
    )

    transfered_points = [[delta_points[i][j] + to_transfers_points[i][j]
                          for j in range(0, 3)] for i in range(0, len(to_transfers_points))]

    log.debug('__________________________________________________ APPLY to_transfers_point TO OBJS')

    index = 0
    for i in range(len(to_transfers_points_size)):

        out_points = transfered_points[index: index + to_transfers_points_size[i]]
        index += to_transfers_points_size[i]

        trsf_matrix_axe_length = to_transfers_trsf_infos[i][0]
        trsf_matrix = to_transfers_trsf_infos[i][1]
        trsf_pivot = to_transfers_trsf_infos[i][2]

        if to_transfers_compute_type[i] == 'point':
            pass

        elif to_transfers_compute_type[i] == 'vector':
            pass

        elif to_transfers_compute_type[i] == 'matrix':
            pass

        elif to_transfers_compute_type[i] == 'matrix_value':
            pass

        elif to_transfers_compute_type[i] in ['transform', 'joint', 'mesh', 'nurbsCurve', 'nurbsSurface']:
            if trsf_matrix[12:-1] != [0, 0, 0]:
                matrix_tmp = points_to_matrix(
                    out_points[0:4], scale_axes=matrix_axe_mult, axe_lengths=trsf_matrix_axe_length, orthogonize_list=matrix_axe_prio)
                mc.xform(to_transfers_target[i], ws=True, m=matrix_tmp)

                out_points = out_points[4:]
            r'''
            if (trsf_pivot[0:3] != trsf_matrix[12:-1]) and (trsf_pivot[3:6] != trsf_matrix[12:-1]):
                pm.xform(to_transfers_target[i], rp=(out_points[0][0], out_points[0][1], out_points[0][2]), sp=(out_points[1][0], out_points[1][1], out_points[1][2]))
                out_points = out_points[2:]
            '''
            if to_transfers_compute_type[i] == 'mesh':
                Mesh(to_transfers_target[i]).set_points(out_points)

            elif to_transfers_compute_type[i] == 'nurbsCurve':
                NurbsCurve(to_transfers_target[i]).set_points(out_points)

            elif to_transfers_compute_type[i] == 'nurbsSurface':
                NurbsSurface(to_transfers_target[i]).set_points(out_points)

        elif to_transfers_compute_type[i] == 'transform_value':
            pass

    log.debug('__________________________________________________ TO TRANSFERS CLEANUP')

    if to_transfers and not keep_origin:
        mc.delete(to_transfers)
        mc.namespace(set=':')
        if mc.namespace(exists=':' + ns_dupli):
            mc.namespace(rm=':' + ns_dupli, mergeNamespaceWithRoot=True, f=True)

    log.debug('__________________________________________________ END')

    log.info('transfer_to_model ========================  DONE ')
    log.info('transfered obj: {}'.format(len(to_transfers_target)))
    log.info('=================================================')

    return to_transfers_target


def get_transfer_type(elem):
    t_type = None

    if type(elem) in (list, tuple):
        n = len(elem)
        if n == 3:
            t_type = 'point'
        elif n == 6:
            t_type = 'vector'
        elif n == 16:
            t_type = 'matrix'
        elif n == 18:
            t_type = 'matrix_value'

    elif isinstance(elem, string_types):
        if '.' not in elem:
            if mc.nodeType(elem) == "transform":
                t_type = 'transform'

                shapes = mc.listRelatives(elem, c=True, s=True, pa=True)
                if shapes:
                    node_type = mc.nodeType(shapes[0])
                    if node_type == "mesh":
                        t_type = 'mesh'
                    elif node_type == "nurbsCurve":
                        t_type = 'nurbsCurve'
                    elif node_type == "nurbsSurface":
                        t_type = 'nurbsSurface'

            elif mc.nodeType(elem) == "joint":
                t_type = 'joint'
        else:
            t_type = 'transform_value'

    return t_type


def get_hierarchy_transforms(node, include_root=False):
    descendents = mc.listRelatives(node, ad=True, f=True, type="transform") or []

    if include_root:
        descendents.append(node)

    hierarchy = [elem for elem in descendents if "Constraint" not in mc.nodeType(elem) and node != elem]
    hierarchy.reverse()
    return hierarchy


def duplicate_hierarchy(root, ns='__safe_dupli__'):
    descendents = mc.listRelatives(root, ad=True, f=True, pa=True, type="transform") or []

    old_ns = mc.namespaceInfo(an=1)
    if not ns.startswith(':'):
        ns = ':' + ns
    if not mc.namespace(ex=ns):
        mc.namespace(add=ns, an=True)
    mc.namespace(set=ns)
    dupe_root = mc.duplicate(root, rr=1)[0]
    mc.namespace(set=old_ns)

    if not descendents:
        return str(dupe_root)

    dupes = mc.listRelatives(str(dupe_root), ad=True, f=True, pa=True, type="transform") or []

    for orig, dupe in zip(descendents + [root], dupes + [str(dupe_root)]):
        orig_name = orig.split("|")[-1]
        ns_orig, _sep, _name = orig_name.rpartition(":")
        new_ns = ns + ':' + ns_orig
        if not mc.namespace(ex=new_ns):
            mc.namespace(add=new_ns, an=True)

        mc.rename(dupe, ns + ':' + orig.split("|")[-1])

    return str(dupe_root)


def string_copy_extension_vtx(source, target):
    if isinstance(source, (list, tuple)) and '.vtx' in source[0]:

        if isinstance(target, string_types) and '.vtx' not in target:
            target = [target + '.' + scr.split('.')[1] for scr in source]

        elif isinstance(target, (list, tuple)) and '.vtx' not in target[0]:
            target = [trg + '.' + scr.split('.')[1] for scr in source for trg in target]

    elif '.vtx' in source:

        if isinstance(target, string_types) and '.vtx' not in target:
            target = target + '.' + source.split('.')[1]

        elif isinstance(target, (list, tuple)) and '.vtx' not in target[0]:
            target = [trg + '.' + source.split('.')[1] for trg in target]

    return target


# -- math

def matrix_to_points(matrix, scale_axes=None):
    if scale_axes is None:
        scale_axes = [1.0, 1.0, 1.0]

    vX = om.MVector(matrix[0], matrix[1], matrix[2])
    vY = om.MVector(matrix[4], matrix[5], matrix[6])
    vZ = om.MVector(matrix[8], matrix[9], matrix[10])

    vX.normalize()
    vY.normalize()
    vZ.normalize()

    vX *= scale_axes[0]
    vY *= scale_axes[1]
    vZ *= scale_axes[2]

    pX = [matrix[12] + vX.x, matrix[13] + vX.y, matrix[14] + vX.z]
    pY = [matrix[12] + vY.x, matrix[13] + vY.y, matrix[14] + vY.z]
    pZ = [matrix[12] + vZ.x, matrix[13] + vZ.y, matrix[14] + vZ.z]
    p = [matrix[12], matrix[13], matrix[14]]

    return [pX, pY, pZ, p]


def matrix_to_axe_lengths(matrix):
    vX = om.MVector(matrix[0], matrix[1], matrix[2])
    vY = om.MVector(matrix[4], matrix[5], matrix[6])
    vZ = om.MVector(matrix[8], matrix[9], matrix[10])

    axe_lengths = [vX.length(), vY.length(), vZ.length()]

    return axe_lengths


def points_to_matrix(points, scale_axes=None, axe_lengths=None, orthogonize_list=None):
    if scale_axes is None:
        scale_axes = [0.2, 0.2, 0.2]
    if axe_lengths is None:
        axe_lengths = [1, 1, 1]
    if orthogonize_list is None:
        orthogonize_list = [1, 2, 0]

    vX = om.MVector(
        points[0][0] - points[3][0],
        points[0][1] - points[3][1],
        points[0][2] - points[3][2]
    )
    vY = om.MVector(
        points[1][0] - points[3][0],
        points[1][1] - points[3][1],
        points[1][2] - points[3][2]
    )
    vZ = om.MVector(
        points[2][0] - points[3][0],
        points[2][1] - points[3][1],
        points[2][2] - points[3][2]
    )

    vX /= scale_axes[0]
    vY /= scale_axes[1]
    vZ /= scale_axes[2]

    vs = [vX, vY, vZ]

    ol = orthogonize_list
    vs[ol[2]] = vs[ol[0]] ^ vs[ol[1]]
    vs[ol[1]] = vs[ol[0]] ^ vs[ol[2]] * -1

    vs[0].normalize()
    vs[1].normalize()
    vs[2].normalize()

    vs[0] *= axe_lengths[0]
    vs[1] *= axe_lengths[1]
    vs[2] *= axe_lengths[2]

    p = [points[3][0], points[3][1], points[3][2]]

    matrix = [
        vs[0].x, vs[0].y, vs[0].z, 0,
        vs[1].x, vs[1].y, vs[1].z, 0,
        vs[2].x, vs[2].y, vs[2].z, 0,
        p[0], p[1], p[2], 1
    ]
    return matrix
