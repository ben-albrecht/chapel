#!/usr/bin/env python
# encoding: utf-8

from __future__ import print_function

import glob
import logging
import os
import shlex
import shutil
from subprocess import Popen, PIPE
import time

from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter


def get_arguments(args=None):
    parser = ArgumentParser(prog='gen_release.py',
                            usage='%(prog)s [options] ',
                            description=''' %(prog)s generates a release
                                            tarball for Chapel''',
                            formatter_class=ArgumentDefaultsHelpFormatter
                            )
    parser.add_argument('--verbose', '-v', action='store_true',
                        default=False, help='Debug messages')
    parser.add_argument('--workspace', default=None,
                        help="""If set, the current CHPL_HOME will be copied to
                        this path to use as the workspace for creating the
                        tarball, rather than cloning a fresh copy.""")
    parser.add_argument('--repo', default='https://github.com/chapel-lang/chapel',
                        help='Chapel repository URL if cloning')
    parser.add_argument('--branch', default='master', help='Chapel branch')

    opts = parser.parse_args(args)

    return opts


def loggingconfig(verbose=False):
    if verbose:
        loglevel=logging.DEBUG
    else:
        loglevel=logging.INFO

    logging.basicConfig(level=loglevel)


def ignorepath(ipath):
    def ignoref(p, files):
        return (f for f in files if os.abspath(os.path.join(p, f)) == ipath)
    return ignoref


def ignorefiles(ifiles):
    def ignoref(p, files):
        return (f for f in files if f in ifiles)
    return ignoref


def run(cmd, cwd=None):
    """Run command"""
    args = shlex.split(cmd)
    p = Popen(args, stdout=PIPE, stderr=PIPE, cwd=cwd)
    out, err = (x.decode() for x in p.communicate())
    return out, err


def main(verbose=False, workspace=None, repo='https://github.com/chapel-lang/chapel', branch='master'):

    # Initial setup
    loggingconfig(verbose=verbose)

    buildRelease = os.path.abspath(os.path.dirname(__file__))

    # Find CHPL_HOME, if unset, use root of repo relative to this script
    if os.environ.has_key('CHPL_HOME'):
        chpl_home = os.environ['CHPL_HOME']
        logging.info('Chapel home found from $CHPL_HOME')
    else:
        chpl_home = os.path.dirname(os.path.dirname(buildRelease))
        logging.info("$CHPL_HOME is not set")
        logging.info('Chapel home found by relative path')


    # Depending on workspace argument provided, setup workspace in some way:
    #if opts.workspace:
    #    workspace=opts.workspace
    #    if workspace != chpl_home:
    #        # Copy (cp -r) current $CHPL_HOME
    #        if not os.path.isdir(workspace):
    #            os.mkdir(workspace)
    #    else:
    #        # Use current $CHPL_HOME
    #        logging.error('Not yet implemented')

    #else:
    workspace=os.path.join(chpl_home, 'tar')
    source = os.path.join(workspace, 'chapel')

    # Wipe directories in workspace
    if os.path.isdir(source):
        shutil.rmtree(source)

    if not opts.workspace:
        #   Checkout a fresh copy of Chapel
        cmd='git clone --depth=1 --branch={0} {1} {2}'.format(branch, repo, source)
        out, err = run(cmd)


        logging.info('Cloning Chapel into {0}'.format(source))
        logging.info(cmd)

        start = time.time()
        # Fastest method of cloning a fresh copy of Chapel (~90 seconds)
        logging.debug('Cloned Chapel in ${0} seconds'.format(time.time() - start))

        logging.info(out.decode())
        logging.info(err.decode())


    # Files to include
    files= [
        'ACKNOWLEDGEMENTS',
        'CHANGES',
        'CONTRIBUTORS',
        'COPYRIGHT',
        'GOALS',
        'LICENSE',
        'LICENSE.chapel',
        'Makefile',
        'PERFORMANCE',
        'README.rst',
        'README.files',
        'STATUS',
        'compiler/passes/reservedSymbolNames',
        'etc/README.md',
        'util/README',
        'util/build_configs.py',
        'util/printchplenv',
        'util/setchplenv.bash',
        'util/setchplenv.csh',
        'util/setchplenv.fish',
        'util/setchplenv.sh',
        'util/start_test',
        'util/chpltags'
        ]

    # C/C++ sources
    code_dirs = ['compiler']

    complete_dirs = [
        'compiler/etc',
        'doc',
        'etc/emacs',
        'etc/source-highlight',
        'etc/vim',
        'examples',
        'make',
        'man/man1',
        'modules',
        'modules-ipe',
        'runtime',
        'third-party',
        'util/chplenv',
        'util/config',
        'util/quickstart',
        'util/test',
        'tools'
        ]


    archive = os.path.join(workspace, 'chapel-release')

    logging.info('Setting CHPL_HOME to: ' + source)
    os.environ['CHPL_HOME'] = source
    logging.info('Setting CHPL_COMM to none')
    os.environ['CHPL_COMM'] = 'none'

    # Build docs
    logging.info('Building docs')
    out, err = run('make -j docs', source)
    logging.info(out)

    html = os.path.join(source, 'doc', 'sphinx', 'build', 'html')
    docrelease = os.path.join(source, 'doc', 'release', 'html')
    shutil.copytree(html, docrelease)

    out, err = run('make clobber', source)
    logging.info(out)

    # Extract examples from test
    logging.info('Creating examples directory')
    examples = os.path.join(source, 'test', 'release', 'examples')
    shutil.copytree(examples, os.path.join(source, 'examples'))

    start_test = os.path.join(source, 'util', 'start_test')
    shutil.copy(start_test, os.path.join(source, 'examples', 'start_test'))

    cmd = 'python util/devel/test/extract_tests --no-futures -o examples/spex spec/*.tex'
    out, err = run(cmd, cwd=source)
    logging.info(out)

    # make man-pages
    out, err = run('make man', cwd=source)
    logging.info(out)
    out, err = run('make man-chpldoc', cwd=source)
    logging.info(out)

    # make STATUS
    out, err = run('make STATUS', cwd=source)
    logging.info(out)

    # Move docs
    shutil.move(os.path.join(source, 'doc'), os.path.join(source,'doctmp'))
    shutil.move(os.path.join(source, 'doctmp', 'release'), os.path.join(source, 'doc'))
    shutil.rmtree(os.path.join(source, 'doctmp'))

    # Prune Makefiles
    os.remove(os.path.join(source, 'make', 'platform', 'Makefile.sunos_old'))
    shutil.rmtree(os.path.join(source, 'compiler', 'include', 'sunos_old'))
    shutil.rmtree(os.path.join(source, 'runtime', 'src', 'launch', 'dummy'))
    shutil.rmtree(os.path.join(source, 'runtime', 'src', 'launch', 'mpirun'))
    shutil.rmtree(os.path.join(source, 'runtime', 'include', 'sunos_old'))
    shutil.rmtree(os.path.join(source, 'third-party', 'txt2man'))

    thirdparty = os.path.join(source, 'third-party')
    develfiles = glob.glob(os.path.join(thirdparty, "*.devel*"))
    print(develfiles)
    for develfile in develfiles:
        os.remove(develfile)

    # Update permissions
    # chmod -R ugo+rX workspace
    # chmod -R go-w workspace

    # Copy files over
    # Copy code_dirs over
    # Copy complete_dirs over

    # Create tar dir?

    # Create tarball

if __name__ == '__main__':
    opts = get_arguments()
    main(verbose=opts.verbose, workspace=opts.workspace, repo=opts.repo, branch=opts.branch)
