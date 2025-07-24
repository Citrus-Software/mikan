# coding: utf-8

import meta_nodal_py as kl
from meta_nodal_py.Imath import V3f, M44f, Euler

import mikan.tangerine.core as mk
from mikan.tangerine.lib.rig import (
    point_constraint, orient_constraint, aim_constraint, matrix_constraint,
    create_srt_in, create_srt_out, copy_transform, find_srt, axis_to_vector
)
from mikan.tangerine.lib.commands import set_plug
from mikan.core import cleanup_str, create_logger

log = create_logger()


class Mod(mk.Mod):

    def run(self):
        node = self.data.get('node', self.node)
        parent = self.data.get('parent', node.get_parent())

        if 'curve' not in self.data:
            raise mk.ModArgumentError('curve not defined')
        else:
            crv_shp, xfo = self.data['curve']
            shp = mk.Deformer.get_deformer_output(crv_shp, xfo).get_node()

        target = self.data.get('target')

        if 'target' not in self.data:
            # legacy mode
            node_id = mk.Nodes.get_node_id(node, find='::skin')
            ctrl_id = node_id.replace('::skin', '::ctrls')
            target = mk.Nodes.get_id(ctrl_id)

            parent = node.get_parent()

        axis = self.data.get('axis', 'y')
        if axis not in 'xyz':
            axis = 'y'

        # build rig
        name = cleanup_str(self.data.get('name', xfo.get_name()))

        root = kl.SceneGraphNode(parent, 'bank_' + name)
        copy_transform(target, root)

        _xfo = kl.SceneGraphNode(root, 'bank_curve_' + name)
        mk.Shape(_xfo).copy(xfo, world=True)
        shp = mk.Shape(_xfo).get_shapes()[0]
        # TODO: si la curve a de l'historique il ne faudrait pas dupliquer

        orient = kl.SceneGraphNode(root, 'bank_orient_' + name)
        srt_out = create_srt_out(target, vectors=False)
        srt = create_srt_in(orient, vectors=False)
        srt.rotate.connect(srt_out.rotate)
        srt.rotate_order.connect(srt_out.rotate_order)

        tgt = kl.SceneGraphNode(orient, 'bank_target_' + name)
        pt = kl.SceneGraphNode(root, 'bank_point_' + name)
        point_constraint(tgt, pt, axes='xyz'.replace(axis, ''))
        tgt.transform.set_value(M44f(axis_to_vector(axis), V3f(), V3f(1, 1, 1), Euler.XYZ))

        aim = kl.SceneGraphNode(root, 'bank_aim_' + name)
        aim_constraint(pt, aim, aim_vector=V3f(1, 0, 0), up_vector=V3f(0, 0, 0))

        loc = kl.SceneGraphNode(aim, 'bank_loc_' + name)
        dim = mk.Shape(_xfo).get_dimensions()

        loc.transform.set_value(M44f(V3f(max(dim) * 2, 0, 0), V3f(), V3f(1, 1, 1), Euler.XYZ))

        poc = kl.SceneGraphNode(root, 'bank_poc_' + name)

        _srt = create_srt_in(poc)

        _c = kl.Closest(poc, 'closest')
        _c.spline_in.connect(shp.spline_in)
        _c.spline_mesh_in.connect(shp.spline_mesh_out)
        _c.geom_world_transform_in.connect(shp.world_transform)
        _c.transform_in.connect(loc.world_transform)

        imx = kl.InverseM44f(poc, '_imx')
        imx.input.connect(poc.parent_world_transform)

        mmx = kl.MultM44f(poc, '_mmx')
        mmx.input[0].connect(_c.transform_out)
        mmx.input[1].connect(imx.output)

        _srto = create_srt_out(mmx)

        # connect poc
        _srt.rotate_pivot.connect(_srto.translate)
        orient_constraint(target, poc)

        # hook
        matrix_constraint(poc, node)

        # lock rotate y
        srt = find_srt(target)
        plug = srt.rotate.get_input().get_node().get_plug(axis)
        set_plug(plug, k=0, min_value=0, max_value=0, lock=True)

        # exit
        root.show.set_value(False)
