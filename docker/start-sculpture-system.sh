#!/bin/bash

# Sculpture System Docker Startup Script
# This script sets up and starts the complete sculpture system for testing

set -e

echo "🎨 Starting Sculpture System Docker Environment"
echo "================================================"

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
print_status "Checking Docker status..."
if ! docker info > /dev/null 2>&1; then
    print_error "Docker is not running. Please start Docker Desktop and try again."
    exit 1
fi
print_success "Docker is running"

# Check if WSL is available (for Windows users)
if command -v wsl > /dev/null 2>&1; then
    print_status "WSL detected - checking Ubuntu installation..."
    if wsl -l -v | grep -q "Ubuntu-22.04"; then
        print_success "Ubuntu 22.04 is installed in WSL"
        WSL_AVAILABLE=true
    else
        print_warning "Ubuntu 22.04 not found in WSL. Control server setup may be needed."
        WSL_AVAILABLE=false
    fi
else
    print_status "WSL not detected - assuming Linux environment"
    WSL_AVAILABLE=false
fi

# Navigate to docker directory
cd "$(dirname "$0")"
print_status "Working directory: $(pwd)"

# Build and start containers
print_status "Building and starting Docker containers..."
docker-compose down > /dev/null 2>&1 || true  # Clean up any existing containers
docker-compose up --build -d

# Wait for containers to start
print_status "Waiting for containers to initialize..."
sleep 10

# Check container status
print_status "Checking container status..."
if docker-compose ps | grep -q "Up"; then
    print_success "Containers are running"
    docker-compose ps
else
    print_error "Some containers failed to start"
    docker-compose ps
    exit 1
fi

# Test network connectivity
print_status "Testing container network connectivity..."
for i in {1..3}; do
    if docker exec sculpture$i ping -c 1 host.docker.internal > /dev/null 2>&1; then
        print_success "Sculpture $i can reach host"
    else
        print_warning "Sculpture $i cannot reach host - check Docker networking"
    fi
done

# Setup control server if WSL is available
if [ "$WSL_AVAILABLE" = true ]; then
    print_status "Setting up control server in WSL..."
    
    # Check if we can access WSL
    if wsl -d Ubuntu-22.04 -e bash -c "echo 'WSL access test'" > /dev/null 2>&1; then
        print_status "Installing control server services in WSL..."
        
        # Copy project to WSL if needed
        WSL_PROJECT_PATH="/home/$(wsl -d Ubuntu-22.04 -e whoami)/sculpture-system"
        
        wsl -d Ubuntu-22.04 -e bash -c "
            # Update package list
            sudo apt update > /dev/null 2>&1
            
            # Install Ansible if not present
            if ! command -v ansible > /dev/null 2>&1; then
                echo 'Installing Ansible...'
                sudo apt install -y ansible > /dev/null 2>&1
            fi
            
            # Create project directory
            mkdir -p $WSL_PROJECT_PATH
            
            echo 'Control server setup initiated in WSL'
        "
        
        print_success "WSL control server setup initiated"
        print_warning "You'll need to complete the setup manually in WSL"
    else
        print_warning "Cannot access WSL automatically. Please set up control server manually."
    fi
fi

# Display access information
echo ""
echo "🎉 Sculpture System Docker Environment Started!"
echo "=============================================="
echo ""
echo "📊 Container Access:"
echo "  • Sculpture 1: ssh -p 2201 pi@localhost (password: raspberry)"
echo "  • Sculpture 2: ssh -p 2202 pi@localhost (password: raspberry)"  
echo "  • Sculpture 3: ssh -p 2203 pi@localhost (password: raspberry)"
echo ""
echo "🌐 Web Interfaces (once control server is running):"
echo "  • Icecast Status:    http://localhost:8000"
echo "  • Control Dashboard: http://localhost:1880/ui"
echo ""
echo "🔧 Useful Commands:"
echo "  • View logs:         docker-compose logs -f"
echo "  • Stop system:       docker-compose down"
echo "  • Restart:           docker-compose restart"
echo "  • Container shell:   docker exec -it sculpture1 bash"
echo ""
echo "📋 Next Steps:"
if [ "$WSL_AVAILABLE" = true ]; then
    echo "  1. Open WSL Ubuntu terminal"
    echo "  2. Run: cd /mnt/c/Users/$(whoami)/source/repos/yaga2025sculptures"
    echo "  3. Run: ansible-playbook server/ansible/install_control_node.yml"
    echo "  4. Start services: sudo systemctl start icecast2 mosquitto liquidsoap node-red"
else
    echo "  1. Set up control server (Icecast, Liquidsoap, Mosquitto, Node-RED)"
    echo "  2. Configure services to listen on localhost"
fi
echo "  5. Open http://localhost:8000 to verify audio streams"
echo "  6. Open http://localhost:1880/ui for the control dashboard"
echo ""
echo "📖 For detailed instructions, see: docker/README-Docker-Testing.md"
echo ""

# Monitor containers for a few seconds
print_status "Monitoring containers for 30 seconds..."
timeout 30 docker-compose logs -f || true

print_success "Sculpture system is ready for testing!" 