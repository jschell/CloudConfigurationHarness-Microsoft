# Plan Lifecycle

## Directory Structure

```
docs/plans/
├── 1_backlog/     # Plans awaiting human review
├── 2_active/      # Currently executing (max 1)
└── 3_complete/    # Verified complete
```

## States

### 1_backlog (Pending Review)

**Entry:** Plan created by writing-plans skill
**Contents:** Unreviewed plans waiting for human approval
**Exit:** Human moves to 2_active after review

**What happens here:**
- Claude creates plan, saves here
- Human reviews plan for scope, approach, risks
- Human may request changes (edit in place)
- Human approves by moving to 2_active

### 2_active (Executing)

**Entry:** Human moves approved plan from 1_backlog
**Contents:** Exactly ONE plan being executed
**Exit:** Move to 3_complete OR back to 1_backlog

**Rules:**
- Maximum ONE plan at a time
- Claude executes using executing-plans skill
- Tests run after each step
- Commits made incrementally

**What happens here:**
- Claude reads plan, executes step-by-step
- Progress tracked in plan file (checkboxes)
- If blocked: move back to 1_backlog with notes

### 3_complete (Done)

**Entry:** All steps verified, tests pass
**Contents:** Historical record of completed work
**Exit:** Archive or delete periodically

**Before moving here:**
- [ ] All plan steps completed
- [ ] All tests passing
- [ ] Changes committed
- [ ] verification-before-completion run

## State Transitions

```
┌─────────────┐
│  1_backlog  │ ◄─── New plan created
└──────┬──────┘
       │ Human approves
       ▼
┌─────────────┐
│  2_active   │ ◄─── Only ONE at a time
└──────┬──────┘
       │ Verified complete
       ▼
┌─────────────┐
│  3_complete │ ──► Archive/delete
└─────────────┘

Blocked path:
2_active ──► 1_backlog (with blocker notes)
```

## File Naming

```
docs/plans/1_backlog/user-authentication.md
docs/plans/1_backlog/api-rate-limiting.md
docs/plans/2_active/shopping-cart.md
docs/plans/3_complete/project-setup.md
docs/plans/3_complete/database-schema.md
```

**Convention:** lowercase, hyphens, descriptive name

## Plan File Format

```markdown
# Plan: Feature Name

**Status:** [Backlog | Active | Complete]
**Created:** YYYY-MM-DD
**Completed:** YYYY-MM-DD (when done)

## Context
[What and why]

## Steps
- [ ] Step 1: Description
- [ ] Step 2: Description
- [x] Step 3: Completed step

## Blockers (if any)
[Notes about what's blocking progress]

## Verification
- [ ] All tests pass
- [ ] Changes committed
- [ ] Feature works end-to-end
```

## Commands

```bash
# Check what's active
ls docs/plans/2_active/

# Move plan to active (human action)
mv docs/plans/1_backlog/feature.md docs/plans/2_active/

# Move to complete (after verification)
mv docs/plans/2_active/feature.md docs/plans/3_complete/

# Count plans in each state
echo "Backlog: $(ls docs/plans/1_backlog/ 2>/dev/null | wc -l)"
echo "Active: $(ls docs/plans/2_active/ 2>/dev/null | wc -l)"
echo "Complete: $(ls docs/plans/3_complete/ 2>/dev/null | wc -l)"
```

## Why This Structure?

1. **Numbered prefixes** - Directories sort in workflow order
2. **Explicit states** - No ambiguity about plan status
3. **Human gate** - 1→2 transition requires human approval
4. **Single active** - Prevents context switching
5. **Audit trail** - 3_complete preserves history
