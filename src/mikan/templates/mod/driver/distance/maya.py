# coding: utf-8

from six import iteritems

from mikan.maya import cmds as mc
import mikan.maya.cmdx as mx

import mikan.maya.core as mk
from mikan.core import cleanup_str, create_logger
from mikan.maya.lib.connect import *
from mikan.maya.lib.nurbs import create_path
from mikan.maya.lib.rig import copy_transform, orient_joint, stretch_ik

log = create_logger()


class Mod(mk.Mod):

    def run(self):
        # get data
        name = cleanup_str(self.data['name'])

        input1 = self.data.get('input1')
        input2 = self.data.get('input2')
        if not isinstance(input1, mx.Node) or not isinstance(input2, mx.Node):
            raise mk.ModArgumentError('invalid input nodes')

        pos1 = self.data.get('pos1', [0, 0, 0])
        pos2 = self.data.get('pos2', [0, 0, 0])

        space_ref = self.data.get('space_ref', mk.Nodes.get_id('*::space.root'))
        parent = self.data.get('parent')
        if parent is None:
            parent = mk.Nodes.get_id('::rig')

        targets = self.data.get('targets', {})
        do_helpers = self.data.get('helpers', 'debug' in self.modes)

        # process data
        tpl = self.get_template()
        do_flip = tpl.do_flip()

        if do_flip and isinstance(pos1, (list, tuple)):
            if not (input1.name()[-2] in ['_']):
                pos1[0] = pos1[0] * -1
            else:
                pos1 = [pos * -1 for pos in pos1]
        if do_flip and isinstance(pos2, (list, tuple)):
            if not (input2.name()[-2] in ['_']):
                pos2[0] = pos2[0] * -1
            else:
                pos2 = [pos * -1 for pos in pos2]

        sfx = self.get_template_id()
        if '.' in sfx:
            sfx = '_' + '_'.join(sfx.split('.')[1:])
        else:
            sfx = ''

        # build
        out_args = create_mod_distance(input1, input2, name, pos1, pos2, space_ref, targets, parent, sfx, do_flip)

        for i, target in enumerate(targets):
            self.set_id(out_args['drivers'][i], 'distance', '{}.{}'.format(self.data['name'], target))

        if do_helpers:
            out_helper = create_mod_distance_helper(out_args)
            self.set_id(out_helper['root'], 'distance', 'helper.{}'.format(self.data['name']))


