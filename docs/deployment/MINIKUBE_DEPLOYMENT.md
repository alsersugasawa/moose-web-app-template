# Minikube Deployment Guide

## Quick Deployment

After ensuring Docker permissions are active in your session, run:

```bash
./deploy-to-minikube.sh
```

This script will:
1. Start minikube
2. Configure Docker to use minikube's Docker daemon
3. Build the application image inside minikube
4. Deploy PostgreSQL with persistent storage
5. Deploy the Web Platform application
6. Wait for all pods to be ready

## Manual Deployment Steps

If you prefer to run commands manually:

### 1. Start Minikube
```bash
minikube start
```

### 2. Configure Docker Environment
```bash
eval $(minikube docker-env)
```

This tells Docker to use minikube's Docker daemon instead of your local one.

### 3. Build the Docker Image
```bash
docker build -t web-platform:latest .
```

### 4. Deploy PostgreSQL
```bash
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/postgres-secrets.yaml
kubectl apply -f k8s/postgres-pvc.yaml
kubectl apply -f k8s/postgres-deployment.yaml
kubectl apply -f k8s/postgres-service.yaml

# Wait for PostgreSQL to be ready
kubectl wait --for=condition=ready pod -l app=postgres -n web-platform --timeout=120s
```

### 5. Deploy Application
```bash
kubectl apply -f k8s/app-configmap.yaml
kubectl apply -f k8s/app-pvc.yaml
kubectl apply -f k8s/app-deployment.yaml
kubectl apply -f k8s/app-service.yaml

# Wait for application to be ready
kubectl wait --for=condition=ready pod -l app=web-platform-web -n web-platform --timeout=120s
```

## Accessing the Application

### Option 1: Port Forward (Recommended for local development)
```bash
kubectl port-forward -n web-platform svc/web-platform-web 8080:80
```

Then open your browser to: `http://localhost:8080`

### Option 2: Minikube Service
```bash
minikube service web-platform-web -n web-platform
```

This will automatically open your browser to the service URL.

### Option 3: NodePort Access
```bash
# Get the minikube IP
minikube ip

# Get the NodePort
kubectl get svc web-platform-web -n web-platform -o jsonpath='{.spec.ports[0].nodePort}'

# Access at http://<minikube-ip>:<nodeport>
```

## Verifying the Deployment

### Check Pod Status
```bash
kubectl get pods -n web-platform
```

You should see:
- 1 PostgreSQL pod (running)
- 2 Web Platform web pods (running)

### View Logs
```bash
# Application logs
kubectl logs -f -l app=web-platform-web -n web-platform

# PostgreSQL logs
kubectl logs -f -l app=postgres -n web-platform
```

### Check Services
```bash
kubectl get svc -n web-platform
```

## Troubleshooting

### Pods Not Starting
```bash
# Describe pod to see events
kubectl describe pod -n web-platform <pod-name>

# Check logs
kubectl logs -n web-platform <pod-name>
```

### Image Pull Errors
If you see `ImagePullBackOff` errors, ensure you built the image in minikube's Docker environment:
```bash
eval $(minikube docker-env)
docker build -t web-platform:latest .
```

### Database Connection Issues
```bash
# Check PostgreSQL is running
kubectl get pods -l app=postgres -n web-platform

# Test connection from app pod
kubectl exec -it -n web-platform deployment/web-platform-web -- \
  python -c "import asyncpg; print('Connection test')"
```

## Updating the Application

After making code changes:

```bash
# Ensure using minikube Docker
eval $(minikube docker-env)

# Rebuild image
docker build -t web-platform:latest .

# Restart deployment to use new image
kubectl rollout restart deployment/web-platform-web -n web-platform

# Watch rollout status
kubectl rollout status deployment/web-platform-web -n web-platform
```

## Scaling

### Manual Scaling
```bash
# Scale to 5 replicas
kubectl scale deployment web-platform-web -n web-platform --replicas=5

# Scale back to 2
kubectl scale deployment web-platform-web -n web-platform --replicas=2
```

### Enable Autoscaling (requires metrics-server)
```bash
# Install metrics-server addon
minikube addons enable metrics-server

# Apply HPA
kubectl apply -f k8s/hpa.yaml

# Check HPA status
kubectl get hpa -n web-platform
```

## Clean Up

### Delete Application
```bash
# Delete entire namespace (removes all resources)
kubectl delete namespace web-platform
```

### Stop Minikube
```bash
# Stop minikube (preserves cluster state)
minikube stop

# Delete minikube cluster entirely
minikube delete
```

## Resource Usage

### View Resource Consumption
```bash
# Pod resource usage (requires metrics-server)
kubectl top pods -n web-platform

# Node resource usage
kubectl top nodes
```

### Access Kubernetes Dashboard
```bash
# Enable dashboard addon
minikube addons enable dashboard

# Open dashboard
minikube dashboard
```

## Environment Variables

The application uses the following configuration (from [k8s/app-configmap.yaml](k8s/app-configmap.yaml)):

- `DATABASE_URL`: PostgreSQL connection string
- `SECRET_KEY`: JWT signing key (change in production!)
- `ENVIRONMENT`: Set to "production"

Database credentials are in [k8s/postgres-secrets.yaml](k8s/postgres-secrets.yaml) (base64 encoded).

## Next Steps

1. **Initial Setup**: Visit `http://localhost:8080` and complete the initial setup wizard
2. **Create Admin Account**: Follow the 3-step wizard to set your app name and create admin account
3. **Explore Features**: Create family trees, upload photos, customize themes
4. **Admin Portal**: Access admin features at the Admin Portal link after logging in

## Additional Resources

- [Main README](README.md) - Application features and overview
- [Kubernetes Deployment Guide](k8s/README.md) - Detailed Kubernetes documentation
- [User Guide](USER_GUIDE.md) - Complete usage instructions
- [Changelog](CHANGELOG.md) - Version history

## Support

For issues or questions:
- Check the troubleshooting section above
- Review the main [README.md](README.md)
- Check pod logs for error messages
