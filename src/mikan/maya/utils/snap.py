# coding: utf-8
"""
placement lib
"""

import math
import string
from collections import OrderedDict

import maya.cmds as mc
import mikan.maya.cmdx as mx
import maya.api.OpenMaya as om

from mikan.vendor.Qt.QtCore import Qt
from mikan.vendor.Qt.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QRadioButton, QGroupBox, QMenuBar
)
from mikan.maya.ui.widgets import MayaWindow, Callback

from mikan.maya.core.shape import Shape
from mikan.maya.lib.rig import copy_transform

from mikan.core.logger import create_logger

log = create_logger('snap.tools')


class SnapUI(MayaWindow):
    ui_height = 200
    ui_width = 320

    def __init__(self, parent=None):
        MayaWindow.__init__(self, parent)
        self.setWindowTitle('snap tools')
        self.setWindowFlags(Qt.Tool)
        self.setStyleSheet('QPushButton {max-height: 16px;}')
        self.setStyleSheet('QLabel {color:#89a; font-size:11px; font-weight:bold; margin-left:2px;}')
        self.resize(self.ui_width, self.ui_height)
        self.setMinimumWidth(self.ui_width)
        self.setMinimumHeight(self.ui_height)

        self.widget = QWidget()
        self.setCentralWidget(self.widget)

        self.layout = QVBoxLayout(self.widget)

        self.build_snap()

    def build_snap(self):
        horizontal_box1 = QHBoxLayout()
        horizontal_box2 = QHBoxLayout()
        horizontal_box3 = QHBoxLayout()
        horizontal_box4 = QHBoxLayout()
        horizontal_box5 = QHBoxLayout()
        horizontal_box6 = QHBoxLayout()

        self.layout.addLayout(horizontal_box1)
        self.layout.addLayout(horizontal_box2)
        self.layout.addLayout(horizontal_box3)
        self.layout.addLayout(horizontal_box4)
        self.layout.addLayout(horizontal_box5)
        self.layout.addLayout(horizontal_box6)

        snap_object = QLabel(' Snap Object :')
        horizontal_box1.addWidget(snap_object)

        bottom_btn = QPushButton('snap at bottom')
        bottom_btn.clicked.connect(Callback(snap, "bottom"))
        bottom_btn.setToolTip('select 2 objects')
        horizontal_box2.addWidget(bottom_btn)

        center_btn = QPushButton('snap at center')
        center_btn.clicked.connect(Callback(snap, "center"))
        center_btn.setToolTip('select 2 objects')
        horizontal_box2.addWidget(center_btn)

        pivot_btn = QPushButton('snap at pivot')
        pivot_btn.clicked.connect(Callback(snap, "pivot"))
        pivot_btn.setToolTip('select 2 objects')
        horizontal_box2.addWidget(pivot_btn)

        create_joint = QLabel(' Create Joint :')
        horizontal_box3.addWidget(create_joint)

        joint_bottom_btn = QPushButton('at bottom')
        joint_bottom_btn.clicked.connect(Callback(create_locator, "bottom", True))
        joint_bottom_btn.setToolTip('select 1 object')
        horizontal_box4.addWidget(joint_bottom_btn)

        joint_center_btn = QPushButton('at center')
        joint_center_btn.clicked.connect(Callback(create_locator, "center", True))
        joint_center_btn.setToolTip('select 1 object')
        horizontal_box4.addWidget(joint_center_btn)

        joint_pivot_btn = QPushButton('at pivot')
        joint_pivot_btn.clicked.connect(Callback(create_locator, "pivot", True))
        joint_pivot_btn.setToolTip('select 1 object')
        horizontal_box4.addWidget(joint_pivot_btn)

        space2 = QFrame()
        space2.setFrameShape(space2.VLine)
        horizontal_box4.addWidget(space2)

        joint_bary_btn = QPushButton('at barycenter')
        joint_bary_btn.clicked.connect(Callback(create_locator, "barycenter", True))
        joint_bary_btn.setToolTip('select vtx')
        horizontal_box4.addWidget(joint_bary_btn)

        create_joint = QLabel(' Create Locator :')
        horizontal_box5.addWidget(create_joint)

        loc_bottom_btn = QPushButton('at bottom')
        loc_bottom_btn.clicked.connect(Callback(create_locator, "bottom"))
        loc_bottom_btn.setToolTip('select 1 object')
        horizontal_box6.addWidget(loc_bottom_btn)

        loc_center_btn = QPushButton('at center')
        loc_center_btn.clicked.connect(Callback(create_locator, "center"))
        loc_center_btn.setToolTip('select 1 object')
        horizontal_box6.addWidget(loc_center_btn)

        loc_pivot_btn = QPushButton('at pivot')
        loc_pivot_btn.clicked.connect(Callback(create_locator, "pivot"))
        loc_pivot_btn.setToolTip('select 1 object')
        horizontal_box6.addWidget(loc_pivot_btn)

        space3 = QFrame()
        space3.setFrameShape(space3.VLine)
        horizontal_box6.addWidget(space3)

        loc_bary_btn = QPushButton('at barycenter')
        loc_bary_btn.clicked.connect(Callback(create_locator, "barycenter"))
        loc_bary_btn.setToolTip('select vtx')
        horizontal_box6.addWidget(loc_bary_btn)
        self.layout.addStretch()


