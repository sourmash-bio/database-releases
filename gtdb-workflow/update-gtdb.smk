###
# This workflow will create a genbank database for sourmash from the HPC cluster at UCDavis.
#
# To run:
# snakemake -s update-genbank.smk -j 15 --use-conda --rerun-incomplete --resources allowed_jobs=100
#
# On HPC, use 10 cpus and ~50gb. Request 2 days?
###

import os

NCBI_API_KEY = os.environ.get("NCBI_API_KEY")

configfile: "config/update-gtdb.yaml"

RELEASES = config.get("update_to_release")
RANKS = config.get("lineage_rank")
OLD_RELEASES, = config["update_from_release"]
VERSION = 0 if config.get("release_version") is None else config.get("release_version")

OUTDIR = [
    f"""{config.get('output_directory', '..')}/gtdb-rs{release}{f'-{config.get("date")}' if config.get('date') else ''}"""
    for release in RELEASES
]

KSIZES = config.get('k_values')
EMAIL = config.get('email')

if EMAIL:
    onsuccess:
        print("\nWorkflow finished without error\n")
        shell("mail -s 'Workflow finished without error' {EMAIL} < {log}")

    onerror:
        print("\nAn error occurred\n")
        shell("mail -s 'an error occurred' {EMAIL} < {log}")

if config.get('batch_size'):
    def ensure_list(x):
        return x if isinstance(x, list) else [x]

    UPDATE_BATCHLIST = expand("{o}/data/batchlist-updated.rs{r}.txt", o=OUTDIR, r=RELEASES)
    MISS_BATCHLIST = expand("{o}/data/batchlist-missing.rs{r}.txt", o=OUTDIR, r=RELEASES)

    BATCHLIST_FILES = ensure_list(UPDATE_BATCHLIST) + ensure_list(MISS_BATCHLIST)

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

# Dictionary for dynamic slurm batch allocations with correct resources
#PART_JOBS = {1: ['low2', 1], 2: ['low2', 1], 3: ['med2', 33], 4: ['med2', 33], 5: ['high2', 100]}
PART_JOBS = {1: ['bml', 1], 2: ['bml', 1], 3: ['bmm', 33], 4: ['bmm', 33], 5: ['bmh', 100]}

wildcard_constraints:
    o = "|".join([f"""{config.get('output_directory', '..')}/gtdb-rs{r}{f'-{config.get("date")}' if config.get('date') else ''}""" for r in RELEASES]),
    k = "\d{2}",
    r = "\\d+",
    OR = "\\w[^-.]+",
    rank = "|".join(config.get('lineage_rank', []))

rule all:
    input:
        expand("{o}/gtdb-rs{r}-k{k}.zip", o=OUTDIR, r=RELEASES, k=KSIZES),
        expand("{o}/gtdb-rs{r}-k{k}.reps.zip", o=OUTDIR, r=RELEASES, k=KSIZES),
#        expand("{o}/gtdb-rs{r}-k{k}.clean.zip", o=OUTDIR, r=RELEASES, k=KSIZES),
#        expand("{o}/gtdb-rs{r}.lineages.csv", o=OUTDIR, r=RELEASES),
#        expand("{o}/gtdb-rs{r}.lineages.reps.csv", o=OUTDIR, r=RELEASES),
#        expand("{o}/data/gtdb-{r}.clean-existing.csv", o=OUTDIR, r=RELEASES),
#        expand("{o}/data/gtdb-{r}.clean-missing.csv", o=OUTDIR, r=RELEASES),
#        expand("{o}/data/final.gtdb-{r}.missing.csv", o=OUTDIR, r=RELEASES),
#        expand("{o}/data/final.gtdb-{r}.existing.csv", o=OUTDIR, r=RELEASES),
#        expand("{o}/data/final-reps.gtdb-{r}.missing.csv", o=OUTDIR, r=RELEASES),
#        expand("{o}/data/final-reps.gtdb-{r}.existing.csv", o=OUTDIR, r=RELEASES),
        expand("{o}/report/report.gtdb-rs{r}.html", o=OUTDIR, r=RELEASES),
        expand("{o}/data/ranktable.gtdb-rs{r}-k{k}.species.log", o=OUTDIR, r=RELEASES, k=KSIZES),
        expand("{o}/gtdb-rs{r}-k{k}.{rank}.zip", o=OUTDIR, r=RELEASES, k=KSIZES, rank=RANKS),
        expand("{o}/gtdb-rs{r}-k{k}.merged.zip", o=OUTDIR, r=RELEASES, k=KSIZES),

