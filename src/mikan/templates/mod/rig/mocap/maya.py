# coding: utf-8

from mikan.maya import cmds as mc
import mikan.maya.cmdx as mx

import mikan.maya.core as mk
from mikan.core import ordered_load
from mikan.core.tree import Tree
from mikan.core.logger import create_logger

log = create_logger()

character_hierarchy = '''
reference:
  hips:
    spine:
     spine1.spine2.spine3.spine4.spine5.spine6.spine7.spine8.spine9:
       neck:
         neck1.neck2.neck3.neck4.neck5.neck6.neck7.neck8.neck9:
           head:

       left_shoulder:
         left_arm.left_arm_roll:
           left_fore_arm.left_fore_arm_roll:
             left_hand:
               left_finger_base:
               left_in_hand_thumb.left_hand_thumb1.left_hand_thumb2.left_hand_thumb3.left_hand_thumb4:
               left_in_hand_index.left_hand_index1.left_hand_index2.left_hand_index3.left_hand_index4:
               left_in_hand_middle.left_hand_middle1.left_hand_middle2.left_hand_middle3.left_hand_middle4:
               left_in_hand_ring.left_hand_ring1.left_hand_ring2.left_hand_ring3.left_hand_ring4:
               left_in_hand_pinky.left_hand_pinky1.left_hand_pinky2.left_hand_pinky3.left_hand_pinky4:

             leaf_left_fore_arm_roll1.leaf_left_fore_arm_roll2.leaf_left_fore_arm_roll3.leaf_left_fore_arm_roll4.leaf_left_fore_arm_roll5:
           leaf_left_arm_roll1.leaf_left_arm_roll2.leaf_left_arm_roll3.leaf_left_arm_roll4.leaf_left_arm_roll5:

       right_shoulder:
         right_arm.right_arm_roll:
           right_fore_arm.right_fore_arm_roll:
             right_hand:
               right_finger_base:
               right_in_hand_thumb.right_hand_thumb1.right_hand_thumb2.right_hand_thumb3.right_hand_thumb4:
               right_in_hand_index.right_hand_index1.right_hand_index2.right_hand_index3.right_hand_index4:
               right_in_hand_middle.right_hand_middle1.right_hand_middle2.right_hand_middle3.right_hand_middle4:
               right_in_hand_ring.right_hand_ring1.right_hand_ring2.right_hand_ring3.right_hand_ring4:
               right_in_hand_pinky.right_hand_pinky1.right_hand_pinky2.right_hand_pinky3.right_hand_pinky4:

             leaf_right_fore_arm_roll1.leaf_right_fore_arm_roll2.leaf_right_fore_arm_roll3.leaf_right_fore_arm_roll4.leaf_right_fore_arm_roll5:
           leaf_right_arm_roll1.leaf_right_arm_roll2.leaf_right_arm_roll3.leaf_right_arm_roll4.leaf_right_arm_roll5:

    left_up_leg.left_up_leg_roll:
      left_leg.left_leg_roll:
        left_foot:
          left_toe_base:

        leaf_left_leg1.leaf_left_leg2.leaf_left_leg3.leaf_left_leg4.leaf_left_leg5:
      leaf_left_up_leg1.leaf_left_up_leg2.leaf_left_up_leg3.leaf_left_up_leg4.leaf_left_up_leg5:

    right_up_leg.right_up_leg_roll:
      right_leg.right_leg_roll:
        right_foot:
          right_toe_base:

        leaf_right_leg1.leaf_right_leg2.leaf_right_leg3.leaf_right_leg4.leaf_right_leg5:
      leaf_right_up_leg1.leaf_right_up_leg2.leaf_right_up_leg3.leaf_right_up_leg4.leaf_right_up_leg5:
'''


def snake_to_pascal(s):
    return ''.join(map(str.title, s.split('_')))


class Mod(mk.Mod):
    HIERARCHY = Tree()

    debug = None

    _hierarchy = ordered_load(character_hierarchy)
    for k, v in Tree.flatten(_hierarchy):
        HIERARCHY[k] = v

    def run(self):

        # create hierarchy
        skeleton = Mod.HIERARCHY.copy()

        # add node to every branches
        for k in list(skeleton):
            b = skeleton.branch(k)
            b['node'] = None
        for b in list(skeleton.branches()):
            b['node'] = None

        keys = {}
        for b in skeleton.branches():
            key = b.key.split('.')[-1]
            keys[key] = b

        self.mocap = {}
        hik = mx.create_node('HIKCharacterNode')
        self.set_id(hik, 'hik')

        for k in keys:
            if k in self.data:
                if self.data[k] is not None:
                    nodes = self.data[k]
                    if isinstance(nodes, mx.Node):
                        nodes = [nodes]
                    keys[k]['node'] = nodes

                    self.mocap[k] = []

                    name = snake_to_pascal(k)
                    for i, node in enumerate(nodes):
                        _name = 'hik_' + name
                        if i > 0:
                            _name = 'end_' + name

                        cls = mx.tJoint
                        if k == 'reference':
                            cls = mx.tTransform
                        j = mx.create_node(cls, parent=node, name=_name)
                        if i == 0:
                            j.add_attr(mx.String('gem_hook'))
                            node['gem_id'] >> j['gem_hook']

                            self.set_id(j, 'mocap.' + k)

                            # connect to hik
                            j.add_attr(mx.Message('Character'))
                            j['Character'] >> hik[name]
                        else:
                            j['v'] = False

                        self.mocap[k].append(j)

        # build skeleton hierarchy
        self.parent_children(Tree.rarefy(skeleton))

    def parent_children(self, data, parent=None, key=None):

        if 'node' in data and data['node'] and self.mocap[key]:
            nodes = self.mocap[key]

            if parent:
                for node in nodes:
                    mc.parent(str(node), str(parent))
                    parent = node
            else:
                nodes[0]['v'] = False
                rig = mk.Nodes.get_id('::rig')
                if rig:
                    mc.parent(str(nodes[0]), str(rig))

            parent = nodes[0]

        for k in data:
            if isinstance(data[k], dict):
                self.parent_children(data[k], parent=parent, key=k)
