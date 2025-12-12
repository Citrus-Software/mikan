# coding: utf-8

import os.path

import maya.cmds as mc
from mikan.maya import cmdx as mx

import mikan.templates.shapes
from mikan.maya.core import Nodes, Shape, Control

from mikan.maya.ui.widgets import Callback

from mikan.vendor.Qt import QtCore
from mikan.vendor.Qt.QtCore import Qt
from mikan.vendor.Qt.QtWidgets import (
    QPushButton, QToolButton, QListWidget, QListView, QListWidgetItem,
    QLabel, QButtonGroup, QRadioButton, QCheckBox
)
from mikan.core.ui.widgets import *
from mikan.core.logger import create_logger

log = create_logger()


class ShapesManager(StackWidget):
    def __init__(self, parent=None):
        StackWidget.__init__(self, parent)

        _main_stack = self.add_column()

        self.setStyleSheet('QLabel {color:#89a; font-size:12px; font-weight:bold; margin-left:2px;}')

        # add collapse 'shapes'
        _box = self.add_collapse('Shapes', parent=_main_stack)
        _box_row = self.add_row(_box)

        _shelf = QListWidget()
        self.shelf_shape = _shelf
        _box_row.addWidget(_shelf, stretch=3)

        _shelf.setViewMode(QListView.IconMode)
        _shelf.setMovement(QListView.Static)
        _shelf.setFlow(QListView.LeftToRight)
        _shelf.setResizeMode(QListView.Adjust)
        _shelf.setUniformItemSizes(True)
        _shelf.setFixedHeight(275)
        _shelf.setSpacing(0)
        _shelf.setStyleSheet('QListWidget {background-color: #333; border: none;}')
        _shelf.setContextMenuPolicy(Qt.NoContextMenu)
        _shelf.setFocusPolicy(Qt.NoFocus)

        shapes_list = Shape.shapes
        for shape in sorted(shapes_list):
            self.shelf_add_shape(shape)

        # shapes toolbar
        _col = self.add_column(_box_row, spacing=1, margins=0)

        self.chk_selection = QCheckBox('use selection')
        self.chk_selection.setChecked(True)
        _col.addWidget(self.chk_selection)

        _col.addSpacing(6)

        _lbl = QLabel('selection :')
        _col.addWidget(_lbl)

        _grp = QButtonGroup(_col)

        self.btn_mode_replace = QRadioButton('replace/add')
        _grp.addButton(self.btn_mode_replace)
        self.btn_mode_add = QRadioButton('inject')
        _grp.addButton(self.btn_mode_add)

        _col.addWidget(self.btn_mode_replace, Qt.AlignRight)
        _col.addWidget(self.btn_mode_add, Qt.AlignRight)
        self.btn_mode_replace.setChecked(True)

        _col.addSpacing(4)

        self.chk_keep_color = QCheckBox('keep color')
        self.chk_keep_color.setChecked(True)
        _col.addWidget(self.chk_keep_color)

        _col.addSpacing(6)

        _lbl = QLabel('axis :')
        _col.addWidget(_lbl)

        _grp = QButtonGroup(_col)
        _row = self.add_row(_col, spacing=0, margins=0)

        self.btn_axis = {}
        for axe in 'xyz':
            btn_axis = QRadioButton(axe)
            _grp.addButton(btn_axis)
            _row.addWidget(btn_axis)

            if axe == 'y':
                btn_axis.setChecked(True)
            self.btn_axis[axe] = btn_axis

        _col.addSpacing(6)

        _lbl = QLabel('shapes :')
        _col.addWidget(_lbl)

        _col.addSpacing(4)
        _btn = QPushButton('copy')
        _btn.setToolTip('select sources then destination')
        _btn.clicked.connect(Callback(self.copy_shape, world=True))
        _col.addWidget(_btn)

        _btn = QPushButton('copy local')
        _btn.setToolTip('select sources then destination')
        _btn.clicked.connect(Callback(self.copy_shape, world=False))
        _col.addWidget(_btn)

        _btn = QPushButton('delete')
        _btn.setToolTip('delete shapes from selected transforms')
        _btn.clicked.connect(Callback(self.remove_shape))
        _col.addWidget(_btn)

        _btn = QPushButton('rig to tpl')
        _btn.setToolTip('copy shapes from rig to template')
        _btn.clicked.connect(Callback(self.copy_shape_to_template))
        _col.addWidget(_btn)

        _col.parent().setStyleSheet(
            'QPushButton {max-height: 16px;}'
        )

        _col.addStretch()

        # deform shape
        _box = self.add_collapse('Shape Toolbox', parent=_main_stack)
        _box.addSpacing(2)

        _row = self.add_row(_box, spacing=1, margins=0)
        _row.addSpacing(6)

        _col = self.add_column(_row, spacing=0, margins=0)
        _col.parent().setMinimumWidth(64)

        _lbl = QLabel('scale :')
        _col.addWidget(_lbl)

        _grp = QButtonGroup(_col)
        self.btn_scale_pivot = QRadioButton('pivot')
        _grp.addButton(self.btn_scale_pivot)
        self.btn_scale_center = QRadioButton('center')
        _grp.addButton(self.btn_scale_center)

        _col.addWidget(self.btn_scale_pivot, Qt.AlignRight)
        _col.addWidget(self.btn_scale_center, Qt.AlignRight)
        self.btn_scale_pivot.setChecked(True)

        _col = self.add_column(_row, spacing=1, margins=0)
        _row1 = self.add_row(parent=_col, height=25, spacing=1, margins=0)
        _row2 = self.add_row(parent=_col, height=25, spacing=1, margins=0)
        _col.addStretch()

        for x in (0.1, 0.5, 2, 3, 4, 10):
            f = x
            label = u'×{}'
            if x < 1:
                label = '+{}'
                f += 1

            _b = QPushButton(label.format(x))
            _b.clicked.connect(Callback(self.scale_shape, f))
            _row1.addWidget(_b, 1)

            f = 1. / x
            label = u'÷{}'
            if x < 1:
                label = '-{}'
                f = 1. / (1 + x)

            _b = QPushButton(label.format(x))
            _b.clicked.connect(Callback(self.scale_shape, f))
            _row2.addWidget(_b, 1)

        # maya colors
        _box = self.add_collapse('Maya colors', parent=_main_stack)
        _box.collapse.setMaximumHeight(72)

        _shelf = QListWidget()
        _box.addWidget(_shelf)

        _shelf.setViewMode(QListView.IconMode)
        _shelf.setMovement(QListView.Static)
        _shelf.setFlow(QListView.LeftToRight)
        _shelf.setResizeMode(QListView.Adjust)
        _shelf.setUniformItemSizes(True)
        _shelf.setSpacing(0)
        _shelf.setStyleSheet('QListWidget {background-color: #333; border: none;}')
        _shelf.setContextMenuPolicy(Qt.NoContextMenu)
        _shelf.setFocusPolicy(Qt.NoFocus)

        for color in Shape.maya_color_list:
            self.shelf_add_color(_shelf, color)

        # css colors
        _box = self.add_collapse('CSS colors', parent=_main_stack)

        _shelf = QListWidget()
        _box.addWidget(_shelf)

        _shelf.setViewMode(QListView.IconMode)
        _shelf.setMovement(QListView.Static)
        _shelf.setFlow(QListView.LeftToRight)
        _shelf.setResizeMode(QListView.Adjust)
        _shelf.setMinimumHeight(224)
        _shelf.setUniformItemSizes(True)
        _shelf.setSpacing(0)
        _shelf.setStyleSheet('QListWidget {background-color: #333; border: none}')
        _shelf.setContextMenuPolicy(Qt.NoContextMenu)
        _shelf.setFocusPolicy(Qt.NoFocus)

        colors = list(Shape.color_names)
        colors.sort(key=lambda c: Shape.color_step_hex(Shape.color_names[c], 8))

        for color in colors:
            self.shelf_add_color(_shelf, color)

        # end of stack
        _main_stack.addStretch(1)

    def shelf_add_shape(self, shape):
        widget = QToolButton(self.shelf_shape)
        widget.setAutoRaise(True)
        widget.setStyleSheet('QToolButton {border:none} QToolButton:pressed {padding-top:1px; padding-left:1px;}')

        size = 36
        path = os.path.join(mikan.templates.shapes.__path__[0], 'icons')
        icon = Icon(shape, size=size, tool=True, path=path)
        widget.setIcon(icon)
        widget.setIconSize(QtCore.QSize(size, size))
        widget.setToolTip(shape)

        widget.clicked.connect(Callback(self.create_shape, shape))

        item = QListWidgetItem()
        item.setSizeHint(widget.sizeHint())

        self.shelf_shape.insertItem(self.shelf_shape.count(), item)
        self.shelf_shape.setItemWidget(item, widget)

    def shelf_add_color(self, shelf, color):
        rgb = color
        if isinstance(color, str):
            rgb = Shape.color_to_rgb(color)
        hex = Shape.rgb_to_hex(rgb)

        widget = QPushButton(shelf)
        widget.setStyleSheet('QPushButton {background-color: ' + hex + '; max-width: 30px;}')
        if isinstance(color, str):
            widget.setToolTip(color)
        widget.clicked.connect(Callback(self.set_color, color))

        item = QListWidgetItem()
        item.setSizeHint(QtCore.QSize(24, 24))

        shelf.insertItem(shelf.count(), item)
        shelf.setItemWidget(item, widget)

    # callbacks ----------------------------------------------------------------

    def get_shape_relatives(self, node):
        if not isinstance(node, mx.Node):
            node = mx.encode(str(node))

        parent = node.parent()
        nodes = {
            'node': None,  # input
            'tpl': None,  # template shapes root
            'shapes': [],  # template shapes
            'ctrl': False,  # if input is controller
            'shape': None,  # selected curve
        }

        if node.is_a(mx.tNurbsCurve):
            nodes['shape'] = node
            node = node.parent()
        else:
            nodes['node'] = node

        if 'gem_shape' in node:
            nodes['node'] = None
            nodes['tpl'] = node

        elif 'gem_type' in node and node['gem_type'].read() == Control.type_name:
            nodes['ctrl'] = True
            nodes['node'] = node

            node_id = Nodes.get_node_id(node, find='ctrls')
            try:
                asset_id = Nodes.get_asset_id(node)
                shp_tpl = Nodes.shapes[asset_id][node_id]
                nodes['tpl'] = shp_tpl
            except:
                pass

        elif parent and 'gem_shape' in parent:
            nodes['tpl'] = parent

        else:
            for c in node.children():
                if 'gem_shape' in c:
                    nodes['tpl'] = c
                    break

        if nodes['tpl']:
            for shp in nodes['tpl'].children():
                if not shp['v'].read():
                    continue
                if Shape(shp).get_shapes():
                    nodes['shapes'].append(shp)

        return nodes

    def opt_axis(self):
        for axis, btn in self.btn_axis.items():
            if btn.isChecked():
                return axis

    def opt_selection(self):
        return self.chk_selection.isChecked()

    def opt_mode(self):
        if self.btn_mode_add.isChecked():
            return 'inject'
        else:
            return 'replace'

    def opt_scale(self):
        if self.btn_scale_center.isChecked():
            return 'center'
        else:
            return 'pivot'

    def create_shape(self, shape):
        axis = self.opt_axis()
        mode = self.opt_mode()
        sel = mx.ls(sl=True)
        results = []

        if not self.opt_selection() or len(sel) == 0:
            Shape.create(shape, axis=axis)
            return

        for obj in sel:
            shp_src = Shape.create(shape, axis=axis).node

            nodes = self.get_shape_relatives(obj)
            parent = obj.parent()
            result = nodes['node']
            saved_color = None
            saved_dim = None

            # ctrl selected
            if nodes['ctrl']:
                if parent:
                    mc.parent(str(shp_src), str(parent), r=1)
                s = Shape(nodes['node'])
                saved_color = s.get_color()
                saved_dim = s.get_dimensions()

                if mode == 'replace':
                    s.remove()

                s.copy(shp_src, world=True)
                if saved_color:
                    s.set_color(saved_color)

                if mode == 'replace':
                    size = max(saved_dim)
                    if size > 0:
                        s.scale(size, absolute=True)

                mx.delete(shp_src)

            # template selected
            elif nodes['tpl']:
                s = Shape(shp_src)
                if mode == 'replace':
                    bb = mx.BoundingBox()
                    for _shp in list(nodes['tpl'].children()):
                        _s = Shape(_shp)
                        if not _s.get_shapes():
                            continue
                        if self.chk_keep_color.isChecked() and saved_color is None:
                            saved_color = _s.get_color()
                        bb.expand(_shp.bounding_box)

                        if _shp.is_referenced():
                            _shp['v'] = False
                        else:
                            mx.delete(_shp)

                    saved_dim = [bb.width, bb.height, bb.depth]

                mc.parent(str(s.node), str(nodes['tpl']), r=1)
                if saved_color:
                    s.set_color(saved_color)
                if saved_dim and max(saved_dim) > 0:
                    s.scale(max(saved_dim), absolute=True)

                result = shp_src

            # any other case
            else:
                mc.parent(str(shp_src), str(nodes['node']), r=1)
                s = Shape(nodes['node'])

                if mode == 'inject':
                    result = shp_src
                    if Shape(obj).get_shapes():
                        mc.parent(str(shp_src), str(parent))

                elif mode == 'replace' and s.get_shapes():
                    if self.chk_keep_color.isChecked() and saved_color is None:
                        saved_color = s.get_color()
                    saved_dim = s.get_dimensions()

                    s.remove()
                    s.copy(shp_src, world=True)
                    if max(saved_dim) > 0:
                        s.scale(max(saved_dim), absolute=True)
                    if saved_color:
                        s.set_color(saved_color)

                    # set controller
                    if 'gem_shape_name' in s.node:
                        s.node['gem_shape_name'] = shape
                    if 'gem_shape_axis' in s.node:
                        s.node['gem_shape_axis'] = axis

                    mx.delete(shp_src)

            results.append(result)

        mx.cmd(mc.select, results)

    def copy_shape(self, world=False):
        sel = mx.ls(sl=1)
        if len(sel) <= 1:
            return

        src = sel[0]
        for obj in sel[1:]:
            nodes = self.get_shape_relatives(obj)

            # template root selected
            if nodes['tpl']:
                shp = Shape(src).duplicate_shape()
                mc.parent(str(shp), str(nodes['tpl']), r=not world)
                if not world:
                    for attr in 'srt':
                        shp[attr] = src[attr]
                continue

            s = Shape(obj)
            s.copy(src, world=world)

    def remove_shape(self):
        for obj in mx.ls(sl=1):
            nodes = self.get_shape_relatives(obj)

            # remove selection
            if nodes['shape']:
                try:
                    mx.delete(nodes['shape'])
                except:
                    nodes['shape'].lodVisibility.set(0)
            elif nodes['node']:
                Shape(nodes['node']).remove()

            # remove template shapes
            if nodes['tpl']:
                for _shp in nodes['shapes']:
                    if _shp.is_referenced():
                        _shp['v'] = False
                    else:
                        mx.delete(_shp)

    def set_color(self, color):
        for obj in mx.ls(sl=1):
            nodes = self.get_shape_relatives(obj)

            if nodes['shape']:
                Shape.set_shape_color(nodes['shape'], color)
            elif nodes['node']:
                Shape(nodes['node']).set_color(color)

            if nodes['tpl']:
                for shp in nodes['shapes']:
                    Shape(shp).set_color(color)

    def scale_shape(self, f):
        mode = self.opt_scale()

        sel = mx.ls(sl=1, type='transform')
        for node in sel:
            nodes = self.get_shape_relatives(node)

            if nodes['ctrl']:
                s = Shape(nodes['node'])
                s.scale(f, center=mode == 'center')

            elif nodes['tpl']:
                for shp in nodes['shapes']:
                    s = Shape(shp)
                    s.scale(f, center=mode == 'center', transform=True)

            else:
                xfo = False
                if 'gem_shape_name' in nodes['node']:
                    xfo = True

                s = Shape(nodes['node'])
                s.scale(f, center=mode == 'center', transform=xfo)

        mx.cmd(mc.select, sel)

    def copy_shape_to_template(self):
        for obj in mx.ls(sl=1, type='transform'):
            nodes = self.get_shape_relatives(obj)

            if nodes['ctrl'] and nodes['tpl']:

                for node in list(nodes['tpl'].children()):
                    if Shape(node).get_shapes():
                        try:
                            mx.delete(node)
                        except:
                            node['v'] = False

                name = str(nodes['node']).split(':')[-1].split('|')[-1]
                if name.startswith('c_'):
                    name = name[2:]
                with mx.DagModifier() as md:
                    shp = md.create_node(mx.tTransform, parent=nodes['tpl'], name='shp_{}'.format(name))
                Shape(shp).copy(nodes['node'], world=True)