def create_mod_distance(input1, input2, name, pos1, pos2, space_ref, targets, parent, sfx, is_mirror):
    # BUILD DRIVER LOC
    driver1 = mx.create_node(mx.tTransform, parent=input1, name='root_distance_{}_driver1{}'.format(name, sfx))
    driver2 = mx.create_node(mx.tTransform, parent=input2, name='root_distance_{}_driver2{}'.format(name, sfx))

    if isinstance(pos1, mx.Node):
        copy_transform(pos1, driver1, t=True, r=True)
    elif isinstance(pos1, (list, tuple)) and len(pos1) == 3:
        mc.xform(str(driver1), ws=False, t=pos1)
    else:
        copy_transform(input1, driver1, t=True, r=True)

    if isinstance(pos2, mx.Node):
        copy_transform(pos2, driver2, t=True, r=True)
    elif isinstance(pos2, (list, tuple)) and len(pos2) == 3:
        mc.xform(str(driver2), ws=False, t=pos2)
    else:
        copy_transform(input2, driver2, t=True, r=True)

    # BUILD distanceBetween
    db = mx.create_node(mx.tDistanceBetween, name='_len')
    db_input1 = driver1['worldMatrix'][0]
    db_input2 = driver2['worldMatrix'][0]

    if space_ref:
        mm1 = mx.create_node(mx.tMultMatrix, name='_mmx')
        mm2 = mx.create_node(mx.tMultMatrix, name='_mmx')
        driver1['worldMatrix'][0] >> mm1['matrixIn'][0]
        driver2['worldMatrix'][0] >> mm2['matrixIn'][0]
        space_ref['worldInverseMatrix'][0] >> mm1['matrixIn'][1]
        space_ref['worldInverseMatrix'][0] >> mm2['matrixIn'][1]

        db_input1 = mm1['matrixSum']
        db_input2 = mm2['matrixSum']

    db_input1 >> db['inMatrix1']
    db_input2 >> db['inMatrix2']

    # BUILD distanceBetween world (EXTRA)
    dbw = mx.create_node(mx.tDistanceBetween, name='_db#')
    driver1['worldMatrix'][0] >> dbw['inMatrix1']
    driver2['worldMatrix'][0] >> dbw['inMatrix2']

    drivers = []
    if targets:
        for key, target in iteritems(targets):
            base_name = '{}_{}'.format(name, key)

            driver = mx.create_node(mx.tNetwork, name='driver_distance_{}{}'.format(base_name, sfx))
            drivers.append(driver)

            driver.add_attr(mx.Double('in_distance_world', keyable=True))
            driver.add_attr(mx.Double('in_distance', keyable=True))
            driver.add_attr(mx.Double('target_distance', keyable=True))
            driver.add_attr(mx.Double('delta_distance', keyable=True))

            driver.add_attr(mx.Double('falloff_before', keyable=True))
            driver.add_attr(mx.Double('falloff_after', keyable=True))
            driver.add_attr(mx.Double('out_normalize', keyable=True))
            driver.add_attr(mx.Double('weight', keyable=True))
            driver.add_attr(mx.Double('out_weighted', keyable=True))

            driver['target_distance'] = target['target_distance']
            driver['falloff_before'] = target['falloff_before']
            driver['falloff_after'] = target['falloff_after']

            weight_value = target.get('weight', 1.0)

            if isinstance(weight_value, (int, float)):
                driver['weight'] = weight_value
            elif isinstance(weight_value, mx.Plug):
                weight_value >> driver['weight']

            # CONNECT
            db['distance'] >> driver['in_distance']
            dbw['distance'] >> driver['in_distance_world']
            connect_sub(driver['in_distance'], driver['target_distance'], driver['delta_distance'])

            cond_pos = connect_expr('falloff != 0 ? delta / clamp(falloff, 0.001, BIG) : 0', delta=driver['delta_distance'], falloff=driver['falloff_after'], BIG=99999999)
            cond_neg = connect_expr('falloff != 0 ? delta / clamp(falloff, 0.001, BIG) : 0', delta=driver['delta_distance'], falloff=driver['falloff_before'], BIG=99999999)
            out_cond = connect_expr('delta > 0 ? cond_pos : cond_neg * -1', delta=driver['delta_distance'], cond_pos=cond_pos, cond_neg=cond_neg)
            tan = target.get('falloff_tangent', target.get('falloff_tangeant', 'linear'))
            connect_driven_curve(out_cond, in_node=driver['out_normalize'], keys={-1: 0, 0: 1, 1: 0}, key_style=tan)

            connect_mult(driver['out_normalize'], driver['weight'], driver['out_weighted'], n='_multi#')

            op = target.get('op', target.get('out_operation'))
            ops = [op for i in range(0, len(target['remaps']))]

            if 'out_operations' in target:
                for i, out_attrA in enumerate(target['remaps']):
                    out_attrA_str = '{}.{}'.format(out_attrA.node(), out_attrA.name())
                    for j, out_attrB in enumerate(target['out_operations']):
                        out_attrB_str = '{}.{}'.format(out_attrB.node(), out_attrB.name())
                        if out_attrA_str == out_attrB_str:
                            ops[i] = target['out_operations'][out_attrB]
                            break

            for i, out_attr in enumerate(target['remaps']):
                if not isinstance(out_attr, mx.Plug):
                    continue

                obj = out_attr.node()
                attr = out_attr.name()
                if attr in {'translateX', 'translateY', 'translateZ'}:
                    attr = 't{}'.format(attr[-1]).lower()
                if attr in {'rotateX', 'rotateY', 'rotateZ'}:
                    attr = 'r{}'.format(attr[-1]).lower()
                if attr in {'scaleX', 'scaleY', 'scaleZ'}:
                    attr = 's{}'.format(attr[-1]).lower()

                obj_attr = '{}_{}'.format(obj, attr)
                obj_attr_out = '{}_out{}'.format(obj_attr, i)

                # ADD ATTR
                driver.add_attr(mx.Double('out{}_min'.format(i), keyable=True))
                driver.add_attr(mx.Double('out{}_max'.format(i), keyable=True))
                driver.add_attr(mx.Double('{}'.format(obj_attr_out), keyable=True))
                out_min = driver['out{}_min'.format(i)]
                out_max = driver['out{}_max'.format(i)]
                out_remap = driver['{}'.format(obj_attr_out)]

                # SET
                out_min.write(target['remaps'][out_attr][0])
                out_max.write(target['remaps'][out_attr][1])

                # CONNECT
                remap = connect_expr('remap(v, 0, 1, min2, max2)', v=driver['out_weighted'], min2=out_min, max2=out_max)
                remap >> out_remap

                if is_mirror and out_attr.name() in {'translateX', 'translateY', 'translateZ'}:
                    out_remap = connect_mult(out_remap, -1, n='_neg#')

                in_plug = out_attr.input(plug=True)
                if isinstance(in_plug, mx.Plug):
                    if in_plug.node().is_a(mx.tUnitConversion):
                        in_plug = in_plug.node()['input'].input(plug=True)

                    if ops[i] == 'add':
                        add = connect_add(in_plug, out_remap)
                        add >> out_attr
                    elif ops[i] == 'mult':
                        mult = connect_mult(in_plug, out_remap)
                        mult >> out_attr
                    elif ops[i] == 'max':
                        max_exp = connect_expr('max(a, b)', a=in_plug, b=out_remap)
                        max_exp >> out_attr
                    elif ops[i] == 'min':
                        min_exp = connect_expr('min(a, b)', a=in_plug, b=out_remap)
                        min_exp >> out_attr
                    else:
                        out_remap >> out_attr
                else:
                    out_remap >> out_attr

    data = {
        'name': name,
        'driver1': driver1,
        'driver2': driver2,
        'sfx': sfx,
        'parent': parent,
        'targets': targets,
        'drivers': drivers
    }
    return data