def create_landmark(name='mark', colorize=True, scale=1.0):
    # TODO: remplacer ça par un call de Shape
    curve_x_xfo = mc.curve(
        n="curveX",
        d=1,
        p=[(-1 * scale, 0, 0), (1 * scale, 0, 0), (1 * scale, 0.05 * scale, 0.05 * scale), (1 * scale, 0, 0), (1 * scale, 0.05 * scale, -0.05 * scale), (1 * scale, 0, 0),
           (1 * scale, -0.05 * scale, -0.05 * scale), (1 * scale, 0, 0), (1 * scale, -0.05 * scale, 0.05 * scale), (1 * scale, 0, 0)],
        k=[0, 1, 2, 3, 4, 5, 6, 7, 8, 9])
    curve_x_shp = mc.listRelatives(curve_x_xfo, s=True, c=True)[0]
    mc.select(cl=True)

    curve_y_xfo = mc.curve(
        n="curveY",
        d=1,
        p=[(0, -1 * scale, 0), (0, 1 * scale, 0), (-0.05 * scale, 1 * scale, 0.05 * scale), (0, 1 * scale, 0), (-0.05 * scale, 1 * scale, -0.05 * scale),
           (0, 1 * scale, 0), (0.05 * scale, 1 * scale, 0.05 * scale), (0, 1 * scale, 0)],
        k=[0, 1, 2, 3, 4, 5, 6, 7])
    curve_y_shp = mc.listRelatives(curve_y_xfo, s=True, c=True)[0]
    mc.select(cl=True)

    curve_z_xfo = mc.curve(
        n="curveZ",
        d=1,
        p=[(0, 0, -1 * scale), (0, 0, 1 * scale), (0.05 * scale, 0.05 * scale, 1 * scale), (-0.05 * scale, 0.05 * scale, 1 * scale), (0.05 * scale, 0.05 * scale, 1 * scale),
           (0, 0, 1 * scale), (-0.05 * scale, -0.05 * scale, 1 * scale), (0.05 * scale, -0.05 * scale, 1 * scale), (-0.05 * scale, -0.05 * scale, 1 * scale), (0, 0, 1 * scale)],
        k=[0, 1, 2, 3, 4, 5, 6, 7, 8, 9])
    curve_z_shp = mc.listRelatives(curve_z_xfo, s=True, c=True)[0]
    mc.select(cl=True)

    mc.setAttr(curve_x_shp + '.lineWidth', 3)
    if colorize: mc.setAttr(curve_x_shp + '.overrideEnabled', 1)
    mc.setAttr(curve_x_shp + '.overrideColor', 4)

    mc.setAttr(curve_y_shp + '.lineWidth', 3)
    if colorize: mc.setAttr(curve_y_shp + '.overrideEnabled', 1)
    mc.setAttr(curve_y_shp + '.overrideColor', 23)

    mc.setAttr(curve_z_shp + '.lineWidth', 3)
    if colorize: mc.setAttr(curve_z_shp + '.overrideEnabled', 1)
    mc.setAttr(curve_z_shp + '.overrideColor', 15)

    if mc.objExists(name):
        name += '#'

    xfo = mc.createNode('transform', n=name)
    mc.parent(curve_x_shp, xfo, s=True, r=True)
    mc.parent(curve_y_shp, xfo, s=True, r=True)
    mc.parent(curve_z_shp, xfo, s=True, r=True)
    mc.delete([curve_x_xfo, curve_y_xfo, curve_z_xfo])

    return xfo


