# coding: utf-8

import yaml
from six.moves import range
from six import string_types, iteritems

import maya.api.OpenMayaAnim as oma
import maya.cmds as mc
from mikan.maya import cmdx as mx

from mikan.core.logger import create_logger, timed_code
from mikan.core.utils.typeutils import ordered_dict
from .configparser import ConfigParser
from .rig import list_future
from .connect import connect_driven_curve, find_anim_curve
from ..core.node import Nodes
from ..core.control import Control, Group
from ..core.template import Template
from ..core.asset import Helper
from ..core.deformer import Deformer

__all__ = [
    'get_ctrl_pose', 'get_group_pose', 'save_ctrl_pose', 'save_group_pose', 'get_driver_plug', 'get_driver_plugs',
    'clear_driver_pose', 'clear_plug_pose', 'recall_group_pose', 'mute_group_pose', 'bake_group_pose',
    'create_ctrl_cmd', 'create_group_cmd',
    'find_mod_node_by_data', 'get_anim_curve_data', 'export_driver_to_mod', 'export_plugs_to_mod',
    'clear_driver_mod'
]

log = create_logger('mikan.pose')


def get_ctrl_pose(c):
    if isinstance(c, Control):
        c = c.node
    elif not isinstance(c, mx.Node):
        c = mx.encode(str(c))

    if 'gem_id' not in c:
        return

    ids = c['gem_id'].read()
    for i in ids.split(';'):
        for key in ['::ctrls.', '::skin.']:
            if key in i:
                pid = i.replace(key, '::poses.')
                p = Nodes.get_id(pid)
                if p:
                    return p


def get_group_pose(grp):
    if not isinstance(grp, Group):
        try:
            grp = Group(grp)
        except:
            log.error('/!\\ {} is not valid Group'.format(grp))
            return

    poses = []
    for c in grp.get_all_members():
        p = get_ctrl_pose(c)
        if p:
            poses.append(p)

    return poses


def save_ctrl_pose(c, driver, force=None, decimals=4, wm=None, keys=None):
    if isinstance(c, Control):
        c = c.node
    elif not isinstance(c, mx.Node):
        c = mx.encode(str(c))

    if keys is None:
        keys = []
    if 0 in keys:
        keys.remove(0)

    pose = get_ctrl_pose(c)
    if not pose:
        return

    # get current xfo
    if wm is None:
        wm = c['wm'][0].as_transform()
    xfo = wm * pose['pim'][0].as_transform()

    x = dict()
    x['t'] = xfo.translation()
    r = xfo.rotation()
    ro = pose['ro'].read()
    if ro != 0:
        r = r.reorder(ro)
    x['r'] = r.asVector()
    x['s'] = xfo.scale()

    for chan in x:
        x[chan] = [round(_, decimals) for _ in x[chan]]

    # check current pose value ?
    _x = {}
    _x['t'] = pose['t'].read()
    _x['r'] = pose['r'].read()
    _x['s'] = pose['s'].read()
    for chan in _x:
        _x[chan] = [round(_, decimals) for _ in _x[chan]]

    # shunt driver
    if not isinstance(driver, mx.Plug):
        driver = mx.encode(str(driver))
    key = driver.read()
    if key == 0:
        raise RuntimeError('driving attribute is not set')

    driver_in = driver.input(plug=True)
    if isinstance(driver_in, mx.Plug):
        with mx.DGModifier() as md:
            md.disconnect(driver_in, driver)

    # save pose
    for chan in 'srt':
        for i, dim in enumerate('xyz'):
            plug = pose[chan + dim]
            v = x[chan][i]
            _v = _x[chan][i]

            if chan == 'r':
                v = mx.Radians(v).asDegrees()
                _v = mx.Radians(_v).asDegrees()

            anm = find_anim_curve(plug, driver)
            if anm:
                _v = mc.keyframe(str(anm), q=1, ev=1, f=(key,))

            v0 = 0
            if chan == 's':
                v0 = 1

            set_key = bool(force)
            if not (v == v0 and _v == v0) and v != _v:
                set_key = True
            if keys:
                if anm or v != v0:
                    set_key = True

            if set_key:
                log.debug('{}: {}'.format(plug.path(), v))
                if plug.input():
                    mc.mute(plug.path(), disable=True)

                pose_keys = {0: v0, key: v}

                if not anm:
                    for k in keys:
                        if k != key:
                            pose_keys[k] = v0

                connect_driven_curve(driver, plug, pose_keys)

    # reset ctrl
    for attr, v in zip('srt', (1, 0, 0)):
        for dim in 'xyz':
            try:
                with mx.DagModifier() as md:
                    md.set_attr(c[attr + dim], v)
            except:
                pass

    # reconnect driver if input
    if driver_in:
        with mx.DGModifier() as md:
            md.connect(driver_in[0], driver)


