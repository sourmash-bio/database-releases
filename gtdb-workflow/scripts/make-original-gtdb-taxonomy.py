#! /usr/bin/env python

import sys
import argparse
import pandas as pd

def main(args):

    metadata_dfs = []
    for metadata_file in args.metadata_files:
        metadata_info = pd.read_csv(metadata_file, header=0, low_memory=False, sep = "\t")
        filtered_metadata_info = metadata_info[["accession", "gtdb_representative", "gtdb_taxonomy"]]
        filtered_metadata_info["accession"] = metadata_info["accession"].str.replace("RS_", "").str.replace("GB_", "")
        metadata_dfs.append(filtered_metadata_info)

    # Write lineages csv file
    metadata_info = pd.concat(metadata_dfs)
    metadata_info[["superkingdom","phylum","class","order","family","genus","species"]] = metadata_info["gtdb_taxonomy"].str.split(pat=";", expand=True)
    metadata_info.drop(columns=["gtdb_taxonomy"], inplace=True)
    metadata_info.rename(columns={"accession":"ident"}, inplace=True)
    metadata_info.to_csv(args.output, sep = ',', index=False)

    if args.reps_csv:
        reps = metadata_info[metadata_info["gtdb_representative"] == 't']
        reps.to_csv(args.reps_csv, sep=',', index=False)


def cmdline(sys_args):
    "Command line entry point w/argparse action."
    p = argparse.ArgumentParser()
    p.add_argument("--metadata-files", nargs="+", help="gtdb metadata files")
    p.add_argument("-o", '--output',  help="output lineages csv")
    p.add_argument("-r", '--reps-csv',  help="also output representative lineages csv")
    args = p.parse_args()
    return main(args)

if __name__ == '__main__':
    returncode = cmdline(sys.argv[1:])
    sys.exit(returncode)
