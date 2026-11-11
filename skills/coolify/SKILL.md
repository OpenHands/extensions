---
name: coolify
description: Deploy and manage applications on Coolify, a self-hosted alternative to Vercel/Netlify. Use when deploying applications from Git repositories, managing Docker containers, databases, or working with Coolify-hosted projects.
triggers:
- coolify
- self-hosted deployment
- coolify deploy
- coolify database
---

# Coolify Deployment Guide

## About Coolify

Coolify is an open-source, self-hosted platform for deploying applications. It serves as an alternative to Vercel, Netlify, and Heroku, allowing you to deploy and manage applications, databases, and services using Docker containers.

## Authentication

### API Token Setup

Coolify uses API tokens for authentication. Set up your API token:

```bash
# Set your Coolify API token
export COOLIFY_API_TOKEN="your-coolify-api-token"

# Set your Coolify instance URL
export COOLIFY_INSTANCE_URL="https://your-coolify-instance.com"
```

<IMPORTANT>
Before performing any Coolify operations, check if the required environment variables are set:

```bash
[ -n "$COOLIFY_API_TOKEN" ] && echo "COOLIFY_API_TOKEN is set" || echo "COOLIFY_API_TOKEN is NOT set"
[ -n "$COOLIFY_INSTANCE_URL" ] && echo "COOLIFY_INSTANCE_URL is set" || echo "COOLIFY_INSTANCE_URL is NOT set"
```

If either variable is missing, ask the user to provide them before proceeding.
</IMPORTANT>

## Coolify API Usage

### Basic API Requests

All Coolify API requests use the API token in the Authorization header:

```bash
curl -X GET "$COOLIFY_INSTANCE_URL/api/v1/applications" \
  -H "Authorization: Bearer $COOLIFY_API_TOKEN" \
  -H "Content-Type: application/json"
```

### Common API Endpoints

#### List Applications

```bash
curl -X GET "$COOLIFY_INSTANCE_URL/api/v1/applications" \
  -H "Authorization: Bearer $COOLIFY_API_TOKEN"
```

#### Get Application Details

```bash
curl -X GET "$COOLIFY_INSTANCE_URL/api/v1/applications/{application_id}" \
  -H "Authorization: Bearer $COOLIFY_API_TOKEN"
```

#### Deploy Application

```bash
curl -X POST "$COOLIFY_INSTANCE_URL/api/v1/applications/{application_id}/deploy" \
  -H "Authorization: Bearer $COOLIFY_API_TOKEN" \
  -H "Content-Type: application/json"
```

#### List Databases

```bash
curl -X GET "$COOLIFY_INSTANCE_URL/api/v1/databases" \
  -H "Authorization: Bearer $COOLIFY_API_TOKEN"
```

#### Create Database

```bash
curl -X POST "$COOLIFY_INSTANCE_URL/api/v1/databases" \
  -H "Authorization: Bearer $COOLIFY_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "my-database",
    "type": "postgresql",
    "version": "15"
  }'
```

## Project Setup

### Connecting Git Repositories

Coolify supports connecting to Git repositories for automatic deployments:

1. **GitHub Integration**
   - Navigate to Coolify Dashboard → Sources → GitHub
   - Connect your GitHub account
   - Authorize access to repositories

2. **GitLab Integration**
   - Navigate to Coolify Dashboard → Sources → GitLab
   - Connect your GitLab account
   - Authorize access to projects

3. **Bitbucket Integration**
   - Navigate to Coolify Dashboard → Sources → Bitbucket
   - Connect your Bitbucket account
   - Authorize access to repositories

### Creating a New Application

**From Git Repository:**

```bash
# Using the API to create an application from a Git repository
curl -X POST "$COOLIFY_INSTANCE_URL/api/v1/applications" \
  -H "Authorization: Bearer $COOLIFY_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "my-app",
    "repository": "https://github.com/username/repo.git",
    "branch": "main",
    "build_pack": "nixpacks",
    "environment_variables": [
      {
        "key": "NODE_ENV",
        "value": "production"
      }
    ]
  }'
```

**From Docker Compose:**

