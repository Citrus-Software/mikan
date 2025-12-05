# coding: utf-8

from fnmatch import fnmatch
from six import string_types

import maya.api.OpenMaya as om
import maya.api.OpenMayaAnim as oma
import maya.mel
import maya.cmds as mc
from mikan.maya import cmdx as mx

from ..core.node import Nodes
from mikan.core.logger import create_logger, timed_code

__all__ = [
    'cleanup_references', 'get_references', 'import_references',
    'cleanup_ref_edits', 'cleanup_layers',

    'cleanup_rig_ctrls', 'cleanup_rig_history', 'cleanup_rig_joints',
    'cleanup_rig_shapes', 'cleanup_shape_orig',
    'rename_skin_clusters', 'cleanup_skin_clusters', 'label_skin_joints',
]

log = create_logger(name='mikan.cleanup')


# references -------------------------------------------------------------------

def cleanup_references(**kw):
    for ref in mx.ls(et='reference'):
        if 'sharedReferenceNode' in ref.name():
            continue
        fn = om.MFnReference(ref.object())
        try:
            ns = fn.associatedNamespace(True)
            name = '{}RN'.format(ns)
            if ref.name() != name:
                ref.lock(False)
                ref.rename(name)
                ref.lock()
        except:
            log.warning('failed to rename reference node "{}"'.format(ref))
            continue

        try:
            if fn.isLoaded() or bool(kw.get('all')):
                mc.file(cleanReference=str(ref))

            log.info('cleanup reference "{}"'.format(ref))
        except:
            continue

        mc.fileInfo('ref_{}'.format(ns), ns)


def get_references():
    refs = []
    for ref in mx.ls(et='reference'):
        if ref.is_referenced():
            continue
        fn = om.MFnReference(ref.object())
        try:
            fn.isLoaded()
            refs.append(ref)
        except:
            pass
    return refs


def import_references():
    refs = get_references()
    while len(refs):
        for ref in refs:
            if not ref.exists:
                continue
            ref_name = str(ref)
            mc.file(cleanReference=str(ref))
            mc.file(referenceNode=str(ref), importReference=True)
            log.info('imported content of "{}"'.format(ref_name))
        refs = get_references()

    for ref_node in mx.ls(et='reference'):
        ref_node.lock(False)
        mx.delete(ref_node)


def cleanup_ref_edits(ns, match_strs, rm=True, reverse=False):
    ref = None

    # find by namespace
    for ref_node in mx.ls(et='reference'):
        try:
            if mc.referenceQuery(str(ref_node), namespace=True).strip(':') == ns.strip(':'):
                ref = ref_node
                break
        except:
            pass

    if not ref and mc.objExists(str(ns)):
        ref = mc.referenceQuery(str(ns), referenceNode=True)

    if not ref:
        raise RuntimeError('/!\\ cannot find reference from "{}"'.format(ns))

    # cleanup ref ?
    fn = om.MFnReference(ref.object())

    do_reload = False
    if fn.isLoaded() and rm:
        mc.file(unloadReference=str(ref))
        do_reload = True

    if isinstance(match_strs, string_types):
        match_strs = [match_strs]

    edits = mc.referenceQuery(editStrings=True, onReferenceNode=str(ref))
    match_edits = []

    for edit in edits:
        e = edit.split()
        target = e[1]
        if e[0] == 'addAttr':
            target = e[-1]
        if e[0] == 'parent':
            target = e[-2]
        if e[0] == 'disconnectAttr':
            target = e[-2]
        target = target.strip('\"')

        snipe = False
        if not reverse:
            for match_str in match_strs:
                match_str = '*{}*'.format(match_str)
                if fnmatch(edit, match_str):
                    snipe = True
                    break
        else:
            snipe = True
            for match_str in match_strs:
                match_str = '*{}*'.format(match_str)
                if fnmatch(edit, match_str):
                    snipe = False

        if snipe:
            if rm:
                mc.referenceEdit(target, editCommand=e[0], r=1, fld=1, scs=1)
                log.info('removed: {}'.format(edit))
            else:
                match_edits.append(edit)
                log.debug('found: {}'.format(edit))

    if do_reload:
        mc.file(loadReference=str(ref))

    if not rm:
        return match_edits


# scene ------------------------------------------------------------------------