# ------------------------------------------------------------------------------------------------------TO UPGRADE
'''
attrsName   = ['DELTA_______','in_distance' , 'target_distance'   , 'delta_distance' ]
attrsType   = ['separator'   ,'floatVisu'  , 'float'            , 'floatVisu'     ]
attrsValue  = [ None         ,None         , target['target_distance'] , None            ]
attrsName  += ['FALLOFF_____','falloff_before'            , 'falloff_after'          , 'out_normalize' ]
attrsType  += ['separator'   ,'float+'                   , 'float+'                , 'floatVisu'    ]
attrsValue += [ None         , target['falloff_before']  , target['falloff_after'] , None           ]
attrsName  += ['REMAP______' , 'out_min'          , 'out_max'           , 'out'  ]
attrsType  += ['separator'   , 'float'           , 'float'            , 'floatVisu' ]
attrsValue += [ None         , target['outs_min'] , target['outs_max']  , None        ]            
attrs      = create_attributes_special( driver , attrsName , attrsType , attrsValue  )
'''


# ________________________________________________________________________________________________TO UPGRADE


def create_mod_distance_helper(out_args):
    name = out_args['name']
    driver1 = out_args['driver1']
    driver2 = out_args['driver2']
    sfx = out_args['sfx']
    parent = out_args['parent']
    targets = out_args['targets']
    drivers = out_args['drivers']

    data = create_mod_distance_helper_stretchy(name, driver1, driver2, sfx)
    mc.parent(str(data['root']), str(parent))
    for i, key in enumerate(targets):
        target = targets[key]
        base_name = '{}_{}'.format(name, key)
        out_target = create_mod_distance_helper_target(base_name, sfx, drivers[i], list(target['remaps']))
        mc.parentConstraint(str(data['joints'][0]), str(out_target['root']))

        div = connect_expr('wDist / inDist', wDist=drivers[i]['in_distance_world'], inDist=drivers[i]['in_distance'])
        div >> out_target['root']['scaleX']

        mc.parent(str(out_target['root']), str(data['root']))

    return data


