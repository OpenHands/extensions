# bump-java-version

Migrate a Maven project one Java LTS step (8->11, 11->17, 17->21, 21->25) so it compiles under the new JDK and every previously-passing test still passes — standard tools only (JDKs, Maven, OpenRewrite from Maven Central), no scripts. PASS = `mvn compile` under the target JDK AND no previously-passing test lost.

Standalone repo & cross-agent packaging: https://github.com/vasiliy-mikhailov/bump-java-version-skill
