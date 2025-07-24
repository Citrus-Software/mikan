# coding: utf-8

import base64
import hashlib
import __main__
import datetime
import traceback
from copy import deepcopy
from functools import partial
from six import string_types, iteritems

from mikan.vendor.Qt import QtCore, QtWidgets, QtGui
from mikan.vendor.Qt.QtCore import Qt, Signal
from mikan.vendor.Qt.QtWidgets import (
    QWidget, QMainWindow, QSplitter, QTreeWidget, QTreeWidgetItem,
    QAction, QMenu, QSizePolicy, QCheckBox
)

import maya.api.OpenMaya as om
from mikan.maya import cmdx as mx
import maya.cmds as mc

from mikan.core.ui.widgets import *
from mikan.core.logger import create_logger, timed_code
from ..core import DeformerGroup, Deformer, Nodes, Asset
from .widgets import OptVarSettings, Callback

__all__ = ['DeformerManager']

# cleanup previously registered callbacks
_callbacks = __main__.__dict__.setdefault(__name__ + '.registered_callbacks', [])
for cb in _callbacks:
    try:
        om.MMessage.removeCallback(cb)
    except:
        pass
del _callbacks[:]

log = create_logger()


class DeformerManager(QMainWindow, OptVarSettings):
    ICON_SIZE = QtCore.QSize(16, 16)
    ICON_RELOAD = Icon('reload', color='#897', size=ICON_SIZE, tool=True)
    ICON_READ = Icon('memory', color='#897', size=ICON_SIZE, tool=True)
    ICON_BACKUP = Icon('box', color='#897', size=ICON_SIZE, tool=True)
    ICON_LINK = Icon('link', color='#897', size=ICON_SIZE, tool=True)
    ICON_DELETE = Icon('trash', color='#897', size=ICON_SIZE, tool=True)

    SPLITTER_HEIGHTS = [256, 512]
    TREE_STYLE = 'QTreeView {selection-background-color: #444; selection-color: #ddd;}'

    def __init__(self, parent=None):
        QMainWindow.__init__(self, parent)
        self.setWindowFlags(Qt.Widget)
        self.setContextMenuPolicy(Qt.NoContextMenu)
        self.setStyleSheet(DeformerManager.TREE_STYLE)

        # layout
        self.tree_group = DeformerGroupTreeWidget(parent=self)
        self.tree_deformers = DeformerTreeWidget(parent=self)

        stack = StackWidget()
        row = stack.add_row()
        row.addWidget(self.tree_group)
        row.addWidget(self.tree_deformers)

        self.widget_edit = DeformerEditWidget(parent=self)
        splitter = QSplitter(Qt.Vertical)
        splitter.addWidget(stack)
        splitter.addWidget(self.widget_edit)
        splitter.setSizes(DeformerManager.SPLITTER_HEIGHTS)
        self.setCentralWidget(splitter)

        # main toolbar
        self.build_toolbar()

        # signals
        self.tree_group.itemClicked.connect(self.update_tree_deformers)
        self.tree_deformers.itemClicked.connect(self.update_widget_edit)

        # load data
        self.tree_group.load(dry=not self.wd_load.checkState())

    def build_toolbar(self):
        toolbar = self.addToolBar('Deformer manager')
        toolbar.setFloatable(False)
        toolbar.setMovable(False)
        toolbar.setIconSize(DeformerManager.ICON_SIZE)
        toolbar.setStyleSheet(
            'QToolButton {border: none; margin: 2px;}'
            'QToolButton:pressed {padding-top:1px; padding-left:1px;}'
        )

        _act = toolbar.addAction('Reload')
        _act.setIcon(DeformerManager.ICON_RELOAD)
        _act.setShortcut('F5')
        _act.triggered.connect(self.reload)

        toolbar.addSeparator()

        _act = toolbar.addAction('read deformers')
        _act.setIcon(DeformerManager.ICON_READ)
        _act.triggered.connect(self.read)

        _act = toolbar.addAction('create backup group')
        _act.setIcon(DeformerManager.ICON_BACKUP)
        _act.triggered.connect(Callback(self.create, filtered=False))

        _act = toolbar.addAction('create linked backup')
        _act.setIcon(DeformerManager.ICON_LINK)
        _act.triggered.connect(Callback(self.create, filtered=True))

        toolbar.addSeparator()

        _act = toolbar.addAction('remove deformer group')
        _act.setIcon(DeformerManager.ICON_DELETE)
        _act.triggered.connect(Callback(self.tree_group.delete_selected_item))

        # spacer
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        toolbar.addWidget(spacer)

        # auto load?
        self.wd_load = QCheckBox('always load')
        self.wd_load.setCheckState(Qt.Checked if self.get_optvar('load', False) else Qt.Unchecked)
        toolbar.addWidget(self.wd_load)

        self.wd_load.stateChanged.connect(self.load_changed)

    # ----- slots

    @busy_cursor
    def reload(self):
        Nodes.rebuild()
        self.tree_group.load()
        self.update_widget_edit()

    @busy_cursor
    def read(self):
        sl = mx.ls(sl=True)
        sl = [node for node in sl if 'gem_deformers' not in node]
        if not sl:
            return
        dfg = DeformerGroup.create(sl)
        if len(dfg):
            self.tree_group.add_item(dfg)
        mx.cmd(mc.select, sl)

    @busy_cursor
    def create(self, filtered=False):
        if filtered:
            Nodes.rebuild()
        sl = mx.ls(sl=True)
        sl = [node for node in sl if 'gem_deformers' not in node]
        if not sl:
            return
        dfg = DeformerGroup.create(sl, filtered=filtered)
        if len(dfg):
            dfg.write()
            self.tree_group.add_item(dfg, check=True)
        mx.cmd(mc.select, sl)

    @busy_cursor
    def update_tree_deformers(self, *args):
        self.blockSignals(True)

        item = self.tree_group.get_selected_item()
        self.tree_deformers.load(item)
        self.update_widget_edit()

        self.blockSignals(False)

    @busy_cursor
    def update_widget_edit(self, *args):
        item = self.tree_deformers.get_selected_item()
        if not isinstance(item, Deformer):
            item = None

        self.widget_edit.load(item)

    @busy_cursor
    def write(self):
        _dfg = self.tree_group.get_selected_item()
        filtered = 'gem_id' in _dfg.node
        _dfg.create(filtered=filtered)
        self.reload()

    def load_changed(self):
        self.set_optvar('load', bool(self.wd_load.checkState()))


