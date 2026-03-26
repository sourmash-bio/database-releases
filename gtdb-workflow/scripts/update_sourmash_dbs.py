#! /usr/bin/env python

import sys
import argparse
import csv
import os
import time
import re
from collections import defaultdict
from sourmash import manifest
import urllib.request
from functools import lru_cache
import traceback

class GeneralManifestHandler:
    def __init__(self, filename):
        self.filename = filename
        self.rows = []

    def read_csv(self):
        with open(self.filename, 'r') as csvfile:
            csvreader = csv.DictReader(csvfile)
            for row in csvreader:
                row['name'] = row.pop('ident', None)
                self.rows.append(row)

    def find_ident_header(self):
        with open(self.filename, 'r') as fp:
            for line in fp:
                if 'ident' in line:
                    print(f'Ident found in header: {line.strip()}')
                    return line.strip()
        print('Ident not found in header.')
        return None

def extract_urls(row):
    url_pattern = r'https?://\S+'
    for value in row:
        urls = re.findall(url_pattern, value)
        if urls:
            return urls[0]  # Only returns the first URL found
    return None

@lru_cache(maxsize=1024)  # Cache up to 1024 URLs
def generate_urls(accession, verbose=False, base_url=False):
    accsplit = accession.split("_", 1)
    if len(accsplit) != 2:
        raise ValueError(f"ERROR: '{accession}' should have precisely one underscore!")

    db, acc = accsplit
    number, version = acc.split(".") if '.' in acc else (acc, '1')
    number = "/".join([number[i:i + 3] for i in range(0, len(number), 3)])
    url = f"https://ftp.ncbi.nlm.nih.gov/genomes/all/{db}/{number}"

    if verbose:
        print(f"Opening directory: {url}", file=sys.stderr)

    try:
        with urllib.request.urlopen(url) as response:
            all_names = response.read().decode("utf-8")
    except urllib.error.URLError as e:
        print(f"Failed to open {url}: {e}", file=sys.stderr)
        return None

    if verbose:
        print("Done!", file=sys.stderr)

    for line in all_names.splitlines():
        if line.startswith('<a href='):
            name = line.split('"')[1][:-1]
            db_, acc_, *_ = name.split("_")
            if db_ == db and acc_.startswith(acc):
                if base_url:
                    return f"{url}/{name}"
                else:
                    return (
                        f"{url}/{name}/{name}_genomic.fna.gz",
                        f"{url}/{name}/{name}_assembly_report.txt",
                    )

    return None

def get_suffix(name):
    ident = name.split(' ')[0]
    try:
        assert ident.startswith('GC')
    except AssertionError:
        _, _, tb = sys.exc_info()
        traceback.print_tb(tb) # Fixed format
        tb_info = traceback.extract_tb(tb)
        filename, line, func, text = tb_info[-1]
        print('An error occurred on line {} in statement {}'.format(line, text))
        print(f'{ident}')
        exit(1)
    return ident[3:]

def get_suffix_no_version(name):
    suffix = get_suffix(name)
    assert '.' in suffix
    return suffix.split('.')[0]

def get_float_version(name):
    suffix = get_suffix(name)
    assert '.' in suffix
    return suffix.split('.')[1]

def row_generator(filename, quiet=False):
    with open(filename, 'rt') as fp:
        for i, line in enumerate(fp, start=1):
            if not quiet and i % 1000 == 0:
                print(f"Reading line {i}", end='\r', flush=True)

            line = line.strip().split('\t')
            if line[0].startswith('#'):
                continue

            accession = f'"{line[0]}"' if ',' in line[0] else (line[0] if len(line) > 0 else None)
            organism_name = f'"{line[7]}"' if ',' in line[7] else (line[7] if len(line) > 7 else None)
            infraspecific_name = f'"{line[8]}"' if ',' in line[8] else (line[8] if len(line) > 8 else None)
            asm_name = f'"{line[15]}"' if ',' in line[15] else (line[15] if len(line) > 15 else None)
            ref_acc = f'"{line[17]}"' if ',' in line[17] else (line[17] if len(line) > 17 else None)
            comparison = line[18] if len(line) > 18 else None
            url = extract_urls(line) if extract_urls(line) is not None else (line[19] if len(line) > 19 else None)
            if url is not None:
                url = f'"{url}"' if ',' in url else url

            yield (accession, organism_name, infraspecific_name, asm_name, ref_acc, url, comparison)

