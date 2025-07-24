# coding: utf-8
import meta_nodal_py as kl

import mikan.tangerine.core as mk
from mikan.tangerine.lib.connect import connect_expr, connect_add, connect_additive
from mikan.tangerine.lib.commands import *
from mikan.core.logger import create_logger

log = create_logger()


class Mod(mk.Mod):

    def run(self):

        # node
        pho_node = self.node
        if self.data.get('create'):
            pho_node = kl.SceneGraphNode(self.node.get_parent(), 'phonemes')

        # attrs
        add_plug(pho_node, 'phonemes', float, keyable=True, min_value=0, max_value=1)

        add_plug(pho_node, 'pho_closed', float, keyable=True, min_value=0, max_value=1)
        for pho in self.data['pho']:
            add_plug(pho_node, 'pho_' + pho, float, keyable=True, min_value=0, max_value=1)

        for mod in self.data['mod']:
            add_plug(pho_node, 'mod_' + mod, float, keyable=True, min_value=0, max_value=1)

        # build shapes
        for mod in [None] + self.data['mod']:
            for pho in [None] + self.data['pho']:

                pho_pose = self.data['poses'].get(pho, {}).get(mod, {})
                if not pho_pose:
                    continue

                # weight plug
                w = pho_node.phonemes
                if pho and not mod:
                    w = connect_expr(
                        'w * pho',
                        w=w,
                        pho=pho_node.get_dynamic_plug('pho_' + pho)
                    )
                if mod and not pho:
                    w = connect_expr(
                        'w * mod',
                        w=w,
                        mod=pho_node.get_dynamic_plug('mod_' + mod)
                    )
                elif pho and mod:
                    w = connect_expr(
                        'w * pho * mod',
                        w=w,
                        pho=pho_node.get_dynamic_plug('pho_' + pho),
                        mod=pho_node.get_dynamic_plug('mod_' + mod)
                    )

                # pose plugs
                for plug, v in pho_pose.items():
                    _node = plug.get_node()
                    if isinstance(_node, (kl.FloatToV3f, kl.FloatToEuler)):
                        _node = _node.get_parent().get_parent()  # fast mode (but unsafe)
                        if _node.get_dynamic_plug('gem_id') and '::ctrls' in _node.gem_id.get_value():
                            _pose_node = None
                            for tag in _node.gem_id.get_value().split(';'):
                                if '::ctrls' in tag:
                                    tag = tag.replace('::ctrls', '::poses')
                                    _pose_node = mk.Nodes.get_id(tag)
                                    break
                            if not _pose_node:
                                self.log_warning('{} has no pose node associated'.format(plug.node()))
                                continue

                            _plug = f'{plug.get_node().get_name()[0]}.{plug.get_name()}'
                            plug = mk.Nodes.get_node_plug(_pose_node, _plug)

                    dv = plug.get_value()
                    if dv != 0 and not plug.get_input():
                        connect_add(0, dv, plug)

                    x = connect_expr('lerp(0, v, w)', v=v, w=w)
                    connect_additive(x, plug)

        self.set_id(pho_node, 'phonemes')
