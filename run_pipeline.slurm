#!/bin/bash
#SBATCH --nodes=1
#SBATCH --account=ucgd-rw
#SBATCH --partition=ucgd-rw
#SBATCH -o test_run-out-%j
#SBATCH -e test_run-err-%j

# Loading modules
module load singularity/3.8.5 jdk/11

# Running Nextflow
nextflow_executable=/uufs/chpc.utah.edu/common/HIPAA/u1084359/work_dir/nextflow/nextflow

sample_table_path=/uufs/chpc.utah.edu/common/HIPAA/u1084359/work_dir/20240418_Penalva/0_example_data/test_data_manifest.tsv

${nextflow_executable} run main.nf \
-profile singularity \
--sample_table_path ${sample_table_path}