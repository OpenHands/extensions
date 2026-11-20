# Coolify Skill for OpenHands

This skill enables OpenHands agents to deploy and manage applications on Coolify, a self-hosted alternative to Vercel, Netlify, and Heroku.

## What is Coolify?

Coolify is an open-source, self-hosted platform that allows you to:
- Deploy applications from Git repositories (GitHub, GitLab, Bitbucket)
- Manage Docker containers and services
- Create and manage databases (PostgreSQL, MySQL, MongoDB, Redis, etc.)
- Set up CI/CD pipelines
- Manage SSL certificates and custom domains
- Create preview deployments for pull requests

## Prerequisites

To use this skill, you need:

1. A running Coolify instance
2. A Coolify API token
3. Your Coolify instance URL

## Setup

Set the required environment variables:

```bash
export COOLIFY_API_TOKEN="your-coolify-api-token"
export COOLIFY_INSTANCE_URL="https://your-coolify-instance.com"
```

## Common Use Cases

### Deploy a Web Application

```bash
# Create and deploy a Node.js application
curl -X POST "$COOLIFY_INSTANCE_URL/api/v1/applications" \
  -H "Authorization: Bearer $COOLIFY_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "my-web-app",
    "repository": "https://github.com/username/my-app.git",
    "branch": "main",
    "build_pack": "nixpacks"
  }'
```

### Create a Database

```bash
# Create a PostgreSQL database
curl -X POST "$COOLIFY_INSTANCE_URL/api/v1/databases" \
  -H "Authorization: Bearer $COOLIFY_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "production-db",
    "type": "postgresql",
    "version": "15"
  }'
```

### Set Environment Variables

```bash
# Add environment variables to an application
curl -X POST "$COOLIFY_INSTANCE_URL/api/v1/applications/{application_id}/environment-variables" \
  -H "Authorization: Bearer $COOLIFY_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "key": "DATABASE_URL",
    "value": "postgresql://user:password@localhost:5432/mydb"
  }'
```

## Features

- **Multiple Build Packs**: Support for Nixpacks, Dockerfile, and Docker Compose
- **Git Integration**: Connect to GitHub, GitLab, and Bitbucket
- **Database Management**: Create and manage various database types
- **Environment Variables**: Separate build-time and runtime variables
- **Custom Domains**: Add custom domains with automatic SSL
- **Preview Deployments**: Automatic preview deployments for pull requests
- **Health Checks**: Configure health checks for automatic monitoring
- **Logs**: Access application and deployment logs

## Supported Applications

- Node.js applications
- Python applications (Django, Flask, FastAPI)
- Ruby on Rails
- PHP applications
- Go applications
- Rust applications
- Static sites (HTML, CSS, JavaScript)
- Docker-based applications
- Any application with a Dockerfile or Docker Compose configuration

## Limitations

- Requires a self-hosted Coolify instance
- API token must have appropriate permissions
- Network connectivity to the Coolify instance is required
- Some advanced features may require Coolify Pro

## Resources

- [Coolify Website](https://coolify.io)
- [Coolify Documentation](https://coolify.io/docs)
- [Coolify GitHub](https://github.com/coollabsio/coolify)
- [Coolify Discord](https://discord.gg/coolify)

## Contributing

To improve this skill, please refer to the main OpenHands documentation for skill contribution guidelines.
