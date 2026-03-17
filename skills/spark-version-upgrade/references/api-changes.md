# Spark API Changes Reference

## Spark 2.x → 3.x Removals

### Core API

| Removed | Replacement | Notes |
|---------|-------------|-------|
| `SparkContext.accumulator()` | `SparkContext.longAccumulator()` / `doubleAccumulator()` | Use `AccumulatorV2` for custom types |
| `SparkContext.tachyonStore` | Removed entirely | Tachyon/Alluxio off-heap store dropped |
| `RDD.mapPartitionsWithContext` | `RDD.mapPartitions` | Task context available via `TaskContext.get()` |
| `RDD.toJavaRDD()` (implicit) | Explicit `JavaRDD.fromRDD(rdd)` | Implicit conversions tightened |

### SQL API

| Removed | Replacement | Notes |
|---------|-------------|-------|
| `SQLContext` | `SparkSession` | Use `spark.sql(...)` instead of `sqlContext.sql(...)` |
| `HiveContext` | `SparkSession.builder().enableHiveSupport()` | |
| `DataFrame` (type alias) | `Dataset[Row]` | `DataFrame` still works as alias but prefer `Dataset[Row]` |
| `createExternalTable` | `createTable` | Method renamed |
| `registerTempTable` | `createOrReplaceTempView` | |
| `SQLContext.read` | `SparkSession.read` | |
| `SQLContext.createDataFrame` | `SparkSession.createDataFrame` | |

### Streaming

| Removed | Replacement | Notes |
|---------|-------------|-------|
| `DStream` API (spark-streaming) | Structured Streaming (`spark-sql`) | DStream still works but is maintenance-only |
| `StreamingContext.awaitTermination` | `SparkSession.streams.awaitAnyTermination` | For Structured Streaming |
| `StreamingContext.remember` | Watermark-based state management | |

### ML / MLlib

| Removed | Replacement | Notes |
|---------|-------------|-------|
| `org.apache.spark.mllib` (RDD-based) | `org.apache.spark.ml` (DataFrame-based) | RDD-based MLlib is deprecated |
| `LabeledPoint` from mllib | `ml.feature` transformers | Use DataFrame pipelines |
| `mllib.classification.SVMWithSGD` | `ml.classification.LinearSVC` | |
| `mllib.clustering.KMeans` | `ml.clustering.KMeans` | Same algorithm, DataFrame API |

---

## Spark 3.x → 4.x Removals

### Core API

| Removed | Replacement | Notes |
|---------|-------------|-------|
| `SparkContext.hadoopConfiguration` (mutable) | `SparkSession.sessionState.newHadoopConf()` | Per-session Hadoop config |
| `JavaSparkContext.sc()` | `JavaSparkContext.toSparkContext()` | Method renamed |
| Scala 2.12 support | Scala 2.13 only | All `_2.12` artifacts dropped |
| Java 8/11 support | Java 17+ required | |

### SQL API

| Removed | Replacement | Notes |
|---------|-------------|-------|
| `spark.sql.legacy.*` flags | No replacement — ANSI behavior is permanent | Audit all legacy flags |
| Non-ANSI `CAST` behavior | Explicit error handling or `TRY_CAST` | Overflows now throw errors |
| `spark.sql.legacy.timeParserPolicy` | New parser is default | Joda → java.time |
| Implicit type coercion in comparisons | Explicit `CAST` required | `string = int` no longer auto-casts |

### PySpark

| Removed | Replacement | Notes |
|---------|-------------|-------|
| `pyspark.sql.types.ArrayType.containsNull` default change | Explicitly set `containsNull=True` | Default changed |
| `DataFrame.toJSON()` returns `Dataset[String]` | `.collect()` to materialize | Behavior aligned with Scala |
| Python 3.8 support | Python 3.9+ required | |

---

## Common Migration Patterns

### Pattern: SQLContext → SparkSession

```scala
// BEFORE
val conf = new SparkConf().setAppName("MyApp")
val sc = new SparkContext(conf)
val sqlContext = new SQLContext(sc)
val df = sqlContext.read.json("data.json")

// AFTER
val spark = SparkSession.builder()
  .appName("MyApp")
  .getOrCreate()
val df = spark.read.json("data.json")
```

### Pattern: Accumulator v1 → v2

```scala
// BEFORE
val counter = sc.accumulator(0, "my-counter")
rdd.foreach(x => counter += 1)

// AFTER
val counter = sc.longAccumulator("my-counter")
rdd.foreach(x => counter.add(1))
```

### Pattern: registerTempTable → createOrReplaceTempView

```scala
// BEFORE
df.registerTempTable("my_table")

// AFTER
df.createOrReplaceTempView("my_table")
```

### Pattern: PySpark UDF Registration

```python
# BEFORE (Spark 2.x)
from pyspark.sql.functions import udf
from pyspark.sql.types import StringType
my_udf = udf(lambda x: x.upper(), StringType())

# AFTER (Spark 3.x+ preferred)
from pyspark.sql.functions import udf
from pyspark.sql.types import StringType

@udf(returnType=StringType())
def my_udf(x):
    return x.upper()
```

### Pattern: ANSI Mode Error Handling (3.x → 4.x)

```sql
-- BEFORE (non-ANSI, returns NULL on overflow)
SELECT CAST('999999999999' AS INT)

-- AFTER (ANSI mode, throws error — use TRY_CAST for NULL behavior)
SELECT TRY_CAST('999999999999' AS INT)
```

### Pattern: Date/Time Parsing (2.x → 3.x)

```scala
// BEFORE (lenient Joda-based parsing)
spark.sql("SELECT to_date('2023-1-5', 'yyyy-MM-dd')")

// AFTER (strict java.time parsing — single-digit month/day needs adjusted pattern)
spark.sql("SELECT to_date('2023-1-5', 'yyyy-M-d')")
// Or set legacy policy temporarily:
// spark.conf.set("spark.sql.legacy.timeParserPolicy", "LEGACY")
```
