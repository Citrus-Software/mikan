# coding: utf-8

import meta_nodal_py as kl

import mikan.tangerine.core as mk
from mikan.tangerine.lib.commands import add_plug
from mikan.core import flatten_list, cleanup_str, create_logger

log = create_logger()


class Mod(mk.Mod):

    def run(self):

        if 'nodes' not in self.data:
            return

        # get nodes
        nodes = list(flatten_list([self.data.get('nodes')]))
        if not any(nodes):
            raise mk.ModArgumentError('node list is empty')

        # tag, name
        _id = self.get_template_id()
        tag = self.data.get('tag', 'grp.{}'.format(_id.split('.')[0]))

        default_name = tag
        if default_name.startswith('vis.'):
            default_name = default_name[4:]

        name = cleanup_str(self.data.get('name', default_name), ' ')
        name = ' '.join([name] + _id.split('.')[1:])

        # create group
        grp = mk.Group.create(name)
        for node in nodes:
            if node is not None:
                grp.add_member(node)

        for parent in list(flatten_list([self.data.get('parent')])):
            if parent and isinstance(parent, kl.Node):
                if parent.get_dynamic_plug('gem_type') and parent.gem_type.get_value() == mk.Group.type_name:
                    parent = mk.Group(parent)
                    grp.add_parent(parent)

        # vis groups
        vis = self.data.get('vis')
        if vis:
            vis = list(flatten_list([vis]))
            add_plug(grp.node, 'gem_vis', str)
            grp.node.gem_vis.set_value(';'.join([mk.Nodes.get_node_id(node) for node in vis if node]))
            grp.node.rename(grp.node.get_name() + '_vis')

        # register
        self.set_id(grp.node, tag, subtag='', prefix='')