class DeformerGroupTreeWidget(QTreeWidget):
    ROW_HEIGHT = 16
    ICON_SIZE = QtCore.QSize(ROW_HEIGHT, ROW_HEIGHT)

    ITEM_SCENE = 'Scene'
    ITEM_MEMORY = 'Memory'

    tree_changed = QtCore.Signal()
    selected_item = None

    def __init__(self, parent=None):
        QTreeWidget.__init__(self, parent)
        self.parent = parent
        self.headerItem().setHidden(True)

        self.setFrameStyle(QtWidgets.QFrame.Box | QtWidgets.QFrame.Plain)
        self.setFocusPolicy(Qt.NoFocus)

        self.setIconSize(DeformerGroupTreeWidget.ICON_SIZE)
        self.setIndentation(DeformerGroupTreeWidget.ROW_HEIGHT)

        self.setExpandsOnDoubleClick(False)
        self.doubleClicked.connect(self.select)

        self._callbacks = {}
        self.tree_items = {}

        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.context_menu_group)

    # tree -------------------------------------------------------------------------------------------------------------
    def load(self, dry=False):
        # remove registered callbacks
        del _callbacks[:]

        for k in list(self._callbacks):
            for cb in self._callbacks.pop(k):
                try:
                    om.MMessage.removeCallback(cb)
                except:
                    pass
        self._callbacks.clear()

        # rebuild item list
        self.blockSignals(True)

        memory_items = []
        for dfg, item in iteritems(self.tree_items):
            if isinstance(dfg, DeformerGroup) and dfg.node is None:
                memory_items.append(dfg)

        self.clear()
        self.tree_items.clear()

        self.check_assets()

        self.add_item(DeformerGroupTreeWidget.ITEM_SCENE)

        nodes = []
        if not dry:
            nodes = mx.ls('*.gem_deformers', o=1, r=1)

        for node in nodes:
            try:
                dfg = DeformerGroup(node)
            except:
                msg = traceback.format_exc().strip('\n')
                log.warning(msg)
                log.warning('failed to load deformer group: "{}"'.format(node))
                continue

            if node == self.selected_item:
                selected = True
            else:
                selected = None
            self.add_item(dfg, select=selected)

        self.add_item(DeformerGroupTreeWidget.ITEM_MEMORY)
        for dfg in memory_items:
            if dfg == self.selected_item:
                selected = True
            else:
                selected = False
            self.add_item(dfg, select=selected)

        self.blockSignals(False)
        self.tree_changed.emit()

    def check_assets(self):
        Nodes.rebuild_assets()
        for node in Nodes.assets:
            if node.exists:
                asset = Asset(node)
                if asset not in self.tree_items:
                    self.add_item(asset)

    def add_item(self, item, select=False, check=False):
        if check and isinstance(item, DeformerGroup):
            self.check_assets()

        tree_item = DeformerGroupTreeItem(item)
        self.tree_items[item] = tree_item

        parent = None
        if isinstance(item, DeformerGroup):
            if item.node:
                parent = DeformerGroupTreeWidget.ITEM_SCENE
                asset = Nodes.get_asset_id(item.node)
                if asset:
                    _node = Nodes.get_id('::asset', asset=asset)
                    parent = Asset(_node)
            else:
                parent = DeformerGroupTreeWidget.ITEM_MEMORY

        if parent and parent in self.tree_items:
            parent = self.tree_items[parent]
            parent.addChild(tree_item)
        else:
            self.addTopLevelItem(tree_item)

        if select:
            self.setCurrentItem(tree_item, 1)
        if isinstance(item, (string_types, Asset)):
            self.expandItem(tree_item)

        self.tree_changed.emit()
        self.attach_item(tree_item)
        return tree_item

    def get_selected_item(self):
        index = self.selectedIndexes()
        if index:
            item = self.itemFromIndex(index[0])
            if isinstance(item.item, DeformerGroup):
                if item.item.node is not None:
                    self.selected_item = item.item.node.name()
            return item.item

    def get_selected_tree_item(self):
        index = self.selectedIndexes()
        if index:
            item = self.itemFromIndex(index[0])
            return item

    def delete_selected_item(self):
        tree_item = self.get_selected_tree_item()
        if tree_item:
            item = tree_item.item
            if isinstance(item, DeformerGroup):

                if item in self.tree_items:
                    del self.tree_items[item]

                if item.node is not None:
                    mx.delete(item.node)

                try:
                    (tree_item.parent() or self.invisibleRootItem()).removeChild(tree_item)
                except:
                    pass

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

    # API callbacks ----------------------------------------------------------------------------------------------------
    def attach_item(self, tree_item):
        item = tree_item.item
        if isinstance(item, (DeformerGroup, Asset)):
            if item.node is None:
                return
            m_obj = item.node.object()
            m_dag = item.node.dag_path()

            self._callbacks[item] = []
            cb = om.MNodeMessage.addNodePreRemovalCallback(m_obj, partial(self.on_delete_item, item))
            self._callbacks[item].append(cb)
            _callbacks.append(cb)

            if isinstance(item, DeformerGroup):
                cb = om.MDagMessage.addParentAddedDagPathCallback(m_dag, partial(self.on_parent_item, item))
                self._callbacks[item].append(cb)
                _callbacks.append(cb)

    def on_delete_item(self, *args):
        item = args[0]

        if item in self._callbacks:
            cbs = self._callbacks.pop(item)
            for cb in cbs:
                om.MMessage.removeCallback(cb)
                if cb in _callbacks:
                    _callbacks.remove(cb)

        del_item = self.tree_items.get(item)
        if del_item:
            clear_deformers = False
            if del_item.isSelected():
                clear_deformers = True

            self.delete_tree_item(del_item)

            if clear_deformers:
                self.parent.update_tree_deformers()

    def on_parent_item(self, *args):
        item = args[0]

        parent = None
        tree_item = self.tree_items.get(item)
        if tree_item:
            parent = self.tree_items[DeformerGroupTreeWidget.ITEM_SCENE]

        asset = Nodes.get_asset_id(item.node)
        if asset:
            _node = Nodes.get_id('::asset', asset=asset)
            parent = self.tree_items.get(Asset(_node))

        if parent and tree_item:
            old_parent = tree_item.parent()
            i = old_parent.indexOfChild(tree_item)
            old_parent.takeChild(i)

            parent.addChild(tree_item)

    # toolbox menu -----------------------------------------------------------------------------------------------------
    def context_menu_group(self, point):
        index = self.indexAt(point)
        if not index.isValid():
            return
        tree_item = self.itemAt(point)
        item = tree_item.item

        if not isinstance(item, DeformerGroup):
            return
        parent_item = tree_item.parent()

        menu = QMenu(self)

        if parent_item.item == DeformerGroupTreeWidget.ITEM_MEMORY:
            _act = menu.addAction('write')
            _act.triggered.connect(self.write_group)

        _act = menu.addAction('duplicate')
        _act.triggered.connect(self.duplicate)

        if parent_item.item != DeformerGroupTreeWidget.ITEM_MEMORY:
            _act = menu.addAction('remove')
            _act.triggered.connect(self.remove)

            _act = menu.addAction('select')
            _act.triggered.connect(self.select)

        menu.exec_(QtGui.QCursor.pos())

    @busy_cursor
    def select(self, *args):
        item = self.get_selected_item()

        if isinstance(item, DeformerGroup) and item.node is not None and item.node.exists:
            mc.select(str(item.node))
        else:
            mc.select(cl=1)

    @busy_cursor
    def remove(self):
        item = self.get_selected_item()
        for node in mx.ls('*.gem_deformers', o=1, r=1):
            if node.endswith(str(item.root)):
                mx.delete(node)

    @busy_cursor
    def write_group(self):
        tree_item = self.get_selected_tree_item()
        item = tree_item.item
        if not isinstance(item, DeformerGroup):
            return

        grp = item
        if grp.node is not None:
            return

        grp.write()

        # update tree
        try:
            (tree_item.parent() or self.invisibleRootItem()).removeChild(tree_item)
        except:
            pass

        self.add_item(grp, select=False)

    @busy_cursor
    def duplicate(self):
        tree_item = self.get_selected_tree_item()
        item = tree_item.item
        if not isinstance(item, DeformerGroup):
            return

        grp = item.duplicate()

        # update tree
        self.add_item(grp, select=False)

    @busy_cursor
    def update_asset(self):
        tree_item = self.get_selected_tree_item()
        item = tree_item.item
        if not isinstance(item, Asset):
            return

        asset = item
        asset.update_deformer_groups()