def cleanup_layers():
    for layer in mc.ls(et='displayLayer'):
        if layer in {'defaultLayer', 'defaultRenderLayer'}:
            continue

        try:
            name = str(layer)
            mc.delete(layer)
            log.info(u'display layer "{}" deleted'.format(name))
        except:
            log.info(u'/!\\ failed to delete display layer "{}"'.format(name))

    # cleanup default layer
    layer = mx.encode('defaultLayer')
    for c_out, c_in in layer.outputs(plugs=True, connections=True):
        c_out // c_in


# rig --------------------------------------------------------------------------

def cleanup_rig_ctrls(release=False, monitor=None):
    log = create_logger(name='mikan')

    ctrls = Nodes.get_id('*::ctrls')
    if not ctrls:
        return

    # detect duplicated names
    ctrl_names = {}
    for ctrl in ctrls:
        name = ctrl.name(namespace=False)
        if name not in ctrl_names:
            ctrl_names[name] = 1
        else:
            ctrl_names[name] += 1

    for name in ctrl_names:
        if ctrl_names[name] > 1:
            log.warning('/!\\ multiple controllers named "{}" detected'.format(name))
            if monitor:
                monitor.warnings += 1

    # cleanup srt
    try:
        mx.cmd(mc.mute, ctrls, f=1, d=1)
    except:
        pass

    for ctrl in ctrls:
        # remove anim curve
        acv = []
        acv += ctrl.inputs(type='animCurveTL')
        acv += ctrl.inputs(type='animCurveTU')
        acv += ctrl.inputs(type='animCurveTA')
        if acv:
            mx.delete(acv)

        # remove blendParent attributes
        for attr in mc.listAttr(str(ctrl), st='blendParent*') or []:
            ctrl.delete_attr(attr)

        # cleanup joints
        if ctrl.is_a(mx.tJoint):
            ctrl['radius'].channel_box = False

        # secure locked attrs
        for attr in mc.listAttr(str(ctrl), keyable=1) or []:
            attr = ctrl[attr]
            if not attr.editable or attr.locked:
                attr.keyable = False
                attr.channel_box = True

        if ctrl.is_a(mx.kTransform):
            # set transform to 0
            for attr in ['tx', 'ty', 'tz', 'rx', 'ry', 'rz']:
                attr = ctrl[attr]
                if attr.keyable:
                    v = attr.read()
                    if -.001 < v < .001:
                        attr.write(0)

            # lock non-animatable attributes
            if release:
                ctrl['ro'].lock()
                if ctrl.is_a(mx.tJoint):
                    ctrl['jo'].lock()

            # ???
            if 'control_shape' in ctrl:
                shp = ctrl['control_shape'].input()
                if shp and shp not in ctrls:
                    shp['msg'] // ctrl['control_shape']

        # check shape
        if not ctrl.is_a(mx.kTransform):
            continue
        if not release:
            has_shape = False
            for shp in ctrl.shapes():
                if shp['v'].read():
                    has_shape = True
                    break
            ctrl['displayHandle'] = not has_shape

        # tag controllers
        maya_version = float(mc.about(api=True)) / 100
        if maya_version >= 2017:
            mc.controller(str(ctrl))

            if release and 'gem_dag_children' in ctrl:
                for i in ctrl['gem_dag_children'].array_indices:
                    node = ctrl['gem_dag_children'][i].input()
                    if node:
                        mc.controller(str(node), str(ctrl), p=1)


def cleanup_rig_joints(root=None, exclude=None):
    if root is None:
        joints = mx.ls(et='joint')
    else:
        joints = list(root.descendents(type=mx.tJoint))
        if root.is_a(mx.tJoint):
            joints.append(root)

    if exclude is not None:
        joints_diff = list(exclude.descendents(type=mx.tJoint))
        if exclude.is_a(mx.tJoint):
            joints_diff.append(exclude)
        joints = [j for j in joints if j not in joints_diff]

    skin = Nodes.get_id('*::skin', as_list=True)
    if not skin:
        return

    for j in joints:
        # joints color
        j['useObjectColor'] = False

        # hide all except skin
        if len(list(j.children(type=mx.tJoint))) > 2:
            j['drawStyle'] = 2
            continue

        if j not in skin:
            j['drawStyle'] = 2
        else:
            j['overrideEnabled'] = True
            j['overrideDisplayType'] = 2
            for ch in j.children():
                ch['overrideEnabled'] = True


def cleanup_rig_shapes(root=None):
    # ik handles ?
    if root is None:
        nodes = mx.ls(et='ikHandle')
    else:
        nodes = []
        for n in root.descendents():
            if n.is_a(mx.kIkHandle):
                nodes.append(n)

    for node in nodes:
        node['v'] = False


