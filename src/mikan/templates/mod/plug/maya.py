# coding: utf-8

from copy import deepcopy
from six import string_types, iteritems

from mikan.maya import cmds as mc
import mikan.maya.cmdx as mx

import mikan.maya.core as mk
from mikan.core import flatten_list
from mikan.core.logger import create_logger

log = create_logger()

plug_types = {
    'float': 'double',
    'int': 'long',
    'bool': 'bool',
    'enum': 'enum'
}

limits_min = {
    'sx': mx.kScaleMinX,
    'sy': mx.kScaleMinY,
    'sz': mx.kScaleMinZ,
    'rx': mx.kRotateMinX,
    'ry': mx.kRotateMinY,
    'rz': mx.kRotateMinZ,
    'tx': mx.kTranslateMinX,
    'ty': mx.kTranslateMinY,
    'tz': mx.kTranslateMinZ,
}

limits_max = {
    'sx': mx.kScaleMaxX,
    'sy': mx.kScaleMaxY,
    'sz': mx.kScaleMaxZ,
    'rx': mx.kRotateMaxX,
    'ry': mx.kRotateMaxY,
    'rz': mx.kRotateMaxZ,
    'tx': mx.kTranslateMaxX,
    'ty': mx.kTranslateMaxY,
    'tz': mx.kTranslateMaxZ,
}


class Mod(mk.Mod):

    def run(self):

        # get nodes
        nodes = self.data.get('nodes', self.data.get('node', self.node))
        nodes = [n for n in list(flatten_list([nodes])) if isinstance(n, (mx.Node))]
        if not nodes:
            raise mk.ModArgumentError('node not found')

        self.data.pop('node', None)
        self.data.pop('nodes', None)

        plug_list = []

        # data
        if isinstance(self.data, list):

            if isinstance(self.data[0], string_types):
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

            else:
                # list of plug cmds
                for plug_data in self.data:
                    plug_list.append((plug_data.keys()[0], plug_data.values()[0]))

        elif isinstance(self.data, dict):
            # dict of plug cmds
            for plug, data in iteritems(self.data):
                plug_list.append((plug, data))

        # conform set value
        _plug_list = []
        for plug, data in plug_list:
            if isinstance(data, (int, float, bool, mx.Plug)):
                data = {'set': data}
            if isinstance(data, (tuple, list)) and len(data) == 3:
                if all([isinstance(v, (int, float)) for v in data]):
                    data = {'set': data}
            if 'set' in data and isinstance(data['set'], mx.Plug):
                data['set'] = data['set'].read()

            _plug_list.append((plug, data))

        plug_list = _plug_list

        # expand vectors
        _plug_list = []
        for plug, data in plug_list:
            if plug in {'s', 'scale', 'r', 'rotate', 't', 'translate'}:

                if 'set' in data:
                    value = data['set']
                    if not isinstance(value, (list, tuple)) or len(value) != 3:
                        raise mk.ModArgumentError('invalid vector value to set')

                for i, dim in enumerate('xyz'):
                    _data = deepcopy(data)
                    if 'set' in data:
                        _data['set'] = _data['set'][i]
                    _plug_list.append((plug[0] + '.' + dim, _data))

            else:
                _plug_list.append((plug, data))

        plug_list = _plug_list

        # build loop data
        plug_data = []
        for plug, data in plug_list:
            if isinstance(plug, mx.Plug):
                plug_data.append((plug, plug.node(), data))

        plug_list = [x for x in plug_list if isinstance(x[0], string_types)]
        for node in nodes:
            for plug_name, data in plug_list:
                plug_data.append((plug_name, node, data))

        # processing
        for plug, node, data in plug_data:
            if isinstance(plug, string_types):
                plug_name = plug
                plug = mk.Nodes.get_node_plug(node, plug_name, add=False)
            if isinstance(plug, mx.Plug):
                plug_name = plug.name(long=False)

            # build cmd
            value = None
            if 'set' in data:
                value = data.get('set')

                # angular?
                if plug is not None and plug.type_class() == mx.Angle:
                    value = mx.Degrees(value).asRadians()

            keyable = data.get('k', data.get('keyable', data.get('show')))
            if 'hide' in data:
                keyable = not data['hide']
            locked = data.get('l', data.get('lock'))

            min_value = data.get('min')
            max_value = data.get('max')
            nice_name = data.get('nice_name')
            proxy = data.get('proxy')
            if proxy is not None and not isinstance(proxy, mx.Plug):
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

            if plug is None:
                plug_type = data.get('type', 'float')
                if plug_type not in plug_types:
                    self.log_error('invalid plug type ("{}")'.format(plug_type))
                    continue
                plug_type = plug_types[plug_type]

                kw = {'at': plug_type}
                if plug_type == 'enum':
                    enum = data.get('enum', [])
                    if isinstance(enum, list):
                        kw['en'] = ':'.join(enum)
                    elif isinstance(enum, dict):
                        _enum = []
                        for k in enum:
                            _enum.append('{}={}'.format(enum[k], k))
                        kw['en'] = ':'.join(_enum)
                if value is not None:
                    kw['dv'] = value
                if nice_name:
                    kw['nn'] = nice_name

                if proxy is not None:
                    kw['proxy'] = proxy.path()

                mc.addAttr(str(node), sn=plug_name, **kw)
                plug = node[plug_name]

            else:
                if value is not None:
                    if plug.editable:
                        with mx.DGModifier() as md:
                            md.set_attr(plug, value)
                    else:
                        self.log_warning('failed to set "{}" (locked or connected) on "{}"'.format(plug, node))

            if keyable is not None:
                with mx.DGModifier() as md:
                    md.set_keyable(plug, keyable)
            if locked is not None:
                with mx.DGModifier() as md:
                    md.set_locked(plug, locked)

            plug_name = plug.name(long=False)
            if len(plug_name) == 2 and plug_name[0] in 'trs' and plug_name[1] in 'xyz':

                if min_value is not None:
                    min_value = float(min_value)
                    if plug_name[0] == 'r':
                        min_value = mx.Degrees(min_value).asRadians()
                    lim = limits_min[plug_name]
                    node.enable_limit(lim, True)
                    node.set_limit(lim, min_value)

                if max_value is not None:
                    max_value = float(max_value)
                    if plug_name[0] == 'r':
                        max_value = mx.Degrees(max_value).asRadians()
                    lim = limits_max[plug_name]
                    node.enable_limit(lim, True)
                    node.set_limit(lim, max_value)

            else:
                if min_value is not None:
                    mc.addAttr(plug.path(), e=True, min=min_value)
                if max_value is not None:
                    mc.addAttr(plug.path(), e=True, max=max_value)
