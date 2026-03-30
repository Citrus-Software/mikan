# coding: utf-8

import re
import os
import io

from mikan.maya import cmds as mc
import mikan.maya.cmdx as mx

import mikan.maya.core as mk
from mikan.core import cleanup_str, create_logger
from mikan.maya.lib.rig import copy_transform
from mikan.maya.lib.connect import connect_mult, connect_expr

log = create_logger()


class Mod(mk.Mod):

    def run(self):

        # check bifrost
        if not check_bifrost_status():
            raise mk.ModError('Bifrost not available')

        bf_version = mc.pluginInfo("bifrostGraph", query=True, version=True)
        match = re.search(r'^(\d+)\.(\d+)\.(\d+)', bf_version)
        if match:
            major = int(match.group(1))
            minor = int(match.group(2))
            if major < 2:
                if major == 2 and minor < 1:
                    raise mk.ModError('Bifrost version too old. Feedback Ports require at least version 2.1.')
                elif major == 2 and minor == 1:
                    log.warning('Bifrost 2.1 detected. Feedback Ports are supported, but version 2.2 or higher is recommended for better stability.')

        # args
        rig = mk.Nodes.get_id('::rig')
        if not rig:
            raise mk.ModArgumentError('cannot build dynamic without world')

        ctrl = self.data.get('ctrl')
        if not ctrl:
            raise mk.ModArgumentError('no controller defined')

        ctrl_main = self.data.get('ctrl_main', ctrl)
        ctrl_dyn = self.data.get('ctrl_dyn', ctrl)

        driven_node = self.data.get('dyn')
        if not driven_node:
            raise mk.ModArgumentError('no driven node defined')

        target = self.data.get('target')
        if not target:
            raise mk.ModArgumentError('no target defined')

        name = self.data.get('name')
        tpl_id = self.get_template_id()
        sfx = ''
        if '.' in tpl_id:
            sfx = '_' + '_'.join(tpl_id.split('.')[1:])

        if not name:
            name = ctrl.name(namespace=False)
            if tpl_id in name:
                name = tpl_id + name.split(tpl_id)[-1]

        name += sfx
        name = cleanup_str(name)

        # rig nodes
        parent = driven_node.parent()

        target_node = mx.create_node(mx.tTransform, parent=parent, name='tgt_' + name)
        copy_transform(target, target_node, t=True)

        body = mx.create_node(mx.tTransform, parent=parent, name='body_' + name)
        copy_transform(target, body, t=True)

        # attributes
        start_frame = self.data.get('start_frame', 1)
        weight = self.data.get('weight', 1)
        goal = self.data.get('goal', 0.5)
        damp = self.data.get('damp', 0.5)

        if 'dynamic' not in ctrl_main:
            ctrl_main.add_attr(mx.Boolean('dynamic', keyable=True, default=False))
        if 'weight' not in ctrl_main:
            ctrl_main.add_attr(mx.Double('weight', keyable=True, min=0, max=1))
        if 'start_frame' not in ctrl_main:
            ctrl_main.add_attr(mx.Long('start_frame', keyable=False, default=1))

        if 'goal' not in ctrl_dyn:
            ctrl_dyn.add_attr(mx.Double('goal', keyable=True, min=0, max=1))
        if 'damp' not in ctrl_dyn:
            ctrl_dyn.add_attr(mx.Double('damp', keyable=True, min=0, max=1))

        ctrl_main['dynamic'].channel_box = True
        ctrl_main['weight'].channel_box = True
        ctrl_main['start_frame'].channel_box = True
        ctrl_dyn['goal'].channel_box = True
        ctrl_dyn['damp'].channel_box = True

        if ctrl_main['weight'].editable:
            ctrl_main['weight'] = weight
        if ctrl_main['start_frame'].editable:
            ctrl_main['start_frame'] = start_frame
        if ctrl_dyn['goal'].editable:
            ctrl_dyn['goal'] = goal
        if ctrl_dyn['damp'].editable:
            ctrl_dyn['damp'] = damp

        # build solver
        mc.currentTime(start_frame)

        plugin_dir = os.path.dirname(__file__)
        json_path = os.path.join(plugin_dir, 'bifrost_jiggle.json')
        json_path = os.path.normpath(json_path)

        try:
            with io.open(json_path, 'r', encoding='utf-8') as f:
                json_str = f.read()
        except Exception as e:
            mk.ModError('Failed to read bifrost json compund file: {}'.format(e))

        bf = mx.create_node('bifrostGraphShape', parent=body, name='body_' + name + 'Shape')
        bf['sc'] = json_str.replace('bifrostGraphShape1', str(bf))

        # connect solver
        ctrl_main['start_frame'] >> bf['start_frame']
        ctrl_main['dynamic'] >> bf['enable_in']

        ctrl_dyn['goal'] >> bf['stiffness_in']
        ctrl_dyn['damp'] >> bf['damp_in']

        body['pim'][0] >> bf['parent_inverse_transform_in']
        target_node['wm'][0] >> bf['target_in']

        bf['position_out'] >> body['t']

        # rig aim
        _wm = body['wm'][0].as_transform()
        _wim = driven_node['wim'][0].as_transform()
        _aim = (_wm * _wim).translation().normalize()

        _ac = mc.aimConstraint(str(body), str(driven_node), mo=1, aim=_aim, u=[0, 0, 0], wut='none', wuo=str(ctrl), wu=[0, 0, 0], n='_ax#')
        _ac = mx.encode(_ac[0])

        _pb = mx.create_node(mx.tPairBlend, name='_pb#')
        _pb['rotInterpolation'] = 1
        _ac['constraintRotate'] >> _pb['inRotate2']
        connect_mult(ctrl_main['dynamic'], ctrl_main['weight'], _pb['weight'])

        driven_node['rotate'].disconnect(destination=False)
        driven_node['rotateX'].disconnect(destination=False)
        driven_node['rotateY'].disconnect(destination=False)
        driven_node['rotateZ'].disconnect(destination=False)

        _pb['outRotate'] >> driven_node['rotate']


def check_bifrost_status():
    plugin_name = "bifrostGraph"

    if not mc.pluginInfo(plugin_name, query=True, loaded=True):
        try:
            mc.loadPlugin(plugin_name)
        except:
            return False

    return True
