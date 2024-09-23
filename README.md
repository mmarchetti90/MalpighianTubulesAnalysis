# Adult *D. melanogaster* Malpighian tubules analysis pipeline

This pipeline will analyzed cross-sectional tiff live-imaging movies of Malpighian tubules from adult *D. melanogaster*. Measurements of tubule, lumen, and cell width and area across time are output to a tab-delimited text file.

The pipeline is designed to be run on a High Performance Computing (HPC) systems using the Slurm Workload Manager. Tasks are parallelized thanks to the Nextflow workflow system and the pipeline uses Docker containers to enhance reproducibility and portability.

The pipeline was developed for Dr. Aylin Rodan's lab at the Eccles Institute of Human Genetics, University of Utah.

/// ---------------------------------------- ///

## Overview:

The pipeline will process tiff movies using the following steps:

* Background removal using a no-neighbor deblurring algorithm (OPTIONAL).

* Masking each time point individually as follows (OPTIONAL):

    * Measure intensities along 4 axis (horizontal, vertical, and two diagonals).

    * Pool measurements and use a Kneedle algorithm to define a threshold.

    * Compute a running average of thresholds across time to mitigate artifacts.

    * Detect and mark 3 areas of the mask corresponding to the tubule lumen and background areas on either side of the tubule.

    * Compare each time point to 4 others (-10, -5, +5, and +10 frames from the time point being processed) to identify and remove vesicles in the lumen (optional, could result in segmentation errors if tubule is moving a lot).

* Process each time point as follows:

    * Find parallel tracts of the lumen edges to define the direction of the tubule.

    * Measure tubule, lumen, and cell width at regular intervals along the tubule, then average measurements.

    * Measure lumen and cell area at regular intervals along the tubule, then average measurements.

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

* **measurements_spacing**: spacing between measurements along the tubule (in microns if scale is specified)

* **options**: options to be passed to the analysis algorithm

Possible options are:

* --make_mask : thresholds the image and generates a mask

* --make_mask --remove_background : cleans up the image, then thresholds it and generates a mask

* --make_mask --vesicles_removal : thresholds the image, aggressively removing vesicles by comparing time-points

* --make_mask --remove_background --vesicles_removal : cleans up the image, thresholds it, generates a mask, and removes vesicles

Options field can also be left empty if none of the above is desired.

/// ---------------------------------------- ///

## OUTPUTS:

All data is saved to a local analysis_results folder which has the following structure:

<pre>
<b>analysis_results</b>
│
└── <b>sample_1_id</b>
|   │
|   ├── <b>sample_1_id_clean.tif</b>
|   │   Tiff file of the movie after cleaning with no-neighbor deblurring.
|   │   Only available if the --remove_background option is specified.
|   │
|   ├── <b>sample_1_id_mask.tif</b>
|   │   Mask of the tubule, where 0 = tubule cells, 1-2 = background outside the tubule, 3 = lumen.
|   │   Only available if the --make_mask option is specified.
|   │
|   ├── <b>sample_1_id_mask-diagnostics.tif</b>
|   │   Multi-channel Tiff overlaying the edges of the mask (red) with the original movie (green).
|   │   Only available if the --make_mask option is specified.
|   │
|   ├── <b>sample_1_measurements-diagnostics.tif</b>
|   │   Diagnostic image showing the lines perpendicular to the lumen that were used for measurements of width.
|   │
|   ├── <b>sample_1_id_measurements.tsv</b>
|   │   Measurements of tubule, lumen, and cell width across time.
|   │
|   ├── <b>sample_1_id_thresholds.tsv</b>
|   │   Thresholds used for each time point.
|   │
|   └──<b>plots</b>
|      │  Folder containing measurements visualizations.
|      │
|      ├── <b>sample_1_id_thresholds.png</b>
|      │   Plot of thresholds measured for each time point (green) with overlaid running average (red).
|      │   Only available if the --remove_background option is specified.
|      │
|      ├── <b>sample_1_id_measurements_raw_width.png</b>
|      │   Plot of raw width measurements across time.
|      │
|      ├── <b>sample_1_id_measurements_raw_width_smoothed.png</b>
|      │   Plot of raw width measurements running average across time.
|      │
|      ├── <b>sample_1_id_measurements_normalized_width.png</b>
|      │   Plot of width measurements across time normalized to a 0-1 range.
|      │
|      ├── <b>sample_1_id_measurements_normalized_width_smoothed.png</b>
|      │   Plot of width measurements running average across time normalized to a 0-1 range.
|      │
|      ├── <b>sample_1_id_measurements_raw_area.png</b>
|      │   Plot of raw area measurements across time.
|      │
|      ├── <b>sample_1_id_measurements_raw_area_smoothed.png</b>
|      │   Plot of raw area measurements running average across time.
|      │
|      ├── <b>sample_1_id_measurements_normalized_area.png</b>
|      │   Plot of area measurements across time normalized to a 0-1 range.
|      │
|      └── <b>sample_1_id_measurements_normalized_area_smoothed.png</b>
|          Plot of area measurements running average across time normalized to a 0-1 range.
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
