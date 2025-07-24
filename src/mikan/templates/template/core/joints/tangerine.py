# coding: utf-8

import meta_nodal_py as kl
from meta_nodal_py.Imath import V3f, M44f, Euler

from mikan.core import re_is_int
import mikan.tangerine.core as mk
from mikan.tangerine.lib import *
from mikan.tangerine.lib.rig import *


class Template(mk.Template):

    def build_template(self, data):
        self.node.rename('tpl_{}'.format(self.name))

        number = data['number']
        joints = [self.node]

        if number > 1:
            for i in range(number - 1):
                j = kl.Joint(joints[-1], 'tpl_{}{}'.format(self.name, len(joints) + 1))
                joints.append(j)

        joints[0].transform.set_value(M44f(V3f(*data['root']), V3f(0, 0, 0), V3f(1, 1, 1), Euler.XYZ))
        for j in joints[1:]:
            j.transform.set_value(M44f(V3f(*data['transform']), V3f(0, 0, 0), V3f(1, 1, 1), Euler.XYZ))

    def build_rig(self):

        tpl_chain = self.get_structure('chain')
        unchain = self.get_opt('unchain')
        do_joint = self.get_opt('type') == 'joint'

        nodes = self.build_chain(tpl_chain, do_joint=do_joint, unchain=unchain)

        # hooks
        last = 'j'
        if not do_joint:
            last = 'c'
            _chain, chain_sub = self.get_chain()
            if chain_sub:
                last = chain_sub[-1]

        for i, tpl in enumerate(tpl_chain):
            self.set_hook(tpl_chain[i], nodes[i][last], 'hooks.{}'.format(i))

    def get_chain(self):
        chain = self.get_opt('add_nodes')
        chain_sub = []
        if not chain:
            chain = []
        if isinstance(chain, str):
            chain = [chain]
        if 'c' in chain:
            chain_sub = chain[chain.index('c') + 1:]
            chain = chain[:chain.index('c')]
        if self.get_opt('do_pose') and 'pose' not in chain + chain_sub:
            chain.append('pose')

        return chain, chain_sub

    def build_chain(self, tpl_chain, hook=None, chain=None, suffixes=None, do_flip=True, do_joint=True, do_skin=None, rotate_order=None, unchain=False, register=True):

        # opts
        if hook is None:
            hook = self.get_hook()

        n_end = self.get_branch_suffix()
        n_chain = self.name

        if rotate_order is None:
            rotate_order = self.get_opt('rotate_order')
            rotate_order = str_to_rotate_order(rotate_order)

        _chain, chain_sub = self.get_chain()
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

                n['root'] = kl.Joint(parent, 'root_' + n_chain + n_end)

                if i == 0 and self.get_opt('parent_scale'):
                    n['root'].scale_compensate.set_value(False)

                n['c'] = kl.SceneGraphNode(n['root'], 'c_' + n_chain + n_end)
                if chain:
                    for chain_id in chain:
                        n[chain_id] = kl.SceneGraphNode(n['root'], chain_id + '_' + n_chain + n_end)
                    n['x'] = kl.SceneGraphNode(n['root'], 'x_' + n_chain + n_end)
                    n['c'].reparent(n['x'])
                if chain_sub:
                    for chain_id in chain_sub:
                        n[chain_id] = kl.SceneGraphNode(n['c'], chain_id + '_' + n_chain + n_end)
                n['j'] = kl.Joint(n['root'], j_prefix + '_' + n_chain + n_end)
                n['j'].scale_compensate.set_value(False)
            else:
                parent = hook
                if i > 0 and not unchain:
                    parent = nodes[i - 1]['c']

                n['root'] = kl.SceneGraphNode(parent, 'root_' + n_chain + n_end)
                _p = n['root']
                if chain:
                    for chain_id in chain:
                        n[chain_id] = kl.SceneGraphNode(_p, chain_id + '_' + n_chain + n_end)
                        _p = n[chain_id]
                n['c'] = kl.SceneGraphNode(_p, 'c_' + n_chain + n_end)
                last = n['c']
                if chain_sub:
                    for chain_id in chain_sub:
                        n[chain_id] = kl.SceneGraphNode(last, chain_id + '_' + n_chain + n_end)
                        last = n[chain_id]
                n['j'] = kl.Joint(last, j_prefix + '_' + n_chain + n_end)

            # do skin?
            n['sk'] = n['j']

            # xfo
            copy_transform(tpl_chain[i], n['root'])
            _xfo = n['root'].transform.get_value()

            # set min scale to 1
            _s = tpl_chain[i].transform.get_value().scaling()
            _s = [_s.x, _s.y, _s.z]
            _s = V3f(_s[0] / min(_s), _s[1] / min(_s), _s[2] / min(_s))

            _xfo = M44f(_xfo.translation(), _xfo.rotation(Euler.XYZ), _s, Euler.XYZ)

            # flip orient
            if do_flip:
                _xfo = M44f(V3f(0, 0, 0), V3f(180, 0, 0), V3f(1, 1, 1), Euler.ZYX) * _xfo

            n['root'].transform.set_value(_xfo)

            # connect
            if do_joint:
                if chain or chain_sub:
                    cmx = {'rt': {}, 's': {}}
                    for chain_id in chain:
                        _rt = kl.SRTToTransformNode(n['x'], '_cmx_rt')
                        _srt = create_srt_out(n[chain_id])
                        _rt.rotate.connect(_srt.rotate)
                        _rt.rotate_order.connect(_srt.rotate_order)
                        _rt.translate.connect(_srt.translate)

                        _s = kl.SRTToTransformNode(n['x'], '_cmx_s')
                        _s.scale.connect(_srt.scale)

                        cmx['rt'][chain_id] = _rt
                        cmx['s'][chain_id] = _s

                    if chain:
                        _mmx_rt = kl.MultM44f(n['x'], '_mmx', len(chain))
                        for j, chain_id in enumerate(chain[::-1]):
                            _mmx_rt.input[j].connect(cmx['rt'][chain_id].transform)

                        n['x'].transform.connect(_mmx_rt.output)
                        # TODO: remplacer ça par un hack du srt in

                    inputs = len(chain) + len(chain_sub) + 2
                    if not chain:
                        inputs -= 1
                    _mmx = kl.MultM44f(n['sk'], '_mmx', inputs)
                    j = 0
                    for chain_id in chain_sub[::-1]:
                        _mmx.input[j].connect(n[chain_id].transform)
                        j += 1
                    for chain_id in chain[::-1]:
                        _mmx.input[j].connect(cmx['s'][chain_id].transform)
                        j += 1
                    _mmx.input[j].connect(n['c'].transform)
                    if chain:
                        _mmx.input[j + 1].connect(_mmx_rt.output)

                    n['j'].transform.connect(_mmx.output)
                else:
                    n['j'].transform.connect(n['c'].transform)

            # srt rig
            create_srt_in(n['root'], k=0, ro=rotate_order)
            create_srt_in(n['c'], k=self.get_opt('do_ctrl'), ro=rotate_order)
            if chain or chain_sub:
                for chain_id in chain + chain_sub:
                    create_srt_in(n[chain_id], k=0, ro=rotate_order)

            # registering
            if register:
                self.set_id(n['root'], 'roots.{}'.format(i))
                self.set_id(n['j'], 'j.{}'.format(i))

                if self.get_opt('do_ctrl'):
                    self.set_id(n['c'], 'ctrls.{}'.format(i))

                if do_skin:
                    self.set_id(n['sk'], 'skin.{}'.format(i))

                if chain or chain_sub:
                    for chain_id in chain + chain_sub:
                        self.set_id(n[chain_id], '{}s.{}'.format(chain_id, i))

        return nodes
