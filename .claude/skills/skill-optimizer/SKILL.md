---
name: skill-optimizer
description: Analyzes and optimizes SKILL.md files to reduce token bloat while maintaining effectiveness. Use when skills exceed 3k tokens.
allowed-tools: Read, Edit, Bash
model: sonnet
---

# Skill Optimizer

Reduces skill token consumption while preserving functionality.

## Process

### Phase 1: Analyze
```
python scripts/optimize-skill.py [skill-path]
```

Token estimation: words × 1.3 ≈ tokens

**Check for bloat:**
- Explanations of common concepts (PDFs, APIs, JSON)
- Installation instructions for standard tools
- Verbose examples inline (>10 lines)
- Paragraphs instead of bullets
- "It is important to...", "First, you need to..."

**Check structure:**
- Large inline code blocks → move to `scripts/`
- Documentation → move to `references/`
- Multiple responsibilities → split into focused skills

### Phase 2: Optimize

**Action order:**

1. **Remove common knowledge** - Delete what Claude already knows
2. **Compress language** - Paragraphs → bullets, verbose → concise
3. **Extract to references/** - API docs, examples, schemas, checklists
4. **Convert to scripts/** - Validation, processing, API calls
5. **Optimize frontmatter** - Description < 100 tokens, specify tools/model
6. **Split if needed** - Skills >5k tokens → multiple focused skills
7. **Streamline examples** - Patterns only, details in references/

**Compression patterns:**
```
❌ "When performing X, it's important to carefully consider Y"
✅ "Consider Y when doing X"

❌ Paragraphs explaining steps
✅ Numbered/bulleted action items

❌ 50-line code example in SKILL.md
✅ "See references/examples.md"

❌ "Write validation code that checks..."
✅ "Run: bash scripts/validate.sh"
```

### Phase 3: Verify

```
python scripts/optimize-skill.py [skill-path]
```

Compare before/after token counts. Test with fresh prompt to verify Claude still completes tasks correctly.

### Phase 4: Report

Generate summary:
```
# Optimization Report
**Skill**: [name]
**Reduction**: [X] → [Y] tokens ([Z]%)

## Changes
- Removed: [list]
- Extracted to references/: [list]
- Created scripts/: [list]

## Verification
- [ ] Test passed
- [ ] < 3k tokens
- [ ] All info accessible
```

## Targets

| Metric | Target |
|--------|--------|
| SKILL.md tokens | < 3,000 |
| Lines | < 500 |
| Frontmatter description | < 100 tokens |
| Reduction goal | 40-70% |

## When NOT to Optimize

- Skill < 1k tokens and working well
- Domain requires extensive context
- Recently created and well-structured
- Used infrequently

## When to Split

- Skill > 8k tokens
- Covers 3+ distinct domains
- Needs different models (opus vs haiku)
- Needs different tool restrictions

## References

- [Quick Reference](references/quick-ref.md)
- [Analysis Script (Python)](scripts/optimize-skill.py) - cross-platform, recommended
- [Analysis Script (Bash)](scripts/optimize-skill.sh) - Unix/macOS only
