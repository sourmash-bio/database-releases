# GTDB Protein - RS214

The protein workflow is a bit different than the genomic workflows, because wort does not make protein signatures (yet). So here, we download the proteome files and build signatures. I've chosen to keep these around for now, since I've found them useful for times when I need to build higher resolution (lower scaled) databases. To save space, we could make the proteome files temporary.

In cases where there is no proteome file available, we instead download the genome file, translate to protein with prodigal, and then sketch the prodigal proteome. We use the `genbank_genomes.py` to determine whether we have a downloadable proteome, and build required fasta `fromfile` information from there. Making this a checkpoint allows us to do the entire workflow dynamically.

For the next release, we could use all signatures from this release to avoid rebuilding sigs. That's not in here yet, but could be by using the `missing` and `manifest` outputs from the `prepare` rule.

To release the next protein GTDB:

1. Run the GTDB genomic workflow first, which will generate the taxonomic lineages files we will use here.
2. Copy the code in this folder (snakefiles, environment.yml config.yaml) to a new one for the release version
3. update `config.yml` with new gtdb information (name, tag, new lineages files, etc)
4. update the `environment.yml` as needed/desired, install, and activate
5. run `snakemake build` to build the base zipfile
6. run `snakemake check` to check that these zipfiles have all needed sigs
7. run `snakemake -s release.smk` to build sbt, lca db's from the zipfiles
8. release databases will be in `/group/ctbrowngrp/sourmash-db/{name}-{tag}`, using params you set in `config.yml`
9. update sourmash docs (databases.md) with the new db information

Notes:
- If you want to take advantage of the automated resource management, set up a slurm profile and pass into snakemake (e.g. snakemake --profile slurm)
- This could also be automated into an `sbatch` file sometime in the future.


# Unused steps I might add back in for next version
- run `snakemake prepare` to cross-check signatures needed  against available genomes