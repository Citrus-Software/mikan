# coding: utf-8

import math
import os.path
import __main__
import tempfile
from functools import partial

from six import iteritems
from xml.dom import minidom
import xml.etree.ElementTree as ET

import maya.mel
import maya.cmds as mc
import maya.api.OpenMaya as om
import maya.api.OpenMayaAnim as oma
from mikan.maya import cmdx as mx

from mikan.core.utils.yamlutils import ordered_load, ordered_dump
from mikan.core.utils.typeutils import filter_str
from mikan.core.logger import create_logger
from mikan.maya.lib.connect import connect_driven_curve

from mikan.vendor.Qt import QtWidgets, QtCore, QtGui
from mikan.vendor.Qt.QtCore import Qt, QSize
from mikan.vendor.Qt.QtWidgets import (
    QMainWindow, QSplitter, QHBoxLayout,
    QPushButton, QLineEdit, QMenu, QInputDialog, QToolButton, QLabel,
    QListWidget, QListWidgetItem, QTreeWidget, QTreeWidgetItem, QCheckBox
)
from mikan.vendor.Qt.QtGui import QPalette, QColor, QBrush

from mikan.core.ui.widgets import StackWidget, Icon, BusyCursor, get_palette_role
from mikan.maya.ui.widgets import Callback, OptVarSettings, find_widget

from ..core import Group, Control, Template, Mod, Nodes, Deformer
from ..lib.pose import *
from ..lib.configparser import ConfigParser

__all__ = ['PosingManager']

log = create_logger()


