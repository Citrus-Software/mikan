# coding: utf-8

import os
import mikan
import subprocess

from mikan.core.prefs import UserPrefs


# get tangerine path
path_exe = UserPrefs.get('tangerine_path')
path_exe = os.path.abspath(path_exe)
if not os.path.exists(path_exe):
    raise RuntimeError('invalid path: {}'.format(path_exe))

path_cwd = os.path.split(path_exe)[0]

mikan_src = os.path.abspath(mikan.__path__[0])
mikan_src = os.path.split(mikan_src)[0]

hook = os.path.sep.join([mikan_src, 'mikan', 'tangerine', 'utils', 'hook.py'])

subprocess.Popen([path_exe, hook, mikan_src], cwd=path_cwd)
