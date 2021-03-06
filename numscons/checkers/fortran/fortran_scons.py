# Last Change: Sun Jul 06 03:00 PM 2008 J
import os
import sys
import string

from os.path import basename, join as pjoin, dirname
from copy import deepcopy

from numscons.core.utils import popen_wrapper
from numscons.core.misc import built_with_mstools, built_with_mingw, \
                   built_with_gnu_f77, built_with_ifort
from fortran import parse_f77link, check_link_verbose, gnu_to_scons_flags

__all__ = ['CheckF77Clib', 'CheckF77Mangling']

#-----------------
# Public functions
#-----------------

# Getting verbose flag
def _CheckFVerbose(context, fcomp):
    flags = ['-v', '--verbose', '-verbose', '-V']
    for flag in flags:
        if _check_f_vflag(context, flag, fcomp):
            return 1, flag

    return 0, ''

def CheckF77Verbose(context):
    context.Message('Checking F77 %s verbose flag ... ' % context.env['F77'] )

    res, flag = _CheckFVerbose(context, 'F77')
    if res:
        context.Result(flag)
        context.env['F77LINK_VFLAG'] = flag
    else:
        context.Result('Failed !')

    return res

def CheckF90Verbose(context):
    context.Message('Checking F90 %s verbose flag ... ' % context.env['F90'] )

    res, flag = _CheckFVerbose(context, 'F90')
    if res:
        context.Result(flag)
        context.env['F90LINK_VFLAG'] = flag
    else:
        context.Result('Failed !')

    return res

# Checking whether the fortran compiler can compile and link a dummy program
def _CheckFDryRun(context, fc = 'F77'):
    """Check whether the compiler fc can compile a program."""
    env = context.env
    try:
        fcomp = env[fc]
    except KeyError:
        raise RuntimeError("Compiler type %s not known !" % fc)

    context.Message('Checking if %s compiler %s can create executables - ' % (fc, fcomp))
    # We use our own builder as long as I don't resolve the issue of TryLink
    # returning 1 when it fails.
    result = _build_empty_program(context, fc)[0]
    context.Result((result and 'yes' or 'no'))
    return result

def CheckF77DryRun(context):
    """Check whether the F77 compiler can compile a program."""
    return _CheckFDryRun(context, 'F77')

def CheckF90DryRun(context):
    """Check whether the F90 compiler can compile a program."""
    return _CheckFDryRun(context, 'F90')

# Getting fortran support runtime
def CheckF77Clib(context, autoadd = 1):
    """This tries to get Fortran runtime facilities necessary at link stage,
    and put the relevant flags in env['F77_LDFLAGS']."""
    import SCons
    fcompiler = 'F77'

    if not context.env.has_key(fcompiler):
        raise Exception("F77 should be set before calling CheckF77Clib !")

    fflags = 'LINKFLAGS'
    env = context.env
    config = context.sconf
    context.Message('Checking %s C compatibility runtime ...' % env[fcompiler])

    if built_with_mstools(env):
        if built_with_gnu_f77(env):
            from fortran import get_g2c_libs
            rtdir, msrtlibs = get_g2c_libs(env, final_flags)
            # XXX: this is ugly, we interpolate by hand.
            libdirflags = ["/LIBPATH:%s" % os.path.join(env['build_dir'], rtdir)]
            libflags    = ["%s" % l for l in msrtlibs]
            env["F77_LDFLAGS"] = libdirflags + libflags
            context.Result(' '.join(env['F77_LDFLAGS']))
        else:
            env["F77_LDFLAGS"] = SCons.Util.CLVar('')
            context.Result('None needed')
        res = 1
    else:
        # XXX: check how to get verbose output
        verbose = ['-v']

        # Convention old* variables MUST be restored in ANY CONDITION.
        oldLINKFLAGS = env.has_key(fflags) and deepcopy(env[fflags]) or []

        try:
            context.env.Append(LINKFLAGS = verbose)
            res, cnt = _build_empty_program(context, fcompiler)
        finally:
            env.Replace(LINKFLAGS = oldLINKFLAGS)

        if res == 1:
            final_flags = parse_f77link(cnt)
            env['F77_LDFLAGS'] = final_flags
            context.Result(' '.join(env['F77_LDFLAGS']))
        else:
            context.Result('Failed !')

    if autoadd:
        env.AppendUnique(LINKFLAGSEND =  env['F77_LDFLAGS'])
    return res

