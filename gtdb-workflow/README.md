# GTDB Database Update Workflow for Sourmash

This repository contains a Snakemake workflow designed to update the existing GTDB sourmash database.

This workflow supports parallelization, dynamic (efficient) resource allocation, and error handling with automated notifications on completion or on failures.

## Getting Started

Clone the repo:
```
git clone <https or ssh>
```

`cd` into the directory:
```
cd
```

## Usage

This was written for the High-Performance Computing (HPC) cluster at UC Davis. The basic requirements are snakemake and conda to run.

1. Update the configuration file parameters:
  - `email`: Your email to receive notifications about the status of the workflow.
    - If an email is provided, the workflow will send an email if it encounters an error or when it finishes successfully
  - `update_to_release`: The GTDB release the workflow will update to.
    - Caution: The genbank metadata will be downloaded at the date of running the workflow. This metadata will be used to check the validity of the sequences (e.g. assembly summary, assembly historical).
  - `update_from_release`: The GTDB release the workflow will update from.
    - Note: Look in the `/group/ctbrowngrp/sourmash-db` directory for last release.
  - `release_version`: The GTDB versioned release (i.e. 220.1) the workflow should use. (The config is set to use `0` as a default)
  - `output_directory`: The absolute path to your existing output directory for generated files.
    - The output path `/group/ctbrowngrp4/2024-ccbaumler-gtdb` will automatically create a sub-directory `gtdb-{RELEASE}`.
  - `k_values`: The k-mer sizes to use for Sourmash.
    - Default values for sourmash are 21, 31, 51.
  - `scale_value`: The scale parameter for Sourmash sketching.
    - Default value is 1000 for genomes (This may change to 100 for some viruses)
    - Note: While downsampling the scale is trivial, upsampling generally requires re-sketching the entire database.

2. Run the workflow:

```
snakemake -s update-gtdb.smk -j 1 --use-conda --rerun-incomplete --resources allowed_jobs=100
```
> [!NOTE]
>
> The resources depend greatly on the quantity of new and updating genomes for the database.
> Here is a rough estimate for resource allocation on an HPC:
> CPUs: Request 4 CPUs.
> Memory: Approximately 100 GB.
> Time: 5 days of runtime.

3. Workflow output:

- GTDB sourmash databases: These ZIP files are the compressed, representative sequence databases of different k-mer sizes.
  - `gtdb-rs220-k21.zip`
  - `gtdb-rs220-k31.zip`
  - `gtdb-rs220-k51.zip`
  - `gtdb-reps-rs220-k21.zip`
  - `gtdb-reps-rs220-k31.zip`
  - `gtdb-reps-rs220-k51.zip`
