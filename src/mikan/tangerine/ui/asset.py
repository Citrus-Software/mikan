# coding: utf-8

import os
import yaml
import inspect
import traceback
from functools import partial

from PySide2 import QtGui, QtWidgets
from PySide2.QtCore import Qt

import meta_nodal_py as kl
from tang_core import profile as cp
from tang_core.callbacks import Callbacks
from tang_core.selection import modifiers_to_selection_mode
from tang_core.monitoring import Monitoring
from tang_core.anim import set_animated_plug_value, get_key_if_any, get_animated_target
from tang_core.logger import info, warning
from tang_gui.tang_action import add_action, TangAction

from mikan.core.ui.widgets import *
from mikan.core.utils import ordered_load
from mikan.core.logger import create_logger, get_version
from mikan.core.prefs import Prefs
from mikan.tangerine.core import Asset, Control, Group
from mikan.tangerine.core.control import cached_groups
from mikan.tangerine.lib.commands import *
from mikan.tangerine.lib.anim import *
from mikan.tangerine.lib import dynamic, find_target

log = create_logger()

version = get_version()
Monitoring.add_extra('mikan_version', version)
info(f"Mikan {version}")


class TangMikanActions:
    FLIP_SELECTED_ACTION = None
    MIRROR_LEFT_SELECTED_ACTION = None
    MIRROR_RIGHT_SELECTED_ACTION = None
    FLIP_SELECTED_ANIM_ACTION = None
    MIRROR_LEFT_SELECTED_ANIM_ACTION = None
    MIRROR_RIGHT_SELECTED_ANIM_ACTION = None
    BIND_POSE_SELECTED_ACTION = None

    @staticmethod
    def set_up_tang_actions():
        if TangMikanActions.FLIP_SELECTED_ACTION:
            return None

        def _mirror_selected(direction):
            AssetMenu.mirror_selected_with_doc(direction, QtWidgets.QApplication.instance().document())

        def _mirror_selected_anim(direction):
            AssetMenu.mirror_selected_anim_with_doc(direction, QtWidgets.QApplication.instance().document())

        def _get_bind_pose_selection():
            AssetMenu.get_bind_pose_selection_with_doc(QtWidgets.QApplication.instance().document())

        def _pickwalk(x, y):
            AssetMenu.pickwalk_with_doc(x, y, QtWidgets.QApplication.instance().document())

        def _select_mirror():
            AssetMenu.select_mirror_with_doc(QtWidgets.QApplication.instance().document())

        app = QtWidgets.QApplication.instance()
        if app.main_window is not None:
            doc = app.document()
            manager = doc.shortcuts_manager
            manager.start_register_block()
            TangMikanActions.FLIP_SELECTED_ACTION = add_action(app.main_window, 'Rig:Flip:Selected', partial(_mirror_selected, 0), shortcut="Tab")
            TangMikanActions.MIRROR_LEFT_SELECTED_ACTION = add_action(app.main_window, 'Rig:< Mirror:Selected', partial(_mirror_selected, -1), shortcut="Shift+Tab")
            TangMikanActions.MIRROR_RIGHT_SELECTED_ACTION = add_action(app.main_window, 'Rig:Mirror >:Selected', partial(_mirror_selected, 1), shortcut="Ctrl+Tab")
            TangMikanActions.BIND_POSE_SELECTED_ACTION = add_action(app.main_window, 'Rig:Get Bind Pose:Selected', _get_bind_pose_selection)
            TangMikanActions.FLIP_SELECTED_ANIM_ACTION = add_action(app.main_window, 'Rig:Flip:Selected Anim', partial(_mirror_selected_anim, 0))
            TangMikanActions.MIRROR_LEFT_SELECTED_ANIM_ACTION = add_action(app.main_window, 'Rig:< Mirror:Selected Anim', partial(_mirror_selected_anim, -1))
            TangMikanActions.MIRROR_RIGHT_SELECTED_ANIM_ACTION = add_action(app.main_window, 'Rig:Mirror >:Selected Anim', partial(_mirror_selected_anim, 1))
            add_action(app.main_window, 'Rig:Pickwalk Up', partial(_pickwalk, 0, -1), shortcut='Ctrl+Alt+Up')
            add_action(app.main_window, 'Rig:Pickwalk Down', partial(_pickwalk, 0, 1), shortcut='Ctrl+Alt+Down')
            add_action(app.main_window, 'Rig:Pickwalk Left', partial(_pickwalk, -1, 0), shortcut='Ctrl+Alt+Left')
            add_action(app.main_window, 'Rig:Pickwalk Right', partial(_pickwalk, 1, 0), shortcut='Ctrl+Alt+Right')
            add_action(app.main_window, 'Rig:Select Mirror (Replace)', _select_mirror, shortcut='<')
            add_action(app.main_window, 'Rig:Select Mirror (Add)', _select_mirror, shortcut='Ctrl+Shift+<')
            add_action(app.main_window, 'Rig:Select Mirror (Invert)', _select_mirror, shortcut='Shift+<')
            add_action(app.main_window, 'Rig:Select Mirror (Subtract)', _select_mirror, shortcut='Ctrl+<')
            manager.end_register_block()


