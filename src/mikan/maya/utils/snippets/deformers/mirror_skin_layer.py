# coding: utf-8

from six import iteritems

import maya.cmds as mc
import mikan.maya.cmdx as mx

from mikan.maya.core import Deformer
from mikan.core.ui.widgets import BusyCursor
from mikan.core.logger import create_logger


def mirror_skin_layer(reverse=False):
    with BusyCursor():

        skins = {}

        for node in mx.ls(sl=True):
            skin = None
            layers = Deformer.get_layers(node)
            for layer in layers:
                shp = layers[layer]
                if shp['io'].read():
                    continue

                dfms = mx.ls(mc.listHistory(str(shp)), type='skinCluster')
                if dfms:
                    skin = dfms[0]
                    break

            if not skin:
                continue

            node_name = node.name()
            if node_name[-2:] in ('_L', '_R'):
                node_name = node_name[:-2]

            if node_name not in skins:
                skins[node_name] = [skin]
            else:
                skins[node_name].append(skin)

        log = create_logger()
        for name, skin in iteritems(skins):
            if len(skin) == 1:
                mc.copySkinWeights(
                    ss=str(skin[0]), ds=str(skin[0]),
                    mirrorMode='YZ',
                    surfaceAssociation='closestPoint',
                    influenceAssociation=['label', 'oneToOne'],
                    mirrorInverse=reverse
                )
                log.info('mirrored {}'.format(skin[0]))

            if len(skin) == 2:
                mc.copySkinWeights(
                    ss=str(skin[0]), ds=str(skin[1]),
                    mirrorMode='YZ',
                    surfaceAssociation='closestPoint',
                    influenceAssociation=['label', 'oneToOne'],
                    mirrorInverse=reverse
                )
                log.info('mirrored {} to {}'.format(skin[0], skin[1]))