class PosingManager(QMainWindow, OptVarSettings):
    COLOR_ASSET_LOW = '#A98'
    COLOR_DFM_LOW = '#9A8'

    COLOR_POSE = '#a98'
    COLOR_EDIT = '#89a'
    COLOR_MODS = '#a89'
    COLOR_TOOL = '#888'

    ICON_SIZE = QtCore.QSize(16, 16)
    ICON_SAVE_MODS = Icon('write', color=COLOR_MODS, size=ICON_SIZE, tool=True)
    ICON_SAVE_POSE = Icon('link', color=COLOR_POSE, size=ICON_SIZE, tool=True)
    ICON_CLEAR_POSE = Icon('broom', color=COLOR_POSE, size=ICON_SIZE, tool=True)
    ICON_STORE_EDIT = Icon('write', color=COLOR_EDIT, size=ICON_SIZE, tool=True)
    ICON_STORE_SELECT = Icon('mouse', color=COLOR_TOOL, size=ICON_SIZE, tool=True)
    ICON_MUTE = Icon('remove', color=COLOR_POSE, size=ICON_SIZE, tool=True)

    ICON_SELECT_DRV = Icon('mouse', color=COLOR_POSE, size=ICON_SIZE, tool=True)
    ICON_RESET_DRV = Icon('reload', color=COLOR_POSE, size=ICON_SIZE, tool=True)

    ICON_RESET_GRP = Icon('reload', color=COLOR_EDIT, size=ICON_SIZE, tool=True)
    ICON_RESET_SEL = Icon('reload', color=COLOR_TOOL, size=ICON_SIZE, tool=True)

    ICON_RESET = Icon('reload', color='#777', size=ICON_SIZE, tool=True)

    STYLE_HEADER = 'font-size: 12px; font-weight: bold; color: #888'
    STYLE_LINEEDIT = 'border: none; background-color: #333;'

    def __init__(self, parent=None):
        QMainWindow.__init__(self, parent)
        self.setWindowFlags(Qt.Widget)

        self.group = None
        self.driver = None

        # build ui
        self.stack = StackWidget(parent=self)

        layout_left, layout_right = self.stack.add_columns(margins=2, stretch=(0, 1))
        layout_left.parent().setFixedWidth(225)

        # LEFT column

        # -- driver
        _row = self.stack.add_row(layout_left, height=20, spacing=2, margins=0)

        _b = QPushButton('Group')
        _b.clicked.connect(self.set_group)
        self.group_field = QLineEdit()
        self.group_field.setStyleSheet(self.STYLE_LINEEDIT)
        self.group_field.setReadOnly(True)
        self.group_field.setContextMenuPolicy(Qt.CustomContextMenu)
        self.group_field.customContextMenuRequested.connect(self.context_menu_group)

        _row.addWidget(_b, 2)
        _row.addWidget(self.group_field, 3)

        _row = self.stack.add_row(layout_left, height=20, spacing=2, margins=0)

        _b = QPushButton('Driver')
        _b.clicked.connect(self.set_driver)
        self.driver_field = QLineEdit()
        self.driver_field.setStyleSheet(self.STYLE_LINEEDIT)
        self.driver_field.setReadOnly(True)

        _row.addWidget(_b, 2)
        _row.addWidget(self.driver_field, 3)

        _row = self.stack.add_row(layout_left, height=20, spacing=2, margins=0)

        _b = QPushButton('Save mods', icon=self.ICON_SAVE_MODS)
        _b.clicked.connect(Callback(self.save_mods))
        _row.addWidget(_b, 4)

        self.chk_auto = QCheckBox('Auto')
        self.chk_auto.setStyleSheet('QCheckBox {padding: 3px;}')
        self.chk_auto.setCheckState(Qt.Checked if self.get_optvar('mod_auto', False) else Qt.Unchecked)
        self.chk_auto.toggled.connect(self.switch_chk_auto)
        _row.addWidget(self.chk_auto, 3)

        self.chk_clean = QCheckBox('Clean')
        self.chk_clean.setStyleSheet('QCheckBox {padding: 3px;}')
        self.chk_clean.setCheckState(Qt.Checked if self.get_optvar('mod_clean', False) else Qt.Unchecked)
        self.chk_clean.toggled.connect(self.switch_chk_clean)
        _row.addWidget(self.chk_clean, 3)

        # -- controllers

        _row = self.stack.add_row(layout_left, height=16, spacing=2, margins=0)
        _lbl = QLabel('Controllers')
        _lbl.setStyleSheet(self.STYLE_HEADER)
        _lbl.setAlignment(Qt.AlignCenter)
        _row.addWidget(_lbl)

        # -- srt edit
        _row = self.stack.add_row(layout_left, height=20, spacing=2, margins=0)

        btn_min_width = 78

        _b = QPushButton('All', icon=self.ICON_RESET_GRP)
        _b.setMinimumWidth(btn_min_width)
        _b.clicked.connect(Callback(self.reset_edit))
        _row.addWidget(_b, 3)

        _palette = _b.palette()
        _palette.setColor(QtGui.QPalette.ButtonText, QtGui.QColor('#bbb'))

        _b = QPushButton('Mirror >')
        _b.setPalette(_palette)
        _b.clicked.connect(Callback(self.mirror_edit, 1))
        _row.addWidget(_b, 2)
        _b = QPushButton('Flip')
        _b.setPalette(_palette)
        _b.clicked.connect(Callback(self.mirror_edit, 0))
        _row.addWidget(_b, 2)
        _b = QPushButton('< Mirror')
        _b.setPalette(_palette)
        _b.clicked.connect(Callback(self.mirror_edit, -1))
        _row.addWidget(_b, 2)

        _row = self.stack.add_row(layout_left, height=20, spacing=2, margins=0)

        _b = QPushButton('Selection', icon=self.ICON_RESET_SEL)
        _b.setMinimumWidth(btn_min_width)
        _b.clicked.connect(Callback(self.reset_edit, sel=1))
        _row.addWidget(_b, 3)

        _b = QPushButton('Mirror >')
        _b.setPalette(_palette)
        _b.clicked.connect(Callback(self.mirror_edit, 1, sel=1))
        _row.addWidget(_b, 2)
        _b = QPushButton('Flip')
        _b.setPalette(_palette)
        _b.clicked.connect(Callback(self.mirror_edit, 0, sel=1))
        _row.addWidget(_b, 2)
        _b = QPushButton('< Mirror')
        _b.setPalette(_palette)
        _b.clicked.connect(Callback(self.mirror_edit, -1, sel=1))
        _row.addWidget(_b, 2)

        _row_up = self.stack.add_row(layout_left, height=20, spacing=2, margins=0)
        _row_dn = self.stack.add_row(layout_left, height=20, spacing=2, margins=0)

        btn_width = 32
        for x in (0.1, 0.5, 2, 3, 4, 10):
            f = x
            label = u'×{}'
            if x < 1:
                label = '+{}'
                f += 1
            _b = QPushButton(label.format(x))
            _b.setPalette(_palette)
            _b.setMinimumWidth(btn_width)
            _b.clicked.connect(Callback(self.factor_edit, f))
            _row_up.addWidget(_b)

            f = 1. / x
            label = u'÷{}'
            if x < 1:
                label = '-{}'
                f = 1. / (1 + x)
            _b = QPushButton(label.format(x))
            _b.setPalette(_palette)
            _b.setMinimumWidth(btn_width)
            _b.clicked.connect(Callback(self.factor_edit, f))
            _row_dn.addWidget(_b)

        # -- shelf line
        self.shelf = Shelf()

        _row = self.stack.add_row(layout_left, height=16, spacing=2, margins=0)
        _lbl = QLabel('Shelf')
        _lbl.setStyleSheet(self.STYLE_HEADER)
        _lbl.setAlignment(Qt.AlignCenter)
        _row.addWidget(_lbl)

        _row = self.stack.add_row(layout_left, height=22, spacing=2, margins=0)

        _b = QPushButton('Save edit', icon=self.ICON_STORE_EDIT)
        _b.clicked.connect(self.store_edit)
        _row.addWidget(_b, 1)

        _b = QPushButton('Save Selection', icon=self.ICON_STORE_SELECT)
        _b.clicked.connect(self.store_select)
        _row.addWidget(_b, 1)

        # shelf widget
        layout_left.addWidget(self.shelf, 1)
        self.shelf.load_temp_shelf()

        # RIGHT column

        # -- pose edit
        self.shapes = ShapeAttributeEditor(self)

        _row = self.stack.add_row(layout_right, height=20, spacing=2, margins=0)

        _lbl = QLabel('Pose Editor')
        _lbl.setStyleSheet(self.STYLE_HEADER)
        _lbl.setAlignment(Qt.AlignCenter)
        _row.addWidget(_lbl, 1)

        _tb = QToolButton()
        _tb.setIcon(self.ICON_RESET)
        _tb.setStyleSheet(
            'QToolButton {border: none; margin: 0px;}'
            'QToolButton:pressed {padding-top: 1px; padding-left: 1px; padding-bottom: -1px}'
        )
        _tb.setAutoRaise(True)
        _tb.clicked.connect(self.shapes.reload)
        _row.addWidget(_tb)

        _row = self.stack.add_row(layout_right, height=20, spacing=2, margins=0)

        _b = QPushButton('Save', icon=self.ICON_SAVE_POSE)
        _b.clicked.connect(Callback(self.shapes.save_pose))
        _row.addWidget(_b, 2)
        _b = QPushButton('Clear', icon=self.ICON_CLEAR_POSE)
        _b.clicked.connect(Callback(self.shapes.clear_pose))
        _row.addWidget(_b, 2)
        _b = QPushButton('Reset', icon=self.ICON_RESET_DRV)
        _b.clicked.connect(Callback(self.shapes.reset_attributes, all=True))
        _row.addWidget(_b, 2)

        _row = self.stack.add_row(layout_right, height=20, spacing=2, margins=0)

        _b = QPushButton('Mute', icon=self.ICON_MUTE)
        _b.clicked.connect(Callback(self.mute_pose))
        _row.addWidget(_b, 2)
        _b = QPushButton('Recall')
        _b.clicked.connect(Callback(self.recall_pose))
        _row.addWidget(_b, 2)
        _b = QPushButton('Bake')
        _b.clicked.connect(Callback(self.bake_pose))
        _row.addWidget(_b, 2)

        # -- attribute editor
        layout_right.addWidget(self.shapes, 1)

        # phonemes
        self.phonemes = PhonemesManager()

        # layout
        splitter = QSplitter(Qt.Vertical)
        splitter.addWidget(self.stack)
        splitter.addWidget(self.phonemes)
        splitter.setStretchFactor(2, 1)
        splitter.setSizes([256, 128])
        self.setCentralWidget(splitter)

        # restore group/driver
        group_tag = self.get_optvar('group')
        if group_tag:
            nodes = Nodes.get_id(group_tag, as_list=True)
            if nodes:
                self.set_group(nodes[0])

        driver_tag = self.get_optvar('driver')
        if driver_tag:
            nodes = Nodes.get_id(driver_tag, as_list=True)
            if nodes:
                self.set_driver(nodes[0])

    def set_group(self, grp=None):
        Nodes.check_nodes()
        self.group = None
        self.group_field.setText('')

        if not grp:
            for node in mx.ls(sl=1, o=1):
                tpl = Template.get_from_node(node)
                asset = Nodes.get_asset_id(node)
                if tpl:
                    grp_id = '{}::group'.format(tpl.name)
                    grp = Nodes.get_id(grp_id, asset=asset)
                    break

        if not grp:
            return
        if not isinstance(grp, Group):
            grp = Group(grp)

        if self.group == grp:
            return
        poses = get_group_pose(grp)
        if not poses:
            log.warning('{} has no controller with pose nodes'.format(grp))
            grp_parents = list(grp.get_parents())
            if grp_parents:
                self.set_group(grp=grp_parents[0])
                return

        self.group = grp
        grps = self.group.get_all_parents()
        if len(grps) > 1:
            self.group = grps[-2]

        tag = '{}::group'.format(grp.node['gem_group'])
        if tag:
            self.set_optvar('group', tag)

        self.group_field.setText(tag)
        self.attach_group(nodes=poses)

        self.shapes.reload()

    def context_menu_group(self):

        menu = QMenu(self)

        grps = []
        for node in mx.ls(sl=1, o=1):
            tpl = Template.get_from_node(node)
            asset = Nodes.get_asset_id(node)
            if tpl:
                grp = Nodes.get_id('{}::group'.format(tpl.name), asset=asset)
                if grp:
                    grp = Group(grp)
                    grps = [grp] + grp.get_all_parents()
                    break

        for grp in grps:
            _act = menu.addAction(grp.get_name())
            _act.triggered.connect(Callback(self.set_group, grp))

        menu.exec_(QtGui.QCursor.pos())

    def set_driver(self, driver=None):
        Nodes.check_nodes()
        self.driver = None
        self.driver_field.setText('')

        if not driver:
            nodes = mx.ls(sl=1, type='transform')
        else:
            nodes = [driver]

        tag = None
        for node in nodes:
            try:
                tag = Nodes.get_node_id(node)
            except:
                continue

            if tag:
                break

        if tag is None:
            return

        self.driver_field.setText(tag)

        self.driver = node
        self.attach_driver()

        self.shapes.reload()

        self.set_optvar('driver', tag)

    def get_decimals(self):
        # return self.decimal_field.getValue()
        return 4

    def mute_pose(self):
        if self.group and self.driver:
            mute_group_pose(self.group)

    def recall_pose(self):
        if self.group and self.driver:
            recall_group_pose(self.group, self.driver, self.get_decimals())

    def bake_pose(self):
        if self.group and self.driver:
            bake_group_pose(self.group, self.driver, self.get_decimals())

    def reset_edit(self, sel=False):
        if sel:
            for node in mx.ls(sl=1, type='transform'):
                c = Control(node)
                if c:
                    for cmd in c.get_bind_pose_cmds():
                        cmd()
            return

        if self.group:
            for cmd in self.group.get_bind_pose_cmds():
                cmd()

    def mirror_edit(self, d, sel=False):
        if sel:
            for node in mx.ls(sl=1, type='transform'):
                c = Control(node)
                if c:
                    for cmd in c.get_mirror_cmds(d):
                        cmd()
            return

        if self.group:
            for cmd in self.group.get_mirror_cmds(d):
                cmd()

    def factor_edit(self, f):
        with mx.DGModifier() as md:
            for node in mx.ls(sl=1, type='transform'):
                for x in ('t', 'r', 's'):
                    plug = node[x]
                    if plug.editable:
                        v = plug.as_vector()
                        if x == 's':
                            v -= mx.Vector(1, 1, 1)
                            v *= f
                            v += mx.Vector(1, 1, 1)
                        else:
                            v *= f
                        md.set_attr(plug, v)

    def select_driver(self):
        if self.driver:
            mc.select(str(self.driver))

    def reset_driver(self):
        if self.driver:
            with mx.DGModifier() as md:
                for plug_name in mc.listAttr(str(self.driver), k=1, ud=1, c=1, s=1) or []:
                    md.set_attr(self.driver[plug_name], 0)

    def save_mods(self):
        with BusyCursor():
            if self.driver and self.group:
                export_plugs_to_mod(self.driver)
                export_driver_to_mod(self.driver, self.group)

    def switch_chk_auto(self):
        v = bool(self.chk_auto.checkState())
        self.set_optvar('mod_auto', v)

    def switch_chk_clean(self):
        v = bool(self.chk_clean.checkState())
        self.set_optvar('mod_clean', v)

    # API callbacks ----------------------------------------------------------------------------------------------------

    def attach_driver(self):
        if self.driver:
            node = self.driver.object()
            om.MNodeMessage.addNodeAboutToDeleteCallback(node, self.on_delete_driver)

    def on_delete_driver(self, node, mod, cli):
        try:
            self.driver = None
            self.driver_field.setText('')

            self.shapes.clear()

        except:
            pass

    def attach_group(self, nodes=None):
        if self.group:

            if nodes is None:
                nodes = get_group_pose(self.group)
            if not nodes:
                return

            node = nodes[0].object()
            om.MNodeMessage.addNodeAboutToDeleteCallback(node, self.on_delete_group)

    def on_delete_group(self, node, mod, cli):
        try:
            self.group = None
            self.group_field.setText('')
        except:
            pass

    # shelf ------------------------------------------------------------------------------------------------------------

    def store_edit(self):
        if not self.group:
            return

        ctrls = self.group.get_all_members()
        if not len(ctrls):
            mc.confirmDialog(m='{} is empty'.format(self.group))
            return

        # ask name
        mc.promptDialog(message='pose name:', button='ok', defaultButton='ok')
        name = mc.promptDialog(q=1, text=1)
        if not name:
            name = 'pose'
        else:
            name = filter_str(name)

        # create command
        cmd = create_group_cmd(self.group, decimals=self.get_decimals())

        # add button
        self.shelf.add_item(name, cmd, icon='faces', color='#789')

        self.shelf.save_temp_shelf()

    def store_select(self):
        ctrls = []

        for node in mx.ls(sl=1):
            if 'gem_id' in node and '::ctrls.' in node['gem_id'].read():
                ctrls.append(node)

        cmd = 'import maya.cmds as mc\n'
        cmd += 'mc.select(cl=1)\n'

        if ctrls:
            ctrls = ['"{}"'.format(ctrl) for ctrl in ctrls]
            cmd += 'mc.select(mc.ls([{}]))\n'.format(', '.join(ctrls))

        # ask name
        mc.promptDialog(message='selection name:', button='ok', defaultButton='ok')
        name = mc.promptDialog(q=1, text=1)
        if not name:
            name = 'sel'
        else:
            name = filter_str(name)

        # create button
        self.shelf.add_item(name, cmd, icon='selection', color='#888')
        self.shelf.save_temp_shelf()


