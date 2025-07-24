# coding: utf-8
import maya.cmds as mc
import mikan.maya.cmdx as mx

joints = [
    ['j_thumb1_L', 'j_thumb2_L', 'j_thumb3_L'],
    ['j_point_meta_L', 'j_point1_L', 'j_point2_L', 'j_point3_L'],
    ['j_middle_meta_L', 'j_middle1_L', 'j_middle2_L', 'j_middle3_L'],
    ['j_ring_meta_L', 'j_ring1_L', 'j_ring2_L', 'j_ring3_L'],
    ['j_pinky_meta_L', 'j_pinky1_L', 'j_pinky2_L', 'j_pinky3_L'],
]

for js in joints:
    js = [mx.encode(j) for j in js]
    p = None

    locs = []
    tips = []
    for j in js:
        name = j.name().replace('j_', 'fix_')

        root = mx.create_node(mx.tTransform, parent=j, name='root_' + name)
        if p:
            mc.parent(str(root), str(p))
        else:
            mc.parent(str(root), w=1)

        loc = mx.create_node(mx.tTransform, parent=root, name=name.replace('_L', '_base_L'))
        locs.append(loc)
        p = loc

        if 'meta' not in name:
            shp = mx.create_node(mx.tLocator, parent=loc)
            shp['localScale'] = [0.25, 0.05, 0.05]
            shp['overrideEnabled'] = True
            shp['overrideColor'] = 14

        tip = mx.create_node(mx.tTransform, parent=loc, name=name.replace('_L', '_tip_L'))
        tips.append(tip)

        # bpm
        for bpm in (loc, tip):
            sk = str(bpm).replace('fix_', 'sk_')
            sk = mx.encode(sk)

            outputs = sk['wm'][0].outputs(plugs=True)
            for o in outputs:
                dfm = o.node()
                x = int(o.path().split('[')[-1].split(']')[0])
                bpm['wim'][0] >> dfm['bindPreMatrix'][x]

    for i in range(len(js)):
        if i < len(js) - 1:
            mc.pointConstraint(str(locs[i + 1]), str(tips[i]))

    main = mx.encode('c_fingers_L')
    for i, j in enumerate(js):
        name = j.name().replace('j_', 'c_')
        if 'meta' in name:
            continue

        ctrl = mx.encode(name)

        cmx = mx.create_node(mx.tComposeMatrix)
        mmx = mx.create_node(mx.tMultMatrix)
        cmx['outputMatrix'] >> mmx['i'][0]
        locs[i]['m'] >> mmx['i'][1]

        attr = 'bend_' + name[2:]
        if attr not in main:
            main.add_attr(mx.Double(attr, keyable=True))
        main[attr] >> cmx['inputRotateZ']

        dmx = mx.create_node(mx.tDecomposeMatrix)
        mmx['o'] >> dmx['imat']
        dmx['outputTranslate'] >> ctrl['t']
        dmx['outputRotate'] >> ctrl['r']
        dmx['outputScale'] >> ctrl['s']
