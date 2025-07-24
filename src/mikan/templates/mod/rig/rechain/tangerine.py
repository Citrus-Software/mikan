# coding: utf-8

import meta_nodal_py as kl
from meta_nodal_py.Imath import M44f

import mikan.tangerine.core as mk
from mikan.core import flatten_list, cleanup_str, create_logger
from mikan.tangerine.lib.commands import add_plug
from mikan.tangerine.lib.rig import compare_transform
from mikan.tangerine.lib.connect import connect_reverse

log = create_logger()


class Mod(mk.Mod):

    def run(self):

        # get nodes
        chain = [n for n in flatten_list([self.data.get('chain')]) if isinstance(n, kl.SceneGraphNode)]
        if 'chain' in self.data and len(chain) <= 1:
            raise mk.ModArgumentError('chain: bad length')

        roots = [n for n in flatten_list([self.data.get('roots')]) if isinstance(n, kl.SceneGraphNode)]
        ctrls = [n for n in flatten_list([self.data.get('ctrls')]) if isinstance(n, kl.SceneGraphNode)]
        nodes = [n for n in flatten_list([self.data.get('nodes')]) if isinstance(n, kl.SceneGraphNode)]
        if 'ctrls' in self.data and len(ctrls) < 1:
            raise mk.ModArgumentError('missing ctrls')
        if len(ctrls) != len(nodes):
            raise mk.ModArgumentError('controller and root lists do not match')
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
                _name = node.get_name().split(':')[-1]
                if name:
                    _name = cleanup_str(name) + ' ' + _name

                root = kl.SceneGraphNode(node, 'root_sub_{}'.format(_name))
                ctrl = kl.SceneGraphNode(root, 'sub_{}'.format(_name))
                nodes.append(root)
                ctrls.append(ctrl)

        else:
            if roots:
                roots.append(None)
            ctrls.append(None)
            nodes.insert(0, None)

        for i in range(len(ctrls)):
            if nodes[i]:
                self.set_id(nodes[i], 'subroot', name, multi=True)
            if ctrls[i]:
                self.set_id(ctrls[i], 'sub', name, multi=True)

            if i == len(ctrls) - 1:
                break

            if not roots:
                mmx = kl.MultM44f(ctrls[i], '_mmx', 3)

                imx = kl.InverseM44f(mmx, '_imx')
                imx.input.connect(ctrls[i].parent_world_transform)
                mmx.input[0].connect(imx.output)
                mmx.input[1].connect(ctrls[i].transform)
                mmx.input[2].connect(ctrls[i].parent_world_transform)
            else:
                mmx = kl.MultM44f(ctrls[i], '_mmx', 4)

                imx = kl.InverseM44f(mmx, '_imx')
                imx.input.connect(roots[i].world_transform)
                mmx.input[0].connect(imx.output)
                mmx.input[1].connect(ctrls[i].world_transform)
                mmx.input[2].connect(imx.output)
                mmx.input[3].connect(roots[i].world_transform)

            xfos.append(mmx)

        # connect hooks
        for i, xfo in enumerate(xfos):
            i += 1

            mmx = kl.MultM44f(nodes[i], '_mmx', (i + 1) * 3)

            for j in range(i):
                k = j * 3

                mmx.input[k].connect(nodes[i].parent_world_transform)
                mmx.input[k + 1].connect(xfos[j].output)
                imx = kl.InverseM44f(nodes[i], '_imx')
                imx.input.connect(nodes[i].parent_world_transform)
                mmx.input[k + 2].connect(imx.output)

            offset = nodes[i].world_transform.get_value() * nodes[i].parent_world_transform.get_value().invert()

            if not compare_transform(offset, M44f()):
                omx = kl.MultM44f(nodes[i], '_mmx')
                omx.input[0].set_value(offset)
                omx.input[1].connect(mmx.output)
                mmx = omx

            output = mmx.output
            if self.data.get('weight', False):
                blend = kl.BlendWeightedTransforms(2, nodes[i], '_bmx')
                blend.transform_interp_in.set_value(False)

                blend.transform_in[0].set_value(nodes[i].transform.get_value())
                blend.transform_in[1].connect(output)

                add_plug(nodes[i], 'weight', float, min_value=0, max_value=1, default_value=1)

                blend.weight_in[1].connect(nodes[i].weight)
                connect_reverse(nodes[i].weight, blend.weight_in[0])

                output = blend.transform_out

            nodes[i].transform.connect(output)
