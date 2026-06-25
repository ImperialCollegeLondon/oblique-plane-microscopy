#!/bin/sh
#
#  Created by Yuriy Alexandrov
#
## sed -i s/\\r//g dispatcher.slurm ------- fixes DOS end lines

##SBATCH --nodes=1
#SBATCH --mem=128000
#SBATCH --time=6:00:00
##SBATCH --ntasks 1 --cpus-per-task 24

umask 22 # make all files group and world readable

sep=@
channels=012
extension=.tif

work_dir=../
data_dir=../../fused_binning_2
output_dir=$work_dir/output
code_dir=$work_dir/code

ALYtools_dir=/nemo/project/proj-sahaie-frenchp/software/ALYtools

export matlab_job_spec=$job_spec$sep$data_dir$sep$output_dir$sep$ALYtools_dir$sep$channels$sep$extension

module load matlab 

matlab -nodisplay -r "run('$code_dir/process_FOV.m')"

exit
 