---
name: openapi-generate-components
description: Generate React components from a TypeScript API client. Creates Form, Detail, and List components for each schema.
license: MIT
compatibility: Requires React 18+, TypeScript 5+
triggers:
  - openapi components
  - generate react components
  - api to react
  - schema components
---

Generate React components from a TypeScript API client.

## Overview

This skill produces a React component library based on the TypeScript client:

- `components/<SchemaName>/` — Directory per schema containing:
  - `<SchemaName>Form.tsx` — Create/edit form
  - `<SchemaName>Detail.tsx` — Read-only detail view
  - `<SchemaName>List.tsx` — List/table view with pagination
  - `index.ts` — Barrel export
- `components/shared/` — Common UI pieces
- `components/index.ts` — Top-level barrel export

## Prerequisites

- Generated TypeScript client (from generate-client phase)
- React 18+
- TypeScript 5+

## Workflow

### Step 1: Analyze the Client Types

Read `client/types.ts` to understand available schemas and their fields.

For each schema, determine:
- Which endpoints exist (POST/PUT → Form, GET single → Detail, GET list → List)
- Field types for input rendering
- Required vs optional fields
- Nested schemas and relationships

### Step 2: Generate Shared Components

Create common UI pieces in `components/shared/`:

**LoadingSpinner.tsx:**

```tsx
import React from 'react';

export interface LoadingSpinnerProps {
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

export function LoadingSpinner({
  size = 'md',
  className = '',
}: LoadingSpinnerProps) {
  const sizeClasses = {
    sm: 'w-4 h-4',
    md: 'w-8 h-8',
    lg: 'w-12 h-12',
  };

  return (
    <div className={`flex justify-center items-center ${className}`}>
      <div
        className={`${sizeClasses[size]} border-2 border-gray-200 border-t-blue-600 rounded-full animate-spin`}
      />
    </div>
  );
}
```

**ErrorDisplay.tsx:**

```tsx
import React from 'react';

export interface ErrorDisplayProps {
  error: Error | string;
  onRetry?: () => void;
  className?: string;
}

export function ErrorDisplay({
  error,
  onRetry,
  className = '',
}: ErrorDisplayProps) {
  const message = typeof error === 'string' ? error : error.message;

  return (
    <div
      className={`bg-red-50 border border-red-200 rounded-lg p-4 ${className}`}
    >
      <div className="flex items-center gap-2 text-red-700">
        <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
          <path
            fillRule="evenodd"
            d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
            clipRule="evenodd"
          />
        </svg>
        <span className="font-medium">Error</span>
      </div>
      <p className="mt-2 text-red-600">{message}</p>
      {onRetry && (
        <button
          onClick={onRetry}
          className="mt-3 px-4 py-2 bg-red-100 text-red-700 rounded hover:bg-red-200 transition-colors"
        >
          Retry
        </button>
      )}
    </div>
  );
}
```

**Pagination.tsx:**

```tsx
import React from 'react';

export interface PaginationProps {
  page: number;
  pageSize: number;
  total: number;
  onPageChange: (page: number) => void;
  className?: string;
}

export function Pagination({
  page,
  pageSize,
  total,
  onPageChange,
  className = '',
}: PaginationProps) {
  const totalPages = Math.ceil(total / pageSize);
  const canGoPrev = page > 1;
  const canGoNext = page < totalPages;

  return (
    <div
      className={`flex items-center justify-between px-4 py-3 ${className}`}
    >
      <div className="text-sm text-gray-700">
        Showing {(page - 1) * pageSize + 1} to{' '}
        {Math.min(page * pageSize, total)} of {total} results
      </div>
      <div className="flex gap-2">
        <button
          onClick={() => onPageChange(page - 1)}
          disabled={!canGoPrev}
          className="px-3 py-1 border rounded disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50"
        >
          Previous
        </button>
        <span className="px-3 py-1">
          Page {page} of {totalPages}
        </span>
        <button
          onClick={() => onPageChange(page + 1)}
          disabled={!canGoNext}
          className="px-3 py-1 border rounded disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50"
        >
          Next
        </button>
      </div>
    </div>
  );
}
```

### Step 3: Generate Schema Components

For each schema with API endpoints, create a component directory.

#### Form Component

Generated when POST or PUT endpoints exist for the schema.