def create_mod_distance_helper_target(base_name, sfx, node_info, output=None):
    # BUILD
    target_root = mx.create_node(mx.tTransform, name='root_{}_target{}'.format(base_name, sfx))
    target_loc = mx.create_node(mx.tTransform, parent=target_root, name='modif_{}_target{}'.format(base_name, sfx))
    mx.create_node(mx.tLocator, parent=target_loc)

    after_root = mx.create_node(mx.tTransform, parent=target_loc, name='root_{}_after{}'.format(base_name, sfx))
    after_scale = mx.create_node(mx.tTransform, parent=after_root, name='scale_{}_after{}'.format(base_name, sfx))
    after_loc = mx.create_node(mx.tTransform, parent=target_loc, name='modif_{}_after{}'.format(base_name, sfx))
    mx.create_node(mx.tLocator, parent=after_loc)

    before_root = mx.create_node(mx.tTransform, parent=target_loc, name='root_{}_before{}'.format(base_name, sfx))
    before_scale = mx.create_node(mx.tTransform, parent=before_root, name='scale_{}_before{}'.format(base_name, sfx))
    before_loc = mx.create_node(mx.tTransform, parent=before_root, name='modif_{}_before{}'.format(base_name, sfx))
    mx.create_node(mx.tLocator, parent=before_loc)

    after_curve = mc.curve(p=[(0, 1, 0), (0.5, 1, 0), (0.5, 0, 0), (1, 0, 0)])
    before_curve = mc.curve(p=[(0, 1, 0), (0.5, 1, 0), (0.5, 0, 0), (1, 0, 0)])
    after_curve = mx.encode(after_curve)
    before_curve = mx.encode(before_curve)
    mc.parent(str(after_curve), str(after_scale))
    mc.parent(str(before_curve), str(before_scale))

    # SET ATTR
    after_loc['tx'] = 1
    after_loc['ty'] = 1

    before_loc['tx'] = 1
    before_loc['ty'] = -1

    before_root['sx'] = -1

    # CONNECT ATTR
    after_loc['tx'] >> after_scale['sx']
    before_loc['tx'] >> before_scale['sx']

    # SHAPE MODIF
    target_loc_shape = target_loc.shape()
    target_loc_shape['overrideEnabled'] = True
    target_loc_shape['overrideColor'] = 13
    target_loc_shape['localScaleX'] = 0
    target_loc_shape['localScaleZ'] = 0.2

    after_loc_shape = after_loc.shape()
    after_loc_shape['overrideEnabled'] = True
    after_loc_shape['overrideColor'] = 11
    after_loc_shape['localScaleY'] = 0.2

    before_loc_shape = before_loc.shape()
    before_loc_shape['overrideEnabled'] = True
    before_loc_shape['overrideColor'] = 11
    before_loc_shape['localScaleY'] = 0.2

    after_curve_shape = after_curve.shape()
    after_curve_shape['overrideEnabled'] = True
    after_curve_shape['overrideDisplayType'] = 2
    after_curve_shape['lineWidth'] = 3

    before_curve_shape = before_curve.shape()
    before_curve_shape['overrideEnabled'] = True
    before_curve_shape['overrideDisplayType'] = 2
    before_curve_shape['lineWidth'] = 3

    # CREATE ATTR
    attrs = ['ty', 'tz', 'rx', 'ry', 'rz', 'sx', 'sy', 'sz']
    for node in (target_loc, before_loc, after_loc):
        for attr in attrs:
            node[attr].keyable = False
            node[attr].lock()

        node.enable_limit(mx.kTranslateMinX, True)
        node.set_limit(mx.kTranslateMinX, 0)

    target_loc['tx'] = node_info['target_distance'].read()
    before_loc['tx'] = node_info['falloff_before'].read()
    after_loc['tx'] = node_info['falloff_after'].read()

    # ADD ATTR
    target_loc.add_attr(mx.Double('in_distance', keyable=True))
    target_loc.add_attr(mx.Double('target_distance', keyable=True))
    target_loc.add_attr(mx.Double('delta_distance', keyable=True))

    target_loc.add_attr(mx.Double('falloff_before', keyable=True))
    target_loc.add_attr(mx.Double('falloff_after', keyable=True))
    target_loc.add_attr(mx.Double('out_normalize', keyable=True))
    target_loc.add_attr(mx.Double('weight', keyable=True))
    target_loc.add_attr(mx.Double('out_weighted', keyable=True))

    target_loc.add_attr(mx.Boolean('show_falloff', keyable=True, default=True))
    target_loc.add_attr(mx.Boolean('show_influence', keyable=True, default=False))

    # OUT
    target_loc['target_distance'] >> node_info['target_distance']
    target_loc['falloff_before'] >> node_info['falloff_before']
    target_loc['falloff_after'] >> node_info['falloff_after']

    # IN
    node_info['in_distance'] >> target_loc['in_distance']
    node_info['delta_distance'] >> target_loc['delta_distance']
    node_info['out_normalize'] >> target_loc['out_normalize']
    node_info['weight'] >> target_loc['weight']
    node_info['out_weighted'] >> target_loc['out_weighted']

    # SYS
    target_loc['tx'] >> target_loc['target_distance']
    before_loc['tx'] >> target_loc['falloff_before']
    after_loc['tx'] >> target_loc['falloff_after']

    target_loc['show_falloff'] >> before_curve['visibility']
    target_loc['show_falloff'] >> after_curve['visibility']

    for i in range(0, len(output)):

        obj = output[i].node()
        attr = output[i].name()
        if attr in {'translateX', 'translateY', 'translateZ'}:
            attr = 't{}'.format(attr[-1]).lower()
        if attr in {'rotateX', 'rotateY', 'rotateZ'}:
            attr = 'r{}'.format(attr[-1]).lower()
        if attr in {'scaleX', 'scaleY', 'scaleZ'}:
            attr = 's{}'.format(attr[-1]).lower()

        obj_attr = '{}_{}'.format(obj, attr)
        obj_attr_out = '{}_out{}'.format(obj_attr, i)

        target_loc.add_attr(mx.Double('out{}_min'.format(i), keyable=True))
        target_loc.add_attr(mx.Double('out{}_max'.format(i), keyable=True))
        target_loc.add_attr(mx.Double('{}'.format(obj_attr_out), keyable=True))

        target_out_min = target_loc['out{}_min'.format(i)]
        target_out_max = target_loc['out{}_max'.format(i)]
        target_out_remap = target_loc['{}'.format(obj_attr_out)]
        node_out_min = node_info['out{}_min'.format(i)]
        node_out_max = node_info['out{}_max'.format(i)]
        node_out_remap = node_info['{}'.format(obj_attr_out)]

        # SET
        target_out_min.write(node_out_min.read())
        target_out_max.write(node_out_max.read())

        # OUT
        target_out_min >> node_out_min
        target_out_max >> node_out_max

        # IN
        node_out_remap >> target_out_remap

        # LINE
        if output:
            out_line = create_path(target_loc, output[i].node(), d=1)
            out_line.rename('{}{}{}'.format(base_name, i, sfx))
            target_loc['show_influence'] >> out_line['visibility']
            mc.parent(str(out_line), str(target_loc), r=True)

    data = {'root': target_root, 'target_loc': target_loc}
    return data