def save_plug_pose(plug, driver, force=None, decimals=4, keys=None, default=0):
    if not isinstance(plug, mx.Plug):
        plug = mx.encode(str(plug))

    if keys is None:
        keys = []
    if 0 in keys:
        keys.remove(0)

    # get current value
    v = round(plug.read(), decimals)
    _v = default

    # shunt driver
    if not isinstance(driver, mx.Plug):
        driver = mx.encode(str(driver))
    key = driver.read()
    if key == 0:
        raise RuntimeError('driving attribute is not set')

    driver_in = driver.input(plug=True)
    if isinstance(driver_in, mx.Plug):
        with mx.DGModifier() as md:
            md.disconnect(driver_in, driver)

    # save pose
    anm = find_anim_curve(plug, driver)
    if anm:
        _v = mc.keyframe(str(anm), q=1, ev=1, f=(key,))

    set_key = bool(force)
    if not (v == default and _v == default) and v != _v:
        set_key = True
    if keys:
        if anm or v != default:
            set_key = True

    if set_key:
        log.debug('{}: {}'.format(plug.path(), v))
        if plug.input():
            mc.mute(plug.path(), disable=True)

        pose_keys = {0: default, key: v}

        if not anm:
            for k in keys:
                if k != key:
                    pose_keys[k] = default

        connect_driven_curve(driver, plug, pose_keys)

    # reconnect driver if input
    if driver_in:
        with mx.DGModifier() as md:
            md.connect(driver_in[0], driver)


def save_group_pose(grp, driver, force=None, decimals=4):
    if not isinstance(grp, Group):
        try:
            grp = Group(grp)
        except:
            log.error('/!\\ {} is not valid Group'.format(grp))
            return

    # get controller poses
    ctrls = list(grp.get_all_members())

    wms = {}
    keys = []
    for c in ctrls:
        pose = get_ctrl_pose(c.node)
        if pose:
            for attr in 'srt':
                for dim in 'xyz':
                    plug = pose[attr + dim]
                    if not plug.input():
                        continue

                    # find keys already saved
                    anm = find_anim_curve(plug, driver)
                    if anm:
                        for k in mc.keyframe(str(anm), q=1, fc=1):
                            if k not in keys:
                                keys.append(k)

                    # mute connected plug
                    mc.mute(plug.path())

        wms[c.node] = c.node['wm'][0].as_transform()

    # find blendshape targets
    grp_name = grp.name
    pose_name = driver.name()
    targets = []

    cls = Deformer.get_class('blend')
    for plug in cls.get_all_group_target_plugs(grp_name):
        targets.append(plug)

        # find keys already saved
        anm = find_anim_curve(plug, driver)
        if anm:
            for k in mc.keyframe(str(anm), q=1, fc=1):
                if k not in keys:
                    keys.append(k)

        else:
            # auto save shape from name
            plug_info = cls.get_target_plug_info(plug)
            if plug_info['alias'] == pose_name:
                with mx.DGModifier() as md:
                    md.set_attr(plug, 1)

        # mute connected plug
        if plug.input() is not None:
            mc.mute(plug.path())

    # shunt rig
    cnx = driver.input(plug=True)
    if isinstance(cnx, mx.Plug):
        with mx.DGModifier() as md:
            md.disconnect(cnx, driver)

    # save controller edits
    for c in ctrls:
        save_ctrl_pose(c, driver, force, decimals, wm=wms[c.node], keys=keys)

    for c in ctrls:
        pose = get_ctrl_pose(c.node)
        if pose:
            for attr in 'srt':
                for dim in 'xyz':
                    plug = pose[attr + dim]
                    if plug.input() is not None:
                        mc.mute(plug.path(), disable=True)

    # save blendshape target edits
    for plug in targets:
        save_plug_pose(plug, driver, force, decimals, keys=keys)
        if plug.input():
            mc.mute(plug.path(), disable=True)

    # restore rig
    if isinstance(cnx, mx.Plug):
        with mx.DGModifier() as md:
            md.connect(cnx, driver)