class Shelf(QListWidget):
    STYLE_SHELF = 'QListWidget {background-color: #373737; border: none;}'
    SHELF_ICON_SIZE = QtCore.QSize(32, 32)

    def __init__(self, parent=None):
        super(Shelf, self).__init__(parent)

        self.setStyleSheet(self.STYLE_SHELF)
        self.setFocusPolicy(Qt.NoFocus)

        self.setViewMode(QtWidgets.QListView.IconMode)
        self.setUniformItemSizes(True)
        self.setMovement(QtWidgets.QListView.Static)

        self.setFlow(QtWidgets.QListView.LeftToRight)
        # self.setFlow(QtWidgets.QListView.TopToBottom)
        self.setResizeMode(QtWidgets.QListView.Adjust)

        self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)

    def resizeEvent(self, event):
        super(Shelf, self).resizeEvent(event)
        self.scheduleDelayedItemsLayout()
        self.repaint()

    def contextMenuEvent(self, event):
        item = self.itemAt(event.pos())

        menu = QMenu(self)

        if item:
            _act = menu.addAction('Delete')
            _act.triggered.connect(partial(self.remove_item, item))
            menu.addSeparator()

        _act = menu.addAction('Clear')
        _act.triggered.connect(self.clear_shelf)

        _act = menu.addAction('Clear Poses')
        _act.triggered.connect(partial(self.clear_shelf, pose=True))

        _act = menu.addAction('Clear Selections')
        _act.triggered.connect(partial(self.clear_shelf, sel=True))

        menu.addSeparator()
        _act = menu.addAction('Import')
        _act.triggered.connect(self.load_shelf)

        _act = menu.addAction('Export')
        _act.triggered.connect(self.save_shelf)

        menu.exec_(QtGui.QCursor.pos())

    def add_item(self, label, cmd, icon=None, color=None):
        kw = {'parent': self, 'label': label, 'cmd': cmd}
        if icon:
            kw['icon'] = icon
        if color:
            kw['color'] = color

        widget = ShelfButton(**kw)

        item = QListWidgetItem()
        item.setSizeHint(widget.sizeHint())
        self.addItem(item)

        self.setItemWidget(item, widget)

        # fix viewport
        self.scheduleDelayedItemsLayout()
        self.repaint()

    # io --------------------

    def remove_item(self, item):
        row = self.row(item)
        if row != -1:
            self.takeItem(row)
        self.save_temp_shelf()

    def clear_shelf(self, pose=False, sel=False):
        if pose == sel:
            self.clear()

        for i in reversed(range(self.count())):
            item = self.item(i)
            if not item:
                continue
            widget = self.itemWidget(item)
            if not widget:
                continue
            if pose and widget.icon == 'faces':
                self.takeItem(i)
            if sel and widget.icon == 'selection':
                self.takeItem(i)

        self.save_temp_shelf()

    def write_shelf(self, path):
        root = ET.Element('root')
        items = ET.SubElement(root, 'items')

        for i in range(self.count()):
            widget = self.itemWidget(self.item(i))
            cmd = '\n' + widget.cmd.strip('\n') + '\n'

            kw = {}
            if widget.icon:
                kw['icon'] = widget.icon
            if widget.color:
                kw['color'] = widget.color
            if widget.label:
                kw['label'] = widget.label

            ET.SubElement(items, 'item', **kw).text = cmd

        xmlstr = minidom.parseString(ET.tostring(root)).toprettyxml(indent='  ')

        f = open(path, 'w')
        try:
            f.write(xmlstr)
        finally:
            f.close()

    def read_shelf(self, path):
        if not os.path.exists(path):
            return

        tree = ET.parse(path)
        root = tree.getroot()

        for item in root.findall("./items/item"):
            cmd = item.text.strip('\n')
            label = item.attrib.get('label')
            icon = item.attrib.get('icon')
            color = item.attrib.get('color')
            self.add_item(label, cmd, icon, color)

    def save_shelf(self):
        project = os.path.realpath(mc.workspace(q=1, rd=1))
        path = mc.fileDialog2(ds=1, cap='save pose shelf', fm=0, dir=project, fileFilter="ASCII file (*)")
        if path:
            self.write_shelf(path[0])

    def load_shelf(self):
        project = os.path.realpath(mc.workspace(q=1, rd=1))
        path = mc.fileDialog2(ds=1, cap='load pose shelf', fm=1, dir=project, fileFilter="ASCII file (*)")
        if path:
            path = path[0]
            self.read_shelf(path)
            self.save_temp_shelf()

    def save_temp_shelf(self):
        path = os.path.join(tempfile.gettempdir(), 'mikan_posing.xml')
        self.write_shelf(path)

    def load_temp_shelf(self):
        path = os.path.join(tempfile.gettempdir(), 'mikan_posing.xml')
        self.read_shelf(path)


