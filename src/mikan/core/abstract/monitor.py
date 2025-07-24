# coding: utf-8

__all__ = ['JobMonitor', 'BuildMonitor']

import logging

from mikan.core.logger import create_logger

log = create_logger()


class JobMonitor(object):
    STATUS_CANCEL = -1
    STATUS_DONE = 0
    STATUS_DELAY = 1
    STATUS_INVALID = 2
    STATUS_ERROR = 3
    STATUS_CRASH = 4

    def __init__(self):
        self.logs = []
        self.unresolved = []

    def clear_logs(self):
        del self.logs[:]
        del self.unresolved[:]

    def log(self, level, msg, insert=-1):
        if insert < 0:
            insert = len(self.logs) + insert + 1
        if level in (logging.WARNING, logging.ERROR):
            if not msg.startswith('--'):
                msg = '/!\\ ' + msg
        self.logs.insert(insert, (level, msg))

    def log_warning(self, msg, insert=-1):
        self.log(logging.WARNING, msg, insert)

    def log_error(self, msg, insert=-1):
        self.log(logging.ERROR, msg, insert)

    def log_summary(self):
        if self.unresolved:
            self.log_warning('unresolved ids: {}'.format(self.unresolved), insert=1)

        for level, msg in self.logs:
            if level == logging.WARNING:
                log.warning(msg)
            elif level == logging.ERROR:
                log.error(msg)
            elif level == logging.CRITICAL:
                log.critical(msg)

    def count_warnings(self):
        n = 0
        for lvl, msg in self.logs:
            if lvl == logging.WARNING:
                n += 1
        if self.unresolved:
            n += 1
        return n

    def count_errors(self):
        n = 0
        for lvl, msg in self.logs:
            if lvl >= logging.ERROR:
                n += 1
        return n

    def count_summary(self):
        msg = []
        n = self.count_warnings()
        if n:
            msg.append('{} warning{}'.format(n, 's' if n > 1 else ''))
        n = self.count_errors()
        if n:
            msg.append('{} error{}'.format(n, 's' if n > 1 else ''))
        return ', '.join(msg)


class BuildMonitor(object):
    STEP_INIT_TEMPLATE = 'parse template'
    STEP_CLEANUP_RIG = 'delete rig'
    STEP_TEMPLATES = 'build templates'
    STEP_SCHEDULER = 'scheduler'
    STEP_MODS_DEFORMERS = 'mods/deformers'
    STEP_GROUPS = 'groups'
    STEP_CLEANUP = 'cleanup'
    STEP_FINISHED = 'build complete'

    def __init__(self):
        self.scheduler = None
        self.current_step = None
        self.current_task = None
        self.current_yaml = None

        self.warnings = 0
        self.errors = 0

        self.jobs_canceled = []
        self.jobs_failed = []

    def set_step(self, step):
        self.current_step = step
        return step

    def log(self, state, logs, cls, src=None, yml=None):

        for level, msg in logs:
            if level == logging.WARNING:
                self.warnings += 1
            elif level >= logging.ERROR:
                self.errors += 1

        if state == JobMonitor.STATUS_DONE:
            return

        job = {}
        job['logs'] = logs
        job['type'] = cls
        job['src'] = src
        job['yml'] = yml

        if state == JobMonitor.STATUS_CANCEL:
            self.jobs_canceled.append(job)
        else:
            self.jobs_failed.append(job)

    @property
    def current_command(self):
        return self.current_task

    @property
    def has_failed(self):
        if self.current_step and self.current_step != BuildMonitor.STEP_FINISHED:
            return True
        if self.errors or self.warnings:
            return True
        return False

    def count(self):
        w = '{} warning{}'.format(self.warnings, 's' if self.warnings > 1 else '')
        e = '{} error{}'.format(self.errors, 's' if self.errors > 1 else '')

        if not self.errors:
            return w
        if not self.warnings:
            return e
        return w + ' and ' + e

    def report(self):
        if self.errors or self.warnings:
            log.warning(u'> job completed with {} 😢'.format(self.count()))

        if self.jobs_canceled:
            n = len(self.jobs_canceled)
            log.warning(u'> {} canceled command{}'.format(n, 's' if n > 1 else ''))
        if self.jobs_failed:
            n = len(self.jobs_failed)
            log.warning(u'> {} failed command{}'.format(n, 's' if n > 1 else ''))
