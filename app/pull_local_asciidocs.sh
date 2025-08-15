#!/bin/bash

set -e

# Configuration
REPO_URL="https://github.com/green-code-initiative/creedengo-rules-specifications.git"
REPO_DIR="temp_repo"
OUTPUT_DIR="pattern-library"

# Clean up any previous clone
rm -rf "$REPO_DIR"

# Clone fresh
git clone "$REPO_URL" "$REPO_DIR"

# Create output directory if not exists
mkdir -p "$OUTPUT_DIR"

# Find each .asciidoc file, clean it, then copy it
find "$REPO_DIR/src/main/rules" -type f -name "*.asciidoc" | while read -r file; do
    python3 cleaner.py "$file"
    cp "$file" "$OUTPUT_DIR"
done

# Optional cleanup
rm -rf "$REPO_DIR"

echo "Done."
