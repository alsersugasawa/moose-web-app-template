# Kubernetes Deployment Guide

This directory contains Kubernetes manifests for deploying the Web App to a Kubernetes cluster.

## Architecture Overview

```
+---------------------------------------------------+
|              Ingress Controller                   |
|         (NGINX + TLS/Let's Encrypt)              |
+------------------------+--------------------------+
                         |
                         v
+---------------------------------------------------+
|           web-platform-web Service                 |
|              (ClusterIP, Port 80)                 |
+------------------------+--------------------------+
                         |
          +--------------+--------------+
          |                             |
          v                             v
    +------------+              +------------+
    |  Web Pod   |              |  Web Pod   |
    |  (2-10)    |              |  (HPA)     |
    +-----+------+              +------+-----+
          |                            |
          +------------+---------------+
                       |
                       v
          +------------------------+
          |   postgres Service     |
          |  (ClusterIP, Port 5432)|
          +----------+-------------+
                     |
                     v
              +-------------+
              | PostgreSQL  |
              |   Pod (1)   |
              +------+------+
                     |
                     v
              +-------------+
              | PVC (10Gi)  |
              +-------------+
```

## Prerequisites

### Required
- Kubernetes cluster (v1.20+)
  - **Minikube** (local development/testing) - **Recommended for local testing**
  - GKE, EKS, AKS (cloud)
  - k3s, k0s (edge/IoT)
- kubectl configured (or use `minikube kubectl --`)
- Container registry access (Docker Hub, GCR, ECR, etc.)
  - **Not required for minikube** - can build images locally

### Optional but Recommended
- Ingress Controller (NGINX, Traefik, etc.)
- cert-manager (for automatic TLS certificates)
- Metrics Server (for HPA)
- Persistent Volume provisioner

## Minikube Quick Start

For local Kubernetes testing with minikube, see the dedicated [Minikube Deployment Guide](../docs/deployment/MINIKUBE_DEPLOYMENT.md) or use the automated deployment:

```bash
# From project root
./scripts/deploy-to-minikube.sh
```

This script handles:
- Starting minikube
- Building the Docker image locally
- Deploying all Kubernetes resources
- Waiting for pods to be ready

**Key Differences for Minikube:**
- No container registry needed - images built in minikube's Docker daemon
- Uses `imagePullPolicy: Never` to use local images
- Requires `eval $(minikube docker-env)` before building images
- Access via `kubectl port-forward` or `minikube service`

For manual minikube deployment, see the sections below with these modifications:
1. Run `eval $(minikube docker-env)` before building images
2. Build images with: `docker build -t web-platform:latest .`
3. Ensure deployment uses `imagePullPolicy: Never`
4. Set `TRUSTED_HOSTS=*` and `CORS_ORIGINS=*` in ConfigMap

## Quick Start

### 1. Create Namespace

```bash
kubectl apply -f namespace.yaml
```

### 2. Configure Secrets

**IMPORTANT**: Update the secrets before deploying to production!

```bash
# Edit postgres-secrets.yaml with your values
# Then apply:
kubectl apply -f postgres-secrets.yaml
```

### 3. Deploy PostgreSQL

```bash
# Create PVC
kubectl apply -f postgres-pvc.yaml

# Deploy PostgreSQL
kubectl apply -f postgres-deployment.yaml
kubectl apply -f postgres-service.yaml

# Wait for PostgreSQL to be ready
kubectl wait --for=condition=ready pod -l app=postgres -n web-platform --timeout=120s
```

### 4. Deploy Application

```bash
# Create ConfigMap
kubectl apply -f app-configmap.yaml

# Create PVC for backups
kubectl apply -f app-pvc.yaml

# Deploy application
kubectl apply -f app-deployment.yaml
kubectl apply -f app-service.yaml

# Wait for app to be ready
kubectl wait --for=condition=ready pod -l app=web-platform-web -n web-platform --timeout=120s
```

### 5. Setup Ingress (Optional)

```bash
# Edit ingress.yaml with your domain
# Then apply:
kubectl apply -f ingress.yaml
```

### 6. Enable Autoscaling (Optional)

```bash
# Requires Metrics Server installed
kubectl apply -f hpa.yaml
```

## One-Command Deployment

Deploy everything at once:

