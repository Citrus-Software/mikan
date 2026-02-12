# coding: utf-8

import os
import re
import zlib
import json
import base64
import itertools
import subprocess
from copy import deepcopy
from contextlib import suppress

if os.name == 'nt':
    import winreg

import meta_nodal_py as kl
from meta_nodal_py.Imath import V3f, Color4f

from mikan.core.utils import re_is_int
from mikan.core.logger import create_logger
from mikan.core.utils.yamlutils import ordered_load
from mikan.tangerine.lib.commands import ls, add_plug, find_root
from mikan.tangerine.lib.connect import connect_sub, safe_connect
from mikan.tangerine.lib.configparser import ConfigParser

log = create_logger()

__all__ = ['apply_materials', 'apply_shaders']


def apply_materials(node):
    """Build and apply the shading network data stored in the 'gem_materials' plug of the specified node.

    Args:
        node (kl.Node): node with 'gem_materials' plug
    """

    nodes = ls(root=node, as_dict=True)
    root = kl.Node(node, '_materials')
    if not node.get_dynamic_plug('gem_materials'):
        return

    log.info(f'applying materials on all objects under {node.get_name()}')

    # load data from node
    raw_data = node.gem_materials.get_value()
    try:
        raw_data = zlib.decompress(base64.b64decode(raw_data))
        materials_db = json.loads(raw_data)
    except Exception as e:
        log.error(f"Failed to load materials: {e}")
        return

    node.remove_dynamic_plug('gem_materials')

    # build materials
    materials = {}

    for mat_name, mat_data in materials_db.items():
        shader_data = mat_data.get('shader', {})

        # layered shader
        if 'layers' in shader_data:
            layer_plugs = []
            layer_indices = sorted([int(k) for k in shader_data['layers']])

            for i in layer_indices[::-1]:
                layer_content = shader_data['layers'][str(i)]  # json keys are strings

                layer_name = f'{mat_name}_layer{i}'
                shader_plug = _create_shader_plug(layer_name, layer_content, node, root)

                blend_val = shader_data['blends'].get(str(i), 1.0)
                if isinstance(blend_val, dict) and 'plug' in blend_val:
                    blend_plug = node.get_dynamic_plug(blend_val['plug'])
                    if blend_plug is None:
                        blend_plug = add_plug(node, blend_val['plug'], float, min_value=0, max_value=1)
                    blend_val = blend_plug

                layer_plugs.append((shader_plug, blend_val))

            materials[mat_name] = {'type': 'layered', 'plugs': layer_plugs}

        # basic shader
        else:
            shader_plug = _create_shader_plug(mat_name, shader_data, node, root)
            materials[mat_name] = {'type': 'basic', 'plug': shader_plug}

    # assign
    for mat_name, mat_entry in materials_db.items():
        target_meshes = mat_entry.get('meshs', [])
        built_mat = materials.get(mat_name)

        if not built_mat:
            continue

        for mesh_path in target_meshes:
            mesh_path_clean = mesh_path.replace('|', '/')
            mesh_node = nodes.get(mesh_path_clean)

            if not mesh_node:
                log.warning(f'Geometry "{mesh_path_clean}" not found while reading shaders')
                continue

            # get geometries
            geometries = []
            if isinstance(mesh_node, kl.Geometry):
                geometries.append(mesh_node)
            elif isinstance(mesh_node, kl.SceneGraphNode):
                for child in mesh_node.get_children():
                    if isinstance(child, kl.Geometry) and child.show.get_value():
                        geometries.append(child)

            for geo in geometries:
                # connect layered shader
                if built_mat['type'] == 'layered':
                    layers_list = built_mat['plugs']
                    geo.resize_shaders(len(layers_list))

                    for idx, (shd_plug, blend_data) in enumerate(layers_list):
                        geo.shader_in[idx].connect(shd_plug.shader)

                        if kl.is_plug(blend_data):
                            safe_connect(blend_data, geo.shader_enable_in[idx])
                        else:
                            geo.shader_enable_in[idx].set_value(blend_data)

                # connect basic shader
                else:
                    geo.shader_in.connect(built_mat['plug'].shader)


