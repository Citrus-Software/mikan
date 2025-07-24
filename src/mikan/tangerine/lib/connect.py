# coding: utf-8

import math

import meta_nodal_py as kl
from meta_nodal_py.Imath import V3f, Euler, Quatf, M44f

from mikan.core.utils.typeutils import singleton
from mikan.core.expression import ExpressionParser as _ExpressionParser
from mikan.tangerine.lib.commands import add_plug
from mikan.core.logger import create_logger

log = create_logger()

__all__ = [
    'safe_connect',
    'connect_add', 'connect_mult', 'connect_sub', 'connect_div', 'connect_reverse', 'connect_sum', 'connect_power',
    'connect_additive', 'connect_remap', 'connect_driven_curve', 'create_curve_value',
    'blend_smooth_remap', 'blend_smooth_weights',
    'connect_expr'
]


def safe_connect(plug_out, plug_in):
    type_out = plug_out.get_type()
    type_in = plug_in.get_type()

    if type_out is type_in:
        plug_in.connect(plug_out)
        return

    types = {float, int, bool}
    if type_out not in types or type_in not in types:
        raise RuntimeError('can\'t connect plug {} <{}> to {} <{}>'.format(plug_out, type_out, plug_in, type_in))

    parent = plug_in.get_node()

    c = None
    if type_in is float:
        if type_out is int:
            c = kl.IntToFloat(parent, '_float')
        elif type_out is bool:
            c = kl.BoolToFloat(parent, '_float')
    elif type_in is int:
        if type_out is float:
            c = kl.FloatToInt(parent, '_int')
        elif type_out is bool:
            c = kl.BoolToInt(parent, '_int')
    elif type_in is bool:
        if type_out is float:
            c = kl.FloatToBool(parent, '_bool')
        elif type_out is int:
            c = kl.IntToBool(parent, '_bool')

    plug_in.connect(c.output)
    c.input.connect(plug_out)

    add_plug(c, 'converted_input', type_out)
    c.converted_input.connect(plug_out)

    return c.input


def connect_remap(plug, min1, max1, min2, max2, plug_out=None):
    remap = kl.RemapFloat(plug.get_node(), plug.get_name() + '_remap')
    remap.input.connect(plug)
    remap.min1.set_value(min1)
    remap.max1.set_value(max1)
    remap.min2.set_value(min2)
    remap.max2.set_value(max2)

    if kl.is_plug(plug_out):
        safe_connect(remap.output, plug_out)

    return remap.output


def connect_operation(mode, *args, **kw):
    if len(args) < 2 or len(args) > 3:
        raise RuntimeError('wrong number of arguments')
    if mode not in ('add', 'mult', 'sub', 'div', 'power'):
        raise RuntimeError('wrong operation')

    parent = kw.get('parent')
    if 'p' in kw:
        parent = kw['p']
    if not isinstance(parent, kl.Node):
        if len(args) > 2 and kl.is_plug(args[2]):
            parent = args[2].get_node()
        elif kl.is_plug(args[1]):
            parent = args[1].get_node()
        elif kl.is_plug(args[0]):
            parent = args[0].get_node()

    name = f'_{mode}'
    if 'n' in kw:
        name = str(kw['n'])

    op = None
    if mode == 'add':
        op = kl.Add(parent, name)
    elif mode == 'sub':
        op = kl.Sub(parent, name)
    elif mode == 'mult':
        op = kl.Mult(parent, name)
    elif mode == 'div':
        op = kl.Div(parent, name)
    elif mode == 'power':
        op = kl.Pow(parent, name)

    if kl.is_plug(args[0]):
        safe_connect(args[0], op.input1)
    else:
        op.input1.set_value(args[0])

    if kl.is_plug(args[1]):
        safe_connect(args[1], op.input2)
    else:
        op.input2.set_value(args[1])

    # connect output
    if len(args) == 3:
        if kl.is_plug(args[2]):
            safe_connect(op.output, args[2])

    # op.rename(name)
    return op.output


def connect_add(*args, **kw):
    return connect_operation('add', *args, **kw)


def connect_mult(*args, **kw):
    return connect_operation('mult', *args, **kw)


def connect_sub(*args, **kw):
    return connect_operation('sub', *args, **kw)


def connect_power(*args, **kw):
    return connect_operation('power', *args, **kw)


def connect_reverse(*args, **kw):
    return connect_sub(1, *args, **kw)


def connect_div(*args, **kw):
    return connect_operation('div', *args, **kw)


def connect_sum(plugs, plug_out=None, n=None, p=None, parent=None):
    if isinstance(p, kl.Node):
        parent = p
    elif plug_out:
        parent = plug_out.get_node()
    elif plugs:
        parent = plugs[0].get_node()

    _sum = None
    if n is None:
        n = '_sum'

    if len(plugs) == 2:
        if plug_out:
            _sum = connect_add(plugs[0], plugs[1], plug_out, n=n)
        else:
            _sum = connect_add(plugs[0], plugs[1], n=n)

    elif len(plugs) > 2:
        _sum = plugs[0]
        for plug in plugs[1:]:
            _nsum = kl.Add(parent, n)
            safe_connect(_sum, _nsum.input1)
            safe_connect(plug, _nsum.input2)
            _sum = _nsum.output

        if plug_out:
            safe_connect(_sum, plug_out)

    return _sum


def connect_additive(plug_out, plug_in):
    plug_in_node = plug_in.get_node()

    if plug_in.is_connected():
        input_node = plug_in.get_input().get_node()
        if isinstance(input_node, kl.Add):
            if not input_node.input2.get_value() and not input_node.input2.is_connected():
                plug_in = input_node.input2
            else:
                input_node.add_inputs(1)
                i = input_node.get_input_count()
                plug_in = input_node.get_dynamic_plug(f'input{i}')

        else:
            i = plug_in.get_input()
            add = kl.Add(plug_in_node, '_add')
            safe_connect(add.output, plug_in)
            safe_connect(i, add.input1)
            plug_in = add.input2

    safe_connect(plug_out, plug_in)
    return plug_out


def connect_driven_curve(plug_out, plug_in, keys=None, tangent_mode=None, pre=None, post=None, parent=None):
    for plug in (plug_out, plug_in):
        if plug is not None and not kl.is_plug(plug):
            return
    if not any((plug_out, plug_in)) and parent is None:
        raise RuntimeError('cannot create driven curve: not enough arguments')

    # args
    if keys is None:
        keys = {0: 0, 1: 1}

    if pre is None:
        pre = 'linear'
    pre = _infinities[pre]
    if post is None:
        post = 'linear'
    post = _infinities[post]

    do_scale = 0

    if plug_in:
        # do scale?
        plug_in_node = plug_in.get_node()
        if isinstance(plug_in_node, kl.FloatToV3f):
            outputs = plug_in_node.vector.get_outputs()
            if outputs:
                if outputs[0].get_name() == 'scale':
                    do_scale = 1

                    if not plug_in.is_connected():
                        _bw = kl.Add(plug_in_node, '_add')
                        _bw.input1.set_value(1)
                        safe_connect(_bw.output, plug_in)

        # create driven curve
        crv_node = _find_driven_curve(plug_in, plug_out)
        if not crv_node:
            crv_node = kl.DrivenFloat(plug_in.get_node(), '_driven_curve')
            safe_connect(plug_out, crv_node.driver)
            connect_additive(crv_node.result, plug_in)

    elif not plug_out:
        crv_node = kl.DrivenFloat(parent, '_driven_curve')
    else:
        crv_node = kl.DrivenFloat(plug_out.get_node(), '_driven_curve')
        safe_connect(plug_out, crv_node.driver)

    crv = create_curve_value(keys, curve=crv_node.curve.get_value(), tangent_mode=tangent_mode, do_scale=do_scale)
    crv_node.curve.set_value(crv)
    crv_node.pre_cycle.set_value(pre)
    crv_node.post_cycle.set_value(post)

    return crv_node


