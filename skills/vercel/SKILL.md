---
name: vercel
description: Deploy and manage applications on Vercel, including serverless functions, preview deployments, and deployment protection. Use when working with Vercel-hosted projects or configuring Vercel deployments.
triggers:
- vercel
- serverless
- preview deployment
---

# Vercel Deployment Guide

## Deployment Protection and Agent Access

Vercel deployments may have **Deployment Protection** enabled, which requires authentication to access preview deployments. This can block automated testing and agent access to preview URLs.

### Identifying Protected Deployments

If you encounter a login page or authentication requirement when accessing a Vercel preview URL, the deployment has protection enabled. Signs include:
- Redirect to `vercel.com/login` or SSO login page
- 401/403 errors when accessing the deployment
- Preview URLs that require Vercel team membership

### Enabling Agent Access with Protection Bypass

To allow agents and automated systems to access protected deployments, users need to set up **Protection Bypass for Automation**:

1. **Navigate to Project Settings**
   - Go to the Vercel Dashboard
   - Select the project
   - Click on **Settings** → **Deployment Protection**

2. **Generate a Protection Bypass Secret**
   - Under "Protection Bypass for Automation", click **Generate Secret**
   - Copy the generated secret securely

3. **Using the Bypass Secret**
   
   The secret can be used in two ways:
   
   **As a Header:**
   ```bash
   curl -H "x-vercel-protection-bypass: <secret>" https://your-preview-url.vercel.app
   ```
   
   **As a Query Parameter:**
   ```
   https://your-preview-url.vercel.app?x-vercel-protection-bypass=<secret>
   ```

4. **For Browser-Based Testing**
   - Append `?x-vercel-protection-bypass=<secret>` to the preview URL
   - The secret will be stored in a cookie for subsequent requests

### Alternative: Disable Protection for Previews

If protection bypass is not suitable, users can disable protection for preview deployments:

1. Go to **Settings** → **Deployment Protection**
2. Set "Vercel Authentication" to **Only Production Deployments** or **Disabled**

<IMPORTANT>
If you cannot access a Vercel preview deployment due to authentication requirements, inform the user that they need to either:
1. Set up a Protection Bypass secret and provide it to you, OR
2. Disable Deployment Protection for preview deployments in their Vercel project settings

Do NOT repeatedly attempt to access protected URLs without the bypass secret.
</IMPORTANT>

## Serverless Functions (API Routes)

Vercel supports serverless functions in the `/api` directory. These are useful for:
- Proxying API requests to avoid CORS issues
- Server-side processing
- Handling webhooks

### Creating a Serverless Function

Create a file in the `api/` directory at the project root:

```typescript
// api/hello.ts
import type { VercelRequest, VercelResponse } from '@vercel/node';

export default function handler(req: VercelRequest, res: VercelResponse) {
  res.status(200).json({ message: 'Hello from Vercel!' });
}
```

### Catch-All Routes

For proxying multiple endpoints, use catch-all routes:

```typescript
// api/proxy/[...path].ts
import type { VercelRequest, VercelResponse } from '@vercel/node';

export default async function handler(req: VercelRequest, res: VercelResponse) {
  const { path } = req.query;
  const apiPath = Array.isArray(path) ? path.join('/') : path || '';
  
  // Forward the request to the target API
  const response = await fetch(`https://api.example.com/${apiPath}`, {
    method: req.method,
    headers: { 'Content-Type': 'application/json' },
    body: req.method !== 'GET' ? JSON.stringify(req.body) : undefined,
  });
  
  const data = await response.json();
  res.status(response.status).json(data);
}
```

### CORS Headers

When creating API proxies, include CORS headers:

```typescript
res.setHeader('Access-Control-Allow-Origin', '*');
res.setHeader('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS');
res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization');

// Handle preflight requests
if (req.method === 'OPTIONS') {
  return res.status(200).end();
}
```

## Environment Variables

Set environment variables in Vercel Dashboard under **Settings** → **Environment Variables**, or use the Vercel CLI:

```bash
vercel env add MY_SECRET
```

Access in serverless functions:
```typescript
const secret = process.env.MY_SECRET;
```

## Vercel CLI Commands

Common Vercel CLI commands:

```bash
# Login to Vercel
vercel login

# Deploy to preview
vercel

# Deploy to production
vercel --prod

# List deployments
vercel ls

# View deployment logs
vercel logs <deployment-url>

# Pull environment variables locally
vercel env pull
```
