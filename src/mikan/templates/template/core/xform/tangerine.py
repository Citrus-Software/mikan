# coding: utf-8

import meta_nodal_py as kl
from meta_nodal_py.Imath import V3f, M44f, Euler

import mikan.tangerine.core as mk
from mikan.tangerine.lib import *


class Template(mk.Template):

    def build_template(self, data):
        self.node.rename('tpl_{}'.format(self.name))
        self.node.transform.set_value(M44f(V3f(*data['transform']), V3f(0, 0, 0), V3f(1, 1, 1), Euler.Default))

    def build_rig(self):
        # init
        hook = self.get_hook()

        n_end = self.get_branch_suffix()
        n_loc = self.name

        tpl_loc = self.root

        # build nodes
        node_class = kl.SceneGraphNode if not self.get_opt('joint') else kl.Joint
        loc = node_class(hook, n_loc + n_end)

        xfo = tpl_loc.world_transform.get_value()
        loc.set_world_transform(xfo)

        _xfo = loc.transform.get_value()
        if not self.get_opt('copy_orient'):
            _xfo = M44f(_xfo.translation(), V3f(0, 0, 0), _xfo.scaling(), Euler.XYZ)
        if self.do_flip() and self.get_opt('flip_orient'):
            _xfo = M44f(V3f(0, 0, 0), V3f(180, 0, 0), V3f(1, 1, 1), Euler.ZYX) * _xfo
        loc.transform.set_value(_xfo)

        rotate_order = self.get_opt('rotate_order')
        rotate_order = str_to_rotate_order(rotate_order)
        create_srt_in(loc, ro=rotate_order)

        if self.get_opt('locator'):
            gen = kl.CrossShapeTool(loc, n_loc + n_end + 'Shape_reader')
            gen.size_in.set_value(0.1)

            shp = kl.Geometry(loc, n_loc + n_end + 'Shape')
            shp.mesh_in.connect(gen.mesh_out)

            loc_color = kl.Imath.Color4f(0, 0.5, 0, 1)
            loc_shader = kl.Shader('', loc_color)
            shp.shader_in.set_value(loc_shader)

        # copy shapes
        if self.get_opt('copy_shapes'):
            shp = mk.Shape(loc)
            shp.copy(self.node)  # local copy from template node
            if self.do_flip():
                mk.Shape(loc).scale(-1)

        # ids
        self.set_id(loc, 'node')
        self.set_hook(tpl_loc, loc, 'node')

        if self.get_opt('do_ctrl'):
            self.set_id(loc, 'ctrls.node')
        if self.get_opt('do_skin'):
            self.set_id(loc, 'skin.node')
