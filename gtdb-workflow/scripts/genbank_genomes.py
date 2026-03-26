#! /usr/bin/env python
"""
Retrieve genome information for genbank genomes.
"""
import sys
import argparse
import urllib.request
import csv

from lxml import etree


import urllib.request
import sys
from functools import lru_cache

@lru_cache(maxsize=1024)  # Cache up to 1024 URLs
def url_for_accession(accession, verbose=False, base_url=False):
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

def get_taxid_from_assembly_report(url):
    print(f"opening assembly report: {url}", file=sys.stderr)
    with urllib.request.urlopen(url) as response:
        content = response.read()
    print("done!", file=sys.stderr)

    content = content.decode("utf-8").splitlines()
    for line in content:
        if "Taxid:" in line:
            line = line.strip()
            pos = line.find("Taxid:")
            assert pos >= 0
            pos += len("Taxid:")
            taxid = line[pos:]
            taxid = taxid.strip()
            return taxid

    assert 0


def get_tax_name_for_taxid(taxid):
    tax_url = (
        f"https://www.ncbi.nlm.nih.gov/taxonomy/?term={taxid}&report=taxon&format=text"
    )
    print(f"opening tax url: {tax_url}", file=sys.stderr)
    with urllib.request.urlopen(tax_url) as response:
        content = response.read()

    print("done!", file=sys.stderr)

    root = etree.fromstring(content)
    notags = etree.tostring(root).decode("utf-8")
    if notags.startswith("<pre>"):
        notags = notags[5:]
    if notags.endswith("</pre>"):
        notags = notags[:-6]
    notags = notags.strip()

    return notags


def main():
    p = argparse.ArgumentParser()
    p.add_argument("accession")
    p.add_argument("-o", "--output")
    args = p.parse_args()

    fieldnames = ["ident", "genome_url", "assembly_report_url", "display_name"]
    fp = None
    if args.output:
        fp = open(args.output, "wt")
        w = csv.DictWriter(fp, fieldnames=fieldnames)
    else:
        w = csv.DictWriter(sys.stdout, fieldnames=fieldnames)
    w.writeheader()

    ident = args.accession

    genome_url, assembly_report_url = url_for_accession(ident)
    taxid = get_taxid_from_assembly_report(assembly_report_url)
    tax_name = get_tax_name_for_taxid(taxid)

    d = dict(
        ident=ident,
        genome_url=genome_url,
        assembly_report_url=assembly_report_url,
        display_name=tax_name,
    )

    w.writerow(d)
    print(f"retrieved for {ident} - {tax_name}", file=sys.stderr)

    if fp:
        fp.close()

    return 0


if __name__ == "__main__":
    sys.exit(main())
