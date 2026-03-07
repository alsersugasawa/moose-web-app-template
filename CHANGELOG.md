# Changelog

All notable changes to this project will be documented in this file.

## [1.8.0] - 2026-03-05

### Added — Phase 8: Frontend & UX

#### Progressive Web App (`static/manifest.json`, `static/service-worker.js`)
- Web App Manifest: `name`, `short_name`, `theme_color` (#667eea), `display: standalone`, icon slots, and two shortcuts (Dashboard, Admin)
- Service worker with a **cache-first** strategy for `/static/*` assets and a **network-first** strategy for `/api/*` calls; offline fallback returns a structured JSON error for API requests
- Service worker registered on every page (`index.html`, `admin.html`, `admin-login.html`, `setup.html`) via a non-blocking `load` event listener
- `<link rel="manifest">` and `<meta name="theme-color">` added to all HTML pages

#### Internationalization — `static/i18n.js` + locale files
- Lightweight zero-dependency i18n module: locale detection from `localStorage` → `navigator.language` → `'en'` fallback
- `I18n.init()` — loads locale JSON and applies translations before first render
- `I18n.setLocale(locale)` — switches language at runtime, persists to `localStorage`, re-applies DOM translations
- `I18n.t(key, fallback)` — programmatic key lookup
- DOM-driven translation via `data-i18n`, `data-i18n-placeholder`, `data-i18n-aria-label`, and `data-i18n-title` attributes
- Locale files for **English** (`en`), **Spanish** (`es`), and **French** (`fr`) at `static/locales/`; covers ~40 UI strings
- `app.js`: `I18n.init()` called before any rendering; profile-save handler calls `I18n.setLocale()` when language changes
- `admin.html`: nav links annotated with `data-i18n`; `I18n.init()` called on load

#### Accessibility — WCAG 2.1 AA
- **Skip navigation links** on every page (`<a class="skip-link" href="#main-content">`) — visible on keyboard focus (WCAG 2.4.1)
- **ARIA landmarks**: `role="main"`, `role="banner"`, `role="navigation"` with `aria-label` on all pages
- **`aria-live` regions**: every error message (`role="alert" aria-live="assertive"`) and success/status message (`role="status" aria-live="polite"`) in `index.html` and `admin-login.html`
- **`aria-required="true"`** on all required form fields; `autocomplete` attributes set throughout auth forms
- **`novalidate`** on forms where custom error UI is used; removes confusing browser-native bubbles
- Admin portal nav: `role="navigation" aria-label="Admin portal navigation"` wraps the `<nav>`, menu items carry `role="menuitem"`; `admin-username` span has `aria-live="polite"`
- Admin portal: `role="main"` wrapper div (`id="admin-main-content"`) enables skip-link target

#### React / Vite SPA Starter (`frontend/`)
- Opt-in React 18 + Vite 6 single-page app; proxies `/api` and `/ws` to the FastAPI backend in development
- `vite.config.js`: dev server on `:5173`; production build outputs to `static/spa/`
- **Auth context** (`App.jsx`): `AuthProvider` + `useAuth()` hook with `login()` / `logout()` helpers; `RequireAuth` wrapper for protected routes; token verified via `GET /api/auth/me` on mount
- **API client** (`src/api/client.js`): typed `fetch` wrappers for auth, notifications, files, and API keys; automatic `Authorization: Bearer` header injection
- **LoginPage** (`src/pages/LoginPage.jsx`): login / register / forgot-password tabs with field-level errors; language switcher; `i18n.changeLanguage()` on login using user's saved language preference
- **DashboardPage** (`src/pages/DashboardPage.jsx`): overview stats, notifications tab (mark read / mark all read), files tab (upload, download via presigned URL, delete); language switcher in header
- **i18n**: react-i18next with `i18next-http-backend`; loads from `/static/locales/` so the SPA shares translation files with the static pages; locale persisted to `localStorage`
- `frontend/.env.example` documents `VITE_API_BASE`

#### Infrastructure
- `requirements.txt`: no new Python dependencies (Pillow already present; boto3 added in v1.7.0)

---

## [1.7.0] - 2026-03-05

### Added — Phase 7: File Storage

#### S3-Compatible Object Storage (`app/storage.py`)
- `upload_file(key, data, content_type)` — uploads bytes to the configured S3 bucket
- `delete_file(key)` — removes an object from the bucket
- `generate_presigned_url(key, expires_in)` — returns a time-limited GET URL (default: `STORAGE_PRESIGN_EXPIRY` seconds, default 3600)
- `make_thumbnail(data, max_size)` — generates a 256×256 JPEG thumbnail from image bytes using Pillow; returns `None` on non-image input
- All S3 calls dispatched to the thread-pool executor via `asyncio.get_event_loop().run_in_executor()` — non-blocking async interface over the synchronous boto3 SDK
- Supports **AWS S3**, **MinIO**, and **Cloudflare R2** via `STORAGE_ENDPOINT_URL`

#### File REST API (`app/routers/files.py`)
- **User endpoints** (`/api/files/*`, requires authenticated user):
  - `POST /api/files/upload` — multipart upload; 50 MB ceiling; auto-generates a 256×256 JPEG thumbnail for image MIME types (JPEG, PNG, GIF, WebP, BMP, TIFF)
  - `GET /api/files` — list caller's uploaded files
  - `GET /api/files/{id}/url?thumbnail=false` — generate a presigned download URL (original or thumbnail)
  - `DELETE /api/files/{id}` — delete object + thumbnail from S3 and DB record
- **Admin endpoints** (`/api/admin/files/*`, requires admin):
  - `GET /api/admin/files` — list all files across all users
  - `GET /api/admin/files/{id}/url` — presigned URL for any file
  - `DELETE /api/admin/files/{id}` — delete any file

#### `StoredFile` Model (`app/models.py`)
- UUID primary key, `user_id` FK (cascade delete), `filename`, `content_type`, `size_bytes`, `s3_key`, `thumbnail_key` (nullable), `created_at`

#### Migration (`migrations/007_phase7.sql`)
- `stored_files` table with UUID PK (`gen_random_uuid()`), FK to `users`, index on `user_id`

#### Admin Portal — File Management UI (`static/admin.html`, `static/admin.js`)
- New **"Files"** section in the admin navigation
- Stats bar: total file count and aggregate size
- Browsable table: inline 48×48 thumbnail previews (lazy-loaded via presigned URLs), filename, MIME type, size, upload timestamp
- Per-row Download (opens presigned URL in new tab) and Delete (with confirmation) actions
- Graceful "storage not configured" warning when `STORAGE_BUCKET` is unset

#### Settings (`app/settings.py`)
- `STORAGE_BUCKET` — bucket name; empty string disables file storage (returns HTTP 503)
- `STORAGE_ACCESS_KEY` / `STORAGE_SECRET_KEY` — S3 credentials
- `STORAGE_REGION` — e.g. `us-east-1` (empty = SDK default)
- `STORAGE_ENDPOINT_URL` — custom endpoint for MinIO / Cloudflare R2
- `STORAGE_PRESIGN_EXPIRY` — presigned URL lifetime in seconds (default `3600`)

#### Infrastructure
- `requirements.txt`: added `boto3==1.38.0`
- Startup banner: prints File Storage status and bucket name

---

## [1.6.0] - 2026-03-04

### Added — Phase 6: Communication & Events

#### Internal Event Bus (`app/events.py`)
- Lightweight synchronous pub/sub: `on(event, handler)` registers a handler; `emit(event, **data)` calls all registered handlers
- Exceptions in handlers are swallowed — they never crash the caller
- Events emitted: `user.registered` (on register), `user.login` (on successful login)

#### In-App Notification System
- `Notification` ORM model: per-user message inbox with `is_read` flag
- REST endpoints at `/api/notifications`: list, unread count, mark one/all as read, delete
- WebSocket push via `ws_manager.send_to_user()` — existing `/ws/notifications` channel delivers `{"type":"notification","id":...,"message":"..."}` in real time
- ARQ task `create_notification_task` + `enqueue_user_notification()` helper with inline fallback

#### Webhook Delivery
- `Webhook` + `WebhookDelivery` ORM models
- REST CRUD at `/api/webhooks`: register, list, update, delete; `/api/webhooks/{id}/deliveries` for delivery history
- Signing secret auto-generated on creation (`secrets.token_hex(32)`)
- ARQ task `deliver_webhook_task`: POSTs HMAC-SHA256 signed payloads (`X-Webhook-Signature: sha256=...`), logs each delivery attempt
- `enqueue_webhook_delivery()` helper with inline fallback for no-Redis deployments
- Event bus fans out to all active webhooks subscribed to `user.registered` and `user.login`

#### Transactional Email — Welcome Email
- `send_welcome_email_task` ARQ task + `enqueue_welcome_email()` helper
- Sent automatically on `user.registered` event via event bus handler

#### Migration
- `migrations/006_phase6.sql`: `notifications`, `webhooks`, `webhook_deliveries` tables with FK cascade and indexes

## [1.5.0] - 2026-03-03

### Added — Phase 5: Observability & Operations

#### Structured JSON Logging (`app/logging_config.py`)
- `configure_logging(level, fmt)` sets up the root logger with a `python-json-logger` JSON formatter; called first in the FastAPI lifespan so all modules inherit it automatically
- `LOG_LEVEL` (default `INFO`) and `LOG_FORMAT` (`json` | `text`) are new settings; set `LOG_FORMAT=text` in `.env.development` for human-readable dev output
- `RequestLoggingMiddleware` emits one structured JSON line per request: `method`, `path`, `status_code`, `duration_ms`, `client_ip`

#### Prometheus Metrics (`app/metrics.py`)
- `webapp_http_requests_total` counter — labels: `method`, `path`, `status_code`
- `webapp_http_request_duration_seconds` histogram — labels: `method`, `path`; buckets tuned for web latencies
- `webapp_db_pool_size / _checkedout / _overflow` gauges — updated every 15 s from the SQLAlchemy async engine
- `PrometheusMiddleware` records counter + histogram for every request (skips `/metrics` and `/health*`)
- `GET /metrics` — Prometheus text-format scrape endpoint; no auth required; only registered when `PROMETHEUS_ENABLED=true` (default)

#### OpenTelemetry Tracing (`app/tracing.py`)
- `init_tracing(app, engine)` bootstraps the OTel SDK with a `BatchSpanProcessor` and OTLP HTTP exporter
- `FastAPIInstrumentor` auto-instruments all FastAPI routes; `SQLAlchemyInstrumentor` auto-instruments all DB queries — zero per-endpoint code changes required
- Only active when `OTEL_ENABLED=true` and `OTEL_ENDPOINT` is set; complete no-op otherwise
- `OTEL_SERVICE_NAME` defaults to `"web-platform"`

#### Sentry Integration (`app/main.py` lifespan)
- `sentry_sdk.init()` called in lifespan when `SENTRY_DSN` is non-empty; integrations: `FastApiIntegration`, `SqlalchemyIntegration`
- `traces_sample_rate=0.1` (10% of transactions sampled for performance traces)
- `send_default_pii=False` — no passwords or tokens sent to Sentry

#### Enhanced Health Check (`app/routers/health.py`)
- `GET /health` — unchanged fast liveness probe: `{"status": "healthy"}` with no DB I/O
- `GET /health/detailed` — readiness probe: pings DB (`SELECT 1`), Redis (`PING`), and ARQ queue (`pool.info()`); returns `{"status": "healthy"|"degraded", "checks": {...}, "version": "1.5.0"}`; returns HTTP 503 only when the database is unreachable
- Admin dashboard now calls `/health/detailed` to populate DB, Redis, and worker status badges

#### Automated Migration Runner (`app/main.py` lifespan)
- `_run_migrations()` runs after `init_db()` when `AUTO_MIGRATE=true` (default `false`)
- Tracks applied files in a `schema_migrations` table (self-bootstrapping); each `.sql` file in `migrations/` applied exactly once
- Fatal on migration error — prevents a broken schema from accepting traffic

#### Infrastructure
- `requirements.txt`: added `python-json-logger==2.0.7`, `prometheus-client==0.21.1`, `opentelemetry-api==1.30.0`, `opentelemetry-sdk==1.30.0`, `opentelemetry-instrumentation-fastapi==0.51b0`, `opentelemetry-instrumentation-sqlalchemy==0.51b0`, `opentelemetry-exporter-otlp-proto-http==1.30.0`, `sentry-sdk[fastapi]==2.24.1`
- Startup banner updated to show Phase 5 feature status
- `.env.example`: documents `LOG_LEVEL`, `LOG_FORMAT`, `PROMETHEUS_ENABLED`, `OTEL_ENABLED`, `OTEL_ENDPOINT`, `OTEL_SERVICE_NAME`, `SENTRY_DSN`, `AUTO_MIGRATE`

---

## [1.4.0] - 2026-03-03

### Added — Phase 4: Infrastructure & Scalability

#### Redis Caching Layer (`app/cache.py`)
- Module-level Redis pool initialised in the FastAPI lifespan; `get_redis()` FastAPI dependency returns `Optional[redis.asyncio.Redis]` — `None` when `REDIS_URL` is unset
- `cache_get / cache_set / cache_delete` helpers with JSON serialisation; all are no-ops when Redis is unavailable
- `GET /api/admin/config` cached with 60 s TTL; `GET /api/admin/dashboard` cached with 30 s TTL
- `GET /api/feature-flags/{name}` cached with 30 s TTL; cache invalidated on `PUT`/`DELETE`

#### Distributed Rate Limiting (`app/security.py`)
- Redis sorted-set sliding window replaces the per-process in-memory dict when Redis is available
- Falls back to the existing `RateLimiter` in-memory implementation when Redis is absent — zero-config deployments unchanged
- `RateLimitMiddleware` reads the Redis pool from `app.state.redis` set during lifespan

#### Background Task Queue (`app/worker.py`, `app/tasks.py`)
- ARQ (`arq==0.26.1`) worker with `send_verification_email_task` and `send_password_reset_email_task`; max 3 retries, 60 s timeout per job
- `enqueue_verification_email` / `enqueue_password_reset_email` helpers enqueue when ARQ pool is available, fall back to inline send otherwise
- Three call sites in `app/routers/auth.py` updated: `/register`, `/resend-verification`, `/forgot-password`
- New `worker` Docker Compose service running `arq app.worker.WorkerSettings`

#### WebSocket Support (`app/ws_manager.py`, `app/routers/websocket.py`)
- `WebSocketManager` singleton tracks admin connections (broadcast) and per-user connections (targeted send)
- `WS /ws/admin/stats?token=<jwt>` — admin-only; pushes `{cpu_percent, memory_percent, disk_percent, ...}` every 5 s
- `WS /ws/notifications?token=<jwt>` — any authenticated user; receives `{type, message}` push events
- JWT auth via `?token=` query param (WebSocket clients cannot send `Authorization` headers); invalid/insufficient token closes with code `4001`
- `static/admin.js`: dashboard section opens the stats WebSocket on enter, closes on leave, auto-reconnects after 5 s
- `static/app.js`: notification WebSocket opened on login, closed on logout; incoming messages show a toast + increment a badge counter

#### Database Read Replica Routing (`app/database.py`)
- `get_read_db()` dependency routes sessions to `DATABASE_REPLICA_URL` when set; falls back to primary transparently
- `GET /api/admin/users`, `GET /api/admin/logs`, `GET /api/feature-flags/{name}` switched to `get_read_db`

#### Connection Pool Tuning (`app/settings.py`, `app/database.py`)
- Five new env vars: `DB_POOL_SIZE` (5), `DB_MAX_OVERFLOW` (10), `DB_POOL_TIMEOUT` (30), `DB_POOL_RECYCLE` (1800), `DB_ECHO` (false)
- Startup banner prints pool configuration and Redis/ARQ/replica status

#### Infrastructure
- `requirements.txt`: added `redis[asyncio]==5.3.0`, `arq==0.26.1`
- `docker-compose.yml`: new `redis` (Redis 7-alpine, named volume `redis_data`) and `worker` services; `web` service depends on Redis health check
- `.env.example`: documents `REDIS_URL`, `DATABASE_REPLICA_URL`, `DB_POOL_SIZE`, `DB_MAX_OVERFLOW`, `DB_POOL_TIMEOUT`, `DB_POOL_RECYCLE`, `DB_ECHO`, `APP_BASE_URL`

---

## [1.3.0] - 2026-03-02

### Added — Phase 3: Developer Experience

#### Scaffold CLI
- `python -m scaffold router <name>` generates a stub CRUD router (`app/routers/<name>.py`), appends schema stubs to `app/schemas.py`, and creates a migration SQL stub in `migrations/`
- No additional dependencies — uses `string.Template` and `pathlib`

#### Auto-generated TypeScript Client
- `GET /api/admin/export/typescript-client` — downloads a typed `client.ts` containing TypeScript interfaces for all schemas and async `fetch` wrappers for all endpoints
- `GET /api/admin/export/openapi` — returns the raw OpenAPI 3.x JSON spec in all environments (including production)
- New "Developer Tools" section in the admin portal with one-click download

#### Plugin Architecture
- `plugins/` directory at the project root — drop a Python package with `__init__.py` there to have it auto-loaded on startup
- Plugin loader (`plugins/__init__.py`) exports `load_plugins(app)` which scans `plugins/`, imports each sub-package, and registers any `router` attribute with the FastAPI app
- `plugins/example/` ships a reference plugin with a `GET /api/plugins/example/ping` endpoint
- Startup banner prints `[plugins] Loaded plugin: <name>` for each discovered plugin

#### Feature Flags
- New `feature_flags` table (migration `005_phase3.sql`) with 4 seeded default flags: `registration`, `oauth_login`, `api_keys`, `invitations`
- Admin CRUD: `GET/POST /api/admin/feature-flags`, `PUT/DELETE /api/admin/feature-flags/{name}`
- Public read: `GET /api/feature-flags/{name}` — returns `{"name": str, "enabled": bool}`
- "Feature Flags" section in the admin portal with toggle switches and inline create form
- Seeded flags are protected from deletion (toggle only)

#### Environment Config Profiles
- New `app/settings.py` — centralised `Settings` class (pydantic-settings) that loads `.env` base + `.env.{APP_ENV}` overlay
- `APP_ENV` env var selects the active profile: `development` (default), `staging`, `production`
- Startup banner now prints `Environment (APP_ENV):`
- `.env.example` documents all ~40 environment variables
- `.env.development.example`, `.env.staging.example`, `.env.production.example` provide profile-specific override templates

#### Other
- `feature_flags:manage` added to the canonical `SCOPES` list in `app/permissions.py`

---

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
