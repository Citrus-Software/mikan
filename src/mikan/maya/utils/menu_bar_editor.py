# coding: utf-8

import os

import maya.cmds as mc

from mikan.core.prefs import UserPrefs
from mikan.core.logger import create_logger
from mikan.core.ui.widgets import Icon
from mikan.maya.ui.widgets import MayaWindow
from mikan.maya.ui.mainframe import MikanUI

from mikan.vendor.Qt import QtWidgets
from mikan.vendor.Qt.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLineEdit, QFileDialog, QScrollArea
)

log = create_logger('mikan.ui')


class MenuBarEditorUI(MayaWindow):
    PREF = 'user_menu_paths'

    ICON_TRASH = Icon('trash', color='#aaa')
    ICON_ADD = Icon('cross', color='#aaa')
    ICON_RELOAD = Icon('reload', color='#aaa')

    def __init__(self, parent=None):
        MayaWindow.__init__(self, parent)
        self.setWindowTitle("Menu Bar Editor")
        self.resize(512, 128)

        self.entries = {}

        main_layout = QVBoxLayout(self)
        main_layout.setMargin(2)
        main_layout.setSpacing(2)

        self.entry_container = QVBoxLayout()
        self.entry_container.setSpacing(2)
        self.entry_container.setMargin(0)

        scroll = QScrollArea()
        scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
        scroll.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)

        scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        scroll_content.setLayout(self.entry_container)

        scroll_content.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Maximum)
        scroll_content.adjustSize()

        scroll.setWidget(scroll_content)
        main_layout.addWidget(scroll)

        button_layout = QHBoxLayout()

        btn_add = QPushButton(" Add entry")
        btn_add.setIcon(self.ICON_ADD)
        btn_add.clicked.connect(self.add_entry)
        button_layout.addWidget(btn_add)

        btn_project = QPushButton("Get current project menu")
        btn_project.clicked.connect(self.detect_project_menu)
        button_layout.addWidget(btn_project)

        btn_rebuild = QPushButton(" Rebuild Menu Bar")
        btn_rebuild.setIcon(self.ICON_RELOAD)
        btn_rebuild.clicked.connect(self.rebuild_menubar)
        button_layout.addWidget(btn_rebuild)

        uniform_height = 24
        for w in (btn_add, btn_project, btn_rebuild):
            w.setFixedHeight(uniform_height)

        main_layout.addLayout(button_layout)

        container = QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)

        # get prefs
        self.prefs = UserPrefs.get(self.PREF, [])
        self.reload()

    def clear(self):
        while self.entry_container.count():
            item = self.entry_container.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()

        self.entries.clear()

    def reload(self):
        self.clear()

        for name, path in self.prefs:
            self.add_entry(name, path)
        self.add_entry('', '')

    def add_entry(self, name="", path=""):
        layout = QHBoxLayout()
        edit_name = QLineEdit(name)
        edit_path = QLineEdit(path)
        btn_browse = QPushButton("...")
        btn_delete = QPushButton()
        btn_delete.setIcon(self.ICON_TRASH)

        edit_name.setPlaceholderText('Menu')
        edit_path.setPlaceholderText('Path')

        layout.addWidget(edit_name, 4)
        layout.addWidget(edit_path, 8)
        layout.addWidget(btn_browse, 1)
        layout.addWidget(btn_delete, 1)

        layout.setSpacing(2)
        layout.setMargin(0)

        uniform_height = 24
        for w in (edit_name, edit_path, btn_delete, btn_browse):
            w.setFixedHeight(uniform_height)

        container = QWidget()
        container.setLayout(layout)
        self.entry_container.addWidget(container)

        edit_name.textChanged.connect(self.on_change)
        edit_path.textChanged.connect(self.on_change)

        btn_browse.clicked.connect(lambda: self.browse_file(edit_path))
        btn_delete.clicked.connect(lambda: self.remove_entry(container))

        self.entries[container] = (edit_name, edit_path)

    def browse_file(self, edit_path):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select a YML menu configuration file", "", "YAML Files (*.yml *.yaml)")
        if file_path:
            edit_path.setText(file_path)

    def remove_entry(self, container):
        self.entry_container.removeWidget(container)
        container.setParent(None)
        self.entries.pop(container, None)

        self.on_change()

    def update_prefs(self):
        del self.prefs[:]
        for edit_name, edit_path in self.entries.values():
            name = edit_name.text().strip()
            path = edit_path.text().strip()
            if name and path:
                self.prefs.append((name, path))

    def on_change(self):
        self.update_prefs()
        UserPrefs.set(self.PREF, self.prefs)

    def detect_project_menu(self):
        sep = os.path.sep

        # get project path
        path_project = mc.workspace(q=1, rd=1)
        name = path_project.split(sep)[-1]

        # check TeamTO env
        try:
            from jad_pipe.core.pipe import Pipe
            project = Pipe.getAssetManager().getProjectEntity()
            path_project = os.path.realpath(project['projectPath']) + sep + project['trigram'] + '_maya'
            name = project['trigram'].upper()
        except Exception:
            pass

        # get menu
        path_menu = path_project + sep + 'rig' + sep + 'menu.yml'

        if not os.path.exists(path_menu):
            log.warning("No menu.yml found at: {}".format(path_menu))
            return

        menu_key = 'Project ({})'.format(name)
        self.prefs.append((menu_key, path_menu))
        UserPrefs.set(self.PREF, self.prefs)

        self.reload()

    def rebuild_menubar(self):
        MikanUI.instance.build_menu_bar()