class DeformerGroupTreeItem(QTreeWidgetItem):
    ROW_HEIGHT = 16
    ICON_SIZE = QtCore.QSize(ROW_HEIGHT, ROW_HEIGHT)
    ICON_MEM = Icon('memory', color='#888', size=ICON_SIZE)
    ICON_SCENE = Icon('world', color='#888', size=ICON_SIZE)
    ICON_ASSET = Icon('box', color='#fb5', size=ICON_SIZE)
    ICON_LINKED = Icon('link', color='#bf5', size=ICON_SIZE)
    ICON_GROUP = Icon('box', color='#bf5', size=ICON_SIZE)
    ICON_GROUP_TMP = Icon('memory', color='#bf5', size=ICON_SIZE)

    def __init__(self, item, parent=None):
        QTreeWidgetItem.__init__(self, parent)
        self.item = item

        icon = None

        if isinstance(item, string_types):
            self.setText(0, item)
            if item == DeformerGroupTreeWidget.ITEM_MEMORY:
                icon = DeformerGroupTreeItem.ICON_MEM
            else:
                icon = DeformerGroupTreeItem.ICON_SCENE

        elif isinstance(item, Asset):
            self.setText(0, '{}'.format(item.name))
            icon = DeformerGroupTreeItem.ICON_ASSET

        elif isinstance(item, DeformerGroup):
            if item.node:
                # scene
                self.setText(0, '{} <{}>'.format(item.node, item.root))
                if 'gem_id' in item.node and item.node['gem_id'].read():
                    icon = DeformerGroupTreeItem.ICON_LINKED
                else:
                    icon = DeformerGroupTreeItem.ICON_GROUP
            else:
                # memory
                name = item.name
                if item.date:
                    t = datetime.datetime.fromtimestamp(item.date)
                    name += ' <{}>'.format(t.strftime('%H:%M:%S (%d-%m-%Y)'))
                self.setText(0, name)
                icon = DeformerGroupTreeItem.ICON_GROUP_TMP

        if icon is not None:
            self.setIcon(0, icon)


