# coding: utf-8

from functools import reduce

import maya.cmds as mc
import mikan.maya.cmdx as mx
import mikan.maya as mk

from mikan.maya.lib.geometry import create_mesh_copy

# get selection
sl = mx.ls(sl=1)

meshes = []

for node in sl:
    if not node.is_a(mx.kTransform):
        continue
    for shp in node.shapes(type=mx.tMesh):
        skin = mx.ls(mc.listHistory(str(shp)), type='skinCluster')
        if skin:
            meshes.append(node)
            break

if len(meshes) < 2:
    raise RuntimeError('not enough skinned mesh selected')

# get deformers
ids = []

dfms = []
for msh in meshes:
    grp = mk.DeformerGroup.create(msh, read=False)

    skins = []
    dfms.append(skins)

    s = set()

    for dfm in grp:
        if dfm.deformer != 'skin':
            continue
        skins.append(dfm)
        s.add(dfm.id)

    ids.append(s)

common_ids = reduce(lambda x, y: x.intersection(y), ids)
if not common_ids:
    raise RuntimeError('skin layer mismatch')

# layer loop
for i in common_ids:

    # duplicate sources
    copies = []
    for msh, skins in zip(meshes, dfms):
        skin = None
        for _skin in skins:
            if _skin.id == i:
                skin = _skin
        if not skin:
            continue
        skin.read()

        copy = create_mesh_copy(msh, shading=True)
        copies.append(copy)

        skin = skin.copy()
        skin.update_transform(copy)
        skin.bind()

    mx.cmd(mc.polyUniteSkinned, copies, ch=0)
