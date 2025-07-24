# coding: utf-8

import meta_nodal_py as kl

import mikan.tangerine.core as mk
from mikan.core.prefs import Prefs
from mikan.tangerine.lib.commands import add_plug, copy_transform
from mikan.tangerine.lib.connect import connect_reverse, connect_add, connect_expr
from mikan.core import flatten_list, cleanup_str, create_logger

log = create_logger()


class Mod(mk.Mod):

    def run(self):

        # get nodes
        nodes = self.data.get('nodes', self.data.get('node', self.node))
        nodes = [n for n in list(flatten_list([nodes])) if n]
        if not nodes:
            raise mk.ModArgumentError('node list to hook is empty')

        # targets
        targets = self.data.get('targets', self.data.get('target'))
        targets = [n for n in list(flatten_list([targets])) if n]
        if not targets:
            raise mk.ModArgumentError('targets missing')

        # name
        if 'name' in self.data:
            name = cleanup_str(self.data['name'])
        else:
            names = []
            for tgt in targets:
                if tgt.get_dynamic_plug('gem_id'):
                    n = tgt.gem_id.get_value().split(';')[0]
                    n = n.replace('::', '_')
                    n = n.replace('.', '_')
                    n = n.replace('!', '')
                    names.append(n)
                else:
                    names.append(str(tgt))
            name = '_'.join(names)

        sfx = self.get_template_id()
        if '.' in sfx:
            sfx = '_' + '_'.join(sfx.split('.')[1:])
        else:
            sfx = ''

        # constrained node
        do_group = self.data.get('group', False)
        if Prefs.get('mod/hook/self', False):
            do_group = not self.data.get('self', False)

        if do_group:
            parent = self.data.get('parent', nodes[0].get_parent() if nodes else None)
            hook = kl.SceneGraphNode(parent, 'hook_{}{}'.format(name, sfx))
            copy_transform(targets[0], hook)
            hooks = [hook]
        else:
            hooks = nodes

        # weights
        weights = self.data.get('weight', 1)
        if 'weights' in self.data:
            weights = self.data['weights']
        if isinstance(weights, (int, float)):
            weights = [weights] * len(targets)
        if not isinstance(weights, list) or len(weights) != len(targets):
            weights = [1.0] * len(targets)
            self.log_warning('weight list not valid')

        s = sum(weights)
        if len(weights) > 1 and s != 1 and s != 0:
            for i in range(len(weights)):
                weights[i] *= 1. / s

        do_offset = self.data.get('maintain_offset', True)

        for hook in hooks:

            # offsets
            xfos = []
            for target in targets:
                if do_offset:
                    omx = hook.world_transform.get_value() * target.world_transform.get_value().inverse()
                    mmx = kl.MultM44f(hook, '_mmx', 3)
                    mmx.input[0].set_value(omx)
                    mmx.input[1].connect(target.world_transform)
                    xfos.append(mmx.output)
                else:
                    xfos.append(target.world_transform)

            _inv = kl.InverseM44f(hook, '_inv')
            _inv.input.connect(hook.parent_world_transform)

            if len(xfos) == 1:

                _mmx = kl.MultM44f(hook, '_mmx')
                _mmx.input[0].connect(xfos[0])
                _mmx.input[1].connect(_inv.output)
                m = _mmx.output

                if 'weights' in self.data or 'weight' in self.data:
                    blend = kl.BlendWeightedTransforms(2, hook, '_bmx')
                    blend.transform_interp_in.set_value(False)

                    blend.transform_in[0].connect(m)
                    w0 = add_plug(hook, 'w0', float, default_value=weights[0])
                    blend.weight_in[0].connect(w0)

                    connect_reverse(w0, blend.weight_in[1])
                    blend.transform_in[1].set_value(hook.transform.get_value())

                    m = blend.transform_out

            else:
                blend = kl.BlendWeightedTransforms(len(xfos) + 1, hook, '_bmx_hook')
                blend.transform_interp_in.set_value(False)

                w = None
                for i, xfo in enumerate(xfos):
                    blend.transform_in[i].connect(xfo)
                    plug = add_plug(hook, 'w{}'.format(i), float, default_value=weights[i])
                    blend.weight_in[i].connect(plug)

                    if w:
                        w = connect_add(w, plug)
                    else:
                        w = plug

                _mmx = kl.MultM44f(hook, '_mmx')
                _mmx.input[0].connect(blend.transform_out)
                _mmx.input[1].connect(_inv.output)
                m = _mmx.output

                blend = kl.BlendWeightedTransforms(2, hook, '_bmx_offset')
                blend.transform_interp_in.set_value(False)

                blend.transform_in[0].connect(m)

                blend.weight_in[0].set_value(1)
                connect_expr('b = 1 - clamp(w, 0, 1)', b=blend.weight_in[1], w=w)

                blend.transform_in[1].set_value(hook.transform.get_value())
                m = blend.transform_out

            hook.transform.connect(m)
            self.set_id(m.get_node(), 'constraint.matrix')

        if do_group:

            # reparent when new hook
            for node in nodes:
                node.reparent(hooks[0])

            # registering
            for hook in hooks:
                self.set_id(hook, 'hooks', self.data.get('name'))
