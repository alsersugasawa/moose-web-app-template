# System Requirements Specification (SRS)

**Project:** Web Platform Template
**Version:** 1.2.0
**Date:** 2026-02-24
**Status:** Approved

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [System Overview](#2-system-overview)
3. [Functional Requirements](#3-functional-requirements)
4. [Non-Functional Requirements](#4-non-functional-requirements)
5. [System Architecture](#5-system-architecture)
6. [Data Model](#6-data-model)
7. [API Specification](#7-api-specification)
8. [Security Requirements](#8-security-requirements)
9. [Infrastructure Requirements](#9-infrastructure-requirements)
10. [Environment Configuration](#10-environment-configuration)
11. [Constraints and Assumptions](#11-constraints-and-assumptions)

---

## 1. Introduction

### 1.1 Purpose

This document specifies the functional and non-functional requirements for the Web Platform Template — a full-stack web application platform providing authentication, role-based access control, user management, and a configurable admin portal. It is intended as the authoritative reference for developers, operators, and stakeholders building on or deploying this template.

### 1.2 Scope

The system provides:

- Multi-user authentication with JWT tokens, OAuth 2.0, and TOTP two-factor authentication
- Role-based access control (RBAC) with fine-grained permission scopes
- User profile management including avatar upload
- API key generation for programmatic/service access
- Invite-only registration mode
- An admin portal for user management, system monitoring, and database backup
- HTTPS termination via Caddy with automatic Let's Encrypt certificate provisioning
- Container-based deployment (Docker Compose and Kubernetes)

### 1.3 Document Conventions

| Term | Definition |
|---|---|
| **Admin** | A user with `is_admin = true`; bypasses all permission scope checks |
| **Role** | A named set of permission scopes assignable to users |
| **Scope** | A string token (e.g. `users:read`) that gates access to a specific action |
| **API Key** | A long-lived `mpk_`-prefixed secret used in place of a JWT for programmatic access |
| **Invitation** | A single-use token that allows one registration when invite-only mode is active |
| **JWT** | JSON Web Token used as the primary session credential after login |
| **JTI** | JWT ID — a unique claim used to track and revoke individual sessions |

### 1.4 References

- [README.md](../README.md) — Quick start and setup guide
- [CHANGELOG.md](../CHANGELOG.md) — Version history
- [docs/ROADMAP.md](ROADMAP.md) — Feature roadmap
- [docs/security/SECURITY_COMPLIANCE.md](security/SECURITY_COMPLIANCE.md) — ISO 27001 / NIST / OWASP mapping
- [docs/guides/USER_GUIDE.md](guides/USER_GUIDE.md) — End-user documentation

---

## 2. System Overview

### 2.1 System Context

The platform is a web application comprising:

- A **FastAPI** backend (REST API, served by uvicorn)
- A **PostgreSQL 14** database (persistent storage)
- A **Caddy 2** reverse proxy (production TLS termination)
- A **Bootstrap 5.3** single-page frontend (HTML + vanilla JS, served as static files from the backend)

Users access the application through a web browser. Automated clients access the API directly using API keys or JWT Bearer tokens. Administrators access the admin portal via a separate HTML page.

### 2.2 User Classes

| Class | Description | Access |
|---|---|---|
| **Unauthenticated** | No session; can reach the login, register, forgot-password, and invite-validate endpoints | Public endpoints only |
| **Regular User** | Authenticated with a JWT or API key; `is_admin = false` | Own data + any scopes granted by assigned role |
| **Role User** | Regular user with one or more permission scopes granted via an assigned role | Admin sections proportional to granted scopes |
| **Administrator** | `is_admin = true`; all permission checks bypassed | Full platform access |

### 2.3 Operating Environment

- **Development**: Docker Compose dev override; web exposed directly on port 8080; no Caddy
- **Production**: Docker Compose with `--profile proxy`; Caddy handles TLS on ports 80/443; web not exposed externally
- **Kubernetes**: Manifests provided in `k8s/`; Ingress required for external TLS

---

## 3. Functional Requirements

Requirements are identified as **FR-NNN** and grouped by subsystem.

### 3.1 Authentication

| ID | Requirement |
|---|---|
| FR-001 | The system shall allow users to register with a unique username, unique email address, and password |
| FR-002 | The system shall validate password complexity: minimum 12 characters, at least one uppercase letter, one lowercase letter, one digit, and one special character |
| FR-003 | The system shall reject passwords containing common patterns (`password`, `123456`, `qwerty`, `abc123`, `admin`) |
| FR-004 | The system shall hash all passwords using bcrypt with a work factor of 12 before storage |
| FR-005 | The system shall issue a signed JWT on successful login; the default token lifetime is 30 minutes |
| FR-006 | The system shall support session tracking via JWT ID (JTI); when `REQUIRE_JTI=true` all tokens must have a valid, non-revoked JTI in the database |
| FR-007 | The system shall support email verification; unverified users are restricted when `FORCE_EMAIL_VERIFICATION=true` |
| FR-008 | The system shall provide a forgot-password flow: submit email → receive time-limited single-use reset link → submit new password |
| FR-009 | The system shall support OAuth 2.0 login via Google and GitHub when the respective client credentials are configured |
| FR-010 | The system shall support TOTP two-factor authentication (RFC 6238); users may enable TOTP and must present a valid 6-digit code on subsequent logins |
| FR-011 | The system shall allow users to view and revoke their active sessions |
| FR-012 | The system shall accept `X-API-Key` header as an alternative authentication credential (see FR-030) |
| FR-013 | On first deployment (no users in the database), the system shall redirect to `/static/setup.html` to create the initial admin account |

### 3.2 Role-Based Access Control

| ID | Requirement |
|---|---|
| FR-020 | The system shall support named roles, each with a JSON array of permission scopes |
| FR-021 | The database migration shall seed three default roles: `viewer` (no scopes), `editor` (no scopes), `manager` (`users:read`, `logs:read`, `system:read`) |
| FR-022 | Each user shall have at most one assigned role (`role_id` FK, nullable) |
| FR-023 | Administrators (`is_admin = true`) shall bypass all permission scope checks |
| FR-024 | Non-admin users shall be granted the union of their role's scopes and any additional scopes stored on `user.permissions` |
| FR-025 | Protected endpoints shall return HTTP 403 when the caller lacks the required scope |
| FR-026 | The admin portal shall expose role CRUD under `/api/admin/roles` |
| FR-027 | The system shall prevent deletion of a role that is assigned to one or more users (HTTP 409) |
| FR-028 | Canonical permission scopes are: `users:read`, `users:write`, `roles:manage`, `invitations:manage`, `logs:read`, `backups:read`, `backups:write`, `system:read`, `api_keys:manage` |

### 3.3 User Profiles

| ID | Requirement |
|---|---|
| FR-031 | Each user shall have optional profile fields: `display_name` (≤100 chars), `bio` (text), `avatar_path`, `timezone`, `language` |
| FR-032 | Users shall be able to read and update their own profile via `GET/PUT /api/auth/profile` |
| FR-033 | Users shall be able to upload an avatar image via `POST /api/auth/profile/avatar` (multipart) |
| FR-034 | Accepted avatar formats: JPEG, PNG, WebP; maximum input size: 2 MB |
| FR-035 | The system shall resize and convert all uploaded avatars to 200×200 JPEG using Pillow before storing them at `static/avatars/{user_id}_{8-hex}.jpg` |
| FR-036 | When a new avatar is uploaded, the previous avatar file shall be deleted |
| FR-037 | The `display_name` shall be shown in the application header when set, replacing the username |

### 3.4 API Keys

| ID | Requirement |
|---|---|
| FR-030 | The system shall accept `X-API-Key` as an authentication header; the header is checked before the JWT Bearer path |
| FR-041 | API keys shall use the format `mpk_` + `secrets.token_hex(20)` (44 characters total) |
| FR-042 | The full API key value shall be returned once (at creation time) and never again; only the `key_prefix` (first 10 characters) is stored in plaintext for index lookup |
| FR-043 | API key values shall be stored as bcrypt hashes |
| FR-044 | API keys shall support an optional `expires_at` timestamp and an `is_active` flag |
| FR-045 | Users shall be able to create, list, and delete their own API keys via `/api/auth/api-keys` |
| FR-046 | API key authentication shall update `last_used` on each successful use |
| FR-047 | Revoked or expired API keys shall return HTTP 401 |

### 3.5 Invite-Only Registration

| ID | Requirement |
|---|---|
| FR-050 | When `INVITE_ONLY=true`, the registration endpoint shall require a valid invitation token |
| FR-051 | When `INVITE_ONLY=false`, the invitation token field shall be optional and ignored at the backend |
| FR-052 | Invitations shall be created by users with the `invitations:manage` scope or any admin |
| FR-053 | Each invitation shall have a unique 64-character cryptographic token, an optional target email address, and an expiry timestamp |
| FR-054 | Invitation tokens shall be consumed atomically on registration: `used_by` and `used_at` are set in the same transaction |
| FR-055 | A consumed invitation may not be reused; the endpoint shall return HTTP 400 |
| FR-056 | Admins may delete unused invitations; used invitations may not be deleted (HTTP 409) |
| FR-057 | A public endpoint (`GET /api/auth/invite/validate?token=<token>`) shall confirm token validity without consuming it |
| FR-058 | The invite link format shall be: `<APP_BASE_URL>/static/index.html?invite=<token>` |

### 3.6 Admin Portal

| ID | Requirement |
|---|---|
| FR-060 | The admin portal shall be available at `/static/admin.html` with a separate login page at `/static/admin-login.html` |
| FR-061 | The admin portal shall display sections conditionally based on the caller's granted scopes |
| FR-062 | **Users section** (`users:read`): list all users; columns include ID, username, display name, email, role, admin flag, active flag, last login |
| FR-063 | **Users section** (admin only): create, edit, and delete users; edit includes role assignment, admin flag, active flag, username, email, and password |
| FR-064 | **Roles section** (admin only): list, create, update, and delete roles and their permission scope arrays |
| FR-065 | **Invitations section** (`invitations:manage`): list invitations with status, create new invitations, copy invite link, delete unused invitations |
| FR-066 | **Logs section** (`logs:read`): view system activity logs; filterable by level |
| FR-067 | **Backups section** (`backups:read` / `backups:write`): list and create database backups stored in `backups/` |
| FR-068 | **System section** (`system:read`): real-time CPU, memory, disk, and service status |
| FR-069 | **Config section** (admin only): read and update application name and invite-only mode |
| FR-070 | The admin portal shall show the Admin button in the main app only when `is_admin=true` or `permissions_effective.length > 0` |

### 3.7 Dashboard

| ID | Requirement |
|---|---|
| FR-080 | The main dashboard shall display built-in cards: Welcome, Account Security, and API Keys |
| FR-081 | Users shall be able to show or hide built-in cards; preferences are stored in browser `localStorage` |
| FR-082 | Users shall be able to create custom dashboard cards with a title, body text, icon (Bootstrap Icons), and optional link |
| FR-083 | Custom cards shall be persisted in `localStorage` keyed by username |

### 3.8 Backup

| ID | Requirement |
|---|---|
| FR-090 | The system shall support on-demand PostgreSQL database backups via `pg_dump` |
| FR-091 | Backups shall be stored in `/app/backups` by default; the path is configurable via `BACKUP_DIR` |
| FR-092 | The system shall support optional backup replication to SMB/CIFS and NFS file shares |
| FR-093 | Backups older than `BACKUP_RETENTION_DAYS` (default: 30) shall be eligible for pruning |

---

## 4. Non-Functional Requirements

### 4.1 Performance

| ID | Requirement |
|---|---|
| NFR-001 | The API shall respond to authentication endpoints within 500 ms under normal load (single-node Docker deployment) |
| NFR-002 | Database queries shall be executed asynchronously via `asyncpg`; no synchronous blocking DB calls are permitted |
| NFR-003 | Avatar image processing shall complete within 2 seconds for inputs up to 2 MB |
| NFR-004 | Static files (HTML, CSS, JS) shall be served directly by FastAPI's `StaticFiles` mount with no server-side processing |

### 4.2 Availability

| ID | Requirement |
|---|---|
| NFR-010 | The application container shall include a Docker health check (`/health`) polled every 30 seconds with a 10-second timeout |
| NFR-011 | Container restart policy shall be `unless-stopped` in Docker Compose |
| NFR-012 | PostgreSQL data shall be stored in a named Docker volume to survive container restarts and image updates |

### 4.3 Scalability

| ID | Requirement |
|---|---|
| NFR-020 | The application shall be stateless with respect to JWT sessions (no server-side session memory required) in `REQUIRE_JTI=false` mode |
| NFR-021 | When `REQUIRE_JTI=true`, all session state is stored in PostgreSQL; horizontal scaling requires a shared database |
| NFR-022 | Rate limiting state is held in-process memory; horizontal scaling requires an external rate-limit store (Redis — see Roadmap Phase 4) |

### 4.4 Maintainability

| ID | Requirement |
|---|---|
| NFR-030 | Database schema changes shall be delivered as idempotent SQL migration files in `migrations/` numbered sequentially |
| NFR-031 | Each migration file shall use `CREATE TABLE IF NOT EXISTS`, `ALTER TABLE ... ADD COLUMN IF NOT EXISTS`, and `ON CONFLICT DO NOTHING` where applicable |
| NFR-032 | New API routers shall be registered in `app/main.py`; the application shall not auto-discover routers |
| NFR-033 | Permission scopes shall be defined in the canonical list in `app/permissions.py`; ad-hoc string scopes are prohibited |

### 4.5 Usability

| ID | Requirement |
|---|---|
| NFR-040 | The frontend shall be responsive and usable on screens ≥ 320 px wide (Bootstrap 5.3 responsive grid) |
| NFR-041 | Theme (Light / Dark / System) shall be persisted in `localStorage` and applied without a page reload |
| NFR-042 | All error messages exposed to end users shall be in plain English and free of internal stack traces |

### 4.6 Portability

| ID | Requirement |
|---|---|
| NFR-050 | The application shall run on any host where Docker Engine 20.10+ and Docker Compose v2 are available |
| NFR-051 | Kubernetes manifests shall target API version `apps/v1` (compatible with Kubernetes ≥ 1.20) |
| NFR-052 | The Python application shall be compatible with Python 3.10+ |

---

## 5. System Architecture

### 5.1 Component Diagram

```
┌─────────────────────────────────────────────────────┐
│                     Client Browser                  │
│   /static/index.html  /static/admin.html            │
└──────────────────────┬──────────────────────────────┘
                       │ HTTPS (port 443) or HTTP (port 8080 dev)
                       ▼
┌──────────────────────────────────────┐
│         Caddy 2 (production)         │  ports 80, 443
│   Auto TLS via Let's Encrypt / ACME  │
└──────────────────────┬───────────────┘
                       │ HTTP (internal, port 8000)
                       ▼
┌──────────────────────────────────────┐
│    FastAPI + uvicorn (webapp-web)    │  port 8000 (internal)
│                                      │
│  Middleware stack (in order):        │
│    1. SessionMiddleware (OAuth CSRF) │
│    2. SecurityHeadersMiddleware      │
│    3. RateLimitMiddleware            │
│    4. CORSMiddleware                 │
│    5. TrustedHostMiddleware          │
│                                      │
│  Routers:                            │
│    /api/auth/*      auth.py          │
│    /api/admin/*     admin.py         │
│    /api/auth/oauth  oauth.py         │
│    /api/admin/roles roles.py         │
│    /api/auth/api-keys api_keys.py   │
│    /api/admin/invitations  inv.py    │
│    /static/*        StaticFiles      │
└──────────────────────┬───────────────┘
                       │ asyncpg (TCP, port 5432)
                       ▼
┌──────────────────────────────────────┐
│    PostgreSQL 14 (webapp-db)         │  port 5432 (internal)
│    Volume: postgres_data             │
└──────────────────────────────────────┘
```

### 5.2 Authentication Flow

```
Browser                FastAPI                  PostgreSQL
  │                      │                           │
  │── POST /api/auth/login ──▶│                      │
  │   {username, password}    │── SELECT user ──────▶│
  │                           │◀── user row ─────────│
  │                           │ bcrypt.verify()       │
  │                           │ [if TOTP] return      │
  │                           │  {totp_required:true} │
  │◀── {access_token} ────────│                       │
  │    localStorage.set()     │                       │
  │                           │                       │
  │── GET /api/auth/me ───────▶│                      │
  │   Authorization: Bearer   │── SELECT user ──────▶│
  │                           │◀── user+role ─────────│
  │◀── UserResponse ──────────│                       │
```

### 5.3 API Key Authentication Flow

```
Client                 FastAPI                  PostgreSQL
  │                      │                           │
  │── GET /api/... ──────▶│                          │
  │   X-API-Key: mpk_xxx  │                          │
  │                       │── SELECT api_keys        │
  │                       │   WHERE key_prefix='mpk_x'──▶│
  │                       │◀── candidate rows ────────│
  │                       │ bcrypt.verify(key, hash)  │
  │                       │── UPDATE last_used ──────▶│
  │◀── 200 OK ────────────│                           │
```

### 5.4 Deployment Models

| Model | TLS | Entry Point | Docker Profile |
|---|---|---|---|
| Development | None | `http://localhost:8080` | *(default)* |
| Production | Let's Encrypt (Caddy) | `https://yourdomain.com` | `--profile proxy` |
| Kubernetes | Ingress controller | Configurable | N/A |

---

## 6. Data Model

### 6.1 Entity Relationship Summary

```
roles ──── (1:N) ──── users ──── (1:N) ──── user_sessions
                        │
                        ├── (1:N) ──── api_keys
                        ├── (1:N) ──── system_logs
                        ├── (1:N) ──── backups
                        ├── (1:N) ──── password_reset_tokens
                        └── (1:N) ──── invitations (created_by / used_by)
```

### 6.2 Table Specifications

#### `roles`
| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | SERIAL | PK | |
| `name` | VARCHAR(50) | UNIQUE NOT NULL | Seeded: `viewer`, `editor`, `manager` |
| `permissions` | JSONB | NOT NULL DEFAULT `[]` | Array of scope strings |
| `description` | VARCHAR(255) | | |
| `created_at` | TIMESTAMP | NOT NULL DEFAULT now() | |
| `updated_at` | TIMESTAMP | NOT NULL DEFAULT now() | |

#### `users`
| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | SERIAL | PK | |
| `username` | VARCHAR(50) | UNIQUE NOT NULL | |
| `email` | VARCHAR(100) | UNIQUE NOT NULL | |
| `hashed_password` | VARCHAR(255) | NOT NULL | bcrypt, work factor 12 |
| `is_admin` | BOOLEAN | NOT NULL DEFAULT false | Superuser flag |
| `is_active` | BOOLEAN | NOT NULL DEFAULT true | Disabled users cannot authenticate |
| `permissions` | JSON | | Per-user additive scope overrides |
| `last_login` | TIMESTAMP | | |
| `email_verified` | BOOLEAN | NOT NULL DEFAULT false | |
| `email_verification_token` | VARCHAR(128) | INDEXED | |
| `email_verification_expires` | TIMESTAMP | | |
| `oauth_provider` | VARCHAR(50) | | `google` or `github` |
| `oauth_user_id` | VARCHAR(255) | | Provider user ID |
| `totp_secret` | VARCHAR(64) | | Base32 TOTP secret |
| `totp_enabled` | BOOLEAN | NOT NULL DEFAULT false | |
| `role_id` | INTEGER | FK → roles.id SET NULL | RBAC role assignment |
| `display_name` | VARCHAR(100) | | |
| `bio` | TEXT | | |
| `avatar_path` | VARCHAR(255) | | Relative path under `/static/avatars/` |
| `timezone` | VARCHAR(50) | DEFAULT `UTC` | |
| `language` | VARCHAR(10) | DEFAULT `en` | |

#### `user_sessions`
| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | UUID | PK | |
| `user_id` | INTEGER | FK → users.id CASCADE | |
| `jti` | UUID | UNIQUE NOT NULL | JWT ID claim |
| `device_info` | VARCHAR(512) | | User-Agent string |
| `ip_address` | VARCHAR(50) | | |
| `created_at` | TIMESTAMP | NOT NULL | |
| `last_used` | TIMESTAMP | NOT NULL | Updated on each authenticated request |
| `expires_at` | TIMESTAMP | NOT NULL | |
| `is_revoked` | BOOLEAN | NOT NULL DEFAULT false | |

#### `api_keys`
| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | UUID | PK | |
| `user_id` | INTEGER | FK → users.id CASCADE | |
| `name` | VARCHAR(100) | NOT NULL | Human-readable label |
| `key_hash` | VARCHAR(255) | NOT NULL | bcrypt hash of full key |
| `key_prefix` | VARCHAR(10) | NOT NULL INDEXED | First 10 chars for lookup |
| `scopes` | JSONB | NOT NULL DEFAULT `[]` | Reserved for future scope restriction |
| `last_used` | TIMESTAMP | | |
| `expires_at` | TIMESTAMP | | NULL = never expires |
| `is_active` | BOOLEAN | NOT NULL DEFAULT true | |
| `created_at` | TIMESTAMP | NOT NULL | |

#### `invitations`
| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | UUID | PK | |
| `token` | VARCHAR(64) | UNIQUE NOT NULL INDEXED | 64-char hex token |
| `email` | VARCHAR(100) | | Optional target email |
| `created_by` | INTEGER | FK → users.id CASCADE | |
| `used_by` | INTEGER | FK → users.id SET NULL | NULL = not yet used |
| `expires_at` | TIMESTAMP | NOT NULL | |
| `created_at` | TIMESTAMP | NOT NULL | |
| `used_at` | TIMESTAMP | | NULL = not yet used |

#### `system_logs`
| Column | Type | Notes |
|---|---|---|
| `id` | SERIAL PK | |
| `level` | VARCHAR(20) | `INFO`, `WARNING`, `ERROR`, `CRITICAL` |
| `message` | TEXT | |
| `user_id` | INTEGER FK | Nullable |
| `action` | VARCHAR(100) | Event category |
| `details` | JSON | Structured context |
| `ip_address` | VARCHAR(50) | |
| `created_at` | TIMESTAMP | |

#### `app_config`
| Column | Type | Notes |
|---|---|---|
| `id` | SERIAL PK | |
| `key` | VARCHAR(100) UNIQUE | Config key (e.g. `app_name`, `invite_only`) |
| `value` | TEXT | |
| `created_at` / `updated_at` | TIMESTAMP | |

---

## 7. API Specification

### 7.1 Authentication Endpoints (`/api/auth`)

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/register` | Public | Register a new user (invite token required if `INVITE_ONLY=true`) |
| POST | `/login` | Public | Login with username + password; returns JWT |
| POST | `/logout` | Bearer | Revoke current session |
| GET | `/me` | Bearer / API Key | Return current user profile |
| POST | `/verify-email` | Public | Consume email verification token |
| POST | `/resend-verification` | Bearer | Re-send verification email |
| POST | `/forgot-password` | Public | Send password reset email |
| POST | `/reset-password` | Public | Consume reset token and set new password |
| GET | `/sessions` | Bearer | List active sessions |
| DELETE | `/sessions/{id}` | Bearer | Revoke a specific session |
| DELETE | `/sessions/all` | Bearer | Revoke all sessions |
| POST | `/totp/setup` | Bearer | Begin TOTP setup; returns QR code and secret |
| POST | `/totp/enable` | Bearer | Confirm TOTP setup with a code |
| POST | `/totp/verify` | Public | Submit TOTP code during login |
| POST | `/totp/disable` | Bearer | Disable TOTP with a confirmation code |
| GET | `/profile` | Bearer / API Key | Get current user's profile |
| PUT | `/profile` | Bearer / API Key | Update display name, bio, timezone, language |
| POST | `/profile/avatar` | Bearer | Upload avatar image (multipart) |
| GET | `/api-keys` | Bearer | List own API keys |
| POST | `/api-keys` | Bearer | Create a new API key |
| PATCH | `/api-keys/{id}` | Bearer | Rename or toggle a key |
| DELETE | `/api-keys/{id}` | Bearer | Delete a key |
| GET | `/invite/validate` | Public | Validate an invitation token |
| GET | `/oauth/providers` | Public | List configured OAuth providers |
| GET | `/oauth/{provider}` | Public | Initiate OAuth login |
| GET | `/oauth/{provider}/callback` | Public | OAuth callback handler |

### 7.2 Admin Endpoints (`/api/admin`)

| Method | Path | Required Permission | Description |
|---|---|---|---|
| GET | `/check-first-run` | Public | Returns `{is_first_run: bool}` |
| POST | `/setup` | Public (first-run only) | Create initial admin account |
| GET | `/config` | Public | Returns app name and invite_only flag |
| PUT | `/config` | Admin | Update app-level config |
| GET | `/users` | `users:read` | List all users with role |
| POST | `/users` | Admin | Create a user |
| PUT | `/users/{id}` | Admin | Update a user |
| DELETE | `/users/{id}` | Admin | Delete a user |
| GET | `/logs` | `logs:read` | Paginated system logs |
| GET | `/system-info` | `system:read` | CPU, memory, disk, service status |
| GET | `/backups` | `backups:read` | List backups |
| POST | `/backups` | `backups:write` | Create a backup |
| GET | `/roles` | `roles:manage` | List all roles |
| POST | `/roles` | Admin | Create a role |
| PUT | `/roles/{id}` | Admin | Update a role |
| DELETE | `/roles/{id}` | Admin | Delete a role (403 if users assigned) |
| GET | `/invitations` | `invitations:manage` | List invitations |
| POST | `/invitations` | `invitations:manage` | Create an invitation |
| DELETE | `/invitations/{id}` | `invitations:manage` | Delete an unused invitation |

### 7.3 Response Formats

All endpoints return `application/json`. Error responses follow the structure:
```json
{ "detail": "Human-readable error message" }
```

Validation errors return HTTP 422 with per-field details:
```json
{
  "detail": [
    { "loc": ["body", "password"], "msg": "...", "type": "value_error" }
  ]
}
```

---

## 8. Security Requirements

### 8.1 Transport Security

| ID | Requirement |
|---|---|
| SR-001 | Production deployments shall terminate TLS at Caddy using a certificate from Let's Encrypt (ACME) or a user-supplied PEM/PFX |
| SR-002 | The Caddy configuration shall enforce TLS 1.2 minimum (Caddy 2 default) |
| SR-003 | All HTTP responses shall include `Strict-Transport-Security: max-age=31536000; includeSubDomains; preload` |

### 8.2 Authentication and Session Management

| ID | Requirement |
|---|---|
| SR-010 | JWT tokens shall be signed with HS256 using a `SECRET_KEY` of at least 256 bits (32 bytes) |
| SR-011 | The `SECRET_KEY` shall be generated with `secrets.token_urlsafe(32)` if not supplied; a randomly generated key is used per process start |
| SR-012 | Token expiry shall default to 30 minutes; configurable via `ACCESS_TOKEN_EXPIRE_MINUTES` |
| SR-013 | Login attempts shall be rate-limited to 5 per 5-minute window per IP address (configurable) |
| SR-014 | All requests shall be rate-limited to 100 per 60-second window per IP address (configurable) |
| SR-015 | OAuth CSRF state shall be stored in a signed server-side session cookie (itsdangerous) |

### 8.3 Password Policy

| ID | Requirement |
|---|---|
| SR-020 | Minimum password length: 12 characters (configurable via `PASSWORD_MIN_LENGTH`) |
| SR-021 | Maximum password length: 128 characters (OWASP ASVS 2.1.2) |
| SR-022 | Passwords shall require uppercase, lowercase, digit, and special character by default (each configurable) |
| SR-023 | Passwords shall be rejected if they contain common patterns |
| SR-024 | All passwords shall be hashed using bcrypt with work factor 12 |

### 8.4 Security Headers

All responses shall include:

| Header | Value |
|---|---|
| `X-Frame-Options` | `DENY` |
| `X-Content-Type-Options` | `nosniff` |
| `X-XSS-Protection` | `1; mode=block` |
| `Strict-Transport-Security` | `max-age=31536000; includeSubDomains; preload` |
| `Content-Security-Policy` | Whitelist: `self`, jsdelivr.net, cdnjs.cloudflare.com |
| `Referrer-Policy` | `strict-origin-when-cross-origin` |
| `Permissions-Policy` | Deny geolocation, microphone, camera, payment |
| `Server` | `Secure` (obfuscated) |

### 8.5 Input Validation and File Upload

| ID | Requirement |
|---|---|
| SR-030 | All user-supplied text inputs shall be sanitized: truncated to max length, null bytes removed, HTML special characters escaped |
| SR-031 | File uploads (avatars) shall be validated for: size (≤ 2 MB for avatars, ≤ 5 MB general), extension (`.jpg`, `.jpeg`, `.png`, `.webp`), MIME type, and path traversal |
| SR-032 | Uploaded filenames shall be replaced with a cryptographically random name; original filename is discarded |

### 8.6 CORS and Trusted Hosts

| ID | Requirement |
|---|---|
| SR-040 | CORS allowed origins shall be an explicit whitelist set via `CORS_ORIGINS`; wildcard (`*`) is prohibited |
| SR-041 | Allowed CORS methods: `GET`, `POST`, `PUT`, `DELETE`, `OPTIONS` |
| SR-042 | Allowed CORS headers: `Authorization`, `Content-Type`, `X-Requested-With`, `X-API-Key` |
| SR-043 | Trusted hosts shall be set via `TRUSTED_HOSTS`; requests with unexpected `Host` headers are rejected |

### 8.7 Audit Logging

| ID | Requirement |
|---|---|
| SR-050 | The system shall log all authentication events (login success/failure, logout, TOTP, OAuth) |
| SR-051 | The system shall log all admin actions (user create/edit/delete, config changes, backup creation) |
| SR-052 | Each log entry shall include: timestamp, level, message, user_id (if known), action category, IP address |

### 8.8 Container Security

| ID | Requirement |
|---|---|
| SR-060 | The application container shall run as a non-root user (`appuser`, UID 1000) |
| SR-061 | The Docker API docs (`/docs`, `/redoc`) shall be disabled in production (`ENVIRONMENT=production`) |
| SR-062 | The Docker socket shall not be mounted into the container by default |

---

## 9. Infrastructure Requirements

### 9.1 Docker Compose (Development)

```
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d
```

| Service | Image | Port | Role |
|---|---|---|---|
| `webapp-db` | `postgres:14-alpine` | 5432 (internal) | Database |
| `webapp-web` | Built from `Dockerfile` | 8080 → 8000 | Application |

### 9.2 Docker Compose (Production)

```
docker compose --profile proxy up -d
```

| Service | Image | Port | Role |
|---|---|---|---|
| `webapp-db` | `postgres:14-alpine` | 5432 (internal) | Database |
| `webapp-web` | Built from `Dockerfile` | 8000 (internal) | Application |
| `webapp-caddy` | `caddy:2-alpine` | 80, 443 | TLS reverse proxy |

### 9.3 Dockerfile Requirements

| Requirement | Detail |
|---|---|
| Base image | `python:3.11-slim` |
| System packages | `gcc`, `python3-dev`, `postgresql-client`, `libpng-dev`, `libjpeg-dev`, `zlib1g-dev` |
| Runtime user | `appuser` (UID 1000, non-root) |
| Exposed port | 8000 |
| Health check | `GET http://localhost:8000/health`; interval 30 s, timeout 10 s, start period 40 s |
| Persistent dirs | `/app/backups`, `/app/certs` (created at build time) |

### 9.4 PostgreSQL Requirements

| Requirement | Value |
|---|---|
| Version | 14 (Alpine) |
| Default database | `webapp` |
| Default user | `postgres` |
| Data volume | `postgres_data` (named Docker volume) |
| Health check | `pg_isready -U postgres`; interval 10 s, retries 5 |

### 9.5 Python Dependencies

| Package | Version | Purpose |
|---|---|---|
| `fastapi` | 0.115.0 | Web framework |
| `uvicorn[standard]` | 0.32.0 | ASGI server |
| `pydantic` | 2.9.0 | Request/response validation |
| `sqlalchemy` | 2.0.23 | Async ORM |
| `asyncpg` | 0.29.0 | Async PostgreSQL driver |
| `pydantic-settings` | 2.1.0 | Config management |
| `python-jose[cryptography]` | 3.3.0 | JWT signing/verification |
| `passlib[bcrypt]` | 1.7.4 | Password hashing |
| `bcrypt` | 4.1.2 | bcrypt backend |
| `python-multipart` | 0.0.6 | File upload support |
| `psutil` | 5.9.8 | System resource monitoring |
| `aiosmtplib` | 3.0.1 | Async SMTP (email) |
| `authlib` | 1.3.1 | OAuth 2.0 client |
| `httpx` | 0.27.0 | Async HTTP (OAuth) |
| `itsdangerous` | 2.2.0 | Signed session cookies |
| `pyotp` | 2.9.0 | TOTP generation/verification |
| `qrcode[pil]` | 7.4.2 | TOTP QR code generation |
| `Pillow` | 10.3.0 | Avatar image processing |

### 9.6 Kubernetes

- Manifests are provided in `k8s/`; Kubernetes ≥ 1.20 required
- A Minikube helper script is available at `scripts/deploy-to-minikube.sh`
- TLS termination must be provided by an Ingress controller (not Caddy) in Kubernetes deployments

---

## 10. Environment Configuration

### 10.1 Core

| Variable | Default | Required | Description |
|---|---|---|---|
| `SECRET_KEY` | *(auto-generated)* | Recommended | JWT and session signing key; 256-bit minimum |
| `DATABASE_URL` | `postgresql+asyncpg://postgres:postgres@db:5432/webapp` | Yes | asyncpg connection string |
| `ENVIRONMENT` | `development` | No | Set to `production` to disable `/docs` and `/redoc` |
| `APP_BASE_URL` | `http://localhost:8080` | No | Base URL used in email links and invite links |

### 10.2 CORS and Trusted Hosts

| Variable | Default | Description |
|---|---|---|
| `CORS_ORIGINS` | `http://localhost:8080,http://127.0.0.1:8080` | Comma-separated allowed origins |
| `TRUSTED_HOSTS` | `localhost,127.0.0.1,*.localhost` | Comma-separated trusted Host values |

### 10.3 Authentication

| Variable | Default | Description |
|---|---|---|
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | JWT token lifetime in minutes |
| `REQUIRE_JTI` | `false` | `true` = strict session tracking via JTI in DB |
| `FORCE_EMAIL_VERIFICATION` | `false` | `true` = block unverified users on every request |
| `INVITE_ONLY` | `false` | `true` = registration requires a valid invitation token |

### 10.4 Security

| Variable | Default | Description |
|---|---|---|
| `SECURITY_HEADERS_ENABLED` | `true` | Enable security headers middleware |
| `RATE_LIMIT_ENABLED` | `true` | Enable rate limiting middleware |
| `RATE_LIMIT_REQUESTS` | `100` | Max requests per window (global) |
| `RATE_LIMIT_WINDOW_SECONDS` | `60` | Global rate limit window in seconds |
| `LOGIN_RATE_LIMIT` | `5` | Max login attempts per window |
| `LOGIN_RATE_WINDOW` | `300` | Login rate limit window in seconds |
| `PASSWORD_MIN_LENGTH` | `12` | Minimum password length |
| `PASSWORD_REQUIRE_UPPERCASE` | `true` | Enforce uppercase in passwords |
| `PASSWORD_REQUIRE_LOWERCASE` | `true` | Enforce lowercase in passwords |
| `PASSWORD_REQUIRE_DIGITS` | `true` | Enforce digits in passwords |
| `PASSWORD_REQUIRE_SPECIAL` | `true` | Enforce special characters in passwords |
| `MAX_FILE_SIZE` | `5242880` (5 MB) | Maximum upload size in bytes |

### 10.5 Email (SMTP)

| Variable | Default | Description |
|---|---|---|
| `SMTP_HOST` | *(unset)* | SMTP hostname; leave blank to print links to stdout |
| `SMTP_PORT` | `587` | SMTP port |
| `SMTP_USER` | *(unset)* | SMTP username |
| `SMTP_PASSWORD` | *(unset)* | SMTP password |
| `SMTP_FROM` | *(unset)* | Sender address |
| `SMTP_TLS` | `true` | Use STARTTLS |

### 10.6 OAuth 2.0

| Variable | Description |
|---|---|
| `GOOGLE_CLIENT_ID` | Google OAuth 2.0 client ID |
| `GOOGLE_CLIENT_SECRET` | Google OAuth 2.0 client secret |
| `GITHUB_CLIENT_ID` | GitHub OAuth App client ID |
| `GITHUB_CLIENT_SECRET` | GitHub OAuth App client secret |

### 10.7 Caddy / TLS

| Variable | Default | Description |
|---|---|---|
| `CADDY_DOMAIN` | `localhost` | Domain for TLS certificate |
| `CADDY_EMAIL` | `admin@example.com` | Let's Encrypt ACME account email |

### 10.8 Backup

| Variable | Default | Description |
|---|---|---|
| `BACKUP_DIR` | `/app/backups` | Local backup directory |
| `BACKUP_RETENTION_DAYS` | `30` | Days before backups are eligible for pruning |
| `SMB_BACKUP_ENABLED` | `false` | Enable SMB/CIFS backup replication |
| `SMB_HOST` | *(unset)* | SMB server hostname |
| `SMB_SHARE` | *(unset)* | SMB share name |
| `SMB_USERNAME` | *(unset)* | SMB username |
| `SMB_PASSWORD` | *(unset)* | SMB password |
| `SMB_MOUNT_POINT` | `/mnt/smb_backups` | Container mount point |
| `NFS_BACKUP_ENABLED` | `false` | Enable NFS backup replication |
| `NFS_HOST` | *(unset)* | NFS server hostname |
| `NFS_EXPORT` | *(unset)* | NFS export path |
| `NFS_MOUNT_POINT` | `/mnt/nfs_backups` | Container mount point |

---

## 11. Constraints and Assumptions

### 11.1 Constraints

- **Single-database**: The system uses PostgreSQL exclusively; no support for other databases without significant ORM changes
- **In-process rate limiting**: Rate limit state is held in application memory; not shared across multiple uvicorn workers or container replicas
- **Synchronous backup**: `pg_dump` runs synchronously in the web process; large databases may cause request timeouts
- **Avatar storage on disk**: Avatars are stored in `static/avatars/` within the container; they will be lost if the container is recreated without a mounted volume
- **Bootstrap 5.3 CDN**: The frontend depends on Bootstrap and Bootstrap Icons loaded from the jsdelivr.net CDN; offline deployments require self-hosting these assets
- **`admin` is not a DB role**: The superuser flag is `users.is_admin` (boolean); it does not correspond to any row in the `roles` table

### 11.2 Assumptions

- A PostgreSQL 14 instance is available and reachable from the application container via the `DATABASE_URL`
- For production HTTPS, DNS for the configured `CADDY_DOMAIN` points to the host running Caddy before the first container start (required for ACME challenge)
- The operator supplies a strong `SECRET_KEY` in production; the auto-generated key changes on every container restart, invalidating all existing JWTs
- Email features (verification, password reset) require a valid SMTP relay; without one, links are printed to stdout (development mode)
- Avatar images written to `static/avatars/` are served by FastAPI's StaticFiles mount and are accessible without authentication

---

*Document prepared from source code analysis of Web Platform Template v1.2.0.*
*Last reviewed: 2026-02-24*
