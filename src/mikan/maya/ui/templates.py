# coding: utf-8

import os
import re
import string
import __main__
import traceback
import itertools
from types import ModuleType
from functools import partial
from six.moves import range
from six import string_types, iteritems

from mikan.vendor.Qt import QtCore, QtGui, QtWidgets
from mikan.vendor.Qt.QtCore import Qt, QSize
from mikan.vendor.Qt.QtWidgets import (
    QMainWindow, QTreeWidget, QTreeWidgetItem, QLabel, QSplitter, QPushButton,
    QLineEdit, QToolButton, QWidget, QSizePolicy, QComboBox, QMenu, QCheckBox,
    QItemDelegate, QShortcut, QAbstractItemView, QTextEdit, QApplication,
    QPlainTextEdit, QSpinBox, QGridLayout, QVBoxLayout,
)

from mikan.core.ui.widgets import *
from mikan.maya.ui.widgets import MayaWindow

import maya.api.OpenMaya as om
from mikan.maya import cmdx as mx
import maya.cmds as mc

from mikan.vendor.unidecode import unidecode
from mikan.core.abstract.mod import Mod
from mikan.core.prefs import Prefs
from mikan.core.utils import re_is_float, ordered_dict, ordered_load, filter_str
from mikan.core.logger import timed_code, create_logger, SafeHandler, get_formatter
from ..ui.widgets import OptVarSettings, SafeUndoInfo, Callback, open_url
from ..lib.rig import apply_transform
from ..lib.configparser import ConfigParser
from ..core import Asset, Template, Helper, Nodes, DeformerGroup, Deformer, parse_nodes

__all__ = ['TemplateManager']

log = create_logger('mikan')

# cleanup previously registered callbacks
_callbacks = __main__.__dict__.setdefault(__name__ + '.registered_callbacks', [])
_callbacks_io = __main__.__dict__.setdefault(__name__ + '.registered_callbacks_io', [])


def _clear_callbacks():
    for cb in _callbacks:
        try:
            om.MMessage.removeCallback(cb)
        except:
            pass
    del _callbacks[:]


def _clear_callbacks_io():
    for cb in _callbacks_io:
        try:
            om.MMessage.removeCallback(cb)
        except:
            pass
    del _callbacks_io[:]


_clear_callbacks()
_clear_callbacks_io()


class TemplateManager(QMainWindow, OptVarSettings):
    ROW_HEIGHT = 16
    ICON_SIZE = QSize(ROW_HEIGHT, ROW_HEIGHT)

    COLOR_ASSET_LOW = '#A98'
    COLOR_TPL_LOW = '#89A'
    COLOR_DFM_LOW = '#9A8'
    COLOR_TOOL_LOW = '#666'

    ICON_RELOAD = Icon('reload', color=COLOR_ASSET_LOW, size=ICON_SIZE, tool=True)
    ICON_BUILD = Icon('rocket', color=COLOR_ASSET_LOW, size=ICON_SIZE, tool=True)
    ICON_CLEANUP = Icon('broom', color=COLOR_ASSET_LOW, size=ICON_SIZE, tool=True)
    ICON_DELETE = Icon('trash', color=COLOR_TPL_LOW, size=ICON_SIZE, tool=True)
    ICON_SHAPES = Icon('shapes', color=COLOR_TPL_LOW, size=ICON_SIZE, tool=True)
    ICON_SELECT = Icon('mouse', color=COLOR_TPL_LOW, size=ICON_SIZE, tool=True)

    ICON_DEV = Icon('fix', color=COLOR_ASSET_LOW, size=ICON_SIZE, tool=True, toggle=True)
    ICON_DEBUG = Icon('bug', color=COLOR_ASSET_LOW, size=ICON_SIZE, tool=True, toggle=True)

    ICON_UPDATE_DFG = Icon('write', color=COLOR_DFM_LOW, size=ICON_SIZE, tool=True)

    ICON_ADD = Icon('cross', color=COLOR_TOOL_LOW, size=12)
    ICON_EDIT = Icon('fix', color=COLOR_TOOL_LOW)

    BUILD_MODES = Prefs.get('pipeline/steps', ['anim', 'layout', 'render'])

    def __init__(self, parent=None):
        QMainWindow.__init__(self, parent)
        self.setWindowFlags(Qt.Widget)
        self.setContextMenuPolicy(Qt.NoContextMenu)

        # panels
        self.tree = TemplateTreeWidget()
        self.tab_add = TemplateAddWidget()
        self.tab_edit = TemplateEditWidget()
        self.tab_log = TemplateLogWidget()
        self.tab_add._tree = self.tree
        self.tab_edit._tree = self.tree
        self.tab_edit._manager = self
        self.tab_log.log_box.widget._manager = self

        self.tabs = TabScrollWidget()
        self.tabs.addTab(self.tab_add, 'Add')
        self.tabs.addTab(self.tab_edit, 'Edit')
        self.tabs.addTab(self.tab_log, 'Logs')

        self.tabs.setTabIcon(0, TemplateManager.ICON_ADD)
        self.tabs.setTabIcon(1, TemplateManager.ICON_EDIT)

        # layout
        splitter = QSplitter(Qt.Vertical)
        splitter.addWidget(self.tree)
        splitter.addWidget(self.tabs)
        splitter.setStretchFactor(2, 1)
        splitter.setSizes([256, 256])
        self.setCentralWidget(splitter)
        self.build_toolbar()

        # init
        self.reload()

        # signals
        self.tree.itemSelectionChanged.connect(self.update_tabs)
        self.tree.itemSelectionChanged.connect(self.update_hooks)
        self.tree.doubleClicked.connect(self.select_tab_edit)
        self.tree.refresh_edit.connect(self.update_tabs)
        self.tree.refresh_edit.connect(self.select_tab_edit)

        self.tab_add.wd_add.clicked.connect(Callback(self.add_template))
        self.tab_add.wd_add_asset.clicked.connect(Callback(self.add_asset))

        self.tree.tree_changed.connect(self.update_tabs)

        self.tab_edit.wd_rename.returnPressed.connect(self.rename_item)
        self.tab_edit.wd_enable.altered.connect(self.update_tree_items)

        self.tabs.currentChanged.connect(self.tab_changed)

        # shortcuts
        up_key = QShortcut(QtGui.QKeySequence(Qt.Key_Up), self.tree)
        dn_key = QShortcut(QtGui.QKeySequence(Qt.Key_Down), self.tree)
        left_key = QShortcut(QtGui.QKeySequence(Qt.Key_Left), self.tree)
        right_key = QShortcut(QtGui.QKeySequence(Qt.Key_Right), self.tree)
        f_key = QShortcut(QtGui.QKeySequence(Qt.Key_F), self.tree)

        up_key.activated.connect(partial(self.navigate, 0, -1))
        dn_key.activated.connect(partial(self.navigate, 0, 1))
        left_key.activated.connect(partial(self.navigate, -1, 0))
        right_key.activated.connect(partial(self.navigate, 1, 0))
        f_key.activated.connect(partial(self.select_from_scene))

        # maya callbacks
        self.destroyed.connect(_clear_callbacks)

        _callbacks_io.append(om.MConditionMessage.addConditionCallback('newing', self.reload_cb))
        _callbacks_io.append(om.MConditionMessage.addConditionCallback('opening', self.reload_cb))
        _callbacks_io.append(om.MConditionMessage.addConditionCallback('readingReferenceFile', self.reload_cb))
        self.destroyed.connect(_clear_callbacks_io)

    def build_toolbar(self):
        toolbar = self.addToolBar('Template tools')
        toolbar.setFloatable(False)
        toolbar.setMovable(False)
        toolbar.setIconSize(TemplateManager.ICON_SIZE)
        toolbar.setStyleSheet(
            'QToolButton {border: none; margin: 2px;}'
            'QToolButton:pressed {padding-top:1px; padding-left:1px;}'
        )

        _act = toolbar.addAction('Reload')
        _act.setIcon(TemplateManager.ICON_RELOAD)
        _act.setShortcut('F5')
        _act.triggered.connect(self.reload)
        _act.triggered.connect(self.update_tabs)

        _act = toolbar.addAction('(Re)build rig')
        _act.setIcon(TemplateManager.ICON_BUILD)
        _act.triggered.connect(Callback(self.make_asset))

        _act = toolbar.addAction('Cleanup rig')
        _act.setIcon(TemplateManager.ICON_CLEANUP)
        _act.triggered.connect(Callback(self.cleanup_asset))

        toolbar.addSeparator()
        _act = toolbar.addAction('Update deformer groups')
        _act.setIcon(TemplateManager.ICON_UPDATE_DFG)
        _act.triggered.connect(Callback(self.update_dfg))

        toolbar.addSeparator()
        _act = toolbar.addAction('Delete selected')
        _act.setIcon(TemplateManager.ICON_DELETE)
        _act.triggered.connect(Callback(self.tree.delete_selected_items))

        _act = toolbar.addAction('Toggle shapes')
        _act.setIcon(TemplateManager.ICON_SHAPES)
        _act.triggered.connect(Callback(self.toggle_shapes))

        _act = toolbar.addAction('Select item from scene')
        _act.setIcon(TemplateManager.ICON_SELECT)
        _act.triggered.connect(Callback(self.select_from_scene))

        # spacer
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        toolbar.addWidget(spacer)

        # modes
        self.wd_debug = QToolButton()
        self.wd_debug.setIcon(TemplateManager.ICON_DEBUG)
        self.wd_debug.setCheckable(True)
        _st = self.get_optvar('mode_debug', False)
        self.wd_debug.setChecked(_st)
        self.wd_debug.setToolTip('debug mode')
        toolbar.addWidget(self.wd_debug)

        self.wd_dev = QToolButton()
        self.wd_dev.setIcon(TemplateManager.ICON_DEV)
        self.wd_dev.setCheckable(True)
        _st = self.get_optvar('mode_dev', True)
        self.wd_dev.setChecked(_st)
        self.wd_dev.setToolTip('dev mode')
        toolbar.addWidget(self.wd_dev)

        self.wd_mode = QComboBox()
        self.wd_mode.addItems(TemplateManager.BUILD_MODES)
        self.wd_mode.setMaximumWidth(96)
        self.wd_mode.setCurrentIndex(self.get_optvar('mode', 0))
        self.wd_mode.setToolTip('release mode')
        toolbar.addWidget(self.wd_mode)

        # connections
        self.wd_dev.toggled.connect(self.mode_dev_changed)
        self.wd_debug.toggled.connect(self.mode_debug_changed)
        self.wd_mode.currentIndexChanged.connect(self.mode_changed)

    # -- UI slots

    def reload(self):
        Nodes.rebuild()
        try:
            self.tree.load()
        except:
            msg = traceback.format_exc().strip('\n')
            log.critical(msg)
            log.critical('/!\\ failed to load template')

    def reload_cb(self, *args):
        n = om.MConditionMessage.getConditionState('newing')
        o = om.MConditionMessage.getConditionState('opening')
        r = om.MConditionMessage.getConditionState('readingReferenceFile')

        # reload l'UI seulement quand maya n'a plus d'opérations de fichiers en cours
        if not any((n, o, r)):
            self.reload()

    def tab_changed(self, tab):
        if tab == 0:
            # add tab
            self.tree.setSelectionMode(QAbstractItemView.SingleSelection)
            self.tree.BRUSH_SELECTED = self.tree.BRUSH_SELECTED_ADD

            self.update_hooks()

        else:
            # other tabs
            self.tree.setSelectionMode(QAbstractItemView.ExtendedSelection)
            self.tree.BRUSH_SELECTED = self.tree.BRUSH_SELECTED_EDIT

            items = self.tree.get_selected_items()
            for item in items:
                if isinstance(item, TemplateHook):
                    tpl = item.template
                    tree_item = self.tree.tree_items[item]
                    tree_item.setSelected(False)

                    tree_item = self.tree.tree_items[tpl]
                    tree_item.setSelected(True)

            # remove all hooks item
            tpl_hooks = [item for item in self.tree.tree_items if isinstance(item, TemplateHook)]

            for tpl_hook in tpl_hooks:
                tree_item = self.tree.tree_items[tpl_hook]
                self.tree.delete_tree_item(tree_item)

        self.tree.viewport().update()

    def update_tabs(self):
        items = self.tree.get_selected_items()
        self.tab_add.set_current_items(items)
        self.tab_edit.set_current_items(items)

        self.tab_add.rebuild()
        self.tab_edit.rebuild()

        self.update_hooks()

    def update_hooks(self):

        add_mode = self.tabs.currentIndex() == 0
        if not add_mode:
            return

        self.tree.blockSignals(True)

        # force only one selected item
        last = None
        items = self.tree.get_selected_tree_items()
        if items:
            last = items[-1]
        if len(items) > 1:
            self.tree.clearSelection()
            last.setSelected(True)

        # add hooks for selected template
        if last and isinstance(last.item, Template):
            tpl = last.item

            # remove all previous hooks
            tpl_hooks = [item for item in self.tree.tree_items if isinstance(item, TemplateHook)]

            for tpl_hook in tpl_hooks:
                tree_item = self.tree.tree_items[tpl_hook]
                self.tree.delete_tree_item(tree_item)

            # add hooks
            hooks = ordered_dict()
            data = tpl.template_data.get('ui', {})
            if 'hooks' in data:
                for name in data['hooks']:
                    if name == 'default':
                        continue
                    nodes = tpl.get_structure(data['hooks'][name])
                    if not nodes:
                        continue
                    n = len(nodes)

                    if n == 1 and '[' not in data['hooks'][name]:
                        hooks[name] = nodes[0]
                    else:
                        for i, node in enumerate(nodes):
                            hooks['{}[{}]'.format(name, i)] = node

            for name in list(hooks)[::-1]:
                tpl_hook = TemplateHook(tpl, name, hooks[name])
                self.tree.add_item(tpl_hook, tpl, insert=True)

        self.tree.blockSignals(False)

    def select_tab_edit(self):
        self.tabs.setCurrentIndex(1)

    def navigate(self, x, y):
        item = self.tree.get_selected_tree_item()

        parent = item.parent()
        children = [item.child(n) for n in range(item.childCount())]
        if parent:
            siblings = [parent.child(n) for n in range(parent.childCount())]
        else:
            siblings = [self.tree.topLevelItem(n) for n in range(self.tree.topLevelItemCount())]

        if x:
            n = siblings.index(item)
            n += x
            if n + 1 > len(siblings):
                n = 0
            elif n == -1:
                n = len(siblings) - 1
            self.tree.setCurrentItem(siblings[n], 1)
            self.tree.tree_changed.emit()
            self.select_tab_edit()

        elif y == -1 and parent:
            self.tree.setCurrentItem(parent, 1)
            self.tree.tree_changed.emit()
            self.select_tab_edit()

        elif y == 1 and children:
            self.tree.setCurrentItem(children[0], 1)
            self.tree.tree_changed.emit()
            self.select_tab_edit()

    # -- slots

    def add_template(self):
        Nodes.get_asset_paths()

        # add
        name = self.tab_add.wd_name.text()
        n = self.tab_add.wd_number.value
        tpl_type = self.tab_add.wd_type.value + '.' + self.tab_add.wd_subtype.value

        parent = None
        parent_item = self.tree.get_selected_item()

        if isinstance(parent_item, Asset):
            parent = parent_item.get_template_root()

        elif isinstance(parent_item, Template):
            parent = parent_item.node

            data = parent_item.template_data.get('ui', {})
            if 'hooks' in data and 'default' in data['hooks']:
                nodes = parent_item.get_structure(data['hooks']['default'])
                if nodes:
                    if isinstance(nodes, list):
                        parent = nodes[0]
                    else:
                        parent = nodes

        elif isinstance(parent_item, TemplateHook):
            parent = parent_item.node

        # create template
        data = {}
        for opt, w in iteritems(self.tab_add.wd_adds):
            if w.value != w.default:
                data[opt] = w.value

        for i in range(n):
            tpl = Template.create(tpl_type, parent, name, data=data)

            # set opts from add box
            for opt, w in iteritems(self.tab_add.wd_opts):
                if w.value != w.default:
                    tpl.set_opt(opt, w.value)

            for opt, w in iteritems(self.tab_add.wd_custom_opts['']):
                if w.value != w.default:
                    tpl.set_opt(opt, w.value)

            self.tree.add_item(tpl, parent=parent_item)

        # refresh ui
        self.tree.setCurrentItem(self.tree.tree_items[tpl], 1)
        self.tree.tree_changed.emit()

    def add_asset(self):
        Nodes.get_asset_paths()

        name = filter_str(self.tab_add.txt_add_asset.text())
        item = Asset.create(name)
        self.tree.add_item(item)

    def get_current_asset(self):
        tree_item = self.tree.get_selected_tree_item()

        while tree_item:
            item = tree_item.item
            if isinstance(item, Asset):
                return item

            tree_item = tree_item.parent()

        # return the single asset if only one in tree
        items = [item for item in self.tree.tree_items if isinstance(item, Asset)]
        if len(items) == 1:
            return items[0]

    @busy_cursor
    def make_asset(self):

        # get info
        asset = self.get_current_asset()

        modes = set()
        modes.add(self.wd_mode.currentText())
        if self.wd_dev.isChecked():
            modes.add('dev')
        if self.wd_debug.isChecked():
            modes.add('debug')

        # clear log
        self.tab_log.clear_text()

        # no asset
        if not asset:
            return

        # remove node editor before build
        for p in mc.lsUI(ed=True, long=1):
            if 'nodeEditor' in p and 'Window' in p:
                p = p.split('|')[0]
                mc.deleteUI(p)

        # build
        with SafeUndoInfo():
            try:
                asset.make(modes=modes)
            except Exception as e:
                msg = traceback.format_exc().strip('\n')
                log.critical(msg)

        # check for errors
        if asset.monitor.has_failed:
            self.tabs.setCurrentIndex(2)

    @busy_cursor
    def cleanup_asset(self):

        # get info
        asset = self.get_current_asset()
        if not asset:
            return

        # remove node editor before build
        for p in mc.lsUI(ed=True, long=1):
            if 'nodeEditor' in p and 'Window' in p:
                p = p.split('|')[0]
                mc.deleteUI(p)

        # cleanup
        with timed_code('cleanup rig', force=True):
            with SafeUndoInfo():
                asset.monitor = None
                asset.init_cleanup()
                tpl_root = asset.get_template_root()
                tpl_root.show()

    @busy_cursor
    def toggle_shapes(self):
        Nodes.rebuild()

        for item in self.tree.get_selected_items():
            if isinstance(item, (Asset, Template, Helper)):
                item.toggle_shapes_visibility()

    @busy_cursor
    def rename_item(self):
        Nodes.get_asset_paths()

        item = self.tab_edit.item

        if item.node.is_referenced():
            self.tab_edit.wd_rename.setText(item.name)
            return

        name = filter_str(self.tab_edit.wd_rename.text())
        item.rename(name)
        self.tab_edit.wd_rename.setText(item.name)
        self.update_tree_items()

    def update_tree_items(self):
        for item in self.tab_edit.items:
            if item in self.tree.tree_items:
                self.tree.tree_items[item].update(rebuild=True)

    def mode_dev_changed(self):
        self.set_optvar('mode_dev', bool(self.wd_dev.isChecked()))

    def mode_debug_changed(self):
        self.set_optvar('mode_debug', bool(self.wd_debug.isChecked()))

    def mode_changed(self):
        self.set_optvar('mode', self.wd_mode.currentIndex())

    def select_from_scene(self):
        sl = mx.ls(sl=1)
        if sl:
            tpl = Template.get_from_node(sl[0])

            if tpl in self.tree.tree_items:
                self.tree.setCurrentItem(self.tree.tree_items[tpl], 1)
            self.tree.tree_changed.emit()

    @busy_cursor
    def update_dfg(self):
        asset = self.tree.get_asset_from_selection()
        if asset:
            asset.update_deformer_groups()