def set_generator(filename):
    with open(filename, 'rt') as fp:
        for i, line in enumerate(fp, start=1):
            if i % 1000 == 0:
                print(f"Reading line {i}", end='\r', flush=True)

            line = line.strip().split('\t')
            if line[0].startswith('#'):
                continue

            accession = line[0]
            rep_status = line[4] if len(line) > 4 else None
            ref_acc = line[17] if len(line) > 17 else None
            comparison = line[18] if len(line) > 18 else None

            yield (accession, rep_status, ref_acc, comparison)

def load_summary(filename, summary_type):
    if summary_type == 'assembly':
        good_idents_dict = defaultdict(lambda: {'gca_version': None, 'gcf_version': None, 'refseq_acc': None, 'comparison': None})
    if summary_type == 'historic':
        bad_idents_dict = defaultdict(list)

    with open(filename, 'rt') as fp:
        print("Reading assembly file content...")
        for i, line in enumerate(fp, start=1):
            if i % 1000 == 0:
                print(f"Processing line {i}", end='\r', flush=True)

            line = line.strip().split('\t')
            if line[0].startswith('#'):
                continue
            
            accession = line[0]
            assert accession.startswith('GCA')
            
            suffix = get_suffix(accession)
            prefix = accession.split('_')[0]
            gca_version = get_float_version(accession)
            gcf_version = None

            ref_acc = line[17] if len(line) > 17 else None
            if ref_acc != 'na': # ensure that the accessions are identical where it counts
                assert ref_acc.startswith('GCF')
                assert get_suffix_no_version(accession) == get_suffix_no_version(ref_acc)
                gcf_version = get_float_version(ref_acc)

            comparison = line[18] if len(line) > 18 else None

            suffix_no_version = get_suffix_no_version(accession)

            if summary_type == 'assembly':
                good_idents_dict[suffix_no_version]['gca_version'] = gca_version
                good_idents_dict[suffix_no_version]['refseq_acc'] = ref_acc
                good_idents_dict[suffix_no_version]['gcf_version'] = gcf_version
                good_idents_dict[suffix_no_version]['comparison'] = comparison

            if summary_type == 'historic':

                assembly, version = suffix.split('.')
                bad_idents_dict[assembly].append(version)

    if summary_type == 'assembly':
        return good_idents_dict
    elif summary_type == 'historic':
        return bad_idents_dict

