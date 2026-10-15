# coding: utf-8

import meta_nodal_py as kl
from meta_nodal_py.Imath import V3f

import mikan.tangerine.core as mk
from mikan.core import ordered_load
from mikan.core.tree import Tree
from mikan.core.logger import create_logger

from mikan.tangerine.lib.commands import add_plug, copy_transform
from mikan.tangerine.lib.rig import (
    point_constraint, aim_constraint, parent_constraint,
    create_srt_in, create_srt_out
)

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
      
  left_ankle_effector:
  left_knee_effector:
  right_ankle_effector:
  right_knee_effector:
    
  left_wrist_effector:
  left_elbow_effector:
  right_wrist_effector:
  right_elbow_effector:
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

        # create group
        grp = mk.Group.create('mocap')

        add_plug(grp.node, 'gem_group_parent', str)
        grp.node.gem_group_parent.set_value('all')

        self.set_id(grp.node, 'subgroups', 'mocap', prefix='')

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

        for k in keys:
            if k in self.data:
                if self.data[k] is not None:
                    nodes = self.data[k]
                    if isinstance(nodes, kl.Node):
                        nodes = [nodes]
                    keys[k]['node'] = nodes

                    self.mocap[k] = []

                    name = snake_to_pascal(k)
                    for i, node in enumerate(nodes):
                        if node is None:
                            log.warning('missing node for definition: {}'.format(name))
                            continue

                        _name = 'hik_' + name
                        if i > 0:
                            _name = 'end_' + name

                        cls = kl.Joint
                        if k == 'reference':
                            cls = kl.SceneGraphNode
                        j = cls(node, _name)

                        if i == 0:
                            add_plug(j, 'gem_hook', str)
                            j.gem_hook.connect(node.gem_id)

                            self.set_id(j, 'mocap.' + k)
                            grp.add_member(j)

                            create_srt_in(j, keyable=True)

                        else:
                            j.show.set_value(False)

                        self.mocap[k].append(j)

        # build skeleton hierarchy
        self.parent_children(Tree.rarefy(skeleton))

        # build effector rig
        for n in (0, 1):
            for side in ('left', 'right'):
                _root = ('hips', 'spine')[n]
                _eff = side + ('_ankle_effector', '_wrist_effector')[n]
                _j0 = side + ('_up_leg', '_arm')[n]
                _j1 = side + ('_leg', '_fore_arm')[n]
                _j2 = side + ('_foot', '_hand')[n]

                aim0 = {'left': V3f(0, -1, 0), 'right': V3f(0, 1, 0)}[side]
                aim1 = {
                    'left': (V3f(0, 0, 1), V3f(0, 0, -1))[n],
                    'right': (V3f(0, 0, -1), V3f(0, 0, 1))[n],
                }[side]

                do_rig = True
                for k in (_root, _eff, _j0, _j1, _j2):
                    if k not in self.mocap:
                        do_rig = False
                        break
                if not do_rig:
                    continue

                root = self.mocap[_root][0]
                eff = self.mocap[_eff][0]
                j0 = self.mocap[_j0][0]
                j1 = self.mocap[_j1][0]
                j2 = self.mocap[_j2][0]

                loc_root = kl.SceneGraphNode(root, 'loc_root_' + _j1)
                loc_aim = kl.SceneGraphNode(loc_root, 'loc_aim_' + _j1)
                loc_mid = kl.SceneGraphNode(loc_aim, 'loc_mid_' + _j1)

                copy_transform(j0, loc_root)
                point_constraint(j0, loc_root)

                aim_constraint(
                    j2, loc_aim,
                    aim_vector=aim0,
                    up_vector=V3f(0, 0, 0)
                )

                copy_transform(loc_aim, loc_root, r=1)

                point_constraint((j0, j2), loc_mid)

                aim_constraint(
                    j1, loc_mid,
                    aim_vector=aim1,
                    up_vector=V3f(0, 0, 0)
                )

                add_plug(eff, 'twist', float, keyable=True)
                srt = create_srt_out(loc_mid, vectors=True)
                eff.twist.connect(srt.find('rotate').y)

                parent_constraint(j2, eff)

    def parent_children(self, data, parent=None, key=None):

        if 'node' in data and data['node'] and self.mocap[key]:
            nodes = self.mocap[key]

            if parent:
                for node in nodes:
                    node.reparent(parent)
                    parent = node
            else:
                nodes[0].show.set_value(False)
                rig = mk.Nodes.get_id('::rig')
                if rig:
                    nodes[0].reparent(rig)

            parent = nodes[0]

        for k in data:
            if isinstance(data[k], dict):
                self.parent_children(data[k], parent=parent, key=k)
