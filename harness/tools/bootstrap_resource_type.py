"""Automate onboarding a new Azure resource type for evaluation, the way
Storage was onboarded manually -- see docs/onboarding-new-resource-type.md
for the full guide this script implements.

What this automates:
  1. Resolve the given swagger ref (branch/tag) to an exact commit SHA,
     fetch the swagger file, and enumerate every property on it
     (harness.tools.enumerate_schema_properties) -- pinned, reproducible,
     no LLM involved. Writes sources/<provider_dir>/<slug>-properties.enumerated.json.
  2. Best-effort discovery of existing Azure Policy built-ins referencing
     the resource type (GitHub code search over Azure/azure-policy) --
     writes sources/<provider_dir>/<slug>-policy-refs.md. This step is
     best-effort and degrades gracefully (empty/placeholder file with a
     note) if code search is unavailable or rate-limited; it does not
     block the rest of onboarding.
  3. Scaffold harness/workflows/<slug>-atomic-tier.yaml from
     harness/workflows/_templates/atomic-tier.yaml.template.
  4. Scaffold harness/workflows/prompts/<slug>/schema_extract.md from
     harness/workflows/prompts/_templates/schema_extract.md.template.
     rule_compile.md/fixture_generate.md are resource-agnostic and
     shared -- not copied.
  5. Print the next manual steps (run_schema_coverage, coverage_status,
     run_hypothesis_buildout) with this resource type's arguments filled
     in.

What this does NOT automate (see the guide for why):
  - Judging which discovered policy built-ins are actually relevant, or
    writing narrative context beyond the raw policyRule conditions found.
  - Anything past step 5 -- schema_extract/rule_compile/fixture_generate
    are still real LLM calls you run yourself, same as for Storage.

Requires the `gh` CLI, authenticated, for both GitHub API calls (swagger
fetch and policy code search).

Usage:
    python -m harness.tools.bootstrap_resource_type \
        --swagger-repo Azure/azure-rest-api-specs \
        --swagger-ref main \
        --swagger-path specification/compute/resource-manager/Microsoft.Compute/stable/2024-07-01/virtualMachine.json \
        --root-definition VirtualMachineProperties \
        --resource-type Microsoft.Compute/virtualMachines \
        --slug vm \
        --provider-dir azure/compute \
        --check-id-prefix AZ-VM
"""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from urllib.parse import quote

from harness.tools.enumerate_schema_properties import enumerate_properties

REPO_ROOT = Path(__file__).resolve().parents[2]
TEMPLATES_DIR = REPO_ROOT / "harness" / "workflows" / "prompts" / "_templates"
WORKFLOW_TEMPLATE = (
    REPO_ROOT / "harness" / "workflows" / "_templates" / "atomic-tier.yaml.template"
)


def _gh_raw(args: list[str]) -> str:
    """For `gh api ... --jq <scalar>` calls -- jq's raw-value output for a
    string is plain text, not JSON-encoded, so json.loads() on it fails."""
    result = subprocess.run(["gh", *args], capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"gh {' '.join(args)} failed: {result.stderr}")
    return result.stdout.strip()


def _gh_json(args: list[str]) -> dict | list:
    result = subprocess.run(["gh", *args], capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"gh {' '.join(args)} failed: {result.stderr}")
    return json.loads(result.stdout)


def _resolve_commit_sha(repo: str, ref: str) -> str:
    return _gh_raw(["api", f"repos/{repo}/commits/{ref}", "--jq", ".sha"])


