# coding: utf-8

from six import string_types

from mikan.maya import cmds as mc
import mikan.maya.cmdx as mx

from mikan.core import re_is_int
import mikan.maya.core as mk
from mikan.maya.lib.rig import copy_transform, fix_inverse_scale
from mikan.maya.lib.connect import connect_matrix


class Template(mk.Template):

    def build_template(self, data):
        number = data['number']
        joints = [self.node]

        if number > 1:
            with mx.DagModifier() as md:
                for i in range(number - 1):
                    j = md.create_node(mx.tJoint, parent=joints[-1], name='tpl_{}{}'.format(self.name, len(joints) + 1))
                    joints.append(j)

        joints[0]['t'] = data['root']
        for j in joints[1:]:
            j['t'] = data['transform']

        fix_inverse_scale(list(self.node.descendents()))

    def rename_template(self):
        chain = self.get_structure('chain')
        for i, j in enumerate(chain):
            if i == 0:
                continue
            if j.is_referenced():
                continue
            j.rename('tpl_{}_{}'.format(self.name, i + 1))

    def build_rig(self):

        tpl_chain = self.get_structure('chain')
        unchain = self.get_opt('unchain')
        do_joint = self.get_opt('type') == 'joint'

        nodes = self.build_chain(tpl_chain, do_joint=do_joint, unchain=unchain)

        # cleanup
        fix_inverse_scale(list(nodes[0]['root'].descendents()))

        # hooks
        last = 'j'
        if not do_joint:
            last = 'c'
            _chain, chain_sub, chain_trail = self.get_chain()
            if chain_sub:
                last = chain_sub[-1]

        for i, tpl in enumerate(tpl_chain):
            self.set_hook(tpl_chain[i], nodes[i][last], 'hooks.{}'.format(i))

    def get_chain(self):
        chain = self.get_opt('add_nodes')
        chain_sub = []
        chain_trail = []
        if not chain:
            chain = []
        if isinstance(chain, string_types):
            chain = [chain]
        if 'j' in chain:
            i = chain.index('j')
            chain_trail = chain[i + 1:]
            chain = chain[:i]
        if 'c' in chain:
            i = chain.index('c')
            chain_sub = chain[i + 1:]
            chain = chain[:i]
        if self.get_opt('do_pose') and 'pose' not in chain + chain_sub:
            chain.append('pose')

        return chain, chain_sub, chain_trail

    def build_chain(self, tpl_chain, hook=None, chain=None, suffixes=None, do_flip=True, do_joint=True, do_skin=None, rotate_order=None, unchain=False, register=True):

        # opts
        if hook is None:
            hook = self.get_hook()

        n_end = self.get_branch_suffix()
        n_chain = self.name

        if rotate_order is None:
            rotate_order = self.get_opt('rotate_order')
        if isinstance(rotate_order, string_types):
            rotate_order = mx.Euler.orders[rotate_order.lower()]

        _chain, chain_sub, chain_trail = self.get_chain()
        if chain is None:
            chain = _chain
        # TODO: check chain_sub

        if do_flip:
            do_flip = False
            if self.do_flip():
                do_flip = self.get_opt('flip_orient')

        if do_skin is None:
            do_skin = self.get_opt('do_skin')

        sk_prefix = 'sk'
        j_prefix = 'j'
        if do_skin:
            j_prefix = sk_prefix

        # build nodes
        nodes = []

        for i, tpl in enumerate(tpl_chain):
            n = {}
            nodes.append(n)

            n_sfx = '{sep}{i}'.format(i=i + 1, sep='' if not re_is_int.match(self.name[-1]) else '_')
            if isinstance(suffixes, (list, tuple)) and len(suffixes) == len(tpl_chain):
                n_sfx = suffixes[i]
            if len(tpl_chain) > 1:
                n_chain = self.name + n_sfx

            if do_joint:
                parent = hook
                if i > 0 and not unchain:
                    parent = nodes[i - 1]['j']

                n['root'] = mx.create_node(mx.tJoint, parent=parent, name='root_' + n_chain + n_end)
                if parent.is_a(mx.tJoint):
                    parent['scale'] >> n['root']['inverseScale']
                if i == 0 and self.get_opt('parent_scale'):
                    n['root']['ssc'] = False
                    n['root']['ssc'].lock()

                n['c'] = mx.create_node(mx.tTransform, parent=n['root'], name='c_' + n_chain + n_end)

                for chain_id in chain:
                    n[chain_id] = mx.create_node(mx.tTransform, parent=n['root'], name=chain_id + '_' + n_chain + n_end)
                if 'offsetParentMatrix' not in n['c']:
                    n['x'] = mx.create_node(mx.tTransform, parent=n['root'], name='x_' + n_chain + n_end)
                    mc.parent(str(n['c']), str(n['x']))
                for chain_id in chain_sub:
                    n[chain_id] = mx.create_node(mx.tTransform, parent=n['c'], name=chain_id + '_' + n_chain + n_end)
                n['j'] = mx.create_node(mx.tJoint, parent=n['root'], name=j_prefix + '_' + n_chain + n_end)
                n['j']['ssc'] = False
                n['j']['ssc'].lock()

            else:
                parent = hook
                if i > 0 and not unchain:
                    parent = nodes[i - 1]['c']

                n['root'] = mx.create_node(mx.tTransform, parent=parent, name='root_' + n_chain + n_end)
                _p = n['root']

                for chain_id in chain:
                    n[chain_id] = mx.create_node(mx.tTransform, parent=_p, name=chain_id + '_' + n_chain + n_end)
                    _p = n[chain_id]
                n['c'] = mx.create_node(mx.tTransform, parent=_p, name='c_' + n_chain + n_end)
                last = n['c']
                for chain_id in chain_sub:
                    n[chain_id] = mx.create_node(mx.tTransform, parent=last, name=chain_id + '_' + n_chain + n_end)
                    last = n[chain_id]
                n['j'] = mx.create_node(mx.tJoint, parent=last, name=j_prefix + '_' + n_chain + n_end)

            for chain_id in chain_trail:
                n[chain_id] = mx.create_node(mx.tJoint, parent=n['j'], name=chain_id + '_' + n_chain + n_end)

            # do skin?
            n['sk'] = n['j']

            # rotate order
            n['root']['ro'] = rotate_order
            n['j']['ro'] = rotate_order
            n['sk']['ro'] = rotate_order
            n['c']['ro'] = rotate_order
            if chain or chain_sub:
                for chain_id in chain + chain_sub:
                    n[chain_id]['ro'] = rotate_order

            # xfo
            copy_transform(tpl_chain[i], n['root'], t=True, r=True)

            # flip orient
            if do_flip:
                mc.xform(str(n['root']), r=1, os=1, ro=(180, 0, 0))

            if do_joint:
                for dim in 'xyz':
                    n['root']['jo' + dim].keyable = True

            # set min scale to 1
            _s = tpl_chain[i]['s'].as_vector()
            n['root']['s'] = _s / min(_s)
            n['root']['sh'] = (0, 0, 0)

            # connect
            if do_joint:
                if chain or chain_sub:
                    cmx = {'rt': {}, 's': {}}
                    for chain_id in chain:
                        _rt = mx.create_node(mx.tComposeMatrix, name='_cmx_rt#')
                        n[chain_id]['rotate'] >> _rt['inputRotate']
                        n[chain_id]['ro'] >> _rt['inputRotateOrder']
                        n[chain_id]['translate'] >> _rt['inputTranslate']

                        _s = mx.create_node(mx.tComposeMatrix, name='_cmx_s#')
                        n[chain_id]['scale'] >> _s['inputScale']

                        cmx['rt'][chain_id] = _rt
                        cmx['s'][chain_id] = _s

                    if chain:
                        _mmx_rt = mx.create_node(mx.tMultMatrix, name='_mmx#')
                        for j, chain_id in enumerate(chain[::-1]):
                            cmx['rt'][chain_id]['outputMatrix'] >> _mmx_rt['matrixIn'][j]

                        if 'offsetParentMatrix' in n['c']:
                            _mmx_rt['matrixSum'] >> n['c']['offsetParentMatrix']
                        else:
                            connect_matrix(_mmx_rt['matrixSum'], n['x'], s=0, sh=0)

                    _mmx = mx.create_node(mx.tMultMatrix, name='_mmx#')
                    j = 0
                    for chain_id in chain_sub[::-1]:
                        n[chain_id]['matrix'] >> _mmx['matrixIn'][j]
                        j += 1
                    for chain_id in chain[::-1]:
                        cmx['s'][chain_id]['outputMatrix'] >> _mmx['matrixIn'][j]
                        j += 1
                    n['c']['matrix'] >> _mmx['matrixIn'][j]
                    if chain:
                        _mmx_rt['matrixSum'] >> _mmx['matrixIn'][j + 1]

                    connect_matrix(_mmx['matrixSum'], n['j'])
                else:
                    connect_matrix(n['c']['matrix'], n['j'])

            # skin gizmo
            if n['root'].is_a(mx.tJoint):
                n['root']['radius'] = 0.5
            n['j']['drawStyle'] = 2
            if do_skin:
                n['sk']['drawStyle'] = 0
                n['sk']['radius'] = 0.5

            # registering
            if register:
                self.set_id(n['root'], 'roots.{}'.format(i))
                self.set_id(n['j'], 'j.{}'.format(i))

                if self.get_opt('do_ctrl'):
                    self.set_id(n['c'], 'ctrls.{}'.format(i))
                else:
                    self.set_id(n['c'], 'nodes.{}'.format(i))

                if do_skin:
                    self.set_id(n['sk'], 'skin.{}'.format(i))

                for chain_id in chain + chain_sub + chain_trail:
                    self.set_id(n[chain_id], '{}s.{}'.format(chain_id, i))

        return nodes
