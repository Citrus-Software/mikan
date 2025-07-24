# coding: utf-8

from six.moves import range
from six import string_types

from mikan.maya import cmds as mc
import mikan.maya.cmdx as mx

import mikan.maya.core as mk
from mikan.core import flatten_list, re_is_int
from mikan.maya.lib import connect_blend_weighted
from mikan.core.logger import create_logger

log = create_logger()


class Mod(mk.Mod):

    def run(self):
        ctrl = self.node

        # constrained node
        node = ctrl.parent()
        if 'root' in self.data:
            node = self.data['root']

        channels = 'tr'
        if self.data.get('orient'):
            channels = 'r'
        elif self.data.get('point'):
            channels = 't'

        # filter targets
        targets = []
        target = self.data.get('target')
        if target:
            targets.append(target)
        targets += list(flatten_list([self.data.get('targets', [])]))
        targets = list(filter(None, targets))

        if 'targets' not in self.data and 'target' not in self.data:
            raise mk.ModArgumentError('targets missing')
        if not targets:
            raise mk.ModArgumentError('no valid targets!')

        # target default weights
        if self.data.get('default'):
            dv = self.data['default']
        else:
            dv = [0.0] * len(targets)

        # target names
        _names = self.data.get('names', {})
        if not isinstance(_names, dict):
            _names = {}

        names = []
        for target in targets:
            name = ''
            if 'gem_id' in target:
                # attr name from target gem_id
                gem_id = target['gem_id'].read().split(';')

                for tag in ['space', 'hooks', 'ctrls', 'skin']:
                    for _id in gem_id:
                        if tag in _id:
                            _name = _id.split('::')[-1]
                            if '.' in _name:
                                _name = _name.split('.')[1]
                                if not re_is_int.match(_name):
                                    name = _name
                                    break
                    if name:
                        break

                if not name:
                    _name, sep, _tags = gem_id[0].partition('::')
                    name = _name.replace('.', '_')
                    if '.' in _tags:
                        name += '_' + '_'.join(_tags.split('.')[1:])

            else:
                # attr name from target name
                name = str(target)
                if '_' in name:
                    name = '_'.join(name.split('_')[1:])

            # attr name from data
            if target in _names:
                _name = _names[target]
                if isinstance(_name, string_types):
                    name = _name

            names.append(name)

        # transfer inputs to blend
        with mx.DGModifier() as md:
            blend = md.create_node(mx.tPairBlend, name='_pb#')
        blend['w'] = 0

        for attr in channels:
            for dim in 'xyz':
                node_attr = node[attr + dim]
                attr_out = node_attr.input(plug=True)
                if isinstance(attr_out, mx.Plug):
                    if attr_out.node().is_a(mx.tUnitConversion):
                        attr_out = attr_out.node()['input'].input(plug=True)
                    attr_out >> blend['i' + attr + dim + '1']
                else:
                    blend['i' + attr + dim + '1'] = node_attr.read()

                node_attr.disconnect(destination=False)

        # build target buffer nodes
        tbuffers = []
        for target in targets:
            node_name = node.name(namespace=False)
            with mx.DagModifier() as md:
                t = md.create_node(mx.tTransform, parent=node, name='_{}_offset'.format(node_name))
            mc.parent(str(t), str(target))
            tbuffers.append(t)
            self.set_id(t, 'space', 'offsets')
        targets = tbuffers

        # create constraint
        if self.data.get('orient'):
            cnst = mx.cmd(mc.orientConstraint, targets, node, mo=1, n='_ox#')
        elif self.data.get('point'):
            cnst = mx.cmd(mc.parentConstraint, targets, node, mo=1, n='_prx#', sr=['x', 'y', 'z'])
        else:
            cnst = mx.cmd(mc.parentConstraint, targets, node, mo=1, n='_prx#')
        cnst = mx.encode(cnst[0])
        cnst['interpType'] = 2

        # attrs
        if self.data.get('orient'):
            ctrl.add_attr(mx.Divider('space'))
        else:
            ctrl.add_attr(mx.Divider('pin'))
        attrs = []

        for i, target in enumerate(targets):
            if channels == 'tr' or channels == 't':
                attr = 'pin_' + names[i]
            else:
                attr = 'follow_' + names[i]
            attrs.append(attr)
            ctrl.add_attr(mx.Double(attr, keyable=True, min=0, max=1, default=dv[i]))
            ctrl[attr] >> cnst['w{}'.format(i)]

            _add = connect_blend_weighted(ctrl[attr], blend['w'])

        with mx.DGModifier() as md:
            _clamp = md.create_node(mx.tClamp)
        _add['o'] >> _clamp['inputR']
        _clamp['maxR'] = 1
        _clamp['outputR'] >> blend['w']

        # transfer constraint to blend
        for attr in channels:
            for dim in 'xyz':
                node_attr = node[attr + dim]
                attr_out = node_attr.input(plug=True)
                if isinstance(attr_out, mx.Plug):
                    if attr_out.node().is_a(mx.tUnitConversion):
                        attr_out = attr_out.node()['input'].input(plug=True)
                    attr_out >> blend['i' + attr + dim + '2']
                else:
                    blend['i' + attr + dim + '1'] = node_attr.read()

                node_attr.disconnect(destination=False)

        # connect blend
        for attr in channels:
            for dim in 'xyz':
                blend['o' + attr + dim] >> node[attr + dim]

        # create ui node
        with mx.DGModifier() as md:
            ui_space = md.create_node(mx.tNetwork, name='ui_space_{}'.format(ctrl))

        if self.data.get('orient'):
            ctrl.add_attr(mx.Message('ui_space_follow'))
            ui_space['msg'] >> ctrl['ui_space_follow']
        else:
            ctrl.add_attr(mx.Message('ui_space_pin'))
            ui_space['msg'] >> ctrl['ui_space_pin']

        _attrs = mx.Double('plug'), mx.String('label')
        ui_space.add_attr(mx.Compound('targets', children=_attrs, array=True, indexMatters=True))

        ui_space['targets'][0]['label'] = self.data.get('rest_name', 'parent')
        for i in range(len(targets)):
            ctrl[attrs[i]] >> ui_space['targets'][i + 1]['plug']
            ui_space['targets'][i + 1]['label'] = names[i]

        ui_space.add_attr(mx.Message('constraint'))
        cnst['msg'] >> ui_space['constraint']
