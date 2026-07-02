# Multi-Tool AI Context Setup

Configure a project to work with multiple AI coding assistants.

## File Standards

| File | Tool Support | Purpose |
|------|--------------|---------|
| `AGENTS.md` | Cursor, Windsurf, Copilot | Vendor-neutral context (root) |
| `.claude/CLAUDE.md` | Claude Code | Claude-specific instructions (auto-discovered) |

## Recommended Structure

```
project/
├── AGENTS.md              # For other AI tools
└── .claude/
    └── CLAUDE.md          # Single source (Claude Code auto-reads)
```

No root `CLAUDE.md` needed - avoids duplicate file names.

## Setup Method

**AGENTS.md (root)** - references the shared context:
```markdown
# Agent Instructions
@.claude/CLAUDE.md
```

**.claude/CLAUDE.md** - contains all detailed instructions.

**Benefits:**
- Claude Code auto-discovers `.claude/CLAUDE.md`
- Other tools use `AGENTS.md` reference
- Single source of truth
- No duplicate `CLAUDE.md` files
- Works on all platforms

## Alternative: Symbolic Link

For `AGENTS.md` only (Unix/macOS):
```bash
ln -s .claude/CLAUDE.md AGENTS.md
```

**Windows (requires admin or developer mode):**
```powershell
New-Item -ItemType SymbolicLink -Path AGENTS.md -Target .claude\CLAUDE.md
```

**Note:** Symlinks can have issues with some git clients.

## Tool-Specific Notes

### Claude Code
- Reads `.claude/CLAUDE.md` automatically
- Supports `@path` references
- Recognizes root `CLAUDE.md`

### Cursor
- Reads `AGENTS.md` or `.cursorrules`
- May not support `@path` syntax in all versions
- Consider duplicating content if reference doesn't work

### Windsurf
- Reads `AGENTS.md`
- Similar behavior to Cursor

### GitHub Copilot
- Limited context file support
- May need `.github/copilot-instructions.md`

## Setup Script

**Unix/macOS:**
```bash
mkdir -p .claude
cat > .claude/CLAUDE.md << 'EOF'
# Project: [Name]

## Commands
- Test: `npm test`
- Lint: `npm run lint`

## Rules
[Project constraints]
EOF

echo -e "# Agent Instructions\n@.claude/CLAUDE.md" > AGENTS.md
```

**Windows PowerShell:**
```powershell
New-Item -ItemType Directory -Force -Path .claude
@"
# Project: [Name]

## Commands
- Test: ``npm test``
- Lint: ``npm run lint``

## Rules
[Project constraints]
"@ | Set-Content .claude\CLAUDE.md

"# Agent Instructions`n@.claude/CLAUDE.md" | Set-Content AGENTS.md
```
