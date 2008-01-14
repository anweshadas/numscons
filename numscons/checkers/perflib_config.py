#! /usr/bin/env python
# Last Change: Sat Jan 12 07:00 PM 2008 J
"""This module contains the infrastructure to get all the necessary options for
perflib checkers."""

from os.path import join as pjoin, dirname as pdirname
from ConfigParser import SafeConfigParser, RawConfigParser
from copy import copy

from numscons.numdist import default_lib_dirs

from numscons.core.utils import DefaultDict
from configuration import available_build_opts_flags,\
                          available_build_opts_factory_flags, \
                          BuildOptsFactory, BuildOpts

_PERFLIBS = ('GenericBlas', 'GenericLapack', 'MKL', 'ATLAS', 'Accelerate',
             'vecLib', 'Sunperf', 'FFTW2', 'FFTW3')

#------------------------
# Generic functionalities
#------------------------
class PerflibConfig:
    """A class which contain all the information for a given performance
    library, including build options (cflags, libs, path, etc....) and meta
    information (name, version, how to check)."""
    def __init__(self, dispname, sitename, values):
        """Initialize the configuration."""
        self.name = dispname
        self.section = sitename

        self.values = values
        self.headers = values['htc']
        self.funcs = values['ftc']
        #self.version_checker = version_checker

        self.defopts = BuildOpts()
        for opt in available_build_opts_flags():
            self.defopts[opt] = values[opt]

    def __str__(self):
        return self.__repr__()

    def __repr__(self):
        repr = ["Display name: %s" % self.name]
        repr += ["Section name: %s" % self.section]
        repr += ["Headers to check : %s" % self.headers]
        repr += ["Funcs to check : %s" % self.funcs]
        return '\n'.join(repr)

    def get_def_opts(self):
        return self.defopts

    def get_def_opts_copy(self):
        return copy(self.defopts)

#-------------------------------------------
# Perflib specific configuration and helpers
#-------------------------------------------
def build_config():
    # list_opts contain a list of all available options available in
    # perflib.cfg which can be a list.
    list_opts = available_build_opts_factory_flags()

    # str_opts contain a list of all available options available in perflib.cfg
    # which are strings and cannot be list.
    str_opts = ('dispname', 'sitename')

    #defint = {'atlas_def_libs' : 
    #          ','.join([pjoin(i, 'atlas') for i in default_lib_dirs])}

    cfg = SafeConfigParser()

    st = cfg.read(pjoin(pdirname(__file__), 'perflib.cfg'))
    # XXX: check this properly
    assert len(st) > 0

    def get_perflib_config(name):
        yop = DefaultDict.fromcallable(list_opts, lambda: [])
        opts = cfg.options(name)

        # Get mandatory options first
        def get_opt(opt):
            opts.pop(opts.index(opt))
            o = cfg.get(name, opt)
            return o
        dispname = get_opt('dispname')
        sitename = get_opt('sitename')

        # Now get all optional options 
        for i in opts:
            #yop[i] =  cfg.get(name, i, vars = defint)
            yop[i] =  cfg.get(name, i).split(',')

        return PerflibConfig(dispname, sitename, yop)

    ret = {}
    for i in _PERFLIBS:
        ret[i] = get_perflib_config(i)

    return ret
        
# A dictionary which keys are the name of the perflib (same than perflib.cfg
# section name) and values a PerflibConfig instance.
CONFIG = build_config()

class IsFactory:
    def __init__(self, name):
        """Name should be one key of CONFIG."""
        try:
            CONFIG[name]
        except KeyError, e:
            raise RuntimeError("name %s is unknown")

        def f(env, libname):
            if env['NUMPY_PKG_CONFIG'][libname] is None:
                return 0 == 1
            else:
                return env['NUMPY_PKG_CONFIG'][libname].name == \
                       CONFIG[name].name
        self.func = f

    def get_func(self):
        return self.func

class GetVersionFactory:
    def __init__(self, name):
        """Name should be one key of CONFIG."""
        try:
            CONFIG[name]
        except KeyError, e:
            raise RuntimeError("name %s is unknown")

        def f(env, libname):
            if env['NUMPY_PKG_CONFIG'][libname] is None or \
               not env['NUMPY_PKG_CONFIG'][libname].name == CONFIG[name].name:
                return 'No version info'
            else:
                return env['NUMPY_PKG_CONFIG'][libname].version
        self.func = f

    def get_func(self):
        return self.func

if __name__ == '__main__':
    for k, v in CONFIG.items():
        print "++++++++++++++++++"
        print k
        print v
