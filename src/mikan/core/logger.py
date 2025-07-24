# coding: utf-8

import time
import os.path
import logging
import platform
from six import string_types
from contextlib import contextmanager
from timeit import default_timer

from mikan import __version__

is_maya = False
try:
    import maya.utils

    is_maya = True
except:
    pass

LOGGER_NAME = 'mikan'

__all__ = [
    'create_logger', 'SafeHandler', 'get_formatter',
    'timed_code', 'set_time_logging', 'get_date_str',
    'get_version',
    'MultiTimer'
]

logging.SUCCESS = 25  # between WARNING and INFO
logging.addLevelName(logging.SUCCESS, 'SUCCESS')


class SafeHandler(logging.Handler):
    pass


class SafeFileHandler(logging.FileHandler, SafeHandler):
    pass


if is_maya:

    class MayaGuiLogHandler(logging.Handler):
        """
        A python logging handler that displays error and warning
        records with the appropriate color labels within the Maya GUI
        """

        def __init__(self):
            super(MayaGuiLogHandler, self).__init__()
            from maya.OpenMaya import MGlobal
            self.MGlobal = MGlobal

        def emit(self, record):
            msg = self.format(record)
            if record.levelno > logging.WARNING:
                # Error (40) Critical (50)
                self.MGlobal.displayError(msg)
            elif record.levelno > logging.SUCCESS:
                # Warning (30)
                self.MGlobal.displayWarning(msg)
            else:
                # Debug (10) and Info (20)
                self.MGlobal.displayInfo(msg)


    class BaseHandler(MayaGuiLogHandler, SafeHandler):
        pass
else:
    class BaseHandler(logging.StreamHandler, SafeHandler):
        pass


def get_formatter(name=True):
    msg = '%(message)s'
    if name:
        s = '[%(name)s] %(levelname)8s| ' + msg
    else:
        s = '%(levelname)-8s| ' + msg

    return logging.Formatter(s)


def create_logger(name='', level=None, save=False):
    if not name:
        name = LOGGER_NAME

    set_level = False
    if name not in logging.root.manager.loggerDict or level is not None:
        set_level = True

    logger = logging.getLogger(name)

    if set_level:
        if level is None:
            level = 'INFO'
        logger.setLevel(level.upper() if isinstance(level, str) else level)

    logger.propagate = False

    # add a success level
    setattr(logger, 'success', lambda message, *args: logger._log(logging.SUCCESS, message, args))

    # cleanup handlers
    logger.handlers = [handler for handler in logger.handlers if isinstance(handler, SafeHandler)]

    # create base handler
    add_handler = True
    for handler in logger.handlers:
        if isinstance(handler, BaseHandler):
            add_handler = False
            break

    if add_handler:
        handler = BaseHandler()

        handler.setFormatter(get_formatter())
        logger.addHandler(handler)

    # save to file
    if save:
        log_file_path = r"%tmp%\{}.log".format(name)
        if isinstance(save, string_types):
            log_file_path = save
        log_file_path = os.path.expandvars(log_file_path)
        log_file_path = os.path.realpath(log_file_path)

        # crate log file
        fh = SafeFileHandler(log_file_path, encoding=None, delay=False)

        if set_level:
            if level is None:
                level = 'INFO'
            fh.setLevel(level.upper() if isinstance(level, str) else level)

        fh.setFormatter(get_formatter())
        logger.addHandler(fh)

    # exit
    return logger


# hack StreamHandler to emit color ---------------------------------------------

def add_coloring_to_emit_windows(fn):
    # add methods we need to the class
    def _out_handle(self):
        import ctypes
        return ctypes.windll.kernel32.GetStdHandle(self.STD_OUTPUT_HANDLE)

    out_handle = property(_out_handle)

    def _set_color(self, code):
        import ctypes
        # Constants from the Windows API
        self.STD_OUTPUT_HANDLE = -11
        hdl = ctypes.windll.kernel32.GetStdHandle(self.STD_OUTPUT_HANDLE)
        ctypes.windll.kernel32.SetConsoleTextAttribute(hdl, code)

    setattr(logging.StreamHandler, '_set_color', _set_color)

    def new(*args):
        std_input_handle = -10
        std_output_handle = -11
        std_error_handle = -12

        foreground_black = 0x0000
        foreground_blue = 0x0001
        foreground_green = 0x0002
        foreground_cyan = 0x0003
        foreground_red = 0x0004
        foreground_magenta = 0x0005
        foreground_yellow = 0x0006
        foreground_white = 0x0007
        foreground_intensity = 0x0008  # foreground color is intensified.

        background_black = 0x0000
        background_blue = 0x0010
        background_green = 0x0020
        background_cyan = 0x0030
        background_red = 0x0040
        background_magenta = 0x0050
        background_yellow = 0x0060
        background_white = 0x0070
        background_intensity = 0x0080  # background color is intensified.

        levelno = args[1].levelno
        if levelno >= 50:
            color = foreground_red | foreground_intensity
        elif levelno >= 40:
            color = foreground_red
        elif levelno >= 30:
            color = foreground_yellow
        elif levelno >= 25:
            color = foreground_green
        elif levelno >= 20:
            color = foreground_blue | foreground_intensity
        elif levelno >= 10:
            color = foreground_black | foreground_intensity
        else:
            color = foreground_white
        args[0]._set_color(color)

        ret = fn(*args)
        args[0]._set_color(foreground_white)
        return ret

    return new