class DeformerTreeWidget(QTreeWidget):
    ROW_HEIGHT = 16
    ICON_SIZE = QtCore.QSize(ROW_HEIGHT, ROW_HEIGHT)

    tree_changed = QtCore.Signal()

    def __init__(self, parent=None):
        QTreeWidget.__init__(self, parent)

        self.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.setFocusPolicy(Qt.NoFocus)

        self.setIconSize(DeformerTreeWidget.ICON_SIZE)
        self.setIndentation(DeformerTreeWidget.ROW_HEIGHT)

        self.setHeaderLabels(['name', 'type'])
        header = self.header()
        header.resizeSection(0, 160)
        header.resizeSection(1, 16)
        header.setStretchLastSection(True)

        self.setExpandsOnDoubleClick(False)
        # self.doubleClicked.connect(self.select)

        # self._callbacks = {}
        self.tree_items = {}

        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.context_menu_group)

        self.itemExpanded.connect(self.save_expanded)
        self.itemCollapsed.connect(self.save_expanded)

        # data
        self.mainframe = parent
        self.clipboard = None

    # tree -------------------------------------------------------------------------------------------------------------
    def load(self, grp):
        # rebuild item list
        self.blockSignals(True)
        self.clear()
        self.tree_items.clear()

        if isinstance(grp, DeformerGroup):

            xfos = {}
            xfo_count = {}
            for dfm in grp:
                xfo = dfm.transform
                if not xfo or not xfo.exists:
                    xfo = dfm.transform_id

                ini = None
                if dfm.ini is not None:
                    ini = dfm.ini.parser.node
                if xfo not in xfo_count:
                    xfo_count[xfo] = []
                if ini is not None and ini not in xfo_count[xfo]:
                    xfo_count[xfo].append(ini)

                xfo_ini = (xfo, ini)
                if xfo_ini not in xfos:
                    xfos[xfo_ini] = []

                xfos[xfo_ini].append(dfm)

            for xfo_ini in list(xfos):
                if len(xfo_count[xfo_ini[0]]) == 1:
                    xfos[(xfo_ini[0], None)] = xfos.pop(xfo_ini)

            for xfo_ini in list(xfos):
                xfos[xfo_ini] = sorted(xfos[xfo_ini], key=lambda x: x.ini.index if x.ini else None)

            for xfo_ini in sorted(xfos, key=lambda x: str(x[0])):
                self.add_item(xfo_ini)

                for dfm in xfos[xfo_ini]:
                    self.add_item(dfm, parent=xfo_ini)

        self.blockSignals(False)
        self.tree_changed.emit()

    def add_item(self, item, parent=None):

        tree_item = DeformerTreeItem(item)
        self.tree_items[item] = tree_item

        if parent and parent in self.tree_items:
            parent = self.tree_items[parent]
            parent.addChild(tree_item)

            if isinstance(item, Deformer) and item.ini is not None:
                ini_grp = item.ini.parser.node
                if 'ui_expanded' not in ini_grp:
                    ini_grp.add_attr(mx.Boolean('ui_expanded', default=False))

                if ini_grp['ui_expanded'].read():
                    self.expandItem(parent)

        else:
            self.addTopLevelItem(tree_item)

        return tree_item

    def get_selected_tree_item(self):
        index = self.selectedIndexes()
        if index:
            return self.itemFromIndex(index[0])

    def get_selected_item(self):
        index = self.selectedIndexes()
        if index:
            item = self.itemFromIndex(index[0])
            return item.item

    def save_expanded(self, tree_item):
        if not isinstance(tree_item.item, tuple):
            return

        # find children items (deformers) to get ini.parser.node
        node = None

        for i in range(tree_item.childCount()):
            child = tree_item.child(i)
            if isinstance(child.item, Deformer) and child.item.ini is not None:
                node = child.item.ini.parser.node
                break

        if node is None or node.is_referenced():
            return

        node['ui_expanded'] = tree_item.isExpanded()

    # toolbox menu -----------------------------------------------------------------------------------------------------
    def context_menu_group(self, point):
        index = self.indexAt(point)
        if not index.isValid():
            return

        tree_item = self.itemAt(point)
        item = tree_item.item

        menu = QMenu(self)

        if isinstance(item, Deformer):
            _act = menu.addAction('build')
            _act.triggered.connect(self.build_deformer)
            _act = menu.addAction('rebuild')
            _act.triggered.connect(self.rebuild_deformer)
            _act = menu.addAction('delete')
            _act.triggered.connect(self.delete_deformer)

            menu.addSeparator()
            _act = menu.addAction('select influences')
            _act.triggered.connect(partial(self.select_infs))

            # menu.addSeparator()
            # _act = menu.addAction('copy weightmaps')
            # _act.triggered.connect(self.copy)
            # if self.clipboard:
            #     _act = menu.addAction('paste weightmaps')
            #     _act.triggered.connect(self.paste)
            #     _act = menu.addAction('clear clipboard')
            #     _act.triggered.connect(self.clear_clipboard)

            menu.addSeparator()
            _act = menu.addAction('transfer')
            _act.triggered.connect(partial(self.transfer, flip=False, mirror=False))
            _act = menu.addAction('mirror')
            _act.triggered.connect(partial(self.transfer, flip=False, mirror=True))
            _act = menu.addAction('flip')
            _act.triggered.connect(partial(self.transfer, flip=True, mirror=False))

            menu.addSeparator()

            _act = menu.addAction('remove data')
            _act.triggered.connect(self.remove)

            if item.ini is not None:
                _act = menu.addAction('select notes')
                _act.triggered.connect(self.select_group)

                _act = menu.addAction('move up')
                _act.triggered.connect(partial(self.reorder_deformer, -1))
                _act = menu.addAction('move down')
                _act.triggered.connect(partial(self.reorder_deformer, 1))

        else:
            _act = menu.addAction('select')
            _act.triggered.connect(self.select_group)

        menu.exec_(QtGui.QCursor.pos())

    # def copy(self):
    #     dfm = self.mainframe.tree_deformers.get_selected_item()
    #     self.clipboard = deepcopy(dfm.data['maps'])
    #
    # def paste(self):
    #     dfm = self.mainframe.tree_deformers.get_selected_item()
    #     dfm.data['maps'] = deepcopy(self.clipboard)
    #     dfm.ui_data['edited_maps'] = True
    #     self.mainframe.widget_edit.reload()
    #
    # def clear_clipboard(self):
    #     self.clipboard = None

    @busy_cursor
    def build_deformer(self):
        dfm = self.get_selected_item()
        if not isinstance(dfm, Deformer):
            return

        dfm.bind()

    @busy_cursor
    def delete_deformer(self):
        dfm = self.get_selected_item()
        if not isinstance(dfm, Deformer):
            return

        dfm.find_node()
        if dfm.node is not None:
            # cleanup
            mx.delete(dfm.node)
            dfm.node = None

    @busy_cursor
    def rebuild_deformer(self):
        dfm = self.get_selected_item()
        if not isinstance(dfm, Deformer):
            return
        dfm = dfm.copy()

        if dfm.transform is None:
            dfm.transform = Deformer.get_node(dfm.transform_id, dfm.root_id)
        dfm.find_geometry()
        dfm.find_node()

        if dfm.node is not None:
            # find io
            input_plug = dfm.get_deformer_input(dfm.node, dfm.transform)
            input_id = dfm.get_input_id(input_plug)

            output_plug = dfm.get_deformer_output(dfm.node, dfm.transform)
            output_id = dfm.get_output_id(output_plug)

            # cleanup
            mx.delete(dfm.node)
            dfm.node = None

            # rebuild
            if input_id:
                dfm.input_id = input_id
            if output_id:
                dfm.output_id = output_id

        dfm.bind()

    def reorder_deformer(self, direction):
        tree_item = self.get_selected_tree_item()
        dfm = tree_item.item
        if not isinstance(dfm, Deformer) or dfm.ini is None:
            return

        parent_item = tree_item.parent()
        n = parent_item.childCount()
        for i in range(n):
            child = parent_item.child(i)
            if child.item.ini == dfm.ini:
                break

        # boundary check
        j = i + direction
        if 0 > j or j >= n:
            return

        # update ini
        ini0 = dfm.ini
        ini1 = parent_item.child(j).item.ini
        ini0.switch(ini1)

        # update menu item position
        child = parent_item.takeChild(i)
        parent_item.insertChild(j, child)

        for i in range(n):
            parent_item.child(i).setSelected(False)
        child.setSelected(True)

    @busy_cursor
    def transfer(self, flip=False, mirror=False):

        tree_item = self.get_selected_tree_item()
        dfm = tree_item.item.copy()

        if dfm.transform is None:
            dfm.transform = Deformer.get_node(dfm.transform_id, dfm.root_id)
        dfm.find_geometry()
        dfm.find_node()

        sl = mx.ls(sl=True)
        if len(sl) == 0:
            log.warning('nothing selected')
            return

        grp = DeformerGroup(name='transfer {}->{}'.format(dfm.transform_id, dfm.id))

        for obj in sl:
            shp = obj.shape()
            if not shp or not shp.is_a((mx.tMesh, mx.tNurbsCurve)):
                log.warning('{} is not a valid geometry'.format(obj))
                continue

            dfm_new = dfm.transfer(obj, flip=flip, mirror=mirror, axis='x')
            dfm_new.id = dfm.id
            dfm_id = '{}->{}'.format(dfm_new.transform_id, dfm_new.id)

            grp.deformers[dfm_id] = dfm_new
            grp.data.append(dfm_new)

        if len(grp):
            self.mainframe.tree_group.add_item(grp, select=False)

    @busy_cursor
    def remove(self):
        tree_item = self.get_selected_tree_item()
        dfm = tree_item.item
        group = self.mainframe.tree_group.get_selected_item()

        # clean ini
        ini = tree_item.ini
        if ini:
            tree_item.ini.delete()

        # remove data
        for key in group.deformers.keys():
            if group[key] == dfm:
                del group[key]

        # update tree
        try:
            (tree_item.parent() or self.invisibleRootItem()).removeChild(tree_item)
        except:
            pass

    def select_group(self):
        item = self.get_selected_item()
        if isinstance(item, Deformer) and item.ini is not None:
            mx.cmd(mc.select, item.ini.parser.node)
        if isinstance(item, tuple):
            try:
                mx.cmd(mc.select, item[0])
            except:
                pass

    def select_infs(self):
        item = self.get_selected_item()

        infs = []
        for inf in item.data['infs']:
            inf = item.data['infs'][inf]
            inf = Deformer.get_node(inf)
            if isinstance(inf, mx.DagNode):
                infs.append(inf)

        mx.cmd(mc.select, infs)


