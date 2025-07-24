# coding: utf-8

from mikan.maya import cmds as mc
import mikan.maya.cmdx as mx

from mikan.core.logger import create_logger
import mikan.maya.core as mk

from mikan.core import flatten_list, cleanup_str
from mikan.maya.lib.connect import connect_matrix, connect_expr, blend_smooth_weights
from mikan.maya.lib.rig import matrix_constraint, copy_transform
from mikan.maya.lib.nurbs import create_path, get_closest_point_on_curve

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

        parent = nodes[0].parent()
        if 'parent' in self.data:
            parent = self.data['parent']

        do_hook = bool(self.data.get('hook', False))

        # targets
        if 'targets' not in self.data:
            raise mk.ModArgumentError('no targets defined')

        targets = list(flatten_list(self.data['targets']))
        if len(targets) < 2:
            raise mk.ModArgumentError('invalid targets')

        # name
        name = '_'.join(map(str, targets))
        if 'name' in self.data:
            name = cleanup_str(self.data['name'])

        # muscle spline
        if len(targets) > 2:
            path = create_path(targets, d=2)
            mc.parent(str(path), str(parent), r=1)
            mc.rename(str(path), 'mu_cv_' + name)
            path_shape = path.shape()

        # tendons rig
        tdata = [{} for _ in range(len(targets))]

        dummy = mx.create_node('transform', parent=parent, name='dummy')
        if len(targets) > 2:
            dummy_tangent = mx.create_node('transform', parent=parent, name='dummy_tangent')
            dummy_poc = mx.create_node(mx.tPointOnCurveInfo)
            path_shape['local'] >> dummy_poc['inputCurve']

        for i, tgt in enumerate(targets):
            if len(targets) == 2:
                copy_transform(targets[0], dummy, t=1)
                mc.delete(mx.cmd(mc.aimConstraint, targets[1], dummy, aim=[0, 1, 0], u=[0, 0, 0], wut='None'))
                copy_transform(tgt, dummy, t=1)
            else:
                dummy_poc['parameter'] = get_closest_point_on_curve(path, tgt, parameter=True)
                dummy['t'] = dummy_poc['position'].read()
                dummy_tangent['t'] = dummy_poc['tangent'].as_vector() + dummy_poc['position'].as_vector()
                mc.delete(mx.cmd(mc.aimConstraint, dummy_tangent, dummy, aim=[0, 1, 0], u=[0, 0, 0], wut='None'))

            mmx = mx.create_node(mx.tMultMatrix, name='_mmx#')

            omx = dummy['wm'][0].as_transform() * tgt['wim'][0].as_transform()
            cmx = mx.create_node(mx.tComposeMatrix, name='_cmx#')
            cmx['inputTranslate'] = omx.translation()
            cmx['inputRotate'] = omx.rotation()
            cmx['inputScale'] = omx.scale()
            cmx['inputShear'] = omx.shear(mx.sTransform)
            cmx['outputMatrix'] >> mmx['i'][0]

            tgt['wm'][0] >> mmx['i'][1]
            parent['wim'][0] >> mmx['i'][2]

            dmx = mx.create_node(mx.tDecomposeMatrix, '_srt#')
            mmx['o'] >> dmx['imat']

            tdata[i]['xfo'] = mmx['o']
            tdata[i]['pos'] = dmx['outputTranslate']

            if not do_orient or not do_scale:
                cmx = mx.create_node(mx.tComposeMatrix, name='_cmx#')

                dmx['outputTranslate'] >> cmx['inputTranslate']
                if do_orient:
                    dmx['outputRotate'] >> cmx['inputRotate']
                else:
                    cmx['inputRotate'] = dmx['outputRotate']
                if do_scale:
                    dmx['outputScale'] >> cmx['inputScale']
                    dmx['outputShear'] >> cmx['inputShear']
                else:
                    cmx['inputScale'] = dmx['outputScale']
                    cmx['inputShear'] = dmx['outputShear']

                tdata[i]['xfo'] = cmx['outputMatrix']

            # extract vectors
            tdata[i]['x'] = connect_expr('t * [1,0,0]', t=tdata[i]['xfo'])
            tdata[i]['z'] = connect_expr('t * [0,0,1]', t=tdata[i]['xfo'])

        dummy.add_attr(mx.Message('kill_me'))
        if len(targets) > 2:
            mc.parent(str(dummy_tangent), str(dummy))
        if not self.modes:
            mx.delete(dummy)

        # stretch
        if len(targets) == 2:
            db = mx.create_node(mx.tDistanceBetween, name='_len#')
            tdata[0]['xfo'] >> db['inMatrix1']
            tdata[1]['xfo'] >> db['inMatrix2']
            stretch_op = connect_expr('d/value(d)', d=db['d'])

        else:
            arclen = mx.create_node(mx.tCurveInfo, name='_arclen#')
            path.shape()['local'] >> arclen['inputCurve']
            stretch_op = connect_expr('d/value(d)', d=arclen['arcLength'])

        # muscle loop
        for i, node in enumerate(nodes):
            mdata = [{} for _ in range(len(targets))]

            # muscle
            mu = mx.create_node(mx.tTransform, parent=parent, name='mu_{}{}'.format(name, i))
            mc.delete(mx.cmd(mc.pointConstraint, targets, mu))
            mc.delete(mx.cmd(mc.aimConstraint, targets[1], mu, aim=[0, 1, 0], u=[0, 0, 0], wut='None'))

            # parameter weights
            if len(targets) == 2:
                p0 = tdata[0]['pos'].as_vector()
                p1 = tdata[1]['pos'].as_vector()
                p2 = node['t'].as_vector()
                r = (p2 - p1).length() / (p2 - p0).length()

                mu.add_attr(mx.Double('slide', keyable=True, min=0, max=1))
                mu['slide'] = r / (r + 1)

                mdata[0]['w'] = mu['slide']
                mdata[1]['w'] = connect_expr('lerp(1,0,w)', w=mu['slide'])

            else:
                blend_smooth_weights(mu, len(targets))
                for j in range(len(targets)):
                    mdata[j]['w'] = mu['w{}'.format(j)]

                mu.add_attr(mx.Double('slide', keyable=True, min=0, max=1))
                mu['slide'] = get_closest_point_on_curve(path, node, length=True)

                mu['u'] = get_closest_point_on_curve(path, node, parameter=True)

            # rig
            for j in range(len(targets)):
                mdata[j]['t'] = connect_expr('w * t', w=mdata[j]['w'], t=tdata[j]['pos'])
                mdata[j]['x'] = connect_expr('w * x', w=mdata[j]['w'], x=tdata[j]['x'])
                mdata[j]['z'] = connect_expr('w * z', w=mdata[j]['w'], z=tdata[j]['z'])

            # stretch axis
            mu.add_attr(mx.Double('stretch', keyable=True, min=0, max=1, default=1))
            stretch = connect_expr('lerp(1, div, w)', div=stretch_op, w=mu['stretch'])

            if len(targets) == 2:
                muy = connect_expr('norm(p1 - p0)', p0=tdata[0]['pos'], p1=tdata[1]['pos'])
                mut = connect_expr('wt0 + wt1', wt0=mdata[0]['t'], wt1=mdata[1]['t'])

            else:
                # poc = mx.create_node(mx.tPointOnCurveInfo, name='_mu_poc#')
                # poc['top'] = True
                # path.shape()['local'] >> poc['inputCurve']
                # mu['u'] >> poc['parameter']
                #
                # muy = connect_expr('norm(t)', t=poc['tangent'])
                # mut = poc['position']

                mp = mx.create_node(mx.tMotionPath, name='_mu_path#')
                path.shape()['local'] >> mp['geometryPath']
                mp['fractionMode'] = True
                mp['follow'] = False
                mu['slide'] >> mp['uValue']

                muy = connect_expr('norm(xfo * [0,1,0])', xfo=mp['orientMatrix'])
                mut = mp['allCoordinates']

                # closest = mx.create_node(mx.tNearestPointOnCurve, name='_u')
                # path.shape()['local'] >> closest['inputCurve']
                # mut >> closest['inPosition']
                # closest['parameter'] >> mu['u']

            muy = connect_expr('y * stretch', y=muy, stretch=stretch)

            # squash axis 1
            _add = mx.create_node(mx.tPlusMinusAverage, name='_add#')
            for j in range(len(targets)):
                mdata[j]['x'] >> _add['input3D'][j]

            mux = _add['output3D']
            if not do_scale:
                mux = connect_expr('norm(v)', v=mux)

            # squash axis 2
            _add = mx.create_node(mx.tPlusMinusAverage, name='_add#')
            for j in range(len(targets)):
                mdata[j]['z'] >> _add['input3D'][j]

            muz = _add['output3D']
            if not do_scale:
                muz = connect_expr('norm(v)', v=muz)

            # unshear rig
            if do_shear:
                mu.add_attr(mx.Double('shearing', keyable=True, min=0, max=1, default=1))
                mux = connect_expr('lerp(norm(y^z), x, sh)', x=mux, y=muy, z=muz, sh=mu['shearing'])
                muz = connect_expr('lerp(norm(x^y), z, sh)', x=mux, y=muy, z=muz, sh=mu['shearing'])

            # squash weight
            if do_squash:
                mu.add_attr(mx.Double('squash', keyable=True, min=0, max=1, default=0))
                mu.add_attr(mx.Double('exponent', keyable=True, max=0, min=-2, default=-0.5))
                squash = connect_expr('lerp(1, div^rate, w)', div=stretch_op, rate=mu['exponent'], w=mu['squash'])

                mux = connect_expr('sq*x', x=mux, sq=squash)
                muz = connect_expr('sq*z', z=muz, sq=squash)

            # ijk transform
            ijk = connect_expr('matrix(x, y, z, t)', x=mux, y=muy, z=muz, t=mut)

            # hook weight
            if do_weight:
                mu.add_attr(mx.Double('weight', keyable=True, min=0, max=1, default=1))

                blend = mx.create_node(mx.tWtAddMatrix, name='_bmx#')
                blend['i'][0]['m'] = ijk.as_matrix()
                connect_expr('b = 1-w', b=blend['i'][0]['w'], w=mu['weight'])

                ijk >> blend['i'][1]['m']
                mu['weight'] >> blend['i'][1]['w']
                connect_matrix(blend['o'], mu)
            else:
                connect_matrix(ijk, mu)

            # stretch settings
            mu['stretch'] = self.data.get('stretch', 1)
            if do_weight:
                mu['weight'] = self.data.get('weight', 0.5)
            if do_shear:
                mu['shearing'] = self.data.get('shear', 1)
            if do_squash:
                mu['squash'] = self.data.get('squash', 0)

            # do hook?
            if do_hook:
                matrix_constraint(mu, node)
            else:
                mc.parent(str(node), str(mu))

            self.set_id(mu, 'muscle')
