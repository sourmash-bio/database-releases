#! /usr/bin/env python

import ftplib
import sys
import argparse


def list_files(ftp, remotedir, host, server):
    count = 10
    tries = count
    file_list = []
    dir_list = []

    while tries > 0:
        try:
            print(remotedir)
            ftp.cwd(remotedir)
            print(f"\nListing directory: {remotedir}\n")

            # List files and directories in the current directory
            files = ftp.nlst()

            # Iterate through each item in the current directory
            for entry in files:
                if '.' not in entry:  # Only consider directories
                    print(entry + '/')  # Print directory names
                    dir_list.append(entry)
                else:
                    print(entry)  # Print file names
                    file_list.append(entry)
            
            # If no exception occurs, break out of the loop
            break
        except ftplib.error_perm as e:
            print(f"Error: {e}")
            tries -= 1
            if tries == 0:
                print("Out of tries. Exiting.")
                return [], []
            else:
                print(f"Trying again... ({tries} tries left)")
    return file_list, dir_list

def list_dir(ftp, remotedir, host):
    directories = []
    try:
        print(f'Listing directory: {remotedir}')
        with ftplib.FTP(host) as ftp:
            ftp.connect(host)
            ftp.login()
            ftp.cwd(remotedir)
            files = ftp.nlst()
            subfiles = []
            for entry in files:
                if '.' not in entry:  # Only consider directories
                    subdir = remotedir + "/" + entry
                    print(subdir)
                    list_dir(ftp, subdir, host)  # Recursively navigate into subdirectories
                else:
                    print(entry)
                    subfiles.append(entry)
    except ftplib.all_errors as e:
        print(f'FTP error: {e}', file=sys.stderr)
    return subfiles

def main():
    p = argparse.ArgumentParser()

    p.add_argument('host', help='The host name for the files (e.g. ftp.ebi.ac.uk)')
    p.add_argument('path', help='The directory path hosting the files (e.g. pub/databases/AllTheBacteria/Releases/0.1)')
    p.add_argument('-s', '--server', type=str, nargs='?', default=['https'], choices=['ftp','https'], help='The server type hosting the files')
    p.add_argument('-o', '--output', help='The text file containing the full path to the files', required=True)

    args = p.parse_args()

    server = args.server + "://"
    host = args.host + '/'
    path = args.path + "/"

    print(f"Connecting to '{host}' to list directories", file=sys.stderr)

    try:
        with ftplib.FTP(args.host) as ftp:
            ftp.connect(args.host)
            ftp.login()
            file_list, dir_list = list_files(ftp, args.path, args.host, args.server)
    except ftplib.all_errors as e:
        print(f"FTP error: {e}", file=sys.stderr)

    with open(args.output, 'wt') as fp:
        for line in file_list:
            print(server + host + path + line, file=fp)

if __name__ == "__main__":
    main()
