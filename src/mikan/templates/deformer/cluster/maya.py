# coding: utf-8

from six import string_types

from mikan.maya.core.deformer import om, oma, mc
import mikan.maya.cmdx as mx

import mikan.maya.core as mk
from mikan.maya.core.deformer import WeightMapInterface
from mikan.maya.lib.connect import connect_expr
from mikan.core.logger import create_logger, timed_code

log = create_logger()


class Deformer(mk.Deformer):
    node_class = (mx.tCluster, mx.tSoftMod)

    def __repr__(self):
        s = 'Deformer(\'{}\')'.format(self.deformer)
        if self.transform:
            node_name = Deformer.get_unique_name(self.transform, self.root)
            if self.id:
                s = 'Deformer(\'{}\', id=\'{}\', transform=\'{}\')'.format(self.deformer, self.id, node_name)
            else:
                s = 'Deformer(\'{}\', transform=\'{}\')'.format(self.deformer, node_name)

        h = self.data.get('handle')
        if h:
            s = s[:-1]
            s += ', handle=\'{}\')'.format(h)

        return s

    def read(self):

        n = self.get_size()
        weights = [1.0] * n

        fn = oma.MFnGeometryFilter(self.node.object())
        oid = int(fn.indexForOutputShape(self.geometry.object()))

        wplug = self.node['wl'][oid]['w']
        for i in wplug.array_indices:
            if i >= n:
                break
            weights[i] = round(wplug[i].read(), self.decimals)

        members_fn = self.get_members()

        if not members_fn.isComplete:
            mmap = self.data.get('membership')
            if mmap:
                if sum(mmap.weights) != members_fn.elementCount:
                    self.log_error('membership map mismatch weights')
                    return
            else:
                mmap = self.get_membership()
                if not mmap and sum(mmap.weights) != members_fn.elementCount:
                    self.log_error('membership map mismatch weights')
                    return
                else:
                    self.data['membership'] = mmap

            for i, v in enumerate(mmap.weights):
                if not v:
                    weights[i] = 0.0

        self.data['maps'][0] = mk.WeightMap(weights)

        self.data['handle'] = self.get_node_id(Deformer.get_handle(self.node))
        bind_pose = self.node['bindPreMatrix'].input(plug=True)
        if bind_pose:
            bp_node = bind_pose.node()
            if 'parent' in bind_pose.name(long=True):
                bp_node = bp_node.parent()
            if bp_node and bp_node != self.data['handle']:
                self.data['bind_pose'] = self.get_node_id(bp_node)

        if self.node.is_a(mx.tSoftMod):
            self.data['soft'] = True

            self.data['falloff_center'] = [round(x, 3) for x in self.node['falloffCenter'].read()]
            r = self.node['falloffRadius'].read()
            if 'falloff_radius_in' in self.node:
                self.node['falloff_radius_in'].read()
            self.data['falloff_radius'] = round(r, 3)
            self.data['falloff_mode'] = self.node['falloffMode'].read()

            center = self.node['falloffCenter'].input(type=mx.tDecomposeMatrix)
            if center:
                xfo = center['imat'].input()
                if xfo:
                    center_id = mk.Deformer.get_node_id(xfo)
                    if center_id:
                        self.data['falloff_pivot'] = center_id

            curve = {}
            d = {0: 'step', 1: 'linear', 2: 'flat', 3: 'spline'}
            for i in self.node['falloffCurve'].array_indices:
                key = {}
                curve[round(self.node['falloffCurve'][i]['fcp'].read(), 2)] = key
                key['v'] = round(self.node['falloffCurve'][i]['fcfv'].read(), 2)
                key['tan'] = d[self.node['falloffCurve'][i]['fci'].read()]
            self.data['falloff_curve'] = curve

    def build(self, data=None):
        # check data
        if not self.transform:
            raise mk.DeformerError('geometry missing')
        if not self.data['handle']:
            raise mk.DeformerError('handle missing')

        # get handle
        handle = self.data['handle']
        try:
            if isinstance(handle, string_types):
                handle = self.get_node(handle)
        except:
            raise mk.DeformerError('skipped: handle does not exist')

        root = self.data.get('bind_pose')
        if root and isinstance(root, string_types):
            root = self.get_node(root)

        # get shape
        if not self.geometry:
            self.find_geometry()

        # intermediate check
        io = self.geometry['io'].read()
        if io:
            self.geometry['io'] = False

        vis = self.geometry['v'].read()
        if not vis:
            self.geometry['v'] = True

        # build rig
        node_class = 'cluster'
        if self.data.get('soft'):
            node_class = 'softMod'

        # check if geometry is already connected to handle
        for node in handle.outputs(type=node_class):
            try:
                fn = oma.MFnGeometryFilter(node.object())
                fn.indexForOutputShape(self.geometry.object())
                self.node = node
            except:
                pass

        if not self.node:
            # build deformer
            self.node = mc.deformer(str(self.geometry), typ=node_class)
            self.node = mx.encode(self.node[0])

            # geometry matrix
            xfo_plug = self.transform['wm'][0]
            if self.data['local']:
                xfo_plug = self.transform['m']

            if self.data['relative']:
                xfo_plug >> self.node['geomMatrix'][0]
            else:
                self.node['geomMatrix'][0] = xfo_plug.as_matrix()

            # connect handle
            if not root:
                handle['pm'][0] >> self.node['preMatrix']
                handle['pim'][0] >> self.node['bindPreMatrix']
                handle['m'] >> self.node['weightedMatrix']
            else:
                root['wm'][0] >> self.node['preMatrix']
                root['wim'][0] >> self.node['bindPreMatrix']

                with mx.DGModifier() as md:
                    mmx = md.createNode(mx.tMultMatrix, name='_mmx#')
                handle['wm'][0] >> mmx['i'][0]
                root['wim'][0] >> mmx['i'][1]
                mmx['o'] >> self.node['weightedMatrix']

            handle['wm'][0] >> self.node['matrix']

            # deform type
            name = '_'.join(handle.name().split('_')[1:])
            if not name:
                name = handle.name()

            prefix = 'clst'
            if self.data.get('soft'):
                prefix = 'soft'
            self.node.rename('{}_{}'.format(prefix, name))
            dfm_set = self.node.output(type=mx.tObjectSet)
            if dfm_set:
                dfm_set.rename('clst_{}Set'.format(handle))

            # soft mod
            if self.data.get('soft'):
                self.node['falloffMode'] = self.data['falloff_mode']
                self.node['falloffRadius'] = self.data['falloff_radius']
                self.node['falloffCenter'] = self.data['falloff_center']

                self.node['falloffAroundSelection'] = False

                pivot = self.data['falloff_pivot']
                if self.data['falloff_pivot'] and isinstance(self.data['falloff_pivot'], string_types):
                    pivot = self.get_node(self.data['falloff_pivot'])

                if isinstance(pivot, mx.Node):
                    with mx.DGModifier() as md:
                        dmx = md.create_node(mx.tDecomposeMatrix, name='_dmx')
                    pivot['wm'][0] >> dmx['imat']
                    dmx['outputTranslate'] >> self.node['falloffCenter']

                if 'falloff_radius' not in handle:
                    handle.add_attr(mx.Double('falloff_radius', keyable=True, min=0))
                handle['falloff_radius'] = self.data['falloff_radius']

                if isinstance(pivot, mx.Node):
                    connect_expr(
                        'r = k*(x+y+z)/3',
                        r=self.node['falloffRadius'],
                        k=handle['falloff_radius'],
                        x=dmx['outputScaleX'],
                        y=dmx['outputScaleY'],
                        z=dmx['outputScaleZ']
                    )
                else:
                    handle['falloff_radius'] >> self.node['falloffRadius']

                curve = self.data['falloff_curve']
                if not curve:
                    curve = {}
                d = {'step': 0, 'linear': 1, 'flat': 2, 'spline': 3}
                for i, key in enumerate(curve):
                    self.node['falloffCurve'][i]['fcp'] = key
                    self.node['falloffCurve'][i]['fcfv'] = curve[key]['v']
                    self.node['falloffCurve'][i]['fci'] = d[curve[key]['tan']]

        # intermediate check
        if io:
            self.geometry['io'] = True

        if not vis:
            self.geometry['v'] = False

        # update i/o
        self.reorder()

        # update weights
        with timed_code('writing {}'.format(self.node), level='debug'):
            self.update()

    def write(self):
        n = self.get_size()

        if 'maps' not in self.data or 0 not in self.data['maps']:
            return

        wmap = self.data['maps'][0].weights
        if len(wmap) != n:
            mk.DeformerError('cannot write weightmap: bad length')

        io = self.geometry['io'].read()
        if io:
            self.geometry['io'] = False
        fn = oma.MFnGeometryFilter(self.node.object())
        i = int(fn.indexForOutputShape(self.geometry.object()))
        if io:
            self.geometry['io'] = True

        wplug = self.node['wl'][i]['w']

        members_fn = self.get_members()
        if members_fn.isComplete:
            for i, w in enumerate(wmap):
                if w == 1.0:
                    if wplug[i].read() != 1.0:
                        wplug[i] = w
                else:
                    wplug[i] = w
        else:
            mmap = self.data.get('membership')
            if not mmap:
                mmap = self.get_membership()
            else:
                mmap = mmap.weights

            for i, m in enumerate(mmap):
                if m:
                    w = wmap[i]
                    if w == 1.0:
                        if wplug[i].read() != 1.0:
                            wplug[i] = w
                    else:
                        wplug[i] = w

    @staticmethod
    def get_handle(dfm):
        return dfm['matrix'].input()

    def get_weightmaps(self):

        maps = []

        if 0 in self.data['maps']:
            data = {'key': 0, 'name': 'cluster'}
            maps.append(WeightMapInterface(self.data['maps'][0], **data))

        return maps

    def set_weightmaps(self, maps):

        for wi in maps:
            if wi.data.get('key') == 0:
                self.data['maps'][0] = wi.weightmap.copy()

    @staticmethod
    def hook(dfm, xfo, hook):

        if hook == 'enable' or hook == 'envelope':
            return dfm['envelope']

        if hook in ('radius', 'falloff_radius'):
            handle = Deformer.get_handle(dfm)

            if dfm.is_a(mx.tSoftMod):
                if handle and 'falloff_radius' in handle:
                    return handle['falloff_radius']
                else:
                    return dfm['falloffRadius']
            else:
                raise mk.DeformerError('cluster does not have radius attribute')
