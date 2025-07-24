# coding: utf-8

import re
import os
import ast
import math
import __main__
from six import string_types
from functools import partial
from collections import OrderedDict

import maya.mel as mel
import maya.cmds as mc
import maya.api.OpenMaya as om

from mikan.vendor.Qt import QtWidgets, QtGui
from mikan.vendor.Qt.QtCore import QTimer, QPoint
from mikan.vendor.Qt.QtCore import Qt
from mikan.vendor.Qt.QtWidgets import (
    QPushButton, QLabel, QLineEdit, QCheckBox,
    QHBoxLayout, QSlider, QComboBox, QMenu
)

from mikan.core.ui.widgets import StackWidget
from mikan.maya.ui.widgets import MayaWindow, Callback

import mikan.maya.utils.ui_auto.text_file_parser as tfp

from mikan.core.utils import flatten_list
from mikan.core.logger import create_logger
from mikan.maya.lib.rig import apply_transform
from .xml_db import path_open_in_explorer, path_open_in_vsCode

re_choice_option = re.compile('\[(.*)\]\[([0-9]?)\]')
re_range_option = re.compile('range\((.*)\)\[([0-9]?)\]')

__all__ = ['FunctionAutoUI']

r'''
from mikan.maya.utils.ui_auto.function_ui import FunctionAutoUI
#reload(mikan.maya.utils.ui_auto.function_ui)

path     = "mikan/maya/utils/transfer_to_model.py"
def_call = "transfer_to_model"

ui_gen = FunctionAutoUI(path, def_call)
ui_gen.show()
'''

log = create_logger('mikan.UI')