_infinities = {
    'constant': kl.Cycle.constant,
    'cycle': kl.Cycle.repeat,
    'repeat': kl.Cycle.repeat,
    'offset': kl.Cycle.repeat_continuous,
    'continuous': kl.Cycle.repeat_continuous,
    'linear': kl.Cycle.linear,
}

_map_tangent_mode = {
    'linear': kl.TangentMode.linear,
    'auto': kl.TangentMode.auto,
    'fast': kl.TangentMode.custom,
    'slow': kl.TangentMode.custom,
    'stepnext': kl.TangentMode.custom,
    'fixed': kl.TangentMode.custom,
    'clamped': kl.TangentMode.custom,
    'spline': kl.TangentMode.spline,
    'plateau': kl.TangentMode.flat,
    'flat': kl.TangentMode.flat,
    'step': kl.TangentMode.step,
}


# get anim curve if any
def _find_driven_curve(plug_in, plug_out):
    if not plug_in.is_connected():
        return
    input_node = plug_in.get_input().get_node()
    if isinstance(input_node, kl.DrivenFloat):
        input_driver = input_node.driver.get_input()
        input_driver_node = input_driver.get_node()
        if plug_out.get_type() is int:
            if isinstance(input_driver_node, kl.IntToFloat):
                input_driver = input_driver_node.input.get_input()
        elif plug_out.get_type() is bool:
            if isinstance(input_driver_node, kl.Condition):
                input_driver = input_driver_node.condition.get_input()
        if input_driver == plug_out:
            return input_node
    elif isinstance(input_node, kl.Add):
        for i in range(input_node.get_input_count()):
            _input = _find_driven_curve(input_node.get_plug(f'input{i + 1}'), plug_out)
            if _input:
                return _input

    # skip conversion nodes
    elif input_node.get_dynamic_plug('converted_input'):
        _input = _find_driven_curve(input_node.converted_input, plug_out)
        if _input:
            return _input
    elif plug_in.get_type() is int and isinstance(input_node, kl.FloatToInt):
        _input = _find_driven_curve(input_node.input, plug_out)
        if _input:
            return _input
    elif plug_in.get_type() is bool and isinstance(input_node, kl.Not) and input_node.get_name().startswith('_bool'):
        eq = input_node.input.get_input()
        if eq:
            _input = _find_driven_curve(eq.input1, plug_out)
            if _input:
                return _input


def create_curve_value(keys, curve=None, tangent_mode=None, do_scale=0):
    if tangent_mode is None:
        tangent_mode = 'spline'
    tangent_mode = _map_tangent_mode[tangent_mode]

    # add keys
    rmb_keys = []
    for k, data in keys.items():
        left_tangent_mode = tangent_mode
        right_tangent_mode = tangent_mode
        dxl, dyl, dxr, dyr = -1, 0, 1, 0

        if isinstance(data, dict):
            if 'v' not in data:
                continue
            v = data['v']
            if 'tan' in data:
                left_tangent_mode = _map_tangent_mode[data['tan']]
                right_tangent_mode = _map_tangent_mode[data['tan']]
            if 'itan' in data:
                left_tangent_mode = _map_tangent_mode[data['itan']]
            if 'otan' in data:
                right_tangent_mode = _map_tangent_mode[data['otan']]

            if 'ix' in data:
                dxl = data['ix']
                dyl = data['iy']
                left_tangent_mode = _map_tangent_mode['fixed']
            if 'ox' in data:
                dxr = data['ox']
                dyr = data['oy']
                right_tangent_mode = _map_tangent_mode['fixed']

        elif type(data) in (float, int, bool):
            v = data
        else:
            continue
        v -= do_scale

        key = (float(v), float(k), dxl, dyl, dxr, dyr, int(left_tangent_mode), int(right_tangent_mode))
        rmb_keys.append(key)

    if curve is None:
        curve = kl.CurveFloat()
    curve.set_keys_with_tangent_mode(rmb_keys)

    return curve


def blend_smooth_remap(plugs_out, plugs_in, connect=True):
    remaps = []

    # smooth step curves
    for o, plug_out in enumerate(plugs_out):
        crv = kl.CurveFloat()
        n = len(plugs_out)
        f = float(o) / (n - 1)
        fn = 1. / (n - 1) * 1.5
        crv.set_keys_with_tangent_mode([(0, f - fn, 4), (1, f, 4), (0, f + fn, 4)])
        remaps.append(crv)

    # blend network
    plugs_out_array = []
    for i, plug_in in enumerate(plugs_in):
        plug_out_array = []
        plugs_out_array.append(plug_out_array)

        for o in range(len(plugs_out)):
            _m = kl.Mult(plug_in.get_node(), '_weight')
            plug_out_array.append(_m)

        _adds = []
        for o in range(len(plugs_out) - 1):
            _add = kl.Add(plug_in.get_node(), '_add')
            if o == 0:
                _add.input1.connect(plug_out_array[0].output)
                _add.input2.connect(plug_out_array[1].output)
            else:
                _add.input1.connect(_adds[-1].output)
                _add.input2.connect(plug_out_array[o + 1].output)
            _adds.append(_add)

        if connect:
            if plug_in.get_input():
                _add = kl.Add(plug_in.get_node(), '_add')
                _add.input1.connect(plug_in.get_input())
                _add.input2.connect(_adds[-1].output)
                plug_in.disconnect(restore_default=True)
                plug_in.connect(_add.output)
            else:
                plug_in.connect(_adds[-1].output)

    # weighted network
    for i, plug_in in enumerate(plugs_in):
        n = len(plugs_in)
        s = 0
        for o, plug_out in enumerate(plugs_out):
            bw = plugs_out_array[i][o]
            bw.input1.connect(plug_out)

            _cycle = kl.Cycle.constant
            v = i / float(n - 1)
            v = remaps[o].cubic_interpolate(v, _cycle, _cycle)
            bw.input2.set_value(v)
            s += v

        for o, plug_out in enumerate(plugs_out):
            bw = plugs_out_array[i][o]
            v = bw.input2.get_value() / s
            bw.input2.set_value(v)


