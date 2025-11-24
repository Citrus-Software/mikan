# coding: utf-8

from math import copysign
from six.moves import range
from functools import partial

import maya.cmds as mc
from mikan.maya import cmdx as mx

from .node import Nodes
from mikan.core.utils import ordered_dict
from mikan.core.logger import create_logger

__all__ = [
    'Group', 'Control',
    'set_bind_pose', 'get_bind_pose'
]

log = create_logger()


class Group(object):
    type_name = 'group'

    def __new__(cls, node):
        if not isinstance(node, mx.Node):
            node = mx.encode(str(node))
        if 'gem_type' not in node:
            raise RuntimeError('node "{}" is not valid'.format(node))
        if node['gem_type'] == Group.type_name:
            return super(Group, cls).__new__(cls)
        else:
            log.warning('/!\\ Control invalid cast for "{}" ')

    def __init__(self, node):
        if not isinstance(node, mx.Node):
            node = mx.encode(str(node))
        self.node = node

    def __str__(self):
        return str(self.node)

    def __repr__(self):
        return 'Group(\'{}\')'.format(self.node)

    def __eq__(self, other):
        if isinstance(other, Group):
            return self.node == other.node
        return False

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return self.node.__hash__() ^ hash(Group)

    @staticmethod
    def create(name):
        node_name = 'grp_{}'.format(name)
        with mx.DGModifier() as md:
            node = md.create_node(mx.tNetwork, name=node_name)

        node.add_attr(mx.String('gem_type'))
        node['gem_type'] = Group.type_name
        node['gem_type'].lock()

        node.add_attr(mx.String('gem_group'))
        node['gem_group'] = name

        node.add_attr(mx.Message('members', array=True))
        node.add_attr(mx.String('parents', array=True, indexMatters=False))
        node.add_attr(mx.String('children', array=True, indexMatters=False))

        return Group(node)

    @property
    def name(self):
        return self.node['gem_group'].read()

    @property
    def nice_name(self):
        return self.name.title().replace('_', ' ')

    def get_name(self):
        return self.name

    def add_parent(self, grp):
        if self == grp:
            raise RuntimeError('cannot parent group to itself')

        if not isinstance(grp, Group):
            raise RuntimeError('{} is not a Group'.format(grp))

        if grp not in self.get_parents():
            self.node['parents'].append(grp.node['gem_group'])
        if self not in grp.get_children():
            grp.node['children'].append(self.node['gem_group'])

    def get_parents(self):
        for i in self.node['parents'].array_indices:
            node = self.node['parents'][i].input(type=mx.tNetwork)
            if node:
                yield Group(node)

    def get_all_parents(self, parents=None):
        if parents is None:
            parents = []

        _parents = list(self.get_parents())
        parents.extend(_parents)
        for parent in _parents:
            parent.get_all_parents(parents)

        return parents

    def get_first_parent(self):
        parents = self.get_all_parents()
        if parents:
            return parents[-1]

    def remove_parent(self, grp):
        for i in self.node['parents'].array_indices:
            plug_out = self.node['parents'][i].input(plug=True)
            if isinstance(plug_out, mx.Plug) and plug_out.node() == grp.node:
                self.node['parents'][i].disconnect()

        for i in grp.node['children'].array_indices:
            plug_out = self.node['children'][i].input(plug=True)
            if isinstance(plug_out, mx.Plug) and plug_out.node() == self.node:
                self.node['children'][i].disconnect()

    def remove_parents(self):
        for grp in self.get_parents():
            self.remove_parent(grp)

    orphan = remove_parents

    def add_child(self, grp):
        if self == grp:
            raise RuntimeError('cannot parent group to itself')

        if not isinstance(grp, Group):
            raise RuntimeError('{} is not a Group'.format(grp))

        if self not in grp.get_parents():
            grp.node['parents'].append(self.node['gem_group'])
        if grp not in self.get_children():
            self.node['children'].append(grp.node['gem_group'])

    def get_children(self):
        for i in self.node['children'].array_indices:
            node = self.node['children'][i].input(type=mx.tNetwork)
            if node:
                yield Group(node)

    def get_all_children(self, children=None):
        if children is None:
            children = []

        _children = list(self.get_children())
        children.extend(_children)
        for child in _children:
            child.get_all_children(children)

        return children

    def remove_child(self, grp):
        for i in self.node['children'].array_indices:
            plug_out = self.node['children'][i].input(plug=True)
            if isinstance(plug_out, mx.Plug) and plug_out.node() == grp.node:
                self.node['children'][i].disconnect()

        for i in grp.node['parents'].array_indices:
            plug_out = self.node['parents'][i].input(plug=True)
            if isinstance(plug_out, mx.Plug) and plug_out.node() == self.node:
                self.node['parents'][i].disconnect()

    def remove_children(self):
        for grp in self.get_children():
            self.remove_child(grp)

    def merge(self, grp):
        tags = []
        if 'gem_id' in grp.node:
            tags = grp.node['gem_id'].read().split(';')
        members = list(grp.get_nodes())
        children = list(grp.get_children())
        for child in children:
            grp.remove_child(child)
        parents = list(grp.get_parents())
        for parent in parents:
            grp.remove_parent(parent)

        mx.delete(grp.node)

        for tag in tags:
            Nodes.set_id(self.node, tag)
        for member in members:
            self.add_member(member)
        for child in children:
            if child != self:
                self.add_child(child)
        for parent in parents:
            if parent != self:
                self.add_parent(parent)

    def add_member(self, node):
        ctrl = node
        if not isinstance(ctrl, Control):
            ctrl = Control.create(ctrl)
        if node not in self.get_nodes():
            self.node['members'].append(ctrl.node['message'])

    def add_members(self, nodes):
        if type(nodes) not in (list, tuple):
            nodes = [nodes]
        for node in nodes:
            self.add_member(node)

    def get_members(self):
        for node in self.get_nodes():
            c = Control(node)
            if c is None:
                continue
            yield Control(node)

    def get_all_members(self):
        ctrls = ordered_dict()
        for ctrl in self.get_members():
            ctrls[ctrl] = None

        for grp in self.get_all_children():
            for ctrl in grp.get_members():
                ctrls[ctrl] = None

        return list(ctrls)

    def get_nodes(self):
        for i in self.node['members'].array_indices:
            node = self.node['members'][i].input()
            if node:
                yield node

    def get_all_nodes(self, vis=False):
        nodes = ordered_dict()
        for node in self.get_nodes():
            nodes[node] = None

        for grp in self.get_all_children():
            for node in grp.get_nodes():
                nodes[node] = None

        nodes = list(nodes)

        # exclude nodes of vis subgroup from group
        if vis and 'gem_id' in self.node and '::vis.' in self.node['gem_id'].read():
            vis_groups = {}
            for node in nodes:
                groups = Group.get_from_node(node)
                for group in groups:
                    if 'gem_id' in group.node and '::vis.' in group.node['gem_id'].read():
                        if group not in vis_groups:
                            vis_groups[group] = []
                        vis_groups[group].append(node)

            s0 = len(vis_groups[self])
            for grp in vis_groups:
                if grp == self:
                    continue
                if len(vis_groups[grp]) < s0:
                    # exclude subgroup vis
                    nodes = list(set(nodes).difference(set(vis_groups[grp])))

        return nodes

    @staticmethod
    def get_from_node(node):
        if isinstance(node, mx.Node) and 'gem_id' in node:
            for _node in node.outputs(type=mx.tNetwork):
                if 'gem_type' in _node and _node['gem_type'] == Group.type_name:
                    yield Group(_node)

    # ui callbacks -----------------------------------------------------------------------------------------------------

    def select(self):
        mx.cmd(mc.select, self.get_all_nodes())

    def set_key(self):
        for node in self.get_all_nodes():
            mx.cmd(mc.setKeyframe, node)

    def get_bind_pose_cmds(self):
        cmds = []
        for c in self.get_all_members():
            cmds += c.get_bind_pose_cmds()
        return cmds

    def get_pose_cmds(self, as_string=False):
        cmds = []
        if as_string:
            cmds = 'import mikan.maya.cmdx as mx\n\n'
        for c in self.get_all_members():
            cmds += c.get_pose_cmds(as_string)
        return cmds

    def get_mirror_cmds(self, direction, axis='x'):
        cmds = []
        for c in self.get_all_members():
            cmds += c.get_mirror_cmds(direction, axis)
        return cmds

    def connect_showhide(self, grp):
        Control.connect_showhide_node(self.node, grp)

    def show(self):
        with mx.DGModifier() as md:
            for node in self.get_all_nodes(vis=True):
                if not node['v'].editable:
                    log.warning('/!\\ {}.visibility is not editable'.format(node))
                    continue
                try:
                    md.set_attr(node['v'], True)
                except:
                    pass

    def hide(self):
        with mx.DGModifier() as md:
            for node in self.get_all_nodes(vis=True):
                if not node['v'].editable:
                    log.warning('/!\\ {}.visibility is not editable'.format(node))
                    continue
                try:
                    md.set_attr(node['v'], False)
                    node.hide()
                except:
                    pass

    def create_set(self, parent=None):

        ctrls = mx.ls(self.get_nodes())
        if not ctrls:
            return

        name = 'ctrl_{}'.format(self.get_name())
        set_node = mx.encode(mc.sets(n=name, empty=True))
        set_node.update(ctrls)

        if isinstance(parent, mx.ObjectSet):
            parent.add(set_node)

        for ch in self.get_children():
            ch.create_set(parent=set_node)