def _fetch_raw_file(repo: str, sha: str, path: str) -> str:
    # Path segments can contain spaces (e.g. "Key Vault/Foo.json" in the
    # azure-policy repo) -- confirmed live these 404 unless percent-encoded.
    encoded_path = "/".join(quote(segment) for segment in path.split("/"))
    result = subprocess.run(
        [
            "curl",
            "-sL",
            f"https://raw.githubusercontent.com/{repo}/{sha}/{encoded_path}",
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0 or not result.stdout.strip():
        raise RuntimeError(f"failed to fetch {repo}@{sha}:{path}")
    return result.stdout


def enumerate_and_save(
    swagger_repo: str,
    swagger_ref: str,
    swagger_path: str,
    root_definition: str,
    provider_dir: str,
    slug: str,
) -> tuple[Path, int]:
    sha = _resolve_commit_sha(swagger_repo, swagger_ref)
    print(f"resolved {swagger_repo}@{swagger_ref} -> {sha}")

    tmp_swagger = REPO_ROOT / f".bootstrap-{slug}-swagger.json"
    tmp_swagger.write_text(_fetch_raw_file(swagger_repo, sha, swagger_path))
    try:
        properties = enumerate_properties(tmp_swagger, root_definition)
    finally:
        tmp_swagger.unlink(missing_ok=True)

    out_dir = REPO_ROOT / "sources" / provider_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{slug}-properties.enumerated.json"
    result = {
        "root_definition": root_definition,
        "source_note": f"{swagger_repo}@{sha} {swagger_path}",
        "property_count": len(properties),
        "properties": properties,
    }
    out_path.write_text(json.dumps(result, indent=2))
    print(f"wrote {len(properties)} properties to {out_path}")
    return out_path, len(properties)


def discover_policy_refs(
    resource_type: str,
    provider_dir: str,
    slug: str,
    policy_repo: str = "Azure/azure-policy",
) -> Path:
    out_dir = REPO_ROOT / "sources" / provider_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{slug}-policy-refs.md"

    try:
        sha = _resolve_commit_sha(policy_repo, "master")
    except RuntimeError:
        sha = _resolve_commit_sha(policy_repo, "main")

    lines = [
        f"# {resource_type} existing Azure Policy built-in coverage (best-effort)",
        "",
        f"Repo: `{policy_repo}`",
        f"Commit: `{sha}`",
        "",
        "Best-effort GitHub code search for built-in policy definitions "
        f"referencing `{resource_type}`. Verify manually -- code search can "
        "miss matches (indexing lag, string formatting differences) or "
        "return irrelevant hits (the string appearing in an unrelated "
        "policy's description).",
        "",
    ]

    try:
        raw = _gh_raw(
            [
                "api",
                "-X",
                "GET",
                "search/code",
                "-f",
                f'q="{resource_type}" repo:{policy_repo} path:built-in-policies/policyDefinitions',
                "--jq",
                ".items[].path",
            ]
        )
        paths = [p for p in raw.splitlines() if p]
        if not paths:
            lines.append(
                "No matches found by code search. Search manually at "
                f"https://github.com/{policy_repo}/search?q=%22{resource_type}%22 "
                "and add relevant definitions here by hand."
            )
        for path in paths:
            try:
                content = json.loads(_fetch_raw_file(policy_repo, sha, path))
                display_name = content.get("properties", {}).get("displayName", "?")
                policy_if = (
                    content.get("properties", {}).get("policyRule", {}).get("if", {})
                )
                lines.append(f'- `{path}` -- "{display_name}"')
                lines.append(f"  - `policyRule.if`: `{json.dumps(policy_if)}`")
            except Exception as exc:  # noqa: BLE001 -- best-effort, log and continue
                lines.append(f"- `{path}` -- (failed to parse: {exc})")
    except RuntimeError as exc:
        lines.append(
            f"Code search failed ({exc}). Search manually at "
            f"https://github.com/{policy_repo}/search?q=%22{resource_type}%22 "
            "and add relevant definitions here by hand."
        )

    out_path.write_text("\n".join(lines) + "\n")
    print(f"wrote policy refs (best-effort) to {out_path}")
    return out_path


def scaffold_workflow(
    slug: str,
    resource_type: str,
    check_id_prefix: str,
    provider_dir: str,
    policy_refs_path: Path,
    enumerated_path: Path,
) -> Path:
    template = WORKFLOW_TEMPLATE.read_text()
    filled = (
        template.replace("{{SLUG}}", slug)
        .replace("{{RESOURCE_TYPE}}", resource_type)
        .replace("{{CHECK_ID_PREFIX}}", check_id_prefix)
        .replace("{{PROVIDER_DIR}}", provider_dir)
        .replace(
            "{{POLICY_REFS_PATH}}",
            str(policy_refs_path.relative_to(REPO_ROOT)).replace("\\", "/"),
        )
        .replace(
            "{{ENUMERATED_PROPERTIES_PATH}}",
            str(enumerated_path.relative_to(REPO_ROOT)).replace("\\", "/"),
        )
    )
    out_path = REPO_ROOT / "harness" / "workflows" / f"{slug}-atomic-tier.yaml"
    out_path.write_text(filled)
    print(f"wrote workflow to {out_path}")
    return out_path


def scaffold_schema_extract_prompt(
    slug: str, resource_type: str, policy_refs_path: Path, enumerated_path: Path
) -> Path:
    template = (TEMPLATES_DIR / "schema_extract.md.template").read_text()
    filled = (
        template.replace("{{RESOURCE_TYPE}}", resource_type)
        .replace(
            "{{POLICY_REFS_PATH}}",
            str(policy_refs_path.relative_to(REPO_ROOT)).replace("\\", "/"),
        )
        .replace(
            "{{ENUMERATED_PROPERTIES_PATH}}",
            str(enumerated_path.relative_to(REPO_ROOT)).replace("\\", "/"),
        )
    )
    out_dir = REPO_ROOT / "harness" / "workflows" / "prompts" / slug
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "schema_extract.md"
    out_path.write_text(filled)
    print(f"wrote schema_extract prompt to {out_path}")
    return out_path


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--swagger-repo", default="Azure/azure-rest-api-specs")
    parser.add_argument("--swagger-ref", default="main")
    parser.add_argument("--swagger-path", required=True)
    parser.add_argument("--root-definition", required=True)
    parser.add_argument(
        "--resource-type", required=True, help="e.g. Microsoft.Compute/virtualMachines"
    )
    parser.add_argument(
        "--slug", required=True, help="short filesystem-friendly name, e.g. vm"
    )
    parser.add_argument("--provider-dir", required=True, help="e.g. azure/compute")
    parser.add_argument("--check-id-prefix", required=True, help="e.g. AZ-VM")
    parser.add_argument("--policy-repo", default="Azure/azure-policy")
    parser.add_argument(
        "--skip-policy-discovery",
        action="store_true",
        help="skip the best-effort GitHub code search step entirely",
    )
    args = parser.parse_args()

    enumerated_path, property_count = enumerate_and_save(
        args.swagger_repo,
        args.swagger_ref,
        args.swagger_path,
        args.root_definition,
        args.provider_dir,
        args.slug,
    )

    if args.skip_policy_discovery:
        policy_refs_path = (
            REPO_ROOT / "sources" / args.provider_dir / f"{args.slug}-policy-refs.md"
        )
        policy_refs_path.parent.mkdir(parents=True, exist_ok=True)
        policy_refs_path.write_text(
            f"# {args.resource_type} existing Azure Policy built-in coverage\n\n"
            "(Policy discovery skipped -- add relevant built-in definitions here by hand.)\n"
        )
    else:
        policy_refs_path = discover_policy_refs(
            args.resource_type, args.provider_dir, args.slug, args.policy_repo
        )

    workflow_path = scaffold_workflow(
        args.slug,
        args.resource_type,
        args.check_id_prefix,
        args.provider_dir,
        policy_refs_path,
        enumerated_path,
    )
    scaffold_schema_extract_prompt(
        args.slug, args.resource_type, policy_refs_path, enumerated_path
    )

    # Relative to REPO_ROOT (not absolute) so the printed commands below
    # are actually copy-pasteable -- an absolute path under a directory
    # with a space in it (as this repo's own path has) breaks unquoted.
    def rel(p: Path) -> str:
        return str(p.relative_to(REPO_ROOT)).replace("\\", "/")

    enumerated_rel = rel(enumerated_path)
    policy_refs_rel = rel(policy_refs_path)
    workflow_rel = rel(workflow_path)

    print()
    print("=== Next steps ===")
    print(f"1. Review {policy_refs_rel} by hand -- code search is best-effort.")
    print(f"2. Review the scaffolded workflow: {workflow_rel}")
    print("3. Sweep to full property coverage:")
    print(
        f'   uv run --frozen python -m harness.tools.run_schema_coverage "{enumerated_rel}" '
        f'"{args.resource_type}" --extra-file "{policy_refs_rel}" --batch-size 10'
    )
    print("4. Confirm completion:")
    print(
        f'   uv run --frozen python -m harness.tools.coverage_status "{enumerated_rel}" "{args.resource_type}"'
    )
    print("5. Compile every discovered hypothesis into a validated rule:")
    print(
        f'   uv run --frozen python -m harness.tools.run_hypothesis_buildout --workflow "{workflow_rel}"'
    )
    print(f"({property_count} properties enumerated)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