def _create_shader_plug(name, data, rig_node, root_node):
    shader = kl.PlugToShader(root_node, name)

    if 'color' in data:
        _apply_color(shader, data['color'], rig_node)

    if 'file' in data:
        _apply_file(shader, data['file'], rig_node)
    elif 'skia' in data:
        _apply_skia(shader, data['skia'])

    if 'alpha' in data:
        _apply_alpha(shader, data['alpha'], rig_node)

    if 'backface_culling' in data:
        shader.backface_culling.set_value(data['backface_culling'])
    if 'alpha_layer' in data:
        shader.alpha_layer.set_value(int(data['alpha_layer']))

    return shader


def _apply_color(shader, color_data, rig_node):
    # flat value
    if isinstance(color_data, (list, tuple)):
        rgb = list(color_data)
        if len(rgb) == 3:
            rgb.append(1.0)
        shader.filled_color.set_value(Color4f(*rgb))

    # switch
    elif isinstance(color_data, dict) and 'plug' in color_data:

        plug = color_data['plug']
        if isinstance(plug, str):
            plug = rig_node.get_dynamic_plug(color_data['plug'])

        # switch colors
        if 'switch' in color_data:
            switch_node = _build_switch_node(
                rig_node,
                color_data,
                mode='color'
            )
            if switch_node:
                shader.filled_color.connect(switch_node.output)

                if kl.is_plug(plug):
                    switch_node.index.connect(plug)
                elif isinstance(plug, (int, float)):
                    switch_node.index.set_value(plug)

        # color plug
        else:
            _col = kl.FloatToColor4f(shader, '_color_in')
            _v = kl.V3fToFloat(_col, '_rgb')
            _v.vector.connect(plug)
            _col.r.connect(_v.x)
            _col.g.connect(_v.y)
            _col.b.connect(_v.z)
            plug = _col.color

            if kl.is_plug(plug):
                shader.filled_color.connect(plug)


def _apply_file(shader, file_data, rig_node):
    # flat value
    if isinstance(file_data, str):
        file_data = convert_map_to_jpg(file_data)
        shader.diffuse_path.set_value(file_data)

    # switch or sequence
    elif isinstance(file_data, dict) and 'plug' in file_data:
        plug_name = file_data['plug']
        plug = rig_node.get_dynamic_plug(plug_name)

        if 'switch' in file_data:
            switch_node = _build_switch_node(
                rig_node,
                file_data,
                mode='file'
            )

            if switch_node:
                str_to_path = kl.StringToPath(switch_node, 'path')
                str_to_path.input.connect(switch_node.output)
                shader.diffuse_path.connect(str_to_path.output)

                if plug is None:
                    plug = add_plug(rig_node, plug_name, int, keyable=True)

                plug_value = plug.get_value()
                if isinstance(plug_value, int):
                    safe_connect(plug, switch_node.index)

        else:
            plug_value = None
            if plug is not None:
                plug_value = plug.get_value()

            if isinstance(plug_value, str):
                str_to_path = kl.StringToPath(shader, 'path')
                str_to_path.input.connect(plug)
                shader.diffuse_path.connect(str_to_path.output)


def _apply_alpha(shader, alpha_data, rig_node):
    # flat value
    if isinstance(alpha_data, (float, int)):
        shader.opacity.set_value(float(alpha_data))

    # switch
    elif isinstance(alpha_data, dict) and 'plug' in alpha_data:
        # TODO: kl.VectorFloatToFloat
        pass


def _apply_skia(shader, skia_root):
    try:
        skia_builder = SkiaTextureBuild(skia_root)
        skia_texture = skia_builder.node
        if skia_texture:
            texture_provider = kl.TextureProvider(shader, 'texture_provider', 0)
            shader.diffuse_texture.connect(texture_provider.texture_out)
            texture_provider.image.connect(skia_texture.image_out)
    except Exception as e:
        log.warning(f"Failed to build Skia texture: {e}")


