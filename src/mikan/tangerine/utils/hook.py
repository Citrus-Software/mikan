# coding: utf-8

import os
import sys
import traceback

path = sys.argv[2]
if path not in sys.path:
    sys.path.append(path)

os.environ["MIKAN_MENU"] = "on"

try:
    # noinspection PyUnresolvedReferences
    import mikan.tangerine.ui.asset
except ImportError:
    print(traceback.format_exc())
