# coding: utf-8

import meta_nodal_py as kl

import mikan.tangerine.core as mk
from mikan.tangerine.lib.rig import parent_constraint, point_constraint, orient_constraint, scale_constraint, matrix_constraint
from mikan.tangerine.lib.connect import safe_connect
from mikan.core.logger import create_logger

log = create_logger()


class Deformer(mk.Deformer):
    node_class = None

    def read(self):
        pass

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
            cnst = parent_constraint(target, self.transform, maintain_offset=True)
            self.set_geometry_id(cnst, 'hook.parent')

        if 'point' in self.data:
            target = self.get_node(self.data['point'])
            cnst = point_constraint(target, self.transform, maintain_offset=True)
            self.set_geometry_id(cnst, 'hook.point')

        if 'orient' in self.data:
            target = self.get_node(self.data['orient'])
            cnst = orient_constraint(target, self.transform, maintain_offset=True)
            self.set_geometry_id(cnst, 'hook.orient')

        if 'scale' in self.data:
            target = self.get_node(self.data['scale'])
            cnst = scale_constraint(target, self.transform, maintain_offset=True)
            self.set_geometry_id(cnst, 'hook.scale')

        # connect plugs
        if 'plug' in self.data:
            for plug, tag in self.data['plug'].items():

                if isinstance(tag, str):
                    if '@' not in tag:
                        self.log_error('/!\\ invalid plug tag ({})'.format(tag))
                        continue
                    tag = self.get_node(tag)

                plug = mk.Nodes.get_node_plug(self.transform, plug)

                if tag and plug:
                    safe_connect(tag, plug)
