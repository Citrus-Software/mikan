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

from mikan.vendor.Qt.QtCore import Qt, QSize
from mikan.vendor.Qt.QtWidgets import QAction

from mikan.core.ui.widgets import *
from .widgets import *
from .templates import TemplateManager
from .posing import PosingManager
from .deformers import DeformerManager
from .shapes import ShapesManager

log = create_logger()

# check TeamTO env
_teamto = False
try:
    from jad_pipe.core.pipe import Pipe

    if 'TT_PROD_TRIG' in os.environ:
        _teamto = True

except ImportError:
    pass

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
        menu_bar = self.menuBar()
        menu_tools = menu_bar.addMenu('&Tools')
        menu_project = menu_bar.addMenu('&Project')
        menu_help = menu_bar.addMenu('&Help')

        menu_tools.setTearOffEnabled(True)
        menu_project.setTearOffEnabled(True)

        # tools menu
        self.load_menu(MikanUI.PATH_TOOLS, menu_tools)

        # project menu
        path = MikanUI.PATH_TOOLS_PROJECT
        if path is not None and os.path.exists(path):
            self.load_menu(path, menu_project)

        # help links
        act = QAction('Mikan Online Documentation', menu_help)
        act.triggered.connect(partial(open_url, 'https://citrus-software.github.io/mikan-docs'))
        menu_help.addAction(act)

        act = QAction('Discord', menu_help)
        act.triggered.connect(partial(open_url, 'https://discord.gg/beHRwnue'))
        menu_help.addAction(act)

        # connect signals
        self.tabs.currentChanged.connect(self.tab_changed)

    def tab_changed(self, v):
        self.set_optvar('selected_main_tab', v)

    @staticmethod
    def load_menu(file_menu, parent):
        data = None
        with open(file_menu, 'r') as stream:
            try:
                data = ordered_load(stream)
            except yaml.YAMLError as exc:
                print(exc)

        if not data:
            return

        MikanUI.load_menuitems(data, parent)

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

            if not cmd:
                continue

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

            if len(cmd) == 1:
                act.triggered.connect(Callback(cmd[0]))
            else:
                act.triggered.connect(Callback(MikanUI.callback_list, cmd))

            if tooltip:
                act.setToolTip(tooltip)
            parent.addAction(act)

    # ----- menu ---------------------------------------------------------------
    sep = os.path.sep
    base_path = os.path.abspath(__file__).split(sep)

    PATH_UI = sep.join(base_path[:-1])
    PATH_TOOLS = PATH_UI + sep + 'tools.yml'

    PATH_MIKAN = sep.join(base_path[:-3])
    PATH_UTILS = PATH_MIKAN + sep + 'maya' + sep + 'utils'

    PATH_PROJECT = mc.workspace(q=1, rd=1)
    if _teamto:
        try:
            project = Pipe.getAssetManager().getProjectEntity()
            PATH_PROJECT = os.path.realpath(project['projectPath']) + sep + os.environ['TT_PROD_TRIG'] + '_maya'
        except:
            # log.warning('/!\\ cannot load TeamTO project menu from {}'.format(os.environ['TT_PROD_TRIG']))
            pass

    PATH_TOOLS_PROJECT = PATH_PROJECT + sep + 'rig' + sep + 'menu.yml'

    PATHS = {
        'mikan': PATH_MIKAN,
        'ui': PATH_UI,
        'vendor': PATH_MIKAN + sep + 'vendor',
        'utils': PATH_UTILS,
        'scripts': PATH_UTILS + sep + 'scripts',
        'snippets': PATH_UTILS + sep + 'snippets',
        'project': PATH_PROJECT,
        'rig': PATH_PROJECT + sep + 'rig'
    }

    @classmethod
    def fix_path(cls, path):
        path = os.path.relpath(path)

        for r in cls.PATHS.keys():
            re = '$' + str(r).strip()
            if re in path:
                path = path.replace(re, cls.PATHS[r])

        path = path.replace('\\', '/')

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
