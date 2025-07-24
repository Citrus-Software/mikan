# coding: utf-8

from six import iteritems
from six.moves import range
from fnmatch import fnmatch
import copy

from mikan.maya import om, oma
from mikan.maya import cmds as mc
from mikan.maya import cmdx as mx

import mikan.maya.core as mk
from mikan.maya.core.deformer import WeightMap, WeightMapInterface
from mikan.maya.lib.shaders import transfer_shading
from mikan.core.logger import create_logger

log = create_logger()


class Deformer(mk.Deformer):
    node_class = mx.tSkinCluster

    def read(self):
        self.data['method'] = self.node['skinningMethod'].read()
        self.data['mmi'] = self.node['mmi'].read()
        self.data['mi'] = self.node['mi'].read()
        self.data['normalize'] = self.node['nw'].read()
        self.data['dq'] = self.node['skinningMethod'].read() > 0

        # get geometry
        if not self.geometry:
            self.find_geometry()

        # influence maps
        fn = oma.MFnSkinCluster(self.node.object())
        infs = [mx.Node(mdag.node()) for mdag in fn.influenceObjects()]
        infid = self.node['matrix'].array_indices

        cps = self.get_components_mobject(self.geometry)
        weights_all, num_inf = fn.getWeights(self.geometry.dag_path(), cps)
        weights_all = list(weights_all)
        weights = []
        for i in range(num_inf):
            weights.append(weights_all[i::num_inf])

        if len(infs) != len(weights) and len(infs) != len(infid):
            log.error('/!\\ failed! skin influences mismatch')
            return

        self.data['infs'].clear()
        self.data['maps'].clear()
        self.data['bind_pose'].clear()
        self.data['bind_pose_root'].clear()

        maps = self.data['maps']
        bpms = self.data['bind_pose']
        bpm_roots = self.data['bind_pose_root']

        for i, inf, wmap in zip(infid, infs, weights):
            maps[i] = mk.WeightMap(list(wmap))
            self.data['infs'][i] = self.get_node_id(inf, '::skin.')

            bpm = self.node['bindPreMatrix'][i].input()
            if bpm:
                if bpm.is_a(mx.tInverseMatrix) and bpm.name().startswith('_bpm_inv'):
                    _bpm = bpm['inputMatrix'].input()
                    _bpm = _bpm['i'][1].input()
                    bpm_roots[i] = self.get_node_id(_bpm)
                else:
                    if bpm.is_a(mx.kTransform):
                        bpms[i] = self.get_node_id(bpm)
                    else:
                        log.warning('/!\\ cannot read bind pose input for influence {}'.format(self.data['infs'][i]))

        # dq blend map
        if self.node['skinningMethod'].read() == 2:
            dqmap = fn.getBlendWeights(self.geometry.dag_path(), cps)
            maps['dq'] = mk.WeightMap(dqmap)

    def build(self, data=None):
        # check data
        if not self.transform:
            raise mk.DeformerError('geometry missing')
        if not self.data['infs']:
            raise mk.DeformerError('influence missing')

        # get shape?
        if not self.geometry:
            self.find_geometry()

        # intermediate check
        io = self.geometry['io'].read()
        if io:
            self.geometry['io'] = False

        vis = self.geometry['v'].read()
        if not vis:
            self.geometry['v'] = True

        # build
        joint_infs = []
        xfo_infs = []

        indices = [i for i in self.data['infs'] if isinstance(i, int)]
        indices.sort()

        for i in indices:
            # influence placeholder
            try:
                inf = self.get_node(self.data['infs'][i])
            except:
                self.log_error('influence "{}" does not exist, replaced with placeholder'.format(self.data['infs'][i]))
                _root_name = '__skin_placeholders__'
                if mc.objExists(_root_name):
                    _root = mx.encode(_root_name)
                else:
                    with mx.DagModifier() as md:
                        _root = md.create_node(mx.tTransform, name=_root_name)
                inf_name = self.data['infs'][i].split()[-1].replace('::', '_') + '_placeholder'
                if mc.objExists(inf_name):
                    inf = mx.encode(inf_name)
                else:
                    with mx.DagModifier() as md:
                        inf = md.create_node(mx.tJoint, parent=_root, name=inf_name)

            if inf.is_a(mx.tJoint):
                joint_infs.append(inf)
            else:
                xfo_infs.append(inf)

        # protect layered skin
        shunt_skin = None
        for skin_node in mc.ls(mc.listHistory(str(self.geometry)), et='skinCluster'):
            skin_node = mx.encode(skin_node)
            fn = oma.MFnGeometryFilter(skin_node.object())
            _shp = fn.getOutputGeometry()
            if _shp:
                _shp = mx.Node(_shp[0])
                if _shp == self.geometry:
                    shunt_skin = skin_node
                    break

        replug = None
        if shunt_skin:
            ids = Deformer.get_deformer_ids(self.transform)
            if 'source' not in ids:
                mc.deformer(self.geometry, type='tweak')

            shp_layer = self.geometry
            shp_name = shp_layer.name(namespace=False)

            dupe = mc.duplicate(str(self.transform), rr=1, rc=1)
            dupe = mx.encode(dupe[0])
            for shp in dupe.shapes():
                if not shp['io'].read():
                    self.geometry = shp
                    mc.parent(str(self.geometry), str(self.transform), r=1, s=1)
                    mx.delete(dupe)
                    break

            if self.geometry.is_a(mx.tMesh):
                transfer_shading(shp_layer, self.geometry)

            isg = 'initialShadingGroup'
            if mc.objExists(isg):
                mc.sets(str(shp_layer), forceElement=isg)

            shp_layer.rename(shp_name + 'Layer#')
            shp_layer['io'] = True
            self.set_geometry_id(shp_layer, 'layer')
            replug = Deformer.get_deformer_output(shp_layer, self.transform)

            self.geometry.rename(shp_name)

        # inject deformer
        node = mx.cmd(mc.skinCluster, joint_infs, self.geometry, mi=self.data['mi'], omi=self.data['mmi'], tsb=True, nw=self.data['normalize'])
        self.node = mx.encode(node[0])

        if self.geometry.is_referenced():
            self.find_geometry()

        if xfo_infs:
            for o in xfo_infs:
                mc.skinCluster(str(self.node), edit=True, ai=o)

        # relative
        if self.data['relative']:
            self.transform['wm'][0] >> self.node['geomMatrix']
        else:
            self.node['geomMatrix'] = self.transform['wm'][0].as_matrix()

        # dual quaternion method
        dq = self.data.get('method', self.data.get('dq', False))
        self.node['skinningMethod'] = int(dq)
        if dq:
            self.node['dqsSupportNonRigid'] = True

            world = self.data.get('dq_scale', mk.Nodes.get_id('::hook'))
            if world:
                with mx.DGModifier() as md:
                    dmx = md.create_node(mx.tDecomposeMatrix, name='_dmx')
                world['wm'][0] >> dmx['imat']
                dmx['outputScale'] >> self.node['dqsScale']

        # bind pose
        fn = oma.MFnSkinCluster(self.node.object())
        infs = [mx.Node(mdag.node()) for mdag in fn.influenceObjects()]
        infid = self.node['matrix'].array_indices

        for i, bpm in iteritems(self.data.get('bind_pose_root', {})):
            bpm = self.get_node(bpm)

            # remap index
            try:
                _inf = self.get_node(self.data['infs'][i])
            except:
                continue
            _i = infs.index(_inf)
            i = infid[_i]

            # connect bpm
            name = 'bpm_{}'.format(_inf.name())
            with mx.DagModifier() as md:
                _bpm = md.create_node(mx.tJoint, parent=_inf, name=name)
            _bpm['v'] = False
            _wm = _bpm['wm'][0].as_matrix() * bpm['wim'][0].as_matrix()
            mc.parent(str(_bpm), str(bpm), r=1)
            mc.xform(str(_bpm), m=_wm)

            with mx.DGModifier() as md:
                mmx = md.create_node(mx.tMultMatrix, name='_bpm_offset#')
            _bpm['m'] >> mmx['i'][0]
            bpm['wm'][0] >> mmx['i'][1]
            with mx.DGModifier() as md:
                imx = md.create_node(mx.tInverseMatrix, name='_bpm_inv#')
            mmx['o'] >> imx['inputMatrix']
            imx['outputMatrix'] >> self.node['bindPreMatrix'][i]

            imx['ihi'] = False
            mmx['ihi'] = False

        for i, bpm in iteritems(self.data.get('bind_pose', {})):
            bpm = self.get_node(bpm)

            # remap index
            try:
                _inf = self.get_node(self.data['infs'][i])
            except:
                continue
            _i = infs.index(_inf)
            i = infid[_i]

            # connect
            bpm['wim'][0] >> self.node['bindPreMatrix'][i]

        # rename
        name = '_'.join(self.transform.name().split('_')[1:])
        if not name:
            name = self.transform.name()
        self.node.rename('skin_{}'.format(name))

        # intermediate check
        if io:
            self.geometry['io'] = True

        if not vis:
            self.geometry['v'] = False

        # replug layered skin
        if replug is not None:
            fn = oma.MFnSkinCluster(self.node.object())
            orig_new = mx.Node(fn.getInputGeometry()[0])
            output_new = Deformer.get_deformer_output(orig_new, self.transform)
            plug_in = output_new.output(plug=True)
            mc.connectAttr(replug.path(), plug_in.path(), force=True)
            mx.delete(orig_new)

        # update i/o
        self.reorder()

        # update weights
        self.update(force=True)

    def update(self, force=False):

        self.write_membership()

        if force:
            self.write()
            return

        # check infs
        ids, maps = self.get_indexed_maps()
        if not maps:
            return

        infid = self.node['matrix'].array_indices

        if ids != infid:
            name = Deformer.get_unique_name(self.transform, self.root)
            key = self.id
            raise mk.DeformerError('cannot update skin weights of "{}->{}". map indices are different'.format(name, key))

        mismatch = False
        fn = oma.MFnSkinCluster(self.node.object())
        infs = [mx.Node(mdag.node()) for mdag in fn.influenceObjects()]
        for i, inf in zip(infid, infs):
            if i not in self.data['infs']:
                mismatch = True
                break
            try:
                _inf = self.get_node(self.data['infs'][i])
                if _inf != inf:
                    mismatch = True
                    break
            except:
                mismatch = True

        if mismatch:
            name = Deformer.get_unique_name(self.transform, self.root)
            key = self.id
            raise mk.DeformerError('cannot update skin weights of "{}->{}". influences do not match'.format(name, key))

        # write if possible
        self.write()

    def write(self):
        ids, maps = self.get_indexed_maps()
        if not maps:
            return

        # check size
        n = self.get_size()
        if maps and len(maps[0].weights) != n:
            self.log_warning('cannot write {}, bad map length'.format(self.node))
            return

        # write maps
        weights = []
        for w in zip(*[m.weights for m in maps]):
            weights.extend(w)
        weights = om.MDoubleArray(weights)

        cps = self.get_components_mobject(self.geometry)

        ids = [i for i, x in enumerate(ids)]
        ids = om.MIntArray(ids)

        fn = oma.MFnSkinCluster(self.node.object())
        weights_bak = fn.setWeights(self.geometry.dag_path(), cps, ids, weights, returnOldWeights=True)
        mx.commit(
            lambda: fn.setWeights(self.geometry.dag_path(), cps, ids, weights_bak),
            lambda: fn.setWeights(self.geometry.dag_path(), cps, ids, weights)
        )

        # dq blend?
        if 'dq' in self.data['maps']:
            dq = self.data['maps']['dq']
            self.node['skinningMethod'] = 2

            dq_map = om.MDoubleArray(dq.weights)
            fn.setBlendWeights(self.geometry.dag_path(), cps, dq_map)

        # fix normalization
        if self.data['normalize'] == 1:
            mc.skinPercent(str(self.node), str(self.geometry), normalize=True)

    @staticmethod
    def hook(dfm, xfo, hook):

        if hook == 'enable' or hook == 'envelope':
            return dfm['envelope']

    # edit maps --------------------------------------------------------------------------------------------------------

    def create_weightmap(self, wm, **data):
        if wm is None:
            n = self.get_size()
            wm = WeightMap([0.0] * n)
        return WeightMapInterface(wm, **data)

    def get_weightmaps(self):

        maps = []

        # membership
        if 'membership' in self.data:
            data = {'name': 'membership'}
            wm = self.data['membership']
            maps.append(WeightMapInterface(wm, **data))

        # dq
        if 'dq' in self.data['maps']:
            data = {'name': 'dual quaternion blend'}
            wm = self.data['maps']['dq']
            maps.append(WeightMapInterface(wm, **data))

        # bind pose data
        bind_pose = self.data.get('bind_pose', {})
        bind_pose_root = self.data.get('bind_pose_root', {})

        # influences
        for i, wm in iteritems(self.data['maps']):
            if not isinstance(i, int):
                continue

            data = {'key': i}

            node = self.data['infs'].get(i)
            data.update(WeightMapInterface.get_node_interface(node))

            data['bind_pose'] = None
            data['bind_pose_root'] = None

            if i in bind_pose:
                data['bind_pose'] = WeightMapInterface.get_node_interface(bind_pose[i])
                data['bind_pose']['key'] = 'bp'
            if i in bind_pose_root:
                data['bind_pose_root'] = WeightMapInterface.get_node_interface(bind_pose_root[i])
                data['bind_pose_root']['key'] = 'bpr'

            maps.append(WeightMapInterface(wm, **data))

        return maps

    def set_weightmaps(self, maps):

        # cleanup
        self.data.pop('membership', None)
        self.data['maps'].clear()
        self.data['infs'].clear()
        self.data['bind_pose'].clear()
        self.data['bind_pose_root'].clear()

        # load maps
        for wi in maps:
            name = wi.data.get('name')
            key = wi.data.get('key')

            if name == 'membership':
                self.data['membership'] = wi.weightmap.copy()

            elif name == 'dual quaternion blend':
                self.data['maps']['dq'] = wi.weightmap.copy()

            elif isinstance(key, int):
                self.data['maps'][key] = wi.weightmap.copy()
                self.data['infs'][key] = wi.get_node_tag()

                if wi.data.get('bind_pose'):
                    self.data['bind_pose'][key] = wi.get_node_tag(subkey='bind_pose')
                if wi.data.get('bind_pose_root'):
                    self.data['bind_pose_root'][key] = wi.get_node_tag(subkey='bind_pose_root')

    def smart_mirror(self, sym, keypos='L', keyneg='R', keysep='_', direction=1, exclude_list=None):
        # args
        if direction < 0:
            keypos, keyneg = keyneg, keypos

        if exclude_list is None:
            exclude_list = []

        # processing
        ids, maps = self.get_indexed_maps()

        rev_ids = {}
        for i in ids:
            names = self.data['infs'][i]
            rev_ids[names.split()[-1]] = i

        # get symmmetry ids
        map_sym = []
        id_sym = []
        id_nosym = ids[:]

        for i in ids:
            names = self.data['infs'][i]
            name = names.split()[-1]
            name_keys = name.split(keysep)
            if keypos in name_keys:
                if keyneg in name_keys:
                    if keypos not in name_keys[:name_keys.index(keyneg)]:
                        continue  # skip if keypos is after keyneg
                _i = name_keys.index(keypos)
                name_keys[_i] = keyneg
                _name = keysep.join(name_keys)
                if _name in rev_ids:
                    rev_id = rev_ids[_name]
                    m0 = self.data['maps'][i]
                    m1 = self.data['maps'][rev_id]
                    map_sym.append((m0, m1))
                    id_sym.append((i, rev_id))
                    id_nosym.remove(i)
                    id_nosym.remove(rev_id)

        # mirror paired maps weights per vertex
        for m0, m1 in map_sym:
            wm0 = m0.weights
            wm1 = m1.weights

            for table in (1, 0, -1):
                for i in sym[table].keys():
                    j = sym[table][i]
                    wm1[j] = wm0[i]

        # mirror unpaired maps weights per vertex
        for i in id_nosym[:]:
            for pattern in exclude_list:
                for name in self.data['infs'][i].split():
                    if fnmatch(name, str(pattern)):
                        id_nosym.remove(i)
                        log.info('excluding: {}'.format(name))
                        break
                else:
                    continue  # only executed if the inner loop did NOT break
                break  # only executed if the inner loop DID break

        for i in id_nosym[:]:
            wm = self.data['maps'][i].weights
            for i in sym[direction].keys():
                j = sym[direction][i]
                wm[j] = wm[i]

        # custom normalization
        idx = {}
        for i, x in enumerate(ids):
            idx[x] = i

        weights = zip(*[wm.weights for wm in maps])

        for vtx, w in enumerate(weights):
            # weight sum
            s = 0
            for wi in w:
                s += wi
            s = round(s, self.decimals)

            # weight sum of paired maps
            sp = 0
            for i0, i1 in id_sym:
                sp += w[idx[i0]] + w[idx[i1]]
            sp = round(sp, self.decimals)

            # weight sum of unpaired maps
            su = s - sp

            # normalize weights
            sn = 1 - su
            if sp > 0 and sn > 0:
                # normalize weights of paired maps
                for i0, i1 in id_sym:
                    self.data['maps'][i0].weights[vtx] *= sn / sp
                    self.data['maps'][i1].weights[vtx] *= sn / sp
            else:
                # normalize weights of unpaired maps
                if s > 0:
                    for i, w in enumerate(w):
                        self.data['maps'][ids[i]].weights[vtx] *= 1 / s
                else:
                    mc.warning('skipped vertex {0} (no weights to mirror)'.format(vtx))

        # mirror dq?
        if 'dq' in self.data['maps']:
            weights = self.data['maps']['dq'].weights

            for table in (1, 0, -1):
                for i in sym[table]:
                    j = sym[table][i]
                    weights[j] = weights[i]

    def merge(self, new_weights):
        if not isinstance(new_weights, mk.Deformer):
            raise RuntimeError('invalid argument: not a deformer')
        if new_weights.deformer != 'skin':
            raise RuntimeError('invalid argument: deformer is not a skin')

        # check validity (size)
        maps = self.data['maps']
        new_maps = new_weights.data['maps']

        s0 = len(list(maps.values())[0].weights)
        s1 = len(list(new_maps.values())[0].weights)
        if s0 != s1:
            raise RuntimeError('not the same size')

        # get shared/unshared tables
        inf_shared = {}
        inf_unshared = []
        inf_locked = []

        for i, wm in iteritems(self.data['maps']):
            if i not in self.data['infs']:
                continue

            shared = False
            for _i, _wm in iteritems(new_weights.data['maps']):
                if set(new_weights.data['infs'][_i].split()) & set(self.data['infs'][i].split()):
                    inf_shared[_i] = i
                    log.debug('shared: {}'.format(self.data['infs'][i]))
                    shared = True
                    break

            locked = False
            try:
                inf = self.get_node(self.data['infs'][i])
                locked = inf['liw'].read()
            except:
                pass

            if locked:
                inf_locked.append(i)
                log.debug('locked: {}'.format(self.data['infs'][i]))

            if not shared:
                inf_unshared.append(i)
                log.debug('unshared: {}'.format(self.data['infs'][i]))

        # compute locked/drop/replace
        for vtx in range(s0):

            w_unshared = 0.0
            w_unshared_locked = 0.0
            w_shared = 0.0
            w_shared_locked = 0.0

            for i in inf_shared:
                if inf_shared[i] in inf_locked:
                    w_old = maps[inf_shared[i]].weights[vtx]
                    w_new = new_maps[i].weights[vtx]
                    if w_new > w_old:
                        maps[inf_shared[i]].weights[vtx] = w_new
                    w_shared_locked += max(w_old, w_new)
                else:
                    w_new = new_maps[i].weights[vtx]
                    maps[inf_shared[i]].weights[vtx] = w_new
                    w_shared += w_new

            for i in inf_unshared:
                w = maps[i].weights[vtx]
                if i in inf_locked:
                    w_unshared_locked += w
                else:
                    w_unshared += w

            k_unshared = 1.0
            k_unshared_locked = 1.0
            k_shared = 1.0
            k_shared_locked = 1.0

            w_all_unshared = w_unshared + w_unshared_locked
            w_all_shared = w_shared + w_shared_locked
            w_all = w_all_unshared + w_all_shared
            w_delta = w_all - 1

            # step by step drop
            if w_delta > 0:
                # unshared first
                if w_unshared > w_delta:
                    k_unshared = 1 - w_delta / w_unshared
                    w_delta = 0
                else:
                    k_unshared = 0
                    w_delta -= w_unshared

                # shared not locked second
                if w_delta > 0:
                    if w_shared > w_delta:
                        k_shared = 1 - w_delta / w_shared
                        w_delta = 0
                    else:
                        k_shared = 0
                        w_delta -= w_shared

                # shared locked third
                if w_delta > 0:
                    if w_shared_locked > w_delta:
                        k_shared_locked = 1 - w_delta / w_shared_locked
                        w_delta = 0
                    else:
                        k_shared_locked = 0
                        w_delta -= w_shared_locked

                # if still delta, unshared locked are > 1 (and it's awkward)
                if w_delta > 0:
                    k_unshared_locked = 1 - w_delta / w_unshared_locked

            else:
                # unshared first
                if w_unshared > 0:
                    k_unshared = (-w_delta + w_unshared) / w_unshared
                    w_delta = 0

                # shared not locked second
                if w_delta < 0 and w_shared > 0:
                    k_shared = (-w_delta + w_shared) / w_shared
                    w_delta = 0

                # shared locked third
                if w_delta < 0 and w_shared_locked > 0:
                    k_shared_locked = (-w_delta + w_shared_locked) / w_shared_locked
                    w_delta = 0

                # if still delta, unshared locked are > 1 (and it's awkward)
                if w_delta < 0:
                    k_unshared_locked = (-w_delta + w_unshared_locked) / w_unshared_locked

            # update weights
            if k_unshared != 1:
                for i in inf_unshared:
                    if i not in inf_locked:
                        maps[i].weights[vtx] *= k_unshared
            if k_shared != 1:
                for i in inf_shared:
                    if inf_shared[i] not in inf_locked:
                        maps[inf_shared[i]].weights[vtx] *= k_shared
            if k_unshared_locked != 1:
                for i in inf_locked:
                    if i not in inf_shared.values():
                        maps[i].weights[vtx] *= k_unshared_locked
            if k_shared_locked != 1:
                for i in inf_shared:
                    if inf_shared[i] in inf_locked:
                        maps[inf_shared[i]].weights[vtx] *= k_shared_locked

    def merge_replace(self, new_weights, vertices=[]):
        if not isinstance(new_weights, mk.Deformer):
            raise RuntimeError('invalid argument: not a deformer')
        if new_weights.deformer != 'skin':
            raise RuntimeError('invalid argument: deformer is not a skin')

        # update infs
        infs = self.data['infs']
        in_infs = copy.copy(new_weights.data['infs'])
        maps = self.data['maps']
        in_maps = new_weights.data['maps']

        new_infs_info = []
        for i, in_inf in in_infs.items():

            if all([in_maps[i].weights[vtx] == 0.0 for vtx in vertices]):
                continue

            info = {'name': in_inf}
            if in_inf in infs:
                info['id'] = list(infs.values()).index(in_inf)
                info['is_in_old'] = True
            else:
                info['id'] = len(infs)
                info['is_in_old'] = False
                infs[info['id']] = in_inf
                maps[info['id']] = WeightMap([0.0] * len(in_maps[0].weights))

            new_infs_info.append(info)

            # update infs

        for vtx in vertices:
            for i, inf in infs.items():
                maps[int(i)].weights[vtx] = 0

            for i, in_inf in in_infs.items():
                i_old = new_infs_info[int(i)]['id']
                maps[i_old].weights[vtx] = in_maps[int(i)].weights[vtx]