class ShelfButton(QToolButton):
    ICON_SIZE = QSize(32, 32)
    STYLE = 'QToolButton {border: none;} QToolButton:pressed {padding-top:1px; padding-left:1px;}'

    def __init__(self, parent=None, label='', icon=None, color=None, cmd=None):
        QToolButton.__init__(self, parent)
        self.setAutoRaise(True)
        self.setStyleSheet(self.STYLE)

        # icon
        if icon is None:
            icon = 'gear_color'

        self.setIcon(Icon(icon, size=ShelfButton.ICON_SIZE, tool=True, color=color, label=label))
        self.setIconSize(ShelfButton.ICON_SIZE)
        self.setFixedSize(ShelfButton.ICON_SIZE)

        self.label = label
        self.icon = icon
        self.color = color

        # command
        self.cmd = cmd
        self.clicked.connect(Callback(self.execute_cmd))

    def execute_cmd(self):
        if self.cmd is not None:

            if 'plug:\n' in self.cmd:
                Mod.execute_cmd(self.cmd)
            else:
                exec(self.cmd, __main__.__dict__)


class ShapeAttributeEditor(QTreeWidget):
    ICON_SIZE = QSize(14, 14)
    INDENT_SIZE = 12

    COLOR_BG = QColor('#373737')
    COLOR_BG_SL = QColor('#5f594e')
    COLOR_FG_SL = QColor('#eee')

    MAYA_PROXY_UI = '_tmp_mikan_window'

    def __init__(self, parent=None):
        super(ShapeAttributeEditor, self).__init__(parent=parent)

        self.manager = parent

        # behaviour
        self.setFocusPolicy(Qt.NoFocus)

        self.setColumnCount(2)
        self.setHeaderLabels(['Name', 'Weight'])
        self.setColumnWidth(0, 112)
        # self.setHeaderHidden(True)

        self.setExpandsOnDoubleClick(False)
        self.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)

        # style
        self.setIconSize(self.ICON_SIZE)
        self.setIndentation(self.INDENT_SIZE)

        self.setFrameShape(QtWidgets.QFrame.NoFrame)

        palette = self.palette()
        palette.setColor(QPalette.Base, self.COLOR_BG)
        palette.setColor(QPalette.Highlight, self.COLOR_BG_SL)
        palette.setColor(QPalette.HighlightedText, self.COLOR_FG_SL)
        self.setPalette(palette)

        self.setItemDelegate(ShapeEditorDelegate())

        # callbacks
        self.doubleClicked.connect(Callback(self.select_attributes))

    def contextMenuEvent(self, event):
        if not self.manager.driver:
            return

        item = self.itemAt(event.pos())
        menu = QMenu(self)

        if item:
            if item.blend:
                _act = menu.addAction('Toggle Sculpt Target')
                _act.triggered.connect(self.toggle_sculpt_target)
                menu.addSeparator()

            if not item.blend:
                _act = menu.addAction('Save Pose')
                _act.triggered.connect(Callback(self.save_pose))
                _act = menu.addAction('Clear Pose')
                _act.triggered.connect(Callback(self.clear_pose))

                _act = menu.addAction('Recall Pose')
                _act.triggered.connect(Callback(self.manager.recall_pose))
                _act = menu.addAction('Bake Pose')
                _act.triggered.connect(Callback(self.manager.bake_pose))
                _act = menu.addAction('Mute Pose')
                _act.triggered.connect(Callback(self.manager.mute_pose))

            if not item.blend:
                menu.addSeparator()
                _act = menu.addAction('Add Sculpt Target')
                _act.triggered.connect(Callback(self.add_sculpt_target))

            menu.addSeparator()
            _act = menu.addAction('Select Attributes')
            _act.triggered.connect(Callback(self.select_attributes))

            _act = menu.addAction('Reset Selected')
            _act.triggered.connect(Callback(self.reset_attributes))

        menu.addSeparator()
        if item:
            _act = menu.addAction('Remove Selected')
            _act.triggered.connect(Callback(self.remove_shapes))

        _act = menu.addAction('Add Shape')
        _act.triggered.connect(Callback(self.add_shape))

        _act = menu.addAction('Reset All')
        _act.triggered.connect(Callback(self.reset_attributes, all=True))

        menu.exec_(event.globalPos())

    def drawRow(self, painter, option, index):
        item = self.itemFromIndex(index)
        brush = item.background(0)
        painter.fillRect(option.rect, brush)

        if item.blend:
            palette = option.palette
            palette.setBrush(QPalette.Highlight, ShapeAttributeItem.BRUSH_BLEND_BG_SL)
            if item.sculpt:
                palette.setBrush(QPalette.Highlight, ShapeAttributeItem.BRUSH_BLEND_BG_SCULPT_SL)

        super(ShapeAttributeEditor, self).drawRow(painter, option, index)

    def reload(self):

        self.clear_items()
        if not self.manager:
            return

        if not self.manager.group:
            return

        driver = self.manager.driver
        if driver is None:
            return

        shapes_data = self.get_shape_plugs()

        plug_names = mc.listAttr(str(driver), ud=1, k=1) or []
        for plug_name in plug_names:
            plug = driver[plug_name]
            if plug.locked or not plug.keyable:
                continue

            item = self.add_attribute(plug)

            if plug_name in shapes_data:
                for plug_bs in shapes_data[plug_name]:
                    self.add_attribute(plug_bs, parent=item)

    def add_attribute(self, plug, parent=None):
        item = ShapeAttributeItem(plug)

        if parent is None:
            self.addTopLevelItem(item)
            item.setExpanded(True)
        else:
            parent.addChild(item)

        self.setItemWidget(item, 1, item.editor)
        return item

    def get_shape_plugs(self):
        data = {}

        if not self.manager:
            return data
        group = self.manager.group
        if group is None:
            return data

        group_name = self.manager.group.name

        # get plugs data
        cls = Deformer.get_class('blend')
        plugs = cls.get_all_group_target_plugs(group_name)

        for plug in plugs:
            _data = cls.get_target_plug_info(plug)

            target_name = _data['alias']
            if target_name not in data:
                data[target_name] = []

            data[target_name].append(plug)

        return data

    def get_all_items(self):
        all_items = []

        def iterate_items(parent):
            for i in range(parent.childCount()):
                child = parent.child(i)
                all_items.append(child)
                iterate_items(child)

        for i in range(self.topLevelItemCount()):
            top_item = self.topLevelItem(i)
            all_items.append(top_item)
            iterate_items(top_item)

        return all_items

    def clear_items(self):

        for i in range(self.topLevelItemCount()):
            item = self.topLevelItem(i)

            widget = self.itemWidget(item, 1)
            if widget:
                self.removeItemWidget(item, 1)
                widget.deleteLater()

            for i in range(item.childCount()):
                _item = item.child(i)

                widget = self.itemWidget(_item, 1)
                if widget:
                    self.removeItemWidget(_item, 1)
                    widget.deleteLater()

        self.clear()

        # clear maya sliders proxy
        if mc.window(self.MAYA_PROXY_UI, exists=True):
            mc.deleteUI(self.MAYA_PROXY_UI, window=True)

    # callbacks --------------------------------------------------------------------------------------------------------

    def select_attributes(self):
        items = self.selectedItems()

        plugs = []
        for item in items:
            plugs.append(item.plug.path())

        mc.select(str(items[0].node))
        self.display_channel_box()
        mc.evalDeferred(lambda: mc.channelBox('mainChannelBox', e=1, s=plugs))

    def display_channel_box(self):

        name = 'Channel Box / Layer Editor'
        component = maya.mel.eval('getUIComponentToolBar("{}", false);'.format(name))

        if component:
            visible = maya.mel.eval('isUIComponentVisible("{}");'.format(component))
            if not visible:
                mc.workspaceControl(component, edit=True, vis=True)
                return

        component = maya.mel.eval('getUIComponentDockControl("{}", false);'.format(name))

        if component:
            visible = maya.mel.eval('isUIComponentVisible("{}");'.format(component))
            if visible:
                if mc.workspaceControl(component, q=1, collapse=1):
                    mc.workspaceControl(component, edit=True, restore=True)
                else:
                    raised = maya.mel.eval('isUIComponentRaised("{}");'.format(component))
                    if not raised:
                        mc.workspaceControl(component, edit=True, restore=True)
            else:
                mc.warning('Channel Box is not ready!')

    def reset_attributes(self, all=False):
        items = self.selectedItems()
        if all:
            items = self.get_all_items()

        with mx.DGModifier() as md:
            for item in items:
                md.set_attr(item.plug, item.plug.default)

    def add_shape(self):
        if not self.manager.driver:
            return

        plug_name, ok = QInputDialog.getText(None, 'Add new shape', 'Shape name:')
        if not ok:
            return

        if plug_name not in self.manager.driver:
            with mx.DGModifier() as md:
                md.add_attr(self.manager.driver, mx.Double(plug_name, keyable=True))
            self.add_attribute(self.manager.driver[plug_name])

    def remove_shapes(self):
        if not self.manager.driver:
            return

        items = self.selectedItems()
        if not items:
            return

        # clear poses before removing attributes
        self.clear_pose()

        # sort items
        blend_items = [item for item in items if item.blend]
        shape_items = [item for item in items if not item.blend]

        for item in blend_items:
            self.remove_sculpt_target(item)

        for item in shape_items:
            children = []
            for i in range(item.childCount()):
                children.append(item.child(i))

            for _item in children:
                self.remove_sculpt_target(_item)

            # remove ui
            plug = item.plug

            index = self.indexOfTopLevelItem(item)
            if index != -1:
                self.takeTopLevelItem(index)
                del item

            # remove plug
            with mx.DGModifier() as md:
                md.delete_attr(plug)

    def save_pose(self):
        if not self.manager.group:
            _msg = 'Group not set'
            mc.inViewMessage(msg='Pose editor: <hl>' + _msg + '</hl>', pos='topCenter', fade=True)
            log.warning(_msg)
            return

        if not self.manager.driver:
            _msg = 'Driver not set'
            mc.inViewMessage(msg='Pose editor: <hl>' + _msg + '</hl>', pos='topCenter', fade=True)
            log.warning(_msg)
            return

        items = self.selectedItems()
        if not items:
            _msg = 'No channel selected'
            mc.inViewMessage(msg='Pose editor: <hl>' + _msg + '</hl>', pos='topCenter', fade=True)
            log.warning(_msg)
            return

        if len(items) > 1:
            _msg = 'Too many channels selected'
            mc.inViewMessage(msg='Pose editor: <hl>' + _msg + '</hl>', pos='topCenter', fade=True)
            log.warning(_msg)
            return

        item = items[0]

        if item.blend:
            _msg = 'Cannot save pose on sculpt attribute'
            mc.inViewMessage(msg='Pose editor: <hl>' + _msg + '</hl>', pos='topCenter', fade=True)
            log.warning(_msg)
            return

        driver = item.plug
        if driver.read() == 0:
            with mx.DGModifier() as md:
                md.set_attr(driver, 1)

        with BusyCursor():
            save_group_pose(self.manager.group, driver, decimals=self.manager.get_decimals())

        _msg = '<span style="color:lime">Pose saved</span>: {} = {}'.format(driver.name(), driver.read())
        mc.inViewMessage(msg=_msg, pos='topCenter', fade=True)

        # auto mod backup
        auto = bool(self.manager.chk_auto.checkState())
        if auto:
            with BusyCursor():
                export_plugs_to_mod(self.manager.driver)
                export_driver_to_mod(self.manager.driver, self.manager.group, plugs=[driver.name(long=False)])

    def clear_pose(self):
        if not self.manager.group:
            _msg = 'Group not set'
            mc.inViewMessage(msg='Pose editor: <hl>' + _msg + '</hl>', pos='topCenter', fade=True)
            log.warning(_msg)
            return

        if not self.manager.driver:
            _msg = 'Driver not set'
            mc.inViewMessage(msg='Pose editor: <hl>' + _msg + '</hl>', pos='topCenter', fade=True)
            log.warning(_msg)
            return

        items = self.selectedItems()
        if not items:
            _msg = 'No channel selected'
            mc.inViewMessage(msg='Pose editor: <hl>' + _msg + '</hl>', pos='topCenter', fade=True)
            log.warning(_msg)
            return

        plugs = []
        for item in items:
            if item.blend:
                continue
            plugs.append(item.plug)

        names = []

        for plug in plugs:
            clear_plug_pose(plug, keep_blendshape=True)

            with mx.DGModifier() as md:
                md.set_attr(plug, 0)

            names.append(plug.name())

        _msg = '<span style="color:lime">Pose cleared</span>: ' + ', '.join(names)
        mc.inViewMessage(msg=_msg, pos='topCenter', fade=True)

        # auto mod cleanup
        auto = bool(self.manager.chk_clean.checkState())
        if auto:
            with BusyCursor():
                export_plugs_to_mod(self.manager.driver)
                clear_driver_mod(self.manager.driver, plugs=plugs)

    def add_sculpt_target(self):
        items = self.selectedItems()
        if not items:
            if not items:
                _msg = 'No channel selected'
                mc.inViewMessage(msg='Pose editor: <hl>' + _msg + '</hl>', pos='topCenter', fade=True)
                log.warning(_msg)
                return

        # find geometries
        geometries = []

        for node in mx.ls(et='transform', sl=True):
            if 'gem_id' in node and '::ctrls' in node['gem_id'].read():
                continue  # exclude controller shapes
            shp = node.shape()
            if shp and mc.objectType(str(shp), isAType='deformableShape'):
                geometries.append(node)

        # select shapes
        _items = []
        for item in items:
            if item.blend:
                item = item.parent()
            if item not in _items:
                _items.append(item)
        items = _items

        # add targets
        group_name = self.manager.group.name

        for item in items:
            pose_name = item.plug.name()

            for geo in geometries:

                # find blend
                _blends = mx.ls(mc.listHistory(str(geo)), et='blendShape')
                if _blends:
                    blend = _blends[0]
                else:
                    blend = mc.blendShape(str(geo), automatic=True)
                    blend = mx.encode(blend[0])

                # check targets
                skip = False
                for t in blend['w'].array_indices:
                    _alias = mc.aliasAttr(blend['w'][t].path(), q=1)
                    if _alias == pose_name:
                        log.warning('target of {} already exists for {}'.format(geo, pose_name))
                        skip = True
                        break

                if skip:
                    continue

                # add target
                cls = Deformer.get_class('blend')
                t = cls.add_target(blend, weight=0, alias=pose_name)

                # group
                cls.group_target(blend['w'][t], group_name)

                # create default driven key
                if pose_name in self.manager.driver:
                    driver = self.manager.driver[pose_name]
                    connect_driven_curve(driver, blend['w'][t], {0: 0, 1: 1})

                # add attribute item
                self.add_attribute(blend['w'][t], parent=item)

                self.scheduleDelayedItemsLayout()

    def remove_sculpt_target(self, item):

        bs = item.node
        target = item.target_index

        # remove ui
        parent_item = item.parent()
        parent_item.removeChild(item)
        del item

        # remove target
        cls = Deformer.get_class('blend')
        cls.remove_target(bs, target)

    def toggle_sculpt_target(self):
        items = self.selectedItems()
        if not items:
            return

        for item in items:
            if item.blend:
                mc.sculptTarget(str(item.node), edit=True, target=item.target_index)

        for item in self.get_all_items():
            if not item.blend:
                continue
            item.update_sculpt_display()

        self.viewport().update()


