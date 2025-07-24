# coding: utf-8

from mikan.maya.core.deformer import om, oma, mc
from mikan.maya import cmdx as mx

import mikan.maya.core as mk
from mikan.core.logger import create_logger

log = create_logger()


class Deformer(mk.Deformer):
    node_class = mx.tWrap

    def read(self):
        data = self.data
        data['target'] = Deformer.get_input_id(self.node['driverPoints'][0])

    def build(self):
        # check data
        if not self.transform:
            raise mk.DeformerError('no transform to hook')

        # get shape
        if not self.geometry:
            self.find_geometry()

        # build
        target_shp = self.data['target']
        if isinstance(target_shp, (tuple, list)):
            target_shp, target_xfo = target_shp

        dfm = mc.deformer(str(self.transform), type='wrap')
        self.node = mx.encode(dfm[0])

        self.node.weightThreshold.set(0.0)
        self.node.maxDistance.set(1.0)
        self.node.exclusiveBind.set(False)
        self.node.autoWeightThreshold.set(True)
        self.node.falloffMode.set(0)

        # update i/o
        self.reorder()

        # update weights
        self.update()
