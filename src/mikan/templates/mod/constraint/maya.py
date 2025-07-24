# coding: utf-8

from six import string_types

from mikan.maya import cmds as mc
import mikan.maya.cmdx as mx

import mikan.maya.core as mk
from mikan.maya.lib.rig import fix_orient_constraint_flip, axis_to_vector
from mikan.core import flatten_list
from mikan.core.logger import create_logger

log = create_logger()


class Mod(mk.Mod):

    def run(self):

        # get nodes
        nodes = self.data.get('nodes', self.data.get('node', self.node))
        nodes = [n for n in list(flatten_list([nodes])) if n]
        if not nodes:
            raise mk.ModArgumentError('node list to constrain is empty')

        # targets
        targets = []
        target = self.data.get('target')
        if target:
            targets.append(target)
        targets = list(flatten_list(targets + [self.data.get('targets', [])]))
        targets = [target for target in targets if isinstance(target, mx.DagNode)]

        if not targets:
            raise mk.ModArgumentError('targets missing')

        # weights
        weights = None
        if 'weights' in self.data:
            weights = self.data['weights']
        if not isinstance(weights, list) or len(weights) != len(targets):
            weights = [1.0] * len(targets)

        # branch reverse?
        flip = 1
        if bool(self.data.get('flip')):
            tpl = self.get_template()
            if tpl and tpl.do_flip():
                flip = -1

        # command
        x = None
        if 'type' not in self.data:
            raise mk.ModArgumentError('type missing')
        cmd = self.data['type']
        if cmd not in ('point', 'orient', 'aim', 'parent', 'scale'):
            raise mk.ModArgumentError('invalid type')
        kw = {}

        # offset
        kw['mo'] = bool(self.data.get('maintain_offset'))
        if not kw['mo']:
            if 'offset' in self.data:
                kw['o'] = mx.Vector(self.data['offset'])

        # skip
        def parse_skip(s):
            if isinstance(s, str):
                return s.lower()
            elif isinstance(s, list):
                return ''.join(s).lower()
            return ''

        skip_translate = parse_skip(self.data.get('skip_translate', self.data.get('skip', '')))
        skip_rotate = parse_skip(self.data.get('skip_rotate', self.data.get('skip', '')))
        skip_scale = parse_skip(self.data.get('skip_scale', self.data.get('skip', '')))

        # build loop
        for node in nodes:

            # blend contraint
            do_blend_translate = False
            input_translate = [None, None, None]
            input_translate_vector = None

            if cmd in ['point', 'parent'] and skip_translate != 'xyz':
                do_blend_translate = bool(self.data.get('blend', False))

                _t = node['t'].input(plug=1)
                if _t is not None:
                    input_translate_vector = _t
                    do_blend_translate = True

                for i, dim in enumerate('xyz'):
                    _t = node['t' + dim].input(plug=1)
                    if _t is not None:
                        input_translate[i] = _t
                        do_blend_translate = True

            do_blend_rotate = False
            input_rotate = [None, None, None]
            input_rotate_vector = None

            if cmd in ['orient', 'aim', 'parent'] and skip_rotate != 'xyz':
                do_blend_rotate = bool(self.data.get('blend', False))

                _r = node['r'].input(plug=1)
                if _r is not None:
                    input_rotate_vector = _r
                    do_blend_rotate = True

                for i, dim in enumerate('xyz'):
                    _r = node['r' + dim].input(plug=1)
                    if _r is not None:
                        input_rotate[i] = _r
                        do_blend_rotate = True

            do_blend_scale = False
            input_scale = [None, None, None]
            input_scale_vector = None

            if cmd in ['scale'] and skip_scale != 'xyz':
                do_blend_scale = bool(self.data.get('blend', False))

                _s = node['s'].input(plug=1)
                if _s is not None:
                    input_scale_vector = _s
                    do_blend_scale = True

                for i, dim in enumerate('xyz'):
                    _s = node['s' + dim].input(plug=1)
                    if _s is not None:
                        input_scale[i] = _s
                        do_blend_scale = True

            # check blend
            if do_blend_translate:
                if 'blend_translate' in node:
                    self.log_error('cannot constrain "{}": translation is already blended'.format(node))
                    continue

            if do_blend_rotate:
                if 'blend_rotate' in node:
                    self.log_error('cannot constrain "{}": rotation is already blended'.format(node))
                    continue

            if do_blend_scale:
                if 'blend_scale' in node:
                    self.log_error('cannot constrain "{}": scale is already blended'.format(node))
                    continue

            # disconnect former inputs
            _t = input_translate_vector
            if _t is not None:
                _t // node['t']

            for i, dim in enumerate('xyz'):
                _t = input_translate[i]
                if _t is not None:
                    _node = _t.node()
                    if _node.is_a(mx.tUnitConversion):
                        input_translate[i] = _node['input'].input(plug=1)
                        mx.delete(_node)
                    else:
                        _t // node['t' + dim]

            _r = input_rotate_vector
            if _r is not None:
                _r // node['r']

            for i, dim in enumerate('xyz'):
                _r = input_rotate[i]
                if _r is not None:
                    _node = _r.node()
                    if _node.is_a(mx.tUnitConversion):
                        input_rotate[i] = _node['input'].input(plug=1)
                        mx.delete(_node)
                    else:
                        _r // node['r' + dim]

            _s = input_scale_vector
            if _s is not None:
                _s // node['s']

            for i, dim in enumerate('xyz'):
                _s = input_scale[i]
                if _s is not None:
                    _node = _s.node()
                    if _node.is_a(mx.tUnitConversion):
                        input_scale[i] = _node['input'].input(plug=1)
                        mx.delete(_node)
                    else:
                        _s // node['s' + dim]

            # apply constraint
            if cmd == 'point':
                if skip_translate:
                    kw['skip'] = list(skip_translate)
                for i, tgt in enumerate(targets):
                    x = mc.pointConstraint(str(tgt), str(node), w=weights[i], **kw)
                    x = mx.encode(x[0])

            elif cmd == 'orient':
                if skip_rotate:
                    kw['skip'] = list(skip_rotate)
                for i, tgt in enumerate(targets):
                    x = mc.orientConstraint(str(tgt), str(node), w=weights[i], **kw)
                    x = mx.encode(x[0])
                if len(targets) > 1:
                    fix_orient_constraint_flip(x)

            elif cmd == 'parent':
                if skip_translate:
                    kw['st'] = list(skip_translate)
                if skip_rotate:
                    kw['sr'] = list(skip_rotate)
                if 'o' in kw:
                    del kw['o']

                if kw['mo'] and len(targets) > 1:
                    _targets = []
                    for i, tgt in enumerate(targets):
                        with mx.DagModifier() as md:
                            _tgt = md.create_node(mx.tTransform, parent=node, name='_tgt_{}'.format(node.name()))
                        mc.parent(str(_tgt), str(tgt))
                        _targets.append(_tgt)
                    targets = _targets
                x = mx.cmd(mc.parentConstraint, targets, node, **kw)
                x = mx.encode(x[0])
                if len(targets) > 1:
                    x['interpType'] = 2
                for i, w in enumerate(weights):
                    x['w{}'.format(i)] = w

            elif cmd == 'aim':
                if skip_rotate:
                    kw['skip'] = list(skip_rotate)

                kw['aim'] = self.data.get('aim', [1, 0, 0])
                if isinstance(kw['aim'], string_types):
                    kw['aim'] = axis_to_vector(kw['aim'])
                kw['aim'] = mx.Vector(kw['aim']) * flip

                kw['u'] = self.data.get('up', [0, 1, 0])
                if isinstance(kw['u'], string_types):
                    kw['u'] = axis_to_vector(kw['u'])
                kw['u'] = mx.Vector(kw['u']) if kw['u'] else mx.Vector()
                kw['u'] *= flip

                kw['wu'] = self.data.get('up_vector', [0, 0, 0])
                if isinstance(kw['wu'], mx.Node):
                    self.log_error('invalid up vector ({})'.format(kw['wu']))
                    kw['wu'] = None
                if isinstance(kw['wu'], string_types):
                    kw['wu'] = axis_to_vector(kw['wu'])
                kw['wu'] = mx.Vector(kw['wu']) if kw['wu'] else mx.Vector()

                kw['wuo'] = self.data.get('up_object')

                kw['wut'] = 'none'  # none by default
                if kw['wuo']:
                    if kw['wu'].length() == 0:
                        kw['wut'] = 'object'
                    else:
                        kw['wut'] = 'objectrotation'
                else:
                    if kw['u'].length() > 0.001:
                        kw['wut'] = 'vector'

                if not kw['wuo']:
                    del kw['wuo']

                for i, tgt in enumerate(targets):
                    x = mx.cmd(mc.aimConstraint, tgt, node, w=weights[i], **kw)
                    x = mx.encode(x[0])

            elif cmd == 'scale':
                if skip_scale:
                    kw['skip'] = list(skip_scale)
                for i, tgt in enumerate(targets):
                    x = mc.scaleConstraint(str(tgt), str(node), w=weights[i], **kw)
                    x = mx.encode(x[0])

            if x:
                self.set_id(x, 'constraint.{}'.format(cmd))

            # blend
            if do_blend_translate:
                with mx.DGModifier() as md:
                    pb = md.create_node(mx.tPairBlend, name='_blend_translate#')
                pb['inTranslate1'] = node['t']
                pb['inTranslate2'] = node['t']

                for i, dim in enumerate('xyz'):
                    _t = node['t' + dim].input(plug=1)
                    if _t is not None:
                        _t >> pb['it' + dim + '2']

                _t = input_translate_vector
                if _t is not None:
                    _t >> pb['it1']

                for i, _t in enumerate(input_translate):
                    if _t is not None:
                        _t >> pb['it' + 'xyz'[i] + '1']

                for dim in 'xyz':
                    if dim not in skip_translate or input_translate[i] is not None:
                        pb['ot' + dim] >> node['t' + dim]

                node.add_attr(mx.Double('blend_translate', default=1, min=0, max=1, keyable=True))
                node['blend_translate'] >> pb['weight']

            if do_blend_rotate:
                with mx.DGModifier() as md:
                    pb = md.create_node(mx.tPairBlend, name='_blend_rotate#')
                pb['inRotate1'] = node['r']
                pb['inRotate2'] = node['r']
                pb['rotInterpolation'] = 1  # quaternions

                for i, dim in enumerate('xyz'):
                    _r = node['r' + dim].input(plug=1)
                    if _r is not None:
                        _r >> pb['ir' + dim + '2']

                _r = input_rotate_vector
                if _r is not None:
                    _r >> pb['ir1']

                for i, _r in enumerate(input_rotate):
                    if _r is not None:
                        _r >> pb['ir' + 'xyz'[i] + '1']

                for dim in 'xyz':
                    if dim not in skip_rotate or input_rotate[i] is not None:
                        pb['or' + dim] >> node['r' + dim]

                node.add_attr(mx.Double('blend_rotate', default=1, min=0, max=1, keyable=True))
                node['blend_rotate'] >> pb['weight']

            if do_blend_scale:
                with mx.DGModifier() as md:
                    pb = md.create_node(mx.tPairBlend, name='_blend_scale#')
                pb['inTranslate1'] = node['s']
                pb['inTranslate2'] = node['s']

                for i, dim in enumerate('xyz'):
                    _s = node['s' + dim].input(plug=1)
                    if _s is not None:
                        _s >> pb['it' + dim + '2']

                _s = input_scale_vector
                if _s is not None:
                    _s >> pb['it1']

                for i, _s in enumerate(input_scale):
                    if _s is not None:
                        _s >> pb['it' + 'xyz'[i] + '1']

                for i, dim in enumerate('xyz'):
                    if dim not in skip_scale or input_scale[i] is not None:
                        pb['ot' + dim] >> node['s' + dim]

                node.add_attr(mx.Double('blend_scale', default=1, min=0, max=1, keyable=True))
                node['blend_scale'] >> pb['weight']
