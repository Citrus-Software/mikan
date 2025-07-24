# coding: utf-8

import meta_nodal_py as kl

import mikan.tangerine.core as mk
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
            if pfx and not isinstance(pfx, str):
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

        # update prefix
        if pfx:
            pfx += '_'

        # processing
        for node in nodes:
            _name = name
            if not name:
                _name = node.get_name().split(':')[-1]
            _name += sfx
            _name = cleanup_str(_name)

            node_class = kl.SceneGraphNode
            if do_skin or self.data.get('joint'):
                node_class = kl.Joint

            if do_root:
                root = node_class(node, 'root_' + pfx + _name)
            loc = node_class(node, pfx + _name)

            if self.data.get('locator'):
                gen = kl.CrossShapeTool(loc, pfx + _name + 'Shape_reader')
                s = self.data.get('scale', 0.1)
                gen.size_in.set_value(s)

                shp = kl.Geometry(loc, pfx + _name + 'Shape')
                shp.mesh_in.connect(gen.mesh_out)

                loc_color = kl.Imath.Color4f(0, 0.5, 0, 1)
                loc_shader = kl.Shader('', loc_color)
                shp.shader_in.set_value(loc_shader)

            if self.data.get('shape'):
                shp = mk.Shape(node)
                if shp.get_shapes():
                    shp = mk.Shape(loc)
                    shp.copy(node)

            _parent = parent
            if not parent:
                _parent = node.get_parent()

            if do_root:
                root.reparent(_parent)
                loc.reparent(root)
            else:
                loc.reparent(_parent)

            if do_copycat:
                loc.transform.connect(node.transform)

            self.set_id(loc, 'loc', name)
            if do_root:
                self.set_id(root, 'loc.root', name)
            if do_skin:
                self.set_id(loc, 'skin.loc', name, prefix='')