def _build_switch_node(rig_node, data, mode='color'):
    if 'switch' not in data:
        return

    keys = [int(k) for k in data['switch'] if k != 'plug' and str(k).isdigit()]
    if not keys:
        return None

    max_index = max(keys)
    switch_plug_name = data['plug']

    if mode == 'color':
        node_type = kl.VectorColor4fToColor4f
    elif mode == 'alpha':
        node_type = kl.VectorFloatToFloat
    elif mode == 'file':
        node_type = kl.VectorStringToString
    else:
        raise RuntimeError()

    switch_node = node_type(max_index + 1, rig_node, switch_plug_name)

    # fill values
    for k in keys:
        val = data['switch'][str(k)]

        if mode == 'color':
            if isinstance(val, (list, tuple)):  # Color
                if len(val) == 3:
                    val = list(val) + [1.0]
                val = Color4f(*val)

        elif mode == 'file':
            if isinstance(val, str):
                val = convert_map_to_jpg(val)

        switch_node.input[k].set_value(val)

    # connect index
    rig_plug = rig_node.get_dynamic_plug(switch_plug_name)
    if not rig_plug:
        rig_plug = add_plug(rig_node, switch_plug_name, int, min_value=0, max_value=max_index)

    safe_connect(rig_plug, switch_node.index)

    return switch_node


def apply_shaders(node):
    """Build and apply the shading network data stored in the 'gem_shaders' plug of the specified node.

    Additionally, this function processes all connections from the rig to the shaders.

    Args:
        node (kl.Node): node with 'gem_shaders' plug
    """

    nodes = ls(root=node, as_dict=True)
    root = kl.Node(node, '_shaders')
    if not node.get_dynamic_plug('gem_shaders'):
        return

    log.info(f'applying shaders on all objects under {node.get_name()}')

    # load data from node
    shaders = node.gem_shaders.get_value()
    shaders = zlib.decompress(base64.b64decode(shaders))
    shaders = json.loads(shaders)
    node.remove_dynamic_plug('gem_shaders')

    # build shaders
    for shader_name, shader_data in shaders.items():

        # split shader data if layers?
        layers = None
        if isinstance(shader_data.get('file'), dict) and 'layers' in shader_data['file']:
            shaders = {}

            layers = shader_data['file']['layers']
            for k in list(layers):
                if re_is_int.match(k):
                    layers[int(k)] = layers.pop(k)
            files = shader_data['file']

            for k in list(files):
                if not re_is_int.match(k):
                    continue
                else:
                    files[int(k)] = files.pop(k)
                _shader_data = deepcopy(shader_data)
                _shader_data['file'] = files[int(k)]
                shaders[int(k)] = _create_plug_to_shader(shader_name, _shader_data, node, root)

            shaders = {i: shaders[key] for i, key in enumerate(sorted(shaders))}
            layers = {i: layers[key] for i, key in enumerate(sorted(layers))}

        else:
            shader = _create_plug_to_shader(shader_name, shader_data, node, root)

        # assign
        for mesh_name in shader_data.get('meshs', []):
            mesh_name = mesh_name.replace('|', '/')
            mesh = nodes.get(mesh_name)
            if not mesh:
                log.warning(f'Geometry "{mesh_name}" not found while reading shaders')
                continue

            meshes = []
            if isinstance(mesh, kl.Geometry):
                meshes.append(mesh)
            elif isinstance(mesh, kl.SceneGraphNode):
                for shp in mesh.get_children():
                    if isinstance(shp, kl.Geometry) and shp.show.get_value():
                        meshes.append(shp)

            for mesh in meshes:
                if not layers:
                    mesh.shader_in.connect(shader.shader)
                else:
                    mesh.resize_shaders(len(shaders))

                    keys = list(shaders)
                    keys.sort()
                    keys = keys[::-1]

                    for k in shaders:
                        mesh.shader_in[keys[k]].connect(shaders[k].shader)
                        v = layers[k]

                        if isinstance(v, str):
                            plug = node.get_dynamic_plug(v)
                            if not plug:
                                plug = add_plug(node, v, float)
                            safe_connect(plug, mesh.shader_enable_in[keys[k]])

                        # elif isinstance(v, (float, int)):
                        #     mesh.shader_enable_in[keys[k]].set_value(v)


