# coding: utf-8

from mikan.maya import cmds as mc
import mikan.maya.cmdx as mx

import mikan.maya.core as mk
from mikan.core import cleanup_str, create_logger
from mikan.maya.lib.rig import copy_transform
from mikan.maya.lib.connect import connect_mult, connect_expr

log = create_logger()


class Mod(mk.Mod):

    def run(self):

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

        if mk.Nodes.get_id('::jiggle') is None:
            dyn = mx.create_node(mx.tTransform, parent=rig, name='jiggle')
            mk.Nodes.set_id(dyn, '::jiggle')
        else:
            dyn = mk.Nodes.get_id('::jiggle')

        name = self.data.get('name')
        sfx = self.get_template_id()
        if '.' in sfx:
            sfx = '_' + '_'.join(sfx.split('.')[1:])
        else:
            sfx = ''
        if not name:
            name = ctrl.name(namespace=False)
        name += sfx
        name = cleanup_str(name)

        # particle
        # mc.select(clear=True)
        start_frame = self.data.get('start_frame', 1)
        # mc.currentTime(start_frame)

        # solver = mel.eval('createNSystem;')
        # solver = mx.encode(solver)
        # solver['v'] = False
        # mc.parent(str(solver), str(dyn))

        # solver['gravity'] = 0
        # solver['airDensity'] = 0
        # solver['subSteps'] = 1
        # solver['timeScale'] = 5

        # pcl, pcl_shp = mc.nParticle(p=target.translation(mx.sWorld), n='pcl_' + name)
        # mc.parent(pcl, str(dyn))
        # pcl = mx.encode(pcl)
        # pcl_shp = mx.encode(pcl_shp)

        # pcl_shp['radius'] = 0
        # pcl_shp['collide'] = 0

        target_node = mx.create_node(mx.tTransform, parent=ctrl, name='tgt_' + name)
        copy_transform(target, target_node, t=True)
        # mc.goal(str(pcl), g=str(target_node), w=1, utr=1)

        # current_solver = pcl_shp['nextState'].input()
        # if solver != current_solver:
        #     mc.select(str(pcl))
        #     mel.eval('assignNSolver("{}");'.format(solver))

        # params
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

        # ctrl_main['start_frame'] >> solver['startFrame']
        # ctrl_main['dynamic'] >> solver['enable']

        # ctrl_dyn['goal'] >> pcl_shp['goalWeight'][0]
        # ctrl_dyn['damp'] >> pcl_shp['damp']

        # loc result
        # name = pcl.name()
        pos = mc.spaceLocator(n='pos_' + name)
        mc.parent(pos, str(dyn))
        pos = mx.encode(pos[0])

        cm = mx.create_node(mx.tComposeMatrix)
        # pcl_shp['worldCentroid'] >> cm['inputTranslate']

        mmx = mx.create_node(mx.tMultMatrix)
        pos['pim'][0] >> mmx['i'][0]
        cm['outputMatrix'] >> mmx['i'][1]

        dm = mx.create_node(mx.tDecomposeMatrix)
        mmx['o'] >> dm['inputMatrix']
        dm['outputTranslate'] >> pos['translate']

        _wm = pos['wm'][0].as_transform()
        _wim = driven_node['wim'][0].as_transform()
        _aim = (_wm * _wim).translation().normalize()

        _ac = mc.aimConstraint(str(pos), str(driven_node), mo=1, aim=_aim, u=[0, 0, 0], wut='none', wuo=str(ctrl), wu=[0, 0, 0], n='_ax#')
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

        # hide
        # pcl['lodVisibility'] = False
        pos['v'] = False
