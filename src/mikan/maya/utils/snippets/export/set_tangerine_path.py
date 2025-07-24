# coding: utf-8

from mikan.core.prefs import UserPrefs
from PySide2 import QtWidgets, QtCore

from mikan.maya.ui.widgets import MayaWindow


class ExePathSelector(MayaWindow):

    def __init__(self, parent=None):
        MayaWindow.__init__(self, parent)

        self.setWindowTitle("🍊 Tangerine Executable  ")
        self.setMinimumWidth(450)
        self.setMaximumHeight(32)
        self.setWindowFlags(self.windowFlags() ^ QtCore.Qt.WindowContextHelpButtonHint)
        self.build_ui()
        self.populate()

    def build_ui(self):
        main_layout = QtWidgets.QVBoxLayout(self)

        form_layout = QtWidgets.QHBoxLayout()
        label = QtWidgets.QLabel("Path:")
        self.line_edit = QtWidgets.QLineEdit()
        browse_btn = QtWidgets.QPushButton("...")

        browse_btn.setFixedWidth(30)
        browse_btn.clicked.connect(self.browse_exe)

        form_layout.addWidget(label)
        form_layout.addWidget(self.line_edit)
        form_layout.addWidget(browse_btn)

        main_layout.addLayout(form_layout)

        self.line_edit.editingFinished.connect(self.save_path)

        container = QtWidgets.QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)

    def populate(self):
        path = UserPrefs.get('tangerine_path')
        if path:
            self.line_edit.setText(path)

    def browse_exe(self):
        file_dialog = QtWidgets.QFileDialog(self)
        file_dialog.setWindowTitle("Find Tangerine.exe")
        file_dialog.setFileMode(QtWidgets.QFileDialog.ExistingFile)
        file_dialog.setNameFilters(["Tangerine.exe", "*.exe"])
        if file_dialog.exec_():
            selected_files = file_dialog.selectedFiles()
            if selected_files:
                file_path = selected_files[0]
                self.line_edit.setText(file_path)
                self.save_path()

    def save_path(self):
        path = self.line_edit.text()
        UserPrefs.set('tangerine_path', path)


_win = ExePathSelector()
_win.show()
