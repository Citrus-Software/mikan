# coding: utf-8

import mikan.maya as mk
import maya.cmds as mc

for node in mc.ls(sl=1, et='transform'):
    mk.Deformer.toggle_layers(node)

    _ids = mk.Deformer.get_deformer_ids(node)

    _h = mc.listHistory(str(_ids['shape']))
    _skin = mc.ls(_h, et='skinCluster')

    _layer = 'layer.shape'
    for k in _ids:
        if k == 'shape':
            continue
        if _ids[k] == _ids['shape']:
            _layer = k

    _message = 'Now showing <hl>{}</hl> of <hl>{}</hl>'.format(_layer, node)
    if _skin:
        _message += ', editing <hl>{}</hl>'.format(_skin[0])

    mc.inViewMessage(
        amg=_message,
        pos='topCenter',
        fade=True
    )
