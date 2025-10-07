# coding: utf-8

import meta_nodal_py as kl
from meta_nodal_py.Imath import V3f, M44f
from meta_nodal_py.Imath import Euler

import mikan.tangerine.core as mk
from mikan.tangerine.lib.commands import *
from mikan.tangerine.lib.rig import create_srt_in
from mikan.tangerine.lib.connect import connect_mult, connect_div


class Template(mk.Template):

    def build_template(self, data):
        self.node.rename(f'tpl_{self.name}')
        self.node.transform.set_value(M44f(V3f(*data['transform']), V3f(0, 0, 0), V3f(1, 1, 1), Euler.Default))

    def build_rig(self):
        hook = self.get_hook()

        cam = kl.SceneGraphNode(hook, self.name)
        cam_shp = kl.Camera(cam, self.name + 'Shape')
        cam.set_world_transform(self.node.world_transform.get_value())
        if self.get_opt('do_ctrl'):
            create_srt_in(cam, k=1)

        add_plug(cam, 'focal_length', float, k=1)
        add_plug(cam, 'near_clip', float, k=1)
        add_plug(cam, 'far_clip', float, k=1)
        add_plug(cam, 'orthographic', bool, k=1)
        add_plug(cam, 'horizontal_aperture', float, k=1)
        add_plug(cam, 'vertical_aperture', float, k=1)

        cam.near_clip.set_value(self.get_opt('near_clip'))
        cam.far_clip.set_value(self.get_opt('far_clip'))
        cam.focal_length.set_value(self.get_opt('focal_length'))
        cam.orthographic.set_value(self.get_opt('orthographic'))
        cam.horizontal_aperture.set_value(self.get_opt('horizontal_aperture'))
        cam.vertical_aperture.set_value(self.get_opt('vertical_aperture'))

        connect_mult(cam.near_clip, 0.99, cam_shp.near_clipping_plane)
        cam_shp.far_clipping_plane.connect(cam.far_clip)
        cam_shp.focal_length.connect(cam.focal_length)
        cam_shp.orthographic.connect(cam.orthographic)
        connect_mult(cam.horizontal_aperture, 2.54, cam_shp.horizontal_aperture)
        connect_mult(cam.vertical_aperture, 2.54, cam_shp.vertical_aperture)

        add_plug(cam, 'pan_x', float, k=1)
        add_plug(cam, 'pan_y', float, k=1)
        add_plug(cam, 'zoom', float, k=1, default_value=1, min_value=0.001)

        pan_2D = kl.FloatToV2f(cam_shp, 'pan_2D')
        cam_shp.pan_2D.connect(pan_2D.vector)
        connect_mult(cam.pan_x, 2.54, pan_2D.x)
        connect_mult(cam.pan_y, 2.54, pan_2D.y)
        connect_div(1, cam.zoom, cam_shp.zoom_2D)

        # FOV
        add_plug(cam, 'fovx', float)
        add_plug(cam, 'fov', float)
        add_plug(cam, 'width', float)
        add_plug(cam, 'height', float)

        _d = connect_mult(cam.horizontal_aperture, 25.4)
        _f = connect_mult(cam.focal_length, 2)
        connect_div(connect_mult(cam.horizontal_aperture, 10), _f, cam.fovx)

        df = connect_div(_d, _f)
        _atan = kl.Atan(cam, '_atan')
        _atan.input.connect(df)
        _fov = connect_mult(_atan.output, 2)
        cam.fov.connect(_fov)

        _w = connect_div(_fov, 2)
        _tan = kl.Tan(cam, '_tan')
        _tan.input.connect(_w)
        _w = connect_mult(_tan.output, 2, cam.width)

        _hd = connect_div(cam.vertical_aperture, cam.horizontal_aperture)
        _h = connect_mult(_w, _hd, cam.height)

        # pan geo
        add_plug(cam, 'geo_pan_x', float)
        add_plug(cam, 'geo_pan_y', float)
        pan_fov = connect_mult(cam.fovx, 1.56250314)
        connect_mult(connect_mult(cam.pan_x, 2.54), pan_fov, cam.geo_pan_x)
        connect_mult(connect_mult(cam.pan_y, 2.54), pan_fov, cam.geo_pan_y)

        # camera shape
        shp = mk.Shape(cam)
        _shp = kl.SceneGraphNode(find_root(), '_dummy')
        _shp = mk.Shape(_shp)

        _ = mk.Shape.create('cube')
        _.node.transform.set_value(M44f(V3f(0, 0, .7), V3f(0, 0, 0), V3f(.4, .5, .7), Euler.Default))
        _shp.copy(_, _shp)
        _.node.remove_from_parent()

        _ = mk.Shape.create('triangle')
        _.node.transform.set_value(M44f(V3f(0, 0, .125), V3f(180, 0, 90), V3f(.25, .25, .25), Euler.Default))
        _shp.copy(_, _shp)
        _.node.remove_from_parent()

        shp.copy(_shp, world=False)
        _shp.node.remove_from_parent()
        shp.set_color('green')

        # image plane
        if self.get_opt('image_plane'):
            add_plug(cam, 'imageplane_depth', float, k=1, default_value=100, min_value=0, nice_name="Image plane's depth")

        # registering
        if self.get_opt('do_ctrl'):
            self.set_id(cam, 'ctrls.camera')

        self.set_id(cam, 'camera')
        self.set_hook(self.node, cam, 'camera')
