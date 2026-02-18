# coding: utf-8

import meta_nodal_py as kl
from meta_nodal_py.Imath import V3f

import mikan.tangerine.core as mk
from mikan.core import re_is_int, create_logger, unique
from mikan.tangerine import connect_driven_curve, connect_add
from mikan.tangerine.lib.commands import add_plug

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
        self.targets = {}

        for key in ('targets', 'weights', 'names', 'delta'):
            for t, v in self.data.get(key, {}).items():
                if t not in self.targets:
                    self.targets[t] = {}
                self.targets[t][key.strip('s')] = v

        last_id = 0
        if self.targets:
            last_id = max(self.targets)

        for t, target_data in self.targets.items():
            target_data['inbetweens'] = {}
            for k in {'target', 'delta'}:
                if k not in target_data or not isinstance(target_data[k], dict):
                    continue
                for i in target_data[k]:
                    if i != 1 and i not in target_data['inbetweens']:
                        last_id += 1
                        target_data['inbetweens'][i] = last_id

        # insert deformer
        self.node = kl.BlendShape(last_id + 1, self.geometry, 'blendshape')

        if not self.node.get_dynamic_plug('_names'):
            add_plug(self.node, '_names', str, array=True, size=last_id + 1)

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

        # build groups
        group_plugs = {}

        groups = self.data.get('groups', {})
        group_max = 1
        if groups:
            group_max = max(groups) + 1
        group_names = add_plug(self.node, '_group_names', str, array=True, size=group_max)

        for gid in groups:
            group_name = groups[gid].get('name', 'group{}'.format(gid))
            group_names[gid].set_value(group_name)

            group_plugs[gid] = add_plug(
                self.node, '_g{}'.format(gid),
                float, min_value=0, max_value=1,
            )
            group_plugs[gid].set_value(groups[gid].get('weight', 1.0))

        # update targets
        for t, data in self.targets.items():
            w = 0
            w_in = data.get('weight')
            if isinstance(w_in, str):
                w_in = mk.Nodes.get_id(w_in)
            elif isinstance(w_in, (float, int)):
                w = w_in

            # add target plugs
            if 'target' in data and not isinstance(data['target'], dict):
                data['target'] = {1.0: data['target']}
            if 'delta' in data and not isinstance(data['delta'], dict):
                data['delta'] = {1.0: data['delta']}

            ib_keys = unique(list(data.get('target', {})) + list(data.get('delta', {})))
            ib_targets = {}

            target_inputs = {}
            for ib in sorted(ib_keys):
                target_id = t
                if ib != 1.0:
                    target_id = data['inbetweens'][ib]

                ib_targets[ib] = target_id

                _w = w if ib == 1.0 else 0.0
                target_inputs[ib] = Deformer._add_target(self.node, self.transform, target_id, _w, in_between=ib != 1.0)

            # weight plug
            plug_weight = self.node.get_dynamic_plug(f'_w{t}')
            if kl.is_plug(w_in):
                plug_weight.connect(w_in)

            # in between emulation
            if len(ib_keys) > 1:
                for ib, target_id in ib_targets.items():
                    curve_keys = {0: 0}
                    for _ib in ib_keys:
                        curve_keys[_ib] = 0
                    curve_keys[ib] = 1

                    weight_curve = connect_driven_curve(
                        plug_weight,
                        None,
                        keys=curve_keys,
                        tangent_mode='linear',
                        pre='linear',
                        post='linear'
                    )

                    # group weight
                    _groups = self._get_target_hierarchy_indices(groups, t)
                    if _groups:
                        _plugs = [group_plugs[gid] for gid in _groups]
                        _plugs.append(weight_curve.result)
                        mult = create_multiply_chain(_plugs, self.node)
                        self.node.weights_in[target_id].connect(mult)
                    else:
                        self.node.weights_in[target_id].connect(weight_curve.result)

            # no in between: direct connection
            else:
                _groups = self._get_target_hierarchy_indices(groups, t)
                if _groups:
                    _plugs = [group_plugs[gid] for gid in _groups]
                    _plugs.append(plug_weight)
                    mult = create_multiply_chain(_plugs, self.node)
                    self.node.weights_in[t].connect(mult)
                else:
                    self.node.weights_in[t].connect(plug_weight)

            # connect geometry
            name = ''

            if 'target' in data:

                for ib, target_id in target_inputs:
                    if ib not in data['target'] or not isinstance(data['target'], dict):
                        continue
                    _target = data['target'][ib]

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
                    target_inputs[ib].connect(target)

            name = data.get('name', name)

            name_size = self.node._names.get_size()
            if t + 1 > name_size:
                self.node._names.resize(t - 1)
            self.node._names[t].set_value(name)

        # update i/o
        self.reorder()

        # update weights
        self.write()

    def write(self):

        # delta
        for t, delta in self.data.get('delta', {}).items():
            if 1 not in delta:
                continue

            if not isinstance(delta, dict):
                delta = {1.0: delta}

            target_ids = {1.0: t}
            if t in self.targets and 'inbetweens' in self.targets[t]:
                target_ids.update(self.targets[t]['inbetweens'])

            for ib in delta:
                if ib not in target_ids:
                    # log?
                    continue

                ref_points = []
                if 'REFERENCE' in self.data.get('names', {}).get(t, ''):
                    if isinstance(self.geometry, kl.Geometry):
                        mesh = self.geometry.mesh_in.get_value()
                        ref_points = mesh.positions()

                points = []
                wm = delta[ib].weights
                count = len(wm)
                for i in range(count):
                    pt = V3f(*wm[i * 3:i * 3 + 3])
                    points.append(pt)

                for i in range(len(ref_points)):
                    points[i] -= ref_points[i]

                target_id = target_ids[ib]
                self.node.shapes_deltas_in[target_id].set_value(points)

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
                return bs.get_dynamic_plug('_w{}'.format(int(hook[1])))

            else:
                for t in range(bs._names.get_size()):
                    name = bs._names[t].get_value()
                    if hook[1] == name:
                        return bs.get_dynamic_plug('_w{}'.format(t))

        elif hook.startswith('group.'):
            hook = hook.split('.')

            if re_is_int.match(hook[1]):
                return bs.get_dynamic_plug('_g{}'.format(int(hook[1])))

            else:
                for t in range(bs._group_names.get_size()):
                    name = bs._group_names[t].get_value()
                    if hook[1] == name:
                        return bs.get_dynamic_plug('_g{}'.format(t))

    @staticmethod
    def _add_target(bs, xfo, index, weight=0, target=None, in_between=False):

        plug_weight_name = '_w{}'.format(index)
        if bs.get_dynamic_plug(plug_weight_name):
            raise mk.DeformerError('weight index already exists')

        if in_between:
            if index >= bs.weights_in.get_size():
                bs.weights_in.resize(index + 1)
                bs.shapes_in.resize(index + 1)
                bs.references_in.resize(index + 1)

                bs.shapes_deltas_in.resize(index + 1)
                bs.shapes_vertex_indices_in.resize(index + 1)
                bs.shapes_vertex_weights_in.resize(index + 1)
        else:
            plug_weight = add_plug(bs, plug_weight_name, float, min_value=0, max_value=1)
            plug_weight.set_value(weight)
            bs.weights_in[index].connect(plug_weight)

        plug_target = bs.shapes_in[index]
        if target:
            plug_target.connect(target)
        else:
            plug_target.connect(bs.mesh_in)

        bs.references_in[index].connect(bs.mesh_in)

        return plug_target

    @staticmethod
    def _get_target_hierarchy_indices(groups, index):

        current_group_id = None

        # find first parent
        for group_id, group_data in groups.items():
            targets = group_data.get('targets', [])
            if index in targets:
                current_group_id = group_id
                break

        if current_group_id is None:
            return []

        # find hierarchy
        hierarchy_ids = []

        while current_group_id is not None:
            hierarchy_ids.append(current_group_id)
            group_data = groups.get(current_group_id)
            if not group_data:
                break

            current_group_id = group_data.get('parent')

        return hierarchy_ids


def create_multiply_chain(plugs, parent):
    count = len(plugs)

    if count == 0:
        return None
    if count == 1:
        return plugs[0]

    mult = kl.Mult(parent, '_mult')
    mult.input1.connect(plugs[0])
    mult.input2.connect(plugs[1])

    for next_plug in plugs[2:]:
        mult_new = kl.Mult(parent, '_mult')
        mult_new.input1.connect(mult.output)
        mult_new.input2.connect(next_plug)
        mult = mult_new

    return mult.output
