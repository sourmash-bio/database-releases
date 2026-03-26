###
# This workflow will create a genbank database for sourmash from the HPC cluster at UCDavis.
#
# To run:
# snakemake -s create-genbank.smk -j 6 --use-conda --retries=3 --rerun-incomplete --resources allowed_jobs=100 --latency-wait=60
# Or:
# snakemake -s create-genbank.smk --profile slurm --resources allowed_jobs=100 -k
# Jobs (`-j`) should be 3 times the number of domains.
###
##

import os

NCBI_API_KEY = os.environ.get("NCBI_API_KEY")

configfile: "config/create-genbank.yaml"

RANKS = config.get("lineage_rank")
DATE = config.get("date")

if not DATE:
    import time
    DATE = [time.strftime("%Y%m%d")]

outdir = [
    f"{config.get('output_directory') if config.get('output_directory') is not None else '..'}/genbank-{date}"
    for date in DATE]

NEW_DOMAINS = config.get('domains')

KSIZES = config.get('k_values')

email = config.get('email')

if email:
    onsuccess:
        print("\nWorkflow finished without error\n")
        shell("mail -s 'Workflow finished without error' {email} < {log}")
    
    onerror:
        print("\nAn error occurred\n")
        shell("mail -s 'an error occurred' {email} < {log}")

if config.get('batch_size'):
    UPDATE_BATCHLIST = expand("{o}/data/update.{d}-{dom}.batchlist.txt", o=outdir, d=DATE, dom=NEW_DOMAINS)
    MISS_BATCHLIST = expand("{o}/data/miss.{d}-{dom}.batchlist.txt", o=outdir, d=DATE, dom=NEW_DOMAINS)

    onsuccess:
        print("\nRemoving the database batch files\n")
        shell("cat {batchlists} | xargs rm -v", batchlists=" ".join(UPDATE_BATCHLIST))
        shell("cat {batchlists} | xargs rm -v", batchlists=" ".join(MISS_BATCHLIST))

if config.get('batch_size'):
    UPDATE_BATCHLIST = expand("{o}/data/update.{d}-{dom}.batchlist.txt", o=outdir, d=DATE, dom=NEW_DOMAINS)
    MISS_BATCHLIST = expand("{o}/data/miss.{d}-{dom}.batchlist.txt", o=outdir, d=DATE, dom=NEW_DOMAINS)

    BATCHLIST_FILES = UPDATE_BATCHLIST + MISS_BATCHLIST

    existing_batchlists = [fp for fp in BATCHLIST_FILES if os.path.exists(fp)]
    print(existing_batchlists)

    onsuccess:
        if not existing_batchlists:
            print("\nNo batchlist files found.\n")
        else:
            print("\nProcessing batchlist files...\n")

            for batchlist in existing_batchlists:
                print(f"\nReading batchlist: {batchlist}")
                with open(batchlist) as f:
                    for filepath in f:
                        filepath = filepath.strip()
                        if not filepath:
                            continue
                        if os.path.exists(filepath):
                            print(f"Deleting {filepath}")
                            os.remove(filepath)
                        else:
                            print(f"Already deleted {filepath}")

wildcard_constraints:
    k = "\d{2}",
    ND = "\w[^-]+",
    d = "\d+",
    rank = "|".join(config.get('lineage_rank', [])),  

# Dictionary for dynamic slurm batch allocations with correct resources
#PART_JOBS = {1: ['low2', 1], 2: ['low2', 1], 3: ['med2', 33], 4: ['med2', 33], 5: ['high2', 100]}
PART_JOBS = {1: ['bml', 1], 2: ['bml', 1], 3: ['bmm', 33], 4: ['bmm', 33], 5: ['bmh', 100]}

