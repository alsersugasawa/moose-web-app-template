#!/bin/bash

# Web Platform - Kubernetes Deployment Script
# This script automates the deployment of the Web Platformlication to Kubernetes

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
NAMESPACE="web-platform"
TIMEOUT="120s"

# Functions
print_header() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

check_prerequisites() {
    print_header "Checking Prerequisites"

    # Check kubectl
    if ! command -v kubectl &> /dev/null; then
        print_error "kubectl not found. Please install kubectl first."
        exit 1
    fi
    print_success "kubectl found"

    # Check cluster connection
    if ! kubectl cluster-info &> /dev/null; then
        print_error "Cannot connect to Kubernetes cluster. Please check your kubectl configuration."
        exit 1
    fi
    print_success "Connected to Kubernetes cluster"

    # Display cluster info
    echo "Cluster: $(kubectl config current-context)"
}

deploy_namespace() {
    print_header "Creating Namespace"
    kubectl apply -f namespace.yaml
    print_success "Namespace created/updated"
}

deploy_secrets() {
    print_header "Deploying Secrets"
    print_warning "Make sure to update postgres-secrets.yaml with production values!"
    kubectl apply -f postgres-secrets.yaml
    print_success "Secrets deployed"
}

deploy_postgres() {
    print_header "Deploying PostgreSQL"

    echo "Creating PersistentVolumeClaim..."
    kubectl apply -f postgres-pvc.yaml

    echo "Deploying PostgreSQL..."
    kubectl apply -f postgres-deployment.yaml
    kubectl apply -f postgres-service.yaml

    echo "Waiting for PostgreSQL to be ready..."
    kubectl wait --for=condition=ready pod -l app=postgres -n ${NAMESPACE} --timeout=${TIMEOUT} || {
        print_error "PostgreSQL pod failed to become ready"
        kubectl describe pod -l app=postgres -n ${NAMESPACE}
        exit 1
    }

    print_success "PostgreSQL deployed and ready"
}

deploy_application() {
    print_header "Deploying Application"

    echo "Creating ConfigMap..."
    kubectl apply -f app-configmap.yaml

    echo "Creating PersistentVolumeClaim for backups..."
    kubectl apply -f app-pvc.yaml

    echo "Deploying application..."
    kubectl apply -f app-deployment.yaml
    kubectl apply -f app-service.yaml

    echo "Waiting for application pods to be ready..."
    kubectl wait --for=condition=ready pod -l app=web-platform -n ${NAMESPACE} --timeout=${TIMEOUT} || {
        print_error "Application pods failed to become ready"
        kubectl describe pod -l app=web-platform -n ${NAMESPACE}
        exit 1
    }

    print_success "Application deployed and ready"
}

deploy_ingress() {
    print_header "Deploying Ingress (Optional)"

    if kubectl get ingressclass nginx &> /dev/null; then
        kubectl apply -f ingress.yaml
        print_success "Ingress deployed"
    else
        print_warning "NGINX Ingress Controller not found. Skipping ingress deployment."
        print_warning "Install ingress controller or use port-forwarding to access the app."
    fi
}

deploy_hpa() {
    print_header "Deploying HPA (Optional)"

    # Check if metrics-server is available
    if kubectl top nodes &> /dev/null; then
        kubectl apply -f hpa.yaml
        print_success "HPA deployed"
    else
        print_warning "Metrics Server not found. Skipping HPA deployment."
        print_warning "Install Metrics Server for autoscaling: https://github.com/kubernetes-sigs/metrics-server"
    fi
}

show_status() {
    print_header "Deployment Status"

    echo "Pods:"
    kubectl get pods -n ${NAMESPACE}

    echo ""
    echo "Services:"
    kubectl get svc -n ${NAMESPACE}

    echo ""
    echo "PVCs:"
    kubectl get pvc -n ${NAMESPACE}
}

show_access_info() {
    print_header "Access Information"

    echo "To access the application:"
    echo ""
    echo -e "${GREEN}Option 1: Port Forwarding${NC}"
    echo "  kubectl port-forward -n ${NAMESPACE} svc/web-platform 8080:80"
    echo "  Then visit: http://localhost:8080"
    echo ""

    # Check if LoadBalancer service exists
    if kubectl get svc web-platform -n ${NAMESPACE} -o jsonpath='{.status.loadBalancer.ingress[0].ip}' &> /dev/null; then
        LB_IP=$(kubectl get svc web-platform -n ${NAMESPACE} -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
        if [ -n "$LB_IP" ]; then
            echo -e "${GREEN}Option 2: LoadBalancer${NC}"
            echo "  http://${LB_IP}"
            echo ""
        fi
    fi

    # Check if ingress exists
    if kubectl get ingress -n ${NAMESPACE} &> /dev/null; then
        INGRESS_HOST=$(kubectl get ingress web-platform-ingress -n ${NAMESPACE} -o jsonpath='{.spec.rules[0].host}' 2>/dev/null)
        if [ -n "$INGRESS_HOST" ]; then
            echo -e "${GREEN}Option 3: Ingress${NC}"
            echo "  https://${INGRESS_HOST}"
            echo ""
        fi
    fi

    echo -e "${YELLOW}To view logs:${NC}"
    echo "  kubectl logs -f -l app=web-platform -n ${NAMESPACE}"
    echo ""
    echo -e "${YELLOW}To scale manually:${NC}"
    echo "  kubectl scale deployment web-platform -n ${NAMESPACE} --replicas=5"
}

# Main deployment flow
main() {
    print_header "Web Platform - Kubernetes Deployment"

    check_prerequisites
    deploy_namespace
    deploy_secrets
    deploy_postgres
    deploy_application
    deploy_ingress
    deploy_hpa

    echo ""
    show_status
    echo ""
    show_access_info

    echo ""
    print_success "Deployment completed successfully!"
}

# Run main function
main "$@"
