# coding: utf-8

import re
import meta_nodal_py as kl
from meta_nodal_py.Imath import V3f

import mikan.tangerine.core as mk
from mikan.tangerine.lib.rig import *
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
        targets = [target for target in targets if isinstance(target, kl.SceneGraphNode)]

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
        kw = dict(weights=weights)

        # offset
        kw['mo'] = bool(self.data.get('maintain_offset'))

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
        kw['force_blend'] = self.data.get('blend', False)

        # apply constraint
        for node in nodes:

            if cmd == 'point':
                if skip_translate:
                    kw['axes'] = re.sub(f'[{skip_translate}]', '', 'xyz')
                x = point_constraint(targets, node, **kw)

            elif cmd == 'orient':
                if skip_rotate:
                    kw['axes'] = re.sub(f'[{skip_rotate}]', '', 'xyz')
                x = orient_constraint(targets, node, **kw)

            elif cmd == 'parent':
                if skip_translate:
                    kw['translate_axes'] = re.sub(f'[{skip_translate}]', '', 'xyz')
                    if skip_translate == 'xyz':
                        kw['skip_translation'] = True
                if skip_rotate:
                    kw['rotate_axes'] = re.sub(f'[{skip_rotate}]', '', 'xyz')
                    if skip_rotate == 'xyz':
                        kw['skip_rotation'] = True
                x = parent_constraint(targets, node, **kw)

            elif cmd == 'aim':
                if skip_rotate:
                    kw['axes'] = re.sub(f'[{skip_rotate}]', '', 'xyz')

                kw['aim_vector'] = self.data.get('aim', [1, 0, 0])
                if isinstance(kw['aim_vector'], str):
                    kw['aim_vector'] = axis_to_vector(kw['aim_vector'])
                kw['aim_vector'] = V3f(*kw['aim_vector']) * flip

                kw['up_vector'] = self.data.get('up', [0, 1, 0])
                if isinstance(kw['up_vector'], str):
                    kw['up_vector'] = axis_to_vector(kw['up_vector'])
                if isinstance(kw['up_vector'], kl.Node):
                    self.log_error('invalid up vector ({})'.format(kw['up_vector']))
                    kw['up_vector'] = None
                kw['up_vector'] = V3f(*kw['up_vector']) if kw['up_vector'] else V3f()
                kw['up_vector'] *= flip

                if 'up_vector' not in self.data and 'up_object' not in self.data:
                    kw['up_vector'] = V3f()

                kw['up_vector_world'] = self.data.get('up_vector', [0, 0, 0])
                if isinstance(kw['up_vector_world'], str):
                    kw['up_vector_world'] = axis_to_vector(kw['up_vector_world'])
                kw['up_vector_world'] = V3f(*kw['up_vector_world']) if kw['up_vector_world'] else V3f()

                kw['up_object'] = self.data.get('up_object')

                if kw['up_object']:
                    if kw['up_vector_world'].length():
                        # object rotation up
                        kw['up_vector_object'] = kw['up_vector_world']
                        kw['up_vector_world'] = V3f(0, 0, 0)

                x = aim_constraint(targets, node, **kw)

            elif cmd == 'scale':
                if skip_scale:
                    kw['axes'] = re.sub(f'[{skip_scale}]', '', 'xyz')
                x = scale_constraint(targets, node, **kw)

            if x and x.get_plug('transform_shortest_in'):
                bw = x.transform_shortest_in.get_input()
                if bw is not None:
                    bw.set_value(True)

            if x:
                self.set_id(x, 'constraint.{}'.format(cmd))
