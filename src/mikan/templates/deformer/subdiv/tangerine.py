# coding: utf-8

import meta_nodal_py as kl

import mikan.tangerine.core as mk
from mikan.core import create_logger

log = create_logger()


class Deformer(mk.Deformer):
    node_class = kl.SubdivMesh

    def build(self):
        # check data
        if not self.transform:
            raise mk.DeformerError('no transform')

        ids = self.get_deformer_ids(self.transform)
        if 'source' not in ids or not isinstance(ids['source'], kl.Node):
            self.log_error('abc reader is needed for subdiv node')

        # get shape?
        if not self.geometry:
            self.find_geometry()
        if isinstance(self.geometry, kl.SplineCurve):
            raise mk.DeformerError('cannot subdivide curve')

        # insert deformer
        self.node = kl.SubdivMesh(self.geometry, 'subdiv')
        self.node.level.set_value(self.data['level'])

        reader_output = Deformer.get_deformer_output(ids['source'], self.transform)
        self.node.static_mesh_in.connect(reader_output)

        node_in_plug = self.geometry.mesh_in.get_input()
        self.geometry.mesh_in.disconnect(restore_default=True)
        self.node.animated_mesh_in.connect(node_in_plug)
        self.geometry.mesh_in.connect(self.node.mesh_out)

        # update i/o
        self.reorder()

    @staticmethod
    def hook(node, xfo, hook):
        if hook == 'level':
            node.level
