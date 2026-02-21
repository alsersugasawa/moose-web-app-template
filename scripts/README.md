# Deployment Scripts

This directory contains deployment and utility scripts for the Web Platform.

## Available Scripts

### `deploy-to-minikube.sh`

Automated deployment script for minikube (local Kubernetes testing).

**Usage:**
```bash
./scripts/deploy-to-minikube.sh
```

**What it does:**
1. Starts minikube cluster
2. Configures Docker to use minikube's Docker daemon
3. Builds the application Docker image locally
4. Deploys PostgreSQL database
5. Deploys the Web Platform application
6. Waits for all pods to be ready

**Requirements:**
- minikube installed
- Docker installed and user added to docker group

**Documentation:** See [Minikube Deployment Guide](../docs/deployment/MINIKUBE_DEPLOYMENT.md)

---

### `deploy-k8s.sh`

Deployment script for production Kubernetes clusters.

**Usage:**
```bash
./scripts/deploy-k8s.sh
```

**What it does:**
1. Creates namespace
2. Deploys secrets
3. Deploys PostgreSQL
4. Deploys application
5. Optionally deploys ingress and HPA

**Requirements:**
- kubectl configured for your cluster
- Access to container registry (Docker Hub, GCR, etc.)

**Documentation:** See [Kubernetes Deployment Guide](../k8s/README.md)

---

## Script Permissions

All scripts should be executable. If you get a permission denied error, run:

```bash
chmod +x scripts/*.sh
```

## Environment Variables

Scripts may use the following environment variables:

- `DOCKER_REGISTRY` - Container registry URL (default: Docker Hub)
- `IMAGE_TAG` - Image version tag (default: latest)
- `NAMESPACE` - Kubernetes namespace (default: web-platform)

## Troubleshooting

If scripts fail:

1. Check script permissions: `ls -la scripts/`
2. Verify prerequisites are installed
3. Check script output for specific errors
4. See deployment documentation for detailed troubleshooting

For more help, see:
- [Minikube Deployment Guide](../docs/deployment/MINIKUBE_DEPLOYMENT.md)
- [Kubernetes README](../k8s/README.md)
