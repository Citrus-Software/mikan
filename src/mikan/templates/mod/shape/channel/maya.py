# coding: utf-8

from six import iteritems

from mikan.maya import om
from mikan.maya import cmds as mc
import mikan.maya.cmdx as mx

import mikan.maya.core as mk
from mikan.maya.lib.connect import *
from mikan.core.logger import create_logger
from mikan.core.utils.typeutils import ordered_dict

log = create_logger()


class Mod(mk.Mod):

    def run(self):

        # get channel node
        channel = self.node
        if 'node' in self.data:
            channel = self.data['node']

        # check sources
        src_nodes = []
        for src in self.data.get('sources', []):
            if isinstance(src, mx.DagNode):
                src_nodes.append(src)

        if not src_nodes:
            raise mk.ModArgumentError('no source defined')

        # get valid channel plugs
        plug_names = []

        for node in src_nodes:
            plugs = mc.listAttr(str(node), ud=1) or []
            for plug_name in plugs:
                plug = node[plug_name]
                if not plug.editable:
                    continue
                if not plug.output():
                    continue
                if plug_name in plug_names:
                    continue

                plug_names.append(plug_name)

        # check controller
        ctrl = self.data.get('target')
        if not ctrl:
            raise mk.ModArgumentError('no controller defined')

        # check rules
        if 'shapes' not in self.data or not isinstance(self.data['shapes'], (list, dict)):
            raise mk.ModArgumentError('no rules defined')

        # face buffer
        buffer = ordered_dict()

        for plug_name in plug_names:
            buffer[plug_name] = {
                'src': None,
                'add': [],
                'mult': [],
                'clamp': [None, None]
            }

        # cleanup rules
        shapes = self.data['shapes']

        if isinstance(shapes, list):
            # convert to dict
            _shapes = ordered_dict()
            for shp in shapes:
                if isinstance(shp, dict):
                    shp_name = list(shp)[0]
                    _shapes[shp_name] = shp[shp_name]
                else:
                    _shapes[shp] = {}
            shapes = _shapes

        # add plugs to controller
        channels = {}

        for shp_name, shp_data in iteritems(shapes):
            if not shp_data:
                shp_data = {}

            # get plug build data
            plug_default = shp_data.get('default', shp_data.get('dv'))
            plug_type = 'float'
            if isinstance(plug_default, bool):
                plug_type = 'bool'
            plug_type = shp_data.get('type', plug_type)
            enum = shp_data.get('enum')

            if plug_type == 'separator' or shp_data.get('sep') or shp_name.startswith('__'):
                self.add_plug(ctrl, shp_name, type='separator')
                continue

            # update ctrl plug build data
            _data = shp_data.get('driven', {})
            if not isinstance(_data, dict):
                self.log_warning('invalid data for driven shapes of "{}"'.format(shp_name))
                shp_data['driven'] = _data = {}

            shp_divs = self.get_divs(shp_data)

            for shp_driven in _data:
                for div in shp_divs:
                    shp_driven_div = shp_driven + div
                    plug = None
                    if shp_driven_div in plug_names:
                        for src in src_nodes:
                            if shp_driven_div in src:
                                plug = src[shp_driven_div]
                                break
                    if plug is None:
                        continue
                    _plug_type = plug.type_class()
                    if _plug_type is mx.Boolean:
                        plug_type = 'bool'
                    elif _plug_type is mx.Long:
                        plug_type = 'int'
                    elif _plug_type is mx.Enum:
                        plug_type = 'enum'
                        enum = []
                        fn = om.MFnEnumAttribute(plug.attribute())
                        for v in range(fn.getMin(), fn.getMax() + 1):
                            try:
                                name = fn.fieldName(v)
                                enum.append((v, name))
                            except:
                                pass

            # add channels div loop
            for div in shp_divs:
                shp_name_div = shp_name + div

                # forced plugs
                if shp_data.get('force'):
                    channels[shp_name_div] = self.add_plug(channel, shp_name_div, shp_name)

                # direct shape plugs
                if 'driven' not in shp_data:
                    if shp_name_div not in plug_names:
                        continue

                    # add channel
                    plug_chan = self.add_plug(channel, shp_name_div)
                    plug_ctrl = self.add_plug(ctrl, shp_name_div, type=plug_type, default=plug_default, enum=enum)
                    connect_blend_weighted(plug_ctrl, plug_chan)

                    channels[shp_name_div] = plug_chan

                # driven shape plugs
                if 'driven' in shp_data:
                    for shp_driven in shp_data['driven']:
                        shp_driven_div = shp_driven + div
                        if shp_driven_div not in plug_names:
                            continue

                        # add channel
                        plug_chan = self.add_plug(channel, shp_name_div)
                        plug_ctrl = self.add_plug(ctrl, shp_name_div, type=plug_type, default=plug_default, enum=enum)
                        connect_blend_weighted(plug_ctrl, plug_chan)

                        channels[shp_name_div] = plug_chan
                        break

                # set controller limits
                if shp_name_div in ctrl:
                    if 'min' in shp_data:
                        mc.addAttr(ctrl[shp_name_div].path(), e=1, min=shp_data['min'])
                    if 'max' in shp_data:
                        mc.addAttr(ctrl[shp_name_div].path(), e=1, max=shp_data['max'])

        # build shape buffer
        for shp_name, shp_data in iteritems(shapes):
            if not shp_data:
                shp_data = {}

            # check for weights
            weight_data = shp_data.get('weight', {})
            if not isinstance(weight_data, dict):
                self.log_warning('invalid weight data for channel "{}"'.format(shp_name))

            # connect loop
            shp_divs = self.get_divs(shp_data)

            for div in shp_divs:
                shp_name_div = shp_name + div
                if shp_name_div not in channels:
                    continue

                plug_chan = channels[shp_name_div]

                # connect weight
                for weight_shape, keys_data in iteritems(weight_data):
                    weight_shape_div = weight_shape + div
                    if weight_shape_div not in channels:
                        continue

                    kw = self.build_keys_kw(keys_data, mode='weight')
                    driven_curve = connect_driven_curve(channels[weight_shape_div], **kw)

                    plug_chan = connect_mult(plug_chan, driven_curve['output'])

                # connect channel to shapes
                if 'driven' in shp_data:
                    # connect driven shape
                    for shp_driven, keys_data in iteritems(shp_data['driven']):
                        shp_driven_div = shp_driven + div
                        if shp_driven_div not in plug_names:
                            continue

                        # build driven key
                        kw = self.build_keys_kw(keys_data)
                        driven_curve = connect_driven_curve(plug_chan, **kw)

                        if buffer[shp_driven_div]['src'] is None:
                            buffer[shp_driven_div]['src'] = driven_curve['output']
                        else:
                            buffer[shp_driven_div]['src'] = connect_add(buffer[shp_driven_div]['src'], driven_curve['output'])

                else:
                    # direct connect shape
                    if shp_name_div not in plug_names:
                        continue

                    if buffer[shp_name_div]['src'] is None:
                        buffer[shp_name_div]['src'] = plug_chan
                    else:
                        buffer[shp_name_div]['src'] = connect_add(buffer[shp_name_div]['src'], plug_chan)

        # combination shapes
        comb_buffer = {}

        comb_data = self.data.get('combos', self.data.get('combo', {}))
        if not isinstance(comb_data, dict):
            self.log_warning('invalid combo data')
            comb_data = {}

        for comb_shape, data in iteritems(comb_data):
            comb_drivers = data.get('drivers', {})
            if not comb_drivers:
                continue

            # do_src = 'src' in data

            for div in self.get_divs(data, strict=True):

                # get target shape
                comb_shape_div = comb_shape + div

                if comb_shape_div not in buffer:  # or not buffer[comb_shape_div]['src']:
                    continue

                for comb_driver in comb_drivers:
                    comb_driver_div = comb_driver + div
                    if comb_driver_div not in buffer or not buffer[comb_driver_div]['src']:
                        continue

                coeffs = {}
                i = 0

                for comb_driver, keys_data in iteritems(comb_drivers):
                    comb_driver_div = comb_driver + div

                    v0 = buffer[comb_driver_div]['src']
                    if comb_driver_div in comb_buffer:
                        v0 = comb_buffer[comb_driver_div]

                    # drive combo
                    kw = self.build_keys_kw(keys_data, mode='combo')

                    vmax = fmax = 0.0  # normalize drivers
                    for key, key_data in iteritems(kw['keys']):
                        if isinstance(key_data, dict):
                            v = key_data['v']
                        else:
                            v = key_data
                        if v > vmax:
                            vmax = v
                            fmax = key

                    driven_curve = connect_driven_curve(v0, **kw)

                    # normalized driver weight
                    driven_normed = driven_curve['output']
                    f = float(vmax) / float(fmax)
                    if f != 1:
                        driven_normed = connect_mult(driven_curve['output'], f)
                    coeffs[comb_driver_div] = f

                    # connect min
                    if i == 0:
                        driven_min = driven_normed
                    else:
                        driven_min = connect_expr('min(a, b)', a=driven_min, b=driven_normed)
                    i += 1

                for comb_driver in comb_drivers:
                    comb_driver_div = comb_driver + div

                    f = coeffs[comb_driver_div]
                    if f != 1:
                        sub = connect_mult(driven_min, -1 / f)
                    else:
                        sub = connect_mult(driven_min, -1)

                    # remove delta from driver
                    buffer[comb_driver_div]['add'].append(sub)

                    # TODO: réintégrer le mode récursif. mais au final je pense que ça ne devrait pas servir
                    # if do_src:
                    #     comb_buffer[comb_driver_div] = sub

                # add delta to target
                buffer[comb_shape_div]['add'].append(driven_min)
                comb_buffer[comb_shape_div] = driven_min

        # weighted shapes
        weight_data = self.data.get('weights', self.data.get('weight', {}))

        for weight_shape, data in iteritems(weight_data):

            for div in self.get_divs(data, strict=True):
                weight_shape_div = weight_shape + div

                if weight_shape_div not in buffer:
                    self.log_warning('invalid weight entry: target shape not available')
                    continue
                if not isinstance(data, dict):
                    self.log_warning('invalid weight entry: value error')
                    continue

                # read description
                weight_drivers = data.get('drivers', {})
                if not weight_drivers:
                    continue

                for weight_driver in weight_drivers:
                    weight_driver_div = weight_driver + div
                    if weight_driver_div not in buffer:
                        continue

                    kw = self.build_keys_kw(weight_drivers[weight_driver], mode='weight')
                    driven_curve = connect_driven_curve(buffer[weight_driver_div].get('src'), **kw)

                    buffer[weight_shape_div]['mult'].append(driven_curve['output'])

        # TODO: clamp ?

        # connect adds
        for shp_name in buffer:
            if buffer[shp_name]['add']:
                _op = mx.create_node(mx.tBlendWeighted)

                o = 0
                if buffer[shp_name]['src'] is not None:
                    buffer[shp_name]['src'] >> _op['input'][0]
                    o = 1

                for i, _add in enumerate(buffer[shp_name]['add']):
                    _add >> _op['input'][i + o]

                buffer[shp_name]['src'] = _op['output']

        # connect mults
        for shp_name in buffer:
            if buffer[shp_name]['src'] is not None and buffer[shp_name]['mult']:
                for _mult in buffer[shp_name]['mult']:
                    _op = connect_mult(buffer[shp_name]['src'], _mult)
                    buffer[shp_name]['src'] = _op

        # connect clamps
        # for shp_name in buffer:
        #     if buffer[shp_name]['src'] is not None and buffer[shp_name]['clamp']:
        #         # clamp = ClampFloat.create(chan, '_clamp')
        #         pass

        # connect to src
        for shp_name in buffer:
            if buffer[shp_name]['src'] is not None:
                for src_node in src_nodes:
                    if shp_name in src_node:
                        connect_blend_weighted(buffer[shp_name]['src'], src_node[shp_name])

    def add_plug(self, node, plug_name, type=None, default=None, enum=None):

        cls = self.PLUG_TYPES.get(type, mx.Double)

        if plug_name not in node:
            if cls == mx.Enum:
                node.add_attr(cls(plug_name, keyable=True, default=default, fields=enum))
            else:
                node.add_attr(cls(plug_name, keyable=True, default=default))

        return node[plug_name]

    PLUG_TYPES = {
        'float': mx.Double,
        'double': mx.Double,
        'bool': mx.Boolean,
        'int': mx.Long,
        'long': mx.Long,
        'enum': mx.Enum,
        'separator': mx.Divider
    }

    @staticmethod
    def get_divs(data, strict=False):
        divs = ['']
        if 'div' not in data:
            return divs

        if strict:
            del divs[:]

        if not isinstance(data['div'], (list, tuple)):
            return divs

        for _div in data['div']:
            if _div:
                _div = '_{}'.format(_div)
            divs.append(_div)

        return divs

    @staticmethod
    def build_keys_kw(keys_data, mode=None):

        kw = {
            'keys': {0: 0},
            'pre': 'linear',
            'post': 'linear',
            'key_style': None,
        }

        if mode == 'weight':
            kw['keys'] = {0: 1}

        # build values
        if isinstance(keys_data, dict):
            for k in keys_data:
                if isinstance(k, (float, int)):
                    kw['keys'][k] = keys_data[k]

        elif isinstance(keys_data, (float, int)):
            if mode == 'weight':
                kw['keys'][1] = float(keys_data)
            else:
                kw['keys'][float(keys_data)] = 1

        # update infinities
        if mode is None:
            fmin = min(kw['keys'])
            fmax = max(kw['keys'])
            if fmin == 0:
                kw['pre'] = 'constant'
            elif fmax == 0:
                kw['post'] = 'constant'

        # overrides
        if isinstance(keys_data, dict):
            if 'pre' in keys_data:
                kw['pre'] = keys_data['pre']
            if 'post' in keys_data:
                kw['post'] = keys_data['post']
            if 'tan' in keys_data:
                kw['key_style'] = keys_data['tan']

        return kw