def snap_cmds(self, cmd):
    options = {}

    for section in self.ui_options[cmd]:
        for opt in self.ui_options[cmd][section]:
            if self.ui_options[cmd][section][opt].isChecked():
                options[section] = opt

    selection = mc.ls(sl=True, flatten=True)

    # Process selection
    cpts = []
    nodes = []
    for obj in selection:
        if obj.endswith(']'):
            cpts.append(obj)
        else:
            nodes.append(obj)

    if cpts and nodes:
        cpts = filter_components(cpts)

    if cmd == 'snap':

        if options['selection'] == 'snap start to all':
            if options['orientation'] == 'copy from transform':
                if options['position'] == 'bb_bottom':
                    snap("bbbottom", True)
                elif options['position'] == 'bb_center':
                    snap("bbcenter", True)
                elif options['position'] == 'barycenter':
                    snap("barycenter", True)
            else:
                if options['position'] == 'bb_bottom':
                    snap("bbbottom", False)
                elif options['position'] == 'bb_center':
                    snap("bbcenter", False)
                elif options['position'] == 'barycenter':
                    snap("barycenter", False)
        elif options['selection'] == 'snap two by two':
            if options['orientation'] == 'copy from transform':
                for i in range(0, len(selection), 2):
                    mc.select(selection[i + 0], selection[i + 1])
                    if options['position'] == 'bb_bottom':
                        snap("bbbottom", True)
                    elif options['position'] == 'bb_center':
                        snap("bbcenter", True)
                    elif options['position'] == 'barycenter':
                        snap("barycenter", True)
            else:
                for i in range(0, len(selection), 2):
                    mc.select(selection[i + 0], selection[i + 1])
                    if options['position'] == 'bb_bottom':
                        snap("bbbottom", False)
                    elif options['position'] == 'bb_center':
                        snap("bbcenter", False)
                    elif options['position'] == 'barycenter':
                        snap("barycenter", False)

    elif cmd == 'build':

        all_marks = 'all_marks_grp'
        if options['type'] in ['locator', 'transform']:
            if not mc.objExists(all_marks):
                mc.createNode('transform', n=all_marks)

        new_objs = []

        if options['selection'] == 'one build for all':
            mc.select(selection)
            if options['type'] in ['locator', 'transform']:
                if options['position'] == 'barycenter':
                    create_locator("barycenter", False, False)
                elif options['position'] == 'bb_center':
                    create_locator("bbcenter", False, False)
                elif options['position'] == 'bb_bottom':
                    create_locator("bbbottom", False, False)
            elif options['type'] == 'joint':
                if options['position'] == 'barycenter':
                    create_locator("barycenter", True, False)
                elif options['position'] == 'bb_center':
                    create_locator("bbcenter", True, False)
                elif options['position'] == 'bb_bottom':
                    create_locator("bbbottom", True, False)

            new_objs = mc.ls(sl=True)

        elif options['selection'] == 'one build per selection':

            for i in range(0, len(selection)):
                mc.select(selection[i])
                if options['type'] in ['locator', 'transform']:
                    if options['position'] == 'barycenter':
                        create_locator("barycenter", False, False)
                    elif options['position'] == 'bb_center':
                        create_locator("bbcenter", False, False)
                    elif options['position'] == 'bb_bottom':
                        create_locator("bbbottom", False, False)
                elif options['type'] == 'joint':
                    if options['position'] == 'barycenter':
                        create_locator("barycenter", True, False)
                    elif options['position'] == 'bb_center':
                        create_locator("bbcenter", True, False)
                    elif options['position'] == 'bb_bottom':
                        create_locator("bbbottom", True, False)

                new_objs += mc.ls(sl=True)

        if options['type'] == 'transform':
            special_locators = []
            for i, obj in enumerate(new_objs):
                trsf = create_landmark(colorize=False, scale=0.25)
                copy_transform(obj, trsf)
                special_locators.append(trsf)
            mc.delete(new_objs)
            new_objs = special_locators

        if options['type'] in ['locator', 'transform']:
            colors = [4, 6, 10, 13, 14, 15, 17, 18, 19, 20]
            color_index = colors[self.cmd_build_count % len(colors)]
            for obj in new_objs:
                mc.setAttr('{}.overrideEnabled'.format(obj), 1)
                mc.setAttr('{}.overrideColor'.format(obj), color_index)
            self.cmd_build_count += 1

        '''if options['type'] == 'mikan bones': 

                if self.MikanUI:
                    result = mc.promptDialog( message       = 'Name', 
                                            button        = 'ok', 
                                            defaultButton = 'ok', 
                                            text          = self.MikanUI.instance.tab_templates.tab_add.wd_name.value )

                    if result == 'ok':
                        tpl_name = mc.promptDialog( q = 1, text = 1 )

                        self.MikanUI.instance.tab_templates.tab_add.wd_type.set_value( 0 ) # default
                        self.MikanUI.instance.tab_templates.tab_add.wd_subtype.set_value( 0 )# bones

                        self.MikanUI.instance.tab_templates.tab_add.wd_name.set_value( tpl_name )
                        self.MikanUI.instance.tab_templates.tab_add.wd_adds['number'].set_value( len(new_objs) )
                        self.MikanUI.instance.tab_templates.tab_add.wd_add.click()


                        new_tpl_elements = mc.ls('tpl_{}*'.format(tpl_name), type = 'joint' )

                        # snap
                        ctrls_matrices = []
                        for i, obj in enumerate(new_objs):
                            ctrls_matrices.append( utils_get_matrix(obj))

                        new_skin_elements = []
                        for i, obj in enumerate(new_objs):
                            m = ctrls_matrices[i]
                            tpl_elem = new_tpl_elements[i]

                            # get name info
                            name = tpl_elem.split('tpl_')[1]
                            end_didgits = []
                            for iChar in reversed(range(len(name))):
                                if name[iChar] in string.digits:
                                    end_didgits.append(name[iChar])
                                    name = name[:-1]
                                else:
                                    break
                            end_didgits = ''.join(reversed(end_didgits))
                            if end_didgits == '':
                                end_didgits = '1'

                            new_skin_elements.append( 'sk_{}{}'.format(name,end_didgits ) )
                            # build shape
                            root = mc.createNode('transform', parent=tpl_elem, name='_shape_{}_{}.{}'.format(name, 'ctrls', int(end_didgits) -1 ))

                            # create shape
                            s = Shape.create('circle')#, axis='x')
                            mc.parent(str(s.node), str(root), r=1)

                            mc.addAttr(root, ln = 'gem_shape', dt = 'string' )
                            mc.setAttr( '{}.gem_shape'.format(root) ,'{}::ctrls.{}'.format(name,int(end_didgits) -1 ), type = 'string' )

                            n = root.replace('_shape_', 'shp_')
                            mc.rename(str(s.node), n)

                            color = [1,0,0]
                            s.set_color(color)
                            s.set_shape_color(s.node, color)
                            for shp in s.get_shapes():
                                s.set_shape_color(shp, color)


                            mc.pointConstraint(tpl_elem,root)

                            # add gem attr on tpl
                            mc.addAttr(tpl_elem, ln = 'gem_hook', dt = 'string' )
                            mc.setAttr( '{}.gem_hook'.format(tpl_elem) ,'{}::hooks.{}'.format(name,int(end_didgits) -1 ), type = 'string' )                       

                            mc.addAttr(tpl_elem, ln = 'gem_dag_ctrls', dt = 'string' )
                            mc.setAttr( '{}.gem_dag_ctrls'.format(tpl_elem) ,'{}::ctrls.{}'.format(name,int(end_didgits) -1 ), type = 'string' )   

                            mc.addAttr(tpl_elem, ln = 'gem_dag_skin', dt = 'string' )
                            mc.setAttr( '{}.gem_dag_skin'.format(tpl_elem) ,'{}::hooks.{}'.format(name,int(end_didgits) -1 ), type = 'string' )   

                            # set matrix to element
                            mc.setAttr('{}.sx'.format(root), matrix_getRow(0,m).length()*1.4 )
                            #mc.setAttr('{}.sy'.format(root), len(matrix_getRow(1,m)) )
                            mc.setAttr('{}.sz'.format(root), matrix_getRow(2,m).length()*1.4 )

                            m_normalize = matrix_normalize(m)
                            utils_set_matrix( new_tpl_elements[i], m_normalize)
                            
                            # add cube
                            cube_dummy_matrices = []
                            for i in range(len(ctrls_matrices)-1):
                                m = ctrls_matrices[i]
                                p = (matrix_getRow(3,ctrls_matrices[i])+matrix_getRow(3,ctrls_matrices[i+1]))/2
                                m = matrix_setRow(3,m,p)
                                vX = matrix_getRow(0,m)
                                vZ = matrix_getRow(2,m)
                                m = matrix_setRow(0,m,vX*2)
                                m = matrix_setRow(2,m,vZ*2)
                                cube_dummy_matrices.append(m)
                            
                            dummy_cubes = []
                            for m in cube_dummy_matrices:
                                cube_trsf = mc.polyCube(n ='dummy')[0]
                                utils_set_matrix(cube_trsf,m)
                                dummy_cubes.append(cube_trsf)

                            dummy_cubes_intermediate = []
                            for i, m in enumerate(ctrls_matrices):
                                if i == 0 or i == len(ctrls_matrices)-1:
                                    continue
                                cube_trsf = mc.polyCube(n ='dummy')[0]
                                utils_set_matrix(cube_trsf,m)
                                dummy_cubes_intermediate.append(cube_trsf)

                            cube_scr_indexes = [0,1,7,6]
                            cube_dst_indexes = [2,3,5,4]
                            for i in range(len(dummy_cubes)-1):
                                c = dummy_cubes[i]
                                cNext = dummy_cubes[i+1]
                                for j in range(4):
                                    iCs = cube_scr_indexes[j]
                                    iCd = cube_dst_indexes[j]
                                    p = mc.xform( '{}.vtx[{}]'.format(cNext,iCs),q=True,ws=True,t=True)
                                    mc.xform('{}.vtx[{}]'.format(c,iCd),ws = True, t = p)

                            angle_max_possible = 10
                            for i in range(0,len(dummy_cubes)-1):
                                p_ctrl = matrix_getRow(3,ctrls_matrices[i+1])
                                c = dummy_cubes[i]
                                cNext = dummy_cubes[i+1]

                                if i < len(dummy_cubes_intermediate):
                                    cInter = dummy_cubes_intermediate[i]

                                for j in range(4):
                                    iCs = cube_scr_indexes[j]
                                    iCd = cube_dst_indexes[j]

                                    pRef = mc.xform( '{}.vtx[{}]'.format(cNext,iCs),q=True,ws=True,t=True)
                                    pRef = om.MVector(*pRef)

                                    dist_to_offset = (pRef-p_ctrl).length()*math.sin(math.radians(angle_max_possible))

                                    pSrc = mc.xform( '{}.vtx[{}]'.format(c    ,iCs),q=True,ws=True,t=True)
                                    pSrc = om.MVector(*pSrc)

                                    pDst = mc.xform( '{}.vtx[{}]'.format(cNext,iCd),q=True,ws=True,t=True)
                                    pDst = om.MVector(*pDst)

                                    vSrc = pSrc-pRef
                                    vDst = pDst-pRef

                                    vSrc.normalize()
                                    vDst.normalize()

                                    pSrc_new = pRef + vSrc*dist_to_offset
                                    pDst_new = pRef + vDst*dist_to_offset

                                    mc.xform('{}.vtx[{}]'.format(c,iCd),ws = True, t = (pSrc_new.x,pSrc_new.y,pSrc_new.z))
                                    mc.xform('{}.vtx[{}]'.format(cNext,iCs),ws = True, t = (pDst_new.x,pDst_new.y,pDst_new.z))
                                    if i < len(dummy_cubes_intermediate):
                                        mc.xform('{}.vtx[{}]'.format(cInter,iCs),ws = True, t = (pSrc_new.x,pSrc_new.y,pSrc_new.z))
                                        mc.xform('{}.vtx[{}]'.format(cInter,iCd),ws = True, t = (pDst_new.x,pDst_new.y,pDst_new.z))

                                

                            # skin cube
                            for i in range(0,len(dummy_cubes)):
                                joints = [new_tpl_elements[i]]
                                selection = joints+[dummy_cubes[i]]
                                mc.select(selection)
                                mc.skinCluster( joints, dummy_cubes[i] , toSelectedBones = True, maximumInfluences = 2 )
                                mc.select(cl = True)                        

                            for i in range(len(dummy_cubes_intermediate)):
                                cInter = dummy_cubes_intermediate[i]
                                joints = [new_tpl_elements[i],new_tpl_elements[i+1]]
                                selection = joints+[cInter]
                                mc.select(selection)
                                sk = mc.skinCluster( joints, cInter , toSelectedBones = True, maximumInfluences = 2 )[0]
                                mc.select(cl = True) 
                                for j in range(4):
                                    iCs = cube_scr_indexes[j]
                                    iCd = cube_dst_indexes[j]                                
                                    mc.skinPercent( sk, '{}.vtx[{}]'.format(cInter,iCs), transformValue=[(new_tpl_elements[i], 1.0),(new_tpl_elements[i+1], 0.0)])
                                    mc.skinPercent( sk, '{}.vtx[{}]'.format(cInter,iCd), transformValue=[(new_tpl_elements[i], 0.0),(new_tpl_elements[i+1], 1.0)])                            

                            # combine cube
                            combined_mesh = combine_skinned_meshes(dummy_cubes+dummy_cubes_intermediate)[0][0]
                            # skin mesh
                            mc.select(new_tpl_elements+[selection_info['mesh']])
                            mc.skinCluster( selection_info['mesh'] , new_tpl_elements, toSelectedBones = True, maximumInfluences = 2 )
                            mc.select(cl = True)  
                                                        
                            mc.copySkinWeights( combined_mesh, selection_info['mesh'], noMirror = True, surfaceAssociation = "closestPoint", influenceAssociation = ["oneToOne"])    

                            # save skin
                            #mx.encode(str(selection_info['mesh']))
                            tpl_to_rig = {}
                            for nTpl, nRig in zip(new_tpl_elements,new_skin_elements):
                                tpl_to_rig[nTpl] = nRig

                            dfg = DeformerGroup.create([selection_info['mesh']], filtered=False)
                            deformer = dfg.data[0]   
                            for i in range( len(deformer.data['infs'])):
                                infs = deformer.data['infs'][i].split(' ')

                                new_infs = []
                                for inf in infs:
                                    new_infs.append(tpl_to_rig.get(inf,inf))

                                if len(new_infs) == 1:
                                    deformer.data['infs'][i] = new_infs[0]
                                else:
                                    deformer.data['infs'][i] = ' '.join(new_infs)

                            dfg.write()

                            #clean
                            
                            mc.delete(dummy_cubes)
                            mc.delete(dummy_cubes_intermediate)
                            mc.delete(combined_mesh)
                            mc.parent(str(dfg.node),'template')

                            #add something for the tips
                            place_tip = True
                            if place_tip:
                                i_tip = len(new_objs)
                                m_beforeLast = utils_get_matrix(new_tpl_elements[i_tip-2])
                                m_last = utils_get_matrix(new_tpl_elements[i_tip-1])
                                p_tip = matrix_getRow(3,m_last) - matrix_getRow(3,m_beforeLast) + matrix_getRow(3,m_last)
                                m_last = matrix_setRow(3,m_last,p_tip)
                                utils_set_matrix( new_tpl_elements[i_tip],m_last )
                                # add gem attr on tpl
                                mc.addAttr(new_tpl_elements[i_tip], ln = 'gem_hook', dt = 'string' )
                                mc.setAttr( '{}.gem_hook'.format(new_tpl_elements[i_tip]) ,'{}::hooks.tip'.format(name), type = 'string' )          

                            mc.delete(new_objs)
                            new_objs = new_tpl_elements
                        else:
                          mc.delete(new_objs)'''

        if options['type'] in ['locator', 'transform']:
            marks_grp = mc.createNode('transform', n='marks_grp_{}'.format(self.cmd_build_count - 1))
            new_objs = mc.parent(new_objs, marks_grp)
            mc.parent(marks_grp, all_marks)

        mc.select(new_objs)