def _create_plug_to_shader(shader_name, shader_data, node, root):
    shader = kl.PlugToShader(root, shader_name)

    diffuse_data = {0: {'color': [0.73, 0.73, 0.73, 1]}}
    diffuse_switch = None

    diffuse = shader_data.get('color_diffuse')
    if isinstance(diffuse, str):
        diffuse_data[0]['file'] = diffuse
    if isinstance(diffuse, list) and len(diffuse) in {3, 4}:
        diffuse_data[0]['color'] = diffuse
    elif isinstance(diffuse, dict):
        if 'plug' in diffuse:
            diffuse_switch = diffuse['plug']
        for k in diffuse:
            if not re_is_int.match(k):
                continue
            _diffuse = diffuse[k]
            k = int(k)
            if k not in diffuse_data:
                diffuse_data[k] = {}
            if isinstance(_diffuse, str):
                diffuse_data[k]['file'] = _diffuse
            elif isinstance(_diffuse, list) and len(_diffuse) in {3, 4}:
                diffuse_data[k]['color'] = _diffuse

    color_file = shader_data.get('file')
    if isinstance(color_file, str):
        diffuse_data[0]['file'] = color_file
    elif isinstance(color_file, dict):
        if 'plug' in color_file:
            diffuse_switch = color_file['plug']
        for k in color_file:
            if not re_is_int.match(k):
                continue
            _color_file = color_file[k]
            k = int(k)
            if k not in diffuse_data:
                diffuse_data[k] = {}
            if isinstance(_color_file, str):
                diffuse_data[k]['file'] = _color_file

        if 'layers' in color_file:
            diffuse_layer = max(diffuse_data)

    # conform diffuse data
    for k in diffuse_data:
        _data = diffuse_data[k]
        if 'color' not in _data:
            _data['color'] = [0.73, 0.73, 0.73, 1]
        if 'file' in _data and _data['file']:
            if _data['file'][-3:] not in ('jpg', 'png'):
                _data['file'] = convert_map_to_jpg(_data['file'])
            if _data['color'][0] == _data['color'][1] and _data['color'][0] == _data['color'][2]:
                _data['color'] = get_color_from_file(_data['file'])
        if len(_data['color']) == 3:
            _data['color'].append(1)

    # diffuse rig
    diffuse_data_keys = [k for k in diffuse_data if isinstance(k, int)]
    min_key = min(diffuse_data_keys)

    if diffuse_data_keys:
        color = diffuse_data[min_key]['color']
        shader.filled_color.set_value(Color4f(*color))
        file_path = diffuse_data[min_key].get('file')
        if file_path:
            shader.diffuse_path.set_value(file_path)

    if diffuse_switch:
        n = max(diffuse_data_keys) + 1
        switch_path_node = kl.VectorStringToString(n, shader, 'diffuse_path')
        for k in diffuse_data:
            file_path = diffuse_data[k].get('file')
            if file_path:
                switch_path_node.input[k].set_value(file_path)

        str_to_path = kl.StringToPath(switch_path_node, 'path')
        str_to_path.input.connect(switch_path_node.output)
        shader.diffuse_path.connect(str_to_path.output)

        switch_color_node = kl.VectorColor4fToColor4f(n, shader, 'diffuse_color')
        for k in diffuse_data:
            if diffuse_data[k]['color']:
                _color = Color4f(*diffuse_data[k]['color'])
                switch_color_node.input[k].set_value(_color)

        shader.filled_color.connect(switch_color_node.output)

        plug = node.get_dynamic_plug(diffuse_switch)
        if not plug:
            plug = add_plug(
                node, diffuse_switch, int,
                default_value=min(diffuse_data_keys),
                min_value=min(diffuse_data_keys), max_value=max(diffuse_data_keys)
            )
        safe_connect(plug, switch_path_node.index)
        safe_connect(plug, switch_color_node.index)

    # alpha rig
    alpha = shader_data.get('transparency', 0)
    if isinstance(alpha, str):
        plug = node.get_dynamic_plug(alpha)
        if not plug:
            plug = add_plug(node, alpha, float)
        connect_sub(1, plug, shader.opacity)
    else:
        shader.opacity.set_value(1 - alpha)

    shader.backface_culling.set_value(shader_data.get('backface_culling', True))

    if 'alpha_layer' in shader_data:
        shader.alpha_layer.set_value(int(shader_data['alpha_layer']))
        log.debug(f'set alpha layer to {shader_data["alpha_layer"]} for {shader_name}')

    return shader


