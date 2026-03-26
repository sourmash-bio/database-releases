#! /usr/bin/env python

# modified from https://github.com/michalbukowski/fetch-genomes/blob/main/fetch_genomes.py

import os
import argparse
import sys
import csv
import urllib.request
import hashlib
import sourmash
from sourmash import sourmash_args
import screed
import gzip

def check_gz_file(file_path, url, row):
    count = 10
    download_tries = count

    try:
        with gzip.open(file_path, 'rb') as f:
            for _ in f:
                pass
        print(f"{file_path} is OK")
    except Exception as e:
        print(f"{file_path} is not OK: {e}")
        os.remove(file_path)

        while download_tries > 0:
            try:
                urllib.request.urlretrieve(url, file_path)
                print(f"Successful removal and re-download of {file_path}. Tries remaining: {download_tries -1}")
                with gzip.open(file_path, 'rb') as f:
                    for _ in f:
                        pass
                print(f"{file_path} is OK after redownload. Final remaining tries: {download_tries - 1} of {count}")
                break  # Exit the loop if download and check are successful
            except Exception as e:
                print(f"Error downloading {url} for file {file_path}: {e}. Tries left: {download_tries - 1}")
                download_tries -= 1
                if download_tries == 0:
                    print("Download failed after multiple attempts.")
                    return row # Exit the function if download fails after multiple attempts

# Data that can be obtained from NCBI GenBank for a given genomic assembly,
# see parse_args function for more information.
assembly_formats = {
    'fna'  : 'genomic.fna.gz',
    'faa'  : 'protein.faa.gz',
    'gbff' : 'genomic.gbff.gz',
    'gff'  : 'genomic.gff.gz',
    'rna'  : 'rna_from_genomic.fna.gz',
    'cds'  : 'cds_from_genomic.fna.gz',
    'prot' : 'translated_cds.faa.gz'
}

md5sums_fname = 'md5checksums.txt'

def read_in_txt(file):
    sketch_info = []
    with open(file, 'rt') as fp:
        r = csv.reader(fp, delimiter='\t')
        for row in r:
            sketch_info.append(row)
    return sketch_info

def sketch_name(accession, ext='sig'):
    sketch_fp = accession + '.' + ext
    return sketch_fp

def sketch_file(input_fp, row, output_dir, ksize=[21,31,51], num_hashes=0, scale=1000, abund=False):
    
    accession = row[0]
    organism_name = row[2]
    infraspecific_name = row[3]
    asm_name = row[4]

    elements = []

    if accession != 'na':
        elements.append(accession)
    if organism_name != 'na':
        elements.append(organism_name)
    if infraspecific_name != 'na':
        elements.append(infraspecific_name)
    
    result = ' '.join(elements)
    
    if asm_name != 'na':
        result = result + ', ' + asm_name

    mh_list = []
    for k in ksize:
        mh = sourmash.MinHash(n=num_hashes, scaled=scale, ksize=k, track_abundance=abund)

        for record in screed.open(input_fp):
            mh.add_sequence(record.sequence, force=True)
        mh_list.append(mh)

    sig1 = sourmash.SourmashSignature(mh_list[0], name=result)
    sig2 = sourmash.SourmashSignature(mh_list[1], name=result)
    sig3 = sourmash.SourmashSignature(mh_list[2], name=result)

    sketch_out = f"{output_dir}/{accession}.sig"

    with sourmash.sourmash_args.SaveSignaturesToLocation(sketch_out) as save_sig:
        save_sig.add(sig1)
        save_sig.add(sig2)
        save_sig.add(sig3)

    print(f"Signature save to {sketch_out}")