class SnapUI2(MayaWindow):
    ui_height = 400
    ui_width = 500

    def __init__(self, parent=None, mikan_ui=None):
        MayaWindow.__init__(self, parent)

        self.MikanUI = mikan_ui
        self.ui_options = {}

        cmd = 'snap'
        self.ui_options[cmd] = {}

        section = 'selection'
        self.ui_options[cmd][section] = OrderedDict()
        for key in ['snap start to all', 'snap two by two']:
            self.ui_options[cmd][section][key] = None

        section = 'position'
        self.ui_options[cmd][section] = OrderedDict()
        for key in ['barycenter', 'bb_center', 'bb_bottom']:
            self.ui_options[cmd][section][key] = None

        section = 'orientation'
        self.ui_options[cmd][section] = OrderedDict()
        for key in ['skip', 'copy from transform']:
            self.ui_options[cmd][section][key] = None

        cmd = 'build'
        self.ui_options[cmd] = {}

        section = 'selection'
        self.ui_options[cmd][section] = OrderedDict()
        for key in ['one build for all', 'one build per selection']:
            self.ui_options[cmd][section][key] = None

        section = 'position'
        self.ui_options[cmd][section] = OrderedDict()
        for key in ['barycenter', 'bb_center', 'bb_bottom']:
            self.ui_options[cmd][section][key] = None

        '''
        section = 'orientation'
        self.ui_options[cmd][section] = OrderedDict()
        for key in ['skip','copy from transform']:
            self.ui_options[cmd][section][key] = None
        '''

        section = 'type'
        self.ui_options[cmd][section] = OrderedDict()
        for key in ['locator', 'joint']:
            self.ui_options[cmd][section][key] = None

        self.cmd_build_count = 0

        self.setWindowTitle('snap tools 2')
        self.setWindowFlags(Qt.Tool)
        self.setStyleSheet('QPushButton {max-height: 16px;}')
        self.setStyleSheet('QLabel {color:#89a; font-size:11px; font-weight:bold; margin-left:2px;}')
        self.resize(self.ui_width, self.ui_height)
        self.setMinimumWidth(self.ui_width)
        self.setMinimumHeight(self.ui_height)

        self.widget = QWidget()
        self.setCentralWidget(self.widget)

        self.layout = QVBoxLayout(self.widget)

        self.build_snap()

    def build_snap(self):

        horizontal_box_menu_bar = QHBoxLayout()

        menubar = QMenuBar()
        horizontal_box_menu_bar.addWidget(menubar)
        action_file = menubar.addMenu("Help")
        action_file.addAction("go to wiki")

        for cmd in self.ui_options:

            horizontal_box_title = QHBoxLayout()
            self.layout.addLayout(horizontal_box_title)

            create_joint = QLabel(' {} :'.format(cmd))
            horizontal_box_title.addWidget(create_joint)

            for section in self.ui_options[cmd]:

                horizontal_box_section = QHBoxLayout()
                self.layout.addLayout(horizontal_box_section)

                build_type_options = QGroupBox()
                horizontal_box_section.addWidget(build_type_options)

                radio_btns_layout = QHBoxLayout()

                build_type_options_title = QLabel(section)
                radio_btns_layout.addWidget(build_type_options_title)

                is_first_elem = True
                for type_option in self.ui_options[cmd][section]:
                    self.ui_options[cmd][section][type_option] = QRadioButton(type_option)
                    if is_first_elem: self.ui_options[cmd][section][type_option].setChecked(True)
                    radio_btns_layout.addWidget(self.ui_options[cmd][section][type_option])
                    is_first_elem = False

                build_type_options.setLayout(radio_btns_layout)

            horizontal_box_cmd = QHBoxLayout()
            self.layout.addLayout(horizontal_box_cmd)

            build_btn = QPushButton(cmd)
            build_btn.clicked.connect(Callback(snap_cmds, self, cmd))
            build_btn.setToolTip(cmd)
            horizontal_box_cmd.addWidget(build_btn)

        self.layout.addStretch()


