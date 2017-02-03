#!/usr/bin/env bash
#
# Test CHPL_COMM=none && CHPL_TARGET_COMPILER=mpi-gnu for MPI module testing
#
# CHPL_TARGET_COMPILER=mpi-gnu
# CHPL_TASKS=fifo
# CHPL_COMM=none

# Setting up MPICH:
# Access MPICH on chapcs:
# module use /usr/share/modules/
# module load modulefiles/mpi
# MPICH_MAX_THREAD_SAFETY=multiple

# TESTS_TO_RUN=test/release/:test/release/modules/packages/MPI/multilocale


CWD=$(cd $(dirname $0) ; pwd)
source $CWD/common.bash

export CHPL_NIGHTLY_TEST_CONFIG_NAME="mpicc"

nightly_args="${nightly_args}"
$CWD/nightly -cron ${nightly_args}