# If need a dummy main
def _CheckFDummyMain(context, fcomp):
    # Check whether the Fortran runtime needs a dummy main.
    if not context.env.has_key(fcomp):
        context.Message('Checking dummy main: no %s compiler defined: cannot check dummy main ' % fcomp)
        return 0, None
    else:
        context.Message('Checking if %s needs dummy main - ' % context.env[fcomp])

    env = context.env
    if not built_with_mstools(context.env):
        savedLINK = env.has_key('LINK') and deepcopy(env['LINK']) or []
        try:
            env['LINK'] = env[fcomp]
            res, m =_dummy_main_imp(context)
        finally:
            env.Replace(LINK = savedLINK)
    else:
        # Using MS tools (Visual studio) with fortran compiler

        # XXX: this has to be dirty... As scons is using visual studio, it uses
        # the related convention (prefix names for libraries, etc...).  Here,
        # we want to compile object code with cl.exe, but link with the fortran
        # compiler which may be totally different than cl.exe (think gnu
        # fortran compiler). So we have to bypass scons commands, and use our
        # own: since this is only used for configuration, it should not matter
        # much.
        savedLINKCOM = env.has_key('LINKCOM') and deepcopy(env['LINKCOM']) or []
        try:
            env['LINKCOM'] = "$F77 -o $TARGET $SOURCES"
            res, m = _dummy_main_imp(context)
        finally:
            env.Replace(LINKCOM = savedLINKCOM)

    return res, m

def _dummy_main_imp(context):
    fcn_tmpl = """
int %s() { return 0; }
"""
    mains = ["MAIN__", "__MAIN", "_MAIN", "MAIN_"]
    mains.extend([string.lower(m) for m in mains])
    # Speed things up on windows, where main is used by gcc+g77 + ifort+msvc
    # combinations, which are the most likely ones
    if sys.platform == 'win32':
        mains.insert(0, "main")
    else:
        mains.append("main")
    mains.append("MAIN")
    mains.append("")
    for m in mains:
        prog = fcn_tmpl % "dummy"
        if m:
            prog = fcn_tmpl % m + prog
        result = context.TryLink(prog, '.c')
        if result:
            if not m:
                m = None
            break
    return result, m

# XXX: refactor those by using function templates
def CheckF77DummyMain(context):
    res, m = _CheckFDummyMain(context, 'F77')
    if res:
        context.Result("%s." % str(m))
        context.env['F77_DUMMY_MAIN'] = m
    else:
        context.Result("Failed !")

    return res

def CheckF90DummyMain(context):
    res, m = _CheckFDummyMain(context, 'F90')
    if res:
        context.Result("%s." % str(m))
        context.env['F90_DUMMY_MAIN'] = m
    else:
        context.Result("Failed !" % str(m))

    return res

# Fortran name mangling
def _CheckFMangling(context, fc, dummym, ext):
    # XXX: rewrite this in a more straightfoward manner, and support prepending
    # underscore
    env = context.env
    # TODO: if does not exist, call the function to get the F77_DUMMY_MAIN
    if not built_with_mstools(env):
        savedLINK = env.has_key('LINK') and deepcopy(env['LINK']) or []
        savedLIBS = env.has_key('LIBS') and deepcopy(env['LIBS']) or []
        try:
            env['LINK'] = env[fc]
            result, mangler, u, du, c = _check_f_mangling_imp(context, fc, dummym, ext)
        finally:
            env.Replace(LINK = savedLINK)
            env.Replace(LIBS = savedLIBS)
    else:
        # XXX: instead of recreating our own build commands, can we use the
        # ones from scons ? (defined in Tools directory)
        savedLINKCOM = env.has_key('LINKCOM') and deepcopy(env['LINKCOM']) or []
        savedLIBLINKPREFFIX = env.has_key('LIBLINKPREFFIX') and deepcopy(env['LIBLINKPREFFIX']) or []
        savedLIBLINKSUFFIX = env.has_key('LIBLINKSUFFIX') and deepcopy(env['LIBLINKSUFFIX']) or []
        savedLIBS = env.has_key('LIBS') and deepcopy(env['LIBS']) or []
        try:
            env['LINKCOM'] = '$%s -o $TARGET $SOURCES $_LIBFLAGS' % fc
            result, mangler, u, du, c = _check_f_mangling_imp(context, fc, dummym, ext)
        finally:
            env.Replace(LINKCOM = savedLINKCOM)
            env.Replace(LIBS = savedLIBS)
            env.Replace(LIBLINKPREFFIX = savedLIBLINKPREFFIX)
            env.Replace(LIBLINKSUFFIX = savedLIBLINKSUFFIX)

    return result, mangler, u, du, c

