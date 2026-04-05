#!/usr/bin/env python3
"""
Parse an OpenAPI spec and output a structured JSON summary.

This script extracts all schemas, endpoints, and auth schemes from an OpenAPI
specification file (JSON or YAML) and outputs a normalized JSON structure
that can be consumed by the generation skills.

Usage:
    python parse-openapi.py <spec-file> [--output <output-file>]

Example:
    python parse-openapi.py openapi.yaml > spec-summary.json
    python parse-openapi.py openapi.json --output summary.json
"""

import argparse
import json
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


def resolve_ref(spec: dict[str, Any], ref: str) -> dict[str, Any]:
    """Resolve a $ref to its definition."""
    if not ref.startswith('#/'):
        return {'type': 'external', 'ref': ref}
    
    parts = ref[2:].split('/')
    current = spec
    for part in parts:
        current = current.get(part, {})
    return current


def parse_type(spec: dict[str, Any], schema: dict[str, Any]) -> dict[str, Any]:
    """Parse a schema type into a normalized format."""
    if '$ref' in schema:
        ref = schema['$ref']
        ref_name = ref.split('/')[-1]
        return {'type': 'ref', 'ref': ref_name}
    
    schema_type = schema.get('type', 'object')
    result: dict[str, Any] = {'type': schema_type}
    
    if 'format' in schema:
        result['format'] = schema['format']
    
    if 'enum' in schema:
        result['enum'] = schema['enum']
    
    if 'nullable' in schema or schema.get('x-nullable'):
        result['nullable'] = True
    
    if schema_type == 'array':
        items = schema.get('items', {})
        result['items'] = parse_type(spec, items)
    
    if schema_type == 'object':
        if 'properties' in schema:
            result['properties'] = {}
            for name, prop in schema.get('properties', {}).items():
                result['properties'][name] = parse_type(spec, prop)
        if 'additionalProperties' in schema:
            result['additionalProperties'] = parse_type(spec, schema['additionalProperties'])
    
    if 'oneOf' in schema:
        result['oneOf'] = [parse_type(spec, s) for s in schema['oneOf']]
    
    if 'anyOf' in schema:
        result['anyOf'] = [parse_type(spec, s) for s in schema['anyOf']]
    
    if 'allOf' in schema:
        result['allOf'] = [parse_type(spec, s) for s in schema['allOf']]
    
    return result


