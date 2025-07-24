# coding: utf-8

import mikan.tangerine.core as mk


class Template(mk.Template):

    def build_rig(self):
        name = self.node.gem_module.get_value()
        raise RuntimeError(f'Template module "{name}" does not exists')
