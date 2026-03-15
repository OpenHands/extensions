# Naming Conventions Reference

This document defines how names are transformed from OpenAPI spec to TypeScript to React components.

## Overview

| Layer | Naming Style | Example |
|-------|--------------|---------|
| OpenAPI Schema | PascalCase | `UserProfile` |
| TypeScript Interface | PascalCase | `interface UserProfile` |
| TypeScript Field | camelCase | `firstName: string` |
| React Component | PascalCase + Suffix | `UserProfileForm` |
| React Prop | camelCase | `onUserSelect` |
| CSS Class | kebab-case | `user-profile-form` |
| File Name | PascalCase.tsx | `UserProfileForm.tsx` |
| Directory | PascalCase | `UserProfile/` |

---

## Schema → TypeScript Interface

### Schema Name

| OpenAPI | TypeScript |
|---------|------------|
| `UserProfile` | `interface UserProfile` |
| `user_profile` | `interface UserProfile` |
| `User-Profile` | `interface UserProfile` |

**Rule:** Convert to PascalCase

### Field Name

| OpenAPI | TypeScript |
|---------|------------|
| `first_name` | `firstName` |
| `firstName` | `firstName` |
| `FIRST_NAME` | `firstName` |
| `FirstName` | `firstName` |

**Rule:** Convert to camelCase

### Type Mapping

| OpenAPI Type | OpenAPI Format | TypeScript |
|--------------|----------------|------------|
| `string` | — | `string` |
| `string` | `date` | `string` (YYYY-MM-DD) |
| `string` | `date-time` | `string` (ISO 8601) |
| `string` | `email` | `string` |
| `string` | `uri` | `string` |
| `string` | `uuid` | `string` |
| `string` | `binary` | `Blob` |
| `string` | `byte` | `string` (base64) |
| `integer` | — | `number` |
| `integer` | `int32` | `number` |
| `integer` | `int64` | `number` |
| `number` | — | `number` |
| `number` | `float` | `number` |
| `number` | `double` | `number` |
| `boolean` | — | `boolean` |
| `array` | — | `T[]` |
| `object` | — | Interface or `Record<string, unknown>` |
| `null` | — | `null` |

### Enum Mapping

| OpenAPI | TypeScript |
|---------|------------|
| `enum: ['active', 'inactive']` | `type Status = 'active' \| 'inactive'` |
| Named enum with many values | `enum Status { Active = 'active', ... }` |

### Nullable Fields

| OpenAPI | TypeScript |
|---------|------------|
| `nullable: true` | `T \| null` |
| `x-nullable: true` | `T \| null` |

### Optional Fields

| OpenAPI | TypeScript |
|---------|------------|
| Not in `required` | `field?: T` |
| In `required` | `field: T` |

---

## Endpoint → API Method

### Method Name

| HTTP Method | Path | Method Name |
|-------------|------|-------------|
| GET | `/users` | `listUsers()` |
| GET | `/users/{id}` | `getUser(id)` |
| POST | `/users` | `createUser(data)` |
| PUT | `/users/{id}` | `updateUser(id, data)` |
| PATCH | `/users/{id}` | `patchUser(id, data)` |
| DELETE | `/users/{id}` | `deleteUser(id)` |
| GET | `/users/{userId}/posts` | `listUserPosts(userId)` |
| POST | `/users/{id}/activate` | `activateUser(id)` |
| GET | `/search` | `search(params)` |

### Naming Algorithm

1. Start with HTTP method:
   - GET (list) → `list`
   - GET (single) → `get`
   - POST → `create` or action verb
   - PUT → `update`
   - PATCH → `patch`
   - DELETE → `delete`

2. Add resource name (singular for single, plural for list):
   - `/users` → `Users`
   - `/users/{id}` → `User`

3. For nested resources, include parent:
   - `/users/{userId}/posts` → `UserPosts`

4. For actions, use the action verb:
   - `/users/{id}/activate` → `activateUser`
   - `/orders/{id}/cancel` → `cancelOrder`

5. If operationId is defined, prefer it (convert to camelCase):
   - `operationId: listAllActiveUsers` → `listAllActiveUsers()`

### Parameter Types

| Parameter Location | TypeScript |
|--------------------|------------|
| Path `{id}` | Method argument: `id: string` |
| Query `?page=1` | Optional params object: `params?: { page?: number }` |
| Header | Handled internally or config |
| Body | Data argument: `data: CreateUserRequest` |

### Return Type

| Response | TypeScript |
|----------|------------|
| `200` with schema | `Promise<ResponseType>` |
| `201` with schema | `Promise<ResponseType>` |
| `204` no content | `Promise<void>` |
| List response | `Promise<ListResponse<T>>` |

