---
name: spark-version-upgrade
description: Upgrade Apache Spark applications between major versions (2.x→3.x, 3.x→4.x). Covers build files, deprecated APIs, configuration changes, SQL/DataFrame updates, and test validation.
license: MIT
compatibility: Requires Java 8+/11+/17+, Scala 2.12/2.13, Maven/Gradle/SBT, Apache Spark
triggers:
  - spark upgrade
  - spark migration
  - spark version
  - upgrade spark
  - spark 3
  - spark 4
  - pyspark upgrade
---

Upgrade Apache Spark applications between major versions with a structured, phase-by-phase workflow.

## When to Use

- Migrating from Spark 2.x → 3.x or Spark 3.x → 4.x
- Updating PySpark, Spark SQL, or Structured Streaming applications
- Resolving deprecation warnings before a Spark version bump

## Workflow Overview

1. **Inventory & Impact Analysis** — Scan the codebase and assess scope
2. **Build File Updates** — Bump Spark/Scala/Java dependencies
3. **API Migration** — Replace deprecated and removed APIs
4. **Configuration Migration** — Update Spark config properties
5. **SQL & DataFrame Migration** — Fix query-level breaking changes
6. **Test Validation** — Compile, run tests, verify results

---

## Phase 1: Inventory & Impact Analysis

Before changing any code, assess what needs to change. Read the official Apache Spark migration guide for the target version — it documents every API removal, config rename, and behavioral change per release:
https://spark.apache.org/docs/latest/migration-guide.html

### Checklist

- [ ] Read the migration guide section for the target Spark version
- [ ] Identify current Spark version (check `pom.xml`, `build.sbt`, `build.gradle`, or `requirements.txt`)
- [ ] Identify target Spark version
- [ ] Search for deprecated APIs: `grep -rn 'import org.apache.spark' --include='*.scala' --include='*.java' --include='*.py'`
- [ ] List all Spark config properties: `grep -rn 'spark\.' --include='*.conf' --include='*.properties' --include='*.scala' --include='*.java' --include='*.py' | grep -v 'test'`
- [ ] Check for custom `SparkSession` or `SparkContext` extensions
- [ ] Identify connector dependencies (Hive, Kafka, Cassandra, Delta, Iceberg)
- [ ] Document findings in `spark_upgrade_impact.md`

### Output

```
spark_upgrade_impact.md   # Summary of affected files, APIs, and configs
```

---

## Phase 2: Build File Updates

Update dependency versions and resolve compilation.

### Maven (`pom.xml`)

```xml
<!-- Update Spark version property -->
<spark.version>3.5.1</spark.version>    <!-- or 4.0.0 -->
<scala.version>2.13.12</scala.version>  <!-- Spark 3.x: 2.12/2.13; Spark 4.x: 2.13 -->

<!-- Update artifact IDs if Scala cross-version changed -->
<artifactId>spark-core_2.13</artifactId>
<artifactId>spark-sql_2.13</artifactId>
```

### SBT (`build.sbt`)

```scala
val sparkVersion = "3.5.1" // or "4.0.0"
scalaVersion := "2.13.12"

libraryDependencies += "org.apache.spark" %% "spark-core" % sparkVersion
libraryDependencies += "org.apache.spark" %% "spark-sql" % sparkVersion
```

### Gradle (`build.gradle`)

```groovy
ext {
    sparkVersion = '3.5.1' // or '4.0.0'
}
dependencies {
    implementation "org.apache.spark:spark-core_2.13:${sparkVersion}"
    implementation "org.apache.spark:spark-sql_2.13:${sparkVersion}"
}
```

### PySpark (`requirements.txt` / `pyproject.toml`)

```
pyspark==3.5.1   # or 4.0.0
```

### Checklist

- [ ] Update Spark version in build file
- [ ] Update Scala version if crossing 2.12→2.13 boundary
- [ ] Update Java source/target level if required (Spark 4.x requires Java 17+)
- [ ] Update connector library versions to match new Spark version
- [ ] Resolve dependency conflicts (`mvn dependency:tree` / `sbt dependencyTree`)
- [ ] Confirm project compiles (errors at this stage are expected — they guide Phase 3)

