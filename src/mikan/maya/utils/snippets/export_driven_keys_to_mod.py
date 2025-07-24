# coding: utf-8

from six import iteritems

import maya.cmds as mc
import mikan.maya.cmdx as mx

from mikan.core.utils import ordered_dump
import mikan.maya as mk


def plug_to_id(plug_name):
    if plug_name == 'v':
        return 'vis'
    if len(plug_name) == 2 and plug_name[0] in 'srt' and plug_name[1] in 'xyz':
        return '.'.join(plug_name)
    return str(plug_name)


for node in mx.ls(sl=True):

    for driven, anms in iteritems(mk.find_anim_curve(node, plugs=True)):
        try:
            driven_id = mk.Nodes.get_node_id(driven.node())
        except:
            driven_id = str(driven.node()) + '->xfo'
        driven_id = driven_id + '@' + plug_to_id(driven.name(long=False))

        # check scale
        do_scale = False
        for anm in anms:
            if "@s." in driven_id and not anm.input():
                num_keys = mc.keyframe(str(anm), query=True, keyframeCount=True)
                if num_keys == 1:
                    do_scale = True

        # driver loop
        for anm in anms:
            num_keys = mc.keyframe(str(anm), query=True, keyframeCount=True)

            data = {}

            driver = anm.input(plug=True)
            if isinstance(driver, mx.Plug):
                if driver.node().is_a(mx.tUnitConversion):
                    driver = driver.node()['input'].input(plug=True)

                try:
                    driver_id = mk.Nodes.get_node_id(driver.node())
                except:
                    driver_id = str(driver.node()) + '->xfo'
                driver_id = driver_id + '@' + plug_to_id(driver.name(long=False))

                data['node'] = driver_id

            # fix scale driven key
            elif num_keys == 1 and do_scale:
                continue

            keys = mk.get_anim_curve_data(anm)

            if do_scale:
                for k in keys:
                    if isinstance(k, float):
                        if isinstance(keys[k], float):
                            keys[k] += 1
                        elif isinstance(keys[k], dict) and 'v' in keys[k]:
                            keys[k]['v'] += 1

            data[driven_id] = keys
            data = {'drive': data}
            print(ordered_dump(data))
