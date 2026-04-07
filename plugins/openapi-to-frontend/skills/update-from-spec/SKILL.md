---
name: openapi-update-from-spec
description: Apply incremental updates to generated code when the OpenAPI spec changes. Makes surgical edits rather than regenerating.
license: MIT
compatibility: Requires existing generated codebase from this plugin
triggers:
  - openapi update
  - spec changed
  - update from spec
  - incremental update
  - api changed
---

Apply incremental updates when the OpenAPI spec changes.

## Overview

Instead of regenerating all code when the spec changes, this skill:

1. Diffs the old and new spec versions
2. Classifies each change into a type (see taxonomy)
3. Applies targeted edits to existing files
4. Verifies the result compiles and is consistent

## Prerequisites

- Previously generated code (client, components, frontend)
- Both old and new OpenAPI spec files
- The spec-differ agent (see `agents/spec-differ.md`)

## Workflow

### Step 1: Diff the Specs

Use the spec-differ agent to compare versions:

```
@spec-differ old-spec.yaml new-spec.yaml
```

The agent outputs a structured list of changes:

```json
{
  "changes": [
    {
      "type": "schema_added",
      "path": "components/schemas/Order",
      "details": { "fields": ["id", "userId", "items", "status", "createdAt"] }
    },
    {
      "type": "endpoint_added",
      "path": "paths./orders.get",
      "details": { "method": "GET", "operationId": "listOrders" }
    },
    {
      "type": "field_added",
      "path": "components/schemas/User.properties.phoneNumber",
      "details": { "type": "string", "required": false }
    }
  ]
}
```

### Step 2: Apply Changes by Type

For each change, apply the corresponding update strategy:

---

#### Schema Added

**Impact:** Client → Components → (Maybe) Frontend

**Actions:**

1. **types.ts**: Add new interface at end of file
   ```typescript
   export interface Order {
     id: string;
     userId: string;
     items: OrderItem[];
     status: OrderStatus;
     createdAt: string;
   }
   ```

2. **api.ts**: Add methods if endpoints exist for this schema
   ```typescript
   async listOrders(params?: ListOrdersParams): Promise<OrderListResponse> {
     return this.request('GET', '/orders', { params });
   }
   ```

