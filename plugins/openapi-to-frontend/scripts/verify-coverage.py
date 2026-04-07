#!/usr/bin/env python3
"""
Verify that generated TypeScript code covers all schemas and endpoints in the OpenAPI spec.

This script cross-references the OpenAPI spec against the generated TypeScript client
to ensure completeness.

Usage:
    python verify-coverage.py <spec-file> <client-dir>

Example:
    python verify-coverage.py openapi.yaml client/

Exit codes:
    0 - All items covered
    1 - Missing coverage detected
"""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:
    yaml = None


def load_spec(path: Path) -> dict[str, Any]:
    """Load an OpenAPI spec from a JSON or YAML file."""
    content = path.read_text()
    
    if path.suffix in ('.yaml', '.yml'):
        if yaml is None:
            print("Error: PyYAML is required for YAML files. Install with: pip install pyyaml", file=sys.stderr)
            sys.exit(1)
        return yaml.safe_load(content)
    else:
        return json.loads(content)


def extract_schema_names(spec: dict[str, Any]) -> set[str]:
    """Extract all schema names from the spec."""
    components = spec.get('components', {})
    return set(components.get('schemas', {}).keys())


def extract_endpoint_keys(spec: dict[str, Any]) -> set[str]:
    """Extract all endpoint keys (METHOD /path) from the spec."""
    endpoints = set()
    
    for path, path_item in spec.get('paths', {}).items():
        for method in ['get', 'post', 'put', 'patch', 'delete', 'options', 'head']:
            if method in path_item:
                endpoints.add(f"{method.upper()} {path}")
    
    return endpoints


def extract_enum_names(spec: dict[str, Any]) -> set[str]:
    """Extract all enum schema names from the spec."""
    enums = set()
    components = spec.get('components', {})
    
    for name, schema in components.get('schemas', {}).items():
        if 'enum' in schema:
            enums.add(name)
    
    return enums


def parse_types_file(path: Path) -> set[str]:
    """Extract interface/type names from types.ts."""
    if not path.exists():
        return set()
    
    content = path.read_text()
    
    # Match: export interface Name, export type Name
    pattern = r'export\s+(?:interface|type)\s+(\w+)'
    return set(re.findall(pattern, content))


def parse_api_file(path: Path) -> set[tuple[str, str]]:
    """Extract method signatures from api.ts to infer covered endpoints."""
    if not path.exists():
        return set()
    
    content = path.read_text()
    methods = set()
    
    # Match async method definitions
    # async methodName(...): Promise<...>
    pattern = r'async\s+(\w+)\s*\([^)]*\)\s*:\s*Promise'
    method_names = re.findall(pattern, content)
    
    # Also look for request calls to infer endpoints
    # this.request('GET', '/users', ...)
    request_pattern = r"this\.request\s*\(\s*['\"](\w+)['\"]\s*,\s*['\"`]([^'\"`]+)['\"`]"
    for match in re.finditer(request_pattern, content):
        http_method = match.group(1)
        path = match.group(2)
        # Normalize path parameters
        normalized_path = re.sub(r'\$\{[^}]+\}', '{param}', path)
        methods.add((http_method, normalized_path))
    
    return methods


def normalize_path(path: str) -> str:
    """Normalize a path for comparison."""
    # Replace {param} variations with a standard format
    return re.sub(r'\{[^}]+\}', '{id}', path)


def verify_coverage(spec_path: Path, client_dir: Path) -> tuple[list[str], list[str], list[str]]:
    """
    Verify coverage and return (missing, covered, extraneous) items.
    """
    spec = load_spec(spec_path)
    
    # Expected from spec
    expected_schemas = extract_schema_names(spec)
    expected_endpoints = extract_endpoint_keys(spec)
    expected_enums = extract_enum_names(spec)
    
    # Found in generated code
    types_file = client_dir / 'types.ts'
    api_file = client_dir / 'api.ts'
    
    found_types = parse_types_file(types_file)
    found_methods = parse_api_file(api_file)
    
    # Check schema coverage
    missing = []
    covered = []
    extraneous = []
    
    # Check interfaces
    for schema in expected_schemas:
        if schema in found_types:
            covered.append(f"Schema: {schema}")
        else:
            missing.append(f"Schema: {schema}")
    
    # Check for extra types (not necessarily bad, could be helper types)
    spec_schema_names = expected_schemas | expected_enums
    extra_types = found_types - spec_schema_names
    # Filter out common helper types
    helper_patterns = ['Request', 'Response', 'Params', 'Config', 'Error', 'Options']
    for t in extra_types:
        is_helper = any(p in t for p in helper_patterns)
        if not is_helper:
            extraneous.append(f"Extra type: {t}")
    
    # Check endpoint coverage
    found_paths = {normalize_path(p) for _, p in found_methods}
    for endpoint in expected_endpoints:
        method, path = endpoint.split(' ', 1)
        normalized = normalize_path(path)
        
        # Check if any found method matches
        matched = False
        for found_method, found_path in found_methods:
            if found_method == method and normalize_path(found_path) == normalized:
                matched = True
                break
        
        if matched:
            covered.append(f"Endpoint: {endpoint}")
        else:
            missing.append(f"Endpoint: {endpoint}")
    
    return missing, covered, extraneous


def main():
    parser = argparse.ArgumentParser(
        description='Verify TypeScript client coverage against OpenAPI spec.'
    )
    parser.add_argument('spec_file', type=Path, help='Path to the OpenAPI spec file')
    parser.add_argument('client_dir', type=Path, help='Path to the client directory')
    parser.add_argument('--json', action='store_true', help='Output as JSON')
    
    args = parser.parse_args()
    
    if not args.spec_file.exists():
        print(f"Error: Spec file not found: {args.spec_file}", file=sys.stderr)
        sys.exit(1)
    
    if not args.client_dir.exists():
        print(f"Error: Client directory not found: {args.client_dir}", file=sys.stderr)
        sys.exit(1)
    
    try:
        missing, covered, extraneous = verify_coverage(args.spec_file, args.client_dir)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    
    if args.json:
        result = {
            'missing': missing,
            'covered': covered,
            'extraneous': extraneous,
            'coverage': {
                'total': len(missing) + len(covered),
                'covered': len(covered),
                'missing': len(missing),
                'percentage': round(len(covered) / (len(missing) + len(covered)) * 100, 1) if missing or covered else 100
            }
        }
        print(json.dumps(result, indent=2))
    else:
        print("=" * 60)
        print("OpenAPI to TypeScript Coverage Report")
        print("=" * 60)
        print()
        
        if covered:
            print(f"✓ Covered ({len(covered)}):")
            for item in sorted(covered):
                print(f"  • {item}")
            print()
        
        if missing:
            print(f"✗ Missing ({len(missing)}):")
            for item in sorted(missing):
                print(f"  • {item}")
            print()
        
        if extraneous:
            print(f"? Extraneous ({len(extraneous)}):")
            for item in sorted(extraneous):
                print(f"  • {item}")
            print()
        
        total = len(missing) + len(covered)
        if total > 0:
            percentage = len(covered) / total * 100
            print("=" * 60)
            print(f"Coverage: {len(covered)}/{total} ({percentage:.1f}%)")
            print("=" * 60)
    
    if missing:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == '__main__':
    main()