- GTDB lineage files: These CSV files are the Genbank accession (GCA#), Representative sequence identity (T/F), and Taxonomic lineage by ranks.
  - `gtdb-rs220.lineages.csv`
  - `gtdb-rs220.lineages.reps.csv`
- The `data/` directory: This directory contains the TXT, TSV, and CSV Files used through the workflow (i.e. metadata files).
  - `ar53_metadata_rs220.tsv` -- contains the archaea metadata for GTDB's release the workflow is updating to
  - `assembly_summary.bacteria.txt` -- contains data on the current good sequence files in genbank for bacteria
  - `assembly_summary_historical.bacteria.txt` -- contains data on the current bad sequence files in genbank for bacteria
  - `assembly_summary.archaea.txt` -- contains data on the current good sequence files in genbank for archaea
  - `assembly_summary_historical.archaea.txt` -- contains data on the current bad sequence files in genbank for archaea
  - `assembly_summary.bac.x.ar.txt` -- contains the combined data on the current good sequence files in genbank for archaea and bacteria
  - `assembly_summary_historical.bac.x.ar.txt` -- contains combined data on the current bad sequence files in genbank for archaea and bacteria
  - `bac120_metadata_rs220.tsv` -- contains the bacteria metadata for GTDB's release the workflow is updating to
  - `collect-mf.214.csv` -- sourmash manifest of previous sourmash database
  - `collect-mf.220.csv` -- sourmash manifest of new sourmash database
  - `gtdb-220.all-missing-links.csv` -- all the genbank links to the missing sequences for the new sourmash database
  - `gtdb-220.clean-existing.csv` -- all the included sequences in the new sourmash manifest from the old sourmash database that have a good status in GenBank (this is a sourmash manifest)
  - `gtdb-220.clean-missing.csv` -- all the missing sequences from the new sourmash manifest from the old sourmash database that have a good status in GenBank (this is a sourmash lineage)
  - `gtdb-220.existing.csv` -- all the included sequences in the new sourmash manifest from the old sourmash database
  - `gtdb-220.missing.csv` -- all the missing sequences from the new sourmash manifest from the old sourmash database
  - `gtdb-220.updated-versions-existing.csv` -- all the genbank links to the updated versions of sequences for the new sourmash database
  - `gtdb-rs220.oldlineages.csv` -- the lineage file for the release the workflow is updating from
  - `gtdb-rs220.oldlineages.reps.csv` -- the representative lineage file for the release the workflow is updating from
  - `report-existing.220.txt` -- contains the report for the kept, updated, and removed sequences of the sequences that exist in both releases
  - `report-missing.220.txt` -- contains the report for the kept, updated, and removed sequences of the sequences that are new and will be added to the new release
- The `reports/` directory: This directory contains stand-alone HTML reports summarizing the database generation process.
  - `report.gtdb-rs{r}.html`
- The `workflow-cleanup` directory: This directory contains CSV files for manually checking sequences and manually downloading failed sequences (View the report files for information on how to handle these files).
  - `manual-check.220.csv`
  - `manual-download.220.csv`
  - `manual-check-reps.220.csv`
  - `manual-download-reps.220.csv`

> [!NOTE]
>
> The necessary Conda environments are defined in the `envs/` directory, ensuring consistent dependencies for different workflow steps.

## Workflow Rules

Rules to acquire current sourmash databases to update and genbank metadata:
- Fetch the GTDB metadata and uncompress them.
  - download_metadata
- Fetch the assembly summary files from the NCBI FTP server.
  - download_assembly_summary
- Link or download the current sourmash data on Farm server.
  - get_ss_db

Rules to preprocess the current sourmash databases:
- Generate a sourmash manifest for the first ksize
  - collect_all
- Split the sourmash manifest into existing sequences in both releases and missing sequences for the newest release
  - picklist_check
- Cleanse the sequences that exist in both database releases from any reversioned or removed sequences with custom script
  - cleanse_existing
    - This script outputs a cleaned manifest and files used by [directsketch](https://github.com/sourmash-bio/sourmash_plugin_directsketch) to download sequences.
- Cleanse the sequences that are missing for the newest release from any reversioned or removed sequences with custom script
  - cleanse_missing
    - This script outputs a cleaned manifest and files used by [directsketch](https://github.com/sourmash-bio/sourmash_plugin_directsketch) to download sequences.

Rules to gather and sketch new or updated genomes into a new database:
- Gather and sketch any updated or missing sequences into a database utilizing a [sourmash plugin -- directsketch](https://github.com/sourmash-bio/sourmash_plugin_directsketch).
  - gather_sketch_existing
  - gather_sketch_missing
- Extract the existing sequences shared by releases
  - extract_db
- Combine the cleaned sourmash databases with the new database.
  - final_db
  - final_db_reps

Rules for quality check of the final database:
- Generate a manifest for the completed, merged database and check against the lineage file
  - final_picklist_check
  - reps_picklist_check
- Generate a set of files to manually gather and sketch any failed sequences
  - make_manual_files

Rules to generate a sourmash lineage file as a companion to the new database:
- Generate the old release's lineage file 
  - make_taxonomy
- Generate a lineage file for the new release
  - make_updated_taxonomy

Rule to generate a quarto report:
- Generate a report for a breakdown of the workflow results
  - quarto_report

## Why?

Updating databases should be transparent, easy, and possible to generate by anyone.

## Authors

Colton Baumler

[![UC Davis Email](https://img.shields.io/badge/UC_Davis-Email-blue?style=for-the-badge&colorA=blue&colorB=gold)](mailto:ccbaumler@ucdavis.edu) <a href="mailto:ccbaumler@gmail.com"><img src="https://img.shields.io/badge/gmail-%23DD0031.svg?&style=for-the-badge&logo=gmail&logoColor=white"/></a>

