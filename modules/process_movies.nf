process ProcessMovies {

    label 'processing'

    publishDir "${projectDir}/analysis_results/${sample_id}", mode: "copy", pattern: "*.tif"
    publishDir "${projectDir}/analysis_results/${sample_id}", mode: "copy", pattern: "*.tsv"
    publishDir "${projectDir}/analysis_results/${sample_id}/plots", mode: "copy", pattern: "*.png"

    input:
    each path(scripts_dir)
    tuple val(sample_id), path(movie), val(scale), val(measurements_spacing), val(options)

    output:
    path "*_clean.tif", optional: true, emit: cleaned_movie
    path "*_mask.tif", optional: true, emit: masked_movie
    path "*_mask-diagnostics.tif", optional: true, emit: mask_diagnostics
    path "*_measurements-diagnostics.tif", emit: measurements_diagnostics
    path "*_measurements.tsv", emit: measurements
    path "*_thresholds.tsv", optional: true, emit: thresholds
    path "*.png", emit: plots

    """
    python ${scripts_dir}/dmel_tubule_analysis.py \
    --sample_name ${sample_id} \
    --movie ${movie} \
    --scale ${scale} \
    --measurements_spacing ${measurements_spacing} \
    ${options}
    """

}