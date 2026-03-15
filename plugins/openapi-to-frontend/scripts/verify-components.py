#!/usr/bin/env python3
"""
Verify that React components exist for all TypeScript client types.

This script cross-references the TypeScript client against the generated React
components to ensure each schema has appropriate Form, Detail, and List components.

Usage:
    python verify-components.py <client-dir> <components-dir>

Example:
    python verify-components.py client/ components/

Exit codes:
    0 - All expected components exist
    1 - Missing components detected
"""

import argparse
import json
import re
import sys
from pathlib import Path


def extract_schema_types(types_file: Path) -> dict[str, dict]:
    """
    Extract interface definitions from types.ts and categorize them.
    
    Returns a dict mapping schema names to their info:
    {
        'User': {
            'fields': ['id', 'email', ...],
            'is_request': False,
            'is_response': False,
        }
    }
    """
    if not types_file.exists():
        return {}
    
    content = types_file.read_text()
    schemas = {}
    
    # Find all interfaces
    interface_pattern = r'export\s+interface\s+(\w+)\s*\{([^}]+)\}'
    
    for match in re.finditer(interface_pattern, content, re.DOTALL):
        name = match.group(1)
        body = match.group(2)
        
        # Extract field names
        field_pattern = r'(\w+)\s*[?]?\s*:'
        fields = re.findall(field_pattern, body)
        
        # Categorize
        is_request = name.endswith('Request') or 'Create' in name or 'Update' in name
        is_response = name.endswith('Response') or name.endswith('ListResponse')
        is_params = name.endswith('Params')
        
        # Skip helper types
        if is_params:
            continue
        
        schemas[name] = {
            'fields': fields,
            'is_request': is_request,
            'is_response': is_response,
            'is_helper': is_request or is_response,
        }
    
    # Also find type aliases (enums/unions)
    type_pattern = r'export\s+type\s+(\w+)\s*='
    for match in re.finditer(type_pattern, content):
        name = match.group(1)
        if name not in schemas:
            schemas[name] = {
                'fields': [],
                'is_request': False,
                'is_response': False,
                'is_helper': True,  # Type aliases are usually helper types
            }
    
    return schemas


def extract_api_endpoints(api_file: Path) -> dict[str, set[str]]:
    """
    Extract what operations exist for each schema type.
    
    Returns a dict mapping schema names to available operations:
    {
        'User': {'list', 'get', 'create', 'update', 'delete'}
    }
    """
    if not api_file.exists():
        return {}
    
    content = api_file.read_text()
    operations = {}
    
    # Match method definitions with their return types
    # async listUsers(...): Promise<UserListResponse>
    method_pattern = r'async\s+(list|get|create|update|delete|patch)(\w+)\s*\([^)]*\)\s*:\s*Promise<([^>]+)>'
    
    for match in re.finditer(method_pattern, content):
        operation = match.group(1).lower()
        resource_part = match.group(2)
        return_type = match.group(3)
        
        # Derive schema name from method name
        # listUsers -> User, getUser -> User
        schema_name = resource_part.rstrip('s')  # Remove trailing 's' for list
        
        if schema_name not in operations:
            operations[schema_name] = set()
        operations[schema_name].add(operation)
    
    return operations


