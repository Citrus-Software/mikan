# coding: utf-8

"""Abstract Template Module.

This module provides the base classes for managing rig templates in the Mikan framework.
Templates are modular building blocks that define how rig components are constructed,
including their structure, options, and hierarchical relationships.

The module supports:
    - Dynamic template class registration via package discovery
    - Template branching for symmetrical rigs (left/right, up/down)
    - Hierarchical template navigation (parent/child relationships)
    - Option management with common defaults
    - Build pipeline integration
    - Tag and hook systems for node identification

Classes:
    TemplateMeta: Metaclass providing per-class function registry.
    Template: Base class for rig template management.

Module Attributes:
    common_data (str): YAML string defining common template options.
    branch_pairs (str): YAML string defining branch pair mappings by axis.

Examples:
    Creating a template instance:
        >>> tpl = Template(node)
        >>> tpl.build(modes={'mirror'})

    Navigating template hierarchy:
        >>> parent = tpl.get_parent()
        >>> children = tpl.get_children()

    Working with branches:
        >>> for branch, root in tpl.get_branches():
        ...     print(branch, root)
"""

import sys
import os.path
import pkgutil
from copy import deepcopy
from six import string_types

from mikan.core.utils import ordered_load, ordered_dict
from mikan.core.logger import create_logger
from mikan.core.abstract.node import Nodes
from mikan.core.prefs import Prefs

import mikan.templates.template

__all__ = ['Template']

log = create_logger()

common_data = '''
opts:
  branches:
    help: |
      List of branches for duplicating the rig module.
       - Example: [L, R] builds the module twice, mirrored left and right.
    value: ''
    yaml: on
    presets:
     - 'L, R'
     - 'up, dn'
     - 'ft, bk'
    legacy: forks
  sym:
    help: Axis of symmetry for flip and mirror functions in the animator menu.
    value: 0
    enum:
      0: parent
      1: x
      2: y
      3: z
  group:
    help: |
      Name of the parent group in the module hierarchy.
      If the group does not exist, it will be created and parented under "all".
    value: ''
  parent:
    help: |
      Determines how the module group will be integrated into the asset's group hierarchy.
       - parent: Parents the module group under the template parent group.
       - merge up: Merges the module's controllers into the template parent group.
       - merge down: Merges the module's controllers into the template child group.
    value: 0
    enum:
      0: parent
      1: merge up
      2: merge down
  do_ctrl:
    help: Tags controllers to make them animatable.
    value: on
  do_skin:
    help: Tags binding joints to make them available for skinning.
    value: on
  virtual_parent:
    help: |
      Sets the new template parent for virtual hierarchy construction.
      This allows the binding skeleton to connect more coherently if the template hierarchy is not suitable,
      and also connects the controllers' pickwalk accordingly.
    value: ''
  isolate_skin:
    help: Separates skin joints into a dedicated group within the rig.
    value: off
'''

branch_pairs = '''
x:
 - [L, R]
 - [l, r]
 - [ex, in]
 - [ext, int]
y:
 - [up, dn]
z:
 - [ft, bk]
'''


class TemplateMeta(type):
    """Metaclass providing per-class function registry for templates.

    Ensures each template class has its own isolated funcs dictionary,
    preventing function registrations from being shared across subclasses.

    Note:
        This metaclass is automatically applied to the Template class.
    """

    def __new__(mcs, name, bases, attrs):
        """Create a new template class with its own funcs registry.

        Args:
            mcs: The metaclass.
            name (str): Name of the class being created.
            bases (tuple): Base classes.
            attrs (dict): Class attributes.

        Returns:
            type: The newly created class with an isolated funcs dict.
        """
        new_class = super(TemplateMeta, mcs).__new__(mcs, name, bases, attrs)
        new_class.funcs = dict()  # each class gets its own funcs dict
        return new_class


