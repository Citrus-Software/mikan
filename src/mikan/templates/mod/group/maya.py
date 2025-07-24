# coding: utf-8

import mikan.maya.cmdx as mx

import mikan.maya.core as mk
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
            if parent and isinstance(parent, mx.Node) and parent.is_a(mx.tNetwork):
                if 'gem_type' in parent and parent['gem_type'].read() == mk.Group.type_name:
                    parent = mk.Group(parent)
                    grp.add_parent(parent)

        # vis groups
        vis = self.data.get('vis')
        if vis:
            vis = list(flatten_list([vis]))
            grp.node.add_attr(mx.String('gem_vis'))
            grp.node['gem_vis'] = ';'.join([mk.Nodes.get_node_id(node) for node in vis if node])
            grp.node.rename('{}_vis'.format(grp.node))

        # register
        self.set_id(grp.node, tag, subtag='', prefix='')
