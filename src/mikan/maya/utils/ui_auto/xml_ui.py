# coding: utf-8

import os
import math
import time
import string
import datetime

import maya.mel
import maya.mel as mel
from six import string_types

from mikan.vendor.Qt import QtCore, QtGui
from mikan.vendor.Qt.QtCore import Qt
from mikan.vendor.Qt.QtWidgets import (
    QPushButton, QLabel, QAction, QLineEdit, QMenu,
    QCheckBox, QListWidget, QListView, QListWidgetItem
)

from mikan.core.ui.widgets import StackWidget
from mikan.maya.ui.widgets import MayaWindow, Callback

from mikan.maya.utils.ui_auto.xml_db import XmlDB, path_remove_extension
from mikan.core.logger import create_logger

__all__ = ['XmlAutoUI']

maya_pid = maya.mel.eval("getpid")
log = create_logger('UI', save='E:/TEMP/maya_mikan_logger_{}.log'.format(maya_pid))
log.setLevel('DEBUG')

r'''
from mikan.maya.sandbox.matthieu.ui_auto.xml_ui import XmlAutoUI
reload(mikan.maya.sandbox.matthieu.ui_auto.xml_ui)

args = {}
args['filePath'] = 'E:/Matthieu CANTAT/xml_test/transfer_to_model_coefs.xml' 
args['sub_key_to_search'] = ['origin_show','origin_char','origin_version','target_show','target_char','target_version']
args['sub_key_to_show']   = ['comment'] 

xml_UI = XmlAutoUI( **args  )
xml_UI.show()
'''


