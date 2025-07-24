# coding: utf-8

from six.moves import range
from six import string_types, iteritems

from mikan.maya import om, oma, om1, oma1, mel
from mikan.maya import cmds as mc
import mikan.maya.cmdx as mx

import mikan.maya.core as mk
from mikan.core import re_is_int, create_logger
from mikan.maya.core.deformer import WeightMap

log = create_logger()


class Deformer(mk.Deformer):
    node_class = mx.tBlendShape

    def read(self):

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
        weights_plug = self.node['inputTarget'][0]['baseWeights']

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

        if len(weights_plug.array_indices):
            self.data['maps'][-1] = mk.WeightMap(wmap)

        # get targets
        fn = oma.MFnGeometryFilter(self.node.object())

        _node = mx._encode1(str(self.node))
        fn1 = oma1.MFnBlendShapeDeformer(_node)
        ids = om1.MIntArray()
        fn1.weightIndexList(ids)
        ids = list(ids)
        # ids = self.node['it'][oid]['itg'].array_indices

        oid = int(fn.indexForOutputShape(self.geometry.object()))

        for t in ids:
            w = round(self.node['w'][t].read(), 4)
            if w != 0:
                self.data['weights'][t] = w

            name = self.node._fn.plugsAlias(self.node['w'][t].plug())

            tgt = None
            for i in self.node['it'][oid]['itg'][t]['iti'].array_indices:
                if i == 6000:
                    tgt = self.node['it'][oid]['itg'][t]['iti'][i]['igt'].input()

            if tgt:
                if tgt.is_a(mx.kShape):
                    tgt = tgt.parent()
                    self.data['targets'][t] = '{}->shape'.format(tgt)
                else:
                    pass
                    # YAGNI: récuperer l'attribut de connexion dans le cas d'un deformer (balaise)

                if name != tgt.name():
                    self.data['names'][t] = name

            else:
                reference = False
                if 'REFERENCE' in name:
                    reference = True
                delta = self.get_delta_weightmaps(self.node, t, reference=reference)
                if delta:
                    self.data['delta'][t] = delta
                self.data['names'][t] = name

            # target weights
            weights_plug = self.node['inputTarget'][0]['inputTargetGroup'][t]['targetWeights']
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

            if len(weights_plug.array_indices):
                self.data['maps'][t] = mk.WeightMap(wmap)

        # groups
        group_names = []
        for i in self.node['targetDirectory'].array_indices:
            if i == 0:
                continue
            bsi = self.node['targetDirectory'][i]

            name = bsi['dtn'].read()
            if name in group_names:
                while name in group_names:
                    head = name.rstrip('0123456789')
                    tail = name[len(head):]
                    if not tail:
                        tail = 1
                    tail = int(tail) + 1
                    name = head + str(tail)
                bsi['dtn'] = name
            group_names.append(name)

            data = {}
            data['name'] = name
            parent = bsi['pnid'].read()
            if parent:
                data['parent'] = parent
            data['targets'] = []
            self.data['groups'][i] = data

        for i in self.node['parentDirectory'].array_indices:
            parent = self.node['parentDirectory'][i].read()
            if parent:
                self.data['groups'][parent]['targets'].append(i)

        for i in self.data['groups']:
            if not self.data['groups'][i]['targets']:
                del self.data['groups'][i]['targets']

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
            # check rig? et connecter geommatrix au bon index
            # ajouter le deformer existant à la geo
        else:
            io = self.geometry['io'].read()
            self.geometry['io'] = False
            bs = mc.deformer(str(self.geometry), typ='blendShape')
            self.node = mx.encode(bs[0])
            # self.transform['wm'][0] >> self.node['geomMatrix'][0]
            self.geometry['io'] = io

            name = '_'.join(self.transform.name(namespace=False).split('_')[1:])
            if not name:
                name = self.transform.name(namespace=False)

            if self.id is None:
                self.set_id()
            name = 'blend_{}_{}'.format('_'.join(self.id.split('.')[1:]), name)
            self.node.rename(name)

        # asset group
        asset = mk.Nodes.current_asset
        if asset:
            self.group_node(self.node, asset)

        # build groups
        groups = self.data.get('groups', {})
        for gid in groups:
            self.node['targetDirectory'][gid]['dtn'] = groups[gid].get('name', 'group{}'.format(gid))
            self.node['targetDirectory'][gid]['pnid'] = groups[gid].get('parent', 0)

        for gid in self.node['targetDirectory'].array_indices:
            cid = []
            for _gid in groups:
                parent = groups[_gid].get('parent', 0)
                if parent == gid:
                    cid.append(-_gid)

            if gid in groups:
                targets = groups[gid].get('targets', [])
                cid += targets

                for t in targets:
                    self.node['parentDirectory'][t] = gid

            if cid:
                mc.setAttr(self.node['targetDirectory'][gid]['cid'].path(), cid, type='Int32Array')

        # build target list
        targets = {}

        for key in ('target', 'weight', 'name'):
            for t, v in iteritems(self.data.get(key + 's', {})):
                if t not in targets:
                    targets[t] = {}
                targets[t][key] = v

        # update targets
        for t, data in iteritems(targets):
            w = 0
            w_in = data.get('weight')
            if isinstance(w_in, string_types):
                w_in = mk.Nodes.get_id(w_in)
            elif isinstance(w_in, (float, int)):
                w = w_in

            name = ''

            target = None
            if 'target' in data:
                _target = data['target']
                if isinstance(_target, string_types):
                    shp, xfo = Deformer.get_geometry_id(_target)
                elif isinstance(_target, (list, tuple)) and len(_target) == 2:
                    shp, xfo = _target
                elif isinstance(_target, mx.Node):
                    if _target.is_a(mx.tTransform):
                        xfo = _target
                        shp = _target.shape()
                    else:
                        shp = _target
                        xfo = shp.parent()
                    if not shp:
                        mk.DeformerError('invalid blend target: {}'.format(_target))
                else:
                    raise mk.DeformerError('invalid blend target: {}'.format(_target))

                name = xfo.name(namespace=False)
                if shp.is_a(mx.kGeometryFilter):
                    name = shp.name(namespace=False)

                target = shp, xfo

            name = data.get('name', name)
            if name:
                name = name.split(':')[-1]

            Deformer.add_target(self.node, index=t, weight=w, target=target, alias=name)

            if isinstance(w_in, mx.Plug):
                w_in >> self.node['w'][t]

        # update i/o
        self.reorder()

        # update weights
        self.update()

    def write(self):

        # delta
        for t, delta in iteritems(self.data.get('delta', {})):
            reference = False
            if 'REFERENCE' in self.data.get('names', {}).get(t, ''):
                reference = True
            self.set_delta_weightmaps(self.node, t, delta, reference=reference)

        # target weights
        count = self.get_size()
        node = mx.encode(str(self.node))

        for t, weights in iteritems(self.data.get('maps', {})):
            if t == -1:
                continue
            if count >= len(weights):
                weights_plug = node['inputTarget'][0]['inputTargetGroup'][t]['targetWeights']
                if not weights_plug.array_indices:
                    weights_plug[0] = 1

                for i, w in enumerate(weights):
                    weights_plug[i] = w

        # envelope
        if 'maps' in self.data and -1 in self.data['maps']:
            weights = self.data['maps'][-1]

            if count >= len(weights):
                weights_plug = node['inputTarget'][0]['baseWeights']
                for i, w in enumerate(weights):
                    weights_plug[i] = w
            else:
                self.log_error('base weights map has bad length')

    @staticmethod
    def hook(bs, xfo, hook):

        if hook == 'enable' or hook == 'envelope':
            return bs['envelope']

        elif hook.startswith('target.'):
            fn = oma.MFnGeometryFilter(bs.object())
            shape = mk.Deformer._get_deformed_geo(bs, xfo)
            oid = int(fn.indexForOutputShape(shape.object()))

            hook = hook.split('.')

            if re_is_int.match(hook[1]):
                index = int(hook[1])
                return bs['it'][oid]['itg'][index]['iti'][6000]['igt']

        elif hook.startswith('weight.'):

            hook = hook.split('.')

            if re_is_int.match(hook[1]):
                return bs['w'][int(hook[1])]

            else:
                fn = oma.MFnGeometryFilter(bs.object())
                shape = mk.Deformer._get_deformed_geo(bs, xfo)
                oid = int(fn.indexForOutputShape(shape.object()))

                ids = bs['it'][oid]['itg'].array_indices

                for t in ids:
                    plug = bs['w'][t]
                    name = bs._fn.plugsAlias(plug.plug())
                    if name == hook[1]:
                        return plug

    @staticmethod
    def add_target(bs, index=None, weight=0, target=None, alias=None):

        # get next index
        if index is None:
            index = 0
            _indices = bs['w'].array_indices
            if _indices:
                index = _indices[-1] + 1

        # add empty target
        with mx.DGModifier() as md:
            md.set_attr(bs['w'][index], weight)
        mel.eval('setAttr "{}" -type "pointArray" 0;'.format(bs['it'][0]['itg'][index]['iti'][6000]['ipt'].path()))
        mel.eval('setAttr "{}" -type "componentList";'.format(bs['it'][0]['itg'][index]['iti'][6000]['ict'].path()))
        # mc.blendShape(str(bs), edit=True, resetTargetDelta=(0, index))

        # connect target
        if target is not None:
            if not isinstance(target, (tuple, list)) and len(target) != 2:
                if not isinstance(target, mx.Node):
                    target = mx.encode(str(target))
                _ids = Deformer.get_deformer_ids(target)
                target = (_ids['shape'], target)

            plug = Deformer.get_deformer_output(*target)

            with mx.DGModifier() as md:
                md.connect(plug, bs['it'][0]['itg'][index]['iti'][6000]['igt'])

        # alias?
        if alias:
            alias = str(alias)
            mc.aliasAttr(alias, bs['w'][index].path())

        return index

    @staticmethod
    def remove_target(bs, index):
        mel.eval('source "blendShapeDeleteTargetGroup";')
        mel.eval('blendShapeDeleteTargetGroup {} {};'.format(str(bs), index))

    @staticmethod
    def get_delta(bs, index):
        if not isinstance(bs, mx.Node):
            bs = mx.encode(str(bs))

        target_plug = bs['inputTarget'][0]['inputTargetGroup']
        if index not in target_plug.array_indices:
            log.error('{} has no target index {}'.format(bs, index))
            return

        item_plug = target_plug[index]['inputTargetItem']
        maps = {}
        for j in item_plug.array_indices:
            target = item_plug[j]
            geo = target['inputGeomTarget']

            if geo.input():
                log.debug('{} has no delta at target index {}'.format(bs, index))
                continue
            else:
                ipt = target['inputPointsTarget']
                ict = target['inputComponentsTarget']

                points = om.MFnPointArrayData(ipt._mplug.asMObject())
                points = [tuple(pt)[:3] for pt in points.array()]
                cpts_data = om.MFnComponentListData(ict._mplug.asMObject())
                cpts = []
                for c in range(cpts_data.length()):
                    cpts += om.MFnSingleIndexedComponent(cpts_data.get(c)).getElements()
                k = j / 1000. - 5
                maps[k] = zip(cpts, points)

        if maps:
            return maps
        log.error('{} has no delta at target index {}'.format(bs, index))
        return {}

    @staticmethod
    def get_delta_weightmaps(bs, index, reference=False):
        if not isinstance(bs, mx.Node):
            bs = mx.encode(str(bs))

        fn = oma.MFnGeometryFilter(bs.object())
        shp = mx.Node(fn.getInputGeometry()[0])
        count = Deformer.get_shape_components_size(shp)

        if reference:
            fn = om.MFnMesh(shp.object())
            points = fn.getPoints(mx.sObject)

        maps = Deformer.get_delta(bs, index)

        for k in list(maps):
            delta = maps[k]
            wm = [0.0] * count * 3

            for cp, pt in delta:
                if reference:
                    pt = mx.Vector(pt)
                    pt += mx.Vector(points[cp])
                wm[cp * 3:cp * 3 + 3] = pt

            maps[k] = WeightMap(wm)
            if not any(wm):
                del maps[k]

        if maps:
            return maps

    @staticmethod
    def set_delta(bs, index, delta, reference=False):
        if not isinstance(bs, mx.Node):
            bs = mx.encode(str(bs))

        if reference:
            fn = oma.MFnGeometryFilter(bs.object())
            shp = mx.Node(fn.getInputGeometry()[0])

            fn = om.MFnMesh(shp.object())
            ref_points = fn.getPoints(mx.sObject)

        group_plug = bs['inputTarget'][0]['inputTargetGroup'][index]

        for k in delta:
            j = int(1000 * (k + 5))
            target_plug = group_plug['inputTargetItem'][j]
            geo = target_plug['inputGeomTarget']

            if geo.input():
                log.debug('{} has input geometry at target index {}'.format(bs, index))
                continue
            else:
                cpts, points = zip(*delta[k])
                points = [om.MPoint(p) for p in points]

                if reference:
                    for i in range(len(points)):
                        points[i] -= ref_points[i]

                id_cpts_fn = om.MFnSingleIndexedComponent()
                id_cpts_data = id_cpts_fn.create(om.MFn.kMeshVertComponent)
                id_cpts_fn.addElements(cpts)

                cpts_fn = om.MFnComponentListData()
                cpts_data = cpts_fn.create()

                if not id_cpts_data.isNull():
                    cpts_fn.add(id_cpts_data)
                    target_plug['inputComponentsTarget']._mplug.setMObject(cpts_data)

                points_data = om.MFnPointArrayData().create(points)
                if not points_data.isNull():
                    target_plug['inputPointsTarget']._mplug.setMObject(points_data)

    @staticmethod
    def set_delta_weightmaps(bs, index, maps, reference=False):

        delta = {}

        for k in maps:
            cpts = []
            points = []

            wm = maps[k]
            count = int(len(wm.weights) / 3)
            for i in range(count):
                pt = wm.weights[i * 3:i * 3 + 3]
                if any(pt):
                    cpts.append(i)
                    points.append(pt)

            if cpts:
                delta[k] = zip(cpts, points)

        if delta:
            Deformer.set_delta(bs, index, delta, reference=reference)

    # groups ------------------------------------------------------------------
    @staticmethod
    def get_blend_group(bs, path, create=False):
        if not isinstance(bs, mx.Node):
            bs = mx.encode(str(bs))

        if not bs.is_a(mx.tBlendShape):
            raise RuntimeError('not a blendshape node')

        # path loop
        parent = 0
        for k in path.split('/'):
            nav = False

            # lookup for element
            for i in bs['tgdt'].array_indices[1:]:  # target directory
                dir_name = bs['tgdt'][i]['dtn'].read()
                dir_parent = bs['tgdt'][i]['pnid'].read()

                if dir_name == k and parent == dir_parent:
                    parent = i
                    nav = True
                    break

            if not nav:
                if not create:
                    return -1  # path not found
                else:
                    group_ids = list(bs['tgdt'].array_indices)

                    # create path element
                    j = max(group_ids) + 1

                    with mx.DGModifier() as md:
                        md.set_attr(bs['tgdt'][j]['dtn'], k)  # name
                        md.set_attr(bs['tgdt'][j]['pnid'], parent)  # parent index

                    # add index to parent children
                    children = mc.getAttr(bs['tgdt'][parent]['cid'].path()) or []
                    children.append(-j)
                    mc.setAttr(bs['tgdt'][parent]['cid'].path(), children, type='Int32Array')

                    # next element
                    parent = j

        return parent

    @staticmethod
    def group_target(plug, path):
        if not isinstance(plug, mx.Plug):
            plug = mx.encode(str(plug))
        if not isinstance(plug, mx.Plug):
            raise RuntimeError('not a valid plug')

        bs = plug.node()
        if not bs.is_a(mx.tBlendShape):
            raise RuntimeError('not a blendshape node')

        # get target id
        if not plug.name().startswith('weight'):
            raise RuntimeError('not a target plug')

        tid = plug.plug().logicalIndex()

        # get group id
        gid = Deformer.get_blend_group(bs, path, create=True)

        # parent target
        for i in bs['tgdt'].array_indices:
            children = mc.getAttr(bs['tgdt'][i]['cid'].path()) or []
            if tid in children:
                children.remove(tid)
                mc.setAttr(bs['tgdt'][i]['cid'].path(), children, type='Int32Array')
                break

        children = mc.getAttr(bs['tgdt'][gid]['cid'].path()) or []
        children.append(tid)
        mc.setAttr(bs['tgdt'][gid]['cid'].path(), children, type='Int32Array')

        with mx.DGModifier() as md:
            md.set_attr(bs['pndr'][tid], gid)

    @staticmethod
    def get_scene_group(path, create=False):
        m = mx.encode('shapeEditorManager')
        parent = 0

        # path loop
        for k in path.split('/'):
            nav = False

            # lookup for element
            for i in m['bsdt'].array_indices:  # blendshape directory
                dir_name = m['bsdt'][i]['bsdn'].read()
                dir_parent = m['bsdt'][i]['bspi'].read()

                if dir_name == k and parent == dir_parent:
                    parent = i
                    nav = True
                    break

            if not nav:
                if not create:
                    return -1  # path not found
                else:
                    group_ids = list(m['bsdt'].array_indices)

                    # create path element
                    j = max(group_ids) + 1

                    with mx.DGModifier() as md:
                        md.set_attr(m['bsdt'][j]['bsdn'], k)  # name
                        md.set_attr(m['bsdt'][j]['bspi'], parent)  # parent index

                    # add index to parent children
                    children = mc.getAttr(m['bsdt'][parent]['bscd'].path()) or []
                    children.append(-j)
                    mc.setAttr(m['bsdt'][parent]['bscd'].path(), children, type='Int32Array')

                    # next element
                    parent = j

        return parent

    @staticmethod
    def group_node(node, path):
        if not node.is_a(mx.tBlendShape):
            raise ValueError('invalid blendshape')
        if not isinstance(path, string_types):
            raise ValueError('invalid group')

        # find manager connection
        manager = node['midLayerParent'].output()
        if manager is None:
            raise RuntimeError('no blendShape manager found!')

        # get indices
        pi = Deformer.get_scene_group(path, True)
        with mx.DGModifier() as md:
            md.set_attr(node['midLayerParent'], pi)
        ci = node['midLayerId'].read()

        # remove child from root
        for i in manager['bsdt'].array_indices:
            children = mc.getAttr(manager['bsdt'][i]['bscd'].path()) or []
            if ci in children:
                children.remove(ci)
                mc.setAttr(manager['bsdt'][i]['bscd'].path(), children, type='Int32Array')
                break

        # add child to new group
        children = mc.getAttr(manager['bsdt'][pi]['bscd'].path()) or []
        children.append(ci)
        mc.setAttr(manager['bsdt'][pi]['bscd'].path(), children, type='Int32Array')

    # plugs utils -------------------------------------------------------------

    @staticmethod
    def get_group_target_plugs(bs, path):
        plugs = []

        gid = Deformer.get_blend_group(bs, path)
        if gid == -1:
            return plugs

        for t in bs['parentDirectory'].array_indices:
            if bs['parentDirectory'][t].read() == gid:
                plug = bs['w'][t]
                plugs.append(plug)

        return plugs

    @staticmethod
    def get_all_group_target_plugs(path):
        plugs = []

        for bs in mx.ls(et='blendShape'):
            plugs += Deformer.get_group_target_plugs(bs, path)

        return plugs

    @staticmethod
    def get_target_plug_info(plug):
        if not isinstance(plug, mx.Plug):
            raise TypeError('not a plug')

        bs = plug.node()
        if not bs.is_a(mx.tBlendShape):
            raise ValueError('not a blendShape')
        if not plug.name().startswith('weight'):
            raise ValueError('not a blendShape target plug')

        fn = oma.MFnGeometryFilter(bs.object())
        obj = fn.getOutputGeometry()[0]
        shp = mx.DagNode(obj)
        geo = shp.parent()

        data = {
            'shape': shp,
            'geometry': geo,
            'index': plug.plug().logicalIndex(),
            'alias': bs._fn.plugsAlias(plug.plug())
        }
        return data