class FunctionAutoUI(MayaWindow):
    ui_height = 200
    ui_width = 250
    colors_loop = [
        [0.5333 * 255, 0.60 * 255, 0.6667 * 255],
        [0.9 * 255, 0.6 * 255, 0.6 * 255],
        [0.9 * 255, 0.3 * 255, 0.3 * 255],
        [0.6 * 255, 0.9 * 255, 0.6 * 255],
        [0.2 * 255, 0.9 * 255, 0.3 * 255],
        [0.9 * 255, 0.9 * 255, 0.6 * 255],
        [0.9 * 255, 0.9 * 255, 0.3 * 255],
        [0.6 * 255, 0.9 * 255, 0.9 * 255],
        [0.3 * 255, 0.9 * 255, 0.9 * 255]
    ]

    def __init__(self, path, def_name=None, parent=None, instance_name_in_maya=None, advance_setting_collapse=True):
        super(FunctionAutoUI, self).__init__()

        self.path = get_full_path(path)

        function_names = [def_name]
        if not def_name:
            function_names = [f for f in tfp.file_to_function_names(self.path) if not f.startswith('_')]

        # UI
        match = re.search(r".*/(.*)\.py", path)
        title = match.group(1)
        title = title.replace('_', ' ')
        title = title.upper()
        self.setWindowTitle(title)
        self.setWindowFlags(Qt.Tool)
        self.setStyleSheet('QPushButton {max-height: 16px;}')

        self.stack_A = StackWidget()

        self.setCentralWidget(self.stack_A)

        self.special_front = QtGui.QFont('courier new', 9)
        self.special_front.setFixedPitch(True)

        # geo tab
        self.stack_A.setStyleSheet('QLabel {font-style:monospace; font-size:12px; font-weight:bold;}')  # color:#89a

        self.advance_setting_collapse = advance_setting_collapse
        self.def_class_instance_name = 'function_inst'
        if instance_name_in_maya:
            self.def_class_instance_name = instance_name_in_maya

            # UI
        self.menu_button = None
        self.iF = 0
        self.custom_uis = []
        self.def_args_keys = []
        self.def_args_values_history = []
        self.def_args_fields = []
        self.def_args_labels = []
        self.def_args_merge = []
        self.def_args_merge_color_index = [0]
        self.return_field = None
        self.update_function_name_on_ui(function_names)

    def update_function_name_on_ui(self, function_names, i=None):

        if self.menu_button and i is not None:
            self.iF = i
        self.update_info_with_function_name(function_names[self.iF])

        self.stack_A.clear_layout(self.stack_A.layout)
        for i, _ in enumerate(self.custom_uis):
            self.stack_A.layout.removeWidget(self.custom_uis[i].widget())
            self.custom_uis[i].deleteLater()
            del self.custom_uis[i]

        self.custom_uis = []

        self.def_args_keys = []
        self.def_args_values_history = []

        for i, _ in enumerate(self.def_args_fields):
            del self.def_args_fields[i]
        self.def_args_fields = []
        del self.return_field

        for i, _ in enumerate(self.def_args_labels):
            del self.def_args_labels[i]
        self.def_args_labels = []

        self.build_stack_A(function_names)
        QTimer.singleShot(0, self.adjustSize)  # hack

    def update_info_with_function_name(self, function_name):

        def_call = tfp.file_to_def_str_line(self.path, function_name)
        self.line = tfp.file_to_def_line(self.path, function_name)
        self.def_name = tfp.str_extract_def_name(def_call)

        def_class_call = tfp.str_extract_def_class_call(self.path, function_name)
        self.def_class_name = tfp.str_extract_class_name(def_class_call)

        def_args = tfp.str_extract_def_args(self.path, function_name)
        self.def_args = def_args[0]
        self.def_key_args = def_args[1]
        self.def_key_args_doc = def_args[2]
        self.def_doc = tfp.file_to_def_doc(self.path, function_name)

        self.module = ""

        if 'self' in self.def_args:
            self.def_args.remove('self')

        # self.def_args.pop(self.def_args.index('self'))

        self.def_args_merge = OrderedDict()
        self.def_args_merge_doc = OrderedDict()
        for key in self.def_args:
            self.def_args_merge[key] = None
            self.def_args_merge_doc[key] = None
        for key, value in self.def_key_args.items():
            self.def_args_merge[key] = value
            self.def_args_merge_doc[key] = self.def_key_args_doc.get(key, None)

        self.def_args_merge_color_index = [0 for _ in self.def_args_merge]

    def dict_to_ui(self, dict_ui):

        i_offset = len(self.def_args)

        for i, arg in enumerate(list(self.def_key_args)):

            if not arg in list(dict_ui): continue

            index = i + i_offset
            value = dict_ui[arg]

            if value in ['True', 'False']:
                check = self.def_args_fields[index]
                if value == 'True':
                    check.setCheckState(Qt.Checked)
                else:
                    check.setCheckState(Qt.Unchecked)

            else:
                field = self.def_args_fields[index]
                if isinstance(value, string_types):
                    field.setText('\'{}\''.format(value))
                else:
                    field.setText('{}'.format(value))

    def build_stack_A(self, function_names):

        row = self.stack_A.add_row(spacing=10)

        btn = QLabel('{}'.format(self.path), alignment=Qt.AlignRight)
        btn.setStyleSheet('color: rgb(%s,%s,%s)' % (self.colors_loop[0][0], self.colors_loop[0][1], self.colors_loop[0][2]))
        row.addWidget(btn)

        row = self.stack_A.add_row(spacing=15)

        self.menu_button = QComboBox()
        self.menu_button.setStyleSheet('QComboBox {font-size:17px; font-weight:bold;}')
        for n in function_names:
            self.menu_button.addItem(n)
        self.menu_button.setCurrentIndex(self.iF)
        self.menu_button.activated.connect(partial(self.update_function_name_on_ui, function_names))

        row.addWidget(self.menu_button)

        grid = self.stack_A.add_grid()
        self.custom_uis.append(grid)
        grid.setSpacing(2)

        i_arg = 0

        # col = self.stack_A.add_collapse('advance setting')
        # col.collapse.set_collapsed(self.advance_setting_collapse)
        # col.collapse.toggle_cmd = Callback(self.do_size_adjustement)
        # grid = self.stack_A.add_grid(col)
        # grid.setSpacing(2)

        for i, arg in enumerate(list(self.def_args_merge)):
            default_value_raw = self.def_args_merge[arg]
            default_value = ''
            if default_value_raw:
                for letter in default_value_raw:
                    if letter != ' ':
                        default_value += letter

            if '____' in arg:

                col = self.stack_A.add_collapse('{}'.format(arg.strip('_')))
                col.collapse.button.setToolTip(self.def_args_merge_doc[arg])

                if default_value == 'False':
                    col.collapse.set_collapsed(True)
                else:
                    col.collapse.set_collapsed(False)

                col.collapse.toggle_cmd = Callback(self.do_size_adjustment)
                grid = self.stack_A.add_grid(col)

                # check = QCheckBox('', visible=0)
                # grid.addWidget(check, i , 1, stretch=6)

                self.def_args_keys.append(arg)
                self.def_args_fields.append(col)
                self.def_args_labels.append(None)

            elif default_value in ('True', 'False'):

                # label
                btn = QLabel('{} :'.format(arg))
                btn.setToolTip(self.def_args_merge_doc[arg])
                # c = self.def_args_merge_color_index[i]
                # btn.setStyleSheet('color: rgb({}, {}, {})'.format(*self.colors_loop[c]))
                btn.setFont(self.special_front)
                grid.addWidget(btn, i, 0, stretch=0)

                # field    
                check = QCheckBox('')
                if default_value == 'True':
                    check.setCheckState(Qt.Checked)
                else:
                    check.setCheckState(Qt.Unchecked)
                grid.addWidget(check, i, 1, stretch=6)

                btn.setContextMenuPolicy(Qt.CustomContextMenu)
                btn.customContextMenuRequested.connect(partial(self.text_field_generate_context_menu, i_arg))

                check.setContextMenuPolicy(Qt.CustomContextMenu)
                check.customContextMenuRequested.connect(partial(self.text_field_generate_context_menu, i_arg))

                check.clicked.connect(partial(self.update_labels, i_arg, False))

                self.def_args_keys.append(arg)
                self.def_args_fields.append(check)
                self.def_args_labels.append(btn)

            elif re_choice_option.match(default_value):

                # label
                btn = QLabel('{} :'.format(arg))
                btn.setToolTip(self.def_args_merge_doc[arg])
                # c = self.def_args_merge_color_index[i]
                # btn.setStyleSheet('color: rgb({}, {}, {})'.format(*self.colors_loop[c]))
                btn.setFont(self.special_front)
                grid.addWidget(btn, i, 0, stretch=0)

                # field 
                raw_choices, raw_default_id = re_choice_option.findall(default_value)[0]
                choices = raw_choices.split(',')
                default_id = int(raw_default_id)

                button_group = QComboBox()

                choices_tmp = []
                for choice in choices:
                    if choice[0] == "'":
                        choice = choice[1:-1]
                    choices_tmp.append(choice)

                button_group.addItems(choices_tmp)

                button_group.setCurrentIndex(default_id)
                grid.addWidget(button_group, i, 1, stretch=6)

                btn.setContextMenuPolicy(Qt.CustomContextMenu)
                btn.customContextMenuRequested.connect(partial(self.text_field_generate_context_menu, i_arg))

                button_group.setContextMenuPolicy(Qt.CustomContextMenu)
                button_group.customContextMenuRequested.connect(partial(self.text_field_generate_context_menu, i_arg))

                button_group.activated.connect(partial(self.update_labels, i_arg, False))

                self.def_args_keys.append(arg)
                self.def_args_fields.append(button_group)
                self.def_args_labels.append(btn)

            elif re_range_option.match(default_value):

                # label
                btn = QLabel('{} :'.format(arg))
                btn.setToolTip(self.def_args_merge_doc[arg])
                # c = self.def_args_merge_color_index[i]
                # btn.setStyleSheet('color: rgb({}, {}, {})'.format(*self.colors_loop[c]))
                btn.setFont(self.special_front)
                grid.addWidget(btn, i, 0, stretch=0)

                # field 
                raw_choices, raw_default_id = re_range_option.findall(default_value)[0]
                choices = raw_choices.split(',')
                choices = list(map(int, choices))
                default_id = int(raw_default_id)

                # Create a QVBoxLayout to hold the widgets
                layout = QHBoxLayout()

                # Create a QLabel to display the slider value
                slider_label = QLabel("0")

                # Create a QSlider
                slider = QSlider()
                slider.setOrientation(Qt.Horizontal)  # Set the slider orientation to horizontal
                slider.setMinimum(choices[0])
                slider.setMaximum(choices[1])
                slider.setSingleStep(1)
                if 2 < len(choices):
                    slider.setSingleStep(choices[2])

                slider.valueChanged.connect(partial(self.on_slider_value_changed, slider_label=slider_label))
                if 2 < len(choices):
                    slider.setValue(range(choices[0], choices[1], choices[2])[default_id])
                else:
                    slider.setValue(range(choices[0], choices[1])[default_id])

                slider.sliderPressed.connect(partial(self.update_labels, i_arg, False))

                # Add the QLabel and QSlider to the layout
                layout.addWidget(slider_label)
                layout.addWidget(slider)

                grid.addLayout(layout, i, 1, stretch=6)

                btn.setContextMenuPolicy(Qt.CustomContextMenu)
                btn.customContextMenuRequested.connect(partial(self.text_field_generate_context_menu, i_arg))

                slider.setContextMenuPolicy(Qt.CustomContextMenu)
                slider.customContextMenuRequested.connect(partial(self.text_field_generate_context_menu, i_arg))

                self.def_args_keys.append(arg)
                self.def_args_fields.append(slider)
                self.def_args_labels.append(btn)

            else:
                # label
                btn = QLabel('{} :'.format(arg))
                btn.setToolTip(self.def_args_merge_doc[arg])
                # c = self.def_args_merge_color_index[i]
                # btn.setStyleSheet('color: rgb({}, {}, {})'.format(*self.colors_loop[c]))
                btn.setFont(self.special_front)
                grid.addWidget(btn, i, 0, stretch=0)

                # field                 
                field = QLineEdit()
                field.setFont(self.special_front)
                field.setStyleSheet('QLineEdit {font-style:monospace; font-size:12px;text-align:left;}')
                field.setText(default_value)
                grid.addWidget(field, i, 1, stretch=6)

                btn.setContextMenuPolicy(Qt.CustomContextMenu)
                btn.customContextMenuRequested.connect(partial(self.text_field_generate_context_menu, i_arg))

                field.setContextMenuPolicy(Qt.CustomContextMenu)
                field.customContextMenuRequested.connect(partial(self.text_field_generate_context_menu, i_arg))

                field.editingFinished.connect(partial(self.update_labels, i_arg, False))

                self.def_args_keys.append(arg)
                self.def_args_fields.append(field)
                self.def_args_labels.append(btn)
            i_arg += 1

        self.def_args_values_history = [[self.def_args_merge[k]] for k in self.def_args_keys]

        grid = self.stack_A.add_grid()
        self.custom_uis.append(grid)
        grid.setSpacing(2)

        btn = QPushButton('RUN')
        btn.clicked.connect(Callback(self.def_eval))
        grid.addWidget(btn, 0, 0, stretch=6)
        btn = QPushButton('PRINT')
        btn.clicked.connect(Callback(self.def_print))
        grid.addWidget(btn, 0, 1, stretch=0)
        btn = QPushButton('OPEN')
        btn.clicked.connect(Callback(self.def_open))
        grid.addWidget(btn, 0, 2, stretch=0)

        grid = self.stack_A.add_grid()
        self.custom_uis.append(grid)
        grid.setSpacing(3)

        btn = QLabel('return :')
        btn.setFont(self.special_front)
        btn.setStyleSheet('QPushButton {font-style:monospace; font-size:12px;text-align:left;}')
        # btn.clicked.connect(Callback(self.select_args, i_arg )  )
        grid.addWidget(btn, 0, 0, stretch=0)

        self.return_field = QLineEdit('')
        self.return_field.setFont(self.special_front)
        self.return_field.setStyleSheet('QLabel {font-style:monospace; font-size:12px;text-align:left;}')
        self.return_field.setText('')
        grid.addWidget(self.return_field, 0, 1, stretch=6)

        btn.setContextMenuPolicy(Qt.CustomContextMenu)
        btn.customContextMenuRequested.connect(partial(self.text_field_generate_context_menu, -1))

        self.return_field.setContextMenuPolicy(Qt.CustomContextMenu)
        self.return_field.customContextMenuRequested.connect(partial(self.text_field_generate_context_menu, -1))

    def text_field_generate_context_menu(self, i_arg, pos):
        is_field = isinstance(self.def_args_fields[i_arg], QLineEdit)
        is_return_field = i_arg == -1

        default_value = self.def_args_merge[self.def_args_keys[i_arg]]
        arg_require_array = default_value == '[]'
        arg_require_array_of_array = default_value == '[[]]'
        arg_require_float = '.' in default_value
        arg_require_int = default_value.isdigit()
        # arg_require_str = any([arg_require_array, arg_require_array_of_array, arg_require_float, arg_require_int]) == False

        menu = None
        if is_return_field:
            menu = self.return_field.createStandardContextMenu()
            name = 'return'

            menu.clear()
            menu.addAction('')
            menu.addSection(name)
            menu.addSeparator()

            act = menu.addAction('select')
            act.triggered.connect(Callback(self.set_selection, i_arg))

            act = menu.addAction('Select next')
            act.triggered.connect(Callback(self.set_selection_next, i_arg))

            act = menu.addAction('create helper locator')
            act.triggered.connect(Callback(self.create_locator, i_arg))

            menu.popup(self.return_field.mapToGlobal(pos))

        elif is_field:
            menu = self.def_args_fields[i_arg].createStandardContextMenu()
            name = self.def_args_keys[i_arg]

            menu.clear()
            menu.addAction('')
            menu.addSection(name)
            menu.addSeparator()

            act = menu.addAction('Reset')
            act.triggered.connect(Callback(self.reset_to_default_value, i_arg))

            act = menu.addAction('Undo')
            act.triggered.connect(Callback(self.undo_value, i_arg))

            if arg_require_int:
                pass
            elif arg_require_float:
                act = menu.addAction('Get distance from selection ')
                act.triggered.connect(Callback(self.get_selected_dist, i_arg))
            else:
                menu.addSection('selection')

                act = menu.addAction('Get')
                act.triggered.connect(Callback(self.get_selected, i_arg))

                if arg_require_array or arg_require_array_of_array:
                    act = menu.addAction('Add')
                    act.triggered.connect(Callback(self.get_selected_add, i_arg))

                menu.addSection('helper')

                act = menu.addAction('Create locator')
                act.triggered.connect(Callback(self.create_locator, i_arg))

                menu.addSection('test')

                act = menu.addAction('Select text field content')
                act.triggered.connect(Callback(self.set_selection, i_arg))

                if arg_require_array or arg_require_array_of_array:
                    act = menu.addAction('Select next elem in text field content')
                    act.triggered.connect(Callback(self.set_selection_next, i_arg))

            menu.popup(self.def_args_fields[i_arg].mapToGlobal(pos))

        else:
            # Create a context menu for the slider
            menu = QMenu()
            name = self.def_args_keys[i_arg]

            menu.clear()
            menu.addAction('')
            menu.addSection(name)
            menu.addSeparator()

            act = menu.addAction('Reset')
            act.triggered.connect(Callback(self.reset_to_default_value, i_arg))

            act = menu.addAction('Undo')
            act.triggered.connect(Callback(self.undo_value, i_arg))

            menu.popup(self.def_args_fields[i_arg].mapToGlobal(pos))

            def _create_menu(event):
                if not isinstance(event, QPoint):
                    menu.exec_(event.globalPos())

            # self.def_args_fields[i_arg].setContextMenuPolicy(1)
            self.def_args_fields[i_arg].customContextMenuRequested.connect(_create_menu)

            # slider_menu.addAction(increase_action)
            # slider_menu.addAction(decrease_action)

            ## Set the context menu for the slider
            # slider.setContextMenuPolicy(3)  # 3 corresponds to Qt.CustomContextMenu
            # slider.customContextMenuRequested.connect(lambda event: menu.exec_(event.globalPos()))

    def on_slider_value_changed(self, value, slider_label):
        slider_label.setText(str(value))

    def class_eval(self):
        to_eval = []
        to_eval.append('{}'.format(self.get_str_import_module()))
        to_eval.append('{} = {}()'.format(self.def_class_instance_name, self.def_class_name))

        for e in to_eval:
            mel.eval('python(\"{}\")'.format(e))

    def def_eval(self):

        to_eval = '{};'.format(self.get_str_import_module())
        if self.def_class_name == '':
            to_eval += 'def_eval_return_value = {}'.format(self.get_str_def_call())
        else:
            to_eval += 'def_eval_return_value = {}.{}'.format(self.def_class_instance_name, self.get_str_def_call())

        exec_globals = __main__.__dict__
        exec(to_eval, exec_globals)
        return_value = exec_globals.get('def_eval_return_value', None)

        self.return_field.setText(str(return_value))

        return return_value

    def def_print(self):
        to_print = '\n########################################\n'
        to_print += '{}\n'.format(self.get_str_import_module())
        to_print += '{}\n'.format(self.get_str_def_call())
        to_print += '#######################################\n'
        log.info(to_print)
        return 0

    def def_open(self):
        log.debug('open: {}'.format(self.def_name))
        path_open_in_vsCode(self.path, line=self.line)
        return 0

    def get_selected(self, i):
        log.debug('get selection {}'.format(i))

        default_value = self.def_args_merge[self.def_args_keys[i]]
        arg_require_array = default_value == '[]'
        arg_require_array_of_array = default_value == '[[]]'
        # arg_require_float = '.' in default_value
        # arg_require_int = default_value.isdigit()

        # old_selection_raw_str = self.def_args_fields[i].text()

        user_selection = get_user_selection()

        if user_selection:
            if arg_require_array:
                self.def_args_fields[i].setText('{}'.format(user_selection))
                # self.update_labels(i,False)
            elif arg_require_array_of_array:
                self.def_args_fields[i].setText('[{}]'.format(user_selection))
                # self.update_labels(i,False)
            else:
                self.def_args_fields[i].setText(repr(user_selection[0]))
                # self.update_labels(i,False)
        else:
            if arg_require_array:
                self.def_args_fields[i].setText(str([]))
                # self.update_labels(i,False)

    def get_selected_add(self, i):
        log.debug('get selection {}'.format(i))

        default_value = self.def_args_merge[self.def_args_keys[i]]
        arg_require_array = default_value == '[]'
        arg_require_array_of_array = default_value == '[[]]'

        user_selection = get_user_selection()
        if user_selection:

            if arg_require_array:
                old_selection_raw_str = self.def_args_fields[i].text()
                elements = []
                for s in old_selection_raw_str.split("'"):
                    if s.strip() == '' or s.strip() in [']', '[', ',', '[]']:
                        continue
                    elements.append(s)
                self.def_args_fields[i].setText('{}'.format(elements + user_selection))

            elif arg_require_array_of_array:
                old_selection_raw_str = self.def_args_fields[i].text()
                elements = eval(old_selection_raw_str)
                self.def_args_fields[i].setText('{}'.format(elements + [user_selection]))

            else:
                self.def_args_fields[i].setText(repr(user_selection[0]))
        else:
            pass

    def get_selected_dist(self, i):
        log.debug('get selection {}'.format(i))

        default_value = self.def_args_merge[self.def_args_keys[i]]
        arg_require_array = default_value == '[]'

        user_selection = get_user_selection()
        if user_selection and len(user_selection == 2):
            d = get_worldspace_distance(*user_selection)
            self.def_args_fields[i].setText(str(d))
        else:
            if arg_require_array:
                self.def_args_fields[i].setText(str([]))

    def set_selection(self, i):

        log.debug('set selection {}'.format(i))

        if i == -1:
            raw_str = self.return_field.text()
        else:
            raw_str = self.def_args_fields[i].text()

        elements = eval(raw_str)
        mc.select(flatten_list(elements))

    def set_selection_next(self, i):

        log.debug('set selection next {}'.format(i))

        if i == -1:
            raw_str = self.return_field.text()
        else:
            raw_str = self.def_args_fields[i].text()

        elements = eval(raw_str)
        user_selection = get_user_selection()
        for sel_id in range(len(elements)):
            if not user_selection:
                mc.select(elements[0])
                return True
            elif user_selection[0] in elements[sel_id]:
                mc.select(elements[(sel_id + 1) % len(elements)])
                return True

        mc.select(elements[0])
        return True

    def create_locator(self, i):

        default_value = self.def_args_merge[self.def_args_keys[i]]
        arg_require_array = default_value == '[]'

        loc = mc.spaceLocator()[0]
        loc_shape = mc.listRelatives(loc, s=True)[0]
        mc.setAttr('%s.localScaleX' % loc_shape, 0.05)
        mc.setAttr('%s.localScaleY' % loc_shape, 0.05)
        mc.setAttr('%s.localScaleZ' % loc_shape, 0.05)
        mc.setAttr('%s.overrideEnabled' % loc, 1)
        mc.setAttr('%s.overrideColor' % loc, 17)
        mc.setAttr('%s.displayLocalAxis' % loc, 1)

        if i == -1:
            raw_str = self.return_field.text()
            m = om.MMatrix(list(flatten_list(eval(raw_str)))[0:16])
            apply_transform(loc, m)

        else:
            raw_str = self.def_args_fields[i].text()

            if arg_require_array:
                elements = []
                for s in raw_str.split("'"):
                    if s.strip() == '' or s.strip() in [']', '[', ',', '[]']:
                        continue
                    elements.append(s)

                elements.append(loc)

                self.def_args_fields[i].setText(str(elements))
            else:
                self.def_args_fields[i].setText(repr(loc))

    def update_labels(self, i, reset):

        if reset:
            self.def_args_merge_color_index[i] = 0
        # else:
        #     self.def_args_merge_color_index[i] += 1
        #     self.def_args_merge_color_index[i] = max(1, self.def_args_merge_color_index[i] % len(self.colors_loop))

        c = self.def_args_merge_color_index[i]
        self.def_args_labels[i].setStyleSheet('color: rgb({}, {}, {})'.format(*self.colors_loop[c]))

        key = list(self.def_args_merge)[i]

        is_field = isinstance(self.def_args_fields[i], QLineEdit)
        is_return_field = i == -1 and is_field
        if self.def_args_merge[key] is None:
            pass
        elif is_return_field:
            pass
        elif is_field:
            self.def_args_values_history[i].append(self.def_args_fields[i].text())

        elif isinstance(self.def_args_fields[i], QComboBox):
            self.def_args_values_history[i].append(self.def_args_fields[i].currentIndex())

        elif isinstance(self.def_args_fields[i], QSlider):
            self.def_args_values_history[i].append(self.def_args_fields[i].value())

        elif isinstance(self.def_args_fields[i], QCheckBox):
            self.def_args_values_history[i].append(self.def_args_fields[i].checkState())

    def undo_value(self, i):
        log.debug('undo_value', self.def_args_values_history[i])

        key = list(self.def_args_merge)[i]

        is_field = isinstance(self.def_args_fields[i], QLineEdit)
        is_return_field = i == -1 and is_field

        i_last = len(self.def_args_values_history[i]) - 2
        if self.def_args_merge[key] is None:
            pass
        elif is_return_field:
            pass
        elif is_field:
            self.def_args_fields[i].setText(self.def_args_values_history[i][i_last])
            self.def_args_values_history[i].pop()

        elif isinstance(self.def_args_fields[i], QComboBox):
            self.def_args_fields[i].setCurrentIndex(self.def_args_values_history[i][i_last])
            self.def_args_values_history[i].pop()

        elif isinstance(self.def_args_fields[i], QSlider):
            self.def_args_fields[i].setValue(self.def_args_values_history[i][i_last])
            self.def_args_values_history[i].pop()

        elif isinstance(self.def_args_fields[i], QCheckBox):
            self.def_args_fields[i].setCheckState(self.def_args_values_history[i][i_last])
            self.def_args_values_history[i].pop()

        log.debug('undo_value', self.def_args_values_history[i])

    def reset_to_default_value(self, i):

        key = list(self.def_args_merge)[i]

        is_field = isinstance(self.def_args_fields[i], QLineEdit)
        is_return_field = i == -1 and is_field

        if self.def_args_merge[key] is None:
            pass
        elif is_return_field:
            pass
        elif is_field:
            self.def_args_fields[i].setText(str(self.def_args_merge[key]))
            self.update_labels(i, reset=True)

        elif isinstance(self.def_args_fields[i], QComboBox):
            _, raw_default_id = re_choice_option.findall(self.def_args_merge[key])[0]
            default_id = int(raw_default_id)
            self.def_args_fields[i].setCurrentIndex(default_id)
            self.update_labels(i, reset=True)

        elif isinstance(self.def_args_fields[i], QSlider):
            _, raw_default_id = re_range_option.findall(self.def_args_merge[key])[0]
            default_id = int(raw_default_id)
            self.def_args_fields[i].setValue(default_id)
            self.update_labels(i, reset=True)

        elif isinstance(self.def_args_fields[i], QCheckBox):
            if self.def_args_merge[key] == 'True':
                self.def_args_fields[i].setCheckState(Qt.Checked)
            else:
                self.def_args_fields[i].setCheckState(Qt.Unchecked)
            self.update_labels(i, reset=True)

    def select_args(self, i):
        log.debug('select_args {}'.format(i))

        text = self.def_args_fields[i].text()
        value = ast.literal_eval(text)
        if isinstance(value, list) or isinstance(value, tuple):
            for v in value:
                if isinstance(value, string_types):
                    if mc.objExists(v):
                        mc.select(v, add=True)
        elif isinstance(value, string_types):
            if '/' in value or '\\' in value:
                path_open_in_explorer(value)

    def do_size_adjustment(self):
        QTimer.singleShot(1.0, self.adjustSize)  # hack
        return 0

    def mouseDoubleClickEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.adjustSize()

    def get_str_def_call(self):

        str_proc_call = ''

        str_proc_call += '{}( '.format(self.def_name)
        for i in range(0, len(self.def_args_fields)):

            if self.def_args_keys[i][0:3] == '___':
                continue

            if self.def_args_keys[i] != "":
                str_proc_call += self.def_args_keys[i] + " = "

            if isinstance(self.def_args_fields[i], QComboBox):
                str_proc_call += repr(self.def_args_fields[i].currentText())
            elif isinstance(self.def_args_fields[i], QSlider):
                str_proc_call += str(self.def_args_fields[i].value())
            elif isinstance(self.def_args_fields[i], QCheckBox):
                if self.def_args_fields[i].checkState() == Qt.Checked:
                    str_proc_call += 'True'
                else:
                    str_proc_call += 'False'
            else:
                txt = self.def_args_fields[i].text()
                if txt == "":
                    str_proc_call += '[]'
                else:
                    str_proc_call += txt

            if i < len(self.def_args_fields) - 1:
                str_proc_call += ", "

        str_proc_call += " )"

        return str_proc_call

    def get_str_import_module(self):

        first_module = 'mikan'
        extension = ".py"

        path = self.path

        if path[-len(extension):] == extension:
            path = path[:-len(extension)]

        path_split = path.split("\\")
        if len(path_split) == 1:
            path_split = path.split(r'/')

        path_split.reverse()
        self.module = ""
        for i in range(len(path_split)):
            if self.module == "":
                self.module = path_split[i]
            else:
                self.module = path_split[i] + '.' + self.module
            if path_split[i] == first_module: break

        module_import = "from " + self.module + " import " + self.def_name
        if self.def_class_name != '':
            module_import = "from " + self.module + " import " + self.def_class_name

        return module_import


