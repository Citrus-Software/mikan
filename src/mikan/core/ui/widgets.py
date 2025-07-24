# coding: utf-8

import time
import yaml
import os.path
import traceback
from functools import partial
from six import string_types

from mikan.vendor.Qt import QtCore, QtWidgets, QtGui
from mikan.vendor.Qt.QtGui import (
    QFont, QPainter, QColor, QImage, QIcon, QPixmap, QPalette,
    QSyntaxHighlighter, QTextCharFormat
)
from mikan.vendor.Qt.QtCore import Qt, Signal, QSize
from mikan.vendor.Qt.QtWidgets import (
    QWidget, QTabWidget, QGridLayout, QVBoxLayout, QHBoxLayout, QLabel,
    QComboBox, QCheckBox, QGroupBox, QScrollArea, QFrame, QSpinBox, QLineEdit,
    QDoubleSpinBox, QAction, QToolButton, QSizePolicy
)

from mikan.vendor.unidecode import unidecode
from mikan.core.utils.typeutils import filter_str
from mikan.core.utils.yamlutils import YamlLoader

__all__ = [
    'SafeWidget',
    'StackWidget', 'TabScrollWidget', 'OptionGridLayout', 'CollapseWidget',
    'AbstractValueWidget', 'AbstractPlugConnect',
    'BoolPlugWidget', 'IntPlugWidget', 'StringPlugWidget', 'StringListPlugWidget',
    'FloatPlugWidget', 'VectorPlugWidget', 'VectorIntPlugWidget',
    'Icon',
    'BusyCursor', 'busy_cursor',
    'ThreadPool', 'Worker',
    'SyntaxHighlighter',
    'get_composition_mode', 'get_palette_role'
]


class SafeWidget(QWidget):

    def safe_position(self):
        app = QtWidgets.QApplication.instance()
        res = app.desktop().screenGeometry()
        w, h = res.width(), res.height()

        pos = self.mapToGlobal(self.pos())
        x, y = pos.x(), pos.y()

        if x < 32 or y < 32 or x > w or y > h:
            self.move(64, 64)


class StackWidget(QWidget):

    def __init__(self, parent=None):
        QWidget.__init__(self, parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)

    def add_widget(self, widget, parent=None, stretch=0):
        if parent is None:
            parent = self.layout

        parent.addWidget(widget, stretch)

    def add_collapse(self, title, parent=None, stretch=0):
        if parent is None:
            parent = self.layout

        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        collapse = CollapseWidget(widget)
        collapse.set_title(title)

        parent.addWidget(collapse, stretch=stretch)

        layout.collapse = collapse

        return layout

    def add_box(self, title, parent=None):
        if parent is None:
            parent = self.layout

        box = QGroupBox(title)
        parent.addWidget(box)

        layout = QVBoxLayout(box)
        layout.setContentsMargins(2, 2, 2, 0)
        layout.setSpacing(0)
        return layout

    def add_grid(self, parent=None):
        if parent is None:
            parent = self.layout
        grid = QWidget()
        parent.addWidget(grid)

        layout = OptionGridLayout(grid)

        layout.setContentsMargins(2, 2, 2, 2)
        layout.setHorizontalSpacing(5)
        layout.setVerticalSpacing(2)

        return layout

    def add_row(self, parent=None, margins=2, spacing=5, height=None):
        if parent is None:
            parent = self.layout
        row = QWidget()
        parent.addWidget(row)

        if isinstance(margins, int):
            margins = (margins, margins, margins, 0)

        if height is not None:
            row.setFixedHeight(height)
            row.setStyleSheet('*{{height: {}}}'.format(height))

        layout = QHBoxLayout(row)
        layout.setContentsMargins(*margins)
        layout.setSpacing(spacing)
        return layout

    def add_column(self, parent=None, margins=2, spacing=5, stretch=None):
        if parent is None:
            parent = self.layout
        row = QWidget()
        if stretch is not None:
            parent.addWidget(row, stretch)
        else:
            parent.addWidget(row)

        layout = QVBoxLayout(row)
        layout.setContentsMargins(margins, margins, margins, 0)
        layout.setSpacing(spacing)
        return layout

    def add_columns(self, parent=None, margins=2, spacing=2, numbers=2, stretch=0):
        if parent is None:
            parent = self.layout

        row = QWidget()
        parent.addWidget(row)

        layout = QHBoxLayout(row)
        layout.setContentsMargins(margins, margins, margins, margins)
        layout.setSpacing(spacing)

        columns = []
        for i in range(numbers):
            col = QWidget()
            col_layout = QVBoxLayout(col)
            col_layout.setContentsMargins(0, 0, 0, 0)
            col_layout.setSpacing(spacing)

            s = stretch
            if isinstance(stretch, (list, tuple)) and i < len(stretch):
                s = stretch[i] or 0
            layout.addWidget(col, s)

            columns.append(col_layout)

        return columns

    def add_line(self, parent=None, label=None):
        if parent is None:
            parent = self.layout

        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        line.setStyleSheet('QFrame {color: #333;}')
        line.setObjectName('separator')

        if label:
            widget = QWidget()
            layout = QHBoxLayout(widget)
            layout.setContentsMargins(8, 4, 0, 0)

            label = QLabel(str(label))
            layout.addWidget(label)
            layout.addWidget(line, stretch=1, alignment=Qt.AlignBottom)

            parent.addWidget(widget)
            return widget

        else:
            line.setMinimumHeight(8)
            parent.addWidget(line)
            return line

    def clear_layout(self, layout):
        if layout is not None:
            while layout.count():
                item = layout.takeAt(0)
                widget = item.widget()
                if widget is not None:
                    widget.deleteLater()
                else:
                    self.clear_layout(item.layout())