def convert_map_to_jpg(path):
    if not os.path.isfile(path):
        return ''

    path_jpg, sep, ext = path.rpartition('.')
    path_jpg += '.jpg'

    if imconvert:

        if os.path.isfile(path_jpg):
            t0 = os.path.getmtime(path)
            t1 = os.path.getmtime(path_jpg)
            if t1 > t0:
                log.debug(f"jpg conversion already done: {path_jpg}")
                return path_jpg

        try:
            log.debug(f"begin conversion to jpg: {path}")
            cmd = [imconvert, path, "-resize", "512x512>", path_jpg]
            fconvert = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = fconvert.communicate()
            assert fconvert.returncode == 0, stderr

            if os.path.isfile(path_jpg):
                log.debug(f"finished conversion")
                return path_jpg
        except:
            pass

    return ''


def get_color_from_file(path):
    gray = [.73, .73, .73]
    if not os.path.isfile(path):
        return gray

    cmd = [imconvert, path, "-resize", "1x1!", "-format", "%[fx:r],%[fx:g],%[fx:b]", "info:-"]
    fconvert = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.DEVNULL)
    stdout, stderr = fconvert.communicate()
    assert fconvert.returncode == 0, stderr

    rgb = stdout.decode('utf-8').strip('\r\n').split(',')
    if len(rgb) == 3:
        try:
            return [float(d) for d in rgb]
        except:
            pass
    return gray


if os.name == 'nt':
    def winreg_subkeys(path, hkey=winreg.HKEY_LOCAL_MACHINE, flags=0):
        with suppress(WindowsError), winreg.OpenKey(hkey, path, 0, winreg.KEY_READ | flags) as k:
            for i in itertools.count():
                yield winreg.EnumKey(k, i)


def find_imconvert():
    # imconvert lookup

    if os.name != 'nt':
        raise NotImplementedError("find_imconvert is only implemented for Windows for now.")

    for key in winreg_subkeys(r'SOFTWARE\Autodesk\Maya'):
        try:
            path = fr'SOFTWARE\Autodesk\Maya\{key}\Setup\InstallPath'
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, path, 0, winreg.KEY_READ | 0)
            maya_path = winreg.QueryValueEx(key, "MAYA_INSTALL_LOCATION")[0]
            path = os.path.sep.join([maya_path, 'bin', 'imconvert.exe'])

            if os.path.isfile(path):
                return path
        except:
            pass


if os.name == 'nt':
    imconvert = find_imconvert()
else:
    imconvert = None  # TODO implement for Linux


def find_skia_roots(root=None, roots=None):
    if roots is None:
        roots = {}
    if root is None:
        root = find_root()

    for node in root.get_children():
        if not isinstance(node, kl.SceneGraphNode):
            continue
        name = node.get_name()
        if name.startswith('__') and name.endswith('__'):
            continue
        if name.startswith('skia'):
            roots[name] = node
        find_skia_roots(node, roots)

    return roots