def clear_driver_pose(driver, grp):
    for plug_name in mc.listAttr(str(driver), k=1, ud=1, c=1, s=1) or []:
        plug = driver[plug_name]
        if plug.read() != 0:
            clear_plug_pose(plug)

    mute_group_pose(grp, connected=False)


def clear_plug_pose(plug, keep_blendshape=False):
    # backup connection
    _i = plug.input(plug=True)
    if isinstance(_i, mx.Plug):
        with mx.DGModifier() as md:
            md.disconnect(_i, plug)

    # set plug to reset pose
    with mx.DGModifier() as md:
        md.set_attr(plug, 0)

    # cleanup loop
    for _o in plug.outputs():
        if _o.is_a((mx.kAnimCurve, mx.tMultDoubleLinear)):

            if keep_blendshape:
                skip = False
                for node in list_future(_o, max_depth=2):
                    if node.is_a(mx.tBlendShape):
                        skip = True
                        break
                if skip:
                    continue

            mx.delete(_o)

    # restore connection
    if isinstance(_i, mx.Plug):
        with mx.DGModifier() as md:
            md.connect(_i, plug)


def mute_group_pose(grp, connected=True):
    if not isinstance(grp, Group):
        try:
            grp = Group(grp)
        except:
            log.error('/!\\ {} is not valid Group'.format(grp))
            return

    for c in grp.get_all_members():
        pose = get_ctrl_pose(c)
        if not pose:
            continue
        for attr in ('tx', 'ty', 'tz', 'rx', 'ry', 'rz'):
            attr = pose[attr]
            if not connected and attr.input() is not None:
                continue
            if attr.editable:
                with mx.DagModifier() as md:
                    md.set_attr(attr, 0)
        for attr in ('sx', 'sy', 'sz'):
            attr = pose[attr]
            if not connected and attr.input() is not None:
                continue
            if attr.editable:
                with mx.DagModifier() as md:
                    md.set_attr(attr, 1)


def recall_group_pose(grp, driver, decimals=4):
    if not isinstance(grp, Group):
        try:
            grp = Group(grp)
        except:
            log.error('/!\\ {} is not valid Group'.format(grp))
            return

    sl = mc.ls(sl=1)

    ctrls = grp.get_all_members()
    poses = dict()

    for c in ctrls:
        pose = get_ctrl_pose(c)
        if pose:
            srt = {}
            poses[c] = srt
            for attr in ['tx', 'ty', 'tz', 'rx', 'ry', 'rz', 'sx', 'sy', 'sz']:
                srt[attr] = pose[attr].read()

    for plug_name in mc.listAttr(str(driver), k=1, ud=1, c=1, s=1) or []:
        plug = driver[plug_name]
        if plug.read() != 0:
            with mx.DagModifier() as md:
                md.set_attr(plug, 0)
            mc.dgdirty(str(driver))

    for c in ctrls:
        if c in poses:
            srt = poses[c]
            for attr, v in iteritems(srt):
                if not c.node[attr].editable:
                    continue
                with mx.DGModifier() as md:
                    md.set_attr(c.node[attr], round(v, decimals))

    mc.select(sl)


def bake_group_pose(grp, driver, decimals=4):
    if not isinstance(grp, Group):
        try:
            grp = Group(grp)
        except:
            log.error('/!\\ {} is not valid Group'.format(grp))
            return

    sl = mc.ls(sl=1)

    ctrls = grp.get_all_members()
    xfos = {}

    for c in ctrls:
        pose = get_ctrl_pose(c)
        if pose:
            xfos[c.node] = c.node['wm'][0].as_matrix() * pose['pim'][0].as_matrix()

    for plug_name in mc.listAttr(str(driver), k=1, ud=1, c=1, s=1) or []:
        plug = driver[plug_name]
        if plug.read() != 0:
            with mx.DagModifier() as md:
                md.set_attr(plug, 0)
            mc.dgdirty(str(driver))

    for node in xfos:
        mc.xform(str(node), m=xfos[node])

    mc.select(sl)


