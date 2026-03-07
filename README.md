# Web App Template v1.8.0

A full-stack web application template with authentication, role-based access control, admin portal, real-time features, background jobs, observability, file storage, and production-ready infrastructure.

## Features

### Authentication & Identity
- **JWT Authentication** — Register/login with JWT tokens and bcrypt password hashing
- **Email Verification** — Require users to confirm their email address before accessing the app
- **Password Reset** — "Forgot password" flow with time-limited, single-use reset tokens
- **OAuth 2.0 / Social Login** — Sign in with Google or GitHub via `authlib`
- **Two-Factor Authentication (TOTP)** — Time-based one-time passwords (Google Authenticator, Authy, etc.)
- **Active Session Management** — View and revoke active JWT sessions from the user profile

### User Management & Access Control
- **Role-Based Access Control (RBAC)** — Named roles (`viewer`, `editor`, `manager`) with JSON permission arrays; assign roles to users from the admin portal
- **Permission Scopes** — Fine-grained action scopes (e.g. `users:read`, `logs:read`) enforced at the router level via `require_permission(scope)`
- **User Profiles** — Avatar upload (200×200 JPEG), display name, bio, timezone, and language preferences
- **API Keys** — Users generate long-lived `mpk_`-prefixed keys for programmatic/service access; stored as bcrypt hashes
- **Invite-Only Registration** — Admins issue single-use invitation tokens; set `INVITE_ONLY=true` to require a token for all new sign-ups

### Platform
- **Admin Portal** — User management, role assignment, invitation management, system monitoring, and database backups
- **Initial Setup Wizard** — Auto-launched on first visit to create the admin account and set the app name
- **Customizable Dashboard** — Show/hide built-in cards and add custom cards with icons and links
- **Administrator Account Editing** — Change username, email, and password from the admin portal
- **HTTPS Support** — TLS termination via Caddy with automatic Let's Encrypt certificate provisioning
- **Certificate Management UI** — View certificate status, trigger renewal, and upload custom PEM/PFX certs

### Developer Experience
- **Scaffold CLI** — `python -m scaffold router <name>` generates a stub CRUD router, schema stubs, and a migration SQL stub
- **Auto-generated TypeScript Client** — `/api/admin/export/typescript-client` downloads a fully-typed `client.ts` for frontend consumption
- **Plugin Architecture** — Drop a Python package into `plugins/` and it is auto-loaded and registered on startup
- **Feature Flags** — Database-backed on/off switches configurable from the admin portal; public read via `/api/feature-flags/{name}`
- **Environment Config Profiles** — First-class `development`, `staging`, and `production` config sets via `.env.<env>` overlay files

### Infrastructure & Scalability
- **Redis Caching Layer** — Cache hot query results (app config, dashboard, feature flags) with configurable TTLs
- **Distributed Rate Limiting** — Redis sliding-window rate limiting with in-process fallback
- **Background Task Queue** — ARQ async job queue for email delivery and long-running tasks; inline fallback when Redis is absent
- **WebSocket Support** — Live admin stats dashboard and per-user notification push channel
- **Database Read Replica Routing** — `get_read_db()` dependency transparently routes reads to a replica when `DATABASE_REPLICA_URL` is set
- **Connection Pool Tuning** — `asyncpg` pool settings exposed via environment variables

### Observability & Operations
- **Structured JSON Logging** — `python-json-logger` with per-request access log middleware; `LOG_FORMAT=text` for human-readable dev output
- **Prometheus Metrics** — `/metrics` endpoint with request counter, latency histogram, and DB pool gauges
- **OpenTelemetry Tracing** — FastAPI + SQLAlchemy auto-instrumentation with OTLP HTTP export
- **Sentry Integration** — Automatic error capture and performance tracing via configurable DSN
- **Enhanced Health Check** — `/health/detailed` reports DB, Redis, and ARQ queue status; returns HTTP 503 on DB failure
- **Automated Migration Runner** — `AUTO_MIGRATE=true` applies pending `.sql` files from `migrations/` on container startup

### Communication & Events
- **Internal Event Bus** — Lightweight pub/sub `emit()`/`on()` system for decoupled domain events (`user.registered`, `user.login`)
- **In-App Notification System** — Per-user notification inbox with read/unread state; REST API + WebSocket push delivery
- **Webhook Delivery** — Register URLs to receive HMAC-SHA256 signed POST payloads on defined events; delivery history and ARQ retry
- **Transactional Email** — Welcome email sent automatically on registration via ARQ task

