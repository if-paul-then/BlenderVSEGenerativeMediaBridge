#!/bin/bash

# This script validates and builds the Blender extension using Blender's command-line tool.

# --- Configuration ---
# Path to the Blender executable.
# IMPORTANT: Update this to match your Blender installation path.
BLENDER_EXE="/mnt/c/Program Files/Blender Foundation/Blender 4.4/blender.exe"

# The directory containing the addon source code (where blender_manifest.toml is).
ADDON_DIR="VSEGenerativeMediaBridge"
# --- End Configuration ---

# 1. Check if Blender executable exists
if [ ! -f "$BLENDER_EXE" ]; then
    echo "Error: Blender executable not found at '$BLENDER_EXE'."
    echo "Please update the BLENDER_EXE variable in this script."
    exit 1
fi

# 2. Check if the addon source directory exists
if [ ! -d "$ADDON_DIR" ]; then
    echo "Error: Addon directory '$ADDON_DIR' not found."
    exit 1
fi

# 3. Validate the extension
echo "--- Validating Extension: $ADDON_DIR ---"
"$BLENDER_EXE" --command extension validate "$ADDON_DIR"

# Check if validation was successful
if [ $? -ne 0 ]; then
    echo "Error: Extension validation failed. Aborting build."
    exit 1
fi
echo "Validation successful."

# 4. Build the extension
echo ""
echo "--- Building Extension: $ADDON_DIR ---"
"$BLENDER_EXE" --command extension build --source-dir "$ADDON_DIR"

# Check if build was successful
if [ $? -ne 0 ]; then
    echo "Error: Extension build failed."
    exit 1
fi

echo ""
echo "Extension successfully validated and built!" 