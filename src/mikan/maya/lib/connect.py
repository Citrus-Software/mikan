# coding: utf-8

import math
from six import iteritems

import maya.cmds as mc
import maya.api.OpenMaya as om
from mikan.maya import cmdx as mx

from mikan.core.utils.typeutils import singleton
from mikan.core.expression import ExpressionParser as _ExpressionParser
from mikan.core.logger import create_logger

__all__ = [
    'connect_add', 'connect_mult', 'connect_div', 'connect_sub', 'connect_reverse', 'connect_power',
    'connect_matrix', 'connect_blend_weighted', 'connect_driven_curve', 'find_anim_curve',
    'get_linear_anim_curves', 'cleanup_linear_anim_curves', 'cleanup_mult_matrix',
    'connect_remap', 'blend_smooth_remap', 'blend_smooth_weights',
    'connect_expr'
]

log = create_logger()


def connect_operation(mode, *args, **kw):
    if len(args) < 2 or len(args) > 3:
        raise RuntimeError('wrong number of arguments')

    name = '_{}#'.format(mode)
    if 'n' in kw:
        name = str(kw['n'])

    if mode == 'add':
        with mx.DGModifier() as md:
            op = md.create_node(mx.tAddDoubleLinear, name='_add#')
        input1 = op['i1']
        input2 = op['i2']
        output = op['o']
    elif mode == 'mult':
        with mx.DGModifier() as md:
            op = md.create_node(mx.tMultDoubleLinear, name='_mult#')
        input1 = op['i1']
        input2 = op['i2']
        output = op['o']
    elif mode == 'div':
        with mx.DGModifier() as md:
            op = md.create_node(mx.tMultiplyDivide, name='_div#')
        op['op'] = 2
        input1 = op['input1X']
        input2 = op['input2X']
        output = op['outputX']
    elif mode == 'power':
        with mx.DGModifier() as md:
            op = md.create_node(mx.tMultiplyDivide, name='_pow#')
        op['op'] = 3
        input1 = op['input1X']
        input2 = op['input2X']
        output = op['outputX']
    else:
        raise RuntimeError('wrong operation')

    i0 = args[0]
    if isinstance(i0, (int, float)):
        input1.write(float(i0))
    else:
        if not isinstance(i0, mx.Plug):
            i0 = mx.encode(str(i0))
        with mx.DGModifier() as md:
            md.connect(i0, input1)

    i1 = args[1]
    if isinstance(i1, (int, float)):
        input2.write(float(i1))
    else:
        if not isinstance(i1, mx.Plug):
            i1 = mx.encode(str(i1))
        with mx.DGModifier() as md:
            md.connect(i1, input2)

    if len(args) == 3:
        o = args[2]
        if not isinstance(o, mx.Plug):
            o = mx.encode(str(o))

        with mx.DGModifier() as md:
            md.connect(output, o)

    op.rename(name)
    return output


def connect_add(*args, **kw):
    return connect_operation('add', *args, **kw)


def connect_mult(*args, **kw):
    return connect_operation('mult', *args, **kw)


def connect_div(*args, **kw):
    return connect_operation('div', *args, **kw)


def connect_power(*args, **kw):
    return connect_operation('power', *args, **kw)


def connect_reverse(*args):
    neg = connect_mult(args[0], -1, n='_neg#')
    if len(args) > 1:
        add = connect_add(neg, 1, args[1], n='_rev#')
    else:
        add = connect_add(neg, 1, n='_rev#')
    return add


def connect_sub(*args):
    args = list(args)
    args[1] = connect_mult(args[1], -1, n='_neg#')
    add = connect_add(*args, n='_sub#')
    return add


def connect_blend_weighted(attr_out, attr_in, weight=None, **kw):
    if not isinstance(attr_out, (int, float)) and not isinstance(attr_out, mx.Plug):
        attr_out = mx.encode(str(attr_out))

    if not isinstance(attr_in, mx.Plug):
        attr_in = mx.encode(str(attr_in))

    # check attr_in input
    bw = None
    cnx = attr_in.input(plug=True)
    if isinstance(cnx, mx.Plug):
        if cnx.node().is_a(mx.tUnitConversion):
            cnx = cnx.node()['input'].input(plug=True)
        if cnx.node().is_a(mx.tBlendWeighted):
            bw = cnx.node()

    if not bw:
        # blendWeighted not found. build a new one
        with mx.DGModifier() as md:
            bw = md.create_node(mx.tBlendWeighted, name='_bw#')
        with mx.DGModifier() as md:
            if isinstance(cnx, mx.Plug):
                md.connect(cnx, bw['i'][0])
            md.connect(bw['o'], attr_in)
    n = bw['i'].count()
    bw.rename('_blend#')

    connect = True
    if kw.get('exclusive'):
        for i in bw['i'].array_indices:
            cnx = bw['i'][i].input(plug=True)
            if isinstance(cnx, mx.Plug):
                if cnx.node().is_a(mx.tUnitConversion):
                    cnx = cnx.node()['input'].input(plug=True)
                if cnx == attr_out:
                    connect = False
                    break

    if connect:
        if isinstance(attr_out, mx.Plug):
            with mx.DGModifier() as md:
                md.connect(attr_out, bw['i'][n])
        else:
            bw['i'][n] = attr_out

        if weight is not None:
            try:
                bw['w'][n] = float(weight)
            except:
                pass

    if kw.get('plug'):
        return bw['i'][n]

    return bw


def connect_matrix(matrix, node, t=True, r=True, s=True, sh=True, xyz=False, pim=False, jo=False):
    if not isinstance(matrix, mx.Plug):
        matrix = mx.encode(str(matrix))
    if not isinstance(node, mx.Node):
        node = mx.encode(str(node))
    with mx.DGModifier() as md:
        dmx = md.create_node(mx.tDecomposeMatrix, name='_dmx#')

    if t and not node['t'].locked:
        dmx['outputTranslate'] >> node['t']

    if r:
        if xyz:
            if node.is_a(mx.tJoint) and jo:
                if not node['jox'].locked and not node['joy'].locked and not node['joz'].locked:
                    dmx['outputRotateX'] >> node['jox']
                    dmx['outputRotateY'] >> node['joy']
                    dmx['outputRotateZ'] >> node['joz']
                    node['r'] = (0, 0, 0)
            else:
                if not node['rx'].locked and not node['ry'].locked and not node['rz'].locked:
                    dmx['outputRotateX'] >> node['rx']
                    dmx['outputRotateY'] >> node['ry']
                    dmx['outputRotateZ'] >> node['rz']
                    if node.is_a(mx.tJoint):
                        node['jo'] = (0, 0, 0)
                    node['ro'] = 0
        else:
            if node.is_a(mx.tJoint) and jo:
                if not node['jo'].locked:
                    dmx['outputRotate'] >> node['jo']
                    node['r'] = (0, 0, 0)
            else:
                if not node['r'].locked:
                    dmx['outputRotate'] >> node['r']
                    if node.is_a(mx.tJoint):
                        node['jo'] = (0, 0, 0)
                    node['ro'] = 0

    if s:
        if xyz:
            if not node['sx'].locked and not node['sy'].locked and not node['sz'].locked:
                dmx['outputScaleX'] >> node['sx']
                dmx['outputScaleY'] >> node['sy']
                dmx['outputScaleZ'] >> node['sz']
        else:
            if not node['s'].locked:
                dmx['outputScale'] >> node['s']

    if sh and not node['sh'].locked:
        dmx['outputShear'] >> node['sh']

    if pim:
        with mx.DGModifier() as md:
            mmx = md.create_node(mx.tMultMatrix, name='_mmx#')
        matrix >> mmx['i'][0]
        node['pim'][0] >> mmx['i'][1]
        mmx['o'] >> dmx['imat']
    else:
        matrix >> dmx['imat']

    if node.is_a(mx.tTransform):
        node['rp'] = (0, 0, 0)
        node['sp'] = (0, 0, 0)
        node['rpt'] = (0, 0, 0)
        node['spt'] = (0, 0, 0)

    return dmx


def connect_remap(plug, min_old, max_old, min, max, plug_out=None):
    if not isinstance(plug, mx.Plug):
        plug = mx.encode(str(plug))
    if plug_out is not None and not isinstance(plug_out, mx.Plug):
        plug_out = mx.encode(str(plug_out))

    with mx.DGModifier() as md:
        sr = md.create_node(mx.tSetRange, name='_remap#')
    with mx.DGModifier() as md:
        md.connect(plug, sr['valueX'])
    sr['oldMinX'] = min_old
    sr['oldMaxX'] = max_old
    sr['minX'] = min
    sr['maxX'] = max
    if plug_out is not None:
        with mx.DGModifier() as md:
            md.connect(sr['outValueX'], plug_out)