### File Storage
- **S3-Compatible Storage** — Upload files to AWS S3, MinIO, or Cloudflare R2; presigned URL generation for direct downloads; configurable via `STORAGE_BUCKET` and related env vars
- **Image Processing** — Automatic 256×256 JPEG thumbnail generation on upload for images (JPEG, PNG, GIF, WebP) via Pillow
- **File Management UI** — Admin portal "Files" section with thumbnail previews, file stats, download, and delete actions

### Frontend & UX
- **React / Vite SPA** — Opt-in single-page app in `frontend/` with React 18, React Router v6, and a typed API client; dev-server proxies to FastAPI; builds to `static/spa/`
- **Internationalization (i18n)** — `static/i18n.js` locale engine with `data-i18n` DOM attributes; English, Spanish, and French locale files shared between the static pages and the SPA (react-i18next); language switcher in user profile and SPA login/dashboard
- **Accessibility (WCAG 2.1 AA)** — Skip navigation links, ARIA landmarks, `aria-live` error/status regions, `aria-required`, `autocomplete` attributes across all pages
- **Progressive Web App (PWA)** — Web app manifest with shortcuts; service worker with cache-first (static) + network-first (API) strategies; installable and offline-capable

### Security & Infrastructure
- **Rate Limiting** — Configurable per-IP request rate limits
- **Security Headers** — HSTS, CSP, X-Frame-Options, and more (OWASP ASVS 14.4)
- **CORS Whitelist** — Explicit allowed-origins list (no wildcard)
- **Theme Customization** — Light, Dark, and System Default modes
- **Responsive Design** — Mobile-friendly Bootstrap 5.3 interface
- **Docker & Kubernetes** — Compose and Kubernetes manifests included

## Tech Stack

- **Backend**: FastAPI, SQLAlchemy 2.0 (async), PostgreSQL 18, uvicorn
- **Frontend (static)**: HTML, CSS, JavaScript, Bootstrap 5.3
- **Frontend (SPA)**: React 18, React Router v6, Vite 6, react-i18next
- **Authentication**: JWT (python-jose), bcrypt, TOTP (pyotp), OAuth 2.0 (authlib)
- **Image Processing**: Pillow (avatar resize + file thumbnails)
- **File Storage**: boto3 (S3 / MinIO / Cloudflare R2)
- **Email**: aiosmtplib (async SMTP)
- **Caching / Queue**: Redis, ARQ (background tasks)
- **Real-time**: WebSockets (built-in FastAPI)
- **Observability**: python-json-logger, prometheus-client, opentelemetry, sentry-sdk
- **Reverse Proxy / TLS**: Caddy 2 (production)
- **Monitoring**: psutil for system resource tracking
- **Containerization**: Docker, Docker Compose
- **Orchestration**: Kubernetes (with Minikube support)

## Quick Start

### Development (HTTP, no Caddy)

```bash
# Start the app with dev overrides (web exposed on port 8080, Caddy disabled)
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d

# Visit the application
# http://localhost:8080
```

On first visit the setup wizard launches automatically — create your admin account and set the app name.

### Production (HTTPS via Caddy)

```bash
# Set your domain and Let's Encrypt email
export CADDY_DOMAIN=yourdomain.com
export CADDY_EMAIL=admin@yourdomain.com

# Start with the Caddy proxy profile enabled
docker compose --profile proxy up -d

# Visit https://yourdomain.com
```

Caddy automatically provisions and renews a Let's Encrypt certificate. No manual cert setup needed.

## Prerequisites

**Option 1: Docker (Recommended)**
- Docker Engine 20.10+ or Docker Desktop
- Docker Compose v2

**Option 2: Kubernetes**
- Kubernetes cluster (v1.20+) or Minikube
- kubectl configured

**Option 3: Local Development**
- Python 3.10+
- PostgreSQL 18
- pip

## Setup Instructions

### Option A: Docker — Development

```bash
# Build and start
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build

# View logs
docker compose -f docker-compose.yml -f docker-compose.dev.yml logs -f web

# Stop
docker compose -f docker-compose.yml -f docker-compose.dev.yml down
```

