# coding: utf-8

import re
import glob
import json
import zlib
import base64
import os.path
from six import string_types

import maya.cmds as mc
import maya.mel as mel
import maya.api.OpenMaya as om
from mikan.maya import cmdx as mx

from mikan.core.logger import create_logger
from mikan.core.utils import ordered_load, re_get_keys
from .configparser import ConfigParser
from .geometry import get_hard_edges

__all__ = ['export_shaders', 'transfer_shading', 'get_shading', 'texture_file_nodes_fix_udim']

log = create_logger('mikan.shaders')


# export shading

def export_shaders(node):
    shaders = ShaderData(node)
    shaders.write()
    return shaders.db


def export_hard_edges():
    # hard edges
    smooth0 = []
    for s in mx.ls('smooth0', r=1) or []:
        for geo in s.members():
            if geo.is_a(mx.kShape):
                geo = geo.parent()
            shp = geo.shape(type=mx.tMesh)
            if shp and geo not in smooth0:
                smooth0.append(geo)

    for geo in smooth0:
        edges = get_hard_edges(geo)

        if edges:
            vertices = []
            for e in edges:
                v = mc.polyListComponentConversion(e, fe=1, tv=1)
                for v in mc.ls(v, fl=1):
                    vertices.append(int(re_get_keys.findall(v)[0]))
            if 'gem_hard_edges' in geo and not geo.is_referenced():
                geo.delete_attr(geo['gem_hard_edges'])
            if 'gem_hard_edges' not in geo:
                geo.add_attr(mx.Long('gem_hard_edges', array=True))

            if vertices[0] == 0:
                vertices[:2] = vertices[1::-1]
            if vertices[-1] == 0:
                vertices[-2:] = vertices[-1:-3:-1]

            geo['gem_hard_edges'] = vertices

        else:
            if 'gem_hard_edges' in geo:
                geo.delete_attr('gem_hard_edges')


def _get_shape(node):
    if not isinstance(node, mx.Node):
        node = mx.encode(str(node))
    if node.is_a(mx.tTransform):
        for shp in node.shapes():
            if not shp['io'].read():
                return shp
    elif node.is_a(mx.kShape):
        return node


def get_shading(src):
    if not isinstance(src, mx.Node):
        src = mx.encode(str(src))
    shp_src = _get_shape(src)

    if not shp_src:
        log.error('/!\\ cannot get shading from {}'.format(src))
        return

    sgs = []
    indices = []
    for i in shp_src['instObjGroups'].array_indices:
        sgs += shp_src['instObjGroups'][i].outputs(type=mx.tShadingEngine)
        sgs += shp_src['instObjGroups'][i]['objectGroups'].outputs(type=mx.tShadingEngine)

        multi = shp_src['instObjGroups'][i]['objectGroups'].array_indices
        if multi:
            _sgs = []
            for j in multi:
                _sgs += shp_src['instObjGroups'][i]['objectGroups'][j].outputs(type=mx.tShadingEngine)
                indices.append(mc.getAttr(shp_src['instObjGroups'][i]['objectGroups'][j]['objectGrpCompList'].path()))
            if _sgs:
                sgs = _sgs

    return sgs


def transfer_shading(src, dst):
    if not isinstance(src, mx.Node):
        src = mx.encode(str(src))
    if not isinstance(dst, mx.Node):
        dst = mx.encode(str(dst))
    shp_src = _get_shape(src)
    shp_dst = _get_shape(dst)

    if not shp_src or not shp_dst:
        log.error('/!\\ cannot transfer shading from {} to {}'.format(src, dst))
        return

    sgs = []
    indices = []
    for i in shp_src['instObjGroups'].array_indices:
        sgs += shp_src['instObjGroups'][i].outputs(type=mx.tShadingEngine)
        sgs += shp_src['instObjGroups'][i]['objectGroups'].outputs(type=mx.tShadingEngine)

        multi = shp_src['instObjGroups'][i]['objectGroups'].array_indices
        if multi:
            _sgs = []
            for j in multi:
                _sgs += shp_src['instObjGroups'][i]['objectGroups'][j].outputs(type=mx.tShadingEngine)
                indices.append(mc.getAttr(shp_src['instObjGroups'][i]['objectGroups'][j]['objectGrpCompList'].path()))
            if _sgs:
                sgs = _sgs
            else:
                multi = []

    if sgs:
        for i in shp_dst['instObjGroups'].array_indices:
            for sg_in in shp_dst['instObjGroups'][i].outputs(plugs=True, type=mx.tShadingEngine):
                shp_dst['instObjGroups'][i] // sg_in

        if not multi:
            mc.sets(str(shp_dst), e=1, forceElement=str(sgs[0]))
        else:
            for i in range(len(sgs)):
                for j in range(len(indices[i])):
                    mc.sets('{}.{}'.format(dst, indices[i][j]), e=True, forceElement=str(sgs[i]))

    else:
        log.error('/!\\ cannot transfer shading from {} to {}'.format(src, dst))


