#! /usr/bin/env python

import filecmp
import os
import argparse
import sys
import shutil

def check_and_rename(files, new_name):
    # Check if all files exist
    if not all(os.path.exists(file) for file in files):
        raise FileNotFoundError("One or more files do not exist.")

    # Compare files
    all_identical = all(filecmp.cmp(files[0], file) for file in files[1:])
    if all_identical:
        # If files are identical, rename one of them
        shutil.copyfile(files[0], new_name)
        print(f"All files are identical. Copied {files[0]} to {new_name}.")
    else:
        # If files differ, raise an error
        raise ValueError("Files have differences.")

def main():
    p=argparse.ArgumentParser()
    p.add_argument('files', nargs='+', help='The txt files to check')
    p.add_argument('-o', '--output', required=True, help='The output txt file name')
    args = p.parse_args()

    check_and_rename(args.files, args.output)

if __name__ == "__main__":
    sys.exit(main())
