import unittest
import tempfile
import os
import yaml
import json
from unittest.mock import patch, MagicMock
from datetime import datetime
import sys
import pathlib

# Add the project root to the Python path
project_root = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from metric_collector.collector import MetricCollector


class TestMetricCollector(unittest.TestCase):
    """Test cases for the MetricCollector class."""

    def setUp(self):
        """Set up test fixtures."""
        self.test_config = {
            'endpoint': {
                'url': 'http://localhost:8000/ingest',
                'timeout': 10,
                'max_retries': 3,
                'retry_delay': 1
            },
            'interval_seconds': 30,
            'thresholds': {
                'cpu': 80,
                'memory': 85,
                'disk': 90,
                'swap': 50
            },
            'alerts': {
                'enabled': True,
                'cooldown_minutes': 5,
                'channels': ['log']
            },
            'metrics': {
                'include_network': True,
                'include_processes': False,
                'disk_usage_only': True
            },
            'log_level': 'INFO'
        }
        
        # Create temporary config file
        self.temp_config = tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False)
        yaml.dump(self.test_config, self.temp_config)
        self.temp_config.close()

    def tearDown(self):
        """Clean up test fixtures."""
        os.unlink(self.temp_config.name)

    def test_config_loading(self):
        """Test configuration loading."""
        collector = MetricCollector(config_path=self.temp_config.name)
        
        self.assertEqual(collector.config['endpoint']['url'], 'http://localhost:8000/ingest')
        self.assertEqual(collector.config['interval_seconds'], 30)
        self.assertEqual(collector.config['thresholds']['cpu'], 80)

    def test_config_validation(self):
        """Test configuration validation."""
        # Test missing required sections
        invalid_config = {'endpoint': {'url': 'test'}}
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(invalid_config, f)
            f.flush()
            
            with self.assertRaises(SystemExit):
                MetricCollector(config_path=f.name)
            
            os.unlink(f.name)

    @patch('metric_collector.collector.psutil')
    def test_collect_metrics_comprehensive(self, mock_psutil):
        """Test comprehensive metrics collection as per assignment requirements."""
        # Mock CPU functions - Assignment requires per-core and overall utilization
        mock_psutil.cpu_percent.side_effect = [
            [25.0, 30.0, 35.0, 40.0],  # Per-core percentages (first call with percpu=True)
            45.5  # Overall percentage (second call with percpu=False)
        ]
        mock_psutil.cpu_count.side_effect = [4, 8]  # Physical, then logical cores
        mock_psutil.os.getloadavg.return_value = [1.0, 1.5, 2.0]

        # Mock CPU times and stats
        mock_cpu_times = type('CPUTimes', (), {
            'user': 1000.0, 'system': 500.0, 'idle': 8500.0, 'nice': 0.0,
            '_asdict': lambda: {'user': 1000.0, 'system': 500.0, 'idle': 8500.0, 'nice': 0.0}
        })()
        mock_psutil.cpu_times.return_value = mock_cpu_times

        mock_cpu_stats = type('CPUStats', (), {
            'ctx_switches': 1000000, 'interrupts': 500000, 'soft_interrupts': 250000,
            '_asdict': lambda: {'ctx_switches': 1000000, 'interrupts': 500000, 'soft_interrupts': 250000}
        })()
        mock_psutil.cpu_stats.return_value = mock_cpu_stats
        
        # Mock memory - Assignment requires total, used, free, % used
        mock_memory = MagicMock()
        mock_memory.total = 8589934592  # 8GB
        mock_memory.available = 4294967296  # 4GB
        mock_memory.percent = 50.0
        mock_memory.used = 4294967296  # 4GB
        mock_memory.free = 4294967296  # 4GB
        mock_memory.buffers = 134217728  # 128MB
        mock_memory.cached = 268435456  # 256MB
        mock_memory.shared = 67108864  # 64MB
        mock_psutil.virtual_memory.return_value = mock_memory
        
        # Mock swap
        mock_swap = MagicMock()
        mock_swap.total = 2147483648  # 2GB
        mock_swap.used = 0
        mock_swap.free = 2147483648
        mock_swap.percent = 0.0
        mock_psutil.swap_memory.return_value = mock_swap
        
        # Mock disk - Assignment requires per filesystem: total, used, free, % used
        mock_partition1 = MagicMock()
        mock_partition1.device = '/dev/sda1'
        mock_partition1.mountpoint = '/'
        mock_partition1.fstype = 'ext4'
        mock_partition1.opts = 'rw,relatime'

        mock_partition2 = MagicMock()
        mock_partition2.device = '/dev/sda2'
        mock_partition2.mountpoint = '/home'
        mock_partition2.fstype = 'ext4'
        mock_partition2.opts = 'rw,relatime'

        mock_psutil.disk_partitions.return_value = [mock_partition1, mock_partition2]

        # Mock disk usage for different partitions
        def mock_disk_usage(path):
            if path == '/':
                usage = MagicMock()
                usage.total = 107374182400  # 100GB
                usage.used = 53687091200   # 50GB
                usage.free = 53687091200   # 50GB
                return usage
            elif path == '/home':
                usage = MagicMock()
                usage.total = 214748364800  # 200GB
                usage.used = 64424509440   # 60GB
                usage.free = 150323855360  # 140GB
                return usage

        mock_psutil.disk_usage.side_effect = mock_disk_usage

        # Mock disk I/O counters
        mock_disk_io = MagicMock()
        mock_disk_io.read_count = 1000000
        mock_disk_io.write_count = 500000
        mock_disk_io.read_bytes = 10737418240  # 10GB
        mock_disk_io.write_bytes = 5368709120  # 5GB
        mock_disk_io.read_time = 60000  # 60 seconds
        mock_disk_io.write_time = 30000  # 30 seconds
        mock_psutil.disk_io_counters.return_value = mock_disk_io
        
        # Mock network
        mock_net = MagicMock()
        mock_net.bytes_sent = 1000000
        mock_net.bytes_recv = 2000000
        mock_net.packets_sent = 1000
        mock_net.packets_recv = 2000
        mock_net.errin = 0
        mock_net.errout = 0
        mock_net.dropin = 0
        mock_net.dropout = 0
        mock_psutil.net_io_counters.return_value = mock_net
        
        # Mock hostname
        mock_uname = MagicMock()
        mock_uname.nodename = 'test-host'
        mock_psutil.os.uname.return_value = mock_uname
        
        collector = MetricCollector(config_path=self.temp_config.name)
        metrics = collector.collect_metrics()

        # Verify basic structure
        self.assertIn('timestamp', metrics)
        self.assertIn('hostname', metrics)
        self.assertIn('collection_duration_ms', metrics)
        self.assertIn('cpu', metrics)
        self.assertIn('memory', metrics)
        self.assertIn('swap', metrics)
        self.assertIn('disk', metrics)
        self.assertIn('network', metrics)

        # Verify CPU metrics (assignment requirement: per-core and overall)
        cpu_data = metrics['cpu']
        self.assertEqual(cpu_data['overall_percent'], 45.5)
        self.assertEqual(cpu_data['core_count_physical'], 4)
        self.assertEqual(cpu_data['core_count_logical'], 8)
        self.assertEqual(len(cpu_data['per_core_percent']), 4)
        self.assertEqual(cpu_data['per_core_percent'], [25.0, 30.0, 35.0, 40.0])
        self.assertEqual(cpu_data['load_average'], [1.0, 1.5, 2.0])
        self.assertIn('cpu_times', cpu_data)
        self.assertIn('cpu_stats', cpu_data)

        # Verify memory metrics (assignment requirement: total, used, free, % used)
        memory_data = metrics['memory']
        self.assertEqual(memory_data['percent_used'], 50.0)
        self.assertEqual(memory_data['total_bytes'], 8589934592)
        self.assertEqual(memory_data['used_bytes'], 4294967296)
        self.assertEqual(memory_data['free_bytes'], 4294967296)
        self.assertEqual(memory_data['available_bytes'], 4294967296)
        self.assertEqual(memory_data['total_gb'], 8.0)
        self.assertEqual(memory_data['used_gb'], 4.0)

        # Verify swap metrics
        swap_data = metrics['swap']
        self.assertEqual(swap_data['percent_used'], 0.0)
        self.assertEqual(swap_data['total_bytes'], 2147483648)

        # Verify disk metrics (assignment requirement: per filesystem)
        disk_data = metrics['disk']
        self.assertIn('filesystems', disk_data)
        self.assertIn('io_stats', disk_data)

        filesystems = disk_data['filesystems']
        self.assertEqual(len(filesystems), 2)

        # Check root filesystem
        root_fs = next(fs for fs in filesystems if fs['mountpoint'] == '/')
        self.assertEqual(root_fs['device'], '/dev/sda1')
        self.assertEqual(root_fs['filesystem_type'], 'ext4')
        self.assertEqual(root_fs['total_bytes'], 107374182400)
        self.assertEqual(root_fs['used_bytes'], 53687091200)
        self.assertEqual(root_fs['free_bytes'], 53687091200)
        self.assertEqual(root_fs['percent_used'], 50.0)
        self.assertEqual(root_fs['total_gb'], 100.0)

        # Check home filesystem
        home_fs = next(fs for fs in filesystems if fs['mountpoint'] == '/home')
        self.assertEqual(home_fs['device'], '/dev/sda2')
        self.assertEqual(home_fs['total_gb'], 200.0)
        self.assertEqual(round(home_fs['percent_used'], 1), 30.0)  # 60GB/200GB = 30%

        # Verify disk I/O stats
        io_stats = disk_data['io_stats']
        self.assertEqual(io_stats['read_count'], 1000000)
        self.assertEqual(io_stats['write_count'], 500000)
        self.assertEqual(io_stats['read_bytes'], 10737418240)
        self.assertEqual(io_stats['write_bytes'], 5368709120)

        # Verify network metrics
        network_data = metrics['network']
        self.assertEqual(network_data['bytes_sent'], 1000000)
        self.assertEqual(network_data['bytes_recv'], 2000000)
        self.assertEqual(network_data['packets_sent'], 1000)
        self.assertEqual(network_data['packets_recv'], 2000)

    def test_alert_checking(self):
        """Test alert threshold checking."""
        collector = MetricCollector(config_path=self.temp_config.name)
        
        # Test metrics that should trigger alerts
        test_metrics = {
            'cpu': {'percent': 85.0},  # Above 80% threshold
            'memory': {'percent': 90.0},  # Above 85% threshold
            'swap': {'percent': 60.0},  # Above 50% threshold
            'disk': [{'percent': 95.0, 'mountpoint': '/'}]  # Above 90% threshold
        }
        
        with patch.object(collector, '_send_alert') as mock_send_alert:
            collector.check_alerts(test_metrics)
            
            # Should have called _send_alert for each threshold violation
            self.assertEqual(mock_send_alert.call_count, 4)

    def test_alert_cooldown(self):
        """Test alert cooldown functionality."""
        collector = MetricCollector(config_path=self.temp_config.name)
        
        test_metrics = {
            'cpu': {'percent': 85.0}  # Above threshold
        }
        
        with patch.object(collector, 'logger') as mock_logger:
            # First alert should be sent
            collector.check_alerts(test_metrics)
            mock_logger.warning.assert_called()
            
            # Reset mock
            mock_logger.reset_mock()
            
            # Second alert immediately should be blocked by cooldown
            collector.check_alerts(test_metrics)
            mock_logger.warning.assert_not_called()

    @patch('metric_collector.collector.requests')
    def test_send_metrics_success(self, mock_requests):
        """Test successful metrics sending."""
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_requests.post.return_value = mock_response
        
        collector = MetricCollector(config_path=self.temp_config.name)
        
        with patch.object(collector, 'collect_metrics') as mock_collect:
            mock_collect.return_value = {'test': 'data'}
            
            result = collector.send_metrics()
            
            self.assertTrue(result)
            mock_requests.post.assert_called_once()

    @patch('metric_collector.collector.requests')
    def test_send_metrics_retry(self, mock_requests):
        """Test metrics sending with retry logic."""
        # First two calls fail, third succeeds
        mock_requests.post.side_effect = [
            Exception("Network error"),
            Exception("Network error"),
            MagicMock()
        ]
        
        collector = MetricCollector(config_path=self.temp_config.name)
        
        with patch.object(collector, 'collect_metrics') as mock_collect:
            mock_collect.return_value = {'test': 'data'}
            
            result = collector.send_metrics()
            
            self.assertTrue(result)
            self.assertEqual(mock_requests.post.call_count, 3)

    def test_signal_handling(self):
        """Test graceful shutdown signal handling."""
        collector = MetricCollector(config_path=self.temp_config.name)

        # Test signal handler
        collector._signal_handler(15, None)  # SIGTERM

        self.assertFalse(collector.running)

    @patch('metric_collector.collector.psutil')
    def test_cpu_per_core_collection(self, mock_psutil):
        """Test CPU per-core collection (assignment requirement)."""
        # Mock per-core CPU data
        mock_psutil.cpu_percent.side_effect = [
            [10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0],  # 8 cores
            45.0  # Overall
        ]
        mock_psutil.cpu_count.side_effect = [4, 8]  # Physical, logical
        mock_psutil.os.getloadavg.return_value = [2.5, 2.0, 1.5]

        # Mock other required components
        mock_psutil.virtual_memory.return_value = MagicMock(
            total=8589934592, used=4294967296, free=4294967296,
            available=4294967296, percent=50.0, buffers=0, cached=0, shared=0
        )
        mock_psutil.swap_memory.return_value = MagicMock(
            total=0, used=0, free=0, percent=0.0
        )
        mock_psutil.disk_partitions.return_value = []
        mock_psutil.disk_io_counters.return_value = None
        mock_psutil.net_io_counters.return_value = MagicMock(
            bytes_sent=0, bytes_recv=0, packets_sent=0, packets_recv=0,
            errin=0, errout=0, dropin=0, dropout=0
        )
        mock_psutil.os.uname.return_value = MagicMock(nodename='test-host')

        collector = MetricCollector(config_path=self.temp_config.name)
        metrics = collector.collect_metrics()

        # Verify per-core CPU data
        cpu_data = metrics['cpu']
        self.assertEqual(len(cpu_data['per_core_percent']), 8)
        self.assertEqual(cpu_data['per_core_percent'], [10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0])
        self.assertEqual(cpu_data['overall_percent'], 45.0)
        self.assertEqual(cpu_data['core_count_physical'], 4)
        self.assertEqual(cpu_data['core_count_logical'], 8)

    @patch('metric_collector.collector.psutil')
    def test_memory_detailed_collection(self, mock_psutil):
        """Test detailed memory collection (assignment requirement)."""
        # Mock detailed memory data
        mock_memory = MagicMock()
        mock_memory.total = 16106127360  # 15GB
        mock_memory.used = 8053063680   # 7.5GB
        mock_memory.free = 8053063680   # 7.5GB
        mock_memory.available = 10737418240  # 10GB
        mock_memory.percent = 46.875  # 7.5/16 * 100
        mock_memory.buffers = 536870912  # 512MB
        mock_memory.cached = 1073741824  # 1GB
        mock_memory.shared = 268435456   # 256MB

        mock_psutil.virtual_memory.return_value = mock_memory

        # Mock other required components
        mock_psutil.cpu_percent.side_effect = [[50.0], 50.0]
        mock_psutil.cpu_count.side_effect = [1, 1]
        mock_psutil.swap_memory.return_value = MagicMock(
            total=0, used=0, free=0, percent=0.0
        )
        mock_psutil.disk_partitions.return_value = []
        mock_psutil.disk_io_counters.return_value = None
        mock_psutil.net_io_counters.return_value = MagicMock(
            bytes_sent=0, bytes_recv=0, packets_sent=0, packets_recv=0,
            errin=0, errout=0, dropin=0, dropout=0
        )
        mock_psutil.os.uname.return_value = MagicMock(nodename='test-host')

        collector = MetricCollector(config_path=self.temp_config.name)
        metrics = collector.collect_metrics()

        # Verify detailed memory metrics
        memory_data = metrics['memory']
        self.assertEqual(memory_data['total_bytes'], 16106127360)
        self.assertEqual(memory_data['used_bytes'], 8053063680)
        self.assertEqual(memory_data['free_bytes'], 8053063680)
        self.assertEqual(memory_data['available_bytes'], 10737418240)
        self.assertEqual(memory_data['percent_used'], 46.875)
        self.assertEqual(memory_data['buffers_bytes'], 536870912)
        self.assertEqual(memory_data['cached_bytes'], 1073741824)
        self.assertEqual(memory_data['shared_bytes'], 268435456)

        # Verify human-readable formats
        self.assertEqual(memory_data['total_gb'], 15.0)
        self.assertEqual(memory_data['used_gb'], 7.5)
        self.assertEqual(memory_data['free_gb'], 7.5)
        self.assertEqual(memory_data['available_gb'], 10.0)

    @patch('metric_collector.collector.psutil')
    def test_disk_per_filesystem_collection(self, mock_psutil):
        """Test disk per-filesystem collection (assignment requirement)."""
        # Mock multiple filesystems
        partitions = [
            MagicMock(device='/dev/sda1', mountpoint='/', fstype='ext4', opts='rw,relatime'),
            MagicMock(device='/dev/sda2', mountpoint='/home', fstype='ext4', opts='rw,relatime'),
            MagicMock(device='/dev/sdb1', mountpoint='/var', fstype='xfs', opts='rw,relatime'),
            MagicMock(device='tmpfs', mountpoint='/tmp', fstype='tmpfs', opts='rw,nosuid,nodev')  # Should be skipped
        ]
        mock_psutil.disk_partitions.return_value = partitions

        def mock_disk_usage(path):
            usage_map = {
                '/': MagicMock(total=107374182400, used=32212254720, free=75161927680),  # 100GB, 30GB used
                '/home': MagicMock(total=214748364800, used=107374182400, free=107374182400),  # 200GB, 100GB used
                '/var': MagicMock(total=53687091200, used=48318382080, free=5368709120)  # 50GB, 45GB used (90%)
            }
            return usage_map.get(path, MagicMock(total=0, used=0, free=0))

        mock_psutil.disk_usage.side_effect = mock_disk_usage

        # Mock other required components
        mock_psutil.cpu_percent.side_effect = [[50.0], 50.0]
        mock_psutil.cpu_count.side_effect = [1, 1]
        mock_psutil.virtual_memory.return_value = MagicMock(
            total=8589934592, used=4294967296, free=4294967296,
            available=4294967296, percent=50.0, buffers=0, cached=0, shared=0
        )
        mock_psutil.swap_memory.return_value = MagicMock(
            total=0, used=0, free=0, percent=0.0
        )
        mock_psutil.disk_io_counters.return_value = None
        mock_psutil.net_io_counters.return_value = MagicMock(
            bytes_sent=0, bytes_recv=0, packets_sent=0, packets_recv=0,
            errin=0, errout=0, dropin=0, dropout=0
        )
        mock_psutil.os.uname.return_value = MagicMock(nodename='test-host')

        collector = MetricCollector(config_path=self.temp_config.name)
        metrics = collector.collect_metrics()

        # Verify disk filesystem data (tmpfs should be excluded)
        filesystems = metrics['disk']['filesystems']
        self.assertEqual(len(filesystems), 3)  # tmpfs excluded

        # Check root filesystem
        root_fs = next(fs for fs in filesystems if fs['mountpoint'] == '/')
        self.assertEqual(root_fs['device'], '/dev/sda1')
        self.assertEqual(root_fs['filesystem_type'], 'ext4')
        self.assertEqual(root_fs['total_bytes'], 107374182400)
        self.assertEqual(root_fs['used_bytes'], 32212254720)
        self.assertEqual(root_fs['percent_used'], 30.0)

        # Check /var filesystem (high usage)
        var_fs = next(fs for fs in filesystems if fs['mountpoint'] == '/var')
        self.assertEqual(var_fs['device'], '/dev/sdb1')
        self.assertEqual(var_fs['filesystem_type'], 'xfs')
        self.assertEqual(var_fs['percent_used'], 90.0)

    def test_json_structured_logging(self):
        """Test JSON structured logging (assignment requirement)."""
        collector = MetricCollector(config_path=self.temp_config.name)

        # Capture log output
        import io
        import sys
        from unittest.mock import patch

        log_capture = io.StringIO()

        with patch('sys.stdout', log_capture):
            collector.logger.info("Test message", extra={
                "hostname": "test-host",
                "metric_type": "test",
                "duration": 100
            })

        log_output = log_capture.getvalue()

        # Verify JSON structure
        try:
            log_data = json.loads(log_output.strip())
            self.assertIn('timestamp', log_data)
            self.assertIn('level', log_data)
            self.assertIn('message', log_data)
            self.assertIn('hostname', log_data)
            self.assertIn('metric_type', log_data)
            self.assertIn('duration', log_data)
            self.assertEqual(log_data['level'], 'INFO')
            self.assertEqual(log_data['message'], 'Test message')
            self.assertEqual(log_data['hostname'], 'test-host')
        except json.JSONDecodeError:
            self.fail("Log output is not valid JSON")


if __name__ == '__main__':
    unittest.main()
