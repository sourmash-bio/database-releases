#! /usr/bin/env python

import sys
import argparse
import csv
import os.path
import time
import re
from collections import defaultdict
from sourmash import manifest


def extract_urls(row):
    url_pattern = r'https?://\S+'
    for value in row:
        urls = re.findall(url_pattern, value)
        if urls:
            return urls[0] #only returns the first and not a list
    return None

def get_suffix(name):
    ident = name.split(' ')[0]
    assert ident.startswith('GC')
    return ident[3:]

def get_suffix_no_version(name):
    suffix = get_suffix(name)
    assert '.' in suffix
    return suffix.split('.')[0]

def load_assembly_summary(filename):
    good_idents = set()
    good_idents_no_version = set()

    with open(filename, 'rt') as fp:
        # skip all initial lines starting with #
        while True:
            line = next(fp)
            if not line.startswith('#'):
                break

        good_doc = [line.strip().split('\t') for line in fp]

        for line in good_doc:
            accession = line[0]
            assert accession.startswith('GC')
            suffix = get_suffix(accession)
            good_idents.add(suffix)
            suffix_no_version = get_suffix_no_version(accession)
            good_idents_no_version.add(suffix_no_version)

    return good_doc, good_idents, good_idents_no_version

def load_historical_summary(filename):
    bad_idents = set()
    bad_idents_dict = defaultdict(list)

    with open(filename, "r", newline='') as fp:
        # Skip the first two lines (i.e. the header)
        for x in range(2):
            next(fp)

        # create list from good db
        bad_doc = [line.strip().split('\t') for line in fp]

        for line in bad_doc:
            accession = line[0]
            assert accession.startswith('GC')
            suffix = get_suffix(accession)
            bad_idents.add(suffix)
            assembly, version = suffix.split('.')
            bad_idents_dict[assembly].append(version)

    return bad_doc, bad_idents, bad_idents_dict

def filter_manifest(old_mf, good_idents, good_idents_no_version, bad_idents_dict):
    keep_rows = []
    removed_list = []
    updated_version_list = []
    updated_version_no_ident_list = set()
    bad_set = set()

    bad_idents = set(key + '.' + value for key, values in bad_idents_dict.items() for value in values)

    for row in old_mf.rows:
        name = row['name']
        mf_ident = get_suffix(name)
        mf_ident_no_version = get_suffix_no_version(name)

        if mf_ident in good_idents:
            keep_rows.append(row)
        else:
            if mf_ident_no_version in good_idents_no_version:
                updated_version_list.append(name)
                updated_version_no_ident_list.add(mf_ident_no_version)
            else:
                removed_list.append(name)

        if mf_ident in bad_idents:
            bad_set.add(mf_ident)

    return keep_rows, removed_list, updated_version_list, updated_version_no_ident_list, bad_set

def write_links_output(gather_ident_list, links):
    total = len(gather_ident_list)
    
    #accession_list = [accession[0] for accession in gather_ident_list]
    with open(links, 'wt') as fp:
        header = ["accession","name","ftp_path"]#,"organism_name","infraspecific_name","asm_name"]
        fp.write(','.join(header) + '\n')
        for n, row in enumerate(gather_ident_list):

            if n % 10 == 0:
                print(f'...Writing {links}: Line {n} of {total}', end='\r', flush=True)

            url = extract_urls(row)
            if url is not None:
                url = f'"{url}"' if ',' in url else url
            accession = f'"{row[0]}"' if ',' in row[0] else row[0]
            organism_name = f'"{row[7]}"' if ',' in row[7] else row[7]
            infraspecific_name = f'"{row[8]}"' if ',' in row[8] else row[8]
            asm_name = f'"{row[15]}"' if ',' in row[15] else row[15]

            elements = []

            if accession != 'na':
                elements.append(accession)
            if organism_name != 'na':
                elements.append(organism_name)
            if infraspecific_name != 'na':
                elements.append(infraspecific_name)
            if asm_name != 'na':
               elements.append(asm_name)
                
            name = ' '.join([e.strip('"') for e in elements])
            if ',' in name:
                name = f'"{name}"'

            if url:
                line = f"{accession},{name},{url}\n"#,{organism_name},{infraspecific_name},{asm_name}\n"
                fp.write(line)

        print(f'...Wrote {links}: Line {n+1} of {total}  ')