def parse_schemas(spec: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract all schemas from the spec."""
    schemas = []
    components = spec.get('components', {})
    
    for name, schema in components.get('schemas', {}).items():
        parsed = {
            'name': name,
            'description': schema.get('description', ''),
            'type': schema.get('type', 'object'),
            'required': schema.get('required', []),
            'fields': [],
        }
        
        for field_name, field_schema in schema.get('properties', {}).items():
            field = {
                'name': field_name,
                'required': field_name in parsed['required'],
                **parse_type(spec, field_schema),
            }
            if 'description' in field_schema:
                field['description'] = field_schema['description']
            parsed['fields'].append(field)
        
        if 'enum' in schema:
            parsed['enum'] = schema['enum']
        
        schemas.append(parsed)
    
    return schemas


def parse_parameter(spec: dict[str, Any], param: dict[str, Any]) -> dict[str, Any]:
    """Parse an endpoint parameter."""
    if '$ref' in param:
        param = resolve_ref(spec, param['$ref'])
    
    schema = param.get('schema', {})
    return {
        'name': param.get('name', ''),
        'in': param.get('in', 'query'),
        'required': param.get('required', False),
        'description': param.get('description', ''),
        **parse_type(spec, schema),
    }


def parse_request_body(spec: dict[str, Any], body: dict[str, Any]) -> dict[str, Any] | None:
    """Parse a request body."""
    if not body:
        return None
    
    if '$ref' in body:
        body = resolve_ref(spec, body['$ref'])
    
    content = body.get('content', {})
    json_content = content.get('application/json', {})
    schema = json_content.get('schema', {})
    
    if not schema:
        return None
    
    return {
        'required': body.get('required', False),
        **parse_type(spec, schema),
    }


def parse_response(spec: dict[str, Any], code: str, response: dict[str, Any]) -> dict[str, Any]:
    """Parse a response definition."""
    if '$ref' in response:
        response = resolve_ref(spec, response['$ref'])
    
    result = {
        'code': code,
        'description': response.get('description', ''),
    }
    
    content = response.get('content', {})
    json_content = content.get('application/json', {})
    schema = json_content.get('schema', {})
    
    if schema:
        result['schema'] = parse_type(spec, schema)
    
    return result


def parse_endpoints(spec: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract all endpoints from the spec."""
    endpoints = []
    
    for path, path_item in spec.get('paths', {}).items():
        # Handle path-level parameters
        path_params = path_item.get('parameters', [])
        
        for method in ['get', 'post', 'put', 'patch', 'delete', 'options', 'head']:
            if method not in path_item:
                continue
            
            operation = path_item[method]
            
            # Merge path and operation parameters
            all_params = path_params + operation.get('parameters', [])
            
            endpoint = {
                'path': path,
                'method': method.upper(),
                'operationId': operation.get('operationId', ''),
                'summary': operation.get('summary', ''),
                'description': operation.get('description', ''),
                'tags': operation.get('tags', []),
                'parameters': [parse_parameter(spec, p) for p in all_params],
                'requestBody': parse_request_body(spec, operation.get('requestBody', {})),
                'responses': [],
                'security': operation.get('security', spec.get('security', [])),
            }
            
            for code, response in operation.get('responses', {}).items():
                endpoint['responses'].append(parse_response(spec, code, response))
            
            endpoints.append(endpoint)
    
    return endpoints


def parse_auth_schemes(spec: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract all security schemes from the spec."""
    schemes = []
    components = spec.get('components', {})
    
    for name, scheme in components.get('securitySchemes', {}).items():
        parsed = {
            'name': name,
            'type': scheme.get('type', ''),
            'description': scheme.get('description', ''),
        }
        
        if scheme['type'] == 'apiKey':
            parsed['in'] = scheme.get('in', 'header')
            parsed['paramName'] = scheme.get('name', '')
        
        elif scheme['type'] == 'http':
            parsed['scheme'] = scheme.get('scheme', '')
            if 'bearerFormat' in scheme:
                parsed['bearerFormat'] = scheme['bearerFormat']
        
        elif scheme['type'] == 'oauth2':
            parsed['flows'] = {}
            for flow_name, flow in scheme.get('flows', {}).items():
                flow_data = {'scopes': flow.get('scopes', {})}
                if 'authorizationUrl' in flow:
                    flow_data['authorizationUrl'] = flow['authorizationUrl']
                if 'tokenUrl' in flow:
                    flow_data['tokenUrl'] = flow['tokenUrl']
                if 'refreshUrl' in flow:
                    flow_data['refreshUrl'] = flow['refreshUrl']
                parsed['flows'][flow_name] = flow_data
        
        elif scheme['type'] == 'openIdConnect':
            parsed['openIdConnectUrl'] = scheme.get('openIdConnectUrl', '')
        
        schemes.append(parsed)
    
    return schemes


def parse_spec(spec: dict[str, Any]) -> dict[str, Any]:
    """Parse an entire OpenAPI spec into a normalized structure."""
    info = spec.get('info', {})
    
    return {
        'openapi': spec.get('openapi', spec.get('swagger', '')),
        'info': {
            'title': info.get('title', ''),
            'version': info.get('version', ''),
            'description': info.get('description', ''),
        },
        'servers': spec.get('servers', []),
        'tags': spec.get('tags', []),
        'schemas': parse_schemas(spec),
        'endpoints': parse_endpoints(spec),
        'authSchemes': parse_auth_schemes(spec),
        'globalSecurity': spec.get('security', []),
    }


def main():
    parser = argparse.ArgumentParser(
        description='Parse an OpenAPI spec and output a structured JSON summary.'
    )
    parser.add_argument('spec_file', type=Path, help='Path to the OpenAPI spec file')
    parser.add_argument('--output', '-o', type=Path, help='Output file (default: stdout)')
    parser.add_argument('--pretty', '-p', action='store_true', help='Pretty-print JSON output')
    
    args = parser.parse_args()
    
    if not args.spec_file.exists():
        print(f"Error: File not found: {args.spec_file}", file=sys.stderr)
        sys.exit(1)
    
    try:
        spec = load_spec(args.spec_file)
    except Exception as e:
        print(f"Error loading spec: {e}", file=sys.stderr)
        sys.exit(1)
    
    try:
        result = parse_spec(spec)
    except Exception as e:
        print(f"Error parsing spec: {e}", file=sys.stderr)
        sys.exit(1)
    
    indent = 2 if args.pretty else None
    output = json.dumps(result, indent=indent)
    
    if args.output:
        args.output.write_text(output)
        print(f"Output written to {args.output}", file=sys.stderr)
    else:
        print(output)


if __name__ == '__main__':
    main()