# Create a file dictionary for normal and test runs for rule cheat_mainfest
def getInputFilesForManifest(wildcards):
    files = dict()
    if config.get('output_directory') == 'test':
        files["good"] = f"{wildcards.o}/data/sub_assembly_summary.{wildcards.ND}.txt"
        files["bad"] = f"{wildcards.o}/data/sub_assembly_summary_historical.{wildcards.ND}.txt"
    else:
        files["good"] = f"{wildcards.o}/data/assembly_summary.{wildcards.ND}.txt"
        files["bad"] = f"{wildcards.o}/data/assembly_summary_historical.{wildcards.ND}.txt"
    return files

rule all:
    input:
        expand("{o}/genbank-{d}-{ND}-k{k}.zip", o=outdir, d=DATE, ND=NEW_DOMAINS, k=KSIZES),
        expand("{o}/lineages.{ND}.csv", o=outdir, ND=NEW_DOMAINS),
        expand("{o}/genbank-{d}-{ND}-k{k}.{rank}.zip", o=outdir, d=DATE, ND=NEW_DOMAINS, k=KSIZES, rank=RANKS),
        expand("{o}/genbank-{d}-{ND}-k{k}.merged.zip", o=outdir, d=DATE, ND=NEW_DOMAINS, k=KSIZES),


rule build_databases:
    input:
        expand("{o}/genbank-{d}-{ND}-k{k}.zip", o=outdir, d=DATE, ND=NEW_DOMAINS, k=KSIZES),

rule build_lineages:
    input:
        expand("{o}/lineages.{ND}.csv", o=outdir, ND=NEW_DOMAINS),

rule download_assembly_summary:
    output:
        good = '{o}/data/assembly_summary.{ND}.txt',
    shell: """
        url_good="https://ftp.ncbi.nlm.nih.gov/genomes/genbank/{wildcards.ND}/assembly_summary.txt"

        server_status_good=$(curl -L -o /dev/null -w "%{{http_code}}" -s "$url_good")

        if [ "$server_status_good" -eq 200 ]; then
            curl -L "$url_good" > {output.good}
        else
            echo "Failed to download files"
            echo "Server status code $server_status_good"
        fi
    """

rule download_historical_summary:
    output:
        bad = '{o}/data/assembly_summary_historical.{ND}.txt',
    shell: """
        url_bad="https://ftp.ncbi.nlm.nih.gov/genomes/genbank/{wildcards.ND}/assembly_summary_historical.txt"

        server_status_bad=$(curl -L -o /dev/null -w "%{{http_code}}" -s "$url_bad")

        if [ "$server_status_bad" -eq 200 ]; then
            curl -L "$url_bad" > {output.bad}
        else
            echo "Failed to download files"
            echo "Server status code $server_status_bad"
        fi
    """


# create a 1% sub_assembly file for testing!!!
rule test_with_sub_assembly_summary:
    input:
        good = '{o}/data/assembly_summary.{ND}.txt',
        bad = '{o}/data/assembly_summary_historical.{ND}.txt',
    output:
        good = '{o}/data/sub_assembly_summary.{ND}.txt',
        bad = '{o}/data/sub_assembly_summary_historical.{ND}.txt',
    shell:"""
        echo {input.good}
        cat {input.good} | wc -l
        awk 'BEGIN {{srand()}} !/^$/ {{ if (rand() <= .01 || FNR<4) print $0}}' {input.good} > {output.good}
        cat {output.good} | wc -l

        echo {input.bad}
        cat {input.bad} | wc -l
        awk 'BEGIN {{srand()}} !/^$/ {{ if (rand() <= .01 || FNR<4) print $0}}' {input.bad} > {output.bad}
        cat {output.bad} | wc -l
    """

rule new_manifest:
    output:
        mani = '{o}/data/mf.{d}-{ND}-k{k}.csv',
    shell:"""
        cat > {output.mani} << EOF
# SOURMASH-MANIFEST-VERSION: 1.0
internal_location,md5,md5short,ksize,moltype,num,scaled,n_hashes,with_abundance,name,filename
EOF
    """