3. **components/**: Create new directory with Form/Detail/List components
   - `components/Order/OrderForm.tsx`
   - `components/Order/OrderDetail.tsx`
   - `components/Order/OrderList.tsx`
   - `components/Order/index.ts`

4. **components/index.ts**: Add export
   ```typescript
   export * from './Order';
   ```

5. **Frontend (if needed)**: Add page and route for new resource
   - `app/pages/OrdersPage.tsx`
   - Update `App.tsx` with new routes
   - Update `Layout.tsx` navigation

---

#### Schema Removed

**Impact:** Client → Components → Frontend

**Actions:**

1. **types.ts**: Remove interface and any references
   - Search for `interface SchemaName` and delete
   - Search for imports/usages and remove

2. **api.ts**: Remove methods that used this schema
   - Delete methods returning or accepting this type
   - Update imports

3. **components/**: Delete entire directory
   ```bash
   rm -rf components/SchemaName/
   ```

4. **components/index.ts**: Remove export line

5. **Frontend**: Remove page, route, and navigation
   - Delete `app/pages/SchemaNamePage.tsx`
   - Remove routes from `App.tsx`
   - Remove nav item from `Layout.tsx`

6. **Tests**: Remove test files for this schema
   ```bash
   rm tests/unit/components/SchemaName.test.tsx
   rm tests/integration/SchemaNameFlow.test.tsx
   ```

---

#### Schema Field Added

**Impact:** Client → Components

**Actions:**

1. **types.ts**: Add field to interface
   ```typescript
   // Find interface
   export interface User {
     id: string;
     email: string;
     // ADD HERE:
     phoneNumber?: string;
   }
   ```

2. **Components**: Add field to Form and Detail
   
   **Form** — Add input field:
   ```tsx
   <div>
     <label htmlFor="phoneNumber">Phone Number</label>
     <input
       type="tel"
       id="phoneNumber"
       name="phoneNumber"
       value={formData.phoneNumber || ''}
       onChange={handleChange}
     />
   </div>
   ```
   
   **Detail** — Add display row:
   ```tsx
   {user.phoneNumber && (
     <div className="flex">
       <dt className="w-32 text-gray-500">Phone</dt>
       <dd>{user.phoneNumber}</dd>
     </div>
   )}
   ```
   
   **List** — Add column if important field:
   ```tsx
   <th>Phone</th>
   // ...
   <td>{user.phoneNumber}</td>
   ```

3. **Tests**: Update factories and tests
   ```typescript
   // factories.ts
   export function makeUser(overrides = {}) {
     return {
       // ... existing fields
       phoneNumber: null,  // ADD
       ...overrides
     };
   }
   ```

---

#### Schema Field Removed

**Impact:** Client → Components

**Actions:**

1. **types.ts**: Remove field from interface

2. **Components**: Remove from Form, Detail, List
   - Search for field name and remove
   - Remove associated label, input, display

3. **Tests**: Update factories and test assertions

---

#### Schema Field Type Changed

**Impact:** Client → Components

**Actions:**

1. **types.ts**: Update field type
   ```typescript
   // Before: status: string;
   // After:  status: OrderStatus;
   ```

2. **Components**: Update input type if needed
   - `string` → `enum`: Change text input to select
   - `number` → `string`: Change number input to text
   - `boolean` → `string`: Change checkbox to text

3. **Tests**: Update type guards and assertions

---

#### Endpoint Added

**Impact:** Client → (Maybe) Components → (Maybe) Frontend

**Actions:**

1. **api.ts**: Add method
   ```typescript
   async cancelOrder(id: string): Promise<Order> {
     return this.request('POST', `/orders/${id}/cancel`);
   }
   ```

2. **Components** (if creates new capability):
   - GET list → Add List component if missing
   - POST → Add Form component if missing
   - Add action buttons (cancel, approve, etc.)

3. **Frontend** (if new resource):
   - Add page and route

---

#### Endpoint Removed

**Impact:** Client → Components → Frontend

**Actions:**

1. **api.ts**: Remove method

2. **Components**: Remove functionality that depends on it
   - If DELETE removed → hide delete button
   - If POST removed → hide create button

3. **Frontend**: Update UI to reflect missing capability

---

#### Endpoint Parameters Changed

**Impact:** Client → Components

**Actions:**

1. **api.ts**: Update method signature
   ```typescript
   // Before: async listOrders(params?: { page?: number })
   // After:  async listOrders(params?: { page?: number; status?: OrderStatus })
   ```

2. **Components**: Update to use new params
   - Add filters for new query params
   - Update form fields for new body params

---

#### Endpoint Response Changed

**Impact:** Client → Components

**Actions:**

1. **api.ts**: Update return type

2. **types.ts**: Update response interface if it changed

3. **Components**: Update rendering to handle new shape

---

#### Auth Method Added/Changed/Removed

**Impact:** Client → Frontend

**Actions:**

1. **auth.ts**: Add/update/remove auth handler

2. **Frontend**:
   - Added OAuth2 → Add login pages if not present
   - Removed all auth → Remove login flow and guards
   - Changed → Update login UI accordingly

---

#### Enum Values Changed

**Impact:** Client → Components

**Actions:**

1. **types.ts**: Update union type or enum
   ```typescript
   // Before: type Status = 'pending' | 'active';
   // After:  type Status = 'pending' | 'active' | 'suspended';
   ```

2. **Components**: Update select options
   ```tsx
   const STATUS_OPTIONS = ['pending', 'active', 'suspended'];
   ```

---

### Step 3: Verify Changes

After applying updates:

```bash
# Type check
npm run typecheck

# Lint
npm run lint

# Run verification scripts
python scripts/verify-coverage.py new-spec.yaml client/
python scripts/verify-components.py client/ components/

# Run tests
npm run test:unit
npm run test:integration
```

### Step 4: Report Summary

Output a summary of changes made:

```
## Update Summary

Applied 5 changes from spec diff:

### Added
- Interface `Order` in types.ts
- Method `listOrders` in api.ts
- Components: Order/OrderForm.tsx, Order/OrderDetail.tsx, Order/OrderList.tsx
- Page: app/pages/OrdersPage.tsx
- Route: /orders

### Modified
- Interface `User`: added field `phoneNumber`
- Component UserForm.tsx: added phone input

### Verification
✓ Type check passed
✓ Lint passed
✓ Coverage verification passed
✓ Unit tests passed
```

## Change Taxonomy Reference

| Change Type | Scope | Strategy |
|-------------|-------|----------|
| schema_added | Client → Components → Frontend | Add interface, methods, components, page |
| schema_removed | Client → Components → Frontend | Remove all related code |
| field_added | Client → Components | Add to interface and forms/displays |
| field_removed | Client → Components | Remove from interface and UI |
| field_type_changed | Client → Components | Update type and input component |
| endpoint_added | Client → Components | Add method, maybe add component |
| endpoint_removed | Client → Components | Remove method, disable UI |
| endpoint_params_changed | Client → Components | Update signature and UI |
| endpoint_response_changed | Client → Components | Update return type and rendering |
| auth_added | Client → Frontend | Add auth handler and login flow |
| auth_removed | Client → Frontend | Remove auth and guards |
| auth_changed | Client → Frontend | Update auth handler |
| enum_changed | Client → Components | Update type and select options |
| description_changed | None | No code changes |

## Best Practices

1. **Don't regenerate** — Make surgical edits to preserve user customizations
2. **Preserve formatting** — Match existing code style
3. **Update tests** — Don't forget to update factories and assertions
4. **Verify completeness** — Run coverage scripts after every update
5. **Commit atomically** — One commit per change type for easy rollback

## Edge Cases

### Breaking Changes

If a change would break existing functionality:

1. Warn the user before applying
2. Suggest migration steps
3. Add TODO comments for manual review

### Ambiguous Changes

If the impact is unclear:

1. Ask the user for clarification
2. Show both options and let them choose
3. Default to the safer option

### Conflicting Changes

If user has modified generated code:

1. Detect modifications (compare to expected output)
2. Show conflicts
3. Let user merge manually or accept overwrite

## See Also

- [../agents/spec-differ.md](../../agents/spec-differ.md) — The subagent that produces the diff
- [../../references/change-taxonomy.md](../../references/change-taxonomy.md) — Full change type reference
