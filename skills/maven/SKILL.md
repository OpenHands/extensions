---
name: maven
description: Build and test Java projects that use Apache Maven (pom.xml, mvnw). Use when a repository has a pom.xml or mvnw, or when a Maven build fails in the sandbox. Covers getting a working Maven, multi-module builds, running a single test, and common sandbox failures.
triggers:
- maven
- mvn
- mvnw
- pom.xml
---

# Maven

## 1. Get a working Maven

1. If the repository has `./mvnw`, use it instead of `mvn`. It downloads the Maven version the project expects.
2. Otherwise, if `mvn` is already on the PATH, check whether it came from the Debian package:

   ```bash
   dpkg -S "$(readlink -f "$(command -v mvn)")" 2>/dev/null
   ```

   Output starting with `maven:` means the Debian package. Replace it with upstream Maven (step 3).
3. Otherwise install upstream Apache Maven. Do not run `apt-get install maven`.

   ```bash
   MAVEN_VERSION=3.9.9
   URL="https://archive.apache.org/dist/maven/maven-3/${MAVEN_VERSION}/binaries/apache-maven-${MAVEN_VERSION}-bin.tar.gz"
   curl -fsSL -o /tmp/maven.tar.gz "$URL"
   echo "$(curl -fsSL "$URL.sha512" | cut -d' ' -f1)  /tmp/maven.tar.gz" | sha512sum -c -
   mkdir -p "$HOME/.local/opt" && tar xzf /tmp/maven.tar.gz -C "$HOME/.local/opt"
   export PATH="$HOME/.local/opt/apache-maven-${MAVEN_VERSION}/bin:$PATH"
   mvn -v
   ```

**Why not the Debian package:** Debian 13 (trixie), which the OpenHands agent image uses, packages Maven 3.9.9 with the system Eclipse Sisu 0.3.5 instead of the bundled 0.9.0.M3. Sisu 0.3.5 cannot load plugins compiled for Java 17 or newer, for example `io.github.ascopes:protobuf-maven-plugin` 5.x. The build fails with `Unable to load the mojo` and `Guice/NullInjectedIntoNonNullable`. The version number is the same, so `mvn -v` does not reveal the problem.

**JDK:** the Maven tarball does not include a JDK. If `java -version` fails, install one with the package manager, for example `sudo apt-get install -y --no-install-recommends openjdk-21-jdk-headless`. The JDK must be at least the release the project targets (`maven.compiler.release`, `<release>`, or `java.version` in `pom.xml`); a newer JDK builds an older target. Debian 13 packages only `openjdk-21` and `openjdk-25`, so use 21 for a project that targets 17.

## 2. Build and test

Always pass `-B` (batch mode) so the output has no progress bars or colour codes.

| Goal | Command |
|---|---|
| Build everything, skip tests | `mvn -B -DskipTests install` |
| Build one module and the modules it needs | `mvn -B -pl <module-path> -am -DskipTests install` |
| Run one test class or method | `mvn -B -pl <module-path> -am test -Dtest='ClassName#method' -Dsurefire.failIfNoSpecifiedTests=false` |
| Re-run without network after the first build | add `-o` |

- `-am` builds the modules that `<module-path>` depends on. Without it, sibling `-SNAPSHOT` dependencies fail with `Could not find artifact`.
- With `-am` and `-Dtest`, the other modules have no matching test, so `-Dsurefire.failIfNoSpecifiedTests=false` is required.
- If `pom.xml` configures a formatter such as Spotless, run its apply goal (for example `mvn -B spotless:apply`) before committing.

## 3. Common failures

| Symptom | Cause | Fix |
|---|---|---|
| `Unable to load the mojo` with `Guice/NullInjectedIntoNonNullable` | Debian-packaged Maven (section 1) | Use `./mvnw` or upstream Maven |
| `Could not find artifact ...-SNAPSHOT` for a module of the same project | Sibling module not built | Add `-am`, or `install` that module first |
| `Permission denied` under `~/.m2` | `~/.m2` is a mounted volume owned by root | `sudo chown -R "$(id -u):$(id -g)" ~/.m2`, or pass `-Dmaven.repo.local=/tmp/m2` |
| `release version 21 not supported` | JDK older than the project's target | Install the JDK version the project targets |