rule cheat_manifest:
    input:
        unpack(getInputFilesForManifest),
        script = "scripts/update_sourmash_dbs.py",
        manifest = "{o}/data/mf.{d}-{ND}-k{k}.csv",
    output:
        clean = "{o}/data/mf-clean.{d}-{ND}-k{k}.csv",
        missing = "{o}/data/missing-genomes.{d}-{ND}-k{k}.csv",
    conda: "envs/sourmash.yaml",
    shell: """
        {input.script} {input.manifest} -a {input.good} -b {input.bad} -o {output.clean}  --missing-genomes {output.missing}
    """

rule check_txt_new:
    input:
        new = expand("{o}/data/missing-genomes.{d}-{ND}-k{k}.csv", o=outdir, d=DATE, ND=NEW_DOMAINS, k=KSIZES),
        script = "scripts/check_txt_files.py",
    output:
        solo = "{o}/data/missing.{d}-{ND,\w[^-]+}.csv",
    wildcard_constraints:
        ND="\w[^-]+"
    shell: """
        files=""
        for file in "{wildcards.o}/data/missing-genomes.*{wildcards.d}-{wildcards.ND}-k*.csv"; do
            files+=" $file"
        done
        {input.script} $files -o {output.solo}
    """

rule gather_sketch_db:
    input:
        solo = "{o}/data/missing.{d}-{ND}.csv",
    output:
        failed = "{o}/data/missing.{d}-{ND,\w[^-]+}.failures.csv",
        checksum = '{o}/data/issing.{d}_{ND}.failures-checksum.csv',
        log = '{o}/data/gather_sketch_db.{d}_{ND}.log',
        batch = "{o}/data/genbank-{d}-{ND,\w[^-]+}.batchlist.txt",
    wildcard_constraints:
    conda: "envs/directsketch.yaml",
    resources:
        mem_mb = 96 * 1024,
        time = lambda wildcards, attempt: 72 * 60 * attempt,
        runtime = lambda wildcards, attempt: 72 * 60 * attempt,
        allowed_jobs = 50,
        partition = "high2",
    threads: 32
    params:
        k_list = lambda wildcards: ",".join([f"k={k}" for k in KSIZES]),
        scale = config.get('scale_value'),
        api_key = NCBI_API_KEY,
        threads = lambda wildcards: int(10 if NCBI_API_KEY and NCBI_API_KEY.strip() else 3),
        batch_size = config.get('batch_size'),
    shell:'''
        mkdir -p {wildcards.o}/batches
        sourmash scripts gbsketch {input.solo} -o {wildcards.o}/batches/genbank-{wildcards.d}-{wildcards.ND}.zip \
            --failed {output.failed} --checksum-fail {output.checksum} \
            --param-str "dna,{params.k_list},scaled={params.scale},abund" \
            -a '{params.api_key}' -r 10 -n 30 -c {params.threads} -g \
            --batch-size {params.batch_size} --allow-completed 2> {output.log}
        mv {wildcards.o}/batches/genbank-{wildcards.d}-{wildcards.ND}.zip.batchlist.txt {output.batch}
    '''

rule extract_db:
    input:
        db = "{o}/data/genbank-{d}-{ND,\w[^-]+}.batchlist.txt",
    output:
        db = "{o}/genbank-{d}-{ND}-k{k}.zip",
    conda: "envs/sourmash.yaml",
    resources:
        mem_mb = 300 * 1024,
        disk_mb = 300 * 1024,
        time = lambda wildcards, attempt: 24 * 60 * attempt,
        runtime = lambda wildcards, attempt: 24 * 60 * attempt,
        allowed_jobs = 50,
        partition = "bmh",
    shell:"""
        sourmash signature cat {input.db} -k {wildcards.k} -o {output.db}
    """

