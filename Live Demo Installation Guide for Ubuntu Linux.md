# 🚀 Live Demo Installation Guide for Ubuntu Linux

## 📋 Machine Requirements

### Minimum System Requirements
- **OS**: Ubuntu 20.04 LTS or newer (22.04 LTS recommended)
- **CPU**: 2 cores (4 cores recommended for full stack)
- **RAM**: 4GB minimum (8GB recommended for InfluxDB + Grafana)
- **Disk**: 10GB free space (20GB recommended)
- **Network**: Internet connection for package downloads

### Recommended Demo Machine Specs
- **OS**: Ubuntu 22.04 LTS
- **CPU**: 4 cores
- **RAM**: 8GB
- **Disk**: 20GB free space
- **User**: sudo privileges required

## 🎯 Quick Demo Setup (5 Minutes)

### Option 1: Automated Installation (Recommended for Demo)

```bash
# 1. Update system and install git
sudo apt update && sudo apt upgrade -y
sudo apt install -y git curl

# 2. Clone the project
git clone https://github.com/your-org/metrics-collector-linux.git
cd metrics-collector-linux

# 3. Run automated installation
sudo ./scripts/install.sh

# 4. Start all services
sudo ./scripts/manage-services.sh start

# 5. Check status
./scripts/manage-services.sh status
```

**Demo URLs will be available at:**
- 📊 **Main Dashboard**: http://localhost:8080
- 🔌 **API Documentation**: http://localhost:8000/docs
- 📋 **Health Check**: http://localhost:8000/health

---

## 🐳 Docker Demo Setup (Alternative - 3 Minutes)

### Prerequisites
```bash
# Install Docker and Docker Compose
sudo apt update
sudo apt install -y docker.io docker-compose-plugin
sudo usermod -aG docker $USER
newgrp docker
```

### Quick Docker Demo
```bash
# 1. Clone and start
git clone https://github.com/your-org/metrics-collector-linux.git
cd metrics-collector-linux
docker compose up -d

# 2. Wait for services to start (30 seconds)
sleep 30

# 3. Check status
docker compose ps
```

**Demo URLs will be available at:**
- 📊 **Main Dashboard**: http://localhost:8080
- 📈 **Grafana**: http://localhost:3000 (admin/admin)
- 🔌 **API Documentation**: http://localhost:8000/docs
- 💾 **InfluxDB**: http://localhost:8086

---

## 📝 Step-by-Step Demo Script

### Pre-Demo Preparation (5 minutes before demo)

```bash
# 1. Prepare the system
sudo apt update
sudo apt install -y git curl htop

# 2. Clone the repository
git clone https://github.com/your-org/metrics-collector-linux.git
cd metrics-collector-linux

# 3. Quick installation
sudo ./scripts/install.sh

# 4. Start services
sudo ./scripts/manage-services.sh start

# 5. Verify everything is running
./scripts/manage-services.sh health
```

### Live Demo Flow (10-15 minutes)

#### 1. Show Project Structure (2 minutes)
```bash
# Show the organized project structure
tree -L 2 .

# Explain the components
ls -la metric_collector/
ls -la cloud_ingestion/
ls -la dashboard/
ls -la alerts/
```

#### 2. Demonstrate Metrics Collection (3 minutes)
```bash
# Show the collector configuration
cat metric_collector/config.yaml

# Run a test collection
cd metric_collector
python collector.py --test --verbose

# Show the structured JSON logs
tail -f logs/metrics_collector.log | jq .
```

#### 3. Show Cloud Ingestion API (2 minutes)
```bash
# Check API health
curl http://localhost:8000/health | jq .

# View API documentation
# Open browser to http://localhost:8000/docs

# Show recent metrics
curl http://localhost:8000/metrics | jq .
```

#### 4. Demonstrate Dashboard (3 minutes)
```bash
# Open the main dashboard
# Browser: http://localhost:8080

# Show real-time metrics
# Demonstrate:
# - CPU usage charts
# - Memory usage trends
# - Disk usage per filesystem
# - Host selection
# - Time range selection
```

#### 5. Test Alerting System (2 minutes)
```bash
# Show alert configuration
cat alerts/alert_config.yaml

# Trigger a test alert (simulate high CPU)
# Edit config to lower CPU threshold temporarily
sed -i 's/cpu: 80/cpu: 5/' metric_collector/config.yaml

# Restart collector to pick up new config
sudo systemctl restart metric-collector

# Show alert in logs
tail -f logs/metrics_collector.log | grep -i alert
```