class TabScrollWidget(QTabWidget):

    def __init__(self, parent=None):
        QTabWidget.__init__(self, parent)

    _addTab = QTabWidget.addTab

    def addTab(self, widget, name):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(widget)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self._addTab(scroll, name)


class OptionGridLayout(QGridLayout):

    def __init__(self, parent=None):
        QGridLayout.__init__(self, parent)

    _addWidget = QGridLayout.addWidget

    def addWidget(self, *args, **kw):
        row, col = 1, 1
        if len(args) > 1:
            row = args[1]
            col = args[2]

        stretch = kw.pop('stretch', None)
        align = kw.pop('align', None)
        if isinstance(align, str):
            align = {
                'center': Qt.AlignCenter,
                'left': Qt.AlignLeft,
                'right': Qt.AlignRight
            }.get(align, Qt.AlignLeft)

        self._addWidget(*args, **kw)

        if align is not None:
            self.itemAtPosition(row, col).setAlignment(align)
        if stretch is not None:
            self.setColumnStretch(col, stretch)


class CollapseWidget(QWidget):
    collapse_state_changed = QtCore.Signal(bool)

    def __init__(self, widget, parent=None):
        QWidget.__init__(self, parent)

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 2)
        self.layout.setSpacing(0)

        self.button = QToolButton()
        self.button.setFixedHeight(20)
        self.button.setSizePolicy(QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred))
        self.button.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.button.setArrowType(Qt.DownArrow)
        self.button.setStyleSheet('QToolButton {font-weight:bold; border:none; background-color:#555}')

        self.widget = widget
        self.layout.addWidget(self.button)
        self.layout.addWidget(self.widget)

        self._visible = True
        self.button.clicked.connect(self._toggle_collapse)

        self.toggle_cmd = None

    def set_title(self, text):
        self.button.setText(text)

    def set_collapsed(self, value):
        if self._visible != value:
            self._toggle_collapse()

    def set_expanded(self, value):
        self.set_collapsed(not value)

    def collapse(self):
        self.set_collapsed(True)

    def expand(self):
        self.set_collapsed(False)

    def is_collapsed(self):
        return not self._visible

    def _toggle_collapse(self):
        self._visible = not self._visible
        self.widget.setVisible(self._visible)

        arrow_type = Qt.RightArrow if not self._visible else Qt.DownArrow
        self.button.setArrowType(arrow_type)

        self.collapse_state_changed.emit(self._visible)
        self._exec_toggle_cmd()

    def _exec_toggle_cmd(self):
        if callable(self.toggle_cmd):
            self.toggle_cmd()


# ------controls -------------------------------------------------------------------------------------------------------

