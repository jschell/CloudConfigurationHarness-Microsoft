# Pattern: never let the model assign its own identifiers

## The bug this documents

`rule_compile` originally asked the model to pick its own `check_id`
(`AZ-STOR-NNN`, "next unused number") and `rule_path`, and to write its
own Rego `package` declaration naming that check_id. Its `reads:` only
included `hypotheses`, not `rules` -- so the model had to guess the next
unused number with no visibility into which numbers were already taken.
Worse, each call to `rule_compile` is a stateless CLI invocation
(`claude -p` / equivalent), with **no memory of any other call**, so even
adding `rules` to `reads` only reduces the odds of a bad guess, it
doesn't eliminate them -- the model still has to correctly scan and count
across however many rows exist, every single time, from scratch.

Running a 35-hypothesis batch buildout (2026-07-02) hit this for real,
three separate times: `AZ-STOR-006`, `AZ-STOR-014`, and `AZ-STOR-020` were
each assigned to two different hypotheses by different calls. Each time,
the second call's content silently overwrote the first's file on disk,
while the `rules` table's `hypothesis_id` column kept pointing at the
*first* (now-wrong) hypothesis -- the journal was left actively lying
about what the check actually tested. Recovery was only possible because
`rule_history`/`fixture_history` (docs/patterns/schema-coverage-discovery.md's
append-only ledger pattern, added earlier the same day) had preserved
every version ever written, including the ones later overwritten.

## The general rule

**Never ask a model to invent an identifier whose uniqueness matters,
when the harness itself can compute it deterministically.** This applies
beyond check_ids -- any time a value needs to be unique across calls the
model has no memory of, assigning it in code removes an entire class of
bug rather than reducing its likelihood. Giving the model more context
(a bigger `reads:` list, more of the existing table) is not equivalent to
this fix; it lowers the odds of a collision without eliminating the
possibility, and every additional row of context also costs prompt size
and latency for no correctness benefit.

Concretely, in `harness/engine/handlers.py`:

- `_check_id_for_hypothesis()` assigns the check_id: reuse the existing
  one if `rules` already has a row for this `hypothesis_id` (a
  gate-triggered retry), otherwise take the max numeric suffix seen
  across **both** `rules` and `rule_history` and add one. Checking
  `rule_history` too means a check_id number is never reused even if the
  `rules` row that used it was later superseded by a retry -- the number
  stays permanently retired.
- The model still writes the Rego rule body, but starts the file with a
  literal `package PLACEHOLDER` line rather than naming its own package
  -- the handler substitutes the real `checks.<check_id>` namespace via
  regex after the check_id is known. Same reasoning: the model can't
  correctly name a package after a check_id it was never told.
- `fixture_generate`'s `check_id`/`fixture_dir` are read from
  `context["check_id"]` (set by `rule_compile` earlier in the *same* run,
  so it's a real, authoritative value already known -- not asked from
  the model at all, removing a second, smaller instance of the same
  failure class in the same pipeline.

## When it's fine to let the model choose

When the value doesn't need global uniqueness across stateless calls --
e.g. a `rationale` string, a `msg` in a Rego `deny` rule, which Bicep
property names to include in a minimal fixture. The distinguishing
question: **"if the model picks this wrong or inconsistently across two
separate calls, does anything silently break or get overwritten?"** If
yes, assign it in code.