### ----------------------------------------------------------------------------------------------------
# 28 : control vertices
# 31 : polygon vertices
# 36 : subdivision Mesh Points
# 46 : lattice point
# 47 : particles

def filter_components(sl):
    cpt_list = []

    faces = mc.filterExpand(sl, expand=True, sm=34)
    if faces:
        for vtx in mc.polyListComponentConversion(faces, ff=True, tv=True):
            cpt_list.append(vtx)

    edges = mc.filterExpand(sl, expand=True, sm=32)
    if edges:
        for vtx in mc.polyListComponentConversion(edges, fe=True, tv=True):
            cpt_list.append(vtx)

    cpt_list += mc.filterExpand(sl, expand=True, sm=(31, 28, 36, 46, 47)) or []
    cpt_list = mc.ls(list(set(cpt_list)), flatten=True)

    if not cpt_list:
        raise NameError("nothing selected, please select components")

    return cpt_list


def get_barycenter(cpt_list):
    b = mx.Vector()
    for cpt in cpt_list:
        pos = mc.xform(cpt, q=True, ws=True, t=True)
        b += mx.Vector(pos)

    b /= len(cpt_list)
    return b


def get_boundingbox_center(cpt_list):
    bb_min = mx.Vector(99999.0, 99999.0, 99999.0)
    bb_max = mx.Vector(-99999.0, -99999.0, -99999.0)
    for cpt in cpt_list:
        pos = mc.xform(cpt, q=True, ws=True, t=True)
        for i in range(3):
            if pos[i] < bb_min[i]: bb_min[i] = pos[i]
            if bb_max[i] < pos[i]: bb_max[i] = pos[i]

    b = (bb_min + bb_max) / 2.0
    return b


