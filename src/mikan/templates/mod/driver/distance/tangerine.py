# coding: utf-8

import meta_nodal_py as kl
from meta_nodal_py.Imath import V3f, M44f, Euler

import mikan.tangerine.core as mk
from mikan.tangerine.lib.commands import add_plug, copy_transform
from mikan.tangerine.lib.connect import connect_sub, connect_expr, connect_driven_curve, connect_add, connect_mult
from mikan.core import cleanup_str, create_logger
from mikan.tangerine.lib.connect import safe_connect

log = create_logger()


class Mod(mk.Mod):

    def run(self):
        # get data
        name = cleanup_str(self.data['name'])

        input1 = self.data.get('input1')
        input2 = self.data.get('input2')
        if not isinstance(input1, kl.Node) or not isinstance(input2, kl.Node):
            raise mk.ModArgumentError('invalid input nodes')

        pos1 = self.data.get('pos1', [0, 0, 0])
        pos2 = self.data.get('pos2', [0, 0, 0])

        space_ref = self.data.get('space_ref', mk.Nodes.get_id('*::space.root'))
        parent = self.data.get('parent')
        if parent is None:
            parent = mk.Nodes.get_id('::rig')

        targets = self.data.get('targets', {})

        # process data
        tpl = self.get_template()
        do_flip = tpl.do_flip()

        if do_flip and isinstance(pos1, (list, tuple)):
            if not (input1.get_name()[-2] in ['_']):
                pos1[0] = pos1[0] * -1
            else:
                pos1 = [pos * -1 for pos in pos1]
        if do_flip and isinstance(pos2, (list, tuple)):
            if not (input2.get_name()[-2] in ['_']):
                pos2[0] = pos2[0] * -1
            else:
                pos2 = [pos * -1 for pos in pos2]

        sfx = self.get_template_id()
        if '.' in sfx:
            sfx = '_' + '_'.join(sfx.split('.')[1:])
        else:
            sfx = ''

        # build
        out_args = create_mod_distance_tang(input1, input2, name, pos1, pos2, space_ref, targets, parent, sfx, do_flip)
        for i, target in enumerate(targets):
            self.set_id(out_args['drivers'][i], 'distance', '{}.{}'.format(self.data['name'], target))

        # if 'debug' in self.modes:
        #     out_helper = create_mod_distance_helper(out_args)
        #     self.set_id(out_helper['root'], 'distance.helper.{}'.format(name))


