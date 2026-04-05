# Auth Patterns Reference

This document describes how to handle different authentication methods found in OpenAPI specs.

## Detecting Auth Type

Read `components/securitySchemes` in the OpenAPI spec:

```yaml
components:
  securitySchemes:
    ApiKeyAuth:
      type: apiKey
      in: header
      name: X-API-Key
    BearerAuth:
      type: http
      scheme: bearer
    OAuth2:
      type: oauth2
      flows:
        authorizationCode:
          authorizationUrl: https://auth.example.com/authorize
          tokenUrl: https://auth.example.com/token
          scopes:
            read: Read access
            write: Write access
```

## Pattern 1: API Key

### Detection

```yaml
securitySchemes:
  ApiKeyAuth:
    type: apiKey
    in: header  # or "query"
    name: X-API-Key  # header/query param name
```

### Client Implementation

```typescript
export interface ApiKeyAuth {
  type: 'apiKey';
  key: string;
  location: 'header' | 'query';
  name: string;
}

export function attachApiKey(
  headers: Record<string, string>,
  url: URL,
  auth: ApiKeyAuth
): void {
  if (auth.location === 'header') {
    headers[auth.name] = auth.key;
  } else {
    url.searchParams.set(auth.name, auth.key);
  }
}
```

### Client Constructor

```typescript
const client = new ApiClient({
  baseUrl: 'https://api.example.com',
  auth: {
    type: 'apiKey',
    key: 'your-api-key',
    location: 'header',
    name: 'X-API-Key',
  },
});
```

### Frontend UI

- Settings page with API key input
- Store key in localStorage
- No login flow required

```tsx
function ApiKeySettings() {
  const [key, setKey] = useState(localStorage.getItem('api_key') || '');

  const handleSave = () => {
    localStorage.setItem('api_key', key);
    // Reinitialize API client
  };

  return (
    <div>
      <label>API Key</label>
      <input
        type="password"
        value={key}
        onChange={(e) => setKey(e.target.value)}
      />
      <button onClick={handleSave}>Save</button>
    </div>
  );
}
```

---

## Pattern 2: Bearer Token

### Detection

```yaml
securitySchemes:
  BearerAuth:
    type: http
    scheme: bearer
    bearerFormat: JWT  # optional
```

### Client Implementation

```typescript
export interface BearerAuth {
  type: 'bearer';
  token: string;
}

export function attachBearer(
  headers: Record<string, string>,
  auth: BearerAuth
): void {
  headers['Authorization'] = `Bearer ${auth.token}`;
}
```

### Client Constructor

```typescript
const client = new ApiClient({
  baseUrl: 'https://api.example.com',
  auth: {
    type: 'bearer',
    token: 'your-jwt-token',
  },
});
```

### Frontend UI

Two approaches based on how tokens are obtained:

#### Option A: Token Input

If tokens are externally issued (e.g., service accounts):

```tsx
function TokenSettings() {
  const [token, setToken] = useState('');

  return (
    <div>
      <label>Access Token</label>
      <textarea value={token} onChange={(e) => setToken(e.target.value)} />
      <button onClick={() => localStorage.setItem('token', token)}>
        Save
      </button>
    </div>
  );
}
```

#### Option B: Login Form

If tokens are obtained via username/password:

```tsx
function LoginForm() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');

  const handleSubmit = async () => {
    const response = await fetch('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    });
    const { token } = await response.json();
    localStorage.setItem('token', token);
  };

  return (
    <form onSubmit={handleSubmit}>
      <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} />
      <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
      <button type="submit">Login</button>
    </form>
  );
}
```

---

## Pattern 3: OAuth2

### Detection

```yaml
securitySchemes:
  OAuth2:
    type: oauth2
    flows:
      authorizationCode:
        authorizationUrl: https://auth.example.com/authorize
        tokenUrl: https://auth.example.com/token
        scopes:
          read: Read access
          write: Write access
```

### Supported Flows

| Flow | Use Case |
|------|----------|
| `authorizationCode` | User login in browser (most common) |
| `clientCredentials` | Server-to-server (no user) |
| `implicit` | Legacy, avoid |
| `password` | Legacy, avoid |

### Client Implementation

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
  tokenType: string;
  scope?: string;
}

export class OAuth2Manager {
  private config: OAuth2Auth;
  private codeVerifier?: string;

  constructor(config: Omit<OAuth2Auth, 'type' | 'token'>) {
    this.config = { ...config, type: 'oauth2' };
  }

