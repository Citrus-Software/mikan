# coding: utf-8

import meta_nodal_py as kl
from meta_nodal_py.Imath import V3f

import mikan.tangerine.core as mk
from mikan.core import re_is_int, create_logger

log = create_logger()


class Deformer(mk.Deformer):
    node_class = kl.BlendShape

    def read(self):
        pass

    def build(self, data=None):
        # check data
        if not self.transform:
            raise mk.DeformerError('no transform to hook')

        # get shape?
        if not self.geometry:
            self.find_geometry()

        # build target list
        targets = {}

        for key in ('targets', 'weights', 'names', 'delta'):
            for t, v in self.data.get(key, {}).items():
                if t not in targets:
                    targets[t] = {}
                targets[t][key.strip('s')] = v

        n = 1
        if targets:
            n = max(targets) + 1

        # insert deformer
        self.node = kl.BlendShape(n, self.geometry, 'blendshape')

        if not self.node.get_dynamic_plug('names'):
            self.node.add_dynamic_plug("names", str(), n)

        if isinstance(self.geometry, kl.SplineCurve):
            node_in_plug = self.geometry.spline_in.get_input()
            self.geometry.spline_in.disconnect(restore_default=True)
            self.node.spline_in.connect(node_in_plug)
            self.geometry.spline_in.connect(self.node.spline_out)
        else:
            node_in_plug = self.geometry.mesh_in.get_input()
            self.geometry.mesh_in.disconnect(restore_default=True)
            self.node.mesh_in.connect(node_in_plug)
            self.geometry.mesh_in.connect(self.node.mesh_out)

        # update targets
        for t, data in targets.items():
            w = 0
            w_in = data.get('weight')
            if isinstance(w_in, str):
                w_in = mk.Nodes.get_id(w_in)
            elif isinstance(w_in, (float, int)):
                w = w_in

            target_in = Deformer._add_target(self.node, self.transform, t, w)

            if kl.is_plug(w_in):
                self.node.get_dynamic_plug('w{}'.format(t)).connect(w_in)

            name = ''
            if 'target' in data:
                _target = data['target']
                shp, xfo = None, None

                if isinstance(_target, str):
                    shp, xfo = Deformer.get_geometry_id(_target)
                elif isinstance(_target, (list, tuple)) and len(_target) == 2:
                    shp, xfo = _target
                elif isinstance(_target, kl.Node):
                    if isinstance(_target, kl.SceneGraphNode):
                        xfo = _target
                        shp = Deformer.get_deformer_ids(xfo).get('shape')
                    else:
                        shp = _target
                        xfo = shp.get_parent()

                if not shp or not xfo:
                    mk.DeformerError('invalid blend target: {}'.format(_target))

                name = xfo.get_name()

                target = Deformer.get_deformer_output(shp, xfo)
                target_in.connect(target)

            name = data.get('name', name)

            name_size = self.node.names.get_size()
            if t + 1 > name_size:
                self.node.names.resize(t - 1)
            self.node.names[t].set_value(name)

        # update i/o
        self.reorder()

        # update weights
        self.write()

    def write(self):

        # delta
        for t, delta in self.data.get('delta', {}).items():
            if 1 not in delta:
                continue

            ref_points = []
            if 'REFERENCE' in self.data.get('names', {}).get(t, ''):
                if isinstance(self.geometry, kl.Geometry):
                    mesh = self.geometry.mesh_in.get_value()
                    ref_points = mesh.positions()

            points = []
            wm = delta[1].weights
            count = len(wm)
            for i in range(count):
                pt = V3f(*wm[i * 3:i * 3 + 3])
                points.append(pt)

            for i in range(len(ref_points)):
                points[i] -= ref_points[i]

            self.node.shapes_deltas_in[t].set_value(points)

        # periodic spline fix?
        if isinstance(self.geometry, kl.SplineCurve):
            spline = self.node.spline_in.get_value()
            if spline.get_wrap():
                degree = spline.get_degree()
                m = self.maps[-1]
                for i in range(degree):
                    m.weights.append(m.weights[i])

        # target weightmaps
        for t, weights in self.data.get('maps', {}).items():
            if t == -1:
                continue

            vtx_indices = []
            vtx_weights = []

            for idx, w in enumerate(self.data['maps'][t].weights):
                if w != 0:
                    vtx_indices.append(idx)
                    vtx_weights.append(w)

            if not any(self.data['maps'][t].weights):
                vtx_indices.append(0)
                vtx_weights.append(0)

            self.node.shapes_vertex_indices_in[t].set_value(vtx_indices)
            self.node.shapes_vertex_weights_in[t].set_value(vtx_weights)

        # base weightmap
        if 'maps' in self.data and -1 in self.data['maps']:
            vtx_indices = []
            vtx_weights = []

            for idx, w in enumerate(self.data['maps'][-1].weights):
                if w != 0:
                    vtx_indices.append(idx)
                    vtx_weights.append(w)

            if not any(self.data['maps'][-1].weights):
                vtx_indices.append(0)
                vtx_weights.append(0)

            self.node.vertex_indices_in.set_value(vtx_indices)
            self.node.vertex_weights_in.set_value(vtx_weights)

    @staticmethod
    def hook(bs, xfo, hook):

        if hook == 'enable' or hook == 'envelope':
            return bs.enable_in

        elif hook.startswith('target.'):

            hook = hook.split('.')

            if re_is_int.match(hook[1]):
                return bs.shapes_in[int(hook[1])]
            else:
                pass

        elif hook.startswith('weight.'):
            hook = hook.split('.')

            if re_is_int.match(hook[1]):
                return bs.get_dynamic_plug('w{}'.format(int(hook[1])))

            else:
                for t in range(bs.names.get_size()):
                    name = bs.names[t].get_value()
                    if hook[1] == name:
                        return bs.get_dynamic_plug('w{}'.format(t))

    @staticmethod
    def _add_target(bs, xfo, index, weight=0, target=None):

        plug_weight_name = 'w{}'.format(index)
        if bs.get_dynamic_plug(plug_weight_name):
            raise mk.DeformerError('weight index already exists')
        plug_weight = bs.add_dynamic_plug(plug_weight_name, float(weight))
        bs.weights_in[index].connect(plug_weight)

        plug_target = bs.shapes_in[index]
        if target:
            plug_target.connect(target)
        else:
            plug_target.connect(bs.mesh_in)

        bs.references_in[index].connect(bs.mesh_in)

        return plug_target

kl.Blend