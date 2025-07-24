# coding: utf-8

from six import iteritems
from collections import OrderedDict

from mikan.maya import cmds as mc
import mikan.maya.cmdx as mx

import mikan.maya.core as mk
from mikan.core.logger import create_logger
from mikan.maya.lib.connect import connect_driven_curve, find_anim_curve, connect_mult, connect_expr

log = create_logger()


class Mod(mk.Mod):

    def run(self):

        # get nodes
        driver = self.node
        if 'node' in self.data:
            driver = self.data['node']

        # driver plug
        if not isinstance(driver, mx.Plug):
            driver = self.data.get('plug')
            if driver is None:
                raise mk.ModArgumentError('driver plug undefined')
            if not isinstance(driver, mx.Plug):
                driver = mk.Nodes.get_node_plug(self.node, driver)

        # get driven plugs data
        driven_plugs = OrderedDict()

        for key, value in iteritems(self.data):
            if isinstance(key, mx.Plug) and isinstance(value, dict):
                driven_plugs[key] = value
            elif isinstance(key, mx.Node) and isinstance(value, dict):
                for _key, _value in iteritems(value):
                    _plug = mk.Nodes.get_node_plug(key, _key)
                    if isinstance(_plug, mx.Plug) and isinstance(_value, dict):
                        driven_plugs[_plug] = _value

        driven_data = self.data.get('driven', {})
        for key, value in iteritems(driven_data):
            if isinstance(key, mx.Node) and isinstance(value, dict):
                for plug, keys in iteritems(value):
                    driven = mk.Nodes.get_node_plug(key, plug)
                    if isinstance(keys, dict):
                        driven_plugs[driven] = keys

            elif isinstance(key, mx.Plug) and isinstance(value, dict):
                driven_plugs[key] = value

        if not driven_plugs:
            raise mk.ModArgumentError('driven plugs undefined')

        # check data
        for driven, keys in driven_plugs.items():
            if not isinstance(driven, mx.Plug):
                raise mk.ModArgumentError('invalid driven plug')
            if not isinstance(keys, dict):
                raise mk.ModArgumentError('invalid keys')

        # weight
        weight = None
        if 'weight' in self.data and 'driven' not in self.data:
            weight = self.data['weight']
            if not isinstance(weight, mx.Plug):
                raise mk.ModArgumentError('invalid weight plug')

        for driven, keys in iteritems(driven_plugs):
            if 'weight' in keys and not isinstance(keys['weight'], mx.Plug):
                raise mk.ModArgumentError('invalid weight plug for {}'.format(driven.path()))

        # branch reverse?
        tpl = self.get_template()
        do_flip = tpl.do_flip() if tpl else False

        # scale
        scale = self.data.get('scale', 1)
        if self.source and 'gem_scale' in self.source:
            scale *= self.source['gem_scale'].read()

        # drive loop
        for driven, keys in iteritems(driven_plugs):
            plug_name = driven.name(long=True)

            cv = None
            pre = keys.get('pre', 'linear')
            post = keys.get('post', 'linear')
            tan = keys.get('tan')

            flip = 1
            if do_flip and keys.get('flip', False):
                flip = -1

            for key, data in iteritems(keys):
                # log.debug('{}->{}.{} : {} {}'.format(driver, node, plug, key, data))
                if not isinstance(key, (int, float)):
                    continue

                if isinstance(data, (int, float)):
                    data = {'v': data}
                    if tan is not None:
                        data['tan'] = tan
                elif isinstance(data, dict):
                    if 'value' in data:
                        data['v'] = data.pop('value')

                if data['v'] is None:
                    continue
                data['v'] *= flip
                if 'iy' in data:
                    data['iy'] *= flip
                if 'oy' in data:
                    data['oy'] *= flip

                if plug_name.startswith('translate'):
                    data['v'] *= scale
                    if 'iy' in data:
                        data['iy'] *= scale
                    if 'oy' in data:
                        data['oy'] *= scale

                # add key
                cv = connect_driven_curve(driver, driven, {key: data})

            # find driven curve
            if not cv:
                cv = find_anim_curve(driven, driver)

            if cv:
                infinity = {'constant': 0, 'linear': 1, 'cycle': 2, 'offset': 3, 'oscillate': 4}
                cv['preInfinity'] = infinity[pre]
                cv['postInfinity'] = infinity[post]

                # connect weight
                w = weight
                if 'weight' in keys:
                    w = keys['weight']
                    if weight is not None:
                        w = connect_mult(weight, w)

                if w is not None:
                    driven_input = cv['output'].output(plug=True)

                    keys = mc.keyframe(str(cv), q=1, vc=1, fc=1)
                    keys = dict(zip(*[iter(keys)] * 2))
                    connect_expr('d = lerp(dv, v, w)', dv=keys.get(0, 0), v=cv['output'], w=w, d=driven_input)

                # register
                if 'gem_id' not in cv:
                    self.set_id(cv, 'drive.{}'.format(driver.name(long=False)))

        self.set_id(driver.node(), 'drive')
