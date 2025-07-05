import psutil
import requests
import yaml
import logging
import time
from datetime import datetime

class MetricCollector:
    def __init__(self, config_path="config.yaml"):
        self.config = self._load_config(config_path)
        self._setup_logging()

    def _load_config(self, path):
        with open(path) as f:
            return yaml.safe_load(f)

    def _setup_logging(self):
        logging.basicConfig(
            level=logging.INFO,
            format='{"time": "%(asctime)s", "level": "%(levelname)s", "message": %(message)s}'
        )

    def collect_metrics(self):
        """Gather CPU, memory, and disk metrics using psutil."""
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "cpu": psutil.cpu_percent(interval=1),
            "memory": dict(psutil.virtual_memory()._asdict()),
            "disk": [dict(part._asdict()) for part in psutil.disk_partitions()]
        }

    def send_metrics(self):
        """Send metrics to the cloud endpoint."""
        try:
            metrics = self.collect_metrics()
            resp = requests.post(
                self.config["endpoint"]["url"],
                json={
                    "hostname": psutil.os.uname().nodename,
                    "metrics": metrics
                },
                timeout=5
            )
            resp.raise_for_status()
            logging.info(f"Metrics sent successfully: {metrics}")
        except Exception as e:
            logging.error(f"Failed to send metrics: {str(e)}")

if __name__ == "__main__":
    collector = MetricCollector()
    while True:
        collector.send_metrics()
        time.sleep(collector.config["interval_seconds"])