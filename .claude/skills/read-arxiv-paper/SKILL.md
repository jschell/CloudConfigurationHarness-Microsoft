---
name: read-arxiv-paper
description: Use when given an arxiv URL to read a paper - fetches LaTeX source, parses content, provides structured summary
---

# Read arXiv Paper

Fetch and read arXiv papers from their LaTeX source (not PDF).

## Quick Reference

| Step | Action |
|------|--------|
| 1. Normalize | Convert URL to source format |
| 2. Fetch | Download and extract LaTeX source |
| 3. Find entry | Locate main .tex file |
| 4. Read | Follow includes recursively |
| 5. Summarize | Extract key points |

## URL Normalization

```
Input formats:
  arxiv.org/abs/2601.07372
  arxiv.org/pdf/2601.07372
  arxiv.org/abs/2601.07372v2

Output format:
  arxiv.org/src/2601.07372
```

Extract ID: `2601.07372` (ignore version suffix)

## Fetch & Extract

```
python scripts/fetch-arxiv.py <arxiv-id-or-url>
```

Cache locations (auto-detected):
- Linux: `~/.cache/arxiv-papers/`
- macOS: `~/Library/Caches/arxiv-papers/`
- Windows: `%LOCALAPPDATA%\arxiv-papers\`

Override with `ARXIV_CACHE` environment variable.

## Find Entrypoint

Search order:
1. `main.tex`, `paper.tex`, `manuscript.tex`
2. File containing `\documentclass`
3. Only `.tex` file (if single file)

## Read Paper

1. Read entrypoint file
2. Follow `\input{file}` and `\include{file}`
3. Skip `\bibliography{}` and style files
4. Read abstract, sections, figures, tables

## Output Format

```markdown
# Paper: [Title]

**Authors:** [names]
**arXiv:** [id]

## Abstract
[extracted abstract]

## Key Contributions
- [point 1]
- [point 2]

## Method
[summary]

## Results
[key findings]

## Relevance
[how this applies to current context]
```

## Error Handling

| Issue | Solution |
|-------|----------|
| Invalid URL | Show expected format |
| 404 error | Check arxiv ID exists |
| No .tex files | May be PDF-only submission |
| Multiple entrypoints | List files, ask user |
| Encoding issues | Try utf-8, then latin-1 |

## See Also

- [LaTeX Patterns](references/latex-patterns.md)
- [Fetch Script (Python)](scripts/fetch-arxiv.py) - cross-platform, recommended
- [Fetch Script (Bash)](scripts/fetch-arxiv.sh) - Unix/macOS only
