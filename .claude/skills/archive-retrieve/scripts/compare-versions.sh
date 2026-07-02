#!/bin/bash
# Compare two archived versions

if [ -z "$3" ]; then
    echo "Usage: compare-versions.sh <url> <timestamp1> <timestamp2>"
    echo "  timestamp format: YYYYMMDDHHMMSS or YYYYMMDD"
    exit 1
fi

url=$1
timestamp1=$2
timestamp2=$3

echo "Downloading version 1 ($timestamp1)..."
curl -sL "https://web.archive.org/web/${timestamp1}id_/$url" -o "v1.html"

echo "Downloading version 2 ($timestamp2)..."
curl -sL "https://web.archive.org/web/${timestamp2}id_/$url" -o "v2.html"

if [ ! -s "v1.html" ] || [ ! -s "v2.html" ]; then
    echo "✗ Failed to download one or both versions"
    exit 1
fi

echo ""
echo "=== Diff (first 50 lines) ==="
diff -u "v1.html" "v2.html" | head -50

echo ""
echo "Files saved: v1.html ($timestamp1), v2.html ($timestamp2)"
echo "Full diff: diff -u v1.html v2.html"
