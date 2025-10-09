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
            _shapes = ordered_dict()
            for shp in shapes:
                if isinstance(shp, dict):
                    shp_name = list(shp)[0]
                    _shapes[shp_name] = shp[shp_name]
                else:
                    _shapes[shp] = {}
            shapes = _shapes

        # add plugs to controller
        for shp_name, shp_data in iteritems(shapes):
            if shp_data is None:
                shp_data = {}

            plug_default = shp_data.get('default', shp_data.get('dv'))
            plug_type = 'float'
            if isinstance(plug_default, bool):
                plug_type = 'bool'
            plug_type = shp_data.get('type', plug_type)
            enum = shp_data.get('enum')

            if plug_type == 'separator' or shp_data.get('sep') or shp_name.startswith('__'):
                self.add_plug(ctrl, shp_name, type='separator')
                continue

            shp_divs = ['']
            if 'div' in shp_data:
                for _div in shp_data['div']:
                    if _div:
                        _div = '_{}'.format(_div)
                    shp_divs.append(_div)

            # update ctrl plug data
            for sfx in shp_divs:
                for shp_driven, keys_data in iteritems(shp_data.get('driven', {shp_name: None})):
                    shp_driven_sfx = shp_driven + sfx
                    plug = None
                    if shp_driven_sfx in plug_names:
                        for src in src_nodes:
                            if shp_driven_sfx in src:
                                plug = src[shp_driven_sfx]
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

            # sfx connect loop
            for sfx in shp_divs:
                shp_name_sfx = shp_name + sfx

                # forced plugs
                if shp_data.get('force'):
                    self.add_plug(channel, shp_name_sfx, shp_name)

                # shape plugs
                if 'driven' not in shp_data:
                    if shp_name_sfx not in plug_names:
                        continue

                    # add channel
                    plug_chan = self.add_plug(channel, shp_name_sfx)

                    if buffer[shp_name_sfx]['src'] is None:
                        buffer[shp_name_sfx]['src'] = plug_chan
                    else:
                        buffer[shp_name_sfx]['src'] = connect_add(buffer[shp_name_sfx]['src'], plug_chan)

                    # connect ctrl to channel
                    plug_ctrl = self.add_plug(ctrl, shp_name_sfx, type=plug_type, default=plug_default, enum=enum)
                    connect_blend_weighted(plug_ctrl, plug_chan)

                # driven shape plugs
                if 'driven' in shp_data:

                    plug_chan = None
                    for shp_driven, keys_data in iteritems(shp_data['driven']):
                        shp_driven_sfx = shp_driven + sfx
                        if shp_driven_sfx not in plug_names:
                            continue

                        # add channel
                        plug_chan = self.add_plug(channel, shp_name_sfx)

                        # build driven key
                        an_pre = 'linear'
                        an_post = 'linear'
                        key_style = None

                        keys = {0: 0}
                        if isinstance(keys_data, dict):
                            if 'pre' in keys_data:
                                an_pre = keys_data['pre']
                            if 'post' in keys_data:
                                an_post = keys_data['post']
                            if 'tan' in keys_data:
                                key_style = keys_data['tan']
                            keys.update(keys_data)
                        else:
                            keys[float(keys_data)] = 1

                        floats = [key for key in keys if isinstance(key, (int, float))]
                        fmin = min(floats)
                        fmax = max(floats)
                        if fmin == 0:
                            an_pre = 'constant'
                        elif fmax == 0:
                            an_post = 'constant'

                        driven_curve = connect_driven_curve(plug_chan, keys=keys, pre=an_pre, post=an_post, key_style=key_style)

                        if buffer[shp_driven_sfx]['src'] is None:
                            buffer[shp_driven_sfx]['src'] = driven_curve['output']
                        else:
                            buffer[shp_driven_sfx]['src'] = connect_add(buffer[shp_driven_sfx]['src'], driven_curve['output'])

                    # connect ctrl to channel
                    if plug_chan is not None:
                        plug_ctrl = self.add_plug(ctrl, shp_name_sfx, type=plug_type, default=plug_default, enum=enum)
                        connect_blend_weighted(plug_ctrl, plug_chan)

                # set controller limits
                if shp_name_sfx in ctrl:
                    if 'min' in shp_data:
                        mc.addAttr(ctrl[shp_name_sfx].path(), e=1, min=shp_data['min'])
                    if 'max' in shp_data:
                        mc.addAttr(ctrl[shp_name_sfx].path(), e=1, max=shp_data['max'])

        # combos
        cmb_buffer = {}

        cmb_data = self.data.get('combos', self.data.get('combo', {}))
        for cmb_name, data in iteritems(cmb_data):
            cmb_drivers = data.get('drivers', {})
            if not cmb_drivers:
                continue

            do_src = 'src' in data

            for sfx in data.get('div', ['']):
                if sfx:
                    sfx = '_' + sfx

                cmb_name_sfx = cmb_name + sfx

                if cmb_name_sfx not in buffer:  # or not buffer[cmb_name_sfx]['src']:
                    continue

                for cmb_driver, drv_data in iteritems(cmb_drivers):
                    cmb_driver_sfx = cmb_driver + sfx
                    if cmb_driver_sfx not in buffer or not buffer[cmb_driver_sfx]['src']:
                        continue

                subs = []
                ans = []

                i = 0
                for cmb_driver, keys_data in iteritems(cmb_drivers):
                    cmb_driver_sfx = cmb_driver + sfx

                    v0 = buffer[cmb_driver_sfx]['src']
                    if cmb_driver_sfx in cmb_buffer:
                        v0 = cmb_buffer[cmb_driver_sfx]

                    sub = connect_mult(0, -1)
                    sub = sub.node()['input1']
                    subs.append(sub)

                    # drive combo
                    vmax = 0.
                    fmax = 0.

                    keys = {0: 0}
                    if isinstance(keys_data, dict):
                        if 'pre' in keys_data:
                            del (keys_data['pre'])
                        if 'post' in keys_data:
                            del (keys_data['post'])
                        keys.update(keys_data)
                    else:
                        keys[float(keys_data)] = 1

                    for key, key_data in iteritems(keys):
                        if isinstance(key_data, dict):
                            v = key_data['v']
                        else:
                            v = key_data
                        if v > vmax:
                            vmax = v
                            fmax = key

                    _pre = None
                    _post = None
                    if min(keys) >= 0:
                        _pre = 'constant'
                    elif max(keys) <= 0:
                        _post = 'constant'

                    driven_curve = connect_driven_curve(v0, sub, keys, pre=_pre, post=_post)
                    ans.append(driven_curve['output'])

                    # maximum at
                    f = float(fmax) / float(vmax)
                    if f != 1:
                        mul = connect_mult(driven_curve['output'], f)
                        sub.disconnect(destination=False)
                        mul >> sub
                        subs[-1] = mul.node()['input1']

                    # connect min
                    if i > 0:
                        _if = connect_expr('b>=a ? a : b', a=ans[-1], b=ans[-2])
                        ans[-1] = _if
                        for sub in subs:
                            _if >> sub
                    i += 1

                    # remove delta from driver
                    buffer[cmb_driver_sfx]['add'].append(sub.node()['output'])

                    if do_src:
                        # je sais plus trop à quoi ça sert ça. ça devait être le mode recursif on/off
                        cmb_buffer[cmb_driver_sfx] = buffer[cmb_driver_sfx]['add'][-1]

                # add delta to target
                buffer[cmb_name_sfx]['add'].append(ans[-1])
                cmb_buffer[cmb_name_sfx] = ans[-1]

        # # weight
        # wt_data = {}
        # if 'weights' in self.data:
        #     wt_data = self.data['weights']
        # if 'weight' in self.data:
        #     wt_data = self.data['weight']
        #
        # for wt_name, data in iteritems(wt_data):
        #
        #     # read description
        #     do_rate = True
        #     do_key = False
        #     try:
        #         rate = float(rule[1][1])
        #     except:
        #         keys = self.parse_keys(rule[1][1].split(','))
        #         do_key = True
        #
        #     try:
        #         src = buffer[rule[1][0]]['src']
        #         vs = [buffer[x]['src'] for x in rule[1][2].split(',')]
        #     except:
        #         do_rate = False
        #
        #     # connect
        #     if do_rate:
        #         driven_curve = DrivenCurveFloatNode.create(chan, '_curve')
        #         driven_curve.pre_cycle_mode.set_int(0)
        #         driven_curve.post_cycle_mode.set_int(0)
        #
        #         curve_keys = [[1, 0], [rate, 10]]
        #         if do_key:
        #             curve_keys = []
        #             for k in keys:
        #                 curve_keys.append((k['v'], k['f']))
        #                 # keyTangent(an, lock=False)
        #                 # if k.has_key('itt'): keyTangent(an, f=[k['f']], itt=k['itt'], ott=k['ott'])
        #                 # if k.has_key('ia'): keyTangent(an, f=[k['f']], inAngle=k['ia'], outAngle=k['oa'])
        #
        #         driven_curve.curve.set_value(animcurves.create_curve_Float_linear(curve_keys))
        #         driven_curve.driver.connect(src, True)
        #
        #         for attr in rule[1][2].split(','):
        #             buffer[attr]['mult'].append(driven_curve.result)
        #
        # # clamp
        # cp_data = {}
        # if 'clamps' in self.data:
        #     cp_data = self.data['clamps']
        # if 'clamp' in self.data:
        #     cp_data = self.data['clamp']
        #
        # for cp_name, data in iteritems(cp_data):
        #
        #     # read description
        #     do_clamp = True
        #     try:
        #         val = float(rule[1][1])
        #         [buffer[x]['src'] for x in rule[1][0].split(',')]
        #     except:
        #         do_clamp = False
        #
        #     # connect
        #     if do_clamp:
        #         for attr in rule[1][0].split(','):
        #             if val < 0:
        #                 buffer[attr]['clamp'][0] = val
        #             elif val > 0:
        #                 buffer[attr]['clamp'][1] = val

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
        for shp_name in buffer:
            if buffer[shp_name]['src'] is not None and buffer[shp_name]['clamp']:
                # clamp = ClampFloat.create(chan, '_clamp')
                pass

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
