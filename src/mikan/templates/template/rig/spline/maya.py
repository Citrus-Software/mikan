# coding: utf-8

from six.moves import range

from mikan.maya import om
from mikan.maya import cmds as mc
import mikan.maya.cmdx as mx

from mikan.core.logger import create_logger
from mikan.core.utils.mathutils import NurbsCurveRemap

import mikan.maya.core as mk
from mikan.maya.lib.connect import *
from mikan.maya.lib.nurbs import *
from mikan.maya.lib.rig import (
    copy_transform, orient_joint, stretch_spline_ik, create_joints_on_curve,
    axis_to_vector, get_stretch_axis, fix_inverse_scale
)

log = create_logger()


class Template(mk.Template):

    def build_template(self, data):
        number = data['number']
        bones = [self.node]

        with mx.DagModifier() as md:
            for i in range(number):
                j = md.create_node(mx.tJoint, parent=bones[-1], name='tpl_{}{}'.format(self.name, i + 2))
                bones.append(j)

        bones[0]['t'] = data['root']
        for j in bones[1:]:
            j['t'] = data['transform']

    def rename_template(self):
        chain = self.get_structure('chain')
        last = len(chain) - 1

        for i, j in enumerate(chain):
            if i == 0:
                continue
            if j.is_referenced():
                continue
            sfx = 'tip' if i == last else i + 1
            j.rename('tpl_{}_{}'.format(self.name, sfx))

    def build_rig(self):

        # init
        n_chain = self.name
        n_end = self.get_branch_suffix()

        tpl_chain = self.get_structure('chain')
        if len(tpl_chain) < 2:
            raise RuntimeError('/!\\ template chain must have at least 2 joints')

        chain, chain_sub = self.get_chain()

        num_ik = self.get_opt('iks')
        num_fk = len(tpl_chain)

        # orient chain
        ref_joints = []
        for i, tpl in enumerate(tpl_chain):
            j = mx.create_node(mx.tJoint, name='dummy_{}{}'.format(n_chain, i))
            copy_transform(tpl, j, t=True, r=True)
            if i > 0:
                mc.parent(str(j), str(ref_joints[-1]))
            ref_joints.append(j)

        if self.get_opt('orient') == 'auto':
            aim_axis = self.get_branch_opt('aim')
            up_axis = self.get_opt('up')

            up_dir = self.get_opt('up_dir')
            if up_dir == 'auto':
                up_auto = self.get_opt('up_auto')
                up_auto = {'average': 0, 'each': 1, 'first': 2, 'last': 3}[up_auto]
                orient_joint(ref_joints, aim=aim_axis, up=up_axis, up_auto=up_auto)
            else:
                up_dir = axis_to_vector(up_dir)
                orient_joint(ref_joints, aim=aim_axis, up=up_axis, up_dir=up_dir)

            # get twist axis (rotate order)
            if 'y' in aim_axis:
                bi_axis = 'z'
                if 'z' in up_axis:
                    bi_axis = 'x'
            elif 'x' in aim_axis:
                bi_axis = 'y'
                if 'y' in up_axis:
                    bi_axis = 'z'
            else:
                bi_axis = 'x'
                if 'x' in up_axis:
                    bi_axis = 'y'

        else:
            # guess axis from given chain
            _axis = get_stretch_axis(tpl_chain)
            if not _axis:
                raise RuntimeError('/!\\ cannot find orientation from template')
            aim_axis, up_axis, bi_axis = _axis
            if self.do_flip():
                aim_axis = self.branch_opt(aim_axis)
                up_axis = self.branch_opt(up_axis)

        rotate_order = self.get_opt('rotate_order')
        if rotate_order == 'auto':
            rotate_order = aim_axis[-1].lower() + up_axis[-1].lower() + bi_axis[-1].lower()

        # build nodes
        fk_joints = []
        ik_joints = []
        cvs = []

        # FK ctrls
        fk_nodes = self.build_chain(ref_joints, rotate_order=rotate_order, do_skin=False, register=False)

        # mx.delete(ref_joints)
        for j in ref_joints:
            j.add_attr(mx.Message('kill_me'))

        for i, n in enumerate(fk_nodes):
            fk_joints.append(n['sk'])
            cvs.append(n['sk'].translation(mx.sWorld))

            # register
            self.set_id(n['root'], 'roots.{}'.format(i))

            if self.get_opt('do_ctrl'):
                self.set_id(n['c'], 'ctrls.fk.{}'.format(i))
                if i < len(tpl_chain):
                    self.set_id(n['c'], 'ctrls.fk.last')

            if chain or chain_sub:
                for chain_id in chain + chain_sub:
                    self.set_id(n[chain_id], '{}s.fk.{}'.format(chain_id, i))
                    if i < len(tpl_chain):
                        self.set_id(n[chain_id], '{}s.fk.last'.format(chain_id))

            self.set_id(n['sk'], 'joints.fk.{}'.format(i))
            self.set_hook(tpl_chain[i], n['sk'], 'hooks.{}'.format(i))

        # IK ctrls
        _tpl_ik = []
        _sfx = []

        for i in range(num_ik):
            _sfx.append('IK_{}'.format(i + 1))
            _tpl_ik.append(mx.create_node(mx.tJoint, name='dummy_{}_IK{}'.format(n_chain, i)))
            if i > 0:
                mc.parent(str(_tpl_ik[-1]), str(_tpl_ik[-2]))

        ik_nodes = self.build_chain(_tpl_ik, rotate_order=rotate_order, do_skin=False, register=False, suffixes=_sfx)

        # mx.delete(_tpl_ik)
        for j in _tpl_ik:
            j.add_attr(mx.Message('kill_me'))

        for i, n in enumerate(ik_nodes):
            ik_joints.append(n['sk'])

            # register
            self.set_id(n['root'], 'roots.ik.{}'.format(i))

            if self.get_opt('do_ctrl'):
                self.set_id(n['c'], 'ctrls.ik.{}'.format(i))

            if chain or chain_sub:
                for chain_id in chain + chain_sub:
                    self.set_id(n[chain_id], '{}s.ik.{}'.format(chain_id, i))

            self.set_id(n['sk'], 'joints.ik.{}'.format(i))

        # switch
        root_switch = mx.create_node(mx.tTransform, parent=fk_nodes[0]['root'], name='root_' + self.name + '_switch' + n_end)
        mc.reorder(str(root_switch), front=1)

        root_switch['v'] = False
        for attr in ['t', 'r', 's', 'v']:
            root_switch[attr].lock()

        c_switch = mk.Control.create_control_shape(root_switch, n='c_' + self.name + '_switch' + n_end)
        self.set_id(c_switch, 'ctrls.switch')

        for n in fk_nodes:
            mk.Control.set_control_shape(c_switch, n['c'])
        for n in ik_nodes:
            mk.Control.set_control_shape(c_switch, n['c'])

        # splines
        d = 3
        if num_fk < 4:
            d = num_fk - 1
        cv_fk = mc.curve(d=d, p=cvs, n='cv_{}_fk{}'.format(self.name, n_end))
        cv_fk = mx.encode(cv_fk)
        mc.parent(str(cv_fk), str(fk_nodes[0]['root']))

        cv_ik = mc.curve(d=d, p=cvs, n='cv_{}_ik{}'.format(self.name, n_end))
        cv_ik = mx.encode(cv_ik)
        mc.makeIdentity(str(cv_fk), str(cv_ik), a=1)

        mc.parent(str(cv_ik), str(fk_nodes[0]['root']))
        mc.rebuildCurve(str(cv_ik), s=num_ik * 2 - 3)

        self.set_id(cv_fk, 'curve.fk')
        self.set_id(cv_ik, 'curve.ik')

        u_fk = []
        for i in range(num_fk):
            u = get_closest_point_on_curve(cv_fk, fk_joints[i], parameter=1)
            u_fk.append(u)

        # secondary spline up
        remap = NurbsCurveRemap(num_fk, degree=d)
        do_flip = self.do_flip()

        up_vectors = []
        for fk in fk_nodes:
            m = fk['c']['wm'][0].as_matrix()
            up_vectors.append(axis_to_vector(up_axis) * m)

        fn = om.MFnNurbsCurve(cv_ik.dag_path())
        cvs = [mx.Vector(cv) for cv in fn.cvPositions(space=mx.sWorld)]

        for i in range(fn.numCVs):
            v = mx.Vector()

            _u = get_closest_point_on_curve(cv_ik, cvs[i], parameter=True)

            weights = remap.get(_u / fn.knotDomain[1])
            for j, w in enumerate(weights):
                v += w * up_vectors[j]

            v.normalize()
            v *= fn.length() / 2
            if do_flip:
                v *= -1

            cvs[i] += v

        cv_up = mc.curve(d=fn.degree, p=cvs, n='cv_{}_up{}'.format(self.name, n_end))
        cv_up = mx.encode(cv_up)
        mc.parent(str(cv_up), str(fk_nodes[0]['root']))
        cv_up['v'] = False

        # intermediate IK control root
        c_switch.add_attr(mx.Double('uniform_ik', keyable=True, min=0, max=1))
        c_switch['uniform_ik'] = self.get_opt('uniform_ik')

        cvs_pos = [mx.Vector(cv) for cv in fn.cvPositions(space=mx.sWorld)]

        for i in range(num_ik):
            pos = (cvs_pos[(i - 1) * 2 + 2] + cvs_pos[(i - 1) * 2 + 3]) / 2
            u = get_closest_point_on_curve(cv_fk, pos, parameter=1)
            d0 = get_curve_length(cv_fk)

            fk = 0
            for _fk, _u in enumerate(u_fk):
                if u >= _u:
                    fk = _fk
            root = ik_nodes[i]['root']
            mc.parent(str(root), str(fk_joints[fk]), r=1)
            fk_joints[fk]['scale'] >> root['inverseScale']

            poc = mx.create_node(mx.tPointOnCurveInfo, name='_poc')
            cv_fk.shape()['local'] >> poc['inputCurve']

            if i == 0:
                poc['parameter'] = 0
                poc['top'] = True
            elif i == num_ik - 1:
                poc['parameter'] = 1
                poc['top'] = True
            else:
                mp = mx.create_node(mx.tMotionPath, name='_path#')
                mp['fractionMode'] = 1
                d = get_curve_length_from_param(cv_fk, u)
                mp['uValue'] = d / d0
                cv_fk.shape()['local'] >> mp['geometryPath']

                npc = mx.create_node(mx.tNearestPointOnCurve, name='_ucoord#')
                cv_fk.shape()['local'] >> npc['inputCurve']
                mp['allCoordinates'] >> npc['inPosition']

                connect_expr(
                    'poc = lerp(u, npc, w)',
                    poc=poc['parameter'], u=u, npc=npc['parameter'], w=c_switch['uniform_ik']
                )

            p = mx.create_node(mx.tTransform, parent=fk_nodes[0]['root'], name='p_{}_ik{}{}'.format(self.name, i, n_end))
            poc['p'] >> p['t']
            mc.pointConstraint(str(p), str(root))

            aim = mx.create_node(mx.tTransform, parent=p, name='aim_{}_ik{}{}'.format(self.name, i, n_end))
            poc['t'] >> aim['t']

            mc.aimConstraint(str(aim), str(root), aim=axis_to_vector(aim_axis), wut='none')

        # bpm
        bpm_root = mx.create_node(mx.tTransform, parent=fk_nodes[0]['root'], name='bpm_{}'.format(self.name))
        bpm_root['v'] = False

        fk_bpm = []
        for i, j in enumerate(fk_joints):
            bpm = mx.create_node(mx.tJoint, parent=bpm_root, name='bpm_{}_fk{}'.format(self.name, i))
            copy_transform(j, bpm, t=True, r=True)
            fk_bpm.append(bpm)

        ik_bpm = []
        for i, j in enumerate(ik_joints):
            bpm = mx.create_node(mx.tJoint, parent=bpm_root, name='bpm_{}_ik{}'.format(self.name, i))
            copy_transform(j, bpm, t=True, r=True)
            ik_bpm.append(bpm)

        # skin fk
        fk_maps = []
        for i in range(num_fk):
            fk_maps.append(mk.WeightMap([0] * num_fk))
            fk_maps[i][i] = 1

        fk_easing = self.get_opt('fk_easing')
        if fk_easing in ['in', 'in-out']:
            fk_maps[0][1] = 1
            fk_maps[1][1] = 0
        if fk_easing in ['out', 'in-out']:
            fk_maps[-1][num_fk - 2] = 1
            fk_maps[num_fk - 2][num_fk - 2] = 0

        skin_data = {
            'deformer': 'skin',
            'transform': cv_fk,
            'data': {
                'infs': dict(zip(range(num_fk), fk_joints)),
                'maps': dict(zip(range(num_fk), fk_maps)),
                'bind_pose': dict(zip(range(num_fk), fk_bpm))
            }
        }
        skin_dfm = mk.Deformer(**skin_data)
        skin_dfm.build()
        skin_dfm.set_protected(True)
        skin_fk = skin_dfm.node
        cv_fk['wm'][0] >> skin_fk['geomMatrix']

        # skin ik
        ik_maps = create_curve_weightmaps(cv_ik, ik_joints)

        skin_data = {
            'deformer': 'skin',
            'transform': cv_ik,
            'data': {
                'infs': dict(zip(range(num_ik), ik_joints)),
                'maps': dict(zip(range(num_ik), ik_maps)),
                'bind_pose': dict(zip(range(num_ik), ik_bpm))
            }
        }
        skin_dfm = mk.Deformer(**skin_data)
        skin_dfm.normalize()
        skin_dfm.build()
        skin_dfm.set_protected(True)
        skin_ik = skin_dfm.node
        cv_ik['wm'][0] >> skin_ik['geomMatrix']

        # skin up
        skin_data = {
            'deformer': 'skin',
            'transform': cv_up,
            'data': {
                'infs': dict(zip(range(num_ik), ik_joints)),
                'maps': dict(zip(range(num_ik), ik_maps)),
                'bind_pose': dict(zip(range(num_ik), ik_bpm))
            }
        }
        skin_dfm = mk.Deformer(**skin_data)
        skin_dfm.normalize()
        skin_dfm.build()
        skin_dfm.set_protected(True)
        skin_up = skin_dfm.node
        cv_up['wm'][0] >> skin_up['geomMatrix']

        # spline IK
        num_sk = self.get_opt('bones')
        bone_length = self.get_opt('bones_length')
        ik_chain = create_joints_on_curve(cv_fk, num_sk, mode=bone_length, name='ik_{n}{{i}}{e}'.format(n=self.name, e=n_end))
        mc.parent(str(ik_chain[0]), str(ik_joints[0]))

        for i, j in enumerate(ik_chain):
            self.set_id(j, 'chain.{}'.format(i))

        up_dir = self.get_opt('up_dir')
        if up_dir == 'auto':
            orient_joint(ik_chain, aim=aim_axis, up=up_axis, up_auto=1)
        else:
            up_dir = axis_to_vector(up_dir)
            orient_joint(ik_chain, aim=aim_axis, up=up_axis, up_dir=up_dir)

        ik_handle = stretch_spline_ik(cv_ik, ik_chain)
        mc.parent(str(ik_handle), str(fk_nodes[0]['root']), r=1)

        c_switch.addAttr(mx.Double('stretch', keyable=True, min=0, max=1))
        c_switch.addAttr(mx.Double('squash', keyable=True, min=0, max=1))
        c_switch.addAttr(mx.Double('slide', keyable=True, min=-1, max=1))
        c_switch['stretch'] >> cv_ik['stretch']
        c_switch['squash'] >> cv_ik['squash']
        c_switch['slide'] >> cv_ik['slide']
        if self.get_opt('default_stretch'):
            c_switch['stretch'] = 1

        # skin joints
        do_skin = self.get_opt('do_skin') and self.get_opt('tweakers') == 'off'
        pfx = 'sk_'
        if not do_skin:
            pfx = 'j_'

        sk_chain = []
        for i, ik in enumerate(ik_chain):
            j = mx.create_node(mx.tJoint, parent=ik, name=str(ik).replace('ik_', pfx))
            sk = j

            if do_skin:
                self.set_id(sk, 'skin.{}'.format(i))
            self.set_id(j, 'j.{}'.format(i))

            sk_chain.append(j)
            ik['s'] >> sk_chain[-1]['inverseScale']
            mc.reorder(str(sk_chain[i]), front=1)
            if i < len(ik_chain) - 1:
                _j = mx.create_node(mx.tJoint, parent=ik_chain[i + 1], name=str(ik).replace('ik_', 'end_'))
                mc.parent(str(_j), str(sk_chain[-1]))

        # -- scale
        skx = []
        skz = []
        for sk in sk_chain:
            skx.append(sk['s' + up_axis[-1]])
            skz.append(sk['s' + bi_axis[-1]])

        bwx = blend_smooth_remap([c['s' + up_axis[-1]] for c in [n['c'] for n in fk_nodes]], skx)
        bwz = blend_smooth_remap([c['s' + bi_axis[-1]] for c in [n['c'] for n in fk_nodes]], skz)

        for i, ik in enumerate(ik_chain):
            if 'squash' in ik:
                connect_mult(ik['squash'], bwx[i]['o'], sk_chain[i]['sx'])
                connect_mult(ik['squash'], bwz[i]['o'], sk_chain[i]['sz'])

            sk_chain[i]['ssc'] = False

        # -- scale last?
        # TODO: ajouter simplement l'option
        # c_spineIK.sy >> sk_spine[-1].sy

        # base twist spline IK
        c_switch.addAttr(mx.Double('twist', keyable=True))

        ik_handle['dTwistControlEnable'] = True

        if 'dForwardAxis' in ik_handle:
            ik_handle['dWorldUpType'] = 4  # obj rotation up start/end
            _axis = {'x': 0, '+x': 0, '-x': 1, 'y': 2, '+y': 2, '-y': 3, 'z': 4, '+z': 4, '-z': 5}
            _axis_up = {'y': 0, '+y': 0, '-y': 1, 'z': 3, '+z': 3, '-z': 4, 'x': 6, '+x': 6, '-x': 7}
            ik_handle['dForwardAxis'] = _axis[aim_axis]
            ik_handle['dWorldUpAxis'] = _axis_up[up_axis]
            ik_handle['dWorldUpVector'] = axis_to_vector(up_axis)
            ik_handle['dWorldUpVectorEnd'] = axis_to_vector(up_axis)
            ik_handle['dTwistValueType'] = 1  # start/end
        else:
            # maya 2015 caca
            ik_handle['dWorldUpType'] = 7  # relative
            ik_handle['dTwistValueType'] = 0
            if 'z' not in aim_axis:
                ik_handle['dWorldUpAxis'] = 3
            else:
                ik_handle['dWorldUpAxis'] = 0

        ik_joints[0]['wm'][0] >> ik_handle['dWorldUpMatrix']
        ik_joints[-1]['wm'][0] >> ik_handle['dWorldUpMatrixEnd']

        if self.do_flip():
            c_switch['twist'] >> ik_handle['dTwistEnd']
        else:
            connect_mult(c_switch['twist'], -1, ik_handle['dTwistEnd'])

        # -- ik secondary up
        fn_ik = om.MFnNurbsCurve(cv_ik.dag_path())
        fn_up = om.MFnNurbsCurve(cv_up.dag_path())
        _fup = fn_up.knotDomain[1] / fn_ik.knotDomain[1]

        up_locs = []
        for i, ik in enumerate(ik_chain):
            mmx = mx.create_node(mx.tMultMatrix, name='_mmx#')
            dmx = mx.create_node(mx.tDecomposeMatrix, name='_dmx#')
            npc = mx.create_node(mx.tNearestPointOnCurve, name='_closest#')
            poc = mx.create_node(mx.tPointOnCurveInfo, name='_poc')

            ik['wm'][0] >> mmx['i'][0]
            cv_ik['wim'][0] >> mmx['i'][1]
            mmx['o'] >> dmx['imat']

            cv_ik.shape()['local'] >> npc['inputCurve']
            cv_up.shape()['local'] >> poc['inputCurve']

            dmx['outputTranslate'] >> npc['inPosition']
            # npc['parameter'] >> poc['parameter']
            connect_mult(npc['parameter'], _fup, poc['parameter'])

            loc = mx.create_node(mx.tTransform, parent=cv_up, name='loc_{}_up#'.format(n_chain))
            # loc['displayScalePivot'] = True
            poc['position'] >> loc['t']

            up_locs.append(loc)

        # -- ik twist
        _up = axis_to_vector(up_axis)
        if do_flip:
            _up *= -1

        for i, sk in enumerate(sk_chain):
            target_aim = axis_to_vector(aim_axis)

            if i < len(ik_chain) - 1:
                target = ik_chain[i + 1]
            else:
                target = ik_chain[i - 1]
                target_aim *= -1

            _aim = mc.aimConstraint(str(target), str(sk), aim=target_aim, u=_up, wut='object', wuo=str(up_locs[i]), skip=[up_axis[-1], bi_axis[-1]])

            sk['ro'] = mx.Euler.orders[rotate_order]

        # orient last
        _aim = mx.encode(_aim[0])
        last_aim = sk_chain[-1]['r' + aim_axis[-1]].input(plug=True)
        last_aim // sk_chain[-1]['r' + aim_axis[-1]]

        _ox = mc.orientConstraint(str(ik_joints[-1]), str(sk_chain[-1]), mo=1)
        _ox = mx.encode(_ox[0])

        blend = mx.create_node(mx.tPairBlend, name='_pb#')
        for dim in 'xyz':
            plug = sk_chain[-1]['r' + dim]
            blend['ir' + dim + '2'] = plug
            plug_input = plug.input(plug=True)
            if plug_input.node().is_a(mx.tUnitConversion):
                plug_input = plug_input.node()['input'].input(plug=True)
            plug_input >> blend['ir' + dim + '2']
            plug.disconnect(destination=False)
            blend['or' + dim] >> plug

        last_aim >> blend['ir' + aim_axis[-1] + '1']

        c_switch['stretch'] >> blend['weight']

        # additional twist
        sky = []
        for sk in sk_chain:
            sky.append(sk['r' + aim_axis[-1]])

        c_switch.addAttr(mx.Double('twist_offset_base', keyable=True))
        c_switch.addAttr(mx.Double('twist_offset_tip', keyable=True))

        ctrls = [c_switch['twist_offset_base']] + [None] * len(ik_joints[1:-1]) + [c_switch['twist_offset_tip']]
        bws = blend_smooth_remap(ctrls, sky, connect=False)

        for i, bw in enumerate(bws):
            twf = float(i) / (len(bws) - 1)
            tw = connect_mult(c_switch['twist'], -twf)

            connect_expr('y = sky + o + tw', y=sky[i], sky=sky[i].input(plug=True), o=bw['o'], tw=tw)

        # tweakers
        do_tweakers = self.get_opt('tweakers')
        if do_tweakers != 'off':
            chained = do_tweakers == 'chained'

            tweakers = []

            parent = ik_nodes[0]['j']
            offsets = [ik_nodes[0]['j']] + sk_chain

            for i, j in enumerate(sk_chain):
                offset = offsets[i]
                if not chained:
                    offset = offsets[0]

                mmx = mx.create_node(mx.tMultMatrix, name='_mmx#')
                j['wm'][0] >> mmx['i'][0]
                offset['wim'][0] >> mmx['i'][1]

                root = mx.create_node(mx.tJoint, parent=parent, name='root_' + n_chain + '_tweaker' + str(i + 1))
                c = mx.create_node(mx.tJoint, parent=root, name='c_' + n_chain + '_tweaker' + str(i + 1))
                root['drawStyle'] = 2
                c['drawStyle'] = 2

                connect_matrix(mmx['o'], root)
                if chained:
                    parent = c

                sk = mx.create_node(mx.tJoint, parent=c, name='sk_' + n_chain + str(i + 1))
                if i < len(offsets) - 2:
                    end = mx.create_node(mx.tJoint, parent=sk, name='end_' + n_chain + str(i + 1))
                    copy_transform(offsets[i + 2], end)

                tweaker = {}
                tweaker['root'] = root
                tweaker['c'] = c
                tweaker['sk'] = sk
                tweakers.append(tweaker)

            for i, tweaker in enumerate(tweakers):
                self.set_id(tweaker['root'], 'roots.tweaker.{}'.format(i))
                self.set_id(tweaker['c'], 'ctrls.tweaker.{}'.format(i))
                self.set_id(tweaker['sk'], 'skin.{}'.format(i))

        # cleanup
        fix_inverse_scale(list(fk_nodes[0]['root'].descendents(type=mx.tJoint)))
