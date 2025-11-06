# coding: utf-8

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

    def __new__(mcs, name, bases, attrs):
        new_class = super(TemplateMeta, mcs).__new__(mcs, name, bases, attrs)
        new_class.funcs = dict()  # each class gets its own funcs dict
        return new_class


class Template(object):
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
        # return instance of the corresponding class of template
        module_name = cls.get_module_from_node(node)
        new_cls = cls.get_class(module_name)

        return super(Template, new_cls).__new__(new_cls)

    def __init__(self, node):
        # init template instance from the given node
        self.node = node

        self.branches = ['']  # branchless default
        self.root = self.node

        self.modes = set()

    def __str__(self):
        return self.name

    def __eq__(self, other):
        if isinstance(other, Template):
            return self.node == other.node
        return False

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash(self.node) ^ hash(Template)

    @classmethod
    def get_class_module(cls, name):

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
        pass

    # instance node ----------------------------------------------------------------------------------------------------

    @property
    def name(self):
        return ''

    @staticmethod
    def create(tpl, parent=None, name=None, data=None, root=None, joint=True):
        pass

    def remove(self):
        pass

    def rename(self, name):
        pass

    def rename_root(self):
        pass

    def rename_template(self):
        pass

    @staticmethod
    def cleanup_name(name):
        name = str(name)
        name = name.replace(' ', '_')
        name = ''.join([c for c in name if c.isalnum() or c == '_'])
        return name

    @staticmethod
    def get_from_node(node):
        return Template(node)

    def build(self, modes=None):
        pass

    def build_template(self, data):
        """ placeholder """
        pass

    def build_rig(self):
        """ placeholder """
        pass

    def get_guide_data(self, user_data):
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
        # merge common data
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
        # warning: no multi asset abstract possible
        node = Nodes.get_id(self.name)
        check = node == self.node
        if not check:
            log.warning('/!\\ {} is not valid! (duplicate ids)'.format(self))
        return check

    def get_name(self, name):
        return ''

    def set_name(self, name, v):
        pass

    def has_opt(self, opt):
        if opt in self.template_data['opts']:
            return True
        return False

    def get_opt(self, opt):
        return object()

    def get_branch_opt(self, opt):
        return object()

    @staticmethod
    def branch_opt(v):
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
        pass

    # navigation -------------------------------------------------------------------------------------------------------

    @staticmethod
    def get_all_template_nodes(self):
        return []

    @staticmethod
    def check_new_name_validity(self, name):
        return True

    def get_children(self, root=None, children=None):
        return []

    def get_all_children(self, children=None):
        if children is None:
            children = []

        for child in self.get_children():
            children.append(child)
            child.get_all_children(children)

        return children

    def get_parent(self, root=None):
        return None

    def get_siblings(self):
        return []

    def get_all_parents(self, parents=None):
        if parents is None:
            parents = []

        parent = self.get_parent()
        if parent is not None:
            parents.append(parent)
            parent.get_all_parents(parents)

        return parents

    def get_first_parent(self):
        parents = self.get_all_parents()
        if parents:
            return parents[-1]
        else:
            return self

    def get_all_related_templates(self):
        templates = []
        for template in self.get_first_parent().get_siblings():
            templates.append(template)
            templates += template.get_all_children()
        return templates

    # structures -------------------------------------------------------------------------------------------------------

    def get_template_nodes(self, root=None, nodes=None):
        return []

    def get_template_chain(self, root=None, nodes=None):
        return []

    def get_structure(self, name):
        return []

    def set_structure(self, struct, v):
        return True

    def delete_template_branches(self):
        pass

    def build_template_branches(self):
        pass

    def update_branch_id(self, e, branch_ids0, branch_ids, all_ids, path=False):
        # e: element à inspecter
        # branch_ids0: ids à remplacer
        # branch_ids: ids de remplacement

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
        n = sep.join(self.branches)
        if n:
            n = sep + n
        return n

    def get_branch_id(self):
        if self.branches[0] or len(self.branches) > 1:
            return ('.{}' * len(self.branches)).format(*self.branches)
        return ''

    def get_branch_ids(self):
        _branches = self.branches
        _root = self.root

        branch_ids = []
        for self.branches, self.root in self.get_branches():
            branch_ids.append(self.get_branch_id())

        self.branches = _branches
        self.root = _root

        return branch_ids

    def do_flip(self):
        flip = False
        for branch in self.branches:
            for axis, pairs in Template.branch_pairs.items():
                for pair in pairs:
                    if branch == pair[1]:
                        flip = not flip
        return flip

    def get_sym_axis(self):

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
        pass

    def set_id(self, node, tag):
        return tag

    # hooks
    def set_hook(self, node, hook, tag):
        pass

    def get_hook(self, tag=False):
        return object()

    def get_first_hook(self):
        tpl = self.get_first_parent()
        return tpl.get_hook()

    # shapes -----------------------------------------------------------------------------------------------------------

    def add_shapes(self):
        pass

    def build_shapes(self):
        pass

    def delete_shapes(self):
        return []

    # hierarchy ----------------------------------------------------------------

    def build_groups(self):
        pass

    def build_virtual_dag(self):
        pass


Template.get_all_modules()