def create_mod_distance_helper_stretchy(name, input1, input2, sfx, stretch=0, joint_radius=0.01):
    base_name = 'distance_' + name + '_debug_stretchy'

    root = mx.create_node(mx.tTransform, name='root_{}{}'.format(base_name, sfx))

    # BUILD OFFSET
    offset1_root = mx.create_node(mx.tTransform, name='root_{}_offset1{}'.format(base_name, sfx))
    offset1 = mx.create_node(mx.tTransform, parent=offset1_root, name='modif_{}_offset1{}'.format(base_name, sfx))
    mx.create_node(mx.tLocator, parent=offset1)

    mc.parentConstraint(str(input1.parent()), str(offset1_root))
    copy_transform(input1, offset1, t=True, r=True)
    offset1['translate'] >> input1['translate']

    offset1_shape = offset1.shape()
    offset1_shape['overrideEnabled'] = True
    offset1_shape['overrideColor'] = 17

    offset2_root = mx.create_node(mx.tTransform, name='root_{}_offset2{}'.format(base_name, sfx))
    offset2 = mx.create_node(mx.tTransform, parent=offset2_root, name='modif_{}_offset2{}'.format(base_name, sfx))
    mx.create_node(mx.tLocator, parent=offset2)

    mc.parentConstraint(str(input2.parent()), str(offset2_root))
    copy_transform(input2, offset2, t=True, r=True)
    offset2['translate'] >> input2['translate']

    offset2_shape = offset2.shape()
    offset2_shape['overrideEnabled'] = True
    offset2_shape['overrideColor'] = 17

    attrs = ['rx', 'ry', 'rz', 'sx', 'sy', 'sz']
    for node in (offset1, offset2):
        for attr in attrs:
            node[attr].keyable = False
            node[attr].lock()

    # IK
    data = create_stretch_IK(base_name, input1, input2, sfx, stretch=0, joint_radius=0.01)
    mc.parent(str(offset1_root), str(offset2_root), str(data['root']), str(root))
    data['root'] = root

    return data


