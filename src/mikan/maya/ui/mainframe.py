# coding: utf-8

import yaml
import os.path
import __main__
from six import string_types
from functools import partial

import maya.cmds as mc
import maya.mel

from mikan.core.utils import ordered_load
from mikan.core.logger import create_logger, get_version
from mikan.core.prefs import Prefs, UserPrefs, find_maya_project_root

from mikan.vendor.Qt import QtWidgets
from mikan.vendor.Qt.QtCore import Qt, QSize
from mikan.vendor.Qt.QtWidgets import QAction

from mikan.maya.core import Template, Mod

from mikan.core.ui.widgets import *
from .widgets import *
from .templates import TemplateManager
from .posing import PosingManager
from .deformers import DeformerManager
from .shapes import ShapesManager

log = create_logger()

__all__ = ['MikanUI']


class MikanUI(MayaDockMixin):
    instance = None

    ICON_SIZE = QSize(16, 16)
    ICONS = {}

    version = get_version()
    TITLE = 'mikan'
    if version:
        TITLE += ' ' + version

    def __init__(self, parent=None):
        super(MikanUI, self).__init__(parent)

        MikanUI.instance = self

        self.setWindowTitle(MikanUI.TITLE)
        self.setWindowFlags(Qt.Tool)

        # refresh prefs
        Prefs.reload()
        Template.get_all_modules()
        Mod.get_all_modules()

        # tabs
        self.tabs = TabScrollWidget()
        self.setCentralWidget(self.tabs)

        self.tab_templates = TemplateManager()
        self.tab_deformers = DeformerManager()
        self.tab_posing = PosingManager()
        self.tab_shapes = ShapesManager()

        self.tabs.addTab(self.tab_templates, 'Templates')
        self.tabs.addTab(self.tab_deformers, 'Deformers')
        self.tabs.addTab(self.tab_posing, 'Posing')
        self.tabs.addTab(self.tab_shapes, 'Shapes')

        # restore selected tab
        self.tabs.setCurrentIndex(self.get_optvar('selected_main_tab', 0))

        # menus
        self.build_menu_bar()

        # connect signals
        self.tabs.currentChanged.connect(self.tab_changed)

    def tab_changed(self, v):
        self.set_optvar('selected_main_tab', v)

    def load_menu(self, name, file_menu):
        data = None

        if not os.path.isfile(file_menu):
            log.error('could not find menu file "{}"'.format(file_menu))
            return

        try:
            with open(file_menu, 'r') as stream:
                try:
                    data = ordered_load(stream)
                except yaml.YAMLError as exc:
                    print(exc)
        except (OSError, IOError) as e:
            log.error('could not read menu file "{}": {}'.format(file_menu, e))
            return

        if not data:
            return

        menu = self.menuBar().addMenu(name)
        MikanUI.load_menuitems(data, menu)
        return menu

    @staticmethod
    def load_menuitems(data, parent):

        for item in data:
            if not isinstance(item, dict):
                continue

            if 'version' in item:
                maya_version = float(mc.about(version=True))
                if maya_version < item['version']:
                    continue

            name = item.get('name', '')

            if 'menu' in item:
                if not name:
                    name = 'menu'

                submenu = parent.addMenu('   ' + name)
                submenu.setTearOffEnabled(True)
                submenu.setToolTipsVisible(True)

                if isinstance(item['menu'], str):
                    path = MikanUI.fix_path(item['menu'])

                    data = None
                    with open(path, 'r') as stream:
                        try:
                            data = ordered_load(stream)
                        except yaml.YAMLError as exc:
                            print(exc)

                    if data:
                        item['menu'] = data

                MikanUI.load_menuitems(item['menu'], submenu)
                continue

            _sep = item.get('separator', False)
            if _sep:
                sep = parent.addSeparator()
                if isinstance(_sep, str):
                    sep.setText(_sep)
                continue

            # item
            cmd = []

            if 'file' in item:
                path = MikanUI.fix_path(item['file'])
                ext = path.split('.')[-1]

                if not name:
                    name = path.split('/')[-1].split('.')[0]

                if ext == 'py':
                    cmd.append(Callback(MikanUI.se_exec_path, path))

                if ext == 'mel':
                    path = path.replace(os.path.sep, '/')
                    cmd.append(Callback(maya.mel.eval, 'source "{}";'.format(path)))

            if 'py' in item:
                cmd.append(Callback(MikanUI.se_exec_str, item['py']))

            if 'mel' in item:
                cmd.append(Callback(maya.mel.eval, item['mel']))

            if 'web' in item:
                cmd.append(partial(open_url, item['web']))

            if not cmd:
                continue

            toggle = None
            if 'toggle' in item:
                code_obj = compile(item['toggle'], '<string>', 'exec')
                local = {}
                exec(code_obj, {}, local)

                for k in local:
                    if callable(local[k]):
                        toggle = local[k]
                        break

            name = '   ' + name

            icon = None
            if 'icon' in item:
                color = item.get('color', '#999')
                if isinstance(color, string_types):
                    icon_name = item['icon']
                    if icon_name not in MikanUI.ICONS:
                        MikanUI.ICONS[icon_name] = Icon(icon_name, color=color, size=MikanUI.ICON_SIZE, tool=True)
                    icon = MikanUI.ICONS[icon_name]

            tooltip = item.get('help')

            act = QAction(name, parent)
            if icon:
                act.setIcon(icon)

            # add checkbox
            if callable(toggle):

                def refresh_toggle_state(action, toggle_func):
                    action.setCheckable(True)
                    try:
                        action.setChecked(bool(toggle_func()))
                    except Exception as e:
                        action.setCheckable(False)

                parent.aboutToShow.connect(lambda a=act, t=toggle: refresh_toggle_state(a, t))

            # connect command
            if len(cmd) == 1:
                act.triggered.connect(Callback(cmd[0]))
            else:
                act.triggered.connect(Callback(MikanUI.callback_list, cmd))

            # add tooltip
            if tooltip:
                act.setToolTip(tooltip)

            # add item
            parent.addAction(act)

    # ----- menu ---------------------------------------------------------------
    def build_menu_bar(self):
        menu_bar = self.menuBar()

        # clear
        for action in menu_bar.actions():
            menu_bar.removeAction(action)

        # get paths
        sep = os.path.sep
        base_path = os.path.abspath(__file__).split(sep)
        path_tools = sep.join(base_path[:-1]) + sep + 'tools.yml'
        path_help = sep.join(base_path[:-1]) + sep + 'help.yml'

        # get prefs
        menus = []
        menus.append(('&Tools', path_tools))
        menus += UserPrefs.get('user_menu_paths', [])
        menus.append(('&Help', path_help))

        # update ui
        for name, path in menus:
            MikanUI.PATHS = self.get_paths_dict(path)
            menu = self.load_menu(name, path)
            if menu and 'Help' not in name:
                menu.setTearOffEnabled(True)

        # env
        self.wd_env = QtWidgets.QLabel()
        self.wd_env.setStyleSheet('QLabel {font-weight: bold; color: #777;}')
        menu_bar.setCornerWidget(self.wd_env, Qt.Corner.TopRightCorner)

        self.update_project_label()

    def update_project_label(self):
        self.wd_env.setText('')
        self.wd_env.setToolTip('')

        path = Prefs.get_config_file()
        name = Prefs.get_project_name()

        if not path or not name:
            return

        self.wd_env.setText('Project: {}  '.format(name))
        self.wd_env.setToolTip('configuration file: {}'.format(path))

    @staticmethod
    def get_paths_dict(path_yml):
        sep = os.path.sep
        base_path = os.path.abspath(__file__).split(sep)

        path_mikan = sep.join(base_path[:-3])
        path_utils = path_mikan + sep + 'maya' + sep + 'utils'
        path_ui = sep.join(base_path[:-1])

        # get paths from yml
        path_menu = os.path.split(path_yml)[0]

        paths = {
            'mikan': path_mikan,
            'ui': path_ui,
            'vendor': path_mikan + sep + 'vendor',
            'utils': path_utils,
            'snippets': path_utils + sep + 'snippets',
            'rig': path_menu,  # legacy
            'menu': path_menu,
        }

        # add project path
        path_project = find_maya_project_root(path_yml)
        if path_project:
            paths['project'] = path_project

        return paths

    @classmethod
    def fix_path(cls, path):
        for r in cls.PATHS:
            re = '$' + str(r).strip()
            if re in path:
                path = path.replace(re, cls.PATHS[r])

        path = os.path.realpath(path)
        return path

    @staticmethod
    def callback_list(*args):
        if not isinstance(args[0], (list, tuple)):
            return

        for cb in args[0]:
            cb()

    @staticmethod
    def se_exec_str(code):
        exec(code, __main__.__dict__)

    @staticmethod
    def se_exec_path(path):
        with open(path, 'rb') as file:
            code = compile(file.read(), path, 'exec')
            exec(code, __main__.__dict__)
