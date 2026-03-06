# Documentation

Welcome to the Web App documentation!

## User Documentation

- **[User Guide](guides/USER_GUIDE.md)** - Complete guide for using the application
  - Getting started and first-run setup
  - Authentication, 2FA, OAuth, and session management
  - API keys, profile, and notifications
  - Admin portal features (users, roles, feature flags, developer tools)

## Deployment Guides

- **[Kubernetes Deployment](../k8s/README.md)** - Production deployment on Kubernetes
  - Cloud platforms (GKE, EKS, AKS)
  - Scaling and high availability
  - Monitoring and logging

- **[Minikube Deployment](deployment/MINIKUBE_DEPLOYMENT.md)** - Local Kubernetes testing
  - Quick start guide
  - Troubleshooting
  - Local development workflow

- **[Update Guide](deployment/UPDATE_GUIDE.md)** - Updating the application
  - Docker updates
  - Kubernetes updates
  - Database migrations

## Development Documentation

- **[Release Process](development/RELEASE_PROCESS.md)** - Creating and publishing releases
  - Version numbering
  - Release workflow
  - Publishing to Docker Hub

- **[Database Migration](development/DATABASE_STORAGE_MIGRATION.md)** - Database schema changes
  - Migration best practices
  - Storage migration guide

## Security Documentation

- **[Security Compliance](security/SECURITY_COMPLIANCE.md)** - Security best practices
  - OWASP compliance
  - Authentication and authorization
  - Security headers and HTTPS
  - Input validation
  - Data protection

## Quick Links

- [Main README](../README.md)
- [Changelog](../CHANGELOG.md)
- [Deployment Scripts](../scripts/)
- [Kubernetes Manifests](../k8s/)

## Contributing

See the [Release Process](development/RELEASE_PROCESS.md) for information on how to contribute and create releases.