TangMikanActions.set_up_tang_actions()


def _right_click_menu(document, menu, viewport):
    try:
        if right_click_menu(document, menu, viewport):
            menu.addSeparator()
    except ImportError:
        pass


def _get_all_controllers_in_asset(asset_node):
    try:
        grp_all_node = asset_node.gem_group.get_input().get_node()
    except AttributeError:
        return list()  # not an asset node
    grp_all_group = Group(grp_all_node)
    return grp_all_group.get_all_nodes(cache=True)


_asset_node_cache = {}


def _find_asset_cache(asset_node):
    cache = _asset_node_cache.get(asset_node)
    if not cache:
        cache = ls(as_dict=True, root=asset_node, shortest=False)
        _asset_node_cache[asset_node] = cache
    return cache


def _find_controller_in_asset(asset_node, controller_key):
    # must be bijective with _get_controller_key
    cache = _find_asset_cache(asset_node)
    return cache.get(controller_key)


def _get_controller_key(asset_node, controller):
    # must be bijective with _find_controller_in_asset
    return controller.get_name()


def _before_unload_document(document):
    global _asset_node_cache
    _asset_node_cache = {}  # release node references before doc clean

    for d in cached_groups:
        d.clear()


def _before_unload_asset(document, asset_node):
    global _asset_node_cache
    if asset_node in _asset_node_cache:
        del _asset_node_cache[asset_node]

    for d in cached_groups:
        d.clear()


def _get_asset_node(document, node):
    asset_node = document.root().get_top_node(node)
    return asset_node if _is_asset_node(document, asset_node) else None


def _is_asset_node(document, node):
    try:
        return node.gem_type.get_value() == "asset"
    except AttributeError:
        return False


class AssetCallbacks:
    # for right-click menu
    function_dict = dict()
    ctrl_function_dict = dict()
    ctrl_sets_function_dict = dict()

    # hack callbacks
    cb = Callbacks()
    cb.viewport_context_menu = _right_click_menu
    cb.get_all_controllers_in_asset = _get_all_controllers_in_asset
    cb.find_controller_in_asset = _find_controller_in_asset
    cb.get_controller_key = _get_controller_key
    cb.before_unload_document = _before_unload_document
    cb.before_unload_asset = _before_unload_asset
    cb.get_asset_node = _get_asset_node
    cb.is_asset_node = _is_asset_node
    try:
        cb.after_load_asset = dynamic.after_load_asset
    except AttributeError:
        pass  # Tangerine too old


def right_click_menu(doc, menu, active_viewport):
    asset_menu = AssetMenu(doc, menu, active_viewport)
    return not asset_menu.empty


def get_tangents(plug, inv, src_plug, frame, layer_name):
    if src_plug is None:
        key = None
        warning("No source plug found for plug: " + plug.get_full_name())
    else:
        key = get_key_if_any(src_plug, frame, layer_name)

    if key is not None:
        if inv:
            # mirror key custom tangents
            if key.left_tangent_mode == kl.TangentMode.custom:
                left = key.get_left_tangent()
                key.set_left_tangent(kl.Imath.V2f(left.x, -left.y))
            if key.right_tangent_mode == kl.TangentMode.custom:
                right = key.get_right_tangent()
                key.set_right_tangent(kl.Imath.V2f(right.x, -right.y))

    return key