class OptPlugConnect(AbstractPlugConnect):

    def __init__(self, tpl, opt):
        self.widget = None
        self.tpl = tpl
        self.opt = opt

    def update(self):
        v = self.widget.value
        self.tpl.set_opt(self.opt, v)
        self.widget.set_altered()

    def reset(self):
        self.tpl.reset_opt(self.opt)
        self.widget.set_altered()

    def read(self):
        return self.tpl.get_opt(self.opt)

    def connected(self):
        return self.tpl.has_opt_plug(self.opt)


class NamePlugConnect(AbstractPlugConnect):

    def __init__(self, tpl, name):
        self.widget = None
        self.tpl = tpl
        self.name = name

    def update(self):
        v = self.widget.value
        self.tpl.set_name(self.name, v)
        self.widget.set_altered()

    def reset(self):
        self.tpl.reset_name(self.name)
        self.widget.set_altered()

    def read(self):
        return self.tpl.get_name(self.name)

    def connected(self):
        return self.tpl.has_name_plug(self.name)


class HelperPlugConnect(AbstractPlugConnect):

    def __init__(self, node, enable=False):
        self.widget = None
        self.enable = enable
        self.helper = Helper(node) if node else None

    def update(self):
        if self.helper is None:
            return

        v = self.widget.value

        if self.enable:
            if not v:
                self.helper.enable()
            else:
                self.helper.disable()
        else:
            v = unidecode(v)
            self.helper.set_enable_modes(v)

        self.widget.set_altered()

    def reset(self):
        if self.helper is None:
            return

        if self.enable:
            self.helper.reset_enable()
        else:
            self.helper.reset_enable_modes()

        self.widget.set_altered()

    def read(self):
        if self.helper is None:
            return
        if self.enable:
            return not self.helper.get_enable()
        else:
            return self.helper.get_enable_modes()

    def connected(self):
        if self.enable:
            if self.helper.has_enable():
                return True
        else:
            if self.helper.has_enable_modes():
                return True

        return False


class TemplateOpts(StackWidget):

    def __init__(self, parent=None):
        StackWidget.__init__(self, parent)
        self.last_add_item = None
        self.last_opts_item = []

        self.wd_adds = {}
        self.wd_opts = {}
        self.wd_custom_opts = {}
        self.wd_names = {}

        self.item = None
        self.items = []

    def set_current_items(self, items):
        self.items = [item for item in items if item is not None]
        self.item = None
        if len(self.items) == 1:
            self.item = self.items[0]

    def get_current_template_modules(self):
        return []

    def build_box_opt(self):

        # process items
        templates = self.get_current_template_modules()

        # clean
        self.clear_layout(self.box_opts)
        self.wd_opts.clear()
        self.wd_custom_opts.clear()
        if not templates:
            return

        # rebuild common opts
        common_keys = Template.common_data['opts'].keys()
        self.wd_opts['branches'] = StringPlugWidget(label='Branches', default='', yaml=True, presets=['[L, R]', '[up, dn]', '[ft, bk]'], unidecode=True)
        self.wd_opts['sym'] = StringListPlugWidget(label='Symmetry axis', default='parent')
        self.wd_opts['sym'].set_list(list(Template.common_data['opts']['sym']['enum'].values()))
        self.wd_opts['group'] = StringPlugWidget(label='Group', default='', filter=True)
        self.wd_opts['parent'] = StringListPlugWidget(label='Parent', default='parent')
        self.wd_opts['parent'].set_list(list(Template.common_data['opts']['parent']['enum'].values()))
        self.wd_opts['do_ctrl'] = BoolPlugWidget(label='Tag ctrl', default=True)
        self.wd_opts['do_skin'] = BoolPlugWidget(label='Tag skin', default=True)
        self.wd_opts['isolate_skin'] = BoolPlugWidget(label='Isolate skin', default=False)
        self.wd_opts['virtual_parent'] = StringPlugWidget(label='Virtual parent', default='', filter=True)

        _col0, _col1 = self.add_columns(self.box_opts)
        _col0.addWidget(self.wd_opts['branches'])
        _col0.addWidget(self.wd_opts['group'])
        _col0.addWidget(self.wd_opts['parent'])
        _col0.addWidget(self.wd_opts['sym'])
        _col1.addWidget(self.wd_opts['do_ctrl'])
        _col1.addWidget(self.wd_opts['do_skin'])
        _col1.addWidget(self.wd_opts['isolate_skin'])
        _col1.addWidget(self.wd_opts['virtual_parent'])
        _col1.addStretch()

        # TODO: delete option in Template
        self.wd_opts['virtual_parent'].setVisible(False)

        # rebuild custom opts
        modules = set()

        for tpl in templates:
            if isinstance(tpl, Template):
                connect = True
            elif isinstance(tpl, ModuleType):
                connect = False
            else:
                continue

            # rebuild custom opts
            if 'opts' in tpl.template_data:
                build_widgets = True

                module_name = ''
                if isinstance(tpl, Template):
                    module_name = tpl.template
                    if module_name == 'core._unknown':
                        continue

                    if tpl.template in modules:
                        build_widgets = False
                    modules.add(tpl.template)

                if build_widgets:
                    self.wd_custom_opts[module_name] = {}

                    line = self.add_line(self.box_opts, label=module_name)
                    line.setStyleSheet('color:#789; font-size:12px; font-weight:bold')

                    _cols = self.add_columns(self.box_opts)
                    opts_number = len(tpl.template_data['opts']) - len(common_keys)
                    row_count = 0
                    col_count = 0

                for opt, data in iteritems(tpl.template_data['opts']):
                    yaml = data.get('yaml', False)

                    dv = data.get('value')
                    if yaml:
                        dv = ordered_load(dv)

                    if connect:
                        dv = tpl.get_opt(opt, default=True)

                    enum = data.get('enum')
                    vmin = data.get('min')
                    vmax = data.get('max')
                    presets = data.get('presets')

                    if opt in common_keys:
                        w = self.wd_opts[opt]
                        w.set_default(dv)

                    else:
                        if build_widgets:
                            label = data.get('label', opt.capitalize().replace('_', ' '))
                            if enum:
                                if isinstance(dv, int):
                                    dv = list(enum.values())[dv]
                                w = StringListPlugWidget(label=label, default=dv)
                                w.set_list(list(enum.values()))
                            elif yaml or isinstance(dv, string_types):
                                w = StringPlugWidget(label=label, default=dv, presets=presets, yaml=yaml, unidecode=True)
                            elif isinstance(dv, bool):
                                w = BoolPlugWidget(label=label, default=dv)
                            elif isinstance(dv, int):
                                w = IntPlugWidget(label=label, default=dv, min_value=vmin, max_value=vmax)
                            elif isinstance(dv, float):
                                w = FloatPlugWidget(label=label, default=dv, min_value=vmin, max_value=vmax)
                            elif isinstance(dv, list) and len(dv) == 3 and all(isinstance(x, (int, float)) for x in dv):
                                w = VectorPlugWidget(label=label, default=dv, presets=presets)
                            else:
                                continue

                            _cols[col_count].addWidget(w)
                            row_count += 1
                            if row_count >= opts_number / 2:
                                col_count = 1

                            self.wd_custom_opts[module_name][opt] = w
                        else:
                            w = self.wd_custom_opts[module_name][opt]

                    if connect:
                        w.add_connector(OptPlugConnect(tpl, opt))
                    else:
                        w.set_value(dv)
                    w.set_altered()

                if opts_number % 2:
                    _cols[1].addStretch()

            # dirty tree item update
            if connect:
                self.wd_opts['branches'].value_changed.connect(self._tree.tree_items[tpl].update)

    def build_box_names(self):

        for tpl in self.get_current_template_modules():
            if isinstance(tpl, (Template, ModuleType)):
                break
        else:
            tpl = None

        # clean
        self.clear_layout(self.box_names)
        self.wd_names.clear()
        if tpl is None:
            return

        # get template data
        if isinstance(tpl, Template):
            connect = True
        else:
            connect = False

        if 'names' not in tpl.template_data:
            return

        _grid = self.add_grid(self.box_names)
        row_count = 0
        col_count = 0

        for name, data in iteritems(tpl.template_data['names']):
            label = name.capitalize().replace('_', ' ')
            w = StringPlugWidget(label=label, default=data)

            _grid.addWidget(w, row_count, col_count)
            col_count = 0
            row_count += 1
            self.wd_names[name] = w

            if connect:
                w.add_connector(NamePlugConnect(tpl, name))
            w.set_altered()


