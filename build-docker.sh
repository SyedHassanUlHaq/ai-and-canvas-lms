#!/bin/bash

# AI Tutor SaaS Platform - Docker Build Script
# This script builds and runs the Docker containers for the AI Tutor platform

set -e

echo "🚀 Building AI Tutor SaaS Platform Docker Images..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    print_error "Docker is not running. Please start Docker and try again."
    exit 1
fi

# Check if credentials file exists
if [ ! -f "elivision-ai-1-4e63af45bd31.json" ]; then
    print_error "Google Cloud credentials file 'elivision-ai-1-4e63af45bd31.json' not found in project root."
    print_warning "Please ensure you have the credentials file in the project root directory."
    exit 1
fi

# Function to build and run development environment
build_dev() {
    print_status "Building development environment..."
    
    # Stop existing containers
    docker compose down --volumes --remove-orphans
    
    # Build images
    docker compose build --no-cache
    
    # Start services
    docker compose up -d
    
    print_success "Development environment started successfully!"
    print_status "Backend API available at: http://localhost:8000"
    print_status "Health check: http://localhost:8000/api/v1/health"
}

# Function to build and run production environment
build_prod() {
    print_status "Building production environment..."
    
    # Stop existing containers
    docker compose -f docker-compose.prod.yml down --volumes --remove-orphans
    
    # Build images
    docker compose -f docker-compose.prod.yml build --no-cache
    
    # Start services
    docker compose -f docker-compose.prod.yml up -d
    
    print_success "Production environment started successfully!"
    print_status "Backend API available at: http://localhost:8000"
    print_status "Health check: http://localhost:8000/api/v1/health"
}

# Function to stop all containers
stop_all() {
    print_status "Stopping all containers..."
    docker compose down --volumes --remove-orphans
    docker compose -f docker-compose.prod.yml down --volumes --remove-orphans
    print_success "All containers stopped!"
}

# Function to show logs
show_logs() {
    print_status "Showing backend logs..."
    docker compose logs -f backend
}

# Function to show status
show_status() {
    print_status "Container status:"
    docker compose ps
}

# Function to run tests in Docker
run_tests() {
    print_status "Running tests in Docker container..."
    docker compose exec backend pytest tests/ -v
}

# Function to clean up
cleanup() {
    print_status "Cleaning up Docker resources..."
    docker system prune -f
    docker volume prune -f
    print_success "Cleanup completed!"
}

# Main script logic
case "${1:-dev}" in
    "dev")
        build_dev
        ;;
    "prod")
        build_prod
        ;;
    "stop")
        stop_all
        ;;
    "logs")
        show_logs
        ;;
    "status")
        show_status
        ;;
    "test")
        run_tests
        ;;
    "cleanup")
        cleanup
        ;;
    "help"|"-h"|"--help")
        echo "Usage: $0 [COMMAND]"
        echo ""
        echo "Commands:"
        echo "  dev      Build and start development environment (default)"
        echo "  prod     Build and start production environment"
        echo "  stop     Stop all containers"
        echo "  logs     Show backend logs"
        echo "  status   Show container status"
        echo "  test     Run tests in Docker container"
        echo "  cleanup  Clean up Docker resources"
        echo "  help     Show this help message"
        echo ""
        echo "Examples:"
        echo "  $0          # Build and start dev environment"
        echo "  $0 prod     # Build and start production environment"
        echo "  $0 logs     # Show logs"
        echo "  $0 test     # Run tests"
        ;;
    *)
        print_error "Unknown command: $1"
        echo "Use '$0 help' for usage information"
        exit 1
        ;;
esac 