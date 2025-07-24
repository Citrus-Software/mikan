# encoding: utf-8

import re
import logging
import traceback

import meta_nodal_py as kl

from mikan.core.ascii import ascii_title
from mikan.core.utils import re_is_int, ordered_load
from mikan.core.abstract.monitor import BuildMonitor
from mikan.core.logger import create_logger, timed_code, get_version
import mikan.core.abstract.asset as abstract

from ..lib.cleanup import *
from ..lib.commands import *
from ..lib import ConfigParser

from .node import Nodes, parse_node
from .template import Template
from .mod import Mod
from .deformer import Deformer
from .control import Group

__all__ = ['Asset', 'Helper']

log = create_logger()


class Asset(abstract.Asset):

    def __new__(cls, node):
        if not isinstance(node, kl.SceneGraphNode) and not node.get_dynamic_plug('gem_type'):
            raise RuntimeError(f'node "{node}" is not valid')
        if node.gem_type.get_value() == Asset.type_name:
            return super(Asset, cls).__new__(cls)

    def __init__(self, node):
        self.node = node

        # debug data
        self.monitor = None

    # nodes management -------------------------------------------------------------------------------------------------

    @staticmethod
    def create(name=None):

        node = kl.SceneGraphNode(find_root(), 'asset')
        add_plug(node, 'gem_type', str, default_value=Asset.type_name)

        if not name:
            name = 'mikan'
        name = name.lower()
        Nodes.set_asset_id(node, name)

        return Asset(node)

    def remove(self):
        self.node.remove_from_parent()
        Nodes.rebuild()

    @property
    def name(self):
        for i in self.node.gem_id.get_value().split(';'):
            if '::' not in i:
                return i

    @staticmethod
    def get_assets():
        assets = []
        for node in ls():
            if not node.get_plug('gem_type'):
                continue
            if node.gem_type.get_value() == Asset.type_name:
                assets.append(Asset(node))
        return assets

    def init_cleanup(self):

        current_asset = Nodes.current_asset
        Nodes.rebuild()
        Nodes.current_asset = Nodes.get_asset_id(self.node)

        # TODO: delete all built nodes (from current asset)

        Nodes.current_asset = current_asset

    def cleanup(self, modes=None):

        # node space
        current_asset = Nodes.current_asset
        Nodes.current_asset = Nodes.get_asset_id(self.node)

        # mode
        if modes is None:
            modes = set()
        release = 'dev' not in modes

        # rig
        cleanup_rig_ctrls()

        tpl = self.get_template_root()
        for node in self.node.get_children():
            if node != tpl and isinstance(node, kl.SceneGraphNode):
                cleanup_rig_shapes(node)

        if release:
            # hide vis groups
            vis_groups = Nodes.get_id('*::vis')
            if vis_groups:
                for node in vis_groups:
                    grp = Group(node)
                    grp.hide()

            # hide utils groups
            for node in ('dfm', 'dyn_utils'):
                grp = self.node.find(node)
                try:
                    grp.show.set_value(False)
                except:
                    pass

        # optimize graph
        if release:
            cleanup_linear_anim_curves()

        # node space
        Nodes.current_asset = current_asset

    def set_version(self):
        plug = self.node.get_dynamic_plug('gem_version')
        if not plug:
            plug = add_plug(self.node, 'gem_version', str)
        plug.set_value(get_version())

    def get_version(self, as_tuple=False):
        plug = self.node.get_dynamic_plug('gem_version')
        if plug:
            version = plug.get_value()
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
        node = self.node.find(name)
        if not node:
            node = kl.SceneGraphNode(self.node, name)
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
        for tpl in self.get_template_root().get_children():
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
        for tpl in self.get_template_root().get_children():
            try:
                templates.append(Template(tpl))
            except:
                pass
        return templates

    def get_helper_nodes(self):
        for node in self.get_template_root().get_children():
            if node.get_dynamic_plug('gem_type'):
                continue

            helper = Helper(node)
            if helper.has_mod():
                yield helper

    # processor ----------------------------------------------------------------

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
                    log.error(f'/!\\ cannot build groups for {tpl}')
                break
            templates = delayed

    @property
    def current_command(self):
        if self.scheduler is not None:
            return self.scheduler.current_command
        elif self.current_template:
            return self.current_template
        else:
            return self.current_step

    @property
    def current_yaml(self):
        if self.scheduler is not None:
            return self.scheduler.current_yaml

    def make(self, modes=None, pipeline=False):
        monitor = BuildMonitor()
        self.monitor = monitor

        # cleanup ids
        Nodes.rebuild()
        asset_id = Nodes.get_asset_id(self.node)

        # modes
        if isinstance(modes, str):
            modes = {modes}
        elif isinstance(modes, (list, tuple, set)):
            modes = set(modes)
        else:
            modes = set()
        modes.add('tangerine')

        # init logging
        log.info(ascii_title)
        if modes:
            log.info(f'make: build "{asset_id}" ({", ".join(modes)})')
        else:
            log.info(f'make: build "{asset_id}"')
        if 'debug' in modes:
            log.setLevel(10)

        # processor
        with timed_code('make'):

            # cleanup
            monitor.set_step(monitor.STEP_CLEANUP_RIG)
            self.init_cleanup()

            # build all templates
            exception = None
            try:
                # build templates
                monitor.set_step(monitor.STEP_TEMPLATES)

                current_asset = Nodes.current_asset
                Nodes.current_asset = asset_id

                templates = list(self.get_templates(modes=modes))

                for tpl in templates:
                    if not tpl.check_validity():
                        raise RuntimeError(f'/!\\ "{tpl}" shares the same id with another template')

                for template in self.get_top_templates():
                    template.build_template_branches()

                for tpl in templates:
                    monitor.current_task = tpl
                    tpl.add_shapes()
                    tpl.build(modes=modes)
                monitor.current_task = None

                # schedule mod and deformers
                with SplitPostponer():
                    monitor.set_step(monitor.STEP_SCHEDULER)
                    scheduler = Scheduler([self.node], modes=modes, monitor=monitor)

                    monitor.set_step(monitor.STEP_MODS_DEFORMERS)
                    scheduler.run(pipeline=pipeline)

                # finalize rig
                monitor.set_step(monitor.STEP_GROUPS)
                self.build_template_groups(templates)

                Template.build_isolate_skeleton()

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
                msg = u'make: aborted! 😱' + (' (halt from pipeline)' if pipeline else '')
                raise RuntimeError(msg)

            # cleanup
            log.info('make: cleaning template')
            monitor.set_step(monitor.STEP_CLEANUP)
            self.get_template_root().show.set_value(False)
            for template in self.get_top_templates():
                template.delete_template_branches()
            self.cleanup(modes=modes)

            # exit
            self.set_version()

        monitor.report()
        if monitor.errors:
            log.info(u'make: job\'s done! 🧐')
        else:
            log.success(u'make: job\'s done! 😎')
        monitor.set_step(monitor.STEP_FINISHED)


