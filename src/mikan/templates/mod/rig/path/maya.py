# coding: utf-8

from six import string_types

from mikan.maya.lib.rig import axis_to_vector

from mikan.maya import cmds as mc, copy_transform
import mikan.maya.cmdx as mx

import mikan.maya.core as mk
from mikan.core.utils import flatten_list
from mikan.core.logger import create_logger
from mikan.core.prefs import Prefs
from mikan.maya.lib.nurbs import get_closest_point_on_curve, get_curve_length_from_param
from mikan.maya.lib.connect import connect_expr

log = create_logger()


class Mod(mk.Mod):

    def run(self):

        debug_mode = 'debug' in self.modes

        legacy = Prefs.get('mod/path/legacy', 1)

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
        elif isinstance(geo, mx.Node) and geo.is_a(mx.tTransform):
            for _shp in geo.shapes():
                if not _shp['io']:
                    shp = _shp
                    xfo = geo
                    break

        if not shp.is_a(mx.tNurbsCurve):
            raise mk.ModArgumentError('invalid geometry (must be a nurbs curve)')

        shp_up, xfo_up = self.data.get('geo_up', (None, None))
        if shp_up is not None and not shp_up.is_a(mx.tNurbsCurve):
            raise mk.ModArgumentError('invalid up geometry (must be a nurbs curve)')

        closest = self.data.get('closest')
        if closest is not None and not isinstance(closest, mx.DagNode):
            raise mk.ModArgumentError('invalid node for closest projection')

        # args
        parent = self.data.get('parent', nodes[0].parent())

        do_hook = bool(self.data.get('hook', True))
        do_snap = bool(self.data.get('snap', False))
        do_orient = self.data.get('rotate', True) and self.data.get('orient', True)

        percent = bool(self.data.get('percent', False))
        io = bool(self.data.get('io', False))

        length_mode = False
        if legacy == 0:
            length_mode = self.data.get('mode') != 'parametric'
        parametric = not self.data.get('length', length_mode)
        if closest:
            parametric = True

        # vectors
        fwd_vector = self.data.get('forward_vector', [1, 0, 0])
        if isinstance(fwd_vector, string_types):
            fwd_vector = axis_to_vector(fwd_vector)
        fwd_vector = mx.Vector(fwd_vector)

        _default = [0, 0, 0]
        if 'up_object_vector' in self.data or 'up_object' in self.data or shp_up:
            _default = [0, 1, 0]

        up_vector = self.data.get('up_vector', _default)
        if isinstance(up_vector, string_types):
            up_vector = axis_to_vector(up_vector)
        up_vector = mx.Vector(up_vector) if up_vector else mx.Vector()

        up_object_vector = self.data.get('up_object_vector', [0, 0, 0])
        if isinstance(up_object_vector, string_types):
            up_object_vector = axis_to_vector(up_object_vector)
        up_object_vector = mx.Vector(up_object_vector) if up_object_vector else mx.Vector()

        up_object = self.data.get('up_object')

        if do_flip:
            fwd_vector *= -1
            up_vector *= -1

        # path
        name = 'path_{}#'.format(xfo)
        tpl = self.get_template()
        if tpl:
            name = 'path_{}#'.format(tpl.name)

        # build loop
        for node in nodes:

            # args
            u = self.data.get('u')
            if not isinstance(u, (float, int)):
                attach = self.data.get('attach', node)  # legacy?
                u = get_closest_point_on_curve(shp, attach, parameter=True)

            if shp_up:
                up_object = Mod.create_path(
                    node, shp_up,
                    parent=parent, name=name.replace('path_', 'path_up_'), legacy=legacy,
                    u=u, parametric=parametric, percent=percent, io=io,
                    closest=closest, debug_mode=debug_mode
                )

            path = Mod.create_path(
                node, shp,
                do_orient, parent, name, legacy,
                u, parametric, percent, io, fwd_vector,
                up_vector, up_object, up_object_vector,
                closest, debug_mode
            )

            if shp_up:
                path['u'] >> up_object['u']

            # hook
            if do_hook:
                mc.parent(str(node), str(path))

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
            closest=None, debug_mode=False
    ):

        # args
        if fwd_vector is None:
            fwd_vector = mx.Vector(1, 0, 0)
        if up_vector is None:
            up_vector = mx.Vector(0, 1, 0)
        if up_object_vector is None:
            up_object_vector = mx.Vector(0, 0, 0)

        # path root
        path = mx.create_node(mx.tTransform, parent=parent, name=name)

        if io:
            parametric = False

        if not isinstance(closest, mx.Node):
            max_u = shp['max'].read()
            if percent or not parametric:
                max_u = 1
            if legacy == 0:
                node.add_attr(mx.Double('u', keyable=True, min=0, max=max_u))
                plug = node['u']
            else:
                path.add_attr(mx.Double('u', keyable=True, min=0, max=max_u))
                plug = path['u']
        else:
            max_u = shp['max'].read()
            path.add_attr(mx.Double('u', keyable=True, min=0, max=max_u))

            parametric = True

        # length ratio mode
        if not parametric:
            mp = mx.create_node(mx.tMotionPath, name='_path#')
            shp['worldSpace'][0] >> mp['geometryPath']

            # set
            mp['fractionMode'] = True
            mp['follow'] = False

            if do_orient:
                mp['follow'] = True
                mp['wut'] = 3

                if up_object:
                    if up_object_vector.length():
                        mp['worldUpType'] = 2
                    else:
                        mp['worldUpType'] = 1
                    up_object['wm'][0] >> mp['worldUpMatrix']

                else:
                    mp['worldUpType'] = 3

                mp['worldUpVector'] = up_object_vector

                if fwd_vector[0] != 0:
                    mp['frontAxis'] = 0
                elif fwd_vector[1] != 0:
                    mp['frontAxis'] = 1
                elif fwd_vector[2] != 0:
                    mp['frontAxis'] = 2

                if up_vector[0] != 0:
                    mp['upAxis'] = 0
                elif up_vector[1] != 0:
                    mp['upAxis'] = 1
                elif up_vector[2] != 0:
                    mp['upAxis'] = 2

            # connect node
            cm = mx.create_node(mx.tComposeMatrix, name='_cm#')
            mp['allCoordinates'] >> cm['inputTranslate']
            if do_orient:
                mp['rotate'] >> cm['inputRotate']

            mmx = mx.create_node(mx.tMultMatrix, name='_mmx')
            cm['outputMatrix'] >> mmx['matrixIn'][0]
            path['parentInverseMatrix'][0] >> mmx['matrixIn'][1]

            dm = mx.create_node(mx.tDecomposeMatrix, name='_dm#')
            mmx['matrixSum'] >> dm['inputMatrix']

            dm['outputTranslate'] >> path['translate']
            if do_orient:
                dm['outputRotate'] >> path['rotate']

            arc_len = get_curve_length_from_param(shp, shp['max'].read())
            arc_pos = get_curve_length_from_param(shp, u)
            _u = arc_pos / arc_len if arc_len != 0 else 0
            plug.write(_u)
            plug >> mp['uValue']

        # parametric mode
        else:
            poc = mx.create_node(mx.tPointOnCurveInfo, name='_poc#')
            shp['worldSpace'][0] >> poc['inputCurve']

            if isinstance(closest, mx.Node):
                _dm = mx.create_node(mx.tDecomposeMatrix)
                closest['wm'][0] >> _dm['inputMatrix']

                _n = mx.create_node(mx.tNearestPointOnCurve)
                _dm['outputTranslate'] >> _n['inPosition']
                shp['worldSpace'][0] >> _n['inputCurve']
                _n['parameter'] >> poc['parameter']

                _n['parameter'] >> path['u']

            else:
                if percent:
                    poc['turnOnPercentage'] = percent
                    u /= shp['max'].read()
                plug.write(u)
                plug >> poc['parameter']

            m1 = mx.create_node(mx.tFourByFourMatrix, name='_mx#')
            poc['positionX'] >> m1['in30']
            poc['positionY'] >> m1['in31']
            poc['positionZ'] >> m1['in32']

            mmx1 = mx.create_node(mx.tMultMatrix, name='_mxx#')
            m1['output'] >> mmx1['matrixIn'][0]
            path['parentInverseMatrix'][0] >> mmx1['matrixIn'][1]

            dm1 = mx.create_node(mx.tDecomposeMatrix, name='_dm#')
            mmx1['matrixSum'] >> dm1['inputMatrix']

            dm1['outputTranslate'] >> path['translate']

            if do_orient:
                add = mx.create_node(mx.tPlusMinusAverage, name='_add#')
                poc['position'] >> add['input3D'][0]
                poc['tangent'] >> add['input3D'][1]

                m2 = mx.create_node(mx.tFourByFourMatrix, name='_m#')
                add['output3Dx'] >> m2['in30']
                add['output3Dy'] >> m2['in31']
                add['output3Dz'] >> m2['in32']

                mmx2 = mx.create_node(mx.tMultMatrix, name='_mxx#')
                m2['output'] >> mmx2['matrixIn'][0]
                path['parentInverseMatrix'][0] >> mmx2['matrixIn'][1]

                dm2 = mx.create_node(mx.tDecomposeMatrix, name='_dm#')
                mmx2['matrixSum'] >> dm2['inputMatrix']

                aim = mx.create_node(mx.tAimConstraint, parent=path, name='_aim#')
                dm2['outputTranslate'] >> aim['target'][0]['targetTranslate']
                path['parentInverseMatrix'][0] >> aim['constraintParentInverseMatrix']
                path['rotateOrder'] >> aim['constraintRotateOrder']
                path['rotatePivot'] >> aim['constraintRotatePivot']
                path['rotatePivotTranslate'] >> aim['constraintRotateTranslate']
                path['translate'] >> aim['constraintTranslate']
                path['parentMatrix'][0] >> aim['target'][0]['targetParentMatrix']

                aim['aimVector'] = fwd_vector
                aim['upVector'] = up_vector

                if up_vector.length() == 0:
                    aim['worldUpType'] = 4  # none
                else:
                    aim['worldUpType'] = 3  # vector

                if isinstance(up_object, mx.Node):
                    up_object['wm'][0] >> aim['worldUpMatrix']
                    aim['worldUpType'] = 2  # object rotation up
                    if up_object_vector.length() == 0:
                        aim['worldUpType'] = 1  # object up

                aim['worldUpVector'] = up_object_vector

                aim['constraintRotate'] >> path['rotate']

        # length out
        path.add_attr(mx.Double('length'))
        path.add_attr(mx.Double('length0'))

        _arc = mx.create_node(mx.tCurveInfo, name='_arclen#')
        shp['worldSpace'][0] >> _arc['inputCurve']

        _arc['arcLength'] >> path['length']
        path['length0'] = _arc['arcLength']
        path['length'].channel_box = True
        path['length0'].channel_box = True
        path['length'].lock()
        path['length0'].lock()

        if io:
            path.add_attr(mx.Double('u_parametric_base'))
            path.add_attr(mx.Double('scale_distance_base'))
            path.add_attr(mx.Double('offset'))
            path.add_attr(mx.Boolean('loop'))
            path['u_parametric_base'].channel_box = True
            path['scale_distance_base'].channel_box = True
            path['offset'].channel_box = True
            path['loop'].channel_box = True
            path['u_parametric_base'] = u
            path['u_parametric_base'].lock()
            path['scale_distance_base'] = 1
            path['offset'] = 0
            path['loop'] = False

            u_base = path['u']
            u_curve_max = shp['max'].read()
            length_curve = path['length']
            length_curve_base_init = path['length'].read()
            if debug_mode:
                path.add_attr(mx.Double('u_base'))
                path.add_attr(mx.Double('u_curve_max'))
                path.add_attr(mx.Double('length_curve'))
                path.add_attr(mx.Double('length_curve_base'))

                path['u_base'].channel_box = True
                path['u_curve_max'].channel_box = True
                path['length_curve'].channel_box = True
                path['length_curve_base'].channel_box = True

                path['u'] >> path['u_base']
                path['u_curve_max'] = shp['max'].read()
                path['length'] >> path['length_curve']
                path['length_curve_base'] = path['length'].read()

                u_base = path['u_base']
                u_curve_max = path['u_curve_max'].read()
                length_curve = path['length_curve']
                length_curve_base_init = path['length_curve_base'].read()

            _dm = mx.create_node('decomposeMatrix')
            path['parentMatrix'][0] >> _dm['inputMatrix']
            global_scale = _dm['outputScale'][0]

            length_curve_base = connect_expr(
                'length_curve_base_init * global_scale',
                length_curve_base_init=length_curve_base_init,
                global_scale=global_scale)

            length_base = connect_expr(
                'u_base * length_curve_base',
                u_base=u_base,
                length_curve_base=length_curve_base)

            if debug_mode:
                path.add_attr(mx.Double('length_base'))
                path['length_base'].channel_box = True
                length_base >> path['length_base']
                length_base = path['length_base']

            u_slide_keep_distance_start_base = connect_expr(
                '(length_base / length_curve * scale_distance_base + offset )',
                length_base=length_base,
                length_curve=length_curve,
                u_curve_max=u_curve_max,
                scale_distance_base=path['scale_distance_base'],
                offset=path['offset'])

            u_slide_keep_distance_start = connect_expr(
                'base % 1 * loop + clamp(base,0,1) * (1-loop)',
                base=u_slide_keep_distance_start_base,
                loop=path['loop'])

            if debug_mode:
                path.add_attr(mx.Double('u_slide_keep_distance_start'))
                path['u_slide_keep_distance_start'].channel_box = True
                u_slide_keep_distance_start >> path['u_slide_keep_distance_start']
                u_slide_keep_distance_start = path['u_slide_keep_distance_start']

            u_slide_keep_distance_end_base = connect_expr(
                '(1 - (length_curve_base - length_base) / length_curve * scale_distance_base) + offset',
                length_base=length_base,
                length_curve_base=length_curve_base,
                length_curve=length_curve,
                scale_distance_base=path['scale_distance_base'],
                offset=path['offset'])

            u_slide_keep_distance_end = connect_expr(
                'base % 1 * loop + clamp(base,0,1) * (1-loop)',
                base=u_slide_keep_distance_end_base,
                loop=path['loop'])

            if debug_mode:
                path.add_attr(mx.Double('u_slide_keep_distance_end'))
                path['u_slide_keep_distance_end'].channel_box = True
                u_slide_keep_distance_end >> path['u_slide_keep_distance_end']
                u_slide_keep_distance_end = path['u_slide_keep_distance_end']

            u_slide_stretch_base = connect_expr(
                '(length_base / length_curve_base + offset )',
                length_base=length_base,
                length_curve=length_curve,
                length_curve_base=length_curve_base,
                offset=path['offset'])

            u_slide_stretch = connect_expr(
                'base % 1 * loop + clamp(base,0,1) * (1-loop)',
                base=u_slide_stretch_base,
                loop=path['loop'])

            if debug_mode:
                path.add_attr(mx.Double('u_slide_stretch'))
                path['u_slide_stretch'].channel_box = True
                u_slide_stretch >> path['u_slide_stretch']
                u_slide_stretch = path['u_slide_stretch']

            sliding_behaviors = (
                (0, 'parametric'),
                (1, 'slide_stretch'),
                (2, 'slide_keep_distance_start'),
                (3, 'slide_keep_distance_end')
            )
            path.add_attr(mx.Enum('sliding_behavior', channelBox=True, default=1, fields=sliding_behaviors))
            path['sliding_behavior'].channel_box = True

            choice_out = connect_expr(
                'switch(trigger, u_base, u_slide_stretch, u_slide_keep_distance_start, u_slide_keep_distance_end)',
                trigger=path['sliding_behavior'],
                u_base=path['u_parametric_base'],
                u_slide_stretch=u_slide_stretch,  # 0 - 1
                u_slide_keep_distance_start=u_slide_keep_distance_start,  # 0 - 1
                u_slide_keep_distance_end=u_slide_keep_distance_end)  # 0 - 1

            if debug_mode:
                path.add_attr(mx.Double('u_out'))
                path['u_out'].channel_box = True
                choice_out >> path['u_out']
                path['u_out'] >> mp['uValue']
            else:
                choice_out >> mp['uValue']

            choice_out = connect_expr(
                'switch(trigger, u_base, u_slide_stretch, u_slide_keep_distance_start, u_slide_keep_distance_end)',
                trigger=path['sliding_behavior'],
                u_base=0,
                u_slide_stretch=1,
                u_slide_keep_distance_start=1,
                u_slide_keep_distance_end=1)

            choice_out >> mp['fractionMode']

        # exit
        return path
