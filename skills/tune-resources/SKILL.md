---
name: tune-resources
description: Optimize application memory and CPU usage by analyzing resource consumption patterns, identifying inefficiencies, and implementing performance improvements.
triggers:
- /tune-resources
- /optimize-memory
- /optimize-cpu
---

# Tune Memory and CPU

Optimize application resource usage for better performance and cost efficiency.

## Process

1. **Analyze usage patterns**: Review code for resource-intensive operations
2. **Identify inefficiencies**: Find memory leaks, excessive allocations, CPU hotspots
3. **Implement optimizations**: Apply targeted fixes
4. **Measure improvement**: Validate changes improve resource usage

## Memory Optimization

### Common Issues
- Memory leaks from unclosed resources
- Excessive object allocation
- Large data structures held in memory
- Cache without eviction policies
- Circular references preventing garbage collection

### Optimization Techniques
- Object pooling and reuse
- Lazy loading and pagination
- Stream processing instead of loading all data
- Proper resource cleanup (try-with-resources, context managers)
- Cache size limits and eviction

## CPU Optimization

### Common Issues
- Inefficient algorithms (O(n²) when O(n) is possible)
- Unnecessary recomputation
- Blocking operations on main thread
- Excessive string concatenation
- Unoptimized database queries

### Optimization Techniques
- Algorithm improvements
- Caching computed values
- Async/parallel processing
- Query optimization and indexing
- Batch processing

## Output Format

Provide:
1. **Current issues**: Identified resource inefficiencies
2. **Recommendations**: Prioritized list of optimizations
3. **Code changes**: Specific fixes with before/after
4. **Expected impact**: Estimated resource savings
