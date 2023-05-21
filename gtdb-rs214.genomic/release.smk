# use the pre-built abund zip to build release databases
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
    log: f"LOGS/{{filename}}.release-zip.log"
    benchmark: f"LOGS/{{filename}}.release-zip.benchmark"
    shell:
        """
        sourmash sig flatten {input} -o {output}
        """


rule wc_build_sbt:
    message: "Build SBT {wildcards.filename}.sbt.zip."
    input:
        db = "{filename}.abund.zip",
    output:
        sbt = f"{RELEASE_DIR}/{{filename}}.sbt.zip",
    params:
        scaled = SCALED,
    log: f"LOGS/{{filename}}.release-sbt.log"
    benchmark: f"LOGS/{{filename}}.release-sbt.benchmark"
    shell: 
        """
        sourmash index {output.sbt} {input.db} --scaled={params.scaled}
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
    log: f"LOGS/{{filename}}.release-lca.log"
    benchmark: f"LOGS/{{filename}}.release-lca.benchmark"
    shell: 
        """
        sourmash lca index {params.tax} {output.lca_db} {input.db} \
           -C {params.colnum} {params.keep_ident_version} \
           --fail-on-missing-taxonomy --split-identifiers --require-taxonomy \
           --scaled={params.scaled} --ksize {params.ksize}
        """