class TemplateEditWidget(TemplateOpts):

    def __init__(self, parent=None):
        TemplateOpts.__init__(self, parent)

        # build field ui
        self.box_fields = self.add_column(margins=0, spacing=0)

        self.wd_type = QLabel()
        self.wd_rename = QLineEdit()

        self.wd_mode = StringPlugWidget(label='mode', default='')
        self.wd_mode.layout.setStretch(0, 1)
        self.wd_mode.color_changed = 'color: #ddd;'
        self.wd_mode.color_altered = 'color: #ddd;'

        self.wd_enable = BoolPlugWidget(label='disable', default=False)
        self.wd_enable.color_changed = 'color: #ddd;'
        self.wd_enable.color_altered = 'color: #ddd;'

        self.box_rename = self.add_grid(self.box_fields)
        self.box_rename.setSpacing(5)
        self.box_rename.addWidget(self.wd_type, 0, 0, stretch=4, align=Qt.AlignRight)
        self.box_rename.addWidget(self.wd_rename, 0, 1, stretch=4)
        self.box_rename.addWidget(self.wd_mode, 0, 2, stretch=5)
        self.box_rename.addWidget(self.wd_enable, 0, 3, stretch=1)

        self.box_opts = self.add_collapse('Options', self.box_fields)
        self.box_names = self.add_collapse('Names', self.box_fields)

        self.box_fields.addStretch(1)

        # build text edit ui
        self.mod_edit = TemplateModEdit()
        self.mod_edit.textChanged.connect(self.update_mod)

        self.highlighter = SyntaxHighlighter(self.mod_edit)

        self.highlighter.add_styles([
            ('comment', 'gray', {'italic': True}),
            ('shell', '#b5f'),

            ('keyword', '#5bf'),
            ('operator', 'orange', {'bold': True}),
            ('brace', 'orange', {'bold': True}),
            ('var', '#5bf'),

            ('key', '#bbb', {'bold': True}),
            ('number', '#bf5'),
            ('string', '#bf5'),

            ('command', '#c7a6e7', {'bold': True}),

            ('id', '#abd7fe'),
            ('id2', '#5c86ae'),
        ])

        self.highlighter.add_rules([
            # operators
            (r',(?=.*(\]|\}))', 0, 'operator'),
            (r': ', 0, 'operator'),
            (r':$', 0, 'operator'),
            (r'^ *- ', 0, 'operator'),

            # keywords
            (r'\b[A-Za-z0-9_]+(?=:)(?!::)', 0, 'key'),

            # numeric literals
            (r'-?\b\d*\.?\d+(?![a-zA-Z\.])', 0, 'number'),
            (r'-?\b\d+\.?\d*(?![a-zA-Z\.])', 0, 'number'),

            # yaml
            (r'\b(on|off|yes|no|true|false|null)\b', 0, 'keyword'),
            (r'(\[|\]|\{|\})', 0, 'brace'),

            # commands
            (r'^({})'.format('|'.join(Mod.modules)), 0, 'command'),

            # quoted string, possibly containing escape sequences
            (r'"[^"\\]*(\\.[^"\\]*)*"', 0, 'string'),
            (r"'[^'\\]*(\\.[^'\\]*)*'", 0, 'string'),

            # gem id
            (r'[a-zA-Z0-9_*.<>|\/]*(::|:::|->)[a-zA-Z0-9_*.<>@]*', 0, 'id'),
            (r'@(?=[a-zA-Z_][a-zA-Z0-9_]*)', 0, 'id2'),
            (r'(::|:::|->)', 0, 'id2'),

            # gem var
            (r'<([a-zA-Z0-9_]+(?:\.[a-zA-Z0-9_]+)?)>', 0, 'var'),
            (r' *\$[a-zA-Z_<>][a-zA-Z0-9_<>]*', 0, 'var'),

            # commands
            (r'^#[!>$?\/]', 0, 'shell'),

            # from '#' until a newline
            (r'#(?![!>$?\/])[^\n]*', 0, 'comment'),
        ])

        # id inspector
        self.mod_ids = TemplateModInspector()
        self.mod_ids.editor = self.mod_edit

        # build splitter
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(self.mod_edit)
        splitter.addWidget(self.mod_ids)
        splitter.setStretchFactor(2, 1)
        splitter.setSizes([256, 128])

        self.box_textedit = self.add_column(stretch=1, margins=0, spacing=0)
        self.box_textedit.addWidget(splitter, stretch=1)

        # search bar
        row = self.add_row(self.box_textedit, margins=0, spacing=1)

        self.search_edit = QLineEdit()
        btn1 = QPushButton('Search')
        btn2 = QPushButton('Search all')

        row.addWidget(self.search_edit, stretch=1)
        row.addWidget(btn1)
        row.addWidget(btn2)

        self.search_edit.returnPressed.connect(self.search_current)
        btn1.clicked.connect(self.search_current)
        btn2.clicked.connect(self.search_all)

        # display
        self.rebuild()

    def get_current_template_modules(self):
        return self.items

    def rebuild(self):

        # check conditions
        v_edit = True
        v_opts = False
        v_names = False
        v_textedit = False

        empty = not self.items
        single = len(self.items) == 1
        types = [Template if issubclass(type(item), Template) else type(item) for item in self.items]
        mixed = not all([types[0] == t for t in types[1:]])

        if empty or mixed:
            v_edit = False

        # rebuild
        if not mixed and Template in types:
            v_opts = True
            v_names = single
            self.build_box_opt()
            self.wd_type.setStyleSheet('color:#789; font-size:12px; font-weight:bold')
            if single:
                tpl_module = self.item.template
                if tpl_module == 'core._unknown':
                    tpl_module = self.item.node['gem_module'].read()
                    self.wd_type.setStyleSheet('color:#c55; font-size:12px; font-weight:bold')
                else:
                    self.build_box_names()
                self.wd_type.setText(tpl_module)
            else:
                self.wd_type.setText('Templates')

        elif single:
            if isinstance(self.item, Helper):
                if self.item.has_mod():
                    v_textedit = True
                    self.build_box_mod()
                    self.wd_type.setText('Modifier')
                    self.wd_type.setStyleSheet('color:#879; font-size:12px; font-weight:bold')

                elif self.item.has_deformer():
                    v_textedit = True
                    self.build_box_mod()
                    self.wd_type.setText('Deformer')
                    self.wd_type.setStyleSheet('color:#897; font-size:12px; font-weight:bold')

                else:
                    self.wd_type.setText('Helper')
                    self.wd_type.setStyleSheet('color:#999; font-size:12px; font-weight:bold')

            elif isinstance(self.item, DeformerGroup):
                self.wd_type.setText('Deformer Group')
                self.wd_type.setStyleSheet('color:#897; font-size:12px; font-weight:bold')

            elif isinstance(self.item, Asset):
                self.wd_type.setText('Asset')
                self.wd_type.setStyleSheet('color:#987; font-size:12px; font-weight:bold')

        self.box_fields.parent().setVisible(v_edit)
        self.box_opts.parent().parent().setVisible(v_opts)
        self.box_names.parent().parent().setVisible(v_names)
        self.box_textedit.parent().setVisible(v_textedit)

        # rename field
        if single and isinstance(self.item, (Asset, Template, Helper, DeformerGroup)):
            self.wd_rename.setText(self.item.name)

            locked = self.item.node.isReferenced()
            self.wd_rename.setEnabled(not locked)

        if not single:
            self.wd_rename.setText('')
            self.wd_rename.setEnabled(False)

        # modes
        self.wd_mode.clear_connections()
        self.wd_enable.clear_connections()
        self.wd_mode.hide()
        self.wd_enable.hide()

        for item in self.items:
            if isinstance(item, (Template, Helper, DeformerGroup)):
                self.wd_mode.add_connector(HelperPlugConnect(item.node))
                self.wd_enable.add_connector(HelperPlugConnect(item.node, enable=True))
                self.wd_mode.show()
                self.wd_enable.show()
        self.wd_mode.set_altered()
        self.wd_enable.set_altered()

    def build_box_mod(self):
        self.mod_edit.blockSignals(True)

        mod = self.item
        txt = mod.node['notes'].read()
        self.mod_edit.setText(txt)

        locked = self.item.node.is_referenced()
        self.mod_edit.setReadOnly(locked)

        self.mod_ids.update_display()

        self.mod_edit.blockSignals(False)

    def update_mod(self):
        if not isinstance(self.item, Helper):
            return

        txt = self.mod_edit.toPlainText()
        self.item.node['notes'] = txt

    def search_current(self, loop=True):
        key_mod = QApplication.keyboardModifiers()
        if loop and key_mod == Qt.ALT:
            return self.search_all()

        doc = self.mod_edit.document()
        pattern = self.search_edit.text()

        cursor = self.search_doc(doc, pattern)
        self.mod_edit.setTextCursor(cursor)

    def search_all(self):
        doc = self.mod_edit.document()
        pattern = self.search_edit.text()

        focus_widget = QApplication.focusWidget()

        cursor = self.search_doc(doc, pattern, loop=False)
        if cursor:
            self.mod_edit.setTextCursor(cursor)
        else:
            current_item = self._tree.get_selected_item()
            items = [x for x in self._tree.tree_items if isinstance(x, Helper) and (x.has_mod() or x.has_deformer())]
            n = len(items)
            if n == 1:
                return self.search_current(loop=False)

            i = items.index(current_item)
            if i == 0:
                items = items[1:]
            elif i == len(items) - 1:
                items = items[:-1]
            else:
                items = items[i + 1:] + items[:i]

            for item in items:
                notes = item.node['notes'].read()
                if pattern not in notes:
                    continue
                self._tree.setCurrentItem(self._tree.tree_items[item])

                self._manager.update_tabs()
                focus_widget.setFocus()
                return self.search_current(loop=False)

            self.search_current(loop=False)

    def search_doc(self, doc, pattern, loop=True):
        cursor = self.mod_edit.textCursor()
        pos = cursor.selectionEnd()

        # search loop
        cursor = doc.find(pattern, pos)
        if not cursor.hasSelection():
            if loop:
                cursor = doc.find(pattern)
            else:
                return

        return cursor