def fetch_genomes(urls, formats, output_dir, remove_files, genomes_only):
    '''Fetches genomes by sending FTP requests via urllib. Arguments:
       urls       -- a list of URLs pointing to the genomes
       formats    -- formats of data to be retrieved
       output_dir -- a directory for the data to be saved to
    '''

    not_found = [] #0
    fetched   = 0
    existing  = 0 

    for row in urls:

        url = row[1]
        if url.startswith('https://'):
            url = 'ftp://' + url[8:]
        parts = url.rstrip('/').split('/')
        asm_full_name = parts[-1]

        done = [False] * len(formats)
        for i, fmt in enumerate(formats):
            suffix  = assembly_formats[fmt]
            fnamein = f'{asm_full_name}_{suffix}'
            fpathout = f'{output_dir}/{fnamein}'
            if os.path.exists(fpathout):
                if os.path.isfile(fpathout):
                    done[i] = True

        accession = row[0]
        sketch_out = f"{output_dir}/{accession}.sig"

        if all(done):
            existing += len(formats)
            print(f'[INFO] All files requested for {asm_full_name} exist and are files, considered done')
            print(f'[INFO] Skipping {asm_full_name}, already fetched')
            if genomes_only:
                print(f'User selected genomes only. Skipping sketching...')
            elif not os.path.exists(sketch_out):
                sketch_file(fpathout, row, output_dir)  # Sketch the fetched file
            else:
                print(f'Skipping {sketch_out}, already sketched')
            if remove_files:
                os.remove(fpathout)
                print(f"Removing {fpathout} files...")
            continue
        print(f'\n[INFO] Fetching files for {asm_full_name}...')
        
        try:
            res = urllib.request.urlopen(url, timeout=60)
            lines = res.read().decode().rstrip().split('\n')
            flist = [ line.split()[-1] for line in lines ]
        except KeyboardInterrupt as e:
            raise e
        except:
            print(f'[ERROR] Cannot fetch file list from "{url}"')
            print(f'[WARNING] Skipping assembly {asm_full_name}...')
            continue
        print(f'[INFO] There is {len(flist)} files at "{url}"')

        ## Fetch the` file with MD5 sums for genome files, if unsuccessful, yield
        ## a proper message and continue to next iteration/genome.
        #full_path = f'{url}/{md5sums_fname}'
        #try:
        #    res = urllib.request.urlopen(full_path, timeout=60)
        #    md5sums = res.read().decode().rstrip().split('\n')
        #except KeyboardInterrupt as e:
        #    raise e
        #except:
        #    print(f'[ERROR] Info on MD5 checksums cannot be fetched from "{full_path}"')
        #    print(f'[WARNING] Skipping assembly {asm_full_name}...')
        #    continue
        #md5sums = [ line.split() for line in md5sums ]
        #md5sums = { line[1].lstrip('./') : line[0] for line in md5sums }
        #print(f'[INFO] MD5 checksums for {asm_full_name} successfully fetched')

        old_fetched = fetched
        for fmt in formats:
            suffix  = assembly_formats[fmt]
            fnamein = f'{asm_full_name}_{suffix}'
            fpathin = f'{url}/{fnamein}'
            
            if not fnamein in flist:
                print(f'[ERROR] No such file for {asm_full_name}: "{fpathin}"')
                print(f'[WARNING] Skipping {asm_full_name} assembly file: "{fpathin}"')
                not_found.append(row) # += 1
                continue
            
            fpathout = f'{output_dir}/{fnamein}'
            if os.path.exists(fpathout):
                if os.path.isfile(fpathout):
                    print(f'[INFO] The output path "{fpathout}" exists and is a file, considered done')
                    print(f'[INFO] Skipping {asm_full_name} assembly file: "{fpathin}", already fetched')
                    existing += 1
                else:
                    print(f'[ERROR] The output path "{fpathout}" exists and is not a file')
                    print(f'[WARNING] Skipping {asm_full_name} assembly file: "{fpathin}"')
                continue
            
            #if not fnamein in md5sums:
            #    print(f'[ERROR] Cannot find MD5 checksum for {asm_full_name} assembly file: "{fpathin}"')
            #    print(f'[WARNING] Skipping {asm_full_name} assembly file: "{fpathin}"')
            #    continue
            
            try:
                res = urllib.request.urlopen(fpathin, timeout=60)
                content = res.read()
            except:
                print(f'[ERROR] {asm_full_name} assembly file cannot be fetched from: "{fpathin}"')
                print(f'[WARNING] Skipping {asm_full_name} assembly file: "{fpathin}"')
                continue
            print(f'[INFO] {asm_full_name} assembly file "{fpathin}" successfully fetched')
            
            #md5sum = hashlib.md5(content).hexdigest()
            #if md5sum == md5sums[fnamein]:
            #    print(f'[INFO] Correct MD5 checksum ({md5sum}) for {asm_full_name} assembly file: "{fpathin}"')
            #else:
            #    print(f'[ERROR] Incorrect MD5 checksum ({md5sum}) ' + '\n'
            #          f'for {asm_full_name} assembly file ({md5sums[fnamein]}): "{fpathin}"')
            #    print(f'[WARNING] Skipping {asm_full_name} assembly file: "{fpathin}"')
            #    continue
            
            tmpfpathout = f'{output_dir}/{fnamein}'
            try:
                with open(tmpfpathout, 'wb') as f:
                    f.write(content)
            except:
                print(f'[ERROR] Cannot save to "{fpathout}" the {asm_full_name} assembly file: "{fpathin}"')
                print(f'[WARNING] Skipping {asm_full_name} assembly file: "{fpathin}"')
                continue
            
            try:
                os.rename(tmpfpathout, fpathout)
            except:
                print(f'[ERROR] Cannot save to "{fpathout}" the {asm_full_name} assembly file: "{fpathin}"')
                print(f'[WARNING] Skipping {asm_full_name} assembly file: "{fpathin}"')
                os.remove(tmpfpathout)
            else:
                print(f'[INFO] {asm_full_name} assembly file "{fpathin}" successfully saved to "{fpathout}"')
                fetched += 1

        failed_row = check_gz_file(fpathout, fpathin, row)
        if failed_row is not None:
            not_found.append(failed_row)

        if os.path.exists(fpathout):
            if genomes_only:
                print(f'{fpathout} found! Skipping sketching... for now!')
            elif os.path.exists(sketch_out):
                print(f'{sketch_out} already exists! Skipping...')
            else:
                sketch_file(fpathout, row, output_dir)  # Sketch the fetched file
        else:
            print(f'{fpathout} not found and not sketched :(')
            
        if remove_files:
            os.remove(fpathout)
            print(f"Removing {fpathout} files...")

    total = len(urls) * len(formats)
    left  = total - existing - len(not_found) - fetched
    print(f'\n[INFO] Fetched {fetched} files out of {total} inferred ' + \
          f'(already existing: {existing}, not found on site: {len(not_found)}')
    if left > 0:
        print(f'\n[WARNING] {left} files are still to be fetched')
    else:
        print('[INFO] All files have been successfully fetched')
    print('[INFO] Fetching genomes has been completed')
    return not_found

