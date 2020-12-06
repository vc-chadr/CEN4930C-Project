"""
Utility functions

"""

from math import trunc
import inspect
import os
import sys
import time


class Nutil():

    def get_time_delta(time_last):
        delta = abs(trunc(time.time() - int(time_last)))

        if delta < 60:
            delta = '{}s'.format(delta)
        elif delta < 3600:
            delta = '{:.1f}m'.format(delta / 60)
        elif delta < 86400:
            delta = '{:.1f}h'.format(delta / 3600)
        else:
            delta = '{:.1f}d'.format(delta / 86400)

        return delta


    def get_script_dir(follow_symlinks=True):
        if getattr(sys, 'frozen', False): # py2exe, PyInstaller, cx_Freeze
            path = os.path.abspath(sys.executable)
        else:
            path = inspect.getabsfile(Nutil.get_script_dir)
        if follow_symlinks:
            path = os.path.realpath(path)

        return os.path.dirname(path)