---

## Phase 3: API Migration

Replace removed and deprecated APIs. Work through compiler errors systematically.

### Common Patterns

Consult the official Apache Spark migration guide for the complete list of changes for each version:
https://spark.apache.org/docs/latest/migration-guide.html

#### SparkSession Creation (2.x → 3.x)

```scala
// BEFORE (Spark 1.x/2.x)
val sc = new SparkContext(conf)
val sqlContext = new SQLContext(sc)

// AFTER (Spark 2.x+/3.x)
val spark = SparkSession.builder()
  .config(conf)
  .enableHiveSupport() // if needed
  .getOrCreate()
val sc = spark.sparkContext
```

#### RDD to DataFrame (2.x → 3.x)

```scala
// BEFORE
rdd.toDF()  // implicit from SQLContext

// AFTER
import spark.implicits._
rdd.toDF()  // implicit from SparkSession
```

#### Accumulator API (2.x → 3.x)

```scala
// BEFORE
val acc = sc.accumulator(0)

// AFTER
val acc = sc.longAccumulator("name")
```

### Checklist

- [ ] Replace `SQLContext` / `HiveContext` with `SparkSession`
- [ ] Replace deprecated `Accumulator` with `AccumulatorV2`
- [ ] Update `DataFrame` → `Dataset[Row]` where needed
- [ ] Replace removed `RDD.mapPartitionsWithContext` with `mapPartitions`
- [ ] Fix `SparkConf` deprecated setters
- [ ] Update custom `UserDefinedFunction` registration
- [ ] Migrate `Experimental` / `DeveloperApi` usages that were removed
- [ ] Verify all compilation errors from Phase 2 are resolved

---

## Phase 4: Configuration Migration

Spark renames and removes configuration properties between versions. The official migration guide documents every renamed and removed property per release:
https://spark.apache.org/docs/latest/migration-guide.html

### Checklist

- [ ] Rename deprecated config keys (e.g., `spark.shuffle.file.buffer.kb` → `spark.shuffle.file.buffer`)
- [ ] Update removed configs to their replacements
- [ ] Review `spark-defaults.conf`, application code, and submit scripts
- [ ] Check for hardcoded config values in test fixtures
- [ ] Verify `SparkSession.builder().config(...)` calls use current property names

---

## Phase 5: SQL & DataFrame Migration

Spark SQL behavior changes between versions can silently alter query results.

### Key Breaking Changes (2.x → 3.x)

- `CAST` to integer no longer truncates silently — set `spark.sql.ansi.enabled` if needed
- `FROM` clause is required in `SELECT` (no more `SELECT 1`)
- Column resolution order changed in subqueries
- `spark.sql.legacy.timeParserPolicy` controls date/time parsing behavior

### Key Breaking Changes (3.x → 4.x)

- ANSI mode is default (`spark.sql.ansi.enabled=true`)
- Stricter type coercion in comparisons
- `spark.sql.legacy.*` flags removed

### Checklist

- [ ] Audit SQL strings and DataFrame expressions for changed behavior
- [ ] Add explicit `CAST` where implicit coercion relied on legacy behavior
- [ ] Update date/time format patterns to match new parser
- [ ] Test SQL queries with representative data and compare output to pre-upgrade baseline
- [ ] Set `spark.sql.legacy.*` flags temporarily if needed for phased migration

---

## Phase 6: Test Validation

### Checklist

- [ ] All code compiles without errors
- [ ] All existing unit tests pass
- [ ] All existing integration tests pass
- [ ] Run Spark jobs locally with sample data and compare output to pre-upgrade baseline
- [ ] No deprecation warnings remain (or are documented with a migration timeline)
- [ ] Update CI/CD pipeline to use new Spark version
- [ ] Document any `spark.sql.legacy.*` flags that are set temporarily

## Done When

✓ Project compiles against target Spark version
✓ All tests pass
✓ No removed APIs remain in code
✓ Configuration properties are current
✓ SQL queries produce correct results
✓ Upgrade impact documented in `spark_upgrade_impact.md`