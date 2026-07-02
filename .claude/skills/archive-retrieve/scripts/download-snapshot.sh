#!/bin/bash
# Download specific archived snapshot

if [ -z "$1" ]; then
    echo "Usage: download-snapshot.sh <url> [timestamp|latest]"
    echo "  timestamp format: YYYYMMDDHHMMSS or YYYYMMDD"
    exit 1
fi

url=$1
timestamp=${2:-latest}

if [ "$timestamp" = "latest" ]; then
    echo "Finding latest snapshot..."
    response=$(curl -s "https://archive.org/wayback/available?url=$url")
    snapshot=$(echo "$response" | grep -o '"url": "[^"]*"' | head -1 | cut -d'"' -f4)

    if [ -z "$snapshot" ]; then
        echo "✗ No snapshot available for: $url"
        exit 1
    fi
else
    snapshot="https://web.archive.org/web/${timestamp}id_/$url"
fi

# Resolve actual timestamp for "latest"
if [ "$timestamp" = "latest" ]; then
    actual_ts=$(echo "$response" | grep -o '"timestamp": "[^"]*"' | head -1 | cut -d'"' -f4)
    actual_ts=${actual_ts:-$(date +%Y%m%d%H%M%S)}
else
    actual_ts=$timestamp
fi

# Extract filename from URL path, strip query/fragment
basename=$(echo "$url" | sed 's/[?#].*//' | sed 's|.*/||')

if [ -n "$basename" ] && echo "$basename" | grep -q '\.'; then
    # Has a recognizable filename with extension — prepend timestamp
    outfile="${actual_ts}_${basename}"
else
    # No filename or extension — derive extension, use domain as name
    ext="${url##*.}"
    case "$ext" in
        pdf|jpg|jpeg|png|gif|svg|css|js|json|xml|csv|txt|zip|gz|mp3|mp4|webp|woff|woff2)
            ;;
        *) ext="html" ;;
    esac
    domain=$(echo "$url" | sed 's|https\?://||' | sed 's|/.*||' | sed 's/[^a-zA-Z0-9.-]/_/g')
    outfile="${actual_ts}_${domain}.${ext}"
fi

echo "Downloading: $snapshot"

curl -sL "$snapshot" -o "$outfile"

if [ -s "$outfile" ]; then
    echo "✓ Downloaded to: $outfile"
    echo "  Size: $(wc -c < "$outfile") bytes"
else
    echo "✗ Download failed or empty response"
    rm -f "$outfile"
    exit 1
fi
