# CLAUDE.md Template for Autonomous Work

## Multi-Tool Support

Create `AGENTS.md` at project root for Cursor/Windsurf/Copilot:

```markdown
# Agent Instructions
@.claude/CLAUDE.md
```

No root `CLAUDE.md` needed - Claude Code auto-discovers `.claude/CLAUDE.md`.

## Main Context File

Copy and customize for your project's `.claude/CLAUDE.md`:

```markdown
# Project: [Name]

## Stack
- Language: [Python 3.11 / Node.js 20 / etc]
- Framework: [FastAPI / Express / Next.js / etc]
- Testing: [pytest / vitest / jest]

## Commands

### Test
npm test          # or: pytest

### Lint
npm run lint      # or: ruff check .

### Build
npm run build     # or: python -m build

## Autonomous Work Settings

### Plan Directories
docs/plans/
├── 1_backlog/   # New plans awaiting review
├── 2_active/    # Plan being executed (max 1)
└── 3_complete/  # Verified complete plans

### Plan Workflow
1. Claude creates plan → saves to 1_backlog/
2. Human reviews → moves to 2_active/ when approved
3. Claude executes → moves to 3_complete/ when verified

### Backlog Location
features.txt
# or: Use GitHub issues with label "backlog"

### Stop Conditions (Project-Specific)
- Coverage drops below [75]%
- Breaking changes to public API
- Changes to [critical-module] require review
- External service [X] unavailable

### Commit Format
Use conventional commits: feat:, fix:, test:, refactor:, docs:

## Project-Specific Rules
[Add any project-specific constraints here]
```

## Minimal Version

For simpler projects:

```markdown
# Project: [Name]

## Test: `npm test`
## Lint: `npm run lint`

## Autonomous Work
Plans: docs/plans/{1_backlog,2_active,3_complete}/
Backlog: features.txt
Stop if: 3 failures, breaking changes, security issues
```

## Setup Commands

**Unix/macOS:**
```bash
mkdir -p .claude docs/plans/{1_backlog,2_active,3_complete}
echo -e "# Agent Instructions\n@.claude/CLAUDE.md" > AGENTS.md
# Then create .claude/CLAUDE.md with template above
```

**Windows PowerShell:**
```powershell
New-Item -ItemType Directory -Force -Path .claude, docs/plans/1_backlog, docs/plans/2_active, docs/plans/3_complete
"# Agent Instructions`n@.claude/CLAUDE.md" | Set-Content AGENTS.md
# Then create .claude/CLAUDE.md with template above
```
