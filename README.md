![Chapel](http://chapel.cray.com/images/cray-chapel-logo-650.png)

[Website](http://chapel.cray.com/) |
[Documentation](http://chapel.cray.com/docs/master/) |
[Mailing List](https://sourceforge.net/p/chapel/mailman/?source=navbar) |
[#chapel](http://webchat.freenode.net/?channels=chapel) |
[Learning Chapel](http://chapel.cray.com/learning.html) |
[Twitter](https://twitter.com/ChapelLanguage) |
[Performance Tracking](http://chapel.sourceforge.net/perf/)


[![Build Status](https://travis-ci.org/chapel-lang/chapel.svg?branch=master)](https://travis-ci.org/chapel-lang/chapel)
[![Coverity Scan Build](https://scan.coverity.com/projects/1222/badge.svg)](https://scan.coverity.com/projects/chapel)
[![Apache licensed](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](./LICENSE.chapel)
[![Release](https://img.shields.io/badge/release-v1.13.0-blue.svg)](https://github.com/chapel-lang/chapel/releases/tag/1.13.0)


# The Chapel Language

Chapel is an emerging programming language designed for productive parallel
computing at scale.

## Features of Chapel

* High productivity
* High performance
* Native parallelism
* Data and task locality
* Multiresolution philosophy
* Robust interoperability

Learn more about the language features `[here]`

## Quick Start Instructions

Building Chapel from source is the preferred method of installation, although
some packages do exist. For most users, the build process consists of checking
a copy of Chapel from the git repository or downloading the release tarball,
entering the `chapel/` directory, invoking `make`, and adding
`chapel/bin/<arch>/` to their `$PATH`:

    cd chapel/

    # Build compiler in parallel
    make -j

    # Script that sets up environment variables, most importantly $PATH
    source util/setchplenv.bash

    # Confirm build succeeded
    make check

For more comprehensive build instructions, prerequisites, and information on
available of packages, see `[quick start instructions]`.


## Language Highlights

`[some code snippets of Chapel demonstrating some key features]`

`[direct links to some useful tests (primers, etc.) for getting started]`

## Where to next?

`[links to useful places]`

