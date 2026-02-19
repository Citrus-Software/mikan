# coding: utf-8

import meta_nodal_py as kl
from meta_nodal_py.Imath import V3f, M44f, Euler

import mikan.tangerine.core as mk
from mikan.tangerine.lib.rig import merge_transform, connect_expr, connect_reverse, add_plug
from mikan.core.logger import create_logger
from mikan.core import cleanup_str

log = create_logger()


class Mod(mk.Mod):

    def run(self):
        # args
        node = self.data.get('node', self.node)
        parent = self.data.get('parent', node.get_parent())
        do_hook = bool(self.data.get('hook', True))

        closest_node = self.data.get('closest')
        do_closest = bool(closest_node)
        if do_closest and not isinstance(closest_node, kl.Node):
            closest_node = node
            do_hook = False
        if do_closest and not isinstance(closest_node, kl.SceneGraphNode):
            raise mk.ModArgumentError('invalid closest node')

        keepout_node = self.data.get('keepout')
        do_keepout = bool(keepout_node)
        if do_keepout and not isinstance(keepout_node, kl.Node):
            keepout_node = node
            do_hook = False
        if do_keepout and not isinstance(keepout_node, kl.SceneGraphNode):
            raise mk.ModArgumentError('invalid keepout node')

        if do_keepout:
            do_closest = True
            closest_node = keepout_node
        if not do_closest:
            closest_node = node

        default_orient = True
        if do_closest:
            default_orient = False
        do_orient = self.data.get('orient', self.data.get('orient', default_orient))

        if 'geo' not in self.data:
            raise mk.ModArgumentError('geometry not defined')

        shp, xfo = self.data['geo']
        shp_output = mk.Deformer.get_deformer_output(shp, xfo)

        for v in xfo.transform.get_value().scaling():
            if round(v, 3) != 1:
                self.log_warning('geometry scale is not frozen')
                break

        do_subdiv = 0
        if 'subdiv' in self.data:
            do_subdiv = self.data['subdiv']
            do_subdiv = do_subdiv if isinstance(do_subdiv, int) else int(bool(do_subdiv))

        # connect subdiv
        if do_subdiv:
            subdiv = None

            # look for subdivided geometry
            for s in shp_output.get_outputs():
                _s = s.get_node()
                if isinstance(_s, kl.SubdivMesh):
                    subdiv = _s
                    break

            # build new subdiv if none
            if subdiv is None:
                subdiv = kl.SubdivMesh(shp, 'subdiv')
                subdiv.level.set_value(do_subdiv)

                ids = mk.Deformer.get_deformer_ids(xfo)
                if 'source' not in ids or not isinstance(ids['source'], kl.Node):
                    self.log_error('abc reader is needed for subdiv node')
                reader_output = mk.Deformer.get_deformer_output(ids['source'], xfo)
                subdiv.static_mesh_in.connect(reader_output)

                subdiv.animated_mesh_in.connect(shp_output)

            shp_output = subdiv.mesh_out

        # build
        name = f'rvt_{xfo.get_name().split(":")[-1]}'
        if 'name' in self.data:
            name += '_' + cleanup_str(self.data['name'])
        else:
            tpl = self.get_template()
            if tpl:
                name += f'_{tpl.name}'
            else:
                name += f'_{node.get_name()}'

        rvt = kl.SceneGraphNode(parent, name)

        # add subdiv level attribute
        if do_subdiv:
            add_plug(rvt, 'level', int, min_value=0, max_value=3, keyable=True)
            rvt.level.set_value(subdiv.level.get_value())

            input_level = subdiv.level.get_input()
            if kl.is_plug(input_level):
                connect_expr('level = max(a, b)', level=subdiv.level, a=rvt.level, b=input_level)
            else:
                subdiv.level.connect(rvt.level)

        # projection
        _cp = kl.Closest(node, 'closest')
        _cp.legacy.set_value(2)
        _cp.spline_mesh_in.connect(shp_output)
        _cp.geom_world_transform_in.connect(xfo.world_transform)

        if 'raycast' in self.data:
            _t = self.data['raycast']
            _cp.transform_in.set_value(M44f(V3f(_t[0], _t[1], _t[2]), V3f(0, 0, 0), V3f(1, 1, 1), Euler.XYZ))
        else:
            _cp.transform_in.connect(closest_node.world_transform)

        uv = _cp.coords_out.get_value()

        if not uv:
            rvt.remove_from_parent()
            _cp.remove_from_parent()
            raise mk.ModArgumentError('failed to retrieve UVs from geometry')

        uv_xfo = kl.MeshCoordsToTransform(rvt, '_uv_xfo')
        uv_xfo.legacy.set_value(1)
        if not do_closest:
            uv_xfo.coords_in.set_value(uv)
            _cp.remove_from_parent()
        else:
            uv_xfo.coords_in.connect(_cp.coords_out)

        uv_xfo.spline_mesh_in.connect(shp_output)
        uv_xfo.geom_world_transform_in.connect(xfo.world_transform)
        uv_xfo.forward_vector_in.set_value(V3f(0, 1, 0))

        _imx = kl.InverseM44f(rvt, '_imx')
        _imx.input.connect(rvt.parent_world_transform)

        _mmx = kl.MultM44f(rvt, '_mmx')
        _mmx.input[0].connect(uv_xfo.transform_out)
        _mmx.input[1].connect(_imx.output)

        xfo_out = _mmx.output

        # connect
        t_in = xfo_out
        r_in = None

        if do_closest:
            _normal = kl.MultDir(rvt, '_normal')
            _normal.rotate_only_in.set_value(True)
            _normal.dir_in.set_value(V3f(0, 1, 0))
            _normal.matrix_in.connect(uv_xfo.transform_out)
            _normal_xfo = kl.SRTToTransformNode(_normal, '_normal')
            _normal_xfo.translate.connect(_normal.dir_out)

            # compute local aim
            if do_orient:
                aim = kl.AimConstrain(rvt, 'aim')
                aim.aim_vector.set_value(V3f(0, 1, 0))
                aim.up_vector.set_value(V3f(0, 0, 0))

                # world ref
                aim.input_world.connect(rvt.parent_world_transform)

                # origin, closest position
                aim.input_transform.connect(uv_xfo.transform_out)
                aim.initial_input_transform.set_value(uv_xfo.transform_out.get_value())

                # target, extract normal from uv_xfo
                _mmx_up = kl.MultM44f(aim, '_mmx')
                _mmx_up.input[0].connect(uv_xfo.transform_out)
                _mmx_up.input[1].connect(_normal_xfo.transform)

                aim.input_target_world_transform.connect(_mmx_up.output)

                r_in = aim.constrain_transform

            if do_keepout:
                # build xfo switch
                _rvt_pos = kl.TransformToSRTNode(uv_xfo, '_srt')
                _rvt_pos.transform.connect(uv_xfo.transform_out)

                _proj_pos = kl.TransformToSRTNode(closest_node, '_srt_world')
                _proj_pos.transform.connect(closest_node.world_transform)

                nv = kl.ScaleV3f(uv_xfo, '_nvector')
                nv.vector_in.connect(_rvt_pos.translate)
                nv.scalar_in.set_value(-1)

                proj = kl.AddV3f(uv_xfo, 'projection')
                proj.input1.connect(nv.vector_out)
                proj.input2.connect(_proj_pos.translate)

                _dot = kl.Dot(uv_xfo, '_dot')
                _dot.input1.connect(proj.output)
                _dot.input2.connect(_normal.dir_out)

                _mmx = kl.MultM44f(rvt, '_mmx')
                _mmx.input[0].connect(closest_node.world_transform)
                _mmx.input[1].connect(_imx.output)

                _blend = kl.BlendWeightedTransforms(2, rvt, '_blend')

                _blend.transform_in[0].connect(_mmx.output)
                _blend.transform_in[1].connect(xfo_out)

                connect_expr('w = dot >=0 ? 1 : 0', dot=_dot.output, w=_blend.weight_in[0])
                w = _blend.weight_in[0].get_input()
                # _blend.weight_in[0].connect(w)  # WTF??
                connect_reverse(w, _blend.weight_in[1])

                t_in = _blend.transform_out

        else:
            t_in = xfo_out
            if do_orient:
                r_in = xfo_out

        # rivet output
        merge_transform(rvt, t_in=t_in, r_in=r_in, override=True)

        # hook
        if do_hook:
            node.reparent(rvt)

        self.set_id(rvt, 'rivet', self.data.get('name'))