rule tax:
    input:
        expand("{o}/lineages.gtdb-rs{r}.csv", o=OUTDIR, r=RELEASES),
        expand("{o}/lineages.gtdb-rs{r}.reps.csv", o=OUTDIR, r=RELEASES),

rule get_metadata:
    input:
        expand('{o}/data/assembly_summary.bac.x.ar.txt', o=OUTDIR),
        expand('{o}/data/assembly_summary_historical.bac.x.ar.txt', o=OUTDIR),
        expand('{o}/data/bac120_metadata_rs{r}.tsv', o=OUTDIR, r=RELEASES),
        expand('{o}/data/ar53_metadata_rs{r}.tsv', o=OUTDIR, r=RELEASES),

rule download_metadata:
    output:
        ar = '{o}/data/ar53_metadata_rs{r}.tsv',
        bac = '{o}/data/bac120_metadata_rs{r}.tsv',
    params:
        ar_path = lambda wildcards: f"https://data.gtdb.ecogenomic.org/releases/release{wildcards.r}/{wildcards.r}.{VERSION}",
        ar_file = lambda wildcards: f"ar53_metadata_r{wildcards.r}.tsv.gz",
        bac_path = lambda wildcards: f"https://data.gtdb.ecogenomic.org/releases/release{wildcards.r}/{wildcards.r}.{VERSION}",
        bac_file = lambda wildcards: f"bac120_metadata_r{wildcards.r}.tsv.gz",
    shell: """
        curl -L {params.bac_path}/{params.bac_file} > {wildcards.o}/data/{params.bac_file}
        curl -L {params.ar_path}/{params.ar_file} > {wildcards.o}/data/{params.ar_file}
        gzip -d {wildcards.o}/data/{params.bac_file} -c > {output.bac}
        gzip -d {wildcards.o}/data/{params.ar_file} -c > {output.ar}
    """

rule download_assembly_summary:
    output:
        good = '{o}/data/assembly_summary.bac.x.ar.txt',
        bad = '{o}/data/assembly_summary_historical.bac.x.ar.txt',
    resources:
        mem_mb = lambda wildcards, attempt: 2 * 1024 * attempt,
        time = lambda wildcards, attempt: 1.5 * 60 * attempt,
        runtime = lambda wildcards, attempt: 1.5 * 60 * attempt,
        allowed_jobs=lambda wildcards, attempt: PART_JOBS[attempt][1],
        partition=lambda wildcards, attempt: PART_JOBS[attempt][0],
    shell: """
        curl -L https://ftp.ncbi.nlm.nih.gov/genomes/genbank/bacteria/assembly_summary.txt > {wildcards.o}/data/assembly_summary.bacteria.txt
        curl -L https://ftp.ncbi.nlm.nih.gov/genomes/genbank/archaea/assembly_summary.txt > {wildcards.o}/data/assembly_summary.archaea.txt

        curl -L https://ftp.ncbi.nlm.nih.gov/genomes/genbank/bacteria/assembly_summary_historical.txt > {wildcards.o}/data/assembly_summary_historical.bacteria.txt
        curl -L https://ftp.ncbi.nlm.nih.gov/genomes/genbank/archaea/assembly_summary_historical.txt > {wildcards.o}/data/assembly_summary_historical.archaea.txt

        cat {wildcards.o}/data/assembly_summary.bacteria.txt > {output.good}
        sed '1,2d' {wildcards.o}/data/assembly_summary.archaea.txt >> {output.good}
        cat {wildcards.o}/data/assembly_summary_historical.bacteria.txt > {output.bad}
        sed '1,2d' {wildcards.o}/data/assembly_summary_historical.archaea.txt >> {output.bad}

    """

