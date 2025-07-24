# coding: utf-8

import traceback
import webbrowser
from functools import partial
from six.moves import range
from six import string_types

from mikan.vendor.Qt import QtCore, QtWidgets, QtCompat
from mikan.vendor.Qt.QtCore import Qt
from mikan.vendor.Qt.QtGui import QSyntaxHighlighter
from mikan.vendor.Qt.QtWidgets import QMainWindow, QDockWidget, QVBoxLayout, QWidget, QDialog, QTextEdit
from mikan.core.ui.widgets import SafeWidget, SyntaxHighlighter

import maya.cmds as mc
from maya.OpenMayaUI import MQtUtil
from maya.app.general.mayaMixin import MayaQWidgetDockableMixin, MayaQDockWidget

from mikan.core.logger import create_logger

__all__ = [
    'MayaWindow', 'MayaDockMixin', 'MayaDockWidget', 'OptVarSettings',
    'SafeUndoInfo', 'safe_undo_info',
    'Callback', 'UndoChunk', 'undo_chunk',
    'open_url', 'install_maya_syntax_highlighter'
]

log = create_logger(name='mikan.UI')
MayaQDockWidget.setAllowedArea = MayaQDockWidget.setAllowedAreas  # maya2015 typo

try:
    long
except NameError:
    # Python 3 compatibility
    long = int


def get_maya_window():
    main_window_ptr = MQtUtil.mainWindow()
    return QtCompat.wrapInstance(long(main_window_ptr), QMainWindow)


def delete_QWidget(name):
    maya_ui = MQtUtil.findControl(name)
    if maya_ui:
        ptr = QtCompat.wrapInstance(long(maya_ui), QWidget)
        QtCompat.delete(ptr)


def find_widget(widget_name):
    for widget in QtWidgets.QApplication.allWidgets():
        if widget.objectName() == widget_name:
            return widget
    return None


class UndoChunk(object):

    def __init__(self, name=None):
        self.name = name

    def __enter__(self):
        mc.undoInfo(openChunk=True, chunkName=self.name)
        return

    def __exit__(self, exec_type, exec_val, traceback):
        mc.undoInfo(closeChunk=True)


def undo_chunk(func):
    def wrapped(*args, **kw):
        with UndoChunk(name=func.__name__):
            func(*args, **kw)

    return wrapped


class Callback(object):
    """
    Enables deferred function evaluation with 'baked' arguments.
    Useful where lambdas won't work...

    It also ensures that the entire callback will be be represented by one
    undo entry.
    """

    def __init__(self, func, *args, **kwargs):
        self.func = func
        self.args = args
        self.kwargs = kwargs

    def __call__(self, *args):
        with UndoChunk(name='Callback: {}'.format(self.func)):
            try:
                return self.func(*self.args, **self.kwargs)
            except:
                msg = traceback.format_exc().strip('\n')

                lines = msg.split('\n')
                lines.insert(0, lines[-1])
                for i in range(1, len(lines)):
                    lines[i] = '# ' + lines[i]
                msg = '\n'.join(lines[:-1])

                log.error(msg)


class EventFilter(QtCore.QObject):
    closed = QtCore.Signal()
    moved = QtCore.Signal()

    def eventFilter(self, obj, event):
        et = event.type()
        if et == QtCore.QEvent.Close:
            self.closed.emit()
        elif et == QtCore.QEvent.Move:
            self.moved.emit()

        return False


