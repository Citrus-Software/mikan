# coding: utf-8

import os
import maya.cmds as mc
from mikan.maya import cmdx as mx
import mikan.maya as mk

# verification du plugin d'export
try:
    mc.loadPlugin('AbcExport', quiet=True)
except:
    raise RuntimeError('cannot load AbcExport plugin!')

# export selection
_export_sel = mc.ls(sl=1, et='transform', long=True)

# look for export objectset
for _export_set in ('export', 'blueprint'):
    if mc.objExists(_export_set) and mc.nodeType(_export_set) == 'objectSet':
        _export_sel = mc.ls(mc.sets(_export_set, q=1), long=True)
        break

# ask confirmation
result = mc.confirmDialog(
    title='Warning',
    message='This operation is destructive and cannot be undone.\nIt is recommended to save your scene before continuing.\n\nDo you want to proceed?',
    button=['OK', 'Cancel'],
    defaultButton='OK',
    cancelButton='Cancel',
    dismissString='Cancel',
    icon='warning'
)

if result != 'OK':
    raise RuntimeError('user cancelled')

# change filename
_scene = mc.file(q=1, sn=1)
if _scene:
    _new_scene, _, _ext = str(_scene).rpartition('.')
    _new_scene = _new_scene + '.export.' + _ext
    mc.file(rename=_new_scene)

# import all references
mk.import_references()

# cleanup rig
for node in mx.ls(_export_sel):
    if 'gem_type' in node and node['gem_type'] == mk.Asset.type_name:
        asset = mk.Asset(node)
        asset.init_cleanup(remove_constraints=True)

# file selector
dir = None
filename = 'export.abc'

_scene = mc.file(q=1, sn=1)
if _scene:
    _scene = os.path.realpath(_scene)
    dir = os.path.split(_scene)[0]
    filename = os.path.split(_scene)[1].split('.')[0] + '.export.abc'
if not dir:
    dir = os.path.realpath(mc.workspace(q=1, rd=1))

if dir:
    filename = dir + os.path.sep + filename

path = mc.fileDialog2(
    dialogStyle=1,
    caption='Save abc blueprint',
    startingDirectory=filename,
    fileMode=0,  # save
    okCaption='Export',
    fileFilter='Alembic (*.abc)',
    selectFileFilter='Alembic (*.abc)',
)

if path:
    path = path[0]
else:
    raise RuntimeError('invalid path')

cmd = '-attr notes -attrPrefix gem_ -noNormals -uvWrite -writeVisibility -autoSubd -dataFormat ogawa'
for _root in _export_sel:
    cmd += ' -root {}'.format(_root)
cmd += ' -file ' + path.replace('\\', '/')

mc.AbcExport(j=cmd)
