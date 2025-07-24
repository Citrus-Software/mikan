# coding: utf-8

from six import string_types

from mikan.maya import om, oma
from mikan.maya import cmds as mc
from mikan.maya import cmdx as mx

import mikan.maya.core as mk
from mikan.core.prefs import Prefs
from mikan.core.logger import create_logger

log = create_logger()


class Deformer(mk.Deformer):
    node_class = mx.tNonLinear

    default_data = {
        'maps': {},
    }

    def read(self):

        # update membership
        cp_fn = self.get_members()

        if not cp_fn.isComplete:
            mmap = self.data.get('membership')
            if mmap:
                if sum(mmap.weights) != cp_fn.elementCount:
                    self.log_error('membership map mismatch weights')
                    return
            else:
                mmap = self.get_membership()
                if not mmap and sum(mmap.weights) != cp_fn.elementCount:
                    self.log_error('membership map mismatch weights')
                    return
                else:
                    self.data['membership'] = mmap

        # base weights
        fn = oma.MFnGeometryFilter(self.node.object())
        oid = int(fn.indexForOutputShape(self.geometry.object()))
        weights_plug = self.node['weightList'][oid]['weights']

        count = self.get_size()
        weights = [1.0] * count
        for i in weights_plug.array_indices:
            weights[i] = weights_plug[i].read()

        if cp_fn.isComplete:
            wmap = weights
        else:
            wmap = [float(w) for w in mmap.weights]
            for i, v in enumerate(mmap.weights):
                if v:
                    wmap[i] = weights[i]

        if any(map(lambda w: w != 1, weights)):
            self.data['maps'][0] = mk.WeightMap(wmap)

        # handle
        self.data['handle'] = self.get_node_id(self.node['matrix'].input())
        self.data['type'] = self.node['deformerData'].input().type_name.split('deform')[1].lower()

        plugs = {}
        self.data['plugs'] = plugs

        if self.data['type'] == 'bend':
            plugs['curvature'] = self.node['curvature'].read()
            plugs['low_bound'] = self.node['lowBound'].read()
            plugs['high_bound'] = self.node['highBound'].read()

        elif self.data['type'] == 'flare':
            plugs['curve'] = self.node['curve'].read()
            plugs['start_flare_x'] = self.node['startFlareX'].read()
            plugs['start_flare_z'] = self.node['startFlareZ'].read()
            plugs['end_flare_x'] = self.node['endFlareX'].read()
            plugs['end_flare_z'] = self.node['endFlareZ'].read()
            plugs['low_bound'] = self.node['lowBound'].read()
            plugs['high_bound'] = self.node['highBound'].read()

        elif self.data['type'] == 'sine':
            plugs['amplitude'] = self.node['amplitude'].read()
            plugs['wavelength'] = self.node['wavelength'].read()
            plugs['offset'] = self.node['offset'].read()
            plugs['dropoff'] = self.node['dropoff'].read()
            plugs['low_bound'] = self.node['lowBound'].read()
            plugs['high_bound'] = self.node['highBound'].read()

        elif self.data['type'] == 'squash':
            plugs['factor'] = self.node['factor'].read()
            plugs['expand'] = self.node['expand'].read()
            plugs['max_expand_pos'] = self.node['maxExpandPos'].read()
            plugs['start_smoothness'] = self.node['startSmoothness'].read()
            plugs['end_smoothness'] = self.node['endSmoothness'].read()
            plugs['low_bound'] = self.node['lowBound'].read()
            plugs['high_bound'] = self.node['highBound'].read()

        elif self.data['type'] == 'twist':
            plugs['start_angle'] = self.node['startAngle'].read()
            plugs['end_angle'] = self.node['endAngle'].read()
            plugs['low_bound'] = self.node['lowBound'].read()
            plugs['high_bound'] = self.node['highBound'].read()

        elif self.data['type'] == 'wave':
            plugs['amplitude'] = self.node['amplitude'].read()
            plugs['wavelength'] = self.node['wavelength'].read()
            plugs['offset'] = self.node['offset'].read()
            plugs['dropoff'] = self.node['dropoff'].read()
            plugs['dropoff_position'] = self.node['dropoffPosition'].read()
            plugs['min_radius'] = self.node['minRadius'].read()
            plugs['max_radius'] = self.node['maxRadius'].read()

        for key in ('curvature', 'start_angle', 'end_angle'):
            if key in plugs:
                plugs[key] = mx.Radians(plugs[key]).asDegrees()

    def build(self, data=None):
        # check data
        if not self.transform:
            raise mk.DeformerError('geometry missing')

        if not self.data['handle']:
            raise mk.DeformerError('handle missing')

        # get shape
        if not self.geometry:
            self.find_geometry()

        # intermediate check
        io = self.geometry['io'].read()
        if io:
            self.geometry['io'] = False

        # build deformer
        if not self.node:
            # get handle
            handle = self.data['handle']
            try:
                if isinstance(handle, string_types):
                    handle = self.get_node(handle)
            except:
                raise mk.DeformerError('skipped: handle does not exist')

            node_type = 'deform{}'.format(self.data['type'].capitalize())

            shp = None
            if Prefs.get('deformer/nonlinear/legacy_plugs', 1) > 0:
                shp = handle.shape(type=node_type)

            if not shp:
                with mx.DagModifier() as md:
                    shp = md.create_node(node_type, parent=handle)

            # build deformer node
            dfm, _shp = mc.nonLinear(str(self.geometry), typ=self.data['type'])
            self.node = mx.encode(dfm)

            for attr in self.nonlinear_attrs[self.data['type']]:
                self.node.delete_attr(attr)
                mc.addAttr(str(self.node), ln=attr, k=True, proxy='{}.{}'.format(shp, attr))

            shp['deformerData'] >> self.node['deformerData']
            handle['wm'][0] >> self.node['matrix']
            mx.delete(_shp)

            xfo_name = self.transform.name(namespace=False)
            self.node.rename('{}_{}'.format(self.data['type'], xfo_name))
            shp.rename('{}_{}Shape'.format(self.data['type'], xfo_name))
            dfm_set = self.node.output(type=mx.tObjectSet)
            if dfm_set:
                dfm_set.rename('{}_{}Set'.format(self.data['type'], xfo_name))

            if '::ctrls.' in handle['gem_id'].read():
                shp['v'] = False

        # intermediate check
        if io:
            self.geometry['io'] = True

        # update i/o
        self.reorder()

        # update weights
        self.update()

        # update plugs
        plugs = self.data.get('plugs', {})

        for key in ('curvature', 'start_angle', 'end_angle'):
            if key in plugs:
                plugs[key] = mx.Degrees(plugs[key]).asRadians()

        if self.data['type'] == 'bend':
            self.node['curvature'] = plugs.get('curvature', 0)
            self.node['lowBound'] = plugs.get('low_bound', -1)
            self.node['highBound'] = plugs.get('high_bound', 1)

        elif self.data['type'] == 'flare':
            self.node['curve'] = plugs['curve']
            self.node['startFlareX'] = plugs.get('start_flare_x', 1)
            self.node['startFlareZ'] = plugs.get('start_flare_z', 1)
            self.node['endFlareX'] = plugs.get('end_flare_x', 1)
            self.node['endFlareZ'] = plugs.get('end_flare_z', 1)
            self.node['lowBound'] = plugs.get('low_bound', -1)
            self.node['highBound'] = plugs.get('high_bound', 1)

        elif self.data['type'] == 'sine':
            self.node['amplitude'] = plugs.get('amplitude', 0)
            self.node['wavelength'] = plugs.get('wavelength', 2)
            self.node['offset'] = plugs.get('offset', 0)
            self.node['dropoff'] = plugs.get('dropoff', 0)
            self.node['lowBound'] = plugs.get('low_bound', -1)
            self.node['highBound'] = plugs.get('high_bound', 1)

        elif self.data['type'] == 'squash':
            self.node['factor'] = plugs.get('factor', 0)
            self.node['expand'] = plugs.get('expand', 1)
            self.node['maxExpandPos'] = plugs.get('max_expand_pos', 0.5)
            self.node['startSmoothness'] = plugs.get('start_smoothness', 0)
            self.node['endSmoothness'] = plugs.get('end_smoothness', 0)
            self.node['lowBound'] = plugs.get('low_bound', -1)
            self.node['highBound'] = plugs.get('high_bound', 1)

        elif self.data['type'] == 'twist':
            self.node['startAngle'] = plugs.get('start_angle', 0)
            self.node['endAngle'] = plugs.get('end_angle', 0)
            self.node['lowBound'] = plugs.get('low_bound', 1)
            self.node['highBound'] = plugs.get('high_bound', 1)

        elif self.data['type'] == 'wave':
            self.node['amplitude'] = plugs.get('amplitude', 0)
            self.node['wavelength'] = plugs.get('wavelength', 1)
            self.node['offset'] = plugs.get('offset', 0)
            self.node['dropoff'] = plugs.get('dropoff', 0)
            self.node['dropoffPosition'] = plugs.get('dropoff_position', 0)
            self.node['minRadius'] = plugs.get('min_radius', 0)
            self.node['maxRadius'] = plugs.get('max_radius', 1)

    def write(self):
        if 0 not in self.data['maps']:
            return

        n = self.get_size()

        wm = self.data['maps'][0].weights[:]
        if len(wm) != n:
            self.log_warning('weightmap error: bad length -> fixed'.format())
            if len(wm) > n:
                wm = wm[:n]
            else:
                wm = wm + [0.0] * (n - len(wm))

        fn = oma.MFnGeometryFilter(self.node.object())
        oid = int(fn.indexForOutputShape(self.geometry.object()))

        mc.setAttr('{}.weightList[{}].weights[0:{}]'.format(self.node, oid, n - 1), *wm, size=len(wm))

    @staticmethod
    def hook(dfm, xfo, hook):

        if hook == 'enable' or hook == 'envelope':
            return dfm.envelope

        plug_hooks = {
            # bend
            'curvature': 'curvature',
            'low_bound': 'lowBound',
            'high_bound': 'highBound',
            # flare
            'curve': 'curve',
            'start_flare_x': 'startFlareX',
            'start_flare_z': 'startFlareZ',
            'end_flare_x': 'endFlareX',
            'end_flare_z': 'endFlareZ',
            # sine
            'amplitude': 'amplitude',
            'wavelength': 'wavelength',
            'offset': 'offset',
            'dropoff': 'dropoff',
            # squash
            'factor': 'factor',
            'expand': 'expand',
            'max_expand_pos': 'maxExpandPos',
            'start_smoothness': 'startSmoothness',
            'end_smoothness': 'endSmoothness',
            # twist
            'start_angle': 'startAngle',
            'end_angle': 'endAngle',
            # wave
            'dropoff_position': 'dropoffPosition',
            'min_radius': 'minRadius',
            'max_radius': 'maxRadius'
        }

        if hook in plug_hooks:
            plug = dfm[plug_hooks[hook]]

            if om.MFnAttribute(plug.plug().attribute()).isProxyAttribute:
                return plug.input(plug=True)

            return plug

    nonlinear_attrs = {
        'bend': (
            'curvature',
            'lowBound',
            'highBound'),
        'flare': (
            'curve',
            'startFlareX',
            'startFlareZ',
            'endFlareX',
            'endFlareZ',
            'lowBound',
            'highBound'),
        'sine': (
            'amplitude',
            'wavelength',
            'offset',
            'dropoff',
            'lowBound',
            'highBound'),
        'squash': (
            'factor',
            'expand',
            'maxExpandPos',
            'startSmoothness',
            'endSmoothness',
            'lowBound',
            'highBound'),
        'twist': (
            'startAngle',
            'endAngle',
            'lowBound',
            'highBound'),
        'wave': (
            'amplitude',
            'wavelength',
            'offset',
            'dropoff',
            'dropoffPosition',
            'minRadius',
            'maxRadius')
    }