### Option B: Docker — Production (HTTPS)

1. Point your DNS A record to the server IP.
2. Set environment variables (`.env` file or shell exports):

   ```env
   CADDY_DOMAIN=yourdomain.com
   CADDY_EMAIL=admin@yourdomain.com
   SECRET_KEY=<long-random-string>
   POSTGRES_PASSWORD=<strong-password>
   ```

3. Start with the proxy profile:

   ```bash
   docker compose --profile proxy up -d
   ```

4. Visit `https://yourdomain.com`.

### Option C: Kubernetes

```bash
# Deploy all resources
kubectl apply -f k8s/

# Wait for pods
kubectl wait --for=condition=ready pod -l app=web-platform -n web-platform --timeout=120s

# Port-forward (or configure an Ingress)
kubectl port-forward -n web-platform svc/web-platform 8080:80
```

Or use the Minikube helper script:

```bash
./scripts/deploy-to-minikube.sh
```

### Option D: Local Development (no Docker)

1. **Create the database**
   ```bash
   psql postgres -c "CREATE DATABASE webapp;"
   ```

2. **Install dependencies**
   ```bash
   python -m venv venv && source venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Run migrations**
   ```bash
   psql webapp < migrations/001_add_admin_features.sql
   psql webapp < migrations/002_add_app_config.sql
   psql webapp < migrations/003_phase1.sql
   psql webapp < migrations/004_phase2.sql
   psql webapp < migrations/005_phase3.sql
   psql webapp < migrations/006_phase6.sql
   psql webapp < migrations/007_phase7.sql
   ```

4. **Start the server**
   ```bash
   uvicorn app.main:app --reload
   ```

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `SECRET_KEY` | *(required)* | JWT signing secret — use a long random string |
| `DATABASE_URL` | `postgresql+asyncpg://postgres:postgres@db/webapp` | PostgreSQL connection string |
| `ENVIRONMENT` | `development` | `development` enables `/docs` and `/redoc` |
| `APP_ENV` | `development` | Config profile: `development`, `staging`, `production` |
| `CORS_ORIGINS` | `http://localhost:8080,...` | Comma-separated list of allowed CORS origins |
| `TRUSTED_HOSTS` | `localhost,127.0.0.1,*.localhost` | Comma-separated trusted Host header values |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | JWT token lifetime |
| `REQUIRE_JTI` | `false` | Enforce session tracking for all JWTs (strict mode) |
| `FORCE_EMAIL_VERIFICATION` | `false` | Block all unverified users globally |
| `APP_BASE_URL` | `http://localhost:8080` | Base URL used in email links |
| `INVITE_ONLY` | `false` | When `true`, registration requires a valid invitation token |

### Email (optional — logs to stdout if unset)

| Variable | Default | Description |
|---|---|---|
| `SMTP_HOST` | *(unset)* | SMTP server hostname |
| `SMTP_PORT` | `587` | SMTP port |
| `SMTP_USER` | *(unset)* | SMTP username |
| `SMTP_PASSWORD` | *(unset)* | SMTP password |
| `SMTP_FROM` | *(unset)* | From address for outgoing emails |
| `SMTP_TLS` | `true` | Use STARTTLS |

### OAuth 2.0 (optional — buttons hidden if unset)

| Variable | Description |
|---|---|
| `GOOGLE_CLIENT_ID` | Google OAuth client ID |
| `GOOGLE_CLIENT_SECRET` | Google OAuth client secret |
| `GITHUB_CLIENT_ID` | GitHub OAuth App client ID |
| `GITHUB_CLIENT_SECRET` | GitHub OAuth App client secret |

### Caddy / HTTPS

| Variable | Default | Description |
|---|---|---|
| `CADDY_DOMAIN` | `localhost` | Domain name for TLS certificate |
| `CADDY_EMAIL` | `admin@example.com` | Let's Encrypt account email |

### Redis & Background Tasks

