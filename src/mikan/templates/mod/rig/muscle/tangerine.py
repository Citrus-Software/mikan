# coding: utf-8

import meta_nodal_py as kl

from mikan.core.logger import create_logger
import mikan.tangerine.core as mk
from mikan.core import flatten_list, cleanup_str
from mikan.tangerine.lib.commands import *
from mikan.tangerine.lib.rig import *
from mikan.tangerine.lib.connect import connect_expr, blend_smooth_weights
from mikan.tangerine.lib.nurbs import create_path, get_closest_point_on_curve

log = create_logger()


class Mod(mk.Mod):

    def run(self):

        do_orient = self.data.get('orient', True)
        do_scale = self.data.get('scale', True)
        do_squash = 'squash' in self.data
        do_weight = 'weight' in self.data
        do_shear = 'shear' in self.data

        # get nodes
        nodes = self.data.get('nodes', self.data.get('node', self.node))
        nodes = [n for n in list(flatten_list([nodes])) if n]

        parent = nodes[0].get_parent()
        if 'parent' in self.data:
            parent = self.data['parent']

        do_hook = bool(self.data.get('hook', False))

        # targets
        if 'targets' not in self.data:
            raise mk.ModArgumentError('no targets defined')

        targets = list(flatten_list(self.data['targets']))
        if len(targets) < 2:
            raise mk.ModArgumentError('/!\\ invalid targets')

        # name
        target_names = list()
        for t in self.data['targets']:
            target_names.append(t.get_name())

        name = '_'.join(map(str, target_names))
        if 'name' in self.data:
            name = cleanup_str(self.data['name'])

        # muscle spline
        if len(targets) > 2:
            path = create_path(targets, d=2, parent=parent)
            path.rename('mu_cv_' + name)

            path_shape = None
            for node in path.get_children():
                if isinstance(node, kl.SplineCurve):
                    path_shape = node
                    break

            # update curve geometry
            spline = path_shape.spline_in.get_value()
            sampling = 10 * (len(spline.get_control_points()) + 1) * (spline.get_degree() ** 2)
            path_shape.sampling_in.set_value(sampling)
            if sampling > 1000:
                path_shape.sampling_in.set_all_user_infos({"max": "20000"})

        # tendons rig
        tdata = [{} for _ in range(len(targets))]
        root = kl.Node(parent, '_muscle_{}'.format(name))

        dummy = kl.SceneGraphNode(parent, 'dummy_muscle')
        if len(targets) > 2:
            dummy_tangent = kl.SceneGraphNode(parent, 'dummy_tangent')
            dummy_poc = kl.PointOnSplineCurve(dummy, 'poc')
            dummy_poc.geom_world_transform_in.connect(path.world_transform)
            dummy_poc.spline_in.connect(path_shape.spline_in)
            dummy_poc.spline_mesh_in.connect(path_shape.spline_mesh_out)

        for i, tgt in enumerate(targets):
            if len(targets) == 2:
                copy_transform(targets, dummy, t=1)

                _aim = aim_constraint(targets[1], dummy, aim_vector=[0, 1, 0], up_vector=[0, 0, 0])
                _xfo = dummy.transform.get_value()
                _aim.remove_from_parent()
                dummy.transform.set_value(_xfo)

                copy_transform(tgt, dummy, t=1)
            else:
                u_in = get_closest_point_on_curve(path_shape, tgt, parametric=True)
                dummy_poc.u_in.set_value(u_in)

                _xfo = dummy_poc.transform_out.get_value()
                dummy.transform.set_value(_xfo)

                _t = dummy_poc.tangent_out.get_value() + _xfo.translation()
                _xfo.setTranslation(_t)
                dummy_tangent.transform.set_value(_xfo)

                _aim = aim_constraint(dummy_tangent, dummy, aim_vector=[0, 1, 0], up_vector=[0, 0, 0])
                _xfo = dummy.transform.get_value()
                _aim.remove_from_parent()
                dummy.transform.set_value(_xfo)

            mmx = kl.MultM44f(root, '_mmx', 3)

            omx = dummy.world_transform.get_value() * tgt.world_transform.get_value().inverse()
            mmx.input[0].set_value(omx)

            mmx.input[1].connect(tgt.world_transform)

            imx = kl.InverseM44f(root, '_imx')
            imx.input.connect(parent.world_transform)
            mmx.input[2].connect(imx.output)

            srt = create_srt_out(mmx.output, vectors=False)

            tdata[i]['xfo'] = mmx.output
            tdata[i]['pos'] = srt.translate

            if not do_orient or not do_scale:
                xfo = kl.SRTToTransformNode(root, '_xfo')

                xfo.translate.connect(srt.translate)
                if do_orient:
                    xfo.rotate.connect(srt.rotate)
                    xfo.rotate_order.connect(srt.rotate_order)
                else:
                    xfo.rotate.set_value(srt.rotate.get_value())
                    xfo.rotate_order.set_value(srt.rotate_order.get_value())
                if do_scale:
                    xfo.scale.connect(srt.scale)
                    xfo.shear.connect(srt.shear)
                else:
                    xfo.scale.set_value(srt.scale.get_value())
                    xfo.shear.set_value(srt.shear.get_value())

                tdata[i]['xfo'] = xfo.transform

            # extract vectors
            tdata[i]['x'] = connect_expr('t * [1,0,0]', t=tdata[i]['xfo'])
            tdata[i]['z'] = connect_expr('t * [0,0,1]', t=tdata[i]['xfo'])

        dummy.remove_from_parent()
        if len(targets) > 2:
            dummy_tangent.remove_from_parent()
            dummy_poc.remove_from_parent()

        # stretch
        if len(targets) == 2:
            db = kl.Distance(root, '_len')
            db.input1.connect(tdata[0]['pos'])
            db.input2.connect(tdata[1]['pos'])
            stretch_op = connect_expr('d/value(d)', d=db.output)
        else:
            stretch_op = connect_expr('d/value(d)', d=path_shape.length_out)

        # muscle loop
        for i, node in enumerate(nodes):
            mdata = [{} for _ in range(len(targets))]

            # muscle
            mu = kl.SceneGraphNode(parent, 'mu_{}'.format(name))
            if i == 0:
                root.set_parent(mu)

            copy_transform(targets, mu, t=1)
            _aim = aim_constraint(targets[1], mu, aim_vector=[0, 1, 0], up_vector=[0, 0, 0])

            _xfo = mu.transform.get_value()
            _aim.remove_from_parent()
            mu.transform.set_value(_xfo)

            # weight
            if len(targets) == 2:
                p0 = tdata[0]['pos'].get_value()
                p1 = tdata[1]['pos'].get_value()
                p2 = node.transform.get_value().translation()
                r = (p2 - p1).length() / (p2 - p0).length()

                add_plug(mu, 'slide', float, min_value=0, max_value=1, keyable=True)
                mu.slide.set_value(r / (r + 1))

                mdata[0]['w'] = mu.slide
                mdata[1]['w'] = connect_expr('lerp(1,0,w)', w=mu.slide)

            else:
                blend_smooth_weights(mu, len(targets))
                for j in range(len(targets)):
                    mdata[j]['w'] = mu.get_dynamic_plug('w{}'.format(j))

                add_plug(mu, 'slide', float, min_value=0, max_value=1, keyable=True)
                slide = get_closest_point_on_curve(path_shape, node, length=True)
                mu.slide.set_value(slide)

                u = get_closest_point_on_curve(path_shape, node, parametric=True)
                mu.u.set_value(u)

            # rig
            for j in range(len(targets)):
                mdata[j]['t'] = connect_expr('w * t', w=mdata[j]['w'], t=tdata[j]['pos'])
                mdata[j]['x'] = connect_expr('w * x', w=mdata[j]['w'], x=tdata[j]['x'])
                mdata[j]['z'] = connect_expr('w * z', w=mdata[j]['w'], z=tdata[j]['z'])

            # stretch axis
            add_plug(mu, 'stretch', float, min_value=0, max_value=1, default_value=1)
            stretch = connect_expr('lerp(1, div, w)', div=stretch_op, w=mu.stretch)

            if len(targets) == 2:
                muy = connect_expr('norm(p1 - p0)', p0=tdata[0]['pos'], p1=tdata[1]['pos'])
                mut = connect_expr('wt0 + wt1', wt0=mdata[0]['t'], wt1=mdata[1]['t'])
            else:
                poc = kl.PointOnSplineCurve(root, '_mu_poc')
                poc.geom_world_transform_in.connect(path.world_transform)
                poc.spline_in.connect(path_shape.spline_in)
                poc.spline_mesh_in.connect(path_shape.spline_mesh_out)

                poc.length_in.connect(path_shape.length_out)
                poc.length_ratio_in.connect(mu.slide)
                # poc.u_in.connect(mu.u)
                muy = poc.tangent_out

                _srt = create_srt_out(poc, vectors=False)
                mut = _srt.translate

            muy = connect_expr('y * stretch', y=muy, stretch=stretch)

            # squash axis 1
            _add = kl.AddV3f(root, '_add_x')
            if len(targets) > 2:
                _add.add_inputs(len(targets) - 2)

            for j in range(len(targets)):
                _add.get_plug(f'input{j + 1}').connect(mdata[j]['x'])

            mux = _add.output
            if not do_scale:
                mux = connect_expr('norm(v)', v=mux)

            # squash axis 2
            _add = kl.AddV3f(root, '_add_z')
            if len(targets) > 2:
                _add.add_inputs(len(targets) - 2)

            for j in range(len(targets)):
                _add.get_plug(f'input{j + 1}').connect(mdata[j]['z'])

            muz = _add.output
            if not do_scale:
                muz = connect_expr('norm(v)', v=muz)

            # unshear rig
            if do_shear:
                add_plug(mu, 'shearing', float, keyable=True, min_value=0, max_value=1, default_value=1)
                mux = connect_expr('lerp(norm(y^z), x, sh)', x=mux, y=muy, z=muz, sh=mu.shearing)
                muz = connect_expr('lerp(norm(x^y), z, sh)', x=mux, y=muy, z=muz, sh=mu.shearing)

            # squash weight
            if do_squash:
                add_plug(mu, 'squash', float, min_value=0, max_value=1, default_value=0)
                add_plug(mu, 'exponent', float, max_value=0, min_value=-2, default_value=-0.5)
                squash = connect_expr('lerp(1, div^rate, w)', div=stretch_op, rate=mu.exponent, w=mu.squash)

                mux = connect_expr('sq*x', x=mux, sq=squash)
                muz = connect_expr('sq*z', z=muz, sq=squash)

            # ijk transform
            ijk = connect_expr('matrix(x, y, z, t)', x=mux, y=muy, z=muz, t=mut)

            # weight rig
            if do_weight:
                add_plug(mu, 'weight', float, keyable=True, min_value=0, max_value=1, default_value=1)

                blend = kl.BlendWeightedTransforms(2, mu, '_bmx')
                blend.transform_interp_in.set_value(False)

                blend.transform_in[0].set_value(ijk.get_value())
                connect_expr('b = 1-w', b=blend.weight_in[0], w=mu.weight)

                blend.transform_in[1].connect(ijk)
                blend.weight_in[1].connect(mu.weight)
                mu.transform.connect(blend.transform_out)
            else:
                mu.transform.connect(ijk)

            # stretch settings
            mu.stretch.set_value(self.data.get('stretch', 1))
            if do_weight:
                mu.weight.set_value(self.data.get('weight', 1))
            if do_shear:
                mu.shearing.set_value(self.data.get('shear', 1))
            if do_squash:
                mu.squash.set_value(self.data.get('squash', 0))

            # do hook?
            if do_hook:
                matrix_constraint(mu, node)
            else:
                node.reparent(mu)

            self.set_id(mu, 'muscle')
