# coding: utf-8

import maya.cmds as mc
import maya.api.OpenMaya as om
import maya.api.OpenMayaAnim as oma
import mikan.maya.cmdx as mx

from mikan.core.logger import create_logger
from mikan.maya.core import Deformer, WeightMap, DeformerGroup

from mikan.vendor.Qt.QtCore import Qt
from mikan.vendor.Qt.QtGui import QColor
from mikan.vendor.Qt.QtWidgets import QPushButton, QListWidget, QListWidgetItem

from mikan.core.ui.widgets import StackWidget, Icon
from mikan.maya.ui.widgets import MayaWindow, Callback

from mikan.maya.lib.geometry import Mesh, get_meshes

log = create_logger()

__all__ = ['AssignDeformerHandlesUI']


class AssignDeformerHandlesUI(MayaWindow):
    ui_width = 256
    ui_height = 256

    dfm_types = {
        'cluster': mx.tCluster,
        'softMod': mx.tSoftMod,
        'nonLinear': mx.tNonLinear,
        'ffd': mx.tFfd
    }

    def __init__(self, parent=None):
        MayaWindow.__init__(self, parent)
        self.setWindowTitle('Assign deformer handles')
        self.setWindowFlags(Qt.Tool)
        self.resize(self.ui_width, self.ui_height)
        # self.setMinimumWidth(self.ui_width)
        # self.setMinimumHeight(self.ui_height)

        self.stack = StackWidget()
        self.setCentralWidget(self.stack)

        col = self.stack.add_column(margins=0, spacing=0)
        row = self.stack.add_row(parent=col, margins=2, spacing=2)

        btn_reload = QPushButton()
        btn_reload.setIcon(Icon('reload', color='#ddd'))
        btn_reload.setMaximumWidth(24)
        btn_reload.setMaximumHeight(23)

        btn_add = QPushButton('assign')
        btn_sub = QPushButton('remove')
        row.addWidget(btn_reload, )
        row.addWidget(btn_add)
        row.addWidget(btn_sub)

        self.handles = QListWidget()
        col.addWidget(self.handles, stretch=1)

        btn_add.clicked.connect(Callback(self.assign_selection))
        btn_sub.clicked.connect(Callback(self.remove_selection))
        btn_reload.clicked.connect(Callback(self.reload))

        self.load()

    def load(self):
        """Fill deformer list with valid deformer handles"""

        # clusters
        handles = []
        for dfm in mx.ls(et='cluster'):
            if 'gem_protected' in dfm:
                continue

            h = dfm['matrix'].input()
            handles.append(h)

        if handles:
            self.add_header('- cluster')
        for h in handles:
            self.add_handle(str(h), 'cluster')

        # soft mods
        handles = []
        for dfm in mx.ls(et='softMod'):
            if 'gem_protected' in dfm:
                continue

            h = dfm['matrix'].input()
            handles.append(h)

        if handles:
            self.add_header('- softMod')
        for h in handles:
            self.add_handle(str(h), 'softMod')

        # non linears
        handles = []
        for dfm in mx.ls(et='nonLinear'):
            if 'gem_protected' in dfm:
                continue

            h = dfm['matrix'].input()
            handles.append(h)

        if handles:
            self.add_header('- nonLinear')
        for h in handles:
            self.add_handle(str(h), 'nonLinear')

        # ffds
        ffds = []
        for dfm in mx.ls(et='ffd'):
            if 'gem_protected' in dfm:
                continue

            shp = dfm['deformedLatticeMatrix'].input()
            if not shp:
                continue
            ffl = shp.parent()
            ffds.append(ffl)

        if ffds:
            self.add_header('- ffd')
        for ffd in ffds:
            self.add_handle(str(ffd), 'ffd')

    def add_header(self, text):
        item = QListWidgetItem(text)
        item.setBackground(QColor("#444"))
        item.setFlags(item.flags() & ~Qt.ItemIsSelectable)
        self.handles.addItem(item)

    def add_handle(self, text, nodetype):
        item = QListWidgetItem(text)
        item._type = nodetype
        self.handles.addItem(item)

    def reload(self):
        self.handles.clear()
        self.load()

    def get_selection(self):
        selection = {}

        for node in mc.ls(sl=True, fl=True):
            cp = None
            if '.' in node:
                node, _, cp = node.partition('.')

            geo = mx.encode(node)
            if geo not in selection:
                selection[geo] = set()

            if cp and 'vtx' in cp:
                cp = int(cp.split('[')[-1].split(']')[0])
                selection[geo].add(cp)

        return selection

    def assign_selection(self):
        selection = self.get_selection()

        for item in self.handles.selectedItems():
            handle = mx.encode(item.text())
            t = item._type

            dfm = handle.output(type=self.dfm_types[t])
            if not dfm:
                for shp in handle.shapes():
                    dfm = shp.output(type=self.dfm_types[t])
                    if dfm:
                        break

            if dfm:
                for geo in selection:
                    # assign deformer
                    try:
                        _dfm = Deformer.create(geo, dfm)
                    except:
                        mc.deformer(str(dfm), e=1, g=str(geo))
                        _dfm = Deformer.create(geo, dfm)

                    # update geommatrix
                    if 'geomMatrix' in _dfm.node:
                        fn = oma.MFnGeometryFilter(_dfm.node.object())
                        oid = int(fn.indexForOutputShape(_dfm.geometry.object()))
                        _dfm.transform['wm'][0] >> _dfm.node['geomMatrix'][oid]

                    # assign components
                    cps = selection[geo]
                    if cps:
                        if 'membership' not in _dfm.data:
                            membership = [0] * _dfm.get_size()
                            _dfm.data['membership'] = WeightMap(membership)
                        for cp in cps:
                            _dfm.data['membership'].weights[cp] = 1
                        _dfm.write_membership()

    def remove_selection(self):
        selection = self.get_selection()

        for item in self.handles.selectedItems():
            item = item.text()
            t, node = item.split(': ')

            handle = mx.encode(node)
            dfm = handle.output(type=self.dfm_types[t])
            if not dfm:
                for shp in handle.shapes():
                    dfm = shp.output(type=self.dfm_types[t])
                    if dfm:
                        break

            if dfm:
                for geo in selection:
                    try:
                        _dfm = Deformer.create(geo, dfm)
                    except:
                        continue

                    cps = selection[geo]
                    if cps:
                        if 'membership' not in _dfm.data:
                            membership = [1] * _dfm.get_size()
                            _dfm.data['membership'] = WeightMap(membership)
                        for cp in cps:
                            _dfm.data['membership'].weights[cp] = 0
                        _dfm.write_membership()
                    else:
                        mc.deformer(str(dfm), e=1, rm=1, g=str(geo))


