---
name: openapi-generate-client
description: Generate a TypeScript API client from an OpenAPI specification. Creates types, API class, and auth handlers.
license: MIT
compatibility: Requires Node.js 18+, TypeScript 5+
triggers:
  - openapi client
  - generate typescript client
  - openapi to typescript
  - api client from spec
---

Generate a TypeScript API client from an OpenAPI specification.

## Overview

This skill produces a complete TypeScript client layer:

- `client/types.ts` — TypeScript interfaces/types for every schema
- `client/api.ts` — A class with one async method per API endpoint
- `client/auth.ts` — Auth configuration based on securitySchemes
- `client/index.ts` — Barrel export

## Prerequisites

- OpenAPI 3.0+ specification (JSON or YAML)
- Node.js 18+ with npm
- TypeScript 5+

## Workflow

### Step 1: Parse the OpenAPI Spec

Run the parse script to extract structured data:

```bash
python scripts/parse-openapi.py path/to/openapi.yaml > .generated/spec-summary.json
```

This outputs:
- All schemas with field names, types, and constraints
- All endpoints with methods, parameters, and responses
- All security schemes with their configuration

### Step 2: Generate types.ts

For each schema in `components/schemas`, create a TypeScript interface:

**Mapping Rules:**

| OpenAPI Type | TypeScript Type |
|--------------|-----------------|
| `string` | `string` |
| `string` (format: date-time) | `string` (ISO 8601) |
| `string` (format: date) | `string` (YYYY-MM-DD) |
| `string` (format: email) | `string` |
| `string` (format: uuid) | `string` |
| `string` (format: binary) | `Blob` |
| `integer` | `number` |
| `number` | `number` |
| `boolean` | `boolean` |
| `array` | `T[]` |
| `object` | Nested interface or `Record<string, unknown>` |
| `$ref` | Import reference to another interface |
| `enum` | Union type (`'a' \| 'b' \| 'c'`) or TypeScript `enum` |
| `oneOf` | Union type |
| `anyOf` | Union type |
| `allOf` | Intersection type (`A & B`) |
| `nullable: true` | `T \| null` |

**Field naming:** Convert `snake_case` to `camelCase`.

**Required fields:** Mark non-required fields as optional with `?`.

**Example output:**

```typescript
// client/types.ts

export interface User {
  id: string;
  email: string;
  firstName: string;
  lastName: string;
  role: UserRole;
  createdAt: string;
  updatedAt?: string;
}

export type UserRole = 'admin' | 'user' | 'guest';

export interface CreateUserRequest {
  email: string;
  firstName: string;
  lastName: string;
  password: string;
  role?: UserRole;
}

export interface UpdateUserRequest {
  firstName?: string;
  lastName?: string;
  role?: UserRole;
}

export interface UserListResponse {
  items: User[];
  total: number;
  page: number;
  pageSize: number;
}
```

### Step 3: Generate api.ts

Create an API class with methods for each endpoint:

**Method naming:**

| HTTP Method | Path Pattern | Method Name |
|-------------|--------------|-------------|
| GET | `/resources` | `listResources()` |
| GET | `/resources/{id}` | `getResource(id)` |
| POST | `/resources` | `createResource(data)` |
| PUT | `/resources/{id}` | `updateResource(id, data)` |
| PATCH | `/resources/{id}` | `patchResource(id, data)` |
| DELETE | `/resources/{id}` | `deleteResource(id)` |
| POST | `/resources/{id}/action` | `actionResource(id)` |

**Parameters:**

- Path parameters → method arguments (typed)
- Query parameters → optional `params` object
- Request body → `data` argument (typed to request schema)
- Headers → handled internally (content-type, auth)

**Return type:** `Promise<ResponseType>` based on response schema.

**Example output:**

