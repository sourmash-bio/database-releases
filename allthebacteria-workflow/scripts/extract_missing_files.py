#! /usr/bin/env python

import tarfile
from collections import defaultdict
import argparse
import os
import csv
import sys

def row_generator(filename):
    with open(filename, 'rt') as fp:
        print("Reading csv file content...")
        for i, line in enumerate(fp, start=1):
            if i % 1000 == 0:
                print(f"Processing csv file: Line {i}", end='\r', flush=True)

            line = line.strip().split(',')

            # Skip header, create index for in_checkfile column, return only lines with true in index
            if i == 1:
                header = line
                in_checkfile_index = header.index('in_checkfile')
                continue

            if line[in_checkfile_index].lower() == 'true':
                yield line

def line_processor(missed_list):
    total = len(missed_list)
    increments = total / 20 # ie 5% increments (100% / 5% = 20)
    missed_dict = defaultdict(list)

    for i, line in enumerate(missed_list):
        if i % int(increments) == 0:
            percentage = (i / total) * 100
            print(f'Processing missing files: {i}/{total} ({percentage:.2f}%)', end='\r', flush=True)
        tar_file = line[0]
        seq_file = line[1]
        missed_dict[tar_file].append(seq_file)

    print('\n')
    print(f'Processed missing files: {total}/{total} (100%)')
    return missed_dict

def load_info_dict(info_files=[]):
    info_dict = {}
    for info_file in info_files:
        print(f'Parsing {info_file}...')
        with open(info_file, 'r') as fp:
            reader = csv.DictReader(fp, delimiter='\t')
            for row in reader:
                info_dict[row['sample']] = row['sample'] + " " + row['Contig_name']
    return info_dict

def manysketch_file(seq_dir, info_dict):
        csv_file = os.path.join(seq_dir, 'manysketch.csv')
        missing_file = os.path.join(seq_dir, 'missing.csv')
        print(f"Writing 'manysketch.csv' and 'missing.csv' files for {seq_dir}")

        with open(csv_file, 'w', newline='') as csvfile, open(missing_file, 'w') as missing_fp:
             csvwriter = csv.writer(csvfile)
             csvwriter.writerow(['name', 'genome_filename', 'protein_filename'])

             filepaths = [os.path.join(seq_dir, f) for f in os.listdir(seq_dir)
                          if os.path.isfile(os.path.join(seq_dir, f)) and
                          f != os.path.basename(csv_file) and f != os.path.basename(missing_file)]
             num_files = len(filepaths)

             increment = int(num_files * 0.05)
             target_line = increment

             line_count = 0

             for filepath in filepaths:
                 filename_ext = os.path.basename(filepath)
                 filename = os.path.splitext(filename_ext)[0]

                 if filename in info_dict:
                     name = info_dict[filename]
                     name = name.replace(',', '')

                     csvwriter.writerow([name, filepath,''])

                     line_count += 1

                     if line_count >= target_line:
                         print(f"Progress: {line_count}/{num_files} lines written")
                         target_line += increment
                 else:
                     if not filename.startswith('.'):
                         missing_fp.write(f"{filename, filepath}\n")

                         csvwriter.writerow([filename, filepath,''])

                     line_count += 1

                     if line_count >= target_line:
                         print(f"Progress: {line_count}/{num_files} lines written")
                         target_line += increment

def main():
    p = argparse.ArgumentParser()

    p.add_argument('missed_files_csv', nargs='?', type=str, help='existing csv file created from find_missing_files.sh')
    p.add_argument('-d', '--data-dir', nargs='?', type=str, help='The directory containing the archive files (must be in "tar.xz" format)')
    p.add_argument('-o', '--output-dir', nargs='?', type=str, help='The name of a directory to store the seq files for processing')

    args = p.parse_args()

    missed_list = list(row_generator(args.missed_files_csv))

    for i in range(6):
        print(missed_list[i])

    missed_dict = line_processor(missed_list)

    for i, (k, v) in enumerate(missed_dict.items()):
        if i >= 6:
            break
        print(f"Key {i+1}: {k}")
        if isinstance(v, list) or isinstance(v, tuple):
            for j, item in enumerate(v):
                if j >= 6:
                    break
                print(f"    Value {j+1}: {item}")
        else:
            print(f"    Value: {v}")

    total_keys = len(missed_dict)
    total_values = sum(len(v) for v in missed_dict.values())

    if os.path.exists(args.output_dir):
         print(f"Storing files in {args.output_dir}")
    else:
         print(f"Creating and Storing files in {args.output_dir}")
         os.makedirs(args.output_dir, exist_ok=True)

    info_dict = load_info_dict([f"{os.path.dirname(args.missed_files_csv)}/sylph.tsv"])

    for i, (k, v) in enumerate(missed_dict.items()):
        print(f"Extracting sequence files from {k}: {i+1}/{total_keys}")
        tar_path = os.path.join(args.data_dir, k)
        dir_path = os.path.join(args.output_dir, os.path.dirname(v[0]))
        print(tar_path, dir_path)

        with tarfile.open(tar_path, 'r:xz') as tar:
            for j, seq_file in enumerate(v):
                #if j >= 6:
                #    break
                print(f"Extracting {seq_file}: {j+1}/{total_values}", end='\r', flush=True)

                try:
                    member = tar.getmember(seq_file)
                    tar.extract(member, path=args.output_dir)
                except KeyError:
                    print(f"    {seq_file} not found in the archive {k}")

            print('\n')
            print(f'Extracted {j+1}/{total_values} from {k}')

        manysketch_file(dir_path, info_dict)


    print(f"Extracted files located in {args.output_dir}")

if __name__ == '__main__':
    sys.exit(main())