"""
# For test
from mikan.maya.utils.deformer_utils import get_influenced_vertices_from_jnt                       
jnt_info = get_influenced_vertices_from_jnt( ['sk_B','sk_A'], ['msh_sphere'], min_inf = 0.1 ) 
mc.select(jnt_info['sk_B'])                    
"""


def get_influenced_vertices_from_jnt(in_jnts, meshes, min_inf=0.1, scene_dfms=None):
    jnt_to_influenced_vertices = {in_jnt: [] for in_jnt in in_jnts}

    if scene_dfms is None:
        scene_dfms = []
        meshes = get_meshes(meshes)
        for mesh in meshes:
            grp = DeformerGroup.create(mesh)
            scene_dfms += grp.data

    for dfm in scene_dfms:
        for in_jnt in in_jnts:
            infs = [dfm.data['infs'][inf].split(' ')[1] for inf in dfm.data['infs']]
            if in_jnt in infs:
                j = infs.index(in_jnt)
                for i in range(len(dfm.data['maps'][j].weights)):
                    if min_inf < dfm.data['maps'][j].weights[i]:
                        jnt_to_influenced_vertices[in_jnt].append('{}.vtx[{}]'.format(dfm.geometry, i))

    return jnt_to_influenced_vertices


def get_influenced_points_from_jnt(in_jnts, meshes, min_inf=0.1, scene_dfms=None):
    jnt_info = get_influenced_vertices_from_jnt(in_jnts, meshes, min_inf=min_inf, scene_dfms=scene_dfms)
    jnt_to_pts = {in_jnt: [] for in_jnt in in_jnts}

    for in_jnt in in_jnts:

        meshes_to_indices = {}
        for j_info in jnt_info[in_jnt]:
            mesh_tmp, idx_tmp = j_info.split('.vtx[')
            idx_tmp = idx_tmp[:-1]
            meshes_to_indices.setdefault(mesh_tmp, [])
            meshes_to_indices[mesh_tmp].append(int(idx_tmp))

        pts = []
        for mesh in meshes_to_indices:
            mesh_pts = Mesh(mesh).get_points(space=mx.sWorld)
            for i in meshes_to_indices[mesh]:
                pts.append(om.MPoint(mesh_pts[i][0], mesh_pts[i][1], mesh_pts[i][2]))

        jnt_to_pts[in_jnt] = pts

    return jnt_to_pts
