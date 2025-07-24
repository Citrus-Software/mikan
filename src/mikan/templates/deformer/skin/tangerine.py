# coding: utf-8

import meta_nodal_py as kl
from meta_nodal_py.Imath import M44f

import mikan.tangerine.core as mk
from mikan.tangerine.lib.commands import *
from mikan.core.logger import create_logger

log = create_logger()


class Deformer(mk.Deformer):
    node_class = (kl.Skin, kl.DualQuatSkin)

    def build(self):
        # check data
        if not self.transform:
            raise mk.DeformerError('geometry missing')
        if not self.data['maps'] or not self.data['infs']:
            raise mk.DeformerError('influence missing')

        # get shape?
        if not self.geometry:
            self.find_geometry()

        # build joints
        joints = {}
        joints_bp = {}

        empty_maps = []
        for i in self.data['maps']:
            if isinstance(i, int) and not any(self.data['maps'][i].weights):
                empty_maps.append(i)
        for i in empty_maps:
            for k in ('maps', 'infs', 'bind_pose', 'bind_pose_root'):
                if k in self.data:
                    self.data[k].pop(i, None)

        ids = []
        for i in self.data['maps']:
            if isinstance(i, int):
                ids.append(i)
        ids.sort()
        remap_ids = {}
        for i, _id in enumerate(ids):
            remap_ids[_id] = i

        for i, m in zip(*self.get_indexed_maps()):
            if i not in self.data['infs']:
                self.log_warning('map {} has no influence specified'.format(i))
                del self.data['maps'][i]
                continue
            try:
                inf = self.get_node(self.data['infs'][i])
            except:
                self.log_error('influence "{}" does not exist, replacing with placeholder'.format(self.data['infs'][i]))
                _root_name = '__skin_placeholders__'
                _root = find_root().find(_root_name)
                if not _root:
                    _root = kl.SceneGraphNode(find_root(), _root_name)
                inf_name = self.data['infs'][i].split()[-1].replace('::', '_') + '_placeholder'
                inf = _root.find(inf_name)
                if not inf:
                    inf = kl.Joint(_root, inf_name)
                inf.name.set_value(inf.get_name())

            joints[i] = inf

            # bind pose
            if not isinstance(inf, kl.Joint):
                add_plug(inf, 'bind_pose', M44f)
            inf.bind_pose.set_value(inf.world_transform.get_value())

            bp_plug = inf.get_dynamic_plug('bind_poses')
            if not bp_plug:
                bp_plug = inf.add_dynamic_plug("bind_poses", M44f(), 1)
                bp_plug[0].set_value(inf.world_transform.get_value())

            nbp = bp_plug.get_size()
            bpid = nbp

            if 'bind_pose' in self.data and i in self.data['bind_pose']:
                bpm = self.get_node(self.data['bind_pose'][i])

                bp_plug.resize(nbp + 1)
                bp_plug[nbp].connect(bpm.world_transform)

            elif 'bind_pose_root' in self.data and i in self.data['bind_pose_root']:
                bpm_root = self.get_node(self.data['bind_pose_root'][i])
                offset = kl.SceneGraphNode(bpm_root, 'bpm_' + joints[i].get_name())
                offset.set_world_transform(joints[i].world_transform.get_value())

                mmx = kl.MultM44f(offset, '_mmx')
                mmx.input[0].connect(offset.transform)
                mmx.input[1].connect(bpm_root.world_transform)

                bp_plug.resize(nbp + 1)
                bp_plug[nbp].connect(mmx.output)

            else:
                bp = inf.world_transform.get_value()

                new_bp = True
                for bpid in range(nbp):
                    if bp_plug[bpid].get_value() == bp:
                        new_bp = False
                        break

                if new_bp:
                    bp_plug.resize(nbp + 1)
                    bpid = nbp

                    bp_plug[bpid].set_value(bp)

            joints_bp[i] = bp_plug[bpid]

        # insert deformer
        if self.data.get('dq', False):
            self.node = kl.DualQuatSkin(len(joints), self.geometry, 'dq_skin')

            world = self.data.get('dq_scale', mk.Nodes.get_id('::hook'))
            if world:
                non_rigid = kl.RigidM44f(self.node, 'non_rigid')
                non_rigid.input.connect(world.world_transform)
                self.node.world_non_rigid_in.connect(non_rigid.non_rigid)

        else:
            self.node = kl.Skin(len(joints), self.geometry, 'skin')

        for i, joint in joints.items():
            self.node.set_joint_at_index(joint, remap_ids[i], joints_bp.get(i))

        if isinstance(self.geometry, kl.SplineCurve):
            shp_out = self.geometry.spline_in.get_input()
            if shp_out:
                self.geometry.spline_in.disconnect(restore_default=True)
                self.node.spline_in.connect(shp_out)
                self.geometry.spline_in.connect(self.node.spline_out)
            else:
                self.node.spline_in.set_value(self.geometry.spline_in.get_value())
                self.geometry.spline_in.connect(self.node.spline_out)
        else:
            shp_out = self.geometry.mesh_in.get_input()
            self.geometry.mesh_in.disconnect(restore_default=True)
            self.node.mesh_in.connect(shp_out)
            self.geometry.mesh_in.connect(self.node.mesh_out)

        # relative
        if self.data['relative']:
            self.node.geom_world_transform.connect(self.transform.world_transform)
        else:
            self.node.geom_world_transform.set_value(self.transform.world_transform.get_value())

        # update i/o
        self.reorder()

        # update weights
        self.write()

    def update(self):
        name = Deformer.get_unique_name(self.transform, self.root)
        key = self.id
        raise mk.DeformerError('updating "{}->{}" is not possible'.format(name, key))

    def write(self):

        # load weights
        ids, maps = self.get_indexed_maps()
        size = len(maps[0].weights)

        _ids = []
        for i in ids:
            if any(self.data['maps'][i].weights):
                _ids.append(i)
        _ids.sort()

        remap_ids = {}
        for i, _id in enumerate(_ids):
            remap_ids[_id] = i

        # periodic spline fix?
        if isinstance(self.geometry, kl.SplineCurve):
            spline = self.node.spline_in.get_value()
            if spline.get_wrap():
                degree = spline.get_degree()
                size += degree
                for m in maps:
                    for i in range(degree):
                        m.weights.append(m.weights[i])

        # write
        offset = 0
        weights = []
        weights_offsets = []

        weight_list = []
        for i in range(size):
            vertex = []
            weight_list.append(vertex)

            for k, m in zip(ids, maps):
                v = m.weights[i]
                if v != 0:
                    vertex.append((remap_ids[k], v))

        for w in weight_list:
            weights_offsets.append(offset)

            for k, v in w:
                weights.append(v)  # weight
                weights.append(k)  # joint index
            offset += len(w)  # number of joints per vertex

        self.node.weights_in.set_value(weights)
        self.node.weights_offsets_in.set_value(weights_offsets)

        # dq?
        if self.data.get('dq', False):
            self.node.dqs_enable_in.set_value(1)

        dqmap = self.data['maps'].get('dq')
        if dqmap:
            if not any(dqmap.weights) and self.data.get('method') != 1:
                self.node.dqs_enable_in.set_value(0)
                return

            indices = []
            weights = []
            for i, w in enumerate(dqmap.weights):
                if w > 0:
                    indices.append(i)
                    weights.append(w)
            self.node.dqs_vertex_indices_in.set_value(indices)
            self.node.dqs_vertex_weights_in.set_value(weights)

    @staticmethod
    def hook(dfm, xfo, hook):

        if hook == 'enable' or hook == 'envelope':
            return dfm.enable_in

        if isinstance(dfm, kl.DualQuatSkin):
            if hook == 'dq_enable':
                return dfm.dqs_enable_in