**Mapping Rules:**

| Field Type | Input Component |
|------------|-----------------|
| `string` | `<input type="text">` |
| `string` (format: email) | `<input type="email">` |
| `string` (format: password) | `<input type="password">` |
| `string` (format: date) | `<input type="date">` |
| `string` (format: date-time) | `<input type="datetime-local">` |
| `string` (format: uri) | `<input type="url">` |
| `string` (multiline/long) | `<textarea>` |
| `number` / `integer` | `<input type="number">` |
| `boolean` | `<input type="checkbox">` or toggle |
| `enum` / union | `<select>` with options |
| `array` | Repeatable field group with add/remove |
| `$ref` (related schema) | Nested form or select dropdown |

**Example UserForm.tsx:**

```tsx
import React, { useState, FormEvent } from 'react';
import type {
  User,
  CreateUserRequest,
  UpdateUserRequest,
  UserRole,
} from '../../client/types';
import { useApiClient } from '../../app/context/ApiContext';
import { LoadingSpinner } from '../shared/LoadingSpinner';
import { ErrorDisplay } from '../shared/ErrorDisplay';

export interface UserFormProps {
  user?: User; // If provided, edit mode; otherwise create mode
  onSuccess?: (user: User) => void;
  onCancel?: () => void;
  className?: string;
}

const USER_ROLES: UserRole[] = ['admin', 'user', 'guest'];

export function UserForm({
  user,
  onSuccess,
  onCancel,
  className = '',
}: UserFormProps) {
  const client = useApiClient();
  const isEditMode = !!user;

  const [formData, setFormData] = useState({
    email: user?.email || '',
    firstName: user?.firstName || '',
    lastName: user?.lastName || '',
    password: '',
    role: user?.role || ('user' as UserRole),
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const handleChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>
  ) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      let result: User;
      if (isEditMode && user) {
        const updateData: UpdateUserRequest = {
          firstName: formData.firstName,
          lastName: formData.lastName,
          role: formData.role,
        };
        result = await client.updateUser(user.id, updateData);
      } else {
        const createData: CreateUserRequest = {
          email: formData.email,
          firstName: formData.firstName,
          lastName: formData.lastName,
          password: formData.password,
          role: formData.role,
        };
        result = await client.createUser(createData);
      }
      onSuccess?.(result);
    } catch (err) {
      setError(err instanceof Error ? err : new Error(String(err)));
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className={`space-y-4 ${className}`}>
      {error && <ErrorDisplay error={error} />}

      <div>
        <label htmlFor="email" className="block text-sm font-medium mb-1">
          Email <span className="text-red-500">*</span>
        </label>
        <input
          type="email"
          id="email"
          name="email"
          value={formData.email}
          onChange={handleChange}
          required
          disabled={isEditMode}
          className="w-full px-3 py-2 border rounded focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100"
        />
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <label htmlFor="firstName" className="block text-sm font-medium mb-1">
            First Name <span className="text-red-500">*</span>
          </label>
          <input
            type="text"
            id="firstName"
            name="firstName"
            value={formData.firstName}
            onChange={handleChange}
            required
            className="w-full px-3 py-2 border rounded focus:ring-2 focus:ring-blue-500"
          />
        </div>
        <div>
          <label htmlFor="lastName" className="block text-sm font-medium mb-1">
            Last Name <span className="text-red-500">*</span>
          </label>
          <input
            type="text"
            id="lastName"
            name="lastName"
            value={formData.lastName}
            onChange={handleChange}
            required
            className="w-full px-3 py-2 border rounded focus:ring-2 focus:ring-blue-500"
          />
        </div>
      </div>

      {!isEditMode && (
        <div>
          <label htmlFor="password" className="block text-sm font-medium mb-1">
            Password <span className="text-red-500">*</span>
          </label>
          <input
            type="password"
            id="password"
            name="password"
            value={formData.password}
            onChange={handleChange}
            required
            minLength={8}
            className="w-full px-3 py-2 border rounded focus:ring-2 focus:ring-blue-500"
          />
        </div>
      )}

      <div>
        <label htmlFor="role" className="block text-sm font-medium mb-1">
          Role
        </label>
        <select
          id="role"
          name="role"
          value={formData.role}
          onChange={handleChange}
          className="w-full px-3 py-2 border rounded focus:ring-2 focus:ring-blue-500"
        >
          {USER_ROLES.map((role) => (
            <option key={role} value={role}>
              {role.charAt(0).toUpperCase() + role.slice(1)}
            </option>
          ))}
        </select>
      </div>

      <div className="flex gap-3 pt-4">
        <button
          type="submit"
          disabled={loading}
          className="flex-1 px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
        >
          {loading ? (
            <LoadingSpinner size="sm" />
          ) : isEditMode ? (
            'Update User'
          ) : (
            'Create User'
          )}
        </button>
        {onCancel && (
          <button
            type="button"
            onClick={onCancel}
            className="px-4 py-2 border rounded hover:bg-gray-50"
          >
            Cancel
          </button>
        )}
      </div>
    </form>
  );
}
```

