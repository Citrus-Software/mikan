# coding: utf-8

import meta_nodal_py as kl

import mikan.tangerine.core as mk
from mikan.core import flatten_list, re_is_int
from mikan.tangerine.lib import *
from mikan.core.logger import create_logger

log = create_logger()


class Mod(mk.Mod):

    def run(self):
        ctrl = self.node

        # constrained node
        node = ctrl.get_parent()
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
            if target.get_dynamic_plug('gem_id'):
                # attr name from target gem_id
                gem_id = target.gem_id.get_value().split(';')

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
                if isinstance(_name, str):
                    name = _name

            names.append(name)

        # build target buffer nodes
        tbuffers = []
        for target in targets:
            t = kl.SceneGraphNode(node, 't_{}_{}'.format(target.get_name(), ctrl.get_name().split('c_')[-1]))
            t.reparent(target)
            tbuffers.append(t)
            self.set_id(t, 'space', 'offsets')
        targets = tbuffers

        if self.data.get('orient'):
            cnst = orient_constraint(targets, node, mo=1, bw_size=len(targets) + 1)
        elif self.data.get('point'):
            cnst = parent_constraint(targets, node, mo=1, skip_rotation=True, bw_size=len(targets) + 1)
        else:
            cnst = parent_constraint(targets, node, mo=1, bw_size=len(targets) + 1)
        if len(targets) > 1:
            cnst.transform_interp_in.set_value(False)
            cnst.transform_shortest_in.set_value(True)
            # bw.add_transform_in(1)

            # extra_weight and extra_transform are created for mikan for now because it is not allowed to manipulate
            # blend_weighted_transforms created by constrain
            # but we should find an other alternative without this plugs
            w_rest = cnst.extra_weight_in[0]
            tr_rest = cnst.extra_transform_in[0]
            tr_rest.set_value(cnst.initial_input_transform.get_value())
            targets_count = len(targets)

            _add = kl.Add(cnst, '_add_bw')
            _add.add_inputs(targets_count - 1)
            for i in range(1, targets_count + 1):
                wa = cnst.weight_in[i - 1]
                a = getattr(_add, 'input{0}'.format(i))
                a.connect(wa)

            ig = kl.IsGreater(cnst, '_ig')
            ig.input1.connect(_add.output)
            ig.input2.set_value(1)

            nt = kl.Not(cnst, '_not')
            nt.input.connect(ig.output)

            sub = kl.Sub(cnst, '_sub')
            sub.input1.set_value(1)
            sub.input2.connect(_add.output)

            cond = kl.Condition(cnst, '_if')
            cond.condition.connect(nt.output)
            cond.input1.connect(sub.output)
            cond.input2.set_value(0)

            w_rest.connect(cond.output)

        plugs = []
        for i, target in enumerate(targets):
            if channels == 'tr' or channels == 't':
                plug_name = 'pin_' + names[i]
                nice_name = 'Pin ' + names[i].capitalize()
            else:
                plug_name = 'follow_' + names[i]
                nice_name = 'Follow ' + names[i].capitalize()

            j = 2
            while ctrl.get_dynamic_plug(plug_name) is not None:
                plug_name = plug_name + str(j)

            plug = add_plug(ctrl, plug_name, float, min_value=0, max_value=1, k=1, default_value=dv[i], nice_name=nice_name)
            plugs.append(plug)

            if len(targets) == 1:
                w = getattr(cnst, "enable_in")
            else:
                w = getattr(cnst, 'w{0}'.format(i))
            w.connect(plug)

            _b = node.get_dynamic_plug('blend_rotate')
            if _b:
                _b.connect(plug)

            _b = node.get_dynamic_plug('blend_translate')
            if _b:
                _b.connect(plug)

        # create ui node
        ui_space = kl.Node(ctrl, 'ui_space_match')
        ui_plug = add_plug(ui_space, 'ui', kl.Unit)

        if self.data.get('orient'):
            add_plug(ctrl, 'ui_space_follow', kl.Unit)
            ctrl.ui_space_follow.connect(ui_plug)
        else:
            add_plug(ctrl, 'ui_space_pin', kl.Unit)
            ctrl.ui_space_pin.connect(ui_plug)

        add_plug(ui_space, 'targets', int, default_value=len(targets) + 1)

        add_plug(ui_space, 'plug0', float)
        add_plug(ui_space, 'label0', str, default_value=self.data.get('rest_name', 'parent'))

        for i in range(len(targets)):
            plug = add_plug(ui_space, 'plug{}'.format(i + 1), float)
            plug.connect(plugs[i])
            add_plug(ui_space, 'label{}'.format(i + 1), str, default_value=names[i])

        add_plug(ui_space, 'constraint', float)
        ui_space.constraint.connect(cnst.enable_in)
