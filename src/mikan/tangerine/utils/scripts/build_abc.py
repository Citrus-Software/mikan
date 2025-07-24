# coding: utf-8

import os

from PySide2 import QtGui, QtWidgets

import meta_nodal_py as kl
import mikan.tangerine as mk
from mikan.tangerine.core.asset import Asset

from mikan.core.logger import log
import mikan.core.logger

log.setLevel('DEBUG')
mikan.core.logger.set_time_logging(True)

# select file from explorer
app = QtWidgets.QApplication.instance()
main_window = app.main_window
file_path, _ = QtWidgets.QFileDialog.getOpenFileName(main_window, 'Import alembic', filter='Alembic file (*.abc)')

with mk.Scene('doc', root_node=mk.find_root()) as root:
    kl.load_abc(root, file_path, 'jnt', automatic_instances=True)
    nodes = mk.ls(root=root, as_dict=True)

    # reparent data to asset
    asset = Asset(nodes['asset'])
    for n in ['dfm', 'data', 'geo']:
        if n in nodes:
            nodes[n].reparent(asset.node)

    # make
    kl.set_building(True)
    asset = Asset(nodes['asset'])
    asset.make(['debug', 'anim'])

    # hide data
    for n in ['data', 'dfm']:
        if n in nodes:
            nodes[n].show.set_value(False)

    # display
    if 'geo' in nodes:
        mk.apply_shaders(nodes['geo'])

    _nodes = mk.ls(as_dict=True, root=nodes.get('geo'))
    for name, node in _nodes.items():
        if type(node) is kl.Geometry:
            node.subdivision_level.set_value(2)
            node.set_pickable(False)

    # cleanup
    asset.node.rename(asset.name)
