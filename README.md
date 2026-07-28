# Biffo Plugins Registry

Central registry of official Biffo plugins. `plugins.json` is the single source
of truth for what the marketplace offers.

It is consumed **live** — the portal marketplace
(`apps/portal/src/lib/plugin-api.ts`) and the CLI
(`cli/src/adapters/registry/index.ts`) both fetch it straight from
`raw.githubusercontent.com` on `main`. There is no build step and no staging
copy: whatever lands on `main` is what every Biffo instance sees, immediately.

## Structure

- **`plugins.json`** — index of all available plugins with metadata (name, version, repo URL, description, tags, etc.)
- **`registry-schema.json`** — JSON Schema (draft-07) that validates `plugins.json`
- **`scripts/upsert_plugin.py`** — upserts one plugin's entry from its `biffo.plugin.json`

## How entries get here

Each plugin repo publishes its own entry on merge to `dev`, via a
`publish-registry.yml` workflow that calls `scripts/upsert_plugin.py` in this
repo. You should not normally need to hand-edit `plugins.json` for a version
bump — that tracks the plugin's manifest automatically.

### Curated vs. derived fields

`description`, `tags` and `ui_components` are **marketplace copy**. They are
written to sell the plugin to a human browsing the store, and are deliberately
*not* the same thing as the plugin manifest's own `description`, which is
written for engineers. An automated publish therefore **preserves** those three
fields once set, and only seeds them from the manifest on a plugin's first
publish.

Everything else — `version`, `minor_version`, `repo`, `required_core_version`,
`api_routes` — is derived from the manifest on every publish.

To deliberately overwrite the curated copy from the manifest, pass
`--refresh-copy`.

`status` is an operator decision and is never changed by a publish.

## Adding or editing a plugin by hand

```bash
pip install jsonschema

# Upsert from a plugin's manifest
python3 scripts/upsert_plugin.py \
  --manifest ../biffo-plugin-<name>/biffo.plugin.json \
  --repo https://github.com/keiranholloway/biffo-plugin-<name>

# Then edit plugins.json to write the marketplace copy, and validate
python3 -c "
import json, jsonschema
jsonschema.Draft7Validator(json.load(open('registry-schema.json'))).validate(json.load(open('plugins.json')))
print('valid')"

git commit -am "feat(registry): add <plugin-name>@<version>"
git push origin main
```

CI (`.github/workflows/validate.yml`) runs the same validation on every push and
pull request, and additionally rejects duplicate plugin names.

## Plugin status

- `active` — visible in the marketplace dashboard
- `disabled` — hidden from the marketplace but preserved in the registry for historical records

## Registered plugins

| Plugin | Repository | Distribution |
| --- | --- | --- |
| `ideation` | [`biffo-plugin-ideation`](https://github.com/keiranholloway/biffo-plugin-ideation) | installable |
| `idea-scout` | [`biffo-plugin-idea-scout`](https://github.com/keiranholloway/biffo-plugin-idea-scout) | installable |
| `orchestrator` | [`biffo-template`](https://github.com/keiranholloway/biffo-template) (`services/_plugins/orchestrator/`) | built-in |
| `agent-runtime` | [`biffo-template`](https://github.com/keiranholloway/biffo-template) (`services/_plugins/agent-runtime/`) | built-in |

**Built-in** plugins ship inside Biffo core and are distributed by `biffo core
upgrade`, not by `biffo plugin install`. They are listed here so the marketplace
shows the full set of capabilities available to an instance; they carry a
`built-in` tag to mark them as already present. Do not run `biffo plugin
install` against them.

See each plugin's README for its internal structure and manifest format.