def main():
    p = argparse.ArgumentParser()

    p.add_argument('old_mf', nargs='?', help='existing sourmash database manifest')
    p.add_argument('--report', nargs='?', help='details of removed etc., for humans')
    p.add_argument('-o', '--output', nargs='?', help='manifest cleansed of the impure')
    p.add_argument('-u', '--updated-version', help='Output a CSV file where each line is the updated versions of genomes existing in old manifest')
    p.add_argument('-m', '--missing-genomes', help='Output a CSV file where each line is a missing genome from old manifest when compared to current database')
    p.add_argument('-a', help='the Genbank assembly summary text file')
    p.add_argument('-b', help='the Genbank assembly summary history text file')

    args = p.parse_args()

    good_doc, good_idents, good_idents_no_version = load_assembly_summary(args.a)
    bad_doc, bad_idents, bad_idents_dict = load_historical_summary(args.b)

    old_mf = manifest.BaseCollectionManifest.load_from_filename(args.old_mf)

    keep_rows, removed_list, updated_version_list, updated_version_no_ident_list, bad_set = filter_manifest(old_mf, good_idents, good_idents_no_version, bad_idents_dict)

    new_mf = manifest.CollectionManifest(keep_rows)

    n_removed = len(old_mf) - len(keep_rows)
    n_changed_version = len(updated_version_list)
    n_suspect_suspension = n_removed - n_changed_version

    creat_time = time.ctime(os.path.getctime(args.a))
    mod_time = time.ctime(os.path.getmtime(args.a))

    print(f"\n\nFrom genome assemblies database:")
    print(f"Loaded {len(good_idents)} identifiers from '{args.a}'")
    print(f"(and loaded {len(good_idents_no_version)} identifiers without version number)")
    print(f"File assembly database created on {creat_time}")
    print(f"File assembly database last modified {mod_time}")

    print(f"\nFrom '{args.old_mf}':")
    print(f"Kept {len(keep_rows)} of {len(old_mf)} identifiers.")

    print(f"\nFrom '{args.b}':")
    print(f"Kept {len(bad_idents)} of {len(bad_idents)} identifiers.")

    print(f"\nNew manifest '{args.output}':")
    print(f"Kept {len(new_mf)} identifiers.")
    print(f"Removed {n_removed} total identifiers.")
    print(f"Removed {n_changed_version} identifiers because of version change.")
    print(f"Removed {n_suspect_suspension} identifiers because of suspected suspension of the genome.\n\n")

    with open(args.output, 'w', newline='') as fp:
        new_mf.write_to_csv(fp, write_header=True)

    if args.report:
        with open(args.report, 'wt') as fp:
            print(f"From {len(old_mf)} in '{args.old_mf}':", file=fp)
            print(f"Kept {len(new_mf)} in '{args.output}.", file=fp)
            print(f"Removed {n_removed} total.", file=fp)
            print(f"Removed {n_suspect_suspension} identifiers because of suspected suspension of the genome.", file=fp)
            print(f"Removed {n_changed_version} because of changed version.", file=fp)

            suppressed_versioned = [row[0::10] for row in bad_doc if get_suffix(row[0]) in bad_set]
            print(f"---- {len(suppressed_versioned)} included into the bad list category ----", file=fp)
            for item in suppressed_versioned:
                print(",".join(str(i) for i in item), file=fp)

            print(f"---- {n_suspect_suspension} removed because presumed guilt ----", file=fp)
            print("\n".join(removed_list), file=fp)

            print(f"---- {n_changed_version} removed because version changed ----", file=fp)
            print("\n".join(updated_version_list), file=fp)

        print(f'... Wrote {args.report}')

    if args.missing_genomes:
        #convert to set for speed!
        keep_rows_set = {get_suffix(row['name']) for row in keep_rows}
        gather_ident_list = [row for row in good_doc if get_suffix(row[0]) not in keep_rows_set]

        write_links_output(gather_ident_list, args.missing_genomes)

    if args.updated_version:
        gather_ident_list = [row for row in good_doc if get_suffix_no_version(row[0]) in updated_version_no_ident_list]

        write_links_output(gather_ident_list, args.updated_version)


if __name__ == '__main__':
    sys.exit(main())