rule get_ss_db:
    params:
        o_r = OLD_RELEASES
    output:
        dbs = temporary(f"temp/gtdb-rs{OLD_RELEASES}-k{{k}}.zip"),
    resources:
        mem_mb = lambda wildcards, attempt: 2 * 1024 * attempt,
        time = lambda wildcards, attempt: 1.5 * 60 * attempt,
        runtime = lambda wildcards, attempt: 1.5 * 60 * attempt,
        allowed_jobs=lambda wildcards, attempt: PART_JOBS[attempt][1],
        partition=lambda wildcards, attempt: PART_JOBS[attempt][0],
    shell: """
            echo "Previous release: {params.o_r}"

            echo "Checking primary directory /group/ctbrowngrp/sourmash-db/gtdb-rs{params.o_r}/ for gtdb-rs{params.o_r}-k{wildcards.k}.zip exists..."
            if [ -e /group/ctbrowngrp/sourmash-db/gtdb-rs{params.o_r}/gtdb-rs{params.o_r}-k{wildcards.k}.zip ]; then

                echo "gtdb-rs{params.o_r}-k{wildcards.k}.zip exists!"
                echo "Linking existing file to $(pwd)"

                ln -s /group/ctbrowngrp/sourmash-db/gtdb-rs{params.o_r}/gtdb-rs{params.o_r}-k{wildcards.k}.zip {output.dbs}
            else

                echo "File not found in primary directory. Checking backup directory /group/ctbrowngrp4/2024-ccbaumler-gtdb/ ..."

                if [ -e /group/ctbrowngrp4/2024-ccbaumler-gtdb/gtdb-rs{params.o_r}/gtdb-rs{params.o_r}-k{wildcards.k}.zip ]; then
                    echo "gtdb-rs{params.o_r}-k{wildcards.k}.zip exists in the backup directory!"
                    echo "Linking existing file to $(pwd)"

                    ln -s /group/ctbrowngrp4/2024-ccbaumler-gtdb/gtdb-rs{params.o_r}/gtdb-rs{params.o_r}-k{wildcards.k}.zip {output.dbs}

                else

                    echo "gtdb-rs{params.o_r}-k{wildcards.k}.zip does not exist!"
                    echo "Downloading file to $(pwd)/{output.dbs}"

                    curl -L https://farm.cse.ucdavis.edu/~ctbrown/sourmash-db/gtdb-rs{params.o_r}/gtdb-rs{params.o_r}-k{wildcards.k}.zip > {output.dbs}
                if [ $? -ne 0 ]; then
                    echo "Download failed! Exiting with error."
                    exit 1
                fi
            fi
        fi
   """

rule make_taxonomy:
    input:
        script = 'scripts/make-updated-gtdb-taxonomy.py',
        ar53_metadata='{o}/data/ar53_metadata_rs{r}.tsv',
        bac120_metadata='{o}/data/bac120_metadata_rs{r}.tsv',
    output:
        tax_csv = '{o}/data/gtdb-rs{r}.oldlineages.csv',
        reps_csv = '{o}/data/gtdb-rs{r}.oldlineages.reps.csv',
    threads: 1
    resources:
        mem_mb = lambda wildcards, attempt: 8 * 1024 * attempt,
        time = lambda wildcards, attempt: 1.5 * 60 * attempt,
        runtime = lambda wildcards, attempt: 1.5 * 60 * attempt,
        allowed_jobs=lambda wildcards, attempt: PART_JOBS[attempt][1],
        partition=lambda wildcards, attempt: PART_JOBS[attempt][0],
    conda:
        "envs/sourmash.yaml",
    shell:
        """
        python {input.script} --metadata-files {input.ar53_metadata} {input.bac120_metadata} \
               -o {output.tax_csv} --reps-csv {output.reps_csv}
        """

rule collect_all:
    input:
        dbs = expand(f"temp/gtdb-rs{OLD_RELEASES}-k{{k}}.zip", k = KSIZES[0])
    output:
        db = f"{{o}}/data/collect-mf-orig.rs{OLD_RELEASES}.csv",
    conda: "envs/sourmash.yaml"
    resources:
        mem_mb = lambda wildcards, attempt: 16 * 1024 * attempt,
        time = lambda wildcards, attempt: 12 * 60 * attempt,
        runtime = lambda wildcards, attempt: 12 * 60 * attempt,
        allowed_jobs=100,
        partition="bmh",
    shell: """
        sourmash sig manifest --no-rebuild {input.dbs} -o {output.db}
    """

rule picklist_check:
    input:
        dbs_manifest = f"{{o}}/data/collect-mf-orig.rs{OLD_RELEASES}.csv",
        tax_picklist = '{o}/data/gtdb-rs{r}.oldlineages.csv',
    output:
        missing = "{o}/data/mf-missing-genomes.rs{r}.csv",
        manifest = "{o}/data/mf-existing-genomes.rs{r}.csv",
    params: 
        log = "logs/picklist_check/gtdb-{r}.picklist_check.log",
        first_k = lambda wildcards: KSIZES[0],
    conda: "envs/sourmash.yaml"
    threads: 1
    resources:
        mem_mb= lambda wildcards, attempt: 6 * 1024 * attempt,
        time= 10000,
        partition='high2',
    shell:
        """
        sourmash sig check -k {params.first_k} \
            --picklist {input.tax_picklist}:ident:ident \
            {input.dbs_manifest} --output-missing {output.missing} \
            --save-manifest {output.manifest} 2> {params.log}
        touch {output.missing}
        """

