#!/usr/bin/env bash
#
# Test CHPL_TARGET_COMPILER=mpi-gnu on test/release/example + MPI module tests
#
# CHPL_TARGET_COMPILER=mpi-gnu
# CHPL_TASKS=fifo
# CHPL_COMM=gasnet
# CHPL_COMM_SUBSTRATE=mpi

CWD=$(cd $(dirname $0) ; pwd)
source $CWD/common.bash
source $CWD/common-mpicc.bash

export CHPL_NIGHTLY_TEST_CONFIG_NAME="mpicc"

nightly_args="${nightly_args}"
$CWD/nightly -cron ${nightly_args}
