"""FSM workflow runner for the Multi-Model Cloud Configuration Discovery Harness.

Loads a workflow YAML file (see the contract in the module docstring below),
executes each state against the journal, and invokes the Claude Code CLI
headless for LLM-driven states using the role/model mapping in roles.yaml.

Workflow YAML contract (one file per workflow under harness/workflows/):

    workflow: string                 # name
    states:
      - name: string
        role: orchestrator | executor_claude | executor_glm   # LLM states
        # -- or, for non-LLM states --
        type: adapter | gate                                  # deterministic states
        reads: [journal table names this state queries]
        writes: [journal table names this state inserts/updates]
        prompt_template: path to a .md file (LLM states only)
        next_on_success: state name or 'end'
        next_on_failure: state name or 'end'

`role` and `type` are mutually exclusive: a state either delegates to an LLM
role (executed by this runner via the Claude Code CLI) or is a deterministic
state (`adapter`/`gate`) whose behavior is implemented directly by the
runner/adapters, never by a model.

Guardrail: `orchestrator`-role states may only declare `reads` against
hypotheses, rules, and runs -- never fixtures -- so raw fixture/source
content is never placed in the orchestrator's context.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from harness.journal.db import connect  # noqa: E402

ENGINE_DIR = Path(__file__).parent
ROLES_PATH = ENGINE_DIR / "roles.yaml"
ENV_PATH = ENGINE_DIR / ".env"
REPO_ROOT = Path(__file__).resolve().parents[2]

ORCHESTRATOR_ALLOWED_READS = {"hypotheses", "rules", "runs"}


class WorkflowError(RuntimeError):
    pass


def load_roles(roles_path: Path = ROLES_PATH) -> dict[str, Any]:
    return yaml.safe_load(roles_path.read_text())["roles"]


def load_env_file(env_path: Path = ENV_PATH) -> dict[str, str]:
    """Parse a simple KEY=VALUE .env file. Missing file -> empty dict."""
    if not env_path.exists():
        return {}
    values = {}
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        values[key.strip()] = value.strip()
    return values


def load_workflow(workflow_path: Path) -> dict[str, Any]:
    workflow = yaml.safe_load(Path(workflow_path).read_text())
    for state in workflow.get("states", []):
        has_role = "role" in state
        has_type = "type" in state
        if has_role == has_type:
            raise WorkflowError(
                f"state '{state.get('name')}' must declare exactly one of "
                f"'role' or 'type'"
            )
        if state.get("role") == "orchestrator":
            extra = set(state.get("reads", [])) - ORCHESTRATOR_ALLOWED_READS
            if extra:
                raise WorkflowError(
                    f"state '{state['name']}' is role=orchestrator but reads "
                    f"disallowed table(s) {extra}; orchestrator may only read "
                    f"{sorted(ORCHESTRATOR_ALLOWED_READS)}"
                )
    return workflow


def _state_by_name(workflow: dict[str, Any], name: str) -> dict[str, Any] | None:
    for state in workflow["states"]:
        if state["name"] == name:
            return state
    return None


def _read_tables(conn, table_names: list[str]) -> dict[str, list[dict]]:
    context = {}
    for table in table_names:
        rows = conn.execute(f"SELECT * FROM {table}").fetchall()
        context[table] = [dict(row) for row in rows]
    return context


def _invoke_claude(role_name: str, roles: dict, prompt: str) -> str:
    """Invoke the Claude Code CLI headless for the given role, return the
    model's raw text result (state-specific JSON parsing happens by the
    caller)."""
    role = roles[role_name]
    env = os.environ.copy()
    env.update(role.get("env", {}))
    env_file_values = load_env_file()
    api_key_var = f"{role_name.upper()}_ANTHROPIC_API_KEY"
    if api_key_var in env_file_values:
        env["ANTHROPIC_API_KEY"] = env_file_values[api_key_var]

    result = subprocess.run(
        ["claude", "-p", prompt, "--output-format", "json", "--model", role["model"]],
        env=env,
        capture_output=True,
        text=True,
        timeout=300,
    )
    if result.returncode != 0:
        raise WorkflowError(
            f"claude invocation failed for role={role_name}: {result.stderr}"
        )
    outer = json.loads(result.stdout)
    if outer.get("is_error"):
        raise WorkflowError(f"claude reported an error for role={role_name}: {outer}")
    return outer["result"]


def _render_prompt(template_path: Path, context: dict[str, Any]) -> str:
    template = template_path.read_text()
    return template + "\n\n## Journal context\n\n" + json.dumps(context, indent=2)


class Runner:
    def __init__(self, db_path=None):
        self.conn = connect(db_path) if db_path else connect()
        self.roles = load_roles()

    def start(self, workflow_path: Path) -> int:
        workflow = load_workflow(workflow_path)
        first_state = workflow["states"][0]["name"]
        cur = self.conn.execute(
            "INSERT INTO workflow_runs (workflow_name, workflow_path, current_state, status, context_json) "
            "VALUES (?, ?, ?, 'running', '{}')",
            (workflow["workflow"], str(workflow_path), first_state),
        )
        self.conn.commit()
        run_id = cur.lastrowid
        return self.resume(run_id, workflow_path)

    def resume(self, run_id: int, workflow_path: Path) -> int:
        workflow = load_workflow(workflow_path)
        row = self.conn.execute(
            "SELECT * FROM workflow_runs WHERE id = ?", (run_id,)
        ).fetchone()
        if row is None:
            raise WorkflowError(f"no workflow_runs row with id={run_id}")

        state_name = row["current_state"]
        context = json.loads(row["context_json"] or "{}")

        while state_name != "end":
            state = _state_by_name(workflow, state_name)
            if state is None:
                raise WorkflowError(f"unknown state '{state_name}' in workflow")

            print(f"[runner] run={run_id} entering state '{state_name}'")
            success = self._execute_state(state, context)

            next_state = state["next_on_success"] if success else state["next_on_failure"]
            self.conn.execute(
                "UPDATE workflow_runs SET current_state = ?, context_json = ?, "
                "status = ?, updated_at = datetime('now') WHERE id = ?",
                (
                    next_state,
                    json.dumps(context),
                    "running" if next_state != "end" else "completed",
                    run_id,
                ),
            )
            self.conn.commit()
            state_name = next_state

        print(f"[runner] run={run_id} reached end")
        return run_id

    def _execute_state(self, state: dict[str, Any], context: dict[str, Any]) -> bool:
        """Execute one state. Returns True on success, False on failure.

        LLM states (role set) are executed here via the Claude Code CLI.
        Deterministic states (type: adapter/gate) are dispatched to
        harness.adapters / gate logic and must never invoke a model.
        """
        if state.get("type") == "adapter":
            return self._execute_adapter_state(state, context)
        if state.get("type") == "gate":
            return self._execute_gate_state(state, context)
        return self._execute_llm_state(state, context)

    def _execute_llm_state(self, state: dict[str, Any], context: dict[str, Any]) -> bool:
        journal_context = _read_tables(self.conn, state.get("reads", []))
        journal_context["_run_context"] = context
        prompt_template = REPO_ROOT / state["prompt_template"]
        prompt = _render_prompt(prompt_template, journal_context)

        raw_result = _invoke_claude(state["role"], self.roles, prompt)
        print(f"[runner] state '{state['name']}' model output: {raw_result}")
        context[f"last_output::{state['name']}"] = raw_result
        return True

    def _execute_adapter_state(self, state: dict[str, Any], context: dict[str, Any]) -> bool:
        raise NotImplementedError(
            "adapter states are wired up per-workflow; see harness/workflows/storage-atomic-tier.yaml"
        )

    def _execute_gate_state(self, state: dict[str, Any], context: dict[str, Any]) -> bool:
        raise NotImplementedError(
            "gate states are wired up per-workflow; see harness/workflows/storage-atomic-tier.yaml"
        )


def main():
    parser = argparse.ArgumentParser(description="Run an FSM workflow.")
    parser.add_argument("workflow", type=Path, help="path to workflow YAML")
    parser.add_argument("--resume", type=int, help="workflow_runs.id to resume")
    parser.add_argument("--db", type=Path, default=None)
    args = parser.parse_args()

    runner = Runner(db_path=args.db)
    if args.resume:
        run_id = runner.resume(args.resume, args.workflow)
    else:
        run_id = runner.start(args.workflow)
    print(f"[runner] finished workflow_runs.id={run_id}")


if __name__ == "__main__":
    main()