def create_ctrl_cmd(c, decimals=4):
    if isinstance(c, Control):
        c = c.node
    elif not isinstance(c, mx.Node):
        c = mx.encode(str(c))

    p = get_ctrl_pose(c)
    if not p:
        return ''

    c_id = Nodes.get_node_id(c)
    if not c_id:
        return ''

    cmd = 'plug:\n'
    cmd += '  node: {}\n'.format(c_id)

    for srt in 'trs':
        for dim in 'xyz':
            plug = c[srt + dim]
            unit = None
            if srt == 'r':
                unit = mx.Degrees
            cmd += '  {}.{}: {{set: {}}}\n'.format(srt, dim, round(plug.read(unit=unit), decimals))

    return cmd


def create_group_cmd(grp, decimals=4):
    if not isinstance(grp, Group):
        try:
            grp = Group(grp)
        except:
            log.error('/!\\ {} is not valid Group'.format(grp))
            return

    cmd = ''
    for c in grp.get_all_members():
        cmd += create_ctrl_cmd(c, decimals=decimals)

    return cmd


def get_driver_plug(driver):
    '''
    return the only plug set of the given driver
    :param driver: node
    :return: pm.Attribute
    '''

    if not isinstance(driver, mx.Plug):
        d = None
        for plug_name in mc.listAttr(str(driver), k=1, ud=1, c=1, s=1) or []:
            plug = driver[plug_name]
            if plug.read() != 0:
                if d is not None:
                    log.error('driver is not properly set, {} and {} have values'.format(d.path(), plug.path()))
                    return
                d = plug
        if d is not None:
            return d
    else:
        return driver


def get_driver_plugs(driver):
    if not isinstance(driver, mx.Node):
        driver = mx.encode(str(driver))

    plugs = []
    for plug_name in mc.listAttr(str(driver), k=1, ud=1, c=1, s=1) or []:
        plug = driver[plug_name]
        if plug.read() != 0:
            plugs.append(plug)

    return plugs


def find_mod_node_by_data(mod_type, find_data):
    for node in mx.ls('*.notes', o=1, r=1, type='transform'):
        data = node['notes'].read()
        if not isinstance(data, string_types) or '[mod]' not in data:
            continue
        lines = data.splitlines()
        lines.append('-')
        if '{}:'.format(mod_type) not in lines:
            continue

        start, sep, end = data.partition(find_data)
        if not sep:
            continue

        graph = Helper(node)
        if graph.disabled():
            continue

        return node


def get_anim_curve_data(anm, do_scale=0):
    if not isinstance(anm, mx.Node):
        anm = mx.encode(str(anm))
    fn = oma.MFnAnimCurve(anm.object())

    a = dict()
    _pre = fn.preInfinityType
    _post = fn.postInfinityType

    infinities = {
        fn.kConstant: 'constant',
        fn.kLinear: 'linear',
        fn.kCycle: 'cycle',
        fn.kCycleRelative: 'offset',
        fn.kOscillate: 'oscillate'
    }

    if _pre != fn.kLinear:
        a['pre'] = infinities[_pre]
    if _post != fn.kLinear:
        a['post'] = infinities[_post]

    _anm = str(anm)
    fc = mc.keyframe(_anm, q=1, fc=1)
    vc = mc.keyframe(_anm, q=1, vc=1)
    if vc and not fc:
        fc = mc.keyframe(_anm, q=1, tc=1)
    itm = mc.keyTangent(_anm, q=1, itt=1)
    otm = mc.keyTangent(_anm, q=1, ott=1)

    w = anm['wgt'].read()
    if not w:
        mc.keyTangent(_anm, e=1, wt=1)
    ix = mc.keyTangent(_anm, q=1, ix=1)
    iy = mc.keyTangent(_anm, q=1, iy=1)
    ox = mc.keyTangent(_anm, q=1, ox=1)
    oy = mc.keyTangent(_anm, q=1, oy=1)
    if anm.is_a((mx.tAnimCurveUA, mx.tAnimCurveTA)):
        iy = [mx.Radians(r).asDegrees() for r in iy]
        oy = [mx.Radians(r).asDegrees() for r in oy]

    if not w:
        mc.keyTangent(_anm, e=1, wt=w)

    for i, f in enumerate(fc):
        _a = dict()
        a[f] = _a
        _a['v'] = round(vc[i] + do_scale, 5)

        if itm[i] == otm[i]:
            if itm[i] not in ('spline', 'fixed'):
                _a['tan'] = str(itm[i])
        else:
            if itm[i] not in ('spline', 'fixed'):
                _a['itan'] = str(itm[i])
            if otm[i] not in ('spline', 'fixed'):
                _a['otan'] = str(otm[i])

        if itm[i] == 'fixed':
            _a['ix'] = round(ix[i] / 3, 6) * -1
            _a['iy'] = round(iy[i] / 3, 6) * -1
        if otm[i] == 'fixed':
            _a['ox'] = round(ox[i] / 3, 6)
            _a['oy'] = round(oy[i] / 3, 6)

        if len(_a) == 1:
            a[f] = _a['v']

    return a


