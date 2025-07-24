# coding: utf-8

import meta_nodal_py as kl

from mikan.core.logger import get_version, create_logger

from .lib import *
from .core import *

# log version
version = get_version()
if version:
    log = create_logger()
    log.info(f'{version} loaded')
