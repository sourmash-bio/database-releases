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
    p.add_argument('assembly_summary_files', nargs='+')
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

    for filename in args.assembly_summary_files:
        print(f"reading assembly summary file from '{filename}'")
        r = csv.reader(open(filename, newline=""), delimiter='\t')

        count = 0
        for row in r:
            if not row: continue
            if row[0][0] == '#':
                continue

            count += 1

            acc = row[0]

#            taxid = row[5]
#            taxid = int(taxid)
#
#            lin_dict = taxfoo.get_lineage_as_dict(taxid, want_taxonomy)
#            if not lin_dict:
#                print(f"WARNING: taxid {taxid} not in taxdump files. Producing empty lineage.")

            original_taxid = row[5]
            try:
                taxid = int(original_taxid)
            except ValueError:
                print(f"WARNING: invalid taxid '{original_taxid}' in row: {row}")
                continue
            
            lin_dict = taxfoo.get_lineage_as_dict(taxid, want_taxonomy)
            
            if not lin_dict or not lin_dict.get('species'):
                # fallback using organism_name and infraspecific_name
                organism_name = row[7]
                infraspecific_name = row[8] if len(row) > 8 and row[8].lower() != 'na' else None
            
                fallback_taxid = taxfoo.get_taxid_from_organism_names(organism_name, infraspecific_name)
                if fallback_taxid:
                    print(f"    INFO: fallback succeeded for {acc}: {organism_name} ({infraspecific_name}) -> taxid {fallback_taxid}")
                    taxid = fallback_taxid
                    lin_dict = taxfoo.get_lineage_as_dict(taxid, want_taxonomy)
                else:
                    print(f"    WARNING: taxid {original_taxid} not found and fallback failed for organism '{organism_name}'.")

            row = [acc, taxid]
            for rank in want_taxonomy:
                name = lin_dict.get(rank, '')
                row.append(name)

            w.writerow(row)

        print('output {} lineages'.format(count))


if __name__ == '__main__':
    sys.exit(main())
