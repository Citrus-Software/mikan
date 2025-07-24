# coding: utf-8

from mikan.tangerine.lib.rig import axis_to_vector

import meta_nodal_py as kl
from meta_nodal_py.Imath import V3f

import mikan.tangerine.core as mk
from mikan.core.utils import flatten_list
from mikan.core.prefs import Prefs
from mikan.tangerine.lib.commands import add_plug
from mikan.tangerine.lib.connect import connect_mult
from mikan.tangerine.lib.rig import create_srt_out, create_srt_in, copy_transform
from mikan.tangerine.lib.nurbs import get_curve_length
from mikan.core.logger import create_logger

from mikan.tangerine.lib.connect import connect_expr

log = create_logger()


class Mod(mk.Mod):

    def run(self):

        legacy = Prefs.get('mod.path.legacy', 1)

        tpl = self.get_template()
        do_flip = False
        if self.data.get('flip', False):
            do_flip = tpl.do_flip()

        # get nodes
        nodes = self.data.get('nodes', self.data.get('node', self.node))
        nodes = [n for n in list(flatten_list([nodes])) if n]

        if legacy == 0:
            gem_id = mk.Nodes.get_node_id(self.node, 'skin')
            if '::skin' in gem_id:
                gem_id = gem_id.replace('::skin', '::roots')
                nodes = mk.Nodes.get_id(gem_id)
                nodes = list(flatten_list([nodes]))
            else:
                nodes = []

        if not nodes:
            raise mk.ModArgumentError('no nodes to attach to path')

        if 'geo' not in self.data:
            raise mk.ModArgumentError('geometry not defined')

        geo = self.data['geo']
        shp, xfo = None, None
        if isinstance(geo, (tuple, list)) and len(geo) == 2:
            shp, xfo = geo
        elif isinstance(geo, kl.SceneGraphNode):
            _ids = mk.Deformer.get_deformer_ids(geo)
            if 'shape' in _ids:
                shp = _ids['shape']
                xfo = geo

        if not isinstance(shp, kl.SplineCurve):
            raise mk.ModArgumentError('invalid geometry (must be a nurbs curve)')

        shp_up, xfo_up = self.data.get('geo_up', (None, None))
        if shp_up is not None and not isinstance(shp_up, kl.SplineCurve):
            raise mk.ModArgumentError('invalid up geometry (must be a nurbs curve)')

        closest = self.data.get('closest')
        if closest is not None and not isinstance(closest, kl.SceneGraphNode):
            raise mk.ModArgumentError('invalid node for closest projection')

        # args
        parent = self.data.get('parent', nodes[0].get_parent())

        do_hook = bool(self.data.get('hook', True))
        do_snap = bool(self.data.get('snap', False))
        do_orient = self.data.get('rotate', True) and self.data.get('orient', True)

        percent = bool(self.data.get('percent', False))

        length_mode = False
        if legacy == 0:
            length_mode = self.data.get('mode') != 'parametric'
        parametric = not self.data.get('length', length_mode)
        if closest:
            parametric = True

        io = bool(self.data.get('io', False))

        # update curve geometry
        for curve in [cv for cv in (shp, shp_up) if cv]:
            spline = curve.spline_in.get_value()
            sampling = 10 * (len(spline.get_control_points()) + 1) * (spline.get_degree() ** 2)
            curve.sampling_in.set_value(sampling)
            if sampling > 1000:
                curve.sampling_in.set_all_user_infos({"max": "20000"})

        # vectors
        fwd_vector = self.data.get('forward_vector', [1, 0, 0])
        if isinstance(fwd_vector, str):
            fwd_vector = axis_to_vector(fwd_vector)
        fwd_vector = V3f(*fwd_vector)

        _default = [0, 0, 0]
        if 'up_object_vector' in self.data or 'up_object' in self.data or shp_up:
            _default = [0, 1, 0]

        up_vector = self.data.get('up_vector', _default)
        if isinstance(up_vector, str):
            up_vector = axis_to_vector(up_vector)
        up_vector = V3f(*up_vector) if up_vector else V3f()

        up_object_vector = self.data.get('up_object_vector', [0, 0, 0])
        if isinstance(up_object_vector, str):
            up_object_vector = axis_to_vector(up_object_vector)
        up_object_vector = V3f(*up_object_vector) if up_object_vector else V3f()

        up_object = self.data.get('up_object')

        if do_flip:
            fwd_vector *= -1
            up_vector *= -1

        # path
        name = 'path_{}'.format(xfo.get_name())
        tpl = self.get_template()
        if tpl:
            name = 'path_{}'.format(tpl.name)

        # build loop
        for node in nodes:

            # get u
            u = self.data.get('u')
            if not isinstance(u, (float, int)):
                _closest = kl.Closest(node, 'closest')
                _closest.legacy.set_value(2)
                _closest.geom_world_transform_in.connect(xfo.world_transform)
                _closest.forward_vector_in.set_value(fwd_vector)
                _closest.up_vector_in.set_value(up_vector)
                _closest.spline_mesh_in.connect(shp.spline_mesh_out)
                _closest.spline_in.connect(shp.spline_in)
                if not parametric:
                    _closest.length_in.connect(shp.length_out)

                attach = self.data.get('attach', node)
                _closest.transform_in.connect(attach.world_transform)
                u = _closest.u_out.get_value()
                _closest.remove_from_parent()

            # build path locator
            if shp_up:
                up_object = Mod.create_path(
                    node, shp_up,
                    parent=parent, name=name.replace('path_', 'path_up_'), legacy=legacy,
                    u=u, parametric=parametric, percent=percent, io=io
                )

            path = Mod.create_path(
                node, shp,
                do_orient, parent, name, legacy,
                u, parametric, percent, io,
                fwd_vector, up_vector, up_object, up_object_vector,
                closest
            )

            if shp_up:
                up_object.u.connect(path.u)

            # hook
            if do_hook:
                node.reparent(path)

            # snap
            if do_snap:
                copy_transform(path, node)

            # register
            self.set_id(path, 'path', self.data.get('name'))
            if shp_up:
                self.set_id(path, 'path.root', self.data.get('name'))
                self.set_id(up_object, 'path.up', self.data.get('name'))

    @staticmethod
    def create_path(
            node, shp,
            do_orient=False, parent=None, name=None, legacy=1,
            u=0.0, parametric=True, percent=False, io=False,
            fwd_vector=None, up_vector=None, up_object=None, up_object_vector=None,
            closest=None
    ):
        # args
        xfo = shp.get_parent()

        if fwd_vector is None:
            fwd_vector = V3f()
        if up_vector is None:
            up_vector = V3f()
        if up_object_vector is None:
            up_object_vector = V3f()

        # path root
        path = kl.SceneGraphNode(parent, name)

        poc = kl.PointOnSplineCurve(path, 'poc')
        poc.geom_world_transform_in.connect(xfo.world_transform)
        poc.spline_in.connect(shp.spline_in)
        poc.spline_mesh_in.connect(shp.spline_mesh_out)

        if io:
            parametric = False

        if isinstance(closest, kl.SceneGraphNode):
            closest_xfo = closest
            closest = kl.Closest(path, 'closest')
            closest.geom_world_transform_in.connect(xfo.world_transform)
            closest.forward_vector_in.set_value(fwd_vector)
            closest.up_vector_in.set_value(up_vector)
            closest.spline_mesh_in.connect(shp.spline_mesh_out)
            closest.spline_in.connect(shp.spline_in)

            closest.transform_in.connect(closest_xfo.world_transform)
            poc.u_in.connect(closest.u_out)

        else:
            spline = shp.spline_in.get_value()
            max_u = spline.get_max_u()
            if not parametric:
                max_u = 1

            if legacy == 0:
                plug = add_plug(node, 'u', float, k=True, min_value=0, max_value=max_u)
            else:
                plug = add_plug(path, 'u', float, k=True, min_value=0, max_value=max_u)

            # length ratio mode
            if not parametric:
                poc.length_in.connect(shp.length_out)
                poc.length_ratio_in.connect(plug)

                len_max = shp.length_out.get_value()
                len_u = get_curve_length(shp, u)

                _u = len_u / len_max if len_max != 0 else 0
                plug.set_value(_u)

            # parametric mode
            else:
                if percent:
                    connect_mult(plug, max_u, poc.u_in)
                    u /= max_u
                else:
                    poc.u_in.connect(plug)
                plug.set_value(u)

        # local aim target
        _imx = kl.InverseM44f(path, '_imx')
        _imx.input.connect(path.parent_world_transform)
        _mmx = kl.MultM44f(path, '_mmx')
        _mmx.input[0].connect(poc.transform_out)
        _mmx.input[1].connect(_imx.output)

        local_xfo = _mmx

        # point only
        if not do_orient:
            _srt_mmx = create_srt_out(_mmx)

            _srt_path = create_srt_in(path)
            _srt_path.translate.connect(_srt_mmx.translate)

        # rotation
        else:

            # basic setup
            aim = kl.AimConstrain(path, 'aim')
            aim.aim_vector.set_value(fwd_vector)
            aim.up_vector.set_value(up_vector)

            # override    
            aim.input_transform.connect(_mmx.output)
            aim.parent_world_transform.connect(path.parent_world_transform)

            # world
            if not up_object_vector.length() or up_object:
                aim.input_world.connect(path.parent_world_transform)

            # aim target
            _mmx = kl.MultM44f(aim, '_mmx')
            _mmx.input[0].connect(poc.transform_out)

            _srt = kl.SRTToTransformNode(aim, '_tan')
            _srt.translate.connect(poc.tangent_out)
            _mmx.input[1].connect(_srt.transform)

            aim.input_target_world_transform.connect(_mmx.output)

            # out    
            _extract_TR_in = kl.TransformToSRTNode(path, 'aim_extract_TR_in')
            _extract_TR_in.transform.connect(aim.constrain_transform)

            _extract_TR_out = kl.SRTToTransformNode(path, 'aim_extract_TR_out')
            _extract_TR_out.translate.connect(_extract_TR_in.translate)
            _extract_TR_out.rotate.connect(_extract_TR_in.rotate)

            path.transform.connect(_extract_TR_out.transform)

            # up target
            if isinstance(up_object, kl.Node):

                # object rotation up
                if up_object_vector.length():
                    aim.up_vector_in_space.set_value(up_object_vector)
                    aim.up_vector_space.connect(up_object.world_transform)

                # object up
                else:
                    # local position
                    _srt_xfo = kl.TransformToSRTNode(aim, '_srt_xfo')
                    _srt_xfo.transform.connect(local_xfo.output)

                    # local up position
                    _mmx = kl.MultM44f(aim, '_mmx')
                    _mmx.input[0].connect(up_object.world_transform)
                    _imx = kl.InverseM44f(aim, '_imx')
                    _imx.input.connect(path.parent_world_transform)
                    _mmx.input[1].connect(_imx.output)

                    _srt_up = kl.TransformToSRTNode(aim, '_srt_up')
                    _srt_up.transform.connect(_mmx.output)

                    # compute local up vector
                    _neg = kl.ScaleV3f(_srt_xfo, '_neg')
                    _neg.vector_in.connect(_srt_xfo.translate)
                    _neg.scalar_in.set_value(-1)

                    _add = kl.AddV3f(_srt_up, '_add')
                    _add.input1.connect(_srt_up.translate)
                    _add.input2.connect(_neg.vector_out)

                    aim.up_vector_world.connect(_add.output)

            else:
                # vector
                aim.up_vector_world.set_value(up_object_vector)

        # locator shape
        gen = kl.CrossShapeTool(path, 'locator')
        gen.size_in.set_value(1)

        loc = kl.Geometry(path, 'shape')
        loc.mesh_in.connect(gen.mesh_out)
        loc.show.set_value(False)

        # length out
        add_plug(path, 'length', float, keyable=0)
        add_plug(path, 'length0', float, keyable=0)
        path.length.connect(shp.length_out)
        path.length0.set_value(shp.length_out.get_value())

        if io:
            add_plug(path, 'scale_distance_base', float, keyable=1)
            add_plug(path, 'u_parametric_base', float, keyable=0)
            add_plug(path, 'offset', float, keyable=1)
            add_plug(path, 'loop', bool, keyable=1)
            path.scale_distance_base.set_value(1)
            path.u_parametric_base.set_value(u)
            path.offset.set_value(0)
            path.loop.set_value(False)

            u_base = path.u
            u_curve_max = shp.spline_in.get_value().get_max_u()
            length_curve = shp.length_out
            length_curve_base_init = shp.length_out.get_value()

            _srt_extract_scale = kl.TransformToSRTNode(path, '_srt_extract_scale')
            _srt_extract_scale.transform.connect(path.parent_world_transform)
            _s_extract_axe = kl.V3fToFloat(path, '_s_extract_axe')
            _s_extract_axe.vector.connect(_srt_extract_scale.scale)
            global_scale = _s_extract_axe.x

            length_curve_base = connect_expr(
                'length_curve_base_init * global_scale',
                length_curve_base_init=length_curve_base_init,
                global_scale=global_scale)

            length_base = connect_expr(
                'u_base * length_curve_base',
                u_base=u_base,
                length_curve_base=length_curve_base)

            u_slide_keep_distance_start_base = connect_expr(
                '(length_base / length_curve * scale_distance_base + offset )',
                length_base=length_base,
                length_curve=length_curve,
                scale_distance_base=path.scale_distance_base,
                offset=path.offset)

            u_slide_keep_distance_start = connect_expr(
                'base % 1 * loop + clamp(base,0,1) * (1-loop)',
                base=u_slide_keep_distance_start_base,
                loop=path.loop)

            u_slide_keep_distance_end_base = connect_expr(
                '(1 - (length_curve_base - length_base) / length_curve * scale_distance_base) + offset',
                length_base=length_base,
                length_curve=length_curve,
                length_curve_base=length_curve_base,
                scale_distance_base=path.scale_distance_base,
                offset=path.offset)

            u_slide_keep_distance_end = connect_expr(
                'base % 1 * loop + clamp(base,0,1) * (1-loop)',
                base=u_slide_keep_distance_end_base,
                loop=path.loop)

            u_slide_stretch_base = connect_expr(
                '(length_base / length_curve_base + offset )',
                length_base=length_base,
                length_curve=length_curve,
                length_curve_base=length_curve_base,
                offset=path.offset)

            u_slide_stretch = connect_expr(
                'base % 1 * loop + clamp(base,0,1) * (1-loop)',
                base=u_slide_stretch_base,
                loop=path.loop)

            sliding_behaviors = [
                'parametric',
                'slide_stretch',
                'slide_keep_distance_start',
                'slide_keep_distance_end']

            add_plug(path, 'sliding_behavior', int, default_value=1, enum=sliding_behaviors)

            choice_out = connect_expr(
                'switch(trigger, u_base, u_slide_stretch, u_slide_keep_distance_start, u_slide_keep_distance_end)',
                trigger=path.sliding_behavior,
                u_base=path.u_parametric_base,
                u_slide_stretch=u_slide_stretch,
                u_slide_keep_distance_start=u_slide_keep_distance_start,
                u_slide_keep_distance_end=u_slide_keep_distance_end)

            poc.u_in.connect(choice_out)
            poc.length_ratio_in.connect(choice_out)

            # switch btw parametric and others
            choice_out = connect_expr(
                'switch(trigger, u_base, u_slide_stretch, u_slide_keep_distance_start, u_slide_keep_distance_end)',
                trigger=path.sliding_behavior,
                u_base=0,  # parametric if length == 0
                u_slide_stretch=shp.length_out,
                u_slide_keep_distance_start=shp.length_out,
                u_slide_keep_distance_end=shp.length_out)

            poc.length_in.connect(choice_out)  # this attr determine in the node the switch btw parametric and others

        # exit
        return path
