# coding: utf-8

import meta_nodal_py as kl

import mikan.tangerine.core as mk
from mikan.core.logger import create_logger

log = create_logger()


class Deformer(mk.Deformer):
    node_class = kl.ShrinkWrap

    def build(self, data=None):
        # check data
        if not self.transform:
            raise mk.DeformerError('geometry missing')

        # get shape
        if not self.geometry:
            self.find_geometry()

        # get target data
        _target = self.data.get('target')
        if isinstance(_target, tuple):
            target_shp, target_xfo = _target
        elif isinstance(_target, str):
            target_shp, target_xfo = self.get_geometry_id(_target)
        else:
            raise mk.DeformerError('invalid target')

        level = self.data['target_subdivision']
        ids = self.get_deformer_ids(target_xfo)
        if level and 'source' not in ids or not isinstance(ids['source'], kl.Node):
            raise mk.DeformerError('target abc reader is needed for subdiv node')

        # insert deformer
        self.node = kl.ShrinkWrap(self.geometry, 'shrink')
        node_in_plug = self.geometry.mesh_in.get_input()
        self.geometry.mesh_in.disconnect(True)
        self.node.mesh_in.connect(node_in_plug)
        self.geometry.mesh_in.connect(self.node.mesh_out)

        self.node.geom_world_transform_in.connect(self.transform.world_transform)

        self.node.bidirectional_in.set_value(self.data['bidirectional'])
        self.node.closest_if_no_intersection_in.set_value(self.data['closest_if_no_intersection'])
        self.node.offset_in.set_value(self.data['offset'] + self.data['target_offset'])

        # target
        target_output = self.get_deformer_output(target_shp, target_xfo)

        if level == 0:
            self.node.target_mesh_in.connect(target_output)
        else:
            # find subd
            for o in target_output.get_outputs():
                o = o.get_node()
                if isinstance(o, kl.SubdivMesh):
                    if o.level.get_value() == level:
                        subd = o
                        break
            else:
                subd = kl.SubdivMesh(target_xfo, 'subdiv')
                subd.level.set_value(level)
                subd.animated_mesh_in.connect(target_output)

                reader_output = Deformer.get_deformer_output(ids['source'], target_xfo)
                subd.static_mesh_in.connect(reader_output)

            self.node.target_mesh_in.connect(subd.mesh_out)

        self.node.target_world_transform_in.connect(target_xfo.world_transform)

        # update i/o
        self.reorder()

        # update weights
        self.write()

    def write(self):
        wm = None
        if 'maps' in self.data and 0 in self.data['maps']:
            wm = self.data['maps'][0]
        if 'membership' in self.data:
            if wm is not None:
                wm *= self.data['membership']
            else:
                wm = self.data['membership']

        if wm is None:
            return

        # periodic spline fix?
        if isinstance(self.geometry, kl.SplineCurve):
            spline = self.node.spline_in.get_value()
            if spline.get_wrap():
                degree = spline.get_degree()
                for i in range(degree):
                    wm.weights.append(wm.weights[i])

        # write
        vtx_indices = []
        vtx_weights = []

        for idx, w in enumerate(wm.weights):
            if w > 0:
                vtx_indices.append(idx)
                vtx_weights.append(w)

        if not any(wm.weights):
            vtx_indices.append(0)
            vtx_weights.append(0)

        self.node.vertex_indices_in.set_value(vtx_indices)
        self.node.vertex_weights_in.set_value(vtx_weights)

    @staticmethod
    def hook(dfm, xfo, hook):

        if hook == 'enable' or hook == 'envelope':
            return dfm.enable_in

        if hook == 'offset':
            return dfm.offset_in
