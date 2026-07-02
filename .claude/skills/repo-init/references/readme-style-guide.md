# README Style Guide

Condensed from jschell/HEIC-convert. Full source: `docs/README_STYLE_GUIDE.md`.

## Core rule

> "The reader should be able to install, run, and understand the tool within the first screenful."

## Section order

1. `# ProjectName` — title only, no subtitle
2. CI/release badges — only if they exist and pass; no badge walls
3. One-sentence description
4. `## Installation` — always first actionable content
5. `## Usage` — command table + one concrete example
6. `## Features`, `## Configuration`, etc. — only if genuinely needed
7. `## Building` — contributors only; skip for simple projects
8. `## License` — single line, required

## Formatting

- Tables over bullet lists for commands, flags, settings
- No heading depth beyond `##`
- Contractions OK ("you'll", "it's") — casual-technical voice
- Flag intentional trade-offs inline: *(deliberate design decision)*
- No emoji, no "hero" screenshots, no author bios, no "made with" footers

## Anti-patterns (do not do these)

| Anti-pattern | Why |
|---|---|
| `<YOUR_REPO_NAME>` placeholders | Readers copy-paste; placeholders break that |
| Badge walls above the fold | Pushes install instructions off-screen |
| `### Deep` heading nesting | Hard to scan; keep to `##` max |
| Boilerplate Contributing section | Link to CONTRIBUTING.md or skip entirely |
| Long feature list before install | Buries the most-needed content |
