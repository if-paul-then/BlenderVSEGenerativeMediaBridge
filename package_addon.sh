#!/bin/bash

# This script packages the Blender addon into a zip file suitable for installation.

# Define the source directory and the output zip file name
ADDON_DIR="VSEGenerativeMediaBridge"
ZIP_FILE="${ADDON_DIR}.zip"

# Check if the source directory exists
if [ ! -d "$ADDON_DIR" ]; then
    echo "Error: Addon directory '$ADDON_DIR' not found."
    exit 1
fi

# Remove the old zip file if it exists, to prevent including it in the new archive
if [ -f "$ZIP_FILE" ]; then
    echo "Removing old archive: $ZIP_FILE"
    rm "$ZIP_FILE"
fi

# Create the new zip archive
echo "Creating new archive: $ZIP_FILE"
zip -r "$ZIP_FILE" "$ADDON_DIR"

echo "Addon successfully packaged!" 