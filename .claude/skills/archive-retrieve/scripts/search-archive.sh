#!/bin/bash
# Search Internet Archive CDX API for all snapshots

if [ -z "$1" ]; then
    echo "Usage: search-archive.sh <url> [limit]"
    exit 1
fi

url=$1
limit=${2:-10}

# CDX API query
response=$(curl -s "https://web.archive.org/cdx/search/cdx?url=$url&limit=$limit&output=json")

# Check if response is valid
if [ -z "$response" ] || [ "$response" = "[]" ]; then
    echo "No snapshots found for: $url"
    exit 0
fi

echo "Snapshots for: $url"
echo ""

# Parse and format (skip header row)
echo "$response" | python3 -c "
import json, sys
data = json.load(sys.stdin)
if len(data) > 1:
    for row in data[1:]:
        ts, url = row[1], row[2]
        print(f'→ {ts}: https://web.archive.org/web/{ts}/{url}')
" 2>/dev/null || echo "$response" | grep -o '"[0-9]\{14\}"' | tr -d '"' | while read ts; do
    echo "→ $ts: https://web.archive.org/web/$ts/$url"
done
