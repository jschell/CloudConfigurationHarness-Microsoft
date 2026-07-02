---
name: archive-retrieve
description: Retrieve and search archived versions of URLs from Internet Archive. Use when user needs to access archived/historical versions of pages, check archive availability, or recover deleted content.
allowed-tools: Bash
model: sonnet
---

# Archive Retrieve

Access archived versions of URLs from Internet Archive.

## Process

### Get Latest Archive
```bash
curl -s "https://archive.org/wayback/available?url=YOUR_URL"
```

### Get Specific Date
```bash
# Format: YYYYMMDD
curl -sL "https://web.archive.org/web/20240101/YOUR_URL"
```

### Search All Versions
```bash
bash scripts/search-archive.sh YOUR_URL
```

## Common Queries

| Task | Command |
|------|---------|
| Latest snapshot | `curl -s "https://archive.org/wayback/available?url=URL"` |
| All snapshots | CDX API → see scripts/search-archive.sh |
| Date range | CDX API with from/to params |
| Download content | `bash scripts/download-snapshot.sh URL [timestamp]` |

## Output Format

### Search
```
Found 127 snapshots for: example.com
  Oldest: 2010-03-15
  Latest: 2024-01-15

Recent snapshots:
→ 20240115: https://web.archive.org/web/20240115120045/example.com
→ 20231220: https://web.archive.org/web/20231220093012/example.com
```

### Download
Files named as `{timestamp}_{original-filename}`, falling back to `{timestamp}_{domain}.{ext}`:
```
✓ Downloaded to: 20251216120030_report.pdf
✓ Downloaded to: 20260206155300_example.com.html
```

## When NOT to Use

- Archiving new URLs → use archive-url skill
- General web search → use web_search
- Live content needed → use web_fetch

## Scripts

- [Search Archive](scripts/search-archive.sh) - CDX API query
- [Download Snapshot](scripts/download-snapshot.sh) - Retrieve specific version
- [Compare Versions](scripts/compare-versions.sh) - Diff between timestamps

## References

- [CDX API Guide](references/cdx-api.md) - Advanced queries
- [Common Patterns](references/patterns.md) - Use case examples