def get_boundingbox_bottom(cpt_list):
    bb_min = mx.Vector(99999.0, 99999.0, 99999.0)
    bb_max = mx.Vector(-99999.0, -99999.0, -99999.0)
    for cpt in cpt_list:
        pos = mc.xform(cpt, q=True, ws=True, t=True)
        for i in range(3):
            if pos[i] < bb_min[i]: bb_min[i] = pos[i]
            if bb_max[i] < pos[i]: bb_max[i] = pos[i]

    b = bb_min
    return b


def get_position(node, mode):
    if not isinstance(node, mx.Node):
        node = mx.encode(str(node))

    if mode != 'pivot':
        if node.is_a(mx.tTransform):
            shp = node.shape()
            node = shp if shp else node

    if mode == 'bottom':
        bb = node.bounding_box
        bb.transformUsing(node['wm'][0].as_matrix())
        return mx.Vector(bb.center[0], bb.min[1], bb.center[2])

    elif mode == 'center':
        bb = node.bounding_box
        bb.transformUsing(node['wm'][0].as_matrix())
        return mx.Vector(bb.center)

    elif mode == 'pivot':
        print(node)
        pos = mc.xform(str(node), q=1, rp=1, ws=1)
        return mx.Vector(pos)


def get_orientation(node):
    b = mx.Vector()

    pos = mc.xform(str(node), q=True, ws=True, ro=True)
    b += mx.Vector(pos)

    return b