class TemplateModEdit(QTextEdit):

    def __init__(self, parent=None):
        QTextEdit.__init__(self, parent)

        f = QtGui.QFont('courier new', 9)
        f.setFixedPitch(True)
        self.setFont(f)
        self.setStyleSheet('QTextEdit {border: none;}')

        self.setAcceptRichText(False)

        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.generate_context_menu)

        self.re_id = QtCore.QRegExp(r'[a-zA-Z0-9_*.<>|\/]*(::|:::|->)[a-zA-Z0-9_*.<>@]*')

    def generate_context_menu(self, pos):
        menu = self.createStandardContextMenu()
        # add extra items to the menu

        act = menu.addAction('Help: Modifiers')
        act.triggered.connect(partial(open_url, 'https://citrus-software.github.io/mikan-docs/usage/modifiers'))
        acts = [act]

        mod = self.find_current_mod(pos)
        if mod and mod in Mod.modules:
            module = Mod.modules[mod]
            wiki = module.mod_data.get('help')

            act = menu.addAction('Help: {}'.format(mod))
            act.triggered.connect(partial(open_url, wiki))
            acts.append(act)

        user_selection = self.get_user_selection()
        if user_selection:
            act = menu.addAction('Duplicate selection')
            act.triggered.connect(partial(self.duplicate_selection_cb, self, user_selection))
            acts.append(act)

        before = None
        for w in menu.children():
            if w.text():
                before = w
                break

        if before:
            for act in acts[::-1]:
                menu.insertAction(before, act)
            menu.insertSeparator(before)
        else:
            menu.addSeparator()
            for act in acts:
                menu.addAction(act)

        # show the menu
        menu.popup(self.mapToGlobal(pos))

    def mouseReleaseEvent(self, event):
        key_mod = QApplication.keyboardModifiers()

        if key_mod == Qt.CTRL and event.button() == Qt.LeftButton:

            # select ids
            select = []
            for find in self.find_current_ids():
                nodes = parse_nodes(find)
                if nodes:
                    if isinstance(nodes, (list, tuple)):
                        select += nodes
                    else:
                        select.append(nodes)
                    log.info('{} selected ({})'.format(find, nodes))
                else:
                    log.error('{} is invalid'.format(find))

            if select:
                nodes = []
                for node in select:
                    if isinstance(node, mx.Node):
                        nodes.append(node)
                    elif isinstance(node, mx.Plug):
                        nodes.append(node.node())
                mx.cmd(mc.select, nodes)

        QTextEdit.mouseReleaseEvent(self, event)

    def find_current_ids(self):
        cursor = self.textCursor()
        doc = self.document()

        line = cursor.block().text()
        b = cursor.positionInBlock()

        # regex mikan ids
        find = ''
        index = self.re_id.indexIn(line, 0)
        while index >= 0:
            index = self.re_id.pos(0)
            length = len(self.re_id.cap(0))
            if index <= b < index + length:
                find = line[index:index + length]
            index = self.re_id.indexIn(line, index + length)
        if not find:
            return []

        # replace <vars>
        vars = re.findall(r'(?<=<)[a-zA-Z0-9_]*(?=>)', find)
        if not vars:
            return [find]
        else:
            mod = doc.toPlainText()
            i = cursor.position()

            limits = [0]
            for it in re.finditer(r'\[[a-zA-Z0-9]+]', mod):
                limits.append(it.start())
            if limits:
                limits.append(len(mod))

            for s, e in zip(limits[:-1], limits[1:]):
                if s <= i < e:
                    break
            lines = mod[s:e].splitlines()

            vars = {}
            for line in lines:
                line = line.strip()
                if line.startswith('#>'):
                    try:
                        data = ordered_load(line[2:].strip())
                        if isinstance(data, dict):
                            vars.update(data)
                    except:
                        pass

            finds = [find]
            news = []
            for k in vars:
                kv = '<{}>'.format(k)
                for find in finds:
                    if kv in find:
                        if isinstance(vars[k], (list, tuple)):
                            for var in vars[k]:
                                news.append(find.replace(kv, str(var)))
                        else:
                            news.append(find.replace(kv, str(vars[k])))
                finds = news
                news = []

            return finds

    def find_current_mod(self, pos):
        cursor = self.cursorForPosition(pos)
        doc = self.document()

        mods = doc.toPlainText()
        i = cursor.position()

        limits = []
        for it in re.finditer(r'^[a-z]+:$', mods, flags=re.MULTILINE):
            limits.append(it.start())
        if not limits:
            return
        limits.append(len(mods))

        for s, e in zip(limits[:-1], limits[1:]):
            if s <= i < e:
                break

        lines = mods[s:e].splitlines()
        if lines:
            mod = lines[0].strip()[:-1]
            return mod

    def get_user_selection(self):
        cursor = self.textCursor()
        doc = self.document()

        mods = doc.toPlainText()
        s = cursor.selectionStart()
        e = cursor.selectionEnd()
        selected_text = ''
        if s is not None and e is not None and s < e:
            selected_text = mods[s:e]

        return selected_text

    def duplicate_selection(self, n, suffixes):
        """
        Duplicates the selected text multiple times with custom suffix incrementation.

        The provided suffixes help determine dynamic patterns for numeric (e.g., "part01") or
        alphabetic (e.g., "A1") incrementation.

        Supported patterns:
            - Numeric: Increments found numbers by 1 for each duplication.
            - Alphabetic: Advances alphabetically (e.g., A → B → C ...).
        """
        import re
        import string

        cursor = self.textCursor()
        doc = self.document()

        # Extract selected text
        mods = doc.toPlainText()
        s = cursor.selectionStart()
        e = cursor.selectionEnd()
        selected_text = mods[s:e] if s is not None and e is not None and s < e else mods

        # Clean suffixes
        suffixes = list({suf for suf in suffixes if suf})

        if suffixes:
            def build_num_increment_fn(offset):
                def replacer(match):
                    number = match.group(1)
                    new_number = str(int(number) + offset + 1)
                    return match.group(0).replace(number, new_number)

                return replacer

            def build_alpha_increment_fn(offset):
                def replacer(match):
                    letter = match.group(1)
                    AZ = string.ascii_uppercase
                    new_index = AZ.index(letter) + offset + 1
                    return match.group(0).replace(letter, AZ[new_index])

                return replacer

            numeric_pattern = re.compile(r'([^0-9]*)([0-9]+)([^0-9]*)')
            alpha_pattern = re.compile(r'([^A-Z]*)([A-Z]+)([^A-Z]*)')

            increment_rules = []
            for suffix in suffixes:
                num_match = numeric_pattern.match(suffix)
                if num_match:
                    prefix, _, suffix_part = num_match.groups()
                    regex = re.compile(r'{}([0-9]+){}'.format(re.escape(prefix), re.escape(suffix_part)))
                    increment_rules.append({
                        'regex': regex,
                        'sub_fn': build_num_increment_fn
                    })
                    continue

                alpha_match = alpha_pattern.match(suffix)
                if alpha_match:
                    prefix, _, suffix_part = alpha_match.groups()
                    regex = re.compile(r'{}([A-Z]+){}'.format(re.escape(prefix), re.escape(suffix_part)))
                    increment_rules.append({
                        'regex': regex,
                        'sub_fn': build_alpha_increment_fn
                    })

            # Build and insert duplicates
            full_duplication = []
            for i in range(n):
                txt = selected_text
                for rule in increment_rules:
                    replacer_fn = rule['sub_fn'](i)
                    txt = rule['regex'].sub(replacer_fn, txt)
                full_duplication.append(txt)

            # Insert duplicated text after current selection
            cursor.setPosition(e)
            for dup in full_duplication:
                cursor.insertText('\n' + dup)

    def duplicate_selection_cb(self, mod, text):
        ui = TemplateModDuplicateUI(self, cmd=self.duplicate_selection)
        ui.show()


class TemplateAddWidget(TemplateOpts, OptVarSettings):
    ICON_ADD_ASSET = Icon('cross', color='#fb5', tool=True)
    ICON_ADD = Icon('cross', color='#5bf', tool=True)

    def __init__(self, parent=None):
        TemplateOpts.__init__(self, parent)

        # build template data
        self.template_types = {}
        for tpl in Template.modules:
            tpl, sub = tpl.split('.')
            if tpl.startswith('_') or sub.startswith('_'):
                continue
            if tpl not in self.template_types:
                self.template_types[tpl] = []
            self.template_types[tpl].append(sub)

        # build ui
        self.wd_add = QToolButton()
        self.wd_add.setIcon(self.ICON_ADD)
        self.wd_add.setAutoRaise(True)
        lbl_add = QLabel('Add Module')
        lbl_add.setStyleSheet('color:#789; font-size:12px; font-weight:bold')
        self.wd_name = QLineEdit()

        self.wd_add_asset = QToolButton()
        self.wd_add_asset.setIcon(self.ICON_ADD_ASSET)
        self.wd_add_asset.setAutoRaise(True)
        lbl_add_asset = QLabel('Add Asset')
        lbl_add_asset.setStyleSheet('color:#987; font-size:12px; font-weight:bold')
        self.txt_add_asset = QLineEdit()

        _col = self.add_columns(stretch=[2, 2])
        _row = self.add_row(_col[0])
        _row.addWidget(self.wd_add)
        _row.addWidget(lbl_add)
        _row.addWidget(self.wd_name)

        _row = self.add_row(_col[1])
        _row.addWidget(self.wd_add_asset)
        _row.addWidget(lbl_add_asset)
        _row.addWidget(self.txt_add_asset)

        self.layout_asset = _row.parent()
        if Asset.get_assets():
            self.layout_asset.hide()

        self.wd_type = StringListPlugWidget(label='Type')
        self.wd_subtype = StringListPlugWidget()

        self.wd_number = IntPlugWidget(label='Number', min_value=1, default=1)

        _grid = self.add_grid()

        _grid.addWidget(self.wd_type, 0, 0)
        _grid.addWidget(self.wd_subtype, 1, 0)

        _grid.addWidget(self.wd_number, 0, 1)

        # collapse build/options
        self.box_add = self.add_collapse('Create')
        self.box_opts = self.add_collapse('Options')
        self.box_opts.collapse.set_collapsed(True)

        self.layout.addStretch(1)

        # init
        self.build_wd_type()

        # signals
        self.wd_type.widget.currentIndexChanged.connect(self.build_wd_subtype)
        self.wd_type.widget.currentIndexChanged.connect(self.opt_type_changed)

        self.wd_subtype.widget.currentIndexChanged.connect(self.build_wd_name)
        self.wd_subtype.widget.currentIndexChanged.connect(self.build_box_add)
        self.wd_subtype.widget.currentIndexChanged.connect(self.build_box_opt)
        self.wd_subtype.widget.currentIndexChanged.connect(self.opt_subtype_changed)

    # slots ------------------------------------------------------------------------------------------------------------

    def rebuild(self):
        if self.item is None:
            self.layout_asset.show()
        else:
            self.layout_asset.hide()

    def build_wd_type(self, *args):
        types = sorted(self.template_types)
        priority = ['core', 'default', 'world']
        ordered = [t for t in priority if t in types]
        types = [t for t in types if t not in priority]
        types = ordered + types

        self.wd_type.set_list(types)
        self.wd_type.set_value(0)
        self.build_wd_subtype()

    def build_wd_subtype(self, *args):
        types = self.template_types[self.wd_type.value][:]
        types.sort()
        if 'default' in types:
            types.remove('default')
            types = ['default'] + types

        self.wd_subtype.set_list(types)

        subtype = self.get_optvar('opt_subtype_{}'.format(self.wd_type.value), types[0])
        if subtype in types:
            self.wd_subtype.set_value(subtype)
        else:
            self.wd_subtype.set_value(0)

        self.build_wd_name()
        self.build_box_add()
        self.build_box_opt()

    def get_current_template_modules(self):
        tpl = self.wd_type.value
        sub = self.wd_subtype.value
        tpl = tpl + '.' + sub
        return [Template.modules[tpl]]

    def build_box_add(self):

        # get item
        module = self.get_current_template_modules()[0]
        # if not isinstance(tpl, Template) and tpl == self.last_add_item:
        #     return
        # self.last_add_item = tpl

        # clean
        self.clear_layout(self.box_add)
        self.wd_adds.clear()
        if module is None:
            return

        # get template data
        _grid = self.add_grid(self.box_add)
        row_count = 0
        col_count = 0

        for opt, data in iteritems(module.template_data.get('guides', {})):
            if not isinstance(data, dict) or 'value' not in data:
                continue
            v = data['value']
            dv = v

            enum = data.get('enum')
            vmin = data.get('min')
            vmax = data.get('max')
            presets = data.get('presets')
            yaml = data.get('yaml', False)

            label = data.get('label', opt.capitalize().replace('_', ' '))
            if enum:
                if isinstance(dv, int):
                    dv = enum.values()[dv]
                w = StringListPlugWidget(label=label, default=dv)
                w.set_list(enum.values())
            elif isinstance(v, bool):
                w = BoolPlugWidget(label=label, default=dv)
            elif isinstance(v, int):
                w = IntPlugWidget(label=label, default=dv, min_value=vmin, max_value=vmax)
            elif isinstance(v, float):
                w = FloatPlugWidget(label=label, default=dv, min_value=vmin, max_value=vmax)
            elif isinstance(v, string_types) or yaml:
                w = StringPlugWidget(label=label, default=dv, presets=presets, yaml=yaml)
            elif isinstance(v, list) and len(v) == 3 and all(isinstance(x, (int, float)) for x in v):
                w = VectorPlugWidget(label=label, default=dv, presets=presets)
            else:
                continue

            _grid.addWidget(w, row_count, col_count)
            col_count = 0
            row_count += 1
            self.wd_adds[opt] = w

    def build_wd_name(self, *args):
        module = self.get_current_template_modules()[0]
        name = module.template_data['name']
        self.wd_name.setText(name)

    def opt_type_changed(self):
        pass

    def opt_subtype_changed(self):
        self.set_optvar('opt_subtype_{}'.format(self.wd_type.value), self.wd_subtype.value)