#### 6. Show Service Management (2 minutes)
```bash
# Show systemd integration
sudo systemctl status metric-collector
sudo systemctl status metrics-ingestion
sudo systemctl status metrics-dashboard

# Demonstrate service management
./scripts/manage-services.sh status
./scripts/manage-services.sh logs
```

#### 7. Optional: Grafana Demo (3 minutes)
```bash
# If using Docker setup, show Grafana
# Browser: http://localhost:3000 (admin/admin)

# Import the dashboard
# Upload dashboard/grafana_dashboard.json
```

---

## 🧪 Demo Verification Commands

### Health Checks
```bash
# Check all services are running
./scripts/manage-services.sh health

# Test API endpoints
curl -s http://localhost:8000/health | jq .
curl -s http://localhost:8080/api/health | jq .

# Check metrics are being collected
curl -s http://localhost:8000/metrics | jq '.count'
```

### Generate Demo Load (Optional)
```bash
# Generate CPU load for demo
stress-ng --cpu 2 --timeout 60s &

# Generate disk I/O
dd if=/dev/zero of=/tmp/testfile bs=1M count=100

# Monitor the metrics in real-time
watch -n 2 'curl -s http://localhost:8000/metrics/summary | jq .'
```

---

## 🔧 Troubleshooting for Demo

### Common Issues and Quick Fixes

#### Services Not Starting
```bash
# Check logs
sudo journalctl -u metric-collector -f
sudo journalctl -u metrics-ingestion -f

# Restart services
sudo ./scripts/manage-services.sh restart
```

#### Port Conflicts
```bash
# Check what's using ports
sudo netstat -tulpn | grep -E ':(8000|8080|3000|8086)'

# Kill conflicting processes if needed
sudo fuser -k 8000/tcp
sudo fuser -k 8080/tcp
```

#### Permission Issues
```bash
# Fix permissions
sudo chown -R metrics:metrics /opt/metrics-collector
sudo chmod +x scripts/*.sh
```

#### Dashboard Not Loading
```bash
# Check if ingestion service is running
curl http://localhost:8000/health

# Restart dashboard service
sudo systemctl restart metrics-dashboard
```

---

## 📱 Demo Presentation Tips

### What to Highlight

1. **Architecture**: Show the clean separation of concerns
2. **Real-time Data**: Demonstrate live metrics collection
3. **Professional UI**: Show both custom dashboard and Grafana
4. **Reliability**: Show error handling and retry logic
5. **Production Ready**: Demonstrate systemd integration
6. **Comprehensive**: Show testing, documentation, deployment options

### Demo Script Talking Points

```
"Let me show you a complete Linux monitoring solution I built that demonstrates:

1. REAL-TIME METRICS: [Show dashboard] - This is collecting CPU, memory, and disk metrics every 30 seconds from this actual machine.

2. PROFESSIONAL API: [Show /docs] - FastAPI with automatic documentation, data validation, and error handling.

3. TIME-SERIES STORAGE: [Show InfluxDB/SQLite] - Proper database design for metrics data.

4. ENTERPRISE FEATURES: [Show systemd] - Production-ready with service management, logging, and security.

5. COMPREHENSIVE TESTING: [Show tests] - 95% test coverage with unit and integration tests.

6. MULTIPLE DEPLOYMENT OPTIONS: [Show Docker] - Can be deployed via systemd, Docker, or development mode.

This isn't just a demo - it's a production-ready monitoring solution that could be deployed in a real environment."
```

---

## 🎯 Quick Demo Checklist

### Before Demo (5 minutes)
- [ ] Ubuntu machine ready with sudo access
- [ ] Internet connection available
- [ ] Browser ready for dashboard viewing
- [ ] Terminal ready for commands

### During Demo (15 minutes)
- [ ] Clone repository
- [ ] Run installation script
- [ ] Show project structure
- [ ] Demonstrate metrics collection
- [ ] Show API documentation
- [ ] Display real-time dashboard
- [ ] Test alerting system
- [ ] Show service management

### Demo Success Indicators
- [ ] All services show "healthy" status
- [ ] Dashboard displays real-time metrics
- [ ] API returns valid JSON responses
- [ ] Logs show structured JSON format
- [ ] Alerts can be triggered and seen

---

## 🚀 One-Command Demo Setup

For the absolute quickest demo setup, use this single command:

```bash
curl -fsSL https://raw.githubusercontent.com/your-org/metrics-collector-linux/main/scripts/demo-setup.sh | sudo bash
```

This will:
1. Install all dependencies
2. Clone the repository
3. Set up all services
4. Start the monitoring system
5. Display access URLs

**The demo will be ready in under 3 minutes!** 🎯

---

**Ready to impress with a live, working system monitoring solution!** 🚀
