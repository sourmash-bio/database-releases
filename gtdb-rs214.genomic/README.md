To release the next GTDB version:

1. copy the code in this folder to a new one for the release version
2. update config.yml with new gtdb information (metadata urls, filenames, tag, etc)
3. update wort manifest and add new to config.yml
4. run `snakemake prepare` to cross-check signatures needed  against available wort sigs
5. run `snakemake build` to build the base zipfiles
6. run `snakemake check` to check that these zipfiles have all needed sigs
7. run `snakemake -s release.smk` to build sbt, lca db's from the zipfiles

Notes:
- building SBTs requires more memory than any other db. I will add resources after benchmarking (tbd)
