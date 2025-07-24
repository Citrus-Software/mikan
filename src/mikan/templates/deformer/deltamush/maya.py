# coding: utf-8

from six.moves import range

from mikan.maya.core.deformer import om, oma, mc
from mikan.maya import cmdx as mx

import mikan.maya.core as mk
from mikan.core import re_is_int, create_logger

log = create_logger()


class Deformer(mk.Deformer):
    node_class = mx.tDeltaMush

    def read(self):

        self.data['iterations'] = self.node['smoothingIterations'].read()
        self.data['smooth_step'] = self.node['smoothingStep'].read()
        self.data['displacement'] = self.node['displacement'].read()
        self.data['maps'] = {}

        # update membership
        cp_fn = self.get_members()

        if not cp_fn.isComplete:
            mmap = self.data.get('membership')
            if mmap:
                if sum(mmap.weights) != cp_fn.elementCount:
                    self.log_error('membership map mismatch weights')
                    return
            else:
                mmap = self.get_membership()
                if not mmap and sum(mmap.weights) != cp_fn.elementCount:
                    self.log_error('membership map mismatch weights')
                    return
                else:
                    self.data['membership'] = mmap

        # base weights
        fn = oma.MFnGeometryFilter(self.node.object())
        oid = int(fn.indexForOutputShape(self.geometry.object()))
        weights_plug = self.node['weightList'][oid]['weights']

        count = self.get_size()
        weights = [1.0] * count
        for i in weights_plug.array_indices:
            weights[i] = weights_plug[i].read()

        if cp_fn.isComplete:
            wmap = weights
        else:
            wmap = [float(w) for w in mmap.weights]
            for i, v in enumerate(mmap.weights):
                if v:
                    wmap[i] = weights[i]

        if any(map(lambda w: w != 1, weights)):
            self.data['maps'][0] = mk.WeightMap(wmap)

    def build(self):
        # check data
        if not self.transform:
            raise mk.DeformerError('no transform to hook')

        # get shape
        if not self.geometry:
            self.find_geometry()

        # build rig
        self.node = None
        if self.node:
            pass
        else:
            io = self.geometry['io'].read()
            self.geometry['io'] = False
            dfm = mc.deformer(str(self.geometry), typ='deltaMush')
            self.node = mx.encode(dfm[0])
            # self.transform.wm >> self.node.geomMatrix[0]
            self.geometry['io'] = io

            name = 'deltamush_{}_{}'.format('_'.join(self.id.split('.')[1:]), '_'.join(self.transform.name().split('_')[1:]))
            self.node.rename(name)

        self.node['smoothingIterations'] = self.data['iterations']
        self.node['smoothingStep'] = self.data['smooth_step']
        self.node['displacement'] = self.data['displacement']

        # update i/o
        self.reorder()

        # update weights
        self.update()

    def write(self):
        if 'maps' not in self.data or 0 not in self.data['maps']:
            return

        oid = self.node.indexForOutputShape(self.geometry)

        p = om.MPlug()
        sl = om.MSelectionList()
        sl.add('{}.weightList[{}].weights'.format(self.node, oid))
        sl.getPlug(0, p)

        weights = self.data['maps'][0]

        # TODO: optimiser sur la maps de membership ?
        for i in range(len(weights)):
            p.elementByLogicalIndex(i).setFloat(weights[i])

    @staticmethod
    def hook(dfm, xfo, hook):

        if hook == 'enable' or hook == 'envelope':
            return dfm.envelope

        elif hook == 'iterations':
            return dfm.smoothingIterations
        elif hook == 'smooth_step':
            return dfm.smoothingStep
        elif hook == 'displacement':
            return dfm.displacement
