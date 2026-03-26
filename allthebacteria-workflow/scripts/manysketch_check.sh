#!/bin/bash

# More info here https://github.com/sourmash-bio/sourmash/issues/3190

    sourmash scripts manysketch {input.csv_file} -p {params.k_list},scaled={params.scale},abund -o {output.zip_file}
usage() {
    echo "Usage: $0 -f CSV_FILE -o OUTPUT_ZIP -d DIR_NAME -p DOWNLOAD_PATH -i DOWNLOAD_LINKS"
    exit 1
}

while getopts "f:o:d:p:i:" opt; do
    case $opt in
        f) DATA_FILE="$OPTARG" ;;
        o) OUTPUT_PATH="$OPTARG" ;;
        d) DIR_NAME="$OPTARG" ;;
        p) DOWNLOAD_PATH="$OPTARG" ;;
        i) DOWNLOAD_LINKS="$OPTARG" ;;
        *) usage ;;
    esac
done

if [ -z "$DATA_FILE" ] || [ -z "$OUTPUT_PATH" ] || [ -z "$DIR_NAME" ] || [ -z "$DOWNLOAD_PATH" ] || [ -z "$DOWNLOAD_LINKS" ] ; then
    usage
fi

sketch_seq() {
    LINK=$(grep "$DIR_NAME" "$DOWNLOAD_LINKS")
    echo "From '$LINK'..."
    sourmash scripts manysketch {input.csv_file} -p {params.k_list},scaled={params.scale},abund -o {output.zip_file}
}

echo "Sketching the file..."

sketch_seq
SKETCH_EXIT_CODE=$?

# Check if the extraction failed due to an unexpected end of input
if [ $SKETCH_EXIT_CODE -ne 0 ]; then
    echo "Error encountered during sketching. Checking for specific error..."

    if grep -q "End-of-central-directory" <<< "$(extract_file 2>&1)"; then
        echo "Detected 'End-of-central-directory' error. Removing corrupted file and re-downloading..."

        rm "$DATA_FILE"
        rm -r "$OUTPUT_PATH"

        # Re-download the file
        download_file

        # Try to extract the file again
        echo "Sketching newly downloaded file..."
        sketch_seq
        SKETCH_EXIT_CODE=$?

        if [ $TAR_EXIT_CODE -ne 0 ]; then
            echo "Extraction failed again. Please check the file source or script for issues."
            exit 1
        else
            echo "File extracted successfully after re-download."
        fi
    else
        echo "Extraction failed due to a different error. Exiting."
        exit 1
    fi
else
    echo "File extracted successfully."
fi

