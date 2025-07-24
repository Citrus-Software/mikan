# coding: utf-8

import os
import string
import subprocess
from ast import literal_eval
from xml.dom.minidom import Document

__all__ = [
    'XmlDB',
    'path_to_windows_syntaxe', 'path_open_in_explorer', 'path_open_in_vsCode'
]

r'''
from mikan.core.utils.ui_auto.xml_db import *
reload(mikan.core.utils.ui_auto.xml_db)

file = '//tdp_server/projets/tdproject/tdp_maya/rig/transfer_to_model/transfer_to_model_coefs.xml'
file = '//tdp_server/projets/tdproject/tdp_maya/rig/\preview/preview_anim_crc_v5.xml'
xml = XmlDB()
xml.create_from_file(file, latest=True)
xml.dict['toto'] = 'tata'
xml.to_file(file, clearOldVar=True, incr=True)
'''


class XmlDB(object):
    r'''
    #_________________________________________________________________CREATE
    create_from_file
    #_________________________________________________________________OUT
    to_file
    #_________________________________________________________________UTILS
    _update_instance_with_dict
    _xml_to_dict
    _dict_to_xml
    utils_dictionaryToMayaObjInfo
    '''

    def __init__(self):
        self.type = 'xml_manager'
        self.objs = None
        self.varNames = []
        self.dict = {}
        self.values = []
        self.suffixIncr = '_v'

        self.classeNames = []
        self.classeNameto_fileName = {}
        self.classeNameToExecutableImport = {}
        self.classeNameToExecutableBuild = {}
        # self.refreshClassesInfo()

    # _________________________________________________________________CREATE
    def create_from_file(self, file, latest=1):

        self.dict = self._xml_to_dict(file, latest, self.suffixIncr)

        self.objs = [file]
        self._update_instance_with_dict()

        return self.dict

    # _________________________________________________________________OUT

    def to_file(self, file, clearOldVar=1, incr=0):

        # UPDATE WITH DICT
        self._update_instance_with_dict()

        # READ INFO
        dictClass = self.dict
        dictOutObj = self._xml_to_dict(file, incr, self.suffixIncr)

        if (clearOldVar):
            dictInObj = dictClass
        else:
            dictInObj = dict_merge(dictOutObj, dictClass)

        # WRITE INFO
        self._dict_to_xml(file, dictInObj, incr, self.suffixIncr)

        return 1

    # _________________________________________________________________UTILS

    def _update_instance_with_dict(self, inValue=None):
        if not (inValue == None):
            self.dict = inValue
        if not (self.dict == {}):
            self.values = [self.dict[key] for key in self.dict.keys()]

    def _xml_to_dict(self, path, latest=0, suffix=''):

        path = path_to_python_syntaxe(path)
        # ADD XML AT THE END
        if not (path[-4:len(path)] == '.xml'): path += '.xml'

        # FIND LATEST FILE
        if (latest):
            fileIndex = self._find_latest_path_index_fast(path, suffix)
            incrPath = self._insert_index_to_path(path, fileIndex, suffix)
            if (path_exists(incrPath)): path = incrPath

        # INIT
        dictValues = {}
        if (os.path.exists(path)):
            tree = ElementTree.parse(path)
            root = tree.getroot()
            for child in root:
                dict_raw = XmlDictConfig(child)
                varName = dict_raw['__name__']
                valueStr = dict_raw['value']
                value = valueStr

                try:
                    if valueStr.startswith("OrderedDict("):
                        value = eval(valueStr)
                    else:
                        value = literal_eval(valueStr)
                except:
                    value = valueStr

                dictValues[varName] = value

        return dictValues

    def _dict_to_xml(self, path, dictionary, incr=0, suffix='', historyFolder=None):

        if incr:
            latestPath = self._find_latest_path(path, suffix=suffix)
            fileIndex = self._find_latest_path_index_fast(path, suffix)
            path = self._insert_index_to_path(path, fileIndex + 1, suffix)

        # INIT
        doc = Document()
        root_node = doc.createElement("scene")
        doc.appendChild(root_node)
        # FILL WITH DICT
        for key in dictionary.keys():
            # CREATE ATTR
            object_node = doc.createElement("object")
            root_node.appendChild(object_node)
            object_node.setAttribute("__name__", key)
            # FILL ATTR
            value = dictionary[key]
            if (is_string(value)): value = ('\'' + value + '\'')
            valueStr = str(value)
            object_node.setAttribute("value", valueStr)

        # WRITE

        # CREATE PATH
        path_splits = path.split('/')
        for i in range(6, len(path_splits) - 1):
            path_tmp = '/'.join(path_splits[0:i + 1])
            if (os.path.isdir(path_tmp) == False):
                os.mkdir(path_tmp)

        # WRITE PER LINE
        xml_txt = doc.toprettyxml()

        xml_file = open(path, "w")

        xml_file.write(xml_txt)

        # for line in xml_txt.split('\\n'):
        #    xml_file.writelines(line)

        xml_file.close()

        # CREATE HISTORY FOLDER AND FILL IT
        if (incr):
            if not (latestPath == ''):

                fileName = latestPath.split('/')[-1]
                if (historyFolder):
                    os.rename(latestPath, historyFolder + '/' + fileName)
                else:
                    latestPathSplit = latestPath.split('/')[0:len(latestPath) - 2]
                    parentFolder = '/'.join(latestPathSplit[0:len(latestPathSplit) - 1])
                    historyFolder = parentFolder + '/history'

                    if not (os.path.exists(historyFolder)):
                        os.mkdir(historyFolder)
                    os.rename(latestPath, historyFolder + '/' + fileName)

        return 1

    def _get_path_to_incr(self, path, suffix=''):
        pathBody = path_remove_extension(path)

        pathBodyNbr = ''
        for i in range(len(pathBody) - 1, 0, -1):
            if (pathBody[i] in string.digits):
                pathBodyNbr += pathBody[i]
            else:
                break

        pathBodyStr = pathBody[0:len(pathBody) - len(pathBodyNbr)]

        pathToIncr = ''
        if (pathBodyStr[-len(pathBodyStr):-1] == suffix):
            pathToIncr = pathBodyStr
        else:
            pathToIncr = pathBody + suffix

        return pathToIncr

    def _find_latest_path(self, path, suffix=''):
        incrMax = 999
        extention = '.' + path_get_extension(path)
        pathToIncr = self._get_path_to_incr(path, suffix)

        latestPath = ''
        for i in range(incrMax, -1, -1):
            pathTmp = pathToIncr + str(i) + extention
            if (os.path.exists(pathTmp)):
                latestPath = pathTmp
                break

        return latestPath

    def _find_latest_path_index(self, path, suffix=''):
        incrMax = 999
        extention = '.' + path_get_extension(path)
        pathToIncr = self._get_path_to_incr(path, suffix)

        index = 0
        for i in range(incrMax, -1, -1):
            if (os.path.exists(pathToIncr + str(i) + extention)):
                index = i
                break

        return index

    def _find_latest_path_index_fast(self, path, suffix=''):
        path_parent = '/'.join(path.split('/')[0:-1])
        extention = '.' + path_get_extension(path)
        pathToIncr = self._get_path_to_incr(path, suffix).split('/')[-1]

        files = []
        if (os.path.exists(path_parent)):
            files = os.listdir(path_parent)

        number_max = -1
        last_file = None
        for file in files:
            if (pathToIncr in file):
                number = int(file.split(pathToIncr)[1].split(extention)[0])
                if (number_max < number):
                    number_max = number
                    last_file = file

        return number_max

    def _insert_index_to_path(self, path, index, suffix=''):
        extention = '.' + path_get_extension(path)
        pathToIncr = self._get_path_to_incr(path, suffix)

        if (index == -1):
            path = '{}{}'.format(pathToIncr, extention)
        else:
            path = '{}{}{}'.format(pathToIncr, index, extention)
        return path


