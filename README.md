# Web App Template v1.2.0

A full-stack web application template with authentication, role-based access control, admin portal, and production-ready infrastructure.

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

### Security & Infrastructure
- **Rate Limiting** — Configurable per-IP request rate limits
- **Security Headers** — HSTS, CSP, X-Frame-Options, and more (OWASP ASVS 14.4)
- **CORS Whitelist** — Explicit allowed-origins list (no wildcard)
- **Theme Customization** — Light, Dark, and System Default modes
- **Responsive Design** — Mobile-friendly Bootstrap 5.3 interface
- **Docker & Kubernetes** — Compose and Kubernetes manifests included

## Tech Stack

- **Backend**: FastAPI, SQLAlchemy 2.0 (async), PostgreSQL 14, uvicorn
- **Frontend**: HTML, CSS, JavaScript, Bootstrap 5.3
- **Authentication**: JWT (python-jose), bcrypt (passlib), TOTP (pyotp), OAuth 2.0 (authlib)
- **Image Processing**: Pillow (avatar resize)
- **Email**: aiosmtplib (async SMTP)
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
- PostgreSQL 14
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

## Project Structure

```
.
├── app/
│   ├── main.py              # FastAPI application entry point
│   ├── models.py            # SQLAlchemy ORM models (User, Role, ApiKey, Invitation, …)
│   ├── schemas.py           # Pydantic request/response schemas
│   ├── auth.py              # JWT + API key authentication and session logic
│   ├── permissions.py       # require_permission(scope) dependency factory
│   ├── database.py          # Async database connection
│   ├── config.py            # App configuration
│   ├── email.py             # Async SMTP helpers (verification, password reset)
│   ├── security.py          # Rate limiting and security header middleware
│   └── routers/
│       ├── auth.py          # Auth endpoints (register, login, profile, TOTP, sessions, …)
│       ├── admin.py         # Admin portal endpoints
│       ├── oauth.py         # OAuth 2.0 redirect + callback (Google, GitHub)
│       ├── roles.py         # Role CRUD (/api/admin/roles)
│       ├── api_keys.py      # API key CRUD (/api/auth/api-keys)
│       └── invitations.py   # Invitation management (/api/admin/invitations)
├── static/
│   ├── index.html           # Main application page
│   ├── app.js               # Frontend application logic
│   ├── styles.css           # Main styles
│   ├── setup.html           # First-run setup wizard
│   ├── admin.html           # Admin portal page
│   ├── admin.js             # Admin portal logic
│   └── admin-styles.css     # Admin styles
├── migrations/
│   ├── 001_add_admin_features.sql
│   ├── 002_add_app_config.sql
│   ├── 003_phase1.sql       # Email verification, OAuth, TOTP, sessions
│   └── 004_phase2.sql       # Roles, API keys, invitations, user profile columns
├── docs/
│   ├── ROADMAP.md           # Feature roadmap
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
└── docker-compose.dev.yml   # Dev override (HTTP, port 8080, no Caddy)
```

## Extending the Template

1. **Add data models** in `app/models.py`
2. **Add API routes** under `app/routers/`
3. **Update the frontend** in `static/index.html` and `static/app.js`
4. **Add database migrations** in `migrations/`
5. **Define permission scopes** in `app/permissions.py` and protect endpoints with `require_permission("scope:action")`
6. **Customize the dashboard** — use the built-in Customize panel to add cards without touching code

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