"""
from mikan.maya.lib.shaders import texture_file_nodes_fix_udim
texture_file_nodes_fix_udim()
"""


def texture_file_nodes_fix_udim():
    for node in mc.ls(type='file'):
        path = mc.getAttr(node + '.fileTextureName')

        split_tmp = path.split('.')
        if len(split_tmp) > 2:
            udim = split_tmp[-2]
            if udim == '1001':
                mc.setAttr(node + '.uvTilingMode', 3)
                mel.eval('generateUvTilePreview {};'.format(node))


class ShaderData(object):

    def __init__(self, node):
        if not isinstance(node, mx.Node):
            node = mx.encode(str(node))
        self.node = node

        self.db = {}
        self.read()

    def read(self):

        # geo loop
        processed = set()

        for shp in self.node.descendents(type=mx.tMesh):
            if shp in processed or shp['io'].read():
                continue

            for i in shp['instObjGroups'].array_indices:
                sgs = shp['instObjGroups'][i].outputs(type=mx.tShadingEngine)
                sgs = [sg for sg in sgs if sg]
                if not sgs:
                    continue
                sg = sgs[0]
                mat = sg['surfaceShader'].input()

                mdb = self.read_material(mat)

                # add assignation
                if shp.isInstanced():
                    geo = None
                    for dag in om.MDagPath.getAllPathsTo(shp.object()):
                        if dag.instanceNumber() == i:
                            geo = dag.partialPathName()
                            geo = '|'.join(geo.split('|')[:-1])
                            break
                    if not geo:
                        continue
                else:
                    geo = str(shp.parent())

                if geo not in mdb['meshs']:
                    mdb['meshs'].add(str(geo))

            processed.add(shp)

        # freeze sets
        for k in self.db:
            if 'meshs' in self.db[k] and self.db[k]['meshs']:
                self.db[k]['meshs'] = list(self.db[k]['meshs'])

    def write(self):

        # store data
        if 'gem_shaders' not in self.node:
            self.node.add_attr(mx.String('gem_shaders'))

        data = json.dumps(self.db)
        data = base64.b64encode(zlib.compress(data.encode('utf-8'), 9)).decode('utf-8')
        self.node['gem_shaders'] = data

    def read_material(self, mat):

        # get entry
        if str(mat) in self.db:
            return self.db[str(mat)]
        else:
            self.db[str(mat)] = mdb = {}
            mdb['meshs'] = set()

        # process material
        mdb['shading'] = 'basic'
        _nt = mat.type_name
        if _nt in {'lambert', 'phong', 'blinn', 'anisotropic'}:
            mdb['shading'] = 'universal'

        # base shaders
        if _nt in {'lambert', 'phong', 'blinn', 'anisotropic'}:

            # diffuse
            _c = mat['color'].read()
            mdb['color_diffuse'] = self.round_list(self.rgb_to_srgb(_c), 3)

            f = mat['color'].input()
            if f and f.is_a(mx.tFile):
                mdb['file'] = self.get_file_data(f)

                _c = f['defaultColor'].read()
                mdb['color_diffuse'] = ShaderData.round_list(ShaderData.rgb_to_srgb(_c), 3)

            elif f and f.is_a('layeredTexture'):
                mdb['file'] = self.get_layered_file_data(f)

            elif f and f.is_a(mx.tBlendColors):
                mdb['file'] = self.get_blend_file_data(f)

            elif f and f.type_name == 'pxrTexture':
                mdb['file'] = self.get_filename_data(f['filename'])
                del mdb['color_diffuse']

            else:
                mdb['color_diffuse'] = self.get_rgb_data(mat['color'])

            # other attributes
            _c = mx.Vector(mat['ambientColor'].as_vector() + mat['incandescence'].as_vector())
            mdb['color_ambient'] = self.round_list(self.rgb_to_srgb(_c), 3)
            mdb['color_specular'] = [0, 0, 0]

            # transparency
            _t = self.round_list(mat['transparency'].read(), 3)
            f = mat['transparency'].input()
            if f:
                _t = [0, 0, 0]
            _t = (_t[0] + _t[1] + _t[2]) / 3
            if _t > 0:
                mdb['transparency'] = _t
                mdb['transparent'] = True

            for dim in 'RGB':
                f = mat['transparency' + dim].input(plug=True)
                if f is not None:
                    if f.node() == self.node:
                        mdb['transparency'] = f.name(long=False)
                        break

        # specular shaders
        if _nt in {'phong', 'blinn', 'anisotropic'}:

            # other attributes
            _c = mat['specularColor'].read()
            mdb['color_specular'] = self.round_list(self.rgb_to_srgb(_c), 3)
            mdb['specular_coef'] = 10
            if _nt == 'blinn':
                e = mat['eccentricity'].read()
                mdb['specular_coef'] = 4 / e if e else 10
            elif _nt == 'phong':
                mdb['specular_coef'] = mat['cosinePower'].read() * 2
            if _nt == 'anisotropic':
                r = mat['roughness'].read()
                mdb['specular_coef'] = 4 / r if r else 10

        # flat shaders
        if _nt == 'surfaceShader':
            _c = mat['outColor'].read()
            mdb['color_diffuse'] = self.round_list(self.rgb_to_srgb(_c), 3)

        # custom notes
        cfg = ConfigParser(mat)['shader'].read()
        if cfg:
            cfg = ordered_load(cfg)
            if isinstance(cfg, dict):
                if 'transparency' in cfg:
                    mdb['transparency'] = cfg['transparency']
                    mdb['transparent'] = True

                if 'double_sided' in cfg:
                    mdb['backface_culling'] = not bool(cfg['double_sided'])
                if 'double-sided' in cfg:
                    mdb['backface_culling'] = not bool(cfg['double-sided'])
                if 'backface_culling' in cfg:
                    mdb['backface_culling'] = bool(cfg['backface_culling'])
                if 'backface-culling' in cfg:
                    mdb['backface_culling'] = bool(cfg['backface-culling'])

                if 'alpha_layer' in cfg:
                    mdb['alpha_layer'] = int(cfg['alpha_layer'])

        # exit
        return mdb

    @staticmethod
    def round_list(array, decimals=4):
        new = []
        for i, v in enumerate(array):
            new.append(round(v, decimals))
        return new

    @staticmethod
    def rgb_to_srgb(color):
        return [pow(c if c > 0 else 0, 0.4545) for c in color]

    @staticmethod
    def srgb_to_rgb(color):
        return [pow(c, 2.2) for c in color]

    @staticmethod
    def get_rgb_data(plug):
        if not isinstance(plug, mx.Plug):
            plug = mx.encode(str(plug))

        plug_input = plug.input(plug=True)
        if plug_input is not None:
            plug_node = plug_input.node()
            choice = None

            if plug_node.is_a(mx.tChoice):
                choice = plug_node

            # choice lookup loopback
            _i = plug_input.input(type=mx.tChoice)
            if _i:
                choice = _i

            if choice:
                data = ShaderData.get_choice_data(choice)
                # TODO: si pas de filepath, retourner la connexion du premier input si plug_node est self.geo
                return data

        return plug.read()

    @staticmethod
    def get_filename_data(plug):
        if not isinstance(plug, mx.Plug):
            plug = mx.encode(str(plug))

        plug_input = plug.input(plug=True)
        if plug_input is not None:
            plug_node = plug_input.node()
            choice = None

            if plug_node.is_a(mx.tChoice):
                choice = plug_node

            # choice lookup loopback
            _i = plug_input.input(type=mx.tChoice)
            if _i:
                choice = _i

            if choice:
                return ShaderData.get_choice_data(choice)

        path = plug.read()
        if os.path.isfile(path):
            path = os.path.realpath(path)
        return path

    @staticmethod
    def get_choice_data(choice, switch=None):
        """Read the data stored in a choice node

        Args:
            choice (mx.Node): the choice node
            switch (mx.Node, optional):

        Returns:
            dict: generated data
        """

        data = {}

        # hacked choice (switch bridge)
        if 'value' in choice:
            s = choice['value'].input(plug=True)
            data['plug'] = s.name(long=False)
            return data

        # switch data
        s = choice['selector'].input(plug=True)
        if isinstance(s, mx.Plug) and s.node().is_a(mx.tChoice):
            s = s.node()['selector'].input(plug=True)

        if isinstance(s, mx.Plug):
            if s.node() == switch or switch is None:
                data['plug'] = s.name(long=False)

        for j in choice['input'].array_indices:
            data[j] = choice['input'][j].read()
            _i = choice['input'][j].input(plug=True)
            if _i is not None:
                data[j] = _i.read()

            if isinstance(data[j], string_types) and os.path.isfile(data[j]):
                data[j] = os.path.realpath(data[j])

        return data

    def get_file_data(self, f):

        data = ShaderData.get_filename_data(f['ftn'])

        # parse file sequence
        if f['useFrameExtension'].read():

            # get file list
            pattern = r'(\d+)(?=\.[^.]*$)'
            search_pattern = re.sub(pattern, '*', data)

            file_data = {}
            for file_path in glob.glob(search_pattern):
                match = re.search(pattern, file_path)
                if match:
                    frame_number = int(match.group(1))
                    file_data[frame_number] = file_path

            # get anim plug
            frame_plug = f['frameExtension'].input(plug=True)
            if frame_plug is not None:
                frame_node = frame_plug.node()

                if frame_node.is_a(mx.tChoice):
                    _data = ShaderData.get_choice_data(frame_node, switch=self.node)
                    if 'plug' in _data:
                        file_data['plug'] = _data['plug']

                elif frame_node == self.node:
                    file_data['plug'] = frame_plug.name(long=False)

            data = file_data

        return data

    def get_layered_file_data(self, layer):
        data = {}
        data['layers'] = {}

        for i in layer['inputs'].array_indices:
            # color base
            f = layer['inputs'][i]['color'].input()
            if f and f.is_a(mx.tFile):
                data[i] = self.get_filename_data(f['ftn'])

            elif f and f.type_name == 'pxrTexture':
                data[i] = self.get_filename_data(f['filename'])

            # alpha blend
            data['layers'][i] = layer['inputs'][i]['alpha'].read()

            a = layer['inputs'][i]['alpha'].input(plug=True)
            if isinstance(a, mx.Plug):
                if a.node() == self.node:
                    data['layers'][i] = a.name(long=False)

        return data

    def get_blend_file_data(self, blend):
        data = {}
        data['layers'] = {}

        # base
        f = blend['color1'].input()
        if f and f.is_a(mx.tFile):
            data[0] = self.get_filename_data(f['ftn'])

        elif f and f.type_name == 'pxrTexture':
            data[0] = self.get_filename_data(f['filename'])

        # layer
        f = blend['color2'].input()
        if f and f.is_a(mx.tFile):
            data[1] = self.get_filename_data(f['ftn'])

        elif f and f.type_name == 'pxrTexture':
            data[1] = self.get_filename_data(f['filename'])

        # alpha blend
        data['layers'][0] = blend['blender'].read()
        data['layers'][1] = 1 - blend['blender'].read()

        a = blend['blender'].input(plug=True)
        if isinstance(a, mx.Plug):
            if a.node() == self.node:
                data['layers'][0] = a.name(long=False)

        # TODO: faire un scan recursif si on chaine les blend

        return data