class TemplateLogWidget(StackWidget):

    def __init__(self, parent=None):
        StackWidget.__init__(self, parent)

        _col = self.add_column(margins=0, spacing=1)
        _row = self.add_row(_col, margins=0, spacing=2)

        _lbl = QLabel('Pattern ')
        _row.addWidget(_lbl, stretch=1, alignment=Qt.AlignRight)
        self.pattern_edit = QLineEdit()
        _row.addWidget(self.pattern_edit, stretch=3)
        self.pattern_edit.setMaximumHeight(24)
        self.pattern_edit.returnPressed.connect(self.search_pattern)

        _btn = QPushButton('Search')
        _row.addWidget(_btn, stretch=1)
        _btn.clicked.connect(self.search_pattern)

        _btn = QPushButton('Filter')
        _row.addWidget(_btn, stretch=1)
        _btn.clicked.connect(self.filter_blocks)

        _btn = QPushButton('Reset')
        _row.addWidget(_btn, stretch=1)
        _btn.clicked.connect(self.reset_blocks)

        _btn = QPushButton('Clear')
        _row.addWidget(_btn, stretch=1)
        _btn.clicked.connect(self.clear_text)

        self.log_box = TemplateLogger(self)
        _col.addWidget(self.log_box.widget, stretch=1)

        _log = create_logger()
        _log.handlers = [handler for handler in _log.handlers if not isinstance(handler, TemplateLogger)]
        _log.addHandler(self.log_box)

        self.backup = None

    def clear_text(self):
        self.log_box.widget.document().clear()

    def search_pattern(self):
        doc = self.log_box.widget.document()
        pattern = self.pattern_edit.text()

        cursor = self.log_box.widget.textCursor()
        pos = cursor.selectionEnd()
        cursor = doc.find(pattern, pos)
        if not cursor.hasSelection():
            cursor = doc.find(pattern)

        self.log_box.widget.setTextCursor(cursor)

    def filter_blocks(self):
        self.reset_blocks()
        self.backup = self.log_box.widget.document().toHtml()

        doc = self.log_box.widget.document()
        pattern = self.pattern_edit.text()
        if not pattern:
            return

        block = doc.begin()
        while block.isValid():
            if pattern not in block.text():
                cursor = QtGui.QTextCursor(block)
                block = block.next()
                cursor.select(QtGui.QTextCursor.BlockUnderCursor)
                cursor.removeSelectedText()
            else:
                block = block.next()

    def reset_blocks(self):
        if self.backup is not None:
            self.log_box.widget.document().setHtml(self.backup)
            self.backup = None


class TemplateLogger(SafeHandler):

    def __init__(self, parent):
        super(SafeHandler, self).__init__()

        formatter = get_formatter(name=False)
        self.setFormatter(formatter)

        self.widget = TemplateLoggerTextEdit(parent)

        self.syntax = SyntaxHighlighter(self.widget.document())
        self.syntax.add_styles([
            ('debug', (152, 152, 152)),
            ('info', (70, 155, 200), {'bold': True}),
            ('success', (160, 180, 50), {'bold': True}),
            ('warning', '#ECD790'),
            ('error', '#E69F85'),
            ('critical', '#F54859'),

            ('debug+', (152, 152, 152), {'bold': True}),
            ('info+', (70, 155, 200), {'bold': True}),
            ('success+', (160, 180, 50), {'bold': True}),
            ('warning+', '#F3C93E', {'bold': True}),
            ('error+', '#EB5C28', {'bold': True}),
            ('critical+', (230, 40, 60), {'bold': True}),
        ])
        self.syntax.add_rules([
            (r'^(DEBUG).+', 0, 'debug'),
            # (r'^(INFO).+', 0, 'info'),
            # (r'^(SUCCESS).+', 0, 'success'),
            (r'^(WARNING|Warning).+', 0, 'warning'),
            (r'^(ERROR|Error).+', 0, 'error'),
            (r'^(CRITICAL).+', 0, 'critical'),

            # (r'^(DEBUG)\b', 0, 'debug'),
            (r'^(INFO)\b', 0, 'info'),
            (r'^(SUCCESS)\b', 0, 'success'),
            (r'^(WARNING|Warning)\b', 0, 'warning+'),
            (r'^(ERROR|Error)\b', 0, 'error+'),
            (r'^(CRITICAL)\b', 0, 'critical+'),
        ])

        self._alive = True
        self.widget.destroyed.connect(self._on_destroyed)

    def emit(self, record):
        if self._alive:
            msg = self.format(record)
            msg = msg.replace('<', '&lt;')
            msg = "<p style=\"white-space: pre-wrap;\">" + msg + "</p>"
            self.widget.appendHtml(msg)

    def _on_destroyed(self):
        self._alive = False


class TemplateLoggerTextEdit(QPlainTextEdit):
    FONT_LOGGER = QtGui.QFont('Courier New', 8)
    FONT_LOGGER.setFixedPitch(True)

    def __init__(self, parent):
        QPlainTextEdit.__init__(self, parent)

        self.setReadOnly(True)

        self.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.setFont(TemplateLoggerTextEdit.FONT_LOGGER)

        self.re_node = QtCore.QRegExp(r'[:|_a-zA-z0-9]+')

    def mouseReleaseEvent(self, event):
        key_mod = QApplication.keyboardModifiers()

        if key_mod == Qt.CTRL and event.button() == Qt.LeftButton:
            focus_widget = QApplication.focusWidget()

            cursor = self.textCursor()

            line = cursor.block().text()
            b = cursor.positionInBlock()

            # regex mikan ids
            find = ''
            index = self.re_node.indexIn(line, 0)
            while index >= 0:
                index = self.re_node.pos(0)
                length = len(self.re_node.cap(0))
                if index <= b < index + length:
                    find = line[index:index + length]
                index = self.re_node.indexIn(line, index + length)

            if find and mc.objExists(find):
                mc.select(mc.ls(find))
                tree_widget = self._manager.tree
                items = [x for x in tree_widget.tree_items if isinstance(x, Helper) and (x.has_mod() or x.has_deformer())]

                for item in items:
                    if str(item.node) == find:
                        for _item in tree_widget.selectedItems():
                            _item.setSelected(False)
                        tree_widget.setCurrentItem(tree_widget.tree_items[item])
                        self._manager.update_tabs()
                        self._manager.select_tab_edit()
                        focus_widget.setFocus()
                        break

        QPlainTextEdit.mouseReleaseEvent(self, event)


