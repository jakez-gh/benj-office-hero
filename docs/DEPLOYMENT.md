# Office Hero MVP - Deployment Guide

**Version:** 1.0  
**Last Updated:** June 2, 2026  
**Target:** Staging Environment

---

## Pre-Deployment Checklist

- [ ] All tests passing locally
- [ ] Code review approved
- [ ] Database migrations tested on fresh schema
- [ ] Environment variables configured
- [ ] JWT keys generated/loaded
- [ ] CORS settings appropriate
- [ ] RLS policies verified
- [ ] Rate limiting configured

---

## Environment Setup

### Backend Environment Variables

```bash
# Database
DATABASE_URL=postgresql+asyncpg://user:password@neon.tech/office_hero_staging

# JWT Keys
JWT_PRIVATE_KEY=$(cat ~/.ssh/jwt-private-key.pem)
JWT_PUBLIC_KEY=$(cat ~/.ssh/jwt-public-key.pem)

# CORS (for staging)
ALLOWED_ORIGINS=https://admin-staging.officehero.dev,https://tech-staging.officehero.dev

# ORS Routing (OpenRouteService)
ORS_BASE_URL=https://api.openrouteservice.org
ORS_API_KEY=your-ors-key

# Logging
LOG_LEVEL=INFO
SENTRY_DSN=https://your-sentry-key@sentry.io/project-id

# Feature flags
ENABLE_BACK_OFFICE_ADAPTER=false
ENABLE_DYNAMIC_ROUTING=false
```

### Frontend Environment Variables (admin-web)

```bash
VITE_API_BASE_URL=https://api-staging.officehero.dev
VITE_AUTH_ISSUER=https://auth.officehero.dev
VITE_SENTRY_DSN=https://your-sentry-key@sentry.io/project-id
```

### Frontend Environment Variables (tech-web)

```bash
VITE_API_BASE_URL=https://api-staging.officehero.dev
VITE_AUTH_ISSUER=https://auth.officehero.dev
VITE_SENTRY_DSN=https://your-sentry-key@sentry.io/project-id
```

---

## Database Setup

### 1. Create Database

```bash
# On Neon (serverless PG)
psql postgres://user:password@neon.tech <<EOF
  CREATE DATABASE office_hero_staging;
