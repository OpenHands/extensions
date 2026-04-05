---
name: openapi-generate-tests
description: Generate comprehensive tests for the TypeScript client, React components, and frontend app. Includes unit, integration, and e2e tests.
license: MIT
compatibility: Requires Vitest or Jest, React Testing Library, Playwright
triggers:
  - openapi tests
  - generate tests
  - api tests
  - frontend tests
  - e2e tests
---

Generate comprehensive tests for the generated codebase.

## Overview

This skill produces three layers of tests:

- `tests/unit/` — Unit tests for client methods and components
- `tests/integration/` — Integration tests for component↔client flows
- `tests/e2e/` — End-to-end tests (assumes running backend)
- `tests/setup/` — Test configuration, fixtures, and mock factories

## Prerequisites

- Generated TypeScript client, components, and frontend
- Node.js 18+
- Test runner (Vitest recommended, Jest supported)
- React Testing Library
- Playwright for e2e

## Workflow

### Step 1: Set Up Test Infrastructure

**tests/setup/vitest.config.ts:**

```typescript
import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    setupFiles: ['./tests/setup/setupTests.ts'],
    globals: true,
    coverage: {
      provider: 'v8',
      reporter: ['text', 'html', 'lcov'],
      include: ['client/**/*.ts', 'components/**/*.tsx', 'app/**/*.tsx'],
    },
  },
});
```

**tests/setup/setupTests.ts:**

```typescript
import '@testing-library/jest-dom';
import { afterEach } from 'vitest';
import { cleanup } from '@testing-library/react';

// Cleanup after each test
afterEach(() => {
  cleanup();
});

// Mock fetch globally
global.fetch = vi.fn();

// Mock localStorage
const localStorageMock = {
  store: {} as Record<string, string>,
  getItem: vi.fn((key: string) => localStorageMock.store[key] || null),
  setItem: vi.fn((key: string, value: string) => {
    localStorageMock.store[key] = value;
  }),
  removeItem: vi.fn((key: string) => {
    delete localStorageMock.store[key];
  }),
  clear: vi.fn(() => {
    localStorageMock.store = {};
  }),
};
Object.defineProperty(window, 'localStorage', { value: localStorageMock });
```

### Step 2: Generate Mock Factories

For each schema, generate a factory function that produces valid test data.

**tests/setup/factories.ts:**

```typescript
import type {
  User,
  CreateUserRequest,
  UpdateUserRequest,
  UserRole,
  UserListResponse,
} from '../../client/types';

let idCounter = 0;

export function makeUser(overrides: Partial<User> = {}): User {
  idCounter++;
  return {
    id: `user-${idCounter}`,
    email: `user${idCounter}@example.com`,
    firstName: `FirstName${idCounter}`,
    lastName: `LastName${idCounter}`,
    role: 'user' as UserRole,
    createdAt: new Date().toISOString(),
    ...overrides,
  };
}

export function makeCreateUserRequest(
  overrides: Partial<CreateUserRequest> = {}
): CreateUserRequest {
  idCounter++;
  return {
    email: `newuser${idCounter}@example.com`,
    firstName: `NewFirst${idCounter}`,
    lastName: `NewLast${idCounter}`,
    password: 'SecurePassword123!',
    role: 'user',
    ...overrides,
  };
}

export function makeUpdateUserRequest(
  overrides: Partial<UpdateUserRequest> = {}
): UpdateUserRequest {
  return {
    firstName: 'UpdatedFirst',
    lastName: 'UpdatedLast',
    ...overrides,
  };
}

export function makeUserListResponse(
  users: User[] = [],
  total?: number
): UserListResponse {
  return {
    items: users,
    total: total ?? users.length,
    page: 1,
    pageSize: 10,
  };
}

// Reset counter between test files
export function resetFactories(): void {
  idCounter = 0;
}
```

### Step 3: Generate Type Guards

For each schema, generate runtime type checking for tests.

**tests/setup/typeGuards.ts:**

