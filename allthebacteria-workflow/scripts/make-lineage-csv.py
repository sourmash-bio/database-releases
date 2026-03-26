#! /usr/bin/env python

from __future__ import print_function
import sys
import argparse
import csv

import ncbi_taxdump_utils


def main():
    want_taxonomy = ['superkingdom', 'phylum', 'class', 'order', 'family', 'genus', 'species', 'strain']
    ictv_taxonomy = ['superkingdom', 'clade', 'subrealm', 'kingdom', 'subkingdom', 'phylum', 'subphylum', 'class', 'subclass', 'order', 'suborder', 'family', 'subfamily', 'genus', 'subgenus', 'species']

    #global want_taxonomy

    p = argparse.ArgumentParser()
    p.add_argument('nodes_dmp')
    p.add_argument('names_dmp')
    p.add_argument('metadata_files', nargs='+')
    p.add_argument('-c', '--check-file', nargs='?', help='A file containing the idents the lineage file should contain')
    p.add_argument('-o', '--output', type=argparse.FileType('wt'))
    p.add_argument('--ictv', action='store_true')
    args = p.parse_args()

    assert args.output

    taxfoo = ncbi_taxdump_utils.NCBI_TaxonomyFoo()

    print(f"loading nodes file '{args.nodes_dmp}'")
    taxfoo.load_nodes_dmp(args.nodes_dmp)
    print(f"loading names file '{args.names_dmp}'")
    taxfoo.load_names_dmp(args.names_dmp)

    want_taxonomy = want_taxonomy if not args.ictv else ictv_taxonomy

    w = csv.writer(args.output)
    w.writerow(['ident', 'taxid'] + want_taxonomy)

    sample_set = {line.strip() for line in open(args.check_file)}
    print(f"Found {len(sample_set)} samples to check against...")

    for filename in args.metadata_files:
        print(f"Reading metadata file from '{filename}'")
        r = csv.reader(open(filename, newline=""), delimiter='\t')
        next(r, None)

        count = 0
        file_length = 0
        for row in r:
            if not row: continue

            count += 1

            if row[0] in sample_set:
                acc = row[0]
                file_length += 1
            else:
                continue

            try:
                taxid = row[100]
                if taxid == '':
                    taxid = None
                else:
                    if ',' in taxid:
                        taxid = taxid.split(',')[0].strip()
                    taxid = float(taxid)
                    taxid = int(taxid)
            except ValueError as e:
                print(f"Error converting taxid: {e}")
                continue

            if taxid is not None:
                lin_dict = taxfoo.get_lineage_as_dict(taxid, want_taxonomy)
                if not lin_dict:
                    print(f"WARNING: taxid {taxid} not in taxdump files. Producing empty lineage.")
            else:
                lin_dict = {}

            row_out = [acc, taxid if taxid is not None else '']
            for rank in want_taxonomy:
                name = lin_dict.get(rank, '')
                row_out.append(name)

            w.writerow(row_out)

        print(f"Found {len(sample_set)} samples to check against...")
        print('Metadata file contained {} lineages'.format(count))
        print("Output file contains {} lineages".format(file_length))


if __name__ == '__main__':
    sys.exit(main())
