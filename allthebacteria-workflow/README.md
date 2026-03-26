A sourmash database for the [AllTheBacteria database](https://doi.org/10.1101/2024.03.08.584059)

The assembly files were all sketched to create a single sourmash database. 

Example release:

- https://ftp.ebi.ac.uk/pub/databases/AllTheBacteria/Releases/0.2/
- https://github.com/AllTheBacteria/AllTheBacteria/releases/tag/v0.2

## Executing 

Note: To run the 5 sample test, simply write `test` in the `output_directory:` section of the config file. This must be run in an srun (no `--profile` works at this time).

Create a list of assembly file paths at the ftp server
```
./scripts/ftp_link_list.py ftp.ebi.ac.uk pub/databases/AllTheBacteria/Releases/0.2/assembly -s ftp -p allthebacteria-r0.2-assembly-paths.txt
```

Run the snakemake workflow
```
snakemake -s allthebacteria.smk --use-conda --rerun-incomplete -j 10
```
> A rough estimate of resources required for completing this workflow:
> set to run for 3 days with 10 cpus and 80 GB mem

## Sanity check?

By checking that the total amount of zip files created match the amount expected
```
find allthebacteria-r0.2-sigs/ -maxdepth 2 -type f -name "*.zip" -exec echo "{}" \; | wc -l
```
Returns the count of individual zip files that were created.
For release 0.2, there were `665`.

Which matches `cat allthebacteria-r0.2-assembly-paths.txt | wc -l`

For renaming purposes `find ./ -type f -name 'missing.csv' | while read file; do     if [ $(wc -l < "$file") -gt 1 ]; then         echo "$file";     fi; done` to find the missing.csv with values