def blend_smooth_weights(node, n, smooth=2, periodic=False):
    # check args
    if not isinstance(node, kl.Node):
        raise TypeError('first argument is not a node')

    n = int(n)

    if smooth < 1:
        smooth = 1
        log.warning('/!\\ blend smooth weights: smooth value cannot be under 1')

    # build
    plug_driver = add_plug(node, 'u', float, keyable=True, min_value=0, max_value=1)

    remaps = []

    if not periodic:
        for i in range(n):
            f = i / (n - 1.)
            x = smooth / (n - 1.)
            fp = f + x
            fn = f - x
            if fp > 1:
                fp = 1
            if fn < 0:
                fn = 0

            _keys = [(1, f, int(kl.TangentMode.spline))]
            if i < n - 1:
                _keys.append((0, fp, int(kl.TangentMode.flat)))
            if i > 0:
                _keys.append((0, fn, int(kl.TangentMode.flat)))

            crv = kl.CurveFloat()
            crv.set_keys_with_tangent_mode(_keys)

            crv_node = kl.DrivenFloat(node, f'_cv{i}_weight')
            crv_node.curve.set_value(crv)
            crv_node.pre_cycle.set_value(kl.Cycle.constant)
            crv_node.post_cycle.set_value(kl.Cycle.constant)

            crv_node.driver.connect(plug_driver)
            remaps.append(crv_node)

    # output weights
    weight_sum = kl.Add(node, '_weight_sum')
    if len(remaps) > 2:
        weight_sum.add_inputs(len(remaps) - 2)

    for i, remap in enumerate(remaps):
        weight_sum.get_plug(f'input{i + 1}').connect(remap.result)

        _div = kl.Div(weight_sum, '_div')
        _div.input1.connect(remap.result)
        _div.input2.connect(weight_sum.output)

        _attr = 'w{}'.format(i)
        _plug = add_plug(node, _attr, float)
        _plug.connect(_div.output)


