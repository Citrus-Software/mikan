# coding: utf-8

from six import iteritems

from mikan.maya import cmds as mc
import mikan.maya.cmdx as mx

import mikan.maya.core as mk
from mikan.core import cleanup_str, create_logger
from mikan.maya.lib.connect import *
from mikan.maya.lib.nurbs import create_path
from mikan.maya.lib.rig import copy_transform, create_extract_vector_from_transform, create_angle_between

log = create_logger()


class Mod(mk.Mod):

    def run(self):
        # get data
        name = cleanup_str(self.data['name'])

        angle_ref = self.data.get('angle_ref')
        angle_parent = self.data.get('angle_parent')
        if not isinstance(angle_ref, mx.Node) or not isinstance(angle_parent, mx.Node):
            raise mk.ModArgumentError('invalid input nodes')

        space_ref = self.data.get('space_ref', mk.Nodes.get_id('*::space.root'))
        parent = self.data.get('parent')
        if parent is None:
            parent = mk.Nodes.get_id('*::rig')

        targets = self.data.get('targets', None)
        do_helpers = self.data.get('helpers', 'debug' in self.modes)

        # process data
        tpl = self.get_template()
        do_flip = tpl.do_flip()

        sfx = self.get_template_id()
        if '.' in sfx:
            sfx = '_' + '_'.join(sfx.split('.')[1:])
        else:
            sfx = ''

        # build
        out_args = create_mod_angle(angle_ref, name, angle_parent, space_ref, targets, parent, sfx, do_flip)
        for i, target in enumerate(targets):
            self.set_id(out_args['drivers'][i], 'angle', '{}.{}'.format(self.data['name'], target))

        if do_helpers:
            out_helper = create_mod_angle_helper(out_args)
            self.set_id(out_helper['root'], 'angle', 'helper.{}'.format(self.data['name']))


