# coding: utf-8

import maya.cmds as mc
import mikan.maya.cmdx as mx

from mikan.core.logger import create_logger
from mikan.maya.core import Deformer
from mikan.core.ui.widgets import BusyCursor

log = create_logger()


def add_influence_layer():
    with BusyCursor():
        sl = mx.ls(sl=True)

        infs = []
        geos = []

        for node in sl:
            shp = node.shape()
            if shp and mc.objectType(str(shp), isAType='deformableShape'):
                geos.append(node)
            else:
                infs.append(node)

        for node in geos:
            layers = Deformer.get_layers(node)
            for layer in layers:
                shp = layers[layer]
                if shp['io'].read():
                    continue

                dfms = mx.ls(mc.listHistory(str(shp)), type='skinCluster')
                if dfms:
                    skin = dfms[0]
                    for inf in infs:
                        try:
                            mc.skinCluster(str(skin), edit=True, ai=str(inf), lockWeights=True, weight=0)
                        except:
                            log.error('/!\\ failed to add influence {}'.format(inf))
