# encoding: utf-8

import re
import logging
import __main__
import traceback
import itertools
from six import string_types
import fnmatch

import maya.OpenMaya as om1
import maya.api.OpenMaya as om
from mikan.maya import cmdx as mx
import maya.cmds as mc

from mikan.core import abstract
from mikan.core.ascii import ascii_title
from mikan.core.abstract.monitor import BuildMonitor
from mikan.core.utils import re_is_int, flatten_list, ordered_load, unique
from mikan.core.logger import create_logger, timed_code, get_version

from .node import Nodes, parse_node
from .control import Group, get_bind_pose
from .deformer import Deformer, DeformerGroup
from .mod import Mod
from .template import Template
from .shape import Shape

from ..lib.configparser import ConfigParser
from ..lib.connect import cleanup_linear_anim_curves
from ..lib.rig import reorder_vdag_set
from ..lib.cleanup import (
    cleanup_shape_orig, cleanup_references, cleanup_layers,
    cleanup_rig_ctrls, cleanup_rig_joints, cleanup_rig_shapes,
    label_skin_joints, cleanup_skin_clusters, cleanup_rig_history
)

__all__ = ['Asset', 'Helper']

log = create_logger()


class Asset(abstract.Asset):

    def __new__(cls, node):
        if not isinstance(node, mx.Node):
            node = mx.encode(str(node))
        if 'gem_type' not in node or node['gem_type'].read() != Asset.type_name:
            raise RuntimeError('node "{}" is not valid'.format(node))
        return super(Asset, cls).__new__(cls)

    def __init__(self, node):
        if not isinstance(node, mx.Node):
            node = mx.encode(str(node))
        self.node = node
        self._path = node.path()

        # debug data
        self.monitor = None

        # cosmetics
        if not self.node.is_referenced():
            try:
                self.node['useOutlinerColor'] = True
                self.node['outlinerColor'] = (1, 0.73, 0.33)
            except:
                pass

    # nodes management -------------------------------------------------------------------------------------------------

    @staticmethod
    def create(name=None):

        with mx.DagModifier() as md:
            node = md.create_node(mx.tTransform, name='asset')
        node.add_attr(mx.String('gem_type'))
        node['gem_type'] = Asset.type_name
        node['gem_type'].lock()

        if not name:
            name = 'mikan'
        name = name.lower()
        Nodes.set_asset_id(node, name)

        return Asset(node)

    def remove(self):
        mx.delete(self.node)
        Nodes.rebuild()

    def rename(self, name):
        self.node['gem_id'] = name
        Nodes.rebuild()

    @property
    def name(self):
        for i in self.node['gem_id'].read().split(';'):
            if '::' not in i:
                return i

    @staticmethod
    def get_assets():
        assets = []
        for node in mx.ls('*.gem_type', o=1, r=1):
            if node['gem_type'].read() == Asset.type_name:
                assets.append(Asset(node))
        return assets

    def init_cleanup(self, remove_constraints=False):

        # cleanup lost nodes
        nodes = mx.ls(et='network')
        grp_nodes = []
        for node in nodes:
            if 'gem_group' in node and 'gem_type' in node and node['gem_type'].read() == Group.type_name:
                grp = Group(node)
                nodes = grp.get_all_nodes()
                n = len(nodes)
                if n == 0:
                    grp_nodes.append(node)
        if grp_nodes:
            log.debug('removed {} empty groups'.format(len(grp_nodes)))
            mx.delete(grp_nodes)

        # reset rig if any
        if 'gem_group' in self.node:
            grp = self.node['gem_group'].input()
            if grp:
                grp = Group(grp)
                for cmd in grp.get_bind_pose_cmds():
                    try:
                        cmd()
                    except:
                        # TODO: allow constraints for mocap build?
                        log.error('/!\\ could not reset: {}'.format(cmd))

        # reset all pose if any
        for node in Nodes.get_id('*::mod.reset') or []:
            get_bind_pose(node, 'reset_pose')

        # delete all built nodes (from current asset)
        current_asset = Nodes.current_asset
        Nodes.rebuild()
        Nodes.current_asset = Nodes.get_asset_id(self.node)

        _nodes = []
        for node in mx.ls('*.gem_deformer', o=1):
            if node.exists:
                try:
                    _node = node
                    tag_node = node['gem_deformer'].output()
                    if tag_node is not None:
                        _node = tag_node

                    _asset_id = Nodes.get_asset_id(_node)

                    if _asset_id != Nodes.current_asset:
                        continue

                    if 'layer.' in node['gem_deformer'].read():
                        Deformer.toggle_layers(node.parent(), top=True)
                    if 'data.' in node['gem_deformer'].read():
                        continue
                    _nodes.append(node)

                    # maya 2018 cleanup
                    if node.is_a(mx.kGeometryFilter):
                        _nodes += node.inputs(type=(mx.tGroupId, mx.tGroupParts))

                except:
                    pass

        dfm_nodes = [str(node) for node in _nodes]

        dg_nodes = []
        dag_nodes = []
        for tag in ('*#::menu', '*::group*', '*::mod.*', '*::hook*', '*::root*', '*::node', '*::ctrl*', '::bind', '::rig'):
            nodes = Nodes.get_id(tag) or []
            if not isinstance(nodes, list):
                nodes = [nodes]
            for node in nodes:
                if node.is_a((mx.tTransform, mx.tJoint)):
                    dag_nodes.append(node)
                else:
                    dg_nodes.append(node)

        for node in dag_nodes:
            for n in set(node.connections(type=mx.kConstraint)):
                dg_nodes.append(n)

        dg_nodes = [str(node) for node in dg_nodes]
        dag_nodes = [str(node) for node in dag_nodes]

        for node in itertools.chain(dfm_nodes, dg_nodes, dag_nodes):
            if mc.objExists(node):
                mc.delete(node)

        cleanup_shape_orig()

        # cleanup template hierarchy
        tpl = self.get_template_root()

        if remove_constraints:
            tpl['v'] = True

            for node in tpl.descendents():
                if not node.is_a((mx.tTransform, mx.tJoint)):
                    continue
                for attr in 'srt':
                    node[attr].read()
                for i in node.inputs(type=mx.kConstraint, plugs=True, connections=True):
                    plug = i[1]
                    plug.unlock()
                    plug.disconnect()

                for _ch in list(node.children()):
                    if _ch.is_a(mx.kConstraint) and not _ch.is_referenced():
                        try:
                            mx.delete(_ch)
                        except:
                            pass

        curves = []
        for node in tpl.descendents(type=mx.tNurbsCurve):
            if not node.is_referenced() and node['create'].input() is not None:
                curves.append(node)
        mx.delete(curves, ch=1)

        Nodes.rebuild()
        Nodes.current_asset = current_asset

    def cleanup(self, modes=None):

        # node space
        current_asset = Nodes.current_asset
        Nodes.current_asset = Nodes.get_asset_id(self.node)

        # mode
        if modes is None:
            modes = set()
        release = 'dev' not in modes

        # scene
        cleanup_references()
        if release:
            cleanup_layers()

        # rig
        cleanup_rig_ctrls(release=release, monitor=self.monitor)
        # create_ctrl_sets(asset=self.node)

        label_skin_joints()
        if release:
            cleanup_rig_joints(self.node, exclude=self.get_template_root())

        tpl = self.get_template_root()
        for node in self.node.children():
            if node != tpl:
                cleanup_rig_shapes(node)
        cleanup_rig_history()

        if release:
            vis_groups = Nodes.get_id('*::vis')
            if vis_groups:
                for node in vis_groups:
                    grp = Group(node)
                    grp.hide()

            # hide utils groups
            for grp in list(self.node.children()):
                if grp.name(namespace=False) in {'dfm', 'dyn_utils'}:
                    try:
                        grp['v'] = False
                    except:
                        pass

        # geometries
        cleanup_shape_orig()
        if release:
            cleanup_skin_clusters()

        # optimize graphs
        if release:
            cleanup_linear_anim_curves()
        # cleanup_mult_matrix()

        # kill me nodes
        nodes = mx.ls('*.kill_me', o=1)
        if nodes:
            mx.delete(nodes)

        # node space
        Nodes.current_asset = current_asset

    def set_version(self):
        if 'gem_version' not in self.node:
            self.node.add_attr(mx.String('gem_version'))
        self.node['gem_version'] = get_version()

    def get_version(self, as_tuple=False):
        if 'gem_version' in self.node:
            version = self.node['gem_version'].read()
        else:
            version = '0.0.0'

        if as_tuple:
            version = [int(x) for x in version.split()[0].split('.')]
            version += [float('inf')] * (3 - len(version))
            version = tuple(version[:3])
        return version

    # templates --------------------------------------------------------------------------------------------------------

    def get_folder(self, name):
        name = name.lower()

        for node in self.node.children(type=mx.tTransform):
            if node.name(namespace=False) == name:
                return node

        with mx.DagModifier() as md:
            node = md.create_node(mx.tTransform, parent=self.node, name=name)
        return node

    def get_template_root(self):
        current_asset = Nodes.current_asset
        Nodes.current_asset = Nodes.get_asset_id(self.node)

        tpl = Nodes.get_id('::template')
        if not tpl:
            tpl = self.get_folder('template')
            Nodes.set_id(tpl, '::template')

        Nodes.current_asset = current_asset

        return tpl

    def get_templates(self, modes=None):
        for tpl in self.get_template_root().children():
            try:
                tpl_root = Template(tpl)
            except:
                continue

            if modes and Helper(tpl_root.node).disabled(modes):
                continue
            yield tpl_root

            for child in tpl_root.get_all_children():
                if modes and Helper(child.node).disabled(modes):
                    continue
                yield child

    def get_top_templates(self):
        templates = []
        for tpl in self.get_template_root().children():
            try:
                templates.append(Template(tpl))
            except:
                pass
        return templates

    def get_helper_nodes(self):
        for node in self.get_template_root().children(type=mx.tTransform):
            if 'gem_type' in node:
                continue

            helper = Helper(node)
            if helper.is_hidden():
                yield helper

    @staticmethod
    def get_rig_nodes(tag, asset=None, templates=None, hierarchy=False):
        if asset and templates is None:
            templates = asset.get_top_templates()
            hierarchy = True

        nodes = []
        for tpl in templates:
            if not isinstance(tpl, Template):
                continue
            if hierarchy:
                sep = ':::'
            else:
                sep = '::'
            asset_id = Nodes.get_asset_id(tpl.node)
            nodes += Nodes.get_id(tpl.name + sep + tag, asset=asset_id, as_list=True)

        nodes = [node for node in unique(nodes) if node is not None]
        if tag in {'skin', 'ctrls'}:
            nodes = reorder_vdag_set(nodes)

        return nodes

    def toggle_shapes_visibility(self):
        asset_id = Nodes.get_asset_id(self.node)
        shapes_tree = Nodes.shapes[asset_id]

        nodes = shapes_tree.get('*::*', [], as_list=True)
        n = len(nodes)
        vis = False

        for tpl in self.get_templates():
            tpl.add_shapes()

        nodes = shapes_tree.get('*::*', [], as_list=True)
        if n == len(nodes):
            for node in nodes:
                if node['v'].read():
                    break  # if one is visible, hide all
            else:
                vis = True

        with mx.DGModifier() as md:
            for node in nodes:
                try:
                    md.set_attr(node['v'], vis)
                except:
                    pass

    # deformers ----------------------------------------------------------------

    def update_deformer_groups(self):
        roots = [self.node]

        for root in roots:
            for node in itertools.chain([root], root.descendents(type=mx.tTransform)):
                helper = Helper(node)

                if helper.is_deformer_group():
                    dfg = DeformerGroup(node)
                    dfg.update()

    # ui ---------------------------------------------------------------------------------------------------------------

    @staticmethod
    def update_menu():
        for _n in mx.ls('mikan_menu', r=1, et='script'):
            mx.delete(_n)

        scr = mc.scriptNode(bs=mikan_menu_loader, st=1, stp='python', n='dagMenuHack')
        mc.scriptNode(scr, eb=1)

        Nodes.set_id(scr, '::menu')

    # processor --------------------------------------------------------------------------------------------------------

    def build_template_groups(self, templates):

        # virtual hooks
        for tpl in templates:
            tpl.build_virtual_dag_hook()

        # build groups loop
        built = set()
        _templates = set(templates)

        while True:
            delayed = []
            n = len(templates)

            for tpl in templates:
                name = tpl.name

                tpl_parents = set(tpl.get_all_parents())
                _delay = False
                for tpl_parent in tpl_parents:
                    if tpl_parent in delayed:
                        delayed.append(tpl)
                        _delay = True
                        break
                if _delay:
                    continue

                group = tpl.get_opt('group')
                if group:
                    if group == name:
                        tpl.set_opt('group', '')
                        log.warning('fixed invalid group option of {}'.format(tpl))
                        delayed.append(tpl)
                        continue

                    _tpl = Nodes.get_id(group)
                    if _tpl in _templates and Template(_tpl).name not in built:
                        delayed.append(tpl)
                        continue

                    names = set([tpl_parent.name for tpl_parent in tpl_parents])
                    if group in names:
                        log.warning('fixed cycle detected in group hierarchy of {}'.format(tpl))
                        tpl.set_opt('group', '')

                tpl.build_groups()
                tpl.build_virtual_dag()
                built.add(name)

            # retry delayed templates
            if len(delayed) == n:
                for tpl in delayed:
                    log.error('/!\\ cannot build groups for {}'.format(tpl))
                break
            templates = delayed

    def make(self, modes=None, pipeline=False, roots=None, exclude=None):
        monitor = BuildMonitor()
        self.monitor = monitor

        # dagmenu injection v1 kill switch
        if __main__.__dict__.get('_mikan_dagmenu_injection') is not None:
            try:
                om.MCommandMessage.removeCallback(__main__._mikan_dagmenu_injection)
            except:
                om1.MCommandMessage.removeCallback(__main__._mikan_dagmenu_injection)
            del __main__._mikan_dagmenu_injection

        # cleanup ids
        mx.clear()
        Nodes.rebuild()
        asset_id = Nodes.get_asset_id(self.node)

        # modes
        if isinstance(modes, string_types):
            modes = {modes}
        elif isinstance(modes, (list, tuple, set)):
            modes = set(modes)
        else:
            modes = set()
        modes.add('maya')

        # init logging
        log.info(ascii_title)
        if modes:
            log.info('make: build "{}" ({})'.format(asset_id, ', '.join(modes)))
        else:
            log.info('make: build "{}"'.format(asset_id))
        if 'debug' in modes:
            log.setLevel(10)

        # custom build?
        monitor.set_step(monitor.STEP_INIT_TEMPLATE)

        if roots is None or not isinstance(roots, list):
            template_roots = list(self.get_top_templates())
            templates = list(self.get_templates(modes=modes))
            roots = [self.node]
        else:
            roots = list(flatten_list([roots]))

            template_exclude = []
            if exclude is not None:
                exclude = list(flatten_list([exclude]))
            for n in exclude:
                if 'gem_type' in n and n['gem_type'].read() == Template.type_name:
                    tpl = Template(n)
                    template_exclude.append(tpl)
                    for _tpl in tpl.get_all_children():
                        template_exclude.append(_tpl)

            template_roots = []
            for n in roots:
                if 'gem_type' in n and n['gem_type'].read() == Template.type_name:
                    tpl = Template(n)
                    template_roots.append(tpl)

            templates = []
            for tpl in template_roots:
                if tpl in templates or tpl in template_exclude:
                    continue
                templates.append(tpl)
                for _tpl in tpl.get_all_children():
                    if _tpl in templates or _tpl in template_exclude:
                        continue
                    templates.append(_tpl)

        # processor
        with timed_code('make', force=True):

            # cleanup
            with timed_code('make: ' + monitor.set_step(monitor.STEP_CLEANUP_RIG)):
                mc.refresh()
                self.init_cleanup()

            log_filter = LogFilter()
            log_filter.start()

            # build all templates
            exception = None
            try:
                # build templates
                monitor.set_step(monitor.STEP_TEMPLATES)

                current_asset = Nodes.current_asset
                Nodes.current_asset = asset_id

                for tpl in templates:
                    if not tpl.check_validity():
                        raise RuntimeError('/!\\ "{}" shares the same id with another template'.format(tpl))

                with timed_code('make: branches'):
                    for template in template_roots:
                        template.build_template_branches()

                with timed_code('make: templates'):
                    for tpl in templates:
                        monitor.current_task = tpl
                        tpl.add_shapes()
                        tpl.build(modes=modes)
                    monitor.current_task = None

                # tmp cmdx cache flush
                if len(templates) > 1000:
                    mx.clear_instances()

                # schedule and run mod and deformers
                with timed_code('make: ' + monitor.set_step(monitor.STEP_SCHEDULER)):
                    scheduler = Scheduler(roots, modes=modes, exclude=exclude, monitor=monitor)
                with timed_code('make: ' + monitor.set_step(monitor.STEP_MODS_DEFORMERS)):
                    scheduler.run(pipeline=pipeline)

                # finalize rig
                with timed_code('make: ' + monitor.set_step(monitor.STEP_GROUPS)):
                    self.build_template_groups(templates)

                Template.build_isolate_skeleton()

                Asset.update_menu()

            except SchedulerError as e:
                exception = e
                log.warning('make: mods/deformer aborted!')

            except Exception as e:
                exception = e
                msg = traceback.format_exc().strip('\n')
                log.critical(msg)
                monitor.errors += 1

            Nodes.current_asset = current_asset

            if exception is not None and ('debug' in modes or pipeline):
                log_filter.end()
                msg = u'make: aborted! 😱' + (' (halt from pipeline)' if pipeline else '')
                raise RuntimeError(msg)

            log_filter.end()
            mc.select(clear=True)

            # cleanup
            with timed_code('make: ' + monitor.set_step(monitor.STEP_CLEANUP)):
                log.info('make: cleaning template')
                with mx.DagModifier() as md:
                    md.set_attr(self.get_template_root()['v'], False)
                for template in template_roots:
                    template.delete_template_branches()
                self.cleanup(modes=modes)
                mc.select(clear=True)

                Nodes.cleanup()
                mx.clear_instances()

            # exit
            self.set_version()

        monitor.report()
        if monitor.errors:
            log.info(u'make: job\'s done! 🧐')
        else:
            log.success(u'make: job\'s done! 😎')
        monitor.set_step(monitor.STEP_FINISHED)


