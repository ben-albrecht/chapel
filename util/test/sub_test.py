#!/usr/bin/env python
"""
 sub_test is used by start_test in the Chapel Testing system

 sub_test interacts with start_test almost exclusively through the environment
 that start_test sets up. The exception is the path to a binary  passed as a
 command line argument, which sub_test uses both to run the given test and
 infer the location of other paths, such as $CHPL_HOME.

 This script can be overridden with a script by the same name
 placed in the test directory.
"""

from __future__ import with_statement, print_function

import execution_limiter
import sys, os, subprocess, string, signal
import operator
import select, fcntl
import fnmatch, time
import re
import shlex
import datetime

from atexit import register
from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter


# TODO -- no globals
# Globals
perflabel = ''
localdir = ''
sub_test_start_time = time.time()


@register
def elapsed_sub_test_time():
    """Print elapsed time for sub_test call to console."""
    global sub_test_start_time, localdir
    elapsed_sec = time.time() - sub_test_start_time

    test_name = localdir
    if 'CHPL_ONETEST' in os.environ:
        chpl_name = os.environ.get('CHPL_ONETEST')
        base_name = os.path.splitext(chpl_name)[0]
        test_name = os.path.join(test_name, base_name)

    print('[Finished subtest "{0}" - {1:.3f} seconds]\n'.format(test_name, elapsed_sec))


class ReadTimeoutException(Exception):
    """
     Time out class:  Read from a stream until time out
     A little ugly but sending SIGALRM (or any other signal) to Python
     can be unreliable (will not respond if holding certain locks).
    """
    pass



def SetNonBlock(stream):
    flags = fcntl.fcntl(stream.fileno(), fcntl.F_GETFL)
    flags |= os.O_NONBLOCK
    fcntl.fcntl(stream.fileno(), fcntl.F_SETFL, flags)


def SuckOutputWithTimeout(stream, timeout):
    SetNonBlock(stream)
    buffer = ''
    end_time = time.time() + timeout
    while True:
        now = time.time()
        if end_time <= now:
            # Maybe return partial result instead?
            raise ReadTimeoutException('Teh tiem iz out!');
        ready_set = select.select([stream], [], [], end_time - now)[0]
        if stream in ready_set:
            bytes = stream.read()
            if len(bytes) == 0:
                break           # EOF
            buffer += bytes     # Inefficient way to accumulate bytes.
            # len(ready_set) == 0 is also an indication of timeout. However,
            # if we relied on that, we would require no data ready in order
            # to timeout  which doesn't seem quite right either.
    return buffer


def LauncherTimeoutArgs(seconds):
    if useLauncherTimeout == 'pbs' or useLauncherTimeout == 'slurm':
        # --walltime=hh:mm:ss
        m, s = divmod(seconds, 60)
        h, m = divmod(m, 60)
        fmttime = '--walltime={0:02d}:{1:02d}:{2:02d}'.format(h, m, s)
        return [fmttime]
    else:
        Fatal('LauncherTimeoutArgs encountered an unknown format spec: ' + \
              useLauncherTimeout)


#
# Auxilliary functions
#

def ShellEscape(arg):
    """ Escape all special characters """
    return re.sub(r'([\\!@#$%^&*()?\'"|<>[\]{} ])', r'\\\1', arg)


def ShellEscapeCommand(arg):
    """ Escape all special characters but leave spaces alone """
    return re.sub(r'([\\!@#$%^&*()?\'"|<>[\]{}])', r'\\\1', arg)


def trim_output(output):
    """ Grabs the start and end of the output and replaces non-printable chars with ~ """
    max_size = 256*1024 # ~1/4 MB
    if len(output) > max_size:
        new_output = output[:max_size/2]
        new_output += output[-max_size/2:]
        output = new_output
    return ''.join(s if s in string.printable else "~" for s in output)


def IsChplTest(f):
    """ Return True if f has .chpl extension """
    if re.match(r'^.+\.(chpl|test\.c)$', f):
        return True
    else:
        return False


def PerfSfx(s):
    """ File suffix: 'keys' -> '.perfkeys' etc. """
    global perflabel
    return '.' + perflabel + s


def PerfDirFile(s):
    """ Directory-wide file: 'COMPOPTS' or 'compopts' -> './PERFCOMPOPTS' etc. """
    global perflabel
    return './' + perflabel.upper() + s.upper()


def PerfTFile(test_filename, sfx):
    """ Test-specific file: (foo,keys) -> foo.perfkeys etc. """
    global perflabel
    return test_filename + '.' + perflabel + sfx


def ReadFileWithComments(f, ignoreLeadingSpace=True):
    """
    Read a file or if the file is executable read its output. If the file is
    executable, the current chplenv is copied into the env before executing.
    Expands shell variables and strip out comments/whitespace. Returns a list
    of string, one per line in the file.
    """
    mylines = ""
    # if the file is executable, run it and grab the output. If we get an
    # OSError while trying to run, report it and try to keep going
    if os.access(f, os.X_OK):
        try:
            # grab the chplenv so it can be stuffed into the subprocess env
            env_cmd = [os.path.join(utildir, 'printchplenv'), '--simple']
            chpl_env = subprocess.Popen(env_cmd, stdout=subprocess.PIPE).communicate()[0]
            chpl_env = dict(map(lambda l: l.split('='), chpl_env.splitlines()))
            file_env = os.environ.copy()
            file_env.update(chpl_env)

            # execute the file and grab its output
            cmd = subprocess.Popen([os.path.abspath(f)], stdout=subprocess.PIPE, env=file_env)
            mylines = cmd.communicate()[0].splitlines()

        except OSError as e:
            global localdir
            f_name = os.path.join(localdir, f)
            sys.stdout.write("[Error trying to execute '{0}': {1}]\n".format(f_name, str(e)))

    # otherwise, just read the file
    else:
        with open(f, 'r') as myfile:
            mylines = myfile.readlines()

    mylist=list()
    for line in mylines:
        line = line.rstrip()
        # ignore blank lines
        if not line.strip(): continue
        # ignore comments
        if ignoreLeadingSpace:
            if line.lstrip()[0] == '#': continue
        else:
            if line[0] == '#': continue
        # expand shell variables
        line = os.path.expandvars(line)
        mylist.append(line)
    return mylist