```typescript
import type { User, UserRole } from '../../client/types';

const USER_ROLES: UserRole[] = ['admin', 'user', 'guest'];

export function isUser(value: unknown): value is User {
  if (!value || typeof value !== 'object') return false;
  const obj = value as Record<string, unknown>;

  return (
    typeof obj.id === 'string' &&
    typeof obj.email === 'string' &&
    typeof obj.firstName === 'string' &&
    typeof obj.lastName === 'string' &&
    typeof obj.role === 'string' &&
    USER_ROLES.includes(obj.role as UserRole) &&
    typeof obj.createdAt === 'string' &&
    (obj.updatedAt === undefined || typeof obj.updatedAt === 'string')
  );
}

export function isUserListResponse(value: unknown): value is {
  items: User[];
  total: number;
  page: number;
  pageSize: number;
} {
  if (!value || typeof value !== 'object') return false;
  const obj = value as Record<string, unknown>;

  return (
    Array.isArray(obj.items) &&
    obj.items.every(isUser) &&
    typeof obj.total === 'number' &&
    typeof obj.page === 'number' &&
    typeof obj.pageSize === 'number'
  );
}
```

### Step 4: Generate Unit Tests

#### Client Method Tests

**tests/unit/client/api.test.ts:**

```typescript
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { ApiClient, ApiError } from '../../../client/api';
import { makeUser, makeCreateUserRequest, makeUserListResponse } from '../../setup/factories';

describe('ApiClient', () => {
  let client: ApiClient;
  const mockFetch = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    global.fetch = mockFetch;
    client = new ApiClient({ baseUrl: 'https://api.example.com' });
  });

  describe('listUsers', () => {
    it('should fetch users with pagination', async () => {
      const users = [makeUser(), makeUser()];
      const response = makeUserListResponse(users, 100);

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(response),
      });

      const result = await client.listUsers({ page: 1, pageSize: 10 });

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/users'),
        expect.objectContaining({ method: 'GET' })
      );
      expect(result.items).toHaveLength(2);
      expect(result.total).toBe(100);
    });

    it('should include search parameter when provided', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(makeUserListResponse([])),
      });

      await client.listUsers({ search: 'john' });

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('search=john'),
        expect.any(Object)
      );
    });
  });

  describe('getUser', () => {
    it('should fetch a single user by ID', async () => {
      const user = makeUser({ id: 'user-123' });

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(user),
      });

      const result = await client.getUser('user-123');

      expect(mockFetch).toHaveBeenCalledWith(
        'https://api.example.com/users/user-123',
        expect.objectContaining({ method: 'GET' })
      );
      expect(result.id).toBe('user-123');
    });

    it('should throw ApiError on 404', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 404,
        text: () => Promise.resolve('Not found'),
      });

      await expect(client.getUser('nonexistent')).rejects.toThrow(ApiError);
    });
  });

  describe('createUser', () => {
    it('should send POST request with user data', async () => {
      const createData = makeCreateUserRequest();
      const createdUser = makeUser({ email: createData.email });

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(createdUser),
      });

      const result = await client.createUser(createData);

      expect(mockFetch).toHaveBeenCalledWith(
        'https://api.example.com/users',
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify(createData),
        })
      );
      expect(result.email).toBe(createData.email);
    });
  });

  describe('updateUser', () => {
    it('should send PUT request with update data', async () => {
      const user = makeUser();
      const updateData = { firstName: 'Updated' };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ ...user, ...updateData }),
      });

      const result = await client.updateUser(user.id, updateData);

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining(`/users/${user.id}`),
        expect.objectContaining({
          method: 'PUT',
          body: JSON.stringify(updateData),
        })
      );
      expect(result.firstName).toBe('Updated');
    });
  });

  describe('deleteUser', () => {
    it('should send DELETE request', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(undefined),
      });

      await client.deleteUser('user-123');

      expect(mockFetch).toHaveBeenCalledWith(
        'https://api.example.com/users/user-123',
        expect.objectContaining({ method: 'DELETE' })
      );
    });
  });
});
```