rule cleanse_existing:
    input:
        script = "scripts/update_sourmash_dbs.py",
        good = "{o}/data/assembly_summary.bac.x.ar.txt",
        bad = "{o}/data/assembly_summary_historical.bac.x.ar.txt",
        manifest = "{o}/data/mf-existing-genomes.rs{r}.csv",
    output:
        clean = "{o}/data/mf-existing-genomes.rs{r}.clean.csv",
        reversion = "{o}/data/mf-existing-genomes.rs{r}.updated.csv",
        report = "{o}/data/report-existing.rs{r}.txt",
    conda: "envs/sourmash.yaml",
    resources:
        mem_mb = lambda wildcards, attempt: 8 * 1024 * attempt,
        time = lambda wildcards, attempt: 1.5 * 60 * attempt,
        runtime = lambda wildcards, attempt: 1.5 * 60 * attempt,
        allowed_jobs=lambda wildcards, attempt: PART_JOBS[attempt][1],
        partition=lambda wildcards, attempt: PART_JOBS[attempt][0],
    shell: """
        {input.script} {input.manifest} -a {input.good} -b {input.bad} -o {output.clean} --updated-version {output.reversion} --report {output.report}
    """

rule cleanse_missing:
    input:
        script = "scripts/update_sourmash_dbs.py",
        good = "{o}/data/assembly_summary.bac.x.ar.txt",
        bad = "{o}/data/assembly_summary_historical.bac.x.ar.txt",
        manifest = "{o}/data/mf-missing-genomes.rs{r}.csv",
    output:
        clean = "{o}/data/mf-missing-genomes.rs{r}.clean.csv",
        all_links = "{o}/data/mf-missing-genomes.rs{r}.all-missing-links.csv",
        report = "{o}/data/report-missing.rs{r}.txt",
    conda: "envs/sourmash.yaml",
    resources:
        mem_mb = lambda wildcards, attempt: 8 * 1024 * attempt,
        time = lambda wildcards, attempt: 1.5 * 60 * attempt,
        runtime = lambda wildcards, attempt: 1.5 * 60 * attempt,
        allowed_jobs=lambda wildcards, attempt: PART_JOBS[attempt][1],
        partition=lambda wildcards, attempt: PART_JOBS[attempt][0],
    shell: """
        {input.script} {input.manifest} -a {input.good} -b {input.bad} -o {output.clean} --all-links {output.all_links} --report {output.report}
    """

rule gather_sketch_existing:
    input:
        updated = "{o}/data/mf-existing-genomes.rs{r}.updated.csv",
    output:
        failed = "{o}/data/mf-existing-genomes.rs{r}.updated.failures.csv",
        checksum = "{o}/data/mf-existing-genomes.rs{r}.updated.failures-checksum.csv",
        log = "{o}/logs/gather_sketch_existing.rs{r}.log",
        batch = "{o}/data/batchlist-updated.rs{r}.txt",
    conda: "envs/directsketch.yaml"
    resources:
        mem_mb = 96 * 1024,
        disk_mb = 96 * 1024,
        time = lambda wildcards, attempt: 72 * 60 * attempt,
        runtime = lambda wildcards, attempt: 72 * 60 * attempt,
        allowed_jobs=34,
        partition="high2",
    threads: 16
    params:
        k_list = lambda wildcards: ",".join([f"k={k}" for k in KSIZES]),
        scale = config.get('scale_value'),
        api = NCBI_API_KEY,
        threads = lambda wildcards: int(10 if NCBI_API_KEY and NCBI_API_KEY.strip() else 3),
        batch_size = config.get('batch_size'),
    shell:'''
        mkdir -p {wildcards.o}/batches
        sourmash scripts gbsketch {input.updated} -o {wildcards.o}/batches/updated-genomes-rs{wildcards.r}.zip \
            --failed {output.failed} --checksum-fail {output.checksum} \
            --param-str "dna,{params.k_list},scaled={params.scale},abund" \
            -a '{params.api}' -r 10 -n 30 -c {params.threads} -g \
            --batch-size {params.batch_size} --allow-completed 2> {output.log}
        mv {wildcards.o}/batches/updated-genomes-rs{wildcards.r}.zip.batchlist.txt {output.batch}
    '''