| Variable | Default | Description |
|---|---|---|
| `REDIS_URL` | *(unset)* | Redis connection URL (e.g. `redis://redis:6379`); caching and ARQ disabled if unset |
| `DATABASE_REPLICA_URL` | *(unset)* | Read replica connection string; falls back to primary if unset |
| `DB_POOL_SIZE` | `5` | asyncpg connection pool size |
| `DB_MAX_OVERFLOW` | `10` | Maximum pool overflow connections |
| `DB_POOL_TIMEOUT` | `30` | Pool checkout timeout in seconds |
| `DB_POOL_RECYCLE` | `1800` | Connection recycle interval in seconds |
| `DB_ECHO` | `false` | Log all SQL statements |

### Observability

| Variable | Default | Description |
|---|---|---|
| `LOG_LEVEL` | `INFO` | Root log level (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |
| `LOG_FORMAT` | `json` | Log format: `json` (structured) or `text` (human-readable) |
| `PROMETHEUS_ENABLED` | `true` | Expose `/metrics` Prometheus scrape endpoint |
| `OTEL_ENABLED` | `false` | Enable OpenTelemetry tracing |
| `OTEL_ENDPOINT` | *(unset)* | OTLP HTTP exporter endpoint |
| `OTEL_SERVICE_NAME` | `web-platform` | Service name reported in traces |
| `SENTRY_DSN` | *(unset)* | Sentry DSN for error and performance monitoring |
| `AUTO_MIGRATE` | `false` | Run pending SQL migrations automatically on startup |

### File Storage (S3-compatible)

| Variable | Default | Description |
|---|---|---|
| `STORAGE_BUCKET` | *(unset)* | S3 bucket name; file storage disabled when empty |
| `STORAGE_ACCESS_KEY` | *(unset)* | S3 / MinIO / R2 access key |
| `STORAGE_SECRET_KEY` | *(unset)* | S3 / MinIO / R2 secret key |
| `STORAGE_REGION` | *(unset)* | AWS region (e.g. `us-east-1`); optional for MinIO/R2 |
| `STORAGE_ENDPOINT_URL` | *(unset)* | Custom endpoint URL for MinIO or Cloudflare R2 |
| `STORAGE_PRESIGN_EXPIRY` | `3600` | Presigned URL lifetime in seconds |

## Project Structure

```
.
├── app/
│   ├── main.py              # FastAPI application entry point and lifespan
│   ├── models.py            # SQLAlchemy ORM models (User, Role, ApiKey, Notification, Webhook, StoredFile, …)
│   ├── schemas.py           # Pydantic request/response schemas
│   ├── auth.py              # JWT + API key authentication and session logic
│   ├── permissions.py       # require_permission(scope) dependency factory
│   ├── database.py          # Async database connection and read replica routing
│   ├── config.py            # Backup configuration
│   ├── settings.py          # Pydantic-settings config with env profile support
│   ├── email.py             # Async SMTP helpers (verification, password reset)
│   ├── security.py          # Rate limiting and security header middleware
│   ├── cache.py             # Redis caching helpers
│   ├── storage.py           # S3-compatible file storage (boto3 + Pillow thumbnails)
│   ├── worker.py            # ARQ worker settings
│   ├── tasks.py             # Background task definitions
│   ├── ws_manager.py        # WebSocket connection manager
│   ├── events.py            # Internal event bus (pub/sub)
│   ├── metrics.py           # Prometheus metrics definitions
│   ├── tracing.py           # OpenTelemetry initialization
│   ├── logging_config.py    # Structured JSON logging setup
│   └── routers/
│       ├── auth.py          # Auth endpoints (register, login, profile, TOTP, sessions, …)
│       ├── admin.py         # Admin portal endpoints
│       ├── oauth.py         # OAuth 2.0 redirect + callback (Google, GitHub)
│       ├── roles.py         # Role CRUD (/api/admin/roles)
│       ├── api_keys.py      # API key CRUD (/api/auth/api-keys)
│       ├── invitations.py   # Invitation management (/api/admin/invitations)
│       ├── websocket.py     # WebSocket endpoints (admin stats, notifications)
│       ├── notifications.py # Notification REST API (/api/notifications)
│       ├── webhooks.py      # Webhook CRUD and delivery history (/api/webhooks)
│       ├── files.py         # File upload/download/delete (/api/files, /api/admin/files)
│       └── health.py        # Health check endpoints (/health, /health/detailed)
├── static/
│   ├── index.html           # Main application page (PWA, i18n, ARIA)
│   ├── app.js               # Frontend application logic (i18n-aware)
│   ├── styles.css           # Main styles
│   ├── setup.html           # First-run setup wizard
│   ├── admin.html           # Admin portal page (PWA, i18n, ARIA)
│   ├── admin.js             # Admin portal logic (file management)
│   ├── admin-styles.css     # Admin styles
│   ├── i18n.js              # Lightweight i18n engine
│   ├── manifest.json        # PWA web app manifest
│   ├── service-worker.js    # PWA service worker (cache-first + network-first)
│   └── locales/
│       ├── en.json          # English translations
│       ├── es.json          # Spanish translations
│       └── fr.json          # French translations
├── frontend/                # Opt-in React/Vite SPA starter
│   ├── package.json         # React 18, Vite 6, react-i18next, react-router-dom
│   ├── vite.config.js       # Dev proxy to FastAPI; build output to static/spa/
│   ├── index.html
│   └── src/
│       ├── main.jsx         # React root + SW registration
│       ├── App.jsx          # Auth context, protected routes
│       ├── i18n.js          # react-i18next config (shares locale files)
│       ├── api/
│       │   └── client.js    # Typed fetch wrappers for all REST endpoints
│       └── pages/
│           ├── LoginPage.jsx    # Login / register / forgot-password
│           └── DashboardPage.jsx # Overview, notifications, file management
├── migrations/
│   ├── 001_add_admin_features.sql
│   ├── 002_add_app_config.sql
│   ├── 003_phase1.sql       # Email verification, OAuth, TOTP, sessions
│   ├── 004_phase2.sql       # Roles, API keys, invitations, user profile columns
│   ├── 005_phase3.sql       # Feature flags
│   ├── 006_phase6.sql       # Notifications, webhooks, webhook_deliveries
│   └── 007_phase7.sql       # stored_files table
├── plugins/
│   └── example/             # Reference plugin with GET /api/plugins/example/ping
├── docs/
│   ├── ROADMAP.md           # Feature roadmap
│   ├── SYSTEM_REQUIREMENTS.md
│   ├── guides/
│   │   └── USER_GUIDE.md    # End-user documentation
│   ├── security/
│   │   └── SECURITY_COMPLIANCE.md
│   └── development/
│       └── RELEASE_PROCESS.md
├── k8s/                     # Kubernetes manifests
├── scripts/                 # Deployment scripts
├── Caddyfile                # Caddy reverse proxy + TLS configuration
├── Dockerfile
├── docker-compose.yml       # Base Compose config (production)
├── docker-compose.dev.yml   # Dev override (HTTP, port 8080, no Caddy)
└── .env.example             # All environment variables documented
```

## Extending the Template

1. **Add data models** in `app/models.py`
2. **Add API routes** under `app/routers/` (or use `python -m scaffold router <name>`)
3. **Update the frontend** in `static/index.html` and `static/app.js`, or build on the React SPA in `frontend/`
4. **Add database migrations** in `migrations/`
5. **Define permission scopes** in `app/permissions.py` and protect endpoints with `require_permission("scope:action")`
6. **Customize the dashboard** — use the built-in Customize panel to add cards without touching code
7. **Add plugins** — drop a Python package with a `router` attribute into `plugins/` for auto-registration
8. **Add translations** — drop a new `static/locales/<locale>.json` file; register the locale in `static/i18n.js` and `frontend/src/i18n.js`

### Running the React SPA

```bash
cd frontend
npm install
npm run dev     # http://localhost:5173 — proxies /api and /ws to localhost:8080
npm run build   # produces static/spa/ for serving by FastAPI
```

## Documentation

- **[Changelog](CHANGELOG.md)** — Version history
- **[Roadmap](docs/ROADMAP.md)** — Planned features and enhancements
- **[System Requirements](docs/SYSTEM_REQUIREMENTS.md)** — Functional and non-functional requirements, data model, API surface, security controls
- **[User Guide](docs/guides/USER_GUIDE.md)** — End-user documentation
- **[Security Compliance](docs/security/SECURITY_COMPLIANCE.md)** — ISO 27001 / NIST / OWASP ASVS mapping
- **[Kubernetes Deployment](k8s/README.md)** — Production Kubernetes guide
- **[Scripts](scripts/README.md)** — Deployment script documentation

## License

MIT
