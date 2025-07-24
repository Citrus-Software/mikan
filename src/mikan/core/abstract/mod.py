# coding: utf-8

import re
import sys
import logging
import os.path
import pkgutil
import traceback
from copy import deepcopy
from six import string_types

from mikan.core.utils import ordered_load, ordered_dict, re_is_int
from mikan.core.logger import create_logger
from mikan.core.prefs import Prefs
from .node import Nodes
from .monitor import JobMonitor
from .template import Template

import mikan.templates.mod

__all__ = ['Mod', 'ModError', 'ModArgumentError']

log = create_logger()


class Mod(JobMonitor):
    modules = {}
    classes = {}
    software = None

    mod = None
    mod_data = ordered_dict()

    nodes = {}  # for parser
    id_prefix = 'mod.'

    @classmethod
    def get_all_modules(cls, module=mikan.templates.mod):

        def safe_import(modname):
            if sys.version_info[0] >= 3:
                import importlib
                return importlib.import_module(modname)
            else:
                import pkgutil
                return importer.find_module(modname).load_module(modname)

        for importer, modname, ispkg in pkgutil.walk_packages(module.__path__, prefix=module.__name__ + '.'):
            if not ispkg:
                continue

            try:
                package = safe_import(modname)
            except Exception as e:
                log.error('failed to import Modifier "{}": {}'.format(modname, e))
                continue

            modname = modname[len(module.__name__ + '.'):]

            # load mod data
            package.mod_data = ordered_dict()
            package.sample = ''

            base_path = package.__path__[0]

            path = base_path + os.path.sep + 'mod.yml'
            if os.path.exists(path):
                try:
                    with open(path, 'r') as stream:
                        package.mod_data = ordered_load(stream)
                except Exception as e:
                    log.error('failed to load Modifier "{}" mod.yml: {}'.format(modname, e))
            else:
                continue

            path = base_path + os.path.sep + 'sample.yml'
            if os.path.exists(path):
                try:
                    with open(path, 'r') as stream:
                        package.sample = stream.read()
                except Exception as e:
                    log.error('failed to load Modifier "{}" sample.yml: {}'.format(modname, e))

            # register
            cls.modules[modname] = package

        # renamed module for legacy
        renamed = {}
        prefs = Prefs.get('mod', {})
        for name in prefs:
            if not isinstance(prefs[name], dict):
                continue
            if 'name' in prefs[name] and name in cls.modules:
                legacy_name = prefs[name]['name']
                renamed[legacy_name] = cls.modules.pop(name)
        cls.modules.update(renamed)

    @classmethod
    def get_class(cls, name):
        if name in cls.classes:
            return cls.classes[name]

        module = Mod.modules[name]

        for importer, modname, ispkg in pkgutil.iter_modules(module.__path__):
            if modname == cls.software:
                _modname = module.__name__ + '.' + modname
                cls_module = importer.find_module(_modname).load_module(_modname)
                new_cls = cls_module.Mod
                new_cls.mod = name
                new_cls.mod_data = module.mod_data

                cls.classes[name] = new_cls
                return new_cls

    def __new__(cls, mod, node=None, data=None, source=None):
        new_cls = cls.get_class(mod)
        return super(Mod, new_cls).__new__(new_cls)

    def __init__(self, mod, node=None, data=None, source=None):
        self.node = node
        self.data = data or {}
        self.data = deepcopy(self.data)
        if isinstance(self.data, dict) and 'node' in self.data:
            self.node = self.data['node']
            del self.data['node']

        self.source = source

        self.modes = None

        # monitor
        JobMonitor.__init__(self)

    def run(self):
        """ placeholder """

    def execute(self, modes=None, source=None):

        if modes is None:
            modes = set()
        self.modes = modes

        source_str = ''
        if source is not None:
            source_str = '  # source: ' + str(source)

        self.clear_logs()

        # recursively lookup for nodes
        self.parse_nodes()
        if self.delay_parser():
            return Mod.STATUS_DELAY

        try:
            self.run()
            if not self.logs and not self.unresolved:
                log.debug('-- execute: {}'.format(self) + source_str)
            else:
                self.log_warning('-- execute: {}'.format(self) + source_str, 0)

            self.log_summary()
            return Mod.STATUS_DONE

        except ModArgumentError as e:
            self.log_warning('-- failed to execute: {}'.format(self) + source_str, 0)
            self.log_error('argument error: {}'.format(e.args[0]))
            self.log_summary()
            return Mod.STATUS_INVALID

        except ModError as e:
            self.log_warning('-- failed to execute: {}'.format(self) + source_str, 0)
            self.log_error('{}'.format(e.args[0]))
            self.log_summary()
            return Mod.STATUS_ERROR

        except Exception as e:
            self.log_warning('-- failed to execute: {}'.format(self) + source_str, 0)
            msg = traceback.format_exc().strip('\n')
            self.log(logging.CRITICAL, msg)
            self.log_summary()
            return Mod.STATUS_CRASH

    def parse_nodes(self):
        """placeholder"""

    def delay_parser(self):
        if self.unresolved:
            for n in self.unresolved:
                if '::mod.' in n or '::!mod.' in n or '->' in n:
                    return True
        return False

    def parse_vars(self, data):
        if isinstance(data, dict):
            new_data = type(data)()
            for k, v in data.items():
                if isinstance(k, string_types) and k.startswith('$'):
                    k = self.get_var(k[1:], self.source)
                new_data[k] = self.parse_vars(v)
            return new_data

        elif isinstance(data, list):
            return [self.parse_vars(e) for e in data]

        elif isinstance(data, string_types):

            if ' ' in data:
                _data = []
                for e in data.split():
                    if e.startswith('$'):
                        e = str(self.get_var(e[1:], self.source))
                    _data.append(e)
                return ' '.join(_data)

            if data.startswith('$'):
                return self.get_var(data[1:], self.source)

        return data

    @staticmethod
    def add_var(var, node):
        """placeholder"""

    @staticmethod
    def get_var(var, node):
        """placeholder"""
        return 0

    @staticmethod
    def parse_ini_replace(ini):
        vars = {}

        for line in ini.get_lines():
            line = line.strip()
            if line.startswith('#>'):
                try:
                    data = ordered_load(line[2:].strip())
                    if isinstance(data, dict):
                        vars.update(data)
                except:
                    log.warning('/!\\ variable parse error: "{}"'.format(line))

        return vars

    @staticmethod
    def parse_replace(mod, data):
        mods = [mod]
        keys = {}

        def replacer(match):
            key = match.group(1)  # extrait le contenu entre < >
            if '.' in key:
                base_key, sub_key = key.split('.')
                if re_is_int.match(sub_key):
                    sub_key = int(sub_key)
                if base_key in keys and isinstance(keys[base_key], (dict, list, tuple)):
                    if isinstance(keys[base_key], dict) and sub_key in keys[base_key]:
                        # remplacement depuis un dictionnaire {clé: dictionnaire[sous clé]}
                        return str(keys[base_key][sub_key])
                    elif isinstance(keys[base_key], (list, tuple)) and isinstance(sub_key, int):
                        # remplacement depuis une liste {clé: liste[sous clé]}
                        return str(keys[base_key][sub_key])

            elif key in keys:
                return str(keys[key])  # remplacement direct {clé: valeur}

            return match.group(0)  # si clé non trouvée, on laisse tel quel

        # replace loop
        for k, v in data.items():
            pattern = re.compile(r"<({}(?:\.[a-zA-Z0-9_]+)?)>".format(k))
            if not pattern.findall(mod):
                continue

            new_mods = []

            for _mod in mods:
                keys.clear()
                if isinstance(v, (list, tuple)):
                    for e in v:
                        keys[k] = e
                        new_mods.append(pattern.sub(replacer, _mod))
                else:
                    keys[k] = v
                    new_mods.append(pattern.sub(replacer, _mod))

            mods = new_mods

        return mods

    def get_template(self):
        return Template.get_from_node(self.source)

    def set_id(self, node, tag, subtag=None):
        """placeholder"""


class ModError(Exception):
    pass


class ModArgumentError(Exception):
    pass


Mod.get_all_modules()
