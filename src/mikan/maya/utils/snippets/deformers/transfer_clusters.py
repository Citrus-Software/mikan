# coding: utf-8

import maya.cmds as mc
import mikan.maya.cmdx as mx
import mikan.maya.core as mk

from mikan.core.logger import create_logger

_log = create_logger()

# transfer all cluster from mesh to mesh
sl = mc.ls(sl=True, flatten=True)

# sort handles and geometries
handles = []
geometries = []
components = {}

for item in sl:

    # component?
    if '.' in item:
        node, comp = item.split(".", 1)
        node = mx.encode(node)
        shp = node.shape()

        if not shp or not mc.objectType(str(shp), isAType='deformableShape'):
            continue

        if node not in components:
            components[node] = set()

        if shp.is_a(mx.tMesh):
            vertices = mc.polyListComponentConversion(item, toVertex=True)
            vertices = mc.ls(vertices, flatten=True)
            indices = [int(vtx.split('[')[-1].split(']')[0]) for vtx in vertices]
            components[node].update(indices)
        else:
            indices = [int(comp.split('[')[-1].split(']')[0])]
            components[node].update(indices)

    # cluster handle?
    node = mx.encode(item)

    _handles = [node]

    if 'gem_id' in node:
        ids = node['gem_id'].read()
        for i in ids.split(';'):
            if '::ctrls.' in i:
                sk = mk.Nodes.get_id(i.replace('::ctrls.', '::skin.'))
                if sk and sk.is_a(mx.kTransform):
                    _handles.append(sk)

    handle = None
    for _handle in _handles:
        clusters = [c for c in _handle['wm'][0].outputs() if c.is_a(mx.tCluster)]
        if clusters:
            _handle_in = clusters[0]['matrix'].input()
            if _handle_in == _handle:
                handle = _handle
                break
    if handle:
        handles.append(handle)
        continue

    # geometry
    shp = node.shape()
    if shp and mc.objectType(str(shp), isAType='deformableShape'):
        geometries.append(node)

# cleanup geo data
for geo in geometries:
    if geo in components:
        del components[geo]

for geo in components:
    geometries.append(geo)

if len(geometries) < 2:
    raise RuntimeError('not enough geometries selected')

src = geometries[0]
dst = geometries[1:]

# transfer loop
grp = mk.DeformerGroup.create(src)
try:
    clusters = grp.deformers.flatten(grp['*->cluster'])
except:
    clusters = []
    raise RuntimeError('input mesh has no cluster')

for geo in dst:
    for dfm in clusters:

        # skip if not in handle selection
        handle = mk.Deformer.get_node(dfm.data['handle'])
        if handles and handle not in handles:
            continue

        # transfer weights
        c = dfm.transfer(geo)
        n = len(c.data['maps'][0])

        # transfer components?
        dfm_orig = None

        if geo in components:
            _grp = mk.DeformerGroup.create(geo, read=False)
            try:
                _clusters = _grp.deformers.flatten(_grp['*->cluster'])
            except:
                _clusters = []

            for _dfm in _clusters:
                _dfm.read_deformer()
                _handle = _dfm.data['handle']
                if _handle == handle:
                    dfm_orig = _dfm
                    break

            # update membership
            wm = [0] * n
            if dfm_orig and 'membership' in dfm_orig.data:
                wm = dfm_orig.data['membership']
            wm_src = [1] * n
            if 'membership' in c.data:
                wm_src = c.data['membership']

            for i in components[geo]:
                wm[i] = wm_src[i]
            c.data['membership'] = mk.WeightMap(wm)

            # update weights
            wm = [0.0] * n
            if dfm_orig:
                wm = dfm_orig.data['maps'][0]
            wm_src = c.data['maps'][0]

            for i in components[geo]:
                wm[i] = wm_src[i]
            c.data['membership'] = mk.WeightMap(wm)

        # check data
        if 'membership' in c.data and not sum(c.data['membership'].weights):
            continue
        if not dfm_orig and not sum(c.data['maps'][0].weights):
            continue

        # apply
        c.build()
        _log.info('transfered cluster "{}" from "{}" to "{}"'.format(dfm.node, src, geo))
