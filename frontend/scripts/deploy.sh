#!/bin/bash

# Production Deployment Script
set -e

echo "🚀 Starting deployment process..."

# Configuration
DOCKER_IMAGE_NAME="stock-analysis-frontend"
DOCKER_TAG="${1:-latest}"
CONTAINER_NAME="stock-frontend"
PORT="${2:-3000}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    log_error "Docker is not running. Please start Docker and try again."
    exit 1
fi

# Check if required files exist
if [ ! -f "package.json" ]; then
    log_error "package.json not found. Please run this script from the frontend directory."
    exit 1
fi

if [ ! -f "Dockerfile" ]; then
    log_error "Dockerfile not found. Please ensure Dockerfile exists in the frontend directory."
    exit 1
fi

# Environment validation
log_info "Validating environment configuration..."

if [ ! -f ".env.production" ] && [ ! -f ".env.local" ]; then
    log_warn "No production environment file found. Using default configuration."
fi

# Pre-deployment checks
log_info "Running pre-deployment checks..."

# Type checking
log_info "Running TypeScript type checking..."
npm run type-check

# Linting
log_info "Running ESLint..."
npm run lint

# Tests (if available)
if npm run test --dry-run > /dev/null 2>&1; then
    log_info "Running tests..."
    npm run test
else
    log_warn "No tests found or test script not configured."
fi

# Build Docker image
log_info "Building Docker image: $DOCKER_IMAGE_NAME:$DOCKER_TAG"
docker build -t "$DOCKER_IMAGE_NAME:$DOCKER_TAG" .

# Stop existing container if running
if docker ps -q -f name="$CONTAINER_NAME" | grep -q .; then
    log_info "Stopping existing container: $CONTAINER_NAME"
    docker stop "$CONTAINER_NAME"
fi

# Remove existing container if exists
if docker ps -aq -f name="$CONTAINER_NAME" | grep -q .; then
    log_info "Removing existing container: $CONTAINER_NAME"
    docker rm "$CONTAINER_NAME"
fi

# Run new container
log_info "Starting new container: $CONTAINER_NAME on port $PORT"
docker run -d \
    --name "$CONTAINER_NAME" \
    --restart unless-stopped \
    -p "$PORT:3000" \
    --env-file .env.production 2>/dev/null || \
    docker run -d \
        --name "$CONTAINER_NAME" \
        --restart unless-stopped \
        -p "$PORT:3000" \
        "$DOCKER_IMAGE_NAME:$DOCKER_TAG"

# Wait for container to be ready
log_info "Waiting for container to be ready..."
sleep 5

# Health check
max_attempts=30
attempt=1

while [ $attempt -le $max_attempts ]; do
    if curl -f http://localhost:$PORT/api/health > /dev/null 2>&1; then
        log_info "✅ Application is healthy and ready!"
        break
    fi

    if [ $attempt -eq $max_attempts ]; then
        log_error "❌ Health check failed after $max_attempts attempts"
        log_error "Container logs:"
        docker logs "$CONTAINER_NAME" --tail 20
        exit 1
    fi

    log_info "Health check attempt $attempt/$max_attempts..."
    sleep 2
    ((attempt++))
done

# Show deployment summary
echo ""
log_info "🎉 Deployment completed successfully!"
echo ""
echo "📊 Deployment Summary:"
echo "  Container Name: $CONTAINER_NAME"
echo "  Image: $DOCKER_IMAGE_NAME:$DOCKER_TAG"
echo "  Port: $PORT"
echo "  Health Check: http://localhost:$PORT/api/health"
echo "  Application: http://localhost:$PORT"
echo ""

# Show container status
docker ps -f name="$CONTAINER_NAME" --format "table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}"

echo ""
log_info "Useful commands:"
echo "  View logs: docker logs $CONTAINER_NAME -f"
echo "  Stop container: docker stop $CONTAINER_NAME"
echo "  Restart container: docker restart $CONTAINER_NAME"
echo "  Remove container: docker rm -f $CONTAINER_NAME"
echo "  Shell into container: docker exec -it $CONTAINER_NAME sh"