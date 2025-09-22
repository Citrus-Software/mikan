# coding: utf-8

import meta_nodal_py as kl

from mikan.core.logger import create_logger
import mikan.tangerine.core as mk
from mikan.tangerine.lib.commands import *
from mikan.tangerine.lib.connect import *

log = create_logger()


class Mod(mk.Mod):

    def run(self):

        # get nodes
        driver = self.node
        if 'node' in self.data:
            driver = self.data['node']

        # driver plug
        if not kl.is_plug(driver):
            driver = self.data.get('plug')
            if not driver:
                raise mk.ModArgumentError('driver plug undefined')
            if not kl.is_plug(driver):
                driver = mk.Nodes.get_node_plug(self.node, driver)

        # get driven plugs data
        driven_plugs = {}

        for key, value in self.data.items():
            if kl.is_plug(key) and isinstance(value, dict):
                driven_plugs[key] = value
            elif isinstance(key, kl.Node) and isinstance(value, dict):
                for _key, _value in value.items():
                    _plug = mk.Nodes.get_node_plug(key, _key)
                    if kl.is_plug(_plug) and isinstance(_value, dict):
                        driven_plugs[_plug] = _value

        driven_data = self.data.get('driven', {})
        for key, value in driven_data.items():
            if isinstance(key, kl.Node) and isinstance(value, dict):
                for plug, keys in value.items():
                    driven = mk.Nodes.get_node_plug(key, plug)
                    if isinstance(keys, dict):
                        driven_plugs[driven] = keys

            elif kl.is_plug(key) and isinstance(value, dict):
                driven_plugs[key] = value

        if not driven_plugs:
            raise mk.ModArgumentError('driven plugs undefined')

        # weight
        weight = None
        if 'weight' in self.data and 'driven' not in self.data:
            weight = self.data['weight']
            if not kl.is_plug(weight):
                raise mk.ModArgumentError('invalid weight plug')

        for driven, keys in driven_plugs.items():
            if 'weight' in keys and not kl.is_plug(keys['weight']):
                raise mk.ModArgumentError('invalid weight plug for {}'.format(driven.path()))

        # check data
        for driven, keys in driven_plugs.items():
            if not kl.is_plug(driven):
                raise mk.ModArgumentError('invalid driven plug')
            if not isinstance(keys, dict):
                raise mk.ModArgumentError('invalid keys')

        # branch reverse?
        tpl = self.get_template()
        do_flip = tpl.do_flip() if tpl else False

        # scale
        scale = self.data.get('scale', 1)
        if self.source and self.source.get_dynamic_plug('gem_scale'):
            scale *= self.source.gem_scale.get_value()

        # drive loop
        crv_node = None
        for driven, keys in driven_plugs.items():

            node = driven.get_node()
            plug = driven.get_name()

            pre = keys.get('pre', 'linear')
            post = keys.get('post', 'linear')
            tan = keys.get('tan')

            flip = 1
            if do_flip and keys.get('flip', False):
                flip = -1

            for key, data in keys.items():
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

                if node.get_name() == 'translate' and plug in 'xyz':
                    data['v'] *= scale
                    if 'iy' in data:
                        data['iy'] *= scale
                    if 'oy' in data:
                        data['oy'] *= scale

                # add key
                crv_node = connect_driven_curve(driver, driven, {key: data}, pre=pre, post=post)

            # connect weight
            w = weight
            if 'weight' in keys:
                w = keys['weight']
                if weight is not None:
                    w = connect_mult(weight, w)

            if w is not None:
                driven_input = crv_node.result.get_outputs()[0]

                dv = 0
                curve_value = crv_node.curve.get_value()
                if curve_value.has_key_at(0):
                    dv = curve_value.get_key_value_at(0)
                connect_expr('d = lerp(dv, v, w)', dv=dv, v=crv_node.result, w=w, d=driven_input)

            # register
            if not crv_node.get_dynamic_plug('output'):
                add_plug(crv_node, 'output', float)
            crv_node.output.connect(crv_node.result)
            self.set_id(crv_node, 'drive.{}'.format(driver.get_name()))

        self.set_id(driver.get_node(), 'drive')
