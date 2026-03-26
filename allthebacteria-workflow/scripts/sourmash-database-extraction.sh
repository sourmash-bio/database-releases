#!/bin/bash

# The first value after this script's name must
# be the database/fileset the new database will
# extract from. The remaining parameters are the
# k-sizes to extract.

# Check for at least two arguments
if [ "$#" -lt 2 ]; then
    echo "Usage: $0 database_name k_size1 [k_size2 ... k_sizeN]"
    exit 1
fi

# Extract the release name
database_name=$1
shift

# Loop through the remaining arguments (i.e. the k_sizes)
for k in "$@"; do
    output_file="${database_name}-k${k}.sig"
    echo "Running: sourmash signature extract ${database_name} -k ${k} --dna -o ${output_file}"
    sourmash signature extract "${database_name}" -k "$k" --dna -o "$output_file"
done

