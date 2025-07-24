# coding: utf-8

from mikan.maya import cmds as mc
import mikan.maya.cmdx as mx

import mikan.maya.core as mk
from mikan.maya.lib.connect import connect_matrix
from mikan.maya.lib.rig import copy_transform
from mikan.core import cleanup_str, create_logger

log = create_logger()


class Mod(mk.Mod):

    def run(self):
        node = self.data.get('node', self.node)
        parent = self.data.get('parent', node.parent())

        if 'curve' not in self.data:
            raise mk.ModArgumentError('curve not defined')
        else:
            crv_shp, xfo = self.data['curve']

        target = self.data.get('target')

        if 'target' not in self.data:
            # legacy mode
            node_id = mk.Nodes.get_node_id(node, find='::skin')
            ctrl_id = node_id.replace('::skin', '::ctrls')
            target = mk.Nodes.get_id(ctrl_id)

            parent = node.parent()

        axis = self.data.get('axis', 'y')
        if axis not in 'xyz':
            axis = 'y'

        # build rig
        name = cleanup_str(self.data.get('name', xfo.name(namespace=False)))

        root = mx.create_node(mx.tTransform, parent=parent, name='bank_' + name)
        copy_transform(target, root, t=True, r=True)

        xfo = mc.duplicate(str(xfo), n='bank_curve_' + name, rr=1, rc=1)
        xfo = mx.encode(xfo[0])
        crv_shp = xfo.shape()
        mc.parent(str(xfo), str(root))
        # TODO: si la curve a de l'historique il ne faudrait pas dupliquer

        orient = mx.create_node(mx.tTransform, parent=root, name='bank_orient_' + name)
        target['r'] >> orient['r']

        tgt = mx.create_node(mx.tTransform, parent=orient, name='bank_target_' + name)
        tgt['t' + axis] = 1

        pt = mx.create_node(mx.tTransform, parent=root, name='bank_point_' + name)
        mc.pointConstraint(str(tgt), str(pt), skip=axis)

        aim = mx.create_node(mx.tTransform, parent=root, name='bank_aim_' + name)
        mc.aimConstraint(str(pt), str(aim), aim=[1, 0, 0], wut='none')

        loc = mx.create_node(mx.tTransform, parent=aim, name='bank_loc_' + name)
        dim = mk.Shape(xfo).get_dimensions()
        loc['tx'] = max(dim) * 2

        poc = mx.create_node(mx.tTransform, parent=root, name='bank_poc_' + name)

        _dmx = mx.create_node(mx.tDecomposeMatrix, name='_dmx#')
        loc['worldMatrix'][0] >> _dmx['inputMatrix']

        _c = mx.create_node(mx.tNearestPointOnCurve, name='_closest#')
        _dmx['outputTranslate'] >> _c['inPosition']
        crv_shp['worldSpace'][0] >> _c['inputCurve']

        _cmx = mx.create_node(mx.tComposeMatrix, name='_cmx#')
        _c['position'] >> _cmx['inputTranslate']

        mmx = mx.create_node(mx.tMultMatrix, name='_mmx#')
        _cmx['outputMatrix'] >> mmx['matrixIn'][0]
        poc['pim'][0] >> mmx['matrixIn'][1]

        _dmx = mx.create_node(mx.tDecomposeMatrix, name='bank_dm_out#')
        mmx['matrixSum'] >> _dmx['inputMatrix']

        _dmx['outputTranslate'] >> poc['rp']

        connect_matrix(poc['wm'][0], node, pim=True)

        # lock rotate y
        target['r' + axis].lock()
        target['r' + axis].keyable = False
        target['r'] >> poc['r']

        # exit
        root['visibility'] = False