class XmlAutoUI(MayaWindow):
    ui_height = 200
    ui_width = 250

    def __init__(self, **kw):
        self.__class__.__name__ = kw.get('win_name', 'XmlAutoUI')
        MayaWindow.__init__(self, parent=kw.get('parent', None))

        self.xml_path = kw.get('xml_path', '')
        self.xml_dict = kw.get('dict', {})
        self.xml_dict_keys = kw.get('keys', None)

        self.title = kw.get('title', '')
        self.title_cmds = kw.get('title_cmds', [])
        self.title_cmds_name = kw.get('title_cmds_name', [])

        self.sub_key_to_search = kw.get('sub_key_to_search', [])
        self.sub_key_to_search_prez_pattern = kw.get('sub_key_to_search_prez_pattern', [])
        self.sub_key_to_fill = kw.get('sub_key_to_fill', [])
        self.sub_key_latest = kw.get('sub_key_latest', None)
        self.sub_key_to_sort_override = kw.get('sub_key_to_sort_override', -1)

        self.dict_to_add = kw.get('dict_to_add', [])

        r'''
        self.cmd_module_import  = args.get('cmd_module_import','')   
        self.cmd_name           = args.get('cmd_name'         ,'')   
        self.cmd_args           = args.get('cmd_args'         ,[])  
        self.cmd_values         = args.get('cmd_values'       ,[])  
        '''
        self.cmds_module_import = kw.get('cmds_module_import', [])
        self.cmds = kw.get('cmds', [])
        self.cmds_args = kw.get('cmds_args', [])
        self.cmds_values = kw.get('cmds_values', [])
        self.cmds_name = kw.get('cmds_name', [])

        self.multi_cmds_module_import = kw.get('multi_cmds_module_import', [])
        self.multi_cmds = kw.get('multi_cmds', [])
        self.multi_cmds_args = kw.get('multi_cmds_args', [])
        self.multi_cmds_values = kw.get('multi_cmds_values', [])
        self.multi_cmds_name = kw.get('multi_cmds_name', [])

        self.xml = XmlDB()

        if self.xml_path != '':
            self.xml.create_from_file(self.xml_path, latest=1)
            self.xml_dict = self.xml.dict

        self.key_outs = []
        self.search_latest_checkBox = None
        self.search_selected_checkBox = None

        self.setWindowTitle(self.__class__.__name__)
        self.setWindowFlags(Qt.Tool)
        self.setStyleSheet('QPushButton {max-height: 16px;}')
        # self.resize(self.ui_width, self.ui_height)
        # self.setMinimumWidth(600)
        # self.setMinimumHeight(self.ui_height)

        self.tab = StackWidget()
        self.setCentralWidget(self.tab)

        self.Fields_sub_key_add = []

        self.close_after_select = False
        self.search_latest = True
        self.search_selected = False

        self.search_page_ui = []

        self.search_page_max_elements = 5000
        self.search_page_max_elements = 500
        self.search_page_nbr = 0
        self.search_page_current = 0

        self.list_elems = []
        self.keys_titles = []
        self.keys_titles_to_main_key = {}
        self.keys_titles_to_color = {}
        self.build_search_list_prepare()

        self.title_lbl = None
        self.title_popMenu = None

        self.search_list_popMenu = None
        self.sub_key_to_search_sort = [0] * len(self.sub_key_to_search)
        if self.sub_key_to_sort_override != -1:
            self.sub_key_to_search_sort[self.sub_key_to_sort_override] = 1

        self.clicked_button_history = []
        self.double_clicked_button_history = None

        # self.button_color_base     = [100,100,100]
        self.button_color_selected = [50, 150, 50]

    def search_ui_panel(self):

        self.grid_search = self.tab.add_grid()
        i_offset = 0

        # TITLE
        if (0 < len(self.title)):
            self.title_lbl = QLabel('{}'.format(self.title), alignment=Qt.AlignCenter)
            self.title_lbl.setStyleSheet('QLabel {color:#89a; font-size:12px; font-weight:bold;}')
            self.grid_search.addWidget(self.title_lbl, 0, 1, stretch=0)
            i_offset += 1

            # POP UP TEST__________________________________________________________________
            # set button context menu policy
            self.title_lbl.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
            self.title_lbl.customContextMenuRequested.connect(self.title_context_menu)

            # create context menu
            self.title_popMenu = QMenu(self)
            for j in range(0, len(self.title_cmds_name)):
                action_tmp = QAction(self.title_cmds_name[j], self)
                self.title_popMenu.addAction(action_tmp)
                action_tmp.triggered.connect(Callback(self.title_cmds_sel, j))

        # SEARCH LINE
        lbl = QLabel('search : ', alignment=Qt.AlignCenter)
        lbl.setStyleSheet('QLabel {color:#89a; font-size:12px; font-weight:bold;}')
        self.grid_search.addWidget(lbl, 0 + i_offset, 0, stretch=0)

        self.search_field = QLineEdit()
        self.search_field.returnPressed.connect(Callback(self.cmd_reload_search_field))  # self.search_field.textChanged.connect(Callback( self.cmd_reload_search_field ))
        self.grid_search.addWidget(self.search_field, 0 + i_offset, 1, stretch=0)

        # LATEST CHECKBOX
        if (self.sub_key_latest != None):
            self.search_latest_checkBox = QCheckBox("latest {}".format(self.sub_key_latest))
            if (self.search_latest):
                self.search_latest_checkBox.setChecked(Qt.Checked)
            self.search_latest_checkBox.stateChanged.connect(Callback(self.cmd_latest_checkBox))  # self.search_field.textChanged.connect(Callback( self.cmd_reload_search_field ))
            self.grid_search.addWidget(self.search_latest_checkBox, 0 + i_offset, 2, stretch=0)

        i_offset += 1

        # REMOVE LINE
        lbl = QLabel('remove : ', alignment=Qt.AlignCenter)
        lbl.setStyleSheet('QLabel {color:#89a; font-size:12px; font-weight:bold;}')
        self.grid_search.addWidget(lbl, 0 + i_offset, 0, stretch=0)

        self.remove_field = QLineEdit()
        self.remove_field.returnPressed.connect(Callback(self.cmd_reload_search_field))  # self.search_field.textChanged.connect(Callback( self.cmd_reload_search_field ))
        self.grid_search.addWidget(self.remove_field, 0 + i_offset, 1, stretch=0)

        # SELECTED CHECKBOX
        self.search_selected_checkBox = QCheckBox("show only selected")
        if (self.search_selected):
            self.search_selected_checkBox.setChecked(Qt.Checked)
        self.search_selected_checkBox.stateChanged.connect(Callback(self.cmd_selected_checkBox))  # self.search_field.textChanged.connect(Callback( self.cmd_reload_search_field ))
        self.grid_search.addWidget(self.search_selected_checkBox, 0 + i_offset, 2, stretch=0)

        i_offset += 1

        # OTHER
        self.grid_search_list = self.tab.add_grid()
        self.list_elems = self.build_search_list(self.grid_search_list, i_offset)

        self.setGeometry(self.get_optvar('geometry', self.geometry()))
        self.safe_position()

    def add_ui(self, show=True):
        self.build_add()
        if (show): self.show()

    def select_ui(self, show=True):
        self.search_ui_panel()
        if (show): self.show()

    def delete_ui(self, show=True):
        self.search_ui_panel()
        if (show): self.show()

    def build_search_list_prepare(self, keep_active_selection=False):
        # log.info(' ' )
        # log.info('++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++ {}.build_search_list_prepare - START'.format(self.__class__.__name__) )
        # log.info(' ' )
        # log.info('xml_dict nbr - {}'.format( len(list(self.xml_dict)) ) )
        # log.info('latest       - {}'.format( self.sub_key_latest ) )
        # log.info('search       - {}'.format( self.sub_key_to_search ) )
        # log.info('keys_titles nbr - BEFORE - {}'.format( len(self.keys_titles) ) )
        # GET INFOS
        self.keys_titles = []
        self.keys_titles_to_main_key = {}
        self.keys_titles_to_color = {}
        self.get_keys_titles_info(self.xml_dict, self.sub_key_to_search, self.sub_key_to_search_prez_pattern, self.sub_key_latest, keep_active_selection=keep_active_selection)

        # log.info('keys_titles nbr - AFTER  - {}'.format( len(self.keys_titles) ) )
        # log.info(' ' )
        # log.info('---------------------------------------------------------------------------- {}.build_search_list_prepare - END'.format(self.__class__.__name__) )
        # log.info(' ' )

    def build_search_list(self, parent, gridLineStartPosition=3):
        # log.info(' ' )
        # log.info('++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++ {}.build_search_list - START'.format(self.__class__.__name__) )
        # log.info(' ' )

        special_front = QtGui.QFont('courier new', 9)
        special_front.setFixedPitch(True)

        # SEARCH
        log.info('FILTER - SEARCH        - BEFORE - {}'.format(len(self.keys_titles)))
        search = self.search_field.text()
        search_words = search.split(" ")

        remove = self.remove_field.text()
        remove_words = remove.split(" ")

        count = 0
        found_indexes = []
        for i in range(0, len(self.keys_titles)):

            found = 1
            if (search != ""):
                for word in search_words:
                    if not (word in self.keys_titles[i]):
                        found = 0
                        break

            if (remove != ""):
                for word in remove_words:
                    if (word in self.keys_titles[i]):
                        found = 0
                        break

            if (found == 1):
                found_indexes.append(i)

        log.info('FILTER - SEARCH        - AFTER  - {}'.format(len(found_indexes)))

        # SELECTED
        log.info('FILTER - ONLY SELECTED - BEFORE - {}'.format(len(found_indexes)))
        if (self.search_selected):
            found_indexes_selected = []
            for i in found_indexes:
                if (self.keys_titles_selected[i] == 1):
                    found_indexes_selected.append(i)

            found_indexes = found_indexes_selected[:]

        log.info('FILTER - ONLY SELECTED - AFTER  - {}'.format(len(found_indexes)))

        # SORT
        log.info('SORT')
        key_to_sort = None
        for i in range(0, len(self.sub_key_to_search_sort)):
            if (self.sub_key_to_search_sort[i] == 1):
                key_to_sort = self.sub_key_to_search[i]

        if (key_to_sort != None):
            values_to_sort = []
            for i in found_indexes:
                main_key = self.keys_titles_to_main_key[self.keys_titles[i]]
                values_to_sort.append(self.xml_dict[main_key].get(key_to_sort, ''))

            values_sorted = values_to_sort[:]
            if (key_to_sort in ['date']):

                values_to_sort_reformated = []
                for i in range(0, len(values_to_sort)):
                    date, hour = values_to_sort[i].split('   ')
                    dates = date.split('/')
                    date_reformated = '{}   {}'.format('/'.join([dates[2], dates[1], dates[0]]), hour)
                    values_to_sort_reformated.append(date_reformated)

                values_to_sort = values_to_sort_reformated
                values_sorted = values_to_sort[:]
                values_sorted.sort()

            else:
                values_sorted.sort()

            values_sorted.reverse()

            found_indexes_sorted = []
            indexes_sorted = []
            for i in range(0, len(values_sorted)):
                i_sorted = values_to_sort.index(values_sorted[i])
                values_to_sort[i_sorted] = 'randomGarbageValue'
                found_indexes_sorted.append(found_indexes[i_sorted])

            found_indexes = found_indexes_sorted

        # PAGE

        self.search_page_nbr = int(math.ceil(len(found_indexes) / self.search_page_max_elements))
        if (self.search_page_nbr < self.search_page_current):
            self.search_page_current = 0
        iStart = self.search_page_current * self.search_page_max_elements
        iEnd = min(len(found_indexes), (self.search_page_current + 1) * self.search_page_max_elements)
        log.info('PAGE - CLAMP - pages nbr: {} - page current: {} - iStart: {} - iEnd: {}'.format(self.search_page_nbr, self.search_page_current, iStart, iEnd))

        # UI PAGE
        self.search_page_ui = []
        i_offset = gridLineStartPosition
        if (0 < self.search_page_nbr):
            search_page_before_btn = QPushButton('<---')
            search_page_before_btn.clicked.connect(Callback(self.cmd_search_page_move, -1))  # self.search_field.textChanged.connect(Callback( self.cmd_reload_search_field ))
            self.grid_search.addWidget(search_page_before_btn, i_offset, 0, stretch=0)

            lbl = QLabel('page {}/{}'.format(self.search_page_current + 1, int(self.search_page_nbr)), alignment=Qt.AlignCenter)
            self.grid_search.addWidget(lbl, i_offset, 1, stretch=0)

            search_page_after_btn = QPushButton('--->')
            search_page_after_btn.clicked.connect(Callback(self.cmd_search_page_move, 1))  # self.search_field.textChanged.connect(Callback( self.cmd_reload_search_field ))
            self.grid_search.addWidget(search_page_after_btn, i_offset, 2, stretch=0)

            self.search_page_ui = [lbl, search_page_before_btn, search_page_after_btn]
            i_offset += 1

        # for fix_i in range(0,2): # wtf QT... make it twice avoid a bug, if I search for on element, it doesn t apear, I have to search a second time...

        self.search_list = QListWidget()
        self.search_list.setViewMode(QListView.IconMode)
        # self.search_list.setContextMenuPolicy(Qt.NoContextMenu)
        self.search_list.setStyleSheet('QListWidget {background-color: #333; border: none;}')
        self.search_list.setMovement(QListView.Static)
        self.search_list.setFlow(QListView.LeftToRight)
        self.search_list.setResizeMode(QListView.Adjust)
        self.search_list.setSpacing(0)
        self.search_list.setUniformItemSizes(True)
        parent.addWidget(self.search_list, 0, 0)

        self.search_list.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.search_list.customContextMenuRequested.connect(self.search_list_context_menu)

        # create context menu
        self.search_list_popMenu = QMenu(self)
        for j in range(0, len(self.sub_key_to_search)):
            action_tmp = QAction(self.sub_key_to_search[j] + ' <<<' * self.sub_key_to_search_sort[j], self)
            self.search_list_popMenu.addAction(action_tmp)
            action_tmp.triggered.connect(Callback(self.cmds_search_list_popup, j))

        # PAGE
        self.btns = [None for i in range(0, len(self.keys_titles))]
        self.btns_popMenu = [None for i in range(0, len(self.keys_titles))]

        lap = 0
        for i in found_indexes[iStart:iEnd]:
            btn = QPushButton(self.keys_titles[i])
            # btn.setToolTipsVisible(True)
            # btn.setToolTip('toto toto atatatat')

            btn.setFont(special_front)
            btn.setStyleSheet('QPushButton {color:rgb(100,100,100); font-style:monospace-size:17px; font-weight:bold; margin-left:2px;}')

            button_color = self.keys_titles_to_color[self.keys_titles_to_main_key[self.keys_titles[i]]]
            btn.setStyleSheet("background-color:rgb({},{},{})".format(button_color[0], button_color[1], button_color[2]))
            if (self.keys_titles_selected[i] == 1):
                button_color = self.button_color_selected
                btn.setStyleSheet("background-color:rgb({},{},{})".format(button_color[0], button_color[1], button_color[2]))

            btn.clicked.connect(Callback(self.cmd_clicked_button, i, found_indexes[iStart:iEnd]))

            item = QListWidgetItem()
            item.setSizeHint(btn.sizeHint())

            lap = self.search_list.count()
            self.search_list.insertItem(lap + 1, item)
            self.search_list.setItemWidget(item, btn)
            self.search_list.repaint()
            self.search_list.insertItem(lap + 2, item)

            self.btns[i] = btn

            # POP UP TEST__________________________________________________________________
            # set button context menu policy
            btn.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
            btn.customContextMenuRequested.connect(self.btns_on_context_menu(i))

            # create context menu
            popMenu = QMenu(self)
            for j in range(0, len(self.multi_cmds_name)):
                action_tmp = QAction(self.multi_cmds_name[j], self)
                popMenu.addAction(action_tmp)
                action_tmp.triggered.connect(Callback(self.multi_cmds_sel_key, j))

            for j in range(0, len(self.cmds_name)):
                action_tmp = QAction(self.cmds_name[j], self)
                popMenu.addAction(action_tmp)
                action_tmp.triggered.connect(Callback(self.cmds_sel_key, j, i))

            self.btns_popMenu[i] = popMenu

            lap += 1

        self.search_list.setResizeMode(QListView.Adjust)
        self.search_list.repaint()

        # log.info(' ' )
        # log.info('---------------------------------------------------------------------------- {}.build_search_list - END'.format(self.__class__.__name__) )
        # log.info(' ' )

        return self.btns

    def btns_on_context_menu(self, i):
        def on_context_menu(point):
            # show context menu
            self.btns_popMenu[i].exec_(self.btns[i].mapToGlobal(point))

        return on_context_menu

    def title_context_menu(self, point):
        # show context menu
        self.title_popMenu.exec_(self.title_lbl.mapToGlobal(point))

    def search_list_context_menu(self, point):
        # show context menu
        self.search_list_popMenu.exec_(self.search_list.mapToGlobal(point))

    def build_add(self):

        if (0 < len(self.title)):
            row = self.tab.add_row(spacing=10)
            lbl = QLabel('{}'.format(self.title), alignment=Qt.AlignCenter)
            lbl.setStyleSheet('QLabel {color:#89a; font-size:12px; font-weight:bold;}')
            row.addWidget(lbl)

        grid_add_list = self.tab.add_grid()
        btns = []
        self.Fields_sub_key_add = []
        for j in range(0, len(self.sub_key_to_fill)):
            lbl = QLabel('{}'.format(self.sub_key_to_fill[j]), alignment=Qt.AlignCenter)
            lbl.setStyleSheet('QLabel {color:#89a; font-size:12px; font-weight:bold;}')
            grid_add_list.addWidget(lbl, j, 0, stretch=0)

            btn = QLineEdit()
            btn.setStyleSheet('QLineEdit { background-color:black;}')
            btn.setText("")
            self.Fields_sub_key_add.append(btn)
            grid_add_list.addWidget(btn, j, 1, stretch=1)

            btns.append(btn)

        row = self.tab.add_row(spacing=10)
        btn = QPushButton("ADD")
        # btn.setStyleSheet('QPushButton {color:#89a; font-size:17px; font-weight:bold; background-color:black;}')
        btn.clicked.connect(Callback(self.cmd_add))
        row.addWidget(btn)

        return btns

    def cmd_add(self):
        main_key = list(self.dict_to_add)[0]

        for i in range(0, len(self.sub_key_to_fill)):
            self.dict_to_add[main_key][self.sub_key_to_fill[i]] = self.Fields_sub_key_add[i].text()

        self.xml.dict[main_key] = {}
        for key in list(self.dict_to_add[main_key]):
            self.xml.dict[main_key][key] = self.dict_to_add[main_key][key]

        self.xml.to_file(self.xml_path, clearOldVar=1, incr=1)
        self.close()

    def cmd_reload_search_field(self, keep_user_position=False):
        for elem in self.list_elems:
            if (elem != None):
                elem.close()
        for elem in self.search_page_ui:
            if (elem != None):
                elem.close()

        row = self.search_list.currentRow()
        self.list_elems = self.build_search_list(self.grid_search_list)

        if (keep_user_position):
            self.search_list.setCurrentRow(row)

    def cmd_latest_checkBox(self):
        if (self.search_latest == False):
            self.search_latest = True
        else:
            self.search_latest = False
        self.build_search_list_prepare()
        self.cmd_reload_search_field()

    def cmd_selected_checkBox(self):
        if (self.search_selected == False):
            self.search_selected = True
        else:
            self.search_selected = False
        self.cmd_reload_search_field()

    def cmd_search_page_move(self, move):

        self.search_page_current += move
        if (self.search_page_current < 0):
            self.search_page_current = self.search_page_nbr - 1
        elif (self.search_page_nbr <= self.search_page_current):
            self.search_page_current = 0

        self.cmd_reload_search_field()

    def cmd_clicked_button(self, current_index, display_indexes=None):

        double_click_speed = 0.35
        if (0 < len(self.clicked_button_history)) and (self.clicked_button_history[0][0] == current_index):
            self.clicked_button_history.append([current_index, time.clock()])
        else:
            self.clicked_button_history = [[current_index, time.clock()]]

        if (1 < len(self.clicked_button_history)) and (self.clicked_button_history[-1][1] - self.clicked_button_history[-2][1] < double_click_speed) and (self.double_clicked_button_history == 'ALL') and (display_indexes != None):
            print("cmd_clicked_button_________________CLEAR")
            for i in display_indexes:
                self.keys_titles_selected[i] = 0
                if (self.keys_titles_selected[i] == 1):
                    button_color = self.button_color_selected
                    self.btns[i].setStyleSheet("background-color:rgb({},{},{})".format(button_color[0], button_color[1], button_color[2]))
                else:
                    button_color = self.keys_titles_to_color[self.keys_titles_to_main_key[self.keys_titles[i]]]
                    self.btns[i].setStyleSheet('QPushButton {' + 'color:rgb({},{},{})'.format(button_color[0], button_color[1], button_color[2]) + '; font-style:monospace-size:17px; font-weight:bold; margin-left:2px;}')
                    self.btns[i].setStyleSheet("background-color:rgb({},{},{})".format(button_color[0], button_color[1], button_color[2]))

            self.clicked_button_history = []
            self.double_clicked_button_history = None

        elif (1 < len(self.clicked_button_history)) and (self.clicked_button_history[-1][1] - self.clicked_button_history[-2][1] < double_click_speed) and (display_indexes != None):
            print("cmd_clicked_button_________________ALL")
            for i in display_indexes:
                self.keys_titles_selected[i] = 1 - self.keys_titles_selected[i]
                if (self.keys_titles_selected[i] == 1):
                    button_color = self.button_color_selected
                    self.btns[i].setStyleSheet("background-color:rgb({},{},{})".format(button_color[0], button_color[1], button_color[2]))
                else:
                    button_color = self.keys_titles_to_color[self.keys_titles_to_main_key[self.keys_titles[i]]]
                    self.btns[i].setStyleSheet('QPushButton {' + 'color:rgb({},{},{})'.format(button_color[0], button_color[1], button_color[2]) + '; font-style:monospace-size:17px; font-weight:bold; margin-left:2px;}')
                    self.btns[i].setStyleSheet("background-color:rgb({},{},{})".format(button_color[0], button_color[1], button_color[2]))

            self.double_clicked_button_history = 'ALL'
        else:
            i = current_index
            self.keys_titles_selected[i] = 1 - self.keys_titles_selected[i]
            if (self.btns[i] != None):
                if (self.keys_titles_selected[i] == 1):
                    button_color = self.button_color_selected
                    self.btns[i].setStyleSheet("background-color:rgb({},{},{})".format(button_color[0], button_color[1], button_color[2]))
                else:
                    button_color = self.keys_titles_to_color[self.keys_titles_to_main_key[self.keys_titles[i]]]
                    self.btns[i].setStyleSheet('QPushButton {' + 'color:rgb({},{},{})'.format(button_color[0], button_color[1], button_color[2]) + '; font-style:monospace-size:17px; font-weight:bold; margin-left:2px;}')
                    self.btns[i].setStyleSheet("background-color:rgb({},{},{})".format(button_color[0], button_color[1], button_color[2]))

    def title_cmds_sel(self, cmd_index):
        to_eval_mel = "python(\"{}\")".format(self.title_cmds[cmd_index])
        print(to_eval_mel)
        mel.eval(to_eval_mel)

    def cmds_search_list_popup(self, cmd_index):
        if (self.sub_key_to_search_sort[cmd_index] == 1):
            self.sub_key_to_search_sort = [0] * len(self.sub_key_to_search)
        else:
            self.sub_key_to_search_sort = [0] * len(self.sub_key_to_search)
            self.sub_key_to_search_sort[cmd_index] = 1

        self.cmd_reload_search_field()

    def cmds_sel_key(self, cmd_index, key_index):
        if (self.keys_titles_selected == [0] * len(self.keys_titles)):
            self.key_outs = [self.keys_titles_to_main_key[self.keys_titles[key_index]]]
        else:
            self.key_outs = self.get_selected_keys()

        for key_out in self.key_outs:

            to_eval = self.cmds_module_import[cmd_index]
            if (to_eval != "") and (to_eval[-1] != ";"):
                to_eval += ';'
            to_eval += self.cmds[cmd_index] + '('

            args = []
            for i in range(0, len(self.cmds_args[cmd_index])):
                arg_str = self.cmds_args[cmd_index][i]

                value = self.cmds_values[cmd_index][i]
                if (isinstance(value, string_types)) and (value[:3] == '>>>'):
                    key_to_search = value[3:]
                    if (key_to_search == ''):
                        value = key_out
                    else:
                        value = self.xml_dict[key_out].get(key_to_search, None)

                value_str = ''
                if (value == ''):
                    value_str = '\'\''
                elif (isinstance(value, (bool))):
                    value_str = '{}'.format(value)
                elif (isinstance(value, (int, float))):
                    value_str = '{}'.format(value)
                elif (isinstance(value, (list, tuple))):
                    value_str = '{}'.format(value)
                elif (value == None):
                    value_str = '{}'.format(value)
                else:
                    value_str = '\'{}\''.format(value)

                if (arg_str == ''):
                    args.append('{}'.format(value_str))
                else:
                    args.append('{} = {}'.format(arg_str, value_str))

            to_eval += ' , '.join(args)
            to_eval += ')'

            print('run : {}'.format(to_eval))

            # exec(to_eval , globals() )
            to_eval_mel = "python(\"{}\")".format(to_eval)
            print(to_eval_mel)
            mel.eval(to_eval_mel)

        if (self.close_after_select):
            self.close()

    def multi_cmds_sel_key(self, cmd_index):

        self.key_outs = self.get_selected_keys()

        to_eval = self.multi_cmds_module_import[cmd_index]
        if (to_eval != "") and (to_eval[-1] != ";"):
            to_eval += ';'
        to_eval += self.multi_cmds[cmd_index] + '('

        args = []
        for i in range(0, len(self.multi_cmds_args[cmd_index])):
            arg_str = self.multi_cmds_args[cmd_index][i]

            value = self.multi_cmds_values[cmd_index][i]
            if (isinstance(value, string_types)) and (value[:3] == '>>>'):
                key_to_search = value[3:]

                values_str = []
                for key_out in self.key_outs:

                    if (key_to_search == ''):
                        value = key_out
                    else:
                        value = self.xml_dict[key_out][key_to_search]

                    value_str = ''
                    if (value == ''):
                        value_str = '\'\''
                    elif (isinstance(value, (bool))):
                        value_str = '{}'.format(value)
                    elif (isinstance(value, (int, float))):
                        value_str = '{}'.format(value)
                    elif (isinstance(value, (list, tuple))):
                        value_str = value
                    else:
                        value_str = value
                    values_str.append(value_str)

            if (arg_str == ''):
                args.append('{}'.format(values_str))
            else:
                args.append('{} = {}'.format(arg_str, values_str))

        to_eval += ' , '.join(args)
        to_eval += ')'

        print('run : {}'.format(to_eval))

        # exec(to_eval , globals() )
        to_eval_mel = "python(\"{}\")".format(to_eval)
        print(to_eval_mel)
        mel.eval(to_eval_mel)

        if (self.close_after_select):
            self.close()

    def get_selected_keys(self):
        return [self.keys_titles_to_main_key[self.keys_titles[i]] for i in range(0, len(self.keys_titles_selected)) if (self.keys_titles_selected[i] == 1)]

    def select_keys(self, preview_keys):
        keys = list(self.xml_dict)

        for i in range(0, len(self.keys_titles)):
            if (self.keys_titles_to_main_key[self.keys_titles[i]] in preview_keys):
                self.cmd_clicked_button(i)

    def get_keys_titles_info(self, dict, sub_key_to_search=[], pattern=[], sub_key_latest=None, keep_active_selection=False):

        keys = list(dict)
        if (self.xml_dict_keys != None):
            keys = self.xml_dict_keys

        # LATEST
        r'''
        if( sub_key_latest != None )and( self.search_latest ):
            
            
            keys_latest = []
    
            key_last   = None     
            value_last = None
            #for key in keys:
            for i in range( 0 , len(keys)):
                value = dict[keys[i]][sub_key_latest]

                if( value <= value_last ):
                    keys_latest.append( key_last )
                else:
                    pass

                value_last = value
                key_last   = keys[i]

 
            if( 0 < len(keys) ):
                keys_latest.append( key_last )

            #keys = keys_latest
            #LATEST
            '''

        if (sub_key_latest != None) and (self.search_latest):
            dict_filtered = preview_filter_latest(dict)
            keys = [key for key in keys if (key in list(dict_filtered))]

        sections_str_max_length = [0] * len(sub_key_to_search)

        for i in range(0, len(sub_key_to_search)):
            for key in keys:
                str = '{}'.format(dict[key].get(sub_key_to_search[i], ''))
                str_size = len(str)
                if (sections_str_max_length[i] < str_size):
                    sections_str_max_length[i] = str_size

        keys_titles_to_main_key = {}
        titles = []
        for key in keys:
            title = ''
            for i in range(0, len(sub_key_to_search)):
                str = '{}'.format(dict[key].get(sub_key_to_search[i], ''))
                str_size = len(str)

                title += str + ' ' * (sections_str_max_length[i] - str_size)
                if i < len(pattern):
                    title += pattern[i]
                else:
                    title += "   "
            titles.append(title)
            keys_titles_to_main_key[title] = key

        self.keys_titles = titles
        self.keys_titles_to_main_key = keys_titles_to_main_key
        if not keep_active_selection:
            self.keys_titles_selected = [0] * len(self.keys_titles)

        for key in keys:
            if 'color' in dict[key]:
                self.keys_titles_to_color[key] = dict[key]['color']
            else:
                self.keys_titles_to_color[key] = [100, 100, 100]

    def reload_with_new_dict(self, new_dict, keys=None):
        self.xml_dict = new_dict
        if (keys != None):
            self.xml_dict_keys = keys
        # SEARCH UI
        self.build_search_list_prepare()
        self.cmd_reload_search_field()


