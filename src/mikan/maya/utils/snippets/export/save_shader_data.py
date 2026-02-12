# coding: utf-8

import maya.cmds as mc
import maya.api.OpenMaya as om

from pprint import pprint
from mikan.maya.lib.shaders import export_materials

from mikan.core.logger import create_logger

log = create_logger('mikan.export')

_sl = mc.ls(sl=1, et='transform')

if len(_sl) == 0:
    mc.error('no group selected!')

_n = 0

for node in _sl:
    data = export_materials(node)
    pprint(data)

    _n += len(data)

log.info('{} shaders exported!'.format(_n))
