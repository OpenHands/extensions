# Efficiency Review

A detailed reference for evaluating performance, resource usage, and algorithmic efficiency in recently modified code. Focus on real, measurable inefficiencies - not premature optimization or micro-benchmarks that do not matter at the project's scale.

## Core Principles

1. **Pragmatic Optimization**: Fix inefficiencies that affect real users or real workloads. Do not optimize code paths that execute once at startup or handle trivial data volumes.
2. **Algorithmic Awareness**: Prefer better algorithms and data structures over micro-optimizations. An O(n²) loop over a growing dataset is a real problem; shaving nanoseconds off an O(n) loop is not.
3. **Measure Before Prescribing**: When recommending a change, explain *why* it matters at the expected scale. Cite the data size, call frequency, or latency target that makes the optimization worthwhile.
4. **Preserve Functionality**: Efficiency improvements must not change behavior. All outputs and side effects remain identical.

## What to Look For

### Algorithmic Complexity

- Nested loops over collections that grow with input size (O(n²) or worse)
- Linear search where a hash/set lookup would suffice
- Repeated sorting or filtering of the same data
- Recursive algorithms without memoization on overlapping subproblems
- Using arrays for membership checks instead of sets or maps

### Unnecessary Work

- Recomputing values inside loops that could be computed once outside
- Performing I/O (file reads, network calls, DB queries) inside tight loops
- Loading entire datasets into memory when streaming or pagination is available
- Eagerly computing expensive results that may never be used (missing lazy evaluation)
- Serializing/deserializing data multiple times in the same pipeline

### Resource Usage

- Unbounded memory growth (appending to lists without limits, caching without eviction)
- File handles, connections, or streams opened but not closed (missing `finally`/`with`/`using`/`defer`)
- Large object allocations in hot paths that could reuse buffers
- Spawning threads or processes without pooling or concurrency limits

### Data Structure Choices

- Using a list where a set or map provides O(1) lookups
- Storing data in formats that require repeated parsing (e.g., stringified JSON accessed multiple times)
- Using mutable shared state where an immutable snapshot or copy-on-write pattern is safer and no slower
- Choosing a general-purpose collection when a specialized one (deque, priority queue, sorted set) better fits the access pattern

### Database and I/O Patterns

- N+1 query patterns (fetching related records one-by-one inside a loop)
- Missing indices on frequently queried columns (when schema is visible)
- Fetching columns or rows not needed by the caller
- Synchronous blocking calls in async contexts

## Review Checklist

- [ ] Identify any loops with O(n²) or worse complexity on non-trivial input sizes
- [ ] Check for repeated computation that could be hoisted or cached
- [ ] Verify I/O operations are batched and not performed in tight loops
- [ ] Confirm resources (connections, handles, streams) are properly closed
- [ ] Review data structure choices for appropriate access-pattern fit
- [ ] Look for N+1 query patterns or unnecessary full-table scans
- [ ] Validate that any suggested optimization is justified by expected scale

## Output Format

For each efficiency finding, provide:

```
**[EFFICIENCY]** [file:line] - Brief description
  Issue: [What is inefficient and at what scale it matters]
  Suggestion: [Concrete fix with expected complexity improvement]
  Impact: HIGH (user-facing latency/cost) | MEDIUM (noticeable at scale) | LOW (minor, worth noting)
```

Impact guide:
- **HIGH**: Causes user-visible latency, excessive memory usage, or cost at current or near-term scale.
- **MEDIUM**: Becomes a problem as data or traffic grows; worth fixing proactively.
- **LOW**: Minor inefficiency; mention if the fix is trivial, otherwise skip.

When no efficiency concerns exist, state explicitly:

```
**[EFFICIENCY]** No significant performance or resource issues detected in the changed code.
```