def check_components(
    schemas: dict[str, dict],
    operations: dict[str, set[str]],
    components_dir: Path
) -> tuple[list[str], list[str], list[str]]:
    """
    Check which components exist and which are missing.
    
    Returns (missing, present, optional) component lists.
    """
    missing = []
    present = []
    optional = []
    
    # Determine which schemas need components
    primary_schemas = {
        name: info
        for name, info in schemas.items()
        if not info['is_helper']
    }
    
    for schema_name, info in primary_schemas.items():
        schema_dir = components_dir / schema_name
        ops = operations.get(schema_name, set())
        
        # Check Form component (needed if create or update exists)
        form_file = schema_dir / f'{schema_name}Form.tsx'
        if 'create' in ops or 'update' in ops:
            if form_file.exists():
                present.append(f"{schema_name}/Form")
            else:
                missing.append(f"{schema_name}/Form (has create/update endpoint)")
        else:
            if form_file.exists():
                optional.append(f"{schema_name}/Form (no create/update endpoint)")
        
        # Check Detail component (needed if get exists)
        detail_file = schema_dir / f'{schema_name}Detail.tsx'
        if 'get' in ops:
            if detail_file.exists():
                present.append(f"{schema_name}/Detail")
            else:
                missing.append(f"{schema_name}/Detail (has get endpoint)")
        else:
            if detail_file.exists():
                optional.append(f"{schema_name}/Detail (no get endpoint)")
        
        # Check List component (needed if list exists)
        list_file = schema_dir / f'{schema_name}List.tsx'
        if 'list' in ops:
            if list_file.exists():
                present.append(f"{schema_name}/List")
            else:
                missing.append(f"{schema_name}/List (has list endpoint)")
        else:
            if list_file.exists():
                optional.append(f"{schema_name}/List (no list endpoint)")
        
        # Check index.ts barrel export
        index_file = schema_dir / 'index.ts'
        if schema_dir.exists() and not index_file.exists():
            missing.append(f"{schema_name}/index.ts (barrel export)")
    
    # Check shared components
    shared_dir = components_dir / 'shared'
    shared_components = ['LoadingSpinner', 'ErrorDisplay', 'Pagination']
    
    for comp in shared_components:
        comp_file = shared_dir / f'{comp}.tsx'
        if comp_file.exists():
            present.append(f"shared/{comp}")
        else:
            missing.append(f"shared/{comp}")
    
    # Check top-level barrel export
    root_index = components_dir / 'index.ts'
    if root_index.exists():
        present.append("index.ts (root barrel)")
    else:
        missing.append("index.ts (root barrel)")
    
    return missing, present, optional


def main():
    parser = argparse.ArgumentParser(
        description='Verify React components exist for TypeScript client types.'
    )
    parser.add_argument('client_dir', type=Path, help='Path to the client directory')
    parser.add_argument('components_dir', type=Path, help='Path to the components directory')
    parser.add_argument('--json', action='store_true', help='Output as JSON')
    
    args = parser.parse_args()
    
    types_file = args.client_dir / 'types.ts'
    api_file = args.client_dir / 'api.ts'
    
    if not types_file.exists():
        print(f"Error: types.ts not found in {args.client_dir}", file=sys.stderr)
        sys.exit(1)
    
    # Extract information
    schemas = extract_schema_types(types_file)
    operations = extract_api_endpoints(api_file)
    
    # Check components
    missing, present, optional = check_components(
        schemas, operations, args.components_dir
    )
    
    if args.json:
        result = {
            'missing': missing,
            'present': present,
            'optional': optional,
            'schemas': list(schemas.keys()),
            'operations': {k: list(v) for k, v in operations.items()},
            'coverage': {
                'required': len(missing) + len(present),
                'present': len(present),
                'missing': len(missing),
                'percentage': round(
                    len(present) / (len(missing) + len(present)) * 100, 1
                ) if missing or present else 100
            }
        }
        print(json.dumps(result, indent=2))
    else:
        print("=" * 60)
        print("TypeScript Client to React Components Coverage Report")
        print("=" * 60)
        print()
        
        print(f"Schemas found: {len(schemas)}")
        print(f"Primary schemas (need components): {len([s for s in schemas.values() if not s['is_helper']])}")
        print()
        
        if present:
            print(f"✓ Present ({len(present)}):")
            for item in sorted(present):
                print(f"  • {item}")
            print()
        
        if missing:
            print(f"✗ Missing ({len(missing)}):")
            for item in sorted(missing):
                print(f"  • {item}")
            print()
        
        if optional:
            print(f"? Optional ({len(optional)}):")
            for item in sorted(optional):
                print(f"  • {item}")
            print()
        
        required = len(missing) + len(present)
        if required > 0:
            percentage = len(present) / required * 100
            print("=" * 60)
            print(f"Coverage: {len(present)}/{required} ({percentage:.1f}%)")
            print("=" * 60)
    
    if missing:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == '__main__':
    main()
