# coding: utf-8
from copy import deepcopy

import meta_nodal_py as kl

import mikan.tangerine.core as mk
from mikan.core import flatten_list
from mikan.tangerine.lib.commands import *
from mikan.core.logger import create_logger

log = create_logger()

plug_types = {
    'float': float,
    'int': int,
    'bool': bool,
    'enum': int
}


class Mod(mk.Mod):

    def run(self):

        # get nodes
        nodes = self.data.get('nodes', self.data.get('node', self.node))
        nodes = [n for n in list(flatten_list([nodes])) if n]
        if not nodes:
            raise mk.ModArgumentError('node not found')

        self.data.pop('node', None)
        self.data.pop('nodes', None)

        plug_list = []

        # data
        if isinstance(self.data, list):

            if isinstance(self.data[0], str):
                # one-liner legacy
                cmd = self.data[0]
                name = self.data[1]
                if cmd not in ['set', 'show', 'hide', 'lock', 'l', 'keyable', 'k']:
                    raise mk.ModArgumentError('command is invalid ("{}")'.format(cmd))
                plug_list.append((name, {cmd: True}))
                if cmd == 'set':
                    plug_list[0][1][cmd] = self.data[2]
                if cmd == 'add':
                    plug_list[0][1][cmd] = 'float'
                    plug_list[0][1]['k'] = True
                    plug_list[0][1]['min'] = -1
                    plug_list[0][1]['max'] = 1

            else:
                # list of plug cmds
                for plug_data in self.data:
                    plug_list.append((list(plug_data)[0], list(plug_data.values())[0]))

        elif isinstance(self.data, dict):
            # dict of plug cmds
            for plug, data in self.data.items():
                plug_list.append((plug, data))

        # conform set value
        _plug_list = []
        for plug, data in plug_list:
            if isinstance(data, (int, float, bool)) or kl.is_plug(data):
                data = {'set': data}
            if isinstance(data, (tuple, list)) and len(data) == 3:
                if all([isinstance(v, (int, float)) for v in data]):
                    data = {'set': data}
            if 'set' in data and kl.is_plug(data['set']):
                data['set'] = data['set'].get_value()

            _plug_list.append((plug, data))

        plug_list = _plug_list

        # expand vectors
        _plug_list = []
        for plug, data in plug_list:
            plug_name = plug.get_name() if kl.is_plug(plug) else plug

            if plug_name in {'s', 'scale', 'r', 'rotate', 't', 'translate'}:
                if 'set' in data:
                    value = data['set']
                    if not isinstance(value, (list, tuple)) or len(value) != 3:
                        raise mk.ModArgumentError('invalid vector value to set')

                for i, dim in enumerate('xyz'):
                    _data = deepcopy(data)
                    if 'set' in _data:
                        _data['set'] = _data['set'][i]
                    _plug_list.append((plug_name[0] + '.' + dim, _data))

            else:
                _plug_list.append((plug, data))

        plug_list = _plug_list

        # build loop data
        plug_data = []
        for plug, data in plug_list:
            if kl.is_plug(plug):
                plug_data.append((plug, plug.get_node(), data))

        plug_list = [x for x in plug_list if isinstance(x[0], str)]
        for node in nodes:
            for plug_name, data in plug_list:
                plug_data.append((plug_name, node, data))

        # processing
        for plug, node, data in plug_data:
            if isinstance(plug, str):
                plug_name = plug
                plug = mk.Nodes.get_node_plug(node, plug_name, add=False)

            # build cmd
            value = data.get('set')

            keyable = data.get('k', data.get('keyable', data.get('show')))
            if 'hide' in data:
                keyable = not data['hide']
            locked = data.get('l', data.get('lock'))

            min_value = data.get('min')
            max_value = data.get('max')
            nice_name = data.get('nice_name')
            proxy = data.get('proxy')
            if proxy is not None and not kl.is_plug(proxy):
                self.log_error('invalid proxy for {} ({})'.format(plug_name, proxy))
                continue

            if data.get('flip', False):
                tpl = self.get_template()
                if tpl.do_flip():
                    if value is not None:
                        value *= -1
                    min_value = data.get('max')
                    max_value = data.get('min')
                    if min_value is not None:
                        min_value *= -1
                    if max_value is not None:
                        max_value *= -1

            if not plug:
                plug_type = data.get('type', 'float')
                if plug_type not in plug_types:
                    self.log_error('invalid plug type ("{}")'.format(plug_type))
                    continue
                plug_type = plug_types[plug_type]

                enum = data.get('enum')
                if isinstance(enum, dict):
                    enum = {v: k for k, v in enum.items()}

                plug = add_plug(node, plug_name, plug_type, default_value=value, max_value=max_value, min_value=min_value, nice_name=nice_name, enum=enum)

            else:
                _input = plug.get_input()
                if value is not None and not _input:
                    plug.set_value(value)

            if keyable is not None:
                set_plug(plug, k=bool(keyable))
            if locked is not None:
                set_plug(plug, lock=bool(locked))
            if min_value is not None:
                set_plug(plug, min_value=min_value)
            if max_value is not None:
                set_plug(plug, max_value=max_value)
            if nice_name is not None:
                set_plug(plug, nice_name=nice_name)
            if proxy:
                plug.connect(proxy)
