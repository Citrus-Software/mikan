# coding: utf-8

import meta_nodal_py as kl

import mikan.tangerine.core as mk
from mikan.tangerine.lib.commands import add_plug
from mikan.tangerine.lib.connect import *
from mikan.tangerine.lib.rig import *
from mikan.core import flatten_list
from mikan.core.logger import create_logger

log = create_logger()


class Mod(mk.Mod):
    def run(self):

        # connected plug
        plug_in = self.node
        if not kl.is_plug(plug_in):
            if 'plug' not in self.data:
                raise mk.ModArgumentError('plug to connect undefined')
            plug = self.data['plug']
            if kl.is_plug(plug):
                plug_in = plug
            elif isinstance(plug, str):
                plug_in = mk.Nodes.get_node_plug(self.node, plug)

        if not kl.is_plug(plug_in):
            raise mk.ModArgumentError('plug to connect undefined')

        # noise
        noise_node = kl.Noise(plug_in.get_node(), 'noise')

        noise_in = self.data.get('amp', 1)
        noise_out = noise_node.output
        if kl.is_plug(noise_in) or noise_in != 1:
            noise_out = connect_mult(noise_node.output, noise_in)

        noise_offset = self.data.get('offset', 0)
        noise_freq = self.data.get('frequency', 1)

        time = kl.CurrentFrame(noise_node, 'time')
        time_out = connect_add(time.result, noise_offset)
        time_out = connect_add(time_out, 0.5)
        connect_mult(time_out, noise_freq, noise_node.input)

        # result
        plug_in.connect(noise_out)

        self.set_id(noise_node, 'noise')
