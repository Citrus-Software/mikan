# coding: utf-8

from six.moves import range

import mikan.maya.cmdx as mx

import mikan.maya.core as mk
from mikan.core import flatten_list, cleanup_str, create_logger
from mikan.maya.lib import connect_matrix, connect_reverse

log = create_logger()


class Mod(mk.Mod):

    def run(self):

        # get nodes
        chain = [n for n in flatten_list([self.data.get('chain')]) if isinstance(n, mx.Node) and n.is_a(mx.kTransform)]
        if 'chain' in self.data and len(chain) <= 1:
            raise mk.ModArgumentError('chain: bad length')

        roots = [n for n in flatten_list([self.data.get('roots')]) if isinstance(n, mx.Node) and n.is_a(mx.kTransform)]
        ctrls = [n for n in flatten_list([self.data.get('ctrls')]) if isinstance(n, mx.Node) and n.is_a(mx.kTransform)]
        nodes = [n for n in flatten_list([self.data.get('nodes')]) if isinstance(n, mx.Node) and n.is_a(mx.kTransform)]
        if 'ctrls' in self.data and len(ctrls) < 1:
            raise mk.ModArgumentError('missing ctrls')
        if len(ctrls) != len(nodes):
            raise mk.ModArgumentError('controller and node lists do not match')
        if roots and len(roots) != len(ctrls):
            raise mk.ModArgumentError('controller and root lists do not match')

        # name
        name = self.data.get('name')

        # processing
        xfos = []

        if not ctrls:
            # chain mode
            roots = []
            ctrls = []
            nodes = []

            for i, node in enumerate(chain):
                _name = node.name(namespace=False)
                if name:
                    _name = cleanup_str(name) + ' ' + _name

                root = mx.create_node(mx.tTransform, parent=node, name='root_sub_{}'.format(_name))
                ctrl = mx.create_node(mx.tTransform, parent=root, name='sub_{}'.format(_name))
                nodes.append(root)
                ctrls.append(ctrl)

        else:
            if roots:
                roots.append(None)
            ctrls.append(None)
            nodes.insert(0, None)

        # build
        for i in range(len(ctrls)):
            if nodes[i]:
                self.set_id(nodes[i], 'subroot', name, multi=True)
            if ctrls[i]:
                self.set_id(ctrls[i], 'sub', name, multi=True)

            if i == len(ctrls) - 1:
                break

            mmx = mx.create_node(mx.tMultMatrix, name='_mmx')
            xfos.append(mmx)

            if not roots:
                ctrls[i]['pim'][0] >> mmx['i'][0]
                ctrls[i]['m'] >> mmx['i'][1]
                ctrls[i]['pm'][0] >> mmx['i'][2]
            else:
                roots[i]['wim'][0] >> mmx['i'][0]
                ctrls[i]['wm'][0] >> mmx['i'][1]
                roots[i]['wim'][0] >> mmx['i'][2]
                roots[i]['wm'][0] >> mmx['i'][3]

        # connect hooks
        for i, xfo in enumerate(xfos):
            i += 1

            mmx = mx.create_node(mx.tMultMatrix, name='_mmx')

            for j in range(i):
                k = j * 3

                nodes[i]['pm'][0] >> mmx['i'][k]
                xfos[j]['o'] >> mmx['i'][k + 1]
                nodes[i]['pim'][0] >> mmx['i'][k + 2]

            offset = nodes[i]['wm'][0].as_matrix() * nodes[i]['pim'][0].as_matrix()
            for v0, v1 in zip(offset, mx.Matrix4()):
                if round(v0, 4) != round(v1, 4):
                    omx = mx.create_node(mx.tMultMatrix, name='mmx')
                    omx['i'][0] = offset
                    mmx['o'] >> omx['i'][1]
                    mmx = omx
                    break

            output = mmx['o']
            if self.data.get('weight', False):
                blend = mx.create_node(mx.tWtAddMatrix, name='_bmx#')
                blend['i'][0]['m'] = nodes[i]['m'].as_matrix()
                output >> blend['i'][1]['m']

                nodes[i].add_attr(mx.Double('weight', min=0, max=1, keyable=True, default=1))
                nodes[i]['weight'] >> blend['i'][1]['w']
                connect_reverse(nodes[i]['weight'], blend['i'][0]['w'])

                output = blend['o']

            connect_matrix(output, nodes[i])
