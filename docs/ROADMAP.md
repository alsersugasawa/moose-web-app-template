# Web Platform Template — Feature Roadmap

Features are organized into phases by theme. Items within each phase are roughly prioritized top-to-bottom. Contributions are welcome.

---

## Phase 1 — Authentication & Identity ✅

Strengthen the existing auth system with standard account-security features.

- [x] **HTTPS support & certificate management** — TLS termination with automatic certificate provisioning (Let's Encrypt / ACME), renewal, and a UI in the admin portal to view certificate status, expiry, trigger manual renewal, and upload or replace custom certificates (PEM/PFX) directly from the UI
- [x] **Email verification** — Require users to confirm their email address on registration before accessing the app
- [x] **Password reset via email** — "Forgot password" flow with time-limited, single-use reset tokens
- [x] **OAuth 2.0 / social login** — Sign in with Google, GitHub, etc. via the `authlib` library
- [x] **Two-factor authentication (TOTP)** — Time-based one-time passwords (e.g. Google Authenticator, Authy)
- [x] **Active session management** — Let users view and revoke their active JWT sessions from their profile page

---

## Phase 2 — User Management & Access Control ✅

Move beyond the binary `is_admin` flag to a proper permission model.

- [x] **Role-Based Access Control (RBAC)** — Define named roles (e.g. `viewer`, `editor`, `manager`) and assign them to users
- [x] **Permission scopes** — Attach fine-grained action permissions to each role, enforced at the router level
- [x] **User profile pages** — Avatar upload, display name, bio, and per-user preferences (theme, timezone, language)
- [x] **API key management** — Allow users to generate long-lived API keys for programmatic/service access
- [x] **Invite-only registration** — Admin-issued invitation tokens that gate new user sign-ups

---

## Phase 3 — Developer Experience ✅

Make the template easier to extend and customize.

- [x] **Scaffold CLI** — `python -m scaffold router <name>` to generate a boilerplate router + schema + migration
- [x] **Auto-generated TypeScript client** — Export an OpenAPI-derived TypeScript SDK for frontend consumption
- [x] **Plugin architecture** — A conventions-based `plugins/` directory that auto-registers routers and models on startup
- [x] **Feature flags** — Database-backed on/off switches per feature, configurable from the admin portal
- [x] **Environment config profiles** — First-class `development`, `staging`, and `production` config sets via `.env.<env>` files

---

## Phase 4 — Infrastructure & Scalability ✅

Prepare the platform for production load.

- [x] **Redis caching layer** — Cache frequently-read query results and rate-limit counters in Redis
- [x] **Background task queue** — Async job processing (ARQ) for emails, exports, and long-running work
- [x] **WebSocket support** — Real-time push notifications and live data updates via WebSocket connections
- [x] **Database read replica routing** — Route read queries to a replica for horizontal read scaling
- [x] **Connection pool tuning** — `asyncpg` pool settings exposed via environment variables

---

## Phase 5 — Observability & Operations ✅

Instrument the application for production visibility.

- [x] **Structured JSON logging** — Replace print-based logging with structured JSON output compatible with log aggregators (Loki, Datadog, CloudWatch)
- [x] **Prometheus metrics endpoint** — `/metrics` endpoint exposing request counts, latency histograms, and DB pool stats
- [x] **OpenTelemetry tracing** — Distributed trace context propagation across services via OTLP export
- [x] **Sentry integration** — Automatic error capture and performance tracing with a configurable DSN
- [x] **Enhanced health check** — `/health/detailed` endpoint that reports the status of all dependencies (DB, cache, queue)
- [x] **Automated migration runner** — Run pending SQL migrations on container startup before the app starts accepting traffic

---

## Phase 6 — Communication & Events

Build out messaging and integration capabilities.

- [ ] **Transactional email** — SMTP / SendGrid / Mailgun integration for verification, password reset, and notification emails
- [ ] **In-app notification system** — Per-user notification inbox with read/unread state, stored in the database
- [ ] **Webhook delivery** — Allow users to register URLs that receive signed POST payloads on defined events
- [ ] **Internal event bus** — Decouple components with a lightweight publish/subscribe system for domain events

---

## Phase 7 — File Storage

Add managed file and asset handling.

- [ ] **S3-compatible storage** — Store user-uploaded files in S3 / MinIO / Cloudflare R2 with presigned URL generation
- [ ] **Image processing** — Automatic resize and thumbnail generation on upload via `Pillow`
- [ ] **File management UI** — Admin portal view for browsing, downloading, and deleting stored files

---

## Phase 8 — Frontend & UX

Modernize and expand the frontend options.

- [ ] **SPA starter option** — Provide an opt-in React (Vite) or SvelteKit frontend that consumes the existing REST API
- [ ] **Internationalization (i18n)** — String extraction, locale detection, and language-switching UI
- [ ] **Accessibility audit** — Bring all pages to WCAG 2.1 AA compliance; add keyboard navigation and screen-reader support
- [ ] **Progressive Web App (PWA)** — Add a service worker and web manifest so the app can be installed and used offline

---

## Completed

| Feature | Version |
|---|---|
| JWT authentication (register/login) | v1.0.0 |
| Admin portal (user management, monitoring, backups) | v1.0.0 |
| Initial setup wizard | v1.0.0 |
| Security middleware (rate limiting, headers, CORS) | v1.0.0 |
| Docker & Docker Compose support | v1.0.0 |
| Kubernetes manifests + Minikube deploy script | v1.0.0 |
| Light / Dark / System theme | v1.0.0 |
| HTTPS support & certificate management (Caddy + admin UI) | v1.1.0 |
| Email verification (registration flow) | v1.1.0 |
| Password reset via email (forgot-password flow) | v1.1.0 |
| OAuth 2.0 / social login (Google, GitHub) | v1.1.0 |
| Two-factor authentication — TOTP | v1.1.0 |
| Active session management (view & revoke JWT sessions) | v1.1.0 |
| Customizable user dashboard (show/hide cards, custom cards) | v1.1.0 |
| Administrator account self-editing (username, email, password) | v1.1.0 |
| Role-Based Access Control — named roles with permission scopes | v1.2.0 |
| User profile pages — avatar, display name, bio, timezone, language | v1.2.0 |
| API key management — `mpk_` prefixed keys, bcrypt-hashed | v1.2.0 |
| Invite-only registration — admin-issued single-use tokens | v1.2.0 |
| Admin portal — Invitations section + role assignment in user editor | v1.2.0 |
| Scaffold CLI — `python -m scaffold router <name>` | v1.3.0 |
| Auto-generated TypeScript client — `/api/admin/export/typescript-client` | v1.3.0 |
| Plugin architecture — `plugins/` directory with auto-registration | v1.3.0 |
| Feature flags — database-backed on/off switches, admin UI | v1.3.0 |
| Environment config profiles — `.env.development/.staging/.production` | v1.3.0 |
| Redis caching layer — hot query cache + distributed rate limiting | v1.4.0 |
| Background task queue — ARQ async email delivery with retry | v1.4.0 |
| WebSocket support — live admin stats + per-user notification channel | v1.4.0 |
| Database read replica routing — `get_read_db()` with transparent fallback | v1.4.0 |
| Connection pool tuning — `DB_POOL_SIZE`, `DB_MAX_OVERFLOW`, etc. | v1.4.0 |
| Structured JSON logging — `python-json-logger`, per-request access log middleware | v1.5.0 |
| Prometheus metrics — `/metrics` with request counter, latency histogram, DB pool gauges | v1.5.0 |
| OpenTelemetry tracing — FastAPI + SQLAlchemy auto-instrumentation, OTLP export | v1.5.0 |
| Sentry integration — error capture + performance tracing via configurable DSN | v1.5.0 |
| Enhanced health check — `/health/detailed` reports DB, Redis, ARQ queue status | v1.5.0 |
| Automated migration runner — `AUTO_MIGRATE=true` applies pending `.sql` files on startup | v1.5.0 |
