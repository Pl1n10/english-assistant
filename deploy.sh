#!/bin/bash

# 🎓 English Assistant - Deploy Script per Kubernetes
# Uso: ./deploy.sh [build|apply|delete|logs|status]

set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Configurazione
REGISTRY="your-registry"  # Cambia con il tuo registry
BACKEND_IMAGE="$REGISTRY/english-assistant-backend"
FRONTEND_IMAGE="$REGISTRY/english-assistant-frontend"
VERSION="latest"
NAMESPACE="english-assistant"

# Funzioni
function build_images() {
    echo -e "${BLUE}🔨 Building images...${NC}"
    
    echo -e "${YELLOW}Building backend...${NC}"
    docker build -f backend/Dockerfile.prod -t $BACKEND_IMAGE:$VERSION backend/
    
    echo -e "${YELLOW}Building frontend...${NC}"
    docker build -f frontend/Dockerfile.prod -t $FRONTEND_IMAGE:$VERSION frontend/
    
    echo -e "${GREEN}✅ Images built${NC}"
}

function push_images() {
    echo -e "${BLUE}📤 Pushing images...${NC}"
    docker push $BACKEND_IMAGE:$VERSION
    docker push $FRONTEND_IMAGE:$VERSION
    echo -e "${GREEN}✅ Images pushed${NC}"
}

function apply_k8s() {
    echo -e "${BLUE}☸️  Applying Kubernetes manifests...${NC}"
    
    kubectl apply -f k8s/00-namespace.yaml
    
    echo -e "${YELLOW}⚠️  Verifica secrets in k8s/01-secrets.yaml${NC}"
    read -p "Hai configurato i secrets? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${RED}Configura k8s/01-secrets.yaml prima di continuare${NC}"
        exit 1
    fi
    
    kubectl apply -f k8s/01-secrets.yaml
    kubectl apply -f k8s/02-postgres-pvc.yaml
    kubectl apply -f k8s/03-postgres.yaml
    kubectl apply -f k8s/04-redis.yaml
    
    echo -e "${YELLOW}⏳ Waiting for PostgreSQL...${NC}"
    kubectl wait --for=condition=ready pod -l app=postgres -n $NAMESPACE --timeout=120s
    
    kubectl apply -f k8s/05-backend.yaml
    kubectl apply -f k8s/06-frontend.yaml
    kubectl apply -f k8s/07-ingress.yaml
    
    echo -e "${GREEN}✅ All manifests applied${NC}"
}

function delete_k8s() {
    echo -e "${RED}🗑️  Deleting all resources...${NC}"
    read -p "Are you sure? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        kubectl delete namespace $NAMESPACE
        echo -e "${GREEN}✅ Resources deleted${NC}"
    fi
}

function show_logs() {
    POD_NAME=$1
    if [ -z "$POD_NAME" ]; then
        echo -e "${YELLOW}Available pods:${NC}"
        kubectl get pods -n $NAMESPACE
        echo ""
        echo "Usage: $0 logs <pod-name>"
        exit 1
    fi
    kubectl logs -f $POD_NAME -n $NAMESPACE
}

function show_status() {
    echo -e "${BLUE}📊 Cluster Status${NC}"
    echo ""
    echo -e "${YELLOW}Pods:${NC}"
    kubectl get pods -n $NAMESPACE
    echo ""
    echo -e "${YELLOW}Services:${NC}"
    kubectl get svc -n $NAMESPACE
    echo ""
    echo -e "${YELLOW}Ingress:${NC}"
    kubectl get ingress -n $NAMESPACE
}

function run_migrations() {
    echo -e "${BLUE}🔄 Running database migrations...${NC}"
    BACKEND_POD=$(kubectl get pods -n $NAMESPACE -l app=backend -o jsonpath='{.items[0].metadata.name}')
    kubectl exec -it $BACKEND_POD -n $NAMESPACE -- alembic upgrade head
    echo -e "${GREEN}✅ Migrations completed${NC}"
}

function register_teacher() {
    echo -e "${BLUE}📝 Registering teacher...${NC}"
    BACKEND_POD=$(kubectl get pods -n $NAMESPACE -l app=backend -o jsonpath='{.items[0].metadata.name}')
    
    read -p "Teacher name: " TEACHER_NAME
    read -p "Email: " EMAIL
    read -sp "Password: " PASSWORD
    echo ""
    read -p "Phone number: " PHONE
    
    kubectl exec -it $BACKEND_POD -n $NAMESPACE -- python -c "
import asyncio
from app.database import AsyncSessionLocal
from app.models import Teacher
from app.routes.auth import get_password_hash

async def create_teacher():
    async with AsyncSessionLocal() as db:
        teacher = Teacher(
            name='$TEACHER_NAME',
            email='$EMAIL',
            phone_number='$PHONE',
            hashed_password=get_password_hash('$PASSWORD'),
            settings={'lesson_duration': 60, 'price_per_lesson': 25}
        )
        db.add(teacher)
        await db.commit()
        print('✅ Teacher registered!')

asyncio.run(create_teacher())
"
}

function port_forward() {
    echo -e "${BLUE}🔌 Port forwarding...${NC}"
    echo "Frontend: http://localhost:3000"
    echo "Backend: http://localhost:8000"
    echo ""
    
    kubectl port-forward -n $NAMESPACE svc/frontend 3000:80 &
    kubectl port-forward -n $NAMESPACE svc/backend 8000:8000 &
    
    wait
}

# Main
case "$1" in
    build)
        build_images
        ;;
    push)
        build_images
        push_images
        ;;
    apply)
        apply_k8s
        ;;
    delete)
        delete_k8s
        ;;
    logs)
        show_logs $2
        ;;
    status)
        show_status
        ;;
    migrate)
        run_migrations
        ;;
    register)
        register_teacher
        ;;
    forward)
        port_forward
        ;;
    deploy)
        build_images
        push_images
        apply_k8s
        ;;
    *)
        echo "🎓 English Assistant - Deploy Script"
        echo ""
        echo "Usage: $0 {build|push|apply|delete|logs|status|migrate|register|forward|deploy}"
        echo ""
        echo "Commands:"
        echo "  build     - Build Docker images"
        echo "  push      - Build and push images"
        echo "  apply     - Apply Kubernetes manifests"
        echo "  delete    - Delete all resources"
        echo "  logs      - Show logs for a pod"
        echo "  status    - Show cluster status"
        echo "  migrate   - Run database migrations"
        echo "  register  - Register teacher"
        echo "  forward   - Port forward to localhost"
        echo "  deploy    - Full deploy (build + push + apply)"
        exit 1
        ;;
esac