```typescript
// client/api.ts

import type {
  User,
  CreateUserRequest,
  UpdateUserRequest,
  UserListResponse,
} from './types';
import { AuthConfig, attachAuth } from './auth';

export interface ApiConfig {
  baseUrl: string;
  auth?: AuthConfig;
}

export interface ListUsersParams {
  page?: number;
  pageSize?: number;
  search?: string;
}

export class ApiClient {
  private baseUrl: string;
  private auth?: AuthConfig;

  constructor(config: ApiConfig) {
    this.baseUrl = config.baseUrl.replace(/\/$/, '');
    this.auth = config.auth;
  }

  private async request<T>(
    method: string,
    path: string,
    options: {
      params?: Record<string, string | number | boolean | undefined>;
      body?: unknown;
    } = {}
  ): Promise<T> {
    const url = new URL(path, this.baseUrl);
    if (options.params) {
      Object.entries(options.params).forEach(([key, value]) => {
        if (value !== undefined) {
          url.searchParams.set(key, String(value));
        }
      });
    }

    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };

    if (this.auth) {
      attachAuth(headers, url, this.auth);
    }

    const response = await fetch(url.toString(), {
      method,
      headers,
      body: options.body ? JSON.stringify(options.body) : undefined,
    });

    if (!response.ok) {
      throw new ApiError(response.status, await response.text());
    }

    return response.json();
  }

  // User endpoints
  async listUsers(params?: ListUsersParams): Promise<UserListResponse> {
    return this.request('GET', '/users', { params });
  }

  async getUser(id: string): Promise<User> {
    return this.request('GET', `/users/${id}`);
  }

  async createUser(data: CreateUserRequest): Promise<User> {
    return this.request('POST', '/users', { body: data });
  }

  async updateUser(id: string, data: UpdateUserRequest): Promise<User> {
    return this.request('PUT', `/users/${id}`, { body: data });
  }

  async deleteUser(id: string): Promise<void> {
    return this.request('DELETE', `/users/${id}`);
  }
}

export class ApiError extends Error {
  constructor(
    public status: number,
    public body: string
  ) {
    super(`API Error ${status}: ${body}`);
    this.name = 'ApiError';
  }
}
```

### Step 4: Generate auth.ts

Based on `components/securitySchemes`, generate auth handlers:

**API Key:**

```typescript
export interface ApiKeyAuth {
  type: 'apiKey';
  key: string;
  location: 'header' | 'query';
  name: string; // e.g., 'X-API-Key' or 'api_key'
}
```

**Bearer Token:**

```typescript
export interface BearerAuth {
  type: 'bearer';
  token: string;
}
```

**OAuth2:**

```typescript
export interface OAuth2Auth {
  type: 'oauth2';
  clientId: string;
  redirectUri: string;
  scopes: string[];
  authorizationUrl: string;
  tokenUrl: string;
  token?: OAuthToken;
}

export interface OAuthToken {
  accessToken: string;
  refreshToken?: string;
  expiresAt?: number;
}
```

**Example output:**

