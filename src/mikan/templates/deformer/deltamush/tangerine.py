# coding: utf-8

import meta_nodal_py as kl

import mikan.tangerine.core as mk
from mikan.core import re_is_int, create_logger

log = create_logger()


class Deformer(mk.Deformer):
    node_class = kl.DeltaMush

    def read(self):
        pass

    def build(self, data=None):
        # check data
        if not self.transform:
            raise mk.DeformerError('no transform to hook')

        # get shape?
        if not self.geometry:
            self.find_geometry()
        if isinstance(self.geometry, kl.SplineCurve):
            mk.DeformerError('cannot build deltamush for spline curve')

        # insert deformer
        self.node = kl.DeltaMush(self.geometry, 'delta_mush')

        # self.node.geom_world_transform_in.connect(self.transform.world_transform)

        node_in_plug = self.geometry.mesh_in.get_input()
        self.geometry.mesh_in.disconnect(restore_default=True)
        self.node.mesh_in.connect(node_in_plug)
        self.geometry.mesh_in.connect(self.node.mesh_out)

        # TODO: refacto du node nécessaire
        self.node.enable_in.set_value(self.data['displacement'])

        # connect smooth
        laplacian = kl.Laplacian(self.node, 'laplacian')
        laplacian.mesh_in.connect(node_in_plug)

        laplacian.iterations_in.set_value(self.data.get('iterations', 10))

        # laplacian.enable_in.connect(self.node.enable_in)

        # laplacian.multiple_basis_in.connect(self.node.multiple_basis_in)
        # laplacian.orthonormalize_in.connect(self.node.orthonormalize_in)
        # self.node.multiple_basis_in.set_value(True)
        # self.node.orthonormalize_in.set_value(True)

        if laplacian.get_plug('keep_borders_in'):
            laplacian.keep_borders_in.set_value(True)

        # set reference values
        self.node.neighbors_in.set_value(laplacian.neighbors_out.get_value())
        self.node.deltas_in.set_value(laplacian.deltas_out.get_value())

        self.node.mesh_in.connect(laplacian.mesh_out)

        # update i/o
        self.reorder()

        # update weights
        self.write()

    def write(self):
        if 'maps' not in self.data or 0 not in self.data['maps']:
            return

        # write
        vtx_indices = []
        vtx_weights = []

        for idx, w in enumerate(self.data['maps'][0].weights):
            if w != 0:
                vtx_indices.append(idx)
                vtx_weights.append(w)

        if not any(self.data['maps'][0].weights):
            vtx_indices.append(0)
            vtx_weights.append(0)

        self.node.vertex_indices_in.set_value(vtx_indices)
        self.node.vertex_weights_in.set_value(vtx_weights)

    @staticmethod
    def hook(bs, xfo, hook):

        if hook == 'enable' or hook == 'envelope':
            return bs.enable_in