class TemplateTreeWidget(QTreeWidget):
    ICON_SIZE = QSize(14, 14)
    INDENT_SIZE = 12

    FONT_SIZE = 11
    TREE_STYLE = 'QTreeView {selection-background-color: transparent; font-size: ' + str(FONT_SIZE) + ';}'
    BRUSH_SELECTED_ADD = QtGui.QBrush(QtGui.QColor('#30778899'))
    BRUSH_SELECTED_EDIT = QtGui.QBrush(QtGui.QColor('#30998877'))
    BRUSH_SELECTED = BRUSH_SELECTED_ADD

    sep = os.path.sep
    _path = os.path.abspath(__file__).split(sep)
    _path = sep.join(_path[:-3])
    _path = _path + sep + 'core' + sep + 'ui' + sep + 'pics'
    _path = os.path.join(_path, "capy.png")
    logo = QtGui.QPixmap(_path)

    tree_changed = QtCore.Signal()
    refresh_edit = QtCore.Signal()

    def __init__(self, parent=None):
        QTreeWidget.__init__(self, parent)
        self.setHeaderLabels(['id', 'branches', 'type', 'mode'])
        self.setIconSize(TemplateTreeWidget.ICON_SIZE)
        self.setIndentation(TemplateTreeWidget.INDENT_SIZE)

        header = self.header()
        header.setStretchLastSection(True)

        header.resizeSection(0, 256)
        header.resizeSection(1, 54)
        header.resizeSection(2, 96)
        header.resizeSection(3, 32)

        self._callbacks = {}
        self.tree_items = {}

        # self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.setExpandsOnDoubleClick(False)
        self.doubleClicked.connect(self.select)

        self.setStyleSheet(TemplateTreeWidget.TREE_STYLE)
        self.setFrameShape(QtWidgets.QFrame.NoFrame)

        self.setFocusPolicy(Qt.NoFocus)
        self.setItemDelegate(TemplateTreeDelegate())

        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.context_menu_group)

        self.itemExpanded.connect(self.expand_children)
        self.itemCollapsed.connect(self.collapse_children)
        self.itemExpanded.connect(self.save_expanded)
        self.itemCollapsed.connect(self.save_expanded)

        self.verticalScrollBar().valueChanged.connect(self.force_update)
        self.horizontalScrollBar().valueChanged.connect(self.force_update)

    def drawRow(self, painter, option, index):
        item = self.itemFromIndex(index)

        brush = item.data(0, Qt.UserRole)
        if isinstance(brush, QtGui.QBrush):
            rect = option.rect
            painter.fillRect(rect, brush)

        if self.selectionModel().isSelected(index):
            rect = option.rect
            painter.fillRect(rect, self.BRUSH_SELECTED)

        super(TemplateTreeWidget, self).drawRow(painter, option, index)

    def force_update(self, _):
        self.viewport().update()

    def paintEvent(self, event):
        painter = QtGui.QPainter(self.viewport())
        x = self.viewport().width() - self.logo.width()
        y = self.viewport().height() - self.logo.height()
        painter.drawPixmap(x, y, self.logo)

        QTreeWidget.paintEvent(self, event)

    @busy_cursor
    def load(self):
        # remove registered callbacks
        del _callbacks[:]

        for k in list(self._callbacks):
            for cb in self._callbacks.pop(k):
                try:
                    om.MMessage.removeCallback(cb)
                except:
                    pass
        self._callbacks.clear()

        # store selected item
        selected = None
        index = self.selectedIndexes()
        if index:
            item = self.itemFromIndex(index[0])
            selected = item.item

        # rebuild item list
        self.blockSignals(True)
        self.clear()
        self.tree_items.clear()

        # add assets
        for asset in Asset.get_assets():
            self.add_item(asset)

        # add scene root
        self.add_item(None)

        # add orphan templates
        for tpl in self.get_template_roots():
            asset = Nodes.get_asset_id(tpl.node)
            if not asset:
                self.add_item(tpl)

        # restore selected id
        if selected in self.tree_items:
            self.setCurrentItem(self.tree_items[selected], 1)

        # exit
        self.blockSignals(False)
        self.tree_changed.emit()

    def get_template_roots(self):
        roots = []
        for node in Template.get_all_template_nodes():
            tpl = Template(node)
            if not tpl.get_parent():
                roots.append(tpl)
        return roots

    def add_item(self, item, parent=None, recursive=True, insert=False):

        # convert helper node to deformer group
        if isinstance(item, Helper) and not isinstance(parent, DeformerGroup):
            if item.is_deformer_group() and item.node != parent.node:
                item = DeformerGroup(item.node, dry=True)

        # scene root?
        if item is None:
            if None in self.tree_items:
                return self.tree_items[None]
            tree_item = TemplateTreeItem(None)
            self.tree_items[None] = tree_item
            self.addTopLevelItem(tree_item)
            self.expandItem(tree_item)
            return tree_item

        # build item
        tree_item = TemplateTreeItem(item)
        self.tree_items[item] = tree_item

        if isinstance(parent, TemplateHook):
            parent = parent.template

        if parent in self.tree_items and not isinstance(item, Asset):
            parent = self.tree_items[parent]
            if insert:
                parent.insertChild(0, tree_item)
            else:
                parent.addChild(tree_item)
        else:
            self.addTopLevelItem(tree_item)

        # find children
        do_parent = False

        if isinstance(item, Asset):
            self.setCurrentItem(tree_item, 1)

            for helper in item.get_helper_nodes():
                self.add_item(helper, parent=item)

            for tpl in item.get_top_templates():
                self.add_item(tpl, parent=item)

            for helper in item.get_top_templates_branch_edits():
                self.add_item(helper, parent=item)

        elif isinstance(item, Helper):
            if 'gem_type' not in item.node:  # skip children if helper is already a template
                if recursive:
                    for helper in item.get_children():
                        self.add_item(helper, parent=item)

                    tpl = Template.get_from_node(item.node)
                    if not tpl:
                        for tpl in item.get_child_templates():
                            self.add_item(tpl, parent=item)

                do_parent = True

            else:
                if item.is_branch_edit():
                    tpl = Template.get_from_node(item.node)
                    if tpl:
                        for node in tpl.get_template_branch_edits(root=item.node):
                            helper = Helper(node)
                            self.add_item(helper, parent=item)

        elif isinstance(item, DeformerGroup):
            _item = Helper(item.node)
            for helper in _item.get_children():
                self.add_item(helper, parent=item)

            if _item.has_deformer():
                self.add_item(_item, parent=item)
            do_parent = True

        elif isinstance(item, Template):
            helper_nodes = []
            for node in item.get_template_nodes():
                helper = Helper(node)
                if helper.is_protected():
                    continue
                elif helper.is_branch() or helper.is_branch_edit():
                    continue
                    # helper_branches.append(helper)
                elif helper.is_hidden() and not helper.is_shape():
                    helper_nodes.append(helper)
                elif not helper.is_hidden() and helper.has_mod():
                    helper_nodes.append(helper)

            helper_branches = []
            for node in item.get_template_branch_edits():
                helper = Helper(node)
                helper_branches.append(helper)

            _nodes = [helper.node for helper in helper_nodes if helper.node != item.node]
            for helper in helper_nodes:
                if helper.node.parent() not in _nodes:
                    self.add_item(helper, parent=item)

            for child in item.get_children():
                item_parent = item
                helper = Helper(child.node.parent())
                if helper.is_hidden():
                    item_parent = helper
                self.add_item(child, parent=item_parent)

            for helper in helper_branches:
                self.add_item(helper, parent=item)

            do_parent = True

        if tree_item.is_expanded():
            self.expandItem(tree_item)
        if isinstance(item, DeformerGroup):
            self.collapseItem(tree_item)

        self.tree_changed.emit()
        self.attach_item(tree_item, do_parent=do_parent)
        return tree_item

    def get_selected_tree_item(self):
        index = self.selectedIndexes()
        if index:
            return self.itemFromIndex(index[0])

    def get_selected_tree_items(self):
        ids = set()
        items = []
        for i in self.selectedIndexes() or []:
            _id = i.internalId()
            if _id in ids:
                continue
            ids.add(_id)

            item = self.itemFromIndex(i)
            items.append(item)
        return items

    def get_selected_item(self):
        item = self.get_selected_tree_item()
        return item.item if item else None

    def get_selected_items(self):
        return [item.item for item in self.get_selected_tree_items() if item]

    def get_asset_from_selection(self):
        item = self.get_selected_item()
        if isinstance(item, Asset):
            return item
        elif isinstance(item, (Template, Helper, DeformerGroup)):
            asset_id = Nodes.get_asset_id(item.node)
            node = Nodes.get_id('::asset', asset=asset_id)
            return Asset(node)

    def delete_selected_items(self):

        self.blockSignals(True)

        remove_items = []
        for tree_item in self.get_selected_tree_items():
            item = tree_item.item

            if isinstance(item, (Template, Helper, DeformerGroup, Asset)):
                if item.node.isReferenced():
                    continue

                if isinstance(item, (Template, DeformerGroup, Asset)):
                    remove_items.append(item)
                elif isinstance(item, Helper):
                    if item.is_hidden():
                        remove_items.append(item)

                self.delete_tree_item(tree_item)

        for item in remove_items:
            try:
                item.remove()
            except:
                pass

        self.blockSignals(False)
        self.tree_changed.emit()

    def delete_tree_item(self, item):
        if item.item in self.tree_items:
            del self.tree_items[item.item]

        try:
            (item.parent() or self.invisibleRootItem()).removeChild(item)
        except:
            pass

        try:
            self.tree_changed.emit()
        except:
            pass

    def select(self, index):
        item = self.itemFromIndex(index).item

        if isinstance(item, (Template, Helper, Asset, DeformerGroup)):
            try:
                mc.select(str(item.node))
            except:
                self.load()

    def save_expanded(self, item):
        if item.item is None:
            return
        node = item.item.node
        if node.is_referenced():
            return
        node['ui_expanded'] = item.isExpanded()

    def get_children(self, root):
        for i in range(root.childCount()):
            item = root.child(i)
            yield item
            for child in self.get_children(item):
                yield child

    def expand_children(self, item):
        modifiers = QApplication.keyboardModifiers()
        if modifiers == Qt.ShiftModifier:
            for child in self.get_children(item):
                if isinstance(item, Helper) and item.is_deformer_group():
                    continue
                else:
                    self.expandItem(child)

    def collapse_children(self, item):
        modifiers = QApplication.keyboardModifiers()
        if modifiers == Qt.ShiftModifier:
            for child in self.get_children(item):
                self.collapseItem(child)

    # API callbacks ----------------------------------------------------------------------------------------------------
    def attach_item(self, tree_item, do_parent=True):

        item = tree_item.item
        if isinstance(item, (Template, Helper, Asset, DeformerGroup, TemplateHook)):
            m_obj = item.node.object()
            m_dag = item.node.dag_path()

            self._callbacks[item] = []
            cb = om.MNodeMessage.addNodePreRemovalCallback(m_obj, partial(self.on_delete_item, item))
            self._callbacks[item].append(cb)
            _callbacks.append(cb)

            if do_parent:
                cb = om.MDagMessage.addParentAddedDagPathCallback(m_dag, partial(self.on_parent_item, item))
                self._callbacks[item].append(cb)
                _callbacks.append(cb)

    def on_delete_item(self, *args):
        item = args[0]

        if isinstance(item, Template):
            asset = Nodes.get_asset_id(item.node)
            name = item.name
            if asset in Nodes.nodes and name in Nodes.nodes[asset]:
                del Nodes.nodes[asset][name]

        if item in self._callbacks:
            for cb in self._callbacks.pop(item):
                om.MMessage.removeCallback(cb)
                if cb in _callbacks:
                    _callbacks.remove(cb)

        del_item = self.tree_items.get(item)
        if del_item:
            self.delete_tree_item(del_item)

    def on_parent_item(self, *args):
        item = args[0]

        parent_item = None
        tree_item = self.tree_items.get(item)
        if not tree_item:
            return

        # find parent
        helper = None
        _parent = item.node.parent()
        if _parent:
            helper = Helper(_parent)

        if isinstance(item, Template):
            parent = item.get_parent()
            if parent:
                parent_item = self.tree_items.get(parent)

        if not parent_item:
            if isinstance(item, Helper):
                tpl = Template.get_from_node(item.node)
                if tpl:
                    parent_item = self.tree_items.get(tpl)
            elif helper:
                parent_item = self.tree_items.get(helper)

            if not parent_item:
                asset = Nodes.get_asset_id(item.node)
                if asset:
                    _node = Nodes.get_id('::asset', asset=asset)
                    parent_item = self.tree_items.get(Asset(_node))

        # reparent widget
        if isinstance(item, DeformerGroup) and not parent_item:
            self.invisibleRootItem().removeChild(tree_item)
            return

        old_parent = tree_item.parent()
        if not old_parent:
            old_parent = self.invisibleRootItem()
        i = old_parent.indexOfChild(tree_item)
        old_parent.takeChild(i)

        if parent_item:
            parent_item.addChild(tree_item)
        else:
            self.tree_items[None].addChild(tree_item)

        try:
            if tree_item.is_expanded():
                self.expandItem(tree_item)
        except:
            pass

    # toolbox menu -----------------------------------------------------------------------------------------------------
    def context_menu_group(self, point):
        index = self.indexAt(point)
        if not index.isValid():
            return

        items = self.get_selected_items()

        # check conditions
        types = [Template if issubclass(type(item), Template) else type(item) for item in items]
        mixed = not all([types[0] == t for t in types[1:]])
        single = len(items) == 1
        has_asset = Asset in types
        has_template = Template in types
        has_helper = Helper in types
        has_mod = any([item.has_mod for item in items if isinstance(item, Helper)])
        has_hook = TemplateHook in types
        has_branch = any([item.is_branch() or item.is_branch_edit() for item in items if isinstance(item, Helper)])

        locked = False
        if single and (has_asset or has_template or has_helper):
            locked = items[0].node.isReferenced()

        # build menu
        menu = QMenu(self)

        if not has_hook:
            _act = menu.addAction('Remove')
            _act.triggered.connect(self.delete_selected_items)

        if single and (has_asset or has_template):
            _act = menu.addAction('Scale')
            _act.triggered.connect(Callback(self.scale_item, items[0]))
            menu.addSeparator()

        if single and (has_asset or has_template or has_hook) and not has_branch:
            _act = menu.addAction('Add helper node')
            _act.triggered.connect(self.create_helper_node)

        if single and (has_helper or has_template or has_hook) and not locked and not has_branch:
            mod_menu = menu.addMenu('Add modifier')
            _act = mod_menu.addAction('(empty)')
            _act.triggered.connect(partial(self.create_mod, ''))

            mods = ordered_dict(sorted(Mod.modules.items()))

            for mod, v in mods.items():
                _act = mod_menu.addAction(mod)
                _act.triggered.connect(partial(self.create_mod, v))

        if has_mod and not locked and not has_branch:
            _act = menu.addAction('Modifiers: Search and replace')
            _act.triggered.connect(self.note_search_and_replace_cb)

        if not mixed and has_template:

            menu.addSeparator()
            _act = menu.addAction('Duplicate')
            _act.triggered.connect(self.duplicate_cb)

            _act = menu.addAction('Rename: Search and replace')
            _act.triggered.connect(self.name_search_and_replace_cb)

            if single:
                menu.addSeparator()
                _act = menu.addAction('Build branches template')
                _act.triggered.connect(Callback(self.build_branches))

            _act = menu.addAction('Add shapes')
            _act.triggered.connect(Callback(self.add_shapes))

            menu.addSeparator()
            _act = menu.addAction('Select skin joints')
            _act.triggered.connect(Callback(self.select_rig_nodes, 'skin'))

            _act = menu.addAction('Select skin joints hierarchy')
            _act.triggered.connect(Callback(self.select_rig_nodes, 'skin', hierarchy=True))

            menu.addSeparator()
            _act = menu.addAction('Select controllers')
            _act.triggered.connect(Callback(self.select_rig_nodes, 'ctrls'))

            _act = menu.addAction('Select controllers hierarchy')
            _act.triggered.connect(Callback(self.select_rig_nodes, 'ctrls', hierarchy=True))

        if single and has_template:
            menu.addSeparator()

            wiki = items[0].template_data.get('help')
            if wiki:
                _act = menu.addAction('Help: {}'.format(items[0].template))
                _act.triggered.connect(partial(open_url, wiki))

            _act = menu.addAction('Help: Blueprints')
            _act.triggered.connect(partial(open_url, 'https://citrus-software.github.io/mikan-docs/usage/blueprints'))

        menu.exec_(QtGui.QCursor.pos())

    def duplicate_template(
            self,
            n,
            pattern,
            incr_suffix,
            inverse_incrementation_order,
            replace,
            apply_transform_from_selection,
            do_mirror_x,
            do_mirror_y,
            do_mirror_z
    ):

        # get duplicate transform from selection
        m_base = None
        m_delta_incr = None
        if apply_transform_from_selection:
            user_selection = mx.ls(selection=True)
            if len(user_selection) < 2:
                log.error("Duplicate: You must select at least 2 transforms")
                return

            m_base = user_selection[0]['wm'][0].as_matrix()
            m_target = user_selection[1]['wm'][0].as_matrix()
            m_delta_incr = m_target * m_base.inverse()

        m_mirror = None
        if do_mirror_x or do_mirror_y or do_mirror_z:
            n = 1
            user_selection = mx.ls(selection=True)
            if len(user_selection) < 1:
                log.error("Duplicate mirror: You must select at least 1 transform")
                return

            m_mirror = user_selection[0]['wm'][0].as_matrix()

        i_step = 1
        if inverse_incrementation_order:
            i_step *= -1

        # Analyse incr pattern
        incr_suffix_info = {}
        if incr_suffix:
            m = re.match(r'([0-9]+|[A-Z]+)(?P<to_match>.*)', incr_suffix[::-1])
            if m:
                incr_suffix_info = {'to_incr': m.group(1)[::-1], 'to_match': m.group(2)[::-1]}
            else:
                log.error('Invalid incrementation suffix: "{}"'.format(incr_suffix))
                return

        # process
        for item in self.get_selected_items():
            if not isinstance(item, Template):
                return

            i_offset = 1

            m_current = None
            m_delta = None
            if apply_transform_from_selection:
                m_current = m_base
                m_delta = item.node['wm'][0].as_matrix() * m_base.inverse()

            for i in range(n):

                d = mc.duplicate(str(item.node), rr=1, rc=1)
                d = mx.encode(d[0])

                nodes = [d] + list(d.descendents())
                nodes = [node for node in nodes if node.is_a(mx.kTransform)]
                tpl_d = Template(d)

                for tpl in [tpl_d] + tpl_d.get_all_children():
                    old_id = tpl.name
                    new_id = old_id

                    if incr_suffix:

                        if incr_suffix_info['to_incr'].isdigit():
                            num_padding = len(incr_suffix_info['to_incr'])
                            incr_current = str(int(incr_suffix_info['to_incr']) + i * i_step + i_offset * i_step).rjust(num_padding, '0')
                        else:
                            num_padding = len(incr_suffix_info['to_incr'])
                            letters_list = string.ascii_uppercase
                            if num_padding > 1:
                                letters_list = list(map(lambda x: ''.join(x), itertools.product(string.ascii_uppercase, repeat=num_padding)))
                            i_current = letters_list.index(incr_suffix_info['to_incr']) + i * i_step + i_offset * i_step
                            incr_current = letters_list[i_current]

                        new_id = old_id.replace(
                            incr_suffix_info['to_match'] + incr_suffix_info['to_incr'],
                            incr_suffix_info['to_match'] + incr_current
                        )

                        new_id = Template.get_next_unique_name(new_id, nodes[0])

                    if replace and pattern:
                        # Search pattern to increment
                        split_tmp = new_id.split(pattern)
                        before = pattern.join(split_tmp[:-1])
                        after = split_tmp[-1]

                        new_id = before + replace + after
                        new_id = Template.get_next_unique_name(new_id, nodes[0])

                    for node in nodes:
                        if 'gem_id' in node:
                            Nodes.rename_plug_ids(node['gem_id'], old_id, new_id)
                        if 'gem_hook' in node:
                            Nodes.rename_plug_ids(node['gem_hook'], old_id, new_id)
                        if 'gem_shape' in node:
                            Nodes.rename_plug_ids(node['gem_shape'], old_id, new_id)
                        if 'notes' in node:
                            Nodes.rename_cfg_ids(node, old_id, new_id)

                    tpl.rename_root()
                    Nodes.rebuild()

                    # transform op
                    if apply_transform_from_selection:
                        m_current = m_delta_incr * m_current
                        apply_transform(tpl.node, m_delta * m_current)

                    if do_mirror_x or do_mirror_y or do_mirror_z:
                        mirror_axis = 0
                        if do_mirror_x:
                            mirror_axis = 0
                        elif do_mirror_y:
                            mirror_axis = 1
                        elif do_mirror_z:
                            mirror_axis = 2

                        m = item.node['wm'][0].as_matrix()
                        dot_product_max = 0
                        axis_to_inverse = None

                        get_row = lambda mat, row_index: mx.Vector(mat[row_index * 4], mat[row_index * 4 + 1], mat[row_index * 4 + 2])

                        for k in range(3):
                            dot_product = abs(get_row(mirror_axis, m_mirror) * get_row(k, m))
                            if dot_product_max < dot_product:
                                dot_product_max = dot_product
                                axis_to_inverse = k

                        # compute new position
                        m_local = m * m_mirror.inverse()
                        x_local = get_row(m_local, 0)
                        y_local = get_row(m_local, 1)
                        z_local = get_row(m_local, 2)
                        p_local = get_row(m_local, 3)

                        if axis_to_inverse == 0:
                            x_local *= -1
                        elif axis_to_inverse == 1:
                            y_local *= -1
                        elif axis_to_inverse == 2:
                            z_local *= -1

                        x_local[mirror_axis] *= -1
                        y_local[mirror_axis] *= -1
                        z_local[mirror_axis] *= -1
                        p_local[mirror_axis] *= -1

                        m_local[0], m_local[1], m_local[2] = x_local
                        m_local[4], m_local[5], m_local[6] = y_local
                        m_local[8], m_local[9], m_local[10] = z_local
                        m_local[12], m_local[13], m_local[14] = p_local

                        apply_transform(tpl.node, m_local * m_mirror)

                self.add_item(tpl_d, tpl_d.get_parent())

    def name_search_and_replace(self, pattern, replace):

        for item in self.get_selected_items():
            if not isinstance(item, Template):
                return

            n = item.node
            nodes = [n] + list(n.descendents())
            nodes = [node for node in nodes if node.is_a(mx.kTransform)]

            tpl_d = Template(item.node)

            # Search pattern to increment
            old_id = tpl_d.name
            split_tmp = old_id.split(pattern)
            before = pattern.join(split_tmp[:-1])
            after = split_tmp[-1]

            new_id = before + replace + after
            new_id = Template.get_next_unique_name(new_id, nodes[0])

            tpl_d.rename(new_id)
            tpl_d.rename_root()
            tpl_d.rename_template()
            Nodes.rebuild()

        Nodes.rebuild()
        self.load()  # update_tree_items()

    def mod_search_and_replace(self, pattern, replace):
        nodes = []

        for item in self.get_selected_items():
            n = item.node
            if n not in nodes:
                nodes.append(n)

        # nodes = [n]  # + list(n.descendents())
        nodes = [node for node in nodes if node.is_a(mx.kTransform)]
        if not nodes:
            return

        log.info('replace "{}" by "{}" in modifiers'.format(pattern, replace))
        for node in nodes:
            lines = node['notes'].read() or ''
            if not lines:
                continue
            split_lines = lines.split(pattern)
            count = len(split_lines) - 1
            lines = replace.join(split_lines)
            with mx.DGModifier() as md:
                md.set_attr(node['notes'], lines)

            log.info('{}: {} occurrence'.format(node, count) + 's' if count > 1 else '')

        # refresh ui
        w = self.find_edit_tab_widget()
        if w:
            w.build_box_mod()

    def find_edit_tab_widget(self):
        w = self.parent()

        while w is not None:
            if hasattr(w, 'tab_edit'):
                return w.tab_edit
            w = w.parent()

        return None

    def duplicate_cb(self):
        ui = TemplateDuplicateUI(self, cmd=self.duplicate_template)
        ui.show()

    def name_search_and_replace_cb(self):
        win = TemplateRenamerUI(self, cmd=self.name_search_and_replace)
        win.show()

    def note_search_and_replace_cb(self):
        ui = TemplateModRenamerUI(self, cmd=self.mod_search_and_replace)
        ui.show()

    def add_shapes(self):
        for item in self.get_selected_items():
            if isinstance(item, Template):
                item.add_shapes()

    @busy_cursor
    def build_branches(self):
        item = self.get_selected_item()
        if not isinstance(item, Template):
            return

        with SafeUndoInfo():
            Nodes.rebuild()
            roots = item.build_template_branches()  # TODO: transférer tout ça dans Template.build_branches_edit()
            for root in roots:
                root = Template.set_branch_edit(root)
                if root:
                    helper = Helper(root)

                    if not helper.is_branch_root():
                        continue

                    tpl = Template.get_from_node(root)
                    parent = tpl.get_parent()
                    if parent is None:  # no parent -> asset?
                        asset_id = Nodes.get_asset_id(root)
                        asset = Nodes.get_id(asset_id + '#::asset')
                        if asset:
                            parent = Asset(asset)

                    self.add_item(helper, parent)

    def select_rig_nodes(self, tag, hierarchy=False):
        templates = []
        for item in self.get_selected_items():
            if isinstance(item, Template):
                templates.append(item)

        nodes = Asset.get_rig_nodes(tag, templates=templates, hierarchy=hierarchy)
        if nodes:
            mx.cmd(mc.select, nodes)

    # template utils -----------------------------------------------------------

    def create_helper_node(self):
        item = self.get_selected_item()
        if isinstance(item, (Asset, Helper, Template, TemplateHook)):
            parent = item.node
            if isinstance(item, Asset):
                parent = item.get_template_root()

            with mx.DagModifier() as md:
                node = md.create_node(mx.tTransform, parent=parent, name='_node#')
            helper = Helper(node)

            if isinstance(item, TemplateHook):
                item = item.template

            self.add_item(helper, parent=item)
            self.setCurrentItem(self.tree_items[helper], 1)
            self.refresh_edit.emit()

    def create_mod(self, mod):
        item = self.get_selected_item()
        if isinstance(item, (Helper, Template, TemplateHook)):
            cfg = ConfigParser(item.node)
            if mod:
                mod = mod.sample.strip('\n') + '\n'
            data = cfg['mod'].read() or ''
            data.strip('\n')
            if data:
                data += '\n\n'
            cfg['mod'].write(data + mod)

            if isinstance(item, (Template, TemplateHook)):
                helper = Helper(item.node)
                if isinstance(item, TemplateHook):
                    item = item.template
                self.add_item(helper, parent=item)
                self.setCurrentItem(self.tree_items[helper], 1)
            else:
                self.tree_items[item].update()
                self.setCurrentItem(self.tree_items[item], 1)
            self.refresh_edit.emit()

    @staticmethod
    def scale_item(item):
        if not isinstance(item, (Asset, Template)):
            return

        mc.promptDialog(message='Scale:', button='OK', defaultButton='OK')
        scale = mc.promptDialog(q=1, text=1)
        if re_is_float.match(scale):
            scale = float(scale)
        else:
            return

        with BusyCursor():
            node = item.node
            if isinstance(item, Asset):
                node = item.get_template_root()

            Helper(node).scale(scale)


