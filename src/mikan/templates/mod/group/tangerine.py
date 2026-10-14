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

        if 'name' not in self.data and 'tag' not in self.data:
            raise mk.ModArgumentError('name or tag missing')

        if 'parent' in self.data and not isinstance(self.data['parent'], (str, bool)):
            raise mk.ModArgumentError('invalid parent')

        # tag, name
        tag = 'subgroups'
        name = cleanup_str(self.data.get('name', ''), ' ')
        subtag = self.data.get('tag', name)

        if subtag.startswith('vis.'):
            tag = 'vis'
            subtag = subtag[4:]

        if not name:
            name = subtag

        branch_sfx = ''
        tpl_id = self.get_template_id()
        if '.' in tpl_id:
            branch_sfx = ' '.join(tpl_id.split('.')[1:])
        if branch_sfx:
            name += ' ' + branch_sfx

        # create group
        grp = mk.Group.create(name)
        for node in nodes:
            if node is not None:
                grp.add_member(node)

        # parent
        parent = self.data.get('parent', tpl_id)
        if tag == 'subgroups' and parent:
            if not isinstance(parent, str):
                parent = tpl_id

            add_plug(grp.node, 'gem_group_parent', str)
            grp.node.gem_group_parent.set_value(parent)

        # vis groups
        vis = self.data.get('vis')
        if vis:
            vis = list(flatten_list([vis]))
            add_plug(grp.node, 'gem_vis', str)
            grp.node.gem_vis.set_value(';'.join([mk.Nodes.get_node_id(node) for node in vis if node]))
            grp.node.rename(grp.node.get_name() + '_vis')

        # register
        self.set_id(grp.node, tag, subtag, prefix='')
