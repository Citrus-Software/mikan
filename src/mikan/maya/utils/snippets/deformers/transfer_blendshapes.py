# coding: utf-8

import mikan.maya.cmdx as mx
import mikan.maya.core as mk

# transfer all blendshapes from mesh to mesh
sl = mx.ls(sl=True, et='transform')
if len(sl) != 2:
    raise RuntimeError('wrong selection')

src = sl[0]
dst = sl[1]

grp = mk.DeformerGroup.create(src)
deformers = grp['*->blend']

for dfm in grp.deformers.flatten(deformers):

    c = dfm.transfer(dst)
    # if not sum(c.data['maps'][0].weights):
    #     continue
    c.build()