class Scheduler(object):
    mod_flags = ['mod']
    dfm_flags = ['deformer']

    def __init__(self, roots, modes=None, mod_flags=None, dfm_flags=None, monitor=None):

        Deformer.cache_nodes()

        self.roots = roots
        self.stack = []

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
            for node in [root] + ls(root=root):
                helper = Helper(node)
                if node.get_dynamic_plug('notes') and not helper.disabled(self.modes):
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
                                            node.get_name(),
                                            cmd['yml']
                                        )
                                        continue

                                    mod_data = {
                                        'data': {
                                            'mod': cmd['mod'],
                                            'data': cmd['data'],
                                            'node': data['node']
                                        },
                                        'class': Mod,
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
                                    'data': data,
                                    'class': Deformer,
                                    'source': node,
                                    'yml': ini.read()
                                }
                                dfm_data.update(args)
                                self.stack.append(dfm_data)

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
                if kl.is_plug(plug):
                    var_plug.set_value(plug.get_value())

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
                source_str = source.get_name()

                self.monitor.current_task = None
                self.monitor.current_yaml = job['yml']

                if job['condition']:
                    data.pop('ini', None)  # strip ini repr from deformers
                    log.warning(f"/!\\ {job['condition']} skip: {cls.__name__}, {data}")
                    continue

                if cls is Mod:
                    if not data['node'].has_parent():
                        continue

                    # check if module exists
                    cmd = data['mod']
                    if cmd not in Mod.modules:
                        msg = f"-- mod '{cmd}' does not exist ({source_str})"
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
                    if not dfm:  # hotfix
                        continue

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
                    source_str = source.get_name()

                    if cls is Mod:
                        cmd = data['mod']
                        mod = Mod(cmd, node=data['node'], data=data['data'], source=source)
                        if mod:
                            mod.log_error(f'-- cancel: {mod}  # source: {source_str}')
                            mod.log_warning(f'unresolved ids: {job["unresolved"]}')
                            mod.log_summary()
                            self.monitor.log(Mod.STATUS_CANCEL, mod.logs, 'mod', source_str, job['yml'])

                    elif cls is Deformer:
                        dfm = Deformer(**data)
                        if dfm:
                            dfm.log_error(f'-- cancel: {dfm}  # source: {source_str}')
                            dfm.log_warning(f'unresolved ids: {job["unresolved"]}')
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

            if kl.is_plug(tokens[i]):
                tokens[i] = tokens[i].get_value()

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


class SplitPostponer(object):

    def __enter__(self):
        self.postponer = kl.SplitPostponer()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.postponer.finish()


class Helper(object):

    def __init__(self, node):
        self.node = node

    @property
    def name(self):
        # TODO: keep hidden
        return self.node.get_name()

    def has_mod(self):
        if self.node.get_dynamic_plug('notes'):
            cfg = ConfigParser(self.node)
            if 'mod' in cfg:
                return True

    def has_deformer(self):
        if self.node.get_dynamic_plug('notes'):
            cfg = ConfigParser(self.node)
            if 'deformer' in cfg:
                return True

    def is_hidden(self):
        return self.node.get_name().startswith('_')

    def rename(self, name):
        self.node.rename(name)

    # -- scheduling
    def is_scheduling(self):
        if self.node.get_dynamic_plug('gem_enable'):
            return True
        if self.node.get_dynamic_plug('gem_enable_modes'):
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

        if node and node.get_dynamic_plug('gem_enable'):
            if not node.gem_enable.get_value():
                # item is specifically disabled
                return True

        if node and node.get_dynamic_plug('gem_enable_modes'):
            enable_modes = node.gem_enable_modes.get_value() or ''

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
            parent = node.get_parent()
            if parent and not isinstance(parent, kl.RootNode):
                return Helper(parent).disabled(modes)

        return False

    def set_enable(self, enable):
        if enable:
            if self.node.get_dynamic_plug('gem_enable'):
                self.node.gem_enable.set_value(True)
        else:
            if not self.node.get_dynamic_plug('gem_enable'):
                add_plug(self.node, 'gem_enable', bool, default_value=True, keyable=1)
            self.node.gem_enable.set_value(False)

    def disable(self):
        self.set_enable(False)

    def enable(self):
        self.set_enable(True)

    def set_enable_modes(self, modes):
        if not self.node.get_dynamic_plug('gem_enable_modes'):
            add_plug(self.node, 'gem_enable_modes', str, default_value='')
        self.node.gem_enable_modes.set_value(modes)