def DiffFiles(f1, f2):
    """ Diff 2 files """
    sys.stdout.write('[Executing diff %s %s]\n'%(f1, f2))
    p = subprocess.Popen(['diff',f1,f2],
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    myoutput = p.communicate()[0] # grab stdout to avoid potential deadlock
    if p.returncode != 0:
        sys.stdout.write(trim_output(myoutput))
    return p.returncode


def DiffBadFiles(f1, f2):
    """
    Diff output vs. .bad file, filtering line numbers out of error messages
    that arise in module files.
    """
    sys.stdout.write('[Executing diff-ignoring-module-line-numbers %s %s]\n'%(f1, f2))
    p = subprocess.Popen([utildir+'/test/diff-ignoring-module-line-numbers', f1, f2],
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    myoutput = p.communicate()[0] # grab stdout to avoid potential deadlock
    if p.returncode != 0:
        sys.stdout.write(myoutput)
    return p.returncode


def KillProc(p, timeout):
    """ Kill process """
    k = subprocess.Popen(['kill',str(p.pid)])
    k.wait()
    now = time.time()
    end_time = now + timeout # give it a little time
    while end_time > now:
        if p.poll():
            return
        now = time.time()
    # use the big hammer (and don't bother waiting)
    subprocess.Popen(['kill','-9', str(p.pid)])
    return


def cleanup(execname):
    """ Clean up after the test has been built """
    try:
        if execname is not None:
            if os.path.isfile(execname):
                os.unlink(execname)
            if os.path.isfile(execname+'_real'):
                os.unlink(execname+'_real')
    except (IOError, OSError) as ex:
        # If the error is "Device or resource busy", call lsof on the file (or
        # handle for windows) to see what is holding the file handle, to help
        # debug the issue.
        if isinstance(ex, OSError) and ex.errno == 16:
            handle = which('handle')
            lsof = which('lsof')
            if handle is not None:
                sys.stdout.write('[Inspecting open file handles with: {0}\n'.format(handle))
                subprocess.Popen([handle]).communicate()
            elif lsof is not None:
                cmd = [lsof, execname]
                sys.stdout.write('[Inspecting open file handles with: {0}\n'.format(' '.join(cmd)))
                subprocess.Popen(cmd).communicate()

        # Do not print the warning for cygwin32 when errno is 16 (Device or resource busy).
        if not (getattr(ex, 'errno', 0) == 16 and platform == 'cygwin32'):
            sys.stdout.write('[Warning: could not remove {0}: {1}]\n'.format(execname, ex))


def which(program):
    """
    Returns absolute path to program, if it exists in $PATH. If not found,
    returns None.
    """
    def is_exe(fpath):
        return os.path.isfile(fpath) and os.access(fpath, os.X_OK)

    fpath, fname = os.path.split(program)
    if fpath:
        if is_exe(program):
            return program
    else:
        for path in os.environ.get('PATH', '').split(os.pathsep):
            path = path.strip('"')
            exe_file = os.path.join(path, program)
            if is_exe(exe_file):
                return exe_file
    return None


def printTestVariation(compoptsnum, compoptslist,
                       execoptsnum=0, execoptslist=[] ):
    """ Print (compopts: XX, execopts: XX) for later decoding of failed tests """
    printCompOpts = True
    printExecOpts = True
    if compoptsnum==0 or len(compoptslist) <= 1:
        printCompOpts = False
    if execoptsnum==0 or len(execoptslist) <= 1:
        printExecOpts = False

    if (not printCompOpts) and (not printExecOpts):
        return;

    sys.stdout.write(' (')
    if printCompOpts:
        sys.stdout.write('compopts: %d'%(compoptsnum))
    if printExecOpts:
        if printCompOpts:
            sys.stdout.write(', ')
        sys.stdout.write('execopts: %d'%(execoptsnum))
    sys.stdout.write(')')
    return


def IsInteger(str):
    """ Return true if string is an integer """
    try:
        int(str)
        return True
    except ValueError:
        return False


def ReadIntegerValue(f, localdir):
    """ Read integer value from a file """
    to = ReadFileWithComments(f)
    if to:
        for l in to:
            if l[0] == '#':
                continue
            if IsInteger(l):
                return string.atoi(l)
            else:
                break
    Fatal('Invalid integer value in '+f+' ('+localdir+')')


def Fatal(message):
    """ Report an error message and exit """
    sys.stdout.write('[Error (sub_test): '+message+']\n')
    magic_exit_code = reduce(operator.add, map(ord, 'CHAPEL')) % 256
    sys.exit(magic_exit_code)


def GetTimer(f):
    """
    Attempts to find an appropriate timer to use. The timer must be in
    util/test/timers/. Expects to be passed a file containing only the name of
    the timer script. If the file is improperly formatted the default timer is
    used, and if the timer is not executable or can't be found 'time -p' is used
    """
    timersdir = os.path.join(utildir, 'test', 'timers')
    defaultTimer = os.path.join(timersdir, 'defaultTimer')

    lines = ReadFileWithComments(f)
    if len(lines) != 1:
        sys.stdout.write('[Error "%s" must contain exactly one non-comment line '
            'with the name of the timer located in %s to use. Using default '
            'timer %s.]\n' %(f, timersdir, defaultTimer))
        timer = defaultTimer
    else:
        timer = os.path.join(timersdir, lines[0])

    if not os.access(timer,os.R_OK|os.X_OK):
        sys.stdout.write('[Error cannot execute timer "%s", using "time -p"]\n' %(timer))
        return 'time -p'

    return timer


def FindGoodFile(basename, envCompopts, commExecNums=['']):
    """
    Attempts to find an appropriate .good file. Good files are expected to be of
    the form basename.<configuration>.<commExecNums>.good. Where configuration
    options are one of the below configuration specific parameters that are
    checked for. E.G the current comm layer. commExecNums are the optional
    compopt and execopt number to enable different .good files for different
    compopts/execopts with explicitly specifying name.
    """

    # Machine name we are running on
    machine=os.uname()[1].split('.', 1)[0]

    chpllm=os.getenv('CHPL_LOCALE_MODEL','flat').strip()
    chpllmstr='.lm-'+chpllm

    chplcomm=os.getenv('CHPL_COMM','none').strip()
    chplcommstr='.comm-'+chplcomm

    goodfile = ''
    for commExecNum in commExecNums:
        # Try the machine specific .good
        if not os.path.isfile(goodfile):
            goodfile = basename+'.'+machine+commExecNum+'.good'
        # Else if --no-local try the no-local .good file.
        if not os.path.isfile(goodfile):
            if '--no-local' in envCompopts:
                goodfile=basename+'.no-local'+commExecNum+'.good'
        # Else try comm and locale model specific .good file.
        if not os.path.isfile(goodfile):
            goodfile=basename+chplcommstr+chpllmstr+commExecNum+'.good'
        # Else try the comm-specific .good file.
        if not os.path.isfile(goodfile):
            # CHPL_COMM
            goodfile=basename+chplcommstr+commExecNum+'.good'
        # Else try locale model specific .good file.
        if not os.path.isfile(goodfile):
            goodfile=basename+chpllmstr+commExecNum+'.good'
        # Else try the platform-specific .good file.
        if not os.path.isfile(goodfile):
            utildir=os.getenv('CHPL_TEST_UTIL_DIR');
            platform=subprocess.Popen([utildir+'/chplenv/chpl_platform.py', '--target'], stdout=subprocess.PIPE).communicate()[0]
            platform = platform.strip()
            goodfile=basename+'.'+platform+commExecNum+'.good'
        # Else use the execopts-specific .good file.
        if not os.path.isfile(goodfile):
            goodfile=basename+commExecNum+'.good'

    return goodfile


def get_exec_log_name(execname, comp_opts_count=None, exec_opts_count=None):
    """
    Returns the execution output log name based on number of comp and exec opts
    """
    suffix = '.exec.out.tmp'
    if comp_opts_count is None and exec_opts_count is None:
        return '{0}{1}'.format(execname, suffix)
    else:
        return '{0}.{1}-{2}{3}'.format(execname, comp_opts_count, exec_opts_count, suffix)


def runSkipIf(skipifName):
    """
    Use testEnv to process skipif files, it works for executable and
    non-executable versions
    """
    skiptest = subprocess.Popen([utildir+'/test/testEnv', './'+skipifName], stdout=subprocess.PIPE).communicate()[0]
    return skiptest


def get_chpl_home(compiler):
    """ Find and return $CHPL_HOME """

    path_to_compiler = os.path.abspath(os.path.dirname(compiler))

    # Assume chpl binary is 2 directory levels down in the base installation
    (chpl_base, tmp) = os.path.split(path_to_compiler)
    (chpl_base, tmp) = os.path.split(chpl_base)
    chpl_base = os.path.normpath(chpl_base)

    # If $CHPL_HOME is not set, use the base installation of the compiler
    chpl_home = os.getenv('CHPL_HOME', chpl_base);
    return os.path.normpath(chpl_home)


def get_utildir():
    """
    Find the test util directory -- set this in start_test to permit
    a version of start_test other than the one in CHPL_HOME to be used
    """

    utildir=os.getenv('CHPL_TEST_UTIL_DIR');

    if utildir is None or not os.path.isdir(utildir):
        Fatal('Cannot find test util directory {0}'.format(utildir))

    # Needed for MacOS mount points
    return os.path.realpath(utildir)


def get_c_compiler(chpl_home):
    """ Find the c compiler """
    # We open the compileline inside of CHPL_HOME rather than CHPL_TEST_UTIL_DIR on
    # purpose. compileline will not work correctly in some configurations when run
    # outside of its directory tree.
    p = subprocess.Popen([os.path.join(chpl_home,'util','config','compileline'),
                            '--compile'],
                        stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    c_compiler = p.communicate()[0].rstrip()
    if p.returncode != 0:
      Fatal('Cannot find c compiler')

    return c_compiler


def parse_args():
    """ Parse command line arguments """

    parser = ArgumentParser(prog='sub_test',
                            usage= "%(prog)s compiler",
                            description = ''' Testing script ''',
                            formatter_class=ArgumentDefaultsHelpFormatter
                           )
    parser.add_argument('compiler', type=str, help='compiler to use')

    return parser.parse_args()


def get_compilerkey(compiler):
    # Find the base installation
    if not os.access(compiler,os.R_OK|os.X_OK):
        Fatal('Cannot execute compiler \'${0}\''.format(compiler))

    compilerkey = 'chpl'
    if compiler.endswith('chpldoc'):
        return 'chpldoc'
    elif compiler.endswith('chpl-ipe'):
        return 'chpl-ipe'


def get_testdir(chpl_home):
    """ Find the test directory """

    testdir = chpl_home + '/test'
    if os.path.isdir(testdir) == 0:
        testdir = chpl_home + '/examples'
        if os.path.isdir(testdir) == 0:
            Fatal('Cannot find test directory ' + chpl_home + '/test or ' + testdir)
    # Needed for MacOS mount points
    testdir = os.path.realpath(testdir)

    # If user specified a different test directory (e.g. with --test-root flag on
    # start_test), use it instead.
    test_root_dir = os.environ.get('CHPL_TEST_ROOT_DIR')
    if test_root_dir is not None:
        testdir = test_root_dir

    return testdir


def timedexec():
    """ Note: This change should be tested and merged separately"""
    pass



def main(compiler):
    """
    sub_test entry point, called from start_test
    """

    """
    Check environment
    """

    compilerkey = get_compilerkey(compiler)

    chpl_home = get_chpl_home(compiler)

    utildir = get_utildir()

    c_compiler = get_c_compiler(chpl_home)

    testdir = get_testdir(chpl_home)

    # Use timedexec
    # As much as I hate calling out to another script for the time out stuff,
    #  subprocess doesn't quite cut it for this kind of stuff
    useTimedExec=True
    if useTimedExec:
        timedexec=utildir+'/test/timedexec'
        if not os.access(timedexec,os.R_OK|os.X_OK):
            Fatal('Cannot execute timedexec script \''+timedexec+'\'')

    # HW platform
    platform=subprocess.Popen([utildir+'/chplenv/chpl_platform.py', '--target'], stdout=subprocess.PIPE).communicate()[0]
    platform = platform.strip()

    # Get the system-wide preexec
    systemPreexec = os.getenv('CHPL_SYSTEM_PREEXEC')
    if systemPreexec is not None:
        if not os.access(systemPreexec, os.R_OK|os.X_OK):
            Fatal("Cannot execute system-wide preexec '{0}'".format(systemPreexec))

    # Get the system-wide prediff
    systemPrediff = os.getenv('CHPL_SYSTEM_PREDIFF')
    if systemPrediff:
      if not os.access(systemPrediff,os.R_OK|os.X_OK):
        Fatal('Cannot execute system-wide prediff \''+systemPrediff+'\'')

    # Use the launcher walltime option for timeout
    useLauncherTimeout = os.getenv('CHPL_LAUNCHER_TIMEOUT')

    uniquifyTests = False
    if os.getenv('CHPL_TEST_UNIQUIFY_EXE') != None:
        uniquifyTests = True

    global localdir
    # Get the current directory (normalize for MacOS case-sort-of-sensitivity)
    localdir = string.replace(os.path.normpath(os.getcwd()), testdir, '.')

    if localdir.find('./') == 0:
        # strip off the leading './'
        localdir = string.lstrip(localdir, '.')
        localdir = string.lstrip(localdir, '/')

    # CHPL_COMM
    chplcomm=os.getenv('CHPL_COMM','none').strip()
    chplcommstr='.comm-'+chplcomm

    # CHPL_LAUNCHER
    chpllauncher=os.getenv('CHPL_LAUNCHER','none').strip()

    # CHPL_LOCALE_MODEL
    chpllm=os.getenv('CHPL_LOCALE_MODEL','flat').strip()
    chpllmstr='.lm-'+chpllm

    #
    # Test options for all tests in this directory
    #

    global perflabel
    if os.getenv('CHPL_TEST_PERF')!=None:
        perftest=True
        perflabel=os.getenv('CHPL_TEST_PERF_LABEL')
        perfdir=os.getenv('CHPL_TEST_PERF_DIR')
        perfdescription = os.getenv('CHPL_TEST_PERF_DESCRIPTION')
        if perfdescription != None:
            sys.stdout.write('Setting perfdir to %s from %s because of additional perf description\n' %(os.path.join(perfdir, perfdescription), perfdir))
            perfdir = os.path.join(perfdir, perfdescription)
        else:
            perfdescription= ''
        if perflabel==None or perfdir==None:
            Fatal('$CHPL_TEST_PERF_DIR and $CHPL_TEST_PERF_LABEL must be set for performance testing')
    else:
        perftest=False
        perflabel=''

    """
    Check files
    """

    compoptssuffix = PerfSfx('compopts')  # .compopts or .perfcompopts or ...

    # If compiler is chpldoc, use .chpldocopts for options.
    chpldocsuffix = '.chpldocopts'

    compenvsuffix  = PerfSfx('compenv')   # compenv  or .perfcompenv  or ...
    execenvsuffix  = PerfSfx('execenv')   # .execenv  or .perfexecenv  or ...
    execoptssuffix = PerfSfx('execopts')  # .execopts or .perfexecopts or ...
    timeoutsuffix  = PerfSfx('timeout')   # .timeout  or .perftimeout  or ...

    # Get global timeout
    if os.getenv('CHPL_TEST_VGRND_COMP')=='on' or os.getenv('CHPL_TEST_VGRND_EXE')=='on':
        globalTimeout=1000
    else:
        globalTimeout=300
    globalTimeout = int(os.getenv('CHPL_TEST_TIMEOUT', globalTimeout))

    # get a threshold for which to report long running tests
    if os.getenv("CHPL_TEST_EXEC_TIME_WARN_LIMIT"):
        execTimeWarnLimit = int(os.getenv('CHPL_TEST_EXEC_TIME_WARN_LIMIT', '0'))
    else:
        execTimeWarnLimit = 0

    # directory level timeout
    if os.access('./TIMEOUT',os.R_OK):
        directoryTimeout = ReadIntegerValue('./TIMEOUT', localdir)
    else:
        directoryTimeout = globalTimeout

    # Check for global PERFTIMEEXEC option
    timerFile = PerfDirFile('TIMEEXEC') # e.g. ./PERFTIMEEXEC
    if os.access(timerFile, os.R_OK):
        globalTimer = GetTimer(timerFile)
    else:
        globalTimer = None

    # Get global timeout for kill
    if os.access('./KILLTIMEOUT',os.R_OK):
        globalKillTimeout = ReadIntegerValue('./KILLTIMEOUT', localdir)
    else:
        globalKillTimeout=10

    if os.access('./NOEXEC',os.R_OK):
        execute=False
    else:
        execute=True

    if os.access('./NOVGRBIN',os.R_OK):
        vgrbin=False
    else:
        vgrbin=True

    if os.access('./COMPSTDIN',os.R_OK):
        compstdin='./COMPSTDIN'
    else:
        compstdin='/dev/null'

    globalLastcompopts=list();
    if os.access('./LASTCOMPOPTS',os.R_OK):
        globalLastcompopts+=subprocess.Popen(['cat', './LASTCOMPOPTS'], stdout=subprocess.PIPE).communicate()[0].strip().split()

    globalLastexecopts=list();
    if os.access('./LASTEXECOPTS',os.R_OK):
        globalLastexecopts+=subprocess.Popen(['cat', './LASTEXECOPTS'], stdout=subprocess.PIPE).communicate()[0].strip().split()

    if os.access(PerfDirFile('NUMLOCALES'),os.R_OK):
        globalNumlocales=ReadIntegerValue(PerfDirFile('NUMLOCALES'), localdir)
        # globalNumlocales.strip(globalNumlocales)
    else:
        # start_test sets this, so we'll assume it's right :)
        globalNumlocales=int(os.getenv('NUMLOCALES', '0'))

    maxLocalesAvailable = os.getenv('CHPL_TEST_NUM_LOCALES_AVAILABLE')
    if maxLocalesAvailable is not None:
        maxLocalesAvailable = int(maxLocalesAvailable)

    if os.access('./CATFILES',os.R_OK):
        globalCatfiles=subprocess.Popen(['cat', './CATFILES'], stdout=subprocess.PIPE).communicate()[0]
        globalCatfiles.strip(globalCatfiles)
    else:
        globalCatfiles=None


    #
    # valgrind stuff
    #
    chpl_valgrind_opts=os.getenv('CHPL_VALGRIND_OPTS', '--tool=memcheck')

    if os.getenv('CHPL_TEST_VGRND_COMP')=='on':
        valgrindcomp = 'valgrind'
        valgrindcompopts=chpl_valgrind_opts.split()
        valgrindcompopts+=['--gen-suppressions=all']
        valgrindcompopts+=['--suppressions=%s/compiler/etc/valgrind.suppressions'%(chpl_home)]
        valgrindcompopts+=['-q']
    else:
        valgrindcomp = None
        valgrindcompopts = None

    if (os.getenv('CHPL_TEST_VGRND_EXE')=='on' and vgrbin):
        valgrindbin = 'valgrind'
        valgrindbinopts = chpl_valgrind_opts.split()+['-q']
        if (chplcomm!='none'):
            valgrindbinopts+=['--trace-children=yes']
    else:
        valgrindbin = None
        valgrindbinopts = None


    #
    # Misc set up
    #

    testfutures=string.atoi(os.getenv('CHPL_TEST_FUTURES','0'))

    testnotests=os.getenv('CHPL_TEST_NOTESTS')

    launchcmd=os.getenv('LAUNCHCMD')

    if os.getenv('CHPL_TEST_INTERP')=='on':
        execute=False
        futureSuffix='.ifuture'
    else:
        futureSuffix='.future'

    printpassesfile = None
    if os.getenv('CHPL_TEST_COMP_PERF')!=None:
        compperftest=True

        # check for the main compiler performance directory
        if os.getenv('CHPL_TEST_COMP_PERF_DIR')!=None:
            compperfdir=os.getenv('CHPL_TEST_COMP_PERF_DIR')
        else:
            compperfdir=chpl_home+'/test/compperfdat/'

        # The env var CHPL_PRINT_PASSES_FILE will cause the
        # compiler to save the pass timings to specified file.
        if os.getenv('CHPL_PRINT_PASSES_FILE')!=None:
            printpassesfile=os.getenv('CHPL_PRINT_PASSES_FILE')
        else:
            printpassesfile='timing.txt'
            os.environ['CHPL_PRINT_PASSES_FILE'] = 'timing.txt'

        # check for the perfkeys file
        if os.getenv('CHPL_TEST_COMP_PERF_KEYS')!=None:
            keyfile=os.getenv('CHPL_TEST_COMP_PERF_KEYS')
        else:
            keyfile=chpl_home+'/test/performance/compiler/compilerPerformance.perfkeys'

        # Check for the directory to store the tempory .dat files that will get
        # combined into one.
        if os.getenv('CHPL_TEST_COMP_PERF_TEMP_DAT_DIR')!=None:
            tempDatFilesDir = os.getenv('CHPL_TEST_COMP_PERF_TEMP_DAT_DIR')
        else:
            tempDatFilesDir = compperfdir + 'tempCompPerfDatFiles/'

    else:
        compperftest=False

    #
    # Global COMPOPTS/PERFCOMPOPTS:
    #
    #   Prefer PERFCOMPOPTS if doing performance testing; otherwise, use
    #   COMPOPTS.  Note that COMPOPTS is used for performance testing
    #   currently in the absence of a PERFCOMPOPTS file.  Not sure whether
    #   or not this is a good idea, but preserving it for now for backwards
    #   compatibility.
    #

    directoryCompopts = list(' ')
    if (perftest and os.access(PerfDirFile('COMPOPTS'),os.R_OK)): # ./PERFCOMPOPTS
        directoryCompopts=ReadFileWithComments(PerfDirFile('COMPOPTS'))
    elif os.access('./COMPOPTS',os.R_OK):
        directoryCompopts=ReadFileWithComments('./COMPOPTS')

    envCompopts = os.getenv('COMPOPTS')
    if envCompopts is not None:
        envCompopts = shlex.split(envCompopts)
    else:
      envCompopts = []

    # Global CHPLDOCOPTS
    if os.access('./CHPLDOCOPTS', os.R_OK):
        dirChpldocOpts = shlex.split(ReadFileWithComments('./CHPLDOCOPTS')[0])
    else:
        dirChpldocOpts = []

    # Env CHPLDOCOPTS
    envChpldocOpts = os.getenv('CHPLDOCOPTS')
    if envChpldocOpts is not None:
        envChpldocOpts = shlex.split(envChpldocOpts)
    else:
        envChpldocOpts = []

    # Global chpldoc options.
    globalChpldocOpts = dirChpldocOpts + envChpldocOpts

    #
    # Global PERFNUMTRIALS
    #
    if perftest and os.access(PerfDirFile('NUMTRIALS'), os.R_OK): # ./PERFNUMTRIALS
        globalNumTrials = ReadIntegerValue(PerfDirFile('NUMTRIALS'), localdir)
    else:
        globalNumTrials=int(os.getenv('CHPL_TEST_NUM_TRIALS', '1'))

    #
    # Global EXECENV
    #
    if os.access('./EXECENV',os.R_OK):
        globalExecenv=ReadFileWithComments('./EXECENV')
    else:
        globalExecenv=list()

    #
    # Global COMPENV
    #
    if os.access('./COMPENV',os.R_OK):
        globalCompenv=ReadFileWithComments('./COMPENV')
    else:
        globalCompenv=list()

    #
    # Global EXECOPTS/PERFEXECOPTS
    #
    #
    #   Prefer PERFEXECOPTS if doing performance testing; otherwise, use
    #   EXECOPTS.  Note that EXECOPTS is used for performance testing
    #   currently in the absence of a PERFEXECOPTS file.  Not sure whether
    #   or not this is a good idea, but preserving it for now for backwards
    #   compatibility.
    #
    if (perftest and os.access(PerfDirFile('EXECOPTS'),os.R_OK)): # ./PERFEXECOPTS
        tgeo=ReadFileWithComments(PerfDirFile('EXECOPTS'))
        globalExecopts= shlex.split(tgeo[0])
    elif os.access('./EXECOPTS',os.R_OK):
        tgeo=ReadFileWithComments('./EXECOPTS')
        globalExecopts= shlex.split(tgeo[0])
    else:
        globalExecopts=list()
    envExecopts = os.getenv('EXECOPTS')

    #
    # Global PRECOMP, PREDIFF & PREEXEC
    #
    if os.access('./PRECOMP', os.R_OK|os.X_OK):
        globalPrecomp='./PRECOMP'
    else:
        globalPrecomp=None
    #
    if os.access('./PREDIFF',os.R_OK|os.X_OK):
        globalPrediff='./PREDIFF'
    else:
        globalPrediff=None
    if os.access('./PREEXEC',os.R_OK|os.X_OK):
        globalPreexec='./PREEXEC'
    else:
        globalPreexec=None
    #
    # Start running tests
    #
    sys.stdout.write('[Starting subtest - %s]\n'%(time.strftime('%a %b %d %H:%M:%S %Z %Y', time.localtime())))
    #sys.stdout.write('[compiler: \'%s\']\n'%(compiler))
    if systemPreexec:
        sys.stdout.write("[system-wide preexec: '{0}']\n".format(systemPreexec))
    if systemPrediff:
        sys.stdout.write('[system-wide prediff: \'%s\']\n'%(systemPrediff))

    # consistently look only at the files in the current directory
    dirlist=os.listdir(".")

    onetestsrc = os.getenv('CHPL_ONETEST')
    if onetestsrc==None:
        testsrc=filter(IsChplTest, dirlist)
    else:
        testsrc=list()
        testsrc.append(onetestsrc)

    original_compiler = compiler

    for testname in testsrc:
        sys.stdout.flush()

        compiler = original_compiler

        # print testname
        sys.stdout.write('[test: %s/%s]\n'%(localdir,testname))
        test_filename = re.match(r'^(.*)\.(?:chpl|test\.c)$', testname).group(1)
        execname = test_filename
        if uniquifyTests:
            execname += '.{0}'.format(os.getpid())
        # print test_filename

        if re.match(r'^.+\.test\.c$', testname):
          is_c_test = True
        else:
          is_c_test = False

        # If the test name ends with .doc.chpl or the compiler was set to chpldoc
        # (i.e. is_chpldoc=True), run this test with chpldoc options.
        if testname.endswith('.doc.chpl') or compilerkey == 'chpldoc':
            test_is_chpldoc = True
        else:
            test_is_chpldoc = False

        # Test specific settings
        catfiles = globalCatfiles
        numlocales = globalNumlocales
        lastcompopts = list()
        if globalLastcompopts:
            lastcompopts += globalLastcompopts
        lastexecopts = list()
        if globalLastexecopts:
            lastexecopts += globalLastexecopts

        # Get the list of files starting with 'test_filename.'
        test_filename_files = fnmatch.filter(dirlist, test_filename+'.*')
        # print test_filename_files, dirlist

        if (perftest and (test_filename_files.count(PerfTFile(test_filename,'keys'))==0) and
            (test_filename_files.count(PerfTFile(test_filename,'execopts'))==0)):
            sys.stdout.write('[Skipping noperf test: %s/%s]\n'%(localdir,test_filename))
            continue # on to next test

        timeout = directoryTimeout
        killtimeout = globalKillTimeout
        numTrials = globalNumTrials
        if (perftest):
            timer = globalTimer
        else:
            timer = None
        futuretest=''

        if test_is_chpldoc or compilerkey == 'chpl-ipe':
            executebin = False
        else:
            executebin = execute

        testfuturesfile=False
        testskipiffile=False
        noexecfile=False
        execoptsfile=False
        precomp=None
        prediff=None
        preexec=None

        if os.getenv('CHPL_NO_STDIN_REDIRECT') == None:
            redirectin = '/dev/null'
        else:
            redirectin = None

        # If there is a .skipif file, put it at front of list.
        skipif_i = -1
        for i, test_filename_file in enumerate(test_filename_files):
            if test_filename_file.endswith('.skipif'):
                skipif_i = i
                break
        if skipif_i > 0:
            test_filename_files.insert(0, test_filename_files.pop(skipif_i))

        # Deal with these files
        do_not_test=False
        for f in test_filename_files:
            (root, suffix) = os.path.splitext(f)

            # 'f' is of the form test_filename.SOMETHING.suffix,
            # not pertinent at the moment
            if root != test_filename:
                continue

            # Deal with these later
            if (suffix == '.good' or
                suffix=='.compopts' or suffix=='.perfcompopts' or
                suffix=='.chpldocopts' or
                suffix=='.execenv' or suffix=='.perfexecenv' or
                suffix=='.compenv' or suffix=='.perfcompenv' or
                suffix=='.execopts' or suffix=='.perfexecopts'):
                continue # on to next file

            elif (suffix=='.notest' and (os.access(f, os.R_OK) and
                                         testnotests=='0')):
                sys.stdout.write('[Skipping notest test: %s/%s]\n'%(localdir,test_filename))
                do_not_test=True
                break

            elif (suffix=='.skipif' and (os.access(f, os.R_OK) and
                   (os.getenv('CHPL_TEST_SINGLES')=='0'))):
                testskipiffile=True
                skiptest=runSkipIf(f)
                try:
                    skipme=False
                    if skiptest.strip() != "False":
                        skipme = skiptest.strip() == "True" or int(skiptest) == 1
                    if skipme:
                        sys.stdout.write('[Skipping test based on .skipif environment settings: %s/%s]\n'%(localdir,test_filename))
                        do_not_test=True
                except ValueError:
                    sys.stdout.write('[Error processing .skipif file %s/%s]\n'%(localdir,f))
                    do_not_test=True
                if do_not_test:
                    break

            elif (suffix=='.suppressif' and (os.access(f, os.R_OK))):
                suppresstest=runSkipIf(f)
                try:
                    suppressme=False
                    if suppresstest.strip() != "False":
                        suppressme = suppresstest.strip() == "True" or int(suppresstest) == 1
                    if suppressme:
                        suppressline = ""
                        with open('./'+test_filename+'.suppressif', 'r') as suppressfile:
                            for line in suppressfile:
                                line = line.strip()
                                if (line.startswith("#") and
                                    not line.startswith("#!")):
                                    suppressline = line.replace('#','').strip()
                                    break
                        futuretest='Suppress (' + suppressline + ') '
                except ValueError:
                    sys.stdout.write('[Error processing .suppressif file %s/%s]\n'%(localdir,f))

            elif (suffix==timeoutsuffix and os.access(f, os.R_OK)):
                timeout=ReadIntegerValue(f, localdir)
                sys.stdout.write('[Overriding default timeout with %d]\n'%(timeout))
            elif (perftest and suffix==PerfSfx('timeexec') and os.access(f, os.R_OK)): #e.g. .perftimeexec
                timer = GetTimer(f)

            elif (perftest and suffix==PerfSfx('numtrials') and os.access(f, os.R_OK)): #e.g. .perfnumtrials
                numTrials = ReadIntegerValue(f, localdir)

            elif (suffix=='.killtimeout' and os.access(f, os.R_OK)):
                killtimeout=ReadIntegerValue(f, localdir)

            elif (suffix=='.catfiles' and os.access(f, os.R_OK)):
                execcatfiles=subprocess.Popen(['cat', f], stdout=subprocess.PIPE).communicate()[0].strip()
                if catfiles:
                    catfiles+=execcatfiles
                else:
                    catfiles=execcatfiles

            elif (suffix=='.lastcompopts' and os.access(f, os.R_OK)):
                lastcompopts+=subprocess.Popen(['cat', f], stdout=subprocess.PIPE).communicate()[0].strip().split()

            elif (suffix=='.lastexecopts' and os.access(f, os.R_OK)):
                lastexecopts+=subprocess.Popen(['cat', f], stdout=subprocess.PIPE).communicate()[0].strip().split()

            elif (suffix==PerfSfx('numlocales') and os.access(f, os.R_OK)):
                numlocales=ReadIntegerValue(f, localdir)

            elif suffix==futureSuffix and os.access(f, os.R_OK):
                with open('./'+test_filename+futureSuffix, 'r') as futurefile:
                    futuretest='Future ('+futurefile.readline().strip()+') '

            elif (suffix=='.noexec' and os.access(f, os.R_OK)):
                noexecfile=True
                executebin=False

            elif (suffix=='.precomp' and os.access(f, os.R_OK|os.X_OK)):
                precomp=f

            elif (suffix=='.prediff' and os.access(f, os.R_OK|os.X_OK)):
                prediff=f

            elif (suffix=='.preexec' and os.access(f, os.R_OK|os.X_OK)):
                preexec=f

            elif (suffix=='.stdin' and os.access(f, os.R_OK)):
                if redirectin == None:
                    sys.stdout.write('[Skipping test with .stdin input since -nostdinredirect is given: %s/%s]\n'%(localdir,test_filename))
                    do_not_test=True
                    break
                else:
                    # chpl-ipe only has a "compile" step, so any stdin needs to be
                    # passed to compiler.
                    if compilerkey == 'chpl-ipe':
                        compstdin = f
                    else:
                        redirectin = f

            if suffix==futureSuffix:
                testfuturesfile=True

        del test_filename_files

        # Skip to the next test
        if do_not_test:
            continue # on to next test

        # 0: test no futures
        if testfutures == 0 and testfuturesfile == True:
            sys.stdout.write('[Skipping future test: %s/%s]\n'%(localdir,test_filename))
            continue # on to next test
        # 1: test all futures
        elif testfutures == 1:
            pass
        # 2: test only futures
        elif testfutures == 2 and testfuturesfile == False:
            sys.stdout.write('[Skipping non-future test: %s/%s]\n'%(localdir,test_filename))
            continue # on to next test
        # 3: test futures that have a .skipif file
        elif testfutures == 3 and testfuturesfile == True and testskipiffile == False:
            sys.stdout.write('[Skipping future test without a skipif: %s/%s]\n'%(localdir,test_filename))
            continue # on to next test

        # c tests don't have a way to launch themselves
        if is_c_test and chpllauncher != 'none':
            sys.stdout.write('[Skipping c test: %s/%s]\n'%(localdir,test_filename))
            continue

        # Set numlocales
        if (numlocales == 0) or (chplcomm=='none') or is_c_test:
            numlocexecopts = None
        else:
            if maxLocalesAvailable is not None:
                if numlocales > maxLocalesAvailable:
                    sys.stdout.write('[Warning: skipping {0} because it requires '
                                     '{1} locales but only {2} are available]\n'
                                     .format(os.path.join(localdir, test_filename),
                                             numlocales, maxLocalesAvailable))
                    continue
            numlocexecopts = ' -nl '+str(numlocales)

        # if any performance test has a timeout longer than the default we only
        # want to run it once
        if (timeout > globalTimeout):
            if numTrials != 1:
                sys.stdout.write('[Lowering number of trials for {0} to 1]\n'.format(test_filename))
                numTrials = 1

        # Get list of test specific compiler options
        # Default to [' ']
        compoptslist = list(' ')

        chpldoc_opts_filename = test_filename + chpldocsuffix
        if test_is_chpldoc and os.access(chpldoc_opts_filename, os.R_OK):
            compoptslist = ReadFileWithComments(chpldoc_opts_filename, False)
            if not compoptslist:
                sys.stdout.write('[Warning: ignoring an empty chpldocopts file %s]\n' %
                                 (test_filename+compoptssuffix))
        elif os.access(test_filename+compoptssuffix, os.R_OK):
            compoptslist = ReadFileWithComments(test_filename+compoptssuffix, False)
            if not compoptslist:
                # cf. for execoptslist no warning is issued
                sys.stdout.write('[Warning: ignoring an empty compopts file %s]\n'%(test_filename+compoptssuffix))

        compoptslist = compoptslist or list(' ')
        directoryCompopts = directoryCompopts or list(' ')

        # Merge global compopts list with local compopts.
        # Use the "product" of the two if they are both provided.
        usecompoptslist = [ ]
        # Note -- this could use itertools.product
        for dir_compopts in directoryCompopts:
            for file_compopts in compoptslist:
                useopt = [dir_compopts, file_compopts]
                usearg = ' '.join(useopt)
                # But change all-spaces into single space.
                if usearg.strip() == '':
                  usearg = ' '
                usecompoptslist += [usearg]
        compoptslist = usecompoptslist

        # The test environment is that of this process, augmented as specified
        if os.access(test_filename+execenvsuffix, os.R_OK):
            execenv = ReadFileWithComments(test_filename+execenvsuffix)
        else:
            execenv = list()

        if os.access(test_filename+compenvsuffix, os.R_OK):
            compenv = ReadFileWithComments(test_filename+compenvsuffix)
        else:
            compenv = list()

        testenv = {}
        for var, val in [env.split('=') for env in globalExecenv]:
            testenv[var.strip()] = val.strip()
        for var, val in [env.split('=') for env in execenv]:
            testenv[var.strip()] = val.strip()

        testcompenv = {}
        for var, val in [env.split('=') for env in globalCompenv]:
            testcompenv[var.strip()] = val.strip()
        for var, val in [env.split('=') for env in compenv]:
            testcompenv[var.strip()] = val.strip()


        # Get list of test specific exec options
        if os.access(test_filename+execoptssuffix, os.R_OK):
            execoptsfile=True
            execoptslist = ReadFileWithComments(test_filename+execoptssuffix, False)
        else:
            execoptslist = list()
        # Handle empty execopts list
        if len(execoptslist) == 0:
            # cf. for compoptslist, a warning is issued in this case
            execoptslist.append(' ')

        if (os.getenv('CHPL_TEST_INTERP')=='on' and
            (noexecfile or testfuturesfile or execoptsfile)):
            sys.stdout.write('[Skipping interpretation of: %s/%s]\n'%(localdir,test_filename))
            continue # on to next test

        clist = list()
        curFileTestStart = time.time()

        # For all compopts + execopts combos..
        compoptsnum = 0
        for compopts in compoptslist:
            sys.stdout.flush()
            del clist
            # use the remaining portion as a .good file for executing tests
            #  clist will be *added* to execopts if it is empty, or just used
            #  as the default .good file if not empty
            clist = compopts.split('#')
            if len(clist) >= 2:
                compopts = clist.pop(0)
                cstr = ' #' + '#'.join(clist)
                del clist[:]
                clist.append(cstr)
            else:
                del clist[:]

            if compopts == ' ':
                complog=execname+'.comp.out.tmp'
            else:
                compoptsnum += 1
                complog = execname+'.'+str(compoptsnum)+'.comp.out.tmp'

            #
            # Run the precompile script
            #
            if globalPrecomp:
                sys.stdout.write('[Executing ./PRECOMP]\n')
                sys.stdout.flush()
                p = subprocess.Popen(['./PRECOMP',
                                      execname,complog,compiler],
                                     stdout=subprocess.PIPE,
                                     stderr=subprocess.STDOUT)
                sys.stdout.write(p.communicate()[0])
                sys.stdout.flush()

            if precomp:
                sys.stdout.write('[Executing precomp %s.precomp]\n'%(test_filename))
                sys.stdout.flush()
                p = subprocess.Popen(['./'+test_filename+'.precomp',
                                      execname,complog,compiler],
                                     stdout=subprocess.PIPE,
                                     stderr=subprocess.STDOUT)
                sys.stdout.write(p.communicate()[0])
                sys.stdout.flush()


            #
            # Build the test program
            #
            args = []
            if test_is_chpldoc:
                args += globalChpldocOpts + shlex.split(compopts)
            elif compilerkey == 'chpl-ipe':
                # No arguments work for chpl-ipe as of 2015-04-08. (thomasvandoren)
                # TODO: When chpl-ipe does support command line flags, decide if it
                #       will use COMPOPTS/.compopts or some other filename.
                #       (thomasvandoren, 2015-04-08)
                pass
            else:
                args += ['-o', execname] + envCompopts + shlex.split(compopts)
            args += [testname]

            if is_c_test:
                # we need to drop envCompopts for C tests as those are options
                # for `chpl` so don't include them here
                args = ['-o', test_filename]+shlex.split(compopts)+[testname]
                cmd = c_compiler
            else:
                if test_is_chpldoc and not compiler.endswith('chpldoc'):
                    # For tests with .doc.chpl suffix, use chpldoc compiler. Update
                    # the compopts accordingly. Add 'doc' prefix to existing compiler.
                    compiler += 'doc'
                    cmd = compiler

                    if which(cmd) is None:
                        sys.stdout.write(
                            '[Warning: Could not find chpldoc, skipping test '
                            '{0}/{1}]\n'.format(localdir, test_filename))
                        break

                if valgrindcomp:
                    cmd = valgrindcomp
                    args = valgrindcompopts+[compiler]+args
                else:
                    cmd = compiler

            if lastcompopts:
                args += lastcompopts

            compStart = time.time()
            #
            # Compile (with timeout)
            #
            # compilation timeout defaults to 4 * execution timeout.
            # This is to quiet compilation timeouts in some oversubscribed test
            # configurations (since they are generating a lot of testing noise, but
            # don't represent a real issue.)
            #
            # TODO (Elliot 02/27/15): Ideally what we want is separate options for
            # compiler and testing timeout, but that's more work to thread through
            # sub_test right now and this is causing a lot of noise in nightly
            # testing. Hopefully this is just a temporary work around and I'll
            # remember to add the cleaner solution soon.
            #
            comptimeout = 4*timeout
            cmd=ShellEscapeCommand(cmd);
            sys.stdout.write('[Executing compiler %s'%(cmd))
            if args:
                sys.stdout.write(' %s'%(' '.join(args)))
            sys.stdout.write(' < %s]\n'%(compstdin))
            sys.stdout.flush()
            if useTimedExec:
                wholecmd = cmd+' '+' '.join(map(ShellEscape, args))
                p = subprocess.Popen([timedexec, str(comptimeout), wholecmd],
                                     env=dict(os.environ.items() + testcompenv.items()),
                                     stdin=open(compstdin, 'r'),
                                     stdout=subprocess.PIPE,
                                     stderr=subprocess.STDOUT)
                output = p.communicate()[0]
                status = p.returncode

                if status == 222:
                    sys.stdout.write('%s[Error: Timed out compilation for %s/%s'%
                                     (futuretest, localdir, test_filename))
                    printTestVariation(compoptsnum, compoptslist);
                    sys.stdout.write(']\n')
                    cleanup(execname)
                    cleanup(printpassesfile)
                    continue # on to next compopts

            else:
                p = subprocess.Popen([cmd]+args,
                                     env=dict(os.environ.items() + testcompenv.items()),
                                     stdin=open(cmpstdin, 'r'),
                                     stdout=subprocess.PIPE,
                                     stderr=subprocess.STDOUT)
                try:
                    output = SuckOutputWithTimeout(p.stdout, comptimeout)
                except ReadTimeoutException:
                    sys.stdout.write('%s[Error: Timed out compilation for %s/%s'%
                                     (futuretest, localdir, test_filename))
                    printTestVariation(compoptsnum, compoptslist);
                    sys.stdout.write(']\n')
                    KillProc(p, killtimeout)
                    cleanup(execname)
                    cleanup(printpassesfile)
                    continue # on to next compopts

                status = p.returncode

            elapsedCompTime = time.time() - compStart
            test_name = os.path.join(localdir, test_filename)
            if compoptsnum != 0:
                test_name += ' (compopts: {0})'.format(compoptsnum)

            print('[Elapsed compilation time for "{0}" - {1:.3f} '
                'seconds]'.format(test_name, elapsedCompTime))

            # remove some_file: output from C compilers
            if is_c_test:
              for arg in args:
                if arg.endswith(".c"):
                  # remove lines like
                  # somefile.c:
                  # that some C compilers emit when compiling multiple files
                  output = output.replace(arg + ":\n", "");

            if (status!=0 or not executebin):
                # Save original output
                origoutput = output;

                # Compare compiler output with expected program output
                if catfiles:
                    sys.stdout.write('[Concatenating extra files: %s]\n'%
                                     (test_filename+'.catfiles'))
                    sys.stdout.flush()
                    output+=subprocess.Popen(['cat']+catfiles.split(),
                                             stdout=subprocess.PIPE,
                                             stderr=subprocess.STDOUT).communicate()[0]

                # Sadly these scripts require an actual file
                complogfile=file(complog, 'w')
                complogfile.write('%s'%(output))
                complogfile.close()

                if systemPrediff:
                    sys.stdout.write('[Executing system-wide prediff]\n')
                    sys.stdout.flush()
                    p = subprocess.Popen([systemPrediff,
                                          execname,complog,compiler,
                                          ' '.join(envCompopts)+' '+compopts,
                                          ' '.join(args)],
                                         stdout=subprocess.PIPE,
                                         stderr=subprocess.STDOUT)
                    sys.stdout.write(p.communicate()[0])
                    sys.stdout.flush()

                if globalPrediff:
                    sys.stdout.write('[Executing ./PREDIFF]\n')
                    sys.stdout.flush()
                    p = subprocess.Popen(['./PREDIFF',
                                          execname,complog,compiler,
                                          ' '.join(envCompopts)+' '+compopts,
                                          ' '.join(args)],
                                         stdout=subprocess.PIPE,
                                         stderr=subprocess.STDOUT)
                    sys.stdout.write(p.communicate()[0])
                    sys.stdout.flush()

                if prediff:
                    sys.stdout.write('[Executing prediff %s.prediff]\n'%(test_filename))
                    sys.stdout.flush()
                    p = subprocess.Popen(['./'+test_filename+'.prediff',
                                          execname,complog,compiler,
                                          ' '.join(envCompopts)+' '+compopts,
                                          ' '.join(args)],
                                         stdout=subprocess.PIPE,
                                         stderr=subprocess.STDOUT)
                    sys.stdout.write(p.communicate()[0])
                    sys.stdout.flush()


                # find the compiler .good file to compare against. The compiler
                # .good file can be of the form testname.<configuration>.good or
                # explicitname.<configuration>.good. It's not currently setup to
                # handle testname.<configuration>.<compoptsnum>.good, but that
                # would be easy to add.
                basename = test_filename
                if len(clist) != 0:
                    explicitcompgoodfile = clist[0].split('#')[1].strip()
                    basename = explicitcompgoodfile.replace('.good', '')

                goodfile = FindGoodFile(basename, envCompopts)

                if not os.path.isfile(goodfile) or not os.access(goodfile, os.R_OK):
                    if perftest:
                        sys.stdout.write('[Error compilation failed for %s]\n'%(test_name))
                    else:
                        sys.stdout.write('[Error cannot locate compiler output comparison file %s/%s]\n'%(localdir, goodfile))
                    sys.stdout.write('[Compiler output was as follows:]\n')
                    sys.stdout.write(origoutput)
                    cleanup(execname)
                    cleanup(printpassesfile)
                    continue # on to next compopts

                result = DiffFiles(goodfile, complog)
                if result==0:
                    os.unlink(complog)
                    sys.stdout.write('%s[Success '%(futuretest))
                else:
                    sys.stdout.write('%s[Error '%(futuretest))
                sys.stdout.write('matching compiler output for %s/%s'%
                                     (localdir, test_filename))
                printTestVariation(compoptsnum, compoptslist);
                sys.stdout.write(']\n')

                if (result != 0 and futuretest != ''):
                    badfile=test_filename+'.bad'
                    if os.access(badfile, os.R_OK):
                        badresult = DiffBadFiles(badfile, complog)
                        if badresult==0:
                            os.unlink(complog);
                            sys.stdout.write('[Clean match against .bad file ')
                        else:
                            # bad file doesn't match, which is bad
                            sys.stdout.write('[Error matching .bad file ')
                        sys.stdout.write('for %s/%s'%(localdir, test_filename))
                        printTestVariation(compoptsnum, compoptslist);
                        sys.stdout.write(']\n');

                cleanup(execname)
                cleanup(printpassesfile)
                continue # on to next compopts
            else:
                compoutput = output # save for diff

                exec_log_names = []

                # Exactly one execution output file.
                if len(compoptslist) == 1 and len(execoptslist) == 1:
                    exec_log_names.append(get_exec_log_name(execname))

                # One execution output file for the current compiler opt.
                elif len(compoptslist) > 1 and len(execoptslist) == 1:
                    exec_opts_num_tmp = 1
                    if execoptslist[0] == ' ':
                        exec_opts_num_tmp = 0
                    exec_log_names.append(get_exec_log_name(execname, compoptsnum, exec_opts_num_tmp))

                # One execution output file for each of the execution opts.
                elif len(compoptslist) == 1 and len(execoptslist) > 1:
                    for i in xrange(1, len(execoptslist) + 1):
                        exec_log_names.append(get_exec_log_name(execname, compoptsnum, i))

                # This enumerates the cross product of all compiler and execution
                # opts. It's not clear whether this is actually supported elsewhere
                # (like start_test), but it's here.
                else:
                    for i in xrange(1, len(execoptslist) + 1):
                        exec_log_names.append(get_exec_log_name(execname, compoptsnum, i))

                # Write the log(s), so it/they can be modified by preexec.
                for exec_log_name in exec_log_names:
                    with open(exec_log_name, 'w') as execlogfile:
                        execlogfile.write(compoutput)

            #
            # Compile successful
            #
            sys.stdout.write('[Success compiling %s/%s]\n'%(localdir, test_filename))

            # Note that compiler performance only times successful compilations.
            # Tests that are designed to fail before compilation is complete will
            # not get timed, so the total time compiling might be off slightly.
            if compperftest and not is_c_test:
                # make the compiler performance directories if they don't exist
                timePasses = True
                if not os.path.isdir(compperfdir) and not os.path.isfile(compperfdir):
                    os.makedirs(compperfdir)
                if not os.access(compperfdir, os.R_OK|os.X_OK):
                    sys.stdout.write('[Error creating compiler performance test directory %s]\n'%(compperfdir))
                    timePasses = False

                if not os.path.isdir(tempDatFilesDir) and not os.path.isfile(tempDatFilesDir):
                    os.makedirs(tempDatFilesDir)
                if not os.access(compperfdir, os.R_OK|os.X_OK):
                    sys.stdout.write('[Error creating compiler performance temp dat file test directory %s]\n'%(tempDatFilesDir))
                    timePasses = False

                # so long as we have to the directories
                if timePasses:
                    # We need to name the files differently for each compiler
                    # option. 0 is the default compoptsnum if there are no options
                    # listed so we don't need to clutter the names with that
                    compoptsstring = str(compoptsnum)
                    if compoptsstring == '0':
                        compoptsstring = ''

                    # make the datFileName the full path with / replaced with ~~ so
                    # we can keep the full path for later but not create a bunch of
                    # new directories.
                    datFileName = localdir.replace('/', '~~') + '~~' + test_filename + compoptsstring

                    # computePerfStats for the current test
                    sys.stdout.write('[Executing computePerfStats %s %s %s %s %s]\n'%(datFileName, tempDatFilesDir, keyfile, printpassesfile, 'False'))
                    sys.stdout.flush()
                    p = subprocess.Popen([utildir+'/test/computePerfStats', datFileName, tempDatFilesDir, keyfile, printpassesfile, 'False'], stdout=subprocess.PIPE)
                    compkeysOutput = p.communicate()[0]
                    datFiles = [tempDatFilesDir+'/'+datFileName+'.dat',  tempDatFilesDir+'/'+datFileName+'.error']
                    status = p.returncode

                    if status == 0:
                        sys.stdout.write('[Success finding compiler performance keys for %s/%s]\n'% (localdir, test_filename))
                    else:
                        sys.stdout.write('[Error finding compiler performance keys for %s/%s.]\n'% (localdir, test_filename))
                        printTestVariation(compoptsnum, compoptslist);
                        sys.stdout.write('computePerfStats output was:\n%s\n'%(compkeysOutput))
                        sys.stdout.flush()
                        sys.stdout.write('Deleting .dat files for %s/%s because of failure to find all keys\n'%(localdir, test_filename))
                        for datFile in datFiles:
                            if os.path.isfile(datFile):
                                os.unlink(datFile)

                #delete the timing file
                cleanup(printpassesfile)


            if os.getenv('CHPL_COMPONLY'):
                sys.stdout.write('[Note: Not executing or comparing the output due to -noexec flags]\n')
                cleanup(execname)
                continue # on to next compopts
            explicitcompgoodfile = None
            # Execute the test for all requested execopts
            execoptsnum = 0
            if len(clist)!=0:
                if len(clist[0].split('#')) > 1:
                    explicitcompgoodfile = clist[0].split('#')[1].strip()
            redirectin_set_in_loop = False
            redirectin_original_value = redirectin
            for texecopts in execoptslist:
                sys.stdout.flush()

                # Reset redirectin, in case execopts has multiple lines with
                # different stdin files.
                if redirectin_set_in_loop:
                    redirectin = redirectin_original_value
                    redirectin_set_in_loop = False
                if (len(compoptslist)==1) and (len(execoptslist)==1):
                    onlyone = True
                    execlog = get_exec_log_name(execname)
                else:
                    onlyone = False
                    if texecopts != ' ':
                        execoptsnum += 1
                    execlog = get_exec_log_name(execname, compoptsnum, execoptsnum)

                tlist = texecopts.split('#')
                execopts = tlist[0].strip()

                if numlocexecopts != None:
                    execopts += numlocexecopts;
                if len(tlist) > 1:
                    # Ignore everything after the first token
                    explicitexecgoodfile = tlist[1].strip().split()[0]
                else:
                    explicitexecgoodfile = explicitcompgoodfile
                del tlist

                if systemPreexec:
                    sys.stdout.write('[Executing system-wide preexec]\n')
                    sys.stdout.flush()
                    p = subprocess.Popen([systemPreexec,
                                          execname,execlog,compiler],
                                         stdout=subprocess.PIPE,
                                         stderr=subprocess.STDOUT)
                    sys.stdout.write(p.communicate()[0])
                    sys.stdout.flush()

                if globalPreexec:
                    sys.stdout.write('[Executing ./PREEXEC]\n')
                    sys.stdout.flush()
                    p = subprocess.Popen(['./PREEXEC',
                                          execname,execlog,compiler],
                                         stdout=subprocess.PIPE,
                                         stderr=subprocess.STDOUT)
                    sys.stdout.write(p.communicate()[0])
                    sys.stdout.flush()

                if preexec:
                    sys.stdout.write('[Executing preexec %s.preexec]\n'%(test_filename))
                    sys.stdout.flush()
                    p = subprocess.Popen(['./'+test_filename+'.preexec',
                                          execname,execlog,compiler],
                                         stdout=subprocess.PIPE,
                                         stderr=subprocess.STDOUT)
                    sys.stdout.write(p.communicate()[0])
                    sys.stdout.flush()

                pre_exec_output = ''
                if os.path.exists(execlog):
                    with open(execlog, 'r') as exec_log_file:
                        pre_exec_output = exec_log_file.read()

                if not os.access(execname, os.R_OK|os.X_OK):
                    sys.stdout.write('%s[Error could not locate executable %s for %s/%s'%
                                     (futuretest, execname, localdir, test_filename))
                    printTestVariation(compoptsnum, compoptslist,
                                       execoptsnum, execoptslist)
                    sys.stdout.write(']\n')
                    break; # on to next compopts

                # When doing whole program execution, we want to time the _real
                # binary for launchers that use a queue so we don't include the
                # time to get the reservation. These are the launchers known to
                # support timing the _real using CHPL_LAUNCHER_REAL_WRAPPER.
                timereal = chpllauncher in ['pbs-aprun', 'aprun', 'slurm-srun']

                args=list()
                if timer and timereal:
                    cmd='./'+execname
                    os.environ['CHPL_LAUNCHER_REAL_WRAPPER'] = timer
                elif timer:
                    cmd=timer
                    args+=['./'+execname]
                elif valgrindbin:
                    cmd=valgrindbin
                    args+=valgrindbinopts+['./'+execname]
                else:
                    cmd='./'+execname

                # if we're using a launchcmd, build up the command to call
                # launchcmd, and have it run the cmd and args built above
                if launchcmd:
                    # have chpl_launchcmd time execution and place results in a
                    # file since sub_test time will include time to get reservation
                    launchcmd_exec_time_file = execname + '_launchcmd_exec_time.txt'
                    os.environ['CHPL_LAUNCHCMD_EXEC_TIME_FILE'] = launchcmd_exec_time_file

                    # save old cmd and args and add them after launchcmd args.
                    oldcmd = cmd
                    oldargs = list(args)
                    launch_cmd_list = shlex.split(launchcmd)
                    cmd = launch_cmd_list[0]
                    args = launch_cmd_list[1:]
                    args += [oldcmd]
                    args += oldargs

                args+=globalExecopts
                args+=shlex.split(execopts)
                # envExecopts are meant for chpl programs, dont add them to C tests
                if not is_c_test and envExecopts != None:
                    args+=shlex.split(envExecopts)
                if lastexecopts:
                    args += lastexecopts

                if len(args) >= 2 and '<' in args:
                  redirIdx = args.index('<')
                  execOptRedirect = args[redirIdx + 1]
                  args.pop(redirIdx+1)
                  args.pop(redirIdx)
                  if redirectin == None:
                      # It is a little unfortunate that we compile the test only to skip it here.
                      # In order to prevent this, the logic for combining all the places execpopts
                      # come from and checking for '<' would have to be factored out or duplicated
                      print('[Skipping test with stdin redirection ("<") in execopts since '
                            '-nostdinredirect is given {0}/{1}]'.format(localdir, test_filename))
                      break;
                  elif redirectin == "/dev/null":
                    if os.access(execOptRedirect, os.R_OK):
                      redirectin = execOptRedirect
                      redirectin_set_in_loop = True
                    else:
                      sys.stdout.write('[Error: redirection file %s does not exist]\n'%(execOptRedirect))
                      break
                  else:
                    sys.stdout.write('[Error: a redirection file already exists: %s]\n'%(redirectin))
                    break

                #
                # Run program (with timeout)
                #
                for count in xrange(numTrials):
                    exec_limiter = execution_limiter.NoLock()
                    if os.getenv("CHPL_TEST_LIMIT_RUNNING_EXECUTABLES") is not None:
                        exec_name = os.path.join(localdir, test_filename)
                        exec_limiter = execution_limiter.FileLock(exec_name, timeout)

                    with exec_limiter:
                        exectimeout = False  # 'exectimeout' is specific to one trial of one execopt setting
                        launcher_error = ''  # used to suppress output/timeout errors whose root cause is a launcher error
                        sys.stdout.write('[Executing program %s %s'%(cmd, ' '.join(args)))
                        if redirectin:
                            sys.stdout.write(' < %s'%(redirectin))
                        sys.stdout.write(']\n')
                        sys.stdout.flush()

                        execStart = time.time()
                        if useLauncherTimeout:
                            if redirectin == None:
                                my_stdin = None
                            else:
                                my_stdin=file(redirectin, 'r')
                            test_command = [cmd] + args + LauncherTimeoutArgs(timeout)
                            p = subprocess.Popen(test_command,
                                                env=dict(os.environ.items() + testenv.items()),
                                                stdin=my_stdin,
                                                stdout=subprocess.PIPE,
                                                stderr=subprocess.STDOUT)
                            output = p.communicate()[0]
                            status = p.returncode

                            if re.search('slurmstepd: Munge decode failed: Expired credential', output, re.IGNORECASE) != None:
                                launcher_error = 'Jira 18 -- Expired slurm credential for'
                            elif re.search('output file from job .* does not exist', output, re.IGNORECASE) != None:
                                launcher_error = 'Jira 17 -- Missing output file for'
                            elif re.search('aprun: Unexpected close of the apsys control connection', output, re.IGNORECASE) != None:
                                launcher_error = 'Jira 193 -- Unexpected close of apsys for'
                            elif (re.search('PBS: job killed: walltime', output, re.IGNORECASE) != None or
                                  re.search('slurm.* CANCELLED .* DUE TO TIME LIMIT', output, re.IGNORECASE) != None):
                                exectimeout = True
                                launcher_error = 'Timed out executing program'

                            if launcher_error:
                                sys.stdout.write('%s[Error: %s %s/%s'%
                                                (futuretest, launcher_error, localdir, test_filename))
                                printTestVariation(compoptsnum, compoptslist,
                                                   execoptsnum, execoptslist);
                                sys.stdout.write(']\n')
                                sys.stdout.write('[Execution output was as follows:]\n')
                                sys.stdout.write(trim_output(output))

                        elif useTimedExec:
                            wholecmd = cmd+' '+' '.join(map(ShellEscape, args))

                            if redirectin == None:
                                my_stdin = sys.stdin
                            else:
                                my_stdin = file(redirectin, 'r')
                            p = subprocess.Popen([timedexec, str(timeout), wholecmd],
                                                env=dict(os.environ.items() + testenv.items()),
                                                stdin=my_stdin,
                                                stdout=subprocess.PIPE,
                                                stderr=subprocess.STDOUT)
                            output = p.communicate()[0]
                            status = p.returncode

                            if status == 222:
                                exectimeout = True
                                sys.stdout.write('%s[Error: Timed out executing program %s/%s'%
                                                (futuretest, localdir, test_filename))
                                printTestVariation(compoptsnum, compoptslist,
                                                   execoptsnum, execoptslist);
                                sys.stdout.write(']\n')
                                sys.stdout.write('[Execution output was as follows:]\n')
                                sys.stdout.write(trim_output(output))
                            else:
                                # for perf runs print out the 5 processes with the
                                # highest cpu usage. This should help identify if other
                                # processes might have interfered with a test.
                                if perftest:
                                    print('[Reporting processes with top 5 highest cpu usages]')
                                    sys.stdout.flush()
                                    psCom = 'ps ax -o user,pid,pcpu,command '
                                    subprocess.call(psCom + '| head -n 1', shell=True)
                                    subprocess.call(psCom + '| tail -n +2 | sort -r -k 3 | head -n 5', shell=True)


                        else:
                            if redirectin == None:
                                my_stdin = None
                            else:
                                my_stdin=file(redirectin, 'r')
                            p = subprocess.Popen([cmd]+args,
                                                env=dict(os.environ.items() + testenv.items()),
                                                stdin=my_stdin,
                                                stdout=subprocess.PIPE,
                                                stderr=subprocess.STDOUT)
                            try:
                                output = SuckOutputWithTimeout(p.stdout, timeout)
                            except ReadTimeoutException:
                                exectimeout = True
                                sys.stdout.write('%s[Error: Timed out executing program %s/%s'%
                                                (futuretest, localdir, test_filename))
                                printTestVariation(compoptsnum, compoptslist,
                                                   execoptsnum, execoptslist);
                                sys.stdout.write(']\n')
                                KillProc(p, killtimeout)

                            status = p.returncode

                    # executable is done running

                    elapsedExecTime = time.time() - execStart
                    test_name = os.path.join(localdir, test_filename)
                    compExecStr = ''
                    if compoptsnum != 0:
                        compExecStr += 'compopts: {0} '.format(compoptsnum)
                    if execoptsnum != 0:
                        compExecStr += 'execopts: {0}'.format(execoptsnum)
                    if compExecStr:
                        test_name += ' ({0})'.format(compExecStr.strip())

                    if launchcmd and os.path.exists(launchcmd_exec_time_file):
                        with open(launchcmd_exec_time_file, 'r') as fp:
                            try:
                                launchcmd_exec_time = float(fp.read())
                                print('[launchcmd reports elapsed execution time '
                                    'for "{0}" - {1:.3f} seconds]'
                                    .format(test_name, launchcmd_exec_time))
                            except ValueError:
                                print('Could not parse launchcmd time file '
                                    '{0}'.format(launchcmd_exec_time_file))
                        os.unlink(launchcmd_exec_time_file)

                    print('[Elapsed execution time for "{0}" - {1:.3f} '
                        'seconds]'.format(test_name, elapsedExecTime))

                    if execTimeWarnLimit and elapsedExcTime > execTimeWarnLimit:
                        sys.stdout.write('[Warning: %s/%s took over %.0f seconds to '
                            'execute]\n' %(localdir, test_filename, execTimeWarnLimit))

                    if catfiles:
                        sys.stdout.write('[Concatenating extra files: %s]\n'%
                                        (test_filename+'.catfiles'))
                        sys.stdout.flush()
                        output+=subprocess.Popen(['cat']+catfiles.split(),
                                                stdout=subprocess.PIPE,
                                                stderr=subprocess.STDOUT).communicate()[0]

                    # Sadly the scripts used below require an actual file
                    with open(execlog, 'w') as execlogfile:
                        execlogfile.write(pre_exec_output)
                        execlogfile.write(output)

                    if not exectimeout and not launcher_error:
                        if systemPrediff:
                            sys.stdout.write('[Executing system-wide prediff]\n')
                            sys.stdout.flush()
                            sys.stdout.write(subprocess.Popen([systemPrediff,
                                                              execname,execlog,compiler,
                                                              ' '.join(envCompopts)+
                                                              ' '+compopts,
                                                              ' '.join(args)],
                                                              stdout=subprocess.PIPE,
                                                              stderr=subprocess.STDOUT).
                                            communicate()[0])

                        if globalPrediff:
                            sys.stdout.write('[Executing ./PREDIFF]\n')
                            sys.stdout.flush()
                            sys.stdout.write(subprocess.Popen(['./PREDIFF',
                                                              execname,execlog,compiler,
                                                              ' '.join(envCompopts)+
                                                              ' '+compopts,
                                                              ' '.join(args)],
                                                              stdout=subprocess.PIPE,
                                                              stderr=subprocess.STDOUT).
                                            communicate()[0])

                        if prediff:
                            sys.stdout.write('[Executing prediff ./%s]\n'%(prediff))
                            sys.stdout.flush()
                            sys.stdout.write(subprocess.Popen(['./'+prediff,
                                                              execname,execlog,compiler,
                                                              ' '.join(envCompopts)+
                                                              ' '+compopts,
                                                              ' '.join(args)],
                                                              stdout=subprocess.PIPE,
                                                              stderr=subprocess.STDOUT).
                                            communicate()[0])

                        if not perftest:
                            # find the good file

                            basename = test_filename
                            commExecNum = ['']

                            # if there were multiple compopts/execopts find the
                            # .good file that corresponds to that run
                            if not onlyone:
                                commExecNum.insert(0,'.'+str(compoptsnum)+'-'+str(execoptsnum))

                            # if the .good file was explicitly specified, look for
                            # that version instead of the multiple
                            # compopts/execopts or just the base .good file
                            if explicitexecgoodfile != None:
                                basename  = explicitexecgoodfile.replace('.good', '')
                                commExecNum = ['']

                            execgoodfile = FindGoodFile(basename, envCompopts, commExecNums=commExecNum)

                            if not os.path.isfile(execgoodfile) or not os.access(execgoodfile, os.R_OK):
                                sys.stdout.write('[Error cannot locate program output comparison file %s/%s]\n'%(localdir, execgoodfile))
                                sys.stdout.write('[Execution output was as follows:]\n')
                                exec_output = subprocess.Popen(['cat', execlog],
                                    stdout=subprocess.PIPE).communicate()[0]
                                sys.stdout.write(trim_output(exec_output))

                                continue # on to next execopts

                            result = DiffFiles(execgoodfile, execlog)
                            if result==0:
                                os.unlink(execlog)
                                sys.stdout.write('%s[Success '%(futuretest))
                            else:
                                sys.stdout.write('%s[Error '%(futuretest))
                            sys.stdout.write('matching program output for %s/%s'%
                                            (localdir, test_filename))
                            if result!=0:
                                printTestVariation(compoptsnum, compoptslist,
                                                   execoptsnum, execoptslist);
                            sys.stdout.write(']\n')

                            if (result != 0 and futuretest != ''):
                                badfile=test_filename+'.bad'
                                if os.access(badfile, os.R_OK):
                                    badresult = DiffFiles(badfile, execlog)
                                    if badresult==0:
                                        os.unlink(execlog);
                                        sys.stdout.write('[Clean match against .bad file ')
                                    else:
                                        # bad file doesn't match, which is bad
                                        sys.stdout.write('[Error matching .bad file ')
                                    sys.stdout.write('for %s/%s'%(localdir, test_filename))
                                    printTestVariation(compoptsnum, compoptslist);
                                    sys.stdout.write(']\n');


                    if perftest:
                        if not os.path.isdir(perfdir) and not os.path.isfile(perfdir):
                            os.makedirs(perfdir)
                        if not os.access(perfdir, os.R_OK|os.X_OK):
                            sys.stdout.write('[Error creating performance test directory %s]\n'%(perfdir))
                            break # on to next compopts

                        if explicitexecgoodfile==None:
                            perfexecname = test_filename
                            keyfile = PerfTFile(test_filename,'keys') #e.g. .perfkeys
                        else:
                            perfexecname = re.sub(r'\{0}$'.format(PerfSfx('keys')), '', explicitexecgoodfile)
                            if os.path.isfile(explicitexecgoodfile):
                                keyfile = explicitexecgoodfile
                            else:
                                keyfile = PerfTFile(test_filename,'keys')

                        perfdate = os.getenv('CHPL_TEST_PERF_DATE')
                        if perfdate == None:
                            perfdate = datetime.date.today().strftime("%m/%d/%y")

                        sys.stdout.write('[Executing %s/test/computePerfStats %s %s %s %s %s %s]\n'%(utildir, perfexecname, perfdir, keyfile, execlog, str(exectimeout), perfdate))
                        sys.stdout.flush()

                        p = subprocess.Popen([utildir+'/test/computePerfStats',
                                              perfexecname, perfdir, keyfile, execlog, str(exectimeout), perfdate],
                                             stdout=subprocess.PIPE)
                        sys.stdout.write('%s'%(p.communicate()[0]))
                        sys.stdout.flush()

                        status = p.returncode
                        if not exectimeout and not launcher_error:
                            if status == 0:
                                os.unlink(execlog)
                                sys.stdout.write('%s[Success '%(futuretest))
                            else:
                                sys.stdout.write('%s[Error '%(futuretest))
                            sys.stdout.write('matching performance keys for %s/%s'%
                                            (localdir, test_filename))
                            if status!=0:
                                printTestVariation(compoptsnum, compoptslist,
                                                   execoptsnum, execoptslist);
                            sys.stdout.write(']\n')

                        if exectimeout or status != 0:
                            break

            cleanup(execname)

        del execoptslist
        del compoptslist

        elapsedCurFileTestTime = time.time() - curFileTestStart
        test_name = os.path.join(localdir, test_filename)
        print('[Elapsed time to compile and execute all versions of "{0}" - '
            '{1:.3f} seconds]'.format(test_name, elapsedCurFileTestTime))


    sys.exit(0)


if __name__ == '__main__':

    args = parse_args()

    main(args.compiler)