#### Detail Component

Generated when GET (single) endpoints exist.

**Example UserDetail.tsx:**

```tsx
import React, { useEffect, useState } from 'react';
import type { User } from '../../client/types';
import { useApiClient } from '../../app/context/ApiContext';
import { LoadingSpinner } from '../shared/LoadingSpinner';
import { ErrorDisplay } from '../shared/ErrorDisplay';

export interface UserDetailProps {
  userId: string;
  onEdit?: (user: User) => void;
  onDelete?: (user: User) => void;
  className?: string;
}

export function UserDetail({
  userId,
  onEdit,
  onDelete,
  className = '',
}: UserDetailProps) {
  const client = useApiClient();
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const fetchUser = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await client.getUser(userId);
      setUser(data);
    } catch (err) {
      setError(err instanceof Error ? err : new Error(String(err)));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchUser();
  }, [userId]);

  if (loading) {
    return <LoadingSpinner className="py-8" />;
  }

  if (error) {
    return <ErrorDisplay error={error} onRetry={fetchUser} />;
  }

  if (!user) {
    return <div className="text-gray-500">User not found</div>;
  }

  const handleDelete = async () => {
    if (!confirm('Are you sure you want to delete this user?')) return;
    try {
      await client.deleteUser(userId);
      onDelete?.(user);
    } catch (err) {
      setError(err instanceof Error ? err : new Error(String(err)));
    }
  };

  return (
    <div className={`bg-white rounded-lg shadow ${className}`}>
      <div className="px-6 py-4 border-b">
        <h2 className="text-xl font-semibold">
          {user.firstName} {user.lastName}
        </h2>
        <p className="text-gray-500">{user.email}</p>
      </div>

      <dl className="px-6 py-4 space-y-3">
        <div className="flex">
          <dt className="w-32 text-gray-500">ID</dt>
          <dd className="font-mono text-sm">{user.id}</dd>
        </div>
        <div className="flex">
          <dt className="w-32 text-gray-500">Role</dt>
          <dd>
            <span className="px-2 py-1 text-xs rounded bg-blue-100 text-blue-700">
              {user.role}
            </span>
          </dd>
        </div>
        <div className="flex">
          <dt className="w-32 text-gray-500">Created</dt>
          <dd>{new Date(user.createdAt).toLocaleDateString()}</dd>
        </div>
        {user.updatedAt && (
          <div className="flex">
            <dt className="w-32 text-gray-500">Updated</dt>
            <dd>{new Date(user.updatedAt).toLocaleDateString()}</dd>
          </div>
        )}
      </dl>

      <div className="px-6 py-4 border-t flex gap-3">
        {onEdit && (
          <button
            onClick={() => onEdit(user)}
            className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
          >
            Edit
          </button>
        )}
        {onDelete && (
          <button
            onClick={handleDelete}
            className="px-4 py-2 border border-red-300 text-red-600 rounded hover:bg-red-50"
          >
            Delete
          </button>
        )}
      </div>
    </div>
  );
}
```

#### List Component

Generated when GET (list) endpoints exist.

**Example UserList.tsx:**