class AssetMenu:

    def __init__(self, doc, menu, active_viewport):
        self.doc = doc

        self.empty = True

        self.node = None
        self.asset = None

        # check selection
        self.selection = doc.node_selection()
        if not self.selection.empty():
            self.node = self.selection[0]

        # check hover?
        hover = active_viewport.hovered_geometry()
        if isinstance(hover, kl.SplineCurve):
            self.node = hover.get_parent()

        active_viewport.makeCurrent()
        pos = active_viewport.mapFromGlobal(QtGui.QCursor.pos())
        x, y = pos.x(), pos.y()
        node = active_viewport.get_node(x, y, only_pickable=False)

        if isinstance(node, kl.Geometry):
            ctrl = None

            geo = node.get_parent()
            while isinstance(geo, kl.SceneGraphNode):
                if Control(geo):
                    break

                target = find_target(geo)
                if target and Control(target):
                    ctrl = target
                    break

                geo = geo.get_parent()

            if ctrl:
                # build mesh menu
                menu.addSeparator()
                menu.setStyleSheet('#ctrl{font-weight: bold; color: lightblue; margin: 2px;}')

                a = QtWidgets.QWidgetAction(menu)
                l = QtWidgets.QLabel(geo.get_name())
                l.setObjectName('ctrl')
                l.setAlignment(Qt.AlignCenter)
                a.setDefaultWidget(l)
                menu.addAction(a)

                _action = QtWidgets.QAction('Select control', menu)
                _action.triggered.connect(partial(self.select_node, ctrl))
                menu.addAction(_action)
                return

        if not self.node:
            return

        self.ctrl = Control(self.node)
        if not self.ctrl:
            return
        ctrl_full_name = self.ctrl.node.get_full_name()

        # get groups from controller
        self.groups = self.ctrl.get_groups()
        self.vis_groups = self.get_vis_groups()
        self.all_groups = self.get_all_groups()

        # build menu
        menu.addSeparator()
        menu.setStyleSheet('#ctrl{font-weight: bold; color: lightblue; margin: 2px;}')

        a = QtWidgets.QWidgetAction(menu)
        l = QtWidgets.QLabel(self.node.get_name())
        l.setObjectName('ctrl')
        l.setAlignment(Qt.AlignCenter)
        a.setDefaultWidget(l)
        menu.addAction(a)

        enable_last_qaction_repeat = TangAction.enable_last_qaction_repeat

        # show/hide menu
        if self.vis_groups:
            menu.addSeparator()
            for group in self.vis_groups:
                label = 'HIDE'
                state = False
                for c in group.get_all_nodes(vis=True, cache=True):
                    if not c.show.get_value(self.doc.current_frame):
                        label = 'SHOW'
                        state = True
                        break

                _action = QtWidgets.QAction(label + ' ' + group.nice_name, menu)
                _action.triggered.connect(partial(self.vis_group, group, state))
                menu.addAction(_action)

        # select menu
        menu.addSeparator()

        _menu = menu.addMenu('Select')

        _action = QtWidgets.QAction('Mirror', _menu)
        _action.triggered.connect(self.select_mirror)
        _menu.addAction(_action)

        for group in self.all_groups:
            if not group:
                _menu.addSeparator()
                continue
            _action = QtWidgets.QAction(group.nice_name, _menu)
            _action.triggered.connect(partial(self.select_group, group))
            _menu.addAction(_action)

        # Pose menu
        _menu = menu.addMenu('Pose')

        _submenu = _menu.addMenu("Flip")

        _action = QtWidgets.QAction(self.node.get_name(), _submenu)
        _action.triggered.connect(partial(self.mirror_control, self.ctrl, 0))
        _submenu.addAction(_action)

        _action = QtWidgets.QAction('Selected', _submenu)
        # create new action to have different name but dispatch to TangAction to be last repeatable
        _action.triggered.connect(TangMikanActions.FLIP_SELECTED_ACTION.triggered)
        _submenu.addAction(_action)

        _submenu.addSeparator()

        for group in self.all_groups:
            if not group:
                _submenu.addSeparator()
                continue
            group_full_name = group.node.get_full_name()
            _action = _submenu.addAction(group.nice_name)
            trigger = partial(self.mirror_group, group_full_name, 0)
            _action.triggered.connect(trigger)
            enable_last_qaction_repeat(_action, trigger)

        #
        _submenu = _menu.addMenu("< Mirror")

        _action = QtWidgets.QAction(self.node.get_name(), _submenu)
        _action.triggered.connect(partial(self.mirror_control, self.ctrl, -1))
        _submenu.addAction(_action)

        _action = QtWidgets.QAction('Selected', _submenu)
        _action.triggered.connect(TangMikanActions.MIRROR_LEFT_SELECTED_ACTION.triggered)
        _submenu.addAction(_action)

        _submenu.addSeparator()

        for group in self.all_groups:
            if not group:
                _submenu.addSeparator()
                continue
            _action = QtWidgets.QAction(group.nice_name, _submenu)
            _action.triggered.connect(partial(self.mirror_group, group, -1))
            _submenu.addAction(_action)

        #
        _submenu = _menu.addMenu("Mirror >")

        _action = QtWidgets.QAction(self.node.get_name(), _submenu)
        _action.triggered.connect(partial(self.mirror_control, self.ctrl, 1))
        _submenu.addAction(_action)

        _action = QtWidgets.QAction('Selected', _submenu)
        _action.triggered.connect(TangMikanActions.MIRROR_RIGHT_SELECTED_ACTION.triggered)
        _submenu.addAction(_action)

        _submenu.addSeparator()

        for group in self.all_groups:
            if not group:
                _submenu.addSeparator()
                continue
            _action = QtWidgets.QAction(group.nice_name, _submenu)
            _action.triggered.connect(partial(self.mirror_group, group, 1))
            _submenu.addAction(_action)

        # Anim Menu
        _menu = menu.addMenu('Anim')

        _submenu = _menu.addMenu("Flip")

        _action = _submenu.addAction(self.node.get_name())
        trigger = partial(self.mirror_control_anim, ctrl_full_name, 0)
        _action.triggered.connect(trigger)
        enable_last_qaction_repeat(_action, trigger)

        _action = QtWidgets.QAction('Selected', _submenu)
        _action.triggered.connect(TangMikanActions.FLIP_SELECTED_ANIM_ACTION.triggered)
        _submenu.addAction(_action)

        _submenu.addSeparator()

        for group in self.all_groups:
            if not group:
                _submenu.addSeparator()
                continue
            group_full_name = group.node.get_full_name()
            _action = _submenu.addAction(group.nice_name)
            trigger = partial(self.mirror_group_anim, group_full_name, 0)
            _action.triggered.connect(trigger)
            enable_last_qaction_repeat(_action, trigger)

        #
        _submenu = _menu.addMenu("< Mirror")

        _action = _submenu.addAction(self.node.get_name())
        trigger = partial(self.mirror_control_anim, ctrl_full_name, -1)
        _action.triggered.connect(trigger)
        enable_last_qaction_repeat(_action, trigger)

        _action = QtWidgets.QAction('Selected', _submenu)
        _action.triggered.connect(TangMikanActions.MIRROR_LEFT_SELECTED_ANIM_ACTION.triggered)
        _submenu.addAction(_action)

        _submenu.addSeparator()

        for group in self.all_groups:
            if not group:
                _submenu.addSeparator()
                continue
            group_full_name = group.node.get_full_name()
            _action = _submenu.addAction(group.nice_name)
            trigger = partial(self.mirror_group_anim, group_full_name, -1)
            _action.triggered.connect(trigger)
            enable_last_qaction_repeat(_action, trigger)

        #
        _submenu = _menu.addMenu("Mirror >")

        _action = _submenu.addAction(self.node.get_name())
        trigger = partial(self.mirror_control_anim, ctrl_full_name, 1)
        _action.triggered.connect(trigger)
        enable_last_qaction_repeat(_action, trigger)

        _action = QtWidgets.QAction('Selected', _submenu)
        _action.triggered.connect(TangMikanActions.MIRROR_RIGHT_SELECTED_ANIM_ACTION.triggered)
        _submenu.addAction(_action)

        _submenu.addSeparator()

        for group in self.all_groups:
            if not group:
                _submenu.addSeparator()
                continue
            group_full_name = group.node.get_full_name()
            _action = _submenu.addAction(group.nice_name)
            trigger = partial(self.mirror_group_anim, group_full_name, 1)
            _action.triggered.connect(trigger)
            enable_last_qaction_repeat(_action, trigger)

        # bind pose menu
        _menu = menu.addMenu('Get bind pose')

        _action = QtWidgets.QAction(self.node.get_name(), _menu)
        _action.triggered.connect(partial(self.get_bind_pose_control, self.ctrl))
        _menu.addAction(_action)

        _action = QtWidgets.QAction('Selected', _menu)
        _action.triggered.connect(TangMikanActions.BIND_POSE_SELECTED_ACTION.triggered)
        _menu.addAction(_action)

        _menu.addSeparator()

        for group in self.all_groups:
            if not group:
                _menu.addSeparator()
                continue
            _action = QtWidgets.QAction(group.nice_name, _menu)
            _action.triggered.connect(partial(self.get_bind_pose_group, group))
            _menu.addAction(_action)

        # space match menu
        for plug_name in ('ui_space_follow', 'ui_space_pin', 'ui_match_ikfk'):
            if self.ctrl.node.get_dynamic_plug(plug_name):
                menu.addSeparator()
                break

        for plug_name in ('ui_space_follow', 'ui_space_pin'):
            if self.node.get_dynamic_plug(plug_name):
                menu_node = self.node.get_dynamic_plug(plug_name).get_input().get_node()
                menu_node_full_name = menu_node.get_full_name()

                label = 'Follow'
                if plug_name.endswith('pin'):
                    label = 'Pin'
                _menu = menu.addMenu(label)

                for i in range(menu_node.targets.get_value()):
                    target = menu_node.get_dynamic_plug('label{}'.format(i)).get_value()
                    _action = _menu.addAction(label + ' ' + target)
                    # use with_full_name to avoid holding ref on node, because repeat keep trigger alive
                    trigger = partial(anim_match_space, menu_node_full_name, i)
                    _action.triggered.connect(trigger)
                    enable_last_qaction_repeat(_action, trigger)

        # ik/fk match menu
        if self.node.get_dynamic_plug('ui_match_ikfk'):
            menu_node = self.node.get_dynamic_plug('ui_match_ikfk').get_input().get_node()
            menu_node_full_name = menu_node.get_full_name()

            switch = menu_node.switch.get_input()
            if switch.get_value(self.doc.current_frame):
                cmd = anim_match_FK  # use with_full_name to avoid holding ref on node
                label = 'Go to FK'
            else:
                cmd = anim_match_IK  # use with_full_name to avoid holding ref on node
                label = 'Go to IK'

            _action = menu.addAction(label)
            trigger = partial(cmd, menu_node_full_name)
            _action.triggered.connect(trigger)
            enable_last_qaction_repeat(_action, trigger)

        # Bake Dynamics
        dynamic_controllers = dynamic.filter_dynamic_controllers(self.selection)
        if dynamic_controllers:
            _action = menu.addAction('Bake Dynamics')
            _action.triggered.connect(partial(dynamic.bake_dynamic_controllers, dynamic_controllers, doc))

        baked_dynamic_controllers = dynamic.filter_baked_dynamic_controllers(self.selection)
        if baked_dynamic_controllers:
            _action = menu.addAction('Restore Dynamics')
            _action.triggered.connect(partial(dynamic.restore_dynamic_controllers, baked_dynamic_controllers, doc))

        self.empty = False

    def get_asset(self, node):
        if isinstance(node, kl.RootNode):
            return

        if node.get_dynamic_plug('gem_type'):
            if node.gem_type.get_value() == Asset.type_name:
                self.asset = Asset(node)

        if not self.asset:
            self.get_asset(node.get_parent())

    def get_vis_groups(self):
        vis_groups = set()

        for group in self.groups:
            if self.node.get_dynamic_plug('menu_showhide'):
                plug = self.node.menu_showhide
                _vector = self.node.find('menu_showhide')  # legacy
                if _vector:
                    plug = _vector.input

                for i in range(plug.get_size()):
                    plug_in = plug[i].get_input()
                    if plug_in:
                        vis_groups.add(Group(plug_in.get_node()))

            if group.node.get_dynamic_plug('gem_id') and '::vis.' in group.node.gem_id.get_value():
                if group not in vis_groups:
                    vis_groups.add(group)
                    continue

            if group.node.get_dynamic_plug('menu_showhide'):
                plug = group.node.menu_showhide
                _vector = group.node.find('menu_showhide')  # legacy
                if _vector:
                    plug = _vector.input

                for i in range(plug.get_size()):
                    plug_in = plug[i].get_input()
                    if plug_in:
                        vis_groups.add(Group(plug_in.get_node()))

        return vis_groups

    def get_all_groups(self):
        all_groups = []

        for group in self.groups:
            if group in self.vis_groups:
                continue
            if len(all_groups):
                all_groups.append(None)

            if group not in all_groups:
                all_groups.append(group)
            for group_parent in group.get_all_parents(cache=True):
                if group_parent not in all_groups:
                    all_groups.append(group_parent)

        if self.vis_groups:
            all_groups.append(None)
        for group in self.vis_groups:
            if group not in all_groups:
                all_groups.append(group)

        return all_groups

    # selection callbacks
    def select_node(self, node):
        modifiers = QtWidgets.QApplication.keyboardModifiers()
        selection_mode = modifiers_to_selection_mode(modifiers)
        with self.doc.modify('Select Node') as modifier:
            modifier.select_nodes([node], selection_mode)

    def select_mirror(self):
        AssetMenu.select_mirror_with_doc(self.doc)

    @staticmethod
    def select_mirror_with_doc(doc):
        selection = doc.node_selection()
        ctrls = AssetMenu.filter_mirror_control(selection)
        nodes = list()
        for ctrl in ctrls:
            mirrors = ctrl.get_mirror_dict()
            if mirrors:
                try:
                    nodes.append(mirrors['-x'] if ctrl.node is mirrors['+x'] else mirrors['+x'])
                except KeyError:
                    warning("No -x/+x in dict: " + str(mirrors))
        if nodes:
            modifiers = QtWidgets.QApplication.keyboardModifiers()
            selection_mode = modifiers_to_selection_mode(modifiers)
            with doc.modify('Select Mirror') as modifier:
                modifier.select_nodes(nodes, selection_mode)
        else:
            warning("Nothing to Select Mirror")

    def select_group(self, group):
        modifiers = QtWidgets.QApplication.keyboardModifiers()
        selection_mode = modifiers_to_selection_mode(modifiers)
        name = group.node.gem_group.get_value().capitalize()
        is_all = group.get_first_parent(cache=True) is None

        with cp.Profile('profile_select_all', active=is_all):
            with self.doc.modify('Select group' + name) as modifier:
                nodes = group.get_all_nodes(cache=True)
                modifier.select_nodes(nodes, selection_mode, is_all)

    # reset callbacks
    def get_bind_pose_control(self, ctrl):
        with self.doc.modify("Get Bind Pose") as modifier:
            ctrl.get_bind_pose(modifier=modifier)

    def get_bind_pose_group(self, group):
        name = group.node.gem_group.get_value().capitalize()
        with self.doc.modify("Get Bind Pose " + name) as modifier:
            for c in group.get_all_members(cache=True):
                c.get_bind_pose(modifier=modifier)

    @staticmethod
    def get_bind_pose_selection_with_doc(doc):
        with doc.modify("Get Bind Pose Selected") as modifier:

            selection = doc.node_selection()
            plug_filter = doc.plug_selection().get_filter()

            for node in selection:
                if not node.get_dynamic_plug('gem_type') or node.gem_type.get_value() != Control.type_name:
                    continue

                c = Control(node)
                if c:
                    c.get_bind_pose(modifier=modifier, plug_filter=plug_filter)

    def get_bind_pose_selection(self):
        AssetMenu.get_bind_pose_selection_with_doc(self.doc)

    # mirror/flip callbacks
    @staticmethod
    def filter_mirror_control(ctrls, axis='x'):
        filtered = []
        reduced = []

        for node in ctrls:
            if not node.get_dynamic_plug('gem_type') or node.gem_type.get_value() != Control.type_name:
                continue

            ctrl = Control(node)
            mirrors = ctrl.get_mirror_dict(axis)

            if len(mirrors) <= 1:
                reduced.append(ctrl)
                continue

            if mirrors['+' + axis] not in filtered:
                reduced.append(ctrl)
                filtered.append(mirrors['+' + axis])

        return reduced

    def mirror_control(self, ctrl, direction):
        if isinstance(ctrl, str):
            node = find_path(ctrl)
            if node:
                ctrl = Control(node)
            else:
                return

        frame = self.doc.current_frame
        layer_name = self.doc.active_layer

        use_tangents = 'tangents' in inspect.signature(set_animated_plug_value).parameters  # >= 1.4.45 TODO: clean

        with self.doc.modify('Mirror' if direction else 'Flip') as modifier:
            for plug, value, src_plug, inv in ctrl.get_mirror_cmds(direction, frame):
                if use_tangents:
                    set_animated_plug_value(plug, value, modifier,
                                            tangents=get_tangents(plug, inv, src_plug, frame, layer_name))
                else:
                    set_animated_plug_value(plug, value, modifier)

    @staticmethod
    def mirror_selected_with_doc(direction, doc):
        with doc.modify(('Mirror' if direction else 'Flip') + " Selected") as modifier:

            selection = doc.node_selection()
            plug_filter = doc.plug_selection().get_filter()

            # we need to do that in two steps since get_mirror_cmds calls get_value()
            # and the selection may be "awkward", ie unorganized, see tang issue #479
            # we haven't seen this problem with preset operations ('All', etc) but with 'Selected' only
            plug_values = list()

            frame = doc.current_frame
            layer_name = doc.active_layer

            for ctrl in AssetMenu.filter_mirror_control(selection):
                for plug, value, src_plug, inv in ctrl.get_mirror_cmds(direction, frame, plug_filter=plug_filter):
                    plug_values.append((plug, value, get_tangents(plug, inv, src_plug, frame, layer_name)))

            use_tangents = 'tangents' in inspect.signature(set_animated_plug_value).parameters  # >= 1.4.45 TODO: clean

            for plug, value, tangents in plug_values:
                if use_tangents:
                    set_animated_plug_value(plug, value, modifier, frame, layer_name=layer_name, tangents=tangents)
                else:
                    set_animated_plug_value(plug, value, modifier, frame, layer_name=layer_name)

    def mirror_selected(self, direction):
        AssetMenu.mirror_selected_with_doc(direction, self.doc)

    def mirror_group(self, group, direction):
        if isinstance(group, str):
            node = find_path(group)
            if node:
                group = Group(node)
            else:
                return

        name = group.node.gem_group.get_value().capitalize()
        with self.doc.modify("Mirror Group: " + name) as modifier:

            frame = self.doc.current_frame
            layer_name = self.doc.active_layer

            use_tangents = 'tangents' in inspect.signature(set_animated_plug_value).parameters  # >= 1.4.45 TODO: clean

            for ctrl in AssetMenu.filter_mirror_control(group.get_all_nodes(cache=True)):
                for plug, value, src_plug, inv in ctrl.get_mirror_cmds(direction, frame):
                    if use_tangents:
                        set_animated_plug_value(plug, value, modifier,
                                                tangents=get_tangents(plug, inv, src_plug, frame, layer_name))
                    else:
                        set_animated_plug_value(plug, value, modifier)

    @staticmethod
    def _mirror_control_anim_with_modifier(ctrl, direction, modifier, plug_filter=None):
        doc = modifier.document
        animated_plugs = list()
        keyframes = set()
        useless_frame = doc.current_frame

        start = doc.range_start_frame if doc.range_start_frame > doc.start_frame else int(-2 ** 31)
        end = doc.range_end_frame if doc.range_end_frame < doc.end_frame else int(2 ** 31 - 1)

        for plug, value, src_plug, _ in ctrl.get_mirror_cmds(direction, useless_frame, plug_filter=plug_filter):
            res = get_animated_target(plug, doc, start, end)
            layer_adapt_value = None
            if len(res) == 2:
                target_plug, target_value = res
            elif len(res) == 3:
                target_plug, target_value, layer_adapt_value = res
            else:
                continue  # an error occurred
            if isinstance(target_value, dict):
                keyframes = keyframes.union(set(target_value.keys()))
                has_src_keys = True
            else:
                target_value = None
                has_src_keys = False
            if src_plug is not None:
                res_src = get_animated_target(src_plug, doc, start, end)
                if len(res_src) != 2 and len(res_src) != 3:
                    continue  # an error occurred
                src_value = res_src[1]
                has_src_keys = False
                if isinstance(src_value, dict):
                    keyframes = keyframes.union(set(src_value.keys()))
                    has_src_keys = True
            animated_plugs.append([target_plug, target_value, layer_adapt_value, has_src_keys])

        if not keyframes:
            keyframes.add(start)  # we must run the loop below at least once

        k_idx = 0
        for k in sorted(keyframes):
            idx = 0
            for plug, value, src_plug, inv in ctrl.get_mirror_cmds(direction, int(k), plug_filter=plug_filter):
                target = animated_plugs[idx]
                idx += 1
                target_value = target[1]
                if target_value is None:
                    target_plug = target[0]
                    has_src_keys = target[3]
                    if target_plug.is_connected():
                        # just-created anim
                        # so no layer here, start/end useless
                        target[0], target[1] = get_animated_target(target_plug, doc, start, end)
                        assert len(target[1]) == k_idx  # check consistency
                    elif has_src_keys:
                        modifier.create_anim_node_at_frame_with_value(target_plug, value, k)
                        target[0] = target_plug.get_input().get_node().curve
                        target[1] = dict()
                    else:
                        modifier.set_plug_value(target_plug, value)
                        continue
                    target_value = target[1]
                target_value[k] = (value, get_tangents(plug, inv, src_plug, k, doc.active_layer))
            k_idx += 1

        replace_instead_of_merge = hasattr(modifier, "remove_anim_key_at_frame")  # >= 1.4.46 TODO: clean

        # remove reference to anim if any to allow its deletion below
        target = None
        res = None
        res_src = None

        for target_plug, target_value, layer_adapt_value, has_src_keys in animated_plugs:
            if target_value is None:
                continue
            anim_node = target_plug.get_node()
            del target_plug  # avoid crash in debugger when stopped somewhere around
            to_remove_keys = []
            last_key = None
            key_added = False
            for k, value_tangents in target_value.items():
                value, tangents = value_tangents
                if layer_adapt_value is not None:
                    value -= layer_adapt_value(k)
                if tangents is not None:
                    if has_src_keys:
                        modifier.add_or_set_key_at_frame(anim_node, value, k)
                        modifier.set_key_tangents_at_frame(anim_node, k, tangents)
                        key_added = True
                    elif replace_instead_of_merge:
                        if anim_node.has_key_at(k):
                            # this key may be removed, so we modify it with the value anyway
                            modifier.add_or_set_key_at_frame(anim_node, value, k)
                            to_remove_keys.append(k)
                            if last_key is None:
                                # if all keys are removed the anim will be deleted and we want that key to give
                                # the remaining value (so, it will be the last deleted key)
                                last_key = k
                elif replace_instead_of_merge:
                    if anim_node.has_key_at(k):
                        # this key may be removed, so we modify it with the value anyway
                        modifier.add_or_set_key_at_frame(anim_node, value, k)
                        to_remove_keys.append(k)
                        if last_key is None:
                            # if all keys are removed the anim will be deleted and we want that key to give
                            # the remaining value (so, it will be the last deleted key)
                            last_key = k
                else:
                    modifier.add_or_set_key_at_frame(anim_node, value, k)  # <= 1.4.45 TODO: clean
            if len(to_remove_keys) != anim_node.key_count() and not key_added:
                # safety: we keep the first and the last key in the range
                if to_remove_keys:
                    del to_remove_keys[0]  # keep first
                if to_remove_keys:
                    del to_remove_keys[-1]  # keep last
            if to_remove_keys:
                anim_sub_path = doc.root().get_sub_path(anim_node.get_full_name())
                del anim_node
                for k in to_remove_keys:
                    if k != last_key:
                        modifier.remove_anim_key_at_frame(anim_sub_path, k)
                if last_key is not None:
                    modifier.remove_anim_key_at_frame(anim_sub_path, last_key)  # should delete the anim

    def mirror_control_anim(self, ctrl, direction):
        if isinstance(ctrl, str):
            node = find_path(ctrl)
            if node:
                ctrl = Control(node)
            else:
                return

        with self.doc.modify('Mirror' if direction else 'Flip') as modifier:
            AssetMenu._mirror_control_anim_with_modifier(ctrl, direction, modifier)

    @staticmethod
    def mirror_selected_anim_with_doc(direction, doc):
        with doc.modify(('Mirror' if direction else 'Flip') + " Selected Anim") as modifier:
            selection = doc.node_selection()
            plug_filter = doc.plug_selection().get_filter()

            for ctrl in AssetMenu.filter_mirror_control(selection):
                AssetMenu._mirror_control_anim_with_modifier(ctrl, direction, modifier, plug_filter)

    def mirror_selected_anim(self, direction):
        AssetMenu.mirror_selected_anim_with_doc(direction, self.doc)

    def mirror_group_anim(self, group, direction):
        node = find_path(group)
        group = Group(node)

        name = node.gem_group.get_value().capitalize()
        with self.doc.modify("Mirror Group: " + name) as modifier:
            for ctrl in AssetMenu.filter_mirror_control(group.get_all_nodes(cache=True)):
                AssetMenu._mirror_control_anim_with_modifier(ctrl, direction, modifier)

    # misc callbacks
    def vis_group(self, group, state):
        cmd = ('Hide', 'Show')[bool(state)]
        name = group.node.gem_group.get_value().capitalize()
        with self.doc.modify(cmd + " Group: " + name) as modifier:
            if state:
                group.show(modifier)
            else:
                group.hide(modifier)

    @staticmethod
    def pickwalk_with_doc(x, y, doc):
        with doc.modify('Pickwalk') as modifier:
            selection = doc.node_selection()


