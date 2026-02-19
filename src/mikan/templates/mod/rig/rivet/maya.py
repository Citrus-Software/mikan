# coding: utf-8

from mikan.maya import om
from mikan.maya import cmds as mc
import mikan.maya.cmdx as mx

import mikan.maya.core as mk
from mikan.core.logger import create_logger
from mikan.core import cleanup_str

from mikan.maya.lib.connect import connect_matrix, connect_expr, connect_reverse

log = create_logger()


class Mod(mk.Mod):

    def run(self):
        # args
        node = self.data.get('node', self.node)
        parent = self.data.get('parent', node.parent())
        do_hook = bool(self.data.get('hook', True))

        closest_node = self.data.get('closest')
        do_closest = bool(closest_node)
        if do_closest and not isinstance(closest_node, mx.Node):
            closest_node = node
            do_hook = False
        if do_closest and not isinstance(closest_node, mx.DagNode):
            raise mk.ModArgumentError('invalid closest node')

        keepout_node = self.data.get('keepout')
        do_keepout = bool(keepout_node)
        if do_keepout and not isinstance(keepout_node, mx.Node):
            keepout_node = node
            do_hook = False
        if do_keepout and not isinstance(keepout_node, mx.DagNode):
            raise mk.ModArgumentError('invalid keepout node')

        if do_keepout:
            do_closest = True
            closest_node = keepout_node

        default_orient = True
        if do_closest:
            default_orient = False
        do_orient = self.data.get('orient', self.data.get('orient', default_orient))

        if 'geo' not in self.data:
            raise mk.ModArgumentError('geometry not defined')

        shp, xfo = self.data['geo']
        shp_output = mk.Deformer.get_deformer_output(shp, xfo)

        xfo_scale = xfo['s'].read()
        for x in range(3):
            if round(xfo_scale[x], 3) != 1:
                self.log_warning('geometry scale is not frozen')
                break

        do_subdiv = 0
        if 'subdiv' in self.data:
            do_subdiv = self.data['subdiv']
            do_subdiv = do_subdiv if isinstance(do_subdiv, int) else int(bool(do_subdiv))

        # connect subdiv
        if do_subdiv:
            subdiv = None
            for s in shp.outputs(type=mx.tPolySmoothFace):
                if s['divisions'].read() == do_subdiv:
                    subdiv = s
                    break
            if subdiv is None:
                with mx.DGModifier() as md:
                    subdiv = md.create_node(mx.tPolySmoothFace)
                subdiv['divisions'] = do_subdiv
                subdiv['keepBorder'] = False
                subdiv['smoothUVs'] = True

            shp_output >> subdiv['inputPolymesh']
            shp_output = subdiv['output']
            mc.setAttr(str(subdiv) + '.ics', 1, 'f[*]', type='componentList')

        # build
        name = 'rvt_{}'.format(xfo)
        if 'name' in self.data:
            name += '_' + cleanup_str(self.data['name'])
        else:
            tpl = self.get_template()
            if tpl:
                name += '_' + tpl.name
            else:
                name += '_' + node.name()

        with mx.DagModifier() as md:
            rvt = md.create_node(mx.tTransform, parent=parent, name=name)

        # add subdiv level attribute
        if do_subdiv:
            with mx.DagModifier() as md:
                md.add_attr(rvt, mx.Long('level', min=0, max=3, keyable=True))
            with mx.DagModifier() as md:
                md.set_attr(rvt['level'], subdiv['divisions'].read())

            input_level = subdiv['divisions'].input(plug=True)
            if isinstance(input_level, mx.Plug):
                connect_expr('level = max(a, b)', level=subdiv['divisions'], a=rvt['level'], b=input_level)
            else:
                with mx.DGModifier() as md:
                    md.connect(rvt['level'], subdiv['divisions'])

        # connect
        if do_closest:
            with mx.DGModifier() as md:
                _cp = md.create_node(mx.tClosestPointOnMesh, name='_closest#')

            xfo['worldMatrix'][0] >> _cp['inputMatrix']
            shp_output >> _cp['inMesh']

            if 'raycast' not in self.data:
                with mx.DGModifier() as md:
                    _dmx = md.create_node(mx.tDecomposeMatrix, name='_dmx#')
                closest_node['worldMatrix'][0] >> _dmx['inputMatrix']
                _dmx['outputTranslate'] >> _cp['inPosition']
            else:
                # TODO: remove, je sais même plus pourquoi y'a ça
                _cp['inPosition'] = self.data['raycast']

            # closest output
            with mx.DGModifier() as md:
                _cmx = md.create_node(mx.tComposeMatrix, name='_cmx#')
                _mmx = md.create_node(mx.tMultMatrix, name='_mmx#')

            _cp['position'] >> _cmx['inputTranslate']
            if do_orient:
                # aim node (parent space)
                with mx.DagModifier() as md:
                    _aim = md.create_node(mx.tAimConstraint, parent=rvt, name='_aim#')
                rvt['pim'][0] >> _aim['constraintParentInverseMatrix']

                _aim['worldUpType'] = 4  # None
                # TODO: normal vector axis
                _aim['aimVector'] = (0, 1, 0)
                _aim['upVector'] = (0, 0, 0)

                # aim origin (parent space)
                with mx.DGModifier() as md:
                    _cmx_p = md.create_node(mx.tComposeMatrix, name='_cmx#')
                    _mmx_p = md.create_node(mx.tMultMatrix, name='_mmx#')
                    _dmx_p = md.create_node(mx.tDecomposeMatrix, name='_dmx#')

                _cp['position'] >> _cmx_p['inputTranslate']

                _cmx_p['outputMatrix'] >> _mmx_p['i'][0]
                rvt['pim'][0] >> _mmx_p['i'][1]
                _mmx_p['o'] >> _dmx_p['imat']
                _dmx_p['outputTranslate'] >> _aim['constraintTranslate']

                # aim target (world space)
                with mx.DGModifier() as md:
                    _vector = md.create_node(mx.tPlusMinusAverage, name='_vector#')
                _cp['position'] >> _vector['input3D'][0]
                _cp['normal'] >> _vector['input3D'][1]

                with mx.DGModifier() as md:
                    _cmx_up = md.create_node(mx.tComposeMatrix, name='_cmx#')
                    _dmx_up = md.create_node(mx.tDecomposeMatrix, name='_dmx#')

                _vector['output3D'] >> _cmx_up['inputTranslate']
                _cmx_up['outputMatrix'] >> _dmx_up['imat']
                _dmx_up['outputTranslate'] >> _aim['target'][0]['targetTranslate']

            _cmx['outputMatrix'] >> _mmx['i'][0]
            rvt['pim'][0] >> _mmx['i'][1]

            xfo_out = _mmx['o']

            # keepout mode
            if do_keepout:
                with mx.DGModifier() as md:
                    _vector = md.create_node(mx.tPlusMinusAverage, name='_vector#')
                    _dot = md.create_node(mx.tVectorProduct, name='_dot#')
                    _blend = md.create_node(mx.tWtAddMatrix, name='_blend#')
                    _mmx = md.create_node(mx.tMultMatrix, name='_mmx#')

                _dmx['outputTranslate'] >> _vector['input3D'][0]
                _cp['position'] >> _vector['input3D'][1]

                _vector['op'] = 2  # sub
                _vector['output3D'] >> _dot['input1']
                _cp['normal'] >> _dot['input2']

                closest_node['worldMatrix'][0] >> _mmx['i'][0]
                rvt['pim'][0] >> _mmx['i'][1]
                _mmx['o'] >> _blend['i'][0]['m']

                xfo_out >> _blend['i'][1]['m']

                _dot = connect_expr('dot >= 0 ? 1 : 0', dot=_dot['outputX'])
                _dot >> _blend['i'][0]['w']
                connect_reverse(_dot, _blend['i'][1]['w'])

                xfo_out = _blend['o']

            if do_orient:
                _aim['constraintRotate'] >> rvt['r']
            connect_matrix(xfo_out, rvt, r=False, s=False, sh=False)

        else:
            with mx.DGModifier() as md:
                _cp = md.create_node(mx.tClosestPointOnMesh, name='_closest#')
            _cp['inPosition'] = node.translation(mx.sWorld)
            mc.connectAttr(shp_output.path(), _cp['inMesh'].path(), f=1)
            xfo['wm'][0] >> _cp['inputMatrix']
            f = _cp['closestFaceIndex'].read()
            v = _cp['closestVertexIndex'].read()
            cp = _cp['position'].read()

            _cp['inMesh'].disconnect()

            _cp.add_attr(mx.Message('kill_me'))
            if not self.modes:
                mx.delete(_cp)

            # coords
            is_deformer = not shp_output.node().is_a(mx.tMesh)

            if is_deformer:
                with mx.DagModifier() as md:
                    _geo = md.create_node(mx.tTransform, name='_mesh')
                    _msh = md.create_node(mx.tMesh, parent=_geo)
                mc.connectAttr(shp_output.path(), _msh['inMesh'].path(), f=1)
            else:
                _msh = shp

            it = om.MItMeshPolygon(_msh.object())
            it.setIndex(f)
            fe = list(it.getEdges())

            it = om.MItMeshVertex(_msh.object())
            it.setIndex(v)
            ve = list(it.getConnectedEdges())

            ce = list(set(ve).intersection(set(fe)))  # first 2 closest edges
            it = om.MItMeshEdge(_msh.object())
            it.setIndex(ce[0])
            cv0 = [it.vertexId(0), it.vertexId(1)]
            it.setIndex(ce[1])
            cv1 = [it.vertexId(0), it.vertexId(1)]

            cv = set(cv0).intersection(set(cv1))
            if cv:
                cv = list(cv)[0]
                if cv0[1] == cv:
                    cv0.reverse()
                if cv1[1] == cv:
                    cv1.reverse()

            if is_deformer:
                _msh['inMesh'].disconnect()
                _geo.add_attr(mx.Message('kill_me'))
                if not self.modes:
                    mx.delete(_geo)

            # rivet
            with mx.DGModifier() as md:
                e0 = md.create_node(mx.tPolyEdgeToCurve)
                e1 = md.create_node(mx.tPolyEdgeToCurve)
                loft = md.create_node(mx.tLoft)
                cpos = md.create_node(mx.tClosestPointOnSurface, name='_cpos#')
                psi = md.create_node(mx.tPointOnSurfaceInfo, name='_pos#')
                ffm = md.create_node(mx.tFourByFourMatrix, name='_mx#')
                add = md.create_node(mx.tPlusMinusAverage, name='_add#')
                vp = md.create_node(mx.tVectorProduct, name='_cross#')

            mc.connectAttr(shp_output.path(), e0['inputPolymesh'].path())
            mc.setAttr(e0['inputComponents'].path(), 2, *['vtx[{}]'.format(v) for v in cv0], type='componentList')

            mc.connectAttr(shp_output.path(), e1['inputPolymesh'].path())
            mc.setAttr(e1['inputComponents'].path(), 2, *['vtx[{}]'.format(v) for v in cv1], type='componentList')

            xfo['wm'][0] >> e0['inputMat']
            xfo['wm'][0] >> e1['inputMat']

            e0['outputcurve'] >> loft['inputCurve'][0]
            e1['outputcurve'] >> loft['inputCurve'][1]

            loft['outputSurface'] >> cpos['inputSurface']
            cpos['ip'] = cp

            loft['outputSurface'] >> psi['inputSurface']
            psi['u'] = cpos['u']
            psi['v'] = cpos['v']

            cpos.add_attr(mx.Message('kill_me'))
            if not self.modes:
                mx.delete(cpos)

            psi['ntu'] >> add['input3D'][0]
            psi['ntv'] >> add['input3D'][1]
            # y'a pas de normalisation mais finalament osef

            psi['nn'] >> vp['input1']
            add['output3D'] >> vp['input2']
            vp['op'] = 2  # cross
            vp['normalizeOutput'] = True

            psi['nnx'] >> ffm['in10']
            psi['nny'] >> ffm['in11']
            psi['nnz'] >> ffm['in12']
            add['output3Dx'] >> ffm['in00']
            add['output3Dy'] >> ffm['in01']
            add['output3Dz'] >> ffm['in02']
            vp['outputX'] >> ffm['in20']
            vp['outputY'] >> ffm['in21']
            vp['outputZ'] >> ffm['in22']
            psi['px'] >> ffm['in30']
            psi['py'] >> ffm['in31']
            psi['pz'] >> ffm['in32']

            # hook to geom
            with mx.DGModifier() as md:
                _mmx1 = md.create_node(mx.tMultMatrix, name='_mmx')
                _mmx2 = md.create_node(mx.tMultMatrix, name='_mmx')

            ffm['output'] >> _mmx1['i'][0]
            xfo['wim'][0] >> _mmx1['i'][1]

            _mmx1['o'] >> _mmx2['i'][0]
            xfo['wm'][0] >> _mmx2['i'][1]
            rvt['pim'][0] >> _mmx2['i'][2]

            # connect to xfo
            connect_matrix(_mmx2['o'], rvt, r=do_orient, s=False, sh=False)

        # hook
        if do_hook:
            mc.parent(str(node), str(rvt))

        # register
        self.set_id(rvt, 'rivet', self.data.get('name'))