def connect_driven_curve(out_node, in_node=None, keys=None, key_style=None, pre=None, post=None):
    """set driven key wrapper"""

    if not isinstance(out_node, mx.Plug):
        out_node = mx.encode(str(out_node))
        if not isinstance(out_node, mx.Plug):
            raise ValueError('given plug is invalid ({})'.format(out_node))
            # return?

    no_output = False
    if in_node is None:
        with mx.DGModifier() as md:
            in_node = md.create_node(mx.tNetwork, name='_tmp#')
        in_node.add_attr(mx.Double('input', keyable=True))
        in_node = in_node['input']
        no_output = True
    else:
        if not isinstance(in_node, mx.Plug):
            in_node = mx.encode(str(in_node))
            if not isinstance(in_node, mx.Plug):
                raise ValueError('given plug is invalid ({})'.format(in_node))
                # return?
    # args
    infinity = {
        'constant': 0,
        'linear': 1,
        'cycle': 2,
        'repeat': 2,
        'offset': 3,
        'continuous': 3,
        'oscillate': 4
    }

    if keys is None:
        keys = {0: 0, 1: 1}
    if key_style is None:
        key_style = 'spline'
    if pre is None:
        pre = 'linear'
    if post is None:
        post = 'linear'

    in_node_input = in_node.input(plug=True)
    if isinstance(in_node_input, mx.Plug):
        if in_node_input.node().is_a(mx.tUnitConversion):
            in_node_input = in_node_input.node()['input'].input(plug=True)

        if not in_node_input.node().is_a((mx.tBlendWeighted, mx.kAnimCurve)):
            connect_blend_weighted(in_node_input, in_node)

    do_scale = 0
    ln = in_node.name()
    if ln.startswith('scale') and len(ln) == 6:
        do_scale = 1
        if not in_node.input():
            with mx.DGModifier() as md:
                _bw = md.createNode('animCurveUU', name='_driven_scale#')
            mc.setKeyframe(str(_bw), f=0, v=1)
            with mx.DGModifier() as md:
                md.connect(_bw['output'], in_node)

    cv = None
    for key, data in iteritems(keys):
        key = float(key)
        itt = key_style
        ott = key_style
        tan_data = {}

        if isinstance(data, dict):
            if 'v' not in data:
                continue
            v = data['v']
            if 'tan' in data:
                itt = data['tan']
                ott = data['tan']
            if 'itan' in data:
                itt = data['itan']
            if 'otan' in data:
                ott = data['otan']
            if itt == 'step' and ott == 'step':
                itt = 'auto'

            if 'ix' in data:
                tan_data['ix'] = data['ix'] * -3
                tan_data['iy'] = data['iy'] * -3
            if 'ox' in data:
                tan_data['ox'] = data['ox'] * 3
                tan_data['oy'] = data['oy'] * 3

        elif type(data) in (float, int):
            v = data
        elif type(data) is bool:
            v = float(data)
        else:
            continue
        v -= do_scale

        mc.setDrivenKeyframe(in_node.path(), cd=out_node.path(), dv=key, v=v, itt=itt, ott=ott)

        # find driven curve
        if not cv:
            cv = find_anim_curve(in_node, out_node)

        # edit tan
        if itt != ott:
            mc.keyTangent(str(cv), edit=True, lock=False)

        if tan_data:
            if cv and cv.is_a((mx.tAnimCurveUA, mx.tAnimCurveTA)):
                deg_to_rad = lambda d: mx.Degrees(d).asRadians()
                tan_data['iy'] = deg_to_rad(tan_data['iy'])
                tan_data['oy'] = deg_to_rad(tan_data['oy'])

            mc.keyTangent(str(cv), edit=True, weightedTangents=True, weightLock=False, lock=False)
            mc.keyTangent(str(cv), edit=True, f=(key,), **tan_data)

    if no_output:
        cv['output'] // in_node
        mx.delete(in_node.node())

    if cv:
        cv['preInfinity'] = infinity[pre]
        cv['postInfinity'] = infinity[post]
        return cv
    else:
        log.error('animCurve not found!')
        return None


def find_anim_curve(plug_in, plug_out=None, plugs=False):
    if not isinstance(plug_in, (mx.Node, mx.Plug)):
        plug_in = mx.encode(str(plug_in))

    oc = []
    if plug_out is not None:
        for node in plug_out.outputs(type=(mx.kAnimCurve, mx.tUnitConversion)):
            if node.is_a(mx.tUnitConversion):
                node = node['output'].output()
            if not node.is_a(mx.kAnimCurve):
                continue
            oc.append(node)

    # get first connections
    data = {}

    if isinstance(plug_in, mx.Node):
        for plug, plug_in in plug_in.inputs(plugs=True, connections=True):
            data[plug_in] = [plug.node()]

    elif isinstance(plug_in, mx.Plug):
        _node = plug_in.input()
        if _node is not None:
            data[plug_in] = [_node]

    # traverse graph loop
    for plug_in, nodes in iteritems(data):
        curves = []

        processed = set()
        while nodes:
            node = nodes[0]
            del nodes[:1]
            processed.add(node)

            if node.is_a(mx.kAnimCurve):
                curves.append(node)
                continue

            if node.is_a((mx.kTransform, mx.kShape)):
                continue
            if node.is_a('shapeEditorManager'):
                continue

            if node.is_a((mx.tMute, mx.tUnitConversion)):
                node = node['input'].input()
                if node not in processed:
                    nodes.append(node)
                continue

            for _node in node.inputs():
                if _node not in processed:
                    nodes.append(_node)

        data[plug_in] = curves

    if plug_out is not None:
        for c in oc:
            for plug_in, curves in iteritems(data):
                if c in curves:
                    return c

    else:
        if plugs:
            return data

        curves = []
        for plug_in, _curves in iteritems(data):
            curves += _curves
        return curves


def get_linear_anim_curves(filter=None, check_infinity=True):
    linear_anim_curves = []

    for anm in mx.ls(type='animCurve'):
        if filter and not anm.is_a(filter):
            continue

        if check_infinity:
            if anm['pre'].read() != 1:
                continue
            if anm['pst'].read() != 1:
                continue

        # get number of keyframes on curve
        keys = anm['ktv'].array_indices
        n_keys = len(keys)
        if n_keys <= 1:
            continue

        values = mc.keyframe(str(anm), q=1, tc=1, fc=1, vc=1)

        # compute linear equation (y=ax+b) a and b
        x0 = values[0]
        y0 = values[1]
        x1 = values[2]
        y1 = values[3]

        if y1 == y0:
            a = 0
        else:
            a = (y1 - y0) / (x1 - x0)
        b = y0 - a * x0

        # check linearity along other steps
        x0 = x1
        y0 = y1
        linear = True
        for k in range(4, len(values), 2):
            x1 = values[k]
            y1 = values[k + 1]

            if y1 == y0:
                ap = 0
            else:
                ap = (y1 - y0) / (x1 - x0)
            bp = y0 - ap * x0
            if ap != a or bp != b:
                linear = False
                break
            # next step
            x0 = x1
            y0 = y1

        if not linear:
            continue

        # check tangents
        tangents = mc.keyTangent(str(anm), query=True, inTangentType=True, outTangentType=True)
        if set(tangents).difference({'spline', 'clamped'}):
            continue

        # store the linear animCurve with its (a, b) parameters
        linear_anim_curves.append((anm, a, b))

    return linear_anim_curves


def cleanup_linear_anim_curves():
    n = 0

    for curve, a, b in get_linear_anim_curves():
        # only use linear equation with b=0
        if b != 0:
            continue

        plug_out = curve['input'].input(plug=True)
        if plug_out is not None:
            plug_node = plug_out.node()
            if plug_node.is_a(mx.tUnitConversion):
                plug_out = plug_node['input'].input(plug=True)

        plug_ins = []
        for plug_in in curve['output'].outputs(plugs=True):
            plug_node = plug_in.node()
            if plug_node.is_a(mx.tUnitConversion):
                for plug_in in plug_node['output'].outputs(plugs=True):
                    plug_ins.append(plug_in)
            else:
                plug_ins.append(plug_in)

        if plug_out is None or not plug_ins:
            continue

        # check for locked attributes
        locked = False
        for plug_in in plug_ins:
            if plug_in.locked:
                locked = True
                break
        if locked:
            continue
        if plug_out.locked:
            continue

        # replace node
        mult = mx.create_node(mx.tMultDoubleLinear, name='_linear#')
        mult['input2'] = a

        # disconnect animCurve
        for plug_in in plug_ins:
            mult['output'] >> plug_in
        plug_out >> mult['input1']

        # remove the resulting unused animCurve
        curve.add_attr(mx.Message('kill_me'))
        n += 1

    log.debug('optimized {} linear anim curves'.format(n))


def cleanup_mult_matrix(nodes=None):
    if nodes is None:
        nodes = mx.ls(et='multMatrix')
    remove = []

    for node in nodes:
        outputs = list(node['o'].outputs())
        if len(outputs) != 1:
            continue
        _node = outputs[0]
        if _node not in nodes:
            continue

        # get inputs
        inputs = []
        for _mmx in (node, _node):
            for i in _mmx['i'].array_indices:
                _i = _mmx['i'][i].input(plug=True)
                if isinstance(_i, mx.Plug):
                    if _i.node() != node:
                        inputs.append(_i)
                    with mx.DGModifier() as md:
                        md.disconnect(_i, _mmx['i'][i])
                else:
                    _i = _mmx['i'][i].as_matrix()
                    inputs.append(_i)
                _mmx['i'][i] = mx.Matrix4()

        # merge
        for i, v in enumerate(inputs):
            if isinstance(v, mx.Plug):
                with mx.DGModifier() as md:
                    md.connect(v, _node['i'][i])
            else:
                _node['i'][i] = v

        node.add_attr(mx.Message('kill_me'))
        remove.append(node)

    log.debug('optimized {} mult matrix nodes'.format(len(remove)))
    return remove


