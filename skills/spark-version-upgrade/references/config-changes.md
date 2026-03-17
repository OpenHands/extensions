# Spark Configuration Changes Reference

## Spark 2.x → 3.x: Renamed Properties

| Old Property | New Property |
|-------------|-------------|
| `spark.shuffle.file.buffer.kb` | `spark.shuffle.file.buffer` |
| `spark.shuffle.consolidateFiles` | Removed (always consolidated) |
| `spark.reducer.maxMbInFlight` | `spark.reducer.maxSizeInFlight` |
| `spark.shuffle.memoryFraction` | Removed (unified memory management) |
| `spark.storage.memoryFraction` | Removed (unified memory management) |
| `spark.storage.unrollFraction` | Removed (unified memory management) |
| `spark.yarn.am.port` | `spark.driver.port` |
| `spark.tachyonStore.baseDir` | Removed |
| `spark.tachyonStore.url` | Removed |
| `spark.sql.tungsten.enabled` | Removed (always enabled) |
| `spark.sql.codegen.wholeStage` | `spark.sql.codegen.wholeStage` (default changed to `true`) |
| `spark.sql.parquet.int96AsTimestamp` | `spark.sql.parquet.int96AsTimestamp` (default changed to `true`) |
| `spark.sql.hive.convertMetastoreParquet` | Still valid but default behavior changed |
| `spark.akka.*` | Removed (Akka replaced with Netty RPC) |

## Spark 2.x → 3.x: New Important Defaults

| Property | Old Default | New Default | Impact |
|----------|------------|-------------|--------|
| `spark.sql.adaptive.enabled` | `false` | `true` (3.2+) | AQE auto-optimizes shuffles and joins |
| `spark.sql.ansi.enabled` | `false` | `false` (3.x) | Opt-in for strict SQL behavior |
| `spark.sql.sources.partitionOverwriteMode` | `static` | `static` | Consider `dynamic` for INSERT OVERWRITE |
| `spark.sql.legacy.timeParserPolicy` | N/A | `EXCEPTION` | Strict date/time parsing |
| `spark.sql.legacy.createHiveTableByDefault` | `true` | `false` | Tables default to data source format |

## Spark 3.x → 4.x: Removed Properties

| Removed Property | Migration Action |
|-----------------|-----------------|
| `spark.sql.legacy.timeParserPolicy` | Remove — new parser is permanent |
| `spark.sql.legacy.allowNegativeScaleOfDecimal` | Remove — negative scale not allowed |
| `spark.sql.legacy.createHiveTableByDefault` | Remove — data source tables default |
| `spark.sql.legacy.replaceDatabricksSparkAvro.enabled` | Remove — native Avro is standard |
| `spark.sql.legacy.setopsPrecedence.enabled` | Remove — SQL standard precedence permanent |
| `spark.sql.legacy.exponentLiteralAsDecimal.enabled` | Remove — standard behavior permanent |
| `spark.sql.legacy.allowHashOnMapType` | Remove |

## Spark 3.x → 4.x: Changed Defaults

| Property | Old Default (3.x) | New Default (4.x) | Impact |
|----------|-------------------|-------------------|--------|
| `spark.sql.ansi.enabled` | `false` | `true` | Overflow/cast errors throw instead of returning NULL |
| `spark.sql.storeAssignmentPolicy` | `ANSI` | `STRICT` | Stricter type checking on INSERT |
| `spark.sql.adaptive.coalescePartitions.enabled` | `true` | `true` | No change, but AQE behavior refined |
| `spark.sql.sources.default` | `parquet` | `parquet` | No change |

## How to Find Config Usage in Your Codebase

```bash
# Find all Spark config references
grep -rn 'spark\.' --include='*.scala' --include='*.java' --include='*.py' \
  --include='*.conf' --include='*.properties' --include='*.xml' --include='*.yaml'

# Find legacy flags specifically
grep -rn 'spark.sql.legacy' --include='*.scala' --include='*.java' --include='*.py' \
  --include='*.conf' --include='*.properties'

# Find spark-defaults.conf
find . -name 'spark-defaults.conf' -o -name 'spark-env.sh'

# Find spark-submit scripts with --conf flags
grep -rn '\-\-conf spark\.' --include='*.sh' --include='*.bash' --include='Makefile'
```

## Migration Strategy for Legacy Flags

When upgrading to Spark 4.x, `spark.sql.legacy.*` flags are removed. To migrate safely:

1. **Audit**: List all `spark.sql.legacy.*` flags in your codebase
2. **Test without them**: Remove each flag on Spark 3.x and run tests to surface failures
3. **Fix code**: Update SQL/DataFrame code to work under non-legacy behavior
4. **Then upgrade**: Bump to Spark 4.x after all legacy flags are eliminated