HIDDEN_TYPES = [
    'dagPose',
    'decomposeMatrix', 'multMatrix', 'fourByFourMatrix', 'wtAddMatrix', 'composeMatrix', 'inverseMatrix',
    str(om.MNodeClass(om.MTypeId(mx.tMultDoubleLinear))),
    str(om.MNodeClass(om.MTypeId(mx.tAddDoubleLinear))),
    'blendTwoAttr', 'multiplyDivide', 'plusMinusAverage', 'vectorProduct',
    'condition', 'distanceBetween', 'blendWeighted', 'pairBlend', 'blendColors', 'clamp',
    'pointOnCurveInfo', 'motionPath', 'polyEdgeToCurve',
    'pointOnSurfaceInfo', 'loft',
]


def cleanup_rig_history():
    for nodetype in HIDDEN_TYPES:
        for node in mx.ls(et=nodetype):
            node['ihi'] = False


def label_skin_joints():
    skin = Nodes.get_id('*::skin', as_list=True)
    if not skin:
        return

    if len(skin) > 0:
        for sk in skin:
            if not sk or not sk.is_a(mx.tJoint):
                continue
            gem_id = Nodes.get_node_id(sk, find='::skin.')
            tpl, sep, tag = gem_id.partition('::')

            for branch in tpl.split('.')[1:]:
                if branch == 'L':
                    sk['side'] = 1
                    tpl = tpl.replace('.L', '', 1)
                    break
                if branch == 'R':
                    sk['side'] = 2
                    tpl = tpl.replace('.R', '', 1)
                    break

            sk['type'] = 18  # other type
            sk['otherType'] = tpl + sep + tag


# cleanup deformers ----------------------------------------------------------------------------------------------------

def rename_skin_clusters():
    # rename skin deformer nodes
    for skin in mx.ls(et='skinCluster'):
        try:
            skin['mi'].keyable = True
            fn = oma.MFnSkinCluster(skin.object())
            geo = fn.getOutputGeometry()
            geo = mx.Node(geo[0])
            p = geo.parent()

            if not skin.is_referenced():
                name = p.name(namespace=False)
                name = name.replace('msh_', '').replace('nrb_', '')
                name = 'skin_{}'.format(name)
                skin.rename(name)

                skin_set = skin.output(type=mx.tObjectSet)
                if skin_set:
                    skin_set.rename('{}Set'.format(name))
        except:
            name = 'unknown#'
            name = 'skin_{}'.format(name)
            skin.rename(name)

            skin_set = skin.output(type=mx.tObjectSet)
            if skin_set:
                skin_set.rename('{}Set'.format(name))


def cleanup_skin_clusters():
    # skin cleanup
    rename_skin_clusters()

    maya.mel.eval("source removeUnusedInfluences.mel;")

    for skin in mx.ls(et='skinCluster'):
        fn = oma.MFnSkinCluster(skin.object())
        geo = fn.getOutputGeometry()

        if geo:
            geo = mx.Node(geo[0])

            infs = [mx.Node(mdag.node()) for mdag in fn.influenceObjects()]
            for inf in infs:
                if 'lockInfluenceWeights' in inf:
                    inf['lockInfluenceWeights'] = False

            p = geo.parent()
            try:
                mc.skinPercent(str(skin), str(geo), prw=0.0001)
                maya.mel.eval('removeUnusedForSkin("{}", 0);'.format(skin))
                mc.skinPercent(str(skin), str(geo), normalize=True)
            except:
                pass

            for inf in infs:
                if 'lockInfluenceWeights' in inf:
                    inf['lockInfluenceWeights'] = True


# cleanup geometry -----------------------------------------------------------------------------------------------------


def cleanup_shape_orig():
    # shapeOrig cleanup
    for msh in mx.ls(et='mesh'):
        if not msh.exists or not msh.is_a(mx.tMesh):  # necessary on huge scene
            continue
        if not msh['io'].read():
            continue

        # disconnect shader from intermediate shapes
        for csg in msh.outputs(type=mx.tShadingEngine, plugs=True, connections=True):
            if not list(csg[0].node().inputs()):
                csg[0] // csg[1]

        # delete unconnected intermediate shapes
        if not list(msh.outputs()) and not msh.is_referenced():
            log.info('shape orig "{}" deleted'.format(msh))
            mx.delete(msh)

    for node in mx.ls(et='nurbsCurve'):
        if not node.exists or not node.is_a(mx.tNurbsCurve):  # necessary on huge scene
            continue
        if not node['io'].read():
            continue
