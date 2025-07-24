# coding: utf-8

from PySide2.QtWidgets import QApplication

import meta_nodal_py as kl
from meta_nodal_py.Imath import V3f, M44f, Euler
from tang_core.anim import is_keyable
from tang_core.layer import get_former_plugs_for_node

from mikan.core.logger import log

__all__ = [
    'Scene', 'find_doc', 'find_root', 'find_path', 'ls', 'get_selected',
    'get_selected', 'find_all_descendant',
    'get_keyable_plugs', 'get_locked_plugs',
    'add_plug', 'set_plug', 'get_next_available',
    'copy_transform', 'is_locked',
]


# doc ------------------------------------------------------------------------------------------------------------------

class Scene(object):
    Current_Root = None  # we use this to allow sandbox files to be run as standalone scripts (without tang.py/exe)

    def __init__(self, name='doc', root_node=None):
        self.name = name
        self.root_node = root_node

    def __enter__(self):
        if self.root_node is None:
            self.root_node = kl.RootNode("document")
        Scene.Current_Root = self.root_node
        return self.root_node

    def __exit__(self, exc_type, exc_val, exc_tb):
        Scene.Current_Root = None
        find_doc().rig_has_changed_without_modifiers()


def find_doc():
    assert Scene.Current_Root is None
    app = QApplication.instance()
    return app.document()


def find_root():
    if Scene.Current_Root is not None:
        return Scene.Current_Root
    return find_doc().root()


def get_selected():
    return find_doc().node_selection()


def find_path(path):
    doc = find_doc()
    return doc.root().find(doc.root().get_sub_path(path))


# nodes ----------------------------------------------------------------------------------------------------------------

def _flatten(l):
    for el in l:
        if type(el) in (tuple, list) and not isinstance(el, str):
            for sub in _flatten(el):
                yield sub
        else:
            yield el


def ls(*args, **kw):
    root = kw.get('root')
    if root is None:
        root = find_root()
    nodes = kw.get('nodes', [])
    hidden = kw.get('hidden', False)
    shortest = kw.get('shortest', True)

    if not args:
        for i in root.depth_first_skippable_iterator():
            node = i.node
            if node == root:
                continue
            name = node.get_name()
            if not hidden and name.startswith('__') and name.endswith('__'):
                i.skip_children()
                continue
            if not (isinstance(node, (kl.SceneGraphNode, kl.Geometry)) or type(node) == kl.Node):
                i.skip_children()
                continue
            nodes.append(node)
    else:
        nodes = _flatten(args)

    if kw.get('as_dict', False):
        d = {}
        duplicates = []
        for n in nodes:
            name = n.get_name()
            if name not in d:
                d[name] = n
            elif shortest:
                if not isinstance(d[name], list):
                    d[name] = [d[name]]
                    duplicates.append(name)
                d[name].append(n)

            plug_uuid = n.get_dynamic_plug('gem_uuid')
            if plug_uuid:
                d[plug_uuid.get_stored_value()] = n

        if shortest:
            i = 2
            while True:
                new = []
                for k in duplicates:
                    for n in d[k]:
                        name = '/'.join(n.get_full_name().split('/')[-i:])

                        if name not in d:
                            d[name] = n
                        else:
                            if not isinstance(d[name], list):
                                d[name] = [d[name]]
                                new.append(name)
                            d[name].append(n)

                if not new:
                    break
                duplicates = new
                i += 1

            for name in list(d):
                if not isinstance(d[name], list):
                    node = d[name]
                    path = node.get_full_name().split('/')[2:]
                    if len(path) < 2:
                        continue
                    for i in range(len(path) - 1):
                        k = '/'.join(path[-2 - i:])
                        if k not in d:
                            d[k] = node

        return d

    return nodes


def find_all_descendant(root=None, nodes=None):
    if root is None:
        root = find_root()
    if nodes is None:
        nodes = []

    for node in root.get_children():
        name = node.get_name()
        if name.startswith('__') and name.endswith('__'):
            continue
        nodes.append(node)
        find_all_descendant(node, nodes)

    return nodes


# plugs ----------------------------------------------------------------------------------------------------------------

def is_locked(plug):
    locked = plug.get_user_info("locked")
    return locked == "yes"


def get_keyable_plugs(node, plug_filter=None):
    plugs = list()

    ps = get_former_plugs_for_node(node, plug_filter)

    for plug in ps:
        if is_keyable(plug) and not is_locked(plug):
            plugs.append(plug)

    return plugs


def get_locked_plugs(node, plugs=None):
    if plugs is None:
        plugs = []

    for plug in node.get_plugs():
        if plug.is_eval():
            continue

        if is_locked(plug):
            plugs.append(plug)

    return plugs


