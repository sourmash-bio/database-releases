#! /usr/bin/env python

import sys
import argparse
import csv
import os.path
import time
import sourmash
from sourmash import manifest # also does 'import sourmash'
import re

"""
sourmash sig manifest -o data/gtdb.mf.csv data/gtdb-rs214-k31.zip --no-rebuild
./scripts/munge_mf_with_idents.py data/gtdb.mf.csv -t data/assembly_summary_genbank.txt -s data/assembly_summary_genbank_historical.txt --report report.txt -o clean.gtdb.mf.csv
"""

def extract_urls(row):
    url_pattern = r'https?://\S+'
    for value in row:
        urls = re.findall(url_pattern, value)
        if urls:
            return urls
    # if none are found return none?
    return None 

def get_suffix(name):
    ident = name.split(' ')[0]
    assert ident.startswith('GC')  
    suffix = ident[3:]
    return suffix

def get_suffix_no_version(name):
    ident = name.split(' ')[0]
    suffix = get_suffix(ident)
    assert '.' in suffix
    return suffix.split('.')[0]

def main():
    p = argparse.ArgumentParser()

    # Add command-line arguments with default values from Snakemake
    p.add_argument('old_mf', nargs='?', help='existing sourmash database manifest')
    p.add_argument('--report', nargs='?', help='details of removed etc., for humans')
    p.add_argument('-o', '--output', nargs='?', help='manifest cleansed of the impure')
    p.add_argument('-l', '--links', help='Links to gather the updated versions of genomes')
    p.add_argument('-om', '--output-missing', help='Output a text file where each line is a missing genome from old manifest when compared to current database') 
    p.add_argument('-t', help='the Genbank assembly summary text file')
    p.add_argument('-s', help='the Genbank assembly summary history text file')

    args = p.parse_args()

    good_idents = set()
    good_idents_no_version = set()

    bad_idents = set()

    bad_idents_dict = {}

    with open(args.t, 'rt') as fp:
        # skip all initial lines starting with #
        while True:
            line = next(fp)
            if not line.startswith('#'):
                break

        # create list from good db
        good_doc = [line.strip().split('\t') for line in fp]

        for line in good_doc:
            accession = line[0]
            assert accession.startswith('GC')
            suffix = get_suffix(accession)
            good_idents.add(suffix)

            suffix_no_version = get_suffix_no_version(accession)
            good_idents_no_version.add(suffix_no_version)

    with open(args.s, "r", newline='') as fp:
        # skip header
        for x in range(2):
            next(fp)
        
        # create list from historical db
        bad_doc = [line.strip().split('\t') for line in fp]

        for line in bad_doc:
            accession = line[0]
            assert accession.startswith('GC')
            suffix = get_suffix(accession)
            bad_idents.add(suffix)

            # Extract the version number from the suffix
            assembly, version = suffix.split('.')

            # Add the suffix and version as key-value pair to the dictionary
            if assembly not in bad_idents_dict:
                bad_idents_dict[assembly] = []

            bad_idents_dict[assembly].append(version)

    assert len(good_idents) == len(good_idents_no_version)

    assert len(bad_idents) == sum([len(v) for v in bad_idents_dict.values()])

    old_mf = manifest.BaseCollectionManifest.load_from_filename(args.old_mf)

    ## now go through and filter

    bad_list = []
    for k in bad_idents_dict:
        for v in bad_idents_dict[k]:
            bad_list.append( k + '.' + v )

    old_version_dict = {k: v for k, v in bad_idents_dict.items() if len(v) > 1}

    versioned_list = []
    for k in old_version_dict:
        for v in old_version_dict[k]:
            versioned_list.append( k + '.' + v )

    removed_list = []
    updated_version_list = []
    keep_rows = []
    n_changed_version = 0
    bad = []
    updated_version_no_ident_list =[]

    for row in old_mf.rows:
        name = row['name']
        mf_ident = get_suffix(name)
        mf_ident_no_version = get_suffix_no_version(name)

        if mf_ident in good_idents:
            keep_rows.append(row)
        else:
            if mf_ident_no_version in good_idents_no_version:
                n_changed_version += 1
                updated_version_list.append(name)
                updated_version_no_ident_list.append(mf_ident_no_version)
            else:
                removed_list.append(name)

        if mf_ident in bad_list:
            bad.append(mf_ident)
        elif mf_ident in versioned_list:
            bad.append(mf_ident)

    if args.output_missing:
        urls = []
        for row in good_doc:
            accession = row[0]
            assert accession.startswith('GC')
            suffix = get_suffix(accession)
    
            if suffix not in keep_rows:
                url = extract_urls(row)  # Extract URLs from the accession, not the entire row
                urls.extend(url)  # Extend the urls list with the extracted URLs
    
        with open(args.output_missing, 'wt') as fp:
            for url in urls:
                print(url, file=fp)

    # Create a list of removed or suspended identifier and their status
    suppressed_versioned = []

    for row in bad_doc:
        name = row[0]
        suffix = get_suffix(name)

        if suffix in bad:
            suppressed_versioned.append(row[0::10])

    gather_ident_list = []

    for row in good_doc:
        accession = row[0]
        gather_ident_no_version = get_suffix_no_version(accession)
        
        if gather_ident_no_version in updated_version_no_ident_list:
            gather_ident_list.append(row)

    if args.links:
        urls = []
        for row in gather_ident_list:
            url = extract_urls(row)
            urls.append(url)
        with open(args.links, 'wt') as fp:
            print("\n".join(urls), file=fp)

    n_removed = len(old_mf) - len(keep_rows)
    n_suspect_suspension = n_removed - n_changed_version
    new_mf = manifest.CollectionManifest(keep_rows)

    creat_time = time.ctime(os.path.getctime(args.t))
    mod_time = time.ctime(os.path.getmtime(args.t)) 

    print(f"\n\nFrom genome assemblies database:", file=sys.stderr)
    print(f"Loaded {len(good_idents)} identifiers from '{args.t}'",
                          file=sys.stderr)
    print(f"(and loaded {len(good_idents_no_version)} identifiers without version number)", file=sys.stderr)
    print(f"File assembly database created on {creat_time}", file=sys.stderr)
    print(f"File assembly database last modified {mod_time}", file=sys.stderr)

    print(f"\nFrom '{args.old_mf}':", file=sys.stderr)
    print(f"Kept {len(keep_rows)} of {len(old_mf)} identifiers.",
            file=sys.stderr)

    print(f"\nFrom '{args.s}':", file=sys.stderr)
    print(f"Kept {len(bad_list)} of {len(bad_idents)} identifiers.", file=sys.stderr)

    print(f"\nNew manifest '{args.output}':", file=sys.stderr)
    print(f"Kept {len(new_mf)} identifiers.", file=sys.stderr)
    print(f"Removed {n_removed} total identifiers.",
            file=sys.stderr)
    print(f"Removed {n_changed_version} identifiers because of version change.",
            file=sys.stderr)
    print(f"Removed {n_suspect_suspension} identifiers because of suspected suspension of the genome.\n\n",
            file=sys.stderr)

    with open(args.output, 'w', newline='') as outfp:
        new_mf.write_to_csv(outfp, write_header=True)

    if args.report:
        with open(args.report, 'wt') as fp:
            print(f"From {len(old_mf)} in '{args.old_mf}':", file=fp)
            print(f"Kept {len(new_mf)} in '{args.output}.", file=fp)
            print(f"Removed {n_removed} total.", file=fp)
            print(f"Removed {n_suspect_suspension} identifiers because of suspected suspension of the genome.",
                  file=fp)
            print(f"Removed {n_changed_version} because of changed version.",
                  file=fp)
            print(f"---- {len(suppressed_versioned)} included into the bad list category ----", file=fp)
            for item in suppressed_versioned:
                print(",".join(str(i) for i in item), file=fp)
            #print(f"\n".join(suppressed_versioned), file=fp)
            print(f"---- {n_suspect_suspension} removed because presumed guilt ----", file=fp)
            print("\n".join(removed_list), file=fp)
            print(f"---- {n_changed_version} removed because version changed ----", file=fp)
            print("\n".join(updated_version_list), file=fp)

if __name__ == '__main__':
    sys.exit(main())
