---
name: openapi-generate-frontend
description: Generate a complete React frontend application from components and API client. Creates routing, context, and purpose-built UI.
license: MIT
compatibility: Requires React 18+, TypeScript 5+, React Router 6+
triggers:
  - openapi frontend
  - generate react app
  - api to app
  - frontend from api
---

Generate a complete React frontend application from the component library.

## Overview

This skill produces a full React application:

- `app/App.tsx` — Main app shell with routing
- `app/pages/` — One page per major resource/workflow
- `app/context/` — API client provider, auth context
- `app/hooks/` — Custom hooks for data fetching
- `app/utils/localStorage.ts` — UI state persistence helpers

## Prerequisites

- Generated TypeScript client (from generate-client phase)
- Generated React components (from generate-components phase)
- React 18+, React Router 6+

## Workflow

### Step 1: Analyze the API Purpose

Read the OpenAPI spec's `info.title`, `info.description`, and endpoint patterns to infer what the app is *for*:

| API Pattern | Frontend Style |
|-------------|----------------|
| **CRUD API** (resources with full CRUD) | Dashboard with list pages, forms, detail views |
| **Data/Analytics API** (read-heavy, aggregations) | Dashboard with charts, filters, summary cards |
| **Auth-heavy API** (user management, permissions) | Login flow, user profile, admin panel |
| **Workflow API** (status transitions, steps) | Step-by-step wizards, status tracking |
| **Search API** (query endpoints, filters) | Search-first UI with results and filters |
| **Mixed** | Sidebar navigation grouping by resource tag |

**Before generating, explain the inference to the user:**

> "Based on the API, this appears to be a **user management system** with CRUD operations for users, roles, and permissions. I'll generate a dashboard-style app with:
> - Login/logout flow (OAuth2 detected)
> - Users list page with search
> - User detail and edit pages
> - Roles management section
>
> Does this match your expectations, or would you like a different approach?"

### Step 2: Generate Context Providers

**app/context/ApiContext.tsx:**

```tsx
import React, { createContext, useContext, useMemo } from 'react';
import { ApiClient, ApiConfig } from '../../client';

const ApiContext = createContext<ApiClient | null>(null);

export interface ApiProviderProps {
  config: ApiConfig;
  children: React.ReactNode;
}

export function ApiProvider({ config, children }: ApiProviderProps) {
  const client = useMemo(() => new ApiClient(config), [config]);

  return <ApiContext.Provider value={client}>{children}</ApiContext.Provider>;
}

export function useApiClient(): ApiClient {
  const client = useContext(ApiContext);
  if (!client) {
    throw new Error('useApiClient must be used within an ApiProvider');
  }
  return client;
}
```

**app/context/AuthContext.tsx (if auth is present):**

```tsx
import React, {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
} from 'react';
import type { AuthConfig, OAuthToken } from '../../client';

interface AuthState {
  isAuthenticated: boolean;
  isLoading: boolean;
  token: OAuthToken | null;
  error: Error | null;
}

interface AuthContextValue extends AuthState {
  login: () => void;
  logout: () => void;
  handleCallback: (code: string) => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

const STORAGE_KEY = 'auth_token';

export interface AuthProviderProps {
  children: React.ReactNode;
}

export function AuthProvider({ children }: AuthProviderProps) {
  const [state, setState] = useState<AuthState>({
    isAuthenticated: false,
    isLoading: true,
    token: null,
    error: null,
  });

  // Load token from storage on mount
  useEffect(() => {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) {
      try {
        const token = JSON.parse(stored) as OAuthToken;
        // Check if token is expired
        if (!token.expiresAt || token.expiresAt > Date.now()) {
          setState({
            isAuthenticated: true,
            isLoading: false,
            token,
            error: null,
          });
          return;
        }
      } catch {
        localStorage.removeItem(STORAGE_KEY);
      }
    }
    setState((prev) => ({ ...prev, isLoading: false }));
  }, []);

  const login = useCallback(() => {
    // Redirect to OAuth authorization URL
    // This URL should be constructed using OAuth2Manager from client/auth.ts
    window.location.href = '/api/auth/login';
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem(STORAGE_KEY);
    setState({
      isAuthenticated: false,
      isLoading: false,
      token: null,
      error: null,
    });
  }, []);

  const handleCallback = useCallback(async (code: string) => {
    setState((prev) => ({ ...prev, isLoading: true, error: null }));
    try {
      // Exchange code for token
      const response = await fetch('/api/auth/callback', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ code }),
      });
      const token = (await response.json()) as OAuthToken;
      localStorage.setItem(STORAGE_KEY, JSON.stringify(token));
      setState({
        isAuthenticated: true,
        isLoading: false,
        token,
        error: null,
      });
    } catch (err) {
      setState((prev) => ({
        ...prev,
        isLoading: false,
        error: err instanceof Error ? err : new Error(String(err)),
      }));
    }
  }, []);

  return (
    <AuthContext.Provider
      value={{ ...state, login, logout, handleCallback }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
```