# used in add_plug and set_plug only
def _handle_plug_desc(plug, min_value, max_value, step, enum, nice_name, keyable, k, lock, exportable):
    kernel_class = plug.get_type()

    desc = plug.get_all_user_infos()

    if kernel_class in [float, int]:
        if min_value is not None and max_value is not None:
            if min_value == max_value and not lock:
                lock = True
                log.warning('avoid locking plug using legacy min=max, but use lock=True for ' + plug.get_full_name())
        if min_value is not None:
            desc['min'] = str(min_value)
        if max_value is not None:
            desc['max'] = str(max_value)
        if step is None:
            step = str(0.1)
            if kernel_class is int:
                step = 1
        desc['step'] = str(step)
        if kernel_class is int and enum:
            if isinstance(enum, (list, tuple)):
                _enum = {}
                for key, value in enumerate(enum):
                    _enum[value] = key
                enum = _enum
            for key, value in enum.items():
                if not isinstance(key, str):
                    enum[str(key)] = enum.pop(key)
            desc['min'] = str(min(enum.values()))
            desc['max'] = str(max(enum.values()))
            desc['enum'] = str(enum)  # NB: use Python 3 ast module to decode: ast.literal_eval(str_of_dict)

    if k is not None:
        keyable = k
    if keyable is not None:
        if keyable:
            desc['keyable'] = 'yes'
            exportable = True  # keyable => exportable

            plug_name = plug.get_name()
            if 'nice_name' not in desc and not nice_name and not plug_name.startswith('_'):
                nice_name = plug.get_name().replace('_', ' ').title()

        else:
            desc.pop('keyable', None)  # removes keyable flag if any

    if exportable is not None:
        if exportable:
            desc['exp'] = 'yes'
        else:
            desc.pop('exp', None)  # removes exportable flag if any

    if lock is not None:
        # Note this does not change the exportable flag of the plug
        # ie: even locked a plug is still exported
        if lock:
            desc['locked'] = 'yes'
        else:
            desc.pop('locked', None)  # removes locked flag if any

    if nice_name is not None:
        if nice_name:
            desc['nice_name'] = nice_name
        else:
            desc.pop('nice_name', None)  # removes nice_name flag if any

    plug.set_all_user_infos(desc)


def add_plug(node, plug_name, kernel_class=float, default_value=None, array=False, size=None,
             min_value=None, max_value=None, step=None, enum=None, nice_name='', keyable=None, k=None,
             lock=None, exportable=None):
    """ add dynamic plug wrapper """

    if node.get_plug(plug_name):
        raise RuntimeError(plug_name + " already exists")

    dv = default_value is not None

    if kernel_class is int:
        default_value = int([0, default_value][dv])
    elif kernel_class is float:
        default_value = float([0, default_value][dv])
    elif kernel_class is bool:
        default_value = bool([False, default_value][dv])
    elif kernel_class is str:
        default_value = str(['', default_value][dv])
    elif kernel_class is kl.Imath.V3f:
        default_value = [kl.Imath.V3f(0), default_value][dv]
    elif kernel_class is kl.Imath.M44f:
        default_value = [kl.Imath.M44f(), default_value][dv]
    elif kernel_class in (kl.Unit, kl.Mesh):
        default_value = kernel_class()
    elif kernel_class is kl.Spline:
        default_value = kl.Spline([V3f(0, 0, 0)], [0.0], [0.0], False)
    else:
        raise ValueError

    if array:
        if isinstance(default_value, list):
            size = len(default_value)
        elif size is None:
            size = 1

    kw = {}
    if array:
        kw['size'] = size

    plug = node.add_dynamic_plug(plug_name, default_value, **kw)

    if kernel_class in [int, float, bool, str] and not array:
        kl.set_plug_bakable(plug)  # warning: this is useless in general since the rig won't be baked in abc

    _handle_plug_desc(plug, min_value, max_value, step, enum, nice_name, keyable, k, lock, exportable)

    return plug


def set_plug(plug, value=None, min_value=None, max_value=None, step=None, enum=None, nice_name=None, keyable=None, k=None,
             lock=None, exportable=None):
    """ set value/desc wrapper """

    if not kl.is_plug(plug):
        raise TypeError('argument is not a valid plug')

    if value is not None:
        vector = None
        if plug.get_type() == V3f:
            vector = plug.get_input()

        if vector:
            vector = vector.get_node()
            vector.x.set_value(value.x)
            vector.y.set_value(value.y)
            vector.z.set_value(value.z)

        else:
            plug.set_value(value)

    _handle_plug_desc(plug, min_value, max_value, step, enum, nice_name, keyable, k, lock, exportable)


def get_next_available(plug):
    """
    Finds the next available slot in the given plug array for connecting.

    Args:
        plug (kl.Plug): Array plug

    Returns:
        int: The index of the next available slot. If all slots are in use,
        it ensures there is at least one more slot available and returns its index.
    """
    i = 0
    size = plug.get_size()

    while i < size and plug[i].is_connected():
        i += 1
    if i == size:
        plug.resize(i + 1)

    return i


# transform ------------------------------------------------------------------------------------------------------------

def copy_transform(src, dst, t=False, r=False, s=False):
    if not t and not r and not s:
        t = True
        r = True
        s = True

    if isinstance(src, kl.SceneGraphNode):
        xfo = src.world_transform.get_value()
    else:
        xfo = M44f()
        for _src in src:
            xfo += _src.world_transform.get_value() * (1. / len(src))

    t_src = xfo.translation()
    r_src = xfo.rotation(Euler.XYZ)
    s_src = xfo.scaling()

    xfo = dst.world_transform.get_value()
    t_dst = xfo.translation()
    r_dst = xfo.rotation(Euler.XYZ)
    s_dst = xfo.scaling()

    if t:
        t_dst = t_src
    if r:
        r_dst = r_src
    if s:
        s_dst = s_src

    dst.set_world_transform(M44f(t_dst, r_dst, s_dst, Euler.XYZ))