#### Type Guard Tests

**tests/unit/client/typeGuards.test.ts:**

```typescript
import { describe, it, expect } from 'vitest';
import { isUser, isUserListResponse } from '../../setup/typeGuards';
import { makeUser, makeUserListResponse } from '../../setup/factories';

describe('Type Guards', () => {
  describe('isUser', () => {
    it('should return true for valid user', () => {
      expect(isUser(makeUser())).toBe(true);
    });

    it('should return false for null', () => {
      expect(isUser(null)).toBe(false);
    });

    it('should return false for missing required fields', () => {
      expect(isUser({ id: '123' })).toBe(false);
    });

    it('should return false for invalid role', () => {
      const user = makeUser();
      expect(isUser({ ...user, role: 'invalid' })).toBe(false);
    });

    it('should accept optional updatedAt', () => {
      const user = makeUser({ updatedAt: new Date().toISOString() });
      expect(isUser(user)).toBe(true);
    });
  });

  describe('isUserListResponse', () => {
    it('should return true for valid response', () => {
      const response = makeUserListResponse([makeUser()]);
      expect(isUserListResponse(response)).toBe(true);
    });

    it('should return false for invalid items', () => {
      expect(isUserListResponse({ items: [{ invalid: true }] })).toBe(false);
    });
  });
});
```

#### Component Unit Tests

**tests/unit/components/UserForm.test.tsx:**

```tsx
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { UserForm } from '../../../components/User/UserForm';
import { ApiProvider } from '../../../app/context/ApiContext';
import { makeUser } from '../../setup/factories';

// Mock the API client
const mockClient = {
  createUser: vi.fn(),
  updateUser: vi.fn(),
};

const wrapper = ({ children }: { children: React.ReactNode }) => (
  <ApiProvider config={{ baseUrl: 'http://test' }}>
    {children}
  </ApiProvider>
);

// Override useApiClient to return mock
vi.mock('../../../app/context/ApiContext', async () => {
  const actual = await vi.importActual('../../../app/context/ApiContext');
  return {
    ...actual,
    useApiClient: () => mockClient,
  };
});

describe('UserForm', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Create mode', () => {
    it('should render empty form', () => {
      render(<UserForm />, { wrapper });

      expect(screen.getByLabelText(/email/i)).toHaveValue('');
      expect(screen.getByLabelText(/first name/i)).toHaveValue('');
      expect(screen.getByLabelText(/password/i)).toBeInTheDocument();
    });

    it('should show Create User button', () => {
      render(<UserForm />, { wrapper });

      expect(screen.getByRole('button', { name: /create user/i })).toBeInTheDocument();
    });

    it('should call createUser on submit', async () => {
      const user = userEvent.setup();
      const newUser = makeUser();
      mockClient.createUser.mockResolvedValueOnce(newUser);

      render(<UserForm />, { wrapper });

      await user.type(screen.getByLabelText(/email/i), 'test@example.com');
      await user.type(screen.getByLabelText(/first name/i), 'Test');
      await user.type(screen.getByLabelText(/last name/i), 'User');
      await user.type(screen.getByLabelText(/password/i), 'password123');
      await user.click(screen.getByRole('button', { name: /create user/i }));

      await waitFor(() => {
        expect(mockClient.createUser).toHaveBeenCalledWith(
          expect.objectContaining({
            email: 'test@example.com',
            firstName: 'Test',
            lastName: 'User',
          })
        );
      });
    });
  });

  describe('Edit mode', () => {
    it('should populate form with user data', () => {
      const user = makeUser({ firstName: 'John', lastName: 'Doe' });
      render(<UserForm user={user} />, { wrapper });

      expect(screen.getByLabelText(/first name/i)).toHaveValue('John');
      expect(screen.getByLabelText(/last name/i)).toHaveValue('Doe');
    });

    it('should disable email field in edit mode', () => {
      const user = makeUser();
      render(<UserForm user={user} />, { wrapper });

      expect(screen.getByLabelText(/email/i)).toBeDisabled();
    });

    it('should hide password field in edit mode', () => {
      const user = makeUser();
      render(<UserForm user={user} />, { wrapper });

      expect(screen.queryByLabelText(/password/i)).not.toBeInTheDocument();
    });

    it('should show Update User button', () => {
      const user = makeUser();
      render(<UserForm user={user} />, { wrapper });

      expect(screen.getByRole('button', { name: /update user/i })).toBeInTheDocument();
    });
  });

  describe('Error handling', () => {
    it('should display error message on API failure', async () => {
      const user = userEvent.setup();
      mockClient.createUser.mockRejectedValueOnce(new Error('Server error'));

      render(<UserForm />, { wrapper });

      await user.type(screen.getByLabelText(/email/i), 'test@example.com');
      await user.type(screen.getByLabelText(/first name/i), 'Test');
      await user.type(screen.getByLabelText(/last name/i), 'User');
      await user.type(screen.getByLabelText(/password/i), 'password123');
      await user.click(screen.getByRole('button', { name: /create user/i }));

      await waitFor(() => {
        expect(screen.getByText(/server error/i)).toBeInTheDocument();
      });
    });
  });
});
```

