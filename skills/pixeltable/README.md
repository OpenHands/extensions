# Pixeltable

Use this skill when the project already uses Pixeltable. It covers TableModel application files, computed columns, embedding indexes, FastAPIRouter routes, UDFs (`pxt.udf`), and the `pxt` CLI (`pxt schema`, `pxt service`). Canonical docs: https://docs.pixeltable.com/

## Triggers

This skill is activated by the following keywords:

- `pixeltable`
- `pxt.udf`
- `pxt.query`
- `pxt.create_table`
- `pxt.tools`
- `pxt.serve`

## What it covers

- Application files (`app.py`) with `TableModel` classes, applied by `pxt schema update`
- HTTP routes with `FastAPIRouter`, started by `pxt service update`
- Computed columns that run on insert
- Embedding indexes and similarity search
- UDFs, UDAs, and tool calling (`pxt.tools`, `invoke_tools`)
- Views and iterators (documents, video, audio, images)
- The `pxt` CLI for schema, serving, inspection, and Cloud
- AI provider integrations

## Links

- [Documentation](https://docs.pixeltable.com/)
- [CLI](https://docs.pixeltable.com/platform/cli)
- [GitHub](https://github.com/pixeltable/pixeltable)
- [Discussions](https://github.com/pixeltable/pixeltable/discussions)