def create_mod_angle(angle_ref, name, angle_parent, space_ref, targets, parent, sfx, is_mirror):
    # BUILD DRIVER LOC
    ref = mx.create_node(mx.tTransform, parent=angle_parent, name='root_angle_{}_ref{}'.format(name, sfx))
    current = mx.create_node(mx.tTransform, parent=ref, name='root_angle_{}_current{}'.format(name, sfx))

    copy_transform(angle_ref, ref, t=True, r=True)
    mc.parentConstraint(str(angle_ref), str(current))

    if is_mirror:
        bone_dir_axis = mx.Vector(0, -1, 0)
    else:
        bone_dir_axis = mx.Vector(0, 1, 0)

    # EXTRACT VECTOR
    current_dir = create_extract_vector_from_transform(current, bone_dir_axis, world_matrix=True, parent_matrix_obj=space_ref)

    drivers = []
    angle_targets = []
    if targets:
        for key, target in iteritems(targets):
            base_name = '{}_{}'.format(name, key)

            # BUILD ANGLE BETWEEN SETUP
            if isinstance(target['target_angle'], (list, tuple)):
                target_trsf = mx.create_node(mx.tTransform, parent=ref, name='root_angle_{}_target{}'.format(base_name, sfx))
                mc.xform(str(target_trsf), ws=False, ro=target['target_angle'])
            else:
                target_trsf = target['target_angle']

            angle_targets.append(target_trsf)

            target_dir = create_extract_vector_from_transform(target_trsf, bone_dir_axis, world_matrix=True, parent_matrix_obj=space_ref)

            a_current_target = create_angle_between(current_dir, target_dir)

            # BUILD network
            driver = mx.create_node(mx.tNetwork, name='driver_angle_{}{}'.format(base_name, sfx))
            drivers.append(driver)

            # ADD ATTR
            driver.add_attr(mx.Double('in_angle', keyable=True))

            # SET
            a_current_target >> driver['in_angle']

            if 'falloff' in target:
                driver.add_attr(mx.Double('falloff', keyable=True))
                driver.add_attr(mx.Double('out_normalize', keyable=True))
                driver.add_attr(mx.Double('weight', keyable=True))
                driver.add_attr(mx.Double('out_weighted', keyable=True))

                driver['falloff'] = target['falloff']
                weight_value = target.get('weight', 1.0)

                if isinstance(weight_value, (int, float)):
                    driver['weight'] = weight_value
                else:
                    weight_value >> driver['weight']

                div = connect_expr('delta / clamp(falloff, 0.001, BIG)', delta=driver['in_angle'], falloff=driver['falloff'], BIG=99999999)
                tan = target.get('falloff_tangent', target.get('falloff_tangeant', 'linear'))
                connect_driven_curve(div, in_node=driver['out_normalize'], keys={-1: 0, 0: 1, 1: 0}, key_style=tan)

                connect_mult(driver['out_normalize'], driver['weight'], driver['out_weighted'], n='_multi#')

            for i, out_attr in enumerate(target['remaps']):
                # ADD ATTR
                out_angle_info = None
                if 'falloff' in target:
                    driver.add_attr(mx.Double('out_min{}'.format(i), keyable=True))
                    driver.add_attr(mx.Double('out_max{}'.format(i), keyable=True))
                    driver.add_attr(mx.Double('out{}'.format(i), keyable=True))
                    out_min = driver['out_min{}'.format(i)]
                    out_max = driver['out_max{}'.format(i)]
                    out_remap = driver['out{}'.format(i)]
                    # SET
                    out_min.write(target['remaps'][out_attr][0])
                    out_max.write(target['remaps'][out_attr][1])
                    # CONNECT
                    remap = connect_expr('remap(v, 0, 1, min2, max2)', v=driver['out_weighted'], min2=out_min, max2=out_max)
                    remap >> out_remap
                    out_angle_info = out_remap
                else:
                    out_angle_info = driver['in_angle']

                if is_mirror and out_attr.name() in ['translateX', 'translateY', 'translateZ']:
                    out_angle_info = connect_mult(out_angle_info, -1, n='_neg#')

                in_plug = out_attr.input(plug=True)
                if isinstance(in_plug, mx.Plug):
                    if in_plug.node().is_a(mx.tUnitConversion):
                        in_plug = in_plug.node()['input'].input(plug=True)

                    op = target.get('op', target.get('out_operation'))
                    if op == 'add':
                        add = connect_add(in_plug, out_angle_info)
                        add >> out_attr
                    elif op == 'mult':
                        mult = connect_mult(in_plug, out_angle_info)
                        mult >> out_attr
                    elif op == 'max':
                        max_exp = connect_expr('max(a, b)', a=in_plug, b=out_angle_info)
                        max_exp >> out_attr
                    elif op == 'min':
                        min_exp = connect_expr('min(a, b)', a=in_plug, b=out_angle_info)
                        min_exp >> out_attr
                    else:
                        out_angle_info >> out_attr
                else:
                    out_angle_info >> out_attr

    data = {
        'name': name,
        'angle_targets': angle_targets,
        'angle_ref': angle_ref,
        'angle_parent': ref,
        'sfx': sfx,
        'parent': parent,
        'targets': targets,
        'drivers': drivers,
        'bone_dir_axis': bone_dir_axis
    }
    return data


# ------------------------------------------------------------------------------------------------------TO UPGRADE
r'''
attrsName   = ['DELTA_______','in_angle' , 'target_angle'   , 'delta_angle' ]
attrsType   = ['separator'   ,'floatVisu'  , 'float'            , 'floatVisu'     ]
attrsValue  = [ None         ,None         , target['target_angle'] , None            ]
attrsName  += ['FALLOFF_____','falloff_before'            , 'falloff_after'          , 'out_normalize' ]
attrsType  += ['separator'   ,'float+'                   , 'float+'                , 'floatVisu'    ]
attrsValue += [ None         , target['falloff_before']  , target['falloff_after'] , None           ]
attrsName  += ['REMAP______' , 'out_min'          , 'out_max'           , 'out'  ]
attrsType  += ['separator'   , 'float'           , 'float'            , 'floatVisu' ]
attrsValue += [ None         , target['outs_min'] , target['outs_max']  , None        ]            
attrs      = create_attributes_special( driver , attrsName , attrsType , attrsValue  )
'''


# ________________________________________________________________________________________________TO UPGRADE


def create_mod_angle_helper(out_args):
    name = out_args['name']
    angle_targets = out_args['angle_targets']
    angle_ref = out_args['angle_ref']
    angle_parent = out_args['angle_parent']
    sfx = out_args['sfx']
    parent = out_args['parent']
    targets = out_args['targets']
    drivers = out_args['drivers']
    bone_dir_axe = out_args['bone_dir_axis']

    targets_root = mx.create_node(mx.tTransform, parent=parent, name='root_{}_modif{}'.format(name, sfx))
    for i, key in enumerate(targets):
        target = targets[key]
        base_name = '{}_{}'.format(name, key)
        out_target = create_mod_angle_helper_target(base_name, sfx, drivers[i], angle_targets[i], bone_dir_axe, list(target['remaps']))
        mc.parentConstraint(str(angle_parent), str(out_target['root']))
        mc.parent(str(out_target['root']), str(targets_root))

    data = {'root': targets_root}
    return data