### Step 5: Generate Integration Tests

**tests/integration/UserFlow.test.tsx:**

```tsx
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { ApiProvider } from '../../app/context/ApiContext';
import { UsersPage } from '../../app/pages/UsersPage';
import { UserDetailPage } from '../../app/pages/UserDetailPage';
import { UserFormPage } from '../../app/pages/UserFormPage';
import { makeUser, makeUserListResponse } from '../setup/factories';

const mockClient = {
  listUsers: vi.fn(),
  getUser: vi.fn(),
  createUser: vi.fn(),
  updateUser: vi.fn(),
  deleteUser: vi.fn(),
};

vi.mock('../../app/context/ApiContext', async () => {
  const actual = await vi.importActual('../../app/context/ApiContext');
  return {
    ...actual,
    useApiClient: () => mockClient,
  };
});

const renderWithRouter = (initialRoute: string) => {
  return render(
    <MemoryRouter initialEntries={[initialRoute]}>
      <ApiProvider config={{ baseUrl: 'http://test' }}>
        <Routes>
          <Route path="/users" element={<UsersPage />} />
          <Route path="/users/new" element={<UserFormPage />} />
          <Route path="/users/:id" element={<UserDetailPage />} />
          <Route path="/users/:id/edit" element={<UserFormPage />} />
        </Routes>
      </ApiProvider>
    </MemoryRouter>
  );
};

describe('User Flow Integration', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should navigate from list to detail view', async () => {
    const users = [makeUser({ id: 'user-1', firstName: 'John' })];
    mockClient.listUsers.mockResolvedValue(makeUserListResponse(users));
    mockClient.getUser.mockResolvedValue(users[0]);

    const user = userEvent.setup();
    renderWithRouter('/users');

    await waitFor(() => {
      expect(screen.getByText('John')).toBeInTheDocument();
    });

    await user.click(screen.getByText('John'));

    await waitFor(() => {
      expect(mockClient.getUser).toHaveBeenCalledWith('user-1');
    });
  });

  it('should create a new user and navigate to detail', async () => {
    const newUser = makeUser({ id: 'new-user' });
    mockClient.createUser.mockResolvedValue(newUser);

    const user = userEvent.setup();
    renderWithRouter('/users/new');

    await user.type(screen.getByLabelText(/email/i), 'new@example.com');
    await user.type(screen.getByLabelText(/first name/i), 'New');
    await user.type(screen.getByLabelText(/last name/i), 'User');
    await user.type(screen.getByLabelText(/password/i), 'password123');
    await user.click(screen.getByRole('button', { name: /create/i }));

    await waitFor(() => {
      expect(mockClient.createUser).toHaveBeenCalled();
    });
  });

  it('should delete user and return to list', async () => {
    const user = makeUser({ id: 'user-to-delete' });
    mockClient.getUser.mockResolvedValue(user);
    mockClient.deleteUser.mockResolvedValue(undefined);

    // Mock window.confirm
    vi.spyOn(window, 'confirm').mockReturnValue(true);

    const userAction = userEvent.setup();
    renderWithRouter('/users/user-to-delete');

    await waitFor(() => {
      expect(screen.getByText(user.firstName)).toBeInTheDocument();
    });

    await userAction.click(screen.getByRole('button', { name: /delete/i }));

    await waitFor(() => {
      expect(mockClient.deleteUser).toHaveBeenCalledWith('user-to-delete');
    });
  });
});
```

