# coding: utf-8

import mikan.maya.core as mk


class Template(mk.Template):

    def rename_template(self):
        self.node.rename('tpl_{}_group'.format(self.name))

    def build_template(self, data):
        self.node['t'].lock()
        self.node['drawStyle'] = 2

    def build_rig(self):
        # pass through
        hook = self.get_hook()

        if 'gem_type' in hook and hook['gem_type'].read() == mk.Asset.type_name:
            hook = self.get_rig_hook()

        # register
        self.set_hook(self.root, hook, 'hooks.group')

        if self.get_opt('main'):
            self.set_opt('group', self.name)