class Template(object):
    """Base class for rig template management.

    Templates are modular building blocks that define rig components.
    Each template type provides construction logic for specific rig parts
    (e.g., limbs, spines, fingers) and handles branching for symmetry.

    Attributes:
        modules (dict): Registry of available template modules.
        classes (dict): Cache of instantiated template classes.
        software (str): Identifier for the DCC software (e.g., 'maya').
        type_name (str): Type identifier, defaults to 'template'.
        common_data (OrderedDict): Parsed common template options.
        branch_pairs (OrderedDict): Branch pair mappings by axis.
        template (str): Name of this template type.
        template_data (OrderedDict): Configuration data for this template.
        node: The root DCC node for this template instance.
        branches (list): Current branch identifiers for this instance.
        root: The root node for the current branch.
        modes (set): Active build modes for this instance.

    Examples:
        Creating and building a template:
            >>> tpl = Template(node)
            >>> tpl.build(modes={'mirror'})

        Accessing template options:
            >>> if tpl.has_opt('branches'):
            ...     branches = tpl.get_opt('branches')

    Note:
        This is an abstract base class. Use software-specific implementations
        like mikan.maya.core.template.Template for actual template operations.
    """

    __metaclass__ = TemplateMeta
    modules = {}
    classes = {}
    software = None

    type_name = 'template'

    common_data = ordered_load(common_data)
    branch_pairs = ordered_load(branch_pairs)

    template = None
    template_data = ordered_dict()

    @classmethod
    def get_all_modules(cls, module=mikan.templates.template):
        """Discover and register all available template modules.

        Scans the templates.template package for template implementations,
        loads their configuration from template.yml files, and registers
        them in the modules dictionary. Also handles legacy name mappings.

        Args:
            module: The parent module to scan for template packages.
                Defaults to mikan.templates.template.

        Note:
            This method is called automatically at module import time.
        """
        cls.modules.clear()
        cls.classes.clear()
        prefs = Prefs.get('template', {})

        def safe_import(modname, importer):
            if sys.version_info[0] >= 3:
                import importlib
                return importlib.import_module(modname)
            else:
                import pkgutil
                return importer.find_module(modname).load_module(modname)

        # get all template modules
        for importer, modname, ispkg in pkgutil.iter_modules(module.__path__):
            if not ispkg:
                continue

            # get all variations of each template modules
            _modname = module.__name__ + '.' + modname

            try:
                package_cat = safe_import(_modname, importer)
            except Exception as e:
                log.error('failed to import Template category "{}": {}'.format(_modname, e))
                continue

            for tpl_importer, tpl_modname, ispkg in pkgutil.iter_modules(package_cat.__path__):
                if not ispkg:
                    continue

                tpl_name = modname + '.' + tpl_modname
                _tpl_modname = module.__name__ + '.' + tpl_name

                try:
                    package = safe_import(_tpl_modname, tpl_importer)
                except Exception as e:
                    log.error('failed to import Template "{}": {}'.format(_tpl_modname, e))
                    continue

                # load package data
                package.template_data = ordered_dict()

                path = package.__path__[0] + os.path.sep + 'template.yml'
                if os.path.exists(path):
                    try:
                        with open(path, 'r') as stream:
                            package.template_data = ordered_load(stream)
                    except Exception as e:
                        log.error('failed to load Template "{}" template.yml: {}'.format(tpl_name, e))
                        continue

                Template.update_template_data(package)

                # legacy
                if prefs and 'opts' in package.template_data:
                    opts = package.template_data['opts']
                    if tpl_name in prefs and 'opts' in prefs[tpl_name]:
                        legacy_opts = prefs[tpl_name]['opts'] or {}
                        for opt in legacy_opts or ():
                            if opt in opts:
                                opts[opt]['value'] = legacy_opts[opt]

                # register
                cls.modules[tpl_name] = package

        # renamed module for legacy
        renamed = {}
        prefs = Prefs.get('template', {})
        for name in prefs:
            if not isinstance(prefs[name], dict):
                continue
            if 'name' in prefs[name] and name in cls.modules:
                legacy_name = prefs[name]['name']
                renamed[legacy_name] = cls.modules.pop(name)
        cls.modules.update(renamed)

    def __new__(cls, node):
        """Create a new template instance of the appropriate type.

        Args:
            node: The DCC node to create a template from.

        Returns:
            Template: New template instance of the appropriate subclass.
        """
        module_name = cls.get_module_from_node(node)
        new_cls = cls.get_class(module_name)

        return super(Template, new_cls).__new__(new_cls)

    def __init__(self, node):
        """Initialize a template instance from the given node.

        Args:
            node: The DCC node that represents this template.
        """
        self.node = node

        self.branches = ['']  # branchless default
        self.root = self.node

        self.modes = set()

    def __str__(self):
        """Return the template name as string representation."""
        return self.name

    def __eq__(self, other):
        """Check equality based on underlying node."""
        if isinstance(other, Template):
            return self.node == other.node
        return False

    def __ne__(self, other):
        """Check inequality based on underlying node."""
        return not self.__eq__(other)

    def __hash__(self):
        """Return hash based on node and class."""
        return hash(self.node) ^ hash(Template)

    @classmethod
    def get_class_module(cls, name):
        """Get the software-specific module for a template type.

        Args:
            name (str): Name of the template type.

        Returns:
            module: The loaded software-specific module.

        Raises:
            RuntimeError: If template doesn't exist or has no software module.
        """
        if name not in cls.modules:
            raise RuntimeError('template "{}" does not exist'.format(name))
        module = cls.modules[name]

        for importer, modname, ispkg in pkgutil.iter_modules(module.__path__):
            if modname == cls.software:
                _modname = module.__name__ + '.' + modname
                try:
                    return importer.find_module(_modname).load_module(_modname)
                except Exception:
                    raise RuntimeError('template "{}" has no {} module'.format(name, cls.software))

    @classmethod
    def get_class(cls, name):
        """Get or create a template class for the specified template type.

        Retrieves a cached template class or dynamically loads and instantiates
        it from the corresponding template module. Handles base class inheritance.

        Args:
            name (str): Name of the template type (e.g., 'limb.arm').

        Returns:
            type: The template class for the specified type.

        Examples:
            >>> ArmTemplate = Template.get_class('limb.arm')
            >>> tpl = ArmTemplate(node)
        """
        # unknown fallback
        if name not in cls.modules:
            name = 'core._unknown'

        # get class from cache
        if name in cls.classes:
            return cls.classes[name]

        # get template class
        module = cls.modules[name]
        cls_module = cls.get_class_module(name)

        new_cls = cls_module.Template
        new_cls.template = name
        new_cls.template_data = deepcopy(module.template_data)

        # import base module
        if 'base' in module.template_data:
            base_module = module.template_data['base']

            prefs = Prefs.get('template', {})
            if base_module in prefs and 'name' in prefs[base_module]:
                base_module = prefs[base_module]['name']

            base_cls_module = cls.get_class_module(base_module)
            base_cls = base_cls_module.Template
            new_cls.__bases__ = (base_cls,)

        # deliver
        cls.classes[name] = new_cls
        return new_cls

    @classmethod
    def get_module_from_node(cls, node):
        """Get the template module name from a DCC node.

        Args:
            node: The DCC node to inspect.

        Returns:
            str: The template module name.

        Note:
            This is a placeholder. Override in subclasses.
        """
        pass

    # instance node ----------------------------------------------------------------------------------------------------

    @property
    def name(self):
        """Get the template name.

        Returns:
            str: The template name (empty in base implementation).
        """
        return ''

    @staticmethod
    def create(tpl, parent=None, name=None, data=None, root=None, joint=True):
        """Create a new template instance in the scene.

        Args:
            tpl (str): Template type to create.
            parent: Parent node or template.
            name (str, optional): Name for the new template.
            data (dict, optional): Initial configuration data.
            root: Root node to use.
            joint (bool): Whether to create joint hierarchy.

        Note:
            This is a placeholder. Override in subclasses.
        """
        pass

    def remove(self):
        """Remove this template from the scene.

        Note:
            This is a placeholder. Override in subclasses.
        """
        pass

    def rename(self, name):
        """Rename this template.

        Args:
            name (str): New name for the template.

        Note:
            This is a placeholder. Override in subclasses.
        """
        pass

    def rename_root(self):
        """Rename the root node based on template name.

        Note:
            This is a placeholder. Override in subclasses.
        """
        pass

    def rename_template(self):
        """Rename template nodes to match current name.

        Note:
            This is a placeholder. Override in subclasses.
        """
        pass

    @staticmethod
    def cleanup_name(name):
        """Clean a name string for use as a node name.

        Removes spaces and non-alphanumeric characters.

        Args:
            name (str): Name to clean.

        Returns:
            str: Cleaned name with only alphanumeric chars and underscores.

        Examples:
            >>> Template.cleanup_name('My Node!')
            'My_Node'
        """
        name = str(name)
        name = name.replace(' ', '_')
        name = ''.join([c for c in name if c.isalnum() or c == '_'])
        return name

    @staticmethod
    def get_from_node(node):
        """Get a template instance from a DCC node.

        Args:
            node: The DCC node to get template from.

        Returns:
            Template: Template instance for the node.
        """
        return Template(node)

    def build(self, modes=None):
        """Build the rig from this template.

        Args:
            modes (set, optional): Build modes to apply.

        Note:
            This is a placeholder. Override in subclasses.
        """
        pass

    def build_template(self, data):
        """Build the template structure.

        Args:
            data (dict): Template configuration data.

        Note:
            This is a placeholder. Override in subclasses.
        """
        pass

    def build_rig(self):
        """Build the rig controls and deformers.

        Note:
            This is a placeholder. Override in subclasses.
        """
        pass

    def get_guide_data(self, user_data):
        """Get guide configuration data with user overrides.

        Merges default guide values with user-provided data.

        Args:
            user_data (dict): User-provided guide overrides.

        Returns:
            dict: Merged guide configuration data.
        """
        data = {}
        for opt, opt_data in self.template_data.get('guides', {}).items():
            if isinstance(opt_data, dict) and 'value' in opt_data:
                data[opt] = opt_data['value']

        if isinstance(user_data, dict):
            for k in user_data:
                if k in data:
                    data[k] = user_data[k]
        return data

    @staticmethod
    def update_template_data(module):
        """Merge common template options into module data.

        Applies common_data defaults to the module's template_data,
        allowing module-specific values to override defaults.

        Args:
            module: The template module to update.
        """
        data = module.template_data
        common_data = Template.common_data

        if 'opts' not in data:
            data['opts'] = {}

        for opt in common_data['opts']:
            _opt = deepcopy(common_data['opts'][opt])
            if opt in data['opts']:
                _opt.update(data['opts'][opt])
            data['opts'][opt] = _opt

    def check_validity(self):
        """Check if this template instance is valid.

        Validates that the template node matches the registered node
        for this template name (detects duplicate IDs).

        Returns:
            bool: True if template is valid, False if duplicate IDs exist.
        """
        node = Nodes.get_id(self.name)
        check = node == self.node
        if not check:
            log.warning('/!\\ {} is not valid! (duplicate ids)'.format(self))
        return check

    def get_name(self, name):
        """Get a named value from the template.

        Args:
            name (str): Name key to retrieve.

        Returns:
            str: The value (empty in base implementation).

        Note:
            This is a placeholder. Override in subclasses.
        """
        return ''

    def set_name(self, name, v):
        """Set a named value on the template.

        Args:
            name (str): Name key to set.
            v: Value to set.

        Note:
            This is a placeholder. Override in subclasses.
        """
        pass

    def has_opt(self, opt):
        """Check if template has a specific option.

        Args:
            opt (str): Option name to check.

        Returns:
            bool: True if option exists in template_data.
        """
        if opt in self.template_data['opts']:
            return True
        return False

    def get_opt(self, opt):
        """Get an option value from the template.

        Args:
            opt (str): Option name to retrieve.

        Returns:
            object: The option value.

        Note:
            This is a placeholder. Override in subclasses.
        """
        return object()

    def get_branch_opt(self, opt):
        """Get an option value adjusted for current branch.

        Args:
            opt (str): Option name to retrieve.

        Returns:
            object: The branch-adjusted option value.

        Note:
            This is a placeholder. Override in subclasses.
        """
        return object()

    @staticmethod
    def branch_opt(v):
        """Flip an option value for branch mirroring.

        Negates numeric values or toggles sign prefix for strings.

        Args:
            v: Value to flip (int, float, or str).

        Returns:
            The flipped value.

        Examples:
            >>> Template.branch_opt(5)
            -5
            >>> Template.branch_opt('-x')
            'x'
            >>> Template.branch_opt('y')
            '-y'
        """
        if type(v) in (int, float):
            return -v
        elif isinstance(v, string_types):
            if v.startswith('-'):
                return v[1:]
            else:
                if v.startswith('+'):
                    v = v[1:]
                return '-' + v
        return v

    def set_opt(self, opt, v):
        """Set an option value on the template.

        Args:
            opt (str): Option name to set.
            v: Value to set.

        Note:
            This is a placeholder. Override in subclasses.
        """
        pass

    # navigation -------------------------------------------------------------------------------------------------------

    @staticmethod
    def get_all_template_nodes(self):
        """Get all template nodes in the scene.

        Returns:
            list: List of template nodes (empty in base implementation).

        Note:
            This is a placeholder. Override in subclasses.
        """
        return []

    @staticmethod
    def check_new_name_validity(self, name):
        """Check if a new name is valid for this template.

        Args:
            name (str): Proposed new name.

        Returns:
            bool: True if name is valid.

        Note:
            This is a placeholder. Override in subclasses.
        """
        return True

    def get_children(self, root=None, children=None):
        """Get direct child templates.

        Args:
            root: Optional root node to search from.
            children: Optional list to append children to.

        Returns:
            list: List of child Template instances.

        Note:
            This is a placeholder. Override in subclasses.
        """
        return []

    def get_all_children(self, children=None):
        """Get all descendant templates recursively.

        Args:
            children (list, optional): List to accumulate results.

        Returns:
            list: All descendant Template instances.

        Examples:
            >>> all_children = tpl.get_all_children()
        """
        if children is None:
            children = []

        for child in self.get_children():
            children.append(child)
            child.get_all_children(children)

        return children

    def get_parent(self, root=None):
        """Get the parent template.

        Args:
            root: Optional root node to search from.

        Returns:
            Template: Parent template, or None if no parent.

        Note:
            This is a placeholder. Override in subclasses.
        """
        return None

    def get_siblings(self):
        """Get sibling templates (same parent).

        Returns:
            list: List of sibling Template instances.

        Note:
            This is a placeholder. Override in subclasses.
        """
        return []

    def get_all_parents(self, parents=None):
        """Get all ancestor templates recursively.

        Args:
            parents (list, optional): List to accumulate results.

        Returns:
            list: All ancestor Template instances, nearest first.

        Examples:
            >>> ancestors = tpl.get_all_parents()
        """
        if parents is None:
            parents = []

        parent = self.get_parent()
        if parent is not None:
            parents.append(parent)
            parent.get_all_parents(parents)

        return parents

    def get_first_parent(self):
        """Get the root ancestor template.

        Returns:
            Template: The topmost ancestor, or self if no parents.
        """
        parents = self.get_all_parents()
        if parents:
            return parents[-1]
        else:
            return self

    def get_all_related_templates(self):
        """Get all templates in the same hierarchy.

        Includes all siblings and descendants of the root ancestor.

        Returns:
            list: All related Template instances.
        """
        templates = []
        for template in self.get_first_parent().get_siblings():
            templates.append(template)
            templates += template.get_all_children()
        return templates

    # structures -------------------------------------------------------------------------------------------------------

    def get_template_nodes(self, root=None, nodes=None):
        """Get all nodes belonging to this template.

        Args:
            root: Optional root node to start from.
            nodes: Optional list to accumulate results.

        Returns:
            list: List of template nodes.

        Note:
            This is a placeholder. Override in subclasses.
        """
        return []

    def get_template_chain(self, root=None, nodes=None):
        """Get the joint chain for this template.

        Args:
            root: Optional root node to start from.
            nodes: Optional list to accumulate results.

        Returns:
            list: List of joints in the chain.

        Note:
            This is a placeholder. Override in subclasses.
        """
        return []

    def get_structure(self, name):
        """Get a named structure from the template.

        Args:
            name (str): Structure name to retrieve.

        Returns:
            list: The structure data (empty in base implementation).

        Note:
            This is a placeholder. Override in subclasses.
        """
        return []

    def set_structure(self, struct, v):
        """Set a structure value on the template.

        Args:
            struct (str): Structure name to set.
            v: Value to set.

        Returns:
            bool: True on success.

        Note:
            This is a placeholder. Override in subclasses.
        """
        return True

    def delete_template_branches(self):
        """Delete all branch duplicates for this template.

        Note:
            This is a placeholder. Override in subclasses.
        """
        pass

    def build_template_branches(self):
        """Build branch duplicates based on branches option.

        Note:
            This is a placeholder. Override in subclasses.
        """
        pass

    def update_branch_id(self, e, branch_ids0, branch_ids, all_ids, path=False):
        """Update branch identifiers in a string element.

        Replaces branch ID patterns in node references or geometry paths
        when duplicating templates for different branches.

        Args:
            e (str): Element string to update (node ID or geometry path).
            branch_ids0 (list): Original branch IDs to replace.
            branch_ids (list): New branch IDs to use.
            all_ids (list): All known branch IDs for validation.
            path (bool): Whether element is a path component.

        Returns:
            str: Updated element string, or None if no update needed.
        """
        _branch_ids0 = []
        for i in range(len(branch_ids0)):
            _branch_ids0.append(branch_ids0[:i + 1])
        _branch_ids = []
        for i in range(len(branch_ids)):
            _branch_ids.append(branch_ids[:i + 1])

        mode = None
        _ids = []

        # id update
        if '::' in e:
            mode = '::'
            _e = e.split('::')
            _name, _sep, _keys = _e[0].partition('.')
            if not _keys:
                return
            _ids = _keys.split('.')

        # geometry id update
        elif '->' in e:
            mode = '->'
            _e = e.split('->')

            # geometry path recursion
            if '/' in _e[0]:
                _path = _e[0].split('/')
                for i, _p in enumerate(_path):
                    _p = self.update_branch_id(_p, branch_ids0, branch_ids, all_ids, path=True)
                    if _p:
                        _path[i] = _p
                _e[0] = '/'.join(_path)
                return mode.join(_e)

            _name = _e[0].split('_')
            _ids = []
            for _n in _name[::-1]:
                if _n not in all_ids:
                    break
                _ids.append(_n)
            if not _ids:
                return
            _ids.reverse()
            _keys = '_'.join(_name[-len(_ids):])
            _name = '_'.join(_name[:-len(_ids)])
            _sep = '_'

        # geometry path element update
        elif path:
            mode = ''
            _e = [e]

            _name = _e[0].split('_')
            _ids = []
            for _n in _name[::-1]:
                if _n not in all_ids:
                    break
                _ids.append(_n)
            if not _ids:
                return
            _ids.reverse()
            _keys = '_'.join(_name[-len(_ids):])
            _name = '_'.join(_name[:-len(_ids)])
            _sep = '_'

        pfx = None
        sfx = None
        for i, fid0 in enumerate(_branch_ids0):
            if len(fid0) <= len(_ids) and _ids[:len(fid0)] == fid0:
                pfx = i
            if len(fid0) == len(_ids) and _ids[-len(fid0):] == fid0:
                sfx = i

        if pfx is not None:
            branch_ids0_pfx = _sep.join(_branch_ids0[pfx])
            branch_ids_pfx = _sep.join(_branch_ids[pfx])
            _e[0] = _name + _sep + branch_ids_pfx + _keys[len(branch_ids0_pfx):]
            return mode.join(_e)

        if sfx is not None:
            branch_ids0_sfx = _sep + _sep.join(_branch_ids0[sfx])
            branch_ids_sfx = _sep + _sep.join(_branch_ids[sfx])
            _e[0] = _e[0][:-len(branch_ids0_sfx)] + branch_ids_sfx
            return mode.join(_e)

    def get_branches(self):
        """Get all branch combinations with their root nodes.

        Computes all branch combinations by traversing the template hierarchy
        and combining branch options from each level. Returns pairs of
        (branch_ids, root_node) for each combination.

        Returns:
            zip: Pairs of (branch_list, root_node) for each branch combination.

        Examples:
            >>> for branch, root in tpl.get_branches():
            ...     print(branch, root)
            ['L'] |arm_L_jnt
            ['R'] |arm_R_jnt
        """
        # get hierarchy
        templates = self.get_all_parents()[::-1]
        templates.append(self)

        branch_ids = []
        for tpl in templates:
            ids = tpl.get_opt('branches')
            if not ids:
                continue
            branch_ids.append(ids)

        # build all branches
        if not branch_ids:
            branches = [['']]
        else:
            branches = None
            for ids in branch_ids:
                if branches:
                    _branches = []
                    for f in branches:
                        for i in ids:
                            _branches.append(f[:])
                            _branches[-1].append(i)
                    branches = _branches
                else:
                    branches = [[i] for i in ids]

        # find roots
        roots = [self.node]
        if len(branches) > 1:
            for branch in branches[1:]:
                root = '{}::branch'.format(self.name)
                if branch[0] or len(branch) > 1:
                    root = '{}{}::branch'.format(self.name, ('.{}' * len(branch)).format(*branch))
                _root = Nodes.get_id(root)
                roots.append(_root if _root else None)

        return zip(branches, roots)

    def get_branch_suffix(self, sep='_'):
        """Get the branch suffix string for naming.

        Args:
            sep (str): Separator character. Defaults to '_'.

        Returns:
            str: Branch suffix (e.g., '_L' or '_L_up'), empty if no branches.

        Examples:
            >>> tpl.branches = ['L']
            >>> tpl.get_branch_suffix()
            '_L'
        """
        n = sep.join(self.branches)
        if n:
            n = sep + n
        return n

    def get_branch_id(self):
        """Get the branch ID string for node tagging.

        Returns:
            str: Branch ID in dot notation (e.g., '.L' or '.L.up').

        Examples:
            >>> tpl.branches = ['L', 'up']
            >>> tpl.get_branch_id()
            '.L.up'
        """
        if self.branches[0] or len(self.branches) > 1:
            return ('.{}' * len(self.branches)).format(*self.branches)
        return ''

    def get_branch_ids(self):
        """Get all branch IDs for this template.

        Iterates through all branch combinations and returns their IDs.

        Returns:
            list: List of branch ID strings.
        """
        _branches = self.branches
        _root = self.root

        branch_ids = []
        for self.branches, self.root in self.get_branches():
            branch_ids.append(self.get_branch_id())

        self.branches = _branches
        self.root = _root

        return branch_ids

    def do_flip(self):
        """Check if current branch requires flipping.

        Determines if the current branch combination results in a flip
        (e.g., right side vs left side).

        Returns:
            bool: True if transforms should be flipped.
        """
        flip = False
        for branch in self.branches:
            for axis, pairs in Template.branch_pairs.items():
                for pair in pairs:
                    if branch == pair[1]:
                        flip = not flip
        return flip

    def get_sym_axis(self):
        """Get the symmetry axis for this template.

        Searches the template hierarchy for an explicit sym option or
        infers axis from branch pairs.

        Returns:
            str: Axis name ('x', 'y', or 'z'), or None if no symmetry.
        """
        # get hierarchy
        templates = self.get_all_parents()
        templates.append(self)

        axes = {'x', 'y', 'z'}

        # find first symmetry
        for tpl in reversed(templates):
            axis = tpl.get_opt('sym')
            if axis in axes:
                return axis

            branches = tpl.get_opt('branches')
            if branches:
                for axis, pairs in Template.branch_pairs.items():
                    for pair in pairs:
                        if set(pair) == set(branches):
                            return axis

    @classmethod
    def get_branch_axis_sign(cls, branch):
        """Get the axis and sign for a branch identifier.

        Args:
            branch (str): Branch identifier (e.g., 'L', 'R', 'up').

        Returns:
            str: Signed axis (e.g., '+x', '-x', '+y').

        Examples:
            >>> Template.get_branch_axis_sign('L')
            '+x'
            >>> Template.get_branch_axis_sign('R')
            '-x'
        """
        for axis, pairs in cls.branch_pairs.items():
            for pair in pairs:
                if branch in pair:
                    if branch == pair[0]:
                        return '+' + axis
                    else:
                        return '-' + axis
        return '+'

    # tag system -------------------------------------------------------------------------------------------------------

    def set_template_id(self, node, tag):
        """Set a template-scoped ID tag on a node.

        Args:
            node: The DCC node to tag.
            tag (str): Tag identifier.

        Note:
            This is a placeholder. Override in subclasses.
        """
        pass

    def set_id(self, node, tag):
        """Set an ID tag on a node.

        Args:
            node: The DCC node to tag.
            tag (str): Tag identifier.

        Returns:
            str: The tag that was set.

        Note:
            This is a placeholder. Override in subclasses.
        """
        return tag

    def set_hook(self, node, hook, tag):
        """Set a hook connection on a node.

        Hooks are connection points for parenting and pickwalk navigation.

        Args:
            node: The DCC node to set hook on.
            hook (str): Hook type identifier.
            tag (str): Tag for the hook.

        Note:
            This is a placeholder. Override in subclasses.
        """
        pass

    def get_hook(self, tag=False):
        """Get the hook node for this template.

        Args:
            tag (bool): If True, return tag instead of node.

        Returns:
            object: The hook node or tag.

        Note:
            This is a placeholder. Override in subclasses.
        """
        return object()

    def get_first_hook(self):
        """Get the hook from the root ancestor template.

        Returns:
            object: The first parent's hook node.
        """
        tpl = self.get_first_parent()
        return tpl.get_hook()

    # shapes -----------------------------------------------------------------------------------------------------------

    def add_shapes(self):
        """Add control shapes to template nodes.

        Note:
            This is a placeholder. Override in subclasses.
        """
        pass

    def build_shapes(self):
        """Build and configure control shapes.

        Note:
            This is a placeholder. Override in subclasses.
        """
        pass

    def delete_shapes(self):
        """Delete control shapes from template nodes.

        Returns:
            list: List of deleted shape nodes.

        Note:
            This is a placeholder. Override in subclasses.
        """
        return []

    # hierarchy ----------------------------------------------------------------

    def build_groups(self):
        """Build the group hierarchy for this template.

        Note:
            This is a placeholder. Override in subclasses.
        """
        pass

    def build_virtual_dag(self):
        """Build the virtual DAG connections for pickwalk.

        Note:
            This is a placeholder. Override in subclasses.
        """
        pass


Template.get_all_modules()
