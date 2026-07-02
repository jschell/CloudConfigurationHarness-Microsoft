#!/bin/bash
# fetch-arxiv.sh - Download and extract arXiv paper source
#
# Usage: fetch-arxiv.sh <arxiv-url-or-id>
# Example: fetch-arxiv.sh 2601.07372
#          fetch-arxiv.sh https://arxiv.org/abs/2601.07372

set -e

# Extract arxiv ID from various input formats
extract_id() {
    local input="$1"
    # Remove URL prefix if present
    local id=$(echo "$input" | sed -E 's|.*arxiv.org/(abs|pdf|src)/||' | sed -E 's|v[0-9]+$||')
    echo "$id"
}

# Validate arxiv ID format (YYMM.NNNNN or older formats)
validate_id() {
    local id="$1"
    if [[ ! "$id" =~ ^[0-9]{4}\.[0-9]{4,5}$ ]] && [[ ! "$id" =~ ^[a-z-]+/[0-9]+$ ]]; then
        echo "Error: Invalid arxiv ID format: $id"
        echo "Expected: YYMM.NNNNN (e.g., 2601.07372)"
        exit 1
    fi
}

if [ -z "$1" ]; then
    echo "Usage: $0 <arxiv-url-or-id>"
    echo "Example: $0 2601.07372"
    echo "         $0 https://arxiv.org/abs/2601.07372"
    exit 1
fi

ARXIV_ID=$(extract_id "$1")
validate_id "$ARXIV_ID"

CACHE_DIR="${ARXIV_CACHE:-$HOME/.cache/arxiv-papers}"
PAPER_DIR="$CACHE_DIR/$ARXIV_ID"
EXTRACT_DIR="$PAPER_DIR/extracted"
TARBALL="$PAPER_DIR/source.tar.gz"

echo "arXiv ID: $ARXIV_ID"
echo "Cache: $PAPER_DIR"

# Check if already cached
if [ -d "$EXTRACT_DIR" ] && [ "$(ls -A "$EXTRACT_DIR" 2>/dev/null)" ]; then
    echo "Already cached at $EXTRACT_DIR"
    echo "Entry point candidates:"
    find "$EXTRACT_DIR" -name "*.tex" -type f | head -5
    exit 0
fi

# Create directories
mkdir -p "$PAPER_DIR"

# Download source
echo "Downloading from https://arxiv.org/src/$ARXIV_ID ..."
if ! curl -L --fail "https://arxiv.org/src/$ARXIV_ID" -o "$TARBALL" 2>/dev/null; then
    echo "Error: Failed to download. Check if arxiv ID exists."
    rm -f "$TARBALL"
    exit 1
fi

# Check if it's actually a tarball
if ! file "$TARBALL" | grep -q "gzip\|tar"; then
    # Might be a single .tex file
    mkdir -p "$EXTRACT_DIR"
    mv "$TARBALL" "$EXTRACT_DIR/paper.tex"
    echo "Single file paper, saved as paper.tex"
else
    # Extract tarball
    mkdir -p "$EXTRACT_DIR"
    if ! tar -xzf "$TARBALL" -C "$EXTRACT_DIR" 2>/dev/null; then
        # Try gunzip + tar separately (some arxiv sources)
        gunzip -c "$TARBALL" | tar -xf - -C "$EXTRACT_DIR" 2>/dev/null || {
            echo "Error: Failed to extract archive"
            exit 1
        }
    fi
    echo "Extracted to $EXTRACT_DIR"
fi

# Find entry point
echo ""
echo "Looking for entry point..."

for candidate in main.tex paper.tex manuscript.tex article.tex; do
    if [ -f "$EXTRACT_DIR/$candidate" ]; then
        echo "Found: $candidate"
        exit 0
    fi
done

# Search for \documentclass
ENTRY=$(grep -l '\\documentclass' "$EXTRACT_DIR"/*.tex 2>/dev/null | head -1)
if [ -n "$ENTRY" ]; then
    echo "Found entry point: $(basename "$ENTRY")"
    exit 0
fi

# List all .tex files
echo "No obvious entry point. Available .tex files:"
find "$EXTRACT_DIR" -name "*.tex" -type f