# -- debug menu

def load_menu(file_menu, parent):
    if not os.path.isfile(file_menu):
        log.error('could not find menu file "{}"'.format(file_menu))
        return

    data = None
    with open(file_menu, 'r') as stream:
        try:
            data = ordered_load(stream)
        except yaml.YAMLError as exc:
            log.error(exc)

    if not data:
        return

    load_menuitems(data, parent)


def load_menuitems(data, parent):
    for item in data:
        if not isinstance(item, dict):
            continue

        name = item.get('name', '')

        if 'menu' in item:
            if not name:
                name = 'menu'
            submenu = parent.addMenu(name)
            submenu.setTearOffEnabled(True)
            load_menuitems(item['menu'], submenu)
            continue

        if item.get('separator', False):
            parent.addSeparator()
            continue

        # item
        debug = False
        cmd = []
        if item.get('debug', False):
            debug = True
        if debug:
            cmd = ''

        if 'file' in item:
            path = fix_path(item['file'])
            ext = path.split('.')[-1]

            if not name:
                name = path.split('/')[-1].split('.')[0]

            if not debug:
                if ext == 'py':
                    cmd.append(partial(exec_file_globals, path))
            else:
                if ext == 'py':
                    cmd += 'exec(open("{}").read())\n'.format(path)

        if not debug:
            if 'py' in item:
                cmd.append(partial(partial_exec, item['py']))
        else:
            if 'py' in item:
                cmd += item['py'] + '\n'

        if not cmd:
            continue

        icon = None
        if 'icon' in item:
            color = item.get('color', '#999')
            if isinstance(color, str):
                icon = Icon(item['icon'], size=16, color=color, tool=True)

        act = QtWidgets.QAction(name, parent)
        if icon:
            act.setIcon(icon)

        if len(cmd) == 1:
            act.triggered.connect(partial(cmd[0]))
        else:
            act.triggered.connect(partial(callback_list, cmd))
        parent.addAction(act)


