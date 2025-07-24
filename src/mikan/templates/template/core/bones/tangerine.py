# coding: utf-8

import meta_nodal_py as kl
from meta_nodal_py.Imath import V3f, M44f, Euler

from mikan.core.logger import create_logger

import mikan.tangerine.core as mk
from mikan.tangerine.lib.commands import copy_transform
from mikan.tangerine.lib.rig import orient_joint, axis_to_vector, get_stretch_axis, str_to_rotate_order

log = create_logger()


class Template(mk.Template):

    def build_template(self, data):
        self.node.rename('tpl_{}1'.format(self.name))

        number = data['number']
        bones = [self.node]

        for i in range(number):
            j = kl.Joint(bones[-1], 'tpl_{}{}'.format(self.name, i + 2))
            bones.append(j)

        bones[0].transform.set_value(M44f(V3f(*data['root']), V3f(0, 0, 0), V3f(1, 1, 1), Euler.XYZ))
        for j in bones[1:]:
            j.transform.set_value(M44f(V3f(*data['transform']), V3f(0, 0, 0), V3f(1, 1, 1), Euler.XYZ))

        bones[-1].rename('tpl_{}_tip'.format(self.name))

    def build_rig(self):

        tpl_chain = self.get_structure('chain')
        if len(tpl_chain) < 2:
            raise RuntimeError('/!\\ template chain must have at least 2 joints')

        rotate_order = self.get_opt('rotate_order')
        hook = self.get_hook()

        # orient chain
        ref_joints = []
        for i, tpl in enumerate(tpl_chain):
            j = kl.Joint(hook, 'ref_joint')
            if i > 0:
                j.reparent(ref_joints[-1])
            ref_joints.append(j)

            copy_transform(tpl, j, t=1, r=1)
            if self.get_opt('orient') == 'parent':
                copy_transform(hook, j, r=1)
            elif self.get_opt('orient') == 'world':
                copy_transform([], j, r=1)

        if self.get_opt('orient') == 'auto':
            aim_axis = self.get_branch_opt('aim_axis')
            up_axis = self.get_opt('up_axis')

            up_dir = self.get_opt('up_dir')
            if up_dir == 'auto':
                up_auto = self.get_opt('up_auto')
                up_auto = {'average': 0, 'each': 1, 'first': 2, 'last': 3}[up_auto]
                orient_joint(ref_joints, aim=aim_axis, up=up_axis, up_auto=up_auto)
            else:
                up_dir = axis_to_vector(up_dir)
                orient_joint(ref_joints, aim=aim_axis, up=up_axis, up_dir=up_dir)

            # get twist axis (rotate order)
            if 'y' in aim_axis:
                bi_axis = 'z'
                if 'z' in up_axis:
                    bi_axis = 'x'
            elif 'x' in aim_axis:
                bi_axis = 'y'
                if 'y' in up_axis:
                    bi_axis = 'z'
            else:
                bi_axis = 'x'
                if 'x' in up_axis:
                    bi_axis = 'y'

        elif rotate_order == 'auto':
            # guess axis from given chain
            _axis = get_stretch_axis(tpl_chain)
            if not _axis:
                raise RuntimeError('/!\\ cannot find orientation from template')
            aim_axis, up_axis, bi_axis = _axis
            if self.do_flip():
                aim_axis = self.branch_opt(aim_axis)
                up_axis = self.branch_opt(up_axis)

        if rotate_order == 'auto':
            rotate_order = aim_axis[-1] + up_axis[-1] + bi_axis[-1]
        rotate_order = str_to_rotate_order(rotate_order)

        # build
        nodes = self.build_chain(ref_joints[:-1], rotate_order=rotate_order)
        ref_joints[0].remove_from_parent()

        # chain tip
        end_name = 'end_' + self.name + self.get_branch_suffix()

        end = kl.Joint(nodes[-1]['sk'], end_name)
        end.scale_compensate.set_value(False)
        copy_transform(tpl_chain[-1], end, t=1)
        self.set_hook(tpl_chain[-1], end, 'hooks.tip')

        self.set_id(end, 'tip')

        # hooks
        for i, tpl in enumerate(tpl_chain[:-1]):
            self.set_hook(tpl_chain[i], nodes[i]['j'], 'hooks.{}'.format(i))
