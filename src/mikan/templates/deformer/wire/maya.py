# coding: utf-8

from six import string_types

from mikan.maya.core.deformer import om, oma, mc
from mikan.maya import cmdx as mx

import mikan.maya.core as mk
from mikan.core.logger import create_logger, timed_code

log = create_logger()


class Deformer(mk.Deformer):
    node_class = mx.tWire

    def read(self):

        cv_wire, cv_base = None, None

        shp_wire = self.node['deformedWire'][0].input()
        shp_base = self.node['baseWire'][0].input()

        if shp_wire:
            cv_wire = shp_wire.parent()

        if shp_base:
            cv_base = shp_base.parent()
            prx_base, proxy = self.get_geometry_id('{}->proxy.basewire'.format(cv_base.name()), self.root)

            if not prx_base:
                with mx.DagModifier() as md:
                    prx_base = md.create_node(mx.tNurbsCurve, parent=cv_base, name='{}_proxy'.format(shp_base))
                prx_base['io'] = True
                shp_base['worldSpace'][0] >> prx_base['create']
                prx_base['worldSpace'][0] >> self.node['baseWire'][0]
                self.set_geometry_id(prx_base, 'proxy.basewire')

        if not cv_wire or not cv_base:
            raise mk.DeformerError('{} wire deformer is invalid'.format(self.node))

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

        # wire weights
        weights_plug = self.node['weightList'][0]['weights']

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

        self.data['maps'][0] = mk.WeightMap(wmap)
        self.data['dropoff'] = self.node['dropoffDistance'][0].read()
        self.data['rotate'] = self.node['rotation'].read()
        self.data['base'] = '{}->shape'.format(cv_base)
        self.data['curve'] = '{}->shape'.format(cv_wire)

    def build(self, data=None):
        # check data
        if not self.transform:
            raise mk.DeformerError('geometry missing')
        if not self.data['maps']:
            raise mk.DeformerError('weightmap missing')

        # get shape
        if not self.geometry:
            self.find_geometry()

        # build deformer
        cv_wire = self.data.get('curve')
        if isinstance(cv_wire, tuple):
            cv_wire = cv_wire[1]
        elif isinstance(cv_wire, string_types):
            _, cv_wire = self.get_geometry_id(cv_wire)

        cv_base = self.data.get('base')
        if isinstance(cv_base, tuple):
            cv_base = cv_base[1]
            # TODO: cleaner cette partie pour grapher correctement la shp de base wire donné

        if isinstance(cv_base, string_types):
            try:
                _, cv_base = self.get_geometry_id(cv_base)
            except:
                cv_base = mc.duplicate(str(cv_wire), n=cv_wire + '_base', rc=1, rr=1)
                cv_base = mx.encode(cv_base[0])

        # intermediate check
        io = self.geometry['io'].read()
        if io:
            self.geometry['io'] = False

        wire = mc.wire(str(self.geometry), w=str(cv_wire))
        self.node = mx.encode(wire[0])

        self.node['dropoffDistance'][0] = self.data.get('dropoff', 1)
        self.node['rotation'] = self.data.get('rotate', 1)

        self.node.rename('wire_{}'.format(self.get_node_id(self.geometry.parent())))
        dfm_set = self.node.output(type=mx.tObjectSet)
        if dfm_set:
            dfm_set.rename('wire_{}Set'.format(self.geometry.parent()))

        for shp in cv_base.shapes(type=mx.tNurbsCurve):
            if shp['io'].read():
                continue

            # delete auto base wire
            if cv_base:
                mx.delete(self.node['baseWire'][0].input().parent())

            # replace by data and create buffer
            with mx.DagModifier() as md:
                prx = md.create_node(mx.tNurbsCurve, parent=cv_base, name='{}_proxy'.format(shp))
            prx['io'] = True
            shp['worldSpace'][0] >> prx['create']
            prx['worldSpace'][0] >> self.node['baseWire'][0]
            break

        # intermediate check
        if io:
            self.geometry['io'] = True

        # update i/o
        self.reorder()

        # update weights
        self.update()

    def write(self):
        if 'maps' not in self.data or 0 not in self.data['maps']:
            return

        n = self.get_size()

        wm = self.data['maps'][0].weights[:]
        if len(wm) != n:
            raise mk.DeformerError('cannot write weightmap: bad length')

        mc.setAttr('{}.weightList[0].weights[0:{}]'.format(self.node, n - 1), *wm, size=len(wm))

    @staticmethod
    def hook(dfm, xfo, hook):

        if hook == 'enable' or hook == 'envelope':
            return dfm['envelope']

        elif hook == 'scale':
            return dfm['scale'][0]
        elif hook == 'rotate':
            return dfm['rotation']