def callback_list(*args):
    if not isinstance(args[0], (list, tuple)):
        return

    for cb in args[0]:
        cb()


def partial_exec(code):
    exec(compile(code, '<string>', 'exec'), globals())


def exec_file_globals(path):
    exec(open(path).read(), globals())


sep = os.path.sep
path_mikan = sep.join(os.path.abspath(__file__).split(sep)[:-3])
path_utils = path_mikan + sep + 'tangerine' + sep + 'utils'
path_scripts = path_utils + sep + 'scripts'
paths = {'mikan': path_mikan, 'utils': path_utils, 'scripts': path_scripts}


def fix_path(path):
    for r in paths.keys():
        re = '$' + str(r).strip()
        if re in path:
            path = path.replace(re, paths[r])

    path = os.path.normpath(path)
    return path


app = QtWidgets.QApplication.instance()
batch_mode = app.config.no_gui()
do_rig_menu = os.getenv('MIKAN_MENU', 'false').lower() not in {'false', 'no', 'off', '0'}

if do_rig_menu and not batch_mode:
    main_window = app.main_window
    _menu = main_window.menuBar().addMenu('Mikan')

    # tools menu
    path = path_utils + sep + 'tools.yml'
    log.warning(path)
    load_menu(path, _menu)

    # prefs menu
    _paths = Prefs.get('tangerine_menu_paths', {})
    if _paths and isinstance(_paths, dict):
        _menu.addSeparator()

    for k in _paths:
        try:
            _submenu_path = _paths[k]
            _submenu_path = os.path.normpath(_submenu_path)

            _submenu = _menu.addMenu(k + '  ')
            load_menu(_submenu_path, _submenu)

        except:
            log.error(traceback.format_exc())
