import re

from numscons.core.utils import popen_wrapper
from numscons.core.errors import UnknownCompiler

GNUCC = re.compile('gcc version ([0-9-.]+)')
SUNCC = re.compile('Sun C ([0-9-.]+)')
SUNCXX = re.compile('Sun C\+\+ ([0-9-.]+)')
SUNFC = re.compile('Sun Fortran 95 ([0-9-.]+)')

def parse_suncc(string):
    m = SUNCC.search(string)
    if m:
        return True, m.group(1)
    else:
        return False, None

def parse_suncxx(string):
    m = SUNCXX.search(string)
    if m:
        return True, m.group(1)
    else:
        return False, None

def parse_sunfortran(string):
    m = SUNFC.search(string)
    if m:
        return True, m.group(1)
    else:
        return False, None

def parse_gnu(string):
    m = GNUCC.search(string)
    if m:
        return True, m.group(1)
    else:
        return False, None

def is_suncc(path):
    """Return True if the compiler in path is sun C compiler."""
    # If the Sun compiler is not given a file as an argument, it returns an
    # error code, even when using dry run and version. So we give a non
    # existing file as an argument: this seems to work, at least for Sun Studio
    # 12 (5.9)
    cmd = [path, '-V', "-###", "nonexistingfile.fakec"]
    st, cnt = popen_wrapper(cmd, merge = True, shell = False)
    ret, ver = parse_suncc(cnt)
    if st == 0 and ret:
        return ret, ver
    else:
        return False, None

def is_suncxx(path):
    """Return True if the compiler in path is sun CXX compiler."""
    # Works on 5.9 (Sun Studio 12). Note that the C++ compiler works in a
    # sensible manner when given -V compared to the C compiler...
    cmd = [path, '-V']
    st, cnt = popen_wrapper(cmd, merge = True, shell = False)
    ret, ver = parse_suncxx(cnt)
    if st == 0 and ret:
        return ret, ver
    else:
        return False, None

def is_sunfortran(path):
    """Return True if the compiler in path is sun fortran compiler."""
    # Works on 8.3 (Sun Studio 12)
    cmd = [path, '-V']
    st, cnt = popen_wrapper(cmd, merge = True, shell = False)
    ret, ver = parse_sunfortran(cnt)
    if st == 0 and ret:
        return ret, ver
    else:
        return False, None

def is_gcc(path):
    """Return True if the compiler in path is GNU compiler."""
    cmd = [path, '-v']
    st, cnt = popen_wrapper(cmd, merge = True, shell = False)
    ret, ver = parse_gnu(cnt)
    if st == 0 and ret:
        return ret, ver
    else:
        return False, None

def get_cc_type(path):
    if is_gcc(path)[0]:
        return "gcc"
    elif is_suncc(path)[0]:
        return "suncc"
    raise UnknownCompiler("Unknown C compiler %s" % path)

def get_cxx_type(path):
    if is_gcc(path)[0]:
        return "g++"
    elif is_suncxx(path)[0]:
        return "suncc"
    raise UnknownCompiler("Unknown CXX compiler %s" % path)

def get_f77_type(path):
    st, v = is_gcc(path)
    if st:
        try:
            major = int(v.split(".")[0])
            if major < 4:
                return "g77"
            else:
                return "gfortran"
        except ValueError:
            raise UnknownCompiler("Could not parse version %v" % v)
    elif is_sunfortran(path)[0]:
        return "sunf77"
    raise UnknownCompiler("Unknown F77 compiler %s" % path)

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        raise ValueError("Usage: %s compiler" % __file__)
    cc = sys.argv[1]
    try:
        print get_cc_type(cc)
    except UnknownCompiler, e:
        print e

    try:
        print get_cxx_type(cc)
    except UnknownCompiler, e:
        print e