```bash
kubectl apply -f namespace.yaml && \
kubectl apply -f postgres-secrets.yaml && \
kubectl apply -f postgres-pvc.yaml && \
kubectl apply -f postgres-deployment.yaml && \
kubectl apply -f postgres-service.yaml && \
kubectl apply -f app-configmap.yaml && \
kubectl apply -f app-pvc.yaml && \
kubectl apply -f app-deployment.yaml && \
kubectl apply -f app-service.yaml && \
kubectl apply -f ingress.yaml && \
kubectl apply -f hpa.yaml
```

## Access the Application

### Local Access (Port Forward)

```bash
# Forward port 8080 to the service
kubectl port-forward -n web-platform svc/web-platform-web 8080:80

# Access at http://localhost:8080
```

### Via LoadBalancer (Cloud)

```bash
# Change service type to LoadBalancer
kubectl patch svc web-platform-web -n web-platform -p '{"spec":{"type":"LoadBalancer"}}'

# Get external IP
kubectl get svc web-platform-web -n web-platform
```

### Via Ingress

After configuring ingress with your domain, access at:
```
https://web-platform.example.com
```

## Monitoring and Management

### View Logs

```bash
# Web application logs
kubectl logs -f -l app=web-platform-web -n web-platform

# PostgreSQL logs
kubectl logs -f -l app=postgres -n web-platform

# Tail last 100 lines
kubectl logs --tail=100 -l app=web-platform-web -n web-platform
```

### Check Pod Status

```bash
# All pods in namespace
kubectl get pods -n web-platform

# Watch pods
kubectl get pods -n web-platform -w

# Describe pod
kubectl describe pod <pod-name> -n web-platform
```

### Execute Commands in Pods

```bash
# Access web container shell
kubectl exec -it -n web-platform deployment/web-platform-web -- bash

# Access PostgreSQL
kubectl exec -it -n web-platform deployment/postgres -- psql -U postgres -d webapp
```

### View Resource Usage

```bash
# Pod resource usage
kubectl top pods -n web-platform

# Node resource usage
kubectl top nodes
```

## Scaling

### Manual Scaling

```bash
# Scale web application
kubectl scale deployment web-platform-web -n web-platform --replicas=5

# View current replicas
kubectl get deployment web-platform-web -n web-platform
```

### Automatic Scaling (HPA)

```bash
# View HPA status
kubectl get hpa -n web-platform

# Describe HPA
kubectl describe hpa web-platform-web-hpa -n web-platform

# Delete HPA (revert to manual)
kubectl delete -f hpa.yaml
```

## Database Backups

### Manual Backup

```bash
# Create backup
kubectl exec -n web-platform deployment/postgres -- \
  pg_dump -U postgres webapp > backup-$(date +%Y%m%d).sql

# Restore backup
kubectl exec -i -n web-platform deployment/postgres -- \
  psql -U postgres webapp < backup-20260122.sql
```

### Automated Backups with CronJob

Create `backup-cronjob.yaml`:

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: postgres-backup
  namespace: web-platform
spec:
  schedule: "0 2 * * *"  # Daily at 2 AM
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: backup
            image: postgres:14-alpine
            command:
            - sh
            - -c
            - |
              pg_dump -h postgres -U postgres webapp | \
              gzip > /backups/backup-$(date +%Y%m%d-%H%M%S).sql.gz
            env:
            - name: PGPASSWORD
              valueFrom:
                secretKeyRef:
                  name: postgres-secrets
                  key: POSTGRES_PASSWORD
            volumeMounts:
            - name: backups
              mountPath: /backups
          volumes:
          - name: backups
            persistentVolumeClaim:
              claimName: app-backups-pvc
          restartPolicy: OnFailure
```

Apply with: `kubectl apply -f backup-cronjob.yaml`

## Updates and Rollouts

### Update Application Image

```bash
# Update to new version
kubectl set image deployment/web-platform-web \
  web=your-org/web-platform:v4.0.1 \
  -n web-platform

# Watch rollout status
kubectl rollout status deployment/web-platform-web -n web-platform
```

### Rollback Deployment

```bash
# View rollout history
kubectl rollout history deployment/web-platform-web -n web-platform

# Rollback to previous version
kubectl rollout undo deployment/web-platform-web -n web-platform

# Rollback to specific revision
kubectl rollout undo deployment/web-platform-web --to-revision=2 -n web-platform
```

### Pause/Resume Rollout

```bash
# Pause rollout
kubectl rollout pause deployment/web-platform-web -n web-platform

# Resume rollout
kubectl rollout resume deployment/web-platform-web -n web-platform
```

## Troubleshooting

### Pods Not Starting

```bash
# Check pod events
kubectl describe pod <pod-name> -n web-platform