class AbstractValueWidget(QWidget):
    value_changed = Signal()
    reset_activated = Signal()
    altered = Signal()

    color_changed = 'color: #5bf;'
    color_mixed = 'color: #28c;'
    color_altered = 'color: #789;'

    def __init__(self, *args, **kw):
        parent = kw.get('parent')
        QWidget.__init__(self, parent)

        self.label = kw.get('label', '')
        self.min_value = kw.get('min_value')
        self.max_value = kw.get('max_value')
        self.presets = []
        if isinstance(kw.get('presets'), list):
            self.presets = kw.get('presets')

        self.build_layout()
        self.build_widget()
        self.setMinimumHeight(20)

        self.value = None
        self.default = kw.get('default')
        if self.default is not None:
            self.set_default(self.default)
        self.set_value(kw.get('value', self.default))
        self.connectors = []

        self.layout.addWidget(self.widget, 3)

        self.setContextMenuPolicy(Qt.ActionsContextMenu)
        self.widget.setContextMenuPolicy(Qt.ActionsContextMenu)
        self.build_menu_actions()

        self.value_changed.connect(self.set_altered)

    def build_layout(self):
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(5)

        self.label_widget = QLabel(self.label)
        self.layout.addWidget(self.label_widget, 2, Qt.AlignRight)

    def build_widget(self):
        self.widget = QWidget()

    def build_menu_actions(self):
        if self.default is not None:
            delete = QAction(self)
            delete.setText('Reset')
            delete.triggered.connect(self.reset)
            self.addAction(delete)
            self.widget.addAction(delete)

        if self.presets:
            for preset in self.presets:
                act = QAction(self)
                act.setText('Preset: ' + str(preset))
                act.triggered.connect(partial(self.widget.setText, preset))
                self.addAction(act)
                self.widget.addAction(act)

    def set_value(self, value):
        self.value = value
        self.value_changed.emit()

    def set_default(self, value):
        self.default = value

    def update_value(self, i):
        self.value = i
        self.value_changed.emit()

    def set_altered(self):
        if self.default is None:
            return

        style = ''
        if self.value != self.default:
            style = 'QLabel {' + self.color_changed + '}'
        elif any(self.connections()):
            style = 'QLabel {' + self.color_altered + '}'

        if len(self.connectors) > 1:
            values = [c.read() for c in self.connectors]
            if values[:-1] != values[1:]:
                style = 'QLabel {' + self.color_mixed + '}'

        self.label_widget.setStyleSheet(style)

    def reset(self):
        if self.default is not None:
            self.set_value(self.default)
        self.reset_activated.emit()

    def add_connector(self, connector):
        if not isinstance(connector, AbstractPlugConnect):
            return

        connector.widget = self
        self.connectors.append(connector)

        values = []
        for connector in self.connectors:
            values.append(connector.read())

        self.blockSignals(True)
        self.set_value(connector.read())
        connector.update_widget()
        self.blockSignals(False)

        self.value_changed.connect(connector.update)
        self.reset_activated.connect(connector.reset)

    def connections(self):
        return [connector.connected() for connector in self.connectors]

    def clear_connections(self):
        for connector in self.connectors:
            self.value_changed.disconnect(connector.update)
            self.reset_activated.disconnect(connector.reset)
        del self.connectors[:]


class AbstractPlugConnect(object):

    def update(self):
        pass

    def reset(self):
        pass

    def read(self):
        pass

    def connected(self):
        return False

    def update_widget(self):
        pass


class BoolPlugWidget(AbstractValueWidget):

    def __init__(self, *args, **kw):
        AbstractValueWidget.__init__(self, *args, **kw)

    def build_widget(self):
        self.widget = QCheckBox()
        self.widget.stateChanged.connect(self.update_value)

    def set_default(self, value):
        self.default = bool(value)

    def set_value(self, value):
        if value is None:
            value = False

        self.widget.blockSignals(True)

        self.value = bool(value)
        st = Qt.Unchecked
        if self.value:
            st = Qt.Checked
        self.widget.setCheckState(st)

        self.widget.blockSignals(False)
        self.value_changed.emit()
        self.altered.emit()

    def update_value(self, i):
        self.value = bool(i)
        self.value_changed.emit()
        self.altered.emit()