```bash
curl -X POST "$COOLIFY_INSTANCE_URL/api/v1/applications" \
  -H "Authorization: Bearer $COOLIFY_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "my-docker-app",
    "build_pack": "docker-compose",
    "docker_compose_location": "./docker-compose.yml"
  }'
```

## Environment Variables

### Setting Environment Variables

**Via API:**

```bash
curl -X POST "$COOLIFY_INSTANCE_URL/api/v1/applications/{application_id}/environment-variables" \
  -H "Authorization: Bearer $COOLIFY_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "key": "DATABASE_URL",
    "value": "postgresql://user:password@localhost:5432/mydb",
    "is_build_time": false,
    "is_preview": false
  }'
```

**Build-time vs Runtime Variables:**

- **Build-time variables**: Used during the build process (e.g., API keys for fetching dependencies)
- **Runtime variables**: Used when the application is running (e.g., database connections)

## Deployment Types

### Production Deployments

```bash
# Trigger a production deployment
curl -X POST "$COOLIFY_INSTANCE_URL/api/v1/applications/{application_id}/deploy" \
  -H "Authorization: Bearer $COOLIFY_API_TOKEN"
```

### Preview Deployments

Coolify can automatically create preview deployments for pull requests:

```bash
# Configure preview deployments
curl -X PATCH "$COOLIFY_INSTANCE_URL/api/v1/applications/{application_id}" \
  -H "Authorization: Bearer $COOLIFY_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "preview_deployments": {
      "enabled": true,
      "preview_prefix": "pr-"
    }
  }'
```

## Database Management

### Supported Database Types

Coolify supports the following databases:
- PostgreSQL
- MySQL
- MariaDB
- MongoDB
- Redis
- Memcached

### Creating a Database

```bash
# Create a PostgreSQL database
curl -X POST "$COOLIFY_INSTANCE_URL/api/v1/databases" \
  -H "Authorization: Bearer $COOLIFY_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "production-db",
    "type": "postgresql",
    "version": "15",
    "destination_docker_id": "local"
  }'
```

### Database Connection Details

After creating a database, retrieve connection details:

```bash
curl -X GET "$COOLIFY_INSTANCE_URL/api/v1/databases/{database_id}" \
  -H "Authorization: Bearer $COOLIFY_API_TOKEN"
```

## SSL and Custom Domains

### Adding Custom Domains

```bash
curl -X POST "$COOLIFY_INSTANCE_URL/api/v1/applications/{application_id}/domains" \
  -H "Authorization: Bearer $COOLIFY_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "domain": "app.example.com",
    "is_default": true
  }'
```

### SSL Certificates

Coolify automatically manages SSL certificates using Let's Encrypt for domains:

```bash
# Force SSL certificate renewal
curl -X POST "$COOLIFY_INSTANCE_URL/api/v1/applications/{application_id}/domains/{domain_id}/ssl/renew" \
  -H "Authorization: Bearer $COOLIFY_API_TOKEN"
```

## Build Packs

Coolify supports multiple build packs for different application types:

### Nixpacks (Recommended)

Nixpacks automatically detects your application type and configures the build:

```bash
# Enable Nixpacks
curl -X PATCH "$COOLIFY_INSTANCE_URL/api/v1/applications/{application_id}" \
  -H "Authorization: Bearer $COOLIFY_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "build_pack": "nixpacks"
  }'
```

### Dockerfile

If you have a custom Dockerfile:

```bash
curl -X PATCH "$COOLIFY_INSTANCE_URL/api/v1/applications/{application_id}" \
  -H "Authorization: Bearer $COOLIFY_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "build_pack": "dockerfile",
    "dockerfile_location": "./Dockerfile"
  }'
```

### Docker Compose

For multi-container applications:

```bash
curl -X PATCH "$COOLIFY_INSTANCE_URL/api/v1/applications/{application_id}" \
  -H "Authorization: Bearer $COOLIFY_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "build_pack": "docker-compose",
    "docker_compose_location": "./docker-compose.yml"
  }'
```

## Monitoring and Logs

### View Application Logs

