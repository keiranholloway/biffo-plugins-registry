#!/usr/bin/env python3
"""Upsert one plugin's entry in plugins.json from its biffo.plugin.json.

This is the mechanism that stops the registry drifting out of date. It used to
drift completely: every plugin ever built was missing from plugins.json, so the
portal marketplace rendered "No plugins available yet" while two plugins were
live in production.

Plugin repos call this from a workflow on merge to `dev` (see
.github/workflows/publish-registry.yml in each plugin repo), passing their own
manifest and clone URL.

Curated marketplace copy is NOT overwritten. `description`, `tags` and
`ui_components` are marketing surface, hand-written to sell the plugin, and a
plugin manifest's own `description` is written for engineers instead. So on an
update those three fields are preserved unless --refresh-copy is passed; on a
first publish they are seeded from the manifest and are expected to be edited
afterwards. Everything else (version, repo, required_core_version, api_routes)
tracks the manifest automatically.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
REGISTRY_PATH = REPO_ROOT / "plugins.json"
SCHEMA_PATH = REPO_ROOT / "registry-schema.json"

# Fields a human curates for the marketplace listing; see module docstring.
CURATED_FIELDS = ("description", "tags", "ui_components")

# registry-schema.json restricts infra_modules to this enum, so a manifest
# naming anything outside it would produce an entry that fails validation.
KNOWN_INFRA_MODULES = {
    "compute",
    "storage",
    "events",
    "cdn",
    "database",
    "auth",
    "networking",
    "oidc",
    "api-gateway",
}


def load_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def entry_from_manifest(manifest: dict, repo: str, extra_tags: list[str]) -> dict:
    """Build a registry entry from a plugin manifest.

    Only the fields registry-schema.json allows, and only in the shape it
    allows: the manifest's `api_routes` are route *objects*, whereas the
    registry documents them as plain path strings.
    """
    version = manifest["version"]
    match = re.fullmatch(r"(\d+)\.(\d+)\.\d+", version)
    if match is None:
        raise SystemExit(
            f"manifest version {version!r} is not a three-part semver, "
            "which registry-schema.json requires"
        )

    entry: dict = {
        "name": manifest["name"],
        "version": version,
        "minor_version": f"{match.group(1)}.{match.group(2)}",
        "repo": repo,
        "status": "active",
    }

    description = manifest.get("description")
    if description:
        # The schema caps this at 500 characters; plugin manifests carry much
        # longer prose than a marketplace card can show.
        entry["description"] = description[:500]

    author = manifest.get("author")
    if author:
        entry["author"] = author

    tags = list(manifest.get("tags") or [])
    for tag in extra_tags:
        if tag not in tags:
            tags.insert(0, tag)
    if tags:
        entry["tags"] = tags

    required_core = manifest.get("required_core_version")
    if required_core:
        entry["required_core_version"] = required_core

    routes = [r["path"] for r in manifest.get("api_routes") or [] if r.get("path")]
    if routes:
        entry["api_routes"] = sorted(set(routes))

    infra = [m for m in manifest.get("infra_modules") or [] if m in KNOWN_INFRA_MODULES]
    if infra:
        entry["infra_modules"] = infra

    return entry


def upsert(registry: dict, entry: dict, refresh_copy: bool) -> str:
    plugins = registry["plugins"]
    for index, existing in enumerate(plugins):
        if existing["name"] == entry["name"]:
            merged = {**existing, **entry}
            if not refresh_copy:
                for field in CURATED_FIELDS:
                    # Keep the curated value where one exists; otherwise seed
                    # from the manifest so a newly-added field still lands.
                    if field in existing:
                        merged[field] = existing[field]
            # `status` is an operator decision (a plugin can be pulled from the
            # marketplace without being deleted), never something a publish
            # from the plugin's own repo should silently flip back to active.
            merged["status"] = existing.get("status", "active")
            plugins[index] = merged
            return "updated" if merged != existing else "unchanged"

    plugins.append(entry)
    plugins.sort(key=lambda p: p["name"])
    return "added"


def validate(registry: dict) -> None:
    try:
        import jsonschema
    except ImportError:
        print("jsonschema not installed — skipping schema validation", file=sys.stderr)
        return
    schema = load_json(SCHEMA_PATH)
    errors = sorted(
        jsonschema.Draft7Validator(schema).iter_errors(registry),
        key=lambda e: list(e.path),
    )
    if errors:
        for error in errors:
            print(f"schema error at {list(error.path)}: {error.message}", file=sys.stderr)
        raise SystemExit(1)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path, help="path to biffo.plugin.json")
    parser.add_argument("--repo", required=True, help="clone URL of the plugin repository")
    parser.add_argument(
        "--tag",
        action="append",
        default=[],
        dest="extra_tags",
        help="extra marketplace tag to prepend (repeatable), e.g. --tag built-in",
    )
    parser.add_argument(
        "--refresh-copy",
        action="store_true",
        help="also overwrite the curated description/tags/ui_components from the manifest",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="report what would change and exit non-zero if it would, without writing",
    )
    args = parser.parse_args()

    manifest = load_json(args.manifest)
    registry = load_json(REGISTRY_PATH)
    before = json.dumps(registry, sort_keys=True)

    entry = entry_from_manifest(manifest, args.repo, args.extra_tags)
    outcome = upsert(registry, entry, args.refresh_copy)

    changed = json.dumps(registry, sort_keys=True) != before
    if changed:
        registry["last_updated"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    validate(registry)

    if args.check:
        print(f"{entry['name']}: would be {outcome}")
        return 1 if changed else 0

    if not changed:
        print(f"{entry['name']}: already up to date at {entry['version']}")
        return 0

    with REGISTRY_PATH.open("w", encoding="utf-8") as handle:
        json.dump(registry, handle, indent=2)
        handle.write("\n")
    print(f"{entry['name']}: {outcome} at {entry['version']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