class TemplateTreeDelegate(QItemDelegate):
    role_highlighted = get_palette_role('HighlightedText')
    role_foreground = get_palette_role('Text')

    def __init__(self, parent=None, *args):
        QItemDelegate.__init__(self, parent, *args)

    def paint(self, painter, option, index):

        # foreground color highlight
        palette = option.palette

        w = option.styleObject
        item = w.itemFromIndex(index)
        if item.isSelected():
            color = item.foreground(index.column()).color()
            if color == Qt.black:
                color = palette.color(self.role_foreground)
            palette.setColor(self.role_highlighted, color.lighter())

        option.palette = palette
        QItemDelegate.paint(self, painter, option, index)


class TemplateTreeItem(QTreeWidgetItem):
    ICONS = {}
    ICON_ROOT = Icon('world', size=16, color='#888')
    ICON_ASSET = Icon('box', size=16, color='#fb5')
    ICON_GRAPH = Icon('tree', size=16, color='#999')
    ICON_BRANCH = Icon('tree', size=16, color='#39d')
    ICON_MODIFIER = Icon('gear', size=16, color='#b5f')
    ICON_DEFORMER = Icon('gear', size=16, color='#bf5')
    ICON_DEFORMER_GROUP = Icon('group', size=16, color='#bf5')
    ICON_HOOK = Icon('cross', size=8, color='#777')

    BRUSH_ASSET = QtGui.QBrush(QtGui.QColor("#987"))
    BRUSH_TEMPLATE = QtGui.QBrush(QtGui.QColor('#789'))
    BRUSH_MODIFIER = QtGui.QBrush(QtGui.QColor("#879"))
    BRUSH_DEFORMER = QtGui.QBrush(QtGui.QColor("#897"))
    BRUSH_GRAPH = QtGui.QBrush(QtGui.QColor("#888"))

    BRUSH_TEXT = QtGui.QBrush(QtGui.QColor("#ccc"))
    BRUSH_DISABLED = QtGui.QBrush(QtGui.QColor("#666"))
    BRUSH_INVALID = QtGui.QBrush(QtGui.QColor('#e00'))

    BRUSH_REF = QtGui.QBrush(QtGui.QColor("#ca7"))
    BRUSH_REF_BG = QtGui.QBrush(QtGui.QColor("#10ccaa77"))

    def __init__(self, item, parent=None):
        QTreeWidgetItem.__init__(self, parent)
        self.item = item
        self.ref = False
        if isinstance(item, (Asset, Helper, Template, DeformerGroup)):
            self.ref = item.node.is_referenced()

        if item is not None:
            node = item.node
            if 'ui_expanded' not in node:
                node.add_attr(mx.Boolean('ui_expanded', default=True))

        self.update()

    def __eq__(self, other):
        if not isinstance(other, TemplateTreeItem):
            return False
        if self.item == other.item:
            return True
        return False

    def __hash__(self):
        return hash(self.item) ^ hash(TemplateTreeItem)

    def update(self, rebuild=False):
        item = self.item

        icon = None
        if isinstance(item, Template):
            name = item.name
            self.setText(0, name)
            try:
                self.setText(1, ', '.join(item.get_opt('branches')))
                self.setForeground(1, self.BRUSH_TEXT)
            except:
                self.setText(1, str(item.get_opt('branches')))
                self.setForeground(1, self.BRUSH_INVALID)

            tpl_module = item.template
            if tpl_module == 'core._unknown':
                self.setText(2, item.node['gem_module'].read())
                self.setForeground(2, self.BRUSH_INVALID)
            else:
                self.setText(2, item.template)
                self.setForeground(2, self.BRUSH_TEMPLATE)

            ui_data = item.template_data.get('ui', {})
            icon_name = ui_data.get('icon', 'locator')
            icon = self.ICONS.get(icon_name)
            if icon is None:
                icon = Icon(icon_name, size=16, color='#5bf')
                self.ICONS[icon_name] = icon

            modes = Helper(item).get_enable_modes()
            self.setText(3, modes)

        elif isinstance(item, TemplateHook):
            self.setText(0, item.name)
            self.setText(2, 'Hook')
            self.setForeground(2, self.BRUSH_GRAPH)
            icon = self.ICON_HOOK

        elif isinstance(item, Asset):
            self.setText(0, item.name)
            self.setText(2, 'Asset')
            icon = self.ICON_ASSET
            self.setForeground(2, self.BRUSH_ASSET)

        elif isinstance(item, Helper):
            self.setText(0, item.name)
            if item.has_mod():
                self.setText(2, 'Modifiers')
                icon = self.ICON_MODIFIER
                self.setForeground(2, self.BRUSH_MODIFIER)
            elif item.has_deformer():
                self.setText(2, 'Deformers')
                icon = self.ICON_DEFORMER
                self.setForeground(2, self.BRUSH_DEFORMER)
            elif item.is_branch():
                name = Nodes.get_node_id(item.node, find='branch')
                name = name.split('::')[0]
                self.setText(0, name)
                self.setText(2, 'Branch Build')
                icon = self.ICON_BRANCH
                self.setForeground(2, self.BRUSH_TEMPLATE)
            elif item.is_branch_edit():
                name = Nodes.get_node_id(item.node, find='edit')
                name = name.split('::')[0]
                self.setText(0, name)
                self.setText(2, 'Branch')
                icon = self.ICON_BRANCH
                self.setForeground(2, self.BRUSH_GRAPH)
            else:
                self.setText(2, 'Helper')
                icon = self.ICON_GRAPH
                self.setForeground(2, self.BRUSH_GRAPH)

                modes = item.get_enable_modes()
                self.setText(3, modes)

        elif isinstance(item, DeformerGroup):
            self.setText(0, item.name)
            self.setText(2, 'Deformer Group')
            icon = self.ICON_DEFORMER_GROUP
            self.setForeground(2, self.BRUSH_DEFORMER)

            modes = Helper(item).get_enable_modes()
            self.setText(3, modes)

        elif item is None:
            self.setText(0, 'scene root')
            icon = self.ICON_ROOT

        if icon is not None:
            self.setIcon(0, icon)

        # reference?
        if self.ref:
            self.setForeground(0, self.BRUSH_REF)
            self.setData(0, Qt.UserRole, self.BRUSH_REF_BG)

        # disabled?
        disabled = False
        if isinstance(item, Template):
            disabled = not Helper(item.node).get_enable()
        if isinstance(item, Helper):
            disabled = not item.get_enable()
        if isinstance(item, DeformerGroup):
            _helper = Helper(item.node)
            disabled = not _helper.get_enable()

        if disabled:
            self.setForeground(0, self.BRUSH_DISABLED)
        elif not self.ref:
            self.setForeground(0, self.BRUSH_TEXT)
        if isinstance(item, TemplateHook):
            self.setForeground(0, self.BRUSH_DISABLED)

        # invalid?
        if isinstance(item, Template):
            if not item.check_validity(rebuild=rebuild):
                [self.setForeground(i, self.BRUSH_INVALID) for i in range(self.columnCount())]

    def is_expanded(self):
        expanded = True
        node = self.item.node
        if 'ui_expanded' in node and not node['ui_expanded'].read():
            expanded = False
        return expanded