**app/context/AuthGuard.tsx:**

```tsx
import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from './AuthContext';
import { LoadingSpinner } from '../../components/shared';

export interface AuthGuardProps {
  children: React.ReactNode;
}

export function AuthGuard({ children }: AuthGuardProps) {
  const { isAuthenticated, isLoading } = useAuth();
  const location = useLocation();

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  return <>{children}</>;
}
```

### Step 3: Generate Custom Hooks

**app/hooks/useResource.ts:**

```tsx
import { useState, useEffect, useCallback } from 'react';

interface UseResourceOptions<T> {
  fetchFn: () => Promise<T>;
  deps?: unknown[];
}

interface UseResourceResult<T> {
  data: T | null;
  loading: boolean;
  error: Error | null;
  refetch: () => Promise<void>;
}

export function useResource<T>({
  fetchFn,
  deps = [],
}: UseResourceOptions<T>): UseResourceResult<T> {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const fetch = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await fetchFn();
      setData(result);
    } catch (err) {
      setError(err instanceof Error ? err : new Error(String(err)));
    } finally {
      setLoading(false);
    }
  }, [fetchFn]);

  useEffect(() => {
    fetch();
  }, [...deps, fetch]);

  return { data, loading, error, refetch: fetch };
}
```

**app/hooks/usePagination.ts:**

```tsx
import { useState, useCallback } from 'react';

interface UsePaginationOptions {
  initialPage?: number;
  initialPageSize?: number;
}

interface UsePaginationResult {
  page: number;
  pageSize: number;
  setPage: (page: number) => void;
  setPageSize: (size: number) => void;
  nextPage: () => void;
  prevPage: () => void;
  reset: () => void;
}

export function usePagination({
  initialPage = 1,
  initialPageSize = 10,
}: UsePaginationOptions = {}): UsePaginationResult {
  const [page, setPage] = useState(initialPage);
  const [pageSize, setPageSize] = useState(initialPageSize);

  const nextPage = useCallback(() => setPage((p) => p + 1), []);
  const prevPage = useCallback(() => setPage((p) => Math.max(1, p - 1)), []);
  const reset = useCallback(() => setPage(initialPage), [initialPage]);

  return { page, pageSize, setPage, setPageSize, nextPage, prevPage, reset };
}
```

### Step 4: Generate Utility Functions

**app/utils/localStorage.ts:**

```typescript
const PREFIX = 'app_';

export const storage = {
  get<T>(key: string, defaultValue: T): T {
    try {
      const item = localStorage.getItem(PREFIX + key);
      return item ? JSON.parse(item) : defaultValue;
    } catch {
      return defaultValue;
    }
  },

  set<T>(key: string, value: T): void {
    try {
      localStorage.setItem(PREFIX + key, JSON.stringify(value));
    } catch {
      // Storage full or unavailable
    }
  },

  remove(key: string): void {
    localStorage.removeItem(PREFIX + key);
  },

  // UI preferences
  getTheme(): 'light' | 'dark' {
    return this.get('theme', 'light');
  },

  setTheme(theme: 'light' | 'dark'): void {
    this.set('theme', theme);
  },

  getSidebarCollapsed(): boolean {
    return this.get('sidebar_collapsed', false);
  },

  setSidebarCollapsed(collapsed: boolean): void {
    this.set('sidebar_collapsed', collapsed);
  },

  getLastVisitedPage(): string | null {
    return this.get('last_page', null);
  },

  setLastVisitedPage(path: string): void {
    this.set('last_page', path);
  },
};
```

