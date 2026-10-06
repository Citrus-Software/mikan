# coding: utf-8

import maya.cmds as mc
import mikan.maya.cmdx as mx

from mikan.core.logger import create_logger
from mikan.maya.core.deformer import DeformerGroup, Deformer

log = create_logger()

sl = mx.ls(sl=True, et='transform')

src = sl[0]
dst = sl[1:]

skin = mx.list_history(src, type=mx.tSkinCluster)
if not skin:
    raise RuntimeError('no valid skin source')

# get data
grp = DeformerGroup.create(src)
Deformer.toggle_layers(src, top=True)

deformers = []
for dfm in grp.data:
    if dfm.deformer == 'skin':
        del dfm.data['maps']
        deformers.append(dfm)

# transfer skin
for geo in dst:

    for dfm in deformers:
        new_dfm = dfm.copy()
        new_dfm.update_transform(geo)
        new_dfm.bind()

        mc.copySkinWeights(ss=str(dfm.node), ds=str(new_dfm.node), sa='closestPoint', ia=['label', 'oneToOne'], noMirror=True)
        log.info('copy layer "{}" to "{}"'.format(dfm.node, new_dfm.node))
