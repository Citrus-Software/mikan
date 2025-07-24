# coding: utf-8

import meta_nodal_py as kl
from meta_nodal_py.Imath import V3f, M44f, Box3f, Euler

from mikan.core import abstract
from mikan.vendor.geomdl.utilities import generate_knot_vector

from ..lib.commands import *

__all__ = ['Shape']


class Shape(abstract.Shape):

    def __init__(self, node):
        self.node = node

    def __repr__(self):
        return f"Shape('{self.node.get_name()}')"

    @staticmethod
    def create(name, **kw):
        if name not in Shape.shapes:
            raise RuntimeError(f'no shape named {name}')
        s = kl.SceneGraphNode(find_root(), f'shp_{name}')
        s = Shape(s)
        s.add(name, **kw)
        return s

    def rename(self):
        shapes = self.get_shapes()
        n = f'{self.node.get_name()}Shape'
        for shape in shapes:
            shape.rename(n)

    def add(self, name, **kw):
        if name not in Shape.shapes:
            raise RuntimeError(f'no shape named {name}')

        if not self.node.get_dynamic_plug('gem_shape_name'):
            add_plug(self.node, 'gem_shape_name', str)
        self.node.gem_shape_name.set_value(name)
        if 'axis' in kw and kw['axis']:
            if not self.node.get_dynamic_plug('gem_shape_axis'):
                add_plug(self.node, 'gem_shape_axis', str)
            self.node.gem_shape_axis.set_value(kw['axis'])

        axis = kw.get('axis')
        if not axis:
            axis = 'y'
        else:
            axis = axis.lower()
        xfo = None
        if axis != 'y':
            if axis == '-y':
                xfo = M44f(V3f(0, 0, 0), V3f(0, 0, 180), V3f(1, 1, 1), Euler.XYZ)
            elif axis in ('x', '+x'):
                xfo = M44f(V3f(0, 0, 0), V3f(0, 0, -90), V3f(1, 1, 1), Euler.XYZ)
            elif axis == '-x':
                xfo = M44f(V3f(0, 0, 0), V3f(0, 0, 90), V3f(1, 1, 1), Euler.XYZ)
            elif axis in ('z', '+z'):
                xfo = M44f(V3f(0, 0, 0), V3f(90, 0, 0), V3f(1, 1, 1), Euler.XYZ)
            elif axis == '-z':
                xfo = M44f(V3f(0, 0, 0), V3f(-90, 0, 0), V3f(1, 1, 1), Euler.XYZ)

        data = Shape.shapes[name]
        for curve in data:
            shp = kl.SplineCurve(self.node, 'shape')

            points = curve['points']
            d = curve.get('degree', 1)

            wrap = False
            if curve.get('periodic'):
                wrap = True
                points = points + points[:d]
            points = [V3f(*point) for point in points]

            if xfo:
                for i, cp in enumerate(points):
                    xcp = M44f(cp, V3f(0, 0, 0), V3f(1, 1, 1), Euler.Default)
                    points[i] = (xcp * xfo).translation()

            knots = generate_knot_vector(d, len(points))
            if wrap or d == 1:
                knots = list(range(-d, len(knots) - d))
            weights = [1] * len(points)

            data = kl.Spline(points, knots, weights, wrap)
            shp.spline_in.set_value(data)

            shp.sampling_in.set_value((len(points) + 1) * (d ** 2))
            shp.world_transform.connect(self.node.world_transform)

            if 'color' in curve:
                Shape.set_shape_color(shp, curve['color'])
            if curve.get('ghost'):
                Shape.set_shape_ghost(shp, True)

    def get_shapes(self):
        shapes = []
        for node in self.node.get_children():
            if node.get_dynamic_plug('gem_type') and node.gem_type.get_value() == 'control':
                continue
            if isinstance(node, kl.SplineCurve):
                shapes.append(node)
        return shapes

    def remove(self):
        for shape in self.get_shapes():
            if type(shape) in (kl.SplineCurve, kl.SplineCurveReader):
                shape.remove_from_parent()

    def replace(self, name, **kw):
        self.remove()
        self.add(name, **kw)

    def copy(self, src, world=False):
        if not isinstance(src, Shape):
            if type(src) not in (kl.SceneGraphNode, kl.Joint):
                raise RuntimeError('wrong source type')
            src = Shape(src)

        for shp in src.get_shapes():
            cv = kl.SplineCurve(self.node, shp.get_name())
            spline = shp.spline_in.get_value()
            cps = spline.get_control_points()
            degree = spline.get_degree()
            cv.sampling_in.set_value((len(cps) + 1 - int(spline.get_wrap())) * (degree ** 2))

            if world:
                xfo1 = src.node.world_transform.get_value()
                xfo2 = self.node.world_transform.get_value().inverse()
                for i, cp in enumerate(cps):
                    xcp = M44f(cp, V3f(0, 0, 0), V3f(1, 1, 1), Euler.Default)
                    cps[i] = (xcp * xfo1 * xfo2).translation()
                spline = kl.Spline(cps, spline.get_knots(), spline.get_weights(), spline.get_wrap())
            cv.spline_in.set_value(spline)

            if shp.get_dynamic_plug('gem_color'):
                Shape.set_shape_color(cv, shp.gem_color.get_value())
            else:
                mat = shp.shader_in.get_value()
                cv.shader_in.set_value(mat)

            if shp.get_dynamic_plug('gem_color_ghost') and shp.gem_color_ghost.get_value():
                Shape.set_shape_ghost(cv)

    def move(self, target):
        if not isinstance(target, kl.SceneGraphNode):
            raise RuntimeError('target is not a valid transform')

        for shp in self.get_shapes():
            shp.set_parent(target)
            shp.world_transform.connect(target.world_transform)

    def shadow(self):
        for shp in self.get_shapes():
            set_plug(shp.show, k=0)

    def scale(self, size, absolute=False, center=False):

        if absolute:
            dim = self.get_dimensions()
            size *= 1 / max((dim.x, dim.y, dim.z))

        for shp in self.get_shapes():
            spline = shp.spline_in.get_value()
            if not center:
                cvs = map(lambda x: x * size, spline.get_control_points())
            else:
                center = self.get_bounding_box().center()
                cvs = map(lambda x: (x - center) * size + center, spline.get_control_points())
            data = kl.Spline(list(cvs), spline.get_knots(), spline.get_weights(), spline.get_wrap())
            shp.spline_in.set_value(data)

    # colors -----------------------------------------------------------------------------------------------------------

    def restore_color(self, force=False):
        has_color = False
        for shp in self.get_shapes():
            color = shp.shader_in.get_value().get_filled_color()
            is_white = color.r + color.g + color.b >= 2.999
            if is_white or force:
                if shp.get_dynamic_plug('gem_color'):
                    try:
                        Shape.set_shape_color(shp, shp.gem_color.get_value())
                        has_color = True
                    except:
                        pass
            if shp.get_dynamic_plug('gem_color_ghost') and shp.gem_color_ghost.get_value():
                Shape.set_shape_ghost(shp)
        return has_color

    @staticmethod
    def set_shape_color(shp, color):
        if color is None:
            return
        srgb = Shape.color_to_rgb(color)
        rgb = Shape.srgb_to_rgb(srgb)
        value = kl.Imath.Color4f(rgb[0], rgb[1], rgb[2], 1)
        sh = kl.Shader('', value)
        shp.shader_in.set_value(sh)

        plug = shp.get_dynamic_plug('gem_color')
        if not plug:
            plug = add_plug(shp, 'gem_color', str)
        plug.set_value(color)

    @staticmethod
    def set_shape_ghost(shp, state=True):
        shp.set_pickable(not state)
        plug = shp.get_dynamic_plug('gem_color_ghost')
        if not plug:
            plug = add_plug(shp, 'gem_color_ghost', bool)
        plug.set_value(state)

    @staticmethod
    def set_shape_color_flip(shp, state=True):
        plug = shp.get_dynamic_plug('gem_color_flip')
        if not plug:
            plug = add_plug(shp, 'gem_color_flip', bool)
        plug.set_value(state)

    @staticmethod
    def is_shape_color_flip(shp):
        plug = shp.get_dynamic_plug('gem_color_flip')
        if plug:
            return plug.get_value()
        return False

    def set_color(self, color):
        for shp in self.get_shapes():
            Shape.set_shape_color(shp, color)

    # geometry operations ----------------------------------------------------------------------------------------------

    def get_bounding_box(self, world=False):
        bb = None
        for curve in self.get_shapes():
            spline = curve.spline_in.get_value()
            if world:
                _bb = kl.Deformer.Compute_spline_bounds(spline)
            else:
                _bb = kl.Deformer.Compute_spline_bounds_in_space(spline, M44f())
            if bb is None:
                bb = _bb
            else:
                bb.extendBy(_bb)
        return bb

    def get_dimensions(self):
        return self.get_bounding_box().size()

    def duplicate_shape(self):
        node = kl.SceneGraphNode(self.node.get_parent(), f'{self.node.get_name()}_dupe')
        for shape in self.get_shapes():
            cv = kl.SplineCurve(node, shape.get_name())
            cv.spline_in.set_value(shape.spline_in.get_value())
            cv.shader_in.set_value(shape.shader_in.get_value())
        return node

    def duplicate_shapes(self):
        nodes = []
        for shape in self.get_shapes():
            node = kl.SceneGraphNode(self.node.get_parent(), f'{self.node.get_name()}_dupe')
            cv = kl.SplineCurve(node, shape.get_name())
            cv.spline_in.set_value(shape.spline_in.get_value())
            cv.shader_in.set_value(shape.shader_in.get_value())
            nodes.append(node)
        return nodes