def _check_f_mangling_imp(context, fc, m, ext):
    env = context.env
    subr = """
      subroutine foobar()
      return
      end
      subroutine foo_bar()
      return
      end
"""
    main_tmpl = """
      int %s() { return 1; }
"""
    prog_tmpl = """
      void %s(void);
      void %s(void);
      int my_main() {
      %s();
      %s();
      return 0;
      }
"""
    # variants:
    #   lower-case, no underscore, no double underscore: foobar, foo_bar
    #   ...
    #   upper-case, underscore, double underscore: FOOBAR_, FOO_BAR__
    context.TryCompile(subr, ext)
    obj = context.lastTarget
    env.Append(LIBS = env.StaticLibrary(obj))

    # Optimize order of tested code depending on platforms to speed up
    # configure checks
    if sys.platform == 'win32':
        under = ['', '_']
        doubleunder = ['', '_']
        casefcn = ["upper", "lower"]
    else:
        under = ['_', '']
        doubleunder = ['', '_']
        casefcn = ["lower", "upper"]
    gen = _RecursiveGenerator(under, doubleunder, casefcn)
    while True:
        try:
            u, du, c = gen.next()
            def make_mangler(u, du, c):
                return lambda n: getattr(string, c)(n) +\
                                 u + (n.find('_') != -1 and du or '')
            mangler = make_mangler(u, du, c)
            foobar = mangler("foobar")
            foo_bar = mangler("foo_bar")
            prog = prog_tmpl % (foobar, foo_bar, foobar, foo_bar)
            if m:
                prog = main_tmpl % m + prog
            result = context.TryLink(prog, '.c')
            if result:
                break
        except StopIteration:
            result = mangler = u = du = c = None
            break

    return result, mangler, u, du, c

def _set_mangling_var(context, u, du, case, type = 'F77', autoadd=1, f2pycompat=1):
    env = context.env
    macros = []

    if du == '_':
        env['%s_UNDERSCORE_G77' % type] = 1
        macros.append('%s_UNDERSCORE_G77' % type)
        if f2pycompat:
            macros.append('UNDERSCORE_G77')
    else:
        env['%s_UNDERSCORE_G77' % type] = 0

    if u == '_':
        env['%s_NO_APPEND_FORTRAN' % type] = 0
    else:
        env['%s_NO_APPEND_FORTRAN' % type] = 1
        macros.append('%s_NO_APPEND_FORTRAN' % type)
        if f2pycompat:
            macros.append('NO_APPEND_FORTRAN')

    if case == 'upper':
        env['%s_UPPERCASE_FORTRAN' % type] = 1
        macros.append('%s_UPPERCASE_FORTRAN' % type)
        if f2pycompat:
            macros.append('UPPERCASE_FORTRAN')
    else:
        env['%s_UPPERCASE_FORTRAN' % type] = 0

    if autoadd:
        env.Append(CPPDEFINES=macros)

def CheckF77Mangling(context, autoadd=1, f2pycompat=1):
    """Find mangling of the F77 compiler.

    If sucessfull, env['F77_NAME_MANGLER'] is a function which given the C
    name, returns the F77 name as seen by the linker."""
    env = context.env
    if not env.has_key('F77_DUMMY_MAIN'):
        st = CheckF77DummyMain(context)
        if st == 0:
            return st
    context.Message('Checking %s name mangling - ' % env['F77'])
    res, mangler, u, du, c = _CheckFMangling(context, 'F77', env['F77_DUMMY_MAIN'], '.f')
    if res:
        context.Result("'%s', '%s', %s-case." % (u, du, c))
        env['F77_NAME_MANGLER'] = mangler
        _set_mangling_var(context, u, du, c, 'F77', autoadd, f2pycompat)
    else:
        context.Result("all variants failed.")
    return res

