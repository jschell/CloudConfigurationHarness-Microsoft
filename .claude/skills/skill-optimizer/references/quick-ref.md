# Skill Optimization Quick Reference

## Target Metrics

| Metric | Target |
|--------|--------|
| Max tokens | 3,000 (SKILL.md only) |
| Max lines | 500 |
| Frontmatter description | < 100 tokens |
| Reduction goal | 40-70% |

## Optimization Priority Order

1. **Remove common knowledge** (40-60% savings)
2. **Extract to references/** (30-50% savings)
3. **Convert to scripts/** (20-40% savings)
4. **Compress frontmatter** (10-20% savings)
5. **Streamline examples** (20-40% savings)
6. **Split large skills** (varies)

## Red Flags

- Explaining what PDFs/APIs/JSON are
- Installation instructions for standard tools
- "It is important to..."
- "First, you need to..."
- Inline code > 10 lines
- Multiple examples showing same pattern
- > 5 code blocks in SKILL.md
- Paragraphs instead of bullets

## Quick Wins

| Before | After |
|--------|-------|
| Paragraphs | Bullets |
| Inline examples | `references/examples.md` |
| Inline validation code | `scripts/validate.py` |
| "When performing X, it's important to carefully consider Y" | "Consider Y when doing X" |

## Compression Examples

### Academic → Directive
```
❌ "It is important to consider performance implications..."
✅ "Check: time complexity, memory usage"
```

### Verbose → Bullets
```
❌ Paragraphs explaining steps
✅ Numbered action items
```

### Inline → Reference
```
❌ 50-line code example in SKILL.md
✅ "See references/examples.md"
```

### Generate → Execute
```
❌ "Write validation code that checks..."
✅ "Run: bash scripts/validate.sh"
```

## Success Metrics

**Good optimization:**
- 40-70% token reduction
- Same or better performance
- Improved maintainability
- Clear structure

**Excellent optimization:**
- 70%+ token reduction
- Enhanced performance
- Reusable components
- Multiple focused skills from one bloated skill
