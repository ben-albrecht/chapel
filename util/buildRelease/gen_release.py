#!/usr/bin/env python
# encoding: utf-8

from __future__ import print_function

import logging
import os

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

    opts = parser.parse_args(args)

    return opts


def loggingconfig(verbose=False):
    if verbose:
        loglevel=logging.DEBUG
    else:
        loglevel=logging.INFO

    logging.basicConfig(level=loglevel)


def main(verbose=False):

    # Initial setup
    loggingconfig(verbose=verbose)

    buildRelease = os.path.abspath(os.path.dirname(__file__))

    # Find CHPL_HOME, if unset, use root of repo relative to this script
    if os.environ.has_key('CHPL_HOME'):
        chpl_home = os.environ['CHPL_HOME']
        logging.info('Chapel home found from $CHPL_HOME: ' + chpl_home)
    else:
        chpl_home = os.path.dirname(os.path.dirname(buildRelease))
        logging.info("$CHPL_HOME is not set")
        logging.info('Chapel home found by relative path: ' + chpl_home)

    # TODO
    # Depending on argument provided, do one of the following to setup workspace:
    #   Checkout a fresh copy of Chapel
    #   Use current $CHPL_HOME
    #   Copy (cp -r) current $CHPL_HOME

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

    # Set CHPL_HOME to new workspace
    # Set CHPL_COMM to 'none' (necessary?)

    # make -j docs
    # mv doc/sphinx/build/html doc/release
    # make clobber

    # Extract examples from test

    # make man-pages

    # make STATUS

    # Move docs

    # Prune Makefiles

    # Prune compiler directories

    # Prune runtime directories

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
    main(verbose=opts.verbose)