```typescript
// client/auth.ts

export type AuthConfig = ApiKeyAuth | BearerAuth | OAuth2Auth;

export interface ApiKeyAuth {
  type: 'apiKey';
  key: string;
  location: 'header' | 'query';
  name: string;
}

export interface BearerAuth {
  type: 'bearer';
  token: string;
}

export interface OAuth2Auth {
  type: 'oauth2';
  clientId: string;
  redirectUri: string;
  scopes: string[];
  authorizationUrl: string;
  tokenUrl: string;
  token?: OAuthToken;
}

export interface OAuthToken {
  accessToken: string;
  refreshToken?: string;
  expiresAt?: number;
}

export function attachAuth(
  headers: Record<string, string>,
  url: URL,
  auth: AuthConfig
): void {
  switch (auth.type) {
    case 'apiKey':
      if (auth.location === 'header') {
        headers[auth.name] = auth.key;
      } else {
        url.searchParams.set(auth.name, auth.key);
      }
      break;
    case 'bearer':
      headers['Authorization'] = `Bearer ${auth.token}`;
      break;
    case 'oauth2':
      if (auth.token?.accessToken) {
        headers['Authorization'] = `Bearer ${auth.token.accessToken}`;
      }
      break;
  }
}

// OAuth2 helpers (only generated if OAuth2 is used)
export class OAuth2Manager {
  private config: OAuth2Auth;
  private codeVerifier?: string;

  constructor(config: Omit<OAuth2Auth, 'type' | 'token'>) {
    this.config = { ...config, type: 'oauth2' };
  }

  getAuthorizationUrl(): string {
    this.codeVerifier = this.generateCodeVerifier();
    const codeChallenge = this.generateCodeChallenge(this.codeVerifier);

    const url = new URL(this.config.authorizationUrl);
    url.searchParams.set('client_id', this.config.clientId);
    url.searchParams.set('redirect_uri', this.config.redirectUri);
    url.searchParams.set('response_type', 'code');
    url.searchParams.set('scope', this.config.scopes.join(' '));
    url.searchParams.set('code_challenge', codeChallenge);
    url.searchParams.set('code_challenge_method', 'S256');

    return url.toString();
  }

  async exchangeCode(code: string): Promise<OAuthToken> {
    const response = await fetch(this.config.tokenUrl, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: new URLSearchParams({
        grant_type: 'authorization_code',
        client_id: this.config.clientId,
        redirect_uri: this.config.redirectUri,
        code,
        code_verifier: this.codeVerifier || '',
      }),
    });

    const data = await response.json();
    return {
      accessToken: data.access_token,
      refreshToken: data.refresh_token,
      expiresAt: data.expires_in
        ? Date.now() + data.expires_in * 1000
        : undefined,
    };
  }

  async refreshToken(token: OAuthToken): Promise<OAuthToken> {
    if (!token.refreshToken) {
      throw new Error('No refresh token available');
    }

    const response = await fetch(this.config.tokenUrl, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: new URLSearchParams({
        grant_type: 'refresh_token',
        client_id: this.config.clientId,
        refresh_token: token.refreshToken,
      }),
    });

    const data = await response.json();
    return {
      accessToken: data.access_token,
      refreshToken: data.refresh_token || token.refreshToken,
      expiresAt: data.expires_in
        ? Date.now() + data.expires_in * 1000
        : undefined,
    };
  }

  private generateCodeVerifier(): string {
    const array = new Uint8Array(32);
    crypto.getRandomValues(array);
    return btoa(String.fromCharCode(...array))
      .replace(/\+/g, '-')
      .replace(/\//g, '_')
      .replace(/=/g, '');
  }

  private generateCodeChallenge(verifier: string): string {
    const encoder = new TextEncoder();
    const data = encoder.encode(verifier);
    return crypto.subtle
      .digest('SHA-256', data)
      .then((hash) =>
        btoa(String.fromCharCode(...new Uint8Array(hash)))
          .replace(/\+/g, '-')
          .replace(/\//g, '_')
          .replace(/=/g, '')
      ) as unknown as string;
  }
}
```

### Step 5: Generate index.ts

Create a barrel export:

```typescript
// client/index.ts

export * from './types';
export * from './api';
export * from './auth';
```

### Step 6: Verify Output

Run the verification scripts:

```bash
# Lint the generated code
./scripts/lint-generated.sh

# Verify coverage against spec
python scripts/verify-coverage.py openapi.yaml client/
```

## Output Files

| File | Contents |
|------|----------|
| `client/types.ts` | TypeScript interfaces for all schemas |
| `client/api.ts` | API client class with typed methods |
| `client/auth.ts` | Auth config types and helpers |
| `client/index.ts` | Barrel export |

## Next Steps

After generating the client, proceed to:

1. **Generate Components** — Create React components using the client
2. **Generate Tests** — Create unit tests for the client

See [../generate-components/SKILL.md](../generate-components/SKILL.md)