def filter_manifest(old_mf, good_idents_dict, bad_idents_dict):
    keep_rows = []
    removed_list = []
    updated_from_list = []
    updated_to_set = set()
    bad_set = set()

    #bad_idents = set(key + '.' + value[0] for key, values in bad_idents_dict.items() for value in values)

    for row in old_mf.rows:
        
        name = row.get('name')
        if not name:
            print(f"Row missing 'name': {row}")
            continue  # Skip rows without 'name'
        mf_prefix = name.split('_')[0]
        mf_ident = get_suffix_no_version(name) # the ident number are identical for GCA and GCF
        mf_version = get_float_version(name)

        if mf_ident in good_idents_dict:

            if mf_prefix == 'GCF':
                ref_acc = good_idents_dict[mf_ident].get('refseq_acc')

                if ref_acc and ref_acc != 'na':
                    gcf_version = good_idents_dict[mf_ident].get('gcf_version')

                    if mf_version == gcf_version:
                        keep_rows.append(row)
                    else:
                        updated_from_list.append(name)
                        updated_to_set.add(f'GCF{mf_ident}.{gcf_version}')
                else:
                    # Use GCA version if GCF is not in assembly summary
                    gca_version = good_idents_dict[mf_ident].get('gca_version')

                    if mf_version == gca_version:
                        keep_rows.append(row)
                    else:
                        updated_from_list.append(name)
                        updated_to_set.add(f'GCA{mf_ident}.{gca_version}')

            elif mf_prefix == 'GCA':
                gca_version = good_idents_dict[mf_ident].get('gca_version')

                if mf_version == gca_version:
                    keep_rows.append(row)
                else:
                    updated_from_list.append(name)
                    updated_to_set.add(f'GCA{mf_ident}.{gca_version}')

            else:
                print(f"Manifest idents do not contain either 'GCA' or 'GCF' identifiers.")
                print(f"Exiting...")
                sys.exit(1)

        else: # Manifest idents are not in assembly summary (i.e. removed from the current genbank)
            removed_list.append(name)

        # manifest item is in assembly historic (i.e. removed/suspressed)
        if mf_ident in bad_idents_dict:
           if mf_version == bad_idents_dict[mf_ident]:
               bad_set.add(name)

    return keep_rows, removed_list, updated_from_list, updated_to_set, bad_set

def write_links_output(lists, links):
    total = sum(len(lst) for _, lst in lists)
    n = 0

    with open(links, 'wt') as fp:
        header = ["accession", "name", "ftp_path"]
        fp.write(','.join(header) + '\n')

        for lst_name, lst in lists:
            print(f"Writing from {lst_name} now...")
            for row in lst:
                if n % 10 == 0:
                    print(f'...Writing {links}: Line {n} of {total}', end='\r', flush=True)

                if lst_name.startswith("GCA"):
                    accession = row[0]
                    url = row[5]
                elif lst_name.startswith("GCF"):
                    accession = row[4]
                    comparison = row[6]

                    if comparison == 'identical':
                        url = row[5]
                    else:
                        url = generate_urls(accession, base_url=True)
                organism_name = row[1]
                infraspecific_name = row[2]
                asm_name = row[3]

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
                    line = f"{accession},{name},{url}\n"
                    fp.write(line)

                n += 1

            print(f"Wrote {n}/{total} rows in {lst_name} now...      ")
        print(f'\n...Wrote {links}: Line {n} of {total}  ')

