#!/bin/bash
# Verify URL was archived

if [ -z "$1" ]; then
    echo "Usage: verify-archive.sh <url>"
    exit 1
fi

url=$1
response=$(curl -s "https://archive.org/wayback/available?url=$url")
available=$(echo "$response" | grep -o '"available": *true')

if [ -n "$available" ]; then
    snapshot=$(echo "$response" | grep -o '"url": "[^"]*"' | head -1 | cut -d'"' -f4)
    timestamp=$(echo "$response" | grep -o '"timestamp": "[^"]*"' | head -1 | cut -d'"' -f4)
    echo "✓ Archive exists"
    echo "  Timestamp: $timestamp"
    echo "  URL: $snapshot"
else
    echo "✗ Not archived or unavailable"
fi
