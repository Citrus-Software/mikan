# coding: utf-8

import meta_nodal_py as kl

import mikan.tangerine.core as mk
from mikan.core import flatten_list
from mikan.tangerine.lib.nurbs import create_path
from mikan.core.logger import create_logger

log = create_logger()


class Mod(mk.Mod):

    def run(self):

        # get nodes
        nodes = [node for node in [self.node] if node is not None]
        if 'nodes' in self.data:
            nodes = self.data.get('nodes')
            del self.data['nodes']
        nodes = list(flatten_list(nodes))
        if not nodes:
            raise mk.ModArgumentError('node not found')

        parent = self.data.get('parent', nodes[0].get_parent())
        degree = self.data.get('degree', 1)

        # build
        helper = create_path(nodes, d=degree, parent=parent)
        self.set_id(helper, 'curve', self.data.get('name'))
        self.set_id(helper, 'helper', self.data.get('name'))

        # rename
        sfx = self.get_template_id()
        if 'name' in self.data:
            name = self.data.get('name').replace('.', '_')
        else:
            name = sfx.split('.')[0]

        if '.' in sfx:
            sfx = '_' + '_'.join(sfx.split('.')[1:])
        else:
            sfx = ''

        helper.rename(str(helper), 'cv_' + name + sfx)
