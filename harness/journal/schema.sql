-- Journal schema for the Multi-Model Cloud Configuration Discovery Harness.
-- Applied idempotently by db.py via CREATE TABLE IF NOT EXISTS.

CREATE TABLE IF NOT EXISTS hypotheses (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  resource_type TEXT NOT NULL,           -- e.g. Microsoft.Storage/storageAccounts
  property_path TEXT NOT NULL,           -- e.g. properties.networkAcls.defaultAction
  risky_value TEXT,
  safe_value TEXT,
  rationale TEXT NOT NULL,
  source_doc TEXT NOT NULL,              -- URL or repo path + commit SHA
  existing_policy_ref TEXT,              -- Azure built-in Policy name, nullable
  proposed_by_model TEXT NOT NULL,       -- e.g. claude-opus-4-8, glm-5.2
  tier INTEGER NOT NULL,                 -- 1=atomic, 2=pattern, 3=chained
  status TEXT NOT NULL DEFAULT 'proposed', -- proposed | promoted | rejected
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS rules (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  hypothesis_id INTEGER NOT NULL REFERENCES hypotheses(id),
  check_id TEXT NOT NULL UNIQUE,         -- e.g. AZ-STOR-001
  rule_path TEXT NOT NULL,               -- file path under rules/
  status TEXT NOT NULL DEFAULT 'draft',  -- draft | validated | deprecated
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS fixtures (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  check_id TEXT NOT NULL REFERENCES rules(check_id),
  fixture_path TEXT NOT NULL,            -- dir under fixtures/
  ground_truth_method TEXT NOT NULL,     -- e.g. azure-policy-builtin, manual-expert, iam-simulator
  ground_truth_ref TEXT,                 -- policy definition ID or reviewer name
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS runs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  check_id TEXT NOT NULL REFERENCES rules(check_id),
  fixture_id INTEGER NOT NULL REFERENCES fixtures(id),
  adapter TEXT NOT NULL,                 -- bicep_validate | rego_validate
  expected_verdict TEXT NOT NULL,        -- pass | fail
  actual_verdict TEXT NOT NULL,
  passed INTEGER NOT NULL,               -- 0 or 1
  raw_output TEXT,
  run_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS findings (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  check_id TEXT NOT NULL REFERENCES rules(check_id),
  target TEXT NOT NULL,                  -- resource ID or fixture path being evaluated
  verdict TEXT NOT NULL,
  evaluated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Added after Task 7: `rules`/`fixtures` above are current-state-only
-- (one mutable row per check_id) -- fine for the retry-until-validated
-- loop they were designed for, but it means whichever workflow_run last
-- wrote a check_id silently overwrites any earlier run's content, with no
-- way to recover what an earlier run actually produced. That broke
-- compare_runs.py for two runs A/B'd against the same check_id (rego
-- diff had nothing to diff once B overwrote A). These two tables are
-- append-only, one row per write, so every run's actual content survives
-- regardless of what a later run does to the same check_id -- this is
-- the "journal tracks provenance and run history" half of the plan's
-- journal/git split (docs/plans/multi-model-config-discovery.md), which
-- `rules`/`fixtures` alone didn't fully deliver.
CREATE TABLE IF NOT EXISTS rule_history (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  workflow_run_id INTEGER REFERENCES workflow_runs(id),
  check_id TEXT NOT NULL,
  rule_path TEXT NOT NULL,
  rego_content TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS fixture_history (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  workflow_run_id INTEGER REFERENCES workflow_runs(id),
  check_id TEXT NOT NULL,
  fixture_path TEXT NOT NULL,
  vulnerable_bicep TEXT NOT NULL,
  safe_bicep TEXT NOT NULL,
  ground_truth_method TEXT,
  ground_truth_ref TEXT,
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Added during Task 3 (runner skeleton): tracks in-flight/completed FSM runs
-- so a crashed run can resume from its last completed state.
CREATE TABLE IF NOT EXISTS workflow_runs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  workflow_name TEXT NOT NULL,           -- name field from the workflow YAML
  workflow_path TEXT NOT NULL,           -- path to the workflow YAML file
  current_state TEXT NOT NULL,           -- name of the state to run/resume next
  status TEXT NOT NULL DEFAULT 'running', -- running | completed | failed
  context_json TEXT,                     -- accumulated cross-state context (e.g. retry reasons)
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);
