#!/bin/bash

# Check for the correct number of arguments
if [ "$#" -ne 4 ]; then
    echo "Usage: $0 DATA_DIR MISSING_IDENT_FILE OUTPUT THREADS"
    exit 1
fi

DATA_DIR="$1"
IDENT_FILE="$2"
OUTPUT="$3"
THREADS="$4"

# THREADS must be a positive integer
if ! [[ "$THREADS" =~ ^[0-9]+$ ]]; then
    echo "Number of threads must be a positive integer"
    exit 1
fi

# Create output file with headers
echo "tar_file_basename,tar_list_item,total_tar_list_items,in_checkfile" > "$OUTPUT"

# Read identifiers into a bash array, skipping header
mapfile -t idents < <(tail -n +2 "$IDENT_FILE"  | tr -d '\r')
echo "Identifiers loaded: ${#idents[@]}"

# Check if specific identifiers are listed in the tar file contents
check_files() {
    local file="$1"
    shift
    local idents=("$@")
    for ident in "${idents[@]}"; do
        if [[ "$file" == *"$ident"* ]]; then
            echo "true"
            return
        fi
    done
    echo "false"
}

# Function to list content of each tar file then use check_files function
process_tar_file() {
    local tar_file="$1"
    shift
    local idents=("$@")
    local tar_basename=$(basename "$tar_file")
    echo "Processing file $tar_basename"

    # List the files stored in the archive
    mapfile -t tar_list < <(tar -tf "$tar_file" 2>/dev/null)
    if [ $? -ne 0 ]; then
        echo "Error processing $tar_file" >&2
        return 1
    fi
    echo "Found ${#tar_list[@]} files in $tar_basename"

    # Check if files are in the idents array
    for file in "${tar_list[@]}"; do
        in_checkfile=$(check_files "$file" "${idents[@]}")
        echo "$tar_basename,$file,${#tar_list[@]},$in_checkfile" >> "$OUTPUT"
    done
}

# Export functions and variables for use in the parallel script
export -f process_tar_file
export -f check_files
export OUTPUT

# Find all .asm.tar.xz files and process them in parallel using xargs
# Use process substitution to pass the idents array
find "$DATA_DIR" -type f -name '*.asm.tar.xz' | xargs -I {} -P "$THREADS" bash -c 'process_tar_file "{}" "${@}"' _ "${idents[@]}"
