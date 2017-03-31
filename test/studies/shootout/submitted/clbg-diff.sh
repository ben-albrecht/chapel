#!/bin/bash

# Checkout benchmarks
cvs -d :pserver:anonymous@cvs.debian.org:/cvs/benchmarksgame checkout benchmarksgame/bench/

for chpl in `ls *.chpl`; do
    basename=$(echo ${chpl} | sed 's/.chpl//')
    # if number, do fancy stuff 
    chapel=${basename}.chapel
    if [ -f benchmarksgame/bench/${basename}/${chapel} ]; then
        echo "diff ${chapel} ${chpl}"
        diff benchmarksgame/bench/${basename}/${chapel} ${chpl}
    else
        echo "benchmarksgame/bench/${basename}/${chapel} not found"
    fi
done



