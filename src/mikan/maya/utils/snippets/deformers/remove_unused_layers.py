# coding: utf-8

import maya.cmds as mc
import mikan.maya.cmdx as mx

from mikan.core.logger import create_logger
from mikan.maya.core import Deformer
from mikan.core.ui.widgets import BusyCursor

log = create_logger()


def remove_unused_influence_layer():
    with BusyCursor():
        sl = mx.ls(sl=True)

        for node in sl:
            layers = Deformer.get_layers(node)
            for layer in layers:
                shp = layers[layer]
                if shp['io'].read():
                    continue

                dfms = mx.ls(mc.listHistory(str(shp)), type='skinCluster')
                if dfms:
                    skin = dfms[0]

                    infs = mc.skinCluster(str(skin), query=True, influence=True)
                    winfs = mc.skinCluster(str(skin), query=True, weightedInfluence=True)
                    for inf in infs:
                        if inf in winfs:
                            continue
                        try:
                            mc.skinCluster(str(skin), edit=True, removeInfluence=str(inf))
                        except:
                            log.error('/!\\ failed to remove influence {}'.format(inf))
