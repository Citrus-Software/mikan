# coding: utf-8

import zlib
import base64
import os.path
from six import string_types, iteritems

import maya.api.OpenMaya as om
import maya.cmds as mc
from mikan.maya import cmdx as mx

from mikan.core import abstract
from mikan.core.utils.yamlutils import ordered_dump
from mikan.vendor.geomdl.utilities import generate_knot_vector

import mikan.templates.shapes

__all__ = ['Shape']


class Shape(abstract.Shape):
    def __init__(self, node):
        if isinstance(node, Shape):
            self.node = node.node
        else:
            if not isinstance(node, mx.Node):
                node = mx.encode(str(node))
            self.node = node

    def __repr__(self):
        return 'Shape(\'{}\')'.format(self.node)

    @staticmethod
    def create(name, **kw):
        if name not in Shape.shapes:
            raise RuntimeError('no shape named {}'.format(name))
        with mx.DagModifier() as md:
            root = md.create_node(mx.tTransform, name='shp_{}#'.format(name))
        s = Shape(root)
        s.add(name, **kw)
        return s

    def rename(self):
        shapes = self.get_shapes()
        n = '{}Shape'.format(self.node.name())
        if len(shapes) > 1:
            n += '#'
        for shape in shapes:
            shape.rename(n)

    def add(self, name, **kw):
        if name not in Shape.shapes:
            raise RuntimeError('no shape named {}'.format(name))

        if 'gem_shape_name' not in self.node:
            self.node.add_attr(mx.String('gem_shape_name'))
        self.node['gem_shape_name'] = name
        if 'axis' in kw and kw['axis']:
            if 'gem_shape_axis' not in self.node:
                self.node.add_attr(mx.String('gem_shape_axis'))
            self.node['gem_shape_axis'] = kw['axis']

        axis = kw.get('axis')
        if not axis:
            axis = 'y'
        else:
            axis = axis.lower()
        xfo = None
        if axis != 'y':
            r90 = mx.Degrees(90).asRadians()
            if axis == '-y':
                xfo = mx.Transformation(rotate=(0, 0, 2 * r90))
            elif axis in ('x', '+x'):
                xfo = mx.Transformation(rotate=(0, r90, -r90))
            elif axis == '-x':
                xfo = mx.Transformation(rotate=(r90, -r90, 0))
            elif axis in ('z', '+z'):
                xfo = mx.Transformation(rotate=(r90, 0, 0))
            elif axis == '-z':
                xfo = mx.Transformation(rotate=(-r90, 0, 0))

        data = Shape.shapes[name]
        for curve in data:
            value = Shape.get_curve_value(curve)
            with mx.DagModifier() as md:
                shp = md.create_node(mx.tNurbsCurve, parent=self.node, name='{}Shape'.format(name))
            mc.setAttr(str(shp) + '.cc', *value, type='nurbsCurve')

            if 'color' in curve:
                Shape.set_shape_color(shp, curve['color'])
            if curve.get('ghost'):
                Shape.set_shape_ghost(shp, True)

            if xfo:
                Shape.transform_shape(shp, xfo)

            with mx.DagModifier() as md:
                md.rename(shp, '{}Shape'.format(name))

    @staticmethod
    def get_curve_value(data):
        """
        First line: degree, number of spans, form (0=open, 1=closed, 2=periodic), rational (yes/no), dimension
        Second line: number of knots, list of knot values
        Third line: number of CVs
        Fourth and later lines: CV positions in x,y,z (and w if rational)
        """
        if isinstance(data, dict):
            points = data['points']
            s = len(points)
            d = data.get('degree', 1)
            f = 0
            if data.get('periodic'):
                f = 2
                points = points + points[:d]
            else:
                s -= d

            k = generate_knot_vector(d, len(points))
            if data.get('periodic') or d == 1:
                k = list(range(-d, len(k) - d))
            k = k[1:-1]  # maya way

        else:
            if not isinstance(data, mx.Node):
                data = mx.encode(str(data))
            if not data.is_a(mx.tNurbsCurve):
                raise TypeError('argument is not a valid nurbsCurve')

            fn = om.MFnNurbsCurve(data.object())
            d = fn.degree
            s = fn.numSpans
            k = fn.knots()
            f = 0 if fn.form == fn.kOpen else 2
            points = [list(cv)[:3] for cv in fn.cvPositions()]

        return [d, s, f, False, 3, k, len(k), len(points)] + points

    def get_shapes(self):
        shapes = []
        for shp in self.node.shapes(type=mx.tNurbsCurve):
            if 'gem_type' in shp and shp['gem_type'].read() == 'control':
                continue
            shapes.append(shp)
        return shapes

    def remove(self, last=False):
        shapes = self.get_shapes()
        if last:
            shapes = list(shapes)[-1:]

        for shape in shapes:
            if shape.is_a(mx.tNurbsCurve):
                try:
                    mx.delete(shape)
                except:
                    with mx.DGModifier() as md:
                        md.set_attr(shape['lodVisibility'], 0)

    def replace(self, name, **kw):
        self.remove()
        self.add(name, **kw)

    def copy(self, src, world=False):
        if not isinstance(src, Shape):
            if not isinstance(src, mx.Node):
                src = mx.encode(str(src))
            if not src.is_a((mx.tTransform, mx.tJoint)):
                raise RuntimeError('wrong source type')
            src = Shape(src)

        for shp in src.get_shapes():
            if shp['io'].read():
                continue

            value = Shape.get_curve_value(shp)
            with mx.DagModifier() as md:
                shp_new = md.create_node(mx.tNurbsCurve, parent=self.node)
            mc.setAttr(str(shp_new) + '.cc', *value, type='nurbsCurve')

            if world:
                xfo1 = src.node['wm'][0].as_matrix()
                xfo2 = self.node['wim'][0].as_matrix()
                Shape.transform_shape(shp_new, xfo1 * xfo2)

            if 'gem_color' in shp:
                Shape.set_shape_color(shp_new, Shape.get_shape_color(shp))
            if 'gem_color_ghost' in shp and shp['gem_color_ghost'].read():
                Shape.set_shape_ghost(shp_new)

    def move(self, target):
        if not isinstance(target, mx.Node):
            target = mx.encode(str(target))
        if not isinstance(target, mx.DagNode):
            raise RuntimeError('target is not a valid transform')

        for shp in self.get_shapes():
            mc.parent(str(shp), str(target), r=1, s=1)

    def shadow(self):
        for shp in self.get_shapes():
            shp['ihi'] = 0

    def scale(self, size, absolute=False, center=False, transform=False):

        if absolute:
            dim = self.get_dimensions()
            size *= 1 / max(dim)

        # scale transform directly
        if transform:
            if center:
                pivot = mx.Vector(self.get_bounding_box().center)
                p = pivot - pivot * size
                mc.move(p[0], p[1], p[2], str(self.node), os=1, r=1)
            mc.scale(size, size, size, str(self.node), r=1)
            return

        # scale components position
        if center:
            p = mx.Vector(self.get_bounding_box(world=True).center)

        for shp in self.get_shapes():
            if not center:
                mc.scale(size, size, size, str(shp) + '.cv[*]', r=1)
            else:
                mc.scale(size, size, size, str(shp) + '.cv[*]', r=1, p=p, os=1)

    @staticmethod
    def transform_shape(shp, xfo):
        if isinstance(xfo, mx.Transformation):
            xfo = xfo.as_matrix()

        fn = om.MFnNurbsCurve(shp.object())
        cvs = fn.cvPositions()
        for i, cv in enumerate(cvs):
            cvs[i] = om.MPoint(cv * xfo)
        fn.setCVPositions(cvs)
        fn.updateCurve()

    def transform(self, xfo):
        for shp in self.get_shapes():
            Shape.transform_shape(shp, xfo)

    # colors -----------------------------------------------------------------------------------------------------------

    def restore_color(self, force=False):
        has_color = False
        for shp in self.get_shapes():
            if not shp['overrideEnabled'].read() or force:
                if 'gem_color' in shp:
                    try:
                        Shape.set_shape_color(shp, shp['gem_color'].read())
                        has_color = True
                    except:
                        pass
                if 'gem_color_ghost' in shp and shp['gem_color_ghost'].read():
                    Shape.set_shape_ghost(shp)
        return has_color

    @staticmethod
    def set_shape_color(shp, color):
        if color is None:
            return
        if not isinstance(color, string_types):
            rgb = color
            color = Shape.rgb_to_hex(rgb)
        else:
            rgb = Shape.color_to_rgb(color)
        i = Shape.color_to_id(color)

        if not isinstance(shp, mx.Node):
            shp = mx.encode(str(shp))
        shp['overrideEnabled'] = 1
        shp['overrideColor'] = i
        if 'overrideRGBColors' in shp:
            shp['overrideRGBColors'] = 1
            shp['overrideColorRGB'] = Shape.srgb_to_rgb(rgb)

        if 'gem_color' not in shp:
            shp.add_attr(mx.String('gem_color'))
        shp['gem_color'] = color

    @staticmethod
    def get_shape_color(shp):
        if not isinstance(shp, mx.Node):
            shp = mx.encode(str(shp))

        if 'gem_color' in shp:
            return shp['gem_color'].read()

        else:
            if 'overrideRGBColors' in shp and shp['overrideRGBColors'].read():
                rgb = shp['overrideColorRGB'].read()
                srgb = Shape.rgb_to_srgb(rgb)
                Shape.set_shape_color(shp, srgb)
                return srgb

            if shp['overrideEnabled'].read():
                color_id = shp['overrideColor'].read()
                srgb = Shape.maya_color_list[color_id]
                Shape.set_shape_color(shp, srgb)
                return srgb

    @staticmethod
    def set_shape_ghost(shp, state=True):
        if not isinstance(shp, mx.Node):
            shp = mx.encode(str(shp))

        Shape.set_shape_color(shp, 'gray')

        shp['template'] = state
        if 'gem_color_ghost' not in shp:
            shp.add_attr(mx.Boolean('gem_color_ghost'))
        shp['gem_color_ghost'] = state

    @staticmethod
    def set_shape_color_flip(shp, state=True):
        if not isinstance(shp, mx.Node):
            shp = mx.encode(str(shp))

        if 'gem_color_flip' not in shp:
            shp.add_attr(mx.Boolean('gem_color_flip'))
        shp['gem_color_flip'] = state

    @staticmethod
    def is_shape_color_flip(shp):
        if not isinstance(shp, mx.Node):
            shp = mx.encode(str(shp))

        if 'gem_color_flip' in shp:
            return shp['gem_color_flip'].read()
        return False

    def set_color(self, color):
        for shp in self.get_shapes():
            Shape.set_shape_color(shp, color)

    def get_color(self):
        for shp in self.get_shapes():
            if 'gem_color' in shp:
                return shp['gem_color'].read()

    # geometry operations ----------------------------------------------------------------------------------------------

    def get_bounding_box(self, world=False):
        bb = mx.BoundingBox()

        for shp in self.get_shapes():
            _bb = shp.boundingBox
            if world:
                wm = shp.parent()['wm'][0].as_matrix()
                _bb.transformUsing(wm)
            bb.expand(_bb)

        return bb

    def get_dimensions(self):
        bb = self.get_bounding_box()
        if bb:
            return [round(x, 6) for x in [bb.width, bb.height, bb.depth]]

    def duplicate_shape(self):
        with mx.DagModifier() as md:
            dup = md.create_node(mx.tTransform, parent=self.node.parent(), name='shp_dupe#')

        fn = om.MFnNurbsCurve()
        for shp in self.get_shapes():
            fn.copy(shp.object(), dup.object())
            shp_new = list(dup.shapes())[-1]

            if 'gem_color' in shp:
                Shape.set_shape_color(shp_new, Shape.get_shape_color(shp))
            if 'gem_color_ghost' in shp and shp['gem_color_ghost'].read():
                Shape.set_shape_ghost(shp_new)

        for attr in ('gem_shape_name', 'gem_shape_axis'):
            if attr in self.node:
                dup.add_attr(mx.String(attr))
                dup[attr] = self.node[attr]

        return dup

    def duplicate_shapes(self):
        dupes = []

        fn = om.MFnNurbsCurve()
        for shp in self.get_shapes():
            with mx.DagModifier() as md:
                dup = md.create_node(mx.tTransform, parent=self.node.parent(), name='shp_dupe#')

            fn.copy(shp.object(), dup.object())
            shp_new = dup.shape()

            if 'gem_color' in shp:
                Shape.set_shape_color(shp_new, Shape.get_shape_color(shp))
            if 'gem_color_ghost' in shp and shp['gem_color_ghost'].read():
                Shape.set_shape_ghost(shp_new)
            dupes.append(dup)

        return dupes

    # shape signature ----------------------------------------------------------

    def get_signature(self):
        sig = ''
        for shp in self.get_shapes():
            fn = om.MFnNurbsCurve(shp.object())
            for p in fn.cvPositions(mx.sObject):
                for v in list(p)[:3]:
                    sig += '{0:.3f}'.format(round(v, 3) + 0).rstrip('0').rstrip('.') + ' '

        sig = sig[:-1]
        sigz = base64.b64encode(zlib.compress(sig.encode('utf-8'), 9)).decode('utf-8')
        return sigz

    def add_signature(self):
        if 'gem_shape_signature' not in self.node:
            self.node.add_attr(mx.String('gem_shape_signature'))
        self.node['gem_shape_signature'] = self.get_signature()

    @staticmethod
    def decode_signature(sig):
        points = [float(v) for v in zlib.decompress(base64.b64decode(sig)).split()]
        return [points[i:i + 3] for i in range(0, len(points), 3)]

    def set_signature(self, sig):
        points = Shape.decode_signature(sig)

        lens = []
        shapes = self.get_shapes()

        for shp in shapes:
            fn = om.MFnNurbsCurve(shp.object())
            lens.append(fn.numCVs)

        if sum(lens) != len(points):
            raise ValueError('wrong signature')

        for shp in shapes:
            fn = om.MFnNurbsCurve(shp.object())
            n = fn.numCVs
            fn.setCVPositions(points[:n])
            fn.updateCurve()
            points = points[n:]

    # extract utilities --------------------------------------------------------

    @staticmethod
    def get_yaml_dump(curve, decimals=4):
        curves = []
        for cv in curve.shapes():
            data = {}
            fn = om.MFnNurbsCurve(cv.object())

            points = fn.cvPositions()
            points = [[round(p[0], decimals), round(p[1], decimals), round(p[2], decimals)] for p in points]

            data['points'] = points
            data['degree'] = fn.degree
            if fn.form == om.MFnNurbsCurve.kPeriodic:
                data['periodic'] = True
                data['points'] = data['points'][:-data['degree']]
            if 'gem_color' in cv:
                data['color'] = cv['gem_color'].read()
            if 'gem_color_ghost' in cv and cv['gem_color_ghost'].read():
                data['ghost'] = True

            curves.append(data)

        return ordered_dump(curves)

    def get_flatten(self):
        dupe = self.duplicate_shape()
        dupe = Shape(dupe)

        v = [0, 1, 0]
        s0 = 0
        s1 = 2
        dim = dupe.get_dimensions()

        if dim[0] < dim[1] and dim[0] < dim[2]:
            v = [1, 0, 0]
            s0 = 1
            s1 = 2
        elif dim[2] < dim[1] and dim[2] < dim[0]:
            v = [0, 0, 1]
            s0 = 0
            s1 = 1

        loc = mx.create_node(mx.tTransform)
        loc['ty'] = 1

        mc.delete(mc.aimConstraint(str(loc), str(dupe.node), aim=v, wut='None'))
        mx.delete(loc)

        dummy = mx.create_node(mx.tTransform)
        dummy['rx'] = mx.Degrees(90)
        mc.parent(str(dupe.node), str(dummy))

        mc.makeIdentity(str(dupe.node), a=1)
        if dim[s0] > 0.1 and dim[s1] > 0.1:
            dupe.node['shxz'] = 0.333
            dupe.node['shyz'] = 0.333
        mc.makeIdentity(str(dupe.node), a=1)
        dupe.node['sz'] = 0
        mc.parent(str(dupe.node), w=1)
        mx.delete(dummy)
        mc.makeIdentity(str(dupe.node), a=1)

        return dupe.node

    def get_beziers(self):
        dupes = self.duplicate_shapes()
        mx.cmd(mc.select, dupes)
        mc.nurbsCurveToBezier()
        dupes = mx.ls(sl=1)
        return dupes

    def get_svg_snapshot(self):
        flatten = Shape(self.get_flatten())
        mc.xform(str(flatten.node), cp=1)
        mc.move(0, 0, 0, str(flatten.node), rpr=1)

        dim = flatten.get_dimensions()
        s = max(dim)
        flatten.node['sx'] = 1 / s
        flatten.node['sz'] = 1 / s
        mc.makeIdentity(str(flatten.node), a=1)

        paths = []
        for cv in flatten.get_shapes():

            color = ''
            if 'gem_color' in cv:
                color = ' stroke="{}"'.format(cv['gem_color'].read())

            cmd = 'L'
            if cv['degree'].read() == 3:
                cmd = 'C'
                mc.select(str(cv))
                mc.nurbsCurveToBezier()
                cv = list(flatten.node.shapes())[-1]
            elif cv['degree'].read() == 2:
                cmd = 'C'
                mc.rebuildCurve(str(cv), d=3, kcp=1)
                mc.select(str(cv))
                mc.nurbsCurveToBezier()
                cv = list(flatten.node.shapes())[-1]

            z = ''
            if cv['form'].read() > 1:
                z = ' Z'

            cvs = mc.ls('{}.cv[*]'.format(cv), fl=1)
            cvs = [mc.xform(x, q=1, t=1, ws=1) for x in cvs]
            cvs = [(round(p[0], 4), round(p[2], 4)) for p in cvs]

            x = cvs[0][0]
            y = cvs[0][1]
            points = ' '.join(['{},{}'.format(p[0], p[1]) for p in cvs[1:]])

            paths.append('<path d="M {x},{y} {cmd} {points}{z}"{color}/>'.format(x=x, y=y, points=points, cmd=cmd, z=z, color=color))

        paths = '\n'.join(paths)

        mx.delete(flatten.node)
        return svg_shape_template.format(paths=paths)

    @staticmethod
    def rebuild_svg_icons():
        path = mikan.templates.shapes.__path__[0]
        path = os.path.join(path, 'icons')

        for shp, abc in iteritems(Shape.shapes):
            s = Shape.create(shp)
            svg = s.get_svg_snapshot()
            mx.delete(s.node)

            with open(os.path.join(path, '{}.svg'.format(shp)), 'w') as f:
                f.writelines(svg)


svg_shape_template = '''<?xml version="1.0" encoding="utf-8"?>
<svg width="100%" height="100%" viewBox="0 0 64 64"
     xmlns="http://www.w3.org/2000/svg">
<style type="text/css">
<![CDATA[
* {{fill: none; stroke: #aaa; stroke-width: 0.03; stroke-linejoin: round;}}
]]>
</style>
<g transform="translate(32, 32) scale(48, 48)" class="curve">
{paths}
</g>
</svg>'''

"""
for shp in mk.Shape.shapes:
    path = mk.Shape.shapes[shp]
    path = path.replace('.abc', '.yml')
    
    curve = mk.Shape.create(shp).node
    data = mk.Shape.get_yaml_dump(curve)
    
    with open(path, 'w') as f:
      f.writelines(data)
"""
