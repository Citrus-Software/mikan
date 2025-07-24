# coding: utf-8

import yaml
import itertools
from copy import deepcopy

import meta_nodal_py as kl
from meta_nodal_py.Imath import V3f, M44f, Euler

from mikan.core import abstract
from mikan.core.logger import create_logger
from mikan.core.utils import get_slice, re_is_int, re_get_keys, flatten_list
from mikan.core.utils.yamlutils import YamlLoader

from ..lib import ConfigParser
from ..lib import (
    mirror_joints, axis_to_vector, point_constraint, aim_constraint, merge_transform,
    find_target, find_closest_node, duplicate_joint, connect_reverse, set_virtual_parent
)
from ..lib.commands import *

from .node import Nodes
from .control import Group, Control
from .shape import Shape

__all__ = ['Template']

log = create_logger()


class Template(abstract.Template):
    """
    Main class for all components of different types of templates
    """
    software = 'tangerine'

    def __repr__(self):
        return f"Template('{self.node.get_name()}')"

    @classmethod
    def get_module_from_node(cls, node):
        if not node.get_dynamic_plug('gem_module'):
            raise RuntimeError(f'node "{node}" is not valid')
        return node.gem_module.get_value()

    @property
    def name(self):
        for i in self.node.gem_id.get_value().split(';'):
            if '::' not in i:
                return i

    @staticmethod
    def create(tpl, parent=None, name=None, data=None, root=None, joint=True):
        """
        initialize node to create a proper template instance.
        need module name, a base name and a parent eventually
        if a root is given, it will use it instead of creating a new hierarchy
        """

        # check if module exists
        cls = Template.get_class(tpl)

        # check if nodes exist
        if root is not None:
            if type(root) not in [kl.SceneGraphNode, kl.Joint]:
                raise TypeError('given root is not a valid Node')

            # check if already set
            if root.get_dynamic_plug('gem_type'):
                if root.gem_type.get_value() == Template.type_name:
                    return Template(root)
                else:
                    raise RuntimeError('root is invalid (gem_type already exists)')

        if parent is not None:
            if type(parent) not in [kl.SceneGraphNode, kl.Joint]:
                raise TypeError('given parent is not a valid Node')
        else:
            parent = find_root()

        if root and parent and root.get_parent() != parent:
            root.reparent(parent)

        # get name
        if name is None:
            name = cls.template_data['name']
        name = Template.cleanup_name(name)
        name = Template.get_next_unique_name(name, parent)

        # create root node
        joint = cls.template_data.get('guides', {}).get('joint', joint)

        if root is None:
            if joint:
                root = kl.Joint(parent, f'tpl_{name}')
            else:
                root = kl.SceneGraphNode(parent, f'tpl_{name}')

        # add attributes
        add_plug(root, 'gem_type', str, default_value=Template.type_name)

        Nodes.set_id(root, name)

        add_plug(root, 'gem_module', str, default_value=tpl)

        # return instance from created node
        it = Template(root)
        data = it.get_guide_data(data)
        it.build_template(data)

        # conform nodes name
        for node in it.get_template_nodes():
            name = node.get_name()
            if type(node) is kl.SceneGraphNode and name.startswith('tpl_'):
                name = 'tpx_' + name[4:]
                node.rename(name)

        return it

    def remove(self):
        self.node.remove_from_parent()
        Nodes.rebuild()

    def rename(self):
        pass

    def build(self, modes=None):
        isolate = False
        if self.get_opt('isolate_skin'):
            isolate = True

        for self.branches, self.root in self.get_branches():
            log.debug(f'-- build: {repr(self)} {self.branches}')

            if not self.root:
                log.warning('/!\\ no template root, skip for this branch')
                continue

            # get valid hook
            self.hook = self.get_hook()
            if not self.hook:
                log.warning('/!\\ no hook, skip build for this branch')
                continue

            self.build_rig()
            self.build_shapes()
            if isolate:
                self.build_isolate_skin()

    @staticmethod
    def get_from_node(node):
        branch_id = ''

        if not (node.get_dynamic_plug('gem_type') and node.gem_type.get_value() == Template.type_name) or node.get_dynamic_plug('gem_branch'):
            if node.get_dynamic_plug('gem_id'):
                tpl_id = node.gem_id.get_value().split(';')[0].split('::')[0]
                tpl, _, branch_id = tpl_id.partition('.')
                _node = node
                node = Nodes.get_id(tpl)

                if isinstance(node, list):
                    asset = Nodes.get_asset_id(_node)
                    node = Nodes.get_id(tpl, asset=asset)

        if not node:
            return

        if node and not node.get_dynamic_plug('gem_module'):
            parent = node.get_parent()
            if parent:
                return Template.get_from_node(parent)
            else:
                return

        tpl = Template(node)
        if branch_id:
            tpl.branches = branch_id.split('.')
        return tpl

    def get_name(self, name):
        data = self.template_data.get('names', {})

        if name not in data:
            raise RuntimeError(f'name {name} not available in module "{self.node.gem_module.get_value()}"')

        # check saved data
        attr = f'gem_name_{name}'
        plug = self.node.get_dynamic_plug(attr)
        if plug:
            return plug.get_value()

        return data[name]

    def set_name(self, name, v):
        data = self.template_data.get('names', {})

        if name not in data:
            raise RuntimeError(f'name {name} not available in module "{self.node.gem_module.get_value()}"')

        attr = f'gem_name_{name}'
        rm = False

        if v != data[name]:
            if not self.node.get_dynamic_plug(attr):
                add_plug(self.node, attr, str, default_value=v)
        else:
            rm = True

        if rm:
            try:
                plug = self.node.get_dynamic_plug(attr)
                if plug:
                    plug.set_value(v)
                    self.node.remove_dynamic_plug(attr)
            except:
                pass
        return True

    def get_opt_plug(self, opt):
        plug_name = f'gem_opt_{opt}'
        plug = self.node.get_dynamic_plug(plug_name)
        if plug:
            return plug

        data = self.template_data['opts']
        if 'legacy' in data[opt]:
            plug_name = f'gem_opt_{data[opt]["legacy"]}'
            plug = self.node.get_dynamic_plug(plug_name)
            if plug:
                return plug

    def get_opt(self, opt, default=False):
        data = self.template_data['opts']

        if opt not in data:
            raise RuntimeError(f'option {opt} not available in module "{self.node.gem_module.get_value()}"')

        v = data[opt]['value']

        # check saved data
        plug = self.get_opt_plug(opt)
        if plug and not default:
            v = plug.get_value()

        # yaml eval
        if data[opt].get('yaml') and v:
            v = yaml.load(v, Loader=YamlLoader)

        # enum filter
        if 'enum' in data[opt]:
            if isinstance(v, int) and v in data[opt]['enum']:
                return data[opt]['enum'][v]
            elif str(v) in data[opt]['enum'].values():
                return str(v)
            else:
                return self.get_opt(opt, default=True)

        return v

    def get_branch_opt(self, opt):
        # return automatically reversed option
        v = self.get_opt(opt)
        if self.do_flip():
            v = Template.branch_opt(v)
        return v

    def set_opt(self, opt, v):
        data = self.template_data['opts']

        if opt not in data:
            raise RuntimeError(f'"{opt}" option is not available in template "{self.node.gem_module.get_value()}"')

        # compare
        dv = data[opt]['value']

        # filter
        if data[opt].get('yaml'):
            if v:
                v = yaml.dump(v, default_flow_style=True).replace('...', '').strip('\n')

        enum = data[opt].get('enum')
        if enum:
            if not isinstance(v, int):
                for k in enum:
                    if enum[k] == str(v):
                        v = k

            if not isinstance(dv, int):
                for k in enum:
                    if enum[k] == str(dv):
                        dv = k

        # save opts
        plug = self.get_opt_plug(opt)
        if not plug:
            attr = f'gem_opt_{opt}'

            if v == dv:
                return False

            if enum:
                plug = add_plug(self.node, attr, int, default_value=dv, enum=enum)
            elif isinstance(v, bool):
                plug = add_plug(self.node, attr, bool, default_value=dv)
            elif isinstance(v, int):
                plug = add_plug(self.node, attr, int, default_value=dv)
            elif isinstance(v, float):
                plug = add_plug(self.node, attr, float, default_value=dv)
            elif isinstance(v, list) and len(v) == 3:
                plug = add_plug(self.node, attr, kl.V3f, default_value=dv)
            elif isinstance(v, str):
                plug = add_plug(self.node, attr, str)
            else:
                raise ValueError('invalid option type')

            set_plug(plug, min_value=data[opt].get('min'), max_value=data[opt].get('max'))

        if v == plug.get_value():
            return False

        plug.set_value(v)

    def reset_opt(self, opt):
        plug = self.get_opt_plug(opt)
        if plug is None:
            return

        attr = plug.get_name()
        self.node.remove_dynamic_plug(attr)

    # navigation -------------------------------------------------------------------------------------------------------

    def check_validity(self):
        asset_id = Nodes.current_asset
        if asset_id is None:
            asset_id = Nodes.get_asset_id(self.node)

        node = Nodes.get_id(self.name, asset=asset_id)
        check = node == self.node
        if not check:
            log.warning(f'/!\\ {self} is not valid! (duplicate ids)')

        # TODO: check de validité avec les subnames?
        return check

    @staticmethod
    def get_all_template_nodes():
        tpls = []
        for node in ls():
            if node.get_dynamic_plug('gem_type') and node.gem_type.get_value() == 'template':
                tpls.append(node)
        return tpls

    @staticmethod
    def get_next_unique_name(name, node):
        Nodes.check_nodes()
        asset_id = Nodes.get_asset_id(node) if node else ''
        tree = Nodes.nodes[asset_id]
        names = list(tree.dict)

        while name in names:
            head = name.rstrip('0123456789')
            tail = name[len(head):]
            if not tail:
                tail = 1
            tail = int(tail) + 1
            name = head + str(tail)
        return name

    def get_children(self, root=None, children=None):
        if root is None:
            root = self.node

        if children is None:
            children = []

        for child in root.get_children():
            if child.get_dynamic_plug('gem_type') and child.gem_type.get_value() == Template.type_name:
                children.append(Template(child))
            else:
                self.get_children(child, children)

        return children

    def get_parent(self, root=None):
        if root is None:
            root = self.node

        node = root.get_parent()
        if node:
            if node.get_dynamic_plug('gem_type') and node.gem_type.get_value() == Template.type_name:
                return Template(node)
            else:
                return self.get_parent(root=node)

        return None

    def get_siblings(self):
        siblings = []

        nodes = self.node.get_parent().get_children()

        for node in nodes:
            if node.get_dynamic_plug('gem_type') and node.gem_type.get_value() == Template.type_name:
                siblings.append(Template(node))

        return siblings

    # structures -------------------------------------------------------------------------------------------------------

    def get_template_nodes(self, root=None, nodes=None, hidden=True):
        if root is None:
            root = self.root
        if nodes is None:
            nodes = [root]

        for child in root.get_children():
            if child.get_dynamic_plug('gem_type') and child.gem_type.get_value() == Template.type_name:
                continue
            if not hidden and child.get_name().split(':')[-1].startswith('_'):
                continue
            nodes.append(child)
            self.get_template_nodes(child, nodes, hidden=hidden)

        return nodes

    def get_template_chain(self, root=None, nodes=None):
        if root is None:
            root = self.root
        if nodes is None:
            nodes = [root]

        child = []
        for c in root.get_children():
            if type(c) not in [kl.SceneGraphNode, kl.Joint]:
                # skip if not hierarchy
                continue
            if c.get_name().split(':')[-1].startswith('_'):
                # skip if node is ignored
                continue
            if c.get_dynamic_plug('gem_template'):
                # skip if node is tagged
                continue
            if c.get_dynamic_plug('gem_type') and c.gem_type.get_value() == Template.type_name:
                # skip if different template
                continue
            else:
                child.append(c)

        if len(child) == 1:
            nodes += child
            self.get_template_chain(child[0], nodes)

        return nodes

    def get_structure(self, name):
        item = re_get_keys.findall(name)
        if item:
            name = name.split('[')[0]
            item = item[0]
        else:
            item = None

        if name == '.':
            return self.root

        data = self.template_data.get('structure', {})
        if name not in data:
            raise RuntimeError(f'structure "{name}" not available in module "{self.node.gem_module.get_value()}"')

        struct = data[name]

        # check saved data
        attr = f'gem_struct_{name}'
        plug = self.node.get_dynamic_plug(attr)
        if plug:
            struct = plug.get_value()

        mounts = []
        # get by tag
        if not struct:
            for node in self.get_template_nodes():
                if node.get_dynamic_plug('gem_template') and node.gem_template.get_value() == name:
                    mounts = [node]

        # get by chain index
        else:
            for spart in struct.split('+'):
                mount = [self.root]
                for s in spart.split('/'):
                    if not s:
                        continue
                    if s == '.':
                        continue
                    chain = self.get_template_chain(mount[-1])
                    if s == '*':
                        mount = chain
                        continue
                    if re_is_int.match(s):
                        mount = [chain[int(s)]]
                    else:
                        se = s.split('[')
                        mount = self.get_structure(se[0])
                        if len(se) > 1:
                            se[1] = se[1].split(']')[0]
                            if ':' in se[1]:
                                mount = mount[get_slice(se[1])]
                            else:
                                mount = [mount[int(se[1])]]
                mounts.extend(mount)

        if item:
            if ':' in item:
                return mounts[get_slice(item)]
            else:
                i = int(item)
                if i < len(mounts) and abs(i) <= len(mounts):
                    return mounts[i]
                else:
                    return None

        return mounts

    def set_structure(self, struct, v):
        data = self.template_data.get('structure', {})

        if struct not in data:
            raise RuntimeError(f'structure {struct} not available in module "{self.node.gem_module.get_value()}"')

        attr = f'gem_struct_{struct}'
        rm = False

        if v != data[struct]:
            plug = self.node.get_dynamic_plug(attr)
            if not plug:
                plug = add_plug(self.node, attr, str)
            plug.set_value(v)
        else:
            rm = True

        if rm:
            try:
                plug = self.node.get_dynamic_plug(attr)
                if plug:
                    plug.set_value(v)
                    self.node.remove_dynamic_plug(attr)
            except:
                pass
        return True

    def delete_template_branches(self):
        # cleanup branches
        roots = Nodes.get_id(f'{self.name}::branch', as_list=True)

        for root in itertools.chain([self.node], [n for n in roots if n]):
            for node in itertools.chain([root], ls(root=root)):
                if not node:
                    continue
                if node.get_dynamic_plug('gem_type') and node.gem_type.get_value() == 'branch':
                    node.remove_from_parent()

    def build_template_branches(self):

        current_asset = Nodes.current_asset
        Nodes.current_asset = Nodes.get_asset_id(self.node)

        # rebuild branched chains
        self.delete_template_branches()
        templates = [self] + self.get_all_children()

        root_keys = list(self.get_branches())[0][0][:-1]
        root_id = ('.{}' * len(root_keys)).format(*root_keys)

        def _set_branch(node, branch_id):
            plug_name = 'gem_branch'
            plug = node.get_dynamic_plug(plug_name)
            if not plug:
                plug = add_plug(node, plug_name, str, default_value=root_id)
            f = plug.get_value()[len(root_id):]
            plug.set_value(f'{root_id}.{branch_id}{f}')

        # tmp mirror edits
        tmp_edits = []
        for tpl in templates:
            edits = Nodes.get_id(f'{tpl.name}::edit')
            if not edits:
                continue

            edits = {}
            branch_keys = list(tpl.get_branches())

            for branch_ids, _root in branch_keys:
                branch_id = ''
                if branch_ids[0] or len(branch_ids) > 1:
                    branch_id = ('.{}' * len(branch_ids)).format(*branch_ids)
                edit = Nodes.get_id(f'{tpl.name}{branch_id}::edit')
                if edit:
                    edits[branch_id] = edit

            for branch_ids, _root in branch_keys:
                branch_id = ''
                if branch_ids[0] or len(branch_ids) > 1:
                    branch_id = ('.{}' * len(branch_ids)).format(*branch_ids)
                edit = edits.get(branch_id)
                if edit:
                    continue

                # check if build is possible
                mxy = 0
                myz = 0
                mxz = 0
                mbranch_id = None
                for axis, pairs in Template.branch_pairs.items():
                    for pair in pairs:
                        if branch_ids[-1] in pair:
                            if axis == 'x':
                                myz = 1
                            elif axis == 'y':
                                mxz = 1
                            elif axis == 'z':
                                mxy = 1
                            _ = branch_ids[:]
                            _[-1] = pair[0]
                            mbranch_id = ('.{}' * len(_)).format(*_)
                medit = edits.get(mbranch_id)
                if medit is None:
                    continue

                branched_nodes = mirror_joints(medit, mxy=mxy, myz=myz, mxz=mxz)
                tmp_edits.append(branched_nodes[0])
                for node in branched_nodes:
                    if not node.has_parent():
                        continue
                    if node.get_dynamic_plug('gem_shape'):
                        node.remove_from_parent()
                        continue

                    if node.get_dynamic_plug('gem_id'):
                        plug = node.get_dynamic_plug('gem_id')
                        gem_ids = [gem_id for gem_id in plug.get_value().split(';') if gem_id]
                        if not gem_ids:
                            continue
                        for i, e in enumerate(gem_ids):
                            _id = e.split('::')
                            _name, _sep, _keys = _id[0].partition('.')
                            if not _keys:
                                continue
                            _keys = '.' + _keys
                            if _keys.startswith(mbranch_id):
                                _keys = branch_id + _keys[len(mbranch_id):]
                                gem_ids[i] = _name + _keys + '::' + _id[1]

                        node.gem_id.set_value('')
                        for gem_id in gem_ids:
                            Nodes.set_id(node, gem_id)
                        continue

        # mirror branches
        roots = []
        for tpl in templates[::-1]:
            # build secondary branches
            branch_ids = tpl.get_opt('branches')
            if not branch_ids:
                branch_ids = ['']

            for f, branch_id in enumerate(branch_ids[1:]):
                # create new branch
                mxy = 0
                myz = 0
                mxz = 0
                for axis, pairs in Template.branch_pairs.items():
                    for pair in pairs:
                        if branch_id in pair:
                            if axis == 'x':
                                myz = 1
                            elif axis == 'y':
                                mxz = 1
                            elif axis == 'z':
                                mxy = 1
                # todo: loop to create multiple axis branch

                branched_nodes = mirror_joints(tpl.node, mxy=mxy, myz=myz, mxz=mxz)

                branch_root = branched_nodes[0]
                _name = tpl.node.get_name().split(':')[-1]
                branch_root.rename(f'_{_name}__sfx__')

                branch_root.gem_type.set_value('branch')
                # set_plug(branch_root.gem_type, locked=True)
                _set_branch(branch_root, branch_id)
                roots.append(branch_root)

                for node in branched_nodes[1:]:
                    if not node.has_parent():
                        continue
                    if node.get_dynamic_plug('gem_shape'):
                        node.remove_from_parent()
                        continue

                    if node.get_dynamic_plug('gem_type') and node.gem_type.get_value() == 'branch':
                        if node not in roots:
                            roots.append(node)

                    if node.get_dynamic_plug('gem_branch') or (
                            node.get_dynamic_plug('gem_type') and node.gem_type.get_value() == Template.type_name):
                        _set_branch(node, branch_id)

                    if '__sfx__' not in node.get_name():
                        node.rename(f'{node.get_name()}__sfx__')

            if branch_ids[0]:
                _set_branch(tpl.node, branch_ids[0])
                for node in ls(root=tpl.node):
                    if node == tpl.node:
                        continue
                    if node.get_dynamic_plug('gem_type') and node.gem_type.get_value() == 'branch':
                        _set_branch(node, branch_ids[0])
                        continue

                    if node.get_dynamic_plug('gem_branch') or (
                            node.get_dynamic_plug('gem_type') and node.gem_type.get_value() == Template.type_name):
                        _set_branch(node, branch_ids[0])

        # inject branch id
        injected = set()
        for root in roots:
            branch_sfx = ''
            branch_ids = []

            for node in [root] + find_all_descendant(root):
                if node in injected:
                    continue
                else:
                    injected.add(node)

                if not node.has_parent():
                    continue

                all_ids = set()
                branch_ids0 = []

                _tpl = Template.get_from_node(node)
                _branch_ids = _tpl.get_branch_ids() if _tpl else None
                if _branch_ids:
                    branch_ids0 = _branch_ids[0][1:].split('.')
                    for f in _branch_ids:
                        all_ids = all_ids.union(set(f.strip('.').split('.')))

                if node.get_dynamic_plug('gem_branch'):
                    branch_keys = node.gem_branch.get_value()
                    branch_ids = branch_keys.strip('.').split('.')

                    tag = f'{node.gem_id.get_value()}{branch_keys}::branch'
                    node.gem_id.set_value('')
                    Nodes.set_id(node, tag)

                    branch_sfx = '_'.join(branch_ids)
                    if branch_sfx:
                        branch_sfx = '_' + branch_sfx

                    n = node.get_name()
                    if not n.startswith('_'):
                        node.rename('_' + n)

                if '__sfx__' in node.get_name():
                    node_split = node.get_name().partition('__sfx__')
                    node.rename(node_split[0] + branch_sfx)

                rm_plug = []
                for plug in node.get_dynamic_plugs():
                    plug_name = plug.get_name()
                    if plug_name in ['gem_template', 'gem_scale']:
                        continue
                    if plug_name == 'gem_type' and plug.get_value() == 'branch':
                        continue
                    if plug_name.startswith('gem_var_'):
                        continue
                    if plug_name.startswith('gem_enable'):
                        continue

                    # update gem_id
                    if plug_name == 'gem_id':
                        gem_ids = [gem_id for gem_id in plug.get_value().split(';') if gem_id]
                        if not gem_ids:
                            continue
                        for i, e in enumerate(gem_ids):
                            _e = self.update_branch_id(e, branch_ids0, branch_ids, all_ids)
                            if _e:
                                gem_ids[i] = _e

                        # check if edit already exists
                        skip_edit = False

                        for gem_id in gem_ids:
                            if '::edit' in gem_id:
                                _edit = Nodes.get_id(gem_id)
                                if _edit:
                                    node.remove_from_parent()
                                    skip_edit = True
                                    break

                        if skip_edit:
                            break

                        # update tree ids
                        node.gem_id.set_value('')
                        for gem_id in gem_ids:
                            Nodes.set_id(node, gem_id)

                        if '::branch' in plug.get_value():
                            if not node.get_dynamic_plug('gem_type'):
                                add_plug(node, 'gem_type', str)
                                node.gem_type.set_value('branch')
                        if '::edit' in plug.get_value():
                            if not node.get_dynamic_plug('gem_type'):
                                add_plug(node, 'gem_type', str)
                                node.gem_type.set_value('edit')

                        continue

                    # update branch ids in mods
                    if plug_name == 'notes':
                        for node_mod in list(ConfigParser(node)['mod']) + list(ConfigParser(node)['deformer']):
                            notes = node_mod.read()
                            lines = notes.splitlines()
                            for line in lines:
                                if line.startswith('#/') and 'solo' in line[2:].split():
                                    notes = '# deleted from branch'
                            if notes:
                                elems = notes.split(' ')
                                for i, e in enumerate(elems):
                                    _e = self.update_branch_id(e, branch_ids0, branch_ids, all_ids)
                                    if _e:
                                        elems[i] = _e

                                notes = ' '.join(elems)
                                node_mod.write(notes)
                        continue

                    rm_plug.append(plug_name)
                for plug in rm_plug:
                    node.remove_dynamic_plug(plug)

        for tpl in templates[::-1]:
            if tpl.node.get_dynamic_plug('gem_branch'):
                tpl.node.gem_branch.set_value('')
                try:
                    tpl.node.remove_dynamic_plug('gem_branch')
                except:
                    pass

        # update from edit
        for tpl in templates:
            edits = Nodes.get_id(f'{tpl.name}::edit')
            if not edits:
                continue

            tpl.root = tpl.node

            mapped = [tpl.node]
            mapping = []
            for struct in tpl.template_data.get('structure', {}):
                for i, node in enumerate(tpl.get_structure(struct)):
                    if node not in mapped:
                        mapped.append(node)
                        mapping.append((struct, i))

            for tpl.branches, tpl.root in list(tpl.get_branches())[1:]:
                root = tpl.root

                edit = Nodes.get_id('{}{}::edit'.format(tpl.name, tpl.get_branch_id()))
                if edit:
                    copy_transform(edit, root)

                    for struct, i in mapping:
                        try:
                            tpl.root = edit
                            edit_node = tpl.get_structure(struct)[i]
                            tpl.root = root
                            tpl_node = tpl.get_structure(struct)[i]
                            copy_transform(edit_node, tpl_node)
                        except:
                            log.warning(f'/!\\ couldn\'t retarget branch edit "{struct}[{i}]" of {tpl.name}{tpl.get_branch_id()}')

                    root.show.set_value(False)

        # remove tmp edits
        for tmp_edit in tmp_edits:
            tmp_edit.remove_from_parent()

        # update dict
        Nodes.rebuild()
        Nodes.current_asset = current_asset

        return roots

    # tag system -------------------------------------------------------------------------------------------------------

    def set_template_id(self, node, tag):
        if not node.get_dynamic_plug('gem_template'):
            add_plug(node, 'gem_template', str)
        ids = node.gem_template.get_value() or None
        if ids is None:
            ids = [tag]
        else:
            ids = ids.split(';')
            if tag not in ids:
                ids.append(tag)
        node.gem_template.set_value(';'.join(ids))

    def set_id(self, node, tag, template=True):
        if template:
            name = self.name
            branch_id = self.get_branch_id()
            if branch_id:
                name += branch_id
            tag = f'{name}::{tag}'
        else:
            tag = f'::{tag}'

        Nodes.set_id(node, tag)
        return tag

    # hooks
    def set_hook(self, node, hook, tag):
        tag = self.set_id(hook, tag)
        if not node.get_dynamic_plug('gem_hook'):
            add_plug(node, 'gem_hook', str)
        if not hook.get_dynamic_plug('gem_hook'):
            add_plug(hook, 'gem_hook', str)
        node.gem_hook.set_value(tag)
        hook.gem_hook.connect(node.gem_hook)

    def get_virtual_hook(self, node=None, plug=None):
        """Returns associated hook from given rig node

        Arguments:
            node (mx.Node, optional): rig node to get hook.
            plug (str, optional): plug name where hook id is stored, "gem_hook" by default
            hooks (dict, optional): template hooks dictionary

        Returns:
            mx.Node: the associated hook node
            str: tag name of the hook if tag argument is on

        """
        virtual = self.get_opt('virtual_parent')
        if not virtual:
            return

        # find from virtual parent
        virtual_parent = Nodes.get_id(virtual) if virtual[0].isalpha() else None

        if isinstance(virtual_parent, list):
            virtual_parent = find_closest_node(node, virtual_parent)

        # find from template
        if virtual_parent and isinstance(virtual_parent, kl.SceneGraphNode):
            if virtual_parent.get_dynamic_plug('gem_type') and virtual_parent.gem_type.get_value() == Template.type_name:
                tpl_parent = Template(virtual_parent)
                tpl_nodes = []
                for _branch, _root in tpl_parent.get_branches():
                    tpl_parent.root = _root
                    _nodes = tpl_parent.get_template_nodes(hidden=False)
                    tpl_nodes += _nodes
                    if self.branches == _branch:
                        tpl_nodes = _nodes
                        break
                tpl_nodes = [_node for _node in tpl_nodes if isinstance(_node, kl.SceneGraphNode)]
                if tpl_nodes:
                    closest = find_closest_node(node, tpl_nodes)
                    return self.get_hook(closest, plug=plug, virtual=True)

            # find from rig
            else:
                hook = self.get_template_hook(virtual_parent)
                if hook:
                    return self.get_hook(hook, plug=plug, virtual=True)

        else:
            return None

        # find top node
        top = node

        name = None
        tpl = self.get_from_node(node)
        if tpl:
            name = tpl.name

        parent = node
        while True:
            parent = parent.get_parent()
            if not parent:
                break
            plug_id = parent.get_dynamic_plug('gem_id')
            if not plug_id:
                continue
            key = plug_id.get_value()
            if key.startswith(name + '.') or key.startswith(name + '::'):
                top = parent
            else:
                break

        # check transform input
        drivers = []
        target = find_target(top)
        if target:
            drivers.append(target)
        drivers.append(top.get_parent())  # check reparent

        for driver in drivers:
            plug_id = driver.get_dynamic_plug('gem_id')
            if plug_id:
                keys = plug_id.get_value()
                if keys.startswith(name + '.') or keys.startswith(name + '::'):
                    continue

                hook = self.get_template_hook(driver)
                if hook:
                    return self.get_hook(hook, plug=plug, virtual=True)

    def get_template_hook(self, node):
        while True:
            plugs = []
            _plug = node.get_dynamic_plug('gem_hook')
            if _plug:
                plugs.append(_plug)
            plugs += [_plug for _plug in node.get_dynamic_plugs() if _plug.get_name().startswith('gem_dag_')]

            for _plug in plugs:
                _input = _plug.get_input().get_node()
                if _input:
                    return _input

            node = node.get_parent()
            if node is None:
                break

    def get_hook(self, node=None, tag=False, plug=None, virtual=False):
        """Returns associated hook from given template node

        Arguments:
            node (mx.Node, optional): template node to get hook. If no node is given, it will use template root instead
            tag (bool, default: False): returns tag name instead
            plug (str, optional): plug name where hook id is stored, "gem_hook" by default
            virtual (bool, optional): get hook directly from given node and above

        Returns:
            mx.Node: the associated hook node
            str: tag name of the hook if tag argument is on

        """
        if node is None:
            node = self.root
        if plug is None:
            plug = 'gem_hook'

        if not isinstance(node, kl.SceneGraphNode):
            raise ValueError(f'"{node}" cannot have a hook')

        if virtual:
            parent = node
        else:
            parent = node.get_parent()

        if isinstance(parent, kl.SceneGraphNode):
            gem_hook = parent.get_dynamic_plug(plug)
            if gem_hook:
                if tag:
                    return gem_hook.get_value()
                try:
                    hook = Nodes.get_id(gem_hook.get_value())
                    if not hook:
                        raise KeyError()
                    if not isinstance(hook, kl.SceneGraphNode):
                        return hook.get_parent()
                    return hook
                except KeyError:
                    return self.get_hook(parent, tag=tag, plug=plug)
            else:
                return self.get_hook(parent, tag=tag, plug=plug)

        elif node != self.root:
            if not tag:
                return node

    def get_rig_hook(self):
        node = Nodes.get_id('::rig')
        if not node:
            hook = self.get_first_hook()
            node = kl.SceneGraphNode(hook, 'rig')
            Nodes.set_id(node, '::rig')
        return node

    def get_bind_hook(self):
        node = Nodes.get_id('::bind')
        if not node:
            hook = self.get_first_hook()
            node = kl.SceneGraphNode(hook, 'bind')
            Nodes.set_id(node, '::bind')
        return node

    def build_isolate_skin(self):
        parent = self.get_bind_hook()

        for sk in Nodes.get_id('{}{}::skin'.format(self.name, self.get_branch_id()), as_list=True):
            name = sk.get_name().split(':')[-1]
            name = '_'.join(name.split('_')[1:])
            sk.rename('j_' + name)

            j = duplicate_joint(sk, p=parent, n='sk_' + name)

            # transfer ids
            ids = sk.gem_id.get_value().split(';')
            new_ids = []
            replaced_ids = []
            for tag in ids:
                if '::skin.' in tag:
                    Nodes.set_id(j, tag)
                    replaced_ids.append(tag.replace('::skin.', '::out.skin.'))
                else:
                    new_ids.append(tag)

            sk.gem_id.set_value(';'.join(new_ids))
            for _id in replaced_ids:
                Nodes.set_id(sk, _id)

            # hook joint
            blend = kl.BlendWeightedTransforms(2, j, '_bmx')
            blend.transform_interp_in.set_value(False)

            blend.transform_in[0].connect(sk.world_transform)

            add_plug(j, 'custom_transform', M44f)
            j.custom_transform.set_value(sk.world_transform.get_value())
            blend.transform_in[1].connect(j.custom_transform)

            add_plug(j, 'blend_transform', float, min_value=0, max_value=1, keyable=True)
            blend.weight_in[1].connect(j.blend_transform)
            connect_reverse(j.blend_transform, blend.weight_in[0])

            _imx = kl.InverseM44f(j, '_imx')
            _imx.input.connect(j.parent_world_transform)
            _mmx = kl.MultM44f(j, '_mmx')
            _mmx.input[0].connect(blend.transform_out)
            _mmx.input[1].connect(_imx.output)
            j.transform.connect(_mmx.output)

    @classmethod
    def build_isolate_skeleton(cls):
        root = Nodes.get_id('::bind')
        if not root:
            return

        joints = root.get_children()
        _joints = set(joints)

        for j in joints:
            plug_list = j.find('gem_dag_children')
            if not plug_list:
                continue
            for idx in range(plug_list.input.get_size()):
                if plug_list.input.is_connected(idx):
                    child = plug_list.input.get_input(idx=idx).get_node()
                    if child in _joints:
                        child.reparent(j)

    # shapes -----------------------------------------------------------------------------------------------------------

    def add_shapes(self):
        data = deepcopy(self.template_data.get('shapes', {}))
        if not data:
            return

        current_asset = Nodes.current_asset
        Nodes.current_asset = Nodes.get_asset_id(self.node)
        shapes_tree = Nodes.shapes[Nodes.current_asset]

        branches = list(self.get_branches())
        branch_ids = self.get_branch_ids()

        _branches = self.branches
        _root = self.root
        for self.branches, self.root in branches:
            if not self.root:
                continue

            edit = Nodes.get_id('{}{}::edit'.format(self.name, self.get_branch_id()))
            if edit:
                self.root = edit

            # spawn more overlords
            for key in list(data):
                specs = data[key]
                if '*' in key and 'parent' in specs:
                    parents = self.get_structure(specs['parent'].replace('*', ':'))
                    for i, p in enumerate(parents):
                        new_key = key.replace('*', str(i))
                        new_specs = deepcopy(specs)
                        for k, _data in new_specs.items():
                            if isinstance(_data, str):
                                new_specs[k] = _data.replace('*', str(i))
                            elif isinstance(_data, list):
                                for _i in range(len(_data)):
                                    if isinstance(_data[_i], str):
                                        _data[_i] = _data[_i].replace('*', str(i))
                            elif isinstance(_data, dict):
                                for _k in _data:
                                    if isinstance(_data[_k], str):
                                        _data[_k] = _data[_k].replace('*', str(i))
                        data[new_key] = new_specs
                    del data[key]

            # spawn shape roots
            for key, specs in data.items():
                _branch_id = self.get_branch_id()
                key_id0 = f'{self.name}::{key}'
                key_id = f'{self.name}{_branch_id}::{key}'

                # skip only if no shapes
                shapes = []
                root = shapes_tree.get(key_id)

                if _branch_id == branch_ids[0] and not root:
                    root = shapes_tree.get(key_id0)

                if root:
                    for node in root.get_children():
                        if not isinstance(node, kl.SceneGraphNode):
                            continue
                        _shapes = node.get_children()
                        if not _shapes:
                            node.remove_from_parent()
                        for shape in _shapes:
                            if isinstance(shape, kl.SplineCurve):
                                shapes.append(node)

                # create shape root
                p = [self.root]
                if 'parent' in specs:
                    _p = self.get_structure(specs['parent'])
                    if _p:
                        if not isinstance(_p, list):
                            _p = [_p]
                        p = _p
                    else:
                        continue

                do_new = False
                if not root:
                    key_name = key.replace('.', '_').replace('*', 'all')
                    root = kl.SceneGraphNode(p[0], f'_shape_{self.name}_{key_name}{self.get_branch_suffix()}')
                    do_new = True
                do_flip = self.do_flip()

                # register
                if not root.get_dynamic_plug('gem_shape'):
                    add_plug(root, 'gem_shape', str)
                root.gem_shape.set_value(key_id)

                shapes_tree[key_id] = root

                # copy relative
                if 'reference' in specs:
                    if not root.get_dynamic_plug('gem_shape_reference'):
                        add_plug(root, 'gem_shape_reference', str)

                    _key_id = '{}{}::{}'.format(self.name, _branch_id, specs['reference'])
                    root.gem_shape_reference.set_value(_key_id)

                # if branch: copy from main shape
                if do_new and self.root != self.node:
                    _branch_id = self.get_branch_id().split('.')

                    for _axis, _pairs in Template.branch_pairs.items():
                        for _pair in _pairs:
                            for f, fid in enumerate(_branch_id):
                                if fid in _pair:
                                    _branch_id[f] = _pair[1 - _pair.index(fid)]
                                    break
                            else:
                                continue
                            break
                        else:
                            continue
                        break

                    shape_ids = ['.'.join(_branch_id)]
                    for fid in branch_ids:
                        if fid not in shape_ids:
                            shape_ids.append(fid)

                    main_root = None
                    for fid in shape_ids:
                        shape_id = '{}{}::{}'.format(self.name, fid, key)
                        main_root = shapes_tree.get(shape_id)
                        if main_root and main_root.get_children():
                            break

                    # if no main root this is not normal
                    if main_root:
                        for node in main_root.get_children():
                            # copy transform
                            xfo = main_root.transform.get_value()
                            xfo.setScale(V3f(*[abs(_s) for _s in xfo.scaling()]))
                            root.transform.set_value(xfo)

                            # copy shapes
                            if not isinstance(node, kl.SceneGraphNode):
                                continue
                            ds = None
                            for shape in node.get_children():
                                if isinstance(shape, kl.SplineCurve):
                                    if not ds:
                                        ds = kl.SceneGraphNode(root, node.get_name())
                                        ds.transform.set_value(node.transform.get_value())
                                    cv = kl.SplineCurve(ds, shape.get_name())
                                    cv.spline_in.connect(shape.spline_in)
                                    if Shape.is_shape_color_flip(shape):
                                        Shape.set_shape_color_flip(cv)

                                    if shape.get_dynamic_plug('gem_color'):
                                        rgb = Shape.color_to_rgb(shape.gem_color.get_value())
                                        if Shape.is_shape_color_flip(shape):
                                            rgb = Shape.get_color_flip(rgb)
                                        if do_flip:
                                            rgb = Shape.get_color_flip(rgb)
                                            Shape.set_shape_color_flip(cv)
                                        add_plug(cv, 'gem_color', str)
                                        cv.gem_color.set_value(Shape.rgb_to_hex(rgb))

                            if ds:
                                s = Shape(ds)
                                s.restore_color(force=True)
                                shapes.append(ds)

                # new shape
                if do_new and not shapes and 'shape' in specs:
                    s = Shape.create(specs['shape'], axis=specs.get('axis'))
                    s.node.set_parent(root)

                    n = root.get_name().replace('_shape_', 'shp_')
                    s.node.rename(n)

                    if 'size' in specs:
                        s.scale(specs['size'], absolute=True)

                    if 'color' in specs:
                        color = specs['color']
                        s.set_color(color)

                # preserve shapes from old root transformation
                if not do_new:
                    _shapes = {}
                    for _shp in [_shp for _shp in root.get_children() if isinstance(_shp, kl.SceneGraphNode)]:
                        _shapes[_shp] = _shp.world_transform.get_value()

                try:
                    root.transform.set_value(M44f())
                except:
                    pass

                # rig root
                if 'point' in specs:
                    point = specs['point']
                    if isinstance(point, list):
                        point = []
                        for _p in specs['point']:
                            _p = self.get_structure(_p)
                            if isinstance(_p, list):
                                point += _p
                            elif isinstance(_p, kl.Node):
                                point.append(_p)
                    else:
                        point = self.get_structure(_p)
                    point_constraint(point, root)
                else:
                    point_constraint(p, root)

                # do aim condition
                do_aim = True
                if 'do_aim' in specs:
                    for k in specs['do_aim']:
                        v = self.get_opt(k)
                        if isinstance(specs['do_aim'][k], list):
                            if v not in specs['do_aim'][k]:
                                do_aim = False
                                break
                        else:
                            if v != specs['do_aim'][k]:
                                do_aim = False
                                break

                # aim rig
                if 'aim' in specs and do_aim:
                    aim = specs['aim']
                    aim_world = axis_to_vector(aim)
                    if aim_world:
                        aim = None
                    else:
                        aim = self.get_structure(aim)

                    aim_args = {}
                    aim_args['aim_vector'] = V3f(0, 1, 0)
                    aim_args['up_vector'] = V3f(0, 0, 0)
                    aim_args['up_vector_world'] = V3f(0, 0, 0)
                    aim_args['up_object'] = None

                    if 'up_axis' in specs:
                        axis = axis_to_vector(specs['up_axis'])
                        aim_args['up_vector'] = axis
                    if do_flip:
                        aim_args['up_vector'] *= -1

                    if 'up' in specs:
                        up = specs['up']
                        up_world = axis_to_vector(up)

                        if up_world:
                            aim_args['up_vector_world'] = up_world
                            if 'up_axis' not in specs:
                                aim_args['up_vector'] = up_world
                        else:
                            up = self.get_structure(up) or None
                            if up:
                                aim_args['up_object'] = up[0]
                                aim_args['up_vector_object'] = V3f(0, 0, 0)

                    if 'aim_axis' in specs:
                        axis = axis_to_vector(specs['aim_axis'])
                        aim_args['aim_vector'] = axis
                    if do_flip:
                        aim_args['aim_vector'] *= -1

                    if aim_world:
                        aim = kl.SceneGraphNode(root.get_parent(), '_world_dir')

                    cnst = aim_constraint(aim, root, **aim_args)

                    if aim_world:
                        aim.transform.connect(cnst.input_transform)
                        cnst.input_target_world_transform.disconnect(restore_default=False)
                        mmx = kl.MultM44f(cnst, '_mmx')
                        mmx.input[1].set_value(M44f(aim_world, V3f(0, 0, 0), V3f(1, 1, 1), Euler.Default))
                        mmx.input[0].connect(aim.world_transform)
                        cnst.input_target_world_transform.connect(mmx.output)

                # restore shapes from old root transformation
                if not do_new:
                    for _shp, _wm in _shapes.items():
                        _shp.set_world_transform(_wm)

                # flip new shape
                if do_flip and do_new:
                    _srt = merge_transform(root)
                    _s = _srt.scale.disconnect(restore_default=False)
                    _srt.scale.set_value(_srt.scale.get_value() * -1)

        # exit
        self.branches = _branches
        self.root = _root
        Nodes.current_asset = current_asset

    def build_shapes(self):
        shapes_tree = Nodes.shapes[Nodes.current_asset]

        # copy shapes
        for node in shapes_tree.get(f'{self.name}{self.get_branch_id()}::*', [], as_list=True):
            key = node.gem_shape.get_value()
            targets = Nodes.get_id(key)  # get target controller

            targets_ref = None
            if node.get_dynamic_plug('gem_shape_reference'):
                key = node.gem_shape_reference.get_value()
                targets_ref = Nodes.get_id(key)

                if targets_ref:
                    targets, targets_ref = targets_ref, targets

            # copy shape to controller
            if type(targets) in [kl.SceneGraphNode, kl.Joint]:
                s = Shape(targets)
                if Shape(node).get_shapes():
                    s.copy(node, world=True)
                else:
                    for shape in node.get_children():
                        _s = Shape(shape)
                        if _s.get_shapes():
                            s.copy(shape, world=True)
                s.rename()
                s.shadow()

                if targets_ref:
                    if not isinstance(targets_ref, list):
                        s.move(targets_ref)
                    else:
                        for t in targets_ref:
                            Shape(t).copy(targets)
                        s.remove()

            elif isinstance(targets, list):
                s = Shape(targets[0])
                if Shape(node).get_shapes():
                    s.copy(node, world=True)
                else:
                    for shape in node.get_children():
                        _s = Shape(shape)
                        if _s.get_shapes():
                            s.copy(shape, world=True)
                s.rename()
                s.shadow()
                node = targets[0]

                for target in targets[1:]:
                    s = Shape(target)
                    if Shape(node).get_shapes():
                        s.copy(node, world=False)
                    s.rename()
                    s.shadow()

        # cloned shapes
        data = deepcopy(self.template_data.get('shapes', {}))
        for key in data:
            specs = data[key]

            if 'clone' in specs:
                src_ctrl = Nodes.get_id('{}{}::{}'.format(self.name, self.get_branch_id(), specs['clone']))
                dst_ctrl = Nodes.get_id('{}{}::{}'.format(self.name, self.get_branch_id(), key))
                if not src_ctrl or not dst_ctrl:
                    continue

                dst_shp = Shape(dst_ctrl)
                if dst_shp.get_shapes():
                    continue

                dst_shp.copy(src_ctrl)
                if 'size' in specs:
                    dst_shp.scale(specs['size'], center=True)
                if 'color' in specs:
                    dst_shp.set_color(specs['color'])

    def delete_shapes(self):
        current_asset = Nodes.current_asset
        Nodes.current_asset = Nodes.get_asset_id(self.node)
        shapes_tree = Nodes.shapes[Nodes.current_asset]

        for node in shapes_tree.get(f'{self.name}::*', [], as_list=True):
            node.remove_from_parent()

        Nodes.current_asset = current_asset

    def toggle_shapes_visibility(self):
        current_asset = Nodes.current_asset
        Nodes.current_asset = Nodes.get_asset_id(self.node)
        shapes_tree = Nodes.shapes[Nodes.current_asset]

        nodes = shapes_tree.get(f'{self.name}::*', [], as_list=True)
        n = len(nodes)
        self.add_shapes()
        nodes = shapes_tree.get(f'{self.name}::*', [], as_list=True)

        vis = True

        if n == len(nodes):

            for node in nodes:
                if not node.show.get_value():
                    break  # if one is hidden, show all
            else:
                vis = False

        for node in nodes:
            try:
                node.show.set_value(vis)
            except:
                pass

        Nodes.current_asset = current_asset

    # grouping ---------------------------------------------------------------------------------------------------------

    def build_groups(self):
        tpl_parent = self.get_parent()
        group = self.get_opt('group')
        self.branches = ['']

        # all group
        grp_all = Nodes.get_id('::group')
        if not grp_all:
            grp_all = Group.create('all')
            Nodes.set_id(grp_all.node, '::group')

            # connect group to default hook
            hook = self.get_hook()
            if not hook.get_dynamic_plug('gem_group'):
                add_plug(hook, 'gem_group', str)

            hook.gem_group.connect(grp_all.node.gem_group)
            grp_all.node.set_parent(hook)

        else:
            grp_all = Group(grp_all)

        # create root group
        for grp_id in (f'{self.name}::group', f'::groups.{self.name}'):
            grp_root = Nodes.get_id(grp_id)
            if grp_root:  # if root already exists (as root or main)
                grp_root = Group(grp_root)
        if not grp_root:
            grp_root = Group.create(self.name)

        if tpl_parent:
            grp_parent_node = Nodes.get_id(f'{tpl_parent.name}::group')
            if grp_parent_node:
                grp_parent = Group(grp_parent_node)
            else:
                raise RuntimeError(f'unable to find group parent {tpl_parent.name} for {self}!')
        else:
            grp_parent = grp_all

        # override parent group
        if group:
            _group = group if group != 'all' else ''
            for grp_id in (f'{_group}::group', f'::groups.{group}'):
                grp_group = Nodes.get_id(grp_id)
                if grp_group:
                    grp_group = Group(grp_group)
                    break

            else:  # new main group
                if group == self.name:
                    grp_group = grp_root
                else:
                    grp_group = Group.create(group)
                Nodes.set_id(grp_group.node, f'::groups.{group}')

                grp_group.add_parent(grp_parent)

            grp_parent = grp_group
            tpl_parent = Nodes.get_id(group)
            if tpl_parent:
                tpl_parent = Template(tpl_parent)

        # merge
        merge = self.get_opt('parent')
        if grp_root != grp_parent:
            if merge == 'parent':
                grp_root.add_parent(grp_parent)
            elif merge == 'merge up':
                grp_parent.merge(grp_root)
                grp_root = grp_parent
            elif merge == 'merge down':
                grp_parent.merge(grp_root)
                grp_root = grp_parent
                grp_root.node.gem_group.set_value(self.name)
                grp_root.node.rename(f'grp_{self.name}')

        # branch sub groups
        if tpl_parent:
            p_branches = tpl_parent.get_branch_ids()

        branch_ctrls = {}
        flip_axis = self.get_sym_axis()

        for self.branches, self.root in self.get_branches():
            if not Nodes.get_id(f'{self.name}::group'):
                self.set_id(grp_root.node, 'group')

            grp_root_branch = grp_root

            branch_id = self.get_branch_id()
            if branch_id:
                grp_root_branch = Group.create(self.name + self.get_branch_suffix(' '))

                if tpl_parent:
                    for p_branch in p_branches:
                        if not p_branch:
                            continue
                        if branch_id.startswith(p_branch):
                            grp_parent_branch = Nodes.get_id(f'{tpl_parent.name}{p_branch}::groups')
                            if grp_parent_branch:
                                grp_parent_branch = Group(grp_parent_branch)

                                # merge
                                if merge == 'parent':
                                    grp_root_branch.add_parent(grp_root)
                                    grp_root_branch.add_parent(grp_parent_branch)
                                elif merge == 'merge up':
                                    grp_parent_branch.merge(grp_root_branch)
                                    grp_root_branch = grp_parent_branch
                                elif merge == 'merge down':
                                    grp_parent_branch.merge(grp_root_branch)
                                    grp_root_branch = grp_parent_branch
                                    grp_root_branch.node.gem_group.set_value(self.name)
                                    grp_root_branch.node.rename(f'grp_{self.name}')

                if not grp_root_branch.get_parents():
                    grp_root_branch.add_parent(grp_root)
                if grp_root_branch != grp_root:
                    self.set_id(grp_root_branch.node, 'groups')

            # vis sub groups
            grp_vis = Nodes.get_id(f'{self.name}{self.get_branch_id()}::vis') or []
            if isinstance(grp_vis, kl.Node):
                grp_vis = [grp_vis]

            _grp = grp_root_branch
            _tpl = self
            while True:
                if not Nodes.get_id(f'{_tpl.name}::ctrls'):
                    _tpl = _tpl.get_parent()
                    if not isinstance(_tpl, Template):
                        _tpl = None
                        break
                else:
                    break
            if _tpl and _tpl != self:
                _grp = Nodes.get_id('{}{}::groups'.format(_tpl.name, self.get_branch_id()))
                if isinstance(_grp, list):
                    _grp = _grp[0]
                if not _grp:
                    _grp = Nodes.get_id(f'{_tpl.name}::group')
                if _grp and isinstance(_grp, kl.Node):
                    _grp = Group(_grp)

            for grp in grp_vis:
                grp = Group(grp)
                if _grp:
                    _grp.connect_showhide(grp)
                if grp.node.get_dynamic_plug('gem_vis'):
                    for vis_id in grp.node.gem_vis.get_value().split(';'):
                        if '::ctrls' not in vis_id:
                            continue
                        for vis_node in flatten_list([Nodes.get_id(vis_id)]):
                            if vis_node:
                                if not vis_node.get_plug('gem_type') or vis_node.gem_type.get_value() != Control.type_name:
                                    Control.create(vis_node)
                                Control(vis_node).connect_showhide(grp)

            # sub ctrl groups
            ctrl_tag = f'{self.name}{branch_id}::ctrls'
            nodes = Nodes.get_id(ctrl_tag)
            if not nodes:
                continue

            # build mirror tables
            # TODO: faire une vrai refacto pour ça, là c'est cracra (moins qu'avant mais quand même)
            sub_grps = {}
            for node in nodes:
                gem_id = Nodes.get_node_id(node, '::ctrls')
                tpl_id, sep, ctrl_key = gem_id.partition('::')
                tpl_id = tpl_id.split('.')
                branch_keys = tpl_id[1:]
                ctrl_key = '.'.join(ctrl_key.split('.')[1:])

                if '.' in ctrl_key:
                    # create subgroup
                    sub_grp_name = tpl_id[0] + '_' + ctrl_key.replace('.', '_') + self.get_branch_suffix()
                    sub_grp = sub_grps.get(sub_grp_name)
                    if not sub_grp:
                        sub_grp = Group.create(sub_grp_name)
                        sub_grp.add_parent(grp_root_branch)
                        sub_grps[sub_grp_name] = sub_grp
                    sub_grp.add_members(node)
                else:
                    grp_root_branch.add_member(node)

                ctrl_key = tpl_id[0] + '.' + ctrl_key
                if ctrl_key not in branch_ctrls:
                    branch_ctrls[ctrl_key] = {}

                if flip_axis == 'x':

                    for i, key in enumerate(branch_keys):
                        if key in ('L', 'R'):
                            common_key = branch_keys[:]
                            common_key[i] = '@'
                            common_key = '.'.join(common_key)
                            if common_key not in branch_ctrls[ctrl_key]:
                                branch_ctrls[ctrl_key][common_key] = {}
                            branch_ctrls[ctrl_key][common_key][key] = node
                            break

                    if 'L' not in branch_keys and 'R' not in branch_keys:
                        common_key = '.'.join(branch_keys)
                        branch_ctrls[ctrl_key][common_key] = {'x': node}

        # connect mirror controls
        for _, data in branch_ctrls.items():
            for _, ctrls in data.items():
                if 'L' in ctrls and 'R' in ctrls:
                    attr = f'mirror_{flip_axis}s'
                    add_plug(ctrls['L'], attr, str, default_value='+x')
                    add_plug(ctrls['R'], attr, str, default_value='-x')

                    for key, node in ctrls.items():
                        plug = add_plug(node, 'mirrors', str, array=True)
                        i = get_next_available(plug)
                        for _key, _node in ctrls.items():
                            if _key != key:
                                plug[i].connect(_node.get_dynamic_plug(attr))

                    Control.create_mirror_table(ctrls['L'], ctrls['R'])

                elif 'x' in ctrls:
                    Control.create_mirror_table(ctrls['x'], ctrls['x'], 'x')

        # vis groups
        grp_vis = Nodes.get_id(f'{self.name}::vis') or []
        if isinstance(grp_vis, kl.Node):
            grp_vis = [grp_vis]

    def build_virtual_dag_hook(self):
        data = self.template_data.get('hierarchy', {})
        data = deepcopy(data)
        opts = {}
        for opt in self.template_data.get('opts', {}):
            opts[opt] = self.get_opt(opt)

        for self.branches, self.root in self.get_branches():
            for key, specs in data.items():
                if not specs:
                    continue
                key_id = '{}{}::{}'.format(self.name, self.get_branch_id(), key)
                plug = 'gem_dag_{}'.format(key.split('.')[0])

                nodes = Nodes.get_id(key_id)
                if isinstance(nodes, kl.Node):
                    nodes = [nodes]
                if nodes is None:
                    continue

                # update specs from opts
                if 'opts' in specs:
                    for opt, opt_data in specs['opts'].items():
                        for _opt in opts:
                            opt = opt.replace(_opt, str(opts[_opt]))
                        if eval(opt):
                            specs.update(opt_data)

                # connect hook
                if 'hook' in specs:
                    hooks = []
                    if not isinstance(specs['hook'], list):
                        specs['hook'] = [specs['hook']]
                    for hook in specs['hook']:
                        if not isinstance(hook, str):
                            continue
                        _hooks = self.get_structure(hook)
                        if isinstance(_hooks, kl.Node):
                            hooks.append(_hooks)
                        else:
                            hooks += _hooks

                    if len(nodes) != len(hooks):
                        if len(hooks) > 1:
                            _nodes = []
                            f = len(nodes) / float(len(hooks) - 1)
                            for i in range(len(hooks)):
                                if len(nodes) > 1:
                                    i *= f
                                    if i >= len(nodes):
                                        i = len(nodes) - 1
                                else:
                                    i = 0
                                _nodes.append(nodes[int(i)])
                            nodes = _nodes
                        else:
                            nodes = nodes[:1]

                    for node, hook in zip(nodes, hooks):
                        if not hook.get_dynamic_plug(plug):
                            add_plug(hook, plug, str)
                        if not node.get_dynamic_plug(plug):
                            add_plug(node, plug, str)

                        hook_id = Nodes.get_node_id(node, find='hooks')
                        hook.get_dynamic_plug(plug).set_value(hook_id)
                        node.get_dynamic_plug(plug).connect(hook.get_dynamic_plug(plug))

    def build_virtual_dag(self):
        data = self.template_data.get('hierarchy', {})
        data = deepcopy(data)
        opts = {}
        for opt in self.template_data.get('opts', {}):
            opts[opt] = self.get_opt(opt)

        isolated = self.get_opt('isolate_skin')

        for self.branches, self.root in self.get_branches():
            for key, specs in data.items():
                if not specs:
                    continue

                _key = key
                if isolated and key.startswith('skin.'):
                    _key = key.replace('skin.', 'out.skin.')

                key_id = '{}{}::{}'.format(self.name, self.get_branch_id(), _key)
                plug = 'gem_dag_{}'.format(key.split('.')[0])

                nodes = Nodes.get_id(key_id)
                if isinstance(nodes, kl.Node):
                    nodes = [nodes]
                if nodes is None:
                    continue

                # update specs from opts
                if 'opts' in specs:
                    for opt, opt_data in specs['opts'].items():
                        for _opt in opts:
                            opt = opt.replace(_opt, str(opts[_opt]))
                        if eval(opt):
                            specs.update(opt_data)

                # connect
                if specs.get('root', False):
                    parent = self.get_hook(plug=plug)
                    for node in nodes:
                        _node = node
                        if isolated:
                            for _id in node.gem_id.get_value().split(';'):
                                if 'out.skin.' in _id:
                                    _node = Nodes.get_id(_id.replace('out.skin.', 'skin.'))
                                    break

                        virtual_parent = self.get_virtual_hook(node, plug=plug)
                        if virtual_parent and virtual_parent != _node:
                            parent = virtual_parent

                        parented = False
                        for o in _node.get_dynamic_plug('gem_id').get_outputs():
                            if o.get_node().get_name() == 'gem_dag_children':
                                parented = True
                                break
                        if parented:
                            continue

                        set_virtual_parent(_node, parent)

                if specs.get('parent'):
                    parents = specs['parent']
                    if not isinstance(parents, list):
                        parents = [parents]

                    for parent in parents:
                        parent_id = '{}{}::{}'.format(self.name, self.get_branch_id(), parent)

                        _parents = Nodes.get_id(parent_id)
                        if isinstance(_parents, kl.Node):
                            _parents = [_parents]
                        if _parents:
                            for node, _parent in zip(nodes, _parents):
                                set_virtual_parent(node, _parent)

                if specs.get('chain', False):
                    nodes = sorted(nodes, key=lambda node: node.get_full_name())
                    nodes = sorted(nodes, key=lambda node: len(node.get_full_name()))
                    for n in range(len(nodes) - 1):
                        set_virtual_parent(nodes[n + 1], nodes[n])
