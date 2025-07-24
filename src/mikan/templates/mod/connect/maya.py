# coding: utf-8

from six import string_types

import mikan.maya.cmdx as mx

import mikan.maya.core as mk
from mikan.maya.lib.connect import *
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

        nodes = [node for node in plugs if isinstance(node, mx.Node)]
        if nodes:
            attrs = []
            if 'plug' in self.data and isinstance(self.data['plug'], string_types):
                attrs.append(self.data['plug'])
            elif 'plugs' in self.data and isinstance(self.data['plugs'], (list, tuple)):
                for attr in self.data['plugs']:
                    if isinstance(attr, string_types):
                        attrs.append(attr)
            for attr in attrs:
                for node in nodes:
                    plugs.append(mk.Nodes.get_node_plug(node, attr))

        plugs = [plug for plug in plugs if isinstance(plug, mx.Plug)]
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

        if 'time' in inputs:
            i = inputs.index('time')
            inputs[i] = mx.encode('time1')['outTime']
        if 'frame' in inputs:
            i = inputs.index('frame')
            inputs[i] = mx.encode('time1')['outTime']

        op = self.data.get('op', self.data.get('operation'))
        if op and op not in {'add', 'sub', 'mult', 'div', 'remap', 'reverse'}:
            raise mk.ModArgumentError('invalid operator ({})'.format(op))
        if op == 'remap':
            if not all(x in self.data for x in {'min_old', 'max_old', 'min', 'max'}):
                raise mk.ModArgumentError('remap keyword missing (min_old, max_old, min, max)')

        # checks
        n = len(inputs)
        if not n:
            raise mk.ModArgumentError('no input to connect')
        if not all([isinstance(i, (mx.Plug, float, int)) for i in inputs]):
            raise mk.ModArgumentError('invalid inputs!')

        for plug in plugs:
            n = len(inputs)
            if plug.input() is not None:
                n += 1

            if n > 1 and op is None:
                raise mk.ModArgumentError('too much inputs or no operator defined')
            if n != 1 and op in {None, 'reverse', 'remap'}:
                raise mk.ModArgumentError('invalid number of inputs to connect ({}) with operator {}'.format(n, op))
            if n != 2 and op in {'add', 'sub', 'mult', 'div'}:
                raise mk.ModArgumentError('invalid number of inputs to connect ({}) or invalid operator ({})'.format(n, op))

        # connect loop
        for plug_in in plugs:

            # bridge connection
            input0 = plug_in.input(plug=True)
            if isinstance(input0, mx.Plug):
                if input0.node().is_a(mx.tUnitConversion):
                    _input = input0.node()['input'].input(plug=True)
                    input0 = _input

            # clamp
            if 'clamp' in self.data:
                clamp = self.data['clamp']
                if not isinstance(clamp, list) and not len(clamp) == 2:
                    raise mk.ModArgumentError('clamp is not valid')
                _c = mx.create_node('clamp')
                _c['minR'] = min(clamp)
                _c['maxR'] = max(clamp)
                _c['outputR'] >> plug_in
                plug_in = _c['inputR']

            # branch reverse?
            if do_flip:
                _f = connect_mult(1, -1, plug_in)
                plug_in = _f.node()['input1']

            # inputs data
            _inputs = []
            if isinstance(input0, mx.Plug):
                _inputs.append(input0)
            _inputs += inputs

            # connect
            result = None

            if op is None:
                _inputs[0] >> plug_in
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
                node = result.node()
                if op and 'output' not in node:
                    node.add_attr(mx.Double('output'))
                    result >> node['output']

                self.set_id(result.node(), 'connect')