  // Generate PKCE code verifier and challenge
  private generateCodeVerifier(): string {
    const array = new Uint8Array(32);
    crypto.getRandomValues(array);
    return this.base64UrlEncode(array);
  }

  private async generateCodeChallenge(verifier: string): Promise<string> {
    const encoder = new TextEncoder();
    const data = encoder.encode(verifier);
    const hash = await crypto.subtle.digest('SHA-256', data);
    return this.base64UrlEncode(new Uint8Array(hash));
  }

  private base64UrlEncode(buffer: Uint8Array): string {
    return btoa(String.fromCharCode(...buffer))
      .replace(/\+/g, '-')
      .replace(/\//g, '_')
      .replace(/=/g, '');
  }

  // Step 1: Get authorization URL
  async getAuthorizationUrl(state?: string): Promise<string> {
    this.codeVerifier = this.generateCodeVerifier();
    const codeChallenge = await this.generateCodeChallenge(this.codeVerifier);

    const url = new URL(this.config.authorizationUrl);
    url.searchParams.set('client_id', this.config.clientId);
    url.searchParams.set('redirect_uri', this.config.redirectUri);
    url.searchParams.set('response_type', 'code');
    url.searchParams.set('scope', this.config.scopes.join(' '));
    url.searchParams.set('code_challenge', codeChallenge);
    url.searchParams.set('code_challenge_method', 'S256');
    if (state) {
      url.searchParams.set('state', state);
    }

    // Store verifier for later
    sessionStorage.setItem('oauth_code_verifier', this.codeVerifier);

    return url.toString();
  }

  // Step 2: Exchange authorization code for token
  async exchangeCode(code: string): Promise<OAuthToken> {
    const codeVerifier = sessionStorage.getItem('oauth_code_verifier');
    if (!codeVerifier) {
      throw new Error('No code verifier found');
    }

    const response = await fetch(this.config.tokenUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: new URLSearchParams({
        grant_type: 'authorization_code',
        client_id: this.config.clientId,
        redirect_uri: this.config.redirectUri,
        code,
        code_verifier: codeVerifier,
      }),
    });

    if (!response.ok) {
      throw new Error(`Token exchange failed: ${response.status}`);
    }

    const data = await response.json();
    sessionStorage.removeItem('oauth_code_verifier');

    return {
      accessToken: data.access_token,
      refreshToken: data.refresh_token,
      expiresAt: data.expires_in
        ? Date.now() + data.expires_in * 1000
        : undefined,
      tokenType: data.token_type,
      scope: data.scope,
    };
  }

  // Step 3: Refresh token
  async refreshToken(token: OAuthToken): Promise<OAuthToken> {
    if (!token.refreshToken) {
      throw new Error('No refresh token available');
    }

    const response = await fetch(this.config.tokenUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: new URLSearchParams({
        grant_type: 'refresh_token',
        client_id: this.config.clientId,
        refresh_token: token.refreshToken,
      }),
    });

    if (!response.ok) {
      throw new Error(`Token refresh failed: ${response.status}`);
    }

    const data = await response.json();

    return {
      accessToken: data.access_token,
      refreshToken: data.refresh_token || token.refreshToken,
      expiresAt: data.expires_in
        ? Date.now() + data.expires_in * 1000
        : undefined,
      tokenType: data.token_type,
      scope: data.scope,
    };
  }

  // Check if token is expired or expiring soon
  isTokenExpired(token: OAuthToken, bufferMs = 60000): boolean {
    if (!token.expiresAt) return false;
    return token.expiresAt < Date.now() + bufferMs;
  }
}
```

### Frontend Implementation

**AuthContext.tsx:**

```tsx
import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { OAuth2Manager, OAuthToken } from '../client/auth';

