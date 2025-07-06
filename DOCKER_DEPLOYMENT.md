# Docker Deployment Guide

This guide explains how to deploy the entire Metrics Collector system using Docker and Docker Compose for reproducible deployment.

## 🐳 Prerequisites

- Docker Engine 20.10+
- Docker Compose 2.0+
- Linux host system (for system metrics collection)

### Install Docker (Ubuntu/Debian)

```bash
# Update package index
sudo apt-get update

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Install Docker Compose
sudo apt-get install docker-compose-plugin

# Add user to docker group
sudo usermod -aG docker $USER
newgrp docker
```

## 🚀 Quick Start

### 1. Clone and Deploy

```bash
# Clone the repository
git clone https://github.com/your-org/metrics-collector-linux.git
cd metrics-collector-linux

# Start all services
docker compose up -d
```

### 2. Verify Deployment

```bash
# Check all services are running
docker compose ps

# Check service health
docker compose exec metrics-ingestion curl http://localhost:8000/health
docker compose exec metrics-dashboard curl http://localhost:8080/api/health
```

### 3. Access Services

- **Dashboard**: http://localhost:8080
- **Grafana**: http://localhost:3000 (admin/admin)
- **InfluxDB**: http://localhost:8086
- **API Docs**: http://localhost:8000/docs

## 📋 Services Overview

### InfluxDB (Port 8086)
- **Purpose**: Time-series database for metrics storage
- **Credentials**: admin/adminpassword
- **Organization**: metrics-org
- **Bucket**: metrics
- **Token**: my-super-secret-auth-token

### Metrics Ingestion (Port 8000)
- **Purpose**: Receives and stores metrics from collectors
- **Health Check**: http://localhost:8000/health
- **API Documentation**: http://localhost:8000/docs

### Metrics Dashboard (Port 8080)
- **Purpose**: Web interface for viewing metrics
- **Health Check**: http://localhost:8080/api/health

### Metrics Collector
- **Purpose**: Collects system metrics from host
- **Network**: Host mode (required for system access)
- **Privileges**: Requires privileged mode for system metrics

### Grafana (Port 3000)
- **Purpose**: Professional dashboards and alerting
- **Credentials**: admin/admin
- **Pre-configured**: InfluxDB datasource and dashboard

## 🔧 Configuration

### Environment Variables

Create a `.env` file to customize deployment:

```bash
# .env file
INFLUXDB_ADMIN_PASSWORD=your-secure-password
INFLUXDB_TOKEN=your-super-secret-token
GRAFANA_ADMIN_PASSWORD=your-grafana-password
METRICS_COLLECTION_INTERVAL=30
```

### Custom Configuration

#### Metrics Collector Configuration

Edit `metric_collector/config.yaml`:

```yaml
endpoint:
  url: "http://localhost:8000/ingest"
  timeout: 10
  max_retries: 3

interval_seconds: 30

thresholds:
  cpu: 80
  memory: 85
  disk: 90
  swap: 50

alerts:
  enabled: true
  cooldown_minutes: 5
  channels:
    - log
    # - slack
    # - email
```

#### Database Configuration

Edit `cloud_ingestion/db_config.json`:

```json
{
  "type": "influxdb",
  "influxdb": {
    "url": "http://influxdb:8086",
    "token": "my-super-secret-auth-token",
    "org": "metrics-org",
    "bucket": "metrics",
    "timeout": 10000
  }
}
```

## 🔍 Monitoring and Logs

### View Logs

```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f metrics-collector
docker compose logs -f metrics-ingestion
docker compose logs -f metrics-dashboard

# Follow logs with timestamps
docker compose logs -f -t metrics-collector
```

### Service Status

```bash
# Check running containers
docker compose ps

# Check resource usage
docker stats

# Check service health
docker compose exec metrics-ingestion curl http://localhost:8000/health
```

### Access Container Shell

```bash
# Access ingestion service
docker compose exec metrics-ingestion bash

# Access collector service
docker compose exec metrics-collector bash

# Access InfluxDB CLI
docker compose exec influxdb influx
```

## 🛠️ Maintenance

### Update Services

```bash
# Pull latest images
docker compose pull

# Restart with new images
docker compose up -d
```

### Backup Data

```bash
# Backup InfluxDB data
docker compose exec influxdb influx backup /tmp/backup
docker compose cp influxdb:/tmp/backup ./influxdb-backup

# Backup Grafana data
docker compose cp grafana:/var/lib/grafana ./grafana-backup
```