---

## Schema → React Component

### Component Names

| Schema | Form | Detail | List |
|--------|------|--------|------|
| `User` | `UserForm` | `UserDetail` | `UserList` |
| `UserProfile` | `UserProfileForm` | `UserProfileDetail` | `UserProfileList` |
| `OrderItem` | `OrderItemForm` | `OrderItemDetail` | `OrderItemList` |

### File Names

```
components/
├── User/
│   ├── UserForm.tsx
│   ├── UserDetail.tsx
│   ├── UserList.tsx
│   └── index.ts
├── UserProfile/
│   ├── UserProfileForm.tsx
│   ├── UserProfileDetail.tsx
│   ├── UserProfileList.tsx
│   └── index.ts
```

### Prop Names

| Purpose | Prop Name |
|---------|-----------|
| Entity data | `user`, `userProfile`, `order` |
| Entity ID | `userId`, `userProfileId`, `orderId` |
| Selection handler | `onSelect`, `onUserSelect` |
| Success handler | `onSuccess` |
| Cancel handler | `onCancel` |
| Delete handler | `onDelete` |
| Loading state | `loading`, `isLoading` |
| Error state | `error` |
| CSS class | `className` |

---

## Field → UI Label

| TypeScript Field | UI Label |
|------------------|----------|
| `firstName` | "First Name" |
| `lastName` | "Last Name" |
| `emailAddress` | "Email Address" |
| `createdAt` | "Created At" |
| `isActive` | "Is Active" or "Active" |
| `userId` | "User ID" |
| `httpStatus` | "HTTP Status" |

### Label Algorithm

1. Split camelCase into words
2. Capitalize each word
3. Handle common abbreviations (ID, HTTP, URL, API)

```typescript
function toLabel(field: string): string {
  return field
    // Insert space before capitals
    .replace(/([A-Z])/g, ' $1')
    // Handle ID specially
    .replace(/\bId\b/g, 'ID')
    // Trim and capitalize
    .trim()
    .replace(/^\w/, c => c.toUpperCase());
}
```

---

## Field → Input Type

| Field Type | Field Name Pattern | Input Type |
|------------|-------------------|------------|
| `string` | — | `<input type="text">` |
| `string` | `email`, `*Email` | `<input type="email">` |
| `string` | `password`, `*Password` | `<input type="password">` |
| `string` | `url`, `*Url`, `*Link` | `<input type="url">` |
| `string` | `phone`, `*Phone` | `<input type="tel">` |
| `string` (format: date) | — | `<input type="date">` |
| `string` (format: date-time) | — | `<input type="datetime-local">` |
| `string` (format: time) | — | `<input type="time">` |
| `string` (long text) | `description`, `*Description`, `bio`, `*Content` | `<textarea>` |
| `number` / `integer` | — | `<input type="number">` |
| `boolean` | — | `<input type="checkbox">` |
| enum / union | — | `<select>` |
| `array` | — | Repeatable group |
| `$ref` | — | Nested form or select |

---

## Route Paths

| Resource | Route |
|----------|-------|
| User list | `/users` |
| User detail | `/users/:id` |
| User create | `/users/new` |
| User edit | `/users/:id/edit` |
| Nested resource | `/users/:userId/posts` |

---

## Barrel Exports

**components/User/index.ts:**

```typescript
export { UserForm } from './UserForm';
export type { UserFormProps } from './UserForm';
export { UserDetail } from './UserDetail';
export type { UserDetailProps } from './UserDetail';
export { UserList } from './UserList';
export type { UserListProps } from './UserList';
```

**components/index.ts:**

```typescript
export * from './User';
export * from './UserProfile';
export * from './Order';
export * from './shared';
```

---

## Special Cases

### Acronyms

| OpenAPI | TypeScript | React |
|---------|------------|-------|
| `URL` | `url: string` | Label: "URL" |
| `HTTP` | `http: string` | Label: "HTTP" |
| `API` | `api: string` | Label: "API" |
| `APIKey` | `apiKey: string` | Label: "API Key" |
| `HTMLContent` | `htmlContent: string` | Label: "HTML Content" |

### Plural/Singular

| OpenAPI | Context | TypeScript |
|---------|---------|------------|
| `User` | Single entity | `User` |
| `User` | Array | `User[]` |
| `users` | Field name | `users: User[]` |
| `Users` | Don't use as schema name | — |

### Reserved Words

If a field name conflicts with TypeScript reserved words, escape or rename:

| OpenAPI | TypeScript |
|---------|------------|
| `class` | `_class` or `classValue` |
| `function` | `_function` or `functionName` |
| `type` | `_type` or `typeValue` |
| `default` | `_default` or `defaultValue` |
