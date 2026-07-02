"""Deterministically enumerate every property on a swagger definition.

This is the first half of the "structured discovery" pattern documented
in docs/patterns/schema-coverage-discovery.md: before any LLM proposes
security hypotheses, produce a complete, code-generated list of every
property on the resource so nothing depends on the model (or a human)
happening to notice a property while skimming curated doc excerpts.
`$ref`s are resolved recursively within the same swagger file, so nested
objects (e.g. `networkAcls` -> `NetworkRuleSet` -> `defaultAction`) show
up as dotted paths (`properties.networkAcls.defaultAction`).

No network access, no LLM calls -- pure, offline, and re-runnable. This
is the same reason `bicep_validate`/`rego_validate` are separate from the
LLM states: this enumeration must be independently verifiable and never
depend on a model's judgment about "did I read the whole spec."

Usage:
    python -m harness.tools.enumerate_schema_properties \
        <swagger.json> <RootDefinitionName> [--out <file.json>]
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

MAX_DEPTH = 6


def _resolve_ref(ref: str, definitions: dict[str, Any]) -> dict[str, Any]:
    # e.g. "#/definitions/NetworkRuleSet" -> definitions["NetworkRuleSet"]
    name = ref.rsplit("/", 1)[-1]
    return definitions[name]


def _enumerate(
    schema: dict[str, Any],
    definitions: dict[str, Any],
    path_prefix: str,
    visited: frozenset[str],
    depth: int,
    out: list[dict[str, Any]],
) -> None:
    if depth > MAX_DEPTH:
        return

    if "$ref" in schema:
        ref_name = schema["$ref"].rsplit("/", 1)[-1]
        if ref_name in visited:
            return  # cycle guard
        if ref_name not in definitions:
            # $refs into a different swagger file (e.g. privatelinks.json)
            # aren't resolvable from a single-file input -- record as an
            # unexpanded leaf rather than crash. Still shows up in the
            # coverage list, just without its own nested properties.
            out.append(
                {
                    "property_path": path_prefix,
                    "type": "object",
                    "enum": None,
                    "default": None,
                    "description": f"(unresolved cross-file $ref: {ref_name})",
                    "read_only": False,
                }
            )
            return
        _enumerate(
            _resolve_ref(schema["$ref"], definitions),
            definitions,
            path_prefix,
            visited | {ref_name},
            depth,
            out,
        )
        return

    if schema.get("type") == "array" and "items" in schema:
        _enumerate(
            schema["items"], definitions, path_prefix + "[]", visited, depth + 1, out
        )
        return

    properties = schema.get("properties")
    if not properties:
        # Leaf scalar/enum -- record it.
        out.append(
            {
                "property_path": path_prefix,
                "type": schema.get("type", "object"),
                "enum": schema.get("enum"),
                "default": schema.get("default"),
                "description": schema.get("description", ""),
                "read_only": bool(schema.get("readOnly", False)),
            }
        )
        return

    for name, sub_schema in properties.items():
        child_path = f"{path_prefix}.{name}" if path_prefix else name
        read_only = bool(sub_schema.get("readOnly", False))
        if "$ref" in sub_schema or sub_schema.get("type") in ("object", "array"):
            _enumerate(sub_schema, definitions, child_path, visited, depth + 1, out)
        else:
            out.append(
                {
                    "property_path": child_path,
                    "type": sub_schema.get("type", "object"),
                    "enum": sub_schema.get("enum"),
                    "default": sub_schema.get("default"),
                    "description": sub_schema.get("description", ""),
                    "read_only": read_only,
                }
            )


def enumerate_properties(
    swagger_path: str | Path, root_definition: str, path_prefix: str = "properties"
) -> list[dict[str, Any]]:
    swagger = json.loads(Path(swagger_path).read_text())
    definitions = swagger["definitions"]
    out: list[dict[str, Any]] = []
    _enumerate(
        {"$ref": f"#/definitions/{root_definition}"},
        definitions,
        path_prefix,
        frozenset(),
        0,
        out,
    )
    # Stable order, deduplicated by path (a property can be reachable via
    # more than one $ref chain in pathological schemas).
    seen: set[str] = set()
    deduped = []
    for entry in sorted(out, key=lambda e: e["property_path"]):
        if entry["property_path"] not in seen:
            seen.add(entry["property_path"])
            deduped.append(entry)
    return deduped


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("swagger_path", type=Path)
    parser.add_argument("root_definition", type=str)
    parser.add_argument("--path-prefix", type=str, default="properties")
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument(
        "--source-note",
        type=str,
        default=None,
        help="provenance string embedded in the output, e.g. "
        "'Azure/azure-rest-api-specs@<sha> path/to/storage.json' -- "
        "the committed output is only reproducible if this is recorded",
    )
    args = parser.parse_args()

    properties = enumerate_properties(
        args.swagger_path, args.root_definition, args.path_prefix
    )
    result = {
        "root_definition": args.root_definition,
        "source_note": args.source_note,
        "property_count": len(properties),
        "properties": properties,
    }
    text = json.dumps(result, indent=2)
    if args.out:
        args.out.write_text(text)
        print(f"wrote {len(properties)} properties to {args.out}")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