class DeformerTreeItem(QTreeWidgetItem):
    ICON_SIZE = QtCore.QSize(16, 16)
    ICON_GEO = Icon('box', color='#888', size=ICON_SIZE)
    ICON_DFM = Icon('gear', color='#bf5', size=ICON_SIZE)
    ICON_DFM_TMP = Icon('memory', color='#bf5', size=ICON_SIZE)

    def __init__(self, item, parent=None):
        QTreeWidgetItem.__init__(self, parent)
        self.item = item
        self.ini = None

        if isinstance(item, Deformer):
            self.ini = item.ini

        # display
        icon = None

        if isinstance(item, tuple) and len(item) == 2:
            label = str(item[0])
            if item[1] is not None:
                label = '{} ({})'.format(*item)
            self.setText(0, label)
            self.setText(1, '')
            icon = DeformerTreeItem.ICON_GEO

        elif isinstance(item, (str, mx.Node)):
            self.setText(0, str(item))
            self.setText(1, '')
            icon = DeformerTreeItem.ICON_GEO

        elif isinstance(item, Deformer):
            self.setText(0, item.id)
            self.setText(1, item.deformer)
            if item.node is not None:
                icon = DeformerTreeItem.ICON_DFM
            else:
                icon = DeformerTreeItem.ICON_DFM_TMP

        if icon is not None:
            self.setIcon(0, icon)


class DeformerEditWidget(QMainWindow):
    ICON_SIZE = QtCore.QSize(16, 16)
    ICON_RELOAD = Icon('reload', color='#897', size=ICON_SIZE, tool=True)
    ICON_WRITE = Icon('write', color='#897', size=ICON_SIZE, tool=True)
    ICON_UP = Icon('arrow_up', color='#888', size=ICON_SIZE, tool=True)
    ICON_DN = Icon('arrow_dn', color='#888', size=ICON_SIZE, tool=True)
    ICON_STYLE = 'QToolButton {border: none; margin: 2px;} QToolButton:pressed {padding-top:1px; padding-left:1px;}'

    edited = Signal()

    def __init__(self, parent=None):
        QMainWindow.__init__(self, parent)
        self.setContextMenuPolicy(Qt.NoContextMenu)

        # mainframe
        self.stack = StackWidget()
        self.setCentralWidget(self.stack)

        # edit
        self.box_edit = self.stack.add_column(margins=0, spacing=0)
        self.wd_opts = {}
        self.wd_custom_opts = {}

        # weightmaps box
        self.tree = WeightMapTree(self)
        self.stack.add_widget(self.tree, stretch=1)

        # side toolbar
        self.build_toolbar()

        # interface
        self.deformer = None

        # connections
        self.edited.connect(self.reload_edited)

    def build_toolbar(self):
        toolbar = QtWidgets.QToolBar()
        self.addToolBar(Qt.RightToolBarArea, toolbar)
        toolbar.setFloatable(False)
        toolbar.setMovable(False)
        toolbar.setIconSize(DeformerEditWidget.ICON_SIZE)
        toolbar.setStyleSheet(DeformerEditWidget.ICON_STYLE)

        _act = toolbar.addAction('Reload')
        _act.setIcon(DeformerEditWidget.ICON_RELOAD)
        _act.setShortcut('F5')
        _act.triggered.connect(self.reload)

        self.act_write = QAction('Write', self)
        _act = self.act_write
        _act.setIcon(DeformerEditWidget.ICON_WRITE)
        _act.triggered.connect(self.write)
        _act.setEnabled(False)
        toolbar.addAction(_act)

        toolbar.addSeparator()
        _act = toolbar.addAction('Move up')
        _act.setIcon(DeformerEditWidget.ICON_UP)
        _act.triggered.connect(partial(self.tree.move_item, -1))

        _act = toolbar.addAction('Move dn')
        _act.setIcon(DeformerEditWidget.ICON_DN)
        _act.triggered.connect(partial(self.tree.move_item, 1))

    def load(self, dfm):
        # reinit ui
        self.act_write.setEnabled(False)

        if dfm is None:
            self.deformer = None
            self.clear()
            return

        if not isinstance(dfm, Deformer):
            raise ValueError('not a Deformer ({})'.format(dfm))

        self.deformer = dfm

        # update widgets
        self.build_edit()

        # set buttons availability
        ini = self.deformer.ini
        if ini is not None:
            self.act_write.setEnabled(True)

        # update weightmap tree
        self.tree.load(dfm)

        # update defaults
        self.reload_edited()

    def clear_edit(self):
        # reset layout
        self.stack.clear_layout(self.box_edit)
        self.wd_opts.clear()
        self.wd_custom_opts.clear()

    def build_edit(self):
        self.clear_edit()
        if not self.deformer:
            return
        dfm = self.deformer

        # type
        _row = self.stack.add_row(self.box_edit)

        self.wd_opts['id'] = StringPlugWidget(label='deformer')
        self.wd_opts['transform_id'] = StringPlugWidget(label='transform')
        _row.addWidget(self.wd_opts['id'], stretch=2)
        _row.addWidget(self.wd_opts['transform_id'], stretch=3)

        self.wd_opts['id'].setStyleSheet('font-size:12px; font-weight:bold')
        self.wd_opts['id'].label_widget.setText(dfm.deformer)

        # rebuild opts
        self.stack.add_line(self.box_edit)

        _col0, _col1 = self.stack.add_columns(self.box_edit)

        self.wd_opts['order'] = StringListPlugWidget(label='Order')
        self.wd_opts['order'].set_list(['default', 'front', 'isolated', 'proxy'])
        self.wd_opts['protected'] = BoolPlugWidget(label='Protected')
        self.wd_opts['input_id'] = StringPlugWidget(label='Input')
        self.wd_opts['output_id'] = StringPlugWidget(label='Output')

        _col0.addWidget(self.wd_opts['order'])
        _col0.addWidget(self.wd_opts['protected'])
        _col1.addWidget(self.wd_opts['input_id'])
        _col1.addWidget(self.wd_opts['output_id'])

        common_defaults = {
            'id': '',
            'transform_id': '',
            'order': 'default',
            'protected': False,
            'input_id': '',
            'output_id': '',
        }

        for key in self.wd_opts:
            w = self.wd_opts[key]
            w.add_connector(OptPlugConnect(dfm, key, common_defaults[key], common=True))
            w.set_altered()

        # deformer options
        opts = []
        cls_data = dfm.deformer_data.get('data')
        for key in cls_data:
            if 'value' in cls_data[key]:
                v = cls_data[key]['value']
                if isinstance(v, dict):
                    continue
                if isinstance(v, list) and len(v) != 3 and not all(isinstance(_v, (int, float)) for _v in v):
                    continue
                opts.append(key)

        if opts:
            self.stack.add_line(parent=self.box_edit)

            _cols = self.stack.add_columns(self.box_edit)
            opts_number = len(opts)
            row_count = 0
            col_count = 0

            for opt in opts:
                opt_data = cls_data[opt]

                dv = opt_data.get('value')
                enum = opt_data.get('enum')
                vmin = opt_data.get('min')
                vmax = opt_data.get('max')
                presets = opt_data.get('presets')
                yaml = opt_data.get('yaml', False)

                label = opt_data.get('label', opt.capitalize().replace('_', ' '))
                if enum:
                    if isinstance(dv, int):
                        dv = list(enum.values())[dv]
                    w = StringListPlugWidget(label=label, default=dv)
                    w.set_list(list(enum.values()))
                elif yaml or isinstance(dv, string_types):
                    w = StringPlugWidget(label=label, default=dv, presets=presets, yaml=yaml)
                elif isinstance(dv, bool):
                    w = BoolPlugWidget(label=label, default=dv)
                elif isinstance(dv, int):
                    w = IntPlugWidget(label=label, default=dv, min_value=vmin, max_value=vmax)
                elif isinstance(dv, float):
                    w = FloatPlugWidget(label=label, default=dv, min_value=vmin, max_value=vmax)
                elif isinstance(dv, list) and len(dv) == 3 and all(isinstance(x, (int, float)) for x in dv):
                    if isinstance(dv[0], int):
                        w = VectorIntPlugWidget(label=label, default=dv, presets=presets)
                    else:
                        w = VectorPlugWidget(label=label, default=dv, presets=presets)
                else:
                    continue

                _cols[col_count].addWidget(w)
                row_count += 1
                if row_count >= opts_number / 2:
                    col_count = 1

                self.wd_custom_opts[opt] = w

                # connect
                w.add_connector(OptPlugConnect(dfm, opt, dv))
                w.set_altered()

            if opts_number % 2:
                _cols[1].addStretch()

    def reload(self):
        self.load(self.deformer)

    def reload_edited(self):
        self.tree.setAccessibleName('')
        if self.deformer.ui_data.get('edited_maps'):
            self.tree.setAccessibleName('edited')

        self.setStyleSheet('*[accessibleName^="edited"] {border: 2px solid #bf5;}')

    def reset_edited(self):
        self.deformer.ui_data.clear()
        self.edited.emit()

    def clear(self):
        self.clear_edit()
        self.tree.clear()

    def write(self):
        if self.deformer is None:
            return

        self.deformer.update_ini()

        self.deformer.ui_data.clear()
        self.reload()


