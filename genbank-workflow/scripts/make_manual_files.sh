#!/bin/bash

# Input parameters
OUTPUT_PATH="$1"
DATE="$2"
DOMAIN="$3"

# Check if DATE and DOMAIN are provided
if [ -z "$OUTPUT_PATH" ] || [ -z "$DATE" ] || [ -z "$DOMAIN" ]; then
    echo "Usage: $0 OUTPUT_PATH DATE DOMAIN"
    exit 1
fi

# Define file paths based on inputs
MISSING="${OUTPUT_PATH}/data/missing-genomes.${DATE}-${DOMAIN}.csv"
CHECK="${OUTPUT_PATH}/data/genbank-${DATE}-${DOMAIN}.missing.csv"
OUTPUT="${OUTPUT_PATH}/workflow-cleanup/manual-download.${DATE}-${DOMAIN}.csv"
MANUAL="${OUTPUT_PATH}/workflow-cleanup/manual-check.${DATE}-${DOMAIN}.csv"

# Create the output file with header
echo -e "accession,name,ftp_path" > "$OUTPUT"

> "$MANUAL"

# Skip the headers, grab the substring identifier, create a key array, check against the second file, if in both > add that line to the output
awk -F, 'NR>1 && FNR==NR { a[$1]=$0; next } NR>1 && $1 in a { print a[$1] }' "$MISSING" "$CHECK" >> "$OUTPUT"

# Find genomes missed in the output file compared to the check file
awk -F, 'NR>1 && FNR==NR { a[$1]=$0; next } NR>1 && !($1 in a) { print $0 } ' "$OUTPUT" "$CHECK" > "$MANUAL"

# Create a check to make sure that we did not duplicate genomes
awk -F, 'NR>1 && FNR==NR { print substr($1, 4, 11) }' $OUTPUT > double-checking.csv

echo -e "\nRecovered $(tail -n +2 $OUTPUT | wc -l)/$(tail -n +2 $CHECK | wc -l) missing genomes for manual download and addition to the $DOMAIN database"
echo "The remaining $(tail -n +2 $MANUAL | wc -l) missing genomes must be manually checked and may be suspended genomes"
echo "There are $(sort double-checking.csv | uniq -c | grep -v '^ *1 ' | wc -l) duplicates in the $(basename $OUTPUT) file"

echo -e "\nCheck the report files for more information on the suspended genomes most likely missing from the final database"

rm double-checking.csv
