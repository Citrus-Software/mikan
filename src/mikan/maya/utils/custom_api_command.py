# coding: utf-8

'''
import maya.cmds as mc

nodeType       = 'customApiCommand'  
pathNodePython = r'E:\Matthieu CANTAT\code\mikan\src\mikan\maya\utils\customApiCommand.py'

print( 'BUILD TEST __________________________ LOAD NODE')
mc.loadPlugin( pathNodePython  )

mc.customApiCommand( 0 , True , 'toto' , value = 3.14 , is_true = True , name = "matthieu")
'''

import maya.api.OpenMaya as ompy
import maya.cmds as mc


def maya_useNewAPI():
    # wtf maya
    pass


class customApiCommand(ompy.MPxCommand):
    name = 'customApiCommand'
    id = ompy.MTypeId(0x00033448)

    argsType = ['float', 'bool', 'string']

    kArgsShort = ['v', 'it', 'n', 'l']
    kArgs = ['value', 'is_true', 'name', 'list']
    kArgsType = ['float', 'bool', 'string', 'list_float']

    def __init__(self):
        print('customApiCommand.__init__')
        ompy.MPxCommand.__init__(self)
        self.undoable = False

        # INPUTS
        self.edit = False
        self.query = False
        self.argsValue = []
        self.kArgsValue = {}
        self.seletedObjects = []

    def doIt(self, args):
        print('customApiCommand.doIt')

        # ARGS VALUE
        self.argsValue = []
        for i in range(0, len(self.argsType)):

            if self.argsType[i] == 'bool':
                self.argsValue.append(args.asBool(i))
            elif self.argsType[i] == 'int':
                self.argsValue.append(args.asInt(i))
            elif self.argsType[i] == 'float':
                self.argsValue.append(args.asFloat(i))
            elif self.argsType[i] == 'double':
                self.argsValue.append(args.asDouble(i))
            elif self.argsType[i] == 'string':
                self.argsValue.append(args.asString(i))

        print('argsValue', self.argsValue)

        # INIT ARG DATA BASE
        try:
            argDb = ompy.MArgDatabase(self.syntax(), args)  # create database with defined flags
        except:
            self.displayInfo("Error parsing arguments")
            raise

        # KEY ARGS VALUE
        self.kArgsValue = {}

        self.edit = argDb.isEdit
        self.query = argDb.isQuery

        for i in range(0, len(self.kArgs)):
            is_set = argDb.isFlagSet(self.kArgs[i])
            if is_set:
                if self.kArgsType[i] == 'bool':
                    self.kArgsValue[self.kArgs[i]] = argDb.flagArgumentBool(self.kArgs[i], 0)
                elif self.kArgsType[i] == 'int':
                    self.kArgsValue[self.kArgs[i]] = argDb.flagArgumentInt(self.kArgs[i], 0)
                elif self.kArgsType[i] == 'float':
                    self.kArgsValue[self.kArgs[i]] = argDb.flagArgumentFloat(self.kArgs[i], 0)
                elif self.kArgsType[i] == 'double':
                    self.kArgsValue[self.kArgs[i]] = argDb.flagArgumentDouble(self.kArgs[i], 0)
                elif self.kArgsType[i] == 'string':
                    self.kArgsValue[self.kArgs[i]] = argDb.flagArgumentString(self.kArgs[i], 0)
                elif 'list' in self.kArgsType[i]:
                    self.kArgsValue[self.kArgs[i]] = []
                    for j in range(0, argDb.numberOfFlagUses(self.kArgs[i])):
                        if 'bool' in self.kArgsType[i]:
                            self.kArgsValue[self.kArgs[i]].append(argDb.getFlagArgumentList(self.kArgs[i], j).asBool(0))
                        elif 'int' in self.kArgsType[i]:
                            self.kArgsValue[self.kArgs[i]].append(argDb.getFlagArgumentList(self.kArgs[i], j).asInt(0))
                        elif 'float' in self.kArgsType[i]:
                            self.kArgsValue[self.kArgs[i]].append(argDb.getFlagArgumentList(self.kArgs[i], j).asFloat(0))
                        elif 'double' in self.kArgsType[i]:
                            self.kArgsValue[self.kArgs[i]].append(argDb.getFlagArgumentList(self.kArgs[i], j).asDouble(0))
                        elif 'string' in self.kArgsType[i]:
                            self.kArgsValue[self.kArgs[i]].append(argDb.getFlagArgumentList(self.kArgs[i], j).asString(0))

        # SELECTION
        self.seletedObjects = []
        lst = argDb.getObjectList()
        for i in range(0, lst.length()):
            self.seletedObjects.append(lst.getDependNode(i))

        # DO
        return_value = self.redoIt()

        # RETURN
        return return_value

    def undoIt(self):
        mc.delete(self.created_node)
        return 1

    def redoIt(self):
        self.created_node = mc.createNode('transform', n=self.kArgsValue['name'])
        return self.created_node

    @classmethod
    def creator(cls):
        return cls()

    @classmethod
    def createSyntax(cls):
        Syntax = ompy.MSyntax()
        Syntax.enableQuery = True
        Syntax.enableEdit = True

        for i in range(0, len(cls.argsType)):
            if 'bool' in cls.argsType[i]:
                Syntax.addArg(Syntax.kBoolean)
            elif 'int' in cls.argsType[i]:
                Syntax.addArg(Syntax.kInt)
            elif 'float' in cls.argsType[i]:
                Syntax.addArg(Syntax.kDouble)
            elif 'double' in cls.argsType[i]:
                Syntax.addArg(Syntax.kDouble)
            elif 'string' in cls.argsType[i]:
                Syntax.addArg(Syntax.kString)

        for i in range(0, len(cls.kArgsType)):
            if 'bool' in cls.kArgsType[i]:
                Syntax.addFlag(cls.kArgsShort[i], cls.kArgs[i], Syntax.kBoolean)
            elif 'int' in cls.kArgsType[i]:
                Syntax.addFlag(cls.kArgsShort[i], cls.kArgs[i], Syntax.kInt)
            elif 'float' in cls.kArgsType[i]:
                Syntax.addFlag(cls.kArgsShort[i], cls.kArgs[i], Syntax.kDouble)
            elif 'double' in cls.kArgsType[i]:
                Syntax.addFlag(cls.kArgsShort[i], cls.kArgs[i], Syntax.kDouble)
            elif 'string' in cls.kArgsType[i]:
                Syntax.addFlag(cls.kArgsShort[i], cls.kArgs[i], Syntax.kString)

        for i in range(0, len(cls.kArgs)):
            if 'list' in cls.kArgs[i]:
                Syntax.makeFlagMultiUse(cls.kArgs[i])

        return Syntax


def initializePlugin(obj):
    plugin = ompy.MFnPlugin(obj)
    plugin.registerCommand(customApiCommand.name, customApiCommand.creator, customApiCommand.createSyntax)


def uninitializePlugin(obj):
    plugin = ompy.MFnPlugin(obj)

    try:
        plugin.deregisterCommand(customApiCommand.name)
    except:
        raise Exception('Failed to unregister cmd: {0}'.format(customApiCommand.name))
