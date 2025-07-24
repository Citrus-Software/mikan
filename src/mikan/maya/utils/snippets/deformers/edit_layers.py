# coding: utf-8

import mikan.maya.cmdx as mx

from mikan.core.logger import create_logger
from mikan.maya.core.deformer import Deformer

log = create_logger()


def _remove_layers():
    for geo in mx.ls(sl=True, et='transform'):
        try:
            Deformer.remove_layers(geo)
            log.info('removed shape layers of {}'.format(geo))
        except:
            log.error('/!\\ failed to remove shape layers of {}'.format(geo))


def _inject_layers():
    for geo in mx.ls(sl=True, et='transform'):
        try:
            Deformer.inject_layers(geo)
            log.info('shape layers injected for {}'.format(geo))
        except:
            log.error('/!\\ failed to inject shape layers for {}'.format(geo))
