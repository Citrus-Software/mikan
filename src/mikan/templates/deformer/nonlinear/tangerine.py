# coding: utf-8
import meta_nodal_py as kl
from meta_nodal_py.Imath import V3f

from mikan.core.prefs import Prefs
from mikan.core.logger import create_logger

import mikan.tangerine.core as mk
from mikan.tangerine.lib.commands import add_plug

log = create_logger()


class Deformer(mk.Deformer):
    try:
        node_class = (kl.Bend, kl.Sine, kl.Squash, kl.Twist, kl.Wave, kl.Flare)
    except AttributeError:
        node_class = (kl.Bend, kl.Sine, kl.Squash, kl.Twist, kl.Wave)

    def build(self, data=None):
        data = self.data
        # check data

        if not self.transform:
            raise mk.DeformerError('geometry missing')

        # get shape
        if not self.geometry:
            self.find_geometry()

        # get handle
        handle = self.data['handle']
        try:
            if isinstance(handle, str):
                handle = self.get_node(handle)
        except:
            raise mk.DeformerError('skipped: handle does not exist')

        # build node
        nonlinear_classes = {
            'bend': kl.Bend,
            'flare': kl.Flare,
            'sine': kl.Sine,
            'twist': kl.Twist,
            'wave': kl.Wave,
            'squash': kl.Squash
        }
        cls = nonlinear_classes[data['type']]
        self.node = cls(self.geometry, data['type'])

        # plug node
        shp = None
        if Prefs.get('deformer/nonlinear/legacy_plugs', 1) > 0:
            shp = handle.find('{}_plugs'.format(data['type']))

        if not shp:
            shp = kl.Node(handle, '{}_plugs'.format(data['type']))
            add_plug(shp, '_plugs', kl.Unit)

            for attr, attr_type in self.nonlinear_attrs[data['type']]:
                shp_plug = add_plug(shp, attr, attr_type, keyable=True)
                plug = self.node.get_plug(attr)
                plug.connect(shp_plug)

                if attr_type is V3f:
                    plug_node = kl.FloatToV3f(shp, attr)
                    shp_plug.connect(plug_node.vector)

        else:
            for attr, attr_type in self.nonlinear_attrs[data['type']]:
                shp_plug = shp.get_dynamic_plug(attr)
                plug = self.node.get_plug(attr)
                plug.connect(shp_plug)

        add_plug(self.node, '_plugs', kl.Unit)
        self.node.get_dynamic_plug('_plugs').connect(shp.get_dynamic_plug('_plugs'))

        # build nonlinear
        plugs = self.data.get('plugs', {})

        if data['type'] == 'bend':
            curvature = plugs.get('curvature', 0)
            start_bound = plugs.get('low_bound', -1)
            end_bound = plugs.get('high_bound', 1)

            shp.start_bound_in.set_value(start_bound)
            shp.end_bound_in.set_value(end_bound)
            shp.curve_in.set_value(curvature)

            self.node.legacy.set_value(Prefs.get('deformer/nonlinear/legacy_bend', 1))

        elif data['type'] == 'flare':
            curve = plugs.get('curve', 0)
            start_flare_x = plugs.get('start_flare_x')
            start_flare_z = plugs.get('start_flare_z')
            end_flare_x = plugs.get('end_flare_x')
            end_flare_z = plugs.get('end_flare_z')
            start_bound = plugs.get('low_bound', -1)
            end_bound = plugs.get('high_bound', 1)

            shp.curve_in.set_value(curve)
            shp.start_bound_in.set_value(start_bound)
            shp.end_bound_in.set_value(end_bound)

            start_flare = shp.find('start_flare_in')
            start_flare.x.set_value(start_flare_x)
            start_flare.y.set_value(1.0)
            start_flare.z.set_value(start_flare_z)

            end_flare = shp.find('end_flare_in')
            end_flare.x.set_value(end_flare_x)
            end_flare.y.set_value(1.0)
            end_flare.z.set_value(end_flare_z)

        elif data['type'] == 'sine':
            amplitude = plugs.get('amplitude')
            wavelength = plugs.get('wavelength')
            offset = plugs.get('offset')
            dropoff = plugs.get('dropoff')
            start_bound = plugs.get('low_bound', -1)
            end_bound = plugs.get('high_bound', 1)

            shp.amplitude_in.set_value(amplitude)
            shp.wavelength_in.set_value(wavelength)
            shp.start_bound_in.set_value(start_bound)
            shp.end_bound_in.set_value(end_bound)
            shp.dropoff_in.set_value(dropoff)
            shp.offset_angle_in.set_value(offset)

        elif data['type'] == 'squash':
            factor = plugs.get('factor')
            expand = plugs.get('expand')
            max_expand_pos = plugs.get('max_expand_pos')
            start_smoothness = plugs.get('start_smoothness')
            end_smoothness = plugs.get('end_smoothness')
            start_bound = plugs.get('low_bound', -1)
            end_bound = plugs.get('high_bound', 1)

            shp.amplitude_in.set_value(factor)
            shp.expand_in.set_value(expand)
            shp.max_expand_pos_in.set_value(max_expand_pos)
            shp.start_smoothness_in.set_value(start_smoothness)
            shp.end_smoothness_in.set_value(end_smoothness)
            shp.start_bound_in.set_value(start_bound)
            shp.end_bound_in.set_value(end_bound)

        elif data['type'] == 'twist':
            start_angle = plugs.get('start_angle')
            end_angle = plugs.get('end_angle')
            start_bound = plugs.get('low_bound', -1)
            end_bound = plugs.get('high_bound', 1)

            shp.start_angle_in.set_value(start_angle)
            shp.end_angle_in.set_value(end_angle)
            shp.start_bound_in.set_value(start_bound)
            shp.end_bound_in.set_value(end_bound)

            self.node.legacy.set_value(Prefs.get('deformer/nonlinear/legacy_twist', 1))

        elif data['type'] == 'wave':
            amplitude = plugs.get('amplitude')
            wavelength = plugs.get('wavelength')
            offset = plugs.get('offset')
            dropoff = plugs.get('dropoff')
            dropoff_position = plugs.get('dropoff_position')
            start_radius = plugs.get('min_radius')
            end_radius = plugs.get('max_radius')

            shp.amplitude_in.set_value(amplitude)
            shp.wavelength_in.set_value(wavelength)
            shp.dropoff_in.set_value(dropoff)
            shp.dropoff_position_in.set_value(dropoff_position)
            shp.start_radius_in.set_value(start_radius)
            shp.end_radius_in.set_value(end_radius)
            shp.offset_angle_in.set_value(offset)

        self.node.offset_in.connect(handle.world_transform)
        self.node.geom_world_transform_in.connect(self.transform.world_transform)

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

        # update i/o
        self.reorder()

        # update weights
        self.write()

    def write(self):
        if 0 not in self.data['maps']:
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
    def hook(dfm, xfo, hook):

        if hook == 'enable' or hook == 'envelope':
            return dfm.enable_in

        elif hook == 'curvature':
            return dfm.curve_in.get_input().get_plug()
        elif hook == 'low_bound':
            return dfm.start_bound_in.get_input().get_plug()
        elif hook == 'high_bound':
            return dfm.end_bound_in.get_input().get_plug()

        elif hook == 'curve':
            return dfm.curve_in.get_input().get_plug()
        elif hook == 'start_flare_x':
            shp = dfm.start_flare_in.get_input().get_node()
            return shp.find('start_flare_in').x
        elif hook == 'start_flare_z':
            shp = dfm.start_flare_in.get_input().get_node()
            return shp.find('start_flare_in').z
        elif hook == 'end_flare_x':
            shp = dfm.end_flare_in.get_input().get_node()
            return shp.find('end_flare_in').x
        elif hook == 'end_flare_z':
            shp = dfm.end_flare_in.get_input().get_node()
            return shp.find('end_flare_in').z
        elif hook == 'amplitude':
            return dfm.amplitude_in.get_input().get_plug()
        elif hook == 'wavelength':
            return dfm.wavelength_in.get_input().get_plug()
        elif hook == 'offset':
            return dfm.offset_angle_in.get_input().get_plug()
        elif hook == 'dropoff':
            return dfm.dropoff_in.get_input().get_plug()

        elif hook == 'factor':
            return dfm.amplitude_in.get_input().get_plug()
        elif hook == 'expand':
            return dfm.expand_in.get_input().get_plug()

        elif hook == 'start_smoothness':
            return dfm.start_smoothness_in.get_input().get_plug()
        elif hook == 'end_smoothness':
            return dfm.end_smoothness_in.get_input().get_plug()

        elif hook == 'start_angle':
            return dfm.start_angle_in.get_input().get_plug()
        elif hook == 'end_angle':
            return dfm.end_angle_in.get_input().get_plug()

        elif hook == 'dropoff_position':
            return dfm.dropoff_position_in.get_input().get_plug()
        elif hook == 'min_radius':
            return dfm.start_radius_in.get_input().get_plug()
        elif hook == 'max_radius':
            return dfm.end_radius_in.get_input().get_plug()

    nonlinear_attrs = {
        'bend': (
            ('curve_in', float),
            ('start_bound_in', float),
            ('end_bound_in', float)),
        'flare': (
            ('curve_in', float),
            ('start_flare_in', V3f),
            ('end_flare_in', V3f),
            ('start_bound_in', float),
            ('end_bound_in', float)),
        'sine': (
            ('amplitude_in', float),
            ('wavelength_in', float),
            ('start_bound_in', float),
            ('end_bound_in', float),
            ('dropoff_in', float),
            ('offset_angle_in', float)),
        'squash': (
            ('amplitude_in', float),
            ('expand_in', float),
            ('max_expand_pos_in', float),
            ('start_smoothness_in', float),
            ('end_smoothness_in', float),
            ('start_bound_in', float),
            ('end_bound_in', float)),
        'twist': (
            ('start_angle_in', float),
            ('end_angle_in', float),
            ('start_bound_in', float),
            ('end_bound_in', float)),
        'wave': (
            ('amplitude_in', float),
            ('wavelength_in', float),
            ('dropoff_in', float),
            ('dropoff_position_in', float),
            ('start_radius_in', float),
            ('end_radius_in', float),
            ('offset_angle_in', float),
        )
    }
