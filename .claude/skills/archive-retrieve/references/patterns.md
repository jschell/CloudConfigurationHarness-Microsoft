# Common Archive Retrieval Patterns

## Pattern 1: Recover Deleted Content

```bash
# Check if archived version exists
curl -s "https://archive.org/wayback/available?url=DELETED_URL"

# Get the snapshot URL
bash scripts/download-snapshot.sh DELETED_URL latest
```

## Pattern 2: Track Changes Over Time

```bash
# Get yearly snapshots
bash scripts/search-archive.sh example.com 100 | grep "0101"

# Compare two years
bash scripts/compare-versions.sh example.com 20220101 20230101
```

## Pattern 3: Verify Historical Claims

```bash
# Check what page said on specific date
curl -sL "https://web.archive.org/web/20200315/example.com/page"

# Get all snapshots from that period
curl -s "https://web.archive.org/cdx/search/cdx?url=example.com/page&from=20200301&to=20200331&output=json"
```

## Pattern 4: Download for Offline Analysis

```bash
# Download multiple versions
for ts in 20200101 20210101 20220101 20230101; do
    bash scripts/download-snapshot.sh example.com $ts
done
```

## Pattern 5: Find First Appearance

```bash
# Get oldest snapshot
curl -s "https://web.archive.org/cdx/search/cdx?url=example.com&limit=1&output=json"
```

## Pattern 6: Check Robots.txt History

```bash
# See how robots.txt changed
bash scripts/search-archive.sh example.com/robots.txt 20
```

## Pattern 7: Recover Specific File

```bash
# Find archived JavaScript/CSS/images
curl -s "https://web.archive.org/cdx/search/cdx?url=example.com/*.js&matchType=prefix&output=json"
```

## Pattern 8: Export Citation with Archive

```bash
# Get archived URL for citation
url="https://example.com/article"
archived=$(curl -s "https://archive.org/wayback/available?url=$url" | grep -o '"url": "[^"]*"' | cut -d'"' -f4)
echo "Accessed via Internet Archive: $archived"
```
