---
name: wardley-mapping
description: Use when asked to create a wardley map, map the value chain, assess evolution stage of components, perform build-vs-buy analysis, or analyze strategic landscape and component maturity
---

# Wardley Mapping

Produce mechanics-first Wardley Map analysis. Output: OWM DSL + evolution rationale table + strategic commentary. Never output React/JSX visualization code.

## Trigger Phrases

"wardley map", "map the value chain", "evolution stage", "where does X sit on the evolution axis", "build vs buy analysis", "strategic landscape", "component maturity"

## Workflow

### Step 1 — Clarify

If input is vague or lacks a clear user/need anchor, ask ONE question before proceeding:
- "Who is the user, and what do they need?" or
- "What is the strategic question this map should answer?"

Do not ask multiple questions. If the input has enough to start, proceed.

### Step 2 — Build Value Chain

1. Identify the **user anchor** (top of map, high visibility)
2. Work downward through dependencies to infrastructure
3. Each component must answer: "What does [parent component] need to exist?"
4. Typical depth: 4–8 components. Stop when you reach commodity infrastructure (power, internet, DNS)

### Step 3 — Score Evolution

For each component, evaluate against the cheat sheet in `references/evolution-assessment.md`.

**Three fast questions:**
1. How many vendors sell this? (0–1 = genesis/custom; 5+ competing products = product; price war = commodity)
2. What happens when it fails? (shrug = genesis; outrage = commodity)
3. How do competitors talk about it? ("we invented this" = genesis; "of course we have it" = commodity)

**Common trap:** Don't score by how *you* treat it — score by market reality. If competitors all have it, it's commodity with inertia, not custom.

**Coordinates:** `[visibility, maturity]`
- Visibility Y-axis: 0 = invisible infrastructure → 1 = directly user-facing
- Maturity X-axis: 0 = genesis → 0.25 = custom built → 0.55 = product → 0.85 = commodity

If a component cannot be confidently placed, decompose it rather than guessing. Explain why decomposition is needed.

### Step 4 — Map Dependencies

- Use `->` for dependency links
- Add `inertia` to components resisting evolution pressure (legacy investment, org habits)
- Add `evolve [Component] [target]` where market pressure is clearly moving a component

### Step 5 — Generate Outputs

Produce all three outputs in sequence: OWM DSL → Evolution Rationale Table → Strategic Commentary.

## Output Format

```
## OWM Map

​```
[OWM DSL here]
​```

Paste into: https://onlinewardleymaps.com or the VS Code Wardley Maps extension.

---

## Evolution Rationale

| Component | Stage | Score | Evidence | Strategic Implication |
|---|---|---|---|---|
| [Name] | Product | 0.55 | [1-line market evidence] | [1-line implication] |

---

## Strategic Commentary

1. [Observation — doctrine/inertia/movement/build-vs-buy signal]
2. [Observation]
3. [Observation]
4. [Optional 4th]
5. [Optional 5th]
```

## OWM DSL Quick Reference

```
title [Map Title]
style wardley

anchor [User/Need Name] [visibility, maturity]
component [Name] [visibility, maturity]
component [Name] [visibility, maturity] inertia

[Component A]->[Component B]
[Component A]+>[Component B]    // flow link

evolve [Component Name] [target maturity]
pipeline [Name] [start_maturity, end_maturity]
note [Text] [visibility, maturity]
```

Full syntax: `references/owm-syntax.md`

## Doctrinal Signals to Flag in Commentary

| Signal | Description |
|---|---|
| **Inertia** | Component resists justified evolution (legacy, politics, habit) |
| **Build vs Buy** | Product/Commodity stage = buy/outsource unless genuinely differentiating |
| **Co-evolution gap** | Product-stage activity + Genesis-stage practice = waste |
| **Commoditize complement** | Competitor depends on your Custom Built → make it commodity |
| **PST mismatch** | Genesis needs Pioneers; Commodity needs Town Planners — wrong team is a failure mode |
| **Ecosystem signal** | Newly commoditized component enables genesis of something above it |

## Placement Rules

- Every coordinate must have a one-line evidence rationale
- Placement without evidence is the primary failure mode — enforce this
- Do NOT cluster components at default mid-map coordinates
- Decompose before guessing

## References

- [Evolution Assessment Cheat Sheet](references/evolution-assessment.md) — full characteristics table, load when scoring is uncertain
- [OWM Syntax Reference](references/owm-syntax.md) — complete DSL, load when writing complex maps
- [Tea Shop Example](references/examples/tea-shop.md) — canonical worked example
- [SaaS Platform Example](references/examples/saas-platform.md) — cloud/product worked example
