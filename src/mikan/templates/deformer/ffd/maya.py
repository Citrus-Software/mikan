# coding: utf-8

from six.moves import range
from six import string_types, iteritems

from mikan.maya.core.deformer import om, oma, mc
from mikan.maya import cmdx as mx

import mikan.maya.core as mk
from mikan.core.logger import create_logger
from mikan.maya.lib.geometry import create_lattice_proxy

log = create_logger()


class Deformer(mk.Deformer):
    node_class = mx.tFfd

    def read(self):

        data = self.data

        shp = self.node['deformedLatticeMatrix'].input()
        ffb = self.node['baseLatticeMatrix'].input().parent()
        ffl = shp.parent()

        data['local'] = self.node['local'].read()
        for i, dim in enumerate('stu'):
            data['stu'][i] = shp[dim + 'Divisions'].read()
            data['local_stu'][i] = self.node['li' + dim].read()
        data['outside'] = self.node['outsideLattice'].read()
        data['falloff'] = self.node['outsideFalloffDist'].read()

        data['lattice'] = ffl.name() + '->xfo'
        data['base'] = ffb.name() + '->xfo'

        # proxies
        prx = self.get_geometry_id('{}->data.tweak'.format(ffl.name()), self.root)
        if prx[0]:
            mx.delete(prx[0])
        prx = create_lattice_proxy(ffl)
        shp = prx.shape()
        mc.parent(str(shp), str(ffl), r=1, s=1)
        mx.delete(prx)
        shp['v'] = False
        self.set_geometry_id(shp, 'data.tweak')

        prx, _prx = self.get_geometry_id('{}->data.base'.format(ffb.name()), self.root)
        if not prx:
            with mx.DagModifier() as md:
                prx = md.create_node(mx.tLocator, parent=ffb, name=ffb.name() + 'Loc')
            self.set_geometry_id(prx, 'data.base')

        if prx.is_a(mx.tLocator):
            prx['localScale'] = (0.5, 0.5, 0.5)
            prx['v'] = False

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

        for w in wmap:
            if w != 1.0:
                self.data['maps'][0] = mk.WeightMap(wmap)
                break

    def build(self, data=None):

        # check data
        if not self.transform:
            raise mk.DeformerError('geometry missing')
        if not self.data['lattice']:
            raise mk.DeformerError('lattice missing')

        # get shapes
        if not self.geometry:
            self.find_geometry()

        # get ffd data
        ffl = self.data.get('lattice')
        if isinstance(ffl, tuple):
            ffl = ffl[1]
        if isinstance(ffl, string_types):
            _, ffl = self.get_geometry_id(self.data['lattice'])

        ffb = self.data.get('base')
        if isinstance(ffb, tuple):
            ffb = ffb[1]
        if isinstance(ffb, string_types):
            _, ffb = self.get_geometry_id(self.data['base'])

        ffl_ids = self.get_deformer_ids(ffl) if ffl else {}
        for key, node in iteritems(ffl_ids):
            if 'data.' in key:
                node['v'] = False

        ffb_ids = self.get_deformer_ids(ffb) if ffb else {}
        for key, node in iteritems(ffb_ids):
            if 'data.' in key:
                node['v'] = False

        # cleanup lattice shape orig
        for shp in list(ffl.shapes(mx.tLattice)):
            if shp['io'].read():
                outputs = [node for node in shp.outputs() if not node.is_a('nodeGraphEditorInfo')]
                if not outputs:
                    mx.delete(shp)

        # intermediate check
        io = self.geometry['io'].read()
        if io:
            self.geometry['io'] = False

        # build rig
        lattice = None
        for shp in ffl.shapes(type=mx.tLattice):
            if not shp['io'].read():
                lattice = shp
                break

        if not lattice:
            with mx.DagModifier() as md:
                lattice = md.create_node(mx.tLattice, parent=ffl, name=ffl.name() + 'Shape')
            lattice['sDivisions'] = self.data['stu'][0]
            lattice['tDivisions'] = self.data['stu'][1]
            lattice['uDivisions'] = self.data['stu'][2]
            mc.reorder(str(lattice), f=1)

        base = None
        for shp in ffb.shapes(type=mx.tBaseLattice):
            base = shp
            break

        if not base:
            with mx.DagModifier() as md:
                base = md.create_node(mx.tBaseLattice, parent=ffb, name=ffb.name() + 'Shape')
            mc.reorder(str(base), f=1)

        self.node = lattice['latticeOutput'].output()
        if not self.node:
            with mx.DGModifier() as md:
                self.node = md.create_node(mx.tFfd)

        # rename
        name = '_'.join(ffl.name().split('_')[1:])
        if not name:
            name = ffl.name()
        _name = 'ffd_' + name

        while mc.ls(_name, r=1):
            # prevent renaming lattice when cleaning up namespace
            head = _name.rstrip('0123456789')
            tail = _name[len(head):]
            if not tail:
                tail = 1
            tail = int(tail) + 1
            _name = head + str(tail)

        self.node.rename(_name)

        sets = self.node.output(type=mx.tObjectSet)
        if sets:
            sets.rename('{}Set'.format(_name))

        # connect deformer
        lattice['wm'][0] >> self.node['deformedLatticeMatrix']
        lattice['latticeOutput'] >> self.node['deformedLatticePoints']
        base['wm'][0] >> self.node['baseLatticeMatrix']

        if self.data['local']:
            self.node['local'] = True
            self.node['localInfluenceS'] = self.data['local_stu'][0]
            self.node['localInfluenceT'] = self.data['local_stu'][1]
            self.node['localInfluenceU'] = self.data['local_stu'][2]
        self.node['outsideLattice'] = self.data['outside']
        self.node['outsideFalloffDist'] = self.data['falloff']

        # bind geo
        geometry = str(self.geometry)
        if 'membership' in self.data:
            ids = []
            for i, v in enumerate(self.data['membership'].weights):
                if v:
                    ids.append(i)
            mobj = self.get_components_mobject(self.geometry, ids)
            sl = om.MSelectionList()
            sl.add((self.geometry.dag_path(), mobj))
            geometry = sl.getSelectionStrings()

        mc.deformer(str(self.node), e=True, g=geometry)

        fn = oma.MFnGeometryFilter(self.geometry.object())

        geo_xfo = self.data.get('relative', False)
        if geo_xfo:
            i = int(fn.indexForOutputShape(self.geometry.object()))
            self.transform['wm'][0] >> self.node['geomMatrix'][i]

        # apply tweak shape
        if 'data.tweak' in ffl_ids:
            fn = om.MFnMesh(ffl_ids['data.tweak'].dag_path())
            pts = [mx.Vector(p) for p in fn.getPoints(mx.sWorld)]

            u = lattice['uDivisions'].read()
            t = lattice['tDivisions'].read()
            s = lattice['sDivisions'].read()

            for _u in range(u):
                for _t in range(t):
                    for _s in range(s):
                        i = ((_t + t * _u) * s) + _s
                        mc.xform('{}.pt[{}][{}][{}]'.format(lattice, _s, _t, _u), t=pts[i], ws=1)

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
            self.log_warning('weightmap error: bad length -> fixed'.format())
            if len(wm) > n:
                wm = wm[:n]
            else:
                wm = wm + [0.0] * (n - len(wm))

        fn = oma.MFnGeometryFilter(self.node.object())
        oid = int(fn.indexForOutputShape(self.geometry.object()))

        mc.setAttr('{}.weightList[{}].weights[0:{}]'.format(self.node, oid, n - 1), *wm, size=len(wm))

    @staticmethod
    def hook(ffd, xfo, hook):

        if hook == 'enable' or hook == 'envelope':
            return ffd['envelope']