def add_coloring_to_emit_ansi(fn):
    # add methods we need to the class
    def new(*args):
        levelno = args[1].levelno
        if levelno >= 50:
            color = '\x1b[31;1m'  # bold red
        elif levelno >= 40:
            color = '\x1b[31m'  # red
        elif levelno >= 30:
            color = '\x1b[33m'  # yellow
        elif levelno >= 25:
            color = '\x1b[32m'  # green
        elif levelno >= 20:
            color = '\x1b[34m'  # blue
        elif levelno >= 10:
            color = '\x1b[3m'  # italic
        else:
            color = '\x1b[0m'  # normal
        args[1].msg = color + str(args[1].msg) + '\x1b[0m'  # normal
        return fn(*args)

    return new


if not hasattr(logging.StreamHandler, '_custom_emit_applied'):
    if platform.system() == 'Windows':
        # Windows does not support ANSI escapes and we are using API calls to set the console color
        logging.StreamHandler.emit = add_coloring_to_emit_windows(logging.StreamHandler.emit)
    # else:
    #     # all non-Windows platforms are supporting ANSI escapes so we use them
    #     logging.StreamHandler.emit = add_coloring_to_emit_ansi(logging.StreamHandler.emit)

logging.StreamHandler._custom_emit_applied = True

log = create_logger()
debug_timings = False


def time_to_str(t):
    next_unit = iter(('s', 'ms', u'µs', 'ns'))

    unit = next(next_unit)
    while t < 1:
        t *= 1000.0
        try:
            unit = next(next_unit)
        except StopIteration:
            break

    return u'{:.2f}{}'.format(t, unit)


@contextmanager
def timed_code(name=None, level='INFO', force=False):
    level = getattr(logging, level.upper())

    msg = '{} took'.format(name) if name else 'section took'
    t0 = default_timer()
    try:
        yield
    finally:
        if debug_timings or force:
            delta = default_timer() - t0
            log.log(level, u'{}: {}'.format(msg, time_to_str(delta)))


def set_time_logging(state):
    global debug_timings
    debug_timings = bool(state)


def get_date_str():
    Gtime = time.gmtime()
    hour_offset = 2
    return time.strftime(" %a, %d %b %Y {}:%M:%S ".format(Gtime.tm_hour + hour_offset), Gtime)


def get_version():
    version = __version__
    if is_git_repo():
        version += '-dev'

    return version


def is_git_repo(start_path=None):
    if start_path is None:
        start_path = os.path.abspath(__file__)

    current_dir = os.path.dirname(start_path)

    while True:
        if os.path.isdir(os.path.join(current_dir, '.git')):
            return True

        parent_dir = os.path.dirname(current_dir)
        if parent_dir == current_dir:
            break

        current_dir = parent_dir

    return False


class MultiTimer(object):
    timings = dict()

    @classmethod
    @contextmanager
    def timer(cls, name):
        if name not in cls.timings:
            cls.timings[name] = [0., 0.]

        start = default_timer()
        try:
            yield
        finally:
            duration = default_timer() - start
            cls.timings[name][0] += duration
            cls.timings[name][1] += 1

    @classmethod
    def report(cls):
        if not cls.timings:
            return

        log.info('timing report:')

        for k in cls.timings:
            d = cls.timings[k][0]
            t = time_to_str(d)
            n = cls.timings[k][1]
            nt = time_to_str(d / n)

            log.info(u'- {} took {}, {} times, took {} on average'.format(k, t, n, nt))

    @classmethod
    def reset(cls):
        cls.timings.clear()