def blend_smooth_remap(attrs_in, attrs_out, connect=True):
    remaps = []
    bws = []

    for i, inAttr in enumerate(attrs_in):
        with mx.DGModifier() as md:
            uu = md.create_node(mx.tAnimCurveUU, name='_uu#')
        remaps.append(uu)

        n = len(attrs_in)
        f = float(i) / (n - 1)
        fn = 1. / (n - 1)
        mc.setKeyframe(str(uu), f=f - fn, v=0)
        mc.setKeyframe(str(uu), f=f, v=1)
        mc.setKeyframe(str(uu), f=f + fn, v=0)

        mc.keyTangent(str(uu), itt='flat', ott='flat')

    for o, attr_out in enumerate(attrs_out):
        with mx.DGModifier() as md:
            bw = md.create_node(mx.tBlendWeighted, name='_bw#')
        bws.append(bw)

        n = len(attrs_out)

        s = 0
        for i, attr_in in enumerate(attrs_in):
            if attr_in is not None:
                with mx.DGModifier() as md:
                    md.connect(attr_in, bw['i'][i])

            remaps[i]['i'] = float(o) / (n - 1)
            bw['w'][i] = remaps[i]['o'].read()
            s += remaps[i]['o'].read()

        for i, attr_in in enumerate(attrs_in):
            bw['w'][i] = bw['w'][i].read() / s

        if connect:
            with mx.DGModifier() as md:
                md.connect(bw['o'], attr_out)

    mx.delete(remaps)
    return bws


def blend_smooth_weights(node, n, smooth=2, periodic=False):
    # check args
    if not isinstance(node, mx.Node):
        node = mx.encode(str(node))

    n = int(n)

    if smooth < 1:
        smooth = 1
        log.warning('/!\\ blend smooth weights: smooth value cannot be under 1')

    # build
    with mx.DGModifier() as md:
        md.add_attr(node, mx.Double('u', min=0, max=1, keyable=True))

    remaps = []

    if not periodic:
        for i in range(n):
            with mx.DGModifier() as md:
                uu = md.create_node(mx.tAnimCurveUU, name='_cv{}_weight#'.format(i))
            uu['preInfinity'] = 0
            uu['postInfinity'] = 0

            f = i / (n - 1.)
            x = smooth / (n - 1.)
            fp = f + x
            fn = f - x
            if fp > 1:
                fp = 1
            if fn < 0:
                fn = 0

            mc.setKeyframe(str(uu), f=f, v=1, itt='spline', ott='spline')
            if i < n - 1:
                mc.setKeyframe(str(uu), f=fp, v=0, itt='flat', ott='flat')
            if i > 0:
                mc.setKeyframe(str(uu), f=fn, v=0, itt='flat', ott='flat')

            node['u'] >> uu['input']
            remaps.append(uu)

    # output weights
    with mx.DGModifier() as md:
        weight_sum = md.createNode(mx.tPlusMinusAverage, name='_sum#')

    for i, remap in enumerate(remaps):
        remap['output'] >> weight_sum['input1D'][i]

        _attr = 'w{}'.format(i)
        node.add_attr(mx.Double(_attr, channelBox=True))

        with mx.DGModifier() as md:
            div = md.createNode(mx.tMultiplyDivide, name='_div#')
        remap['output'] >> div['input1X']
        weight_sum['output1D'] >> div['input2X']
        div['operation'] = 2
        div['outputX'] >> node[_attr]


