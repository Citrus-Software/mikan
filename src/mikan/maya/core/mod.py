# coding: utf-8

from copy import deepcopy
from six import string_types, iteritems

import maya.cmds as mc
from mikan.maya import cmdx as mx

from mikan.core import abstract
from mikan.core.logger import create_logger
from mikan.core.abstract.mod import ModError, ModArgumentError
from mikan.core.utils import re_is_int, re_is_float, ordered_load, ordered_dump
from mikan.vendor import yamllint
from .node import *
from .template import Template
from ..lib.configparser import ConfigParser

__all__ = ['Mod', 'ModError', 'ModArgumentError']

log = create_logger()


class Mod(abstract.Mod):
    software = 'maya'

    def __repr__(self):
        node = str(self.node)
        if isinstance(self.node, mx.Plug):
            node = self.node.path()

        if self.data:
            if isinstance(self.data, string_types):
                return "Mod('{}', node='{}', data='{}')".format(self.mod, node, self.data)
            else:
                return "Mod('{}', node='{}', data={})".format(self.mod, node, self.data)
        else:
            return "Mod('{}', node='{}')".format(self.mod, node)

    @staticmethod
    def execute_cmd(cmd):
        # deprecated
        # TODO: refactor

        commands = []
        for line in cmd.splitlines():
            # mod options
            if line.strip().startswith('#!'):
                continue
            elif len(line) == 0 or line.startswith('#'):
                continue
            # preserve commands order by grouping them into a list
            elif not line.startswith(' '):
                commands.append([line])
            else:
                if commands:
                    commands[-1].append(line)
                else:
                    commands.append([line])

        for i, cmd in enumerate(commands):
            failed = []
            cmd = '\n'.join(cmd)
            mod_data = Mod.load(cmd)
            if not mod_data:
                log.error('/!\\ failed to parse mod #{}'.format(i + 1))
                continue
            mod_data = parse_nodes(mod_data, failed=failed)
            if failed:
                log.error('/!\\ failed to resolve {}'.format(failed))

            for mod, data in iteritems(mod_data):
                mod = Mod(mod, data=data)
                mod.execute()

    @staticmethod
    def parse(ini):
        commands = []
        node = ini.parser.node
        data = {'node': node}
        data['source'] = data['node']

        for line in ini.get_lines():
            # preserve commands order by grouping them into a list
            if len(line) == 0 or line.startswith('#') or len(line.strip()) == 0:
                continue
            elif not line.startswith(' '):
                commands.append([line])
            else:
                if commands:
                    commands[-1].append(line)
                else:
                    commands.append([line])

        # inline replace/loops
        data['replace'] = Mod.parse_ini_replace(ini)

        # update node
        if 'gem_hook' in node:
            data['node'] = Nodes.get_id(node['gem_hook'].read())
            if not data['node']:
                return

        # sort commands
        parsed_commands = []
        for i, lines in enumerate(commands):
            _mod = '\n'.join(lines)

            for _mod in Mod.parse_replace(_mod, data['replace']):
                cmd_data = {'yml': _mod}
                parsed_commands.append(cmd_data)

                _cmd = Mod.load(_mod)
                if _cmd:
                    cmd_data['mod'] = list(_cmd)[0]
                    cmd_data['data'] = _cmd[cmd_data['mod']]
                else:
                    errors = []
                    errors.append('-- failed to parse mod #{} of "{}" ({})'.format(i + 1, ini.parser.node, lines[0].strip(':')))
                    for lint in yamllint.run(_mod):
                        _lines = [
                            str(lint),
                            lines[lint.line - 1],
                            ' ' * (lint.column - 1) + '^'
                        ]
                        errors.append('\n'.join(_lines) + '\n')
                    cmd_data['errors'] = errors
                    for error in errors:
                        log.error(error)

        if not parsed_commands:
            return

        data['commands'] = parsed_commands
        return data

    def parse_nodes(self):
        # recursively lookup for nodes
        del self.unresolved[:]

        if isinstance(self.node, string_types):
            self.node = self.parse_vars(self.node)
            self.node = parse_nodes(self.node, failed=self.unresolved, silent=True)

        parsed_data = deepcopy(self.data)
        parsed_data = self.parse_vars(parsed_data)
        parsed_data = parse_nodes(parsed_data, failed=self.unresolved, silent=True)
        self.data = parsed_data

    @staticmethod
    def add_var(var, node):
        # filter data
        if not isinstance(node, mx.Node):
            node = mx.encode(str(node))

        plug_name = 'gem_var_{}'.format(var)

        # add variable
        if plug_name not in node:
            log.warning('/!\\ initialized variable ${} on "{}"'.format(var, node))
            node.add_attr(mx.Double(plug_name, keyable=True))

        return node[plug_name]

    @staticmethod
    def get_var(var, node):
        plug = Mod.add_var(var, node)
        return plug.read()

    @staticmethod
    def load(cmd):
        try:
            data = ordered_load(cmd)
        except:
            return {}

        # convert simple commands
        if isinstance(data, dict):
            _command = list(data)[0]
            _data = data[_command]
            if isinstance(_data, string_types):
                _data = _data.split()
                for j, v in enumerate(_data):
                    if re_is_int.match(v):
                        _data[j] = int(v)
                    elif re_is_float.match(v):
                        _data[j] = float(v)
                if not _data:
                    _data = None
                return {_command: _data}
            else:
                return data

        elif isinstance(data, string_types):
            cmd = data.split()
            if len(cmd) > 1:
                return {cmd[0]: cmd[1:]}
            else:
                return {cmd[0]: None}

    @staticmethod
    def add(node, mod, data):
        if not isinstance(node, mx.Node):
            node = mx.Node(str(node))
        cmd = {mod: data}
        cmd = ordered_dump(cmd)

        mod = ConfigParser(node)['mod']
        old = mod.read()
        if old:
            cmd = old + '\n' + cmd
        mod.write(cmd)

    def get_template(self):
        tpl = None
        if self.source:
            tpl = Template.get_from_node(self.source)
        if not tpl:
            if isinstance(self.node, mx.Plug):
                tpl = Template.get_from_node(self.node.node())
            elif isinstance(self.node, mx.Node):
                tpl = Template.get_from_node(self.node)
        return tpl

    def get_template_id(self, node=None):
        if node is None:
            node = self.source
        if not node:
            return

        for plug in ('gem_hook', 'gem_id'):
            if plug in node:
                for tag in node[plug].read().split(';'):
                    if tag.startswith('::'):
                        continue
                    tpl_id = tag.split('::')[0]
                    if tpl_id:
                        return tpl_id

        parent = node.parent()
        if parent:
            return self.get_template_id(parent)
        else:
            return

    def set_id(self, node, tag, subtag=None, prefix=None, multi=False):
        if prefix is None:
            prefix = self.id_prefix

        tpl = self.get_template_id()
        if not tpl:
            tpl = ''
        tag = '{}::{}{}'.format(tpl, prefix, tag)

        if subtag is not None and subtag:
            tag = tag + '.' + subtag

        if multi or not subtag:
            # remove alpha suffix: mod.path.root.0
            # keep num suffix: mod.path.0
            nodes = Nodes.get_id(tag, as_dict=True)
            keys = [int(k) for k in nodes if re_is_int.match(k)]
            count = max(keys) if keys else -1
            tag += '.{}'.format(count + 1)

        Nodes.set_id(node, tag)