rule gather_sketch_missing:
    input:
        missing = "{o}/data/mf-missing-genomes.rs{r}.all-missing-links.csv",
    output:
        failed = "{o}/data/mf-missing-genomes.rs{r}.all-missing-links.failures.csv",
        checksum = "{o}/data/mf-missing-genomes.rs{r}.all-missing-links.failures-checksum.csv",
        log = "{o}/logs/gather_sketch_missing.rs{r}.log",
        batch = "{o}/data/batchlist-missing.rs{r}.txt",
    conda: "envs/directsketch.yaml"
    resources:
        mem_mb = 96 * 1024,
        disk_mb = 96 * 1024,
        time = lambda wildcards, attempt: 72 * 60 * attempt,
        runtime = lambda wildcards, attempt: 72 * 60 * attempt,
        allowed_jobs=34,
        partition="high2",
    threads: 16
    params:
        k_list = lambda wildcards: ",".join([f"k={k}" for k in KSIZES]),
        scale = config.get('scale_value'),
        api = NCBI_API_KEY,
        threads = lambda wildcards: int(10 if NCBI_API_KEY and NCBI_API_KEY.strip() else 3),
        batch_size = config.get('batch_size'),
    shell:'''
        mkdir -p {wildcards.o}/batches
        sourmash scripts gbsketch {input.missing} -o {wildcards.o}/batches/missing-genomes-rs{wildcards.r}.zip \
            --failed {output.failed} --checksum-fail {output.checksum} \
            --param-str "dna,{params.k_list},scaled={params.scale},abund" \
            -a '{params.api}' -r 10 -n 30 -c {params.threads} -g \
            --batch-size {params.batch_size} --allow-completed 2> {output.log}
        mv {wildcards.o}/batches/missing-genomes-rs{wildcards.r}.zip.batchlist.txt {output.batch}
    '''

rule extract_db:
    input:
        clean = "{o}/data/mf-existing-genomes.rs{r}.clean.csv",
        dbs = f"temp/gtdb-rs{OLD_RELEASES}-k{{k}}.zip",
    output:
        dbs = temporary("{o}/gtdb-rs{r}-k{k}.clean.zip"),
    conda: "envs/sourmash.yaml",
    resources:
        mem_mb = 80 * 1024,
        time = lambda wildcards, attempt: 24 * 60 * attempt,
        runtime = lambda wildcards, attempt: 24 * 60 * attempt,
        allowed_jobs = 100,
        partition = "bmh",
    shell:"""
        sourmash signature cat {input.dbs} --picklist {input.clean}:name:name -k {wildcards.k} -o {output.dbs}
    """

rule make_updated_taxonomy:
    input:
        clean = "{o}/data/mf-existing-genomes.rs{r}.clean.csv",
        updated = "{o}/data/mf-existing-genomes.rs{r}.updated.csv",
        missing = "{o}/data/mf-missing-genomes.rs{r}.all-missing-links.csv",
        script = 'scripts/make-updated-gtdb-taxonomy.py',
        ar53_metadata='{o}/data/ar53_metadata_rs{r}.tsv',
        bac120_metadata='{o}/data/bac120_metadata_rs{r}.tsv',
        assembly_summary='{o}/data/assembly_summary.bac.x.ar.txt',
    output:
        tax_csv = '{o}/lineages.gtdb-rs{r}.csv',
        reps_csv = '{o}/lineages.gtdb-rs{r}.reps.csv',
    threads: 1
    resources:
        mem_mb = lambda wildcards, attempt: 8 * 1024 * attempt,
        time = lambda wildcards, attempt: 1.5 * 60 * attempt,
        runtime = lambda wildcards, attempt: 1.5 * 60 * attempt,
        allowed_jobs=lambda wildcards, attempt: PART_JOBS[attempt][1],
        partition=lambda wildcards, attempt: PART_JOBS[attempt][0],
    conda:
        "envs/sourmash.yaml",
    shell:
        """
        python {input.script} --metadata-files {input.ar53_metadata} {input.bac120_metadata} \
               --update-files {input.assembly_summary} \
               -o {output.tax_csv} --reps-csv {output.reps_csv}
        """

rule final_db:
    input:
        old_existing = "{o}/gtdb-rs{r}-k{k}.clean.zip",
        updated_existing = "{o}/data/batchlist-updated.rs{r}.txt",
        updated_missing = "{o}/data/batchlist-missing.rs{r}.txt",
    output:
        woohoo = "{o}/gtdb-rs{r}-k{k}.zip"
    conda: "envs/sourmash.yaml",
    resources:
        mem_mb = 80 * 1024,
        time = lambda wildcards, attempt: 24 * 60 * attempt,
        runtime = lambda wildcards, attempt: 24 * 60 * attempt,
        allowed_jobs = 100,
        partition = "bmh",
    shell:"""
        sourmash signature cat \
            {input.old_existing} {input.updated_existing} {input.updated_missing} \
            -k {wildcards.k} -o {output.woohoo}
    """

