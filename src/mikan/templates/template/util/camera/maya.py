# coding: utf-8

from mikan.maya import cmds as mc
import mikan.maya.cmdx as mx

import mikan.maya.core as mk
from mikan.maya.lib.rig import copy_transform
from mikan.maya.lib.connect import connect_mult, connect_expr


class Template(mk.Template):

    def build_template(self, data):
        self.node['t'] = data['transform']

    def build_rig(self):
        hook = self.get_hook()

        cam = mx.create_node(mx.tTransform, parent=hook, name=self.name)
        copy_transform(self.node, cam, t=True, r=True)
        cam_shp = mx.create_node(mx.tCamera, parent=cam, name=self.name + 'Shape')

        cam.add_attr(mx.Double('focal_length', keyable=True, min=1))
        cam.add_attr(mx.Double('near_clip', keyable=True, min=0.001))
        cam.add_attr(mx.Double('far_clip', keyable=True))
        cam.add_attr(mx.Boolean('orthographic', keyable=True))
        cam.add_attr(mx.Double('horizontal_aperture', keyable=True))
        cam.add_attr(mx.Double('vertical_aperture', keyable=True))

        cam['horizontal_aperture'] = self.get_opt('horizontal_aperture')
        cam['vertical_aperture'] = self.get_opt('vertical_aperture')
        cam['focal_length'] = self.get_opt('focal_length')
        cam['near_clip'] = self.get_opt('near_clip')
        cam['far_clip'] = self.get_opt('far_clip')
        cam['orthographic'] = self.get_opt('orthographic')

        cam['horizontal_aperture'] >> cam_shp['horizontalFilmAperture']
        cam['vertical_aperture'] >> cam_shp['verticalFilmAperture']
        cam['focal_length'] >> cam_shp['focalLength']
        connect_mult(cam['near_clip'], 0.99, cam_shp['nearClipPlane'])
        cam['far_clip'] >> cam_shp['farClipPlane']
        cam['orthographic'] >> cam_shp['orthographic']

        cam.add_attr(mx.Double('pan_x', keyable=True))
        cam.add_attr(mx.Double('pan_y', keyable=True))
        cam.add_attr(mx.Double('zoom', keyable=True, default=1, min=0.001))

        cam_shp['panZoomEnabled'] = True
        cam_shp['renderPanZoom'] = True
        cam['pan_x'] >> cam_shp['horizontalPan']
        cam['pan_y'] >> cam_shp['verticalPan']
        connect_expr('zoom = ortho == 1 ? (z * 10) : z', zoom=cam_shp['zoom'], ortho=cam['orthographic'], z=cam['zoom'])

        for plug in ('lsr', 'fs', 'fd', 'sa', 'lla'):
            try:
                cam_shp[plug].keyable = True
                cam_shp[plug].lock()
            except:
                pass

        for plug in ('lensSqueezeRatio', 'fStop', 'focusDistance', 'shutterAngle', 'locatorScale'):
            cam_shp[plug].keyable = False
            cam_shp[plug].channel_box = True

        # FOV
        cam.add_attr(mx.Double('fovx'))
        cam.add_attr(mx.Double('fov'))
        cam.add_attr(mx.Double('width'))
        cam.add_attr(mx.Double('height'))

        fovx = connect_expr("(25.4 * d) / (2 * f)", d=cam['horizontal_aperture'], f=cam['focal_length'])  # 25.4 mm = 1 in
        fov = connect_expr("(2 * atan(fovx)) * (180 / 3.141592)", fovx=fovx)
        width = connect_expr("2 * tan((3.141592 / 180) * (fov / 2))", fov=fov)
        height = connect_expr("width * h / d", width=width, h=cam['vertical_aperture'], d=cam['horizontal_aperture'])

        fovx >> cam['fovx']
        fov >> cam['fov']
        width >> cam['width']
        height >> cam['height']

        # pan geo
        cam.add_attr(mx.Double('geo_pan_x'))
        cam.add_attr(mx.Double('geo_pan_y'))
        pan_fov = connect_mult(cam['fovx'], 1.56250314)
        connect_mult(cam['pan_x'], pan_fov, cam['geo_pan_x'])
        connect_mult(cam['pan_y'], pan_fov, cam['geo_pan_y'])

        # image plane
        if self.get_opt('image_plane'):
            cam.add_attr(mx.Double('imageplane_depth', keyable=True, default=100, min=0))

        # registering
        if self.get_opt('do_ctrl'):
            self.set_id(cam, 'ctrls.camera')

        self.set_id(cam, 'camera')
        self.set_hook(self.node, cam, 'camera')