class ShapeAttributeItem(QTreeWidgetItem):
    BRUSH_L = QBrush(QColor('#e99'))
    BRUSH_R = QBrush(QColor('#99e'))
    BRUSH_BLEND_FG = QBrush(QColor('#888'))
    BRUSH_BLEND_BG = QBrush(QColor('#2f2f2f'))
    BRUSH_BLEND_BG_SL = QBrush(QColor('#524d44'))
    BRUSH_BLEND_BG_SCULPT = QBrush(QColor('#622a2a'))
    BRUSH_BLEND_BG_SCULPT_SL = QBrush(QColor('#8d3f3f'))

    STYLE_SLIDER = '''
        QSlider::groove:horizontal {{
            background: #242424;
            margin-top: 6px;
            margin-bottom: 5px;
        }}
        QSlider::handle:horizontal {{
            background: {};
            border-radius: 2px;
            margin: -4px 0;
            width: 5px;
        }}
    '''
    STYLE_SLIDER_HANDLE = 'rgb(200, 200, 200)'
    STYLE_SLIDER_HANDLE_BS = 'rgb(100, 100, 100)'

    MAYA_PROXY_UI = '_tmp_mikan_window'

    def __init__(self, plug, parent=None):
        super(ShapeAttributeItem, self).__init__(parent)

        # item data
        self.plug = plug
        self.node = self.plug.node()

        self.blend = self.node.is_a(mx.tBlendShape)
        self.target_index = None
        self.sculpt = False

        # draw info
        plug_name = plug.name()

        label = plug_name
        if self.blend:
            cls = Deformer.get_class('blend')
            plug_data = cls.get_target_plug_info(plug)

            label = str(plug_data['geometry'])
            self.target_index = plug_data['index']

        self.setText(0, label)
        self.setTextAlignment(0, Qt.AlignVCenter)

        if self.blend:
            self.setForeground(0, self.BRUSH_BLEND_FG)
            self.update_sculpt_display()
        else:
            if plug_name.endswith('_L'):
                self.setForeground(0, self.BRUSH_L)
            elif plug_name.endswith('_R'):
                self.setForeground(0, self.BRUSH_R)

        # add maya slider widget
        self.editor = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout(self.editor)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        win = ShapeAttributeEditor.MAYA_PROXY_UI
        if not mc.window(win, exists=True):
            mc.window(win)
        mc.setParent(win)

        value = plug.read()
        min_value = 0
        max_value = 1
        if value < min_value:
            min_value = math.floor(value)
        if value > max_value:
            max_value = math.ceil(value)

        maya_widget = mc.attrFieldSliderGrp(at=plug.path(), precision=2, min=min_value, max=max_value, label='')
        widget = find_widget(maya_widget.split('|')[-1])

        slider = widget.findChildren(QtWidgets.QSlider)[0]
        if self.blend:
            slider_style = self.STYLE_SLIDER.format(self.STYLE_SLIDER_HANDLE_BS)
        else:
            slider_style = self.STYLE_SLIDER.format(self.STYLE_SLIDER_HANDLE)
        slider.setStyleSheet(slider_style)

        field = widget.findChildren(QtWidgets.QLineEdit)[0]
        field.setFixedWidth(34)

        field.textEdited.connect(self.on_field_update)
        self.editor_maya = maya_widget
        self.float_field = field

        layout.addWidget(slider)
        layout.addWidget(field)

    def __eq__(self, other):
        if not isinstance(other, ShapeAttributeItem):
            return False
        if self.plug.path() == other.plug.path():
            return True
        return False

    def __hash__(self):
        return hash(self.plug) ^ hash(ShapeAttributeItem)

    def update_sculpt_display(self):
        fn = oma.MFnGeometryFilter(self.node.object())
        obj = fn.getOutputGeometry()[0]
        oid = int(fn.indexForOutputShape(obj))

        sculpt_index = self.node['inputTarget'][oid]['sculptTargetIndex'].read()
        if sculpt_index == self.target_index:
            self.sculpt = True
            self.setData(0, Qt.BackgroundRole, self.BRUSH_BLEND_BG_SCULPT)
        else:
            self.sculpt = False
            self.setData(0, Qt.BackgroundRole, self.BRUSH_BLEND_BG)

    def on_field_update(self):
        min_value = mc.attrFieldSliderGrp(self.editor_maya, query=True, min=True)
        max_value = mc.attrFieldSliderGrp(self.editor_maya, query=True, max=True)
        try:
            value = float(self.float_field.text())
        except:
            return

        # update min/max
        if value > max_value:
            max_value = math.ceil(value)
            mc.attrFieldSliderGrp(self.editor_maya, edit=True, max=max_value)
        if value < min_value:
            min_value = math.floor(value)
            mc.attrFieldSliderGrp(self.editor_maya, edit=True, min=min_value)