class OptPlugConnect(AbstractPlugConnect):

    def __init__(self, dfm, opt, default, common=False):
        self.widget = None
        self.dfm = dfm
        self.opt = opt
        self.default = default
        self.common = common

    def _write(self, v):
        if self.common:
            if self.opt == 'id':
                self.dfm.id = v if v else None
            elif self.opt == 'transform_id':
                self.dfm.transform_id = v if v else None
            elif self.opt == 'order':
                self.dfm.order = v if v != 'default' else None
            elif self.opt == 'protected':
                self.dfm.protected = v
            elif self.opt == 'input_id':
                self.dfm.input_id = v if v else None
            elif self.opt == 'output_id':
                self.dfm.output_id = v if v else None
        else:
            self.dfm.data[self.opt] = v

    def update(self):
        value = self.widget.value
        if isinstance(self.widget, StringListPlugWidget):
            value = self.widget.widget.currentIndex()
        self._write(value)
        self.widget.set_altered()

    def reset(self):
        self._write(self.widget.default)
        self.widget.set_altered()

    def read(self):
        if self.common:
            if self.opt == 'id':
                v = self.dfm.id
                return v if v else ''
            elif self.opt == 'transform_id':
                v = self.dfm.transform_id
                return v if v else ''
            elif self.opt == 'order':
                v = self.dfm.order
                return v if v else 'default'
            elif self.opt == 'protected':
                return self.dfm.protected
            elif self.opt == 'input_id':
                v = self.dfm.input_id
                return v if v else ''
            elif self.opt == 'output_id':
                v = self.dfm.output_id
                return v if v else ''
        else:
            value = self.dfm.data[self.opt]
            if isinstance(self.widget, StringListPlugWidget):
                value = self.widget.widget.itemText(int(value))
            return value

    def connected(self):
        # show if current value is different from deformer default
        return self.read() != self.default

    def update_widget(self):
        # update default widget value from initial deformer load
        if self.common:
            if 'common' not in self.dfm.ui_data:
                self.dfm.ui_data['common'] = {}
            ui_data = self.dfm.ui_data['common']
        else:
            if 'data' not in self.dfm.ui_data:
                self.dfm.ui_data['data'] = {}
            ui_data = self.dfm.ui_data['data']

        if self.opt not in ui_data:
            ui_data[self.opt] = deepcopy(self.read())

        self.widget.default = ui_data[self.opt]

        # change colors when connected
        self.widget.color_changed = 'color: #bf5;'
        self.widget.color_altered = 'color: #897;'