#############################################################################################################################
#############################################################################################################################
#############################################################################################################################


def create_line(input1, input2, base_name, sfx, line_width=-1):
    line_trsf = mx.create_node(mx.tTransform, name='line_{}{}'.format(base_name, sfx))
    line_curve = mc.curve(p=[(0, 0, 0), (1, 0, 0)], d=1, n='line_{}_crv{}'.format(base_name, sfx))
    line_curve = mx.encode(line_curve)
    line_curve_shape = line_curve.shape()
    cluster0, handle0 = mc.cluster(str(line_curve_shape) + '.cv[0]', n='line_{}_cluster{}'.format(base_name, sfx))
    cluster1, handle1 = mc.cluster(str(line_curve_shape) + '.cv[1]', n='line_{}_cluster{}'.format(base_name, sfx))
    cluster0 = mx.encode(cluster0)
    cluster1 = mx.encode(cluster1)
    handle0 = mx.encode(handle0)
    handle1 = mx.encode(handle1)

    cluster0.add_attr(mx.Boolean('gem_protected', default=True))
    cluster1.add_attr(mx.Boolean('gem_protected', default=True))

    mc.parent(str(line_curve), str(handle0), str(handle1), str(line_trsf))

    mc.parentConstraint(str(input1), str(handle0))
    mc.parentConstraint(str(input2), str(handle1))

    handle0['visibility'] = False
    handle1['visibility'] = False

    line_curve['inheritsTransform'] = False

    line_curve_shape['overrideEnabled'] = True
    line_curve_shape['overrideDisplayType'] = 2

    line_curve_shape['lineWidth'] = line_width

    data = {'root': line_trsf}
    return data


def create_stretch_IK(base_name, input1, input2, sfx, stretch=0, joint_radius=0.01):
    base_name = base_name + '_sik'

    # BUILD BASE HIERARCHY
    root = mx.create_node(mx.tTransform, name='root_{}{}'.format(base_name, sfx))
    input1_hook = mx.create_node(mx.tTransform, parent=root, name='hook_{}_1{}'.format(base_name, sfx))
    input2_hook = mx.create_node(mx.tTransform, parent=root, name='hook_{}_2{}'.format(base_name, sfx))

    input2_hook['tx'] = 1
    # BUILD JOINTS
    joint1 = mx.create_node(mx.tJoint, parent=input1_hook, name='j_{}_1{}'.format(base_name, sfx))
    joint2 = mx.create_node(mx.tJoint, parent=joint1, name='j_{}_2{}'.format(base_name, sfx))

    joint2['tx'] = 1
    # SET JOINTS POS
    mc.parentConstraint(str(input1), str(input1_hook))
    mc.parentConstraint(str(input2), str(input2_hook))
    copy_transform(input2, joint2, t=True, r=True)

    # BUILD STRETCHY
    orient_joint([joint1, joint2], aim='x', up='y', up_dir=(0, 1, 0))
    stretch_elems = stretch_ik([joint1, joint2], input2_hook)
    mx.cmd(mc.parent, stretch_elems, root)

    input2_hook['stretch'] = stretch

    # SET VIS
    for elem in stretch_elems:
        elem['visibility'] = False

    input2_hook['visibility'] = False

    joint1['overrideEnabled'] = True
    joint1['overrideDisplayType'] = 2

    data = {'joints': [joint1, joint2], 'root': root}
    return data


