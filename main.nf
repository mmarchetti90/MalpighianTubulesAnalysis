#!/usr/bin/env nextflow

nextflow.enable.dsl=2

/*
Pipeline to analyze D. melangaster adult Malpighian tubules cross-section movies
*/

// ----------------Workflow---------------- //

include { ProcessMovies } from './modules/process_movies.nf'

workflow {

  // Scripts dir channel
  Channel
    .fromPath("${projectDir}/scripts")
    .set{ scripts_dir }

  // Read samples table
  Channel.fromPath("${params.sample_table_path}")
    .splitCsv(header: true, sep: '\t')
    .map{ row -> tuple(row.sample_id, file(row.file_path), row.scale, row.options) }
    .set{ samples_info }

  // Run processing
  ProcessMovies(scripts_dir, samples_info)

}