mikan_menu_loader = '''# mikan menu loader
from mikan.maya.ui.dagmenu import DagMenu
DagMenu.inject()
'''


class Scheduler(object):
    mod_flags = ['mod']
    dfm_flags = ['deformer']

    def __init__(self, roots, modes=None, mod_flags=None, dfm_flags=None, exclude=None, monitor=None):
        self.roots = roots
        self.stack = []
        if exclude is None:
            exclude = []
        elif not isinstance(exclude, list):
            exclude = [exclude]

        if monitor is None:
            monitor = BuildMonitor()
        self.monitor = monitor

        # parse hierarchy
        self.modes = modes
        if mod_flags is None:
            mod_flags = Scheduler.mod_flags
        if dfm_flags is None:
            dfm_flags = Scheduler.dfm_flags

        for root in self.roots:
            for node in itertools.chain([root], root.descendents()):
                if node in exclude:
                    continue
                helper = Helper(node)
                if 'notes' in node and not helper.disabled(self.modes):
                    cfg = ConfigParser(node)

                    for flag in mod_flags:
                        for ini in cfg[flag]:

                            args = self.get_args(ini)
                            if helper.disabled(self.modes, args['mode']):
                                continue

                            data = Mod.parse(ini)
                            if data:
                                # split block
                                for cmd in data['commands']:

                                    if 'errors' in cmd:
                                        monitor.log(
                                            Mod.STATUS_CANCEL,
                                            [(logging.ERROR, msg) for msg in cmd['errors']],
                                            'mod',
                                            node.name(namespace=True),
                                            cmd['yml']
                                        )
                                        continue

                                    mod_data = {
                                        'class': Mod,
                                        'data': {
                                            'mod': cmd['mod'],
                                            'data': cmd['data'],
                                            'node': data['node']
                                        },
                                        'source': node,
                                        'yml': cmd['yml']
                                    }

                                    mod_data.update(args)
                                    self.stack.append(mod_data)

                    for flag in dfm_flags:
                        for ini in cfg[flag]:

                            args = self.get_args(ini)
                            if helper.disabled(self.modes, args['mode']):
                                continue

                            data = Deformer.parse(ini)
                            if data:
                                dfm_data = {
                                    'class': Deformer,
                                    'data': data,
                                    'source': node,
                                    'yml': ini.read()
                                }
                                dfm_data.update(args)
                                self.stack.append(dfm_data)

                # link group if needed
                if helper.is_deformer_group():
                    DeformerGroup(node).set_filtered()

        # first pass reorder
        stack_mod = []
        stack_dfm = []
        stack_mod_dfm = []
        for cmd in self.stack:
            if cmd['class'] == Mod:
                # if '->' in cmd['yml']:
                #     stack_mod_dfm.append(cmd)
                # else:
                stack_mod.append(cmd)
            else:
                stack_dfm.append(cmd)
        self.stack = stack_mod + stack_dfm + stack_mod_dfm

        self.stack = sorted(self.stack, key=lambda x: (x['priority'] * -1))

    @staticmethod
    def get_args(ini):
        data = {'priority': 0, 'condition': None}
        modes = []

        for line in ini.get_lines():
            if line.startswith('#!'):
                for arg in re.findall(r"[\w'^!*~+-]+", line[2:]):
                    if re_is_int.match(arg):
                        data['priority'] = int(arg)
                    else:
                        modes.append(arg)

            elif line.startswith('#?'):
                condition = line[2:].strip()
                if not Scheduler.evaluate_condition(condition, ini.parser.node):
                    data['condition'] = condition

            elif line.startswith('#$'):
                line = line[2:].strip()
                var, sep, plug = line.partition(':')
                var_plug = Mod.add_var(var.strip(), ini.parser.node)

                plug = parse_node(plug.strip(), silent=True, add_hook=False)
                if isinstance(plug, mx.Plug):
                    var_plug.write(plug.read())

        data['mode'] = ';'.join(modes)
        return data

    @staticmethod
    def uniq(seq):
        seen = set()
        seen_add = seen.add
        return [x for x in seq if x not in seen and not seen_add(x)]

    def run(self, pipeline=False):
        if len(self.stack) == 0:
            return

        debug = 'debug' in self.modes
        halt_on_error = debug or pipeline

        failed_count = 0
        failed_stack = []
        while True:
            if failed_count:
                log.debug('scheduler: delayed stack')

            for job in self.stack:
                cls = job['class']
                data = job['data']
                source = job['source']
                source_str = source.name(namespace=True)

                self.monitor.current_task = None
                self.monitor.current_yaml = job['yml']

                if job['condition']:
                    data.pop('ini', None)  # strip ini repr from deformers
                    log.debug('/!\\ {} skip: {}, {}'.format(job['condition'], cls.__name__, data))
                    continue

                if cls is Mod:
                    if not data['node'].exists:
                        continue

                    # check if module exists
                    cmd = data['mod']
                    if cmd not in Mod.modules:
                        msg = "-- mod '{}' does not exist ({})".format(cmd, source_str)
                        log.error(msg)
                        if halt_on_error:
                            raise SchedulerError()
                        self.monitor.log(Mod.STATUS_CANCEL, [(logging.ERROR, msg)], 'mod', source_str, job['yml'])
                        continue

                    mod = Mod(cmd, node=data['node'], data=data['data'], source=source)
                    if mod:
                        self.monitor.current_task = mod
                        state = mod.execute(modes=self.modes, source=source_str)

                        if state == Mod.STATUS_DELAY:
                            job['unresolved'] = mod.unresolved[:]
                            failed_stack.append(job)
                            continue

                        self.monitor.log(state, mod.logs, 'mod', source_str, job['yml'])
                        if state == Mod.STATUS_CRASH and halt_on_error:
                            raise SchedulerError()

                elif cls is Deformer:
                    dfm = Deformer(**data)
                    if 'transform' not in data:
                        continue

                    with timed_code('binding {}.{}'.format(data['transform'], data.get('id', data['deformer'])), level='debug'):
                        self.monitor.current_task = dfm
                        state = dfm.bind(modes=self.modes, source=source_str)

                    if state == Deformer.STATUS_DELAY:
                        job['unresolved'] = dfm.unresolved[:]
                        failed_stack.append(job)
                        continue

                    self.monitor.log(state, dfm.logs, 'deformer', source_str, job['yml'])
                    if state == Deformer.STATUS_CRASH and halt_on_error:
                        raise SchedulerError()

            # retry failed stack
            if len(failed_stack) != failed_count:
                self.stack = failed_stack
                failed_count = len(failed_stack)
                failed_stack = []

            else:
                for job in failed_stack:
                    cls = job['class']
                    data = job['data']
                    source = job['source']
                    source_str = source.name(namespace=True)

                    if cls is Mod:
                        cmd = data['mod']
                        mod = Mod(cmd, node=data['node'], data=data['data'], source=source)
                        if mod:
                            mod.log_error('-- cancel: {}  # source: {}'.format(mod, source_str))
                            mod.log_warning('unresolved ids: {}'.format(job['unresolved']))
                            mod.log_summary()
                            self.monitor.log(Mod.STATUS_CANCEL, mod.logs, 'mod', source_str, job['yml'])

                    elif cls is Deformer:
                        dfm = Deformer(**data)
                        if dfm:
                            dfm.log_error('-- cancel: {}  # source: {}'.format(dfm, source_str))
                            dfm.log_warning('unresolved ids: {}'.format(job['unresolved']))
                            dfm.log_summary()
                            self.monitor.log(Deformer.STATUS_CANCEL, dfm.logs, 'deformer', source_str, job['yml'])

                # stop retry stack when unchanged
                break

        self.monitor.current_task = None
        self.monitor.current_yaml = None

    @staticmethod
    def evaluate_condition(condition, parser_node):
        if not condition:
            return True

        # parse condition
        condition = condition.replace('->', '--')
        tokens = re.split(r"(==|!=|<=|>=|<|>|&&|\|\|)", condition)
        tokens = [token.strip().replace('--', '->') for token in tokens if token.strip()]

        # get nodes and plug values
        for i, e in enumerate(tokens):

            if e.startswith('$'):
                tokens[i] = Mod.get_var(e[1:], parser_node)

            elif '::' in e or '->' in e:
                failed = []
                node = parse_node(e, failed=failed, silent=True)
                if failed:
                    return False
                tokens[i] = node
                if isinstance(node, list):
                    tokens[i] = node[0]
            else:
                tokens[i] = ordered_load(tokens[i])

            if isinstance(tokens[i], mx.Plug):
                tokens[i] = tokens[i].read()

        # evaluate
        if len(tokens) == 1:
            return bool(tokens[0])
        elif len(tokens) == 2:
            a, b = tokens
            return a == b
        elif len(tokens) == 3 and tokens[1] in ('==', '!=', '<', '<=', '>', '>='):
            a, op, b = tokens
            if op == '==':
                return a == b
            elif op == '!=':
                return a != b
            elif op == '<':
                return a < b
            elif op == '<=':
                return a <= b
            elif op == '>':
                return a > b
            elif op == '>=':
                return a >= b

        log.warning('/!\\ invalid condition: {}'.format(' '.join(condition)))
        return True


