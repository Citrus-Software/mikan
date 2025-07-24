# coding: utf-8

import os
import zlib
import json
import base64
import winreg
import itertools
import subprocess
from copy import deepcopy
from contextlib import suppress

import meta_nodal_py as kl
from meta_nodal_py.Imath import V3f, Color4f

from mikan.core.utils import re_is_int
from mikan.core.logger import create_logger
from mikan.tangerine.lib.commands import ls, add_plug
from mikan.tangerine.lib.connect import connect_sub, safe_connect

log = create_logger()

__all__ = ['apply_shaders']


def apply_shaders(node):
    """Build and apply the shading network data stored in the 'gem_shaders' plug of the specified node.

   Additionally, this function processes all connections from the rig to the shaders.

    Args:
        node (kl.Node): node with 'gem_shaders' plug
    """

    log.info(f'applying shaders on all objects under {node.get_name()}')

    nodes = ls(root=node, as_dict=True)
    root = kl.Node(node, '_shaders')
    if not node.get_dynamic_plug('gem_shaders'):
        return

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


def winreg_subkeys(path, hkey=winreg.HKEY_LOCAL_MACHINE, flags=0):
    with suppress(WindowsError), winreg.OpenKey(hkey, path, 0, winreg.KEY_READ | flags) as k:
        for i in itertools.count():
            yield winreg.EnumKey(k, i)


def find_imconvert():
    # imconvert lookup

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


imconvert = find_imconvert()