class OptVarSettings(object):

    def __init__(self, *args, **kw):
        pass

    def optvar_id(self):
        opt = self.__class__.__name__
        try:
            opt = self.objectName() or opt
        except:
            pass
        return opt

    def get_optvar(self, name, default=None):
        opt_var = '{object}::{name}'.format(object=self.optvar_id(), name=name)
        opt_vars = list(filter(partial(lambda x: x.startswith(opt_var)), mc.optionVar(list=1)))

        if opt_vars:
            opt_var = opt_vars[0]
            if mc.optionVar(exists=opt_var):
                v = mc.optionVar(q=opt_var)
                if opt_var.endswith('.bool'):
                    return bool(v)
                elif opt_var.endswith('.point'):
                    return QtCore.QPoint(*v)
                elif opt_var.endswith('.geo'):
                    return QtCore.QRect(*v)
                elif opt_var.endswith('.area'):
                    return getattr(Qt, v)
                return v
        return default

    def set_optvar(self, name, v):
        opt_var = '{object}::{name}'.format(object=self.optvar_id(), name=name) + '{}'

        if isinstance(v, bool):
            mc.optionVar(intValue=(opt_var.format('.bool'), int(v)))
        elif isinstance(v, int):
            mc.optionVar(intValue=(opt_var.format(''), v))
        elif isinstance(v, float):
            mc.optionVar(floatValue=(opt_var.format(''), v))
        elif isinstance(v, string_types):
            mc.optionVar(stringValue=(opt_var.format(''), str(v)))

        elif isinstance(v, Qt.DockWidgetArea):
            mc.optionVar(stringValue=(opt_var.format('.area'), v.name))

        elif isinstance(v, QtCore.QPoint):
            opt_var = opt_var.format('.point')
            if mc.optionVar(exists=opt_var):
                mc.optionVar(remove=opt_var)
            mc.optionVar(intValueAppend=[
                (opt_var, v.x()),
                (opt_var, v.y())
            ])

        elif isinstance(v, QtCore.QRect):
            opt_var = opt_var.format('.geo')
            if mc.optionVar(exists=opt_var):
                mc.optionVar(remove=opt_var)
            mc.optionVar(intValueAppend=[
                (opt_var, v.x()),
                (opt_var, v.y()),
                (opt_var, v.width()),
                (opt_var, v.height())
            ])


class MayaWindow(QMainWindow, OptVarSettings, SafeWidget):

    def __init__(self, parent=None, **kw):
        delete_QWidget(self.__class__.__name__)

        parent = parent or get_maya_window()
        QMainWindow.__init__(self, parent)

        self.setWindowFlags(Qt.Tool)
        self.setObjectName(self.__class__.__name__)
        self.setAttribute(Qt.WA_DeleteOnClose, True)
        self.safe_position()

    def resizeEvent(self, e):
        self.set_optvar('geometry', self.geometry())
        return QMainWindow.resizeEvent(self, e)

    def closeEvent(self, e):
        self.set_optvar('geometry', self.geometry())
        return QMainWindow.closeEvent(self, e)

    def restore_geometry(self):
        geo = self.get_optvar('geometry')
        if geo is not None:
            self.setGeometry(geo)


class MayaDialog(QDialog, OptVarSettings, SafeWidget):

    def __init__(self, parent=None, *args, **kw):
        delete_QWidget(self.__class__.__name__)

        parent = parent or get_maya_window()
        QDialog.__init__(self, parent=parent, *args, **kw)

        self.setWindowFlags(Qt.Tool)
        self.setObjectName(self.__class__.__name__)
        self.setAttribute(Qt.WA_DeleteOnClose, True)
        self.safe_position()

    def resizeEvent(self, e):
        self.set_optvar('geometry', self.geometry())
        return QDialog.resizeEvent(self, e)

    def closeEvent(self, e):
        self.set_optvar('geometry', self.geometry())
        return QDialog.closeEvent(self, e)


