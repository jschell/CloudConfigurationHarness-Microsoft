#!/bin/bash
# optimize-skill.sh - Analyze skill for optimization opportunities

# Don't use set -e as grep returns 1 when no match found

SKILL_PATH="$1"

if [ -z "$SKILL_PATH" ]; then
    echo "Usage: $0 <skill-path>"
    echo "Example: $0 ~/.claude/skills/my-skill"
    exit 1
fi

if [ ! -f "$SKILL_PATH/SKILL.md" ]; then
    echo "Error: SKILL.md not found at $SKILL_PATH"
    exit 1
fi

echo "=== Skill Optimization Analysis ==="
echo ""
echo "Skill: $(basename "$SKILL_PATH")"
echo ""

# Token estimation
WORDS=$(wc -w < "$SKILL_PATH/SKILL.md")
TOKENS=$(echo "$WORDS * 1.3" | bc | cut -d'.' -f1)
echo "Estimated tokens: $TOKENS"

# Size check
LINES=$(wc -l < "$SKILL_PATH/SKILL.md")
echo "Lines: $LINES"

# Structure check
echo ""
echo "=== Structure Analysis ==="
[ -d "$SKILL_PATH/references" ] && echo "✓ Has references/" || echo "✗ No references/ directory"
[ -d "$SKILL_PATH/scripts" ] && echo "✓ Has scripts/" || echo "✗ No scripts/ directory"
[ -d "$SKILL_PATH/assets" ] && echo "✓ Has assets/" || echo "✗ No assets/ directory"

# Content analysis
echo ""
echo "=== Bloat Indicators ==="

IMPORTANT_COUNT=$(grep -ic "important" "$SKILL_PATH/SKILL.md" 2>/dev/null | head -1 || echo "0")
[ -n "$IMPORTANT_COUNT" ] && [ "$IMPORTANT_COUNT" -gt 0 ] 2>/dev/null && echo "⚠ Contains 'important' ($IMPORTANT_COUNT times)"

INSTALL_COUNT=$(grep -ic "install" "$SKILL_PATH/SKILL.md" 2>/dev/null | head -1 || echo "0")
[ -n "$INSTALL_COUNT" ] && [ "$INSTALL_COUNT" -gt 0 ] 2>/dev/null && echo "⚠ Contains installation references ($INSTALL_COUNT times)"

EXAMPLE_COUNT=$(grep -ic "for example" "$SKILL_PATH/SKILL.md" 2>/dev/null | head -1 || echo "0")
[ -n "$EXAMPLE_COUNT" ] && [ "$EXAMPLE_COUNT" -gt 0 ] 2>/dev/null && echo "⚠ Contains 'for example' ($EXAMPLE_COUNT times)"

FIRST_NEED=$(grep -Eic "first.*need|need.*first" "$SKILL_PATH/SKILL.md" 2>/dev/null | head -1 || echo "0")
[ -n "$FIRST_NEED" ] && [ "$FIRST_NEED" -gt 0 ] 2>/dev/null && echo "⚠ Contains 'first...need' phrasing ($FIRST_NEED times)"

CODE_BLOCKS=$(grep -c '```' "$SKILL_PATH/SKILL.md" 2>/dev/null || echo "0")
CODE_BLOCKS=$((CODE_BLOCKS / 2))
echo "📝 Code blocks: $CODE_BLOCKS"
[ "$CODE_BLOCKS" -gt 5 ] && echo "⚠ Many code blocks - consider moving to scripts/"

# Frontmatter analysis
echo ""
echo "=== Frontmatter Analysis ==="
DESC_LINE=$(grep -n "^description:" "$SKILL_PATH/SKILL.md" 2>/dev/null | head -1)
if [ -n "$DESC_LINE" ]; then
    DESC_WORDS=$(echo "$DESC_LINE" | cut -d':' -f3- | wc -w)
    DESC_TOKENS=$(echo "$DESC_WORDS * 1.3" | bc | cut -d'.' -f1)
    echo "Description tokens: ~$DESC_TOKENS"
    [ "$DESC_TOKENS" -gt 100 ] && echo "⚠ Description exceeds 100 tokens"
fi

ALLOWED_TOOLS=$(grep "^allowed-tools:" "$SKILL_PATH/SKILL.md" 2>/dev/null)
[ -n "$ALLOWED_TOOLS" ] && echo "✓ Tool restrictions specified" || echo "✗ No tool restrictions"

MODEL=$(grep "^model:" "$SKILL_PATH/SKILL.md" 2>/dev/null)
[ -n "$MODEL" ] && echo "✓ Model specified: $(echo "$MODEL" | cut -d':' -f2 | tr -d ' ')" || echo "✗ No model specified"

# Recommendations
echo ""
echo "=== Recommendations ==="
if [ "$TOKENS" -gt 5000 ]; then
    echo "🔴 CRITICAL: Skill exceeds 5k tokens - significant optimization needed"
elif [ "$TOKENS" -gt 3000 ]; then
    echo "🟡 WARNING: Skill exceeds 3k tokens - optimization recommended"
else
    echo "🟢 OK: Skill is reasonably sized ($TOKENS tokens)"
fi

if [ "$LINES" -gt 500 ]; then
    echo "📝 Consider splitting SKILL.md (currently $LINES lines)"
fi

if [ ! -d "$SKILL_PATH/references" ] && [ "$TOKENS" -gt 2000 ]; then
    echo "📁 Create references/ directory to offload documentation"
fi

if [ "$CODE_BLOCKS" -gt 5 ] && [ ! -d "$SKILL_PATH/scripts" ]; then
    echo "⚙️  Create scripts/ directory to offload executable code"
fi

echo ""
echo "=== Summary ==="
echo "Tokens: $TOKENS | Lines: $LINES | Code blocks: $CODE_BLOCKS"
echo ""
echo "To optimize: claude '/skill-optimizer $SKILL_PATH'"
