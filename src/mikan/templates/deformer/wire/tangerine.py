# coding: utf-8

import meta_nodal_py as kl

from mikan.core.prefs import Prefs
import mikan.tangerine.core as mk
from mikan.tangerine.lib.commands import *
from mikan.core.logger import create_logger

log = create_logger()


class Deformer(mk.Deformer):
    node_class = kl.Wire

    def build(self, data=None):
        # check data
        if not self.transform:
            raise mk.DeformerError('geometry missing')
        if not self.data['maps']:
            raise mk.DeformerError('map missing')

        # get shape
        if not self.geometry:
            self.find_geometry()

        # get wire data
        _curve = self.data.get('curve')
        if isinstance(_curve, tuple):
            cv_wire_shp, cv_wire = _curve
        elif isinstance(_curve, str):
            cv_wire_shp, cv_wire = self.get_geometry_id(_curve)

        _base = self.data.get('base')
        if isinstance(_base, tuple):
            cv_base_shp, cv_base = _base
        if isinstance(cv_base, str):
            try:
                cv_base_shp, cv_base = mk.Deformer.get_geometry_id(_base)
            except:
                cv_base = kl.SceneGraphNode(cv_wire.get_parent(), 'wire_base')
                cv_base_shp = kl.Curve(cv_base, 'wire_baseShape')
                cv_base_shp.spline_in.set_value(cv_wire_shp.spline_in.get_value())

        # adjust sampling
        if isinstance(cv_wire_shp, kl.Geometry):
            spline = cv_wire_shp.spline_in.get_value()
            cps = spline.get_control_points()
            degree = spline.get_degree()
            cv_wire_shp.sampling_in.set_value(4 * (len(cps) + 1) * (degree ** 2))

        if isinstance(cv_base_shp, kl.Geometry):
            spline = cv_base_shp.spline_in.get_value()
            cps = spline.get_control_points()
            degree = spline.get_degree()
            cv_base_shp.sampling_in.set_value(4 * (len(cps) + 1) * (degree ** 2))

        # insert wire
        self.node = kl.Wire(self.geometry, 'wire')
        node_in_plug = self.geometry.mesh_in.get_input()
        self.geometry.mesh_in.disconnect(True)
        self.node.mesh_in.connect(node_in_plug)
        self.geometry.mesh_in.connect(self.node.mesh_out)

        # rebuild base if not here ?
        dropoff = self.data.get('dropoff', 1)
        rotate = self.data.get('rotate', 1)

        self.node.wire_curve_in.connect(cv_wire_shp.spline_mesh_out)
        self.node.wire_world_transform_in.connect(cv_wire.world_transform)
        self.node.geom_world_transform_in.connect(self.transform.world_transform)
        self.node.reference_curve_in.connect(cv_base_shp.spline_mesh_out)
        self.node.reference_world_transform_in.connect(cv_base.world_transform)
        self.node.dropoff_in.set_value(dropoff)
        self.node.rotate_in.set_value(rotate)

        if Prefs.get('deformer/wire/use_derivatives', False):
            self.node.wire_spline_in.connect(cv_wire_shp.spline_in)
            self.node.wire_sampling_in.connect(cv_wire_shp.sampling_in)
            self.node.wire_length_in.connect(cv_wire_shp.length_out)
            self.node.reference_spline_in.connect(cv_base_shp.spline_in)
            self.node.reference_sampling_in.connect(cv_base_shp.sampling_in)
            self.node.reference_length_in.connect(cv_base_shp.length_out)

        # update i/o
        self.reorder()

        # update weights
        self.write()

    def write(self):
        if 'maps' not in self.data or 0 not in self.data['maps']:
            return

        # periodic spline fix?
        if isinstance(self.geometry, kl.SplineCurve):
            spline = self.node.spline_in.get_value()
            if spline.get_wrap():
                degree = spline.get_degree()
                m = self.maps[0]
                for i in range(degree):
                    m.weights.append(m.weights[i])

        # write
        vtx_indices = []
        vtx_weights = []

        for idx, w in enumerate(self.data['maps'][0].weights):
            if w > 0:
                vtx_indices.append(idx)
                vtx_weights.append(w)

        if not any(self.data['maps'][0].weights):
            vtx_indices.append(0)
            vtx_weights.append(0)

        self.node.vertex_indices_in.set_value(vtx_indices)
        self.node.vertex_weights_in.set_value(vtx_weights)

    @staticmethod
    def hook(dfm, xfo, hook):

        if hook == 'enable' or hook == 'envelope':
            return dfm.enable_in

        elif hook == 'scale':
            return dfm.scale_in
        elif hook == 'rotate':
            return dfm.rotate_in
