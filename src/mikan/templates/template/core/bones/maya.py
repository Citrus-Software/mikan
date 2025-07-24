# coding: utf-8

from mikan.maya import cmds as mc
import mikan.maya.cmdx as mx

import mikan.maya.core as mk
from mikan.maya.lib.rig import (
    copy_transform, apply_transform, orient_joint,
    axis_to_vector, get_stretch_axis, fix_inverse_scale
)


class Template(mk.Template):

    def build_template(self, data):
        number = data['number']
        bones = [self.node]

        with mx.DagModifier() as md:
            for i in range(number):
                j = md.create_node(mx.tJoint, parent=bones[-1], name='tpl_{}{}'.format(self.name, i + 2))
                bones.append(j)

        bones[0]['t'] = data['root']
        for j in bones[1:]:
            j['t'] = data['transform']

        fix_inverse_scale(list(self.node.descendents()))

    def rename_template(self):
        chain = self.get_structure('chain')
        last = len(chain) - 1

        for i, j in enumerate(chain):
            if i == 0:
                continue
            if j.is_referenced():
                continue
            sfx = 'tip' if i == last else i + 1
            j.rename('tpl_{}_{}'.format(self.name, sfx))

    def build_rig(self):

        n_chain = self.name
        tpl_chain = self.get_structure('chain')
        if len(tpl_chain) < 2:
            raise RuntimeError('/!\\ template chain must have at least 2 joints')

        rotate_order = self.get_opt('rotate_order')
        hook = self.get_hook()

        # orient chain
        ref_joints = []
        for i, tpl in enumerate(tpl_chain):
            with mx.DagModifier() as md:
                j = md.create_node(mx.tJoint, parent=hook, name='dummy_{}{}'.format(n_chain, i))
            if i > 0:
                mc.parent(str(j), str(ref_joints[-1]))
            ref_joints.append(j)

            copy_transform(tpl, j, t=True, r=True)
            if self.get_opt('orient') == 'parent':
                copy_transform(hook, j, r=True)
            elif self.get_opt('orient') == 'world':
                apply_transform(j, mx.Matrix4(), r=True)

        if self.get_opt('orient') == 'auto':
            aim_axis = self.get_branch_opt('aim_axis')
            up_axis = self.get_opt('up_axis')

            up_dir = self.get_opt('up_dir')
            if up_dir == 'auto':
                up_auto = self.get_opt('up_auto')
                up_auto = {'average': 0, 'each': 1, 'first': 2, 'last': 3}[up_auto]
                orient_joint(mx.decode(ref_joints), aim=aim_axis, up=up_axis, up_auto=up_auto)
            else:
                up_dir = axis_to_vector(up_dir)
                orient_joint(mx.decode(ref_joints), aim=aim_axis, up=up_axis, up_dir=up_dir)

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
        rotate_order = rotate_order.lower()
        rotate_order = mx.Euler.orders[rotate_order]

        # build
        nodes = self.build_chain(ref_joints[:-1], rotate_order=rotate_order)

        # mx.delete(ref_joints)
        for j in ref_joints:
            j.add_attr(mx.Message('kill_me'))

        # chain tip
        end_name = 'end_' + self.name + self.get_branch_suffix()

        with mx.DagModifier() as md:
            end = md.create_node(mx.tJoint, parent=nodes[-1]['j'], name=end_name)
        nodes[-1]['j']['scale'] >> end['inverseScale']
        end['ssc'] = False
        copy_transform(tpl_chain[-1], end, t=True)
        self.set_hook(tpl_chain[-1], end, 'hooks.tip')

        self.set_id(end, 'tip')

        # cleanup
        fix_inverse_scale(list(nodes[0]['root'].descendents()))

        # hooks
        for i, tpl in enumerate(tpl_chain[:-1]):
            self.set_hook(tpl_chain[i], nodes[i]['j'], 'hooks.{}'.format(i))