def snap(mode, orient=False):
    if mode == "barycenter":
        sl = mc.ls(sl=True)

        cpts = []
        nodes = []
        for obj in sl:
            if obj.endswith(']'):
                cpts.append(obj)
            else:
                nodes.append(obj)

        dummy = None

        if cpts and nodes:
            cpts = filter_components(cpts)

            dummy = mx.create_node(mx.tTransform, name='dummy')
            dummy['t'] = get_barycenter(cpts)

            for node in nodes:
                copy_transform(dummy, node, t=True)


        elif nodes:
            src = nodes[0]
            dummy = mx.create_node(mx.tTransform, name='dummy')
            dummy['t'] = get_position(src, 'pivot')
            if not orient:
                for i in range(1, len(nodes)):
                    copy_transform(dummy, nodes[i], t=True)
            else:
                for i in range(1, len(nodes)):
                    copy_transform(dummy, nodes[i], t=True)
                    copy_transform(src, nodes[i], r=True)

        if dummy: mx.delete(dummy)

    elif mode == "bbcenter":
        sl = mc.ls(sl=True)

        cpts = []
        nodes = []
        for obj in sl:
            if obj.endswith(']'):
                cpts.append(obj)
            else:
                nodes.append(obj)

        if cpts and nodes:
            cpts = filter_components(cpts)

            dummy = mx.create_node(mx.tTransform, name='dummy')
            dummy['t'] = get_boundingbox_center(cpts)

            for node in nodes:
                copy_transform(dummy, node, t=True)

            mx.delete(dummy)

        elif nodes:
            sl = mx.ls(sl=True)
            src = sl[0]
            dummy = mx.create_node(mx.tTransform, name='dummy')
            dummy['t'] = get_position(src, 'center')
            if not orient:
                for i in range(1, len(nodes)):
                    copy_transform(dummy, nodes[i], t=True)
            else:
                for i in range(1, len(nodes)):
                    copy_transform(dummy, nodes[i], t=True)
                    copy_transform(src, nodes[i], r=True)

            mx.delete(dummy)

    elif mode == "bbbottom":
        sl = mc.ls(sl=True)

        cpts = []
        nodes = []
        for obj in sl:
            if obj.endswith(']'):
                cpts.append(obj)
            else:
                nodes.append(obj)

        dummy = None

        if cpts and nodes:
            cpts = filter_components(cpts)

            dummy = mx.create_node(mx.tTransform, name='dummy')
            dummy['t'] = get_boundingbox_bottom(cpts)

            for node in nodes:
                copy_transform(dummy, node, t=True)

        elif nodes:
            sl = mx.ls(sl=True)
            src = sl[0]
            dummy = mx.create_node(mx.tTransform, name='dummy')
            dummy['t'] = get_position(src, 'bottom')
            if not orient:
                for i in range(1, len(nodes)):
                    copy_transform(dummy, nodes[i], t=True)
            else:
                for i in range(1, len(nodes)):
                    copy_transform(dummy, nodes[i], t=True)
                    copy_transform(src, nodes[i], r=True)

        if not dummy:
            mx.delete(dummy)


