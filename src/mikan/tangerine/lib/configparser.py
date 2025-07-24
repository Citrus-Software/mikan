# coding: utf-8

from meta_nodal_py import Node
from mikan.core.utils import configparser

__all__ = ['ConfigParser']


class ConfigParser(configparser.ConfigParser):
    def __new__(cls, node, attr='notes'):
        if not isinstance(node, Node):
            raise RuntimeError('"%s" is not an existing node' % str(node))

        return super(ConfigParser, cls).__new__(cls)

    def _read(self):
        plug = self.node.get_dynamic_plug(self.attr)
        if plug:
            data = plug.get_value()
            if data:
                return data
        return ''

    def _write(self, data):
        plug = self.node.get_dynamic_plug(self.attr)
        if not plug:
            self.node.add_dynamic_plug(self.attr, "")
        plug = self.node.get_dynamic_plug(self.attr)
        plug.set_value(data)
