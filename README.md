# Web Platform Template v1.0.0

A full-stack web application template with user authentication, admin portal, and production-ready infrastructure.

## Features

- **User Authentication** - Register/login with JWT tokens and bcrypt password hashing
- **Admin Portal** - User management, system monitoring, and backups
- **Initial Setup Wizard** - First-run admin account creation with custom app name
- **Theme Customization** - Light, Dark, and System Default modes
- **Responsive Design** - Mobile-friendly Bootstrap 5.3 interface
- **Security Hardened** - Rate limiting, security headers, CORS whitelist, trusted hosts

## Tech Stack

- **Backend**: FastAPI, SQLAlchemy (async), PostgreSQL 14
- **Frontend**: HTML, CSS, JavaScript, Bootstrap 5.3
- **Authentication**: JWT tokens with bcrypt password hashing
- **Monitoring**: psutil for system resource tracking
- **Containerization**: Docker, Docker Compose
- **Orchestration**: Kubernetes (with Minikube support)

## Quick Start with Docker

```bash
# Start the application (includes PostgreSQL database)
docker-compose up -d

# Visit the application
# http://localhost:8080
```

All dependencies are included in the container.

## Prerequisites

**Option 1: Docker (Recommended)**
- Docker Desktop or Docker Engine
- Docker Compose

**Option 2: Kubernetes**
- Kubernetes cluster (v1.20+) or Minikube
- kubectl configured (or minikube)

**Option 3: Local Development**
- Python 3.8+
- PostgreSQL 14
- pip (Python package manager)

## Setup Instructions

### Option A: Docker Setup (Recommended)

1. **Install Docker Desktop**
   Download from [docker.com](https://www.docker.com/products/docker-desktop/)

2. **Start the Application**
   ```bash
   docker-compose up -d
   ```

3. **Access the Application**
   - Web App: `http://localhost:8080`
   - API Docs: `http://localhost:8080/docs`

4. **Common Commands**
   ```bash
   # Rebuild after changes
   docker-compose up -d --build

   # View logs
   docker-compose logs -f web

   # Stop application
   docker-compose down
   ```

### Option B: Kubernetes Setup

1. **Quick Deploy**
   ```bash
   # Deploy all resources
   kubectl apply -f k8s/

   # Wait for pods to be ready
   kubectl wait --for=condition=ready pod -l app=web-platform -n web-platform --timeout=120s
   ```

2. **Access the Application**
   ```bash
   # Port forward
   kubectl port-forward -n web-platform svc/web-platform 8080:80

   # Access at http://localhost:8080
   ```

3. **Minikube (local Kubernetes)**
   ```bash
   ./scripts/deploy-to-minikube.sh
   ```

### Option C: Local Development Setup

1. **Install PostgreSQL 14**
   ```bash
   # macOS
   brew install postgresql@14
   brew services start postgresql@14

   # Ubuntu/Debian
   sudo apt install postgresql postgresql-contrib
   ```

2. **Create Database**
   ```bash
   psql postgres
   CREATE DATABASE webapp;
   CREATE USER postgres WITH PASSWORD 'postgres';
   GRANT ALL PRIVILEGES ON DATABASE webapp TO postgres;
   \q
   ```

3. **Setup Python Environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

4. **Run Application**
   ```bash
   uvicorn app.main:app --reload
   ```

## Getting Started

1. Visit `http://localhost:8080`
2. On first run, complete the setup wizard to create your admin account
3. Log in and start building your application

## Project Structure

```
.
├── app/
│   ├── main.py          # FastAPI application entry point
│   ├── models.py        # SQLAlchemy ORM models (User, SystemLog, Backup, AppConfig)
│   ├── schemas.py       # Pydantic request/response schemas
│   ├── auth.py          # JWT authentication logic
│   ├── database.py      # Database connection setup
│   ├── config.py        # Backup/storage configuration
│   ├── security.py      # Security middleware
│   └── routers/
│       ├── auth.py      # Authentication endpoints
│       └── admin.py     # Admin portal endpoints
├── static/
│   ├── index.html       # Main application page
│   ├── app.js           # Frontend application logic
│   ├── styles.css       # Main styles
│   ├── admin.html       # Admin portal page
│   ├── admin.js         # Admin portal logic
│   └── admin-styles.css # Admin styles
├── migrations/
│   ├── 001_add_admin_features.sql
│   └── 002_add_app_config.sql
├── k8s/                 # Kubernetes manifests
├── scripts/             # Deployment scripts
├── Dockerfile
└── docker-compose.yml
```

## Customization

1. **Add your data models** in `app/models.py`
2. **Add API routes** under `app/routers/`
3. **Update the frontend** in `static/index.html` and `static/app.js`
4. **Add database migrations** in `migrations/`

## Documentation

- **[Roadmap](docs/ROADMAP.md)** - Planned future features and enhancements
- **[Kubernetes Deployment](k8s/README.md)** - Production Kubernetes deployment guide
- **[Scripts](scripts/README.md)** - Deployment script documentation

## License

MIT
