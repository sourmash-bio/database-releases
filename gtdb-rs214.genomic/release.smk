# use the pre-built abund zip to build release databases

configfile: "config.yml"

NAME = config['name']
TAG = config['tag']
KSIZES = config['ksizes']
SCALED = config['scaled']
LCA_JSON_SCALED = config['lca_json_scaled']

# identifier info
#IDENTIFIERS = config['identifiers']
#IDENTIFIER_COL = config['identifier_col']
#IDENTIFIER_TYPE = config['identifier_type']

# taxonomy info
TAXONOMY_FILE = f"{NAME}-{TAG}.lineages.csv"
REPS_TAXONOMY_FILE = f"{NAME}-{TAG}.lineages.reps.csv"
TAXONOMY_COLNUM = int(config['tax_column'])
TAXONOMY_KEEP_VERSION = bool(config['tax_keep_version'])

wildcard_constraints:
    filename = "[^/]+"

ZIP_NAMES = expand([f'{NAME}-{TAG}-k{{k}}', f'{NAME}-{TAG}-reps.k{{k}}'], k=KSIZES)

rule all:
    input:
        expand("releases/{filename}.zip", filename=ZIP_NAMES),
        expand("releases/{filename}.sbt.zip", filename=ZIP_NAMES),
        expand("releases/{filename}.lca.json.gz", filename=ZIP_NAMES),

#rule check:
#    input:
#        expand("releases/{filename}.zip.check", name=NAME, tag=TAG, ksize=KSIZES),
#        expand("releases/{filename}.sbt.zip.check", name=NAME, tag=TAG, ksize=KSIZES),
#        expand("releases/{filename}.lca.json.gz.check", name=NAME, tag=TAG, ksize=KSIZES),


rule build_release_zip:
    input:
        abund_zip="{filename}.abund.zip"
    output:
        "releases/{filename}.zip"
    shell:
        """
        sourmash sig flatten {input} -o {output}
        """


rule wc_build_sbt:
    message: "Build SBT {wildcards.filename}.sbt.zip."
    input:
        db = "{filename}.abund.zip",
    output:
        sbt = "releases/{filename}.sbt.zip",
    params:
        scaled = SCALED,
    shell: 
        """
        sourmash index {output.sbt} {input.db} --scaled={params.scaled}
        """

rule wc_build_lca:
    message: "Build LCA {wildcards.filename}.lca.json.gz"
    input:
        db = "{filename}.abund.zip",
    output:
        lca_db = "releases/{filename}.lca.json.gz",
    params:
        tax = lambda w: REPS_TAXONOMY_FILE if 'reps' in w.filename else TAXONOMY_FILE,
        colnum = TAXONOMY_COLNUM,
        keep_ident_version = "--keep-identifier-v" if TAXONOMY_KEEP_VERSION else "",
        scaled = LCA_JSON_SCALED,
    shell: 
        """
        sourmash lca index {params.tax} {output.lca_db} {input.db} \
           -C {params.colnum} {params.keep_ident_version} \
           --fail-on-missing-taxonomy --split-identifiers --require-taxonomy \
           --scaled={params.scaled}
        """
