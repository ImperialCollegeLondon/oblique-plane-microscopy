#!/bin/sh
#
#  Created by Yuriy Alexandrov
#

sep=@

set ji=0 #job index

declare -a rows=("B" "C" "D" "E" "F" "G")
declare -a cols=("5" "6" "7" "8")
declare -a tiles=("0" "1" "2" "3" "4" "5" "6" "7" "8" "9")

tp=0

for row in "${rows[@]}"; do \
	for col in "${cols[@]}"; do \
		for tile in "${tiles[@]}"; do \
			export ji=$(($ji+1))				
			sbatch --export job_spec="$ji$sep$tp$sep$row$sep$col$sep$tile" -a $ji dispatcher.slurm
		done
	done
done































