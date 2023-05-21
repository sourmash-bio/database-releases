To release the next GTDB version:

1. update wort manifest. This will build a new manifest with today's date:
```
bash /group/ctbrowngrp/sourmash-db/wort-manifests/update-wort-manifest.sh
```
2. copy the code in this folder to a new one for the release version
3. update `config.yml` with new gtdb information (metadata urls, filenames, tag, new wort manifest,etc)
4. run `snakemake prepare` to cross-check signatures needed  against available wort sigs
5. run `snakemake build` to build the base zipfiles
6. run `snakemake check` to check that these zipfiles have all needed sigs
7. run `snakemake -s release.smk` to build sbt, lca db's from the zipfiles
8. release databases will be in `/group/ctbrowngrp/sourmash-db/{name}-{tag}`, using params you set in `config.yml`
9. update sourmash docs (databases.md) with the new db information

Notes:
- building SBTs requires more memory than any other db. I will add resources to rules after benchmarking (tbd)
