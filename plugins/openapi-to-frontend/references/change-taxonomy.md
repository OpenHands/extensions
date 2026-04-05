# Change Taxonomy Reference

This document enumerates all change types detected by the spec-differ agent and how each should be handled by the update-from-spec skill.

## Change Types Overview

| Category | Change Types |
|----------|--------------|
| Schema | added, removed, renamed |
| Field | added, removed, type_changed, required_changed |
| Endpoint | added, removed |
| Parameter | added, removed, type_changed, location_changed |
| Response | type_changed, code_added, code_removed |
| Auth | scheme_added, scheme_removed, scheme_modified |
| Enum | values_added, values_removed, values_reordered |
| Metadata | info_changed, server_changed, tag_changed |

---

## Schema Changes

### schema_added

**When:** New schema appears in `components/schemas`

**Impact:**
- Client: Add interface to types.ts, add methods to api.ts if endpoints exist
- Components: Add component directory with Form/Detail/List
- Frontend: Add page and route if it's a primary resource
- Tests: Add factory, type guard, component tests

**Actions:**

```
1. types.ts: Add interface
   export interface NewSchema { ... }

2. api.ts: Add methods (if endpoints exist)
   async listNewSchemas(): Promise<...>
   async getNewSchema(id: string): Promise<...>

3. components/NewSchema/: Create directory
   - NewSchemaForm.tsx
   - NewSchemaDetail.tsx
   - NewSchemaList.tsx
   - index.ts

4. components/index.ts: Add export
   export * from './NewSchema';

5. app/pages/: Add page (if primary resource)
   NewSchemasPage.tsx

6. app/App.tsx: Add routes

7. app/Layout.tsx: Add nav item

8. tests/setup/factories.ts: Add makeNewSchema()

9. tests/unit/components/: Add test files
```

---

### schema_removed

**When:** Schema no longer exists in `components/schemas`

**Impact:**
- Client: Remove interface, remove methods, remove imports
- Components: Remove entire directory
- Frontend: Remove page, route, navigation
- Tests: Remove factories, guards, tests

**Actions:**

```
1. types.ts: Remove interface
   - Delete interface definition
   - Remove from any union types
   - Remove related enums

2. api.ts: Remove methods
   - Delete methods using this type
   - Update imports

3. components/SchemaName/: Delete directory
   rm -rf components/SchemaName/

4. components/index.ts: Remove export

5. app/pages/: Delete page
   rm app/pages/SchemaNamesPage.tsx
   rm app/pages/SchemaNameDetailPage.tsx
   rm app/pages/SchemaNameFormPage.tsx

6. app/App.tsx: Remove routes

7. app/Layout.tsx: Remove nav item

8. tests/: Remove all related test files
```

**Breaking Change:** Yes — warn user before applying

---

### schema_renamed

**When:** Schema name changed but fields are similar (>80% match)

**Impact:** Same as remove + add, but preserve user customizations

**Actions:**

```
1. types.ts: Rename interface
   - Find: interface OldName
   - Replace: interface NewName

2. Update all imports and usages

3. Rename component directory
   mv components/OldName/ components/NewName/

4. Rename component files
   mv OldNameForm.tsx NewNameForm.tsx
   
5. Update component names inside files

6. Update routes and navigation
```

---

## Field Changes

### field_added

**When:** New property added to schema

**Impact:**
- Client: Add to interface
- Components: Add to Form, Detail, List
- Tests: Update factories

**Actions:**

```
1. types.ts: Add field to interface
   export interface User {
     // existing fields...
     newField?: string;  // ADD
   }

2. UserForm.tsx: Add input
   <div>
     <label>New Field</label>
     <input name="newField" ... />
   </div>

3. UserDetail.tsx: Add display
   <div>
     <dt>New Field</dt>
     <dd>{user.newField}</dd>
   </div>

4. UserList.tsx: Add column (if important)
   <th>New Field</th>
   <td>{user.newField}</td>

5. factories.ts: Add to factory
   export function makeUser(overrides = {}) {
     return {
       ...existing,
       newField: null,  // ADD
       ...overrides
     };
   }
```

---

### field_removed

**When:** Property deleted from schema

**Impact:**
- Client: Remove from interface
- Components: Remove from Form, Detail, List
- Tests: Update factories and assertions

**Actions:**

```
1. types.ts: Remove field from interface

2. Form: Remove input and label

3. Detail: Remove display row

4. List: Remove column

5. factories.ts: Remove from factory

6. Existing tests: Remove assertions on this field
```

**Breaking Change:** Yes if field was required

---

### field_type_changed

**When:** Property type changed

**Examples:**
- `string` → `number`
- `string` → `enum`
- `string` → `$ref`

**Impact:**
- Client: Update type
- Components: Update input component

**Actions:**

```
1. types.ts: Update field type
   // Before: status: string;
   // After:  status: OrderStatus;

2. Form: Update input type
   // Before: <input type="text" ...>
   // After:  <select>...</select>

3. factories.ts: Update mock value

4. Tests: Update assertions
```

---

### field_required_changed

