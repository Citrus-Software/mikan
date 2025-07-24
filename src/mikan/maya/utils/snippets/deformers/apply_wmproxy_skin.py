# coding: utf-8

from six import iteritems

import maya.cmds as mc
import mikan.maya.cmdx as mx

from mikan.core.ui.widgets import BusyCursor
from mikan.core.logger import create_logger, timed_code
from mikan.maya.core.deformer import Deformer, DeformerGroup, NurbsWeightMap
from mikan.maya.lib.configparser import ConfigParser

log = create_logger()

# pm.flushUndo()
sel = mx.ls(sl=1, et='transform')

nmap = None

for node in sel:
    if 'notes' not in node:
        continue
    if 'nmap' in ConfigParser(node).sections():
        nmap = node
        break
else:
    raise RuntimeError('no nmap selected')

sel.remove(nmap)

with timed_code('apply wmproxy:'):
    with BusyCursor():
        for geo in sel:
            prx = NurbsWeightMap(nmap)
            _dfm = prx.convert(geo)
            log.info('wm proxy converted to {}'.format(_dfm))

            nodes = mc.listHistory(str(geo)) or []
            nodes = mx.ls(nodes, et='skinCluster')
            if nodes:
                skin = nodes[0]

            layer = Deformer.get_current_layer(geo)
            grp = DeformerGroup.create(geo)['*->skin']
            for i, dfm in iteritems(grp):
                if dfm.node == skin:
                    log.info('skin found "{}"'.format(dfm))
                    dfm.merge(_dfm)
                    dfm.find_geometry()
                    dfm.write()

            if isinstance(layer, int):
                Deformer.toggle_layers(geo, layer=layer)
