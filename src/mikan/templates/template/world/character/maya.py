# coding: utf-8

from mikan.maya import cmds as mc
import mikan.maya.cmdx as mx

import mikan.maya.core as mk
from mikan.maya.lib.rig import fix_inverse_scale
from mikan.maya.lib.connect import *
from mikan.core.prefs import Prefs


class Template(mk.Template):

    def build_template(self, data):
        if self.node.is_a(mx.tJoint):
            self.node['drawStyle'] = 2
        with mx.DagModifier() as md:
            root = md.create_node(mx.tJoint, parent=self.node)
        root['ty'] = data['height']

        fix_inverse_scale(root)

    def rename_template(self):
        root = self.get_structure('root')[0]
        root.rename('tpl_{}_root'.format(self.name))

    def build_rig(self):
        n_world = self.get_name('world')
        n_move = self.get_name('move')
        n_fly = self.get_name('fly')
        n_scale = self.get_name('scale')
        tpl_root = self.get_structure('root')[0]

        do_fly = self.get_opt('fly')
        do_scale = self.get_opt('scale')

        hook = self.get_first_hook()
        rig = self.get_rig_hook()
        world = mx.create_node(mx.tTransform, parent=hook, name=n_world)

        if do_scale:
            s_move = mx.create_node(mx.tTransform, parent=world, name='s_' + n_move)
            move = mx.create_node(mx.tTransform, parent=s_move, name=n_move)
        else:
            move = mx.create_node(mx.tTransform, parent=world, name=n_move)

        if do_fly:
            if do_scale:
                s_fly = mx.create_node(mx.tTransform, parent=move, name='s_' + n_fly)
                root_fly = mx.create_node(mx.tTransform, parent=s_fly, name='root_' + n_fly)
            else:
                root_fly = mx.create_node(mx.tTransform, parent=move, name='root_' + n_fly)
            root_fly['t'] = tpl_root['wm'][0].as_transform().translation()
            c_fly = mx.create_node(mx.tTransform, parent=root_fly, name='c_' + n_fly)

        # scale
        if do_scale:
            scale_move = Prefs.get('template/world.character/scale_move', 1)

            world.add_attr(mx.Double('scale_factor', min=0.1, default=1))
            world.add_attr(mx.Double('scale_offset', keyable=True, min=0.1, default=1))
            world.add_attr(mx.Boolean('scale_move', keyable=True, default=bool(scale_move)))
            s = connect_expr('factor * offset', factor=world['scale_factor'], offset=world['scale_offset'])
            connect_expr('s_move = w==1 ? [s,s,s] : [1,1,1]', s_move=s_move['s'], s=s, w=world['scale_move'])
            if do_fly:
                connect_expr('s_fly = w==1 ? [1,1,1] : [s,s,s]', s_fly=s_fly['s'], s=s, w=world['scale_move'])

            if 'dev' in self.modes:
                world['scale_factor'].channel_box = True

            root_scale = mx.create_node(mx.tTransform, parent=world, name='root_' + n_scale)
            if do_fly:
                mc.parent(str(root_scale), str(c_fly))
            else:
                mc.parent(str(root_scale), str(move))

            c_scale = mx.create_node(mx.tTransform, parent=root_scale, name='c_' + n_scale)
            c_scale.add_attr(mx.Double('squash', min=0, max=1, default=1, keyable=True))

            s_scale = mx.create_node(mx.tTransform, parent=c_scale, name='s_' + n_scale)

            # squash rig
            sq = connect_expr('[abs(c.x)^-.5, abs(c.y)^-.5, abs(c.z)^-.5]', c=c_scale['s'])
            connect_expr('s = [lerp(c.x, c.x*sq.y*sq.z, w), lerp(c.y, c.y*sq.x*sq.z, w), lerp(c.z, c.z*sq.x*sq.y, w)]',
                         s=s_scale['s'], c=c_scale['s'], sq=sq, w=c_scale['squash'])

            # reverse matrix
            rev_scale = mx.create_node(mx.tTransform, name='rev_' + n_scale)
            connect_expr('rev = root * c', rev=rev_scale['m'], root=root_scale['im'], c=c_scale['im'])
            mc.parent(str(rev_scale), str(s_scale))

        if do_fly:
            loc_fly = mx.create_node(mx.tTransform, parent=c_fly, name='loc_' + n_fly)
        else:
            loc_fly = mx.create_node(mx.tTransform, parent=move, name='loc_' + n_fly)

        if do_scale:
            mc.parent(str(loc_fly), str(rev_scale))

        world.add_attr(mx.Double('height'))
        world['height'] >> loc_fly['ty']
        if 'dev' in self.modes:
            world['height'].channel_box = True

        # follow switch
        if do_scale:
            c_scale.add_attr(mx.Divider('space_switch'))
            c_scale.add_attr(mx.Double('follow_world', keyable=True, min=0, max=1))

            pb = mx.create_node(mx.tPairBlend, name='_pb#')
            pb['inTranslate1'] = root_scale['t']

            mc.parentConstraint(str(world), str(root_scale), mo=1, n='_prx#')

            for dim in 'XYZ':
                root_scale['translate' + dim].input(plug=True) >> pb['inTranslate' + dim + '2']
                root_scale['rotate' + dim].input(plug=True) >> pb['inRotate' + dim + '2']
                pb['outTranslate' + dim] >> root_scale['translate' + dim]
                pb['outRotate' + dim] >> root_scale['rotate' + dim]

            c_scale['follow_world'] >> pb['w']

            if do_fly:
                connect_expr('t = -root', t=pb['inTranslate1'], root=root_fly['t'])

        # hook
        hook_root = mx.create_node(mx.tTransform, parent=rig, name='hook_root')
        connect_matrix(loc_fly['wm'][0], hook_root)

        # register -----------------------------------------------------------------------------------------------------
        self.set_id(hook_root, 'hook', template=False)

        self.set_id(world, 'ctrls.world')
        self.set_id(move, 'ctrls.move')
        if do_fly:
            self.set_id(c_fly, 'ctrls.fly')
        if do_scale:
            self.set_id(c_scale, 'ctrls.scale')

        self.set_id(world, 'space.world')
        self.set_id(move, 'space.move')
        self.set_id(loc_fly, 'space.root')

        # result
        self.set_hook(self.node, world, 'hooks.world')
        self.set_hook(tpl_root, hook_root, 'hooks.root')