class IntPlugWidget(AbstractValueWidget):

    def __init__(self, *args, **kw):
        AbstractValueWidget.__init__(self, *args, **kw)

    def build_widget(self):
        min_value = -1000000
        if self.min_value is not None:
            min_value = self.min_value
        max_value = 1000000
        if self.max_value is not None:
            max_value = self.max_value

        self.widget = QSpinBox()
        self.widget.setMinimum(min_value)
        self.widget.setMaximum(max_value)
        self.widget.valueChanged.connect(self.update_value)

    def set_default(self, value):
        if value is None:
            value = 0
        self.default = int(value)

    def set_value(self, value):
        if value is None:
            value = 0

        value = int(value)
        self.widget.blockSignals(True)
        self.widget.setValue(value)
        self.widget.blockSignals(False)
        self.value = value
        self.value_changed.emit()


class FloatPlugWidget(AbstractValueWidget):

    def __init__(self, *args, **kw):
        AbstractValueWidget.__init__(self, *args, **kw)

    def build_widget(self):
        min_value = -1000000
        if self.min_value is not None:
            min_value = self.min_value
        max_value = 1000000
        if self.max_value is not None:
            max_value = self.max_value

        self.widget = QDoubleSpinBox()
        self.widget.setSingleStep(0.1)
        self.widget.setMinimum(min_value)
        self.widget.setMaximum(max_value)
        self.widget.valueChanged.connect(self.update_value)

    def set_default(self, value):
        if value is None:
            value = 0
        self.default = float(value)

    def set_value(self, value):
        if value is None:
            value = 0

        value = float(value)
        self.widget.blockSignals(True)
        self.widget.setValue(value)
        self.widget.blockSignals(False)
        self.value = value
        self.value_changed.emit()


class StringPlugWidget(AbstractValueWidget):

    def __init__(self, *args, **kw):
        self.yaml = kw.get('yaml', False)
        self.filter = kw.get('filter', False)
        self.unidecode = kw.get('unidecode', False)
        AbstractValueWidget.__init__(self, *args, **kw)

    def build_widget(self):
        self.widget = QLineEdit()
        self.widget.textChanged.connect(self.update_value)

    def set_default(self, value):
        if value is None:
            value = ''

        if not self.yaml:
            self.default = str(value)
        else:
            self.default = value

    def set_value(self, value):
        if value is None:
            value = ''

        if not self.yaml:
            value = str(value)
            txt = value
        else:
            txt = yaml.dump(value, default_flow_style=True).replace('...', '').strip('\n')
            if value is None or value == '':
                txt = ''

        self.widget.blockSignals(True)
        self.widget.setText(txt)
        self.widget.blockSignals(False)
        self.value = value
        self.value_changed.emit()

    def update_value(self, value):
        value = self.widget.text()
        if self.unidecode:
            value = unidecode(value)
        if self.filter:
            value = filter_str(value)
        self.value = value

        try:
            if self.yaml and value:
                self.value = yaml.load(self.value, YamlLoader)
        except:
            pass

        self.value_changed.emit()


class StringListPlugWidget(AbstractValueWidget):

    def __init__(self, *args, **kw):
        AbstractValueWidget.__init__(self, *args, **kw)

    def build_widget(self):
        self.widget = QComboBox()
        self.widget.currentIndexChanged.connect(self.update_value)

    def set_default(self, value):
        if value is None:
            value = ''

        if isinstance(value, string_types):
            value = str(value)
        else:
            value = self.widget.itemText(int(value))

        self.default = value

    def set_value(self, value):
        if value is None:
            value = ''

        if isinstance(value, string_types):
            value = str(value)
        else:
            value = self.widget.itemText(int(value))

        string_list = self.get_list()
        if value in string_list:
            self.widget.blockSignals(True)
            self.widget.setCurrentIndex(string_list.index(value))
            self.widget.blockSignals(False)
            self.value = value
        else:
            self.value = self.default
        self.value_changed.emit()

    def update_value(self, value):
        self.value = self.widget.itemText(value)
        self.value_changed.emit()

    def set_list(self, string_list):
        self.widget.blockSignals(True)
        self.widget.clear()
        for item in string_list:
            self.widget.addItem(str(item))
        self.widget.blockSignals(False)
        self.value = string_list[0]

    def get_list(self):
        items = []
        for i in range(self.widget.count()):
            items.append(self.widget.itemText(i))
        return items


