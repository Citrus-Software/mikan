# coding: utf-8

from six import string_types

from mikan.maya.core.deformer import om, oma, mc
from mikan.maya import cmdx as mx

import mikan.maya.core as mk
from mikan.core.logger import create_logger

log = create_logger()


class Deformer(mk.Deformer):
    node_class = mx.tShrinkWrap

    def read(self):
        data = self.data

        data['target'] = Deformer.get_input_id(self.node['targetGeom'])

        data['mode'] = self.node['projection'].read()  # should be 3 (vertex normals)
        data['bidirectional'] = self.node['bidirectional'].read()
        data['closest_if_no_intersection'] = self.node['closestIfNoIntersection'].read()
        data['offset'] = self.node['offset'].read()
        data['target_offset'] = self.node['targetInflation'].read()
        data['target_subdivision'] = self.node['targetSmoothLevel'].read()

    def build(self):
        # check data
        if not self.transform:
            raise mk.DeformerError('no transform to hook')

        # get shape
        if not self.geometry:
            self.find_geometry()

        # build
        _target = self.data['target']
        if isinstance(_target, (tuple, list)):
            target_shp, target_xfo = _target
        elif isinstance(_target, string_types):
            target_shp, target_xfo = self.get_geometry_id(_target)
        else:
            raise mk.DeformerError('invalid target')

        dfm = mc.deformer(str(self.transform), type='shrinkWrap')
        self.node = mx.encode(dfm[0])

        plug_out = Deformer.get_deformer_output(target_shp, target_xfo)
        plug_out >> self.node['targetGeom']

        self.node['projection'] = 3
        self.node['bidirectional'] = self.data.get('bidirectional', False)
        self.node['closestIfNoIntersection'] = self.data.get('closest_if_no_intersection', False)
        self.node['offset'] = self.data['offset']
        self.node['targetInflation'] = self.data['target_offset']
        self.node['targetSmoothLevel'] = self.data['target_subdivision']

        # update i/o
        self.reorder()

        # update weights
        self.update()

    @staticmethod
    def hook(dfm, xfo, hook):

        if hook == 'enable' or hook == 'envelope':
            return dfm['envelope']

        elif hook == 'offset':
            return dfm['offset']
        elif hook == 'target_offset':
            return dfm['targetInflation']
