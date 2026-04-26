# Coolify API Reference

This document contains detailed information about the Coolify API endpoints and common patterns.

## Base URL

All API requests should be made to:
```
{COOLIFY_INSTANCE_URL}/api/v1
```

## Authentication

All requests must include the API token in the Authorization header:
```
Authorization: Bearer {COOLIFY_API_TOKEN}
```

## Application Endpoints

### List All Applications
```
GET /applications
```

**Response:**
```json
{
  "data": [
    {
      "id": "uuid",
      "name": "string",
      "repository": "string",
      "branch": "string",
      "build_pack": "string",
      "created_at": "datetime",
      "updated_at": "datetime"
    }
  ]
}
```

### Get Application Details
```
GET /applications/{application_id}
```

### Create Application
```
POST /applications
```

**Body Parameters:**
- `name` (string, required): Application name
- `repository` (string, optional): Git repository URL
- `branch` (string, optional): Git branch (default: main)
- `build_pack` (string, required): One of: nixpacks, dockerfile, docker-compose
- `dockerfile_location` (string, optional): Path to Dockerfile
- `docker_compose_location` (string, optional): Path to docker-compose.yml
- `environment_variables` (array, optional): Array of environment variable objects

### Update Application
```
PATCH /applications/{application_id}
```

### Delete Application
```
DELETE /applications/{application_id}
```

### Deploy Application
```
POST /applications/{application_id}/deploy
```

**Response:**
```json
{
  "data": {
    "deployment_id": "uuid",
    "status": "queued|building|deploying|success|failed",
    "created_at": "datetime"
  }
}
```

## Deployment Endpoints

### List Deployments
```
GET /applications/{application_id}/deployments
```

### Get Deployment Details
```
GET /applications/{application_id}/deployments/{deployment_id}
```

### Get Deployment Logs
```
GET /applications/{application_id}/deployments/{deployment_id}/logs
```

## Environment Variable Endpoints

### List Environment Variables
```
GET /applications/{application_id}/environment-variables
```

### Create Environment Variable
```
POST /applications/{application_id}/environment-variables
```

**Body Parameters:**
- `key` (string, required): Variable name
- `value` (string, required): Variable value
- `is_build_time` (boolean, optional): Use during build (default: false)
- `is_preview` (boolean, optional): Use for preview deployments (default: false)

### Update Environment Variable
```
PATCH /applications/{application_id}/environment-variables/{variable_id}
```

### Delete Environment Variable
```
DELETE /applications/{application_id}/environment-variables/{variable_id}
```

## Database Endpoints

### List Databases
```
GET /databases
```

**Response:**
```json
{
  "data": [
    {
      "id": "uuid",
      "name": "string",
      "type": "postgresql|mysql|mariadb|mongodb|redis|memcached",
      "version": "string",
      "status": "running|stopped|error",
      "created_at": "datetime"
    }
  ]
}
```

### Get Database Details
```
GET /databases/{database_id}
```

### Create Database
```
POST /databases
```

**Body Parameters:**
- `name` (string, required): Database name
- `type` (string, required): Database type
- `version` (string, required): Database version
- `destination_docker_id` (string, optional): Target Docker instance
- `initial_database_name` (string, optional): Initial database name
- `initial_database_user` (string, optional): Initial database user
- `initial_database_password` (string, optional): Initial database password

### Update Database
```
PATCH /databases/{database_id}
```

### Delete Database
```
DELETE /databases/{database_id}
```

### Start Database
```
POST /databases/{database_id}/start
```

### Stop Database
```
POST /databases/{database_id}/stop
```

### Restart Database
```
POST /databases/{database_id}/restart
```

## Domain Endpoints

### List Domains
```
GET /applications/{application_id}/domains
```

### Add Domain
```
POST /applications/{application_id}/domains
```

**Body Parameters:**
- `domain` (string, required): Domain name
- `is_default` (boolean, optional): Set as default domain (default: false)

### Update Domain
```
PATCH /applications/{application_id}/domains/{domain_id}
```

### Delete Domain
```
DELETE /applications/{application_id}/domains/{domain_id}
```

### Renew SSL Certificate
```
POST /applications/{application_id}/domains/{domain_id}/ssl/renew
```

## Log Endpoints

### Get Application Logs
```
GET /applications/{application_id}/logs
```

**Query Parameters:**
- `lines` (integer, optional): Number of log lines (default: 100)
- `since` (datetime, optional): Start time for logs

### Get Container Logs
```
GET /applications/{application_id}/containers/{container_id}/logs
```

## Health Check Endpoints