def create_locator(mode, joint=False, orient=False):
    locators = []

    if mode == "barycenter":
        sl = mc.ls(sl=True)
        cpts = []
        nodes = []
        for obj in sl:
            if obj.endswith(']'):
                cpts.append(obj)
            else:
                nodes.append(obj)

        if cpts:
            sl = filter_components(mc.ls(sl=True, flatten=True))

            obj = mx.encode(cpts[0].split('.')[0])
            if obj.is_a(mx.kShape):
                obj = obj.parent()

            name = obj.name(namespace=False)
            name = name.split('_', 1)[-1]

            with mx.DagModifier() as md:
                if not joint:
                    nd = md.create_node(mx.tTransform, name='loc_{}'.format(name))
                    md.create_node(mx.tLocator, parent=nd, name='loc_{}Shape'.format(name))
                else:
                    nd = md.create_node(mx.tJoint, name='sk_{}'.format(name))

                nd['t'] = get_barycenter(sl)
            locators.append(nd)

        if nodes:
            sl = mc.ls(sl=True)

            obj = mx.encode(str(sl[0]))
            name = obj.name(namespace=False)

            with mx.DagModifier() as md:
                if not joint:
                    nd = md.create_node(mx.tLocator, name='loc_{}'.format(name))
                else:
                    nd = md.create_node(mx.tJoint, name='sk_{}'.format(name))

            b = mx.Vector()
            for sel in sl:
                pos = get_position(sel, 'pivot')
                b += mx.Vector(pos)

            b /= len(sl)

            nd['t'] = b
            locators.append(nd)

    elif mode == "bbcenter":
        sl = mc.ls(sl=True)

        cpts = []
        nodes = []
        for obj in sl:
            if obj.endswith(']'):
                cpts.append(obj)
            else:
                nodes.append(obj)

        if cpts:
            sl = filter_components(mc.ls(sl=True))

            obj = mx.encode(sl[0].split('.')[0])
            if obj.is_a(mx.kShape):
                obj = obj.parent()

            name = obj.name(namespace=False)
            name = name.split('_', 1)[-1]

            with mx.DagModifier() as md:
                if not joint:
                    nd = md.create_node(mx.tTransform, name='loc_{}'.format(name))
                    md.create_node(mx.tLocator, parent=nd, name='loc_{}Shape'.format(name))
                else:
                    nd = md.create_node(mx.tJoint, name='sk_{}'.format(name))

            nd['t'] = get_boundingbox_center(sl)
            locators.append(nd)

        if nodes:
            obj = mx.encode(nodes[0])
            name = obj.name(namespace=False)

            with mx.DagModifier() as md:
                if not joint:
                    nd = md.create_node(mx.tTransform, name='loc_{}'.format(name))
                    md.create_node(mx.tLocator, parent=nd, name='loc_{}Shape'.format(name))
                else:
                    nd = md.create_node(mx.tJoint, name='sk_{}'.format(name))

            nd['t'] = get_boundingbox_center(sl)
            locators.append(nd)

    elif mode == "bbbottom":
        sl = mc.ls(sl=True)

        cpts = []
        nodes = []
        for obj in sl:
            if obj.endswith(']'):
                cpts.append(obj)
            else:
                nodes.append(obj)

        if cpts:
            obj = mx.encode(str(sl[0]))
            name = obj.name(namespace=False)

            with mx.DagModifier() as md:
                if not joint:
                    nd = md.create_node(mx.tTransform, name='loc_{}'.format(name))
                    md.create_node(mx.tLocator, parent=nd, name='loc_{}Shape'.format(name))
                else:
                    nd = md.create_node(mx.tJoint, name='sk_{}'.format(name))

            b = mx.Vector()
            for sel in sl:
                pos = get_position(sel, 'bottom')
                b += mx.Vector(pos)

            b /= len(sl)
            nd['t'] = b
            locators.append(nd)

        if nodes:
            obj = mx.encode(nodes[0])
            name = obj.name(namespace=False)

            with mx.DagModifier() as md:
                if not joint:
                    nd = md.create_node(mx.tTransform, name='loc_{}'.format(name))
                    md.create_node(mx.tLocator, parent=nd, name='loc_{}Shape'.format(name))
                else:
                    nd = md.create_node(mx.tJoint, name='sk_{}'.format(name))

            b = mx.Vector()
            for sel in sl:
                pos = get_position(sel, 'bottom')
                b += mx.Vector(pos)

            b /= len(sl)
            nd['t'] = b
            locators.append(nd)

    mx.cmd(mc.select, locators)


def create_ctrl(mode):
    ctrls = []

    if mode != 'barycenter':
        for obj in mx.ls(sl=True):
            name = obj.name(namespace=False)

            with mx.DagModifier() as md:
                root = md.create_node(mx.tTransform, name='root_' + name)
                c = md.create_node(mx.tTransform, parent=root, name='c_' + name)
                ctrls.append(c)

            copy_transform(obj, root)
            pos = get_position(obj, mode)
            root['t'] = pos

            parent = obj.parent()
            if parent:
                mc.parent(str(root), str(parent))
            mc.parent(str(obj), str(c))

    elif mode == 'barycenter':
        sl = filter_components(mc.ls(sl=True))

        obj = mx.encode(sl[0].split('.')[0])
        if obj.is_a(mx.kShape):
            obj = obj.parent()

        name = obj.name(namespace=False)
        name = name.split('_', 1)[-1]

        with mx.DagModifier() as md:
            root = md.create_node(mx.tTransform, name='root_' + name)
            c = md.create_node(mx.tTransform, parent=root, name='c_' + name)
            ctrls.append(c)

        copy_transform(obj, root)
        pos = get_barycenter(sl)
        root['t'] = pos

        parent = obj.parent()
        if parent:
            mc.parent(str(root), str(parent))
        mc.parent(str(obj), str(c))

    mx.cmd(mc.select, ctrls)