class Control(object):
    type_name = 'control'

    def __new__(cls, node):
        if not isinstance(node, mx.Node):
            node = mx.encode(str(node))
        if 'gem_type' not in node:
            raise RuntimeError('node "{}" is not valid'.format(node))
        if node['gem_type'] == Control.type_name:
            return super(Control, cls).__new__(cls)
        else:
            log.warning('/!\\ invalid cast with wrong mikan type ({}: {})'.format(node, node['gem_type'].read()))

    def __init__(self, node):
        if not isinstance(node, mx.Node):
            node = mx.encode(str(node))
        self.node = node

    def __str__(self):
        return str(self.node)

    def __repr__(self):
        return 'Control(\'{}\')'.format(self.node)

    def __eq__(self, other):
        if isinstance(other, Control):
            return self.node == other.node
        return False

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return self.node.__hash__() ^ hash(Control)

    @staticmethod
    def create(node):
        if not isinstance(node, mx.Node):
            node = mx.encode(str(node))

        if 'gem_type' not in node:
            with mx.DGModifier() as md:
                md.add_attr(node, mx.String('gem_type'))
            with mx.DGModifier() as md:
                md.set_attr(node['gem_type'], Control.type_name)
            node['gem_type'].lock()

        ctrl = Control(node)

        # hidden?
        if 'hidden' not in node:
            node.add_attr(mx.Boolean('hidden', default=False))

        # bind pose
        ctrl.set_bind_pose()

        # cosmetics
        node['v'].keyable = False
        node['v'].channel_box = True
        if node.type_id == mx.tJoint:
            node['radius'].keyable = False
            node['radius'].channel_box = True

        return ctrl

    def set_bind_pose(self):
        set_bind_pose(self.node)

    def get_bind_pose(self):
        get_bind_pose(self.node)

    def get_groups(self):
        return list(Group.get_from_node(self.node))

    @staticmethod
    def create_control_shape(root, n=None):
        if not n:
            n = 'c_shape#'

        with mx.DagModifier() as md:
            loc = md.create_node(mx.tLocator, parent=root, name=n)
        loc['localScale'] = (0, 0, 0)
        for dim in ('', 'X', 'Y', 'Z'):
            loc['localScale' + dim].keyable = False
            loc['localScale' + dim].channel_box = False
            loc['localPosition' + dim].keyable = False
            loc['localPosition' + dim].channel_box = False
        loc['v'] = False
        return loc

    @staticmethod
    def set_control_shape(shape, control):
        for s in control.shapes():
            s['ihi'] = False

        mx.cmd(mc.parent, shape, control, r=1, s=1, add=1)

        if 'control_shape' not in control:
            control.add_attr(mx.Message('control_shape'))
            shape['message'] >> control['control_shape']

        shape['ihi'] = True

    # mirroring --------------------------------------------------------------------------------------------------------

    @staticmethod
    def create_mirror_table(node0, node1, axis='x', epsilon=0.0001):

        def extract(pm, wm):
            return (
                [mx.Vector(pm[i:i + 3]) for i in (0, 4, 8)],
                [mx.Vector(wm[i:i + 3]) for i in (0, 4, 8)]
            )

        def flip(v, a):
            if a in ('x', 'yz'):  return mx.Vector(-v[0], v[1], v[2])
            if a in ('y', 'xz'):  return mx.Vector(v[0], -v[1], v[2])
            if a in ('z', 'xy'):  return mx.Vector(v[0], v[1], -v[2])
            return v

        p0, w0 = extract(node0['pm'][0].read(), node0['wm'][0].read())
        p1, w1 = extract(node1['pm'][0].read(), node1['wm'][0].read())

        d0 = node0['pm'][0].as_matrix().det4x4()
        d1 = node1['pm'][0].as_matrix().det4x4()

        w0 = [v * d0 for v in w0]
        w1 = [v * d1 * -1 for v in w1]

        p1 = [flip(v, axis) for v in p1]
        w1 = [flip(v, axis) for v in w1]

        dot = [(a * b) for a, b in zip(p0 + w0, p1 + w1)]

        table = [
            1 if v > epsilon else
            -1 if v < -epsilon else
            (-1 if i < 3 else 1)
            for i, v in enumerate(dot)
        ]

        mt = 'mirror_{}t'.format(axis)
        mr = 'mirror_{}r'.format(axis)

        for node in (node0, node1):
            if mt not in node: node.add_attr(mx.Double3(mt))
            if mr not in node: node.add_attr(mx.Double3(mr))
            node[mt], node[mr] = table[:3], table[3:]

    def get_mirror_cmds(self, direction, axis='x'):
        if 'mirror_{}t'.format(axis) not in self.node:
            return []

        cmds = []

        cps = []
        for i in self.node['bind_pose'].array_indices:
            plug_name = self.node['bind_pose'][i]['plug'].read()
            if plug_name.startswith('!'):
                plug = self.node[plug_name[1:]]
            else:
                plug = self.node[plug_name]
            if not plug.editable:
                continue
            cps.append(plug_name)

        single = False
        if 'mirrors' not in self.node:
            single = True
            pc = self.node
            nc = None
        else:
            attr = 'mirror_{}s'.format(axis)
            mirrors = {self.node[attr].read(): self.node}

            _m = self.node['mirrors']
            for sign, node in [(_m[i].read(), _m[i].input()) for i in _m.array_indices]:
                if axis in sign:
                    mirrors[sign] = node

            if len(mirrors) != 2:
                return

            pc = mirrors['+' + axis]
            nc = mirrors['-' + axis]

        do_xfo = self.node.is_a(mx.kTransform)
        if do_xfo:
            mt = pc['mirror_{}t'.format(axis)].read()
            mr = pc['mirror_{}r'.format(axis)].read()

            pt = pc['t'].as_vector()
            pr = pc['r'].as_vector()
            ps = pc['s'].as_vector()
            if not single:
                nt = nc['t'].as_vector()
                nr = nc['r'].as_vector()
                ns = nc['s'].as_vector()
                _pt = mx.Vector(pt)
                _pr = mx.Vector(pr)
                _ps = mx.Vector(ps)

        # middle ctrls
        if single:
            # mirror plugs
            pp = {}
            np = {}
            for plug in cps:
                if plug.endswith('_L'):
                    pp[plug[:-2]] = plug
                if plug.endswith('_R'):
                    np[plug[:-2]] = plug
            cp = list(set(pp).union(set(np)))

            for p in cp:
                if p in pp and p in np:
                    pv = pc[pp[p]].read()
                    nv = pc[np[p]].read()
                    if direction >= 0:
                        cmds.append(partial(_set_attr, pc[pp[p]], nv))
                    if direction <= 0:
                        cmds.append(partial(_set_attr, pc[np[p]], pv))

            # mirror xfo
            if do_xfo:
                if direction != 0:
                    # mirror
                    ix = {'x': 0, 'y': 1, 'z': 2}[axis]
                    zt = [1, 1, 1]
                    zr = [0, 0, 0]
                    zt[ix] = 0
                    zr[ix] = 1
                    for i in range(3):
                        pt[i] = pt[i] * mt[i] * zt[i]
                        pr[i] = pr[i] * mr[i] * zr[i]

                else:
                    # flip
                    for i in range(3):
                        pt[i] = pt[i] * mt[i]
                        pr[i] = pr[i] * mr[i]

                for i, dim in enumerate('xyz'):
                    if '!t' + dim in cps:
                        cmds.append(partial(_set_attr, pc['t' + dim], pt[i]))
                    if '!r' + dim in cps:
                        cmds.append(partial(_set_attr, pc['r' + dim], pr[i]))

        # branched controls
        else:
            # mirror plugs
            pp = {}
            np = {}
            for plug in cps:
                if '!' in plug:
                    continue
                if plug in nc:
                    pp[plug] = pc[plug].read()
                    np[plug] = nc[plug].read()
            _pp = pp.copy()

            # mirror xfo
            if direction == 0:
                # flip
                if do_xfo:
                    for i in range(3):
                        pt[i] = nt[i] * mt[i]
                        pr[i] = nr[i] * mr[i]
                        ps[i] = ns[i]
                        nt[i] = _pt[i] * mt[i]
                        nr[i] = _pr[i] * mr[i]
                        ns[i] = _ps[i]
                for plug in pp:
                    pp[plug] = np[plug]
                    np[plug] = _pp[plug]
            elif direction == -1:
                # + to -
                if do_xfo:
                    _pt = pt
                    for i in range(3):
                        nt[i] = _pt[i] * mt[i]
                        nr[i] = _pr[i] * mr[i]
                        ns[i] = _ps[i]
                for plug in pp:
                    np[plug] = _pp[plug]
            elif direction == 1:
                # - to +
                if do_xfo:
                    for i in range(3):
                        pt[i] = nt[i] * mt[i]
                        pr[i] = nr[i] * mr[i]
                        ps[i] = ns[i]
                for plug in pp:
                    pp[plug] = np[plug]

            for i, dim in enumerate('xyz'):
                if direction >= 0:
                    if '!t' + dim in cps:
                        cmds.append(partial(_set_attr, pc['t' + dim], pt[i]))
                    if '!r' + dim in cps:
                        cmds.append(partial(_set_attr, pc['r' + dim], pr[i]))
                    if '!s' + dim in cps:
                        cmds.append(partial(_set_attr, pc['s' + dim], ps[i]))
                if direction <= 0:
                    if '!t' + dim in cps:
                        cmds.append(partial(_set_attr, nc['t' + dim], nt[i]))
                    if '!r' + dim in cps:
                        cmds.append(partial(_set_attr, nc['r' + dim], nr[i]))
                    if '!s' + dim in cps:
                        cmds.append(partial(_set_attr, nc['s' + dim], ns[i]))
            for plug in pp:
                if direction >= 0:
                    cmds.append(partial(_set_attr, pc[plug], pp[plug]))
                if direction <= 0:
                    cmds.append(partial(_set_attr, nc[plug], np[plug]))

        return cmds

    def get_bind_pose_cmds(self):
        cmds = []
        for i in self.node['bind_pose'].array_indices:
            plug = self.node['bind_pose'][i]['plug'].read()
            if '!' in plug:
                plug = plug.replace('!', '')
            if plug not in self.node:
                continue
            _plug = self.node[plug]
            if _plug.locked or not _plug.keyable:
                continue
            v = self.node['bind_pose'][i]['value'].read()
            cmds.append(partial(_set_attr, _plug, v))
        return cmds

    def get_pose_cmds(self, as_string=False):
        cmds = []
        cmds_str = ''
        for i in self.node['bind_pose'].array_indices:
            plug = self.node['bind_pose'][i]['plug'].read()
            if '!' in plug:
                plug = plug.replace('!', '')
            v = self.node[plug].read()
            cmds.append(partial(_set_attr, self.node[plug], v))
            if as_string:
                cmds_str += 'with mx.DGModifier() as md:\n  try: plug = mx.encode("{}")["{}"]; md.set_attr(plug, {})\n  except: pass\n'.format(
                    self.node, plug, v)
        if as_string:
            return cmds_str
        return cmds

    @staticmethod
    def connect_showhide_node(node, grp):
        if 'menu_showhide' not in node:
            node.add_attr(mx.Message('menu_showhide', array=True))

        menu = node['menu_showhide']
        if grp.node not in [menu[i].input() for i in menu.array_indices]:
            menu.append(grp.node['message'])

    def connect_showhide(self, grp):
        self.connect_showhide_node(self.node, grp)


