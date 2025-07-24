# coding: utf-8

import meta_nodal_py as kl

import mikan.tangerine.core as mk
from mikan.tangerine.lib.commands import add_plug
from mikan.tangerine.lib.connect import create_curve_value, connect_expr
from mikan.core.logger import create_logger

log = create_logger()


class Deformer(mk.Deformer):
    node_class = kl.Cluster

    def build(self):
        # check data
        if not self.transform:
            raise mk.DeformerError('geometry missing')
        if not self.data['handle']:
            raise mk.DeformerError('handle missing')

        # get handle
        handle = self.data['handle']
        try:
            if isinstance(handle, str):
                handle = self.get_node(handle)
        except:
            raise mk.DeformerError('skipped: handle does not exist')

        bind_pose = self.data.get('bind_pose')
        if bind_pose and isinstance(bind_pose, str):
            bind_pose = self.get_node(bind_pose)
        elif not isinstance(bind_pose, kl.SceneGraphNode):
            bind_pose = handle.get_parent()

        # get shape
        if not self.geometry:
            self.find_geometry()

        # insert deformer
        name = '_'.join(handle.get_name().split('_')[1:])
        if not name:
            name = handle.get_name()

        self.node = kl.Cluster(self.geometry, 'cluster_{}'.format(name))
        self.node.offset_in.connect(bind_pose.world_transform)
        self.node.start_transform_in.connect(bind_pose.world_transform)
        if not self.data['local']:
            if self.data['relative']:
                self.node.geom_world_transform_in.connect(self.transform.world_transform)
            else:
                self.node.geom_world_transform_in.set_value(self.transform.world_transform.get_value())
        self.node.transform_in.connect(handle.world_transform)
        self.node.transform_interp_in.set_value(True)

        if isinstance(self.geometry, kl.SplineCurve):
            node_in_plug = self.geometry.spline_in.get_input()
            self.geometry.spline_in.disconnect(restore_default=False)
            self.node.spline_in.connect(node_in_plug)
            self.geometry.spline_in.connect(self.node.spline_out)
        else:
            node_in_plug = self.geometry.mesh_in.get_input()
            self.geometry.mesh_in.disconnect(restore_default=False)
            self.node.mesh_in.connect(node_in_plug)
            self.geometry.mesh_in.connect(self.node.mesh_out)

        # soft mod ?
        if self.data.get('soft'):
            distance = kl.DistanceWeightSolver(self.node, 'distance')
            distance.radius_in.set_value(self.data['falloff_radius'])
            distance.mesh_world_transform_in.connect(self.geometry.world_transform)

            if isinstance(self.geometry, kl.SplineCurve):
                self.log_error('spline curve cannot be soft mod deformed')
            else:
                distance.mesh_in.connect(node_in_plug)

            pivot = self.data['falloff_pivot']
            if self.data['falloff_pivot'] and isinstance(self.data['falloff_pivot'], str):
                pivot = self.get_node(self.data['falloff_pivot'])

            if isinstance(pivot, kl.SceneGraphNode):
                distance.world_target_in.connect(pivot.world_transform)

            falloff_radius_plug = handle.get_dynamic_plug('falloff_radius')
            if not falloff_radius_plug:
                falloff_radius_plug = add_plug(handle, 'falloff_radius', float, keyable=True, min_value=0)
            falloff_radius_plug.set_value(self.data['falloff_radius'])

            if isinstance(pivot, kl.SceneGraphNode):
                srt = kl.TransformToSRTNode(handle, 'srt_world')
                srt.transform.connect(handle.world_transform)
                vs = kl.V3fToFloat(srt, 'scale')
                vs.vector.connect(srt.scale)
                connect_expr(
                    'r = k*(x+y+z)/3',
                    r=distance.radius_in,
                    k=falloff_radius_plug,
                    x=vs.x,
                    y=vs.y,
                    z=vs.z
                )
            else:
                distance.radius_in.connect(falloff_radius_plug)

            keys = self.data['falloff_curve']
            if keys:
                curve = create_curve_value(keys)
                distance.curve_in.set_value(curve)

            solver = distance
            self.node.vertex_indices_in.connect(solver.vertex_indices_out)
            self.node.vertex_weights_in.connect(solver.vertex_weights_out)

        # update i/o
        self.reorder()

        # update weights
        self.write()

    def write(self):

        if self.node.vertex_indices_in.is_connected():
            return

        if 'maps' not in self.data or 0 not in self.data['maps']:
            return

        # periodic spline fix?
        if isinstance(self.geometry, kl.SplineCurve):
            spline = self.node.spline_in.get_value()
            if spline.get_wrap():
                degree = spline.get_degree()
                m = self.data['maps'][0]
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
    def get_handle(dfm):
        handle = dfm.transform_in.get_input()
        if handle:
            return handle.get_node()

    @staticmethod
    def hook(dfm, xfo, hook):

        if hook == 'enable' or hook == 'envelope':
            return dfm.enable_in

        # soft mod
        distance = dfm.find('distance')

        if hook in ('radius', 'falloff_radius'):
            handle = Deformer.get_handle(dfm)

            if distance:
                if handle and handle.get_dynamic_plug('falloff_radius'):
                    return handle.get_dynamic_plug('falloff_radius')
                else:
                    return distance.get_dynamic_plug('radius_in')
            else:
                raise mk.DeformerError('cluster does not have radius attribute')
