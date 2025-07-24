# coding: utf-8

from six.moves import range

from mikan.maya import cmds as mc
import mikan.maya.cmdx as mx

import mikan.maya.core as mk
from mikan.core.prefs import Prefs
from mikan.maya.lib.rig import copy_transform
from mikan.maya.lib.connect import connect_matrix, connect_reverse, connect_add, connect_expr
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
                if 'gem_id' in tgt:
                    n = tgt['gem_id'].read().split(';')[0]
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
            parent = self.data.get('parent', nodes[0].parent() if nodes else None)
            with mx.DagModifier() as md:
                hook = md.create_node(mx.tTransform, parent=parent, name='hook_{}{}'.format(name, sfx))
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
            xfos = []

            for target in targets:
                if do_offset:
                    with mx.DGModifier() as md:
                        cmx = md.create_node(mx.tComposeMatrix, name='_cmx#')
                        mmx = md.create_node(mx.tMultMatrix, name='_mmx#')

                    offset = hook['wm'][0].as_transform() * target['wim'][0].as_transform()
                    cmx['inputTranslate'] = offset.translation()
                    cmx['inputRotate'] = offset.rotation()
                    cmx['inputScale'] = offset.scale()
                    cmx['inputShear'] = offset.shear(mx.sObject)

                    cmx['outputMatrix'] >> mmx['i'][0]
                    target['wm'][0] >> mmx['i'][1]

                    xfos.append(mmx['o'])
                else:
                    xfos.append(target['wm'][0])

            if len(xfos) == 1:
                with mx.DGModifier() as md:
                    _mmx = md.create_node(mx.tMultMatrix, name='_mmx#')
                xfos[0] >> _mmx['i'][0]
                hook['pim'][0] >> _mmx['i'][1]
                m = _mmx['o']

                if 'weights' in self.data or 'weight' in self.data:
                    with mx.DGModifier() as md:
                        blend = md.create_node(mx.tWtAddMatrix, name='_bmx#')
                    m >> blend['i'][0]['m']

                    hook.add_attr(mx.Double('w0', keyable=True, default=weights[0]))
                    hook['w0'] >> blend['i'][0]['w']

                    connect_reverse(hook['w0'], blend['i'][1]['w'])
                    blend['i'][1]['m'] = hook['m'].as_matrix()

                    m = blend['o']

            else:
                with mx.DGModifier() as md:
                    blend = md.create_node(mx.tWtAddMatrix, name='_bmx_hook#')

                w = None
                for i, xfo in enumerate(xfos):
                    xfo >> blend['i'][i]['m']

                    plug = 'w{}'.format(i)
                    hook.add_attr(mx.Double(plug, keyable=True, default=weights[i]))
                    hook[plug] >> blend['i'][i]['w']

                    if w is not None:
                        w = connect_add(w, hook[plug])
                    else:
                        w = hook[plug]

                with mx.DGModifier() as md:
                    mmx = md.create_node(mx.tMultMatrix, name='_mmx#')
                blend['o'] >> mmx['i'][0]
                hook['pim'][0] >> mmx['i'][1]
                m = mmx['o']

                with mx.DGModifier() as md:
                    blend = md.create_node(mx.tWtAddMatrix, name='_bmx_offset#')
                m >> blend['i'][0]['m']

                blend['i'][0]['w'] = 1
                connect_expr('b = 1 - clamp(w, 0, 1)', b=blend['i'][1]['w'], w=w)

                blend['i'][1]['m'] = hook['m'].as_matrix()
                m = blend['o']

            dmx = connect_matrix(m, hook)
            self.set_id(dmx, 'constraint.matrix')

        if do_group:

            # reparent when new hook
            for node in nodes:
                mc.parent(str(node), str(hooks[0]))

            # registering
            for hook in hooks:
                self.set_id(hook, 'hooks', self.data.get('name'))
