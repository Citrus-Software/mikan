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

        # prefix
        prefix = self.get_opt('prefix')
        if not prefix.endswith('_'):
            prefix += '_'

        do_ctrl = self.get_opt('do_ctrl')
        do_skin = self.get_opt('do_skin')

        if do_ctrl:
            prefix = 'c_'
        elif do_skin:
            prefix = 'sk_'

        # build nodes
        do_joint = self.get_opt('joint')
        local_orient = self.get_opt('local_orient')

        root = None
        if self.get_opt('root'):
            node_class = kl.SceneGraphNode if not do_joint else kl.Joint
            root = node_class(hook, 'root_' + n_loc + n_end)
            hook = root

        node_class = kl.SceneGraphNode if not do_joint and not local_orient else kl.Joint
        loc = node_class(hook, prefix + n_loc + n_end)

        # orient
        orient_node = loc
        if root:
            orient_node = root

        xfo = tpl_loc.world_transform.get_value()
        orient_node.set_world_transform(xfo)
        _xfo = orient_node.transform.get_value()
        if self.do_flip() and self.get_opt('flip_orient'):
            _xfo = M44f(V3f(0, 0, 0), V3f(180, 0, 0), V3f(1, 1, 1), Euler.ZYX) * _xfo

        if local_orient and root:
            _xfo_t = M44f(_xfo.translation(), V3f(0, 0, 0), _xfo.scaling(), Euler.XYZ)
            root.transform.set_value(_xfo_t)
            _xfo_r = M44f(V3f(), _xfo.rotation(Euler.XYZ), V3f(1, 1, 1), Euler.XYZ)
            loc.transform.set_value(_xfo_r)
        else:
            if not self.get_opt('copy_orient'):
                _xfo = M44f(_xfo.translation(), V3f(0, 0, 0), _xfo.scaling(), Euler.XYZ)
            orient_node.transform.set_value(_xfo)

        rotate_order = self.get_opt('rotate_order')
        rotate_order = str_to_rotate_order(rotate_order)
        create_srt_in(loc, ro=rotate_order, keyable=do_ctrl)
        if root:
            create_srt_in(root, ro=rotate_order)

        # shapes
        if self.get_opt('locator'):
            gen = kl.CrossShapeTool(loc, prefix + n_loc + n_end + 'Shape_reader')
            gen.size_in.set_value(0.1)

            shp = kl.Geometry(loc, n_loc + n_end + 'Shape')
            shp.mesh_in.connect(gen.mesh_out)

            loc_color = kl.Imath.Color4f(0, 0.5, 0, 1)
            loc_shader = kl.Shader('', loc_color)
            shp.shader_in.set_value(loc_shader)

        if self.get_opt('copy_shapes'):
            shp = mk.Shape(loc)
            shp.copy(self.node)  # local copy from template node
            if self.do_flip():
                mk.Shape(loc).scale(-1)

        # ids
        self.set_id(loc, 'node')
        self.set_hook(tpl_loc, loc, 'node')

        if root:
            self.set_id(root, 'roots.node')

        if do_ctrl:
            self.set_id(loc, 'ctrls.node')
        if do_skin:
            self.set_id(loc, 'skin.node')