### Get Health Check Status
```
GET /applications/{application_id}/health-check
```

### Update Health Check Configuration
```
PATCH /applications/{application_id}/health-check
```

**Body Parameters:**
- `path` (string, optional): Health check path
- `port` (integer, optional): Health check port
- `interval` (integer, optional): Check interval in seconds
- `retries` (integer, optional): Number of retries before marking as unhealthy

## Database Types

### Supported Database Types and Versions

#### PostgreSQL
- Versions: 11, 12, 13, 14, 15, 16
- Default Port: 5432

#### MySQL
- Versions: 5.7, 8.0
- Default Port: 3306

#### MariaDB
- Versions: 10.6, 10.11, 11.0
- Default Port: 3306

#### MongoDB
- Versions: 4.4, 5.0, 6.0, 7.0
- Default Port: 27017

#### Redis
- Versions: 6.2, 7.0, 7.2
- Default Port: 6379

#### Memcached
- Versions: 1.6, 1.7
- Default Port: 11211

## Build Pack Types

### Nixpacks
- Automatically detects application type
- Supports most modern web frameworks
- No configuration required

### Dockerfile
- Requires a Dockerfile in the repository
- Full control over the build process
- Specify path with `dockerfile_location`

### Docker Compose
- Requires a docker-compose.yml file
- For multi-container applications
- Specify path with `docker_compose_location`

## Error Codes

### Common HTTP Status Codes

- `200 OK`: Request successful
- `201 Created`: Resource created successfully
- `400 Bad Request`: Invalid request parameters
- `401 Unauthorized`: Missing or invalid API token
- `403 Forbidden`: Insufficient permissions
- `404 Not Found`: Resource not found
- `422 Unprocessable Entity`: Validation error
- `500 Internal Server Error`: Server error

### Error Response Format

```json
{
  "error": {
    "message": "string",
    "code": "string",
    "details": {}
  }
}
```

## Rate Limiting

API requests may be rate limited. Check response headers for rate limit information:

- `X-RateLimit-Limit`: Request limit per window
- `X-RateLimit-Remaining`: Remaining requests in current window
- `X-RateLimit-Reset`: Unix timestamp when the window resets

## Pagination

List endpoints support pagination:

```
GET /applications?page=1&per_page=20
```

**Response:**
```json
{
  "data": [...],
  "meta": {
    "current_page": 1,
    "per_page": 20,
    "total": 100,
    "last_page": 5
  }
}
```

## Webhooks

Coolify can send webhooks for various events:

### Supported Events
- `deployment.started`
- `deployment.success`
- `deployment.failed`
- `application.created`
- `application.updated`
- `application.deleted`

### Configure Webhooks
Webhooks can be configured through the Coolify dashboard or API (if supported).

## Examples

### Complete Application Deployment Workflow

```bash
# 1. Create application
APP_RESPONSE=$(curl -s -X POST "$COOLIFY_INSTANCE_URL/api/v1/applications" \
  -H "Authorization: Bearer $COOLIFY_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "my-app",
    "repository": "https://github.com/username/repo.git",
    "branch": "main",
    "build_pack": "nixpacks"
  }')

APP_ID=$(echo $APP_RESPONSE | jq -r '.data.id')

# 2. Add environment variables
curl -s -X POST "$COOLIFY_INSTANCE_URL/api/v1/applications/$APP_ID/environment-variables" \
  -H "Authorization: Bearer $COOLIFY_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "key": "NODE_ENV",
    "value": "production"
  }'

# 3. Trigger deployment
DEPLOY_RESPONSE=$(curl -s -X POST "$COOLIFY_INSTANCE_URL/api/v1/applications/$APP_ID/deploy" \
  -H "Authorization: Bearer $COOLIFY_API_TOKEN")

DEPLOY_ID=$(echo $DEPLOY_RESPONSE | jq -r '.data.deployment_id')

# 4. Monitor deployment status
while true; do
  STATUS=$(curl -s -X GET "$COOLIFY_INSTANCE_URL/api/v1/applications/$APP_ID/deployments/$DEPLOY_ID" \
    -H "Authorization: Bearer $COOLIFY_API_TOKEN" | jq -r '.data.status')
  
  echo "Deployment status: $STATUS"
  
  if [ "$STATUS" = "success" ] || [ "$STATUS" = "failed" ]; then
    break
  fi
  
  sleep 5
done
```

## Additional Resources

- [Coolify API Documentation](https://coolify.io/docs/api)
- [Coolify GitHub Issues](https://github.com/coollabsio/coolify/issues)
- [Coolify Discord](https://discord.gg/coolify)
