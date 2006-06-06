#! /usr/bin/env python
# Last Change: Tue Oct 09 03:00 PM 2007 J

"""Module to support building python extension. KEEP THIS INDEPENDANT OF SCONS
!"""

import sys
import os
from os.path import join as pjoin

from distutils.sysconfig import get_python_version, get_python_inc

def get_pythonlib_dir():
    """Returns a list of path to look for the python engine library
    (pythonX.X.lib on win32, libpythonX.X.so on unix, etc...)."""
    if os.name == 'nt':
        return [pjoin(sys.exec_prefix, 'libs')]
    else:
        return [pjoin(sys.exec_prefix, 'lib')]

if __name__ == '__main__':
    print "Python version is %s" % get_python_version()
    print "Python include dir is %s" % get_python_inc()