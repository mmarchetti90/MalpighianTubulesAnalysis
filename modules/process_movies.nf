process ProcessMovies {

    label 'processing'

    publishDir "${projectDir}/analysis_results/${sample_id}", mode: "copy", pattern: "*.zip"
    publishDir "${projectDir}/analysis_results/${sample_id}", mode: "copy", pattern: "*_measurements.tsv"
    publishDir "${projectDir}/analysis_results/${sample_id}", mode: "copy", pattern: "*.png"

    input:
    each path(scripts_dir)
    tuple val(sample_id), path(movie), val(scale), val(options)

    output:
    path "*_clean.zip", optional: true, emit: cleaned_movie
    path "*_mask.zip", optional: true, emit: masked_movie
    path "*_measurements.tsv", emit: measurements
    path "*.png", emit: plots

    """
    python ${scripts_dir}/dmel_tubule_analysis.py \
    --sample_name ${sample_id} \
    --movie ${movie} \
    --scale ${scale} \
    ${options}
    """

}