def main():
    p = argparse.ArgumentParser()
    p.add_argument('-i', '--input', help='The input file containing only the https links to NCBI')
    p.add_argument('-f', '--format', type=str, nargs='+', default=['fna'], choices=assembly_formats.keys(), help='The file format you would like to acquire')
    p.add_argument('-o', '--output-dir', help='The location to send the downloaded files')
    p.add_argument('-r', '--remove-files', action='store_true', help='Remove the intermediate files')
    p.add_argument('-g', '--genomes-only', action='store_true', help='Only download the intermediate files and skip sketching')
    p.add_argument('-m', '--missing-files', nargs='?', help='Create a new file with the missing files that were not downloaded or sketched')

    args = p.parse_args()

    sketch_info = read_in_txt(args.input)

    #for line in range(len(sketch_info)):
    #    print(sketch_info[line])

    missing_files = fetch_genomes(urls = sketch_info, formats = args.format, output_dir = args.output_dir, remove_files=args.remove_files, genomes_only=args.genomes_only)

    if args.missing_files:
        if len(missing_files) > 0:
            with open(args.missing_files, 'wt') as fp:
                for line in missing_files:
                    fp.write(line + '\n')
            print("Missing files found and written to:", args.missing_files)
        else:
            print(f"No missing files!!! Nothing to write to {args.missing_files}")
    elif len(missing_files) > 0:
        print("Missing files found, but '--missing-files' argument not provided. File of missing not created.")

if __name__ == '__main__':
    sys.exit(main())
# Example usage:
#urls = [
#    "https://example.com/genomes/genome1.zip",
#    "https://example.com/genomes/genome2.zip",
#    "https://example.com/genomes/genome3.zip"
#]
#formats = ["fasta", "gff"]
#output_dir = "output"
#fetch_genomes(urls, formats, output_dir)
#
