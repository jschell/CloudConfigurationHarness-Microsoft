#!/usr/bin/env python3
"""optimize-skill.py - Analyze skill for optimization opportunities (cross-platform)

Usage: python optimize-skill.py <skill-path>
Example: python optimize-skill.py skills/my-skill
"""

import sys
import re
from pathlib import Path

def count_words(text):
    """Count words in text."""
    return len(text.split())

def estimate_tokens(word_count):
    """Estimate tokens from word count."""
    return int(word_count * 1.3)

def count_pattern(text, pattern, flags=re.IGNORECASE):
    """Count occurrences of regex pattern."""
    return len(re.findall(pattern, text, flags))

def analyze_skill(skill_path):
    """Analyze a skill directory."""
    skill_path = Path(skill_path)
    skill_md = skill_path / 'SKILL.md'

    if not skill_md.exists():
        print(f"Error: SKILL.md not found at {skill_path}")
        sys.exit(1)

    content = skill_md.read_text(encoding='utf-8')
    lines = content.splitlines()

    # Basic metrics
    word_count = count_words(content)
    tokens = estimate_tokens(word_count)
    line_count = len(lines)

    print("=== Skill Optimization Analysis ===")
    print()
    print(f"Skill: {skill_path.name}")
    print()
    print(f"Estimated tokens: {tokens}")
    print(f"Lines: {line_count}")

    # Structure check
    print()
    print("=== Structure Analysis ===")

    refs_dir = skill_path / 'references'
    scripts_dir = skill_path / 'scripts'
    assets_dir = skill_path / 'assets'

    print(f"{'✓' if refs_dir.exists() else '✗'} {'Has' if refs_dir.exists() else 'No'} references/ directory")
    print(f"{'✓' if scripts_dir.exists() else '✗'} {'Has' if scripts_dir.exists() else 'No'} scripts/ directory")
    print(f"{'✓' if assets_dir.exists() else '✗'} {'Has' if assets_dir.exists() else 'No'} assets/ directory")

    # Bloat indicators
    print()
    print("=== Bloat Indicators ===")

    bloat_patterns = [
        (r'\bimportant\b', "Contains 'important'"),
        (r'\binstall\b', "Contains installation references"),
        (r'\bfor example\b', "Contains 'for example'"),
        (r'\bfirst\b.*\bneed\b|\bneed\b.*\bfirst\b', "Contains 'first...need' phrasing"),
    ]

    for pattern, message in bloat_patterns:
        count = count_pattern(content, pattern)
        if count > 0:
            print(f"⚠ {message} ({count} times)")

    # Code blocks
    code_blocks = content.count('```') // 2
    print(f"📝 Code blocks: {code_blocks}")
    if code_blocks > 5:
        print("⚠ Many code blocks - consider moving to scripts/")

    # Frontmatter analysis
    print()
    print("=== Frontmatter Analysis ===")

    desc_match = re.search(r'^description:\s*(.+)$', content, re.MULTILINE)
    if desc_match:
        desc_words = count_words(desc_match.group(1))
        desc_tokens = estimate_tokens(desc_words)
        print(f"Description tokens: ~{desc_tokens}")
        if desc_tokens > 100:
            print("⚠ Description exceeds 100 tokens")

    has_tools = bool(re.search(r'^allowed-tools:', content, re.MULTILINE))
    print(f"{'✓' if has_tools else '✗'} {'Tool restrictions specified' if has_tools else 'No tool restrictions'}")

    model_match = re.search(r'^model:\s*(\S+)', content, re.MULTILINE)
    if model_match:
        print(f"✓ Model specified: {model_match.group(1)}")
    else:
        print("✗ No model specified")

    # Recommendations
    print()
    print("=== Recommendations ===")

    if tokens > 5000:
        print("🔴 CRITICAL: Skill exceeds 5k tokens - significant optimization needed")
    elif tokens > 3000:
        print("🟡 WARNING: Skill exceeds 3k tokens - optimization recommended")
    else:
        print(f"🟢 OK: Skill is reasonably sized ({tokens} tokens)")

    if line_count > 500:
        print(f"📝 Consider splitting SKILL.md (currently {line_count} lines)")

    if not refs_dir.exists() and tokens > 2000:
        print("📁 Create references/ directory to offload documentation")

    if code_blocks > 5 and not scripts_dir.exists():
        print("⚙️  Create scripts/ directory to offload executable code")

    # Summary
    print()
    print("=== Summary ===")
    print(f"Tokens: {tokens} | Lines: {line_count} | Code blocks: {code_blocks}")

    return tokens

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    skill_path = sys.argv[1]
    analyze_skill(skill_path)

if __name__ == '__main__':
    main()