### Step 5: Generate Pages

Create pages based on API structure. For a CRUD API:

**app/pages/UsersPage.tsx:**

```tsx
import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import type { User } from '../../client/types';
import { UserList } from '../../components/User';

export function UsersPage() {
  const navigate = useNavigate();

  const handleSelect = (user: User) => {
    navigate(`/users/${user.id}`);
  };

  const handleCreate = () => {
    navigate('/users/new');
  };

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold">Users</h1>
        <button
          onClick={handleCreate}
          className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
        >
          Create User
        </button>
      </div>

      <UserList onSelect={handleSelect} />
    </div>
  );
}
```

**app/pages/UserDetailPage.tsx:**

```tsx
import React from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import type { User } from '../../client/types';
import { UserDetail } from '../../components/User';

export function UserDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  if (!id) {
    return <div>User ID required</div>;
  }

  const handleEdit = (user: User) => {
    navigate(`/users/${user.id}/edit`);
  };

  const handleDelete = () => {
    navigate('/users');
  };

  return (
    <div className="p-6">
      <button
        onClick={() => navigate('/users')}
        className="mb-4 text-blue-600 hover:underline"
      >
        ← Back to Users
      </button>

      <UserDetail userId={id} onEdit={handleEdit} onDelete={handleDelete} />
    </div>
  );
}
```

**app/pages/UserFormPage.tsx:**

```tsx
import React from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import type { User } from '../../client/types';
import { UserForm, UserDetail } from '../../components/User';
import { useResource } from '../hooks/useResource';
import { useApiClient } from '../context/ApiContext';
import { LoadingSpinner, ErrorDisplay } from '../../components/shared';

export function UserFormPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const client = useApiClient();
  const isEditMode = !!id;

  const { data: user, loading, error } = useResource({
    fetchFn: () => (id ? client.getUser(id) : Promise.resolve(null)),
    deps: [id],
  });

  const handleSuccess = (savedUser: User) => {
    navigate(`/users/${savedUser.id}`);
  };

  const handleCancel = () => {
    navigate(id ? `/users/${id}` : '/users');
  };

  if (isEditMode && loading) {
    return <LoadingSpinner className="py-8" />;
  }

  if (isEditMode && error) {
    return <ErrorDisplay error={error} />;
  }

  return (
    <div className="p-6 max-w-2xl">
      <h1 className="text-2xl font-bold mb-6">
        {isEditMode ? 'Edit User' : 'Create User'}
      </h1>

      <UserForm
        user={user || undefined}
        onSuccess={handleSuccess}
        onCancel={handleCancel}
      />
    </div>
  );
}
```

**app/pages/LoginPage.tsx (if auth present):**

```tsx
import React, { useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

export function LoginPage() {
  const { isAuthenticated, isLoading, login, error } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const from = (location.state as { from?: Location })?.from?.pathname || '/';

  useEffect(() => {
    if (isAuthenticated) {
      navigate(from, { replace: true });
    }
  }, [isAuthenticated, navigate, from]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="max-w-md w-full p-8 bg-white rounded-lg shadow">
        <h1 className="text-2xl font-bold text-center mb-6">Sign In</h1>

        {error && (
          <div className="mb-4 p-3 bg-red-50 text-red-700 rounded">
            {error.message}
          </div>
        )}

        <button
          onClick={login}
          disabled={isLoading}
          className="w-full py-3 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
        >
          {isLoading ? 'Signing in...' : 'Sign in with OAuth'}
        </button>
      </div>
    </div>
  );
}
```

### Step 6: Generate App Shell and Routing

**app/App.tsx:**

