#!/bin/bash

# Run this script with:
# gather_failed.sh path/to/dir/before/workflow-cleanup 
#
# After running this script follow-up by running:
# sourmash scripts gbsketch workflow-cleanup/manual-download.20240712-protozoa.csv -o manual-download.20240712-protozoa.zip --failed manual-download.20240712-protozoa.failed.csv --param-string "dna,k=21,k=31,k=51,scaled=1000,abund" -r 5 -g 2> manual-download.20240712-protozoa.log

# Input parameters
OUTPUT_PATH="$1"
RELEASE="$2"

# Check if DATE and DOMAIN are provided
if [ -z "$OUTPUT_PATH" ] || [ -z "$RELEASE" ]; then
    echo "Usage: $0 OUTPUT_PATH RELEASE"
    exit 1
fi

# Define file paths based on inputs
MISSING="${OUTPUT_PATH}/data/gtdb-${RELEASE}.all-missing-links.csv"
REVERSION="${OUTPUT_PATH}/data/gtdb-${RELEASE}.updated-versions-existing.csv"
CHECK="${OUTPUT_PATH}/data/final.gtdb-${RELEASE}.missing.csv"
CHECK_REPS="${OUTPUT_PATH}/data/final-reps.gtdb-${RELEASE}.missing.csv"
OUTPUT="${OUTPUT_PATH}/workflow-cleanup/manual-download.${RELEASE}.csv"
OUTPUT_REPS="${OUTPUT_PATH}/workflow-cleanup/manual-download-reps.${RELEASE}.csv"
MANUAL="${OUTPUT_PATH}/workflow-cleanup/manual-check.${RELEASE}.csv"
MANUAL_REPS="${OUTPUT_PATH}/workflow-cleanup/manual-check-reps.${RELEASE}.csv"

# Create the output file with header
echo -e "accession,name,ftp_path" > "$OUTPUT"
echo -e "accession,name,ftp_path" > "$OUTPUT_REPS"

# Skip the headers, grab the substring identifier, create a key array, check against the second file, if in both > add that line to the output
awk -F, 'NR>1 && FNR==NR { key = substr($1, 4, 10) ; a[key]=$0; next } NR>1 { key = substr($1, 4, 10) ; if (key in a) { print a[key] } }' "$MISSING" "$CHECK" >> "$OUTPUT"
awk -F, 'NR>2 && FNR==NR { key = substr($1, 4, 10) ; a[key]=$0; next } NR>1 { key = substr($1, 4, 10) ; if (key in a) { print a[key] } }' "$MISSING" "$CHECK_REPS" >> "$OUTPUT_REPS"

awk -F, 'NR>1 && FNR==NR { key = substr($1, 4, 10) ; a[key]=$0; next } NR>1 { key = substr($1, 4, 10) ; if (key in a) { print a[key] } }' "$REVERSION" "$CHECK" >> "$OUTPUT"
awk -F, 'NR>1 && FNR==NR { key = substr($1, 4, 10) ; a[key]=$0; next } NR>1 { key = substr($1, 4, 10) ; if (key in a) { print a[key] } }' "$REVERSION" "$CHECK_REPS" >> "$OUTPUT_REPS"

# Find genomes missed in the output file compared to the check file
awk -F, 'NR>1 && FNR==NR { key = substr($1, 4, 10) ; a[key]=$0; next } NR>1 { key = substr($1, 4, 10) ; if (!(key in a)) { print $0 } }' "$OUTPUT" "$CHECK" > "$MANUAL"
awk -F, 'NR>1 && FNR==NR { key = substr($1, 4, 10) ; a[key]=$0; next } NR>1 { key = substr($1, 4, 10) ; if (!(key in a)) { print $0 } }' "$OUTPUT_REPS" "$CHECK_REPS" > "$MANUAL_REPS"

# Create a check to make sure that we did not duplicate genomes
awk -F, 'NR>1 && FNR==NR { print substr($1, 4, 11) }' $OUTPUT > double-checking.csv
awk -F, 'NR>1 && FNR==NR { print substr($1, 4, 11) }' $OUTPUT_REPS > double-checking_reps.csv

echo -e "\nRecovered $(tail -n +2 $OUTPUT | wc -l)/$(tail -n +2 $CHECK | wc -l) missing genomes for manual download and addition to the Full Database"
echo "The remaining $(tail -n +2 $MANUAL | wc -l) missing genomes must be manually checked and may be suspended genomes"
echo "There are $(sort double-checking.csv | uniq -c | grep -v '^ *1 ' | wc -l) duplicates in the $(basename $OUTPUT) file"


echo -e "\nRecovered $(tail -n +2 $OUTPUT_REPS | wc -l)/$(tail -n +2 $CHECK_REPS | wc -l) missing genomes for manual download and addition to the Reps Database"
echo "The remaining $(tail -n +2 $MANUAL_REPS | wc -l) missing genomes must be manually checked and may be suspended genomes"
echo "There are $(sort double-checking_reps.csv | uniq -c | grep -v '^ *1 ' | wc -l) duplicates in $(basename $OUTPUT_REPS) file"

echo -e "\nCheck the report files for more information on the suspended genomes most likely missing from the final database"
