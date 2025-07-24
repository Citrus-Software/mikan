# coding: utf-8

import meta_nodal_py as kl
from meta_nodal_py.Imath import V3f, M44f, Euler

import mikan.tangerine.core as mk
from mikan.tangerine.lib.commands import add_plug, copy_transform
from mikan.tangerine.lib.connect import connect_expr, connect_driven_curve, connect_add, connect_mult
from mikan.tangerine.lib.rig import create_extract_vector_from_transform, create_angle_between, parent_constraint
from mikan.core import cleanup_str, create_logger
from mikan.tangerine.lib.connect import safe_connect

log = create_logger()


class Mod(mk.Mod):

    def run(self):
        # GET INFO
        name = cleanup_str(self.data['name'])

        angle_ref = self.data.get('angle_ref')
        angle_parent = self.data.get('angle_parent')
        if not isinstance(angle_ref, kl.Node) or not isinstance(angle_parent, kl.Node):
            raise mk.ModArgumentError('invalid input nodes')

        space_ref = self.data.get('space_ref', mk.Nodes.get_id('*::space.root'))
        parent = self.data.get('parent')
        if parent is None or parent == 'rig':
            parent = mk.Nodes.get_id('*::rig')

        targets = self.data.get('targets', None)

        # PROCESS INFO
        tpl = self.get_template()
        do_flip = tpl.do_flip()

        sfx = self.get_template_id()
        if '.' in sfx:
            sfx = '_' + '_'.join(sfx.split('.')[1:])
        else:
            sfx = ''

        # BUILD
        out_args = create_mod_angle_tang(angle_ref, name, angle_parent, space_ref, targets, parent, sfx, do_flip)


def create_mod_angle_tang(angle_ref, name, angle_parent, space_ref, targets, parent, sfx, is_mirror):
    # BUILD DRIVER LOC
    ref = kl.SceneGraphNode(angle_parent, 'root_angle_{}_ref{}'.format(name, sfx))
    current = kl.SceneGraphNode(angle_ref, 'root_angle_{}_current{}'.format(name, sfx))

    copy_transform(angle_ref, ref)
    parent_constraint(angle_ref, current)

    if is_mirror:
        bone_dir_axis = V3f(0, -1, 0)
    else:
        bone_dir_axis = V3f(0, 1, 0)

    # pos = ref.transform.get_value().translation()
    # bone_dir_axis = V3f(pos[0], pos[1], pos[2])
    # bone_dir_axis.normalize()

    # EXTRACT VECTOR
    current_dir = create_extract_vector_from_transform(current, bone_dir_axis, world_matrix=True, parent_matrix_obj=space_ref)

    drivers = []
    if targets:
        angle_targets = []
        for key in list(targets):
            target = targets[key]
            base_name = '{}_{}'.format(name, key)

            # BUILD ANGLE BETWEEN SETUP
            target_trsf = kl.SceneGraphNode(ref, 'root_angle_{}_target{}'.format(base_name, sfx))
            angle_targets.append(target_trsf)

            m = M44f()
            m.setRotation(V3f(target['target_angle'][0], target['target_angle'][1], target['target_angle'][2]), Euler.XYZ)
            target_trsf.set_transform_matrix(m)

            target_dir = create_extract_vector_from_transform(target_trsf, bone_dir_axis, world_matrix=True, parent_matrix_obj=space_ref)

            a_current_target = create_angle_between(current_dir, target_dir)

            # BUILD network
            driver = kl.Node(ref, 'driver_angle_{}{}'.format(base_name, sfx))
            drivers.append(driver)

            # ADD ATTR
            add_plug(driver, 'in_angle', float, k=1)

            # CONNECT
            driver.in_angle.connect(a_current_target)

            if 'falloff' in target:
                add_plug(driver, 'falloff', float, k=1)
                add_plug(driver, 'out_normalize', float, k=1)
                add_plug(driver, 'weight', float, k=1)
                add_plug(driver, 'out_weighted', float, k=1)
            # SET
            driver.falloff.set_value(target['falloff'])
            weight_value = target.get('weight', 1.0)

            if isinstance(weight_value, (int, float)):
                driver.weight.set_value(weight_value)
            else:
                safe_connect(weight_value, driver.weight)

                div = connect_expr('delta / clamp(falloff, 0.001 , BIG )', delta=driver.in_angle, falloff=driver.falloff, BIG=99999999)
                tan = target.get('falloff_tangent', target.get('falloff_tangeant', 'linear'))
                connect_driven_curve(div, driver.out_normalize, keys={-1: 0, 0: 1, 1: 0}, tangent_mode=tan, pre='constant', post='constant')

                connect_mult(driver.out_normalize, driver.weight, driver.out_weighted, n='_multi#')

            for i, out_attr in enumerate(list(target['remaps'])):
                # ADD ATTR
                out_angle_info = None
                if 'falloff' in target:
                    out_min = add_plug(driver, 'out_min{}'.format(i), float, k=1)
                    out_max = add_plug(driver, 'out_max{}'.format(i), float, k=1)
                    out_remap = add_plug(driver, 'out{}'.format(i), float, k=1)

                    # SET
                    out_min.set_value(target['remaps'][out_attr][0])
                    out_max.set_value(target['remaps'][out_attr][1])

                    # CONNECT
                    remap = connect_expr('remap(v, 0, 1, min2, max2) ', v=driver.out_weighted, min2=out_min, max2=out_max)
                    out_remap.connect(remap)
                    out_angle_info = out_remap
                else:
                    out_angle_info = driver.in_angle

                if is_mirror:
                    attrs_to_flip = ['translate.x', 'translate.y', 'translate.z']
                    for attr in attrs_to_flip:
                        if attr in out_attr.get_full_name():
                            out_angle_info = connect_mult(out_angle_info, -1, n='_neg#')
                            break

                in_plugs = out_attr.get_input()
                if in_plugs:
                    op = target.get('op', target.get('out_operation'))
                    if op == 'add':
                        add = connect_add(in_plugs, out_angle_info)
                        out_attr.connect(add)
                    elif op == 'mult':
                        mult = connect_mult(in_plugs, out_angle_info)
                        out_attr.connect(mult)
                    elif op == 'max':
                        max_exp = connect_expr('max(a, b)', a=in_plugs, b=out_angle_info)
                        out_attr.connect(max_exp)
                    elif op == 'min':
                        min_exp = connect_expr('min(a, b)', a=in_plugs, b=out_angle_info)
                        out_attr.connect(min_exp)
                    else:
                        out_attr.connect(out_angle_info)
                else:
                    out_attr.connect(out_angle_info)

    data = {
        'name': name,
        'angle_ref': angle_ref,
        'ref': ref,
        'sfx': sfx,
        'parent': parent,
        'targets': targets,
        'drivers': drivers
    }
    return data
