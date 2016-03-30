#!/bin/sh

# A counterpart for modules/internal/fixInternalDocs.sh
# for modules/dists, modules/layouts.

# NOTE:
# This script _should_ eventually go away entirely as chpldoc improves.
# For now, we'll use common unix utilities to achieve a cleaner result.

if [ $# -ne 1 ]; then
  echo "Error: This script takes one argument, the path of the intermediate sphinx project"
  exit 1
fi

if [ ! -d "$1" ]; then
  echo "Error: Unable to find directory $1."
  exit 2
fi

process "../layouts/LayoutCSR.rst"
process "BlockDist.rst"
process "CyclicDist.rst"
process "BlockCycDist.rst"
process "ReplicatedDist.rst"
process "PrivateDist.rst"
process "DimensionalDist2D.rst"
process "dims/ReplicatedDim.rst"
process "dims/BlockDim.rst"
process "dims/BlockCycDim.rst"

function process() {

  rst=$1

  # Extract module name from file name

  # Confirm files exists

   # Print all lines until the one after the module name heading,
   # which is the underline.

   # Skip everything until "class::", edit that line and print.

   # Print until a chpldoc line for the next declaration.

}
