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

__all__ = [
    'export_shaders', 'transfer_shading', 'get_shading', 'texture_file_nodes_fix_udim',
    'export_materials', 'TangerineMaterialData'
]

log = create_logger('mikan.shaders')


# export shading

def export_shaders(node):
    shaders = ShaderData(node)
    shaders.write()
    return shaders.db


def export_materials(node):
    data = TangerineMaterialData(node)
    data.write()
    return data.db


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
    """deprecated"""

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


def round_list(array, decimals=4):
    new = []
    for i, v in enumerate(array):
        new.append(round(v, decimals))
    return new


def linear_to_srgb(color):
    return [pow(c if c > 0 else 0, 0.4545) for c in color]


class TangerineMaterialData(object):

    def __init__(self, node):
        if not isinstance(node, mx.Node):
            node = mx.encode(str(node))

        self.node = node
        self.db = {}

        self.read()

    def read(self):
        processed_shapes = set()

        for shape in self.node.descendents(type='mesh'):

            if shape in processed_shapes:
                continue

            if shape['io'].read():
                continue

            for i in shape['instObjGroups'].array_indices:
                sgs = shape['instObjGroups'][i].outputs(type='shadingEngine')
                sgs = [sg for sg in sgs if sg]  # Filter None

                if not sgs:
                    continue

                sg = sgs[0]

                material = sg['surfaceShader'].input()
                if not material:
                    continue

                mat_data = self._get_material_data(material)

                geo_path = self._resolve_geo_path(shape, instance_index=i)
                if geo_path:
                    mat_data['meshs'].add(geo_path)

            processed_shapes.add(shape)

        # burn sets
        for k in self.db:
            if 'meshs' in self.db[k]:
                self.db[k]['meshs'] = list(self.db[k]['meshs'])

    def write(self):
        if 'gem_materials' not in self.node:
            self.node.add_attr(mx.String('gem_materials'))

        # Sérialisation identique à l'original
        json_data = json.dumps(self.db)
        compressed_data = base64.b64encode(zlib.compress(json_data.encode('utf-8'), 9)).decode('utf-8')

        self.node['gem_materials'] = compressed_data

    def _resolve_geo_path(self, shape, instance_index):
        geo_path = None

        if shape.isInstanced():
            mobj = shape.object()

            for dag_path in om.MDagPath.getAllPathsTo(mobj):
                if dag_path.instanceNumber() == instance_index:
                    full_path = dag_path.fullPathName()
                    geo_path = '|'.join(full_path.split('|')[:-1])
                    break
        else:
            geo_path = str(shape.parent())

        return geo_path

    def _get_material_data(self, material):
        mat_name = str(material)
        mat_data = self.parse_material(material)

        if mat_name not in self.db:
            self.db[mat_name] = {
                'meshs': set(),
                'shader': mat_data,
            }

        return self.db[mat_name]

    # -- materials
    def parse_material(self, material_node):
        # Base dict
        data = {
            'type': 'basic',
        }

        nt = material_node.type_name

        # -- Standard Shaders
        if nt in {'lambert', 'phong', 'blinn', 'anisotropic'}:
            _data = self.resolve_color_alpha(material_node['color'], material_node['transparency'])
            if isinstance(_data, dict):
                data.update(_data)

        # -- Flat Shaders
        elif nt == 'surfaceShader':
            _data = self.resolve_color_alpha(material_node['outColor'], material_node['outTransparency'])
            if isinstance(_data, dict):
                data.update(_data)

        # -- Custom Attributes (Notes / ConfigParser)
        cfg = ConfigParser(material_node)['shader'].read()
        if not cfg:
            return data

        cfg = ordered_load(cfg)
        if not isinstance(cfg, dict):
            return data

        for k in cfg:
            _k = k.replace('-', '_').strip()

            if k == 'transparency':
                material_node['transparency'] = cfg[k]
                material_node['transparent'] = True
            elif _k == 'double_sided':
                material_node['backface_culling'] = not bool(cfg[k])
            elif _k == 'backface_culling':
                material_node['backface_culling'] = bool(cfg[k])
            elif _k == 'alpha_layer':
                material_node['alpha_layer'] = int(cfg[k])

        return data

    def resolve_color_alpha(self, color_plug, alpha_plug=None, depth=0):
        depth += 1
        data = {}

        color_data = self.resolve_plug(color_plug, depth=depth)

        if 'layers' in color_data:
            return color_data

        if isinstance(color_data, dict) and ('file' in color_data or 'skia' in color_data):
            data.update(color_data)
        else:
            data['color'] = color_data

        # get alpha
        alpha = 1.0

        if alpha_plug:
            alpha_data = self.resolve_plug(alpha_plug, depth=depth)

            if isinstance(alpha_data, dict) and 'choice' in alpha_data:
                alpha = alpha_data

            elif isinstance(alpha_data, (int, float)):
                alpha = alpha_data
            elif isinstance(alpha_data, (list, tuple)):
                alpha = 1 - round(max(0.0, min(alpha_data)), 3)

        data['alpha'] = alpha
        return data

    def resolve_plug(self, plug, depth=0):
        if not isinstance(plug, mx.Plug):
            return

        depth += 1
        input_node = plug.input()

        # flat value
        if not input_node:
            value = plug.read()
            if isinstance(value, (list, tuple)) and len(value) == 3:
                return round_list(linear_to_srgb(value), 3)
            return value

        # upward connection
        nt = input_node.type_name

        if nt in {'file', 'pxrTexture'}:
            return self._get_file_data(input_node, depth=depth)

        elif nt == 'layeredTexture':
            if depth <= 2:
                return self._get_layered_data(input_node, depth=depth)
            else:
                log.warning('cannot resolve layered texture at depth {}'.format(depth))

        elif nt == 'blendColors':
            if depth <= 2:
                return self._get_blend_data(input_node, depth=depth)
            else:
                log.warning('cannot resolve blend colors at depth {}'.format(depth))

        elif nt == 'choice':
            return self._resolve_choice_node(input_node, depth=depth)

        elif nt == 'skiaTexture':
            return self._get_skia_data(input_node)

        elif nt == 'projection':
            # TODO: projection
            return {}

        elif nt == 'transform':
            input_plug = plug.input(plug=True)
            return {'plug': input_plug.name()}

        # fallback
        input_plug = plug.input(plug=True)
        value = input_plug.read()
        if isinstance(value, (list, tuple)) and len(value) == 3:
            return round_list(linear_to_srgb(value), 3)
        return value

    def _get_file_data(self, node, depth=0):
        depth += 1

        # get raw path
        plug = None
        if node.type_name == 'file':
            plug = node['fileTextureName']
        elif node.type_name == 'pxrTexture':
            plug = node['filename']

        if not isinstance(plug, mx.Plug):
            return

        path = plug.read()
        if path and os.path.isfile(path):
            path = os.path.realpath(path)

        data = {'file': path}

        # default color
        if node.type_name == 'file':
            data['color'] = self.resolve_plug(node['defaultColor'])

        # connected filename
        input_node = plug.input()
        if input_node:
            input_fn = self.resolve_plug(plug, depth=depth)
            if isinstance(input_fn, dict) and 'switch' in input_fn:
                data['color'] = {'plug': input_fn['plug'], 'switch': {}}
                data['file'] = {'plug': input_fn['plug'], 'switch': {}}
                for k in input_fn['switch']:
                    _k = input_fn['switch'][k]
                    if 'color' in _k:
                        data['color']['switch'][k] = _k['color']
                    if 'file' in _k:
                        data['file']['switch'][k] = _k['file']
            else:
                data['file'] = input_fn

        # image sequence
        use_frame_ext = False
        if node.type_name == 'file' and node['useFrameExtension'].read():
            use_frame_ext = True

        if use_frame_ext:
            # TODO: faire la récursion choice/sequence quand y'a un input à ftn en envoyant seq_data à choice

            pattern_regex = r'(\d+)(?=\.[^.]*$)'
            search_pattern = re.sub(pattern_regex, '*', path)

            seq_data = {}
            found_files = glob.glob(search_pattern)

            if found_files:
                for file_path in found_files:
                    match = re.search(pattern_regex, file_path)
                    if match:
                        frame_num = int(match.group(1))
                        seq_data[frame_num] = file_path

                frame_plug = node['frameExtension'].input(plug=True)
                if frame_plug:
                    seq_data['plug'] = frame_plug.name(long=False)

                return {'file': seq_data}

        return data

    def _get_layered_data(self, node, depth=0):
        depth += 1
        data = {'layers': {}, 'blends': {}}

        remove_ids = []

        for i in node['inputs'].array_indices:
            layer_input = node['inputs'][i]
            data['layers'][i] = {}
            data['blends'][i] = {}

            color = self.resolve_plug(layer_input['color'], depth=depth)
            alpha = self.resolve_plug(layer_input['alpha'], depth=depth)

            if 'layers' in color:
                log.warning('invalid layer entry at {} ({})'.format(i, node))
                continue

            if 'file' in color or 'skia' in color:
                data['layers'][i] = color
                data['blends'][i] = 1.0
                if not isinstance(alpha, dict) or 'file' not in alpha and 'skia' not in alpha:
                    data['blends'][i] = alpha
            else:
                data['layers'][i] = {'color': color, 'alpha': 1.0}
                data['blends'][i] = 1.0
                if not isinstance(alpha, dict) or 'plug' in alpha:
                    data['blends'][i] = alpha

                if isinstance(alpha, dict) and 'file' in alpha:
                    log.warning('invalid alpha entry at index {} of {}: {}'.format(i, node, alpha))
                    remove_ids.append(i)

            if alpha == 0:
                remove_ids.append(i)

        for i in remove_ids:
            del data['layers'][i]
            del data['blends'][i]

        return data

    def _get_blend_data(self, node, depth=0):
        depth += 1
        data = {'layers': {}, 'blends': {}}

        # Layer 1 (Top) -> input 1
        data['layers'][0] = self.resolve_plug(node['color1'], depth=depth)

        # Layer 2 (Base) -> input 2
        data['layers'][1] = self.resolve_plug(node['color2'], depth=depth)

        # alpha blend
        data['blends'][0] = self.resolve_plug(node['blender'], depth=depth)

        # TODO: compiler les blend récursif sur un unique layer
        return data

    def _resolve_choice_node(self, node, depth=0):
        data = {'switch': {}}

        selector = self.resolve_plug(node['selector'], depth=depth)
        if isinstance(selector, dict):
            data.update(selector)
        else:
            data['plug'] = selector

        # TODO: compiler les selector connecté avec un autre choice

        for i in node['input'].array_indices:
            value = self.resolve_plug(node['input'][i], depth=depth)
            if value is not None:
                data['switch'][i] = value

        return data

    def _get_skia_data(self, node):
        root = node['rm'].input()
        if not root:
            return

        data = {}
        data['skia'] = str(root)
        return data
