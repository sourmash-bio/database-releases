# Genbank Database Update Workflow for Sourmash

This repository contains a Snakemake workflow designed to update the existing genbank sourmash databases. 

This workflow supports parallelization, dynamic (efficient) resource allocation, sub-sample testing, and error handling with automated notifications on completion or failures.

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
  - `output_directory`: The absolute path to your existing output directory for generated files.
    - The output path `/group/ctbrowngrp4/2024-ccbaumler-genbank` will automatically create a sub-directory `genbank-{UPDATE-TO-DATE}`.
  - `domains`: Domains of organisms (e.g. bacteria, archaea) to update as Genbank database.
  - `k_values`: The k-mer sizes to use for Sourmash.
    - Default values for sourmash are 21, 31, 51.
  - `update_to_date`: The date of the Genbank update you want to use.
    - Caution: The genbank metadata will be downloaded at the date of running the workflow. This parameter is mostly used for an existing update that must be re-run and already contains the metadata (e.g. assembly summary, assembly historical)
  - `update_from_date`: The previous update date for fetching historical data.
    - Note: Look in the `/group/ctbrowngrp/sourmash-db` directory for last date.
  - `email`: Your email to receive notifications about the status of the workflow.
    - If an email is provided, the workflow will send an email if it encounters an error or when it finishes successfully
  - `scale_value`: The scale parameter for Sourmash sketching.
    - Default value is 1000 for genomes (This may change to 100 for some viruses)

2. Run the workflow:

```
snakemake -s update-genbank.smk -j 15 --use-conda --rerun-incomplete --resources allowed_jobs=100
```
> [!NOTE]
>
> The resources depend greatly on the quantity of new and updating genomes for the database.
> Here is a rough estimate for resource allocation on an HPC:
> CPUs: Request 10 CPUs.
> Memory: Approximately 50 GB.
> Time: 2 days of runtime. 

3. Workflow output:

- Genbank sourmash databases: These ZIP files are the compressed, representative sequence databases for different domains and k-mer sizes.
  - `genbank-20240712-bacteria-k21.zip`
  - `genbank-20240712-bacteria-k31.zip`
  - `genbank-20240712-bacteria-k51.zip`
- Genbank lineage files: These CSV files are the Genbank accession (GCA#), Representative sequence identity (T/F), and Taxonomic lineage by ranks (i.e. 
  - `lineages.bacteria.csv`
- The `data/` directory: This directory contains the TXT and CSV Files used through the workflow (i.e. metadata files).
  - `assembly_summary.bacteria.txt` -- contains data on the current good sequence files in genbank
  - `assembly_summary_historical.bacteria.txt` -- contains data on the current bad sequence files in genbank
  - `collect-mf.2022.03-bacteria.csv` -- sourmash manifest of previous sourmash database
  - `collect-mf.20240712-bacteria.csv` -- sourmash manifest of new sourmash database
  - `genbank-20240712-bacteria.existing.csv` -- all the included sequences in the new sourmash manifest
  - `genbank-20240712-bacteria.missing.csv` -- all the missing sequences from the new sourmash manifest
  - `mf-clean.20240712-bacteria.csv` -- sourmash manifest of all shared sequences between old and new sourmash database
  - `missing-genomes.20240712-bacteria.csv` -- sourmash manifest of all missing sequences for the new sourmash database
  - `missing-genomes.20240712-bacteria.failures.csv` -- sourmash manifest of all the missing sequences that failed to download and sketch into new sourmash database
  - `update-report.20240712-bacteria.txt` -- contains the report for the existing, missing, and updated sequences of the old sourmash database sequences
  - `update.20240712-bacteria.failures.csv` -- sourmash manifest of all the updated sequences that failed to download and sketch into the new sourmash database
  - `updated-versions.20240712-bacteria.csv` -- sourmash manifest of all the updated sequences for the new sourmash database
- The `reports/` directory: This directory contains stand-alone HTML reports summarizing the database generation process.
  - `report.20240712-bacteria.html`
- The `workflow-cleanup` directory: This directory contains CSV files for manually checking sequences and manually downloading failed sequences (View the report files for information on how to handle these files).
  - `manual-check.20240712-bacteria.csv`
  - `manual-download.20240712-bacteria.csv`

> [!NOTE]
>
> The necessary Conda environments are defined in the `envs/` directory, ensuring consistent dependencies for different workflow steps.

## Workflow Rules

Rules to acquire current sourmash databases to update and genbank metadata:
- Fetch the assembly summary files from the NCBI FTP server.
  - download_assembly_summary
  - download_historical_summary
- Link or download the current sourmash data on Farm server.
  - get_ss_db

Rules to preprocess the current sourmash databases:
- Generate a sourmash manifest for the first ksize of each domain database
  - collect_all
- Cleanse the current database manifest and database with custom script
  - cleanse_manifest
    - This script outputs a cleaned manifest and files used by [directsketch](https://github.com/sourmash-bio/sourmash_plugin_directsketch) to download sequences.
  - picklist_clean_db

Rules to gather and sketch new or updated genomes into a new database:
- Gather and sketch any updated or missing sequences into a database utilizing a [sourmash plugin -- directsketch](https://github.com/sourmash-bio/sourmash_plugin_directsketch).
  - gather_sketch_revisioned
  - gather_sketch_missing
- Combine the cleaned sourmash database with the new database.
  - cat_to_clean_reversioned (optional)
  - cat_to_clean_missing

Rules for quality check of the final database:
- Generate a manifest for the completed, merged database and check against the lineage file
  - collect_complete
  - picklist_check
- Generate a set of files to manually gather and sketch any failed sequences
  - make_manual_files

Rules to generate a sourmash lineage file as a companion to the new database:
- Download the taxonomic metadata and custom script
  - download_ncbi_utils
  - download_taxscript
  - download_taxdump
- Generate a lineage file from the current genbank domain
  - make_lineage_csv

Rule to generate a quarto report:
- Generate a report for a breakdown of the workflow results
  - quarto_report

## Why?

Updating databases should be transparent, easy, and possible to generate by anyone.

## Authors

Colton Baumler

[![UC Davis Email](https://img.shields.io/badge/UC_Davis-Email-blue?style=for-the-badge&colorA=blue&colorB=gold)](mailto:ccbaumler@ucdavis.edu) <a href="mailto:ccbaumler@gmail.com"><img src="https://img.shields.io/badge/gmail-%23DD0031.svg?&style=for-the-badge&logo=gmail&logoColor=white"/></a>

