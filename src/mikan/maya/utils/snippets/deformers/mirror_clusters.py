# coding: utf-8

import maya.cmds as mc
import mikan.maya.cmdx as mx
import mikan.maya.core as mk
from mikan.maya.lib.geometry import get_mesh_hash
from mikan.core.logger import create_logger

if '_mikan_sym_tables' not in globals():
    _mikan_sym_tables = dict()


def _mirror_cluster(direction=1, smart=False):
    log = create_logger()

    # suffixes
    sfx_p = '_L'
    sfx_n = '_R'
    if direction == -1:
        sfx_p = '_R'
        sfx_n = '_L'

    # mirror all cluster from mesh
    sl = mx.ls(sl=True, et='transform')
    if len(sl) != 1:
        raise RuntimeError('wrong selection')

    src = sl[0]
    dst = src
    if str(dst).endswith(sfx_p):
        dst = str(dst)[:-2] + sfx_n
        if mc.objExists(dst):
            mx.encode(dst)

    elif str(dst).endswith(sfx_n):
        dst = str(dst)[:-2] + sfx_n
        if mc.objExists(dst):
            mx.encode(dst)

    # check smart
    if smart:
        if src == dst:
            if src not in _mikan_sym_tables:
                raise RuntimeError('/!\\ {} has no mirror table generated'.format(src))
        else:
            if get_mesh_hash(src) != get_mesh_hash(dst):
                raise RuntimeError('/!\\ {} and {} have different topology'.format(src, dst))

    # find clusters
    grp = mk.DeformerGroup.create(src, read=False)

    layer = mk.Deformer.get_current_layer(src)
    mk.Deformer.toggle_layers(src, top=True)
    for dfm in grp.data:
        if dfm.deformer != 'cluster':
            continue
        dfm.read_deformer()

        h = str(mk.Deformer.get_node(dfm.data['handle']))
        if h.endswith(sfx_n):
            continue

        # flip map
        if smart:
            dfm_new = dfm.copy()
            dfm_new.node = None
            dfm_new.id = None

            maps = [dfm_new.data['maps'][0]]
            if 'membership' in dfm_new.data:
                maps.append(dfm_new.data['membership'])

            if src == dst:
                sym = _mikan_sym_tables[src]

                for wm in maps:
                    if sfx_p in h:
                        wm.flip(sym)
                    else:
                        wm.mirror(sym, direction=direction)

        else:
            if sfx_p in h:
                dfm_new = dfm.transfer(dst, flip=1)
            else:
                dfm_new = dfm.transfer(dst, mirror=1)

        # get mirror nodes
        if sfx_p in h:
            k = h.rfind(sfx_p)
            h = h[:k] + sfx_n + h[k + 2:]
            h = mx.encode(h)
            dfm_new.data['handle'] = h
        if 'bind_pose' in dfm.data:
            bp = str(mk.Deformer.get_node(dfm.data['bind_pose']))
            if sfx_p in bp:
                k = bp.rfind(sfx_p)
                bp = bp[:k] + sfx_n + bp[k + 2:]
                bp = mx.encode(bp)
            dfm_new.data['bind_pose'] = bp

        # rebuild
        dfm_new.build()
        log.info('mirrored {}'.format(dfm_new))

    mk.Deformer.toggle_layers(src, layer=layer)