######################################################## FROM TEAMTO_ASSET
def reorder_date_str_for_sort(date_str):
    # "%d/%m/%Y   %H:%M:%S")
    # "%Y/%m/%d   %H:%M:%S")

    day_str = date_str.split('   ')[0]
    time_str = date_str.split('   ')[1]

    day_str_splitted = day_str.split('/')
    day_str_new = '/'.join([day_str_splitted[2], day_str_splitted[1], day_str_splitted[0]])
    date_str_new = '   '.join([day_str_new, time_str])

    return date_str_new


def preview_filter_latest(preview):
    path_body_to_date = {}
    for key in list(preview):

        path_body = get_path_body(preview[key]['path'])
        if path_body in list(path_body_to_date):
            date_new = preview[key]['date']
            date_stored = path_body_to_date[path_body]
            if (reorder_date_str_for_sort(date_stored) < reorder_date_str_for_sort(date_new)):
                path_body_to_date[path_body] = date_new
        else:
            path_body_to_date[path_body] = preview[key]['date']

    preview_filtered = {}
    for key in list(preview):
        path_body = get_path_body(preview[key]['path'])
        if (path_body_to_date[path_body] == preview[key]['date']):
            preview_filtered[key] = preview[key]

    return preview_filtered


def paths_dict_filter_latest(paths_dict, use_date=True):
    paths_to_search = paths_dict
    path_body_info = {}

    for path in paths_to_search:
        body = get_path_body(path)
        path_body_info.setdefault(body, [])
        path_body_info[body].append(path)

    latest = []

    if (use_date):

        for body in list(path_body_info):
            dates = []

            for p in path_body_info[body]:
                statinfo = os.stat(p)
                date_raw = datetime.datetime.fromtimestamp(statinfo.st_mtime).strftime("%d/%m/%Y   %H:%M:%S")
                dates.append(reorder_date_str_for_sort(date_raw))

            dates_sorted = dates[:]
            dates_sorted.sort()
            latest_i = dates.index(dates_sorted[-1])
            latest.append(path_body_info[body][latest_i])
    else:

        for body in list(path_body_info):
            path_body_info[body].sort()
            latest.append(path_body_info[body][-1])

    return latest


def get_path_body(path):
    path_name = path_remove_extension(path)

    version_indexe = len(path_name)
    for k in range(len(path_name) - 1, 0, -1):
        if (path_name[k] in string.digits):
            version_indexe = k
        else:
            break

    return path_name[:version_indexe]