interface AuthContextValue {
  isAuthenticated: boolean;
  isLoading: boolean;
  token: OAuthToken | null;
  login: () => void;
  logout: () => void;
  handleCallback: (code: string) => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

const STORAGE_KEY = 'oauth_token';

const oauth2Manager = new OAuth2Manager({
  clientId: import.meta.env.VITE_OAUTH_CLIENT_ID,
  redirectUri: `${window.location.origin}/callback`,
  scopes: ['read', 'write'],
  authorizationUrl: import.meta.env.VITE_OAUTH_AUTH_URL,
  tokenUrl: import.meta.env.VITE_OAUTH_TOKEN_URL,
});

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [token, setToken] = useState<OAuthToken | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Load token from storage
  useEffect(() => {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) {
      try {
        const parsed = JSON.parse(stored) as OAuthToken;
        if (!oauth2Manager.isTokenExpired(parsed)) {
          setToken(parsed);
        } else if (parsed.refreshToken) {
          // Try to refresh
          oauth2Manager.refreshToken(parsed).then(setToken).catch(() => {
            localStorage.removeItem(STORAGE_KEY);
          });
        }
      } catch {
        localStorage.removeItem(STORAGE_KEY);
      }
    }
    setIsLoading(false);
  }, []);

  // Auto-refresh before expiry
  useEffect(() => {
    if (!token?.expiresAt || !token.refreshToken) return;

    const refreshTime = token.expiresAt - Date.now() - 60000; // 1 min before
    if (refreshTime <= 0) return;

    const timeout = setTimeout(async () => {
      try {
        const newToken = await oauth2Manager.refreshToken(token);
        setToken(newToken);
        localStorage.setItem(STORAGE_KEY, JSON.stringify(newToken));
      } catch {
        setToken(null);
        localStorage.removeItem(STORAGE_KEY);
      }
    }, refreshTime);

    return () => clearTimeout(timeout);
  }, [token]);

  const login = useCallback(async () => {
    const state = crypto.randomUUID();
    sessionStorage.setItem('oauth_state', state);
    const authUrl = await oauth2Manager.getAuthorizationUrl(state);
    window.location.href = authUrl;
  }, []);

  const logout = useCallback(() => {
    setToken(null);
    localStorage.removeItem(STORAGE_KEY);
    sessionStorage.removeItem('oauth_state');
    sessionStorage.removeItem('oauth_code_verifier');
  }, []);

  const handleCallback = useCallback(async (code: string) => {
    setIsLoading(true);
    try {
      const newToken = await oauth2Manager.exchangeCode(code);
      setToken(newToken);
      localStorage.setItem(STORAGE_KEY, JSON.stringify(newToken));
    } finally {
      setIsLoading(false);
    }
  }, []);

  return (
    <AuthContext.Provider
      value={{
        isAuthenticated: !!token,
        isLoading,
        token,
        login,
        logout,
        handleCallback,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth must be used within AuthProvider');
  return context;
}
```

**CallbackPage.tsx:**

```tsx
import { useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

export function CallbackPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { handleCallback } = useAuth();

  useEffect(() => {
    const code = searchParams.get('code');
    const state = searchParams.get('state');
    const storedState = sessionStorage.getItem('oauth_state');

    if (!code) {
      navigate('/login?error=no_code');
      return;
    }

    if (state !== storedState) {
      navigate('/login?error=invalid_state');
      return;
    }

    handleCallback(code)
      .then(() => {
        const returnTo = sessionStorage.getItem('return_to') || '/';
        sessionStorage.removeItem('return_to');
        navigate(returnTo);
      })
      .catch(() => {
        navigate('/login?error=exchange_failed');
      });
  }, [searchParams, navigate, handleCallback]);

  return <div>Completing sign in...</div>;
}
```

**AuthGuard.tsx:**

```tsx
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { LoadingSpinner } from '../components/shared';

export function AuthGuard({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading } = useAuth();
  const location = useLocation();

  if (isLoading) {
    return <LoadingSpinner />;
  }

  if (!isAuthenticated) {
    sessionStorage.setItem('return_to', location.pathname);
    return <Navigate to="/login" replace />;
  }

  return <>{children}</>;
}
```

---

## Multiple Auth Methods

If the spec defines multiple auth methods:

```yaml
securitySchemes:
  ApiKeyAuth:
    type: apiKey
    in: header
    name: X-API-Key
  BearerAuth:
    type: http
    scheme: bearer
```

Generate a union type:

```typescript
export type AuthConfig =
  | { type: 'apiKey'; key: string; location: 'header' | 'query'; name: string }
  | { type: 'bearer'; token: string }
  | { type: 'none' };

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
    case 'none':
      break;
  }
}
```

---

## Security Best Practices

1. **Never store tokens in URL params** — Use localStorage or sessionStorage
2. **Use PKCE for OAuth2** — Required for SPAs
3. **Validate state parameter** — Prevent CSRF attacks
4. **Refresh before expiry** — Don't wait for 401
5. **Clear tokens on logout** — Remove from all storage
6. **Use HttpOnly cookies when possible** — For better security (requires backend support)