```tsx
import React, { useEffect, useState, useCallback } from 'react';
import type { User, UserListResponse } from '../../client/types';
import { useApiClient } from '../../app/context/ApiContext';
import { LoadingSpinner } from '../shared/LoadingSpinner';
import { ErrorDisplay } from '../shared/ErrorDisplay';
import { Pagination } from '../shared/Pagination';

export interface UserListProps {
  onSelect?: (user: User) => void;
  className?: string;
}

export function UserList({ onSelect, className = '' }: UserListProps) {
  const client = useApiClient();
  const [data, setData] = useState<UserListResponse | null>(null);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const pageSize = 10;

  const fetchUsers = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await client.listUsers({
        page,
        pageSize,
        search: search || undefined,
      });
      setData(response);
    } catch (err) {
      setError(err instanceof Error ? err : new Error(String(err)));
    } finally {
      setLoading(false);
    }
  }, [client, page, pageSize, search]);

  useEffect(() => {
    fetchUsers();
  }, [fetchUsers]);

  const handleSearch = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setPage(1);
    fetchUsers();
  };

  return (
    <div className={`bg-white rounded-lg shadow ${className}`}>
      <div className="px-6 py-4 border-b">
        <form onSubmit={handleSearch} className="flex gap-2">
          <input
            type="search"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search users..."
            className="flex-1 px-3 py-2 border rounded focus:ring-2 focus:ring-blue-500"
          />
          <button
            type="submit"
            className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
          >
            Search
          </button>
        </form>
      </div>

      {loading ? (
        <LoadingSpinner className="py-8" />
      ) : error ? (
        <ErrorDisplay error={error} onRetry={fetchUsers} className="m-4" />
      ) : !data || data.items.length === 0 ? (
        <div className="px-6 py-8 text-center text-gray-500">
          No users found
        </div>
      ) : (
        <>
          <table className="w-full">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Name
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Email
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Role
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Created
                </th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {data.items.map((user) => (
                <tr
                  key={user.id}
                  onClick={() => onSelect?.(user)}
                  className={onSelect ? 'cursor-pointer hover:bg-gray-50' : ''}
                >
                  <td className="px-6 py-4">
                    {user.firstName} {user.lastName}
                  </td>
                  <td className="px-6 py-4 text-gray-500">{user.email}</td>
                  <td className="px-6 py-4">
                    <span className="px-2 py-1 text-xs rounded bg-blue-100 text-blue-700">
                      {user.role}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-gray-500">
                    {new Date(user.createdAt).toLocaleDateString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          <Pagination
            page={page}
            pageSize={pageSize}
            total={data.total}
            onPageChange={setPage}
            className="border-t"
          />
        </>
      )}
    </div>
  );
}
```

### Step 4: Generate Barrel Exports

**components/<SchemaName>/index.ts:**

```typescript
export { UserForm } from './UserForm';
export type { UserFormProps } from './UserForm';
export { UserDetail } from './UserDetail';
export type { UserDetailProps } from './UserDetail';
export { UserList } from './UserList';
export type { UserListProps } from './UserList';
```

**components/shared/index.ts:**

```typescript
export { LoadingSpinner } from './LoadingSpinner';
export type { LoadingSpinnerProps } from './LoadingSpinner';
export { ErrorDisplay } from './ErrorDisplay';
export type { ErrorDisplayProps } from './ErrorDisplay';
export { Pagination } from './Pagination';
export type { PaginationProps } from './Pagination';
```

**components/index.ts:**

```typescript
export * from './User';
// ... other schema exports
export * from './shared';
```

### Step 5: Verify Output

Run the verification scripts:

```bash
# Lint the generated code
./scripts/lint-generated.sh

# Verify components match client types
python scripts/verify-components.py client/ components/
```

## Component Conventions

1. **API Client via Context** — Components receive the client through React context, not props
2. **Loading States** — All data-fetching components show a spinner while loading
3. **Error Handling** — All components display errors with retry option
4. **Empty States** — List components show appropriate message when no data
5. **Accessibility** — Labels linked to inputs, semantic HTML
6. **Styling** — Tailwind CSS classes (no UI framework dependency)

## Output Files

| Directory | Contents |
|-----------|----------|
| `components/<Schema>/` | Form, Detail, List components per schema |
| `components/shared/` | LoadingSpinner, ErrorDisplay, Pagination |
| `components/index.ts` | Top-level barrel export |

## Next Steps

After generating components, proceed to:

1. **Generate Frontend** — Create application shell and routing
2. **Generate Tests** — Create component tests

See [../generate-frontend/SKILL.md](../generate-frontend/SKILL.md)
