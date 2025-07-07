# Grafana Dashboard Setup Guide

This guide explains how to set up Grafana with InfluxDB for visualizing system metrics as required by the assignment.

## Prerequisites

- InfluxDB 2.x installed and running
- Grafana installed and running
- Metrics collector sending data to InfluxDB

## Step 1: Install and Configure InfluxDB

### Install InfluxDB

```bash
# Ubuntu/Debian
wget -qO- https://repos.influxdata.com/influxdb.key | sudo apt-key add -
echo "deb https://repos.influxdata.com/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/influxdb.list
sudo apt-get update && sudo apt-get install influxdb2

# CentOS/RHEL
sudo yum install https://dl.influxdata.com/influxdb/releases/influxdb2-2.7.1.x86_64.rpm

# Start InfluxDB
sudo systemctl start influxdb
sudo systemctl enable influxdb
```

### Initial Setup

1. Open InfluxDB UI: http://localhost:8086
2. Complete the initial setup:
   - Username: admin
   - Password: (choose a secure password)
   - Organization: metrics-org
   - Bucket: metrics
3. Generate an API token:
   - Go to Data > API Tokens
   - Generate > All Access API Token
   - Copy the token for later use

### Configure Metrics Collector for InfluxDB

Update `cloud_ingestion/db_config.json`:

```json
{
  "type": "influxdb",
  "influxdb": {
    "url": "http://localhost:8086",
    "token": "your-api-token-here",
    "org": "metrics-org",
    "bucket": "metrics",
    "timeout": 10000
  }
}
```

## Step 2: Install and Configure Grafana

### Install Grafana

```bash
# Ubuntu/Debian
sudo apt-get install -y software-properties-common
sudo add-apt-repository "deb https://packages.grafana.com/oss/deb stable main"
wget -q -O - https://packages.grafana.com/gpg.key | sudo apt-key add -
sudo apt-get update && sudo apt-get install grafana

# CentOS/RHEL
sudo yum install https://dl.grafana.com/oss/release/grafana-10.0.0-1.x86_64.rpm

# Start Grafana
sudo systemctl start grafana-server
sudo systemctl enable grafana-server
```

### Access Grafana

1. Open Grafana UI: http://localhost:3000
2. Default login: admin/admin
3. Change the password when prompted

## Step 3: Configure InfluxDB Data Source

1. In Grafana, go to Configuration > Data Sources
2. Click "Add data source"
3. Select "InfluxDB"
4. Configure the data source:
   - **Name**: InfluxDB-Metrics
   - **URL**: http://localhost:8086
   - **Access**: Server (default)
   - **InfluxDB Details**:
     - Query Language: Flux
     - Organization: metrics-org
     - Token: (paste your InfluxDB API token)
     - Default Bucket: metrics
5. Click "Save & Test"

## Step 4: Import the Dashboard

### Method 1: Import JSON File

1. In Grafana, go to Dashboards > Import
2. Click "Upload JSON file"
3. Select `dashboard/grafana_dashboard.json`
4. Configure the dashboard:
   - Name: System Metrics Dashboard
   - Folder: General
   - UID: system-metrics
   - Data source: InfluxDB-Metrics
5. Click "Import"

### Method 2: Manual Creation

If you prefer to create the dashboard manually, create panels for:

1. **CPU Usage Overall (%)**: 
   ```flux
   from(bucket: "metrics")
     |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
     |> filter(fn: (r) => r["_measurement"] == "cpu_usage")
     |> filter(fn: (r) => r["type"] == "overall")
     |> filter(fn: (r) => r["_field"] == "percent")
     |> aggregateWindow(every: v.windowPeriod, fn: mean, createEmpty: false)
   ```

2. **CPU Usage Per Core (%)**: 
   ```flux
   from(bucket: "metrics")
     |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
     |> filter(fn: (r) => r["_measurement"] == "cpu_usage")
     |> filter(fn: (r) => r["type"] == "per_core")
     |> filter(fn: (r) => r["_field"] == "percent")
     |> aggregateWindow(every: v.windowPeriod, fn: mean, createEmpty: false)
   ```

3. **Memory Usage (%)**: 
   ```flux
   from(bucket: "metrics")
     |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
     |> filter(fn: (r) => r["_measurement"] == "memory_usage")
     |> filter(fn: (r) => r["_field"] == "percent_used")
     |> aggregateWindow(every: v.windowPeriod, fn: mean, createEmpty: false)
   ```

4. **Disk Usage Per Filesystem (%)**: 
   ```flux
   from(bucket: "metrics")
     |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
     |> filter(fn: (r) => r["_measurement"] == "disk_usage")
     |> filter(fn: (r) => r["_field"] == "percent_used")
     |> aggregateWindow(every: v.windowPeriod, fn: mean, createEmpty: false)
   ```

## Step 5: Configure Alerts (Optional)

1. In Grafana, go to Alerting > Alert Rules
2. Create alert rules for:
   - CPU usage > 80%
   - Memory usage > 85%
   - Disk usage > 90%

Example alert rule for CPU:
```
Query: Same as CPU panel query
Condition: IS ABOVE 80
Evaluation: every 1m for 5m
```

## Step 6: Verify the Setup

1. Start the metrics collector:
   ```bash
   cd metric_collector
   python collector.py
   ```

2. Check that data is flowing:
   - InfluxDB UI: Data Explorer should show incoming data
   - Grafana: Dashboard should display real-time metrics

## Troubleshooting

### No Data in Grafana

1. Check InfluxDB connection:
   ```bash
   curl -H "Authorization: Token YOUR_TOKEN" \
        "http://localhost:8086/api/v2/buckets?org=metrics-org"
   ```

2. Verify data in InfluxDB:
   ```flux
   from(bucket: "metrics")
     |> range(start: -1h)
     |> limit(n: 10)
   ```

3. Check Grafana data source configuration
4. Verify metrics collector is sending to InfluxDB

### Connection Issues

1. Ensure InfluxDB is running: `sudo systemctl status influxdb`
2. Check firewall settings
3. Verify network connectivity between services

### Performance Issues

1. Adjust query time ranges
2. Use appropriate aggregation windows
3. Consider data retention policies in InfluxDB

## Assignment Requirements Met

✅ **Time-series store**: InfluxDB for efficient time-series data storage
✅ **Grafana dashboard**: Visual plots for CPU, memory, disk usage over time
✅ **Real-time monitoring**: 30-second refresh rate
✅ **Multi-host support**: Hostname templating variable
✅ **Historical data**: Configurable time ranges

This setup provides a production-ready monitoring solution that meets all assignment requirements for visualization and time-series data storage.