'''
from mikan.templates.mod.distance.maya import get_distance_angle_tool_activate_attributes_on_rig
get_distance_angle_tool_activate_attributes_on_rig()
'''


def get_distance_angle_tool_activate_attributes_on_rig():
    distance_nodes = mc.ls('driver_distance*', r=True, type='network')
    angle_nodes = mc.ls('driver_angle*', r=True, type='network')

    activate_attrs = []

    for n in distance_nodes + angle_nodes:
        in_attrs_raw = mc.listConnections('{}.weight'.format(n), s=True, d=False, plugs=True) or []
        if in_attrs_raw:
            in_attr = in_attrs_raw[0]
            activate_attrs.append(in_attr)

    activate_attrs = list(set(activate_attrs))

    return activate_attrs


def activate_distance_angle_tool( set_keyframe = None ):
    activate_attrs = get_distance_angle_tool_activate_attributes_on_rig()
    for obj_attr in activate_attrs:
        if mc.getAttr(obj_attr, l=True):
            mc.setAttr(obj_attr, l=False)

        source = mc.listConnections(obj_attr, s=True, d=False, plugs=True)
        if source:
            mc.disconnectAttr(source[0], obj_attr)
        mc.setAttr(obj_attr, 1)
        if set_keyframe != None and type(set_keyframe) in [int,float]:
            ctrl, attr = obj_attr.split('.')
            mc.setKeyframe( ctrl, attribute = attr, value = 1, time = set_keyframe, breakdown =  0      )

    return activate_attrs


def isolate_distance_angle_tool():
    distance_roots = mc.ls("root_distance*", r=True, type='transform') or []
    distance_locs_target = mc.ls("modif_*_target_*", r=True, type='transform') or []
    for l in distance_locs_target:
        mc.showHidden(l)
        mc.setAttr('{}.show_falloff'.format(l), 1)
        mc.setAttr('{}.show_influence'.format(l), 1)
    distance_locs = []
    distance_locs += mc.ls("modif_distance_*", r=True, type='transform') or []

    for l in distance_locs:
        mc.showHidden(l)
    distance_jnts = mc.ls("j_distance_*", r=True, type='joint') or []
    for j in distance_jnts:
        mc.setAttr('{}.radius'.format(j), 0.01)

    distance_nodes = mc.ls('driver_distance_*', r=True, type='network')
    geos = mc.ls('geo', r=True, type='transform')
    playblast_gui = [obj for obj in ['turn_sys_GRP', 'camera:camera', 'text_overlay1'] if (mc.objExists(obj))]
    try:
        playblast_gui += mc.ls(type='text_overlay') or []
    except:
        pass

    for elem in mc.ls(type='locator'):
        if '_overlay' in elem:
            playblast_gui.append(elem)
        elif 'ttDraw' in elem:
            playblast_gui.append(elem)

    distance_outputs = []
    for n in distance_nodes:
        for i in range(0, 20):
            obj_attr = '{}.out{}'.format(n, i)

            if mc.objExists(obj_attr):

                buffers = mc.listConnections(obj_attr, s=False, d=True, skipConversionNodes=True) or []
                for j in range(0, 100):
                    buffers_next = []
                    for buf in buffers:
                        buffers_next = []
                        if mc.nodeType(buf) == 'transform':
                            if buf[:6] != 'modif_':
                                distance_outputs.append(buf)
                        else:
                            if mc.nodeType(buf) == 'addDoubleLinear':
                                buffers_next += mc.listConnections(buf + '.output', s=False, d=True, skipConversionNodes=True) or []
                    if not buffers_next:
                        break
                    buffers = buffers_next[:]

    distance_outputs = list(set(distance_outputs))
    ctrs_outputs = []
    for o in distance_outputs:
        ctrs_outputs += mc.listRelatives(o, p=True, c=False, f=True) or []

    viewport = mc.paneLayout('viewPanes', q=True, pane1=True)
    mc.select(geos + distance_roots + ctrs_outputs + playblast_gui)

    mc.select(geos + distance_roots + ctrs_outputs + playblast_gui)
    mc.isolateSelect(viewport, state=1)
    mc.isolateSelect(viewport, addSelected=True)
    mc.select(cl=True)