def main():
    p = argparse.ArgumentParser()

    p.add_argument('old_mf', nargs='?', help='existing sourmash database manifest or lineage file (i.e. picklist output from `sig check` using lineage file)')
    p.add_argument('--report', nargs='?', help='details of removed etc., for humans')
    p.add_argument('-o', '--output', nargs='?', help='manifest cleansed of the impure')
    p.add_argument('-u', '--updated-version', help='Output a CSV file where each line is the updated versions of genomes existing in old manifest')
    p.add_argument('-m', '--missing-genomes', help='Output a CSV file where each line is a missing genome from old manifest when compared to current database')
    p.add_argument('-l', '--all-links', help='Output a CSV file of the full input manifest with updated versions')
    p.add_argument('-a', help='the Genbank assembly summary text file')
    p.add_argument('-b', help='the Genbank assembly summary history text file')

    args = p.parse_args()

    print(f"\nLoading assembly summary from '{args.a}'")
    good_idents_dict = load_summary(args.a, summary_type = 'assembly')
    print(f"Loaded {len(good_idents_dict)} identifiers with their individual {', '.join(list(sorted({key for d in good_idents_dict.values() for key in d.keys()})))} information")

    print(f"\nLoading historical summary from '{args.b}'")
    bad_idents_dict = load_summary(args.b, summary_type = 'historic')
    print(f"Loaded {len(bad_idents_dict)} identifiers with {sum(len(values) for values in bad_idents_dict.values())} total versions across the identifiers")

    ident = None
    new_mf = None

    try:
        print(f"\nTrying to load Sourmash Manifest from {args.old_mf}...")
        old_mf = manifest.BaseCollectionManifest.load_from_filename(args.old_mf)
        print(f"Loaded manifest with {len(old_mf.rows)} rows")

        keep_rows, removed_list, updated_from_list, updated_to_set, bad_set = filter_manifest(old_mf, good_idents_dict, bad_idents_dict)

        new_mf = manifest.CollectionManifest(keep_rows)

    except (ValueError, KeyError) as e:
        print(f"\nError when processing Sourmash Manifest: {e}")
        print("Attempting to find 'ident' in header...")

        old_mf = GeneralManifestHandler(args.old_mf)
        ident = old_mf.find_ident_header()
        print(f"Using 'ident' column in {args.old_mf}")

        if ident:
            old_mf.read_csv()

            print(f"\nLoaded manifest with {len(old_mf.rows)} rows")
            keep_rows, removed_list, updated_from_list, updated_to_set, bad_set = filter_manifest(old_mf, good_idents_dict, bad_idents_dict)

        else:
            print("\nNo Sourmash Manifest or 'ident' column found... \nExiting script")
            sys.exit(1)

    # Create a list of the possible new genomes from assembly summary
    new_list = []
    keep_rows_no_version_set = {get_suffix_no_version(row['name']) for row in keep_rows}
    updated_to_no_ident_set = {get_suffix_no_version(item) for item in updated_to_set}
    for k in good_idents_dict.keys():
        if k not in keep_rows_no_version_set:
            if k not in updated_to_no_ident_set:
                new_list.append(k)

    if args.missing_genomes or args.updated_version or args.all_links:
        print('\nWriting link files...')
        print("Reading assembly summary file...")
        good_doc_gen_list = list(row_generator(args.a))

        if args.missing_genomes: #this is only designed for GCA and genbank databases, including GCF will yield assert errors
            kept_set = {row['name'].split(' ')[0] for row in keep_rows}

            gca_list = [row for row in good_doc_gen_list if row[0] not in kept_set and row[0] not in updated_to_set]

            assert len(new_list) == len(gca_list)

            print(f"Found {len(gca_list)} missing sequences...")

            write_links_output([("GCA_list", gca_list)], args.missing_genomes)

        if args.updated_version:

            gca_list = [row for row in good_doc_gen_list if row[0] in updated_to_set]

            gcf_list = [row for row in good_doc_gen_list if row[4] in updated_to_set]

            expected_count = len(updated_to_set)
            actual_count = len(gca_list) + len(gcf_list)
            
            print(f"Expected {expected_count} sequences to update")
            print(f"Actual found sequences to update: {actual_count}")
            print(f"GenBank (GCA) = {len(gca_list)} | RefSeq (GCF) = {len(gcf_list)}")
            print(f"Missing sequences? {expected_count - actual_count}")

            if expected_count != actual_count:
                column_0_set = set(row[0] for row in good_doc_gen_list)
                column_4_set = set(row[4] for row in good_doc_gen_list)

                # Unite sets
                combined_set = column_0_set | column_4_set

                # Find missing by subtracting sets
                missing_from_lists = updated_to_set - combined_set

                # Print the missing elements
                print(f"Number of missing elements: {len(missing_from_lists)}")
                if missing_from_lists:
                    print("Missing elements from lists:")
                    for missing_item in missing_from_lists:
                        print(missing_item)

            write_links_output([("GCA_list", gca_list), ("GCF_list", gcf_list)], args.updated_version)

        if args.all_links:
            kept_set = {row['name'].split(' ')[0] for row in keep_rows}

            gca_list = [row for row in good_doc_gen_list if row[0] in kept_set or row[0] in updated_to_set]
            gcf_list = [row for row in good_doc_gen_list if row[4] in kept_set or row[4] in updated_to_set]

            write_links_output([("GCA_list", gca_list), ("GCF_list", gcf_list)], args.all_links)

    if args.output:# or args.report:
        with open(args.output, 'w', newline='') as fp:
            if new_mf:
                new_mf.write_to_csv(fp, write_header=True)
            else:
                wr = csv.writer(fp)
                with open(args.old_mf, 'r') as hf:
                    header = next(csv.reader(hf))
                    wr.writerow(header)

                lineage_map = {
                    'ident': 'name',
                    'gtdb_representative': 'gtdb_representative',
                    'superkingdom': 'superkingdom',
                    'phylum': 'phylum',
                    'class': 'class',
                    'order': 'order',
                    'family': 'family',
                    'genus': 'genus',
                    'species': 'species'
                }

                for row in keep_rows:
                    ordered_row = [row[lineage_map[col]] for col in header]
                    wr.writerow(ordered_row)

    n_removed = len(old_mf.rows) - len(keep_rows)

    assert n_removed == len(removed_list) + len(updated_to_set)
    n_changed_version = len(updated_from_list)
    n_suspect_suspension = n_removed - n_changed_version

    creat_time = time.ctime(os.path.getctime(args.a))
    mod_time = time.ctime(os.path.getmtime(args.a))

    print(f"\n\nFrom '{args.a}:")
    print(f"Loaded {len(good_idents_dict)} identifiers")
    print(f"Each contains a unique {', '.join(list(sorted({key for d in good_idents_dict.values() for key in d.keys()})))}")

    print(f"\nFrom '{args.b}':")
    print(f"Loaded {len(bad_idents_dict)} identifiers")
    print(f"Loaded {sum(len(values) for values in bad_idents_dict.values())} total versions across the identifiers")

    print(f"\nFile assembly databases created on {creat_time}")
    print(f"File assembly databases last modified {mod_time}")

    print(f"\nFrom '{args.old_mf}':")
    print(f"Kept {len(keep_rows)} of {len(old_mf.rows)} ({len(keep_rows)/len(old_mf.rows)*100:.2f}%) identifiers.")

    print(f"\nNew manifest '{args.output}':")
    print(f"Kept {len(keep_rows)} identifiers.")
    if args.missing_genomes: print(f"Included {len(new_list)} new genomes by new identifiers.")
    print(f"Removed {n_removed} total identifiers.")
    print(f"Removed {n_changed_version} identifiers because of version change.")
    print(f"Removed {n_suspect_suspension} identifiers because of suspected suspension of the genome.\n")

    if args.report:
        with open(args.report, 'wt') as fp:
            print(f"From {len(old_mf.rows)} in '{args.old_mf}':", file=fp)
            print(f"Kept {len(keep_rows)} ({len(keep_rows)/len(old_mf.rows)*100:.2f}%) in '{args.output}.", file=fp)
            print(f"Removed {n_removed} total.", file=fp)
            print(f"Removed {n_suspect_suspension} identifiers because of suspected suspension of the genome.", file=fp)
            print(f"Removed {n_changed_version} because of changed version.", file=fp)

#            bad_doc_gen = row_generator(args.b, quiet=True)
#            suppressed_versioned = [line for line in bad_doc_gen if get_suffix(line[0]) in bad_set]
#            print(f"---- {len(suppressed_versioned)} included into the bad list category ----", file=fp)
#            for item in suppressed_versioned:
#                print(",".join(str(i) for i in item), file=fp)

            print(f"---- {n_suspect_suspension} removed because presumed guilt ----", file=fp)
            print("\n".join(removed_list), file=fp)

            print(f"---- {n_changed_version} removed because version changed ----", file=fp)
            print("\n".join(updated_from_list), file=fp)

        print(f'... Wrote {args.report}\n')


if __name__ == '__main__':
    sys.exit(main())