### Step 6: Generate E2E Tests

**tests/e2e/playwright.config.ts:**

```typescript
import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './tests/e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: 'html',
  use: {
    baseURL: process.env.E2E_BASE_URL || 'http://localhost:5173',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
  },
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
    { name: 'firefox', use: { ...devices['Desktop Firefox'] } },
  ],
  webServer: {
    command: 'npm run dev',
    url: 'http://localhost:5173',
    reuseExistingServer: !process.env.CI,
  },
});
```

**tests/e2e/smoke.spec.ts:**

```typescript
import { test, expect } from '@playwright/test';

test.describe('Smoke Tests', () => {
  test('homepage loads', async ({ page }) => {
    await page.goto('/');
    await expect(page).toHaveTitle(/App/);
  });

  test('users page loads', async ({ page }) => {
    await page.goto('/users');
    await expect(page.getByRole('heading', { name: /users/i })).toBeVisible();
  });

  test('no console errors on main pages', async ({ page }) => {
    const errors: string[] = [];
    page.on('console', (msg) => {
      if (msg.type() === 'error') {
        errors.push(msg.text());
      }
    });

    await page.goto('/users');
    await page.waitForLoadState('networkidle');

    expect(errors).toHaveLength(0);
  });
});
```

**tests/e2e/users.spec.ts:**

```typescript
import { test, expect } from '@playwright/test';

test.describe('User Management', () => {
  test.beforeEach(async ({ page }) => {
    // Login if auth is required
    // await page.goto('/login');
    // await page.fill('[name="email"]', 'test@example.com');
    // ...
  });

  test('can view user list', async ({ page }) => {
    await page.goto('/users');

    await expect(page.getByRole('table')).toBeVisible();
    // Or check for at least one user row
    await expect(page.locator('tbody tr').first()).toBeVisible();
  });

  test('can create a new user', async ({ page }) => {
    await page.goto('/users');
    await page.click('text=Create User');

    await page.fill('[name="email"]', `test-${Date.now()}@example.com`);
    await page.fill('[name="firstName"]', 'E2E');
    await page.fill('[name="lastName"]', 'TestUser');
    await page.fill('[name="password"]', 'SecurePass123!');
    await page.click('button[type="submit"]');

    // Should navigate to detail page
    await expect(page.getByText('E2E TestUser')).toBeVisible();
  });

  test('can edit a user', async ({ page }) => {
    // First, get an existing user
    await page.goto('/users');
    await page.locator('tbody tr').first().click();

    // Click edit
    await page.click('text=Edit');

    // Update name
    await page.fill('[name="firstName"]', 'UpdatedName');
    await page.click('button[type="submit"]');

    // Verify update
    await expect(page.getByText('UpdatedName')).toBeVisible();
  });

  test('can delete a user', async ({ page }) => {
    await page.goto('/users');

    // Get user count before
    const countBefore = await page.locator('tbody tr').count();

    // Click first user
    await page.locator('tbody tr').first().click();

    // Delete
    page.on('dialog', (dialog) => dialog.accept());
    await page.click('text=Delete');

    // Should be back on list
    await expect(page).toHaveURL('/users');

    // Count should decrease
    const countAfter = await page.locator('tbody tr').count();
    expect(countAfter).toBeLessThan(countBefore);
  });

  test('handles validation errors', async ({ page }) => {
    await page.goto('/users/new');

    // Submit empty form
    await page.click('button[type="submit"]');

    // Should show validation
    await expect(page.locator('[name="email"]:invalid')).toBeVisible();
  });

  test('handles API errors gracefully', async ({ page }) => {
    // Navigate to non-existent user
    await page.goto('/users/nonexistent-id');

    // Should show error
    await expect(page.getByText(/error|not found/i)).toBeVisible();
  });
});
```