class TemplateHook(object):

    def __init__(self, tpl, name, node):
        self.name = name
        self.template = tpl
        self.node = node


class TemplateModInspector(QTreeWidget):
    tree_changed = QtCore.Signal()
    refresh_edit = QtCore.Signal()

    BRUSH_ID = QtGui.QBrush(QtGui.QColor('#abd7fe'))
    FONT = QtGui.QFont('courier new', 9)
    FONT.setFixedPitch(True)

    def __init__(self, parent=None):
        QTreeWidget.__init__(self, parent)

        self.setFrameStyle(QtWidgets.QFrame.Box | QtWidgets.QFrame.Plain)
        self.setFocusPolicy(Qt.NoFocus)

        self.setFont(TemplateModInspector.FONT)
        self.setIndentation(8)

        header = self.header()
        header.hide()
        self.hide()

        # data
        self.editor = None

        # connections
        self.setExpandsOnDoubleClick(False)
        self.doubleClicked.connect(self.copy_paste)

        self.destroyed.connect(TemplateModInspector._on_destroyed)

        # build inspector callback
        cb = __main__.__dict__.get('_mikan_mod_inspector')
        if cb:
            try:
                om.MCommandMessage.removeCallback(cb)
            except:
                pass
        __main__._mikan_mod_inspector = om.MEventMessage.addEventCallback('SelectionChanged', self.maya_selection_changed)

        _callbacks.append(cb)

    def maya_selection_changed(self, *args):
        if not self.editor.isVisible():
            return
        self.update_display()

    def update_display(self):
        self.blockSignals(True)
        self.clear()

        nodes = []
        sl = om.MGlobal.getActiveSelectionList(True)
        for i in range(sl.length()):
            obj = sl.getDependNode(i)
            try:
                nodes.append(mx.Node(obj))
            except:
                pass

        hide = True
        for node in nodes:
            if 'gem_id' in node:
                node_item = QTreeWidgetItem()
                node_item.setText(0, str(node))
                self.addTopLevelItem(node_item)
                self.expandItem(node_item)

                ids = node['gem_id'].read()
                for i in ids.split(';'):
                    if not i:
                        continue
                    id_item = QTreeWidgetItem(i)
                    id_item.setText(0, i)
                    id_item.setForeground(0, self.BRUSH_ID)
                    node_item.addChild(id_item)
                hide = False

            elif node.is_a(mx.tTransform):
                parents = []
                parent = node.parent()
                while parent:
                    parents.append(parent)
                    parent = parent.parent()

                if parents and not any(['gem_id' in _node for _node in parents]):
                    node_item = QTreeWidgetItem()
                    node_item.setText(0, str(node))
                    self.addTopLevelItem(node_item)
                    self.expandItem(node_item)

                    ids = Deformer.get_deformer_ids(node, parents[0])
                    name = Deformer.get_unique_name(node, parents[0])
                    for i in ids:
                        _name = name + '->' + i
                        id_item = QTreeWidgetItem(_name)
                        id_item.setText(0, _name)
                        id_item.setForeground(0, self.BRUSH_ID)
                        node_item.addChild(id_item)
                    hide = False

        if hide:
            self.hide()
        else:
            self.show()

        self.blockSignals(False)

    def copy_paste(self):
        index = self.selectedIndexes()
        if index:
            item = self.itemFromIndex(index[0])
            text = item.text(0)

            if not text or ('::' not in text and '->' not in text):
                return

            cursor = self.editor.textCursor()
            pos = cursor.selectionStart()
            if pos == 0:
                doc_txt = self.editor.toPlainText()
                pos = len(doc_txt)
                cursor.setPosition(pos)
                self.editor.setTextCursor(cursor)

            clipboard = QApplication.clipboard()
            clipboard.setText(text)
            self.editor.paste()

            self.editor.setFocus()

    @staticmethod
    def _on_destroyed():
        cb = __main__.__dict__.get('_mikan_mod_inspector')
        if cb:
            try:
                om.MCommandMessage.removeCallback(cb)
            except:
                pass


class TemplateDuplicateUI(MayaWindow):

    def __init__(self, parent=None, cmd=None):
        MayaWindow.__init__(self, parent)

        self.cmd = cmd

        self.setWindowTitle("Duplicate templates")
        self.setMaximumHeight(32)

        self.spin_n = QSpinBox()
        self.spin_n.setMinimum(1)
        self.spin_n.setValue(1)

        self.edit_pattern = QLineEdit()
        self.edit_suffix = QLineEdit('1')
        self.edit_replace = QLineEdit()

        # self.apply_transform_from_selection_ui_value = QCheckBox("Apply transform from selection")
        # self.apply_mirrorX_from_selection_ui_value = QCheckBox("Apply mirror X from selection")
        # self.apply_mirrorY_from_selection_ui_value = QCheckBox("Apply mirror Y from selection")
        # self.apply_mirrorZ_from_selection_ui_value = QCheckBox("Apply mirror Z from selection")

        container_reverse = QWidget()
        _layout = QVBoxLayout(container_reverse)
        _layout.setContentsMargins(3, 1, 0, 1)
        self.chk_inverse = QCheckBox()
        _layout.addWidget(self.chk_inverse)

        btn_duplicate = QPushButton('Duplicate')
        btn_duplicate.clicked.connect(self.do_cmd)

        # btn_help = QPushButton("Help")
        # btn_help.clicked.connect(self.help_)

        layout = QGridLayout()
        layout.setSpacing(2)
        layout.setMargin(3)

        layout.addWidget(QLabel(' Copies: '), 0, 0, alignment=Qt.AlignRight)
        layout.addWidget(self.spin_n, 0, 1)
        # layout.addWidget(self.apply_transform_from_selection_ui_value, 1, 0)
        # layout.addWidget(self.apply_mirrorX_from_selection_ui_value, 2, 0)
        # layout.addWidget(self.apply_mirrorY_from_selection_ui_value, 3, 0)
        # layout.addWidget(self.apply_mirrorZ_from_selection_ui_value, 4, 0)

        layout.addWidget(QLabel(' Suffix: '), 5, 0, alignment=Qt.AlignRight)
        layout.addWidget(self.edit_suffix, 5, 1)
        layout.addWidget(QLabel(' Reverse: '), 6, 0, alignment=Qt.AlignRight)
        layout.addWidget(container_reverse, 6, 1)

        layout.addWidget(QLabel(' Pattern: '), 7, 0, alignment=Qt.AlignRight)
        layout.addWidget(self.edit_pattern, 7, 1)
        layout.addWidget(QLabel(' Replace: '), 8, 0, alignment=Qt.AlignRight)
        layout.addWidget(self.edit_replace, 8, 1)

        layout.addWidget(btn_duplicate, 9, 0, 1, 2)
        # layout.addWidget(btn_help, 9, 1)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

    def help_(self):
        raise RuntimeError('not implemented yet')
        # open_url("https://ovm.io/assets-wiki/11e757fa-d78f-3a00-bd8c-0242ac130002/11edf0bd-7105-e286-9feb-0242ac1b0009")

    def do_cmd(self):
        if self.cmd is None:
            return

        self.cmd(
            self.spin_n.value(),
            filter_str(self.edit_pattern.text()),
            filter_str(self.edit_suffix.text()),
            self.chk_inverse.isChecked(),
            filter_str(self.edit_replace.text()),
            False,
            False,
            False,
            False
        )


class TemplateRenamerUI(MayaWindow):

    def __init__(self, parent=None, cmd=None):
        MayaWindow.__init__(self, parent)
        self.cmd = cmd

        self.setWindowTitle("Templates: Search and replace")
        self.setMaximumHeight(32)

        self.edit_pattern = QLineEdit()
        self.edit_replace = QLineEdit()

        btn_duplicate = QPushButton("Replace")
        btn_duplicate.clicked.connect(self.do_cmd)

        btn_help = QPushButton("Help")
        btn_help.clicked.connect(self.help_)

        layout = QGridLayout()
        layout.setSpacing(2)
        layout.setMargin(2)

        layout.addWidget(QLabel(" Pattern:", alignment=Qt.AlignRight), 0, 0)
        layout.addWidget(self.edit_pattern, 0, 1)
        layout.addWidget(QLabel(" Replace:", alignment=Qt.AlignRight), 1, 0)
        layout.addWidget(self.edit_replace, 1, 1)

        layout.addWidget(btn_duplicate, 2, 1)
        # layout.addWidget(btn_help, 2, 1)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

    def help_(self):
        raise RuntimeError('not implemented yet')
        # open_url("https://ovm.io/assets-wiki/11e757fa-d78f-3a00-bd8c-0242ac130002/11edf0bd-7105-e286-9feb-0242ac1b0009")

    def do_cmd(self):
        if self.cmd is None:
            return

        self.cmd(
            filter_str(self.edit_pattern.text()),
            filter_str(self.edit_replace.text())
        )


class TemplateModRenamerUI(MayaWindow):

    def __init__(self, parent, cmd=None):
        MayaWindow.__init__(self, parent)
        self.cmd = cmd

        self.setWindowTitle("Modifiers: Search and replace")
        self.setMaximumHeight(32)

        self.edit_pattern = QLineEdit("")
        self.edit_replace = QLineEdit("")

        btn_duplicate = QPushButton("Replace")
        btn_duplicate.clicked.connect(Callback(self.do_cmd))

        btn_help = QPushButton("Help")
        btn_help.clicked.connect(self.help_)

        layout = QGridLayout()
        layout.setSpacing(2)
        layout.setMargin(2)

        layout.addWidget(QLabel(" Pattern:", alignment=Qt.AlignRight), 0, 0)
        layout.addWidget(self.edit_pattern, 0, 1)
        layout.addWidget(QLabel(" Replace:", alignment=Qt.AlignRight), 1, 0)
        layout.addWidget(self.edit_replace, 1, 1)

        layout.addWidget(btn_duplicate, 2, 1)
        # layout.addWidget(btn_help, 2, 1)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

    def help_(self):
        raise RuntimeError('not implemented yet')
        # open_url("https://ovm.io/assets-wiki/11e757fa-d78f-3a00-bd8c-0242ac130002/11edf0bd-7105-e286-9feb-0242ac1b0009")

    def do_cmd(self):
        if self.cmd is None:
            raise RuntimeError('command not set')

        self.cmd(
            self.edit_pattern.text(),
            self.edit_replace.text()
        )


class TemplateModDuplicateUI(MayaWindow):

    def __init__(self, parent=None, cmd=None):
        MayaWindow.__init__(self, parent)

        self.cmd = cmd

        self.setWindowTitle("Duplicate selected mod")
        self.setMaximumHeight(32)

        self.spin_number = QSpinBox()
        self.spin_number.setMinimum(1)
        self.spin_number.setValue(1)

        # self.edit_pattern = QLineEdit("")
        # self.edit_replace = QLineEdit("")

        self.edit_pattern1 = QLineEdit("")
        self.edit_pattern2 = QLineEdit("")
        self.edit_pattern3 = QLineEdit("")
        self.edit_pattern4 = QLineEdit("")

        btn_duplicate = QPushButton("Duplicate")
        btn_duplicate.clicked.connect(Callback(self.do_cmd))

        btn_help = QPushButton("Help")
        btn_help.clicked.connect(self.help_)

        layout = QGridLayout()
        layout.setSpacing(2)
        layout.setMargin(2)

        layout.addWidget(QLabel(" Number of copy:", alignment=Qt.AlignRight), 0, 0)
        layout.addWidget(self.spin_number, 0, 1)

        layout.addWidget(QLabel(" Pattern 1:", alignment=Qt.AlignRight), 5, 0)
        layout.addWidget(self.edit_pattern1, 5, 1)

        layout.addWidget(QLabel(" Pattern 2:", alignment=Qt.AlignRight), 6, 0)
        layout.addWidget(self.edit_pattern2, 6, 1)

        layout.addWidget(QLabel(" Pattern 3:", alignment=Qt.AlignRight), 7, 0)
        layout.addWidget(self.edit_pattern3, 7, 1)

        layout.addWidget(QLabel(" Pattern 4:", alignment=Qt.AlignRight), 8, 0)
        layout.addWidget(self.edit_pattern4, 8, 1)

        # layout.addWidget(QLabel(" Pattern:"), 7, 0)
        # layout.addWidget(self.edit_pattern, 7, 1)
        # layout.addWidget(QLabel(" Replace:"), 8, 0)
        # layout.addWidget(self.edit_replace, 8, 1)

        layout.addWidget(btn_duplicate, 9, 0)
        layout.addWidget(btn_help, 9, 1)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

    def help_(self):
        raise RuntimeError('not implemented yet')
        # open_url("https://ovm.io/assets-wiki/11e757fa-d78f-3a00-bd8c-0242ac130002/11edf0bd-7105-e286-9feb-0242ac1b0009")

    def do_cmd(self):
        if self.cmd is None:
            return
        n = self.spin_number.value()
        patterns = [
            self.edit_pattern1.text(),
            self.edit_pattern2.text(),
            self.edit_pattern3.text(),
            self.edit_pattern4.text()
        ]
        self.cmd(n, patterns)

        self.close()