def get_full_path(path):
    dir_path = os.path.dirname(os.path.realpath(__file__))

    path_split = path.split('/')
    dir_path_split = dir_path.split('\\')

    i_max = -1
    for i in range(len(dir_path_split) - 1, 0, -1):
        if path_split[0] == dir_path_split[i]:
            i_max = i
            break

    full_path = '/'.join(dir_path_split[0:i_max] + path_split)

    return full_path


def get_user_selection():
    """
    get obj in selection + selected channels in channel box
    """
    channelbox_sel_attrs = mel.eval('selectedChannelBoxAttributes')
    selection = mc.ls(sl=True)

    is_component = any(['.' in elem for elem in selection])
    all_is_edge = all(['.e[' in elem for elem in selection])
    all_is_vertex = all(['.vtx[' in elem for elem in selection])
    all_is_face = all(['.f[' in elem for elem in selection])

    if all_is_vertex: selection = mc.filterExpand(sm=31)
    if all_is_edge:   selection = mc.filterExpand(sm=32)
    if all_is_face:   selection = mc.filterExpand(sm=34)

    if channelbox_sel_attrs and not is_component:
        selection_attrs = []
        for elem in selection:
            for attr in channelbox_sel_attrs:
                selection_attrs.append('{}.{}'.format(elem, attr))
        selection = selection_attrs

    return selection


def get_worldspace_distance(obj1, obj2):
    if not mc.objExists(obj1) or not mc.objExists(obj2):
        raise ValueError("One or both objects do not exist.")

    pos1 = mc.xform(obj1, q=True, ws=True, t=True)
    pos2 = mc.xform(obj2, q=True, ws=True, t=True)

    distance = math.sqrt(sum((a - b) ** 2 for a, b in zip(pos1, pos2)))
    return distance
