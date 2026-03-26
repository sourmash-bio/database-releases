#!/bin/bash

Help()
{
  echo "Add description of the script functions here."
  echo
  echo "Syntax: [-d|h]"
  echo "options:"
  echo "-d    Directory that contains gzip files to check" 
}

while getopts ":hd:" option; do
  case $option in
    h) #display Help
       Help
       exit;;
    d) # Enter a dir
       directory=$OPTARG;;
   \?) #invalid option
       echo "Error: Invalid option."
       echo "See available arguments with `-h`"
       exit;;
  esac
done

echo "Checking .gz files for EOF failures..."
echo

> gzip_failures.txt
> gzip_checked_files.txt

total=$(find "$directory" -type f -name "*.gz" | tee gzip_checked_files.txt | wc -l)
echo "Total .gz files to check: $total"
echo

progress_file=$(mktemp)

cat gzip_checked_files.txt |
 xargs -P 100 -I {} bash -c '
    file="$1"
    progress_file="$2"
    total="$3"

    echo "Checking: $file"

    if gzip -t "$file" 2>/dev/null; then
      echo "    PASSED: $file"
    else
      echo "    FAILED: $file"
      echo "$file" >> gzip_failures.txt
    fi

    echo 1 >> "$progress_file"
    count=$(wc -l < "$progress_file")
    echo "    Progress: $(( 100 * count / total ))% ($count / $total)"
  ' bash {} "$progress_file" "$total"

total2=$(wc -l < gzip_checked_files.txt)
failures=$(wc -l < gzip_failures.txt)

[ "$total" -eq "$total2" ] || { echo "Assertion failed: $total != $total2"; exit 1; }

if (( total > 0 )); then
  percent=$(( 100 * failures / total ))
else
  percent=0
fi

echo
echo "Total checked files: $total"
echo "Total failed files: $failures ($percent%)"

echo "Files with errors and should be removed"
xargs -a gzip_failures.txt echo rm --

while read -r file; do
    if [ -e "$file" ]; then
        echo "Not deleted: $file"
    else
        echo "Deleted: $file"
    fi
done < gzip_failures.txt