def path_exists(path):
    return os.path.exists(path)


def path_to_windows_syntaxe(path):
    newPath = path

    if ('/' in path):
        newPath = '\\'.join(path.split('/'))
        if ('/' == path[-1]):
            newPath += '\\'

    return newPath


def path_to_python_syntaxe(path):
    newPath = path

    if ('\\' in path):
        newPath = '/'.join(path.split('\\'))
        if ('\\' == path[-1]):
            newPath += '/'

    return path


def path_remove_file(path):
    if ('\\' == path[-1]) or ('/' == path[-1]): path = path[0:-1]

    lastElem = None
    if ('\\' in path):
        lastElem = path.split('\\')[-1]
    elif ('/' in path):
        lastElem = path.split('/')[-1]

    newPath = path
    if not (lastElem == None):
        if ('.' in lastElem):
            if ('\\' in path):
                newPath = '\\'.join(path.split('\\')[0:-1])
            elif ('/' in path):
                newPath = '/'.join(path.split('/')[0:-1])

    return newPath


def path_open_in_explorer(path):
    path = path_to_windows_syntaxe(path)
    # path = path_remove_file( path )
    if (path_exists(path)):
        subprocess.Popen(r'explorer /select, {}'.format(path))
        return 1
    else:
        print('path_open_in_explorer - path doesnt exists : {}'.format(path))
        return 0


