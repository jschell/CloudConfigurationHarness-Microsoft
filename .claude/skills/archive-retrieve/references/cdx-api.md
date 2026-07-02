# CDX API Reference

## Endpoint

```
https://web.archive.org/cdx/search/cdx
```

## Query Parameters

| Param | Description | Example |
|-------|-------------|---------|
| url | Target URL (required) | `example.com` |
| from | Start date | `20200101` |
| to | End date | `20240101` |
| limit | Max results | `100` |
| filter | Field filter | `statuscode:200` |
| collapse | Deduplicate | `timestamp:10` |
| output | Format | `json` |
| matchType | URL matching | `exact`, `prefix`, `host`, `domain` |

## Response Fields

| Index | Field | Description |
|-------|-------|-------------|
| 0 | urlkey | Canonicalized URL |
| 1 | timestamp | YYYYMMDDHHMMSS |
| 2 | original | Original URL |
| 3 | mimetype | Content type |
| 4 | statuscode | HTTP status |
| 5 | digest | Content hash |
| 6 | length | Response size |

## Examples

### Get all 200 OK responses
```bash
curl -s "https://web.archive.org/cdx/search/cdx?url=example.com&filter=statuscode:200&output=json"
```

### Date range query
```bash
curl -s "https://web.archive.org/cdx/search/cdx?url=example.com&from=20200101&to=20240101&output=json"
```

### Monthly snapshots (collapse by month)
```bash
curl -s "https://web.archive.org/cdx/search/cdx?url=example.com&collapse=timestamp:6&output=json"
```

### All pages under domain
```bash
curl -s "https://web.archive.org/cdx/search/cdx?url=example.com&matchType=domain&output=json"
```

### Exclude redirects
```bash
curl -s "https://web.archive.org/cdx/search/cdx?url=example.com&filter=!statuscode:3..&output=json"
```

## Rate Limits

- No authentication required
- Recommended: 1 request per second
- Large queries may timeout; use pagination with `limit` and `offset`
