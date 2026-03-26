#! /usr/bin/env python

import sys
import argparse
import concurrent.futures
import csv
import gzip
import logging
import os
from collections import defaultdict
from typing import Dict, List, Tuple

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_taxon_name2taxids(names_file: str, limite2SciName: bool) -> Dict[str, List[int]]:
    taxon_name2taxids = defaultdict(list)
    with open(names_file, "rt") as f:
        reader = csv.reader(f, delimiter="\t")
        for row in reader:
            if limite2SciName and row[3] != "scientific name":
                continue
            taxon_name2taxids[row[1].lower()].append(int(row[0]))
    return taxon_name2taxids


def get_ranks(nodes_file: str) -> Dict[int, str]:
    taxon_id2rank = {}
    with open(nodes_file, "rt") as f:
        reader = csv.reader(f, delimiter="\t")
        for row in reader:
            taxon_id2rank[int(row[0])] = row[2]
    return taxon_id2rank


def convert_name_to_taxid(names_file: str, nodes_file: str, print_rank: bool, name_field: int, limite2SciName: bool, out_file: str, threads: int) -> None:
    taxon_name2taxids = get_taxon_name2taxids(names_file, limite2SciName)
    ranks = get_ranks(nodes_file) if print_rank else {}

    def process_line(line: str) -> List[str]:
        fields = line.strip().split("\t")
        taxids = taxon_name2taxids.get(fields[name_field - 1].lower(), [])
        if not taxids:
            return [line, "", "" if not print_rank else ""]
        else:
            return [line, ",".join(map(str, taxids)), ",".join(ranks[taxid] for taxid in taxids) if print_rank else ""]

    with concurrent.futures.ThreadPoolExecutor(max_workers=threads) as executor:
        with open(out_file, "w") as outfile:
            writer = csv.writer(outfile, delimiter="\t")
            for result in executor.map(process_line, sys.stdin):
                writer.writerow(result)


def main():
    parser = argparse.ArgumentParser(description="Convert taxon names to TaxIds")
    parser.add_argument("names_file", help="path to the names.dmp.gz file")
    parser.add_argument("nodes_file", help="path to the nodes.dmp.gz file")
    parser.add_argument("-r", "--show-rank", action="store_true", help="show rank")
    parser.add_argument("-i", "--name-field", type=int, default=1, help="field index of name. data should be tab-separated")
    parser.add_argument("-s", "--sci-name", action="store_true", help="only searching scientific names")
    parser.add_argument("-o", "--out-file", default="out.tsv", help="output file")
    parser.add_argument("-t", "--threads", type=int, default=os.cpu_count(), help="number of threads")
    args = parser.parse_args()

    convert_name_to_taxid(args.names_file, args.nodes_file, args.show_rank, args.name_field, args.sci_name, args.out_file, args.threads)


if __name__ == "__main__":
    main()
