# coding: utf-8

from math import copysign
from ast import literal_eval

import meta_nodal_py as kl
from meta_nodal_py.Imath import V3f, M44f
from meta_nodal_py.gui_nodes import NodeSelection
from tang_core.anim import set_animated_plug_value, is_keyable

from mikan.core.logger import create_logger
from mikan.core.utils import flatten_list
from ..lib.commands import *
from .node import Nodes

__all__ = [
    'Group',
    'Control'
]

log = create_logger()

cached_group_nodes = {}
cached_group_children = {}
cached_group_parents = {}
cached_group_members = {}
cached_group_all_nodes = {}
cached_group_all_nodes_vis = {}

cached_groups = [
    cached_group_nodes,
    cached_group_children,
    cached_group_parents,
    cached_group_members,
    cached_group_all_nodes,
    cached_group_all_nodes_vis,
]


class Group(object):
    type_name = 'group'

    def __new__(cls, node):
        if not isinstance(node, kl.Node) or not node.get_dynamic_plug('gem_type'):
            raise RuntimeError(f'node "{node}" is not valid')
        if node.gem_type.get_value() == Group.type_name:
            return super(Group, cls).__new__(cls)

    def __init__(self, node):
        self.node = node

    def __str__(self):
        return str(self.node.get_name())

    def __repr__(self):
        return f"Group('{self}')"

    def __eq__(self, other):
        if isinstance(other, Group):
            return self.node == other.node
        return False

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return self.node.__hash__() ^ hash(Group)

    @staticmethod
    def create(name, parent=None):
        if parent is None:
            parent = find_root()

        node = kl.Node(parent, f'grp_{name}'.replace(' ', '_'))

        add_plug(node, 'gem_type', str, default_value=Group.type_name)
        add_plug(node, 'gem_group', str, default_value=name)

        add_plug(node, 'members', str, array=True)
        add_plug(node, 'parents', str, array=True)
        add_plug(node, 'children', str, array=True)

        return Group(node)

    @property
    def name(self):
        return self.node.gem_group.get_value()

    @property
    def nice_name(self):
        return self.name.title().replace('_', ' ')

    def get_name(self):
        return self.name

    def add_parent(self, grp):
        if self == grp:
            raise RuntimeError('cannot parent group to itself')

        if not isinstance(grp, Group):
            raise RuntimeError(f'{grp} is not a Group')

        if grp not in self.get_parents():
            plug = self.node.parents
            i = get_next_available(plug)
            plug[i].connect(grp.node.gem_group)

        if self not in grp.get_children():
            plug = grp.node.children
            i = get_next_available(plug)
            plug[i].connect(self.node.gem_group)

        self.node.set_parent(grp.node)

    def get_parents(self, cache=False):
        if cache:
            if self in cached_group_parents:
                return cached_group_parents[self]

        groups = []

        plug = self.node.parents
        _vector = self.node.find('parents')  # legacy
        if _vector:
            plug = _vector.input

        groups += [Group(v.get_node()) for v in [plug[i].get_input() for i in range(plug.get_size())] if v]

        if cache:
            cached_group_parents[self] = groups
        return groups

    def get_all_parents(self, parents=None, cache=False):
        if parents is None:
            parents = []

        _parents = self.get_parents(cache=cache)
        parents.extend(_parents)
        for parent in _parents:
            parent.get_all_parents(parents, cache=cache)

        return parents

    def get_first_parent(self, cache=False):
        parents = self.get_all_parents(cache=cache)
        if parents:
            return parents[-1]

    def remove_parent(self, grp):
        if not isinstance(grp, Group):
            raise AssertionError('invalid argument')

        plug = self.node.parents
        for i in range(plug.get_size()):
            plug_in = plug[i].get_input()
            if plug_in:
                node = plug_in.get_node()
                if node == grp.node:
                    plug[i].disconnect(True)

        plug = grp.node.children
        for i in range(plug.get_size()):
            plug_in = plug[i].get_input()
            if plug_in:
                node = plug_in.get_node()
                if node == self.node:
                    plug[i].disconnect(True)

    def remove_parents(self):
        for grp in self.get_parents():
            self.remove_parent(grp)

    orphan = remove_parents

    def add_child(self, grp):
        if self == grp:
            raise RuntimeError('cannot parent group to itself')

        if not isinstance(grp, Group):
            raise RuntimeError(f'{grp} is not a Group')

        if self not in grp.get_parents():
            plug = grp.node.parents
            i = get_next_available(plug)
            plug[i].connect(self.node.gem_group)

        if grp not in self.get_children():
            plug = self.node.children
            i = get_next_available(plug)
            plug[i].connect(grp.node.gem_group)

        grp.node.set_parent(self.node)

    def get_children(self, cache=False):
        if cache:
            if self in cached_group_children:
                return cached_group_children[self]

        groups = []

        plug = self.node.children
        _vector = self.node.find('children')  # legacy
        if _vector:
            plug = _vector.input

        groups += [Group(v.get_node()) for v in [plug[i].get_input() for i in range(plug.get_size())] if v]

        if cache:
            cached_group_children[self] = groups

        return groups

    def get_all_children(self, children=None, cache=False):

        if children is None:
            children = []

        for child in self.get_children(cache=cache):
            children.append(child)
            child.get_all_children(children, cache=cache)

        return children

    def remove_child(self, grp):
        if not isinstance(grp, Group):
            raise RuntimeError(f'{grp} is not a Group')

        plug = self.node.children
        for i in range(plug.get_size()):
            plug_in = plug[i].get_input()
            if plug_in:
                node = plug_in.get_node()
                if node == grp.node:
                    plug[i].disconnect(True)

        plug = grp.node.parents
        for i in range(plug.get_size()):
            plug_in = plug[i].get_input()
            if plug_in:
                node = plug_in.get_node()
                if node == self.node:
                    plug[i].disconnect(True)

    def remove_children(self):
        for grp in self.get_children():
            self.remove_child(grp)

    def merge(self, grp):
        tags = []
        if grp.node.get_dynamic_plug('gem_id'):
            tags = grp.node.gem_id.get_value().split(';')
        members = list(grp.get_nodes())
        children = list(grp.get_children())
        for child in children:
            grp.remove_child(child)
        parents = list(grp.get_parents())
        for parent in parents:
            grp.remove_parent(parent)

        grp.node.remove_from_parent()

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

    def add_member(self, ctrl):
        if not isinstance(ctrl, Control):
            if not isinstance(ctrl, kl.Node):
                raise RuntimeError(f"can't create Control for {ctrl}")

            ctrl = Control.create(ctrl)

        if ctrl not in self.get_members():
            if not ctrl.node.get_dynamic_plug('gem_id'):
                add_plug(ctrl.node, 'gem_id', str)

            plug = self.node.members
            i = get_next_available(plug)
            plug[i].connect(ctrl.node.gem_id)

    def add_members(self, *args):
        nodes = [node for node in flatten_list(args)]
        if not nodes:
            nodes = get_selected()
        if not nodes:
            return

        for node in nodes:
            ctrl = Control.create(node)
            self.add_member(ctrl)

    def get_members(self, cache=False):
        if cache:
            if self in cached_group_members:
                return cached_group_members[self]

        members = list(map(lambda node: Control(node), self.get_nodes(cache=cache)))

        if cache:
            cached_group_members[self] = members
        return members

    def get_all_members(self, cache=False):

        ctrls = self.get_members(cache=cache)
        if cache:
            ctrls = ctrls[:]

        for grp in self.get_all_children(cache=cache):
            for ctrl in grp.get_members(cache=cache):
                if ctrl not in ctrls:
                    ctrls.append(ctrl)

        return ctrls

    def get_nodes(self, cache=False):
        if cache:
            if self in cached_group_nodes:
                return cached_group_nodes[self]
            node_selection = NodeSelection()

        plug = self.node.members
        _vector = self.node.find('members')  # legacy
        if _vector:
            plug = _vector.input

        nodes = [v.get_node() for v in [plug[i].get_input() for i in range(plug.get_size())] if v]

        if cache:
            for node in nodes:
                node_selection.add(node)
            cached_group_nodes[self] = node_selection
            return node_selection

        return nodes

    def get_all_nodes(self, vis=False, cache=False):
        if vis:
            if not (self.node.get_dynamic_plug('gem_id') and '::vis.' in self.node.gem_id.get_value()):
                vis = False

        if cache:
            cache_data = cached_group_all_nodes
            if vis:
                cache_data = cached_group_all_nodes_vis

            if self in cache_data:
                return cache_data[self]

            nodes = self.get_nodes(cache=cache)

        else:
            nodes = self.get_nodes()

        for grp in self.get_all_children(cache=cache):
            for node in grp.get_nodes(cache=cache):
                if node not in nodes:
                    if cache:
                        nodes.add(node)
                    else:
                        nodes.append(node)

        # exclude nodes of vis subgroup from group
        if vis:
            vis_groups = {}
            for node in nodes:
                for group in Group.get_from_node(node):
                    if group.node.get_dynamic_plug('gem_id') and '::vis.' in group.node.gem_id.get_value():
                        if group not in vis_groups:
                            vis_groups[group] = set()
                        vis_groups[group].add(node)

            s0 = len(vis_groups[self])
            for grp in vis_groups:
                if grp == self:
                    continue
                if len(vis_groups[grp]) < s0:
                    # exclude subgroup vis
                    if cache:
                        for node in vis_groups[grp]:
                            if node in nodes:
                                nodes.remove(node)
                    else:
                        nodes = list(set(nodes).difference(vis_groups[grp]))

        if cache:
            cache_data[self] = nodes
        return nodes

    @staticmethod
    def get_from_node(node):
        groups = []
        if not isinstance(node, kl.Node) or not node.get_dynamic_plug('gem_id'):
            return groups

        for plug in node.gem_id.get_outputs():
            _node = plug.get_node()
            if plug.get_name() == 'members':
                grp = _node
            elif isinstance(_node, kl.StringToVectorString) and _node.get_name() == 'members':  # legacy
                grp = _node.get_parent()
            else:
                continue

            if grp.get_dynamic_plug('gem_type') and grp.gem_type.get_value() == Group.type_name:
                groups.append(Group(grp))

        return groups

    # ui callbacks -----------------------------------------------------------------------------------------------------

    def connect_showhide(self, grp):
        Control.connect_showhide_node(self.node, grp)

    def show(self, modifier=None):
        for node in self.get_all_nodes(vis=True, cache=True):
            try:
                if modifier:
                    set_animated_plug_value(node.show, True, modifier=modifier)
                else:
                    node.show.set_value(True)
            except:
                pass

    def hide(self, modifier=None):
        for node in self.get_all_nodes(vis=True, cache=True):
            try:
                if modifier:
                    set_animated_plug_value(node.show, False, modifier=modifier)
                else:
                    node.show.set_value(False)
            except:
                pass