def path_open_in_vsCode(path, line=0):
    path = path_to_windows_syntaxe(path)
    if (path_exists(path)):
        subprocess.Popen(r'C:\Program Files\Microsoft VS Code\Code.exe *-file "{}":{} -g'.format(path, line))
        return 1
    else:
        print('path_open_in_explorer - path doesnt exists : {}'.format(path))
        return 0


def dict_merge(dictA, dictB):
    dictOut = {}
    for keyA in dictA.keys():
        dictOut[keyA] = dictA[keyA]
    for keyB in dictB.keys():
        dictOut[keyB] = dictB[keyB]

    return dictOut


from six import string_types


def is_string(elem):
    if (isinstance(elem, string_types)):
        return True
    else:
        return False

        isinstance(elem, str)


from xml.etree import ElementTree


# from xml.etree import cElementTree as ElementTree

class XmlListConfig(list):
    def __init__(self, aList):
        for element in aList:
            if element:
                # treat like dict
                if len(element) == 1 or element[0].tag != element[1].tag:
                    self.append(XmlDictConfig(element))
                # treat like list
                elif element[0].tag == element[1].tag:
                    self.append(XmlListConfig(element))
            elif element.text:
                text = element.text.strip()
                if text:
                    self.append(text)


class XmlDictConfig(dict):
    r'''
    Example usage:

    >>> tree = ElementTree.parse('your_file.xml')
    >>> root = tree.getroot()
    >>> xmldict = XmlDictConfig(root)

    Or, if you want to use an XML string:

    >>> root = ElementTree.XML(xml_string)
    >>> xmldict = XmlDictConfig(root)

    And then use xmldict for what it is... a dict.
    '''

    def __init__(self, parent_element):
        if parent_element.items():
            self.update(dict(parent_element.items()))
        for element in parent_element:
            if element:
                # treat like dict - we assume that if the first two tags
                # in a series are different, then they are all different.
                if len(element) == 1 or element[0].tag != element[1].tag:
                    aDict = XmlDictConfig(element)
                # treat like list - we assume that if the first two tags
                # in a series are the same, then the rest are the same.
                else:
                    # here, we put the list in dictionary; the key is the
                    # tag name the list elements all share in common, and
                    # the value is the list itself 
                    aDict = {element[0].tag: XmlListConfig(element)}
                # if the tag has attributes, add those to the dict
                if element.items():
                    aDict.update(dict(element.items()))
                self.update({element.tag: aDict})
            # this assumes that if you've got an attribute in a tag,
            # you won't be having any text. This may or may not be a 
            # good idea -- time will tell. It works for the way we are
            # currently doing XML configuration files...
            elif element.items():
                self.update({element.tag: dict(element.items())})
            # finally, if there are no child tags and no attributes, extract
            # the text
            else:
                self.update({element.tag: element.text})


def path_remove_extension(path):
    path_split = path.split('.')
    if (0 < len(path_split)) and not ('\\' in path_split[-1]) and not ('//' in path_split[-1]):
        pathBody = '.'.join(path_split[0:-1])
    else:
        pathBody = path

    return pathBody


def path_get_extension(path):
    path_split = path.split('.')
    extension = ''
    if (0 < len(path_split)) and not ('\\' in path_split[-1]) and not ('//' in path_split[-1]):
        extension = path_split[-1]

    return extension
