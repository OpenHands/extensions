# spark-version-upgrade

Upgrade Apache Spark applications between major versions (2.x→3.x, 3.x→4.x). Covers build files, deprecated APIs, configuration changes, SQL/DataFrame updates, and test validation.

## Triggers

This skill is activated by the following keywords:

- `spark upgrade`
- `spark migration`
- `spark version`
- `upgrade spark`
- `spark 3`
- `spark 4`
- `pyspark upgrade`

## Overview

This skill provides a structured, six-phase workflow for upgrading Apache Spark applications:

| Phase | Description |
|-------|-------------|
| 1. Inventory & Impact Analysis | Scan the codebase, identify Spark usage, document scope |
| 2. Build File Updates | Bump Spark/Scala/Java versions in Maven, SBT, Gradle, or pip |
| 3. API Migration | Replace removed/deprecated APIs (SQLContext, Accumulator, etc.) |
| 4. Configuration Migration | Rename/remove deprecated Spark config properties |
| 5. SQL & DataFrame Migration | Fix breaking SQL behavior (ANSI mode, type coercion, date parsing) |
| 6. Test Validation | Compile, test, compare output to pre-upgrade baseline |

## Supported Upgrade Paths

- **Spark 2.x → 3.x** — Major API removals (SQLContext, HiveContext, Accumulator v1), Scala 2.12/2.13
- **Spark 3.x → 4.x** — ANSI mode default, Java 17+ requirement, Scala 2.13 only, legacy flag removal

## Languages & Build Systems

- **Languages**: Scala, Java, Python (PySpark)
- **Build systems**: Maven, SBT, Gradle, pip/uv

## Reference Material

- [Apache Spark Migration Guide](https://spark.apache.org/docs/latest/migration-guide.html) — The official, up-to-date guide covering API removals, configuration changes, SQL behavior, PySpark, Structured Streaming, and MLlib for every Spark release

## Example Usage

Ask the agent:

> "Upgrade this project from Spark 2.4 to Spark 3.5"

> "Migrate our PySpark codebase to Spark 4.0"

> "Fix all Spark deprecation warnings in this repo"

The agent will follow the six-phase workflow, producing a `spark_upgrade_impact.md` document and systematically updating build files, code, configuration, and SQL queries.