class SchedulerError(Exception):
    pass


class Helper(object):

    def __init__(self, node):
        if isinstance(node, (Asset, Template, DeformerGroup)):
            node = node.node
        if not isinstance(node, mx.Node):
            node = mx.encode(str(node))
        self.node = node

    def __eq__(self, other):
        if isinstance(other, Helper):
            return self.node == other.node
        return False

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash(self.node) ^ hash(Helper)

    @property
    def name(self):
        return self.node.name()

    def has_mod(self):
        if 'notes' in self.node:
            cfg = ConfigParser(self.node)
            if 'mod' in cfg:
                if not self.node.is_referenced() and 'gem_id' not in self.node:
                    try:
                        self.node['useOutlinerColor'] = 1
                        self.node['outlinerColor'] = (0.73, 0.33, 1)
                    except:
                        pass

                return True
        return False

    def has_deformer(self):
        if 'notes' in self.node:
            cfg = ConfigParser(self.node)
            if 'deformer' in cfg:
                if not self.node.is_referenced() and 'gem_id' not in self.node:
                    try:
                        self.node['useOutlinerColor'] = 1
                        self.node['outlinerColor'] = (0.73, 1, 0.33)
                    except:
                        pass

                return True
        return False

    def is_deformer_group(self):
        if 'gem_deformers' in self.node:
            if not self.node.is_referenced():
                try:
                    self.node['useOutlinerColor'] = 1
                    self.node['outlinerColor'] = (0.73, 1, 0.33)
                except:
                    pass

            return True
        return False

    def is_template(self):
        if 'gem_type' in self.node and self.node['gem_type'].read() == Template.type_name:
            return True
        return False

    def is_branch(self):
        if 'gem_type' in self.node and self.node['gem_type'].read() == 'branch':
            return True
        return False

    def is_branch_edit(self):
        if 'gem_type' in self.node and self.node['gem_type'].read() == 'edit':
            return True
        return False

    def is_hidden(self):
        return self.name.startswith('_')

    def is_protected(self):
        return self.name.startswith('__') and self.name.endswith('__')

    def is_shape(self):
        return 'gem_shape' in self.node

    def remove(self):
        mx.delete(self.node)

    def rename(self, name):
        if self.node.is_referenced():
            return
        if self.is_hidden() and not name.startswith('_'):
            name = '_' + name

        node_name = self.node.name()
        ns = node_name.split(':')[0] + ':' if ':' in node_name else ''
        self.node.rename(ns + name)

    def get_children(self):
        for node in self.node.children():
            if 'gem_type' in node or 'gem_shape' in node:
                continue
            if not node.is_a(mx.tTransform):
                continue
            yield Helper(node)

    def get_all_children(self, children=None):
        if children is None:
            children = []

        _children = list(self.get_children())

        children.extend(_children)
        for child in _children:
            child.get_all_children(children)

        return children

    def as_DeformerGroup(self, filter_deformer_type=None):
        dfms = []
        cfg = ConfigParser(self.node)
        for key in cfg:
            if key == 'deformer':
                ini = cfg[key]
                if ini:
                    data = Deformer.parse(ini)
                    if filter_deformer_type:
                        if filter_deformer_type == data['deformer']:
                            dfms.append(Deformer(**data))
                    else:
                        dfms.append(Deformer(**data))
        return dfms

    def as_Deformers(self, filter_deformer_type=None):
        dfms = []
        cfgs = ConfigParser(self.node)
        for ini in cfgs:
            if ini.name == 'deformer':
                data = Deformer.parse(ini)
                if filter_deformer_type:
                    if filter_deformer_type == data['deformer']:
                        dfms.append(Deformer(**data))
                else:
                    dfms.append(Deformer(**data))
        return dfms

    @staticmethod
    def filter_nodes(nodes, type=None, name=None):
        for node in nodes:

            if name and not fnmatch.fnmatch(node.name, name):
                continue

            if type == 'template':
                if node.is_deformer_group():
                    yield node
            elif type == 'deformer_group':
                if node.is_template():
                    yield node
            elif type == 'shape':
                if node.is_shape():
                    yield node
            elif type == 'deformer':
                if node.has_deformer():
                    yield node
            else:
                yield node

    def get_all_children_filtered(self, type=None, name=None):
        return self.filter_nodes(self.get_all_children(), type, name)

    def get_child_templates(self):
        for node in self.node.children():
            if 'gem_type' in node and node['gem_type'].read() == Template.type_name:
                yield Template(node)

    # -- scheduling
    def is_scheduling(self):
        if 'gem_enable' in self.node:
            return True
        if 'gem_enable_modes' in self.node:
            return True
        return False

    def disabled(self, modes=None, value=None):
        if modes is None:
            modes = set()

        enable_modes = ''
        if value is not None:
            node = None
            enable_modes = value
        else:
            node = self.node

        if node and 'gem_enable' in node:
            if not node['gem_enable'].read():
                # item is specifically disabled
                return True

        if node and 'gem_enable_modes' in node:
            enable_modes = node['gem_enable_modes'].read() or ''

        # get modes
        modes_allowed = set()
        modes_excluded = set()
        for _mode in re.findall(r"[\w'^!*~+-]+", enable_modes):
            if _mode[0] in r'-~^':
                modes_excluded.add(_mode[1:])
            else:
                modes_allowed.add(_mode)

        # modes requested
        if modes_allowed and not modes_allowed.issubset(modes):
            return True

        # modes forbidden
        if modes & modes_excluded:
            return True

        # check hierarchy
        if node:
            parent = node.parent()
            if parent:
                return Helper(parent).disabled(modes)

        return False

    def set_enable(self, enable):
        if enable:
            if 'gem_enable' in self.node:
                self.node['gem_enable'] = True
        else:
            if 'gem_enable' not in self.node:
                self.node.add_attr(mx.Boolean('gem_enable', default=True, keyable=True))
            self.node['gem_enable'] = False

    def disable(self):
        self.set_enable(False)

    def enable(self):
        self.set_enable(True)

    def set_enable_modes(self, modes):
        if modes:
            if 'gem_enable_modes' not in self.node:
                self.node.add_attr(mx.String('gem_enable_modes'))
            self.node['gem_enable_modes'] = modes
        else:
            if 'gem_enable_modes' in self.node:
                self.node['gem_enable_modes'] = modes

    def has_enable(self):
        return 'gem_enable' in self.node

    def has_enable_modes(self):
        return 'gem_enable_modes' in self.node

    def get_enable(self):
        if self.has_enable():
            return self.node['gem_enable'].read()
        return True

    def get_enable_modes(self):
        if self.has_enable_modes():
            return self.node['gem_enable_modes'].read() or ''
        return ''

    def reset_enable(self):
        if self.node.is_referenced():
            self.enable()
            return
        if 'gem_enable' in self.node:
            self.node.delete_attr(self.node['gem_enable'])

    def reset_enable_modes(self):
        if self.node.is_referenced():
            self.set_enable_modes('')
            return
        if 'gem_enable_modes' in self.node:
            self.node.delete_attr(self.node['gem_enable_modes'])

    def scale(self, scale, root=None):
        exclude = []
        if root is None:
            root = self.node

        for node in root.descendents():
            if not node.is_a(mx.kTransform):
                continue

            # scale modifiers
            helper = Helper(node)
            if helper.has_mod():
                if 'gem_scale' not in node:
                    with mx.DGModifier() as md:
                        md.add_attr(node, mx.Double('gem_scale', keyable=True, default=1))
                if node['gem_scale'].editable:
                    with mx.DGModifier() as md:
                        md.set_attr(node['gem_scale'], node['gem_scale'].read() * scale)

            # force scale
            if 'gem_scale_template' in node and node['gem_scale_template'].read():
                with mx.DGModifier() as md:
                    md.set_attr(node['s'], node['s'].as_vector() * scale)
                exclude += node.descendents()

            # scale translations
            if node not in exclude:
                for attr in ('t', 'rp', 'sp', 'rpt', 'spt'):
                    for dim in 'xyz':
                        plug = node[attr + dim]
                        if plug.editable:
                            with mx.DGModifier() as md:
                                md.set_attr(plug, plug.read() * scale)

                if 'gem_shape' in node:
                    for shp in node.children():
                        if not shp.is_a(mx.tTransform) or not shp.shape():
                            continue
                        if shp['s'].editable:
                            with mx.DGModifier() as md:
                                md.set_attr(shp['s'], shp['s'].as_vector() * scale)

                if node.shape() and 'gem_shape' not in node.parent():
                    if not node['s'].editable or node.child():
                        shp = Shape(node)
                        scale_shape = True
                        for cv in shp.get_shapes():
                            if cv['create'].input():
                                scale_shape = False
                                break
                        if scale_shape:
                            Shape(node).scale(scale)
                    else:
                        with mx.DGModifier() as md:
                            md.set_attr(node['s'], node['s'].as_vector() * scale)


class LogFilter(object):

    def __init__(self):
        self.callback = None

    def start(self):
        if self.callback is not None:
            self.end()
        self.callback = om1.MCommandMessage.addCommandOutputFilterCallback(LogFilter.filter)

    def end(self):
        if self.callback is not None:
            om1.MMessage.removeCallback(self.callback)
        self.callback = None

    @staticmethod
    def filter(msg, msgType, filterOutput, clientData):

        shunt = False

        # line = str(msg)
        if msgType == om1.MCommandMessage.kWarning:
            # line = '# Warning: %s #\n' % line
            # shunt = True
            pass
        # elif msgType == om1.MCommandMessage.kError:
        #     # line = '// Error: %s //\n' % line
        #     shunt = True
        elif msgType == om1.MCommandMessage.kResult:
            # line = '# Result: %s #\n' % line
            shunt = True

        # sys.__stdout__.write(line)
        # sys.__stdout__.flush()
        om1.MScriptUtil.setBool(filterOutput, shunt)