# Check logs
kubectl logs <pod-name> -n web-platform

# Check previous container logs (if crashed)
kubectl logs <pod-name> -n web-platform --previous
```

### Database Connection Issues

```bash
# Test connection from web pod
kubectl exec -it -n web-platform deployment/web-platform-web -- \
  python -c "import asyncpg; print('Testing connection...')"

# Check PostgreSQL is running
kubectl get pods -l app=postgres -n web-platform

# Check service endpoints
kubectl get endpoints postgres -n web-platform
```

### Persistent Volume Issues

```bash
# Check PVC status
kubectl get pvc -n web-platform

# Describe PVC
kubectl describe pvc postgres-pvc -n web-platform

# Check PV
kubectl get pv
```

### Ingress Not Working

```bash
# Check ingress status
kubectl get ingress -n web-platform

# Describe ingress
kubectl describe ingress web-platform-ingress -n web-platform

# Check ingress controller logs
kubectl logs -n ingress-nginx deployment/ingress-nginx-controller
```

## Security Best Practices

### 1. Use Secrets for Sensitive Data

```bash
# Create secret from literal
kubectl create secret generic app-secrets \
  --from-literal=jwt-secret=your-secret-key \
  -n web-platform

# Create secret from file
kubectl create secret generic tls-secret \
  --from-file=tls.crt=cert.crt \
  --from-file=tls.key=cert.key \
  -n web-platform
```

### 2. Network Policies

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-web-to-postgres
  namespace: web-platform
spec:
  podSelector:
    matchLabels:
      app: postgres
  policyTypes:
  - Ingress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: web-platform-web
    ports:
    - protocol: TCP
      port: 5432
```

### 3. Resource Quotas

```yaml
apiVersion: v1
kind: ResourceQuota
metadata:
  name: web-platform-quota
  namespace: web-platform
spec:
  hard:
    requests.cpu: "4"
    requests.memory: 8Gi
    limits.cpu: "8"
    limits.memory: 16Gi
    persistentvolumeclaims: "5"
```

### 4. Pod Security Standards

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: web-platform
  labels:
    pod-security.kubernetes.io/enforce: baseline
    pod-security.kubernetes.io/audit: restricted
    pod-security.kubernetes.io/warn: restricted
```

## Clean Up

### Delete All Resources

```bash
# Delete entire namespace (removes everything)
kubectl delete namespace web-platform

# Or delete individual resources
kubectl delete -f hpa.yaml
kubectl delete -f ingress.yaml
kubectl delete -f app-service.yaml
kubectl delete -f app-deployment.yaml
kubectl delete -f app-pvc.yaml
kubectl delete -f app-configmap.yaml
kubectl delete -f postgres-service.yaml
kubectl delete -f postgres-deployment.yaml
kubectl delete -f postgres-pvc.yaml
kubectl delete -f postgres-secrets.yaml
kubectl delete -f namespace.yaml
```

## Production Considerations

### High Availability

1. **Multi-zone Deployment**: Use node affinity to spread pods across availability zones
2. **Pod Disruption Budgets**: Ensure minimum number of pods during updates
3. **Database Replication**: Consider PostgreSQL HA solutions (Patroni, Stolon)

### Performance

1. **Resource Limits**: Set appropriate CPU/memory limits
2. **Connection Pooling**: Use PgBouncer for database connection pooling
3. **Caching**: Add Redis for session/cache management
4. **CDN**: Use CDN for static assets

### Monitoring

1. **Prometheus**: Metrics collection
2. **Grafana**: Metrics visualization
3. **Jaeger/Zipkin**: Distributed tracing
4. **EFK Stack**: Logging (Elasticsearch, Fluentd, Kibana)

### Cost Optimization

1. **Right-sizing**: Use VPA (Vertical Pod Autoscaler) to optimize resource requests
2. **Spot Instances**: Use spot/preemptible instances for non-critical workloads
3. **Storage Classes**: Use appropriate storage classes for cost/performance balance

## Additional Resources

- [Kubernetes Documentation](https://kubernetes.io/docs/)
- [kubectl Cheat Sheet](https://kubernetes.io/docs/reference/kubectl/cheatsheet/)
- [Kubernetes Best Practices](https://kubernetes.io/docs/concepts/configuration/overview/)
- [cert-manager Documentation](https://cert-manager.io/docs/)
- [NGINX Ingress Controller](https://kubernetes.github.io/ingress-nginx/)
