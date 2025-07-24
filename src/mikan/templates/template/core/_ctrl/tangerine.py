# coding: utf-8

import meta_nodal_py as kl
from meta_nodal_py.Imath import V3f, M44f, Euler

import mikan.tangerine.core as mk
from mikan.tangerine.lib import *
from mikan.tangerine.lib.rig import *


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
        root = kl.SceneGraphNode(hook, 'root_{}{}'.format(n_loc, n_end))
        copy_transform(tpl_loc, root)

        if self.do_flip() and self.get_opt('flip_orient'):
            _xfo = root.transform.get_value()
            _xfo = M44f(V3f(0, 0, 0), V3f(180, 0, 0), V3f(1, 1, 1), Euler.ZYX) * _xfo
            root.transform.set_value(_xfo)

        local_orient = self.get_opt('local_orient')
        if not local_orient:
            ctrl = kl.SceneGraphNode(root, 'c_{}{}'.format(n_loc, n_end))
        else:
            ctrl = kl.Joint(root, 'c_{}{}'.format(n_loc, n_end))
            ctrl.reparent(hook)
            copy_transform(hook, root, r=1)
            ctrl.reparent(root)

        rotate_order = self.get_opt('rotate_order')
        rotate_order = str_to_rotate_order(rotate_order)

        create_srt_in(root, ro=rotate_order)
        create_srt_in(ctrl, ro=rotate_order, k=self.get_opt('do_ctrl'))

        ctrl.find('transform').find('scale').x.set_value(1)
        ctrl.find('transform').find('scale').y.set_value(1)
        ctrl.find('transform').find('scale').z.set_value(1)

        if self.get_opt('locator'):
            gen = kl.CrossShapeTool(ctrl, 'shp_{}{}_reader'.format(n_loc, n_end))
            gen.size_in.set_value(0.1)

            shp = kl.Geometry(ctrl, 'shp_{}{}'.format(n_loc, n_end))
            shp.mesh_in.connect(gen.mesh_out)

            loc_color = kl.Color(0, 0.5, 0, 1)
            loc_shader = kl.Shader('', loc_color)
            shp.shader_in.set_value(loc_shader)

        # copy shapes
        if self.get_opt('copy_shapes'):
            # local copy from template node
            if not self.do_flip():
                src = self.node
                mk.Shape(ctrl).copy(src)
            else:
                src = kl.SceneGraphNode(ctrl, '_dummy')
                mk.Shape(src).copy(self.node)
                if self.do_flip():
                    src.transform.set_value(M44f(V3f(0, 0, 0), V3f(0, 0, 0), V3f(-1, 1, 1), rotate_order))
                    _src = mk.Shape(src)
                    for shp in _src.get_shapes():
                        if shp.get_dynamic_plug('gem_color'):
                            rgb = mk.Shape.color_to_rgb(shp.gem_color.get_value())
                            rgb = mk.Shape.get_color_flip(rgb)
                            shp.gem_color.set_value(mk.Shape.rgb_to_hex(rgb))
                    _src.restore_color(force=True)
                mk.Shape(ctrl).copy(src, world=True)
                src.remove_from_parent()

        # ids
        self.set_id(root, 'root')
        self.set_id(root, 'roots.0')
        self.set_id(ctrl, 'ctrl')
        if self.get_opt('do_ctrl'):
            self.set_id(ctrl, 'ctrls.0')
        self.set_hook(tpl_loc, ctrl, 'ctrl')
