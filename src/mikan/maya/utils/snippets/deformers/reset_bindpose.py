# coding: utf-8

import maya.cmds as mc
import mikan.maya.cmdx as mx

for geo in mc.ls(sl=1, et='transform'):
    for skin in mx.ls(mc.listHistory(geo), et='skinCluster'):
        infs = mc.skinCluster(str(skin), q=1, inf=1)
        shapes = mc.skinCluster(str(skin), q=1, g=1)

        bp = mc.listConnections(infs, d=1, s=0, t='dagPose')
        if bp:
            mc.delete(bp)

        for i in skin['matrix'].array_indices:
            inf = skin['matrix'][i].input()
            if inf is not None:
                bpm = skin['bindPreMatrix'][i]
                if bpm.input() is None:
                    mc.setAttr(bpm.path(), inf['wim'][0].as_matrix(), type='matrix')


def reset_bindpose():
    # old method
    sel = mc.ls(sl=True)
    history = mc.listHistory(sel)
    skins = mc.ls(history, et='skinCluster')
    skins = list(set(skins))

    for skin in skins:
        shapes = mc.skinCluster(skin, q=1, g=1)
        infs = mc.skinCluster(skin, q=1, inf=1)
        bp = mc.listConnections(infs, d=1, s=0, t='dagPose')
        if bp:
            mc.delete(bp)

        for shape in shapes:
            mc.skinCluster(shape, e=1, ubk=1)
            mc.select(infs, r=1)
            mc.skinCluster(shape, infs, tsb=1, ibp=1)

    mc.select(sel)
