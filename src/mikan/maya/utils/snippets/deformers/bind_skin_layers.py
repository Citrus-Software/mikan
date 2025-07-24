# coding: utf-8

import maya.cmds as mc
import mikan.maya.cmdx as mx

from mikan.core.logger import create_logger
from mikan.maya.core.deformer import Deformer

log = create_logger()

infs = []
geos = []

# get data
for node in mx.ls(sl=True):
    shape = node.shape()
    if shape and node.is_a(mx.tTransform):
        geos.append(node)
    elif node.is_a(mx.tJoint):
        infs.append(node)

if not infs or not geos:
    raise RuntimeError('invalid selection')

# build
for geo in geos:
    skin_data = {
        'deformer': 'skin',
        'transform': geo,
        'data': {
            'infs': dict(enumerate(infs))
        }
    }

    skin_dfm = Deformer(**skin_data)
    skin_dfm.build()