class SkiaTextureBuild(object):
    KEYS = ('b', 'i', 'f', 'v', 'c', 't', 'm', 'cv')
    pattern = re.compile(r"^<({})\.([A-Za-z_][A-Za-z0-9_]*)>$".format("|".join(map(re.escape, KEYS))))

    @staticmethod
    def is_valid_key(key):
        return bool(SkiaTextureBuild.pattern.match(key))

    def __init__(self, root):
        skia_roots = find_skia_roots()
        root = skia_roots.get(root)
        if not isinstance(root, kl.SceneGraphNode):
            raise ValueError('root is not a valid scene graph node')

        self.root = root
        self.node = kl.SkiaTexture(self.root, 'skia_texture')

        _imx = kl.InverseM44f(self.root, '_imx')
        _imx.input.connect(self.root.world_transform)
        self.node.ref_matrix_in.connect(_imx.output)

        # -- init attributes and json
        self.prefix = 'switch_'

        self.link_root_attributes()
        self.node_names = {}
        self.nodes = []

        self.plugs = {}
        for k in self.KEYS:
            self.plugs[k] = []

        self.update_node()

    def update_node(self):

        # create and connect attributes while walk
        self.build_node_names()
        self.walk(self.root)
        self.link_dag_values(self.nodes)

        # write json
        json_str = json.dumps(self.nodes, indent=2)
        self.node.load_from_json(json_str)

        # connect plugs
        self.connect_plugs()

    def build_node_names(self):
        self.node_names.clear()

        node_names = ls(root=self.root, as_dict=True)
        for node_name, node in node_names.items():
            if isinstance(node, kl.SceneGraphNode):
                self.node_names[node_name] = node

    def walk(self, node, parent_id=None):

        # get node data
        cfg = ConfigParser(node)
        draw = ordered_load(cfg['skia'].read())
        if not isinstance(draw, dict):
            draw = {}

        data = {
            'name': node.get_name(),
            'parent': parent_id,
            'draw': draw,
            'children': []
        }

        # link plugs from config
        data = self.link_values(data, node=node)

        # get geometry data
        shp = None
        for _shp in node.get_children():
            if isinstance(_shp, kl.SplineCurve):
                shp = _shp
                break

        path = None

        # add bezier data
        if shp:
            i = len(self.plugs['cv'])
            self.plugs['cv'].append(shp.spline_in)

            _spline = shp.spline_in.get_value()
            degree = _spline.get_degree()
            if degree == 1:
                path = {'line': '<cv.{}>'.format(i)}
            else:
                path = {'bezier': '<cv.{}>'.format(i)}

        if path:
            if 'path' in draw and isinstance(draw['path'], dict):
                draw['path'].update(path)
            else:
                draw['path'] = path

        # connect transform
        if draw:
            i = len(self.plugs['m'])
            self.plugs['m'].append(node.world_transform)
            data['matrix'] = '<m.{}>'.format(i)

        # defaults
        if 'path' in draw:
            if not any(key.startswith(('stroke', 'fill')) for key in draw):
                draw['stroke.0'] = {}  # default draw for curve

        # register node
        node_id = len(self.nodes)
        self.nodes.append(data)

        # parse children
        for ch in node.get_children():
            if not isinstance(ch, kl.SceneGraphNode):
                continue
            if ch.get_name().startswith('_'):
                continue
            child_id = self.walk(ch, node_id)
            data['children'].append(child_id)

        return node_id

    def link_values(self, v, node=None):

        if isinstance(v, str):
            if not self.is_valid_key(v):
                if v.startswith('<') and v.endswith('>'):
                    log.error('invalid key: {}'.format(v))
                return v

            m = self.pattern.match(v)
            key = m.group(1)
            tag = m.group(2)
            attr = self.prefix + tag

            if node is None:
                raise ValueError('invalid node provided')

            plug = node.get_dynamic_plug(attr)

            if key == 'b':
                if plug is None:
                    plug = add_plug(node, attr, bool, keyable=True)
                i = len(self.plugs[key])
                self.plugs[key].append(plug)
                return '<b.{}>'.format(i)

            if key == 'i':
                if plug is None:
                    plug = add_plug(node, attr, int, keyable=True)
                i = len(self.plugs[key])
                self.plugs[key].append(plug)
                return '<i.{}>'.format(i)

            if key == 'f':
                if plug is None:
                    plug = add_plug(node, attr, float, keyable=True)
                i = len(self.plugs[key])
                self.plugs[key].append(plug)
                return '<f.{}>'.format(i)

            if key == 'v':
                if plug is None:
                    plug = add_plug(node, attr, V3f, keyable=True)
                i = len(self.plugs[key])
                self.plugs[key].append(plug)
                return '<v.{}>'.format(i)

            if key == 'c':
                if plug is None:
                    plug = add_plug(node, attr, V3f, keyable=True)
                i = len(self.plugs[key])
                self.plugs[key].append(plug)
                return '<c.{}>'.format(i)

            if key == 't':
                if plug is None:
                    plug = add_plug(node, attr, str)
                i = len(self.plugs[key])
                self.plugs[key].append(plug)
                return '<t.{}>'.format(i)

            return v

        elif isinstance(v, list):
            for i, e in enumerate(v):
                v[i] = self.link_values(e, node=node)
            return v

        elif isinstance(v, tuple):
            v = [self.link_values(e, node=node) for e in v]
            return tuple(v)

        elif isinstance(v, dict):
            for k, e in v.items():
                v[k] = self.link_values(e, node=node)
            return v

        return v

    def get_next_slot(self, attr):
        i = 0
        ai = self.node[attr].array_indices
        if ai:
            i = max(ai) + 1
        return i

    def link_dag_values(self, v):

        if isinstance(v, str):
            if not self.is_valid_key(v):
                return v

            m = self.pattern.match(v)
            key = m.group(1)
            tag = m.group(2)

            if key == 'm':
                if tag not in self.node_names:
                    log.error('cannot find matrix of "{}"'.format(tag))
                    return

                plug = self.node_names[tag].world_transform
                i = len(self.plugs['m'])
                self.plugs['m'].append(plug)
                return '<m.{}>'.format(i)

            if key == 'cv':
                if tag not in self.node_names:
                    log.error('cannot find curve of "{}"'.format(tag))

                for _data in self.nodes:
                    if _data['name'] == tag:
                        if 'draw' not in _data:
                            continue
                        if 'path' not in _data['draw']:
                            continue
                        for t in ('bezier', 'linear', 'circle', 'rect'):
                            if t in _data['draw']['path']:
                                return _data['draw']['path'][t]
                        break

                log.error('cannot find curve of "{}"'.format(tag))
                return

        elif isinstance(v, list):
            for i, e in enumerate(v):
                v[i] = self.link_dag_values(e)
            return v

        elif isinstance(v, tuple):
            v = [self.link_dag_values(e) for e in v]
            return tuple(v)

        elif isinstance(v, dict):
            for k, e in v.items():
                v[k] = self.link_dag_values(e)
            return v

        return v

    def connect_plugs(self):
        skia_plugs = {
            'b': self.node.bool_in,
            'i': self.node.int_in,
            'f': self.node.float_in,
            'v': self.node.v3f_in,
            'c': self.node.color_in,
            't': self.node.texture_in,
            'm': self.node.world_matrix_in,
            'cv': self.node.spline_in,
        }

        for k in self.plugs:
            for i, plug in enumerate(self.plugs[k]):
                if k == 'c':
                    ftc = kl.FloatToColor3f(self.node, f'_color_in{i}')
                    vtf = kl.V3fToFloat(ftc, '_v3f')

                    vtf.vector.connect(plug)
                    ftc.r.connect(vtf.x)
                    ftc.g.connect(vtf.y)
                    ftc.b.connect(vtf.z)
                    skia_plugs[k][i].connect(ftc.color)

                elif k in {'i', 'f', 'b'}:
                    safe_connect(self.plugs[k][i], skia_plugs[k][i])

                else:
                    skia_plugs[k][i].connect(self.plugs[k][i])

    def link_root_attributes(self):
        plug = self.root.get_dynamic_plug(self.prefix + 'rx')
        if kl.is_plug(plug):
            self.node.width_in.connect(plug)

        plug = self.root.get_dynamic_plug(self.prefix + 'ry')
        if kl.is_plug(plug):
            self.node.height_in.connect(plug)

        plug = self.root.get_dynamic_plug(self.prefix + 'depth')
        if kl.is_plug(plug):
            self.node.depth_in.connect(plug)

        plug = self.root.get_dynamic_plug(self.prefix + 'linear')
        if kl.is_plug(plug):
            self.node.linear_in.connect(plug)
            plug.set_value(0)

        plug = self.root.get_dynamic_plug(self.prefix + 'bgc')
        if kl.is_plug(plug):
            ftc = kl.FloatToColor3f(self.node, '_color_in')
            vtf = kl.V3fToFloat(ftc, '_v3f')

            vtf.vector.connect(plug)
            ftc.r.connect(vtf.x)
            ftc.g.connect(vtf.y)
            ftc.b.connect(vtf.z)
            self.node.background_color_in.connect(ftc.color)

        plug = self.root.get_dynamic_plug(self.prefix + 'bgo')
        if kl.is_plug(plug):
            self.node.background_opacity_in.connect(plug)

        plug = self.root.get_dynamic_plug(self.prefix + 'aa')
        if kl.is_plug(plug):
            self.node.antialiasing_in.connect(plug)
