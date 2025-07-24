# coding: utf-8

import itertools
import maya.cmds as mc
import mikan.maya.cmdx as mx

from mikan.core.logger import create_logger
from mikan.maya.core import Asset

log = create_logger()

for node in mx.ls('|*'):

    if 'gem_type' not in node or node['gem_type'].read() != Asset.type_name:
        continue
    asset = Asset(node)
    root = asset.get_template_root()
    for node in itertools.chain([root], root.descendents()):
        if not node.is_a((mx.tTransform, mx.tJoint)):
            continue
        if any(node['rp'].read()) or any(node['rpt'].read()):
            rp = node['rp'].as_vector()
            rpt = node['rpt'].as_vector()
            t = node['t'].as_vector()
            node['t'] = t + rp + rpt
            node['rp'] = (0, 0, 0)
            node['sp'] = (0, 0, 0)
            node['rpt'] = (0, 0, 0)
            node['spt'] = (0, 0, 0)

            for ch in node.children():
                try:
                    ch['t'] = ch['t'].as_vector() - rp - rpt
                except:
                    pass

            log.info('fixed pivot of {}'.format(node))

    mc.dgdirty(a=1)
    log.info('pivots fixed for asset {}'.format(asset.name))
