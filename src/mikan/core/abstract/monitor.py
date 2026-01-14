# coding: utf-8

"""Abstract Monitor Module.

This module provides monitoring classes for tracking job execution and build progress
in the Mikan framework. It enables status tracking, error logging, and build reporting
during rig construction.

The module supports:
    - Job execution status tracking with multiple status codes
    - Warning and error logging with insertion control
    - Build progress monitoring across multiple steps
    - Build report generation with summary statistics

Classes:
    JobMonitor: Base class for tracking individual job execution status.
    BuildMonitor: Class for monitoring overall build progress and aggregating results.

Examples:
    Using JobMonitor for status tracking:
        >>> class MyJob(JobMonitor):
        ...     def execute(self):
        ...         self.clear_logs()
        ...         # ... do work ...
        ...         return JobMonitor.STATUS_DONE

    Using BuildMonitor for build tracking:
        >>> monitor = BuildMonitor()
        >>> monitor.set_step(BuildMonitor.STEP_TEMPLATES)
        >>> # ... build templates ...
        >>> monitor.report()
"""

__all__ = ['JobMonitor', 'BuildMonitor']

import logging

from mikan.core.logger import create_logger

log = create_logger()


class JobMonitor(object):
    """Base class for tracking individual job execution status.

    Provides status codes, logging capabilities, and summary reporting for
    jobs such as modifiers or deformers during rig building.

    Attributes:
        STATUS_CANCEL (int): Job was canceled (-1).
        STATUS_DONE (int): Job completed successfully (0).
        STATUS_DELAY (int): Job delayed due to unresolved dependencies (1).
        STATUS_INVALID (int): Job has invalid arguments (2).
        STATUS_ERROR (int): Job encountered an expected error (3).
        STATUS_CRASH (int): Job encountered an unexpected exception (4).
        logs (list): List of (level, message) tuples for logged events.
        unresolved (list): List of unresolved node or connection identifiers.

    Examples:
        Subclassing for a custom job:
            >>> class MyModifier(JobMonitor):
            ...     def execute(self):
            ...         self.clear_logs()
            ...         try:
            ...             # ... perform operation ...
            ...             return JobMonitor.STATUS_DONE
            ...         except Exception as e:
            ...             self.log_error(str(e))
            ...             return JobMonitor.STATUS_ERROR

        Checking execution results:
            >>> if job.count_errors() > 0:
            ...     print('Job failed with errors')
    """

    STATUS_CANCEL = -1
    STATUS_DONE = 0
    STATUS_DELAY = 1
    STATUS_INVALID = 2
    STATUS_ERROR = 3
    STATUS_CRASH = 4

    def __init__(self):
        """Initialize a JobMonitor instance."""
        self.logs = []
        self.unresolved = []

    def clear_logs(self):
        """Clear all logs and unresolved references."""
        del self.logs[:]
        del self.unresolved[:]

    def log(self, level, msg, insert=-1):
        """Add a log entry at the specified level.

        Args:
            level (int): Logging level (logging.WARNING, logging.ERROR, etc.).
            msg (str): Message to log.
            insert (int): Position to insert the log entry. Negative values
                count from the end. Defaults to -1 (append).

        Note:
            Warning and error messages are automatically prefixed with '/!\\'
            unless they start with '--'.
        """
        if insert < 0:
            insert = len(self.logs) + insert + 1
        if level in (logging.WARNING, logging.ERROR):
            if not msg.startswith('--'):
                msg = '/!\\ ' + msg
        self.logs.insert(insert, (level, msg))

    def log_warning(self, msg, insert=-1):
        """Add a warning log entry.

        Args:
            msg (str): Warning message to log.
            insert (int): Position to insert. Defaults to -1 (append).
        """
        self.log(logging.WARNING, msg, insert)

    def log_error(self, msg, insert=-1):
        """Add an error log entry.

        Args:
            msg (str): Error message to log.
            insert (int): Position to insert. Defaults to -1 (append).
        """
        self.log(logging.ERROR, msg, insert)

    def log_summary(self):
        """Output all logged messages to the logger.

        Logs unresolved IDs as a warning if any exist, then outputs
        all accumulated log entries at their respective levels.
        """
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
        """Count the number of warnings.

        Returns:
            int: Total warning count, including one for unresolved IDs if any.
        """
        n = 0
        for lvl, msg in self.logs:
            if lvl == logging.WARNING:
                n += 1
        if self.unresolved:
            n += 1
        return n

    def count_errors(self):
        """Count the number of errors.

        Returns:
            int: Total count of ERROR and CRITICAL level logs.
        """
        n = 0
        for lvl, msg in self.logs:
            if lvl >= logging.ERROR:
                n += 1
        return n

    def count_summary(self):
        """Get a summary string of warnings and errors.

        Returns:
            str: Summary like "2 warnings, 1 error" or empty string if none.

        Examples:
            >>> job.count_summary()
            '2 warnings, 1 error'
        """
        msg = []
        n = self.count_warnings()
        if n:
            msg.append('{} warning{}'.format(n, 's' if n > 1 else ''))
        n = self.count_errors()
        if n:
            msg.append('{} error{}'.format(n, 's' if n > 1 else ''))
        return ', '.join(msg)


