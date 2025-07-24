# coding: utf-8

import sys
import traceback

from .utils import *
from .logger import create_logger, timed_code

log = create_logger()

# python 3 check
is_python_3 = (sys.version_info[0] == 3)

# maya loader
if 'maya' in sys.executable or 'Maya' in sys.executable:
    try:
        import maya.cmds as mc
        from ..maya import *
    except ImportError:
        log.info(traceback.format_exc())

# tang loader
else:
    try:
        import meta_nodal_py as kl
        from ..tangerine import *
    except ImportError:
        log.info(traceback.format_exc())