class WeightMapTree(QTreeWidget):
    """ Interface entre les données du deformer et le widget """
    FONT_TREE = QtGui.QFont('courier new', 9)
    FONT_TREE.setFixedPitch(True)
    ROW_HEIGHT = 64
    ROW_INDENT = 12
    ICON_SIZE = QtCore.QSize(ROW_HEIGHT, ROW_HEIGHT)

    def __init__(self, parent=None):
        self.parent = parent
        QTreeWidget.__init__(self, parent)
        self.setIconSize(WeightMapTree.ICON_SIZE)

        self.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.setFocusPolicy(Qt.NoFocus)

        self.setFont(WeightMapTree.FONT_TREE)
        self.setIndentation(WeightMapTree.ROW_INDENT)

        self.setHeaderLabels(['key', 'name', 'id', 'weightmap'])
        header = self.header()
        header.resizeSection(0, 50)
        header.resizeSection(1, 132)
        header.resizeSection(2, 132)
        header.setStretchLastSection(True)

        self.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.setExpandsOnDoubleClick(False)

        self.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.doubleClicked.connect(self.edit_item)
        self.itemChanged.connect(self.update_item)

        self.clipboard = None

        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.context_menu_group)

    def load(self, dfm):
        """ Charge les données du deformer dans le widget """
        assert isinstance(dfm, Deformer)

        # rebuild item list
        self.blockSignals(True)
        self.clear()

        for wm in dfm.get_weightmaps():
            self.add_item(wm)

        self.blockSignals(False)

    def add_item(self, item, expand=False):

        tree_item = WeightMapTreeItem(item)
        self.addTopLevelItem(tree_item)

        if item.data.get('bind_pose') is not None:
            _tree_item = WeightMapTreeItem(item, subkey='bind_pose')
            tree_item.addChild(_tree_item)
            if expand:
                self.expandItem(tree_item)

        if item.data.get('bind_pose_root') is not None:
            _tree_item = WeightMapTreeItem(item, subkey='bind_pose_root')
            tree_item.addChild(_tree_item)
            if expand:
                self.expandItem(tree_item)

        return tree_item

    def get_selected_tree_item(self):
        index = self.selectedIndexes()
        if index:
            item = self.itemFromIndex(index[0])
            return item

    def get_selected_tree_items(self):
        indices = self.selectedIndexes() or []
        items = []
        for i in indices:
            item = self.itemFromIndex(i)
            if item not in items:
                items.append(item)
        return items

    def get_selected_item(self):
        tree_item = self.get_selected_tree_item()
        if tree_item:
            return tree_item.item

    def get_selected_items(self):
        return [item.item for item in self.get_selected_tree_items()]

    def edit_item(self, *args):
        column = args[0].column()
        if column not in (1, 2):
            return

        index = self.selectedIndexes()
        if index:
            item = self.itemFromIndex(index[0])
        else:
            return

        self.editItem(item, column)

    def get_top_level_items(self):
        top_level_items = []
        item_count = self.topLevelItemCount()
        for i in range(item_count):
            item = self.topLevelItem(i)
            top_level_items.append(item)
        return top_level_items

    def update_item(self, *args):
        tree_item = args[0]
        col = args[1]
        text = tree_item.text(col)
        wi = tree_item.item
        data = wi.data
        if tree_item.subkey:
            data = wi.data[tree_item.subkey]

        # set name
        if col == 1:
            node_name = text.replace('_', '')
            if node_name.isalnum():
                data['name'] = text

                if mc.objExists(text):
                    node = mx.encode(text)
                    ni = wi.get_node_interface(node)
                    data['tag'] = ni['tag']
                    tree_item.setText(2, data['tag'])
            else:
                tree_item.setText(col, data['name'])

        # set tag
        elif col == 2:
            if '::' in text:
                data['tag'] = text

                node = Nodes.get_id(text)
                if isinstance(node, mx.Node):
                    ni = wi.get_node_interface(node)
                    data['name'] = ni['name']
                    tree_item.setText(1, data['name'])

            else:
                tree_item.setText(col, data['tag'])

        # update deformer
        deformer = self.parent.deformer
        if deformer is None:
            return

        deformer.set_weightmaps(self.get_all_weightmaps())
        deformer.ui_data['edited_maps'] = True
        self.parent.edited.emit()

    def get_all_tree_items(self):
        tree_items = []

        root = self.invisibleRootItem()
        for i in range(root.childCount()):
            tree_items.append(root.child(i))

        return tree_items

    def get_all_weightmaps(self):
        tree_items = self.get_all_tree_items()
        return [x.item for x in tree_items]

    # toolbox menu -------------------------------------------------------------
    def context_menu_group(self, point):
        if not self.parent.deformer:
            return

        index = self.indexAt(point)
        if not index.isValid():
            # build void menu
            menu = QMenu(self)
            _act = menu.addAction('add empty item')
            _act.triggered.connect(partial(self.add_empty_item))

            if self.clipboard:
                _act = menu.addAction('paste weightmaps')
                _act.triggered.connect(self.paste_weightmaps)

                _act = menu.addAction('clear clipboard')
                _act.triggered.connect(self.clear_clipboard)

            menu.exec_(QtGui.QCursor.pos())
            return

        tree_item = self.itemAt(point)
        item = tree_item.item

        # check data
        has_subkey = False
        for subkey in ('bind_pose', 'bind_pose_root'):
            if subkey in item.data:
                has_subkey = True
                break

        # build menu
        menu = QMenu(self)

        _sep = False
        if item.weightmap:
            _act = menu.addAction('copy weightmaps')
            _act.triggered.connect(self.copy_weightmaps)

            _act = menu.addAction('switch weightmaps')
            _act.triggered.connect(self.switch_weightmaps)
            _sep = True

        if self.clipboard:
            _act = menu.addAction('paste weightmaps')
            _act.triggered.connect(self.paste_weightmaps)

            _act = menu.addAction('clear clipboard')
            _act.triggered.connect(self.clear_clipboard)
            _sep = True

        if _sep:
            menu.addSeparator()

        _act = menu.addAction('remove')
        _act.triggered.connect(self.remove)

        _act = menu.addAction('select')
        _act.triggered.connect(self.select)

        _act = menu.addAction('replace by selection')
        _act.triggered.connect(partial(self.replace_selection, subkey=tree_item.subkey))

        if has_subkey:
            menu.addSeparator()

            for subkey in ('bind_pose', 'bind_pose_root'):
                if subkey in item.data:
                    if item.data[subkey] is None:
                        _act = menu.addAction('add ' + subkey)
                        _act.triggered.connect(partial(self.add_subkey, subkey))
                    else:
                        _act = menu.addAction('remove {}'.format(subkey))
                        _act.triggered.connect(partial(self.remove_subkey, subkey))

        menu.exec_(QtGui.QCursor.pos())

    def select(self):
        nodes = []

        for item in self.get_selected_items():
            node = item.data.get('node')
            if node:
                if isinstance(node, mx.Node):
                    nodes.append(node)
                else:
                    try:
                        node = Deformer.get_node(node)
                        nodes.append(node)
                    except:
                        pass

        mx.cmd(mc.select, nodes)

    def replace_selection(self, subkey=None):
        tree_items = self.get_selected_tree_items()
        if len(tree_items) != 1:
            return
        wi = tree_items[0].item

        if not isinstance(wi.data['key'], int):
            return

        nodes = mx.ls(sl=1, type='transform')
        if len(nodes) != 1:
            return
        node = nodes[0]

        # update tree item
        wi.set_node_interface(node, subkey=subkey)
        tree_items[0].update()

        # update deformer
        deformer = self.parent.deformer
        if deformer is None:
            return

        deformer.set_weightmaps(self.get_all_weightmaps())
        deformer.ui_data['edited_maps'] = True
        self.parent.edited.emit()

    def move_item(self, direction):

        deformer = self.parent.deformer
        if deformer is None:
            return

        items = self.get_selected_items()
        if not items:
            return
        ids, maps = deformer.get_indexed_maps()

        if direction == 1:
            items = items[::-1]
            ids = ids[::-1]

        selected_tags = []
        selected_names = []
        moved = [-1]
        remap = {}

        for item in items:
            selected_tags.append(item.data.get('tag'))
            selected_names.append(item.data.get('name'))

            key = item.data.get('key')
            if key is not None:
                i = ids.index(key)

                if i - 1 in moved:
                    moved.append(i)
                    continue
                moved.append(i - 1)

                key_pop = ids[i - 1]
                remap[key] = key_pop

        for key in ('maps', 'infs', 'bind_pose', 'bind_pose_root'):
            if key not in deformer.data or not isinstance(deformer.data[key], dict):
                continue
            d = deformer.data[key]
            for k in remap:
                _value0 = d.pop(k, None)
                _value1 = d.pop(remap[k], None)
                if _value0 is not None:
                    d[remap[k]] = _value0
                if _value1 is not None:
                    d[k] = _value1

        deformer.remap_indexed_maps()
        self.load(deformer)

        for tree_item in self.get_top_level_items():
            tag = tree_item.item.data.get('tag')
            if tag and tag in selected_tags:
                tree_item.setSelected(True)
                continue
            name = tree_item.item.data.get('name')
            if name and name in selected_names:
                tree_item.setSelected(True)

        deformer.ui_data['edited_maps'] = True
        self.parent.edited.emit()

    def remove(self):
        tree_items = self.get_selected_tree_items()

        for tree_item in tree_items:
            if not tree_item.subkey:
                try:
                    (tree_item.parent() or self.invisibleRootItem()).removeChild(tree_item)
                except:
                    pass

        # update deformer
        deformer = self.parent.deformer
        if deformer is None:
            print('no deformer???')
            return

        print('update dfm')
        deformer.set_weightmaps(self.get_all_weightmaps())
        deformer.ui_data['edited_maps'] = True
        self.parent.edited.emit()

    def add_subkey(self, subkey):
        tree_items = self.get_selected_tree_items()
        if len(tree_items) != 1:
            return
        wi = tree_items[0].item

        if not isinstance(wi.data['key'], int):
            return

        # add subkey
        wi.data[subkey] = {}

        if subkey == 'bind_pose':
            wi.data[subkey]['key'] = 'bp'
        elif subkey == 'bind_pose_root':
            wi.data[subkey]['key'] = 'bpr'

        # update tree item
        nodes = mx.ls(sl=1, type='transform')
        if nodes:
            node = nodes[0]
            wi.set_node_interface(node, subkey=subkey)

        tree_item = WeightMapTreeItem(wi, subkey=subkey)
        tree_items[0].addChild(tree_item)
        self.expandItem(tree_items[0])

        # update deformer
        deformer = self.parent.deformer
        if deformer is None:
            return

        deformer.set_weightmaps(self.get_all_weightmaps())
        deformer.ui_data['edited_maps'] = True
        self.parent.edited.emit()

    def remove_subkey(self, subkey):

        tree_items = self.get_selected_tree_items()
        if len(tree_items) != 1:
            return
        wi = tree_items[0].item

        if not isinstance(wi.data['key'], int):
            return

        # remove subkey
        wi.data[subkey] = None

        tree_item_subkey = None
        if tree_items[0].subkey:
            tree_item_subkey = tree_items[0]
        else:
            for i in range(tree_items[0].childCount()):
                tree_item_subkey = tree_items[0].child(i)
                break

        if tree_item_subkey:
            try:
                (tree_item_subkey.parent() or self.invisibleRootItem()).removeChild(tree_item_subkey)
            except:
                pass

        # update deformer
        deformer = self.parent.deformer
        if deformer is None:
            return

        deformer.set_weightmaps(self.get_all_weightmaps())
        deformer.ui_data['edited_maps'] = True
        self.parent.edited.emit()

    def copy_weightmaps(self):
        self.clipboard = []

        for tree_item in self.get_selected_tree_items():
            if tree_item.subkey:
                continue
            item = tree_item.item
            if item.weightmap:
                self.clipboard.append(item.weightmap.copy())

    def paste_weightmaps(self):
        tree_items = self.get_selected_tree_items()
        if not self.clipboard:
            return

        if len(tree_items) == 0:
            pass

        elif len(self.clipboard) == 1:
            wm = self.clipboard[0]
            for tree_item in tree_items:
                item = tree_item.item
                item.weightmap = wm.copy()
                tree_item.update()

        elif len(self.clipboard) > len(tree_items):
            log.error('too much weightmaps to paste')
            return

        else:
            for i in range(len(self.clipboard)):
                wm = self.clipboard[i]
                tree_item = tree_items[i]
                item = tree_item.item
                item.weightmap = wm.copy()
                tree_item.update()

        # update deformer
        deformer = self.parent.deformer
        if deformer is None:
            return

        deformer.set_weightmaps(self.get_all_weightmaps())
        deformer.ui_data['edited_maps'] = True
        self.parent.edited.emit()

    def clear_clipboard(self):
        self.clipboard = None

    def switch_weightmaps(self):
        tree_items = self.get_selected_tree_items()
        tree_items = [x for x in tree_items if not x.subkey]

        if len(tree_items) != 2:
            return

        tree_items[0].item.weightmap, tree_items[1].item.weightmap = tree_items[1].item.weightmap, tree_items[0].item.weightmap
        [x.update() for x in tree_items]

        # update deformer
        deformer = self.parent.deformer
        if deformer is None:
            return

        deformer.set_weightmaps(self.get_all_weightmaps())
        deformer.ui_data['edited_maps'] = True
        self.parent.edited.emit()

    def add_empty_item(self):
        key = 0
        name = 'dummy'

        keys = []
        names = []
        for tree_item in self.get_all_tree_items():
            wi = tree_item.item
            if 'key' in wi.data:
                keys.append(wi.data['key'])
            n = wi.data.get('name')
            if n and n.startswith(name):
                names.append(n)

        if keys:
            key = max(filter(lambda k: isinstance(k, int), keys)) + 1

        while name in names:
            head = name.rstrip('0123456789')
            tail = name[len(head):]
            if not tail:
                tail = 1
            tail = int(tail) + 1
            name = head + str(tail)

        deformer = self.parent.deformer
        if deformer is None:
            return

        wi = deformer.create_weightmap(None, key=key, name=name)
        self.add_item(wi)

        # update deformer
        deformer.set_weightmaps(self.get_all_weightmaps())
        deformer.ui_data['edited_maps'] = True
        self.parent.edited.emit()