rule final_db_reps:
    input:
        dbs = "{o}/gtdb-rs{r}-k{k}.zip",
        picklist = "{o}/lineages.gtdb-rs{r}.reps.csv",
    output:
        woohoo = "{o}/gtdb-rs{r}-k{k}.reps.zip"
    conda: "envs/sourmash.yaml",
    resources:
        mem_mb = 80 * 1024,
        time = lambda wildcards, attempt: 24 * 60 * attempt,
        runtime = lambda wildcards, attempt: 24 * 60 * attempt,
        allowed_jobs = 100,
        partition = "bmh",
    shell:"""
        sourmash signature cat \
            {input.dbs} -k {wildcards.k} \
            --picklist {input.picklist}:ident:ident \
            -o {output.woohoo}
    """

rule final_picklist_check:
    input:
        dbs = expand("{o}/gtdb-rs{r}-k{k}.zip", o = OUTDIR, r = RELEASES, k = KSIZES[0]), 
        tax_picklist = '{o}/lineages.gtdb-rs{r}.csv',
    output:
        missing = "{o}/data/final.gtdb-rs{r}.missing.csv",
        manifest = "{o}/data/final.gtdb-rs{r}.existing.csv",
    params: 
        log = "logs/picklist_check/final.gtdb-rs{r}.picklist_check.log",
        first_k = lambda wildcards: KSIZES[0],
    conda: "envs/sourmash.yaml"
    threads: 1
    resources:
        mem_mb= lambda wildcards, attempt: 6 * 1024 * attempt,
        time= 10000,
        partition='high2',
    shell:
        """
        sourmash sig check -k {params.first_k} \
            --picklist {input.tax_picklist}:ident:ident \
            {input.dbs} --output-missing {output.missing} \
            --save-manifest {output.manifest} 2> {params.log}
        touch {output.missing}
        """

rule reps_picklist_check:
    input:
        dbs = expand("{o}/gtdb-rs{r}-k{k}.reps.zip", o = OUTDIR, r = RELEASES, k = KSIZES[0]), 
        tax_picklist = '{o}/lineages.gtdb-rs{r}.reps.csv',
    output:
        missing = "{o}/data/final-reps.gtdb-rs{r}.missing.csv",
        manifest = "{o}/data/final-reps.gtdb-rs{r}.existing.csv",
    params: 
        log = "logs/picklist_check/final-reps.gtdb-rs{r}.picklist_check.log",
        first_k = lambda wildcards: KSIZES[0],
    conda: "envs/sourmash.yaml"
    threads: 1
    resources:
        mem_mb= lambda wildcards, attempt: 6 * 1024 * attempt,
        time= 10000,
        partition='high2',
    shell:
        """
        sourmash sig check -k {params.first_k} \
            --picklist {input.tax_picklist}:ident:ident \
            {input.dbs} --output-missing {output.missing} \
            --save-manifest {output.manifest} 2> {params.log}
        touch {output.missing}
        """

rule make_manual_files:
    input:
        script = "scripts/gather_failed.sh",
        updated = "{o}/data/mf-existing-genomes.rs{r}.updated.csv",
        missing = "{o}/data/mf-missing-genomes.rs{r}.all-missing-links.csv",
        CHECK="{o}/data/final.gtdb-rs{r}.missing.csv",
        CHECK_REPS="{o}/data/final-reps.gtdb-rs{r}.missing.csv",
    output:
        OUTPUT="{o}/workflow-cleanup/manual-download.{r}.csv",
        OUTPUT_REPS="{o}/workflow-cleanup/manual-download-reps.{r}.csv",
        MANUAL="{o}/workflow-cleanup/manual-check.{r}.csv",
        MANUAL_REPS="{o}/workflow-cleanup/manual-check-reps.{r}.csv",
        log = "{o}/workflow-cleanup/log.{r}.txt",
    resources:
        mem_mb = lambda wildcards, attempt: 4 * 1024 * attempt,
        time = lambda wildcards, attempt: 1.5 * 60 * attempt,
        runtime = lambda wildcards, attempt: 1.5 * 60 * attempt,
        allowed_jobs=lambda wildcards, attempt: PART_JOBS[attempt][1],
        partition=lambda wildcards, attempt: PART_JOBS[attempt][0],
    shell:"""
        {input.script} {wildcards.o} {wildcards.r} 2>&1 | tee {output.log}
    """

### create pangenome databases as well ###

