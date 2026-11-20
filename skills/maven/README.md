# Maven

Build and test Java projects that use Apache Maven (pom.xml, mvnw). Use when a repository has a pom.xml or mvnw, or when a Maven build fails in the sandbox. Covers getting a working Maven, multi-module builds, running a single test, and common sandbox failures.

## Triggers

This skill is activated by the following keywords:

- `maven`
- `mvn`
- `mvnw`
- `pom.xml`

## Details

- Prefers the project's `./mvnw`, otherwise upstream Apache Maven with a checksum check.
- Explains why the Debian `maven` package is avoided: on Debian 13 it ships an older Eclipse Sisu that cannot load plugins compiled for Java 17 or newer.
- Lists the commands for multi-module builds (`-pl`, `-am`), a single test, and offline re-runs.
- Maps common sandbox failures to fixes.