class WeightMapTreeItem(QTreeWidgetItem):
    BRUSH_SUBKEY = QtGui.QBrush(QtGui.QColor("#7c7"))
    BRUSH_ITEM = QtGui.QBrush(QtGui.QColor("#888"))

    def __init__(self, item, parent=None, subkey=None):
        QTreeWidgetItem.__init__(self, parent)
        self.item = item
        self.subkey = subkey

        # icon = None
        # if icon is not None:
        #     self.setIcon(0, icon)

        self.update()

    def __eq__(self, other):
        if isinstance(other, WeightMapTreeItem):
            return self.item == other.item
        return NotImplemented

    def update(self):
        for i in range(3):
            self.setText(i, '')

        item = self.item
        data = item.data
        if self.subkey:
            data = item.data[self.subkey]

        if 'key' in data:
            self.setText(0, str(data['key']))
            self.setFlags(self.flags() | Qt.ItemIsEditable)

        if 'name' in data:
            self.setText(1, data['name'])
        if 'tag' in data:
            self.setText(2, data['tag'])

        if item.weightmap and not self.subkey:
            wm_str = item.weightmap.encode()
            if len(wm_str) > 24:
                h = hashlib.md5(wm_str.encode('utf-8'))
                wm_str = base64.b64encode(h.digest()).decode()
            self.setText(3, wm_str)

        if self.subkey:
            self.setForeground(0, WeightMapTreeItem.BRUSH_SUBKEY)
            self.setForeground(1, WeightMapTreeItem.BRUSH_ITEM)
            self.setForeground(2, WeightMapTreeItem.BRUSH_ITEM)

        # update children
        for i in range(self.childCount()):
            tree_item = self.child(i)
            tree_item.update()
