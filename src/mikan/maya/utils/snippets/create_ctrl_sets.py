# coding: utf-8

import mikan.maya.cmdx as mx
import mikan.maya as mk

assets = mk.Asset.get_assets()
asset = assets[0]

grp_all = mk.Nodes.get_id('::group')
grp_all = mk.Group(grp_all)

ctrl_all = list(grp_all.get_all_nodes())
ctrl_all = mk.reorder_vdag_set(ctrl_all)

sets = []
for grp in grp_all.get_children():
    ctrls = list(grp.get_all_nodes())
    ctrls = mk.reorder_vdag_set(ctrls)
    if not ctrls:
        continue
    s = mx.create_node(mx.tObjectSet, name='ctrl_{}'.format(grp.name))
    for c in ctrls:
        s.add(c)
    sets.append(s)

if sets or ctrl_all:
    set_all = mx.create_node(mx.tObjectSet, name='ctrl_all')
    for c in ctrl_all:
        set_all.add(c)
    for s in sets:
        set_all.add(s)
