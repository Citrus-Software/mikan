# coding: utf-8

import maya.cmds as mc
import mikan.maya.cmdx as mx

from mikan.core.logger import create_logger
from mikan.maya.core.deformer import DeformerGroup, Deformer

log = create_logger()

sl = mx.ls(sl=True, et='transform')

src = sl[0]
dst = sl[1:]

skin = mx.ls(mc.listHistory(str(src)), type='skinCluster')
if not skin:
    raise RuntimeError('no valid skin source')

# get data
grp = DeformerGroup.create(src)
Deformer.toggle_layers(src, top=True)
layers = Deformer.get_layers(src)

skins = []
for dfm in grp.data:
    if dfm.deformer == 'skin':
        del dfm.data['maps']
        skins.append(dfm)

# transfer skin
for geo in dst:
    for skin in skins:
        dfm = skin.copy()
        dfm.update_transform(geo)
        dfm.bind()

    cls = Deformer.get_class('skin')
    for k in layers:
        log.info('copy layer {} from "{}" to "{}"'.format(k, src, geo))
        Deformer.toggle_layers(src, layer=k)
        Deformer.toggle_layers(geo, layer=k)
        mc.copySkinWeights(str(src), str(geo), sa='closestPoint', ia=['label', 'oneToOne'], noMirror=True)
