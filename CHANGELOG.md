# Changelog

All notable changes to this project will be documented in this file.

## [1.2.1] - 2026-03-02

### Changed — dependency upgrades
- **Python base image**: 3.11-slim → 3.13-slim
- **PostgreSQL**: 14-alpine → 18-alpine  ⚠️ *Existing deployments must dump and restore data before upgrading — PostgreSQL does not auto-upgrade volumes across major versions*
- **FastAPI**: 0.115.0 → 0.135.1
- **uvicorn**: 0.32.0 → 0.41.0
- **pydantic** / **pydantic-settings** / **pydantic[email]**: 2.9.0 / 2.1.0 → 2.12.5 / 2.13.1
- **email-validator**: 2.1.0 → 2.3.0
- **SQLAlchemy**: 2.0.23 → 2.0.48
- **asyncpg**: 0.29.0 → 0.31.0
- **python-jose**: 3.3.0 → 3.5.0
- **bcrypt**: 4.1.2 → 5.0.0
- **python-multipart**: 0.0.6 → 0.0.22
- **alembic**: 1.13.1 → 1.18.4
- **psutil**: 5.9.8 → 7.2.2
- **requests**: 2.31.0 → 2.32.5
- **aiosmtplib**: 3.0.1 → 5.1.0
- **authlib**: 1.3.1 → 1.6.9
- **httpx**: 0.27.0 → 0.28.1
- **qrcode**: 7.4.2 → 8.2
- **Pillow**: 10.3.0 → 12.1.1
- **Bootstrap**: 5.3.0 → 5.3.8 (CDN in all HTML pages)
- **Bootstrap Icons**: 1.11.0 → 1.13.1 (CDN in all HTML pages)

---

## [1.2.0] - 2026-02-24

### Added
- **Role-Based Access Control (RBAC)** — Named roles (`viewer`, `editor`, `manager`) with per-role JSON permission arrays; seeded at migration time
- **Permission scopes** — `require_permission(scope)` dependency factory enforced at the router level; admins bypass scope checks; non-admins check their role's permissions plus any user-level overrides
- **User profiles** — `GET/PUT /api/auth/profile` for display name, bio, timezone, and language; avatar upload (`POST /api/auth/profile/avatar`) stored as 200×200 JPEG in `static/avatars/`
- **API key management** — Users can generate `mpk_`-prefixed long-lived keys; stored as bcrypt hashes with a searchable prefix index; full CRUD at `/api/auth/api-keys`; `X-API-Key` header accepted alongside JWT Bearer auth
- **Invite-only registration** — `INVITE_ONLY=true` env var; admins create single-use invitation tokens via `/api/admin/invitations`; tokens consumed atomically on registration; invite link format `?invite=<token>`
- **Admin portal — Invitations section** — Create, list, copy invite links, and revoke unused invitations
- **Admin portal — Role assignment** — Users table shows Display Name and Role columns; Edit User modal includes role dropdown populated from the roles API
- **New routers**: `app/routers/roles.py`, `app/routers/api_keys.py`, `app/routers/invitations.py`
- **New module**: `app/permissions.py`
- **Migration**: `migrations/004_phase2.sql` — `roles`, `api_keys`, `invitations` tables; five new columns on `users`

### Fixed
- Legacy `.modal { display: flex; }` CSS rule in `styles.css` was overriding Bootstrap 5.3's `.modal { display: none; }`, causing all Bootstrap modals to render as permanent full-screen dark overlays and blocking interaction with the login form

---

## [1.1.0] - 2026-01-22

### Added
- **HTTPS / TLS** — Caddy 2 reverse proxy with automatic Let's Encrypt certificate provisioning and renewal
- **Certificate management UI** — Admin portal section to view certificate status, trigger manual renewal, and upload custom PEM/PFX certificates
- **Email verification** — Users must confirm their email address before accessing the app; configurable via `FORCE_EMAIL_VERIFICATION`
- **Password reset** — "Forgot password" flow with time-limited, single-use reset tokens delivered via email (or printed to stdout in dev)
- **OAuth 2.0 / social login** — Sign in with Google and GitHub via `authlib`; provider buttons shown automatically when credentials are configured
- **Two-factor authentication (TOTP)** — QR code setup, enable/disable flow, enforced at login when enabled
- **Active session management** — Users can view and revoke individual JWT sessions from their profile; `REQUIRE_JTI=true` enables strict session tracking
- **Customizable dashboard** — Show/hide built-in cards; add custom cards with title, body, icon, and optional link
- **Administrator self-editing** — Admins can change their own username, email, and password from the admin portal

---

## [1.0.0] - Initial Release

### Added
- User authentication (register/login) with JWT tokens and bcrypt password hashing
- Admin portal with user management, system monitoring, and database backups
- Initial setup wizard for first-run admin account creation and app name configuration
- Security middleware: rate limiting, security headers, CORS whitelist, trusted hosts
- Docker and Docker Compose support
- Kubernetes deployment manifests (with Minikube support)
- Automated deployment scripts
- Light/Dark/System theme support
- Health check endpoint