rule pangenome_database:
    input:
        db = "{o}/genbank-{d}-{ND}-k{k}.zip",
        taxa = "{o}/lineages.{ND}.csv",
    output:
        pan = "{o}/genbank-{d}-{ND}-k{k}.{rank}.zip",
    conda: "envs/pangenome.yaml"
    resources:
        mem_mb = lambda wildcards, attempt: 260 * 1024, # * attempt,
        disk_mb = lambda wildcards, attempt: 260 * 1024,
        time = lambda wildcards, attempt: 8 * 60 * attempt,
        runtime = lambda wildcards, attempt: 8 * 60 * attempt,
        allowed_jobs= 33,
        partition=lambda wildcards, attempt: PART_JOBS[attempt][0],
    params:
        scale = config.get('scale_value'),
    shell: """
        sourmash scripts pangenome_createdb {input.db} -t {input.taxa} -a -k {wildcards.k} --scaled {params.scale} -o {output.pan}
    """

rule pangenome_merge_database:
    input:
        db = "{o}/genbank-{d}-{ND}-k{k}.zip",
        taxa = "{o}/lineages.{ND}.csv",
    output:
        merge = "{o}/genbank-{d}-{ND}-k{k}.merged.zip",
    conda: "envs/pangenome.yaml"
    resources:
        mem_mb = lambda wildcards, attempt: 400 * 1024, # * attempt,
        disk_mb = lambda wildcards, attempt: 400 * 1024, # * attempt,
        time = lambda wildcards, attempt: 8 * 60 * attempt,
        runtime = lambda wildcards, attempt: 8 * 60 * attempt,
        allowed_jobs= 100,
        partition=lambda wildcards, attempt: PART_JOBS[attempt][0],
    params:
        scale = config.get('scale_value'),
    shell: """
        sourmash scripts pangenome_merge {input.db} -k {wildcards.k} --scaled {params.scale} -o {output.merge}
    """

# taxonomy rules, from https://github.com/ctb/2022-assembly-summary-to-lineages
rule download_ncbi_utils:
    output: "scripts/ncbi_taxdump_utils.py"
    shell:
        "curl -L https://raw.githubusercontent.com/ccbaumler/database-releases/refs/heads/wort-removal/genbank-workflow/scripts/ncbi_taxdump_utils.py > {output}"

rule download_taxscript:
    output: "scripts/make-lineage-csv-better.py"
    shell:
        "curl -L https://raw.githubusercontent.com/ccbaumler/database-releases/refs/heads/wort-removal/genbank-workflow/scripts/make-lineage-csv-better.py > {output}"

rule download_taxdump: 
    output:
        directory("{o}/taxdump"),
    shell:"""
        mkdir -p {output}
        curl -L ftp://ftp.ncbi.nlm.nih.gov/pub/taxonomy/taxdump.tar.gz | tar xzvf - -C {output}
    """

rule make_lineage_csv:
    input:
        "{o}/data/assembly_summary.{ND}.txt",
        "taxdump/nodes.dmp",
        "taxdump/names.dmp",
        "scripts/make-lineage-csv-better.py",
        "scripts/ncbi_taxdump_utils.py",
    output:
        "{o}/lineages.{ND}.csv"
    params:
        ictv_cmd = lambda w: " --ictv " if 'viral' in w.ND else '',
    resources:
        mem_mb = lambda wildcards, attempt: 8 * 1024 * attempt,
        disk_mb = lambda wildcards, attempt: 8 * 1024 * attempt,
        time = lambda wildcards, attempt: 1.5 * 60 * attempt,
        runtime = lambda wildcards, attempt: 1.5 * 60 * attempt,
        allowed_jobs=lambda wildcards, attempt: PART_JOBS[attempt][1],
        partition=lambda wildcards, attempt: PART_JOBS[attempt][0],
    shell:
        "python scripts/make-lineage-csv-better.py taxdump/{{nodes.dmp,names.dmp}} {input[0]} -o {output} {params.ictv_cmd}"


# Include a quarto report showing all the info for the workflow
