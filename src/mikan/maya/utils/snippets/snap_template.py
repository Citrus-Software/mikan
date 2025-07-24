# coding: utf-8

import maya.cmds as mc
import mikan.maya.cmdx as mx

import mikan.maya as mk
from mikan.core.logger import create_logger

log = create_logger()

# find pairs to snap
pairs = []
tpl_nodes = {}

for node in mx.ls(sl=1):

    # check if linked to template
    if 'gem_dag_ctrls' not in node:
        continue

    tpl_node = node['gem_dag_ctrls'].input()
    if not tpl_node:
        continue

    pairs.append((node, tpl_node))

    # check children without ctrls
    tpl = mk.Template.get_from_node(node)
    if tpl not in tpl_nodes:
        tpl_nodes[tpl] = tpl.get_template_nodes()

    _nodes = tpl_nodes[tpl]

    for ch in tpl_node.children():
        if not ch.is_a(type=(mx.tJoint, mx.tTransform)):
            continue
        if ch not in _nodes:
            continue

        if 'gem_dag_ctrls' in ch or 'gem_hook' not in ch:
            continue

        hook_id = ch['gem_hook'].read()
        hook = mk.Nodes.get_id(hook_id)
        if hook and isinstance(hook, mx.Node):
            pairs.append((hook, ch))

# snap template nodes
for node, tpl_node in pairs:

    # preserve children
    children = {}
    for ch in tpl_node.children():
        if 'gem_hook' in ch or 'gem_dag_ctrls' in ch or 'gem_dag_skin' in ch:
            children[ch] = ch['wm'][0].as_matrix()

    # snap
    wm = node['wm'][0].as_transform()
    pos = wm.translation()
    mc.move(pos[0], pos[1], pos[2], str(tpl_node), ws=1)
    log.info('snap {} to {}'.format(tpl_node, node))

    # restore children templates
    for ch in children:
        wm = children[ch]

        try:
            pim = ch['pim'][0].as_matrix()
            mc.xform(str(ch), m=wm * pim)
            ch['sh'] = [0, 0, 0]
        except:
            pass
