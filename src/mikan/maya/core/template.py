# coding: utf-8

import yaml
import itertools
from copy import deepcopy
from six.moves import range
from six import string_types, iteritems

import maya.cmds as mc
from mikan.maya import cmdx as mx

from mikan.core import abstract
from mikan.core.utils import get_slice, re_is_int, re_get_keys, flatten_list
from mikan.core.utils.yamlutils import YamlLoader
from mikan.core.logger import create_logger, timed_code

from .node import Nodes
from .control import Group, Control
from .shape import Shape
from ..lib.configparser import ConfigParser
from ..lib.rig import axis_to_vector, mirror_joints, copy_transform, duplicate_joint, find_closest_node, set_virtual_parent
from ..lib.connect import connect_matrix, connect_reverse

__all__ = ['Template']

log = create_logger()


class Template(abstract.Template):
    """Main class for all components of different types of templates.

    Attributes:
        node (str, mx.Node): root node of the template hierarchy

    """
    software = 'maya'

    def __init__(self, node):
        # init template instance from the given node
        if not isinstance(node, mx.Node):
            node = mx.encode(str(node))
        self.node = node

        self.branches = ['']  # no branch by default
        self.root = self.node

        self.modes = set()

        if not self.node.is_referenced():
            try:
                self.node['useOutlinerColor'] = 1
                self.node['outlinerColor'] = (0.33, 0.73, 1)
            except:
                pass

    def __repr__(self):
        return 'Template(\'{}\')'.format(self.node)

    @classmethod
    def get_module_from_node(cls, node):
        """Returns template type string from given node.

        Arguments:
            node (str, mx.Node): template node

        """
        if not isinstance(node, mx.Node):
            node = mx.encode(str(node))
        if 'gem_module' not in node:
            raise RuntimeError('node "{}" is not valid'.format(node))
        return node['gem_module'].read()

    @property
    def name(self):
        """Returns the name id of the template.

        Returns:
            str: id name

        """
        for i in self.node['gem_id'].read().split(';'):
            if '::' not in i:
                return i

    @name.setter
    def name(self, name):
        """Updates id name of the template.

        Arguments:
            name (str): new name of the template id

        """
        old_name = self.name
        ids = []
        for i in self.node['gem_id'].read().split(';'):
            if i == old_name:
                ids.append(name)
            else:
                ids.append(i)
        with mx.DGModifier() as md:
            md.set_attr(self.node['gem_id'], ';'.join(ids))

    @staticmethod
    def create(tpl, parent=None, name=None, data=None, root=None, joint=True):
        """initializes node to create a proper template instance.

        Arguments:
            tpl (str): template type string
            parent (str, mx.Node, optional): parent node of the new template
            name (str, optional): id name
            data (dict, optional): custom options for template guides creation
            root (str, mx.Node, optional): convert the given node to a template instead of creating a new one
            joint (bool, optional): node type of the created root node

        Returns:
            Template: instance of the newly created template

        """
        # check if module exists
        cls = Template.get_class(tpl)

        # check if nodes exist
        build = True
        if root is not None:
            if not isinstance(root, mx.Node):
                root = mx.encode(str(root))
            build = False

            # check if already set
            if 'gem_type' in root:
                if root['gem_type'].read() == Template.type_name:
                    return Template(root)
                else:
                    raise RuntimeError('root is invalid (type is not template)')

        if parent is not None:
            if not isinstance(parent, mx.Node):
                parent = mx.encode(str(parent))

        if root and parent and root.parent() != parent:
            mc.parent(str(root), str(parent))

        # get name
        if name is None:
            name = cls.template_data['name']
        name = Template.cleanup_name(name)
        name = Template.get_next_unique_name(name, parent)

        # create root node
        joint = cls.template_data.get('guides', {}).get('joint', joint)

        if root is None:
            if joint:
                with mx.DagModifier() as md:
                    root = md.create_node(mx.tJoint, parent=parent)
                if parent and parent.is_a(mx.tJoint):
                    parent['scale'] >> root['inverseScale']
            else:
                with mx.DagModifier() as md:
                    root = md.create_node(mx.tTransform, parent=parent)
                    loc = md.create_node(mx.tLocator, parent=root)
                    loc['localScale'] = (0.1, 0.1, 0.1)

        # add attributes
        root.add_attr(mx.String('gem_type'))
        root['gem_type'] = Template.type_name
        root['gem_type'].lock()

        Nodes.set_id(root, name)

        root.add_attr(mx.String('gem_module'))
        root['gem_module'] = tpl

        # return instance from created node
        it = Template(root)
        data = it.get_guide_data(data)
        if build:
            it.build_template(data)
        it.rename_root()
        mc.select(str(it.node))

        # conform nodes name
        for node in it.get_template_nodes():
            name = node.name(namespace=False)
            if not node.is_a(mx.tJoint) and name.startswith('tpl_'):
                name = 'tpx_' + name[4:]
                node.rename(name)

        return it

    def remove(self):
        """Removes template node from scene and cache."""
        mx.delete(self.node)
        Nodes.rebuild()

    def rename(self, name):
        """Renames instance id with a unique name and updates all occurrences in asset template.

        Returns:
            str: new id (it is automatically incremented if the given name is already used)

        """
        log.debug('rename {} to {}'.format(self, name))
        old_name = self.name
        if name == old_name:
            return name

        paths = Nodes.get_asset_paths()
        Nodes.current_asset = Nodes.get_asset_id(self.node, paths=paths)

        valid = self.check_validity()

        # rename self
        name = Template.cleanup_name(name)
        name = Template.get_next_unique_name(name, self.node)
        self.name = name

        # rename branches/other ids
        if valid:
            nodes = mx.ls('*.gem_id', o=1, r=1)
            if len(Nodes.assets) < 2:
                _nodes = []
                for node in nodes:
                    _asset_id = Nodes.get_asset_id(node, paths=paths)
                    if _asset_id == Nodes.current_asset:
                        _nodes.append(node)
                nodes = _nodes
        else:
            nodes = [node for node in self.get_template_nodes() if 'gem_id' in node]

        for node in nodes:
            if not node.exists:
                continue
            Nodes.rename_plug_ids(node['gem_id'], old_name, name)
            if 'gem_hook' in node:
                Nodes.rename_plug_ids(node['gem_hook'], old_name, name)

        # rename shapes
        if valid:
            nodes = mx.ls('*.gem_shape', o=1, r=1)
            if len(Nodes.assets) < 2:
                _nodes = []
                for node in nodes:
                    _asset_id = Nodes.get_asset_id(node, paths=paths)
                    if _asset_id == Nodes.current_asset:
                        _nodes.append(node)
                nodes = _nodes
        else:
            nodes = [node for node in self.get_template_nodes() if 'gem_shape' in node]

        for node in nodes:
            _asset_id = Nodes.get_asset_id(node, paths=paths)
            if _asset_id != Nodes.current_asset:
                continue
            Nodes.rename_plug_ids(node['gem_shape'], old_name, name)

        Nodes.rebuild()

        # rename mod/deformer
        if valid:
            nodes = mx.ls('*.notes', o=1, r=1)
        else:
            nodes = self.get_template_nodes()
        _old_name = '{}#{}'.format(Nodes.current_asset, old_name)
        _name = '{}#{}'.format(Nodes.current_asset, name)

        for node in nodes:
            if len(Nodes.assets) < 2:
                Nodes.rename_cfg_ids(node, old_name, name)
                continue

            _asset_id = Nodes.get_asset_id(node, paths=paths)
            if _asset_id == Nodes.current_asset:
                Nodes.rename_cfg_ids(node, old_name, name)
            else:
                Nodes.rename_cfg_ids(node, _old_name, _name)

        # rename node
        self.rename_root()

        # regen
        Nodes.rebuild()

        return name

    def rename_root(self):
        if self.node.is_referenced():
            return
        prefix = 'tpl'
        if not self.node.is_a(mx.tJoint):
            prefix = 'tpx'

        with mx.DagModifier() as md:
            md.rename(self.node, '{}_{}'.format(prefix, self.name))
        self.rename_template()

    def build(self, modes=None):

        if modes is None:
            modes = set()
        self.modes = modes

        isolate = False
        if self.get_opt('isolate_skin'):
            isolate = True

        for self.branches, self.root in self.get_branches():
            msg = '-- build: {}'.format(repr(self))
            if len(self.branches) > 1 or self.branches[0] != '':
                msg += ' {}'.format(self.branches)
            log.debug(msg)

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
        if not isinstance(node, mx.Node):
            node = mx.encode(str(node))

        if not ('gem_type' in node and node['gem_type'].read() == Template.type_name) or 'gem_branch' in node:
            if 'gem_id' in node:
                tpl_id = node['gem_id'].read().split(';')[0].split('::')[0]
                tpl, _, branch_id = tpl_id.partition('.')
                _node = node
                node = Nodes.get_id(tpl)

                if isinstance(node, list):
                    asset = Nodes.get_asset_id(_node)
                    node = Nodes.get_id(tpl, asset=asset)

        if not node or not isinstance(node, mx.DagNode):
            return

        if 'gem_module' not in node:
            parent = node.parent()
            if parent:
                return Template.get_from_node(parent)
            else:
                return

        tpl = Template(node)
        if branch_id:
            tpl.branches = branch_id.split('.')
        return tpl

    def get_name_plug(self, name):
        attr = 'gem_name_{}'.format(name)
        if attr in self.node:
            return self.node[attr]

    def has_name_plug(self, name):
        attr = 'gem_name_{}'.format(name)
        return attr in self.node

    def get_name(self, name):
        data = self.template_data.get('names', {})

        if name not in data:
            raise RuntimeError('name {} not available in module "{}"'.format(name, self.node['gem_module'].read()))

        # check saved data
        attr = 'gem_name_{}'.format(name)
        if attr in self.node:
            return self.node[attr].read()

        return data[name]

    def set_name(self, name, v):
        data = self.template_data.get('names', {})

        if name not in data:
            raise RuntimeError('name {} not available in module "{}"'.format(name, self.node['gem_module'].read()))

        attr = 'gem_name_{}'.format(name)
        rm = False

        if v != data[name]:
            if attr not in self.node:
                self.node.add_attr(mx.String(attr))
            self.node[attr] = v
        else:
            rm = True

        if rm:
            try:
                if attr in self.node:
                    self.node[attr] = v
                    self.node.delete_attr(self.node[attr])
            except:
                pass
        return True

    def reset_name(self, name):
        attr = 'gem_name_{}'.format(name)

        if attr in self.node:
            try:
                dv = self.template_data['names'][name]
                self.node[attr] = dv
            except:
                pass

            try:
                self.node[attr].keyable = False
                self.node[attr].channel_box = False
                self.node.delete_attr(self.node[attr])
            except:
                pass

    def get_opt_plug(self, opt):
        attr = 'gem_opt_{}'.format(opt)
        if attr in self.node:
            return self.node[attr]

        data = self.template_data['opts']
        if 'legacy' in data[opt]:
            attr = 'gem_opt_{}'.format(data[opt]['legacy'])
            if attr in self.node:
                return self.node[attr]

    def has_opt_plug(self, opt):
        return self.get_opt_plug(opt) is not None

    def get_opt(self, opt, default=False):
        data = self.template_data['opts']

        if opt not in data:
            raise RuntimeError('option {} not available in module "{}"'.format(opt, self.node['gem_module'].read()))

        v = data[opt]['value']

        # check saved data
        plug = self.get_opt_plug(opt)
        if plug is not None and not default:
            v = plug.read()

        # yaml eval
        if data[opt].get('yaml') and v:
            v = yaml.load(v, YamlLoader)

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
            raise RuntimeError('"{}" option is not available in template "{}"'.format(opt, self.node['gem_module'].read()))

        # compare
        dv = data[opt]['value']

        # filter
        if data[opt].get('yaml'):
            if v != '':
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
        if plug is None:
            attr_name = 'gem_opt_{}'.format(opt)

            if v == dv:
                return False

            if enum:
                attr = mx.Enum(attr_name, default=dv, fields=enum)
            elif isinstance(v, bool):
                attr = mx.Boolean(attr_name, default=dv)
            elif isinstance(v, int):
                attr = mx.Long(attr_name, default=dv)
            elif isinstance(v, float):
                attr = mx.Double(attr_name, default=dv)
            elif isinstance(v, list) and len(v) == 3:
                attr = mx.Double3(attr_name, default=dv)
            elif isinstance(v, string_types):
                attr = mx.String(attr_name)
            else:
                raise ValueError('invalid option type')

            if 'min' in data[opt]:
                attr['min'] = data[opt]['min']
            if 'max' in data[opt]:
                attr['max'] = data[opt]['max']

            attr['keyable'] = True
            with mx.DagModifier() as md:
                md.add_attr(self.node, attr)
            plug = self.node[attr_name]

        if v == plug.read():
            return False

        with mx.DagModifier() as md:
            md.set_attr(plug, v)

    def reset_opt(self, opt):
        plug = self.get_opt_plug(opt)
        if plug is None:
            return

        try:
            data = self.template_data['opts']
            dv = data[opt]['value']
            with mx.DagModifier() as md:
                md.set_attr(plug, dv)
        except:
            pass

        try:
            plug.keyable = 0
            plug.channel_box = 0
            with mx.DagModifier() as md:
                md.delete_attr(plug)
        except:
            pass

    # navigation -------------------------------------------------------------------------------------------------------

    def check_validity(self, rebuild=False):
        asset_id = Nodes.current_asset
        if asset_id is None:
            asset_id = Nodes.get_asset_id(self.node)

        node = Nodes.get_id(self.name, asset=asset_id)
        check = node == self.node

        if rebuild and not check:
            Nodes.rebuild()
            node = Nodes.get_id(self.name, asset=asset_id)
            check = node == self.node

        if not check:
            log.warning('/!\\ {} is not valid! (duplicate ids)'.format(self))

        # TODO: check de validité avec les subnames?
        return check

    @staticmethod
    def get_all_template_nodes():
        tpls = []
        for node in mx.ls('*.gem_type', o=1, r=1):
            if node['gem_type'].read() == Template.type_name:
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

        for child in root.children():
            if 'gem_type' in child and child['gem_type'].read() == Template.type_name:
                children.append(Template(child))
            else:
                self.get_children(child, children)

        return children

    def get_parent(self, root=None):
        if root is None:
            root = self.node

        node = root.parent()
        if node:
            if 'gem_type' in node and node['gem_type'].read() == Template.type_name:
                return Template(node)
            else:
                return self.get_parent(root=node)

        return None

    def get_siblings(self):
        siblings = []

        parent = self.node.parent()
        if parent:
            nodes = parent.children()
        else:
            nodes = mx.ls('|*', r=1, type='transform')

        for node in nodes:
            if 'gem_type' in node and node['gem_type'].read() == Template.type_name:
                siblings.append(Template(node))

        return siblings

    # structures -------------------------------------------------------------------------------------------------------

    def get_template_nodes(self, root=None, nodes=None, hidden=True):
        if root is None:
            root = self.root
        if not isinstance(root, mx.Node):
            root = mx.encode(str(root))

        if nodes is None:
            nodes = [root]

        for child in root.children():
            if child.type_id not in (mx.tTransform, mx.tJoint):
                continue
            if not hidden and child.name(namespace=False).startswith('_'):
                continue
            if 'gem_type' in child and child['gem_type'].read() == Template.type_name:
                continue
            nodes.append(child)
            self.get_template_nodes(child, nodes, hidden=hidden)

        return nodes

    def get_template_chain(self, root=None, nodes=None):
        if root is None:
            root = self.root
        elif not isinstance(root, mx.Node):
            root = mx.encode(str(root))
        if nodes is None:
            nodes = [root]

        child = []
        for c in root.children():
            if c.type_id not in (mx.tTransform, mx.tJoint):
                # skip if not hierarchy
                continue
            if c.name(namespace=False).startswith('_'):
                # skip if node is ignored
                continue
            if 'gem_template' in c:
                # skip if node is tagged
                continue
            if 'gem_type' in c and c['gem_type'].read() == Template.type_name:
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
            raise RuntimeError(
                'structure {} not available in module "{}"'.format(name, self.node['gem_module'].read())
            )

        struct = data[name]

        # check saved data
        attr = 'gem_struct_{}'.format(name)
        if attr in self.node:
            struct = self.node[attr].read()

        mounts = []
        # get by tag
        if not struct:
            for node in self.get_template_nodes():
                if 'gem_template' in node and node['gem_template'].read() == name:
                    mounts = [node]
                    break

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

        if item is not None:
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
            raise RuntimeError(
                'structure {} not available in module "{}"'.format(struct, self.node['gem_module'].read()))

        attr = 'gem_struct_{}'.format(struct)
        rm = False

        if v != data[struct]:
            if attr not in self.node:
                self.node.add_attr(mx.String(attr))
            self.node[attr] = v
        else:
            rm = True

        if rm:
            try:
                if attr in self.node:
                    self.node[attr] = v
                    self.node.delete_attr(attr)
            except:
                pass
        return True

    def delete_template_branches(self):
        # cleanup branches
        roots = Nodes.get_id('{}::branch'.format(self.name), as_list=True)

        for root in itertools.chain([self.node], [n for n in roots if n]):
            for node in itertools.chain([root], root.descendents()):
                if not node.exists:
                    continue
                if 'gem_branch' in node:
                    node['gem_branch'] = ''
                if 'gem_type' in node and node['gem_type'].read() == 'branch':
                    mx.delete(node)

    def build_template_branches(self):

        current_asset = Nodes.current_asset
        Nodes.current_asset = Nodes.get_asset_id(self.node)

        # rebuild branched chains
        self.delete_template_branches()
        templates = [self] + self.get_all_children()

        root_keys = list(self.get_branches())[0][0][:-1]
        root_id = ('.{}' * len(root_keys)).format(*root_keys)

        def _set_branch(node, branch_id):
            attr = 'gem_branch'
            if attr not in node:
                node.add_attr(mx.String(attr))
                node[attr] = root_id
            f = node[attr].read()[len(root_id):]
            node[attr] = root_id + '.' + branch_id + f

        # tmp mirror edits
        tmp_edits = []
        for tpl in templates:
            edits = Nodes.get_id('{}::edit'.format(tpl.name))
            if not edits:
                continue

            edits = {}
            branch_keys = list(tpl.get_branches())

            for branch_ids, _root in branch_keys:
                branch_id = ''
                if branch_ids[0] or len(branch_ids) > 1:
                    branch_id = ('.{}' * len(branch_ids)).format(*branch_ids)
                edit = Nodes.get_id('{}{}::edit'.format(tpl.name, branch_id))
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
                for axis, pairs in iteritems(Template.branch_pairs):
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
                    if not node.exists:
                        continue
                    if node.type_id not in (mx.tTransform, mx.tJoint):
                        mx.delete(node)
                        continue
                    if 'gem_shape' in node:
                        mx.delete(node)
                        continue

                    if 'gem_id' in node:
                        gem_ids = [gem_id for gem_id in node['gem_id'].read().split(';') if gem_id]
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

                        node['gem_id'] = ''
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
                for axis, pairs in iteritems(Template.branch_pairs):
                    for pair in pairs:
                        if branch_id in pair:
                            if axis == 'x':
                                myz = 1
                            elif axis == 'y':
                                mxz = 1
                            elif axis == 'z':
                                mxy = 1
                branched_nodes = mirror_joints(tpl.node, mxy=mxy, myz=myz, mxz=mxz)
                branch_root = branched_nodes[0]
                _name = tpl.node.name()
                branch_root.rename('_{}__sfx__'.format(_name))
                branch_root['gem_type'].unlock()
                branch_root['gem_type'] = 'branch'
                branch_root['gem_type'].lock()
                _set_branch(branch_root, branch_id)
                roots.append(branch_root)

                for node in branched_nodes[1:]:
                    if not node.exists:
                        continue
                    if node.type_id not in (mx.tTransform, mx.tJoint):
                        mx.delete(node)
                        continue
                    if 'gem_shape' in node:
                        mx.delete(node)
                        continue

                    if 'gem_type' in node and node['gem_type'].read() == 'branch':
                        if node not in roots:
                            roots.append(node)

                    if 'gem_branch' in node or ('gem_type' in node and node['gem_type'].read() == Template.type_name):
                        _set_branch(node, branch_id)

                    if '__sfx__' not in str(node):
                        node.rename('{}__sfx__'.format(node.name()))

            if branch_ids[0]:
                _set_branch(tpl.node, branch_ids[0])
                for node in list(tpl.node.descendents())[::-1]:
                    if 'gem_type' in node and node['gem_type'].read() == 'branch':
                        _set_branch(node, branch_ids[0])
                        continue

                    if 'gem_branch' in node or ('gem_type' in node and node['gem_type'].read() == Template.type_name):
                        _set_branch(node, branch_ids[0])

        injected = set()
        for root in roots:
            branch_sfx = ''
            branch_ids = []

            for node in [root] + list(root.descendents()):
                if node in injected:
                    continue
                else:
                    injected.add(node)

                if not node.exists:
                    continue

                all_ids = set()
                branch_ids0 = []

                _tpl = Template.get_from_node(node)
                _branch_ids = _tpl.get_branch_ids() if _tpl else None
                if _branch_ids:
                    branch_ids0 = _branch_ids[0][1:].split('.')
                    for f in _branch_ids:
                        all_ids = all_ids.union(set(f.strip('.').split('.')))

                if 'gem_branch' in node:
                    branch_keys = node['gem_branch'].read()
                    branch_ids = branch_keys.strip('.').split('.')

                    tag = '{}{}::branch'.format(node['gem_id'].read(), branch_keys)
                    node['gem_id'] = ''
                    Nodes.set_id(node, tag)

                    branch_sfx = '_'.join(branch_ids)
                    if branch_sfx:
                        branch_sfx = '_' + branch_sfx

                    n = str(node).split(':')[-1].split('|')[-1]
                    if not n.startswith('_'):
                        node.rename('_' + n)

                if '__sfx__' in str(node):
                    node_split = str(node.name()).partition('__sfx__')
                    node.rename(node_split[0] + branch_sfx)

                for plug_name in mc.listAttr(str(node), ud=1) or []:
                    plug = node[plug_name]
                    if plug_name in ['gem_template', 'gem_scale']:
                        continue
                    if plug_name == 'gem_type' and plug.read() == 'branch':
                        continue
                    if plug_name.startswith('gem_var_'):
                        continue
                    if plug_name.startswith('gem_enable'):
                        continue

                    # update gem_id
                    if plug_name == 'gem_id':
                        gem_ids = [gem_id for gem_id in plug.read().split(';') if gem_id]
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
                                    mx.delete(node)
                                    skip_edit = True
                                    break

                        if skip_edit:
                            break

                        # update tree ids
                        node['gem_id'] = ''
                        for gem_id in gem_ids:
                            Nodes.set_id(node, gem_id)

                        if '::branch' in plug.read():
                            if 'gem_type' not in node:
                                node.add_attr(mx.String('gem_type'))
                                node['gem_type'] = 'branch'
                                node['gem_type'].lock()
                        if '::edit' in plug.read():
                            if 'gem_type' not in node:
                                node.add_attr(mx.String('gem_type'))
                                node['gem_type'] = 'edit'
                                node['gem_type'].lock()

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

                    plug.unlock()
                    node.delete_attr(plug)

        for tpl in templates[::-1]:
            if 'gem_branch' in tpl.node:
                tpl.node['gem_branch'] = ''
                try:
                    tpl.node.delete_attr('gem_branch')
                except:
                    pass

        # update from edit
        for tpl in templates:
            edits = Nodes.get_id('{}::edit'.format(tpl.name))
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
                            log.warning('/!\\ couldn\'t retarget branch edit "{}[{}]" of {}{}'.format(struct, i, tpl.name, tpl.get_branch_id()))

                    root['v'] = False

        # remove tmp edits
        if tmp_edits:
            mx.delete(tmp_edits)

        # update dict
        Nodes.rebuild()
        Nodes.current_asset = current_asset

        return roots

    @staticmethod
    def set_branch_edit(root):
        if not isinstance(root, mx.Node):
            root = mx.encode(str(root))
        if root.is_referenced():
            log.warning('/!\\ cannot edit referenced template branch branch')
            return

        if 'gem_id' in root:
            gem_id = root['gem_id'].read()
            root['gem_id'] = gem_id.replace('::branch', '::edit')

        if 'gem_type' in root:
            if root['gem_type'].read() == 'branch':
                root['gem_type'].unlock()
                root['gem_type'] = 'edit'
                root['gem_type'].lock()

        for attr in ('gem_hook', 'notes'):
            if attr in root:
                root[attr].unlock()
                root.delete_attr(root[attr])

        if root.name().startswith('_') and 'gem_type' not in root:
            mx.delete(root)
        else:
            for node in root.children():
                Template.set_branch_edit(node)

    # tag system -------------------------------------------------------------------------------------------------------

    def set_template_id(self, node, tag):
        if not isinstance(node, mx.Node):
            node = mx.encode(str(node))
        if 'gem_template' not in node:
            node.add_attr(mx.String('gem_template'))
        ids = node['gem_template'].read()
        if not ids:
            ids = [tag]
        else:
            ids = ids.split(';')
            if tag not in ids:
                ids.append(tag)
        node['gem_template'] = ';'.join(ids)

    def set_id(self, node, tag, template=True):
        if template:
            name = self.name
            branch_id = self.get_branch_id()
            if branch_id:
                name += branch_id
            tag = '{}::{}'.format(name, tag)
        else:
            tag = '::{}'.format(tag)

        Nodes.set_id(node, tag)
        return tag

    # hooks
    def set_hook(self, node, hook, tag, plug=None):
        if not isinstance(node, mx.Node):
            node = mx.encode(str(node))
        if not isinstance(hook, mx.Node):
            hook = mx.encode(str(hook))
        if plug is None:
            plug = 'gem_hook'

        tag = self.set_id(hook, tag)
        if plug not in node:
            node.add_attr(mx.String(plug))
        if plug not in hook:
            hook.add_attr(mx.String(plug))
        node[plug] = tag
        node[plug] >> hook[plug]

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

        if virtual_parent and isinstance(virtual_parent, mx.Node):

            # find from template
            if 'gem_type' in virtual_parent and virtual_parent['gem_type'] == Template.type_name:
                tpl_parent = Template(virtual_parent)
                tpl_nodes = []
                for _branch, _root in tpl_parent.get_branches():
                    tpl_parent.root = _root
                    _nodes = tpl_parent.get_template_nodes(hidden=False)
                    tpl_nodes += _nodes
                    if self.branches == _branch:
                        tpl_nodes = _nodes
                        break
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
            parent = parent.parent()
            if not parent:
                break
            if 'gem_id' not in parent:
                continue
            key = parent['gem_id'].read()
            if key.startswith(name + '.') or key.startswith(name + '::'):
                top = parent
            else:
                break

        # check transform input
        inputs = set()
        for dim in ('', 'x', 'y', 'z'):
            n = top['t' + dim].input()
            if n:
                inputs.add(n)

        drivers = []
        for input in inputs:
            for driver in mc.ls(mc.listHistory(str(input)), type='transform'):
                driver = mx.encode(driver)
                if driver.is_a(mx.kConstraint):
                    continue
                if driver not in drivers:
                    drivers.append(driver)

        drivers.append(top.parent())  # check reparent

        for driver in drivers:
            if driver.is_a(mx.kConstraint):
                continue
            if 'gem_id' in driver:
                keys = driver['gem_id'].read()
                if keys.startswith(name + '.') or keys.startswith(name + '::'):
                    continue

                hook = self.get_template_hook(driver)
                if hook:
                    return self.get_hook(hook, plug=plug, virtual=True)

    def get_template_hook(self, node):
        while True:
            attrs = []
            if 'gem_hook' in node:
                attrs.append('gem_hook')
            _attrs = mc.listAttr(str(node), ud=1) or []
            attrs += [attr for attr in _attrs if attr.startswith('gem_dag_')]

            for attr in attrs:
                _input = node[attr].input()
                if _input:
                    return _input

            node = node.parent()
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

        if not node.is_a(mx.kTransform):
            raise ValueError('"{}" cannot have a hook'.format(node))

        if virtual:
            parent = node
        else:
            parent = node.parent()

        if parent:
            if plug in parent:
                if tag:
                    return str(parent[plug].read())
                try:
                    hook = Nodes.get_id(parent[plug].read())
                    if not hook:
                        raise KeyError()
                    if hook.is_a(mx.kShape):
                        return hook.parent()
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
            with mx.DagModifier() as md:
                node = md.create_node(mx.tTransform, parent=hook, name='rig')
            Nodes.set_id(node, '::rig')
        return node

    def get_bind_hook(self):
        node = Nodes.get_id('::bind')
        if not node:
            hook = self.get_first_hook()
            with mx.DagModifier() as md:
                node = md.create_node(mx.tTransform, parent=hook, name='bind')
            Nodes.set_id(node, '::bind')
        return node

    def build_isolate_skin(self):
        parent = self.get_bind_hook()

        for sk in Nodes.get_id('{}{}::skin'.format(self.name, self.get_branch_id()), as_list=True):
            name = sk.name(namespace=False)
            name = '_'.join(name.split('_')[1:])
            sk.rename('j_' + name)

            j = duplicate_joint(sk, p=parent, n='sk_' + name)

            # transfer ids
            ids = sk['gem_id'].read().split(';')
            new_ids = []
            replaced_ids = []
            for tag in ids:
                if '::skin.' in tag:
                    Nodes.set_id(j, tag)
                    replaced_ids.append(tag.replace('::skin.', '::out.skin.'))
                else:
                    new_ids.append(tag)

            sk['gem_id'] = ';'.join(new_ids)
            for _id in replaced_ids:
                Nodes.set_id(sk, _id)

            # hook joint
            blend = mx.create_node(mx.tWtAddMatrix, name='_bmx#')
            sk['wm'][0] >> blend['i'][0]['m']

            j.add_attr(mx.Matrix('custom_transform'))
            j['custom_transform'] = sk['wm'][0]
            j['custom_transform'] >> blend['i'][1]['m']

            j.add_attr(mx.Double('blend_transform', min=0, max=1, keyable=True))
            j['blend_transform'] >> blend['i'][1]['w']
            connect_reverse(j['blend_transform'], blend['i'][0]['w'])

            connect_matrix(blend['o'], j, pim=True)

    @classmethod
    def build_isolate_skeleton(cls):
        root = Nodes.get_id('::bind')
        if not root:
            return

        joints = list(root.children())
        _joints = set(joints)

        for j in joints:
            if 'gem_dag_children' in j:
                ch_plug = j['gem_dag_children']
                for i in ch_plug.array_indices:
                    ch = j['gem_dag_children'][i].input()
                    if ch in _joints and ch != j:
                        mc.parent(str(ch), str(j))
                        if ch.is_a(mx.tJoint):
                            ch['jo'] = (0, 0, 0)

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
                        for k, _data in iteritems(new_specs):
                            if isinstance(_data, string_types):
                                new_specs[k] = _data.replace('*', str(i))
                            elif isinstance(_data, list):
                                for _i in range(len(_data)):
                                    if isinstance(_data[_i], string_types):
                                        _data[_i] = _data[_i].replace('*', str(i))
                            elif isinstance(_data, dict):
                                for _k in _data:
                                    if isinstance(_data[_k], string_types):
                                        _data[_k] = _data[_k].replace('*', str(i))
                        data[new_key] = new_specs
                    del data[key]

            # spawn shape roots
            for key, specs in iteritems(data):
                _branch_id = self.get_branch_id()
                key_id0 = '{}::{}'.format(self.name, key)
                key_id = '{}{}::{}'.format(self.name, _branch_id, key)

                # skip only if no shapes
                shapes = []
                root = shapes_tree.get(key_id)

                if _branch_id == branch_ids[0] and not root:
                    root = shapes_tree.get(key_id0)

                if root:
                    for node in root.children(type=mx.tTransform):
                        if list(node.shapes()):
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
                    with mx.DagModifier() as md:
                        root = md.create_node(mx.tTransform, parent=p[0], name='_shape_{}_{}{}'.format(self.name, key_name, self.get_branch_suffix()))
                    do_new = True
                do_flip = self.do_flip()

                # register
                if 'gem_shape' not in root:
                    with mx.DagModifier() as md:
                        md.add_attr(root, mx.String('gem_shape'))
                root['gem_shape'] = key_id

                shapes_tree[key_id] = root

                # copy relative
                if 'reference' in specs:
                    if 'gem_shape_reference' not in root:
                        with mx.DagModifier() as md:
                            md.add_attr(root, mx.String('gem_shape_reference'))

                    _key_id = '{}{}::{}'.format(self.name, _branch_id, specs['reference'])
                    root['gem_shape_reference'] = _key_id

                # if branch: copy from main shape
                if do_new and self.root != self.node:
                    _branch_id = self.get_branch_id().split('.')

                    for _axis, _pairs in iteritems(Template.branch_pairs):
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
                        if main_root and main_root.child():
                            break

                    # if no main root this is not normal
                    if main_root:
                        # copy transform
                        root['t'] = main_root['t']
                        root['r'] = main_root['r']
                        root['s'] = [abs(_s) for _s in main_root['s']]

                        # copy shapes
                        for node in main_root.children(mx.tTransform):
                            if list(node.shapes()):
                                ds = mx.encode(mc.duplicate(str(node), rr=1, rc=1)[0])
                                mc.parent(str(ds), str(root), r=1)
                                s = Shape(ds)

                                for shp in s.get_shapes():
                                    if 'gem_color' in shp:
                                        rgb = Shape.color_to_rgb(shp['gem_color'].read())
                                        if Shape.is_shape_color_flip(shp):
                                            rgb = Shape.get_color_flip(rgb)
                                        if do_flip:
                                            rgb = Shape.get_color_flip(rgb)
                                            Shape.set_shape_color_flip(shp)
                                        shp['gem_color'] = Shape.rgb_to_hex(rgb)
                                        s.restore_color(force=True)
                                shapes.append(ds)

                # new shape
                if do_new and not shapes and 'shape' in specs:
                    s = Shape.create(specs['shape'], axis=specs.get('axis'))
                    mc.parent(str(s.node), str(root), r=1)

                    n = root.name(namespace=False).replace('_shape_', 'shp_')
                    mc.rename(str(s.node), n)

                    if 'size' in specs:
                        s.scale(specs['size'], absolute=True)

                    if 'color' in specs:
                        color = specs['color']
                        s.set_color(color)

                # update constraints
                for attr in 'srt':
                    root[attr].read()
                with mx.DagModifier() as md:
                    for _o, _i in root.inputs(type=mx.kConstraint, plugs=1, connections=1):
                        md.disconnect(_o, _i)
                for _ch in list(root.children()):
                    if not _ch.is_a(mx.kConstraint):
                        continue
                    try:
                        mc.hide(str(_ch))
                        if not _ch.is_referenced():
                            mx.delete(_ch)
                    except:
                        pass

                # preserve shapes from old root transformation
                if not do_new:
                    _shapes = {}
                    for _shp in root.children(type=mx.tTransform):
                        _shapes[_shp] = _shp['wm'][0].as_matrix()

                with mx.DagModifier() as md:
                    for attr in 'tr':
                        try:
                            md.set_attr(root[attr], (0, 0, 0))
                        except:
                            pass
                    try:
                        md.set_attr(root['s'], (1, 1, 1))
                    except:
                        pass

                # rig root
                if 'point' in specs:
                    point = specs['point']
                    if isinstance(point, list):
                        point = []
                        for _p in specs['point']:
                            point.append(self.get_structure(_p))
                        point = list(flatten_list(point))
                    else:
                        point = self.get_structure(_p)
                    mx.cmd(mc.pointConstraint, point, root)
                else:
                    mx.cmd(mc.pointConstraint, p, root)

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
                    aim_args['aim'] = mx.Vector(0, 1, 0)
                    aim_args['u'] = mx.Vector(0, 0, 0)
                    aim_args['wut'] = 'none'

                    if 'up' in specs:
                        up = specs['up']
                        up_world = axis_to_vector(up)
                        if up_world:
                            aim_args['wu'] = up_world
                            aim_args['wut'] = 'scene'
                        else:
                            up = self.get_structure(up) or None
                            if up:
                                aim_args['wuo'] = up[0]
                                aim_args['wut'] = 'object'

                    if 'aim_axis' in specs:
                        aim_args['aim'] = axis_to_vector(specs['aim_axis'])
                    if do_flip:
                        aim_args['aim'] *= -1
                    if 'up_axis' in specs:
                        aim_args['u'] = axis_to_vector(specs['up_axis'])
                        if do_flip:
                            aim_args['u'] *= -1

                    if aim:
                        mx.cmd(mc.aimConstraint, aim, root, **aim_args)
                    elif aim_world:
                        with mx.DagModifier() as md:
                            ax = md.create_node(mx.tAimConstraint, parent=root)
                            px = md.create_node(mx.tPointConstraint, parent=root)
                        with mx.DagModifier() as md:
                            md.set_attr(px['offset'], aim_world)

                            md.connect(p[0]['t'], px['tg'][0]['tt'])
                            md.connect(p[0]['pm'][0], px['tg'][0]['tpm'])

                            md.set_attr(px['tg'][0]['tw'], 1)

                            md.connect(px['ct'], ax['tg'][0]['tt'])
                            md.set_attr(ax['tg'][0]['tw'], 1)

                            md.connect(root['pim'][0], ax['cpim'])
                            md.connect(ax['crx'], root['rx'])
                            md.connect(ax['cry'], root['ry'])
                            md.connect(ax['crz'], root['rz'])
                            md.set_attr(ax['aimVector'], aim_args['aim'])
                            md.set_attr(ax['upVector'], aim_args['u'])

                            if 'wuo' in aim_args:
                                md.connect(aim_args['wuo']['wm'][0], ax['wum'])
                                md.set_attr(ax['wut'], 1)
                            if 'wu' in aim_args:
                                md.set_attr(ax['worldUpVector'], aim_args['wu'])
                                md.set_attr(ax['wut'], 3)

                # restore shapes from old root transformation
                if not do_new:
                    for _shp, _wm in iteritems(_shapes):
                        try:
                            m = _wm * root['wim'][0].as_matrix()
                            mc.xform(str(_shp), m=m)
                        except:
                            pass

                # flip new shape
                if do_flip and do_new:
                    root['s'] = mx.Vector(root['s']) * -1

                # hide constraints
                for _cnst in root.children():
                    if _cnst.is_a(mx.kConstraint):
                        _cnst['hio'] = 1

        # exit
        self.branches = _branches
        self.root = _root
        Nodes.current_asset = current_asset

    def build_shapes(self):
        shapes_tree = Nodes.shapes[Nodes.current_asset]

        # copy shapes
        for node in shapes_tree.get('{}{}::*'.format(self.name, self.get_branch_id()), [], as_list=True):
            key = node['gem_shape'].read()
            targets = Nodes.get_id(key)  # get target controller

            targets_ref = None
            if 'gem_shape_reference' in node:
                key = node['gem_shape_reference'].read()
                targets_ref = Nodes.get_id(key)

                if targets_ref:
                    targets, targets_ref = targets_ref, targets

            # copy shape to controller
            if isinstance(targets, mx.DagNode):
                s = Shape(targets)
                if node.shape(type=mx.tNurbsCurve):
                    s.copy(node, world=True)
                else:
                    for child in node.children():
                        if child.shape(type=mx.tNurbsCurve):
                            s.copy(child, world=True)
                s.rename()
                s.shadow()

                if targets_ref:
                    if not isinstance(targets_ref, list):
                        s.move(targets_ref)
                    else:
                        for t in targets_ref:
                            Shape(t).copy(targets)
                        s.remove()

            # legacy copy shape to multiple controllers
            elif isinstance(targets, list):
                s = Shape(targets[0])
                if node.shape(type=mx.tNurbsCurve):
                    s.copy(node, world=True)
                else:
                    for child in node.children():
                        if child.shape(type=mx.tNurbsCurve):
                            s.copy(child, world=True)
                s.rename()
                s.shadow()
                node = targets[0]

                for target in targets[1:]:
                    s = Shape(target)
                    if node.shape():
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

        skipped_nodes = []
        for node in shapes_tree.get('{}::*'.format(self.name), [], as_list=True):
            try:
                mx.delete(node)
            except:
                skipped_nodes.append(node)

        Nodes.current_asset = current_asset
        return skipped_nodes

    def toggle_shapes_visibility(self):
        current_asset = Nodes.current_asset
        Nodes.current_asset = Nodes.get_asset_id(self.node)
        shapes_tree = Nodes.shapes[Nodes.current_asset]

        nodes = shapes_tree.get('{}::*'.format(self.name), [], as_list=True)
        n = len(nodes)
        self.add_shapes()
        nodes = shapes_tree.get('{}::*'.format(self.name), [], as_list=True)

        vis = True

        if n == len(nodes):

            for node in nodes:
                if not node['v'].read():
                    break  # if one is hidden, show all
            else:
                vis = False

        for node in nodes:
            try:
                node['v'] = vis
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
            if 'gem_group' not in hook:
                hook.add_attr(mx.String('gem_group'))

            grp_all.node['gem_group'] >> hook['gem_group']

        else:
            grp_all = Group(grp_all)

        # create root group
        for grp_id in ('{}::group'.format(self.name), '::groups.{}'.format(self.name)):
            grp_root = Nodes.get_id(grp_id)
            if grp_root:  # if root already exists (as root or main)
                grp_root = Group(grp_root)
        if not grp_root:
            grp_root = Group.create(self.name)

        if tpl_parent:
            grp_parent_node = Nodes.get_id('{}::group'.format(tpl_parent.name))
            if grp_parent_node:
                grp_parent = Group(grp_parent_node)
            else:
                raise RuntimeError('unable to find group parent {} for {}!'.format(tpl_parent.name, self))
        else:
            grp_parent = grp_all

        # override parent group?
        if group:
            _group = group if group != 'all' else ''
            for grp_id in ('{}::group'.format(_group), '::groups.{}'.format(group)):
                grp_group = Nodes.get_id(grp_id)
                if grp_group:
                    grp_group = Group(grp_group)
                    break

            else:  # new main group
                if group == self.name:
                    grp_group = grp_root
                else:
                    grp_group = Group.create(group)
                Nodes.set_id(grp_group.node, '::groups.{}'.format(group))

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
                grp_root.node['gem_group'] = self.name
                grp_root.node.rename('grp_{}'.format(self.name))

        # branch sub groups
        if tpl_parent:
            p_branches = tpl_parent.get_branch_ids()

        branch_ctrls = {}
        flip_axis = self.get_sym_axis()

        for self.branches, self.root in self.get_branches():
            if not Nodes.get_id('{}::group'.format(self.name)):
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
                            grp_parent_branch = Nodes.get_id('{}{}::groups'.format(tpl_parent.name, p_branch))
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
                                    grp_root_branch.node['gem_group'] = self.name
                                    grp_root_branch.node.rename('grp_{}'.format(self.name))

                if not list(grp_root_branch.get_parents()):
                    grp_root_branch.add_parent(grp_root)
                if grp_root_branch != grp_root:
                    self.set_id(grp_root_branch.node, 'groups')

            # vis sub groups
            grp_vis = Nodes.get_id('{}{}::vis'.format(self.name, self.get_branch_id())) or []
            if isinstance(grp_vis, mx.Node):
                grp_vis = [grp_vis]

            _grp = grp_root_branch
            _tpl = self
            while True:
                if not Nodes.get_id('{}::ctrls'.format(_tpl.name)):
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
                    _grp = Nodes.get_id('{}::group'.format(_tpl.name))
                if _grp and isinstance(_grp, mx.Node):
                    _grp = Group(_grp)

            for grp in grp_vis:
                grp = Group(grp)
                grp_node = grp.node
                if _grp:
                    _grp.connect_showhide(grp)
                if 'gem_vis' in grp_node:
                    for vis_id in grp_node['gem_vis'].read().split(';'):
                        if '::ctrls' not in vis_id:
                            continue
                        for vis_node in flatten_list([Nodes.get_id(vis_id)]):
                            if vis_node:
                                if 'gem_type' not in vis_node or vis_node['gem_type'].read() != Control.type_name:
                                    Control.create(vis_node)
                                Control(vis_node).connect_showhide(grp)

            # sub ctrl groups
            ctrl_tag = '{}{}::ctrls'.format(self.name, branch_id)
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
        for _, data in iteritems(branch_ctrls):
            for _, ctrls in iteritems(data):
                if 'L' in ctrls and 'R' in ctrls:
                    attr = 'mirror_xs'
                    ctrls['L'].add_attr(mx.String(attr))
                    ctrls['R'].add_attr(mx.String(attr))
                    ctrls['L'][attr] = '+x'
                    ctrls['R'][attr] = '-x'

                    for key, node in iteritems(ctrls):
                        node.add_attr(mx.String('mirrors', array=True, indexMatters=True))
                        m = 0
                        for _key, _node in iteritems(ctrls):
                            if _key != key:
                                _node[attr] >> node['mirrors'][m]
                                m += 1

                    Control.create_mirror_table(ctrls['L'], ctrls['R'])

                elif 'x' in ctrls:
                    Control.create_mirror_table(ctrls['x'], ctrls['x'], 'x')

    def build_virtual_dag_hook(self):
        data = self.template_data.get('hierarchy', {})
        data = deepcopy(data)
        opts = {}
        for opt in self.template_data.get('opts', {}):
            opts[opt] = self.get_opt(opt)

        for self.branches, self.root in self.get_branches():
            for key, specs in iteritems(data):
                if not specs:
                    continue
                key_id = '{}{}::{}'.format(self.name, self.get_branch_id(), key)
                plug = 'gem_dag_{}'.format(key.split('.')[0])

                nodes = Nodes.get_id(key_id)
                if isinstance(nodes, mx.Node):
                    nodes = [nodes]
                if nodes is None:
                    continue

                # update specs from opts
                if 'opts' in specs:
                    for opt, opt_data in iteritems(specs['opts']):
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
                        if not isinstance(hook, string_types):
                            continue
                        _hooks = self.get_structure(hook)
                        if isinstance(_hooks, mx.Node):
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
                        if plug not in hook:
                            hook.add_attr(mx.String(plug))
                        if plug not in node:
                            node.add_attr(mx.String(plug))

                        hook_id = Nodes.get_node_id(node, find='hooks')
                        hook[plug] = hook_id
                        hook[plug] >> node[plug]

    def build_virtual_dag(self):
        data = self.template_data.get('hierarchy', {})
        data = deepcopy(data)
        opts = {}
        for opt in self.template_data.get('opts', {}):
            opts[opt] = self.get_opt(opt)

        isolated = self.get_opt('isolate_skin')

        for self.branches, self.root in self.get_branches():
            for key, specs in iteritems(data):
                if not specs:
                    continue

                key_id = '{}{}::{}'.format(self.name, self.get_branch_id(), key)
                plug = 'gem_dag_{}'.format(key.split('.')[0])

                nodes = Nodes.get_id(key_id)
                if isinstance(nodes, mx.Node):
                    nodes = [nodes]
                if nodes is None:
                    continue

                # update specs from opts
                if 'opts' in specs:
                    for opt, opt_data in iteritems(specs['opts']):
                        for _opt in opts:
                            opt = opt.replace(_opt, str(opts[_opt]))
                        if eval(opt):
                            specs.update(opt_data)

                # connect
                if specs.get('root', False):
                    parent = self.get_hook(plug=plug)
                    for node in nodes:

                        virtual_parent = self.get_virtual_hook(node, plug=plug)
                        if virtual_parent and virtual_parent != node:
                            parent = virtual_parent

                        parented = False
                        for o in node['gem_id'].outputs(plugs=True):
                            if o.name() == 'gem_dag_children':
                                parented = True
                                break
                        if parented:
                            continue

                        set_virtual_parent(node, parent)

                if specs.get('parent'):
                    parents = specs['parent']
                    if not isinstance(parents, list):
                        parents = [parents]

                    for parent in parents:
                        parent_id = '{}{}::{}'.format(self.name, self.get_branch_id(), parent)

                        _parents = Nodes.get_id(parent_id)
                        if isinstance(_parents, mx.Node):
                            _parents = [_parents]
                        if _parents:
                            for node, _parent in zip(nodes, _parents):
                                set_virtual_parent(node, _parent)

                if specs.get('chain', False):
                    nodes = sorted(nodes, key=lambda node: node.path())
                    nodes = sorted(nodes, key=lambda node: len(node.path()))
                    for n in range(len(nodes) - 1):
                        set_virtual_parent(nodes[n + 1], nodes[n])