def create_mod_distance_tang(input1, input2, name, pos1, pos2, space_ref, targets, parent, sfx, is_mirror):
    # BUILD DRIVER LOC
    driver1 = kl.SceneGraphNode(input1, 'root_distance_{}_driver1{}'.format(name, sfx))
    driver2 = kl.SceneGraphNode(input2, 'root_distance_{}_driver2{}'.format(name, sfx))

    if isinstance(pos1, kl.SceneGraphNode):
        copy_transform(pos1, driver1, t=True, r=True)
    elif isinstance(pos1, (list, tuple)):
        p = V3f(pos1[0], pos1[1], pos1[2])
        xfo = M44f(p, V3f(0, 0, 0), V3f(1, 1, 1), Euler.XYZ)
        driver1.transform.set_value(xfo)
    else:
        copy_transform(input1, driver1, t=True, r=True)

    if isinstance(pos2, kl.SceneGraphNode):
        copy_transform(pos2, driver2, t=True, r=True)
    elif isinstance(pos2, (list, tuple)):
        p = V3f(pos2[0], pos2[1], pos2[2])
        xfo = M44f(p, V3f(0, 0, 0), V3f(1, 1, 1), Euler.XYZ)
        driver2.transform.set_value(xfo)
    else:
        copy_transform(input2, driver2, t=True, r=True)

    # BUILD distanceBetween
    db = kl.Distance(driver1, '_db#')
    db_input1 = driver1.world_transform
    db_input2 = driver2.world_transform

    if space_ref:
        im = kl.InverseM44f(driver1, '_im#')
        im.input[0].connect(space_ref.world_transform)

        mm1 = kl.MultM44f(driver1, '_mmx', 2)
        mm2 = kl.MultM44f(driver1, '_mmx', 2)
        mm1.input[0].connect(driver1.world_transform)
        mm2.input[0].connect(driver2.world_transform)
        mm1.input[1].connect(im.output)
        mm2.input[1].connect(im.output)

        db_input1 = mm1.output
        db_input2 = mm2.output

    # TANG - CONVERT MATRIX TO VECTOR
    M44_to_t_1 = kl.TransformToSRTNode(driver1, '_M44ToTranslate#')
    M44_to_t_2 = kl.TransformToSRTNode(driver1, '_M44ToTranslate#')

    M44_to_t_1.transform.connect(db_input1)
    M44_to_t_2.transform.connect(db_input2)

    db.input1.connect(M44_to_t_1.translate)
    db.input2.connect(M44_to_t_2.translate)

    # BUILD distanceBetween world (EXTRA) - USE FOR THE HELPER SETTING ( IN MAYA )
    # dbw = pm.createNode('distanceBetween', n='_db#')
    # driver1.worldMatrix >> dbw.inMatrix1
    # driver2.worldMatrix >> dbw.inMatrix2

    drivers = []
    if targets:
        for key, target in targets.items():
            base_name = '{}_{}'.format(name, key)
            # BUILD network
            driver = kl.Node(driver1, 'driver_distance_{}{}'.format(base_name, sfx))
            drivers.append(driver)

            # ADD ATTR
            add_plug(driver, 'in_distance_world', float, k=1)  # , default_value=1, min_value=0.1, max_value=1, nice_name='Min Stretch)'
            add_plug(driver, 'in_distance', float, k=1)
            add_plug(driver, 'target_distance', float, k=1)
            add_plug(driver, 'delta_distance', float, k=1)

            add_plug(driver, 'falloff_before', float, k=1)
            add_plug(driver, 'falloff_after', float, k=1)
            add_plug(driver, 'out_normalize', float, k=1)
            add_plug(driver, 'weight', float, k=1)
            add_plug(driver, 'out_weighted', float, k=1)

            # SET
            driver.target_distance.set_value(target['target_distance'])
            driver.falloff_before.set_value(target['falloff_before'])
            driver.falloff_after.set_value(target['falloff_after'])

            weight_value = target.get('weight', 1.0)

            if isinstance(weight_value, (int, float)):
                driver.weight.set_value(weight_value)
            else:
                safe_connect(weight_value, driver.weight)

            # CONNECT
            driver.in_distance.connect(db.output)
            # driver.in_distance_world.connect( db.output ) # - USE FOR THE HELPER SETTING ( IN MAYA )
            connect_sub(driver.in_distance, driver.target_distance, driver.delta_distance)

            condPos = connect_expr(' falloff != 0 ? delta / clamp(falloff, 0.001 , BIG ) : 0 ', delta=driver.delta_distance, falloff=driver.falloff_after, BIG=99999999)
            condNeg = connect_expr(' falloff != 0 ? delta / clamp(falloff, 0.001 , BIG ) : 0 ', delta=driver.delta_distance, falloff=driver.falloff_before, BIG=99999999)
            outCond = connect_expr(' delta > 0 ? condPos : condNeg * -1 ', delta=driver.delta_distance, condPos=condPos, condNeg=condNeg)
            # connect_driven_curve( outCond, in_node=driver.out_normalize, keys={ -1:0 , 0:1 , 1:0 } , key_style = target['falloff_tangeant'] ) # in_node & key_style     not existig in tang version
            tan = target.get('falloff_tangent', target.get('falloff_tangeant', 'linear'))
            connect_driven_curve(outCond, driver.out_normalize, keys={-1: 0, 0: 1, 1: 0}, tangent_mode=tan, pre='constant', post='constant')

            out_multy = connect_mult(driver.out_normalize, driver.weight, driver.out_weighted, n='_multi#')

            op = target.get('op', target.get('out_operation'))
            ops = [op for i in range(0, len(target['remaps']))]
            if 'out_operations' in target:
                for i, out_attrA in enumerate(target['remaps']):
                    out_attrA_str = '{}'.format(out_attrA.get_full_name())
                    for j, out_attrB in enumerate(target['out_operations']):
                        out_attrB_str = '{}'.format(out_attrB.get_full_name())
                        if out_attrA_str == out_attrB_str:
                            ops[i] = target['out_operations'][out_attrB]
                            break

            for i, out_attr in enumerate(list(target['remaps'])):

                # ADD ATTR
                out_min = add_plug(driver, 'out{}_min'.format(i), float, k=1)
                out_max = add_plug(driver, 'out{}_max'.format(i), float, k=1)
                out_remap = add_plug(driver, 'out{}'.format(i), float, k=1)

                # SET
                out_min.set_value(target['remaps'][out_attr][0])
                out_max.set_value(target['remaps'][out_attr][1])

                # CONNECT
                remap = connect_expr(' remap(v, 0, 1, min2, max2) ', v=driver.out_weighted, min2=out_min, max2=out_max)
                out_remap.connect(remap)

                if is_mirror:
                    attrs_to_flip = ['translate.x', 'translate.y', 'translate.z']
                    for attr in attrs_to_flip:
                        if attr in out_attr.get_full_name():
                            out_remap = connect_mult(out_remap, -1, n='_neg#')
                            break

                inPlugs = out_attr.get_input()
                if inPlugs:
                    if ops[i] == 'add':
                        add = connect_add(inPlugs, out_remap)
                        out_attr.connect(add)
                    elif ops[i] == 'mult':
                        mult = connect_mult(inPlugs, out_remap)
                        out_attr.connect(mult)
                    elif ops[i] == 'max':
                        max_exp = connect_expr('max(a, b)', a=inPlugs, b=out_remap)
                        out_attr.connect(max_exp)
                    elif ops[i] == 'min':
                        min_exp = connect_expr('min(a, b)', a=inPlugs, b=out_remap)
                        out_attr.connect(min_exp)
                    else:
                        out_attr.connect(out_remap)
                else:
                    out_attr.connect(out_remap)

    out_args = {'name': name, 'driver1': driver1, 'driver2': driver2, 'sfx': sfx, 'parent': parent, 'targets': targets, 'drivers': drivers}
    return out_args
