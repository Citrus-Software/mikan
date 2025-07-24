# coding: utf-8

import maya.cmds as mc
import mikan.maya.cmdx as mx

from mikan.maya.lib.geometry import get_sym_map, get_sym_map_topology
from mikan.maya.core import Deformer, DeformerGroup
from mikan.core.ui.widgets import BusyCursor
from mikan.core.logger import create_logger

if '_gem_sym_tables' not in globals():
    _gem_sym_tables = dict()


def build_mirror_tables():
    log = create_logger()

    with BusyCursor():
        for _obj in mx.ls(sl=True):
            try:
                _gem_sym_tables[_obj] = get_sym_map(_obj)
            except:
                log.error('/!\\ failed to build mirror table for {}'.format(_obj))


def build_mirror_tables_topology():
    log = create_logger()

    with BusyCursor():
        for _obj in mc.ls(sl=True):
            if '.e[' not in _obj:
                log.error('/!\\ invalid selection ({}), you must select the middle edge'.format(_obj))
                continue
            geo = _obj.split('.e[')[0]
            middle_edge = int(_obj.split('.e[')[1][:-1])

            _gem_sym_tables[mx.encode(geo)] = get_sym_map_topology(geo, middle_edge)


def smart_mirror(deformer, direction=1):
    log = create_logger()

    with BusyCursor():
        for node in mx.ls(sl=True):
            if node in _gem_sym_tables:

                layer = Deformer.get_current_layer(node)
                Deformer.toggle_layers(node, top=True)

                for dfm in DeformerGroup.create(node):
                    if dfm.deformer != deformer:
                        continue

                    dfm.read_deformer()
                    dfm.smart_mirror(_gem_sym_tables[node], direction=direction)
                    dfm.find_geometry()
                    dfm.write()
                    log.info('mirrored {}'.format(dfm))

                Deformer.toggle_layers(node, layer=layer)

            else:
                log.error('/!\\ {} has no mirror table generated'.format(node))