class MayaDockMixin(MayaQWidgetDockableMixin, QMainWindow, OptVarSettings):

    def __init__(self, parent=None, *args, **kw):
        self.delete_instances()
        self._save_geometry = False

        parent = parent or get_maya_window()
        super(MayaDockMixin, self).__init__(parent=parent, *args, **kw)

        self.setWindowFlags(Qt.Tool)
        self.setObjectName(self.__class__.__name__)
        self.setAttribute(Qt.WA_DeleteOnClose, True)

    @property
    def workspace_name(self):
        return self.__class__.__name__ + 'WorkspaceControl'

    def delete_instances(self):
        for obj in get_maya_window().children():
            if '.mayaMixin' in str(type(obj)):
                if obj.widget().__class__.__name__ == self.__class__.__name__:
                    obj.setParent(None)
                    obj.deleteLater()

        try:
            delete_QWidget(self.__class__.__name__)
        except:
            pass

        workspace_name = self.workspace_name
        if mc.workspaceControl(workspace_name, q=True, exists=True):
            mc.workspaceControl(workspace_name, e=True, close=True)
            mc.deleteUI(workspace_name, control=True)

    def save_floating(self):
        workspace_name = self.workspace_name
        floating = bool(mc.workspaceControl(workspace_name, q=1, fl=1))
        self.set_optvar('floating', floating)
        return floating

    def save_geometry(self):
        floating = self.save_floating()
        if self._save_geometry and floating:
            self.set_optvar('geometry', self.parent().geometry())
            self.set_optvar('position', self.parent().mapToGlobal(QtCore.QPoint(0, 0)))

    def floatingChanged(self, floating):
        if isinstance(floating, string_types):
            floating = int(floating)
        floating = bool(floating)

        if floating:
            self.parent().setGeometry(self.get_optvar('geometry', self.parent().geometry()))

        if self._save_geometry:
            self.set_optvar('floating', floating)
            self.set_optvar('area', self.dockArea())

    def __del__(self):
        pass

    def run(self):

        # show
        area = self.get_optvar('area', 'right')
        floating = self.get_optvar('floating', False)
        pos = self.get_optvar('position', QtCore.QPoint(128, 128))
        geo = self.get_optvar('geometry', QtCore.QRect(0, 0, 400, 800))

        workspace_name = self.workspace_name
        mc.workspaceControlState(
            workspace_name,
            topLeftCorner=[pos.y(), pos.x()],
            widthHeight=[geo.width(), geo.height()]
        )

        kw = {'dockable': True, 'area': area, 'allowedArea': 'left|right'}
        kw['floating'] = floating
        self.show(**kw)

        # workspace control
        kw = {'retain': False}
        kw['floating'] = floating
        if not floating:
            kw['tabToControl'] = ('ChannelBoxLayerEditor', -1)

        kw['label'] = self.windowTitle()

        mc.workspaceControl(workspace_name, e=True, **kw)

        # exec dock
        self.parent().setMinimumWidth(256)
        self.setSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Preferred)

        self.raise_()

        # hack events
        self.filter = EventFilter()
        self.parent().installEventFilter(self.filter)

        self.filter.moved.connect(self.save_geometry)
        self.filter.closed.connect(self.save_geometry)
        self.filter.closed.connect(self.delete_instances)

        self._save_geometry = True

    @classmethod
    def start(cls):
        ui = cls()
        ui.run()
        return ui