```tsx
import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { ApiProvider } from './context/ApiContext';
import { AuthProvider, AuthGuard } from './context/AuthContext';
import { Layout } from './Layout';
import { LoginPage } from './pages/LoginPage';
import { UsersPage } from './pages/UsersPage';
import { UserDetailPage } from './pages/UserDetailPage';
import { UserFormPage } from './pages/UserFormPage';
// Import other pages as needed

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:3000';

export function App() {
  return (
    <BrowserRouter>
      <ApiProvider config={{ baseUrl: API_BASE_URL }}>
        <AuthProvider>
          <Routes>
            {/* Public routes */}
            <Route path="/login" element={<LoginPage />} />

            {/* Protected routes */}
            <Route
              path="/"
              element={
                <AuthGuard>
                  <Layout />
                </AuthGuard>
              }
            >
              <Route index element={<Navigate to="/users" replace />} />
              <Route path="users" element={<UsersPage />} />
              <Route path="users/new" element={<UserFormPage />} />
              <Route path="users/:id" element={<UserDetailPage />} />
              <Route path="users/:id/edit" element={<UserFormPage />} />
              {/* Add other resource routes */}
            </Route>

            {/* 404 */}
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </AuthProvider>
      </ApiProvider>
    </BrowserRouter>
  );
}
```

**app/Layout.tsx:**

```tsx
import React, { useState } from 'react';
import { Outlet, Link, useLocation } from 'react-router-dom';
import { useAuth } from './context/AuthContext';
import { storage } from './utils/localStorage';

const NAV_ITEMS = [
  { path: '/users', label: 'Users', icon: '👥' },
  // Add more nav items based on API resources
];

export function Layout() {
  const { logout } = useAuth();
  const location = useLocation();
  const [sidebarCollapsed, setSidebarCollapsed] = useState(
    storage.getSidebarCollapsed()
  );

  const toggleSidebar = () => {
    const newState = !sidebarCollapsed;
    setSidebarCollapsed(newState);
    storage.setSidebarCollapsed(newState);
  };

  return (
    <div className="min-h-screen flex">
      {/* Sidebar */}
      <aside
        className={`bg-gray-800 text-white transition-all ${
          sidebarCollapsed ? 'w-16' : 'w-64'
        }`}
      >
        <div className="p-4 flex items-center justify-between">
          {!sidebarCollapsed && (
            <span className="font-bold text-lg">App Name</span>
          )}
          <button
            onClick={toggleSidebar}
            className="p-2 hover:bg-gray-700 rounded"
          >
            {sidebarCollapsed ? '→' : '←'}
          </button>
        </div>

        <nav className="mt-4">
          {NAV_ITEMS.map((item) => (
            <Link
              key={item.path}
              to={item.path}
              className={`flex items-center px-4 py-3 hover:bg-gray-700 ${
                location.pathname.startsWith(item.path) ? 'bg-gray-700' : ''
              }`}
            >
              <span className="text-xl">{item.icon}</span>
              {!sidebarCollapsed && (
                <span className="ml-3">{item.label}</span>
              )}
            </Link>
          ))}
        </nav>

        <div className="absolute bottom-0 w-full p-4">
          <button
            onClick={logout}
            className="w-full py-2 text-left hover:bg-gray-700 rounded px-2"
          >
            {sidebarCollapsed ? '🚪' : 'Sign Out'}
          </button>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 bg-gray-50 overflow-auto">
        <Outlet />
      </main>
    </div>
  );
}
```

### Step 7: Generate Entry Point

**app/main.tsx:**

```tsx
import React from 'react';
import ReactDOM from 'react-dom/client';
import { App } from './App';
import './index.css';

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
```

**app/index.css:**

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

/* Custom styles */
body {
  @apply bg-gray-50 text-gray-900;
}
```

## UI Style Variations

Based on API purpose, adjust the generated UI:

### Analytics Dashboard

- Summary cards at top with key metrics
- Charts using a library like Recharts or Chart.js
- Date range filters
- Export functionality

### Workflow App

- Multi-step wizards for complex operations
- Status badges and progress indicators
- Timeline views for history
- Action buttons based on current status

### Search-First App

- Prominent search bar
- Faceted filters in sidebar
- Infinite scroll or pagination
- Result cards with key info

## Output Files

| Directory | Contents |
|-----------|----------|
| `app/App.tsx` | Main app with routing |
| `app/Layout.tsx` | App shell with navigation |
| `app/main.tsx` | Entry point |
| `app/pages/` | Page components |
| `app/context/` | API and Auth providers |
| `app/hooks/` | Custom React hooks |
| `app/utils/` | Helper functions |

## Next Steps

After generating the frontend, proceed to:

1. **Generate Tests** — Create unit, integration, and e2e tests
2. **Generate CI** — Create GitHub Actions workflows

See [../generate-tests/SKILL.md](../generate-tests/SKILL.md)
