---
name: archive-url
description: Archive URLs to Internet Archive's Wayback Machine. Use when user requests archiving/preserving URLs or citations need permanence.
allowed-tools: Bash
model: haiku
---

# Archive URL

Submit URLs to Internet Archive for permanent preservation.

## Process

### Single URL
```bash
curl -sL "https://web.archive.org/save/YOUR_URL"
```

Returns archived URL: `https://web.archive.org/web/TIMESTAMP/YOUR_URL`

### Multiple URLs
```bash
bash scripts/archive-batch.sh urls.txt
```

## Output Format

```
✓ Archived: https://example.com
→ https://web.archive.org/web/20260206143022/https://example.com
```

## Error Handling

| Error | Cause | Action |
|-------|-------|--------|
| 403 | robots.txt blocks | Inform user, cannot archive |
| 429 | Rate limited | Wait 30s, retry |
| Auth required | Login page | Cannot archive, explain limitation |

## When NOT to Use

- Retrieving existing archives → use archive-retrieve skill
- Checking archive history → use archive-retrieve skill
- Bulk archiving >20 URLs → suggest manual Wayback Machine API

## Scripts

- [Batch Archiver](scripts/archive-batch.sh) - Process multiple URLs
- [Verify Archive](scripts/verify-archive.sh) - Confirm successful archival
