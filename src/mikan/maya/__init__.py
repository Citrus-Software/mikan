# coding: utf-8

import maya.OpenMaya as om1
import maya.OpenMayaAnim as oma1
import maya.api.OpenMaya as om
import maya.api.OpenMayaAnim as oma
import maya.cmds as cmds
import maya.mel as mel

from mikan.core.logger import create_logger, get_version

from mikan.maya import cmdx as cmdx
from .lib import *
from .core import *

# log version
version = get_version()
if version:
    log = create_logger()
    log.info('{} loaded'.format(version))

# load maya plugin
for _p in (
        'decomposeMatrix',
        'nearestPointOnMesh',
        'matrixNodes',
        'quatNodes',
        'AbcImport'
):
    try:
        cmds.loadPlugin(_p, quiet=True)
    except:
        pass

# maya color syntaxing in script editor
# from .ui.widgets import install_maya_syntax_highlighter
#
# install_maya_syntax_highlighter()
