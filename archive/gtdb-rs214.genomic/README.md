To release the next GTDB version:

1. update wort manifest. This will build a new manifest with today's date:
```
bash /group/ctbrowngrp/sourmash-db/wort-manifests/update-wort-manifest.sh
```
2. Copy the code in this folder (snakefiles, environment.yml config.yaml) to a new one for the release version
3. update `config.yml` with new gtdb information (metadata urls, filenames, tag, new wort manifest,etc)
4. update the `environment.yml` as needed/desired, install, and activate
5. run `snakemake prepare` to cross-check signatures needed  against available wort sigs
6. run `snakemake build` to build the base zipfiles
7. run `snakemake check` to check that these zipfiles have all needed sigs
8. run `snakemake -s release.smk` to build sbt, lca db's from the zipfiles
9. release databases will be in `/group/ctbrowngrp/sourmash-db/{name}-{tag}`, using params you set in `config.yml`
10. update sourmash docs (databases.md) with the new db information

Notes:
- If you want to take advantage of the automated resource management, set up a slurm profile and pass into snakemake (e.g. snakemake --profile slurm)
- This could usefully be automated into an `sbatch` file sometime in the future.
