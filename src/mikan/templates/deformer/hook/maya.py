# coding: utf-8

from six import string_types, iteritems

from mikan.maya import cmds as mc
import mikan.maya.cmdx as mx

import mikan.maya.core as mk
from mikan.maya.lib.rig import matrix_constraint
from mikan.core.logger import create_logger

log = create_logger()


class Deformer(mk.Deformer):
    node_class = None

    def read(self):

        plugs = {}
        for attr in 'srt':
            for dim in 'xyz':
                i = self.transform[attr + dim].input(plug=True)
                if isinstance(i, mx.Plug) and i.node().is_a(mx.tUnitConversion):
                    i = i.node()['input'].input(plug=True)
                if i:
                    plugs[attr + '.' + dim] = i

        v = self.transform['v'].input(plug=True)
        if v:
            plugs['vis'] = v

    def build(self, data=None):
        # check data
        if not self.transform:
            raise mk.DeformerError('no transform to hook')

        # hook type
        if 'transform' in self.data:
            target = self.get_node(self.data['transform'])
            node = matrix_constraint(target, self.transform)
            self.set_geometry_id(node, 'hook.transform')

        if 'hook' in self.data:
            target = self.get_node(self.data['hook'])
            node = matrix_constraint(target, self.transform)
            self.set_geometry_id(node, 'hook.transform')

        if 'parent' in self.data:
            target = self.get_node(self.data['parent'])
            cnst = mc.parentConstraint(str(target), str(self.transform), mo=1)
            self.set_geometry_id(cnst, 'hook.parent')

        if 'point' in self.data:
            target = self.get_node(self.data['point'])
            cnst = mc.pointConstraint(str(target), str(self.transform), mo=1)
            self.set_geometry_id(cnst, 'hook.point')

        if 'orient' in self.data:
            target = self.get_node(self.data['orient'])
            cnst = mc.orientConstraint(str(target), str(self.transform), mo=1)
            self.set_geometry_id(cnst, 'hook.orient')

        if 'scale' in self.data:
            target = self.get_node(self.data['scale'])
            cnst = mc.scaleConstraint(str(target), str(self.transform), mo=1)
            self.set_geometry_id(cnst, 'hook.scale')

        # connect plugs
        if 'plug' in self.data:
            for plug, tag in iteritems(self.data['plug']):

                if isinstance(tag, string_types):
                    if '@' not in tag:
                        self.log_error('invalid plug tag ({})'.format(tag))
                        continue
                    tag = self.get_node(tag)

                plug = mk.Nodes.get_node_plug(self.transform, plug)

                if tag and plug:
                    tag >> plug
