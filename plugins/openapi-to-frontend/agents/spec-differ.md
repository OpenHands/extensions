# Spec Differ Agent

A subagent that compares two OpenAPI specification versions and produces a structured diff.

## Purpose

This agent analyzes the differences between two OpenAPI specs and classifies each change into a type that can be acted upon by the update-from-spec skill.

## Invocation

```
@spec-differ <old-spec-path> <new-spec-path>
```

## Output Format

The agent produces a JSON structure:

```json
{
  "summary": {
    "schemas_added": 2,
    "schemas_removed": 0,
    "schemas_modified": 3,
    "endpoints_added": 4,
    "endpoints_removed": 1,
    "endpoints_modified": 2,
    "auth_changed": false
  },
  "changes": [
    {
      "type": "schema_added",
      "path": "components/schemas/Order",
      "details": {
        "name": "Order",
        "fields": [
          { "name": "id", "type": "string", "required": true },
          { "name": "userId", "type": "string", "required": true },
          { "name": "items", "type": "array", "items": "OrderItem", "required": true },
          { "name": "status", "type": "OrderStatus", "required": true },
          { "name": "createdAt", "type": "string", "format": "date-time", "required": true }
        ]
      }
    },
    {
      "type": "field_added",
      "path": "components/schemas/User.properties.phoneNumber",
      "details": {
        "schema": "User",
        "field": "phoneNumber",
        "type": "string",
        "required": false
      }
    },
    {
      "type": "endpoint_added",
      "path": "paths./orders.get",
      "details": {
        "method": "GET",
        "path": "/orders",
        "operationId": "listOrders",
        "parameters": [
          { "name": "page", "in": "query", "type": "integer" },
          { "name": "status", "in": "query", "type": "OrderStatus" }
        ],
        "response": "OrderListResponse"
      }
    }
  ],
  "breaking_changes": [
    {
      "type": "field_removed",
      "path": "components/schemas/User.properties.legacyId",
      "severity": "high",
      "migration": "Ensure no client code references User.legacyId before removing"
    }
  ]
}
```

## Change Types

### Schema Changes

| Type | Description |
|------|-------------|
| `schema_added` | New schema in components/schemas |
| `schema_removed` | Schema deleted |
| `schema_renamed` | Schema name changed (detected by field similarity) |
| `field_added` | New property added to schema |
| `field_removed` | Property removed from schema |
| `field_type_changed` | Property type changed |
| `field_required_changed` | Required status changed |

### Endpoint Changes

| Type | Description |
|------|-------------|
| `endpoint_added` | New path+method combination |
| `endpoint_removed` | Path+method deleted |
| `endpoint_method_changed` | HTTP method changed (rare) |
| `param_added` | New parameter (path, query, header, body) |
| `param_removed` | Parameter removed |
| `param_type_changed` | Parameter type changed |
| `response_type_changed` | Response schema changed |
| `response_code_added` | New response code |
| `response_code_removed` | Response code removed |

### Auth Changes

| Type | Description |
|------|-------------|
| `auth_scheme_added` | New security scheme |
| `auth_scheme_removed` | Security scheme removed |
| `auth_scheme_modified` | Scheme configuration changed |
| `security_requirement_changed` | Endpoint auth requirements changed |

### Metadata Changes

| Type | Description |
|------|-------------|
| `info_changed` | title, version, description changed |
| `server_added` | New server URL |
| `server_removed` | Server URL removed |
| `tag_added` | New tag |
| `tag_removed` | Tag removed |

## Diff Algorithm

### Step 1: Normalize Specs

1. Parse both specs (JSON or YAML)
2. Resolve all `$ref` references
3. Sort keys for consistent comparison
4. Handle nullable and oneOf/anyOf unions

### Step 2: Compare Schemas

For each schema in old spec:
- If not in new spec → `schema_removed`
- If in new spec → compare fields

For each schema in new spec:
- If not in old spec → `schema_added`

For each field:
- Compare type, format, required, enum values

### Step 3: Compare Endpoints