class VectorPlugWidget(AbstractValueWidget):

    def __init__(self, *args, **kw):
        AbstractValueWidget.__init__(self, *args, **kw)

    def build_widget(self):
        self.widget = QWidget()
        layout = QHBoxLayout(self.widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        self.widgets = []
        for i in range(3):
            w = QDoubleSpinBox()
            w.setButtonSymbols(QtWidgets.QAbstractSpinBox.NoButtons)
            w.setSingleStep(0.1)
            w.setRange(-100, 100)
            w.valueChanged.connect(self.update_value)
            layout.addWidget(w)
            self.widgets.append(w)

    def set_default(self, value):
        if value is None:
            value = [0.0, 0.0, 0.0]
        assert isinstance(value, list) and len(value) == 3 and all(isinstance(x, (int, float)) for x in value)

        self.default = value

    def set_value(self, value):
        if value is None:
            value = [0.0, 0.0, 0.0]
        assert isinstance(value, list) and len(value) == 3 and all(isinstance(x, (int, float)) for x in value)

        self.widget.blockSignals(True)
        for i in range(3):
            self.widgets[i].setValue(value[i])
        self.widget.blockSignals(False)
        self.value = value
        self.value_changed.emit()

    def update_value(self, value):
        self.value = [w.value() for w in self.widgets]
        self.value_changed.emit()


class VectorIntPlugWidget(AbstractValueWidget):

    def __init__(self, *args, **kw):
        AbstractValueWidget.__init__(self, *args, **kw)

    def build_widget(self):
        self.widget = QWidget()
        layout = QHBoxLayout(self.widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        self.widgets = []
        for i in range(3):
            w = QSpinBox()
            w.setButtonSymbols(QtWidgets.QAbstractSpinBox.NoButtons)
            w.setSingleStep(0.1)
            w.setRange(-100, 100)
            w.valueChanged.connect(self.update_value)
            layout.addWidget(w)
            self.widgets.append(w)

    def set_default(self, value):
        if value is None:
            value = [0, 0, 0]
        assert isinstance(value, list) and len(value) == 3 and all(isinstance(x, int) for x in value)

        self.default = value

    def set_value(self, value):
        if value is None:
            value = [0, 0, 0]
        assert isinstance(value, list) and len(value) == 3 and all(isinstance(x, int) for x in value)

        self.widget.blockSignals(True)
        for i in range(3):
            self.widgets[i].setValue(value[i])
        self.widget.blockSignals(False)
        self.value = value
        self.value_changed.emit()

    def update_value(self, value):
        self.value = [w.value() for w in self.widgets]
        self.value_changed.emit()


# cosmetics ------------------------------------------------------------------------------------------------------------


# path = os.path.dirname(__file__)
# QtCore.QResource.addSearchPath(os.path.join(path, 'icons'))
# QtCore.QResource.addSearchPath(os.path.join(path, 'pics'))


class Icon(QIcon):
    FONT_LABEL = QFont('Lucida', 7)
    FONT_LABEL.setWeight(QtGui.QFont.Weight.Bold)
    FONT_LABEL.setStretch(99)

    COLOR_LABEL = QColor('#ccc')
    COLOR_LABEL_BG = QColor(0, 0, 0, 128)
    COLOR_HIGHLIGHT = QColor('#556')
    COLOR_DARKEN = QColor('#404030')

    def __init__(self, *args, **kw):
        QtGui.QIcon.__init__(self)

        path = kw.get('path')
        if not path:
            path = os.path.join(os.path.dirname(__file__), 'icons')
        path = os.path.join(path, '{}.svg'.format(args[0]))
        # path = ':/{}.svg'.format(args[0])

        size = kw.get('size', 16)
        if not isinstance(size, QSize):
            size = QSize(size, size)
        width = size.width()

        self.pixmap = QIcon(path).pixmap(QSize(width, width))

        color = kw.get('color')
        if color is not None:
            if isinstance(color, string_types):
                color = QColor(color)
            else:
                color = QColor(*color)

            image = self.pixmap.toImage()
            painter = QPainter(image)

            painter.setCompositionMode(get_composition_mode('SourceIn'))
            painter.fillRect(self.pixmap.rect(), color)
            painter.end()

            self.pixmap = QPixmap.fromImage(image)

        label = kw.get('label')
        if label is not None:
            x = 0
            y = (width / 3) * 2
            h = (width / 3)
            w = width
            path = QtGui.QPainterPath()
            path.addRoundedRect(QtCore.QRectF(x, y, w, h), 4, 4)

            image = self.pixmap.toImage()
            painter = QPainter(image)

            painter.setPen(Qt.transparent)
            painter.setRenderHint(QPainter.Antialiasing)
            painter.fillPath(path, Icon.COLOR_LABEL_BG)
            painter.drawPath(path)

            painter.setPen(Icon.COLOR_LABEL)
            painter.setFont(Icon.FONT_LABEL)
            painter.drawText(x, y, w, h, Qt.AlignCenter, label)
            painter.end()

            self.pixmap = QPixmap.fromImage(image)

        self.addPixmap(self.pixmap, mode=QIcon.Normal, state=QIcon.On)

        if kw.get('toggle'):
            image = self.pixmap.toImage()

            no_alpha = self.pixmap.toImage()
            no_alpha = no_alpha.convertToFormat(QImage.Format_RGB888)

            painter = QPainter(no_alpha)
            painter.setCompositionMode(get_composition_mode('Difference'))
            painter.fillRect(self.pixmap.rect(), Icon.COLOR_DARKEN)
            painter.end()

            no_alpha = QPixmap.fromImage(no_alpha)

            painter = QPainter(image)
            painter.setCompositionMode(get_composition_mode('SourceIn'))
            painter.drawPixmap(0, 0, no_alpha)
            painter.end()

            pixmap = QPixmap.fromImage(image)
            self.addPixmap(pixmap, mode=QIcon.Normal, state=QIcon.Off)

        if kw.get('tool'):
            image = self.pixmap.toImage()

            no_alpha = self.pixmap.toImage()
            no_alpha = no_alpha.convertToFormat(QImage.Format_RGB888)

            painter = QPainter(no_alpha)
            painter.setCompositionMode(get_composition_mode('ColorDodge'))
            painter.fillRect(self.pixmap.rect(), Icon.COLOR_HIGHLIGHT)
            painter.end()

            no_alpha = QPixmap.fromImage(no_alpha)

            painter = QPainter(image)
            painter.setCompositionMode(get_composition_mode('SourceIn'))
            painter.drawPixmap(0, 0, no_alpha)
            painter.end()

            pixmap = QPixmap.fromImage(image)
            self.addPixmap(pixmap, mode=QIcon.Active, state=QIcon.On)


# context --------------------------------------------------------------------------------------------------------------


class BusyCursor(object):
    """Busy cursor context"""

    def __enter__(self):
        QtWidgets.QApplication.setOverrideCursor(QtGui.QCursor(QtCore.Qt.WaitCursor))

    def __exit__(self, type_, value, traceback):
        QtWidgets.QApplication.restoreOverrideCursor()


def busy_cursor(func):
    """Busy cursor decorator"""

    def wrapped(*args, **kw):
        with BusyCursor():
            func(*args, **kw)

    return wrapped


# multithreading ---------------------------------------------------------------

class ThreadSignals(QtCore.QObject):
    """
    Signals must inherit from QObject, so this is a workaround to signal from a QRunnable object.
    We will use signals to communicate from the Worker class back to the ThreadPool.
    """

    finished = QtCore.Signal(int)


class Worker(QtCore.QRunnable):
    """
    Executes code in a seperate thread.
    Communicates with the ThreadPool it spawned from via signals.
    """

    StatusOk = 0
    StatusError = 1

    def __init__(self):
        super(Worker, self).__init__()
        self.signals = ThreadSignals()

    def run(self):
        status = Worker.StatusOk

        try:
            time.sleep(1)  # process something big here
        except:
            print(traceback.format_exc())
            status = Worker.StatusError

        self.signals.finished.emit(status)


class ThreadPool(QtCore.QObject):
    """
    Manages all Worker objects.
    This will receive signals from workers then communicate back to the main gui.
    """

    pool_started = QtCore.Signal(int)
    pool_finished = QtCore.Signal()
    worker_finished = QtCore.Signal(int)

    def __init__(self, max_thread_count=1):
        QtCore.QObject.__init__(self)

        self._count = 0
        self._processed = 0
        self._has_errors = False

        self.pool = QtCore.QThreadPool()
        self.pool.setMaxThreadCount(max_thread_count)

    def worker_on_finished(self, status):
        self._processed += 1

        # if a worker fails, indicate that an error happened
        if status == Worker.StatusError:
            self._has_errors = True

        if self._processed == self._count:
            # signal to gui that all workers are done
            self.pool_finished.emit()

    def start(self, count):
        # reset values
        self._count = count
        self._processed = 0
        self._has_errors = False

        # signal to gui that workers are about to begin. You can prepare your gui at this point
        self.pool_started.emit(count)

        # create workers and connect signals to gui so we can update it as they finish
        for i in range(count):
            worker = Worker()
            worker.signals.finished.connect(self.worker_finished)
            worker.signals.finished.connect(self.worker_on_finished)
            self.pool.start(worker)


# syntax highlighter

class SyntaxHighlighter(QSyntaxHighlighter):

    def __init__(self, parent):
        QSyntaxHighlighter.__init__(self, parent)
        self.parent = parent

        self.styles = {}
        self.rules = []

    def add_style(self, name, color, **kw):
        _format = QTextCharFormat()

        if isinstance(color, (tuple, list)):
            _color = QColor(*color)
        elif isinstance(color, string_types):
            _color = QtGui.QColor()
            _color.setNamedColor(color)
        else:
            _color = color
        _format.setForeground(_color)

        color = kw.get('background')
        if color:
            if isinstance(color, (tuple, list)):
                _color = QColor(*color)
            elif isinstance(color, string_types):
                _color = QtGui.QColor()
                _color.setNamedColor(color)
            else:
                _color = color
            _format.setBackground(_color)

        if kw.get('bold'):
            _format.setFontWeight(QtGui.QFont.Bold)
        if kw.get('italic'):
            _format.setFontItalic(True)

        self.styles[name] = _format

    def add_styles(self, styles):
        if not isinstance(styles, (tuple, list)):
            raise TypeError('list needed')

        for style in styles:
            if not isinstance(style, (tuple, list)):
                continue
            if len(style) == 2:
                style = list(style) + [{}]

            self.add_style(style[0], style[1], **style[2])

    def add_rule(self, expression, index, style):
        if style not in self.styles:
            raise ValueError('style {} does not exist'.format(style))

        try:
            rule = (QtCore.QRegularExpression(expression), index, self.styles[style])
        except:
            rule = (QtCore.QRegExp(expression), index, self.styles[style])

        self.rules.append(rule)

    def add_rules(self, rules):
        if not isinstance(rules, (tuple, list)):
            raise TypeError('list needed')

        for rule in rules:
            if not isinstance(rule, (tuple, list)) and len(rule) != 3:
                continue
            self.add_rule(*rule)

    def highlightBlock(self, text):
        text = text.encode('unicode_escape').decode()

        for expression, nth, format in self.rules:
            if hasattr(expression, 'globalMatch'):
                # QRegularExpression (PySide6)
                match_iterator = expression.globalMatch(text)
                while match_iterator.hasNext():
                    match = match_iterator.next()
                    index = match.capturedStart(nth)
                    length = len(match.captured(nth))
                    self.setFormat(index, length, format)
            else:
                # QRegExp (PySide2)
                index = expression.indexIn(text, 0)
                while index >= 0:
                    index = expression.pos(nth)
                    length = len(expression.cap(nth))
                    self.setFormat(index, length, format)
                    index = expression.indexIn(text, index + length)


# -- compat Pyside2/6

def get_composition_mode(name):
    """Retourne le QPainter.CompositionMode compatible PySide2/PySide6."""
    try:
        # PySide6 (enum imbriquée)
        return getattr(QPainter.CompositionMode, str(name))
    except AttributeError:
        # PySide2 (attribut direct sur QPainter)
        return getattr(QPainter, 'CompositionMode_{}'.format(name))


def get_palette_role(name):
    """Retourne un rôle de palette compatible PySide2 / PySide6."""
    try:
        # PySide6 style (enum imbriquée)
        return getattr(QPalette.ColorRole, name)
    except AttributeError:
        # PySide2 style (attribut direct)
        return getattr(QPalette, name)