class ShapeEditorDelegate(QtWidgets.QItemDelegate):
    role_highlighted = get_palette_role('HighlightedText')
    role_foreground = get_palette_role('Text')

    def paint(self, painter, option, index):

        # foreground color highlight
        palette = option.palette

        w = option.styleObject
        item = w.itemFromIndex(index)
        if item.isSelected():
            color = item.foreground(index.column()).color()
            if color == Qt.black:
                color = palette.color(self.role_foreground)

            palette.setColor(self.role_highlighted, color)

        option.palette = palette
        QtWidgets.QItemDelegate.paint(self, painter, option, index)


class PhonemesManager(StackWidget):
    ICON_ADD = Icon('cross', color='#999')
    ICON_RELOAD = Icon('reload', color='#999')

    ICON_PHO = Icon('cross', color='#777')
    ICON_MOD = Icon('cross', color='#777')

    STYLE_PHO = 'background-color: #4b4b4b; color: #999'
    STYLE_MOD = 'background-color: #4b4b4b; color: #999'

    def __init__(self, parent=None):
        StackWidget.__init__(self, parent)

        _collapse = self.add_collapse('Phonemes')
        self.grid = self.add_grid(_collapse)
        _collapse.addStretch(1)

        self.setStyleSheet(
            'QLabel {font-weight: bold;}'
        )

        # data
        self.node = None
        self.cfg = None

        self.phonemes = {}
        self.phonemes['src'] = ['chan_face::node']
        self.phonemes['pho'] = []
        self.phonemes['mod'] = []
        self.phonemes['poses'] = {}

        self.load()

    def clear(self):
        self.clear_layout(self.grid)

        _b = QPushButton('Add phonemes')
        _b.setIcon(PhonemesManager.ICON_ADD)

        _b.clicked.connect(self.create_node)
        self.grid.addWidget(_b, 0, 0)

    def load(self):
        self.clear()

        self.find_node()
        if not self.node:
            return
        else:
            self.clear_layout(self.grid)

            self.grid.setColumnMinimumWidth(0, 64)
            self.attach_node()

        # build ui
        _b = QPushButton('Reload')
        _b.setIcon(PhonemesManager.ICON_RELOAD)

        _b.clicked.connect(self.load)
        self.grid.addWidget(_b, 0, 0)

        _c = self.add_column()

        for i, mod in enumerate([''] + self.phonemes['mod']):
            _b = QLabel(mod)
            self.grid.addWidget(_b, 0, i + 1, align=Qt.AlignCenter)
            self.grid.setColumnMinimumWidth(i + 1, 72)

        for i, pho in enumerate([''] + self.phonemes['pho']):
            _b = QLabel(pho)
            self.grid.addWidget(_b, i + 1, 0, align=Qt.AlignRight)

        c = len(self.phonemes['pho']) + 2
        _b = QPushButton('phoneme')
        _b.clicked.connect(self.add_pho)
        _b.setIcon(PhonemesManager.ICON_PHO)
        _b.setStyleSheet(PhonemesManager.STYLE_PHO)
        self.grid.addWidget(_b, c, 0)

        c = len(self.phonemes['mod']) + 2
        _b = QPushButton('mode')
        _b.clicked.connect(self.add_mod)
        _b.setIcon(PhonemesManager.ICON_MOD)
        _b.setStyleSheet(PhonemesManager.STYLE_MOD)
        self.grid.addWidget(_b, 0, c)
        self.grid.setColumnMinimumWidth(c, 72)

        self.grid.setColumnStretch(c + 1, 1)

        for i, mod in enumerate([None] + self.phonemes['mod']):
            for j, pho in enumerate([None] + self.phonemes['pho']):
                _get = QPushButton('get')
                _set = QPushButton('set')

                _get.clicked.connect(Callback(self.get, pho, mod))
                _set.clicked.connect(Callback(self.set_callback, pho, mod))

                col_pho = '#ddd'
                col_mod = '#bbb'
                if i and not j:
                    col_pho = '#bbdee7'
                    col_mod = '#7aafbc'
                elif not i and j:
                    col_pho = '#fffeb8'
                    col_mod = '#d0cf8c'
                elif not i and not j:
                    col_pho = '#bdecc1'
                    col_mod = '#99d09e'

                _get.setStyleSheet('background-color:' + col_pho + '; color: black')
                _set.setStyleSheet('background-color:' + col_mod + '; color: black')

                _layout = QHBoxLayout(self)
                _layout.setSpacing(0)
                _layout.setContentsMargins(0, 0, 0, 0)
                _layout.addWidget(_get)
                _layout.addWidget(_set)
                self.grid.addLayout(_layout, j + 1, i + 1, align=Qt.AlignCenter)

    def find_node(self):
        self.node = None
        self.cfg = None

        nodes = mx.ls('_phonemes', et='transform', r=1)
        for node in nodes:
            if not node.exists:
                continue
            self.node = node
            self.cfg = ConfigParser(self.node)
            self.parse()

    def create_node(self):
        self.find_node()
        if not self.node:
            with mx.DagModifier() as md:
                self.node = md.create_node(mx.tTransform, name='_phonemes')
            self.cfg = ConfigParser(self.node)
            self.write()

        self.load()

    # API callbacks ------------------------------------------------------------

    def attach_node(self):
        if self.node:
            node = self.node.object()
            om.MNodeMessage.addNodePreRemovalCallback(node, self.on_delete_node)

    def on_delete_node(self, *args):
        try:
            self.node = None
            self.clear()
        except:
            pass

    # I/O ----------------------------------------------------------------------

    def write(self):
        data = {'phonemes': self.phonemes}
        _n = ordered_dump(data, default_flow_style=False)
        self.cfg['mod'].write(_n)

    def parse(self):
        self.phonemes = ordered_load(self.cfg['mod'].read())['phonemes']

    def get_sources(self):
        ctrls = []

        for src_id in self.phonemes['src']:
            nodes = Nodes.get_id(src_id)
            if not nodes:
                continue
            if not isinstance(nodes, list):
                nodes = [nodes]
            for node in nodes:
                if 'gem_type' in node:
                    if node['gem_type'].read() == Control.type_name:
                        if get_ctrl_pose(node):
                            ctrls.append(node)
                    elif node['gem_type'].read() == Group.type_name:
                        grp = Group(node)
                        for n in grp.get_all_nodes():
                            c = get_ctrl_pose(n)
                            if c:
                                ctrls.append(c)
                    else:
                        ctrls.append(node)
                else:
                    ctrls.append(node)

        return ctrls

    def get_blend_targets(self):

        targets = []
        # groups = []
        # drivers = []
        #
        # for src_id in self.phonemes['src']:
        #     nodes = Nodes.get_id(src_id)
        #     if not nodes:
        #         continue
        #     if not isinstance(nodes, list):
        #         nodes = [nodes]
        #     for node in nodes:
        #         if 'gem_type' in node and node['gem_type'].read() == Group.type_name:
        #             groups.append(Group(node))
        #         elif 'gem_id' in node:
        #             drivers.append(node)
        #
        # groups = [grp.name for grp in groups]
        # drivers = set([str(driver) for driver in drivers])
        groups = ['phonemes']

        for bs in mx.ls(et='blendShape'):

            _groups = []
            for i in bs['targetDirectory'].array_indices:
                if i == 0:
                    continue
                if bs['targetDirectory'][i]['dtn'].read() in groups:
                    _groups.append(i)

            if not _groups:
                continue

            for t in bs['parentDirectory'].array_indices:
                if bs['parentDirectory'][t].read() in _groups:
                    plug = bs['w'][t]

                    # i = plug.input()
                    # if i is not None:
                    #     history = set(mc.listHistory(str(i)) or [])
                    #     if not set(history).isdisjoint(drivers):
                    #         continue

                    targets.append(plug)

        return targets

    def set_callback(self, pho, mod):
        with BusyCursor():
            try:
                self.set(pho, mod)
                log.info('phoneme {}{} saved'.format(pho, '.' + mod if mod else ''))
            except:
                log.error('failed to save phoneme {}{}'.format(pho, '.' + mod if mod else ''))

    def set(self, pho, mod):

        if 'poses' not in self.phonemes:
            self.phonemes['poses'] = dict()
        if not isinstance(self.phonemes['poses'], dict):
            self.phonemes['poses'] = dict()

        db = self.phonemes['poses']

        # reset stored phoneme
        if pho not in db:
            db[pho] = {}
        db[pho][mod] = {}

        # store phoneme
        for src in self.get_sources():
            is_ctrl = False
            tag = Nodes.get_node_id(src, find='::ctrls')
            if '::ctrls' in tag:
                is_ctrl = True

            # pose > ctrl
            _src = src
            _tag = Nodes.get_node_id(src, find='::poses')
            if '::poses' in _tag:
                is_ctrl = True
                _tag = _tag.replace('::poses', '::ctrls')
                _src = Nodes.get_id(_tag) or src

            # xfo plugs
            if is_ctrl:
                for srt in 'srt':
                    for dim in 'xyz':
                        attr = _src[srt + dim]
                        if attr.editable:
                            v = attr.read()
                            dv = 0
                            if srt == 's':
                                v -= 1
                            if attr.type_class() == mx.Angle:
                                v = mx.Radians(v).asDegrees()
                            v = round(v, 3)

                            key = tag + '@' + srt + '.' + dim
                            if mod:
                                if pho in db and None in db[pho] and key in db[pho][None]:
                                    v -= db[pho][None][key]
                            if pho:
                                if None in db and mod in db[None] and key in db[None][mod]:
                                    v -= db[None][mod][key]
                            if v != dv:
                                db[pho][mod][key] = v

            # custom plugs
            else:
                for attr in mc.listAttr(str(src), ud=1, k=1) or []:
                    attr = src[attr]
                    v = attr.read()
                    dv = attr.default

                    key = tag + '@' + attr.name(long=False)
                    if mod:
                        if pho in db and None in db[pho] and key in db[pho][None]:
                            v -= db[pho][None][key]
                    if pho:
                        if None in db and mod in db[None] and key in db[None][mod]:
                            v -= db[None][mod][key]
                    if v != dv:
                        db[pho][mod][key] = round(v, 2)

        for attr in self.get_blend_targets():
            v = attr.read()
            dv = attr.default

            bs = attr.node()
            shp = mc.blendShape(str(bs), q=1, g=1)
            geo = mx.encode(shp[0]).parent()
            dfm = Deformer.create(geo, bs, read=False)
            tag = dfm.get_id()

            key = '{}@weight.{}'.format(tag, attr.plug().logicalIndex())
            if mod:
                if pho in db and None in db[pho] and key in db[pho][None]:
                    v -= db[pho][None][key]
            if pho:
                if None in db and mod in db[None] and key in db[None][mod]:
                    v -= db[None][mod][key]
            if v != dv:
                db[pho][mod][key] = round(v, 2)

        self.write()

    def get(self, pho, mod):

        # reset phoneme sources
        for src in self.get_sources():

            # pose > ctrl
            is_ctrl = False
            _src = src
            _tag = Nodes.get_node_id(src, find='::poses')
            if '::poses' in _tag:
                is_ctrl = True
                _tag = _tag.replace('::poses', '::ctrls')
                _src = Nodes.get_id(_tag) or src

            # reset plugs
            for srt in 'srt':
                for dim in 'xyz':
                    plug = _src[srt + dim]
                    if plug.editable:
                        v = 0
                        if srt == 's':
                            v = 1
                        with mx.DagModifier() as md:
                            md.set_attr(plug, v)

            if not is_ctrl:
                for attr in mc.listAttr(str(src), ud=1, k=1) or []:
                    plug = src[attr]
                    if plug.editable:
                        v = plug.default
                        with mx.DagModifier() as md:
                            md.set_attr(plug, v)

        for plug in self.get_blend_targets():
            if plug.editable:
                v = plug.default
                with mx.DagModifier() as md:
                    md.set_attr(plug, v)

        # restore phoneme
        if 'poses' not in self.phonemes:
            self.phonemes['poses'] = dict()
        if not isinstance(self.phonemes['poses'], dict):
            self.phonemes['poses'] = dict()

        db = self.phonemes['poses']
        values = []

        if pho in db:
            if mod in db[pho]:
                values.append(db[pho][mod])
            if mod:
                if None in db[pho]:
                    values.append(db[pho][None])
        if pho:
            if None in db and mod in db[None]:
                values.append(db[None][mod])

        for v in values:
            for tag, v in iteritems(v or {}):
                # pose > ctrl
                if '::poses' in tag:
                    tag = tag.replace('::poses', '::ctrls')

                if '->' in tag:
                    plug = Deformer.get_geometry_id(tag)
                    if plug:
                        plug = plug[0]
                else:
                    plug = Nodes.get_id(tag)
                if not plug:
                    pass
                    # log.warning()

                # restore
                if isinstance(plug, mx.Plug) and plug.editable:
                    if plug.type_class() == mx.Angle:
                        v = mx.Degrees(v).asRadians()
                    with mx.DagModifier() as md:
                        md.set_attr(plug, plug.read() + v)

    def add_mod(self):
        # ask name
        mc.promptDialog(message='mode:', button='ok', defaultButton='ok')
        name = mc.promptDialog(q=1, text=1)

        if name and name not in self.phonemes['mod']:
            self.phonemes['mod'].append(name)
            self.write()
            self.load()

    def add_pho(self):
        # ask name
        mc.promptDialog(message='phoneme:', button='ok', defaultButton='ok')
        name = mc.promptDialog(q=1, text=1)

        if name and name not in self.phonemes['pho']:
            self.phonemes['pho'].append(name)
            self.write()
            self.load()
