#!/bin/bash
# Archive multiple URLs from file

if [ -z "$1" ]; then
    echo "Usage: archive-batch.sh <urls-file>"
    exit 1
fi

while IFS= read -r url; do
    [ -z "$url" ] && continue
    echo "Archiving: $url"
    response=$(curl -sI "https://web.archive.org/save/$url" 2>/dev/null)
    location=$(echo "$response" | grep -i "^location:" | head -1 | cut -d' ' -f2 | tr -d '\r')

    if [ -n "$location" ]; then
        echo "✓ Archived: $url"
        echo "→ $location"
    else
        echo "✗ Failed: $url"
    fi
    echo ""
    sleep 2  # Rate limit protection
done < "$1"