def export_driver_to_mod(driver, group, plugs=None):
    if not isinstance(driver, mx.Node):
        driver = mx.encode(str(driver))
    if not isinstance(group, Group):
        group = Group(group)
    if not plugs:
        plugs = []

    filter_plugs = set()
    if not isinstance(plugs, (list, tuple)):
        plugs = [plugs]
    for plug in plugs:
        if isinstance(plug, mx.Plug):
            filter_plugs.add(plug.name(long=False))
        else:
            filter_plugs.add(str(plug))

    driver_template = Template.get_from_node(driver).node

    # find all anim curves from driver
    anm_data = ordered_dict()

    # -- pose anim curves
    poses = get_group_pose(group)
    for n in poses:
        _anm = {}

        for attr in 'srt':
            for dim in 'xyz':
                cvs = find_anim_curve(n[attr + dim])
                if cvs:
                    _anm[attr + '.' + dim] = cvs

        for attr in mc.listAttr(str(n), ud=1, k=1, s=1) or []:
            cvs = find_anim_curve(n[attr])
            if cvs:
                _anm[attr] = cvs

        if _anm:
            anm_data[n] = _anm

    # -- blendshape anim curves
    grp_name = group.name

    cls = Deformer.get_class('blend')
    for plug in cls.get_all_group_target_plugs(grp_name):

        plug_data = cls.get_target_plug_info(plug)
        target_name = plug_data['alias']

        cvs = find_anim_curve(plug)
        if not cvs and target_name in driver:  # link auto
            cv = connect_driven_curve(driver[target_name], plug, {0.0: 0.0, 1.0: 1.0})
            cvs = [cv]

        bs = plug.node()
        if bs not in anm_data:
            anm_data[bs] = {}

        anm_data[bs]['weight.{}'.format(target_name)] = cvs

    # filter and extract anim curve data
    data = ordered_dict()
    for n in anm_data:
        for driven_plug, anms in iteritems(anm_data[n]):

            for anm in anms:
                driver_plug = anm['input'].input(plug=True)
                if driver_plug is None or driver_plug.node() != driver:
                    continue

                driver_plug = driver_plug.name(long=False)
                if filter_plugs and driver_plug not in filter_plugs:
                    continue

                if driver_plug not in data:
                    data[driver_plug] = {}

                _data = data[driver_plug]

                if n not in _data:
                    _data[n] = {}
                _data[n][driven_plug] = anm

    # write shape loop
    for driver_plug, _data in iteritems(data):

        find_cmd = []
        _cmd = '  node: {}\n'.format(Nodes.get_node_id(driver))
        _cmd += '  plug: {}\n'.format(driver_plug)
        find_cmd.append(_cmd)
        _cmd = '  node: {}@{}\n'.format(Nodes.get_node_id(driver), driver_plug)
        find_cmd.append(_cmd)

        cmd_mod = 'drive:\n'
        cmd_mod += _cmd
        cmd_pose = ''
        cmd_bs = ''

        mod_node = None
        for _cmd in find_cmd:
            mod_node = find_mod_node_by_data('drive', _cmd)
            if mod_node:
                break

        for driven, driven_plugs in iteritems(_data):

            if driven.is_a(mx.tBlendShape):
                # driven blendshape targets
                shp = mc.blendShape(str(driven), q=1, g=1)
                geo = mx.encode(shp[0]).parent()
                dfm = Deformer.create(geo, driven, read=False)
                driven_id = dfm.get_id()

                for plug, anm in iteritems(driven_plugs):
                    cmd_bs += '  {}@{}: '.format(driven_id, plug)

                    a = get_anim_curve_data(anm)

                    cmd_bs += yaml.dump(a, default_flow_style=True).strip('\n') + '\n'

            else:
                # driven poses
                driven_id = Nodes.get_node_id(driven)

                cmd_pose += '  {}:\n'.format(driven_id)
                for plug, anm in iteritems(driven_plugs):
                    cmd_pose += '    {}: '.format(plug)

                    do_scale = 0
                    if len(plug) == 3 and '.' in plug and plug[0] == 's':
                        do_scale = 1
                    a = get_anim_curve_data(anm, do_scale=do_scale)

                    cmd_pose += yaml.dump(a, default_flow_style=True).strip('\n') + '\n'

        # build notes
        new_notes = ''
        if cmd_pose:
            new_notes += cmd_mod + cmd_pose
        if cmd_bs:
            if new_notes:
                new_notes += '\n'
            cmd_bs += '#!-10\n'
            new_notes += cmd_mod + cmd_bs

        # update existing mod?
        if mod_node:

            # disable referenced mod if unchanged
            if mod_node.is_referenced():
                old_notes = mod_node['notes'].read()
                _new_notes = '[mod]\n' + new_notes

                if old_notes != _new_notes:
                    Helper(mod_node).set_enable(False)
                    mod_node = None

            # update notes
            else:
                with mx.DGModifier() as md:
                    md.set_attr(mod_node['notes'], '[mod]\n' + new_notes)

                if 'gem_scale' in mod_node:
                    try:
                        with mx.DGModifier() as md:
                            md.set_attr(mod_node['gem_scale'], 1)
                            md.delete_attr(mod_node['gem_scale'])
                    except:
                        pass

        # create new mod node
        if not mod_node:
            with mx.DagModifier() as md:
                mod_node = md.create_node(mx.tTransform, parent=driver_template, name='_pose_{}'.format(driver_plug))
            ConfigParser(mod_node)['mod'].write(new_notes)


