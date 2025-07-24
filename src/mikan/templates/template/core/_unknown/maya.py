# coding: utf-8

import mikan.maya.core as mk


class Template(mk.Template):

    def build_rig(self):
        name = self.node['gem_module'].read()
        raise RuntimeError('Template module "{}" does not exists'.format(name))