rule pangenome_database:
    input:
        db = "{o}/gtdb-rs{r}-k{k}.zip",
        taxa = "{o}/lineages.gtdb-rs{r}.csv",
    output:
        pan = "{o}/gtdb-rs{r}-k{k}.{rank}.zip",
    conda: "envs/pangenome.yaml"
    resources:
        mem_mb = lambda wildcards, attempt: 160 * 1024, # * attempt,
        disk_mb = lambda wildcards, attempt: 160 * 1024, # * attempt,
        time = lambda wildcards, attempt: 8 * 60 * attempt,
        runtime = lambda wildcards, attempt: 8 * 60 * attempt,
        allowed_jobs=lambda wildcards, attempt: PART_JOBS[attempt][1],
        partition=lambda wildcards, attempt: PART_JOBS[attempt][0],
    params:
        scale = config.get('scale_value'),
    shell: """
        sourmash scripts pangenome_createdb {input.db} -t {input.taxa} -a -k {wildcards.k} --scaled {params.scale} -o {output.pan} --rank {wildcards.rank}
    """

rule pangenome_merged_database:
    input:
        db = "{o}/gtdb-rs{r}-k{k}.zip",
        taxa = "{o}/lineages.gtdb-rs{r}.csv",
    output:
        merge = "{o}/gtdb-rs{r}-k{k}.merged.zip",
    conda: "envs/pangenome.yaml"
    resources:
        mem_mb = lambda wildcards, attempt: 96 * 1024, # * attempt,
        disk_mb = lambda wildcards, attempt: 96 * 1024, # * attempt,
        time = lambda wildcards, attempt: 8 * 60 * attempt,
        runtime = lambda wildcards, attempt: 8 * 60 * attempt,
        allowed_jobs=lambda wildcards, attempt: PART_JOBS[attempt][1],
        partition=lambda wildcards, attempt: PART_JOBS[attempt][0],
    params:
        scale = config.get('scale_value'),
    shell: """
        sourmash scripts pangenome_merge {input.db} -k {wildcards.k} --scaled {params.scale} -o {output.merge}
    """


rule pangenome_ranktable:
    input:
        script = "scripts/make-all-ranktables-threaded.py",
        pan = "{o}/gtdb-rs{r}-k{k}.species.zip",
    output:
        log = "{o}/data/ranktable.gtdb-rs{r}-k{k}.species.log",
    conda: "envs/pangenome.yaml"
    threads: 32
    resources:
        mem_mb = lambda wildcards, attempt: 16 * 1024 * attempt,
        time = lambda wildcards, attempt: 8 * 60 * attempt,
        runtime = lambda wildcards, attempt: 8 * 60 * attempt,
        allowed_jobs = 25, #lambda wildcards, attempt: PART_JOBS[attempt][1],
        partition = 'high2', #lambda wildcards, attempt: PART_JOBS[attempt][0],
    params:
        scale = config.get('scale_value'),
    shell: """
        mkdir -p {wildcards.o}/ranktables
        {input.script} {input.pan} --outdir {wildcards.o}/ranktables/ --ksize {wildcards.k} --scaled {params.scale} \
          --release {wildcards.r} --rank species --threads {threads} --gzip

        echo "completed" > {output.log}
    """


### create a report with sourmash sig summarize for the databases... and sourmash compare(?)

