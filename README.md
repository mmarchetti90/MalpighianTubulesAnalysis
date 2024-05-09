# Adult *D. melanogaster* Malpighian tubules analysis pipeline

This pipeline will analyzed cross-sectional tiff live-imaging movies of Malpighian tubules from adult *D. melanogaster*. Measurements of tubule, lumen, and cell width across time are output to a tab-delimited text file.

The pipeline is designed to be run on High Performance Computing (HPC) systems using the Slurm Workload Manager. Tasks are parallelized thanks to the Nextflow workflow system and the pipeline uses Docker containers to enhance reproducibility and portability.

The pipeline was developed for Dr. Aylin Rodan's lab at the Eccles Institute of Human Genetics, University of Utah.

/// ---------------------------------------- ///

## Overview:

The pipeline will process tiff movies using the following steps:

* Background removal using a no-neighbor deblurring algorithm (OPTIONAL).

* Masking via brute-force thresholding until 3 areas can be defined corresponding to the tubule lumen and background areas on either side of the tubule (OPTIONAL).

* Process each time point as follows:

    * Define centroids that best describe the profile of the lumen once connected.

    * Measure tubule, lumen, and cell width at 100 points along the lumen, then average measurements.

* Report each time-point measurements in a table.

/// ---------------------------------------- ///

## SETUP:

1. Clone Github repo.

```
git clone https://github.com/mmarchetti90/MalpighianTubulesAnalysis.git
```

2. Make sure that Nextflow and your container platform of choice (Docker, Podman, or Singularity) are installed. If using Lmod, load the necessary modules: *e.g.*

```
module load docker java nextflow 
```

3. Modify the config file (nextflow.config):

* Set the container path

* Set clusterOptions parameters according to your HPC settings

4. Run pipeline on input data.

```
nextflow run main.nf -profile singularity --sample_table_path </path/to/file>
```

/// ---------------------------------------- ///

## INPUT:

The pipeline reads samples' info from a tab-delimited file.
The file has the following columns:

* **sample_id**: unique sample identifier

* **file_path**: full path to tiff movie

* **scale**: scale used to convert pixels measurements, expressed as unit/pixel (set to 1 if unknown)

* **options**: options to be passed to the analysis algorithm

Possible options are:

* --make_mask : thresholds the image and generates a mask

* --make_mask --remove_background : cleans up the image, then thresholds it and generates a mask

Options field can also be left empty if none of the above is desired.

/// ---------------------------------------- ///

## OUTPUTS:

All data is saved to a local analysis_results folder which has the following structure:

<pre>
<b>analysis_results</b>
│
└── <b>sample_1_id</b>
|   │
|   ├── <b>sample_1_id_clean.zip_</b>
|   │   Tiff file of the movie after cleaning with no-neighbor deblurring.
|   │   Only available if the --remove_background option is specified.
|   │
|   ├── <b>sample_1_id_mask.zip</b>
|   │   Mask of the tubule, where 0 = tubule cells, 1-2 = background outside the tubule, 3 = lumen.
|   │   Only available if the --make_mask option is specified.
|   │
|   ├── <b>sample_1_id_measurements.tsv</b>
|   │   Measurements of tubule, lumen, and cell width across time.
|   │
|   ├── <b>sample_1_id_measurements_raw.png</b>
|   │   Plot of measurements across time.
|   │
|   └── <b>sample_1_id_measurements_normalized.png</b>
|       Plot of measurements across time, normalized to 0-1 scale.
|
└── <b>sample_n_id</b>
</pre>

/// ---------------------------------------- ///

## DEPENDENCIES:

* Nextflow 23.10.1+

* Container platform, one of
    * Docker 20.10.21+
    * Podman
    * Singularity 3.8.5+

* Slurm