class Control(object):
    type_name = 'control'

    def __new__(cls, node):
        if isinstance(node, kl.Node) and node.get_dynamic_plug('gem_type') and node.gem_type.get_value() == Control.type_name:
            return super(Control, cls).__new__(cls)

    def __init__(self, node):
        self.node = node

    def __str__(self):
        return self.node.get_name()

    def __repr__(self):
        return f"Control('{self}')"

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
        if not node.get_plug('gem_type'):
            add_plug(node, 'gem_type', str)
        node.gem_type.set_value(Control.type_name)

        ctrl = Control(node)

        # hidden?
        if not node.get_plug('hidden'):
            add_plug(node, 'hidden', bool, nice_name='Hidden')

        # bind pose
        ctrl.set_bind_pose()

        # deliver
        return ctrl

    def set_bind_pose(self):

        def _get_keyable_plugs(node, plugs=None):
            if plugs is None:
                plugs = []

            for plug in node.get_plugs():
                if plug.is_eval():
                    continue

                plug_name = plug.get_name()
                type_name = plug.get_type_name()

                if type_name == 'meta_nodal_py.Imath.M44f':
                    n = node.find(plug_name)
                    if n:
                        _get_keyable_plugs(n, plugs)

                elif type_name == 'meta_nodal_py.Imath.V3f':
                    n = node.find(plug_name)
                    if n:
                        _get_keyable_plugs(n, plugs)

                elif type_name in ('float', 'int', 'bool'):
                    if is_keyable(plug) and not is_locked(plug):
                        plugs.append(plug)

            return plugs

        for plug in _get_keyable_plugs(self.node):
            plug.set_user_info('bind_pose', str(plug.get_value()))

    def get_bind_pose(self, modifier, plug_filter=None):
        # special case of all 'Get Bind Pose' actions:
        # if it's been asked on the Base Anim, the value is not adapted from other layers
        adapt_layer_value = modifier.document.active_layer != ''

        for plug in get_keyable_plugs(self.node, plug_filter):
            node = plug.get_node()
            if node != self.node and node.get_dynamic_plug('gem_id'):
                if '::ctrls' in node.gem_id.get_value():
                    continue

            bind_pose = plug.get_user_info('bind_pose')
            if not bind_pose:
                continue
            set_animated_plug_value(plug, literal_eval(bind_pose), modifier=modifier, adapt_layer_value=adapt_layer_value)

    def get_groups(self):
        return Group.get_from_node(self.node)

    @staticmethod
    def create_mirror_table(node0, node1, axis='x'):
        w0 = node0.world_transform.get_value()
        w1 = node1.world_transform.get_value()
        p0 = node0.get_parent().world_transform.get_value()
        p1 = node1.get_parent().world_transform.get_value()

        ti0 = V3f(*[p0.get(0, i) for i in range(3)])
        tj0 = V3f(*[p0.get(1, i) for i in range(3)])
        tk0 = V3f(*[p0.get(2, i) for i in range(3)])
        ti1 = V3f(*[p1.get(0, i) for i in range(3)])
        tj1 = V3f(*[p1.get(1, i) for i in range(3)])
        tk1 = V3f(*[p1.get(2, i) for i in range(3)])
        ri0 = V3f(*[w0.get(0, i) for i in range(3)])
        rj0 = V3f(*[w0.get(1, i) for i in range(3)])
        rk0 = V3f(*[w0.get(2, i) for i in range(3)])
        ri1 = V3f(*[w1.get(0, i) for i in range(3)])
        rj1 = V3f(*[w1.get(1, i) for i in range(3)])
        rk1 = V3f(*[w1.get(2, i) for i in range(3)])

        d0 = 1 if ti0.cross(tj0).dot(tk0) > 0 else -1  # det
        d1 = 1 if ti1.cross(tj1).dot(tk1) > 0 else -1  # det

        x0 = [ti0, tj0, tk0, ri0, rj0, rk0]
        x1 = [ti1, tj1, tk1, ri1, rj1, rk1]
        x0[3:] = map(lambda x: x * d0, x0[3:])
        x1[3:] = map(lambda x: x * d1 * -1, x1[3:])

        if axis in ['x', 'yz']:
            x1 = map(lambda x: V3f(-x.x, x.y, x.z), x1)
        elif axis in ['y', 'xz']:
            x1 = map(lambda x: V3f(x.x, -x.y, x.z), x1)
        elif axis in ['z', 'xy']:
            x1 = map(lambda x: V3f(x.x, x.y, -x.z), x1)

        table = map(lambda x: copysign(1, x[0].dot(x[1])), zip(x0, x1))
        table = list(map(lambda x: x / abs(x) if x else 0, table))
        if 0 in table:
            table = [1, 1, 1, 1, 1, 1]

        for node in (node0, node1):
            mt = f'mirror_{axis}t'
            mr = f'mirror_{axis}r'
            if not node.get_plug(mt):
                plug = add_plug(node, mt, V3f)
                plug.set_value(V3f(*table[:3]))
            if not node.get_plug(mr):
                plug = add_plug(node, mr, V3f)
                plug.set_value(V3f(*table[3:]))

    def get_mirror_dict(self, axis='x'):
        mirrors = {}

        if self.node.get_dynamic_plug('mirrors'):
            _plug = self.node.get_dynamic_plug(f'mirror_{axis}s')
            if _plug:
                mirrors[_plug.get_value()] = self.node

            plug = self.node.mirrors
            _vector = self.node.find('mirrors')  # legacy
            if _vector:
                plug = _vector.input

            for i in range(plug.get_size()):
                plug_in = plug[i].get_input()
                if plug_in:
                    node = plug_in.get_node()
                    sign = plug_in.get_value()
                    if axis in sign:
                        mirrors[sign] = node

        return mirrors

    def get_mirror_cmds(self, direction, current_frame, axis='x', plug_filter=None):
        cmds = []

        plugs = {}
        for plug in get_keyable_plugs(self.node, plug_filter):
            plug_name = plug.get_name()
            if len(plug_name) == 2 and plug_name[0] in 'srt' and plug_name[1] in 'xyz':
                plug_name = plug_name[0] + '.' + plug_name[1]
            plugs[plug_name] = plug

        single = False
        if not self.node.get_dynamic_plug('mirrors'):
            single = True
            pc = self.node
            nc = None
        else:
            mirrors = self.get_mirror_dict(axis)

            if len(mirrors) != 2:
                return []

            pc = mirrors['+' + axis]
            nc = mirrors['-' + axis]

        do_xfo = isinstance(pc, kl.SceneGraphNode) and self.node.get_dynamic_plug(f'mirror_{axis}t')
        if do_xfo:
            mt = pc.get_dynamic_plug(f'mirror_{axis}t').get_value()
            mr = pc.get_dynamic_plug(f'mirror_{axis}r').get_value()
            mt = (mt.x, mt.y, mt.z)
            mr = (mr.x, mr.y, mr.z)

            pt = [0, 0, 0]
            pr = [0, 0, 0]
            ps = [1, 1, 1]
            _pt_src = None
            _pr_src = None
            _ps_src = None
            _pt = pc.find('transform/translate')
            if _pt:
                pt = _pt.vector.get_value(current_frame)
                pt = [pt.x, pt.y, pt.z]
                _pt_src = [getattr(pc, "tx", None), getattr(pc, "ty", None), getattr(pc, "tz", None)]
            _pr = pc.find('transform/rotate')
            if _pr:
                pr = _pr.euler.get_value(current_frame)
                pr = [pr.x, pr.y, pr.z]
                _pr_src = [getattr(pc, "rx", None), getattr(pc, "ry", None), getattr(pc, "rz", None)]
            _ps = pc.find('transform/scale')
            if _ps:
                ps = _ps.vector.get_value(current_frame)
                ps = [ps.x, ps.y, ps.z]
                _ps_src = [getattr(pc, "sx", None), getattr(pc, "sy", None), getattr(pc, "sz", None)]
            if not single:
                nt = [0, 0, 0]
                nr = [0, 0, 0]
                ns = [1, 1, 1]
                _nt_src = [None, None, None]
                _nr_src = [None, None, None]
                _ns_src = [None, None, None]
                _nt = nc.find('transform/translate')
                if _nt:
                    nt = _nt.vector.get_value(current_frame)
                    nt = [nt.x, nt.y, nt.z]
                    _nt_src = [getattr(nc, "tx", None), getattr(nc, "ty", None), getattr(nc, "tz", None)]
                _nr = nc.find('transform/rotate')
                if _nr:
                    nr = _nr.euler.get_value(current_frame)
                    nr = [nr.x, nr.y, nr.z]
                    _nr_src = [getattr(nc, "rx", None), getattr(nc, "ry", None), getattr(nc, "rz", None)]
                _ns = nc.find('transform/scale')
                if _ns:
                    ns = _ns.vector.get_value(current_frame)
                    ns = [ns.x, ns.y, ns.z]
                    _ns_src = [getattr(nc, "sx", None), getattr(nc, "sy", None), getattr(nc, "sz", None)]

                _pt = pt[:]
                _pr = pr[:]
                _ps = ps[:]

        # middle ctrls
        if single:
            # mirror plugs
            pp = {}
            np = {}
            for plug_name, plug in plugs.items():
                if plug_name.endswith('_L'):
                    pp[plug_name[:-2]] = plug
                if plug_name.endswith('_R'):
                    np[plug_name[:-2]] = plug
            cp = list(set(pp).union(set(np)))

            for p in cp:
                if p in pp and p in np:
                    pv = pp[p].get_value(current_frame)
                    nv = np[p].get_value(current_frame)
                    if direction >= 0:
                        cmds.append((pp[p], nv, np[p], False))
                    if direction <= 0:
                        cmds.append((np[p], pv, pp[p], False))

            # mirror xfo
            if do_xfo:
                inv_t = [False, False, False]
                inv_r = [False, False, False]
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
                        inv_t[i] = (mt[i] * zt[i]) < 0
                        inv_r[i] = (mr[i] * zr[i]) < 0

                else:
                    # flip
                    for i in range(3):
                        pt[i] = pt[i] * mt[i]
                        pr[i] = pr[i] * mr[i]
                        inv_t[i] = mt[i] < 0
                        inv_r[i] = mr[i] < 0

                for plug_name, plug in plugs.items():
                    if len(plug_name) != 3:
                        continue
                    if plug_name[1] != '.':
                        continue
                    dim = plug_name[2]
                    if dim not in 'xyz':
                        continue
                    i = {'x': 0, 'y': 1, 'z': 2}[dim]
                    srt_name = plug_name[0]
                    if srt_name == 't':
                        cmds.append((plug, pt[i], _pt_src[i], inv_t[i]))
                    elif srt_name == 'r':
                        cmds.append((plug, pr[i], _pr_src[i], inv_r[i]))

        # branched controls
        else:
            # mirror plugs
            pp = {}
            np = {}
            for plug_name, plug in plugs.items():
                if '.' in plug_name:  # cheap way to check if it is transform vector
                    continue
                _pc = pc.get_dynamic_plug(plug_name)
                _nc = nc.get_dynamic_plug(plug_name)
                if _pc and _nc:
                    pp[plug_name] = _pc.get_value(current_frame)
                    np[plug_name] = _nc.get_value(current_frame)
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

            inv_t = [False, False, False]
            inv_r = [False, False, False]
            if do_xfo:
                for i in range(3):
                    inv_t[i] = mt[i] < 0
                    inv_r[i] = mr[i] < 0

            for plug_name, plug in plugs.items():
                dim = plug_name[-1]
                plug_node = plug.get_node()

                if '.' in plug_name and dim in 'xyz':
                    _plug_name = plug_name.replace('.', '')
                    i = {'x': 0, 'y': 1, 'z': 2}[dim]
                    if plug_name[0] == 't':
                        if direction >= 0:
                            cmds.append((pc.get_dynamic_plug(_plug_name), pt[i], _nt_src[i], inv_t[i]))
                        if direction <= 0:
                            cmds.append((nc.get_dynamic_plug(_plug_name), nt[i], _pt_src[i], inv_t[i]))
                    elif plug_name[0] == 'r':
                        if direction >= 0:
                            cmds.append((pc.get_dynamic_plug(_plug_name), pr[i], _nr_src[i], inv_r[i]))
                        if direction <= 0:
                            cmds.append((nc.get_dynamic_plug(_plug_name), nr[i], _pr_src[i], inv_r[i]))
                    elif plug_name[0] == 's':
                        if direction >= 0:
                            cmds.append((pc.get_dynamic_plug(_plug_name), ps[i], _ns_src[i], False))
                        if direction <= 0:
                            cmds.append((nc.get_dynamic_plug(_plug_name), ns[i], _ps_src[i], False))

                else:
                    if direction >= 0 and plug_name in pp:
                        cmds.append((pc.get_dynamic_plug(plug_name), pp[plug_name],
                                     nc.get_dynamic_plug(plug_name), False))
                    if direction <= 0 and plug_name in np:
                        cmds.append((nc.get_dynamic_plug(plug_name), np[plug_name],
                                     pc.get_dynamic_plug(plug_name), False))

        return cmds

    @staticmethod
    def connect_showhide_node(node, grp):
        if not node.get_dynamic_plug('menu_showhide'):
            add_plug(node, 'menu_showhide', str, array=True)

        plug = node.menu_showhide
        i = get_next_available(plug)
        plug[i].connect(grp.node.gem_id)

        if isinstance(grp.node.get_parent(), kl.RootNode):
            grp.node.set_parent(node)

    def connect_showhide(self, grp):
        self.connect_showhide_node(self.node, grp)
