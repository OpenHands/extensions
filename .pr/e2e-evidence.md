# End-to-end evidence: `maven` skill in Agent Canvas

Environment: `ghcr.io/openhands/agent-canvas:latest` (OpenHands v1.62.0, Agent Canvas v1.41.0, bundled `@openhands/extensions` 0.43.0), Debian 13, arm64. No JDK or Maven installed. Agent: Claude Code over ACP.

Setup: copied `skills/maven/` into the bundled `@openhands/extensions` package and added its `skills/index.js` and marketplace entries, the same files this PR changes. Test project: `.pr/maven-repro/` (protobuf-maven-plugin 5.1.11, compiled for Java 17). The project contained no skill files.

Prompt (no mention of the skill or Debian):

> In /projects/maven-skill-test, build the project with Maven (`package`) until it succeeds. Java and Maven are not installed yet, so set up whatever you need. Run commands in the foreground and wait for each to finish. At the end, list the exact commands you ran and the final result.

Result:
- `maven` was in the conversation's skill set (75 skills, `agent_context.skills`).
- The agent checked for `mvnw` and the target release, installed `openjdk-21-jdk-headless` via apt, then installed upstream Apache Maven 3.9.9 from archive.apache.org. The SHA-512 checksum was verified. It did not install the Debian `maven` package. In its words: "installed upstream Apache Maven 3.9.9 rather than the Debian package, as the maven skill advises".
- `mvn -B package`: BUILD SUCCESS on the first attempt (28 s), `target/maven-repro-1.0.jar`.
- The agent first tried `openjdk-17-jdk-headless`, which Debian 13 does not package. The skill now says so (21 and 25 only).

Control (`.pr/maven-repro/run.sh`, same base image):
- Debian `maven` 3.9.9 (system Sisu 0.3.5): `Guice/NullInjectedIntoNonNullable`, the build fails.
- Upstream Maven 3.9.9 (bundled Sisu 0.9.0.M3): BUILD OK.
