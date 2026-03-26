#! /usr/bin/env python

import sys
import argparse
import pandas as pd
from collections import defaultdict


def get_suffix(name):
    ident = name.split(' ')[0]
    assert ident.startswith('GC')
    return ident[3:]

def get_suffix_no_version(name):
    suffix = get_suffix(name)
    assert '.' in suffix
    return suffix.split('.')[0]

def get_float_version(name):
    suffix = get_suffix(name)
    assert '.' in suffix
    return suffix.split('.')[1]

def create_dict(filename):
    genbank_dict = defaultdict(lambda: {'gca_version': None, 'gcf_version': None, 'refseq_acc': None, 'comparison': None})

    with open(filename, 'rt') as fp:
        for i, line in enumerate(fp, start=1):
            if i % 1000 == 0:
                print(f"Reading line {i}", end='\r', flush=True)

            line = line.strip().split('\t')
            if line[0].startswith('#'):
                continue

            accession = line[0]
            assert accession.startswith('GCA')

            gca_version = get_float_version(accession)
            gcf_version = None

            ref_acc = line[17] if len(line) > 17 else None
            if ref_acc != 'na': # ensure that the accessions are identical where it counts
                assert ref_acc.startswith('GCF')
                assert get_suffix_no_version(accession) == get_suffix_no_version(ref_acc)
                gcf_version = get_float_version(ref_acc)

            comparison = line[18] if len(line) > 18 else None

            suffix_no_version = get_suffix_no_version(accession)

            genbank_dict[suffix_no_version]['gca_version'] = gca_version
            genbank_dict[suffix_no_version]['refseq_acc'] = ref_acc
            genbank_dict[suffix_no_version]['gcf_version'] = gcf_version
            genbank_dict[suffix_no_version]['comparison'] = comparison

    return genbank_dict

def update_accessions(metadata_info, update_files):
    """Update accession numbers based on matching suffixes."""
    genbank_dict = create_dict(update_files)

    def update_row(row):
        accession = row['ident']
        prefix = accession.split('_')[0]
        suffix = get_suffix_no_version(row['ident'])
        version = get_float_version(row['ident'])

        if suffix not in genbank_dict:
            return None

        if prefix == "GCA":
            gca_version = genbank_dict[suffix].get('gca_version')

            if version != gca_version:
                print(f"Updating {accession} to version {gca_version}")
                accession = f"GCA{suffix}.{gca_version}"

        elif prefix == "GCF":
            ref_acc = genbank_dict[suffix].get('refseq_acc')

            if ref_acc and ref_acc != 'na':
                gcf_version = genbank_dict[suffix].get('gcf_version')

                if version != gcf_version:
                    print(f"Updating {accession} to version {gcf_version}")
                    accession = f"GCF{suffix}.{gcf_version}"

            else:
                # Use GCA if GCF is not in assembly summary
                gca_version = genbank_dict[suffix].get('gca_version')

                if version != gca_version:
                    print(f"Updating {accession} to version {gca_version}")
                    accession = f"GCA{suffix}.{gca_version}"

        return accession

    # Update with the update_row() function
    metadata_info['ident'] = metadata_info.apply(update_row, axis=1)

    # Drop rows with None in the 'ident' column
    metadata_info = metadata_info.dropna(subset=['ident'])

    return metadata_info

def main(args):

    metadata_dfs = []
    for metadata_file in args.metadata_files:
        metadata_info = pd.read_csv(metadata_file, header=0, low_memory=False, sep = "\t")
        filtered_metadata_info = metadata_info[["accession", "gtdb_representative", "gtdb_taxonomy"]]
        filtered_metadata_info.loc[:, "accession"] = filtered_metadata_info["accession"].str.replace("RS_", "").str.replace("GB_", "")
        metadata_dfs.append(filtered_metadata_info)

    # Write lineages csv file
    metadata_info = pd.concat(metadata_dfs)
    metadata_info[["superkingdom","phylum","class","order","family","genus","species"]] = metadata_info["gtdb_taxonomy"].str.split(pat=";", expand=True)
    metadata_info.drop(columns=["gtdb_taxonomy"], inplace=True)
    metadata_info.rename(columns={"accession":"ident"}, inplace=True)

    if args.update_files:
        metadata_info = update_accessions(metadata_info, args.update_files)

    metadata_info.to_csv(args.output, sep = ',', index=False)

    if args.reps_csv:
        reps = metadata_info[metadata_info["gtdb_representative"] == 't']
        reps.to_csv(args.reps_csv, sep=',', index=False)

def cmdline(sys_args):
    "Command line entry point w/argparse action."
    p = argparse.ArgumentParser()
    p.add_argument("--metadata-files", nargs="+", help="gtdb metadata files")
    p.add_argument("--update-files", help="files used to compare against when updating the database (update_sourmash_dbs.py)")
    p.add_argument("-o", '--output',  help="output lineages csv")
    p.add_argument("-r", '--reps-csv',  help="also output representative lineages csv")
    args = p.parse_args()
    return main(args)

if __name__ == '__main__':
    returncode = cmdline(sys.argv[1:])
    sys.exit(returncode)