@singleton
class ExpressionParser(_ExpressionParser):

    def equal(self, src, dst):

        # check args
        do_scalar = self.is_scalar(src) and self.is_scalar(dst)
        do_vector = False
        do_matrix = False
        do_quat = False
        if not do_scalar:
            do_vector = self.is_vector(src) and self.is_vector(dst)
            if not do_vector:
                do_matrix = self.is_matrix(src) and self.is_matrix(dst)
                if not do_matrix:
                    do_quat = self.is_quat(src) and self.is_quat(dst)

        if not any((do_scalar, do_vector, do_matrix, do_quat)):
            raise TypeError('connect equal: incompatible inputs')

        if not kl.is_plug(dst):
            raise TypeError('connect equal: invalid destination input')

        # connect matrix
        if do_matrix:
            dst_node = dst.get_node()

            if not kl.is_plug(src):
                src = self.matrix(*src)

            if isinstance(dst_node, kl.SceneGraphNode) and dst.get_name() == 'world_transform':
                dst = dst_node.transform
                if kl.is_plug(src):
                    _inv = kl.InverseM44f(dst_node, '_imx')
                    _inv.input.connect(dst_node.parent_world_transform)

                    _mmx = kl.MultM44f(dst_node, '_mmx')
                    _mmx.input[0].connect(src)
                    _mmx.input[1].connect(_inv.output)
                    dst.connect(_mmx.output)
                else:
                    pm = dst_node.parent_world_transform.get_value()
                    pim = pm.inverse()
                    dst.set_value(src * pim)

            else:
                if kl.is_plug(src):
                    dst.connect(src)
                else:
                    dst.set_value(src)
            return

        # connect
        if kl.is_plug(src):
            if do_scalar:
                safe_connect(src, dst)
            else:
                dst.connect(src)
        else:
            # scalar
            if do_scalar:
                dst.set_value(src)

            # vector
            elif do_vector:
                if isinstance(src, V3f):
                    dst.set_value(src)

                # TODO?: passer par le merge transform pour les connexions srt
                for vc, dim in zip(src, 'xyz'):
                    vector = dst.get_input()
                    if kl.is_plug(vector):
                        vector = vector.get_node()
                    else:
                        vector = kl.FloatToV3f(dst.node(), dst.get_name())
                        dst.connect(vector.vector)

                    _dst = vector.get_plug(dim)
                    if kl.is_plug(vc):
                        _dst.connect(vc)
                    else:
                        _dst.set_value(vc)

            # quaternion
            elif do_quat:
                if isinstance(src, Quatf):
                    dst.set_value(src)

                else:
                    node = kl.FloatToQuatf(dst.get_node(), dst.get_name())
                    dst.connect(node.quat)

                    for vc, dim in zip(src, 'xyzw'):
                        _dst = node.get_plug(dim)
                        if kl.is_plug(vc):
                            _dst.connect(vc)
                        else:
                            _dst.set_value(vc)

            # invalid
            else:
                raise TypeError('invalid destination plug type')

    def add(self, v1, v2):
        # scalar + scalar
        if self.is_scalar(v1) and self.is_scalar(v2):
            return connect_add(v1, v2, parent=self.container)

        # vector + vector
        if self.is_vector(v1) and self.is_vector(v2):
            node = kl.AddV3f(self.container, '_add')
            self.connect_vector(v1, node.input1)
            self.connect_vector(v2, node.input2)
            return node.output

        # quat + quat
        if self.is_quat(v1) and self.is_quat(v2):
            # TODO: add quat
            pass

        # matrix + matrix
        if self.is_matrix(v1) and self.is_matrix(v2):
            if not kl.is_plug(v1) and not isinstance(v1, M44f):
                v1 = self.matrix(*v1)
            if not kl.is_plug(v2) and not isinstance(v2, M44f):
                v2 = self.matrix(*v2)

            node = kl.AddM44f(self.container, '_add_xfo')

            for i, v in zip((1, 2), (v1, v2)):
                _plug = node.get_plug('input{}'.format(i))
                if kl.is_plug(v):
                    _plug.connect(v)
                else:
                    _plug.set_value(v)

            return node.output

        # invalid
        log.warning('input1: {}, {}'.format(type(v1), v1))
        log.warning('input2: {}, {}'.format(type(v2), v2))
        raise TypeError('add: invalid inputs')

    def subtract(self, v1, v2):
        # scalar - scalar
        if self.is_scalar(v1) and self.is_scalar(v2):
            return connect_sub(v1, v2, parent=self.container)

        # vector - vector
        if self.is_vector(v1) and self.is_vector(v2):
            neg = self.multiply(-1, v2)
            return self.add(v1, neg)

        # invalid
        log.warning('input1: {}, {}'.format(type(v1), v1))
        log.warning('input2: {}, {}'.format(type(v2), v2))
        raise TypeError('substract: invalid inputs')

    def multiply(self, v1, v2):

        # scalar * scalar
        _s1 = self.is_scalar(v1)
        _s2 = self.is_scalar(v2)

        if _s1 and _s2:
            return connect_mult(v1, v2, parent=self.container)

        # vectors
        _v1 = self.is_vector(v1)
        _v2 = self.is_vector(v2)

        # vector * vector (dot)
        if _v1 and _v2:
            return self.dot(v1, v2, check=False)

        # scalar * vector
        if _s2 and _v1:
            v1, v2 = v2, v1
            _s1, _v2 = _s2, _v1

        if _s1 and _v2:
            node = kl.ScaleV3f(self.container, '_scale')

            if kl.is_plug(v1):
                safe_connect(v1, node.scalar_in)
            else:
                node.scalar_in.set_value(v1)

            self.connect_vector(v2, node.vector_in)
            return node.vector_out

        # quat * quat
        if self.is_quat(v1) and self.is_quat(v2):
            # TODO: mult quat
            pass

        # matrix * matrix
        _m1 = self.is_matrix(v1)
        _m2 = self.is_matrix(v2)
        if _m1 and _m2:
            node = kl.MultM44f(self.container, '_mmx')

            for i, v in zip((0, 1), (v1, v2)):
                _plug = node.input[i]
                if kl.is_plug(v):
                    _plug.connect(v)
                elif isinstance(v, M44f):
                    _plug.set_value(v)
                else:
                    v = self.matrix(*v)
                    _plug.set_value(v)

            return node.output

        # scalar * matrix
        if _m1 and _s2:
            v1, v2 = v2, v1
            _s1, _m2 = _m1, _s2

        if _s1 and _m2:
            node = kl.ScalarM44f(self.container, '_scale_xfo')

            if kl.is_plug(v1):
                node.matrix_in.connect(v1)
            else:
                node.scalar_in.set_value(v1)

            if kl.is_plug(v2):
                node.matrix_in.connect(v2)
            elif isinstance(v2, M44f):
                node.matrix_in.set_value(v2)
            else:
                v2 = self.matrix(*v2)
                node.matrix_in.set_value(v2)

            return node.matrix_out

        # matrix * vector
        if _m1 and _v2:
            node = kl.MultDir(self.container, '_mult_dir')

            if kl.is_plug(v1):
                node.matrix_in.connect(v1)
            elif isinstance(v1, M44f):
                node.matrix_in.set_value(v1)
            else:
                v1 = self.matrix(*v1)
                node.matrix_in.set_value(v1)

            if kl.is_plug(v2):
                node.dir_in.connect(v2)
            elif isinstance(v2, V3f):
                node.dir_in.set_value(v2)
            else:
                self.connect_vector(v2, node.dir_in)

            return node.dir_out

        # invalid
        log.warning('input1: {}, {}'.format(type(v1), v1))
        log.warning('input2: {}, {}'.format(type(v2), v2))
        raise TypeError('multiply: invalid inputs')

    def pow(self, v1, v2):

        # scalar ^ scalar
        if self.is_scalar(v1) and self.is_scalar(v2):
            return connect_power(v1, v2, parent=self.container)

        # vector ^ vector
        if self.is_vector(v1) and self.is_vector(v2):
            return self.cross(v1, v2, check=False)

        # matrix^-1
        if v2 == -1 and self.is_matrix(v1):
            return self.inverse(v1)

        # quat^-1
        if v2 == -1 and self.is_quat(v1):
            return self.inverse(v1)

        # invalid
        log.warning('input1: {}, {}'.format(type(v1), v1))
        log.warning('input2: {}, {}'.format(type(v2), v2))
        raise TypeError('power: invalid inputs')

    def inverse(self, v):

        # scalar
        if self.is_scalar(v):
            return self.pow(v, -1)

        # matrix
        if self.is_matrix(v):
            node = kl.InverseM44f(self.container, '_imx')

            if kl.is_plug(v):
                node.input.connect(v)
            elif isinstance(v, M44f):
                node.input.set_value(v)
            else:
                v = self.matrix(*v)
                node.input.set_value(v)

            return node.output

        # quaternion
        if self.is_quat(v):
            # TODO: inverse quat
            pass

        # invalid
        log.warning('input: {}, {}'.format(type(v), v))
        raise TypeError('inverse: invalid input')

    def divide(self, v1, v2):

        # scalar / scalar
        _s1 = self.is_scalar(v1)
        _s2 = self.is_scalar(v2)

        if _s1 and _s2:
            return connect_div(v1, v2, parent=self.container)

        # vector / scalar
        _v1 = self.is_vector(v1)
        _v2 = self.is_vector(v2)

        if _v2 and _s1:
            v1, v2 = v2, v1
            _v1, _s2 = _v2, _s1

        if _v1 and _s2:
            v2 = self.divide(1, v2)
            return self.multiply(v2, v1)

        # 1/matrix
        if v1 == 1 and self.is_matrix(v2):
            return self.inverse(v2)

        # 1/quat
        if v1 == 1 and self.is_quat(v2):
            return self.inverse(v2)

        # invalid
        log.warning('input1: {}, {}'.format(type(v1), v1))
        log.warning('input2: {}, {}'.format(type(v2), v2))
        raise TypeError('divide: invalid inputs')

    def exp(self, v):
        return connect_power(math.e, v, parent=self.container)

    def logical_or(self, a, b):

        # check inputs
        if not self.is_scalar(a) and not self.is_scalar(b):
            log.warning('input1: {}, {}'.format(type(a), a))
            log.warning('input2: {}, {}'.format(type(b), b))
            raise TypeError('or: invalid inputs')

        # logical gate node emulation
        node = kl.Or(self.container, '_or')

        # connect
        if kl.is_plug(a):
            safe_connect(a, node.input[0])
        else:
            node.input1.set_value(a)

        if kl.is_plug(b):
            safe_connect(b, node.input[1])
        else:
            node.input2.set_value(b)

        return node.output

    def logical_and(self, a, b):

        # check inputs
        if not self.is_scalar(a) and not self.is_scalar(b):
            log.warning('input1: {}, {}'.format(type(a), a))
            log.warning('input2: {}, {}'.format(type(b), b))
            raise TypeError('and: invalid inputs')

        # logical gate node emulation
        node = kl.And(self.container, '_and')

        # connect
        if kl.is_plug(a):
            safe_connect(a, node.input[0])
        else:
            node.input[0].set_value(a)

        if kl.is_plug(b):
            safe_connect(b, node.input[1])
        else:
            node.input[1].set_value(b)

        return node.output

    def logical_xor(self, a, b):

        # check inputs
        if not self.is_scalar(a) and not self.is_scalar(b):
            log.warning('input1: {}, {}'.format(type(a), a))
            log.warning('input2: {}, {}'.format(type(b), b))
            raise TypeError('xor: invalid inputs')

        # logical gate node emulation
        node = kl.Xor(self.container, '_xor')

        # connect
        if kl.is_plug(a):
            safe_connect(a, node.input[0])
        else:
            node.input1.set_value(a)

        if kl.is_plug(b):
            safe_connect(b, node.input[1])
        else:
            node.input2.set_value(b)

        return node.output

    def logical_not(self, b):

        # check input
        if not self.is_scalar(b):
            log.warning('input: {}, {}'.format(type(b), b))
            raise TypeError('not: invalid inputs')

        # logical gate node emulation
        node = kl.Not(self.container, '_not')

        # connect
        if kl.is_plug(b):
            safe_connect(b, node.input)
        else:
            node.input.set_value(b)

        return node.output

    def int(self, v):

        # check input
        if not self.is_scalar(v):
            log.warning('input: {}, {}'.format(type(v), v))
            raise TypeError('int: invalid inputs')

        # conversion node
        if kl.is_plug(v):
            vtype = v.get_type()
        else:
            vtype = type(v)

        if vtype is int:
            return v

        # build node
        if vtype is float:
            # TODO: corriger le float to int qui fait un ceil en négatif (alors qu'on voulait du floor)
            # node = kl.FloatToInt(self.container, '_int')
            drive = connect_driven_curve(None, None, {0: 0, 1: 1}, tangent_mode='step', pre='offset', post='offset', parent=self.container)
            plug_in = drive.driver
            plug_out = drive.result
        else:
            # TODO; changer le node de cast quand ça sera possible
            node = kl.Node(self.container, '_int')
            add_plug(node, 'value', int)
            plug_in = node.value
            plug_out = node.value

        # connect
        if kl.is_plug(v):
            safe_connect(v, plug_in)
        else:
            plug_in.set_value(v)

        return plug_out

    def bool(self, v):

        # check input
        if not self.is_scalar(v):
            log.warning('input: {}, {}'.format(type(v), v))
            raise TypeError('bool: invalid inputs')

        # conversion node
        # TODO; changer le node de cast quand ça sera possible
        node = kl.Node(self.container, '_bool')
        add_plug(node, 'value', bool)

        # connect
        if kl.is_plug(v):
            safe_connect(v, node.value)
        else:
            node.value.set_value(v)

        return node.value

    def clamp(self, value, min_value, max_value):

        # check inputs
        if not self.is_scalar(value):
            raise TypeError('clamp: invalid input value')
        if not self.is_scalar(min_value):
            raise TypeError('clamp: invalid minimum input')
        if not self.is_scalar(max_value):
            raise TypeError('clamp: invalid maximum input')

        # connect
        node = kl.ClampFloat(self.container, '_clamp')

        if kl.is_plug(min_value):
            safe_connect(min_value, node.min)
        else:
            node.min.set_value(min_value)

        if kl.is_plug(max_value):
            safe_connect(max_value, node.max)
        else:
            node.max.set_value(max_value)

        if kl.is_plug(value):
            safe_connect(value, node.input)
        else:
            # unlikely for a static value to be clamped, but it should still work
            node.input.set_value(value)

        return node.output

    def condition(self, first_term, operation, second_term, if_true, if_false):

        # check inputs
        if not self.is_scalar(first_term):
            raise TypeError('condition: invalid first term')
        if not self.is_scalar(second_term):
            raise TypeError('condition: invalid second term')

        if operation not in self.conditionals:
            raise TypeError('condition: invalid operator')

        a = if_true
        b = if_false

        do_scalar = self.is_scalar(a) and self.is_scalar(b)
        do_vector = False
        do_matrix = False
        do_quat = False

        if not do_scalar:
            do_vector = self.is_vector(a) and self.is_vector(b)
            if not do_vector:
                do_matrix = self.is_matrix(a) and self.is_matrix(b)
                if not do_matrix:
                    do_quat = self.is_quat(a) and self.is_quat(b)

        if not any((do_scalar, do_vector, do_quat, do_matrix)):
            log.warning('input true: {}, {}'.format(type(a), a))
            log.warning('input false: {}, {}'.format(type(b), b))
            raise TypeError('condition: invalid inputs')

        # connect
        parent = self.container
        op, switch = None, None
        if_output = None

        # switch
        do_condition = True
        if do_scalar:
            if not kl.is_plug(if_true) and if_true in (1, True):
                if not kl.is_plug(if_false) and if_false in (0, False):
                    do_condition = False

            if do_condition:
                switch = kl.Condition(self.container, '_if')
                parent = switch

        else:
            switch = kl.BlendV3f(self.container, '_if')
            parent = switch

        # operator
        if operation == '==' or operation == '!=':
            op = kl.IsEqual(parent, '_is_equal')
            if operation == '!=':
                op_not = kl.Not(op, '_not')
                op_not.input.connect(op.output)
                if_output = op_not.output
            else:
                if_output = op.output

        elif operation == '>' or operation == '<=':
            op = kl.IsGreater(parent, '_is_greater')
            if operation == '<=':
                op_not = kl.Not(op, '_not')
                op_not.input.connect(op.output)
                if_output = op_not.output
            else:
                if_output = op.output

        elif operation == '>=' or operation == '<':
            op = kl.IsGreaterOrEqual(parent, '_is_greater_or_equal')
            if operation == '<':
                op_not = kl.Not(op, '_not')
                op_not.input.connect(op.output)
                if_output = op_not.output
            else:
                if_output = op.output

        if kl.is_plug(first_term):
            safe_connect(first_term, op.input1)
        else:
            op.input1.set_value(first_term)

        if kl.is_plug(second_term):
            safe_connect(second_term, op.input2)
        else:
            op.input2.set_value(second_term)

        # switch scalar
        if do_scalar:

            if switch:
                switch.condition.connect(if_output)

                if kl.is_plug(if_true):
                    safe_connect(if_true, switch.input1)
                else:
                    switch.input1.set_value(if_true)

                if kl.is_plug(if_false):
                    safe_connect(if_false, switch.input2)
                else:
                    switch.input2.set_value(if_false)

                return switch.output

            else:
                return if_output

        # switch vector
        if do_vector:
            safe_connect(if_output, switch.weight)
            self.connect_vector(if_true, switch.input2)
            self.connect_vector(if_false, switch.input1)
            return switch.output

        # switch quat
        if do_quat:
            # TODO: quat
            pass

        # switch matrix
        if do_matrix:
            # TODO: matrix
            pass

    def lerp(self, a, b, t):

        # check
        if not self.is_scalar(t):
            raise TypeError('lerp: invalid weight')

        do_scalar = self.is_scalar(a) and self.is_scalar(b)
        do_vector = False
        do_matrix = False
        do_quat = False

        if not do_scalar:
            do_vector = self.is_vector(a) and self.is_vector(b)
            if not do_vector:
                do_matrix = self.is_matrix(a) and self.is_matrix(b)
                if not do_matrix:
                    do_quat = self.is_quat(a) and self.is_quat(b)

        if not any((do_scalar, do_vector, do_quat, do_matrix)):
            log.warning('input1: {}, {}'.format(type(a), a))
            log.warning('input2: {}, {}'.format(type(b), b))
            raise TypeError('lerp: invalid inputs')

        # connect
        if do_scalar:
            node = kl.Blend(self.container, '_lerp')
        else:
            node = kl.BlendV3f(self.container, '_lerp')

        if kl.is_plug(t):
            safe_connect(t, node.weight)
        else:
            # static value on attributesBlender doesn't make much sense but we don't want to error out
            node.weight.set_value(t)

        # scalar
        if do_scalar:
            if kl.is_plug(a):
                safe_connect(a, node.input1)
            else:
                node.input1.set_value(a)

            if kl.is_plug(b):
                safe_connect(b, node.input2)
            else:
                node.input2.set_value(b)

            return node.output

        # vector
        if do_vector:
            self.connect_vector(a, node.input1)
            self.connect_vector(b, node.input2)
            return node.output

        # quaternion (slerp)
        if do_quat:
            return self.slerp(a, b, t, check=False)

        # matrix
        if do_matrix:
            raise TypeError('lerp: matrix not yet implemented')

    def remap(self, v, old_min, old_max, new_min, new_max):

        # check
        if not self.is_scalar(v):
            raise TypeError('remap: invalid input value')
        if not self.is_scalar(old_min):
            raise TypeError('remap: invalid old_min')
        if not self.is_scalar(old_max):
            raise TypeError('remap: invalid old_max')
        if not self.is_scalar(new_min):
            raise TypeError('remap: invalid new_min')
        if not self.is_scalar(new_max):
            raise TypeError('remap: invalid new_max')

        # connect
        node = kl.RemapFloat(self.container, '_remap')

        if kl.is_plug(v):
            safe_connect(v, node.input)
        else:
            node.input.set_value(v)

        if kl.is_plug(old_min):
            safe_connect(old_min, node.min1)
        else:
            node.min1.set_value(old_min)

        if kl.is_plug(old_max):
            safe_connect(old_max, node.max1)
        else:
            node.max1.set_value(old_max)

        if kl.is_plug(new_min):
            safe_connect(new_min, node.min2)
        else:
            node.min2.set_value(new_min)

        if kl.is_plug(new_max):
            safe_connect(new_max, node.max2)
        else:
            node.max2.set_value(new_max)

        return node.output

    def abs(self, v):
        if not self.is_scalar(v):
            raise TypeError('abs: invalid input')

        if kl.is_plug(v):
            node = kl.Abs(self.container, '_abs')
            safe_connect(v, node.input)
            return node.output
        else:
            return abs(v)

    def cos(self, a):
        if not self.is_scalar(a):
            raise TypeError('cos: invalid input')

        if kl.is_plug(a):
            node = kl.Cos(self.container, '_cos')
            safe_connect(a, node.input)
            return node.output
        else:
            return math.cos(a * math.pi / 180)

    def sin(self, a):
        if not self.is_scalar(a):
            raise TypeError('sin: invalid input')

        if kl.is_plug(a):
            node = kl.Sin(self.container, '_sin')
            safe_connect(a, node.input)
            return node.output
        else:
            return math.sin(a * math.pi / 180)

    def tan(self, a):
        if not self.is_scalar(a):
            raise TypeError('tan: invalid input')

        if kl.is_plug(a):
            node = kl.Tan(self.container, '_tan')
            safe_connect(a, node.input)
            return node.output
        else:
            return math.tan(a * math.pi / 180)

    def acos(self, v):
        if not self.is_scalar(v):
            raise TypeError('acos: invalid input')

        if kl.is_plug(v):
            node = kl.Acos(self.container, '_acos')
            safe_connect(v, node.input)
            return node.output
        else:
            return math.acos(v) * 180 / math.pi

    def asin(self, v):
        if not self.is_scalar(v):
            raise TypeError('asin: invalid input')

        if kl.is_plug(v):
            node = kl.Asin(self.container, '_asin')
            safe_connect(v, node.input)
            return node.output
        else:
            return math.asin(v) * 180 / math.pi

    def atan(self, v):
        if not self.is_scalar(v):
            raise TypeError('atan: invalid input')

        if kl.is_plug(v):
            node = kl.Atan(self.container, '_atan')
            safe_connect(v, node.input)
            return node.output
        else:
            return math.atan(v) * 180 / math.pi

    def noise(self, v):
        if not self.is_scalar(v):
            raise TypeError('noise: invalid input')

        node = kl.Noise(self.container, '_noise')

        if kl.is_plug(v):
            safe_connect(v, node.input)
        else:
            node.input.set_value(v)

        noise = connect_div(node.output, 2)
        noise = connect_add(noise, 0.5)
        return noise

    def dnoise(self, v):
        if not self.is_scalar(v):
            raise TypeError('dnoise: invalid input')

        node = kl.Noise(self.container, '_dnoise')

        if kl.is_plug(v):
            safe_connect(v, node.input)
        else:
            node.input.set_value(v)

        return node.output

    def norm(self, v):

        # vector
        if self.is_vector(v):
            norm = kl.Normalize(self.container, name='_norm')
            self.connect_vector(v, norm.input)
            return norm.output

        # quat
        if self.is_quat(v):
            # TODO: quat norm
            pass

        # invalid
        log.warning('input1: {}, {}'.format(type(v), v))
        raise TypeError('normalize: invalid input')

    def dot(self, v1, v2, check=True):
        # check
        if check:
            if not self.is_vector(v1):
                raise TypeError('dot: invalid input 1')
            if not self.is_vector(v2):
                raise TypeError('dot: invalid input 2')

        # connect
        node = kl.Dot(self.container, '_dot')
        self.connect_vector(v1, node.input1)
        self.connect_vector(v2, node.input2)
        return node.output

    def cross(self, v1, v2, check=True):
        # check
        if check:
            if not self.is_vector(v1):
                raise TypeError('cross: invalid input 1')
            if not self.is_vector(v2):
                raise TypeError('cross: invalid input 2')

        # connect
        node = kl.Cross(self.container, '_cross')
        self.connect_vector(v1, node.input1)
        self.connect_vector(v2, node.input2)
        return node.output

    def len(self, v):

        # check
        if not self.is_vector(v):
            raise TypeError('length: invalid input')

        # connect
        d = kl.Distance(self.container, '_len')
        self.connect_vector(v, d.input2)
        return d.output

    def distance(self, v1, v2):

        # check
        for i, v in enumerate((v1, v2)):
            if not self.is_vector(v) and not self.is_matrix(v):
                raise TypeError('distance: invalid input {}'.format(i))

        # connect
        d = kl.Distance(self.container, '_len')
        for i, v in enumerate((v1, v2)):
            if self.is_matrix_plug(v):
                M44_to_t = kl.TransformToSRTNode(self.container, '_M44ToTranslate#')
                M44_to_t.transform.connect(v)
                v = M44_to_t.translate

            self.connect_vector(v, d.get_plug(f'input{i + 1}'))

        return d.output

    def angle(self, v1, v2):

        # check
        for i, v in enumerate((v1, v2)):
            if not self.is_vector(v):
                raise TypeError('angle: invalid input {}'.format(i))

        # connect
        dot = self.dot(self.norm(v1), self.norm(v2))
        acos = self.acos(dot)
        return connect_mult(acos, 180 / math.pi)

    def slerp(self, a, b, t, shortest=True, check=True):

        # check
        if check:
            if not self.is_scalar(t):
                raise TypeError('slerp: invalid weight')
            if not self.is_quat(a):
                raise TypeError('slerp: invalid input 1')
            if not self.is_quat(b):
                raise TypeError('slerp: invalid input 2')

        # connect
        # TODO: quat slerp

    def vector(self, x, y, z):

        # check
        if not self.is_scalar(x):
            raise TypeError('vector: invalid input x')
        if not self.is_scalar(y):
            raise TypeError('vector: invalid input y')
        if not self.is_scalar(z):
            raise TypeError('vector: invalid input z')

        # connect?
        if any(map(kl.is_plug, (x, y, z))):
            return [x, y, z]
        else:
            return V3f(x, y, z)

    def euler(self, *args):

        # components
        if len(args) == 4:
            x, y, z, ro = args

            if not self.is_scalar(x):
                raise TypeError('euler: invalid input x')
            if not self.is_scalar(y):
                raise TypeError('euler: invalid input y')
            if not self.is_scalar(z):
                raise TypeError('euler: invalid input z')

            # euler
            ro = self.rotate_order(ro)

            vector = [x, y, z]
            if not any(map(kl.is_plug, vector)):
                vector = V3f(*vector)

            return vector, ro

        # quaternion
        elif len(args) == 1 and self.is_quat(args[0]):
            q = args[0]
            node = kl.QuatfToM44f(self.container, '_tmp')

            if isinstance(q, Quatf):
                node.quat.set_value(q)

                xfo = node.transform.get_value()
                euler = xfo.rotation(Euler.XYZ)

                node.remove_from_parent()
                return euler, Euler.XYZ

            # from plug
            # TODO: replace by QuetToEuler node
            node.quat.connect(q)

            srt = kl.TransformToSRTNode(node, '_euler')
            srt.transform.connect(node.transform)

            return srt.rotate, srt.rotate_order

    def rotate_order(self, ro):
        rotate_orders = {
            'XYZ': Euler.XYZ,
            'YZX': Euler.YZX,
            'ZXY': Euler.ZXY,
            'XZY': Euler.XZY,
            'YXZ': Euler.YXZ,
            'ZYX': Euler.ZYX
        }

        if ro in rotate_orders.values():
            return ro
        if kl.is_plug(ro) and ro.get_name().endswith('rotateOrder'):
            return ro

        # convert
        if ro not in self.rotate_orders:
            raise TypeError('invalid rotate order')

        return rotate_orders[ro]

    def quat(self, *args):

        # unpack euler
        if len(args) == 1 and isinstance(args[0], (list, tuple)) and len(args[0]) == 2:
            args = args[0]

        # components
        if len(args) == 4:
            x, y, z, w = args

            if not self.is_scalar(x):
                raise TypeError('quaternion: invalid input x')
            if not self.is_scalar(y):
                raise TypeError('quaternion: invalid input y')
            if not self.is_scalar(z):
                raise TypeError('quaternion: invalid input z')
            if not self.is_scalar(w):
                raise TypeError('quaternion: invalid input w')

            # connect?
            if any(map(kl.is_plug, (x, y, z, w))):
                return [x, y, z, w]
            else:
                return Quatf(x, y, z, w)

        # euler
        elif len(args) == 2 and self.is_euler(args):
            e, ro = args

            if isinstance(e, (list, tuple)) and not any(map(kl.is_plug, e)) and not kl.is_plug(ro):
                return Quatf()

            node = kl.EulerToQuatf(self.container, '_quat')

            if kl.is_plug(e):
                node.rotate.connect(e)
            elif isinstance(e, V3f):
                node.rotate.set_value(e)
            else:
                if any(map(kl.is_plug, e)):
                    rotate = kl.FloatToEuler(node, 'rotate')
                    node.rotate.connect(rotate.euler)
                    node.rotate_order.connect(rotate.rotate_order)
                    for vc, dim in zip(e, 'xyz'):
                        _plug = rotate.get_plug(dim)
                        if kl.is_plug(vc):
                            _plug.connect(vc)
                        else:
                            _plug.set_value(vc)

                    if kl.is_plug(ro):
                        rotate.rotate_order.connect(ro)
                    else:
                        rotate.rotate_order.set_value(ro)

                else:
                    node.rotate.set_value(V3f(*e))
                    if kl.is_plug(ro):
                        node.rotate_order.connect(ro)
                    else:
                        node.rotate_order.set_value(ro)

            return node.quat

        # transform
        elif len(args) == 1 and self.is_matrix(args[0]):
            xfo = args[0]

            # TODO
            # if kl.is_plug(xfo):
            #     srt = kl.TransformToSRTNode
            #     node = kl.EulerToQuatf

    def transform(self, t, r, s):
        # check
        if not self.is_vector(t):
            raise TypeError('transform: invalid translate')
        if not self.is_vector(s):
            raise TypeError('transform: invalid scale')

        _rv = self.is_vector(r)
        _re = self.is_euler(r)
        _rq = self.is_quat(r)
        if not any((_rv, _re, _rq)):
            raise TypeError('transform: invalid rotate')

        # result
        if _rv:
            x, y, z = r
            r = self.euler(x, y, z, 'XYZ')
            _rv, _re = False, True

        has_plug = False
        if kl.is_plug(t) or (isinstance(t, (list, tuple)) and any(map(self.is_scalar_plug, t))):
            has_plug = True
        elif kl.is_plug(r) or (isinstance(r, (list, tuple)) and any(map(self.is_scalar_plug, r))):
            has_plug = True
        elif _re and isinstance(r, (list, tuple)):
            if kl.is_plug(r[0]):
                has_plug = True
            elif isinstance(r[0], (list, tuple)) and any(map(self.is_scalar_plug, r[0])):
                has_plug = True
        elif kl.is_plug(s) or (isinstance(s, (list, tuple)) and any(map(self.is_scalar_plug, s))):
            has_plug = True

        if not has_plug:
            if _rq:
                r = self.euler(r)
            if not isinstance(t, V3f):
                t = V3f(*t)
            if not isinstance(s, V3f):
                s = V3f(*s)
            return M44f(t, r[0], s, r[1])

        else:
            node = kl.SRTToTransformNode(self.container, '_srt')

            # translate
            if isinstance(t, (list, tuple)) and not any(map(kl.is_plug, t)):
                t = V3f(*t)

            if kl.is_plug(t):
                node.translate.connect(t)
            elif isinstance(t, V3f):
                node.translate.set_value(t)
            else:
                _node = kl.FloatToV3f(node, 'translate')
                node.translate.connect(_node.vector)
                for v, dim in zip(t, 'xyz'):
                    _plug = _node.get_plug(dim)
                    if kl.is_plug(v):
                        _plug.connect(v)
                    else:
                        _plug.set_value(v)

            # rotation
            if _rq:
                r = self.euler(r)
            r, ro = r

            if kl.is_plug(ro):
                node.rotate_order.connect(ro)
            else:
                node.rotate_order.set_value(ro)

            if isinstance(r, (list, tuple)) and not any(map(kl.is_plug, r)):
                r = V3f(*r)

            if kl.is_plug(r):
                node.rotate.connect(r)
            elif isinstance(r, V3f):
                node.rotate.set_value(r)
            else:
                _node = kl.FloatToEuler(node, 'rotate')
                node.rotate.connect(_node.vector)
                node.rotate_order.connect(_node.rotate_order)
                for v, dim in zip(r, 'xyz'):
                    _plug = _node.get_plug(dim)
                    if kl.is_plug(v):
                        _plug.connect(v)
                    else:
                        _plug.set_value(v)

                if kl.is_plug(ro):
                    node.rotate_order.connect(ro)
                else:
                    node.rotate_order.set_value(ro)

            # scale
            if isinstance(s, (list, tuple)) and not any(map(kl.is_plug, s)):
                s = V3f(*s)

            if kl.is_plug(s):
                node.translate.connect(s)
            elif isinstance(s, V3f):
                node.translate.set_value(s)
            else:
                _node = kl.FloatToV3f(node, 'scale')
                node.scale.connect(_node.vector)
                for v, dim in zip(s, 'xyz'):
                    _plug = _node.get_plug(dim)
                    if kl.is_plug(v):
                        _plug.connect(v)
                    else:
                        _plug.set_value(v)

            return node.transform

    def matrix(self, *args):
        # check
        if not len(args) == 16 and not len(args) == 4 and map(lambda x: len(x) in {3, 4}, args):
            raise ValueError('matrix: invalid arguments')

        # connect?
        values = list(args)

        if len(values) == 4:
            for i in range(4):
                if kl.is_plug(values[i]):
                    continue
                values[i] = list(values[i])
                if len(values[i]) == 3:
                    values[i].append((0, 0, 0, 1)[i])

        else:
            values = [values[:4], values[4:8], values[8:12], values[12:]]

        has_plug = False
        for line in values:
            if kl.is_plug(line):
                has_plug = True
                break
            for v in line:
                if kl.is_plug(v):
                    has_plug = True
                    break
            if has_plug:
                break

        if has_plug:
            node = kl.IJKToTransform(self.container, '_ijk')

            for line, dim in zip(values, ('i', 'j', 'k', 'translate')):
                if kl.is_plug(line):
                    node.get_plug(dim).connect(line)
                    continue

                line = line[:3]
                if any(map(kl.is_plug, line)):
                    line_node = kl.FloatToV3f(node, dim)
                    node.get_plug(dim).connect(line_node.vector)

                    for v, j in zip(line, 'xyz'):
                        if kl.is_plug(v):
                            line_node.get_plug(j).connect(v)
                        else:
                            line_node.get_plug(j).set_value(v)

            return node.transform
        else:
            values = values[0] + values[1] + values[2] + values[3]
            return M44f(values)

    def get_component(self, v, i):
        i = i.lower()

        # vector
        if self.is_vector(v):
            if i not in 'xyz':
                raise IndexError('invalid component: it must be x, y or z')

            if kl.is_plug(v):
                vector = None
                for o in v.get_outputs():
                    if o and isinstance(o.get_node(), kl.V3fToFloat):
                        vector = o.get_node()
                        break

                if not vector:
                    vector = kl.V3fToFloat(v.get_node(), v.get_name() + '_output')
                    vector.vector.connect(v)

                return vector.get_plug(i)

            else:
                if i == 'x':
                    return v[0]
                elif i == 'y':
                    return v[1]
                elif i == 'z':
                    return v[2]

        # quaternion
        if self.is_quat(v):
            if i not in 'xyzwijkr':
                raise ValueError('invalid component: it must be x/i, y/j, z/k or w/r')

            if isinstance(v, (list, tuple)):
                if i == 'x' or i == 'i':
                    return v[0]
                elif i == 'y' or i == 'j':
                    return v[1]
                elif i == 'z' or i == 'k':
                    return v[2]
                elif i == 'w' or i == 'r':
                    return v[3]

            node = None
            if isinstance(v, Quatf):
                node = kl.QuatfToFloat(self.container, '_quat')
                node.quat.set_value(v)
            elif kl.is_plug(v):
                node = kl.QuatfToFloat(v.get_node(), '_quat')
                node.quat.connect(v)

            if node:
                if i == 'x' or i == 'i':
                    return node.i
                elif i == 'y' or i == 'j':
                    return node.j
                elif i == 'z' or i == 'k':
                    return node.k
                elif i == 'w' or i == 'r':
                    return node.r

        # transform
        # TODO

        # euler
        # TODO

        # invalid
        log.warning('input: {}, {}'.format(type(v), v))
        raise TypeError('component: invalid input')

    def is_scalar(self, v):
        if isinstance(v, (int, float, bool)):
            return True
        if self.is_scalar_plug(v):
            return True
        return False

    def is_scalar_plug(self, plug):
        if not kl.is_plug(plug):
            return False

        cls = plug.get_type_name()
        if cls in {'bool', 'float', 'int'}:
            return True

    def is_vector(self, v):
        if isinstance(v, (tuple, list)) and len(v) == 3:
            return all(map(self.is_scalar, v))
        if isinstance(v, V3f):
            return True
        if self.is_vector_plug(v):
            return True
        return False

    def is_vector_plug(self, plug):
        if not kl.is_plug(plug):
            return False

        cls = plug.get_type_name()
        cls = cls.split('.')[-1]
        if cls == 'V3f':
            return True

    def is_euler(self, v):
        if isinstance(v, tuple) and len(v) == 2:
            if isinstance(v[0], V3f) or (isinstance(v[0], (tuple, list)) and len(v[0]) == 3 and all(map(self.is_scalar, v[0]))):
                if v[1] in {Euler.XYZ, Euler.XZY, Euler.YXZ, Euler.YZX, Euler.ZXY, Euler.ZYX} or (kl.is_plug(v[1]) and v[1].get_name().endswith('order')):
                    return True
        return False

    def is_quat(self, v):
        if isinstance(v, (tuple, list)) and len(v) == 4:
            return all(map(self.is_scalar, v))
        if isinstance(v, Quatf):
            return True
        if self.is_quat_plug(v):
            return True
        return False

    def is_quat_plug(self, plug):
        if not kl.is_plug(plug):
            return False

        cls = plug.get_type_name()
        cls = cls.split('.')[-1]
        if cls == 'Quatf':
            return True

    def is_matrix(self, v):
        if isinstance(v, M44f):
            return True
        if self.is_matrix_plug(v):
            return True

        if isinstance(v, (tuple, list)) and len(v) == 16:
            return all(map(self.is_scalar, v))
        if isinstance(v, (tuple, list)) and len(v) == 4:
            for x in v:
                if isinstance(x, (tuple, list)) and len(x) in {3, 4}:
                    if not all(map(self.is_scalar, x)):
                        return False
                else:
                    return False
            return True

        return False

    def is_matrix_plug(self, plug):
        if not kl.is_plug(plug):
            return False

        cls = plug.get_type_name()
        cls = cls.split('.')[-1]
        if cls == 'M44f':
            return True

    def connect_vector(self, src, dst):
        if kl.is_plug(src):
            dst.connect(src)
        else:
            if any(map(kl.is_plug, src)):
                vector = kl.FloatToV3f(dst.get_node(), dst.get_name())
                dst.connect(vector.vector)
                for i, v in zip('xyz', src):
                    if kl.is_plug(v):
                        safe_connect(v, vector.get_plug(i))
                    else:
                        vector.get_plug(i).set_value(v)
            else:
                if not isinstance(src, V3f):
                    src = V3f(*src)
                dst.set_value(src)

    def switch(self, *args):

        if len(args) < 3:
            raise TypeError('switch: invalid list size')

        s = args[0]
        if not self.is_scalar(s):
            raise TypeError('switch: invalid selector')

        inputs = args[1:]
        if not all([self.is_scalar(v) for v in inputs]):
            raise TypeError('switch: invalid inputs')

        # build choice node
        switch = None
        n = len(inputs)
        types = set([type(v.get_value() if kl.is_plug(v) else v) for v in inputs])
        if float in types:
            switch = kl.VectorFloatToFloat(n, self.container, '_switch')
        elif int in types:
            switch = kl.VectorIntToInt(n, self.container, '_switch')
        elif bool in types:
            switch = kl.VectorBoolToBool(n, self.container, '_switch')

        # connect
        if kl.is_plug(s):
            safe_connect(s, switch.index)
        else:
            switch.index.set_value(s)

        for i, v in enumerate(inputs):
            if kl.is_plug(v):
                safe_connect(v, switch.input[i])
            else:
                switch.input[i].set_value(v)

        return switch.output

    def value(self, v):
        if kl.is_plug(v):
            return v.get_value()
        else:
            return v


def connect_expr(expr, **kw):
    # update args
    if 'parent' in kw:
        kw['container'] = kw.pop('parent')
    if 'container' not in kw:
        for k, v in kw.items():
            if kl.is_plug(v):
                kw['container'] = v.get_node()
                break
    if 'container' not in kw:
        raise Exception('no parent found for expression')

    # connect
    return ExpressionParser().eval(expr, **kw)
