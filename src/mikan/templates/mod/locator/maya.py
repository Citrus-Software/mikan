# coding: utf-8

from six import string_types

from mikan.maya import cmds as mc
import mikan.maya.cmdx as mx

import mikan.maya.core as mk
from mikan.maya.lib.connect import connect_matrix
from mikan.core import flatten_list, cleanup_str, create_logger

log = create_logger()


class Mod(mk.Mod):

    def run(self):

        # get nodes
        nodes = self.data.get('nodes', self.data.get('node', self.node))
        nodes = [n for n in list(flatten_list([nodes])) if n]

        parent = self.data.get('parent')
        name = self.data.get('name')
        if name == 'root':
            self.log_warning('name root is reserved for loc.root ids')
        sfx = self.get_template_id()
        if '.' in sfx:
            sfx = '_' + '_'.join(sfx.split('.')[1:])
        else:
            sfx = ''

        # prefix
        pfx = 'loc'
        if 'prefix' in self.data:
            pfx = self.data['prefix']
            if pfx and not isinstance(pfx, string_types):
                raise mk.ModArgumentError('invalid prefix: {}'.format(type(pfx)))
            if not pfx:
                pfx = ''

        # opts
        do_root = bool(self.data.get('root'))
        do_copycat = bool(self.data.get('copycat'))
        if do_copycat:
            do_root = True
        do_skin = bool(self.data.get('skin'))
        if do_skin:
            pfx = 'sk'
        size = self.data.get('scale', 1)

        # update prefix
        if pfx:
            pfx += '_'

        # processing
        for node in nodes:
            _name = name
            if not name:
                _name = node.name(namespace=False)
            _name += sfx
            _name = cleanup_str(_name)

            node_type = mx.tTransform
            if do_skin or self.data.get('joint'):
                node_type = mx.tJoint

            with mx.DagModifier() as md:
                if do_root:
                    root = md.create_node(node_type, parent=node, name='root_' + pfx + _name)
                loc = md.create_node(node_type, parent=node, name=pfx + _name)

                if do_skin:
                    md.set_attr(loc['radius'], size)
                    if do_root:
                        md.set_attr(root['radius'], size)

                if self.data.get('locator'):
                    shp = md.create_node(mx.tLocator, parent=loc, name=pfx + _name + 'Shape')
                    md.set_attr(shp['localScale'], (size, size, size))

                if self.data.get('shape'):
                    shp = mk.Shape(node)
                    if shp.get_shapes():
                        shp = mk.Shape(loc)
                        shp.copy(node)

            _parent = parent
            if not parent:
                _parent = node.parent()

            if do_root:
                wm = root['wm'][0].as_matrix()
                if root.parent() != _parent:
                    mc.parent(str(root), str(_parent), r=1)
                mc.xform(str(root), m=wm * root['pim'][0].as_matrix())
                mc.parent(str(loc), str(root))
            else:
                wm = loc['wm'][0].as_matrix()
                if _parent != loc.parent():
                    mc.parent(str(loc), str(_parent), r=1)
                mc.xform(str(loc), m=wm * loc['pim'][0].as_matrix())

            if do_copycat:
                connect_matrix(node['m'], loc)

            # ids
            self.set_id(loc, 'loc', name)
            if do_root:
                self.set_id(root, 'loc.root', name)
            if do_skin:
                self.set_id(loc, 'skin.loc', name, prefix='')