### Scale Services

```bash
# Scale ingestion service
docker compose up -d --scale metrics-ingestion=3

# Scale with load balancer (requires additional configuration)
docker compose -f docker-compose.yml -f docker-compose.scale.yml up -d
```

## 🔒 Security Considerations

### Production Deployment

1. **Change Default Passwords**:
   ```bash
   # Update .env file
   INFLUXDB_ADMIN_PASSWORD=strong-password-here
   GRAFANA_ADMIN_PASSWORD=another-strong-password
   INFLUXDB_TOKEN=generate-secure-token-here
   ```

2. **Use Secrets Management**:
   ```yaml
   # docker-compose.prod.yml
   services:
     influxdb:
       environment:
         - DOCKER_INFLUXDB_INIT_PASSWORD_FILE=/run/secrets/influxdb_password
       secrets:
         - influxdb_password
   
   secrets:
     influxdb_password:
       file: ./secrets/influxdb_password.txt
   ```

3. **Network Security**:
   ```yaml
   # Restrict external access
   services:
     influxdb:
       ports:
         - "127.0.0.1:8086:8086"  # Only localhost access
   ```

4. **Resource Limits**:
   ```yaml
   services:
     metrics-collector:
       deploy:
         resources:
           limits:
             memory: 512M
             cpus: '0.5'
   ```

## 🧪 Testing

### Integration Testing

```bash
# Run integration tests
docker compose -f docker-compose.test.yml up --abort-on-container-exit

# Manual testing
curl http://localhost:8000/health
curl http://localhost:8080/api/health
curl http://localhost:3000/api/health
```

### Load Testing

```bash
# Generate test metrics
for i in {1..100}; do
  curl -X POST http://localhost:8000/ingest \
    -H "Content-Type: application/json" \
    -d "{\"hostname\":\"test-$i\",\"metrics\":{\"timestamp\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\"cpu\":{\"overall_percent\":$((RANDOM % 100))},\"memory\":{\"percent_used\":$((RANDOM % 100))},\"swap\":{\"percent_used\":0},\"disk\":{\"filesystems\":[]}}}"
done
```

## 🚨 Troubleshooting

### Common Issues

1. **Collector Can't Access System Metrics**:
   ```bash
   # Ensure privileged mode and host mounts
   docker compose logs metrics-collector
   ```

2. **InfluxDB Connection Issues**:
   ```bash
   # Check InfluxDB health
   docker compose exec influxdb curl http://localhost:8086/health
   
   # Verify token
   docker compose exec influxdb influx auth list
   ```

3. **Dashboard Shows No Data**:
   ```bash
   # Check ingestion service
   curl http://localhost:8000/metrics
   
   # Check collector logs
   docker compose logs metrics-collector
   ```

4. **High Resource Usage**:
   ```bash
   # Monitor resource usage
   docker stats
   
   # Adjust collection interval
   # Edit metric_collector/config.yaml
   interval_seconds: 60  # Increase from 30 to 60 seconds
   ```

### Debug Mode

```bash
# Run with debug logging
docker compose -f docker-compose.yml -f docker-compose.debug.yml up -d

# Access debug endpoints
curl http://localhost:8000/debug/metrics
curl http://localhost:8080/debug/status
```

## 📊 Performance Tuning

### Resource Optimization

```yaml
# docker-compose.prod.yml
services:
  metrics-collector:
    deploy:
      resources:
        limits:
          memory: 256M
          cpus: '0.25'
        reservations:
          memory: 128M
          cpus: '0.1'
  
  metrics-ingestion:
    deploy:
      resources:
        limits:
          memory: 512M
          cpus: '0.5'
```

### Database Optimization

```bash
# InfluxDB retention policy
docker compose exec influxdb influx bucket update \
  --name metrics \
  --retention 30d
```

## 🎯 Assignment Requirements Met

✅ **Reproducible Deployment**: Complete Docker Compose setup
✅ **Service Isolation**: Each component in separate container
✅ **Health Monitoring**: Health checks for all services
✅ **Persistent Storage**: Volumes for data persistence
✅ **Network Security**: Isolated network for services
✅ **Configuration Management**: Environment variables and config files
✅ **Logging**: Centralized logging with Docker
✅ **Scalability**: Services can be scaled independently

This Docker deployment provides a production-ready, reproducible setup that meets all assignment requirements for deployment and observability.