def _set_attr(plug, value):
    with mx.DGModifier() as md:
        md.set_attr(plug, value)


def set_bind_pose(node, attr='bind_pose'):
    # get bind pose plug
    if attr not in node:
        children = mx.String('plug'), mx.Double('value')
        node.add_attr(mx.Compound(attr, array=True, children=children))
    plug = node[attr]

    plugs = {}
    for i in plug.array_indices:
        plugs[plug[i]['plug'].read()] = i

    # transform
    if node.is_a(mx.kTransform):
        for attr in 'trs':
            for dim in 'xyz':
                _attr = node[attr + dim]
                if _attr.locked or _attr.input():
                    continue
                if not _attr.keyable:
                    continue

                v = node[attr + dim].read()
                _attr = '!' + attr + dim
                if _attr not in plugs:
                    if plugs:
                        i = max(plugs.values()) + 1
                    else:
                        i = 0
                else:
                    i = plugs[_attr]

                plugs[_attr] = i
                plug[i]['plug'] = _attr
                plug[i]['value'] = v

    # custom attributes
    for attr in mc.listAttr(str(node), k=1, u=1, ud=1, c=1, s=1) or []:
        attr = node[attr]
        if attr.input():
            continue

        _attr = attr.name()
        if attr.name(long=True) in ['controlPoints', 'colorSet']:
            continue

        v = attr.read()
        if _attr not in plugs:
            if plugs:
                i = max(plugs.values()) + 1
            else:
                i = 0
        else:
            i = plugs[_attr]

        plugs[_attr] = i
        plug[i]['plug'] = _attr
        plug[i]['value'] = v


def get_bind_pose(node, attr='bind_pose'):
    if attr not in node:
        return
    plug = node[attr]

    for i in plug.array_indices:
        attr = plug[i]['plug'].read()

        try:
            if attr.startswith('!'):
                attr = attr[1:]
            v = plug[i]['value'].read()
            with mx.DGModifier() as md:
                md.set_attr(node[attr], v)
        except:
            pass
