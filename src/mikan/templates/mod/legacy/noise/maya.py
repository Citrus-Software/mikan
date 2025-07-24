# coding: utf-8

from six import string_types

import mikan.maya.cmdx as mx

import mikan.maya.core as mk
from mikan.maya.lib.connect import *
from mikan.core.logger import create_logger

log = create_logger()


class Mod(mk.Mod):
    def run(self):

        # connected plug
        plug_in = self.node
        if not isinstance(plug_in, mx.Plug):
            if 'plug' not in self.data:
                raise mk.ModArgumentError('plug to connect undefined')
            plug = self.data['plug']
            if isinstance(plug, mx.Plug):
                plug_in = plug
            elif isinstance(plug, string_types):
                plug_in = mk.Nodes.get_node_plug(self.node, plug)

        if not isinstance(plug_in, mx.Plug):
            raise mk.ModArgumentError('plug to connect undefined')

        # noise
        noise_node = mx.create_node(mx.tNoise)
        noise_node['noiseType'] = 0  # perlin

        noise_in = self.data.get('amp', 1)
        if isinstance(noise_in, (int, float)):
            noise_out = connect_mult(noise_node['outColorR'], noise_in * 2)
            noise_out = connect_sub(noise_out, noise_in)
        elif isinstance(noise_in, mx.Plug):
            noise_out = connect_mult(noise_node['outColorR'], 2)
            noise_out = connect_sub(noise_out, 1)
            noise_out = connect_mult(noise_out, noise_in)
        else:
            raise mk.ModArgumentError('invalid amp')

        noise_offset = self.data.get('offset', 0)
        noise_freq = self.data.get('frequency', 1)

        time_out = connect_add(mx.encode('time1')['outTime'], noise_offset)
        connect_mult(time_out, noise_freq, noise_node['time'])

        # result
        noise_out >> plug_in

        self.set_id(noise_node, 'noise')

