# coding: utf-8

import meta_nodal_py as kl

import mikan.tangerine.core as mk
from mikan.core.logger import create_logger
from mikan.tangerine.lib.commands import add_plug

log = create_logger()


class Deformer(mk.Deformer):
    node_class = kl.FreeForm

    def build(self, data=None):

        # check data
        if not self.transform:
            raise mk.DeformerError('geometry missing')
        if not self.data['lattice']:
            raise mk.DeformerError('base missing')

        # get shape
        if not self.geometry:
            self.find_geometry()

        # get ffd data
        ffl = self.data.get('lattice')
        if isinstance(ffl, tuple):
            ffl = ffl[1]
        if isinstance(ffl, str):
            _, ffl = self.get_geometry_id(self.data['lattice'])

        ffb = self.data.get('base')
        if isinstance(ffb, tuple):
            ffb = ffb[1]
        if isinstance(ffb, str):
            _, ffb = self.get_geometry_id(self.data['base'])

        ffl_ids = self.get_deformer_ids(ffl) if ffl else {}
        for key, node in ffl_ids.items():
            if 'data.' in key:
                node.show.set_value(False)

        ffb_ids = self.get_deformer_ids(ffb) if ffb else {}
        for key, node in ffb_ids.items():
            if 'data.' in key:
                node.show.set_value(False)

        # build rig
        lattice = None
        if not lattice:
            lattice = ffl.find('geometry')
            lattice_gen = ffl.find('lattice')

        if not lattice:
            lattice = kl.Geometry(ffl, 'geometry')
            lattice.show.set_value(1)

            lattice_gen = kl.Lattice(lattice.get_parent(), 'lattice')
            lattice_gen.x_steps_in.set_value(self.data['stu'][0])
            lattice_gen.y_steps_in.set_value(self.data['stu'][1])
            lattice_gen.z_steps_in.set_value(self.data['stu'][2])
            lattice.mesh_in.connect(lattice_gen.mesh_out)

            # tweak
            if 'data.tweak' in ffl_ids:
                bs = kl.BlendShape(1, lattice, 'tweak')
                lattice.mesh_in.connect(bs.mesh_out)
                bs.mesh_in.connect(lattice_gen.mesh_out)

                bs.add_dynamic_plug('w0', 1.0)
                bs.set_shape_at_index(ffl_ids['data.tweak'], 'w0', 0)

        base_lattice = None
        if not base_lattice:
            base_lattice = ffb.find('base_lattice')

        if not base_lattice:
            base_lattice = kl.Geometry(ffb, 'base_lattice')
            base_lattice.mesh_in.connect(lattice_gen.mesh_out)
            base_lattice.show.set_value(0)

        # deformer
        self.node = kl.FreeForm(self.geometry, 'ffd')

        self.node.mesh_world_transform_in.connect(self.transform.world_transform)
        self.node.cage_in.connect(lattice.mesh_in)
        self.node.cage_world_transform_in.connect(ffl.world_transform)

        self.node.bind_cage_in.connect(base_lattice.mesh_in)
        self.node.bind_cage_world_transform_in.connect(ffb.world_transform)

        # solver
        solver = kl.LatticeWeightSolver(self.node, 'weight_solver')
        solver.x_steps_in.connect(lattice_gen.x_steps_in)
        solver.y_steps_in.connect(lattice_gen.y_steps_in)
        solver.z_steps_in.connect(lattice_gen.z_steps_in)

        solver.x_influences_in.set_value(self.data['local_stu'][0])
        solver.y_influences_in.set_value(self.data['local_stu'][1])
        solver.z_influences_in.set_value(self.data['local_stu'][2])

        solver.local_in.set_value(self.data['local'])
        solver.lattice_world_transform_in.connect(ffb.world_transform)

        if self.data['outside'] >= 1:
            if self.data['outside'] == 1:
                solver.falloff_in.set_value(-1)
            else:
                solver.falloff_in.set_value(self.data['falloff'])

        if isinstance(self.geometry, kl.SplineCurve):
            solver.spline_in.connect(self.node.spline_in)
        elif isinstance(self.geometry, kl.Geometry):
            solver.mesh_in.connect(self.node.mesh_in)

        self.node.cage_weights_in.connect(solver.cage_weights_out)
        solver.mesh_world_transform_in.connect(self.geometry.world_transform)

        # insert
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

        # connect global envelope
        if not ffl.get_dynamic_plug('enable_all'):
            add_plug(ffl, 'enable_all', float, keyable=True, default_value=1, min_value=0, max_value=1)
        self.node.enable_in.connect(ffl.enable_all)

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

        wm = self.data['maps'][0].weights
        # n = self.get_size()
        # if len(wm) != n:
        #     log.warning('/!\\ weightmap error: bad length -> fixed')
        #     if len(wm) > n:
        #         wm = wm[:n]
        #     else:
        #         wm = wm + [0.0] * (n - len(wm))

        do = False
        for w in wm:
            if w < 1:
                do = True
                break
        if not do:
            log.debug('weightmap is not needed')
            return

        for idx, w in enumerate(wm):
            if w > 0:
                vtx_indices.append(idx)
                vtx_weights.append(w)

        self.node.vertex_indices_in.set_value(vtx_indices)
        self.node.vertex_weights_in.set_value(vtx_weights)

    @staticmethod
    def hook(ffd, xfo, hook):

        if hook == 'enable' or hook == 'envelope':
            # find lattice
            lattice = ffd.cage_in.get_input()
            if lattice:
                lattice = lattice.get_node().get_parent()

            # find global envelope
            if lattice and lattice.get_dynamic_plug('enable_all'):
                return lattice.enable_all
            else:
                return ffd.enable_in
