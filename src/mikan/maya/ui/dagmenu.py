# coding: utf-8

import os
import sys
import inspect
import __main__
from functools import partial

import maya.OpenMaya as om1
import maya.api.OpenMaya as om
import maya.cmds as mc
import maya.mel as mel

from mikan.maya import cmdx as mx

from ..core.control import Control, Group
from ..core.asset import Asset
from ..lib.anim import *
from ..lib.rig import find_target
from .widgets import Callback

from mikan.core.logger import create_logger

log = create_logger()


class partialmethod(partial):
    def __get__(self, instance, owner):
        if instance is None:
            return self
        return partial(self.func, instance, *(self.args or ()), **(self.keywords or {}))


class DagMenu(object):
    loaded = False
    trigger = None
    services = [0, 0]

    callbacks = __main__.__dict__.setdefault(__name__ + '.registered_callbacks', {})

    def __init__(self, parent, node):
        DagMenu.cleanup()

        self.state = 1
        if str(node).split('|')[-1].startswith('msh_'):
            self.build_menu_layout(parent, node)

        if not isinstance(node, mx.Node):
            node = mx.encode(node)
        if 'gem_type' in node and node['gem_type'] == Control.type_name:
            self.build_menu_control(parent, node)
            return

        self.state = 0

        self.node = None
        self.ctrl = None
        self.groups = []
        self.vis_groups = set()
        self.all_groups = []

    def build_menu_control(self, parent, node):

        self.node = node
        self.ctrl = Control(node)
        self.groups = self.ctrl.get_groups()
        self.vis_groups = self.get_vis_groups()
        self.all_groups = self.get_all_groups()

        # build menu
        mc.setParent(parent, menu=1)
        mc.menuItem(str(node).split('|')[-1], bld=1)

        # show/hide groups
        if self.vis_groups:
            mc.menuItem(d=1)
            for group in self.vis_groups:
                label = 'HIDE'
                cmd = group.hide
                for c in group.get_all_nodes(vis=True):
                    if not c['v']:
                        label = 'SHOW'
                        cmd = group.show
                        break
                mc.menuItem(l=label + ' ' + group.nice_name, ec=1, c=Callback(cmd))

        # control groups standard functions
        mc.menuItem(d=1)

        # select
        mc.menuItem(l='select', subMenu=1)
        for group in self.all_groups:
            if not group:
                mc.menuItem(d=1)
                continue
            mc.menuItem(l=group.nice_name, ec=1, c=Callback(group.select))
        mc.setParent('..', menu=True)

        # set key
        mc.menuItem(l='set key', subMenu=1)
        for group in self.all_groups:
            if not group:
                mc.menuItem(d=1)
                continue
            mc.menuItem(l=group.nice_name, ec=1, c=Callback(group.set_key))
        mc.setParent('..', menu=True)

        # branches
        mc.menuItem(l='pose', subMenu=1)

        mc.menuItem(l='flip', subMenu=1)
        mc.menuItem(l=str(node), ec=1, c=Callback(DagMenu.mirror_control, self.ctrl, 0))
        mc.menuItem(l='selection', ec=1, c=Callback(DagMenu.mirror_selected, 0))
        mc.menuItem(d=1)
        for group in self.all_groups:
            if not group:
                mc.menuItem(d=1)
                continue
            mc.menuItem(l=group.nice_name, ec=1, c=Callback(DagMenu.mirror_group, group, 0))
        mc.setParent('..', menu=True)

        mc.menuItem(l='<mirror', subMenu=1)
        mc.menuItem(l=str(node), ec=1, c=Callback(DagMenu.mirror_control, self.ctrl, -1))
        mc.menuItem(l='selection', ec=1, c=Callback(DagMenu.mirror_selected, -1))
        mc.menuItem(d=1)
        for group in self.all_groups:
            if not group:
                mc.menuItem(d=1)
                continue
            mc.menuItem(l=group.nice_name, ec=1, c=Callback(DagMenu.mirror_group, group, -1))
        mc.setParent('..', menu=True)

        mc.menuItem(l='mirror>', subMenu=1)
        mc.menuItem(l=str(node), ec=1, c=Callback(DagMenu.mirror_control, self.ctrl, 1))
        mc.menuItem(l='selection', ec=1, c=Callback(DagMenu.mirror_selected, 1))
        mc.menuItem(d=1)
        for group in self.all_groups:
            if not group:
                mc.menuItem(d=1)
                continue
            mc.menuItem(l=group.nice_name, ec=1, c=Callback(DagMenu.mirror_group, group, 1))
        mc.setParent('..', menu=True)

        mc.setParent('..', menu=True)

        # get bind pose
        mc.menuItem('get bind pose', subMenu=1)
        mc.menuItem(l=str(node), ec=1, c=Callback(self.ctrl.get_bind_pose))
        mc.menuItem(l='selection', ec=1, c=Callback(DagMenu.get_bind_pose_selected))
        mc.menuItem(d=1)
        for group in self.all_groups:
            if not group:
                mc.menuItem(d=1)
                continue
            mc.menuItem(l=group.nice_name, ec=1, c=Callback(DagMenu.get_bind_pose_group, group))
        mc.setParent('..', menu=True)

        # daemons
        mc.menuItem(d=1)
        mc.menuItem('daemons', subMenu=1)
        self.build_layout_select_daemon()
        mc.setParent('..', menu=True)

        # switch random roll
        if 'menu_random' in node:
            menu = node['menu_random'].input()
            if menu:
                mc.menuItem(d=1)
                mc.menuItem(l='switches', ec=1, c=Callback(self.show_random, menu))

        # space switch
        for plug in ('ui_space_follow', 'ui_space_pin'):
            if plug in node:
                menu_node = node[plug].input()
                ctrls = mx.ls(str(node), mx.ls(sl=1))
                ctrls = list(set(ctrls))

                l = 'follow'
                p = 'NE'
                if plug.endswith('pin'):
                    l = 'pin'
                    p = 'SE'
                mc.menuItem(l=l, subMenu=1, rp=p)

                for i in menu_node['targets'].array_indices:
                    target = menu_node['targets'][i]['label'].read()

                    cbs = []
                    for c in ctrls:
                        if c == node:
                            cbs.append(Callback(anim_match_space, menu_node, i))

                        elif plug in c:
                            c_menu_node = c[plug].input()
                            if i in c_menu_node['targets'].array_indices and c_menu_node['targets'][i]['label'] == target:
                                cbs.append(Callback(anim_match_space, c_menu_node, i))

                    rp = ['NE', 'E', 'SE', 'S', 'SW', 'W', 'NW', 'N'][i]
                    mc.menuItem(l='{} {}'.format(l, target), rp=rp, echoCommand=1, c=partial(self.callback_list, cbs))

                mc.setParent('..', menu=True)

        # ik/fk switch
        if 'menu_match_ikfk' in node:
            menu_node = node['menu_match_ikfk'].input()
            ctrls = mx.ls(str(node), mx.ls(sl=1))
            ctrls = list(set(ctrls))

            switch = menu_node['switch'].input(plug=True)
            if switch.read() > 0:
                cmd = anim_match_FK
                l = 'go to FK'
                p = 'NW'
            else:
                cmd = anim_match_IK
                l = 'go to IK'
                p = 'SW'

            cbs = []
            for c in ctrls:
                if c == node:
                    cbs.append(Callback(cmd, menu_node))
                    continue

                if 'menu_match_ikfk' in c:
                    c_menu_node = c['menu_match_ikfk'].input()
                    cbs.append(Callback(cmd, c_menu_node))

            mc.menuItem(l=l, rp=p, ec=1, c=partial(self.callback_list, cbs))

    @staticmethod
    def load():
        # shadow maya dag menu
        DagMenu.shadow()

        # triggers
        if 'trigger' in DagMenu.callbacks:
            om.MMessage.removeCallback(DagMenu.callbacks['trigger'])
        DagMenu.callbacks['trigger'] = om.MEventMessage.addEventCallback('SelectionChanged', DagMenu.trigger_cb)

        # GUIs
        for gui in mx.ls('GUI', r=1):
            gui['v'] = False

        # hack graph editor display
        mc.outlinerEditor('graphEditor1OutlineEd', e=1, hir=1)

        # hack move tool options
        mc.manipMoveContext('Move', e=1, preserveChildPosition=0)
        mc.manipMoveContext('Move', e=1, oje=0)

    @staticmethod
    def reload():
        DagMenu.load()

    @staticmethod
    def cleanup():
        pass

    @staticmethod
    def shadow():

        # check if already loaded
        if 'interactively' in mel.eval('whatIs dagMenuProc;'):
            return

        # source original dag menu proc
        def _source():
            mel.eval('catchQuiet(buildObjectMenuItemsNow(""));')
            mel.eval('catchQuiet(dagMenuProc("", ""));')

        mc.evalDeferred(_source)

        # check paths
        mayapath, mayabin = os.path.split(sys.executable)
        path = mayapath.split(os.path.sep)[:-1] + ['scripts', 'others', 'dagMenuProc.mel']
        dagmenu_path = os.path.sep.join(path)

        # hack mel
        f = open(dagmenu_path, 'r')
        lines = f.readlines()
        f.close()

        idx = 0
        for line in lines:
            # > maya 2018
            if 'hasTraversalMM()' in line:
                idx = lines.index(line) - 1
            # < maya 2018
            elif 'global proc dagMenuProc' in line:
                idx = lines.index(line) + 2

        if not idx:
            raise RuntimeError('failed to generate dagMenuProc shadow')

        # inject
        try:
            lines.insert(idx, injection_code)
            dag_menu_proc = ''.join(lines)

            def _source():
                mel.eval(dag_menu_proc)

            mc.evalDeferred(_source)

        except:
            raise RuntimeError('failed to shadow dagMenuProc')

    @staticmethod
    def inject():
        try:
            DagMenu.load()
        except:
            log.error('/!\\ failed to load mikan dag menu')

    # callbacks --------------------------------------------------------------------------------------------------------

    @staticmethod
    def get_asset(node):
        p = node.parent()
        if p:
            if 'gem_type' in p and p['gem_type'] == Asset.type_name:
                return Asset(p)
            else:
                return DagMenu.get_asset(p)
        return None

    def get_vis_groups(self):
        vis_groups = []

        if 'menu_showhide' in self.node:
            _menu = self.node['menu_showhide']
            nodes = [_menu[i].input() for i in _menu.array_indices]
            for _node in nodes:
                vis_grp = Group(_node)
                if vis_grp not in vis_groups:
                    vis_groups.append(vis_grp)
        for group in self.groups:
            if 'gem_id' in group.node and '::vis.' in group.node['gem_id']:
                if group not in vis_groups:
                    vis_groups.append(group)
                    continue
            if 'menu_showhide' in group.node:
                _menu = group.node['menu_showhide']
                nodes = [_menu[i].input() for i in _menu.array_indices]
                for _node in nodes:
                    vis_grp = Group(_node)
                    if vis_grp not in vis_groups:
                        vis_groups.append(vis_grp)

        return vis_groups

    def get_all_groups(self):
        all_groups = []

        for group in self.groups:
            if group in self.vis_groups:
                continue
            if all_groups:
                all_groups.append(None)

            if group not in all_groups:
                all_groups.append(group)
            for group_parent in group.get_all_parents():
                if group_parent not in all_groups:
                    all_groups.append(group_parent)

        if self.vis_groups:
            all_groups.append(None)
        for group in self.vis_groups:
            if group not in all_groups:
                all_groups.append(group)

        return all_groups

    # command callbacks
    @staticmethod
    def get_bind_pose_selected():
        ctrls = []
        for node in mx.ls(sl=1):
            if 'gem_type' in node and node['gem_type'] == Control.type_name:
                ctrls.append(Control(node))

        for ctrl in ctrls:
            ctrl.get_bind_pose()

    @staticmethod
    def get_bind_pose_group(group):
        ctrls = group.get_all_members()

        for ctrl in ctrls:
            ctrl.get_bind_pose()

    @staticmethod
    def filter_mirror_control(ctrls, axis='x'):
        filtered = []
        reduced = []
        attr = 'mirror_{}s'.format(axis)

        for node in ctrls:
            if 'gem_type' not in node or node['gem_type'] != Control.type_name:
                continue
            if 'mirrors' not in node or attr not in node:
                reduced.append(Control(node))
                continue

            _m = node['mirrors']
            mirrors = dict([(_m[i].read(), _m[i].input()) for i in _m.array_indices])
            mirrors[node[attr].read()] = node
            if mirrors['+' + axis] not in filtered:
                reduced.append(Control(node))
                filtered.append(mirrors['+' + axis])

        return reduced

    @staticmethod
    def filter_mirror_cmds(cmds):
        cmds0 = []
        cmds1 = []
        for cmd in cmds:
            if '.ik' in cmd.args[0].path():
                cmds0.append(cmd)
            else:
                cmds1.append(cmd)
        return cmds0 + cmds1

    @staticmethod
    def mirror_control(ctrl, direction):
        for cmd in ctrl.get_mirror_cmds(direction):
            cmd()

    @staticmethod
    def mirror_selected(direction):
        cmds = []
        for ctrl in DagMenu.filter_mirror_control(mx.ls(sl=1)):
            cmds += ctrl.get_mirror_cmds(direction)

        for cmd in DagMenu.filter_mirror_cmds(cmds):
            cmd()

    @staticmethod
    def mirror_group(group, direction):
        cmds = []
        for ctrl in DagMenu.filter_mirror_control(group.get_all_nodes()):
            cmds += ctrl.get_mirror_cmds(direction)

        for cmd in DagMenu.filter_mirror_cmds(cmds):
            cmd()

    # callbacks
    @staticmethod
    def callback_list(cb_list, x):
        for cb in cb_list:
            cb()

    # triggers
    @staticmethod
    def trigger_cb(arg):
        pass

    # tools
    def show_random(self, node):
        from ..utils.pipeline.switch import SwitchRollUI  # avoid cyclic import

        roll = SwitchRollUI(node=node)
        roll.show()

    # -- layout toolbox --------------------------------------------------------

    def build_menu_layout(self, parent, node):
        # build menu
        mc.setParent(parent, menu=1)
        mc.menuItem('mikan daemons', bld=1)
        self.build_layout_select_daemon()
        mc.menuItem(d=1)

    def build_layout_select_daemon(self):
        lbl = 'select ctrl from msh'

        if 'layout_select' in DagMenu.callbacks:
            mc.menuItem(lbl, checkBox=True, c=Callback(DagMenu.layout_select_state, False))
        else:
            mc.menuItem(lbl, checkBox=False, c=Callback(DagMenu.layout_select_state, True))
            self.layout_lock_geo()

    @staticmethod
    def layout_select_state(state):
        if 'layout_select' in DagMenu.callbacks:
            om.MMessage.removeCallback(DagMenu.callbacks['layout_select'])
            del DagMenu.callbacks['layout_select']

        if state:
            DagMenu.layout_unlock_geo()
            DagMenu.callbacks['layout_select'] = om.MEventMessage.addEventCallback('SelectionChanged', DagMenu.layout_select_cb)
        else:
            DagMenu.layout_lock_geo()

    @staticmethod
    def layout_unlock_geo():
        for geo in mc.ls('geo', r=1):
            try:
                if mc.getAttr(geo + '.overrideEnabled'):
                    mc.setAttr(geo + '.overrideEnabled', False)
            except:
                pass

    @staticmethod
    def layout_lock_geo():
        for geo in mc.ls('geo', r=1):
            try:
                if not mc.getAttr(geo + '.overrideEnabled'):
                    mc.setAttr(geo + '.overrideEnabled', True)
            except:
                pass

    @staticmethod
    def layout_select_cb(arg):
        reselect = False

        nodes = []
        for node in mc.ls(sl=1):

            if node.split('|')[-1].split(':')[-1].startswith('msh_'):
                while node:
                    reselect = True
                    ctrl = find_target(node)
                    if ctrl:
                        nodes.append(str(ctrl))
                        break

                    _node = mc.listRelatives(node, pa=1, p=1)
                    if _node:
                        node = _node[0]
                    else:
                        break
            else:
                nodes.append(node)

        if reselect:
            mc.select(nodes)


injection_code = '''
if(attributeExists("gem_type", $object) || startsWith($object, "msh_")) {
  python("from mikan.maya.ui.dagmenu import DagMenu");
  int $mikan_menu = python("DagMenu(\\""+$parent+"\\",\\""+$object+"\\").state");
  if($mikan_menu) return;
}
'''
