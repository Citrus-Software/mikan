# coding: utf-8

from six import iteritems

from mikan.maya import cmds as mc
import mikan.maya.cmdx as mx

import mikan.maya.core as mk
from mikan.core.logger import create_logger
from mikan.maya.lib.connect import connect_expr, connect_blend_weighted
from mikan.maya.lib.pose import get_ctrl_pose

log = create_logger()


class Mod(mk.Mod):

    def run(self):

        # node
        pho_node = self.node
        if self.data.get('create'):
            with mx.DagModifier() as md:
                pho_node = md.create_node(mx.tTransform, parent=self.node.parent(), name='phonemes')

        # attrs
        pho_node.add_attr(mx.Double('phonemes', keyable=True, min=0, max=1))

        pho_node.add_attr(mx.Double('pho_closed', keyable=True, min=0, max=1))
        for pho in self.data['pho']:
            pho_node.add_attr(mx.Double('pho_' + pho, keyable=True, min=0, max=1))

        for mod in self.data['mod']:
            pho_node.add_attr(mx.Double('mod_' + mod, keyable=True, min=0, max=1))

        # build shapes
        for mod in [None] + self.data['mod']:
            for pho in [None] + self.data['pho']:

                pho_pose = self.data['poses'].get(pho, {}).get(mod, {})
                if not pho_pose:
                    continue

                # weight plug
                w = pho_node['phonemes']
                if pho and not mod:
                    w = connect_expr(
                        'w * pho',
                        w=w,
                        pho=pho_node['pho_' + pho]
                    )
                if mod and not pho:
                    w = connect_expr(
                        'w * mod',
                        w=w,
                        mod=pho_node['mod_' + mod]
                    )
                elif pho and mod:
                    w = connect_expr(
                        'w * pho * mod',
                        w=w,
                        pho=pho_node['pho_' + pho],
                        mod=pho_node['mod_' + mod]
                    )

                # pose plugs
                for plug, v in iteritems(pho_pose):
                    _node = plug.node()
                    if 'gem_id' in _node and '::ctrls' in _node['gem_id'].read():
                        _node = get_ctrl_pose(_node)
                        if not _node:
                            self.log_warning('{} has no pose node associated'.format(plug.node()))
                            continue
                        plug = _node[plug.name()]

                    if '[' not in plug.name():
                        dv = mc.attributeQuery(plug.name(), n=str(_node), ld=1)[0]
                    else:
                        dv = plug.default
                    if dv != 0 and not plug.input():
                        connect_blend_weighted(dv, plug)

                    x = connect_expr('lerp(0, v, w)', v=v, w=w)
                    connect_blend_weighted(x, plug)

        self.set_id(pho_node, 'phonemes')
