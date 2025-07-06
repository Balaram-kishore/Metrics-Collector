#!/bin/bash

# Demo Setup Script for Linux Metrics Collector
# This script sets up the complete monitoring system for live demonstration

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# Demo configuration
DEMO_DIR="/tmp/metrics-collector-demo"
REPO_URL="https://github.com/your-org/metrics-collector-linux.git"

# Logging functions
log_info() {
    echo -e "${GREEN}[DEMO-SETUP]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[DEMO-SETUP]${NC} $1"
}

log_error() {
    echo -e "${RED}[DEMO-SETUP]${NC} $1"
}

log_header() {
    echo -e "${BLUE}[DEMO-SETUP]${NC} $1"
}

log_success() {
    echo -e "${PURPLE}[DEMO-SETUP]${NC} $1"
}

# Check if running as root
check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "This demo setup script must be run as root (use sudo)"
        exit 1
    fi
}

# Install system dependencies
install_dependencies() {
    log_header "Installing system dependencies..."
    
    # Update package list
    apt-get update -qq
    
    # Install required packages
    apt-get install -y \
        python3 \
        python3-pip \
        python3-venv \
        sqlite3 \
        curl \
        git \
        tree \
        htop \
        jq \
        stress-ng \
        net-tools \
        > /dev/null 2>&1
    
    log_info "System dependencies installed successfully"
}

# Clone repository
clone_repository() {
    log_header "Setting up demo environment..."
    
    # Remove existing demo directory if it exists
    if [[ -d "$DEMO_DIR" ]]; then
        rm -rf "$DEMO_DIR"
    fi
    
    # Create demo directory
    mkdir -p "$DEMO_DIR"
    cd "$DEMO_DIR"
    
    # Clone repository (or copy if running from local)
    if [[ -f "/tmp/metrics-collector-linux.tar.gz" ]]; then
        log_info "Using local project files..."
        tar -xzf /tmp/metrics-collector-linux.tar.gz
        mv metrics-collector-linux/* .
        rmdir metrics-collector-linux
    else
        log_info "Cloning repository..."
        git clone "$REPO_URL" .
    fi
    
    log_info "Demo environment prepared"
}

# Setup the monitoring system
setup_monitoring() {
    log_header "Installing metrics collector system..."
    
    # Make scripts executable
    chmod +x scripts/*.sh
    
    # Run the installation script
    ./scripts/install.sh > /dev/null 2>&1
    
    log_info "Metrics collector system installed"
}

# Start services
start_services() {
    log_header "Starting monitoring services..."
    
    # Start all services
    ./scripts/manage-services.sh start > /dev/null 2>&1
    
    # Wait for services to be ready
    log_info "Waiting for services to start..."
    sleep 10
    
    # Check service health
    local health_check_passed=false
    for i in {1..30}; do
        if curl -s http://localhost:8000/health > /dev/null 2>&1 && \
           curl -s http://localhost:8080/api/health > /dev/null 2>&1; then
            health_check_passed=true
            break
        fi
        sleep 2
    done
    
    if [[ "$health_check_passed" == "true" ]]; then
        log_info "All services started successfully"
    else
        log_warn "Services may still be starting up..."
    fi
}

# Display demo information
show_demo_info() {
    log_success "🚀 DEMO SETUP COMPLETE! 🚀"
    echo
    log_header "Demo Access URLs:"
    echo -e "  📊 ${GREEN}Main Dashboard${NC}:     http://localhost:8080"
    echo -e "  🔌 ${GREEN}API Documentation${NC}:  http://localhost:8000/docs"
    echo -e "  📋 ${GREEN}Health Check${NC}:       http://localhost:8000/health"
    echo -e "  📈 ${GREEN}API Metrics${NC}:        http://localhost:8000/metrics"
    echo
    log_header "Demo Commands:"
    echo -e "  ${YELLOW}cd $DEMO_DIR${NC}"
    echo -e "  ${YELLOW}./scripts/manage-services.sh status${NC}     # Check service status"
    echo -e "  ${YELLOW}./scripts/manage-services.sh health${NC}     # Health check all services"
    echo -e "  ${YELLOW}./scripts/manage-services.sh logs${NC}       # View service logs"
    echo -e "  ${YELLOW}curl http://localhost:8000/health | jq${NC}  # Test API"
    echo
    log_header "Demo Testing:"
    echo -e "  ${YELLOW}stress-ng --cpu 2 --timeout 30s${NC}        # Generate CPU load"
    echo -e "  ${YELLOW}watch -n 2 'curl -s http://localhost:8000/metrics/summary | jq .'${NC}"
    echo
    log_header "Project Structure:"
    echo -e "  ${YELLOW}tree -L 2 .${NC}                            # Show project layout"
    echo -e "  ${YELLOW}cat metric_collector/config.yaml${NC}       # View configuration"
    echo
    log_success "Demo is ready for presentation! 🎯"
}

# Cleanup function
cleanup_on_exit() {
    if [[ $? -ne 0 ]]; then
        log_error "Demo setup failed!"
        log_info "Check logs with: journalctl -u metric-collector -f"
        log_info "Or run: $DEMO_DIR/scripts/manage-services.sh status"
    fi
}

# Set up cleanup trap
trap cleanup_on_exit EXIT

# Main demo setup function
main() {
    log_header "🚀 Starting Linux Metrics Collector Demo Setup..."
    echo
    
    check_root
    install_dependencies
    clone_repository
    setup_monitoring
    start_services
    show_demo_info
    
    # Change ownership of demo directory to the original user
    if [[ -n "$SUDO_USER" ]]; then
        chown -R "$SUDO_USER:$SUDO_USER" "$DEMO_DIR"
        log_info "Demo directory ownership set to $SUDO_USER"
    fi
}

# Run main function
main "$@"