def clear_driver_mod(driver, plugs=None):
    if not plugs:
        return
    if not isinstance(driver, mx.Node):
        driver = mx.encode(str(driver))

    filter_plugs = set()
    if not isinstance(plugs, (list, tuple)):
        plugs = [plugs]
    for plug in plugs:
        if isinstance(plug, mx.Plug):
            filter_plugs.add(plug.name(long=False))
        else:
            filter_plugs.add(str(plug))

    driver_template = Template.get_from_node(driver).node

    # search loop
    for plug_name in filter_plugs:

        find_cmd = []
        _cmd = '  node: {}\n'.format(Nodes.get_node_id(driver))
        _cmd += '  plug: {}\n'.format(plug_name)
        find_cmd.append(_cmd)
        _cmd = '  node: {}@{}\n'.format(Nodes.get_node_id(driver), plug_name)
        find_cmd.append(_cmd)

        mod_node = None
        for _cmd in find_cmd:
            mod_node = find_mod_node_by_data('drive', _cmd)
            if mod_node:
                break

        if mod_node and mod_node.parent() == driver_template:
            mx.delete(mod_node)


def export_plugs_to_mod(node):
    if not isinstance(node, mx.Node):
        node = mx.encode(str(node))

    node_template = Template.get_from_node(node).node
    cfg = ConfigParser(node_template)
    for ini in cfg['mod']:
        data = ini.get_lines()
        if '# mikan plug export' in data:
            break
    else:
        cfg['mod'].write('')
        ini = cfg['mod'][0]

    cmd = '# mikan plug export\n\n'
    cmd += 'plug:\n'
    cmd += '  node: {}\n'.format(Nodes.get_node_id(node))

    plug_names = mc.listAttr(str(node), ud=1, k=1) or []
    for plug_name in plug_names:
        plug = node[plug_name]
        if plug.locked or not plug.keyable:
            continue

        plug_types = {
            mx.Double: 'float',
            mx.Float: 'float',
            mx.Long: 'int',
            mx.Boolean: 'bool',
            mx.Enum: 'enum'
        }
        at = plug_types[plug.type_class()]
        cmd += '  {}: {{type: {}, k: on}}\n'.format(plug.name(long=False), at)

    ini.write(cmd)
