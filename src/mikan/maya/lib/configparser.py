# coding: utf-8

from mikan.maya import cmdx as mx
from mikan.core.utils import configparser

__all__ = ['ConfigParser']


class ConfigParser(configparser.ConfigParser):

    def __new__(cls, node, attr='notes'):
        if isinstance(node, mx.Node):
            if not node.exists:
                raise RuntimeError(r'"{}" is not an existing node'.format(node))
        elif not mx.obj_exists(str(node)):
            raise RuntimeError(r'"{}" is not an existing node'.format(node))
        return super(ConfigParser, cls).__new__(cls)

    def __init__(self, node, attr='notes'):
        if not isinstance(node, mx.Node):
            node = mx.encode(str(node))
        self.node = node
        self.attr = attr

    def _read(self):
        if self.attr in self.node:
            data = self.node[self.attr].read()
            if data:
                return data
        return ''

    def _write(self, data):
        sn = self.attr
        if self.attr == 'notes':
            sn = 'nts'
        if self.attr not in self.node:
            with mx.DGModifier() as md:
                plug = mx.String(self.attr)
                plug['shortName'] = sn
                md.add_attr(self.node, plug)

        with mx.DGModifier() as md:
            md.set_attr(self.node[self.attr], data)