def CheckF90Mangling(context):
    env = context.env
    context.Message('Checking %s name mangling - ' % env['F90'])
    res, mangler, u, du, c = _CheckFMangling(context, 'F90', env['F90_DUMMY_MAIN'], '.f90')
    if res:
        context.Result("'%s', '%s', %s-case." % (u, du, c))
        env['F90_NAME_MANGLER'] = mangler
        _set_mangling_var(context, u, du, c, 'F90')
    else:
        context.Result("all variants failed.")
    return res

#------------------
# Support functions
#------------------
def _check_f_vflag(context, flag, fcomp):
    """Return True if flag is an acceptable verbose flag for fortran compiler
    fcomp."""

    oldLINKFLAGS = context.env['LINKFLAGS']
    res = 0
    try:
        context.env.Append(LINKFLAGS = flag)
        res, out = _build_empty_program(context, fcomp)
    finally:
        context.env['LINKFLAGS'] = oldLINKFLAGS

    return res and check_link_verbose(out)

def _build_empty_program(context, fcomp):
    """Build an empty fortran stand alone program, and capture the output of
    the link step.

    Return:
        st : 1 on success, 0 on failure.
        list : list of lines of the output."""
    cnt = []
    src = """
      PROGRAM MAIN
      END"""
    # XXX: the logic to choose fortran compiler is bogus...
    if fcomp == 'F77':
        res = context.TryCompile(src, '.f')
    elif fcomp == 'F90':
        res = context.TryCompile(src, '.f90')
    else:
        raise RuntimeError("fcomp %s not implemented..." % fcomp)
        return 0

    if res:
        if not built_with_mstools(context.env):
            res, cnt = _build_empty_program_posix(context, fcomp)
        else:
            res, cnt = _build_empty_program_ms(context, fcomp)

    return res, cnt

def _build_empty_program_ms(context, fcomp):
    # MS tools and g77/gfortran semantics are totally different, so we cannot
    # just compile a program replacing MS linker by g77/gfortran as we can for
    # all other platforms.
    slast = str(context.lastTarget)
    dir = dirname(slast)
    test_prog = pjoin(dir, basename(slast).split('.')[0])
    cmd = context.env.subst("$%s -v -o $TARGET $SOURCES" % fcomp,
                            target = context.env.File(test_prog),
                            source = context.lastTarget)

    st, out = popen_wrapper(cmd, merge = True)
    if st:
        res = 0
    else:
        res = 1
    cnt = out.split('\n')
    return res, cnt

def _build_empty_program_posix(context, fcomp):
    oldLINK = context.env['LINK']
    # XXX: get the fortran compiler
    context.env['LINK'] = '$' + fcomp
    res = 0
    cnt = ''
    try:
        # We always want to do this build, and we do not want scons cache
        # to interfer. So we build a command executed directly through our
        # popen_wrapper, which output is captured.

        # XXX: does this scheme to get the program name always work ? Can
        # we use Scons to get the target name from the object name ?
        slast = str(context.lastTarget)
        dir = dirname(slast)
        test_prog = pjoin(dir, basename(slast).split('.')[0])
        cmd = context.env.subst('$LINKCOM',
                                target = context.env.File(test_prog),
                                source = context.lastTarget)
        st, out = popen_wrapper(cmd, merge = True)
        if st:
            res = 0
        else:
            res = 1
        cnt = out.split('\n')
    finally:
        context.env['LINK'] = oldLINK

    return res, cnt

# Helper to generate combinations of lists
def _RecursiveGenerator(*sets):
   """Returns a generator that yields one tuple per element combination.
      A set may be any iterable to which the not operator is applicable.
   """
   if not sets: return
   def calc(sets):
      head, tail = sets[0], sets[1:]
      if not tail:
         for e in head:
            yield (e,)
      else:
         for e in head:
            for t in calc(tail):
               yield (e,) + t
   return calc(sets)

