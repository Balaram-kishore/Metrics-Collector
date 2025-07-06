"""
InfluxDB Adapter for Metrics Storage
Assignment requirement: Use a time-series store (InfluxDB)
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import json
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS
from influxdb_client.client.exceptions import InfluxDBError

logger = logging.getLogger(__name__)


class InfluxDBAdapter:
    """InfluxDB adapter for storing and retrieving metrics data."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize InfluxDB connection."""
        self.config = config
        self.client = None
        self.write_api = None
        self.query_api = None
        self.bucket = config.get('bucket', 'metrics')
        self.org = config.get('org', 'metrics-org')
        
        self._connect()
    
    def _connect(self):
        """Establish connection to InfluxDB."""
        try:
            self.client = InfluxDBClient(
                url=self.config.get('url', 'http://localhost:8086'),
                token=self.config.get('token'),
                org=self.org,
                timeout=self.config.get('timeout', 10000)
            )
            
            self.write_api = self.client.write_api(write_options=SYNCHRONOUS)
            self.query_api = self.client.query_api()
            
            # Test connection
            self.client.ping()
            logger.info("Successfully connected to InfluxDB", extra={
                "url": self.config.get('url'),
                "org": self.org,
                "bucket": self.bucket
            })
            
        except Exception as e:
            logger.error(f"Failed to connect to InfluxDB: {e}", exc_info=True)
            raise
    
    def store_metrics(self, hostname: str, metrics: Dict[str, Any]) -> bool:
        """Store metrics in InfluxDB."""
        try:
            points = self._convert_to_points(hostname, metrics)
            
            if not points:
                logger.warning("No valid points to write to InfluxDB")
                return False
            
            self.write_api.write(bucket=self.bucket, org=self.org, record=points)
            
            logger.info("Metrics stored successfully in InfluxDB", extra={
                "hostname": hostname,
                "points_count": len(points),
                "bucket": self.bucket
            })
            
            return True
            
        except InfluxDBError as e:
            logger.error(f"InfluxDB error storing metrics: {e}", extra={
                "hostname": hostname,
                "error_code": getattr(e, 'status', None)
            })
            return False
            
        except Exception as e:
            logger.error(f"Unexpected error storing metrics: {e}", extra={
                "hostname": hostname
            }, exc_info=True)
            return False
    
    def _convert_to_points(self, hostname: str, metrics: Dict[str, Any]) -> List[Point]:
        """Convert metrics dictionary to InfluxDB points."""
        points = []
        timestamp = datetime.fromisoformat(metrics['timestamp'].replace('Z', '+00:00'))
        
        try:
            # CPU metrics
            if 'cpu' in metrics:
                cpu_data = metrics['cpu']
                
                # Overall CPU point
                point = Point("cpu_usage") \
                    .tag("hostname", hostname) \
                    .tag("type", "overall") \
                    .field("percent", cpu_data.get('overall_percent', 0)) \
                    .field("core_count_physical", cpu_data.get('core_count_physical', 0)) \
                    .field("core_count_logical", cpu_data.get('core_count_logical', 0)) \
                    .time(timestamp, WritePrecision.S)
                points.append(point)
                
                # Per-core CPU points
                if 'per_core_percent' in cpu_data:
                    for i, core_percent in enumerate(cpu_data['per_core_percent']):
                        point = Point("cpu_usage") \
                            .tag("hostname", hostname) \
                            .tag("type", "per_core") \
                            .tag("core", str(i)) \
                            .field("percent", core_percent) \
                            .time(timestamp, WritePrecision.S)
                        points.append(point)
                
                # Load average
                if cpu_data.get('load_average'):
                    load_avg = cpu_data['load_average']
                    point = Point("load_average") \
                        .tag("hostname", hostname) \
                        .field("load_1m", load_avg[0] if len(load_avg) > 0 else 0) \
                        .field("load_5m", load_avg[1] if len(load_avg) > 1 else 0) \
                        .field("load_15m", load_avg[2] if len(load_avg) > 2 else 0) \
                        .time(timestamp, WritePrecision.S)
                    points.append(point)
            
            # Memory metrics
            if 'memory' in metrics:
                memory_data = metrics['memory']
                point = Point("memory_usage") \
                    .tag("hostname", hostname) \
                    .field("total_bytes", memory_data.get('total_bytes', 0)) \
                    .field("used_bytes", memory_data.get('used_bytes', 0)) \
                    .field("free_bytes", memory_data.get('free_bytes', 0)) \
                    .field("available_bytes", memory_data.get('available_bytes', 0)) \
                    .field("percent_used", memory_data.get('percent_used', 0)) \
                    .field("buffers_bytes", memory_data.get('buffers_bytes', 0)) \
                    .field("cached_bytes", memory_data.get('cached_bytes', 0)) \
                    .time(timestamp, WritePrecision.S)
                points.append(point)
            
            # Swap metrics
            if 'swap' in metrics:
                swap_data = metrics['swap']
                point = Point("swap_usage") \
                    .tag("hostname", hostname) \
                    .field("total_bytes", swap_data.get('total_bytes', 0)) \
                    .field("used_bytes", swap_data.get('used_bytes', 0)) \
                    .field("free_bytes", swap_data.get('free_bytes', 0)) \
                    .field("percent_used", swap_data.get('percent_used', 0)) \
                    .time(timestamp, WritePrecision.S)
                points.append(point)
            
            # Disk metrics
            if 'disk' in metrics and 'filesystems' in metrics['disk']:
                for fs in metrics['disk']['filesystems']:
                    point = Point("disk_usage") \
                        .tag("hostname", hostname) \
                        .tag("device", fs.get('device', '')) \
                        .tag("mountpoint", fs.get('mountpoint', '')) \
                        .tag("filesystem_type", fs.get('filesystem_type', '')) \
                        .field("total_bytes", fs.get('total_bytes', 0)) \
                        .field("used_bytes", fs.get('used_bytes', 0)) \
                        .field("free_bytes", fs.get('free_bytes', 0)) \
                        .field("percent_used", fs.get('percent_used', 0)) \
                        .time(timestamp, WritePrecision.S)
                    points.append(point)
                
                # Disk I/O metrics
                if metrics['disk'].get('io_stats'):
                    io_stats = metrics['disk']['io_stats']
                    point = Point("disk_io") \
                        .tag("hostname", hostname) \
                        .field("read_count", io_stats.get('read_count', 0)) \
                        .field("write_count", io_stats.get('write_count', 0)) \
                        .field("read_bytes", io_stats.get('read_bytes', 0)) \
                        .field("write_bytes", io_stats.get('write_bytes', 0)) \
                        .field("read_time", io_stats.get('read_time', 0)) \
                        .field("write_time", io_stats.get('write_time', 0)) \
                        .time(timestamp, WritePrecision.S)
                    points.append(point)
            
            # Network metrics
            if 'network' in metrics:
                network_data = metrics['network']
                point = Point("network_io") \
                    .tag("hostname", hostname) \
                    .field("bytes_sent", network_data.get('bytes_sent', 0)) \
                    .field("bytes_recv", network_data.get('bytes_recv', 0)) \
                    .field("packets_sent", network_data.get('packets_sent', 0)) \
                    .field("packets_recv", network_data.get('packets_recv', 0)) \
                    .field("errors_in", network_data.get('errors_in', 0)) \
                    .field("errors_out", network_data.get('errors_out', 0)) \
                    .field("drops_in", network_data.get('drops_in', 0)) \
                    .field("drops_out", network_data.get('drops_out', 0)) \
                    .time(timestamp, WritePrecision.S)
                points.append(point)
            
        except Exception as e:
            logger.error(f"Error converting metrics to InfluxDB points: {e}", extra={
                "hostname": hostname
            }, exc_info=True)
        
        return points
    
    def get_recent_metrics(self, hostname: Optional[str] = None, hours: int = 24) -> List[Dict]:
        """Retrieve recent metrics from InfluxDB."""
        try:
            # Build query
            time_filter = f"-{hours}h"
            hostname_filter = f'|> filter(fn: (r) => r["hostname"] == "{hostname}")' if hostname else ""
            
            query = f'''
            from(bucket: "{self.bucket}")
                |> range(start: {time_filter})
                {hostname_filter}
                |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
                |> sort(columns: ["_time"], desc: true)
                |> limit(n: 1000)
            '''
            
            result = self.query_api.query(org=self.org, query=query)
            
            metrics = []
            for table in result:
                for record in table.records:
                    metrics.append({
                        'timestamp': record.get_time().isoformat(),
                        'hostname': record.values.get('hostname'),
                        'measurement': record.get_measurement(),
                        'values': {k: v for k, v in record.values.items() 
                                 if not k.startswith('_') and k not in ['hostname', 'result', 'table']}
                    })
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error retrieving metrics from InfluxDB: {e}", exc_info=True)
            return []
    
    def get_summary_stats(self, hostname: Optional[str] = None, hours: int = 24) -> Dict:
        """Get summary statistics from InfluxDB."""
        try:
            time_filter = f"-{hours}h"
            hostname_filter = f'|> filter(fn: (r) => r["hostname"] == "{hostname}")' if hostname else ""
            
            query = f'''
            from(bucket: "{self.bucket}")
                |> range(start: {time_filter})
                {hostname_filter}
                |> filter(fn: (r) => r["_measurement"] == "cpu_usage" and r["type"] == "overall")
                |> mean(column: "_value")
            '''
            
            result = self.query_api.query(org=self.org, query=query)
            
            # This is a simplified example - you would build more comprehensive stats
            stats = {"avg_cpu": 0, "avg_memory": 0, "total_records": 0}
            
            for table in result:
                for record in table.records:
                    if record.get_field() == "percent":
                        stats["avg_cpu"] = record.get_value()
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting summary stats from InfluxDB: {e}", exc_info=True)
            return {}
    
    def cleanup_old_data(self, days_to_keep: int = 30) -> int:
        """Clean up old data from InfluxDB."""
        try:
            # InfluxDB handles retention policies automatically
            # This is a placeholder for custom cleanup logic if needed
            logger.info(f"InfluxDB cleanup requested for data older than {days_to_keep} days")
            return 0
            
        except Exception as e:
            logger.error(f"Error during InfluxDB cleanup: {e}", exc_info=True)
            return 0
    
    def close(self):
        """Close InfluxDB connection."""
        if self.client:
            self.client.close()
            logger.info("InfluxDB connection closed")