rule quarto_report:
    input:
        good = "{o}/data/assembly_summary.bac.x.ar.txt",
        bad = "{o}/data/assembly_summary_historical.bac.x.ar.txt",
        exist_report = "{o}/data/report-existing.rs{r}.txt",
        miss_report = "{o}/data/report-missing.rs{r}.txt",
        new_mf = "{o}/data/final.gtdb-rs{r}.existing.csv",
        new_reps_mf = "{o}/data/final-reps.gtdb-rs{r}.existing.csv",
        old_mf = f"{{o}}/data/collect-mf-orig.rs{OLD_RELEASES}.csv",
        existing_failures = "{o}/data/mf-existing-genomes.rs{r}.updated.failures.csv",
        missing_failures = "{o}/data/mf-missing-genomes.rs{r}.all-missing-links.failures.csv",
        missing = "{o}/data/final.gtdb-rs{r}.missing.csv",
        gathered = "{o}/data/final.gtdb-rs{r}.existing.csv",
        reps_missing = "{o}/data/final-reps.gtdb-rs{r}.missing.csv",
        reps_gathered = "{o}/data/final-reps.gtdb-rs{r}.existing.csv",
        lineage = '{o}/lineages.gtdb-rs{r}.csv',
        reps_lineage = '{o}/lineages.gtdb-rs{r}.reps.csv',
        recovered = "{o}/workflow-cleanup/log.{r}.txt",
        ar53='{o}/data/ar53_metadata_rs{r}.tsv',
        bac120='{o}/data/bac120_metadata_rs{r}.tsv',
    output:
        "{o}/report/report.gtdb-rs{r}.html"
    params:
        report_title = "GTDB's {r} Database Update Report",
        old_release= OLD_RELEASES,
        old_db = lambda wildcards: ",".join([f'"gtdb-rs{OLD_RELEASES}-k{k}.zip"' for k in KSIZES]),
        new_db = lambda wildcards: ",".join([f'"{wildcards.o}/gtdb-rs{wildcards.r}-k{k}.zip"' for k in KSIZES]),
        new_reps_db = lambda wildcards: ",".join([f'"{wildcards.o}/gtdb-rs{wildcards.r}-k{k}.reps.zip"' for k in KSIZES]),
        man = "{o}/workflow-cleanup/manual-download.{r}.csv",
        man_check = "{o}/workflow-cleanup/manual-check.{r}.csv",
        man_out = "{o}/workflow-cleanup/manual-download.{r}.zip",
        man_fail = "{o}/workflow-cleanup/manual-download.{r}.failed.csv",
        man_log = "{o}/workflow-cleanup/manual-download.{r}.log",
        reps = "{o}/workflow-cleanup/manual-download-reps.{r}.csv",
        reps_check = "{o}/workflow-cleanup/manual-check-reps.{r}.csv",
        reps_out = "{o}/workflow-cleanup/manual-download-reps.{r}.zip",
        reps_fail = "{o}/workflow-cleanup/manual-download-reps.{r}.failed.csv",
        reps_log = "{o}/workflow-cleanup/manual-download-reps.{r}.log",
        k_list = lambda wildcards: ",".join([f"k={k}" for k in KSIZES]),
        scale = config.get('scale_value'),
    conda: "envs/quarto.yaml",
    resources:
        mem_mb = lambda wildcards, attempt: 24 * 1024 * attempt,
        time = lambda wildcards, attempt: 1.5 * 60 * attempt,
        runtime = lambda wildcards, attempt: 1.5 * 60 * attempt,
        allowed_jobs=lambda wildcards, attempt: PART_JOBS[attempt][1],
        partition=lambda wildcards, attempt: PART_JOBS[attempt][0],
    shell:
        """
        # Mimicing https://github.com/ETH-NEXUS/quarto_example/blob/main/workflow/rules/clean_data_report.smk
        # This will be a stand-alone html document and needs to embed-resources
        # https://quarto.org/docs/output-formats/html-publishing.html#standalone-html
        mkdir -p {wildcards.r}.temp
        cp scripts/report.qmd {wildcards.r}.temp/
        cd {wildcards.r}.temp/

        DIRNAME=$(dirname "{output}")

        quarto render report.qmd \
            -P existing_report:{input.exist_report} -P missing_report:{input.miss_report} -P old_details:{params.old_release} \
            -P new_details:{wildcards.r} -P old_db:{params.old_db} \
            -P new_db:{params.new_db} -P new_reps_db:{params.new_reps_db} \
            -P old_mf:{input.old_mf} -P new_mf:{input.new_mf} \
            -P new_reps_mf:{input.new_reps_mf} -P existing_failures:{input.existing_failures} -P missing_failures:{input.missing_failures} \
            -P report_title:"{params.report_title}" -P config:"{config}" \
            -P good_assm:{input.good} -P bad_assm:{input.bad} \
            -P missed:{input.missing} -P gathered:{input.gathered} \
            -P reps_missed:{input.reps_missing} -P reps_gathered:{input.reps_gathered} \
            -P lineage:{input.lineage} -P reps_lineage:{input.reps_lineage} -P recovered:{input.recovered} \
            -P manual_download:{params.man} -P manual_output:{params.man_out} \
            -P manual_failed:{params.man_fail} -P manual_log:{params.man_log} \
            -P manual_check:{params.man_check} -P manual_reps_download:{params.reps} \
            -P manual_reps_output:{params.reps_out} -P manual_reps_failed:{params.reps_fail} \
            -P manual_reps_check:{params.reps_check} -P manual_reps_log:{params.reps_log} -P output_dir:{wildcards.o} \
            -P ar:{input.ar53} -P bac:{input.bac120} \
            -P k_list:{params.k_list} -P scale:{params.scale}

        # the `--output` arg adds an unnecessary `../` to the output file path
        # https://github.com/quarto-dev/quarto-cli/issues/10129
        # just mving it back in place

        mv report.html {output}
        cd ..
        rm -rf {wildcards.r}.temp
        """
