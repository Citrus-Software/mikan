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

        # plugs to connect
        plugs = []

        if 'nodes' in self.data:
            nodes = self.data['nodes']
            if isinstance(nodes, (list, tuple)):
                plugs = list(nodes)
            else:
                plugs.append(nodes)
        else:
            if isinstance(self.node, (list, tuple)):
                plugs = list(self.node)
            else:
                plugs.append(self.node)

        nodes = [node for node in plugs if isinstance(node, kl.Node)]
        if nodes:
            attrs = []
            if 'plug' in self.data and isinstance(self.data['plug'], str):
                attrs.append(self.data['plug'])
            elif 'plugs' in self.data and isinstance(self.data['plugs'], (list, tuple)):
                for attr in self.data['plugs']:
                    if isinstance(attr, str):
                        attrs.append(attr)
            for attr in attrs:
                for node in nodes:
                    plugs.append(mk.Nodes.get_node_plug(node, attr))

        plugs = [plug for plug in plugs if kl.is_plug(plug)]
        if not plugs:
            raise mk.ModArgumentError('plug to connect undefined')

        # args
        do_flip = False
        if self.data.get('flip', False):
            tpl = self.get_template()
            if tpl.do_flip():
                do_flip = True

        inputs = []
        if 'input' in self.data:
            _input = self.data.get('input')
            if _input is not None:
                inputs.append(_input)
        elif 'inputs' in self.data:
            inputs = self.data.get('inputs', [])
        if not inputs:
            raise mk.ModArgumentError('input list not valid')

        # time
        for i, _input in enumerate(inputs):
            if not isinstance(_input, str):
                continue
            if _input == 'time' or _input == 'frame':
                time = kl.CurrentFrame(plugs[0].get_node(), 'time')
                inputs[i] = time.result

        op = self.data.get('op', self.data.get('operation'))
        if op and op not in {'add', 'sub', 'mult', 'div', 'remap', 'reverse'}:
            raise mk.ModArgumentError(f'invalid operator ({op})')
        if op == 'remap':
            if not all(x in self.data for x in {'min_old', 'max_old', 'min', 'max'}):
                raise mk.ModArgumentError('remap keyword missing (min_old, max_old, min, max)')

        # checks
        n = len(inputs)
        if not n:
            raise mk.ModArgumentError('no input to connect')
        if not all([kl.is_plug(i) or isinstance(i, (float, int)) for i in inputs]):
            raise mk.ModArgumentError('invalid inputs!')

        for plug in plugs:
            n = len(inputs)
            if plug.get_input() is not None:
                n += 1

            if n > 1 and op is None:
                raise mk.ModArgumentError('too much inputs or no operator defined')
            if n != 1 and op in {None, 'reverse', 'remap'}:
                raise mk.ModArgumentError(f'invalid number of inputs to connect ({n}) with operator {op}')
            if n != 2 and op in {'add', 'sub', 'mult', 'div'}:
                raise mk.ModArgumentError(f'invalid number of inputs to connect ({n}) or invalid operator ({op})')

        # connect loop
        for plug_in in plugs:

            # bridge connection
            input0 = plug_in.get_input()

            # clamp
            if 'clamp' in self.data:
                clamp = self.data['clamp']
                if not isinstance(clamp, list) and not len(clamp) == 2:
                    raise mk.ModArgumentError('clamp is not valid')
                _c = kl.ClampFloat(plug_in.get_node(), '_clamp')
                _c.min.set_value(min(clamp))
                _c.max.set_value(max(clamp))
                safe_connect(_c.output, plug_in)
                plug_in = _c.input

            # branch reverse?
            if do_flip:
                _f = connect_mult(1, -1, plug_in)
                plug_in = _f.get_node().input1

            # inputs data
            _inputs = []
            if input0 is not None:
                _inputs.append(input0)
            _inputs += inputs

            # connect
            result = None

            if op is None:
                safe_connect(_inputs[0], plug_in)
            elif op == 'reverse':
                result = connect_reverse(_inputs[0], plug_in)
            elif op == 'remap':
                result = connect_remap(_inputs[0], self.data['min_old'], self.data['max_old'], self.data['min'], self.data['max'], plug_out=plug_in)
            elif op == 'add':
                result = connect_add(_inputs[0], _inputs[1], plug_in)
            elif op == 'sub':
                result = connect_sub(_inputs[0], _inputs[1], plug_in)
            elif op == 'mult':
                result = connect_mult(_inputs[0], _inputs[1], plug_in)
            elif op == 'div':
                result = connect_div(_inputs[0], _inputs[1], plug_in)

            # registering
            if result:
                node = result.get_node()
                if op and not node.get_plug('output'):
                    add_plug(node, 'output', float)
                    node.output.connect(result)

                self.set_id(node, 'connect')
