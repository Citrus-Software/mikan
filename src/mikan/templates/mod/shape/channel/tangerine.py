# coding: utf-8

from ast import literal_eval

import meta_nodal_py as kl

import mikan.tangerine.core as mk
from mikan.tangerine.lib.commands import *
from mikan.tangerine.lib.connect import *
from mikan.core.logger import create_logger

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
            if isinstance(src, kl.SceneGraphNode):
                src_nodes.append(src)

        if not src_nodes:
            raise mk.ModArgumentError('no source defined')

        # get valid channel plugs
        plug_names = []

        for node in src_nodes:
            for plug in node.get_dynamic_plugs():
                if plug.get_input():
                    continue
                if len(plug.get_outputs()) == 0:
                    continue
                if plug.get_name() in plug_names:
                    continue

                plug_names.append(plug.get_name())

        # check controller
        ctrl = self.data.get('target')
        if not ctrl:
            raise mk.ModArgumentError('no controller defined')

        # check rules
        if 'shapes' not in self.data or not isinstance(self.data['shapes'], (list, dict)):
            raise mk.ModArgumentError('no shapes defined')

        # face buffer
        buffer = {}

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
            _shapes = {}
            for shp in shapes:
                if isinstance(shp, dict):
                    shp_name = list(shp)[0]
                    _shapes[shp_name] = shp[shp_name]
                else:
                    _shapes[shp] = {}
            shapes = _shapes

        # add plugs to controller
        for shp_name, shp_data in shapes.items():
            if shp_data is None:
                shp_data = {}

            plug_value = shp_data.get('default', shp_data.get('dv'))
            plug_type = 'float'
            if isinstance(plug_value, bool):
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
                for shp_driven, keys_data in shp_data.get('driven', {shp_name: None}).items():
                    shp_driven_sfx = shp_driven + sfx
                    plug = None
                    if shp_driven_sfx in plug_names:
                        for src in src_nodes:
                            plug = src.get_dynamic_plug(shp_driven_sfx)
                            if plug:
                                break
                    if plug is None:
                        continue
                    _plug_type = plug.get_value()
                    _plug_info = plug.get_all_user_infos()
                    if isinstance(_plug_type, bool):
                        plug_type = 'bool'
                    elif isinstance(_plug_type, int):
                        plug_type = 'int'
                        if 'enum' in _plug_info:
                            plug_type = 'enum'
                            enum = literal_eval(_plug_info['enum'])

            # sfx loop
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

                    if not buffer[shp_name_sfx]['src']:
                        buffer[shp_name_sfx]['src'] = plug_chan
                    else:
                        buffer[shp_name_sfx]['src'] = connect_add(buffer[shp_name_sfx]['src'], plug_chan)

                    # connect ctrl to channel
                    plug_ctrl = self.add_plug(ctrl, shp_name_sfx, default=plug_value, type=plug_type, enum=enum)
                    connect_additive(plug_ctrl, plug_chan)

                # driven shape plugs
                if 'driven' in shp_data:

                    plug_chan = None
                    for shp_driven, keys_data in shp_data['driven'].items():
                        shp_driven_sfx = shp_driven + sfx
                        if shp_driven_sfx not in plug_names:
                            continue

                        # add channel
                        plug_chan = self.add_plug(channel, shp_name_sfx)

                        # driven curve
                        an_pre = 'linear'
                        an_post = 'linear'
                        tan_mode = None

                        keys = {0: 0}
                        if isinstance(keys_data, dict):
                            if 'pre' in keys_data:
                                an_pre = keys_data['pre']
                            if 'post' in keys_data:
                                an_post = keys_data['post']
                            if 'tan' in keys_data:
                                tan_mode = keys_data['tan']
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

                        driven_curve = connect_driven_curve(plug_chan, None, keys, pre=an_pre, post=an_post, tangent_mode=tan_mode)

                        if not buffer[shp_driven_sfx]['src']:
                            buffer[shp_driven_sfx]['src'] = driven_curve.result
                        else:
                            buffer[shp_driven_sfx]['src'] = connect_add(buffer[shp_driven_sfx]['src'], driven_curve.result)

                    # connect ctrl to channel
                    if plug_chan is not None:
                        plug_ctrl = self.add_plug(ctrl, shp_name_sfx, default=plug_value, type=plug_type, enum=enum)
                        connect_additive(plug_ctrl, plug_chan)

                # set controller limits
                plug_ctrl = ctrl.get_dynamic_plug(shp_name_sfx)
                if plug_ctrl:
                    set_plug(plug_ctrl, min_value=shp_data.get('min'), max_value=shp_data.get('max'))

        # combos
        cmb_buffer = {}

        cmb_data = self.data.get('combos', self.data.get('combo', {}))
        for cmb_name, data in cmb_data.items():
            cmb_drivers = data.get('drivers', {})
            if not cmb_drivers:
                continue

            do_src = data.get('src', False)

            for sfx in data.get('div', ['']):
                if sfx:
                    sfx = '_' + sfx

                cmb_name_sfx = cmb_name + sfx

                if cmb_name_sfx not in buffer:  # or not buffer[cmb_name_sfx]['src']:
                    continue

                for cmb_driver, drv_data in cmb_drivers.items():
                    cmb_driver_sfx = cmb_driver + sfx
                    if cmb_driver_sfx not in buffer or not buffer[cmb_driver_sfx]['src']:
                        continue

                subs = []
                ans = []

                i = 0
                for cmb_driver, keys_data in cmb_drivers.items():
                    cmb_driver_sfx = cmb_driver + sfx

                    v0 = buffer[cmb_driver_sfx]['src']
                    if cmb_driver_sfx in cmb_buffer:
                        v0 = cmb_buffer[cmb_driver_sfx]

                    sub = connect_mult(0, -1, p=channel)
                    sub = sub.get_node().input1
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

                    for key, key_data in keys.items():
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
                    driven_curve.rename('_driven_curve' + str(i))
                    ans.append(driven_curve.result)

                    # maximum at
                    f = float(fmax) / float(vmax)
                    if f != 1:
                        mul = connect_mult(driven_curve.result, f)
                        sub.connect(mul)
                        subs[-1] = mul.get_node().input1

                    # connect min
                    if i > 0:
                        _cond = kl.Condition(node, '_if')
                        _isge = kl.IsGreaterOrEqual(node, '_isge')
                        _cond.condition.connect(_isge.output)
                        _isge.input2.connect(ans[-1])
                        _isge.input1.connect(ans[-2])

                        _cond.input2.connect(ans[-2])
                        _cond.input1.connect(ans[-1])
                        ans[-1] = _cond.output

                        for sub in subs:
                            sub.connect(_cond.output)
                    i += 1

                    # remove delta from driver
                    buffer[cmb_driver_sfx]['add'].append(sub.get_node().output)

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
        # for wt_name, data in wt_data.items():
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
        #         driven_curve = DrivenCurveFloatNode(chan, '_curve')
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
        #         driven_curve.driver.connect(src)
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
        # for cp_name, data in cp_data.items():
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
                _op = kl.Add(node.get_parent(), '_add')
                _op.add_inputs(len(buffer[shp_name]['add']) - 1)

                o = 1
                if buffer[shp_name]['src']:
                    _op.input1.connect(buffer[shp_name]['src'])
                    o = 2

                for i, _add in enumerate(buffer[shp_name]['add']):
                    _op_i = _op.get_plug('input{0}'.format(i + o))
                    _op_i.connect(_add)

                buffer[shp_name]['src'] = _op.output

        # connect mults
        for shp_name in buffer:
            if buffer[shp_name]['src'] and buffer[shp_name]['mult']:
                for _mult in buffer[shp_name]['mult']:
                    _op = connect_mult(buffer[shp_name]['src'], _mult)
                    buffer[shp_name]['src'] = _op

        # connect clamps
        for shp_name in buffer:
            if buffer[shp_name]['src'] and buffer[shp_name]['clamp']:
                # clamp = ClampFloat(chan, '_clamp')
                pass

        # connect to src
        for shp_name in buffer:
            if buffer[shp_name]['src']:
                for src_node in src_nodes:
                    # if src_node.hasAttr(shp_name):
                    if hasattr(src_node, shp_name):
                        # connect_additive(buffer[shp_name]['src'], src_node.attr(shp_name))
                        connect_additive(buffer[shp_name]['src'], src_node.get_dynamic_plug(shp_name))

    def add_plug(self, node, plug_name, default=None, type='float', enum=None):

        plug_type = self.PLUG_TYPES.get(type, float)
        plug = node.get_dynamic_plug(plug_name)
        if plug:
            return plug

        if type == 'separator':
            pass
        else:
            plug = add_plug(node, plug_name, plug_type, k=True, default_value=default, enum=enum)
            return plug

    PLUG_TYPES = {
        'float': float,
        'double': float,
        'bool': bool,
        'int': int,
        'long': int,
        'enum': int,
        'separator': 'separator'
    }
