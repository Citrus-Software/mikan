# coding: utf-8

from mikan.maya.core.deformer import mc
from mikan.maya import cmdx as mx

import mikan.maya.core as mk
from mikan.core import create_logger

log = create_logger()


class Deformer(mk.Deformer):
    node_class = mx.tPolySmoothFace

    def read(self):
        self.data['level'] = self.node['divisions'].read()

    def build(self):
        # check data
        if not self.transform:
            raise mk.DeformerError('no transform to hook')

        # get shape
        if not self.geometry:
            self.find_geometry()

        # build
        smooth = mc.polySmooth(str(self.geometry))
        self.node = mx.encode(smooth[0])
        self.node['divisions'] = self.data['level']
        self.node['keepBorders'] = False
        self.node['smoothUVs'] = True

        # update i/o
        self.reorder()
