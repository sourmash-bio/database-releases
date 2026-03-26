"""
#### Use db zipfile to build add'l release databases ####

To use the 'resources' information in each rule, set up
a snakemake profile for slurm job submission and pass it
into snakemake when running, e.g.

    `snakemake -s release.smk --profile slurm`

These resources represent real values from running
gtdb-rs214, with some padding. If memory limits are
hit and your profile allows job restarts (`restart-times`),
memory will be multiplied by the current attempt number
(e.g. if 3G on 1st attempt, 6G on second, 9G on third).

Resource 'time' is excessive as jobs will exit when finished.
"""
import re

configfile: "config.yml"

NAME = config['name']
TAG = config['tag']
RELEASE_DIR= f"/group/ctbrowngrp/sourmash-db/{NAME}-{TAG}"
KSIZES = config['ksizes']
SCALED = config['scaled']
LCA_JSON_SCALED = config['lca_json_scaled']

# taxonomy info
TAXONOMY_FILE = f"{NAME}-{TAG}.lineages.csv"
REPS_TAXONOMY_FILE = f"{NAME}-{TAG}.lineages.reps.csv"
TAXONOMY_COLNUM = int(config['tax_column'])
TAXONOMY_KEEP_VERSION = bool(config['tax_keep_version'])

LOGS = "logs"

wildcard_constraints:
    filename = "[^/]+"

ZIP_NAMES = expand([f'{NAME}-{TAG}-k{{k}}', f'{NAME}-{TAG}-reps.k{{k}}'], k=KSIZES)

rule all:
    input:
        expand(f"{RELEASE_DIR}/{{filename}}.zip", filename=ZIP_NAMES),
        expand(f"{RELEASE_DIR}/{{filename}}.sbt.zip", filename=ZIP_NAMES),
        expand(f"{RELEASE_DIR}/{{filename}}.lca.json.gz", filename=ZIP_NAMES),


rule build_release_zip:
    input:
        abund_zip="{filename}.abund.zip"
    output:
        f"{RELEASE_DIR}/{{filename}}.zip"
    threads: 1
    resources:
        mem_mb= lambda wildcards, attempt: attempt * 20000, # 214 reps needed <5G; full <14G
        time= 6000,
        partition='bmh',
    log: f"{LOGS}/{{filename}}.release-zip.log"
    benchmark: f"{LOGS}/{{filename}}.release-zip.benchmark"
    shell:
        """
        sourmash sig flatten {input} -o {output} 2> {log}
        """


rule wc_build_sbt:
    message: "Build SBT {wildcards.filename}.sbt.zip."
    input:
        db = "{filename}.abund.zip",
    output:
        sbt = f"{RELEASE_DIR}/{{filename}}.sbt.zip",
    params:
        scaled = SCALED,
    threads: 1
    resources:
        mem_mb=5000, # 5G
        mem_mb= lambda wildcards, attempt: attempt * 60000, # 214 reps needed <10G; full <50G
        time= 6000,
        partition='bmh',
    log: f"{LOGS}/{{filename}}.release-sbt.log"
    benchmark: f"{LOGS}/{{filename}}.release-sbt.benchmark"
    shell: 
        """
        sourmash index {output.sbt} {input.db} --scaled={params.scaled} 2> {log}
        """

rule wc_build_lca:
    message: "Build LCA {wildcards.filename}.lca.json.gz"
    input:
        db = "{filename}.abund.zip",
    output:
        lca_db = f"{RELEASE_DIR}/{{filename}}.lca.json.gz",
    params:
        tax = lambda w: REPS_TAXONOMY_FILE if 'reps' in w.filename else TAXONOMY_FILE,
        colnum = TAXONOMY_COLNUM,
        keep_ident_version = "--keep-identifier-v" if TAXONOMY_KEEP_VERSION else "",
        scaled = LCA_JSON_SCALED,
        ksize = lambda w: re.search(r'k(\d+)', w.filename).group(1),
    threads: 1
    resources:
        mem_mb= lambda wildcards, attempt: attempt * 35000, # 214 reps needed <12G; full <30G
        time= 6000,
        partition='bmh',
    log: f"{LOGS}/{{filename}}.release-lca.log"
    benchmark: f"{LOGS}/{{filename}}.release-lca.benchmark"
    shell: 
        """
        sourmash lca index {params.tax} {output.lca_db} {input.db} \
           -C {params.colnum} {params.keep_ident_version} \
           --fail-on-missing-taxonomy --split-identifiers --require-taxonomy \
           --scaled={params.scaled} --ksize {params.ksize} 2> {log}
        """