def create_mod_angle_helper_target(base_name, sfx, node_info, angle_target, vector, output=None):
    falloff_exists = 'falloff' in node_info

    # BUILD
    target_root = mx.createNode(mx.tTransform, name='root_{}_target{}'.format(base_name, sfx))
    target_loc = mx.create_node(mx.tTransform, parent=target_root, name='modif_{}_target{}'.format(base_name, sfx))
    mx.create_node(mx.tLocator, parent=target_loc)

    vector = mx.Vector(vector)
    vector *= -1

    # SHAPE MODIF
    target_loc_shape = target_loc.shape()
    target_loc_shape['overrideEnabled'] = True
    target_loc_shape['overrideColor'] = 14

    target_loc_shape['localPosition'] = vector * 1
    target_loc_shape['localScale'] = vector * 1

    # lINE HOOK (VISUAL)
    line_hook = mx.create_node(mx.tTransform, parent=target_loc, name='debug_{}_line_hook{}'.format(base_name, sfx))
    line_hook['translate'] = vector * 2

    # CREATE ATTR
    attrs = ['tx', 'ty', 'tz', 'sx', 'sy', 'sz']
    for attr in attrs:
        target_loc[attr].keyable = False
        target_loc[attr].lock()

    # ADD ATTR
    target_loc.add_attr(mx.Double('in_angle', keyable=True))
    target_loc.add_attr(mx.Boolean('show_influence', keyable=True, default=False))

    if falloff_exists:
        target_loc.add_attr(mx.Double('falloff', keyable=True))
        target_loc.add_attr(mx.Double('out_normalize', keyable=True))
        target_loc.add_attr(mx.Double('weight', keyable=True))
        target_loc.add_attr(mx.Double('out_weighted', keyable=True))
        target_loc.add_attr(mx.Boolean('show_falloff', keyable=True, default=True))

        # CONE
        cone, poly = mc.polyCone(n='visu_{}_cone{}'.format(base_name, sfx))
        cone = mx.encode(cone)
        poly = mx.encode(poly)

        if vector[1] > 0:
            cone['rotateX'] = 180
            cone['translateY'] = 0.5
        else:
            cone['rotateX'] = 0
            cone['translateY'] = -0.5

        cone['overrideEnabled'] = True
        cone['overrideDisplayType'] = 1
        poly['height'] = 1
        mc.parent(str(cone), str(target_loc))

        tan_out = connect_expr('tan(input)', input=target_loc['falloff'])
        tan_out >> poly['radius']

        target_loc['show_falloff'] >> cone['visibility']

        # SET ATTR
        target_loc['falloff'] = node_info['falloff'].read()

        # OUT
        target_loc['falloff'] >> node_info['falloff']

        # IN
        node_info['out_normalize'] >> target_loc['out_normalize']
        node_info['weight'] >> target_loc['weight']
        node_info['out_weighted'] >> target_loc['out_weighted']

    target_loc['r'] = angle_target['r'].read()
    target_loc['r'] >> angle_target['r']

    # IN
    node_info['in_angle'] >> target_loc['in_angle']

    for i in range(len(output)):
        if falloff_exists:
            target_loc.add_attr(mx.Double('out_min{}'.format(i), keyable=True))
            target_loc.add_attr(mx.Double('out_max{}'.format(i), keyable=True))
            target_loc.add_attr(mx.Double('out{}'.format(i), keyable=True))

            target_out_min = target_loc['out_min{}'.format(i)]
            target_out_max = target_loc['out_max{}'.format(i)]
            target_out_remap = target_loc['out{}'.format(i)]
            node_out_min = node_info['out_min{}'.format(i)]
            node_out_max = node_info['out_max{}'.format(i)]
            node_out_remap = node_info['out{}'.format(i)]

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
            out_line = create_path(line_hook, output[i].node(), d=1)
            out_line.rename('{}{}{}'.format(base_name, i, sfx))
            target_loc['show_influence'] >> out_line['visibility']
            mc.parent(str(out_line), str(target_loc), r=True)

    data = {'root': target_root, 'target_loc': target_loc}
    return data
