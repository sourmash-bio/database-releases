#!/bin/bash

usage() {
    echo "Usage: $0 -f DATA_FILE -o OUTPUT_PATH -d DIR_NAME -p DOWNLOAD_PATH -i DOWNLOAD_LINKS"
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

download_file() {
    echo "Downloading the file..."
    LINK=$(grep "$DIR_NAME" "$DOWNLOAD_LINKS")
    echo "From '$LINK'..."
    wget -P "$DOWNLOAD_PATH" --continue --no-clobber --tries=3 --wait=1 -nv "$LINK"
}

extract_file() {
    echo "Extracting the file..."
    pv "$DATA_FILE" | tar --use-compress-program="xz -T0 -q" --skip-old-files -xf - -C "$OUTPUT_PATH"
}

if [ ! -f "$DATA_FILE" ]; then
    echo "Data file not found."
    download_file
fi

echo "Data file found. Extracting..."

extract_file
TAR_EXIT_CODE=$?

# Check if the extraction failed due to an unexpected end of input
if [ $TAR_EXIT_CODE -ne 0 ]; then
    echo "Error encountered during extraction. Checking for specific error..."

    if grep -q "Unexpected end of input" <<< "$(extract_file 2>&1)"; then
        echo "Detected 'Unexpected end of input' error. Removing corrupted file and re-downloading..."

        rm "$DATA_FILE"
        rm -r "$OUTPUT_PATH"

        # Re-download the file
        download_file

        # Try to extract the file again
        echo "Extracting newly downloaded file..."
        extract_file
        TAR_EXIT_CODE=$?

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

