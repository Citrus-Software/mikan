# coding: utf-8
import maya.cmds as mc
import mikan.maya.cmdx as mx

from mikan.maya.core.deformer import Deformer

# build hook list
hooks = []

nodes = []
for node in mc.ls(sl=True):
    if '.' not in node:
        node = mx.encode(node)
        for tag in ('root', 'infs', 'poses', None):
            inf_id = Deformer.get_node_id(node, find=tag)
            if inf_id:
                nodes.append(inf_id.split()[0])
                break

for vtx in [vtx for vtx in mc.ls(sl=True, fl=1) if '.vtx' in vtx]:
    geo = vtx.split('.')[0]

    # find skin
    skin = mc.ls(mc.listHistory(str(geo)), type='skinCluster')
    if not skin:
        raise RuntimeError('no valid skin source')
    skin = skin[0]

    # weights
    weights = zip(
        mc.skinPercent(skin, vtx, q=1, v=1),
        mc.skinCluster(skin, query=True, inf=True)
    )

    for v, inf in weights:
        if not v:
            continue

        found = False
        for hook in hooks:
            if hook[1] == inf:
                hook[0] += v
                found = True
                break
        if not found:
            hooks.append([v, inf])

for i in range(2):
    # normalize
    s = 0
    for hook in hooks:
        s += hook[0]

    for hook in hooks:
        hook[0] /= s

    # prune
    hooks = [[round(v, 3), inf] for v, inf in hooks if v > 0.05]

# replace ids
for hook in hooks:
    inf = hook[1]

    inf_id = Deformer.get_node_id(mx.encode(inf), find='skin')
    if inf_id:
        hook[1] = inf_id.split()[0]

# build cmd
weights = []
cmd = 'hook:\n'

cmd += '  targets:\n'
for hook in hooks:
    cmd += '    - {}\n'.format(hook[1])
    weights.append(hook[0])

if len(nodes) == 1:
    cmd += '  node: {}\n'.format(nodes[0])
elif nodes:
    cmd += '  nodes:\n'
    for node in nodes:
        cmd += '    - {}\n'.format(node)

cmd += '  weights: {}\n'.format(weights)

print(cmd)