class BuildMonitor(object):
    """Class for monitoring overall build progress and aggregating results.

    Tracks the current build step, accumulates warnings and errors from
    individual jobs, and provides reporting functionality.

    Attributes:
        STEP_INIT_TEMPLATE (str): Step for parsing templates.
        STEP_CLEANUP_RIG (str): Step for deleting existing rig.
        STEP_TEMPLATES (str): Step for building templates.
        STEP_SCHEDULER (str): Step for running the scheduler.
        STEP_MODS_DEFORMERS (str): Step for applying modifiers and deformers.
        STEP_GROUPS (str): Step for organizing groups.
        STEP_CLEANUP (str): Step for final cleanup.
        STEP_FINISHED (str): Step indicating build completion.
        scheduler: Reference to the build scheduler.
        current_step (str): Currently executing build step.
        current_task: Currently executing task within the step.
        current_yaml: Current YAML source being processed.
        warnings (int): Total warning count across all jobs.
        errors (int): Total error count across all jobs.
        jobs_canceled (list): List of canceled job records.
        jobs_failed (list): List of failed job records.

    Examples:
        Monitoring a build process:
            >>> monitor = BuildMonitor()
            >>> monitor.set_step(BuildMonitor.STEP_TEMPLATES)
            >>> # ... execute jobs ...
            >>> monitor.log(status, job.logs, 'Mod', src='arm.yml')
            >>> monitor.set_step(BuildMonitor.STEP_FINISHED)
            >>> monitor.report()
    """

    STEP_INIT_TEMPLATE = 'parse template'
    STEP_CLEANUP_RIG = 'delete rig'
    STEP_TEMPLATES = 'build templates'
    STEP_SCHEDULER = 'scheduler'
    STEP_MODS_DEFORMERS = 'mods/deformers'
    STEP_GROUPS = 'groups'
    STEP_CLEANUP = 'cleanup'
    STEP_FINISHED = 'build complete'

    def __init__(self):
        """Initialize a BuildMonitor instance."""
        self.scheduler = None
        self.current_step = None
        self.current_task = None
        self.current_yaml = None

        self.warnings = 0
        self.errors = 0

        self.jobs_canceled = []
        self.jobs_failed = []

    def set_step(self, step):
        """Set the current build step.

        Args:
            step (str): Step identifier (use STEP_* constants).

        Returns:
            str: The step that was set.
        """
        self.current_step = step
        return step

    def log(self, state, logs, cls, src=None, yml=None):
        """Log a job result and accumulate statistics.

        Counts warnings and errors from the job's logs. If the job
        did not complete successfully, records it in the appropriate list.

        Args:
            state (int): Job status code (JobMonitor.STATUS_*).
            logs (list): List of (level, message) tuples from the job.
            cls (str): Class or type name of the job.
            src (str, optional): Source file or identifier.
            yml (str, optional): YAML content or reference.
        """
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
        """Get the current task being executed.

        Returns:
            The current task reference.
        """
        return self.current_task

    @property
    def has_failed(self):
        """Check if the build has failed or has issues.

        Returns:
            bool: True if build did not complete or has warnings/errors.
        """
        if self.current_step and self.current_step != BuildMonitor.STEP_FINISHED:
            return True
        if self.errors or self.warnings:
            return True
        return False

    def count(self):
        """Get a formatted string of warning and error counts.

        Returns:
            str: Formatted count like "2 warnings and 1 error".
        """
        w = '{} warning{}'.format(self.warnings, 's' if self.warnings > 1 else '')
        e = '{} error{}'.format(self.errors, 's' if self.errors > 1 else '')

        if not self.errors:
            return w
        if not self.warnings:
            return e
        return w + ' and ' + e

    def report(self):
        """Output a summary report of the build results.

        Logs warnings about total errors/warnings and lists
        counts of canceled and failed jobs.
        """
        if self.errors or self.warnings:
            log.warning(u'> job completed with {} 😢'.format(self.count()))

        if self.jobs_canceled:
            n = len(self.jobs_canceled)
            log.warning(u'> {} canceled command{}'.format(n, 's' if n > 1 else ''))
        if self.jobs_failed:
            n = len(self.jobs_failed)
            log.warning(u'> {} failed command{}'.format(n, 's' if n > 1 else ''))
