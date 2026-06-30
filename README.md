# Biffo Plugins Registry

Central registry of official Biffo plugins. The `plugins.json` file is the single source of truth for available plugins.

## Structure

- **`plugins.json`** — Index of all available plugins with metadata (name, version, repo URL, description, tags, etc.)
- **`registry-schema.json`** — JSON Schema for validating `plugins.json`

## Adding a Plugin

To add or update a plugin:

1. Edit `plugins.json` — add a new entry or update an existing one
2. Validate against the schema: `python3 -m json.tool registry-schema.json > /dev/null`
3. Commit and push

```bash
git add plugins.json
git commit -m "feat(registry): add <plugin-name>@<version>"
git push origin main
```

## Plugin Status

- `active` — visible in the marketplace dashboard
- `disabled` — hidden from the marketplace but preserved in the registry for historical records

## Plugin Repositories

Each plugin lives in its own GitHub repository under the `keiranholloway` org:

- `biffo-plugin-invoicing` — Invoice generation and billing
- `biffo-plugin-analytics` — Analytics and reporting
- etc.

See each plugin's README for its internal structure and manifest format.