@singleton
class ExpressionParser(_ExpressionParser):

    def args_str(self, *args):
        strs = []
        for v in args:
            if isinstance(v, mx.Plug):
                strs.append(v.path())
            else:
                strs.append(str(v))

        return strs

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

        if not isinstance(dst, mx.Plug):
            raise TypeError('connect equal: invalid destination input')

        # connect matrix
        if do_matrix:
            dst_node = dst.node()

            if not isinstance(src, mx.Plug):
                src = self.matrix(*src)

            if isinstance(dst_node, mx.DagNode):
                plug_name = dst.name()
                if plug_name == 'matrix':
                    if isinstance(src, mx.Plug):
                        connect_matrix(src, dst_node)
                    else:
                        mc.xform(str(dst_node), m=src)

                elif plug_name.startswith('worldMatrix'):
                    if isinstance(src, mx.Plug):
                        connect_matrix(src, dst_node, pim=True)
                    else:
                        pim = dst_node['pim'][0].as_matrix()
                        mc.xform(str(dst_node), m=src * pim)

                else:
                    raise TypeError('invalid destination matrix plug')

            else:
                with mx.DGModifier() as md:
                    if isinstance(src, mx.Plug):
                        md.connect(src, dst)
                    else:
                        md.set_attr(dst, src)

            return

        # connect scalar, vector, quat
        with mx.DGModifier() as md:
            if isinstance(src, mx.Plug):
                md.connect(src, dst)
            else:
                # scalar
                if do_scalar:
                    if dst.type_class() == mx.Angle:
                        src = mx.Degrees(src).asRadians()
                    md.set_attr(dst, src)

                # vector
                elif do_vector:
                    for vc, dim in zip(src, 'xyz'):
                        _dst = self.get_component(dst, dim)
                        if isinstance(vc, mx.Plug):
                            md.connect(vc, _dst)
                        else:
                            if dst.type_class() == mx.Angle:
                                src = mx.Degrees(src).asRadians()
                            md.set_attr(_dst, vc)

                # quaternion
                elif do_quat:
                    for vc, dim in zip(src, 'xyzw'):
                        _dst = self.get_component(dst, dim)
                        if isinstance(vc, mx.Plug):
                            md.connect(vc, _dst)
                        else:
                            md.set_attr(_dst, vc)

    def get_nodes(self, nt):
        nodes = []
        for k, v in iteritems(self.created_nodes):
            if isinstance(v, mx.Plug):
                node = v.node()
                if node.is_a(nt):
                    nodes.append(node)
        return nodes

    def optimize(self, result):
        # optimize graph node stack
        remove = []

        # -- addDoubleLinear
        nodes = self.get_nodes(mx.tAddDoubleLinear)
        for node in nodes:
            outputs = list(node['o'].outputs())
            if len(outputs) != 1:
                continue
            _node = outputs[0]
            if _node not in nodes:
                continue

            # get inputs
            inputs = []
            for _add in (node, _node):
                for plug in (_add['input1'], _add['input2']):
                    _i = plug.input(plug=True)
                    if isinstance(_i, mx.Plug):
                        if _i.node() != node:
                            inputs.append(_i)
                        with mx.DGModifier() as md:
                            md.disconnect(_i, plug)
                    else:
                        _i = plug.read()
                        inputs.append(_i)

            # merge
            with mx.DGModifier() as md:
                _add = md.create_node(mx.tBlendWeighted, name='_add#')

            with mx.DGModifier() as md:
                for i, v in enumerate(inputs):
                    if isinstance(v, mx.Plug):
                        md.connect(v, _add['i'][i])
                    else:
                        _add['i'][i] = v

            remove.append(node)
            remove.append(_node)

            # fix output
            with mx.DGModifier() as md:
                for o in _node['o'].outputs(plugs=True):
                    md.connect(_add['o'], o)

            if isinstance(result, mx.Plug):
                if result.path() == _node['o'].path():
                    result = _add['o']

        # -- multMatrix
        nodes = self.get_nodes(mx.tMultMatrix)
        for node in nodes:
            outputs = list(node['o'].outputs())
            if len(outputs) != 1:
                continue
            _node = outputs[0]
            if _node not in nodes:
                continue

            # get inputs
            inputs = []
            for _mmx in (node, _node):
                for i in _mmx['i'].array_indices:
                    _i = _mmx['i'][i].input(plug=True)
                    if isinstance(_i, mx.Plug):
                        if _i.node() != node:
                            inputs.append(_i)
                        with mx.DGModifier() as md:
                            md.disconnect(_i, _mmx['i'][i])
                    else:
                        _i = _mmx['i'][i].as_matrix()
                        inputs.append(_i)
                    _mmx['i'][i] = mx.Matrix4()

            # merge
            for i, v in enumerate(inputs):
                if isinstance(v, mx.Plug):
                    with mx.DGModifier() as md:
                        md.connect(v, _node['i'][i])
                else:
                    _node['i'][i] = v

            remove.append(node)

        # -- wtAddMatrix
        nodes = self.get_nodes(mx.tWtAddMatrix)
        for node in nodes:
            outputs = list(node['o'].outputs())
            if len(outputs) != 1:
                continue
            _node = outputs[0]
            if _node not in nodes:
                continue

            # get inputs
            inputs = []
            for _add in (node, _node):
                for i in _add['i'].array_indices:
                    _w = _add['i'][i]['w'].input(plug=True)
                    if isinstance(_w, mx.Plug):
                        with mx.DGModifier() as md:
                            md.disconnect(_w, _add['i'][i]['w'])
                    else:
                        _w = _add['i'][i]['w'].read()

                    _m = _add['i'][i]['m'].input(plug=True)
                    if isinstance(_m, mx.Plug):
                        if _m.node() != node:
                            inputs.append((_m, _w))
                        with mx.DGModifier() as md:
                            md.disconnect(_m, _add['i'][i]['m'])
                    else:
                        _m = _add['i'][i]['m'].as_matrix()
                        inputs.append((_m, _w))
                    _add['i'][i]['w'] = 1
                    _add['i'][i]['m'] = mx.Matrix4()

            # merge
            for i, v in enumerate(inputs):
                m, w = v
                if isinstance(m, mx.Plug):
                    with mx.DGModifier() as md:
                        md.connect(m, _node['i'][i]['m'])
                else:
                    _node['i'][i]['m'] = m

                if isinstance(w, mx.Plug):
                    with mx.DGModifier() as md:
                        md.connect(w, _node['i'][i]['w'])
                else:
                    _node['i'][i]['w'] = w

            remove.append(node)

        # -- plusMinusAverage 3D
        nodes = self.get_nodes(mx.tPlusMinusAverage)
        nodes = [node for node in nodes if node['op'] == 1 and not node['input1D'].array_indices and not node['input2D'].array_indices]
        for node in nodes:
            outputs = list(node['output3D'].outputs())
            if len(outputs) != 1:
                continue
            _node = outputs[0]
            if _node not in nodes:
                continue

            # get inputs
            inputs = []
            for _add in (node, _node):
                for i in _add['input3D'].array_indices:
                    plug = _add['input3D'][i]

                    _i = plug.input(plug=True)
                    if isinstance(_i, mx.Plug):
                        if _i.node() != node:
                            inputs.append(_i)
                        with mx.DGModifier() as md:
                            md.disconnect(_i, plug)
                    else:
                        _i = []
                        for dim in 'xyz':
                            _plug = _add['input3D'][i]['input3D' + dim]
                            _ic = _plug.input(plug=True)
                            if isinstance(_ic, mx.Plug):
                                with mx.DGModifier() as md:
                                    md.disconnect(_ic, _plug)
                                _i.append(_ic)
                            else:
                                _i.append(_plug.read())
                        inputs.append(_i)
                    plug.write((0, 0, 0))

            # merge
            for i, v in enumerate(inputs):
                if isinstance(v, mx.Plug):
                    with mx.DGModifier() as md:
                        md.connect(v, _node['input3D'][i])
                else:
                    for vc, dim in zip(v, 'xyz'):
                        if isinstance(vc, mx.Plug):
                            with mx.DGModifier() as md:
                                md.connect(vc, _node['input3D'][i]['input3D' + dim])
                        else:
                            _node['input3D'][i]['input3D' + dim] = vc

            remove.append(node)

        # cleanup
        if remove:
            mx.delete(remove)

        return result

    def add(self, v1, v2):

        # scalar + scalar
        if self.is_scalar(v1) and self.is_scalar(v2):
            return connect_add(v1, v2)

        # vector + vector
        if self.is_vector(v1) and self.is_vector(v2):
            with mx.DGModifier() as md:
                node = md.create_node(mx.tPlusMinusAverage, name='_add_vector#')

            with mx.DGModifier() as md:
                for i, v in zip((0, 1), (v1, v2)):
                    if isinstance(v, mx.Plug):
                        md.connect(v, node['input3D'][i])
                    else:
                        for vc, dim in zip(v, 'xyz'):
                            plug = node['input3D'][i]['input3D' + dim]
                            if isinstance(vc, mx.Plug):
                                md.connect(vc, plug)
                            else:
                                md.set_attr(plug, vc)

            return node['output3D']

        # quat + quat
        if self.is_quat(v1) and self.is_quat(v2):
            with mx.DGModifier() as md:
                node = md.create_node('quatAdd', name='_add_quat#')

            with mx.DGModifier() as md:
                for i, v in zip((1, 2), (v1, v2)):
                    if isinstance(v, mx.Plug):
                        md.connect(v, node['input{}Quat'.format(i)])
                    else:
                        for vc, dim in zip(v, 'XYZW'):
                            plug = node['input{}Quat{}'.format(i, dim)]
                            if isinstance(vc, mx.Plug):
                                md.connect(vc, plug)
                            else:
                                md.set_attr(plug, vc)

            return node['outputQuat']

        # matrix + matrix
        if self.is_matrix(v1) and self.is_matrix(v2):
            if not isinstance(v1, (mx.Plug, mx.Matrix4)):
                v1 = self.matrix(*v1)
            if not isinstance(v2, (mx.Plug, mx.Matrix4)):
                v2 = self.matrix(*v2)

            with mx.DGModifier() as md:
                node = md.create_node(mx.tWtAddMatrix, name='_add_xfo#')

            with mx.DGModifier() as md:
                for i, v in zip((0, 1), (v1, v2)):
                    if isinstance(v, mx.Plug):
                        md.connect(v, node['i'][i]['m'])
                    else:
                        node['i'][i]['m'] = v

            return node['o']

        # invalid
        log.warning('input1: {}, {}'.format(type(v1), v1))
        log.warning('input2: {}, {}'.format(type(v2), v2))
        raise TypeError('add: invalid inputs')

    def subtract(self, v1, v2):

        # scalar - scalar
        if self.is_scalar(v1) and self.is_scalar(v2):
            return connect_sub(v1, v2)

        # vector - vector
        if self.is_vector(v1) and self.is_vector(v2):
            with mx.DGModifier() as md:
                node = md.create_node(mx.tPlusMinusAverage, name='_sub#')

            with mx.DGModifier() as md:
                md.set_attr(node['op'], 2)

                for i, v in zip((0, 1), (v1, v2)):
                    if isinstance(v, mx.Plug):
                        md.connect(v, node['input3D'][i])
                    else:
                        for vc, dim in zip(v, 'xyz'):
                            plug = node['input3D'][i]['input3D' + dim]
                            if isinstance(vc, mx.Plug):
                                md.connect(vc, plug)
                            else:
                                md.set_attr(plug, vc)

            return node['output3D']

        # invalid
        log.warning('input1: {}, {}'.format(type(v1), v1))
        log.warning('input2: {}, {}'.format(type(v2), v2))
        raise TypeError('substract: invalid inputs')

    def multiply(self, v1, v2):

        # scalar * scalar
        _s1 = self.is_scalar(v1)
        _s2 = self.is_scalar(v2)

        if _s1 and _s2:
            return connect_mult(v1, v2)

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
            with mx.DGModifier() as md:
                node = md.create_node(mx.tMultiplyDivide, name='_scale#')

            with mx.DGModifier() as md:
                if isinstance(v1, mx.Plug):
                    [md.connect(v1, node['input1' + i]) for i in 'XYZ']
                else:
                    [md.set_attr(node['input1' + i], v1) for i in 'XYZ']

                if isinstance(v2, mx.Plug):
                    md.connect(v2, node['input2'])
                else:
                    for vc, dim in zip(v2, 'XYZ'):
                        plug = node['input2' + dim]
                        if isinstance(vc, mx.Plug):
                            md.connect(vc, plug)
                        else:
                            md.set_attr(plug, vc)

            return node['output']

        # quat * quat
        if self.is_quat(v1) and self.is_quat(v2):
            with mx.DGModifier() as md:
                node = md.create_node('quatProd', name='_mult_quat#')

            with mx.DGModifier() as md:
                for i, v in zip((1, 2), (v1, v2)):
                    if isinstance(v, mx.Plug):
                        md.connect(v, node['input{}Quat'.format(i)])
                    else:
                        for vc, dim in zip(v, 'XYZW'):
                            plug = node['input{}Quat{}'.format(i, dim)]
                            if isinstance(vc, mx.Plug):
                                md.connect(vc, plug)
                            else:
                                md.set_attr(plug, vc)

            return node['outputQuat']

        # matrix * matrix
        _m1 = self.is_matrix(v1)
        _m2 = self.is_matrix(v2)
        if _m1 and _m2:

            with mx.DGModifier() as md:
                node = md.create_node(mx.tMultMatrix, name='_mmx#')

            with mx.DGModifier() as md:
                for i, v in zip((0, 1), (v1, v2)):
                    if isinstance(v, mx.Plug):
                        md.connect(v, node['i'][i])
                    else:
                        node['i'][i] = v

            return node['o']

        # scalar * matrix
        if _m1 and _s2:
            v1, v2 = v2, v1
            _s1, _m2 = _m1, _s2

        if _s1 and _m2:
            if not isinstance(v2, (mx.Plug, mx.Matrix4)):
                v2 = self.matrix(*v2)

            with mx.DGModifier() as md:
                node = md.create_node(mx.tWtAddMatrix, name='_weight_xfo#')

            with mx.DGModifier() as md:
                i = 0
                if isinstance(v1, mx.Plug):
                    md.connect(v1, node['i'][i]['w'])
                else:
                    node['i'][i]['w'] = v1  # unlikely

                if isinstance(v2, mx.Plug):
                    md.connect(v2, node['i'][i]['m'])
                else:
                    node['i'][i]['m'] = v2

            return node['o']

        # matrix * vector
        if _m1 and _v2:
            with mx.DGModifier() as md:
                node = md.create_node(mx.tVectorProduct, name='_mult_dir#')

            with mx.DGModifier() as md:
                node['op'] = 3  # vector matrix product

                if not isinstance(v1, (mx.Plug, mx.Matrix4)):
                    v1 = self.matrix(*v1)
                if isinstance(v1, mx.Plug):
                    md.connect(v1, node['matrix'])
                else:
                    node['matrix'] = v1

                if isinstance(v2, mx.Plug):
                    md.connect(v2, node[''])
                else:
                    for vc, dim in zip(v2, 'XYZ'):
                        if isinstance(vc, mx.Plug):
                            md.connect(vc, node['input1' + dim])
                        else:
                            node['input1' + dim] = vc

            return node['output']

        # invalid
        log.warning('input1: {}, {}'.format(type(v1), v1))
        log.warning('input2: {}, {}'.format(type(v2), v2))
        raise TypeError('multiply: invalid inputs')

    def pow(self, v1, v2):

        # scalar ^ scalar
        if self.is_scalar(v1) and self.is_scalar(v2):
            return connect_power(v1, v2)

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
            with mx.DGModifier() as md:
                node = md.create_node(mx.tInverseMatrix, name='_imx#')

            with mx.DGModifier() as md:
                if not isinstance(v, (mx.Plug, mx.Matrix4)):
                    v = self.matrix(*v)
                if isinstance(v, mx.Plug):
                    md.connect(v, node['inputMatrix'])
                else:
                    node['inputMatrix'] = v

            return node['outputMatrix']

        # quaternion
        if self.is_quat(v):
            with mx.DGModifier() as md:
                node = md.create_node('quatInvert', name='_inverse_quat#')

            with mx.DGModifier() as md:
                if isinstance(v, mx.Plug):
                    md.connect(v, node['inputQuat'])
                else:
                    for vc, dim in zip(v, 'XYZW'):
                        if isinstance(vc, mx.Plug):
                            md.connect(vc, node['inputQuat' + dim])
                        else:
                            node['inputQuat' + dim] = vc

            return node['outputQuat']

        # invalid
        log.warning('input: {}, {}'.format(type(v), v))
        raise TypeError('inverse: invalid input')

    def divide(self, v1, v2):

        # scalar / scalar
        _s1 = self.is_scalar(v1)
        _s2 = self.is_scalar(v2)

        if _s1 and _s2:
            return connect_div(v1, v2)

        # vector / scalar
        _v1 = self.is_vector(v1)
        _v2 = self.is_vector(v2)

        if _v2 and _s1:
            v1, v2 = v2, v1
            _v1, _s2 = _v2, _s1

        if _v1 and _s2:
            with mx.DGModifier() as md:
                div = md.create_node(mx.tMultiplyDivide, name='_div#')

            with mx.DGModifier() as md:
                if isinstance(v1, mx.Plug):
                    md.connect(v1, div['input1'])
                else:
                    for vc, dim in zip(v1, 'XYZ'):
                        plug = div['input1' + dim]
                        if isinstance(vc, mx.Plug):
                            md.connect(vc, plug)
                        else:
                            md.set_attr(plug, vc)

                if isinstance(v2, mx.Plug):
                    [md.connect(v2, div['input2' + dim]) for dim in 'XYZ']
                else:
                    [md.set_attr(div['input2' + dim], v2) for dim in 'XYZ']

            return div['output']

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

    def logical_or(self, a, b):

        # check inputs
        if not self.is_scalar(a) and not self.is_scalar(b):
            log.warning('input1: {}, {}'.format(type(a), a))
            log.warning('input2: {}, {}'.format(type(b), b))
            raise TypeError('or: invalid inputs')

        # logical gate node emulation
        with mx.DGModifier() as md:
            node = md.create_node(mx.tAddDoubleLinear, name='_or_op#')
            convert = md.create_node(mx.tNetwork, name='_or#')

        with mx.DGModifier() as md:
            md.add_attr(convert, mx.Boolean('input1'))
            md.add_attr(convert, mx.Boolean('input2'))
            md.add_attr(convert, mx.Boolean('output'))
        with mx.DGModifier() as md:
            md.connect(convert['input1'], node['input1'])
            md.connect(convert['input2'], node['input2'])
            md.connect(node['output'], convert['output'])

        # connect
        if isinstance(a, mx.Plug):
            with mx.DGModifier() as md:
                md.connect(a, convert['input1'])
        else:
            convert['input1'] = a

        if isinstance(b, mx.Plug):
            with mx.DGModifier() as md:
                md.connect(b, convert['input2'])
        else:
            convert['input2'] = b

        return convert['output']

    def logical_and(self, a, b):

        # check inputs
        if not self.is_scalar(a) and not self.is_scalar(b):
            log.warning('input1: {}, {}'.format(type(a), a))
            log.warning('input2: {}, {}'.format(type(b), b))
            raise TypeError('and: invalid inputs')

        # logical gate node emulation
        with mx.DGModifier() as md:
            node = md.create_node(mx.tMultDoubleLinear, name='_and_op#')
            convert = md.create_node(mx.tNetwork, name='_and#')

        with mx.DGModifier() as md:
            md.add_attr(convert, mx.Boolean('input1'))
            md.add_attr(convert, mx.Boolean('input2'))
            md.add_attr(convert, mx.Boolean('output'))
        with mx.DGModifier() as md:
            md.connect(convert['input1'], node['input1'])
            md.connect(convert['input2'], node['input2'])
            md.connect(node['output'], convert['output'])

        # connect
        if isinstance(a, mx.Plug):
            with mx.DGModifier() as md:
                md.connect(a, convert['input1'])
        else:
            convert['input1'] = a

        if isinstance(b, mx.Plug):
            with mx.DGModifier() as md:
                md.connect(b, convert['input2'])
        else:
            convert['input2'] = b

        return convert['output']

    def logical_xor(self, a, b):

        # check inputs
        if not self.is_scalar(a) and not self.is_scalar(b):
            log.warning('input1: {}, {}'.format(type(a), a))
            log.warning('input2: {}, {}'.format(type(b), b))
            raise TypeError('xor: invalid inputs')

        # logical gate node emulation
        with mx.DGModifier() as md:
            node = md.create_node(mx.tCondition, name='_xor_op#')
            convert = md.create_node(mx.tNetwork, name='_xor#')

        with mx.DGModifier() as md:
            md.add_attr(convert, mx.Boolean('input1'))
            md.add_attr(convert, mx.Boolean('input2'))
            md.add_attr(convert, mx.Boolean('output'))
        with mx.DGModifier() as md:
            md.connect(convert['input1'], node['firstTerm'])
            md.connect(convert['input2'], node['secondTerm'])
            md.connect(node['outColorR'], convert['output'])

        # connect
        if isinstance(a, mx.Plug):
            with mx.DGModifier() as md:
                md.connect(a, convert['input1'])
        else:
            convert['input1'] = a

        if isinstance(b, mx.Plug):
            with mx.DGModifier() as md:
                md.connect(b, convert['input2'])
        else:
            convert['input2'] = b

        return convert['output']

    def logical_not(self, b):

        # check input
        if not self.is_scalar(b):
            log.warning('input: {}, {}'.format(type(b), b))
            raise TypeError('not: invalid inputs')

        # logical gate node emulation
        with mx.DGModifier() as md:
            node = md.create_node(mx.tCondition, name='_if#')
            convert = md.create_node(mx.tNetwork, name='_not#')
        node['op'] = 1  # b != False ? False : True

        with mx.DGModifier() as md:
            md.add_attr(convert, mx.Boolean('output'))
        with mx.DGModifier() as md:
            md.connect(node['outColorR'], convert['output'])

        # connect
        if isinstance(b, mx.Plug):
            with mx.DGModifier() as md:
                md.connect(b, node['firstTerm'])
        else:
            node['firstTerm'] = b

        return convert['output']

    def int(self, x):

        # check input
        if not self.is_scalar(x):
            log.warning('input: {}, {}'.format(type(x), x))
            raise TypeError('int: invalid inputs')

        # build node
        with mx.DGModifier() as md:
            node = md.create_node(mx.tAnimCurveUU, name='_int#')

        mc.setKeyframe(str(node), v=0, f=0)
        mc.setKeyframe(str(node), v=1, f=1)
        mc.keyTangent(str(node), ott='step')
        node['preInfinity'] = 4
        node['postInfinity'] = 4

        # connect
        if isinstance(x, mx.Plug):
            with mx.DGModifier() as md:
                md.connect(x, node['input'])
        else:
            node['input'] = x

        return node['output']

    def bool(self, x):

        # check input
        if not self.is_scalar(x):
            log.warning('input: {}, {}'.format(type(x), x))
            raise TypeError('bool: invalid inputs')

        # build node
        with mx.DGModifier() as md:
            node = md.create_node(mx.tNetwork, name='_bool#')

        with mx.DGModifier() as md:
            md.add_attr(node, mx.Boolean('value'))

        # connect
        if isinstance(x, mx.Plug):
            with mx.DGModifier() as md:
                md.connect(x, node['value'])
        else:
            node['value'] = x

        return node['value']

    def clamp(self, value, min_value, max_value):

        # check inputs
        if not self.is_scalar(value):
            raise TypeError('clamp: invalid value')
        if not self.is_scalar(min_value):
            raise TypeError('clamp: invalid min_value')
        if not self.is_scalar(max_value):
            raise TypeError('clamp: invalid max_value')

        # connect
        with mx.DGModifier() as md:
            node = md.create_node(mx.tClamp, name='_clamp#')

        with mx.DGModifier() as md:
            for v, attr in ((min_value, 'minR'), (max_value, 'maxR')):
                if isinstance(v, mx.Plug):
                    md.connect(v, node[attr])
                else:
                    md.set_attr(node[attr], v)

            if isinstance(value, mx.Plug):
                md.connect(value, node['inputR'])
            else:
                # unlikely for a static value to be clamped, but it should still work
                md.set_attr(node['inputR'], value)

        return node['outputR']

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
        with mx.DGModifier() as md:
            node = md.create_node(mx.tCondition, name='_if#')
        node['op'] = self.conditionals.index(operation)

        with mx.DGModifier() as md:
            for v, attr in ((first_term, 'firstTerm'), (second_term, 'secondTerm')):
                if isinstance(v, mx.Plug):
                    md.connect(v, node[attr])
                else:
                    node[attr] = v

            # switch scalar
            if do_scalar:
                for v, attr in ((if_true, 'colorIfTrueR'), (if_false, 'colorIfFalseR')):
                    if isinstance(v, mx.Plug):
                        md.connect(v, node[attr])
                    else:
                        node[attr] = v

                return node['outColorR']

            # switch vector
            if do_vector:
                for v, attr in ((if_true, 'colorIfTrue'), (if_false, 'colorIfFalse')):
                    if isinstance(v, mx.Plug):
                        md.connect(v, node[attr])
                    else:
                        for vc, dim in zip(v, 'RGB'):
                            if isinstance(vc, mx.Plug):
                                md.connect(vc, node[attr + dim])
                            else:
                                node[attr + dim] = vc

                return node['outColor']

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

        # scalar
        if do_scalar:
            with mx.DGModifier() as md:
                node = md.create_node(mx.tBlendTwoAttr, name='_lerp#')

            with mx.DGModifier() as md:
                if isinstance(t, mx.Plug):
                    md.connect(t, node['attributesBlender'])
                else:
                    # static value on attributesBlender doesn't make much sense but we don't want to error out
                    node['attributesBlender'] = t

                for i, v in zip((0, 1), (a, b)):
                    if isinstance(v, mx.Plug):
                        md.connect(v, node['input'][i])
                    else:
                        node['input'][i] = v

            return node['output']

        # vector
        if do_vector:
            with mx.DGModifier() as md:
                node = md.create_node(mx.tBlendColors, name='_lerp#')

            with mx.DGModifier() as md:
                if isinstance(t, mx.Plug):
                    md.connect(t, node['blender'])
                else:
                    # static value on attributesBlender doesn't make much sense but we don't want to error out
                    node['blender'] = t

                for i, v in zip(('2', '1'), (a, b)):
                    if isinstance(v, mx.Plug):
                        md.connect(v, node['color' + i])
                    else:
                        for vc, dim in zip(v, 'RGB'):
                            if isinstance(vc, mx.Plug):
                                md.connect(vc, node['color' + i + dim])
                            else:
                                node['color' + i + dim] = vc

            return node['output']

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
        with mx.DGModifier() as md:
            node = md.create_node(mx.tSetRange, name='_remap#')

        with mx.DGModifier() as md:
            if isinstance(v, mx.Plug):
                md.connect(v, node['valueX'])
            else:
                node['valueX'] = v

            if isinstance(old_min, mx.Plug):
                md.connect(old_min, node['oldMinX'])
            else:
                node['oldMinX'] = old_min

            if isinstance(old_max, mx.Plug):
                md.connect(old_max, node['oldMaxX'])
            else:
                node['oldMaxX'] = old_max

            if isinstance(new_min, mx.Plug):
                md.connect(new_min, node['minX'])
            else:
                node['minX'] = new_min

            if isinstance(new_max, mx.Plug):
                md.connect(new_max, node['maxX'])
            else:
                node['maxX'] = new_max

        return node['outValueX']

    def cos(self, a):
        if not self.is_scalar(a):
            raise TypeError('cos: invalid input')

        if isinstance(a, mx.Plug):
            with mx.DGModifier() as md:
                node = md.create_node(mx.tEulerToQuat, name='_cos#')
            connect_mult(a, 2, node['inputRotateX'])
            return node['outputQuatW']
        else:
            return math.cos(a * math.pi / 180)

    def sin(self, a):
        if not self.is_scalar(a):
            raise TypeError('sin: invalid input')

        if isinstance(a, mx.Plug):
            with mx.DGModifier() as md:
                node = md.create_node(mx.tEulerToQuat, name='_sin#')
            connect_mult(a, 2, node['inputRotateX'])
            return node['outputQuatX']
        else:
            return math.sin(a * math.pi / 180)

    def acos(self, cos):
        if not self.is_scalar(cos):
            raise TypeError('acos: invalid input')

        if isinstance(cos, mx.Plug):
            with mx.DGModifier() as md:
                node = md.create_node(mx.tQuatToEuler, name='_acos#')
            sin = connect_power(connect_sub(1, connect_mult(cos, cos)), 0.5)
            with mx.DGModifier() as md:
                md.connect(sin, node['inputQuatX'])
                md.connect(cos, node['inputQuatW'])
            return connect_mult(node['outputRotateX'], 0.5)
        else:
            return math.acos(cos) * 180 / math.pi

    def asin(self, sin):
        if not self.is_scalar(sin):
            raise TypeError('asin: invalid input')

        if isinstance(sin, mx.Plug):
            with mx.DGModifier() as md:
                node = md.create_node(mx.tQuatToEuler, name='_asin#')
            cos = connect_power(connect_sub(1, connect_mult(sin, sin)), 0.5)
            with mx.DGModifier() as md:
                md.connect(sin, node['inputQuatX'])
                md.connect(cos, node['inputQuatW'])
            return connect_mult(node['outputRotateX'], 0.5)
        else:
            return math.asin(sin) * 180 / math.pi

    def atan(self, tan):
        if not self.is_scalar(tan):
            raise TypeError('atan: invalid input')

        if isinstance(tan, mx.Plug):
            with mx.DGModifier() as md:
                node = md.create_node(mx.tAngleBetween, name='_atan#')
            node['vector1'] = (1, 0, 0)
            node['vector2'] = (1, 0, 0)
            with mx.DGModifier() as md:
                md.connect(tan, node['vector2Y'])
            return node['angle']
        else:
            return math.atan(tan) * 180 / math.pi

    def noise(self, v):
        if not self.is_scalar(v):
            raise TypeError('noise: invalid input')

        with mx.DGModifier() as md:
            node = md.create_node(mx.tNoise, n='_noise#')
        node['noiseType'] = 0  # perlin

        if not isinstance(v, (float, int, mx.Plug)):
            v = mx.encode(str(v))

        if isinstance(v, mx.Plug):
            with mx.DGModifier() as md:
                md.connect(v, node['time'])
        else:
            node['time'] = v

        return node['outColorR']

    def dnoise(self, v):
        if not self.is_scalar(v):
            raise TypeError('dnoise: invalid input')

        with mx.DGModifier() as md:
            node = md.create_node(mx.tNoise, name='_dnoise#')
        node['noiseType'] = 0  # perlin

        if not isinstance(v, (float, int, mx.Plug)):
            v = mx.encode(str(v))

        if isinstance(v, mx.Plug):
            with mx.DGModifier() as md:
                md.connect(v, node['time'])
        else:
            node['time'] = v

        noise_out = connect_mult(node['outColorR'], 2)
        noise_out = connect_sub(noise_out, 1)
        return noise_out

    def norm(self, v):

        # vector
        if self.is_vector(v):
            with mx.DGModifier() as md:
                norm = md.create_node(mx.tVectorProduct, name='_norm#')

            with mx.DGModifier() as md:
                md.set_attr(norm['op'], 0)
                md.set_attr(norm['normalizeOutput'], True)

                if isinstance(v, mx.Plug):
                    md.connect(v, norm['input1'])
                else:
                    for vc, dim in zip(v, 'XYZ'):
                        plug = norm['input1' + dim]
                        if isinstance(vc, mx.Plug):
                            md.connect(vc, plug)
                        else:
                            md.set_attr(plug, vc)

            return norm['output']

        # quat
        if self.is_quat(v):
            with mx.DGModifier() as md:
                norm = md.create_node('quatNormalize', name='_norm#')

            with mx.DGModifier() as md:
                if isinstance(v, mx.Plug):
                    md.connect(v, norm['inputQuat'])
                elif isinstance(v, om.MQuaternion):
                    norm['inputQuat'] = v
                else:
                    for vc, dim in zip(v, 'XYZW'):
                        plug = norm['inputQuat' + dim]
                        if isinstance(vc, mx.Plug):
                            md.connect(vc, plug)
                        else:
                            md.set_attr(plug, vc)

            return norm['output']

        # invalid
        log.warning('input1: {}, {}'.format(type(v), v))
        raise TypeError('normalize: invalid input')

    def dot(self, v1, v2, check=True):

        # check
        if check:
            if not self.is_vector(v1):
                raise TypeError('dot: invalid input v1')
            if not self.is_vector(v2):
                raise TypeError('dot: invalid input v2')

        # connect
        with mx.DGModifier() as md:
            node = md.create_node(mx.tVectorProduct, name='_dot#')

        with mx.DGModifier() as md:

            for i, v in zip(('1', '2'), (v1, v2)):
                if isinstance(v, mx.Plug):
                    md.connect(v, node['input' + i])
                else:
                    for vc, dim in zip(v, 'XYZ'):
                        plug = node['input' + i + dim]
                        if isinstance(vc, mx.Plug):
                            md.connect(vc, plug)
                        else:
                            md.set_attr(plug, vc)

        return node['outputX']

    def cross(self, v1, v2, check=True):

        # check
        if check:
            if not self.is_vector(v1):
                raise TypeError('cross: invalid input v1')
            if not self.is_vector(v2):
                raise TypeError('cross: invalid input v2')

        # connect
        with mx.DGModifier() as md:
            node = md.create_node(mx.tVectorProduct, name='_cross#')

        with mx.DGModifier() as md:
            md.set_attr(node['op'], 2)  # cross

            for i, v in zip(('1', '2'), (v1, v2)):
                if isinstance(v, mx.Plug):
                    md.connect(v, node['input' + i])
                else:
                    for vc, dim in zip(v, 'XYZ'):
                        plug = node['input' + i + dim]
                        if isinstance(vc, mx.Plug):
                            md.connect(vc, plug)
                        else:
                            md.set_attr(plug, vc)

        return node['output']

    def len(self, v):

        # check
        if not self.is_vector(v):
            raise TypeError('length: invalid input')

        # connect
        with mx.DGModifier() as md:
            node = md.create_node(mx.tDistanceBetween, name='_len#')

        with mx.DGModifier() as md:
            if isinstance(v, mx.Plug):
                md.connect(v, node['point2'])
            else:
                for dim, vc in zip('XYZ', v):
                    plug = node['point2{}'.format(dim)]
                    if isinstance(vc, mx.Plug):
                        md.connect(vc, plug)
                    else:
                        md.set_attr(plug, vc)

        return node['distance']

    def distance(self, v1, v2):

        # check
        for i, v in enumerate((v1, v2)):
            if not self.is_vector(v) and not self.is_matrix(v):
                raise TypeError('distance: invalid input {}'.format(i))

        # connect
        with mx.DGModifier() as md:
            node = md.create_node(mx.tDistanceBetween, name='_len#')

        with mx.DGModifier() as md:
            for i, v in zip(('1', '2'), (v1, v2)):
                if isinstance(v, mx.Plug):
                    if self.is_matrix_plug(v):
                        decomp_mat = md.create_node(mx.tDecomposeMatrix, name='_decomp_mat#')
                        md.connect(v, decomp_mat['inputMatrix'])
                        v = decomp_mat['outputTranslate']

                    md.connect(v, node['point' + i])
                else:
                    for dim, vc in zip('XYZ', v):
                        plug = node['point' + i + dim]
                        if isinstance(vc, mx.Plug):
                            md.connect(vc, plug)
                        else:
                            md.set_attr(plug, vc)

        return node['distance']

    def angle(self, v1, v2):

        # check
        for i, v in enumerate((v1, v2)):
            if not self.is_vector(v):
                raise TypeError('distance: invalid input {}'.format(i))

        # connect
        with mx.DGModifier() as md:
            node = md.create_node(mx.tAngleBetween, name='_angle#')

        with mx.DGModifier() as md:
            for i, v in zip(('1', '2'), (v1, v2)):
                if isinstance(v, mx.Plug):
                    md.connect(v, node['vector' + i])
                else:
                    for dim, vc in zip('XYZ', v):
                        plug = node['vector' + i + dim]
                        if isinstance(vc, mx.Plug):
                            md.connect(vc, plug)
                        else:
                            md.set_attr(plug, vc)

        return node['angle']

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
        with mx.DGModifier() as md:
            node = md.create_node('quatSlerp', name='_slerp#')

        with mx.DGModifier() as md:
            if not shortest:
                node['angleInterpolation'] = 1  # slerp positive

            if isinstance(t, mx.Plug):
                md.connect(t, node['inputT'])
            else:
                # static value on attributesBlender doesn't make much sense but we don't want to error out
                node['inputT'] = t

            for i, v in zip((1, 2), (a, b)):
                if isinstance(v, mx.Plug):
                    md.connect(v, node['input{}Quat'.format(i)])
                else:
                    for vc, dim in zip(v, 'XYZW'):
                        if isinstance(vc, mx.Plug):
                            md.connect(vc, node['input{}Quat{}'.format(i, dim)])
                        else:
                            node['input{}Quat{}'.format(i, dim)] = vc

        return node['outputQuat']

    def vector(self, x, y, z):

        # check
        if not self.is_scalar(x):
            raise TypeError('vector: invalid input x')
        if not self.is_scalar(y):
            raise TypeError('vector: invalid input y')
        if not self.is_scalar(z):
            raise TypeError('vector: invalid input z')

        # connect?
        if any(map(lambda v: isinstance(v, mx.Plug), (x, y, z))):
            return [x, y, z]
        else:
            return mx.Vector(x, y, z)

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

            if any(map(lambda x: isinstance(x, mx.Plug), (x, y, z))) or isinstance(ro, mx.Plug):
                return [x, y, z], ro
            else:
                x = mx.Degrees(x).asRadians()
                y = mx.Degrees(y).asRadians()
                z = mx.Degrees(z).asRadians()
                return mx.Euler(x, y, z, ro)

        # quaternion
        elif len(args) == 1 and self.is_quat(args[0]):
            q = args[0]

            if isinstance(q, om.MQuaternion):
                return mx.Euler(q.asEulerRotation())

            # from plug
            with mx.DGModifier() as md:
                node = md.create_node(mx.tQuatToEuler, name='_euler#')

            with mx.DGModifier() as md:
                if isinstance(q, mx.Plug):
                    md.connect(q, node['inputQuat'])
                else:
                    for vc, dim in zip(q, 'XYZW'):
                        if isinstance(vc, mx.Plug):
                            md.connect(vc, node['inputQuat' + dim])
                        else:
                            node['inputQuat' + dim] = vc

            return node['outputRotate'], node['inputRotateOrder']

    def rotate_order(self, ro):
        if ro in {0, 1, 2, 3, 4, 5}:
            return ro
        if isinstance(ro, mx.Plug) and ro.name() == 'rotateOrder':
            return ro

        # convert
        if ro not in self.rotate_orders:
            raise TypeError('invalid rotate order')

        rotate_orders = {
            'XYZ': 0,
            'YZX': 1,
            'ZXY': 2,
            'XZY': 3,
            'YXZ': 4,
            'ZYX': 5
        }
        return rotate_orders[ro]

    def quat(self, *args):

        # pack euler
        if len(args) == 2:
            args = [args]

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
            if any(map(lambda v: isinstance(v, mx.Plug), (x, y, z, w))):
                return [x, y, z, w]
            else:
                return mx.Quaternion(x, y, z, w)

        # euler
        elif len(args) == 1 and self.is_euler(args[0]):
            e = args[0]

            if isinstance(e, mx.Euler):
                return mx.Quaternion(e.asQuaternion())

            else:
                with mx.DGModifier() as md:
                    node = md.create_node(mx.tEulerToQuat, name='_quat#')

                with mx.DGModifier() as md:
                    for vc, dim in zip(e[0], 'XYZ'):
                        if isinstance(vc, mx.Plug):
                            md.connect(vc, node['inputRotate' + dim])
                        else:
                            node['inputRotate' + dim] = mx.Degrees(vc).asRadians()

                    if isinstance(e[1], mx.Plug):
                        md.connect(e[1], node['inputRotateOrder'])
                    else:
                        node['inputRotateOrder'] = e[1]

                return node['outputQuat']

        # transform
        elif len(args) == 1 and self.is_matrix(args[0]):
            xfo = args[0]

            if isinstance(xfo, mx.Plug):
                with mx.DGModifier() as md:
                    dmx = md.create_node(mx.tDecomposeMatrix, name='_dmx#')
                    node = md.create_node(mx.tEulerToQuat, name='_quat#')
                with mx.DGModifier() as md:
                    md.connect(xfo, dmx['inputMatrix'])
                    md.connect(dmx['outputRotate'], node['inputRotate'])

                return node['outputQuat']

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
        if isinstance(t, mx.Plug) or (isinstance(t, (list, tuple)) and any(map(self.is_scalar_plug, t))):
            has_plug = True
        elif isinstance(r, mx.Plug) or (isinstance(r, (list, tuple)) and any(map(self.is_scalar_plug, r))):
            has_plug = True
        elif _re and isinstance(r, (list, tuple)):
            if isinstance(r[0], mx.Plug):
                has_plug = True
            elif isinstance(r[0], (list, tuple)) and any(map(self.is_scalar_plug, r[0])):
                has_plug = True
        elif isinstance(s, mx.Plug) or (isinstance(s, (list, tuple)) and any(map(self.is_scalar_plug, s))):
            has_plug = True

        if not has_plug:
            return mx.Transformation(translate=t, rotate=r, scale=s)

        else:
            with mx.DGModifier() as md:
                node = md.create_node(mx.tComposeMatrix, name='_xfo#')

            with mx.DGModifier() as md:
                # translate
                if isinstance(t, mx.Plug):
                    md.connect(t, node['t'])
                else:
                    for v, dim in zip(t, 'XYZ'):
                        if isinstance(v, mx.Plug):
                            md.connect(v, node['inputTranslate' + dim])
                        else:
                            node['inputTranslate' + dim] = v

                # rotation
                if isinstance(r, mx.Euler):
                    node['inputRotate'] = r
                    node['inputRotateOrder'] = r.order
                elif not _rq:
                    for v, dim in zip(r[0], 'XYZ'):
                        if isinstance(v, mx.Plug):
                            md.connect(v, node['inputRotate' + dim])
                        else:
                            node['inputRotate' + dim] = mx.Degrees(v).asRadians()
                    if isinstance(r[1], mx.Plug):
                        md.connect(r[1], node['inputRotateOrder'])
                    else:
                        node['inputRotateOrder'] = r[1]
                else:
                    # quaternion mode
                    node['useEulerRotation'] = False

                    if isinstance(r, mx.Plug):
                        md.connect(r, node['inputQuat'])
                    else:
                        for vc, dim in zip(r, 'XYZW'):
                            if isinstance(vc, mx.Plug):
                                md.connect(vc, node['inputQuat' + dim])
                            else:
                                node['inputQuat' + dim] = vc

                # scale
                if isinstance(s, mx.Plug):
                    md.connect(s, node['s'])
                else:
                    for v, dim in zip(s, 'XYZ'):
                        if isinstance(v, mx.Plug):
                            md.connect(v, node['inputScale' + dim])
                        else:
                            node['inputScale' + dim] = v

            return node['outputMatrix']

    def matrix(self, *args):
        # check
        if not len(args) == 16 and not len(args) == 4 and map(lambda x: len(x) in {3, 4}, args):
            raise ValueError('matrix: invalid arguments')

        # connect?
        values = list(args)

        if len(values) == 4:
            for i in range(4):
                if isinstance(values[i], mx.Plug):
                    continue
                values[i] = list(values[i])
                if len(values[i]) == 3:
                    values[i].append((0, 0, 0, 1)[i])

        else:
            values = [values[:4], values[4:8], values[8:12], values[12:]]

        has_plug = False
        for line in values:
            if isinstance(line, mx.Plug):
                has_plug = True
                break
            for v in line:
                if isinstance(v, mx.Plug):
                    has_plug = True
                    break
            if has_plug:
                break

        if has_plug:
            with mx.DGModifier() as md:
                node = md.create_node(mx.tFourByFourMatrix, name='_ijk#')

            with mx.DGModifier() as md:
                for i, line in enumerate(values):
                    if isinstance(line, mx.Plug):
                        line = [
                            self.get_component(line, 'x'),
                            self.get_component(line, 'y'),
                            self.get_component(line, 'z')
                        ]
                    for j, v in enumerate(line):
                        if isinstance(v, mx.Plug):
                            md.connect(v, node['in{}{}'.format(i, j)])
                        else:
                            node['in{}{}'.format(i, j)] = v

            return node['output']
        else:
            return mx.Matrix4(values)

    def get_component(self, v, i):
        i = i.lower()

        # vector
        if self.is_vector(v):
            if i not in 'xyz':
                raise ValueError('invalid component: it must be x, y or z')

            if isinstance(v, (om.MVector, om.MFloatVector)):
                if i == 'x':
                    return v.x
                elif i == 'y':
                    return v.y
                elif i == 'z':
                    return v.z

            elif isinstance(v, mx.Plug):
                plug = v.plug()
                try:
                    if i == 'x':
                        return mx.Plug(v.node(), plug.child(0))
                    elif i == 'y':
                        return mx.Plug(v.node(), plug.child(1))
                    elif i == 'z':
                        return mx.Plug(v.node(), plug.child(2))
                except:
                    log.warning('invalid component: plug error')

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

            if isinstance(v, om.MQuaternion):
                if i == 'x' or i == 'i':
                    return v.x
                elif i == 'y' or i == 'j':
                    return v.y
                elif i == 'z' or i == 'k':
                    return v.z
                elif i == 'w' or i == 'r':
                    return v.w

            elif isinstance(v, mx.Plug):
                plug = v.plug()
                try:
                    if i == 'x' or i == 'i':
                        return mx.Plug(v.node(), plug.child(0))
                    elif i == 'y' or i == 'j':
                        return mx.Plug(v.node(), plug.child(1))
                    elif i == 'z' or i == 'k':
                        return mx.Plug(v.node(), plug.child(2))
                    elif i == 'w' or i == 'r':
                        return mx.Plug(v.node(), plug.child(3))
                except:
                    log.warning('invalid component: plug error')

            else:
                if i == 'x' or i == 'i':
                    return v[0]
                elif i == 'y' or i == 'j':
                    return v[1]
                elif i == 'z' or i == 'k':
                    return v[2]
                elif i == 'w' or i == 'r':
                    return v[3]

        # transform
        # TODO

        # euler
        # TODO

        # invalid
        log.warning('input: {}, {}'.format(type(v), v))
        raise TypeError('component: invalid input')

    def is_bool(self, v):
        if isinstance(v, bool):
            return True
        if self.is_bool_plug(v):
            return True
        return False

    def is_bool_plug(self, plug):
        if not isinstance(plug, mx.Plug):
            return False

        try:
            typ = plug.type_class()
        except:
            typ = None

        return typ == mx.Boolean

    def is_scalar(self, v):
        if isinstance(v, (int, float, bool)):
            return True
        if self.is_scalar_plug(v):
            return True
        return False

    def is_scalar_plug(self, plug):
        if not isinstance(plug, mx.Plug):
            return False

        try:
            typ = plug.type_class()
        except:
            typ = None

        if typ in (mx.Double, mx.Float, mx.Distance, mx.Angle, mx.Long, mx.Enum, mx.Boolean, mx.Time):
            return True

        try:
            v = mc.getAttr(plug.path())
            if isinstance(v, (int, float, bool)):
                return True
        except:
            pass

        return False

    def is_vector(self, v):
        if isinstance(v, (tuple, list)) and len(v) == 3:
            return all(map(self.is_scalar, v))
        if isinstance(v, (om.MVector, om.MFloatVector)):
            return True
        if self.is_vector_plug(v):
            return True
        return False

    def is_vector_plug(self, plug):
        if not isinstance(plug, mx.Plug):
            return False

        attr = plug.attribute()
        typ = attr.apiType()

        if typ in (om.MFn.kAttribute3Double, om.MFn.kAttribute3Float):
            return True
        return False

    def is_euler(self, v):
        if isinstance(v, om.MEulerRotation):
            return True
        if isinstance(v, (tuple, list)) and len(v) == 2:
            if isinstance(v[0], (tuple, list)) and len(v[0]) == 3 and all(map(self.is_scalar, v[0])):
                if v[1] in {0, 1, 2, 3, 4, 5} or (isinstance(v[1], mx.Plug) and v[1].name() == 'rotateOrder'):
                    return True
        return False

    def is_quat(self, v):
        if isinstance(v, (tuple, list)) and len(v) == 4:
            return all(map(self.is_scalar, v))
        if isinstance(v, om.MQuaternion):
            return True
        if self.is_quat_plug(v):
            return True
        return False

    def is_quat_plug(self, plug):
        if not isinstance(plug, mx.Plug):
            return False

        attr = plug.attribute()
        typ = attr.apiType()
        if typ == om.MFn.kCompoundAttribute:
            plug = plug.plug()
            if plug.numChildren() == 4:
                return True
        return False

    def is_matrix(self, v):
        if isinstance(v, om.MMatrix):
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
        if not isinstance(plug, mx.Plug):
            return False

        attr = plug.attribute()
        typ = attr.apiType()
        if typ == om.MFn.kTypedAttribute:
            typ = om.MFnTypedAttribute(attr).attrType()
            if typ == om.MFnData.kMatrix:
                return True
        elif typ == om.MFn.kMatrixAttribute:
            return True

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
        with mx.DGModifier() as md:
            node = md.create_node(mx.tChoice, name='_switch#')

        # connect
        if isinstance(s, mx.Plug):
            with mx.DGModifier() as md:
                md.connect(s, node['selector'])
        else:
            node['selector'] = s

        with mx.DGModifier() as md:
            for i, v in enumerate(inputs):
                if isinstance(v, mx.Plug):
                    md.connect(v, node['input'][i])
                else:
                    node['input'][i] = v

        return node['output']

    def value(self, v):
        if isinstance(v, mx.Plug):
            if self.is_matrix_plug(v):
                return v.as_matrix()
            else:
                return v.read()
        else:
            return v


def connect_expr(expr, **kw):
    # check keywords
    for k in kw:
        if not isinstance(kw[k], (float, int, bool, list, tuple)):
            if mc.objExists(str(kw[k])):
                kw[k] = mx.encode(str(kw[k]))

    # connect
    parser = ExpressionParser()
    return parser.eval(expr, **kw)