Build a key for each endpoint: `{method} {path}`

For each endpoint in old spec:
- If not in new spec → `endpoint_removed`
- If in new spec → compare parameters and responses

For each endpoint in new spec:
- If not in old spec → `endpoint_added`

### Step 4: Compare Auth

Compare `components/securitySchemes`:
- Added/removed schemes
- Changed scheme configurations

Compare `security` requirements on paths

### Step 5: Identify Breaking Changes

Flag changes that may break existing clients:

- `schema_removed`
- `field_removed`
- `endpoint_removed`
- `param_added` (required)
- `field_type_changed`
- `auth_scheme_removed`

## Example Usage

### Input: old-spec.yaml

```yaml
openapi: 3.0.0
info:
  title: My API
  version: 1.0.0
components:
  schemas:
    User:
      type: object
      required: [id, email]
      properties:
        id:
          type: string
        email:
          type: string
        legacyId:
          type: string
paths:
  /users:
    get:
      operationId: listUsers
      responses:
        '200':
          content:
            application/json:
              schema:
                type: array
                items:
                  $ref: '#/components/schemas/User'
```

### Input: new-spec.yaml

```yaml
openapi: 3.0.0
info:
  title: My API
  version: 1.1.0
components:
  schemas:
    User:
      type: object
      required: [id, email]
      properties:
        id:
          type: string
        email:
          type: string
        phoneNumber:
          type: string
    Order:
      type: object
      required: [id, userId]
      properties:
        id:
          type: string
        userId:
          type: string
paths:
  /users:
    get:
      operationId: listUsers
      parameters:
        - name: search
          in: query
          schema:
            type: string
      responses:
        '200':
          content:
            application/json:
              schema:
                type: array
                items:
                  $ref: '#/components/schemas/User'
  /orders:
    get:
      operationId: listOrders
      responses:
        '200':
          content:
            application/json:
              schema:
                type: array
                items:
                  $ref: '#/components/schemas/Order'
```

### Output

```json
{
  "summary": {
    "schemas_added": 1,
    "schemas_removed": 0,
    "schemas_modified": 1,
    "endpoints_added": 1,
    "endpoints_removed": 0,
    "endpoints_modified": 1,
    "auth_changed": false
  },
  "changes": [
    {
      "type": "schema_added",
      "path": "components/schemas/Order",
      "details": {
        "name": "Order",
        "fields": [
          { "name": "id", "type": "string", "required": true },
          { "name": "userId", "type": "string", "required": true }
        ]
      }
    },
    {
      "type": "field_added",
      "path": "components/schemas/User.properties.phoneNumber",
      "details": {
        "schema": "User",
        "field": "phoneNumber",
        "type": "string",
        "required": false
      }
    },
    {
      "type": "field_removed",
      "path": "components/schemas/User.properties.legacyId",
      "details": {
        "schema": "User",
        "field": "legacyId",
        "type": "string"
      }
    },
    {
      "type": "param_added",
      "path": "paths./users.get.parameters.search",
      "details": {
        "endpoint": "GET /users",
        "param": "search",
        "in": "query",
        "type": "string",
        "required": false
      }
    },
    {
      "type": "endpoint_added",
      "path": "paths./orders.get",
      "details": {
        "method": "GET",
        "path": "/orders",
        "operationId": "listOrders",
        "response": "Order[]"
      }
    }
  ],
  "breaking_changes": [
    {
      "type": "field_removed",
      "path": "components/schemas/User.properties.legacyId",
      "severity": "medium",
      "migration": "Remove references to User.legacyId in generated code"
    }
  ]
}
```

## Error Handling

- If specs are invalid YAML/JSON, report parsing errors
- If specs are not valid OpenAPI 3.x, report validation errors
- If `$ref` cannot be resolved, report reference errors

## See Also

- [../skills/update-from-spec/SKILL.md](../skills/update-from-spec/SKILL.md) — Uses this agent's output
- [../references/change-taxonomy.md](../references/change-taxonomy.md) — Full change type definitions