**tests/e2e/auth.spec.ts (if auth present):**

```typescript
import { test, expect } from '@playwright/test';

test.describe('Authentication', () => {
  test('redirects to login when not authenticated', async ({ page }) => {
    await page.goto('/users');
    await expect(page).toHaveURL(/\/login/);
  });

  test('can log in', async ({ page }) => {
    await page.goto('/login');
    await page.click('text=Sign in');

    // Handle OAuth redirect (mock or real)
    // ...

    await expect(page).toHaveURL('/');
  });

  test('can log out', async ({ page }) => {
    // Assume logged in
    await page.goto('/');
    await page.click('text=Sign Out');

    await expect(page).toHaveURL(/\/login/);
  });

  test('protected routes require auth', async ({ page }) => {
    // Clear any auth
    await page.evaluate(() => localStorage.clear());

    await page.goto('/users');
    await expect(page).toHaveURL(/\/login/);
  });
});
```

### Step 7: Generate E2E Backend Startup Script

**tests/e2e/start-server.sh:**

```bash
#!/bin/bash
# E2E Backend Startup Script
# Auto-generated based on detected backend type

set -e

echo "Starting backend for e2e tests..."

# Strategy: Docker Compose (if available)
if [ -f "docker-compose.yml" ] || [ -f "../docker-compose.yml" ]; then
    echo "Using Docker Compose..."
    docker compose up -d
    
    # Wait for health check
    for i in {1..30}; do
        if curl -s http://localhost:3000/health > /dev/null; then
            echo "Backend ready!"
            exit 0
        fi
        echo "Waiting for backend... ($i/30)"
        sleep 2
    done
    echo "Backend failed to start"
    exit 1
fi

# Strategy: Node.js backend
if [ -f "package.json" ] && grep -q '"start"' package.json; then
    echo "Using npm start..."
    npm start &
    SERVER_PID=$!
    
    # Wait for server
    for i in {1..30}; do
        if curl -s http://localhost:3000 > /dev/null; then
            echo "Backend ready! (PID: $SERVER_PID)"
            exit 0
        fi
        sleep 1
    done
    exit 1
fi

# Strategy: Python Django
if [ -f "manage.py" ]; then
    echo "Using Django runserver..."
    python manage.py runserver 0.0.0.0:3000 &
    sleep 5
    exit 0
fi

# Strategy: Mock server with Prism
if command -v prism &> /dev/null; then
    echo "Using Prism mock server..."
    prism mock openapi.yaml --port 3000 &
    sleep 3
    exit 0
fi

# Fallback: Check E2E_BASE_URL
if [ -n "$E2E_BASE_URL" ]; then
    echo "Using external backend at $E2E_BASE_URL"
    exit 0
fi

echo "No backend startup method found!"
echo "Please set E2E_BASE_URL or add a docker-compose.yml"
exit 1
```

## Test Scripts in package.json

```json
{
  "scripts": {
    "test": "vitest",
    "test:unit": "vitest run tests/unit",
    "test:integration": "vitest run tests/integration",
    "test:coverage": "vitest run --coverage",
    "test:e2e": "playwright test",
    "test:e2e:ui": "playwright test --ui"
  }
}
```

## Output Files

| Directory | Contents |
|-----------|----------|
| `tests/setup/` | Config, factories, type guards |
| `tests/unit/client/` | API client tests |
| `tests/unit/components/` | Component tests |
| `tests/integration/` | Flow tests |
| `tests/e2e/` | Playwright tests |

## Next Steps

After generating tests, proceed to:

1. **Generate CI** — Create GitHub Actions to run these tests

See [../generate-ci/SKILL.md](../generate-ci/SKILL.md)
