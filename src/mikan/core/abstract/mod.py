# coding: utf-8

"""Abstract Mod (Modifier) Module.

This module provides the base classes for managing modifiers in the Mikan framework.
Modifiers are instructions that can be executed on rig elements, such as creating
constraints, setting attributes, or performing custom actions during rig building.

The module supports:
    - Dynamic modifier class registration via templates
    - Variable substitution and parsing
    - Execution status tracking and error handling
    - Cross-platform modifier abstraction

Classes:
    Mod: Abstract base class for modifier management.
    ModError: Exception raised for modifier execution errors.
    ModArgumentError: Exception raised for invalid modifier arguments.

Examples:
    Creating and executing a modifier:
        >>> mod = Mod('constraint', node=joint_node, data={'target': ctrl_node})
        >>> status = mod.execute()

    Using variable substitution:
        >>> mod.parse_vars({'target': '$my_variable'})
"""

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
from .monitor import JobMonitor
from .template import Template

import mikan.templates.mod

__all__ = ['Mod', 'ModError', 'ModArgumentError']

log = create_logger()


class Mod(JobMonitor):
    """Abstract base class for modifier management.

    This class provides the core interface for managing modifiers across different
    DCC applications. Modifiers are operations that execute during rig building,
    such as creating constraints, setting attributes, expressions, or driven keys.

    Attributes:
        modules (dict): Registry of available modifier modules.
        classes (dict): Cache of instantiated modifier classes.
        software (str): Identifier for the DCC software (e.g., 'maya').
        mod (str): Type of modifier (e.g., 'constraint', 'setAttr').
        mod_data (OrderedDict): Default configuration data for the modifier type.
        nodes (dict): Node references for parser resolution.
        id_prefix (str): Prefix for modifier IDs, defaults to 'mod.'.
        node: The target node for this modifier.
        data (dict): Dictionary containing modifier parameters.
        source: Source template or node for variable resolution.
        modes (set): Active modes for the modifier.

    Examples:
        Creating a modifier from template data:
            >>> mod = Mod('constraint', node=joint, data={'type': 'parent'})
            >>> status = mod.execute()

        Checking execution status:
            >>> if status == Mod.STATUS_DONE:
            ...     print('Modifier executed successfully')

    Note:
        This is an abstract base class. Use software-specific implementations
        like mikan.maya.core.mod.Mod for actual modifier operations.
    """

    modules = {}
    classes = {}
    software = None

    mod = None
    mod_data = ordered_dict()

    nodes = {}  # for parser
    id_prefix = 'mod.'

    @classmethod
    def get_all_modules(cls, module=mikan.templates.mod):
        """Discover and register all available modifier modules.

        Scans the templates.mod package for modifier implementations,
        loads their configuration from mod.yml files, and registers
        them in the modules dictionary. Also handles legacy name mappings.

        Args:
            module: The parent module to scan for modifier packages.
                Defaults to mikan.templates.mod.

        Note:
            This method is called automatically at module import time.
        """
        cls.modules.clear()
        cls.classes.clear()

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
        """Get or create a modifier class for the specified modifier type.

        Retrieves a cached modifier class or dynamically loads and instantiates
        it from the corresponding template module.

        Args:
            name (str): Name of the modifier type (e.g., 'constraint', 'setAttr').

        Returns:
            type: The modifier class for the specified type, or None if not found.

        Examples:
            >>> ConstraintMod = Mod.get_class('constraint')
            >>> mod = ConstraintMod('constraint', node=joint)
        """
        if name in cls.classes:
            return cls.classes[name]

        module = cls.modules[name]

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
        """Create a new modifier instance of the appropriate type.

        Args:
            mod (str): Type of modifier to create.
            node: Target node for the modifier.
            data (dict, optional): Modifier parameters.
            source: Source template for variable resolution.

        Returns:
            Mod: New modifier instance of the appropriate subclass.
        """
        new_cls = cls.get_class(mod)
        return super(Mod, new_cls).__new__(new_cls)

    def __init__(self, mod, node=None, data=None, source=None):
        """Initialize a modifier instance.

        Args:
            mod (str): Type of modifier.
            node: Target node for the modifier.
            data (dict, optional): Modifier parameters.
            source: Source template for variable resolution.
        """
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
        """Execute the modifier's main operation.

        Must be implemented by software-specific subclasses.

        Note:
            This is a placeholder. Override in subclasses.
        """

    def execute(self, modes=None, source=None):
        """Execute the modifier.

        Resolves node references, runs the modifier operation,
        and handles errors. Logs status and returns a status code.

        Args:
            modes (set, optional): Active modes for execution behavior.
            source (str, optional): Source identifier for logging.

        Returns:
            int: Status code indicating result:
                - STATUS_DONE: Successfully executed
                - STATUS_DELAY: Waiting for unresolved dependencies
                - STATUS_INVALID: Invalid arguments provided
                - STATUS_ERROR: ModError occurred
                - STATUS_CRASH: Unexpected exception occurred

        Examples:
            >>> status = mod.execute(modes={'mirror'}, source='template.yml')
            >>> if status == Mod.STATUS_DONE:
            ...     print('Modifier executed successfully')
        """
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
        """Parse and resolve node references in modifier data.

        Resolves string identifiers to actual DCC nodes.
        Must be implemented by software-specific subclasses.

        Note:
            This is a placeholder. Override in subclasses.
        """

    def delay_parser(self):
        """Check if parsing should be delayed due to unresolved dependencies.

        Returns:
            bool: True if there are unresolved module or connection references.
        """
        if self.unresolved:
            for n in self.unresolved:
                if '::mod.' in n or '::!mod.' in n or '->' in n:
                    return True
        return False

    def parse_vars(self, data):
        """Parse and substitute variables in data structures.

        Recursively processes data, replacing $variable references
        with their resolved values from the source template.

        Args:
            data: Data structure to process (dict, list, or string).

        Returns:
            The processed data with variables substituted.

        Examples:
            >>> mod.parse_vars({'target': '$my_node'})
            {'target': <resolved_node>}

            >>> mod.parse_vars('$prefix_name')
            'L_arm'
        """
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
        """Add a variable to the node's variable storage.

        Args:
            var (str): Variable name.
            node: Node to store the variable on.

        Note:
            This is a placeholder. Override in subclasses.
        """

    @staticmethod
    def get_var(var, node):
        """Get a variable value from the node's variable storage.

        Args:
            var (str): Variable name to retrieve.
            node: Node to get the variable from.

        Returns:
            The variable value, or 0 if not found.

        Note:
            This is a placeholder. Override in subclasses.
        """
        return 0

    @staticmethod
    def parse_ini_replace(ini):
        """Parse variable definitions from INI-style comments.

        Extracts variables defined in #> comment lines.

        Args:
            ini: INI parser instance with get_lines() method.

        Returns:
            dict: Dictionary of parsed variable names and values.

        Examples:
            >>> # In template file:
            >>> # #> {side: L, limb: arm}
            >>> vars = Mod.parse_ini_replace(ini)
            >>> vars
            {'side': 'L', 'limb': 'arm'}
        """
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
        """Parse and expand template replacement patterns.

        Replaces <key> patterns in mod string with values from data.
        If data values are lists, generates multiple mod strings.

        Args:
            mod (str): Template string with <key> placeholders.
            data (dict): Dictionary of replacement values.

        Returns:
            list: List of expanded mod strings.

        Examples:
            >>> Mod.parse_replace('joint_<side>', {'side': ['L', 'R']})
            ['joint_L', 'joint_R']

            >>> Mod.parse_replace('<limb>_ctrl', {'limb': 'arm'})
            ['arm_ctrl']
        """
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
        """Get the template associated with this modifier's source.

        Returns:
            Template: The template instance, or None if not found.
        """
        return Template.get_from_node(self.source)

    def set_id(self, node, tag, subtag=None):
        """Set an ID tag on a node.

        Args:
            node: Node to tag.
            tag (str): Primary tag identifier.
            subtag (str, optional): Secondary tag identifier.

        Note:
            This is a placeholder. Override in subclasses.
        """


class ModError(Exception):
    """Exception raised for modifier execution errors.

    Raised when a modifier operation fails in an expected way,
    such as missing nodes or invalid operations.

    Examples:
        >>> raise ModError('Target node not found')
    """


class ModArgumentError(Exception):
    """Exception raised for invalid modifier arguments.

    Raised when modifier arguments are invalid or missing.

    Examples:
        >>> raise ModArgumentError('Missing required parameter: target')
    """


Mod.get_all_modules()