class MayaDockWidget(QDockWidget, OptVarSettings):

    def __init__(self, parent=None, **kw):
        parent = parent or get_maya_window()
        QDockWidget.__init__(self, parent)

        self.setObjectName(self.__class__.__name__)
        self._save_geometry = False

        allowedAreas = kw.get('allowedAreas', Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        layout = kw.get('layout', QVBoxLayout)

        area = kw.get('area', None)
        floating = kw.get('floating', None)

        self._window_flag = Qt.Window
        if kw.get('toolbox', False):
            self._window_flag = Qt.Tool

        if area:
            self.set_optvar('area', area)
        if floating:
            self.set_optvar('floating', floating)

        self.setAllowedAreas(allowedAreas)

        self.dockWidgetContents = QWidget()
        self.layout = layout(self.dockWidgetContents)
        self.setWidget(self.dockWidgetContents)
        self.setContentsMargins(0, 0, 0, 0)
        self.layout.setContentsMargins(0, 0, 0, 0)

        self._widgets = []

        # connections
        self.topLevelChanged.connect(self._on_floating_changed)
        self.topLevelChanged.connect(partial(self.set_optvar, 'floating'))
        self.dockLocationChanged.connect(partial(self.set_optvar, 'area'))

        # restore UI
        self.load_optvars()

    def setFloating(self, floating):
        v = QDockWidget.setFloating(self, floating)
        self._on_floating_changed(floating)
        return v

    def resizeEvent(self, e):
        if self._save_geometry:
            self.set_optvar('geometry', self.geometry())
        return QDockWidget.resizeEvent(self, e)

    def _on_floating_changed(self, floating):
        vis = self.isVisible()

        if floating:
            self.setWindowFlags(self._window_flag)

            pos = self.pos()
            if pos.x() < 0:
                pos.setX(0)
            if pos.y() < 0:
                pos.setY(0)
            self.move(pos)
            self.setVisible(vis)
            if self._widgets:
                self.setWindowIcon(self._widgets[0].windowIcon())

        else:
            self.setWindowFlags(Qt.Widget)
            self.setVisible(vis)

    def widgets(self):
        return self._widgets

    def load_optvars(self):
        area = self.get_optvar('area', Qt.LeftDockWidgetArea)
        parent = self.parent()
        if not isinstance(parent, QMainWindow):
            return
        for ch in parent.findChildren(QDockWidget):
            if not ch.isFloating():
                if parent.dockWidgetArea(ch) == area:
                    parent.addDockWidget(area, self)
                    parent.tabifyDockWidget(ch, self)
                    break
        else:
            parent.addDockWidget(area, self)

        self.setGeometry(self.get_optvar('geometry', self.geometry()))
        self.setFloating(self.get_optvar('floating', True))

    def addWidget(self, widget):
        if widget in self._widgets:
            return

        self.layout.addWidget(widget)
        if not self._widgets:
            self.setWindowTitle(widget.windowTitle())
            self.setWindowIcon(widget.windowIcon())
        self._widgets.append(widget)
        if self.objectName() == self.__class__.__name__:
            self.setObjectName(self._widgets[0].__class__.__name__)
            self.load_optvars()
        self._save_geometry = True


def open_url(url):
    if 'ovm.io/' in url:
        url += '?fullscreen=true'
    webbrowser.open(url)


def find_script_editor_widget():
    for i in range(100):
        ptr = MQtUtil.findControl('cmdScrollFieldReporter{}'.format(i))
        if ptr is not None:
            return QtCompat.wrapInstance(long(ptr), QTextEdit)


def install_maya_syntax_highlighter():
    script_editor = find_script_editor_widget()
    if not script_editor:
        return

    w = script_editor.findChild(QSyntaxHighlighter)
    if w:
        # w.deleteLater()
        if w.objectName() == SyntaxHighlighter.__name__:
            return w
        else:
            w.deleteLater()

    # add new syntax highlighter
    syntax = SyntaxHighlighter(script_editor.document())
    syntax.add_styles([
        ('comment', (136, 136, 136), {'italic': True}),

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
    syntax.add_rules([
        (r'^(#|\/\/)(?!.+(DEBUG|INFO|SUCCESS|WARNING|ERROR|CRITICAL)).+$', 0, 'comment'),

        (r'^(#|\/\/).*(DEBUG).+', 0, 'debug'),
        # (r'^(#|\/\/).*(INFO).+', 0, 'info'),
        # (r'^(#|\/\/).*(SUCCESS).+', 0, 'success'),
        (r'^(#|\/\/).*(WARNING|Warning).+', 0, 'warning'),
        (r'^(#|\/\/).*(ERROR|Error).+', 0, 'error'),
        (r'^(#|\/\/).*(CRITICAL).+', 0, 'critical'),

        # (r'^(#|\/\/).*(DEBUG)\b', 0, 'debug'),
        (r'^(#|\/\/).*(INFO)\b', 0, 'info'),
        (r'^(#|\/\/).*(SUCCESS)\b', 0, 'success'),
        (r'^(#|\/\/).*(WARNING|Warning)\b', 0, 'warning+'),
        (r'^(#|\/\/).*(ERROR|Error)\b', 0, 'error+'),
        (r'^(#|\/\/).*(CRITICAL)\b', 0, 'critical+'),
    ])

    syntax.setObjectName(SyntaxHighlighter.__name__)
    syntax.rehighlight()
    return syntax


class SafeUndoInfo(object):

    def __enter__(self):
        mc.flushUndo()
        self.undo_info = mc.undoInfo(query=True, state=True)
        mc.undoInfo(state=False)

    def __exit__(self, type_, value, traceback):
        mc.undoInfo(state=self.undo_info)


def safe_undo_info(func):
    def wrapped(*args, **kw):
        with SafeUndoInfo():
            func(*args, **kw)

    return wrapped
