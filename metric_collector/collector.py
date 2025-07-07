import psutil
import requests
import yaml
import logging
import time
import json
import os
import signal
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

class MetricCollector:
    def __init__(self, config_path="config.yaml"):
        self.config = self._load_config(config_path)
        self._setup_logging()
        self.running = True
        self.alert_cooldown = {}  # Track alert cooldowns to prevent spam

        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        logging.info(f"Received signal {signum}, shutting down gracefully...")
        self.running = False

    def _load_config(self, path):
        """Load configuration with error handling and validation."""
        try:
            config_path = Path(path)
            if not config_path.exists():
                raise FileNotFoundError(f"Configuration file not found: {path}")

            with open(config_path) as f:
                config = yaml.safe_load(f)

            # Validate required configuration sections
            required_sections = ['endpoint', 'interval_seconds', 'thresholds']
            for section in required_sections:
                if section not in config:
                    raise ValueError(f"Missing required configuration section: {section}")

            # Set default values for optional configurations
            config.setdefault('alerts', {
                'enabled': True,
                'cooldown_minutes': 5,
                'channels': ['log']
            })
            config.setdefault('metrics', {
                'include_network': True,
                'include_processes': False,
                'disk_usage_only': True
            })

            return config
        except Exception as e:
            print(f"Error loading configuration: {e}")
            sys.exit(1)

    def _setup_logging(self):
        """Setup structured JSON logging with timestamps and levels as per assignment requirements."""
        log_level = getattr(logging, self.config.get('log_level', 'INFO').upper())

        # Create logs directory if it doesn't exist
        log_dir = Path('logs')
        log_dir.mkdir(exist_ok=True)

        # Custom JSON formatter for structured logging
        class JSONFormatter(logging.Formatter):
            def format(self, record):
                log_entry = {
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "level": record.levelname,
                    "logger": record.name,
                    "message": record.getMessage(),
                    "module": record.module,
                    "function": record.funcName,
                    "line": record.lineno
                }

                # Add exception info if present
                if record.exc_info:
                    log_entry["exception"] = self.formatException(record.exc_info)

                # Add extra fields if present
                if hasattr(record, 'hostname'):
                    log_entry["hostname"] = record.hostname
                if hasattr(record, 'metric_type'):
                    log_entry["metric_type"] = record.metric_type
                if hasattr(record, 'duration'):
                    log_entry["duration_ms"] = record.duration

                return json.dumps(log_entry)

        # Configure handlers with JSON formatting
        file_handler = logging.FileHandler(log_dir / 'metrics_collector.log')
        file_handler.setFormatter(JSONFormatter())

        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(JSONFormatter())

        # Configure root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(log_level)
        root_logger.handlers.clear()
        root_logger.addHandler(file_handler)
        root_logger.addHandler(console_handler)

        self.logger = logging.getLogger(__name__)
        self.logger.info("Structured JSON logging initialized", extra={
            "hostname": psutil.os.uname().nodename,
            "log_level": logging.getLevelName(log_level)
        })

    def collect_metrics(self) -> Dict[str, Any]:
        """Gather comprehensive system metrics as per assignment requirements."""
        start_time = time.time()
        hostname = psutil.os.uname().nodename

        try:
            timestamp = datetime.utcnow().isoformat() + "Z"

            # CPU metrics - Assignment requires per-core and overall utilization
            self.logger.debug("Collecting CPU metrics", extra={"hostname": hostname, "metric_type": "cpu"})

            # Get per-core CPU percentages (assignment requirement)
            cpu_per_core = psutil.cpu_percent(interval=1, percpu=True)
            cpu_overall = psutil.cpu_percent(interval=0)  # Overall CPU

            cpu_data = {
                "overall_percent": cpu_overall,
                "per_core_percent": cpu_per_core,
                "core_count_physical": psutil.cpu_count(logical=False),
                "core_count_logical": psutil.cpu_count(logical=True),
                "load_average": list(os.getloadavg()) if hasattr(os, 'getloadavg') else None,
                "cpu_times": dict(psutil.cpu_times()._asdict()),
                "cpu_stats": dict(psutil.cpu_stats()._asdict()) if hasattr(psutil, 'cpu_stats') else None
            }

            # Memory metrics - Assignment requires total, used, free, % used
            self.logger.debug("Collecting memory metrics", extra={"hostname": hostname, "metric_type": "memory"})

            memory = psutil.virtual_memory()
            memory_data = {
                "total_bytes": memory.total,
                "used_bytes": memory.used,
                "free_bytes": memory.free,
                "available_bytes": memory.available,
                "percent_used": memory.percent,
                "buffers_bytes": getattr(memory, 'buffers', 0),
                "cached_bytes": getattr(memory, 'cached', 0),
                "shared_bytes": getattr(memory, 'shared', 0),
                # Human readable formats for easier understanding
                "total_gb": round(memory.total / (1024**3), 2),
                "used_gb": round(memory.used / (1024**3), 2),
                "free_gb": round(memory.free / (1024**3), 2),
                "available_gb": round(memory.available / (1024**3), 2)
            }

            # Swap memory metrics
            swap = psutil.swap_memory()
            swap_data = {
                "total_bytes": swap.total,
                "used_bytes": swap.used,
                "free_bytes": swap.free,
                "percent_used": swap.percent,
                "total_gb": round(swap.total / (1024**3), 2) if swap.total > 0 else 0,
                "used_gb": round(swap.used / (1024**3), 2) if swap.used > 0 else 0,
                "free_gb": round(swap.free / (1024**3), 2) if swap.free > 0 else 0
            }

            # Disk metrics - Assignment requires per filesystem: total, used, free, % used
            self.logger.debug("Collecting disk metrics", extra={"hostname": hostname, "metric_type": "disk"})

            disk_data = []
            for partition in psutil.disk_partitions():
                try:
                    # Skip special filesystems that don't have meaningful usage stats
                    if partition.fstype in ['tmpfs', 'devtmpfs', 'squashfs', 'overlay']:
                        continue

                    usage = psutil.disk_usage(partition.mountpoint)

                    # Assignment requirement: per filesystem with total, used, free, % used
                    filesystem_data = {
                        "device": partition.device,
                        "mountpoint": partition.mountpoint,
                        "filesystem_type": partition.fstype,
                        "mount_options": getattr(partition, 'opts', ''),

                        # Raw bytes
                        "total_bytes": usage.total,
                        "used_bytes": usage.used,
                        "free_bytes": usage.free,
                        "percent_used": round((usage.used / usage.total) * 100, 2) if usage.total > 0 else 0,

                        # Human readable formats
                        "total_gb": round(usage.total / (1024**3), 2),
                        "used_gb": round(usage.used / (1024**3), 2),
                        "free_gb": round(usage.free / (1024**3), 2),

                        # Additional useful metrics
                        "inodes_total": getattr(usage, 'inodes_total', None),
                        "inodes_used": getattr(usage, 'inodes_used', None),
                        "inodes_free": getattr(usage, 'inodes_free', None)
                    }

                    disk_data.append(filesystem_data)

                except (PermissionError, OSError) as e:
                    self.logger.warning(f"Cannot access disk {partition.device}: {e}",
                                      extra={"hostname": hostname, "device": partition.device})
                    continue

            # Disk I/O statistics
            try:
                disk_io = psutil.disk_io_counters()
                disk_io_data = {
                    "read_count": disk_io.read_count,
                    "write_count": disk_io.write_count,
                    "read_bytes": disk_io.read_bytes,
                    "write_bytes": disk_io.write_bytes,
                    "read_time": disk_io.read_time,
                    "write_time": disk_io.write_time
                } if disk_io else None
            except Exception:
                disk_io_data = None

            # Compile final metrics structure
            metrics = {
                "timestamp": timestamp,
                "hostname": hostname,
                "collection_duration_ms": round((time.time() - start_time) * 1000, 2),
                "cpu": cpu_data,
                "memory": memory_data,
                "swap": swap_data,
                "disk": {
                    "filesystems": disk_data,
                    "io_stats": disk_io_data
                }
            }

            # Optional network metrics
            if self.config['metrics'].get('include_network', True):
                self.logger.debug("Collecting network metrics", extra={"hostname": hostname, "metric_type": "network"})
                try:
                    net_io = psutil.net_io_counters()
                    metrics["network"] = {
                        "bytes_sent": net_io.bytes_sent,
                        "bytes_recv": net_io.bytes_recv,
                        "packets_sent": net_io.packets_sent,
                        "packets_recv": net_io.packets_recv,
                        "errors_in": net_io.errin,
                        "errors_out": net_io.errout,
                        "drops_in": net_io.dropin,
                        "drops_out": net_io.dropout
                    }
                except Exception as e:
                    self.logger.warning(f"Failed to collect network metrics: {e}",
                                      extra={"hostname": hostname})

            # Optional process metrics (top processes by CPU/memory)
            if self.config['metrics'].get('include_processes', False):
                self.logger.debug("Collecting process metrics", extra={"hostname": hostname, "metric_type": "processes"})
                try:
                    processes = []
                    for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent', 'username']):
                        try:
                            proc_info = proc.info
                            if proc_info['cpu_percent'] > 0 or proc_info['memory_percent'] > 0:
                                processes.append(proc_info)
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            continue

                    # Sort by CPU usage and take top 10
                    processes.sort(key=lambda x: x.get('cpu_percent', 0), reverse=True)
                    metrics["top_processes"] = processes[:10]
                except Exception as e:
                    self.logger.warning(f"Failed to collect process metrics: {e}",
                                      extra={"hostname": hostname})

            # Log successful collection
            collection_time = round((time.time() - start_time) * 1000, 2)
            self.logger.info("Metrics collection completed successfully", extra={
                "hostname": hostname,
                "duration_ms": collection_time,
                "cpu_cores": len(cpu_per_core),
                "filesystems_count": len(disk_data),
                "memory_usage_percent": memory_data["percent_used"]
            })

            return metrics

        except Exception as e:
            collection_time = round((time.time() - start_time) * 1000, 2)
            self.logger.error("Critical error during metrics collection", extra={
                "hostname": hostname,
                "duration_ms": collection_time,
                "error_type": type(e).__name__,
                "error_message": str(e)
            }, exc_info=True)

            # Return minimal error metrics to maintain data flow
            return {
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "hostname": hostname,
                "collection_duration_ms": collection_time,
                "error": {
                    "type": type(e).__name__,
                    "message": str(e),
                    "occurred_at": datetime.utcnow().isoformat() + "Z"
                },
                "status": "error"
            }

    def check_alerts(self, metrics: Dict[str, Any]) -> None:
        """Check metrics against thresholds and trigger alerts."""
        if not self.config.get('alerts', {}).get('enabled', True):
            return

        thresholds = self.config.get('thresholds', {})
        alerts_triggered = []

        # Check CPU threshold
        if 'cpu' in thresholds and 'cpu' in metrics:
            cpu_percent = metrics['cpu'].get('percent', 0)
            if cpu_percent > thresholds['cpu']:
                alerts_triggered.append(f"High CPU usage: {cpu_percent:.1f}% (threshold: {thresholds['cpu']}%)")

        # Check memory threshold
        if 'memory' in thresholds and 'memory' in metrics:
            memory_percent = metrics['memory'].get('percent', 0)
            if memory_percent > thresholds['memory']:
                alerts_triggered.append(f"High memory usage: {memory_percent:.1f}% (threshold: {thresholds['memory']}%)")

        # Check disk threshold
        if 'disk' in thresholds and 'disk' in metrics:
            disk_threshold = thresholds['disk']
            for disk in metrics['disk']:
                if isinstance(disk, dict) and 'percent' in disk:
                    if disk['percent'] > disk_threshold:
                        alerts_triggered.append(
                            f"High disk usage on {disk.get('mountpoint', 'unknown')}: "
                            f"{disk['percent']:.1f}% (threshold: {disk_threshold}%)"
                        )

        # Check swap threshold
        if 'swap' in thresholds and 'swap' in metrics:
            swap_percent = metrics['swap'].get('percent', 0)
            if swap_percent > thresholds['swap']:
                alerts_triggered.append(f"High swap usage: {swap_percent:.1f}% (threshold: {thresholds['swap']}%)")

        # Send alerts if any were triggered
        for alert_message in alerts_triggered:
            self._send_alert(alert_message)

    def _send_alert(self, message: str) -> None:
        """Send alert through configured channels with cooldown."""
        # Check cooldown to prevent alert spam
        cooldown_key = hash(message)
        cooldown_minutes = self.config.get('alerts', {}).get('cooldown_minutes', 5)
        current_time = datetime.utcnow()

        if cooldown_key in self.alert_cooldown:
            time_diff = (current_time - self.alert_cooldown[cooldown_key]).total_seconds() / 60
            if time_diff < cooldown_minutes:
                return  # Still in cooldown period

        self.alert_cooldown[cooldown_key] = current_time

        # Log alert
        self.logger.warning(f"ALERT: {message}")

        # Send to configured channels
        alert_channels = self.config.get('alerts', {}).get('channels', ['log'])

        for channel in alert_channels:
            try:
                if channel == 'slack':
                    self._send_slack_alert(message)
                elif channel == 'email':
                    self._send_email_alert(message)
                # 'log' channel is already handled above
            except Exception as e:
                self.logger.error(f"Failed to send alert via {channel}: {e}")

    def _send_slack_alert(self, message: str) -> None:
        """Send alert to Slack webhook."""
        webhook_url = self.config.get('alerts', {}).get('slack_webhook_url')
        if not webhook_url:
            self.logger.error("Slack webhook URL not configured")
            return

        payload = {
            "text": f"🚨 ALERT from {psutil.os.uname().nodename}: {message}",
            "username": "MetricsCollector",
            "icon_emoji": ":warning:"
        }

        response = requests.post(webhook_url, json=payload, timeout=10)
        response.raise_for_status()

    def _send_email_alert(self, message: str) -> None:
        """Send alert via email (placeholder for future implementation)."""
        # This would require SMTP configuration
        self.logger.info(f"Email alert (not implemented): {message}")

    def send_metrics(self) -> bool:
        """Send metrics to the cloud endpoint with robust retry logic and structured logging."""
        max_retries = self.config.get('endpoint', {}).get('max_retries', 3)
        retry_delay = self.config.get('endpoint', {}).get('retry_delay', 5)
        hostname = psutil.os.uname().nodename

        for attempt in range(max_retries):
            try:
                # Collect metrics
                start_time = time.time()
                metrics = self.collect_metrics()
                collection_time = round((time.time() - start_time) * 1000, 2)

                # Check for alerts before sending (assignment requirement)
                if not metrics.get('error'):  # Only check alerts if collection was successful
                    self.check_alerts(metrics)

                # Prepare payload for cloud ingestion (assignment requirement)
                payload = {
                    "hostname": metrics.get("hostname", hostname),
                    "metrics": metrics
                }

                # Send to cloud endpoint with structured logging
                send_start = time.time()
                self.logger.info("Sending metrics to cloud endpoint", extra={
                    "hostname": hostname,
                    "attempt": attempt + 1,
                    "max_retries": max_retries,
                    "endpoint_url": self.config["endpoint"]["url"],
                    "collection_duration_ms": collection_time
                })

                response = requests.post(
                    self.config["endpoint"]["url"],
                    json=payload,
                    timeout=self.config.get('endpoint', {}).get('timeout', 10),
                    headers={
                        'Content-Type': 'application/json',
                        'User-Agent': f'MetricsCollector/1.0 ({hostname})'
                    }
                )
                response.raise_for_status()

                send_time = round((time.time() - send_start) * 1000, 2)

                # Log successful transmission
                self.logger.info("Metrics sent successfully to cloud endpoint", extra={
                    "hostname": hostname,
                    "attempt": attempt + 1,
                    "response_status": response.status_code,
                    "send_duration_ms": send_time,
                    "total_duration_ms": collection_time + send_time,
                    "payload_size_bytes": len(json.dumps(payload))
                })

                return True

            except requests.exceptions.Timeout as e:
                self.logger.warning("Request timeout on metrics transmission", extra={
                    "hostname": hostname,
                    "attempt": attempt + 1,
                    "max_retries": max_retries,
                    "error": str(e),
                    "will_retry": attempt < max_retries - 1
                })

            except requests.exceptions.ConnectionError as e:
                self.logger.warning("Connection error on metrics transmission", extra={
                    "hostname": hostname,
                    "attempt": attempt + 1,
                    "max_retries": max_retries,
                    "error": str(e),
                    "will_retry": attempt < max_retries - 1
                })

            except requests.exceptions.HTTPError as e:
                self.logger.error("HTTP error on metrics transmission", extra={
                    "hostname": hostname,
                    "attempt": attempt + 1,
                    "status_code": e.response.status_code if e.response else None,
                    "error": str(e),
                    "will_retry": attempt < max_retries - 1
                })

            except Exception as e:
                self.logger.error("Unexpected error sending metrics", extra={
                    "hostname": hostname,
                    "attempt": attempt + 1,
                    "error_type": type(e).__name__,
                    "error": str(e)
                }, exc_info=True)
                break

            # Wait before retry (assignment requirement: robust error handling)
            if attempt < max_retries - 1:
                self.logger.info(f"Waiting {retry_delay}s before retry", extra={
                    "hostname": hostname,
                    "retry_delay_seconds": retry_delay
                })
                time.sleep(retry_delay)

        # All retries exhausted
        self.logger.error("Failed to send metrics after all retry attempts", extra={
            "hostname": hostname,
            "max_retries": max_retries,
            "endpoint_url": self.config["endpoint"]["url"]
        })
        return False

    def run(self) -> None:
        """Main execution loop with graceful shutdown handling."""
        self.logger.info("Starting Metrics Collector service...")
        self.logger.info(f"Collection interval: {self.config['interval_seconds']} seconds")
        self.logger.info(f"Endpoint: {self.config['endpoint']['url']}")

        while self.running:
            try:
                start_time = time.time()

                # Send metrics
                success = self.send_metrics()

                # Calculate sleep time to maintain consistent intervals
                elapsed_time = time.time() - start_time
                sleep_time = max(0, self.config["interval_seconds"] - elapsed_time)

                if sleep_time > 0:
                    time.sleep(sleep_time)
                else:
                    self.logger.warning(f"Metrics collection took {elapsed_time:.2f}s, "
                                      f"longer than interval of {self.config['interval_seconds']}s")

            except KeyboardInterrupt:
                self.logger.info("Received keyboard interrupt, shutting down...")
                break
            except Exception as e:
                self.logger.error(f"Unexpected error in main loop: {e}")
                time.sleep(5)  # Brief pause before retrying

        self.logger.info("Metrics Collector service stopped.")

def main():
    """Entry point for the metrics collector service."""
    import argparse

    parser = argparse.ArgumentParser(description='Linux Metrics Collector Service')
    parser.add_argument('--config', '-c', default='config.yaml',
                       help='Path to configuration file (default: config.yaml)')
    parser.add_argument('--test', '-t', action='store_true',
                       help='Run a single metrics collection test and exit')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose logging')

    args = parser.parse_args()

    try:
        collector = MetricCollector(config_path=args.config)

        if args.verbose:
            logging.getLogger().setLevel(logging.DEBUG)

        if args.test:
            print("Running metrics collection test...")
            metrics = collector.collect_metrics()
            print(json.dumps(metrics, indent=2))
            collector.check_alerts(metrics)
            print("Test completed successfully!")
        else:
            collector.run()

    except Exception as e:
        print(f"Failed to start metrics collector: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()