**When:** Field moved in/out of `required` array

**Impact:**
- Client: Add/remove `?` from field
- Components: Add/remove required validation

**Actions:**

```
1. types.ts:
   // Now required: field: string;
   // Now optional: field?: string;

2. Form: Update required attribute
   <input required={true/false} ...>

3. Validation: Update schema/logic
```

---

## Endpoint Changes

### endpoint_added

**When:** New path+method combination

**Impact:**
- Client: Add method
- Components: Add functionality if creates new capability
- Frontend: Add route if new resource

**Actions:**

```
1. api.ts: Add method
   async newEndpoint(...): Promise<...> {
     return this.request('METHOD', '/path', ...);
   }

2. types.ts: Add params/response types if needed

3. Components:
   - GET list → Add List component
   - GET single → Add Detail component
   - POST → Add Form component
   - DELETE → Add delete button
   - Custom action → Add action button

4. Frontend: Add page/route if new resource
```

---

### endpoint_removed

**When:** Path+method no longer exists

**Impact:**
- Client: Remove method
- Components: Disable/hide functionality
- Frontend: Remove route if resource deleted

**Actions:**

```
1. api.ts: Remove method

2. Components:
   - List endpoint removed → Hide/disable list
   - Detail endpoint removed → Hide/disable detail view
   - Create endpoint removed → Hide create button
   - Delete endpoint removed → Hide delete button

3. Frontend: Remove route if applicable

4. Tests: Remove related tests
```

**Breaking Change:** Yes — warn user

---

## Parameter Changes

### param_added

**When:** New parameter added to endpoint

**Impact:**
- Client: Update method signature
- Components: Add filter/input for new param

**Actions:**

```
1. api.ts: Add to params type
   interface ListUsersParams {
     existing: string;
     newParam?: string;  // ADD
   }

2. Components: Add UI for new param
   - Query param → Add filter/search input
   - Path param → Usually affects route
   - Body param → Add form field
```

---

### param_removed

**When:** Parameter removed from endpoint

**Actions:**

```
1. api.ts: Remove from params type

2. Components: Remove filter/input
```

---

### param_type_changed

**When:** Parameter type changed

**Actions:**

```
1. api.ts: Update param type

2. Components: Update input type
```

---

## Response Changes

### response_type_changed

**When:** Response schema changed

**Actions:**

```
1. api.ts: Update return type

2. types.ts: Update response interface

3. Components: Update rendering
```

---

### response_code_added

**When:** New response code added (e.g., 400, 404)

**Actions:**

```
1. Consider adding error handling for new code

2. Components: Handle new error case
```

---

## Auth Changes

### auth_scheme_added

**When:** New security scheme in securitySchemes

**Impact:**
- Client: Add auth handler
- Frontend: Add login flow if first auth

**Actions:**

```
1. auth.ts: Add handler type and function
   export interface NewAuth { type: 'new'; ... }
   
2. api.ts: Update attachAuth

3. Frontend (if first auth):
   - Add AuthContext
   - Add AuthGuard
   - Add LoginPage
   - Add callback route (if OAuth)
```

---

### auth_scheme_removed

**When:** Security scheme removed

**Actions:**

```
1. auth.ts: Remove handler

2. Frontend (if last auth):
   - Remove login flow
   - Remove guards
```

---

### auth_scheme_modified

**When:** Scheme configuration changed

**Examples:**
- OAuth URLs changed
- Scopes changed
- Header name changed

**Actions:**

```
1. auth.ts: Update configuration

2. Frontend: Update OAuth config
```

---

## Enum Changes

### enum_values_added

**When:** New values added to enum

**Actions:**

```
1. types.ts: Add values
   type Status = 'a' | 'b' | 'c';  // added 'c'

2. Components: Add option
   <option value="c">C</option>
```

---

### enum_values_removed

**When:** Values removed from enum

**Actions:**

```
1. types.ts: Remove values

2. Components: Remove option
```

**Breaking Change:** Yes — data may have removed values

---

## Metadata Changes

### info_changed

**When:** API info (title, description, version) changed

**Impact:** Usually none — consider updating UI titles

---

### server_changed

**When:** Server URLs changed

**Impact:** Update base URL configuration

---

### tag_changed

**When:** Tags added/removed/modified

**Impact:** Update navigation grouping

---

## Change Severity

| Severity | Description | Action |
|----------|-------------|--------|
| **None** | Metadata only | Auto-apply |
| **Low** | Additive change | Auto-apply, notify |
| **Medium** | Non-breaking modification | Apply with review |
| **High** | Breaking change | Warn, require confirmation |

### High Severity (Breaking)

- schema_removed
- field_removed (required)
- endpoint_removed
- param_added (required)
- field_type_changed (incompatible)
- enum_values_removed
- auth_scheme_removed

### Medium Severity

- field_type_changed (compatible)
- param_removed
- response_type_changed
- auth_scheme_modified

### Low Severity

- schema_added
- field_added
- endpoint_added
- param_added (optional)
- enum_values_added

### None

- info_changed
- description_changed
- server_changed
- tag_changed
