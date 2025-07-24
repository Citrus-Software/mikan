# coding: utf-8

import maya.mel as mel
import maya.cmds as mc

result = mc.promptDialog(
    title='Flooding', message='How many times?', text='250',
    button=['OK', 'Cancel'], defaultButton='OK', cancelButton='Cancel', dismissString='Cancel'
)
if result == 'OK':
    for i in range(0, int(mc.promptDialog(query=True, text=True))):
        mel.eval("artAttrCtx -e -clear `currentCtx`;")
