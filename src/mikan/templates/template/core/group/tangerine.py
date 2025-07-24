# coding: utf-8

import meta_nodal_py as kl

import mikan.tangerine.core as mk


class Template(mk.Template):

    def build_template(self, data):
        self.node.rename('tpl_{}_group'.format(self.name))

    def build_rig(self):
        # pass through
        hook = self.get_hook()

        if hook.get_dynamic_plug('gem_type') and hook.gem_type.get_value() == mk.Asset.type_name:
            hook = self.get_rig_hook()

        # register
        self.set_hook(self.root, hook, 'hooks.group')

        if self.get_opt('main'):
            self.set_opt('group', self.name)
