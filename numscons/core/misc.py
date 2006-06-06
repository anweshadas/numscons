"""Misc utilities which did not find they way elsewhere."""

import sys
import os
import re

from os.path import join as pjoin, dirname as pdirname, \
                    basename as pbasename, splitext

import numscons

def get_scons_path():
    """Returns the name of the directory where our local scons is."""
    return pjoin(pdirname(numscons.__file__), 'scons-local')

def get_scons_build_dir():
    """Return the top path where everything produced by scons will be put.
    
    The path is relative to the top setup.py"""
    return pjoin('build', 'scons')

def get_scons_configres_dir():
    """Return the top path where everything produced by scons will be put.
    
    The path is relative to the top setup.py"""
    return pjoin('build', 'scons-configres')

def get_scons_configres_filename():
    """Return the top path where everything produced by scons will be put.
    
    The path is relative to the top setup.py"""
    return '__configres.py'

# Those built_* are not good: we should have a better way to get the real type
# of compiler instead of being based on names (to support things like colorgcc,
# gcc-4.2, etc...). Fortunately, we mostly need this on MS platform only.
def built_with_mstools(env):
    """Return True if built with MS tools (compiler + linker)."""
    return env['cc_opt'] == 'msvc'

def built_with_mingw(env):
    """Return true if built with mingw compiler."""
    return env['cc_opt'] == 'mingw' or \
	   (sys.platform == 'win32' 
	    and (env['f77_opt'] == 'g77' or
		 env['f77_opt'] == 'gfortran'))  

def built_with_gnu_f77(env):
    """Return true if f77 compiler is gnu (g77, gfortran, etc...)."""
    return env['f77_opt'] == 'g77' or env['f77_opt'] == 'gfortran'

def get_pythonlib_name(debug = 0):
    """Return the name of python library (necessary to link on NT with
    mingw."""
    # Yeah, distutils burried the link option on NT deep down in
    # Extension module, we cannot reuse it !
    if debug == 1:
        template = 'python%d%d_d'
    else:
        template = 'python%d%d'

    return template % (sys.hexversion >> 24, 
		       (sys.hexversion >> 16) & 0xff)

def pyplat2sconsplat():
    """Returns the scons platform."""
    # XXX: should see how env['PLATFORM'] is defined, make this a dictionary 
    if sys.platform[:5] == 'linux':
        return 'posix'
    elif sys.platform[:5] == 'sunos':
        return 'sunos'
    else:
        return sys.platform

def is_cc_suncc(fullpath):
    """Return true if the compiler is suncc."""
    # I wish there was a better way: we launch suncc -V, read the output, and
    # returns true if Sun is found in the output. We cannot check the status
    # code, because the compiler does not seem to have a way to do nothing
    # while returning success (0).
    
    suncc = re.compile('Sun C')
    # Redirect stderr to stdout
    cmd = fullpath + ' -V 2>&1'
    out = os.popen(cmd)
    cnt = out.read()
    #st = out.close()
    out.close()

    return suncc.search(cnt)

def get_local_toolpaths():
    """Returns the full pathname for the numscons tools directory."""
    return [pdirname(numscons.tools.__file__)]

def get_custom_toolpaths(env):
    """Returns the list of user-customized pathnames for scons tools."""
    return env['scons_tool_path'].split(os.pathsep)

def get_additional_toolpaths(env):
    """Returns the full list of pathnames where to look for scons tools."""
    toolp = []
    # Put custom toolpath FIRST !
    toolp.extend(get_custom_toolpaths(env))
    toolp.extend(get_local_toolpaths())
    return toolp

def is_f77_gnu(env):
    """Returns true if F77 in env is a Gnu fortran 
    compiler."""
    # XXX: do this properly
    if env.has_key('F77'):
        fullpath = env['F77']
        return pbasename(fullpath) == 'g77' or pbasename(fullpath) == 'gfortran'
    else:
        return False

def get_vs_version(env):
    """Returns the visual studio version."""
    try:
        version = env['MSVS']['VERSION']
        m = re.compile("([0-9]).([0-9])").match(version)
        if m:
            major = int(m.group(1))
            minor = int(m.group(2))
            return (major, minor)
        else:
            raise RuntimeError("FIXME: failed to parse VS version")
    except KeyError:
        raise RuntimeError("Could not get VS version !")

def isfortran(env, source):
    """Return 1 if any of code in source has fortran files in it, 0
    otherwise."""
    try:
        fsuffixes = env['FORTRANSUFFIXES']
    except KeyError:
        # If no FORTRANSUFFIXES, no fortran tool, so there is no need to look
        # for fortran sources.
        return 0

    if not source:
        # Source might be None for unusual cases like SConf.
        return 0
    for s in source:
        if s.sources:
            ext = os.path.splitext(str(s.sources[0]))[1]
            if ext in fsuffixes:
                return 1
    return 0

def isf2py(env, source):
    """Return 1 if any of code in source has f2py interface files in it, 0
    otherwise."""
    fsuffixes = ['.pyf']

    if not source:
        # Source might be None for unusual cases like SConf.
        return 0
    for s in source:
        if s.sources:
            ext = os.path.splitext(str(s.sources[0]))[1]
            if ext in fsuffixes:
                return 1
    return 0