```bash
curl -X GET "$COOLIFY_INSTANCE_URL/api/v1/applications/{application_id}/logs" \
  -H "Authorization: Bearer $COOLIFY_API_TOKEN"
```

### View Deployment Logs

```bash
curl -X GET "$COOLIFY_INSTANCE_URL/api/v1/applications/{application_id}/deployments/{deployment_id}/logs" \
  -H "Authorization: Bearer $COOLIFY_API_TOKEN"
```

## Health Checks

Configure health checks for your application:

```bash
curl -X PATCH "$COOLIFY_INSTANCE_URL/api/v1/applications/{application_id}" \
  -H "Authorization: Bearer $COOLIFY_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "health_check": {
      "path": "/health",
      "port": 3000,
      "interval": 30,
      "retries": 3
    }
  }'
```

## Common Workflows

### Deploy a Next.js Application

```bash
# 1. Create the application
curl -X POST "$COOLIFY_INSTANCE_URL/api/v1/applications" \
  -H "Authorization: Bearer $COOLIFY_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "nextjs-app",
    "repository": "https://github.com/username/nextjs-app.git",
    "branch": "main",
    "build_pack": "nixpacks"
  }'

# 2. Set environment variables
curl -X POST "$COOLIFY_INSTANCE_URL/api/v1/applications/{application_id}/environment-variables" \
  -H "Authorization: Bearer $COOLIFY_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "key": "NODE_ENV",
    "value": "production"
  }'

# 3. Trigger deployment
curl -X POST "$COOLIFY_INSTANCE_URL/api/v1/applications/{application_id}/deploy" \
  -H "Authorization: Bearer $COOLIFY_API_TOKEN"
```

### Deploy with PostgreSQL Database

```bash
# 1. Create database
curl -X POST "$COOLIFY_INSTANCE_URL/api/v1/databases" \
  -H "Authorization: Bearer $COOLIFY_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "app-db",
    "type": "postgresql",
    "version": "15"
  }'

# 2. Create application
curl -X POST "$COOLIFY_INSTANCE_URL/api/v1/applications" \
  -H "Authorization: Bearer $COOLIFY_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "app-with-db",
    "repository": "https://github.com/username/app.git",
    "branch": "main",
    "build_pack": "nixpacks"
  }'

# 3. Link database to application (get database_id from step 1)
curl -X POST "$COOLIFY_INSTANCE_URL/api/v1/applications/{application_id}/databases" \
  -H "Authorization: Bearer $COOLIFY_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "database_id": "{database_id}"
  }'
```

## Troubleshooting

### Build Failures

If a build fails:

1. Check deployment logs: `GET /api/v1/applications/{id}/deployments/{deployment_id}/logs`
2. Verify build pack is correctly configured
3. Check environment variables are set correctly
4. Ensure repository is accessible and branch exists

### Connection Issues

If you cannot connect to your Coolify instance:

1. Verify `COOLIFY_INSTANCE_URL` is correct and accessible
2. Check that `COOLIFY_API_TOKEN` is valid
3. Ensure network connectivity to the Coolify instance

### Database Connection Issues

If your application cannot connect to its database:

1. Verify the database is running: `GET /api/v1/databases/{id}`
2. Check that the database is linked to the application
3. Verify environment variables contain the correct connection string
4. Check network connectivity between application and database

## Best Practices

1. **Use Environment Variables**: Never hardcode secrets in your application code
2. **Enable Health Checks**: Configure health checks for automatic restart on failure
3. **Use Preview Deployments**: Enable preview deployments for pull requests to test changes
4. **Monitor Logs**: Regularly check application and deployment logs
5. **Regular Backups**: Set up automated backups for databases
6. **SSL Certificates**: Always use HTTPS with custom domains
7. **Resource Limits**: Set appropriate resource limits for containers
8. **Security**: Keep your Coolify instance and dependencies updated

## Documentation

- [Coolify Documentation](https://coolify.io/docs)
- [Coolify GitHub Repository](https://github.com/coollabsio/coolify)
- [Coolify API Reference](https://coolify.io/docs/api)
