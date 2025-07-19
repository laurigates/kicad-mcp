"""
Unit tests for migration monitoring utilities.

Tests the migration monitoring and health check functionality.
"""

from datetime import datetime
from unittest.mock import patch

import pytest

from kicad_mcp.utils.migration_monitor import AlertThresholds, HealthMetrics, MigrationMonitor


class TestMigrationMonitor:
    """Test suite for MigrationMonitor class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.monitor = MigrationMonitor()
        self.sample_stats = {
            "generator": {"count": 100, "total_time": 5.0, "errors": 1},
            "handler": {"count": 50, "total_time": 2.5, "errors": 0},
            "fallbacks": 2,
        }

    def test_monitor_initialization(self):
        """Test monitor initialization."""
        assert self.monitor.logger is not None
        assert self.monitor.service is not None
        assert isinstance(self.monitor.thresholds, AlertThresholds)
        assert self.monitor.metrics_history == []

    def test_monitor_initialization_with_custom_thresholds(self):
        """Test monitor initialization with custom thresholds."""
        custom_thresholds = AlertThresholds(max_error_rate=2.0, max_response_time=10.0)
        monitor = MigrationMonitor(custom_thresholds)

        assert monitor.thresholds.max_error_rate == 2.0
        assert monitor.thresholds.max_response_time == 10.0

    def test_collect_metrics(self):
        """Test metrics collection."""
        with (
            patch.object(self.monitor.service, "get_performance_stats") as mock_stats,
            patch.object(self.monitor.service, "get_config_info") as mock_config,
        ):
            mock_stats.return_value = self.sample_stats
            mock_config.return_value = {"primary_implementation": "generator"}

            metrics = self.monitor.collect_metrics()

            assert isinstance(metrics, HealthMetrics)
            assert metrics.total_requests == 150  # 100 + 50
            assert metrics.error_rate == pytest.approx(0.67, rel=0.1)  # 1/150 * 100
            assert metrics.avg_response_time == 0.05  # 7.5/150
            assert metrics.fallback_rate == pytest.approx(1.33, rel=0.1)  # 2/150 * 100
            assert len(self.monitor.metrics_history) == 1

    def test_metrics_history_limit(self):
        """Test that metrics history is limited to prevent memory growth."""
        with (
            patch.object(self.monitor.service, "get_performance_stats") as mock_stats,
            patch.object(self.monitor.service, "get_config_info") as mock_config,
        ):
            mock_stats.return_value = self.sample_stats
            mock_config.return_value = {}

            # Collect more than 100 metrics
            for i in range(105):
                self.monitor.collect_metrics()

            # Should be limited to 100
            assert len(self.monitor.metrics_history) == 100

    def test_check_health_healthy(self):
        """Test health check with healthy metrics."""
        healthy_metrics = HealthMetrics(
            timestamp=datetime.now().isoformat(),
            error_rate=0.5,  # Below 1.0% threshold
            avg_response_time=2.0,  # Below 5.0s threshold
            fallback_rate=2.0,  # Below 5.0% threshold
            compatibility_rate=98.0,  # Above 95.0% threshold
            total_requests=100,
            handler_requests=50,
            generator_requests=50,
            validation_failures=0,
        )

        with patch.object(self.monitor, "collect_metrics", return_value=healthy_metrics):
            health = self.monitor.check_health()

            assert health["overall_status"] == "healthy"
            assert health["alerts"] == []
            assert "metrics" in health
            assert "thresholds" in health

    def test_check_health_with_alerts(self):
        """Test health check with alert conditions."""
        unhealthy_metrics = HealthMetrics(
            timestamp=datetime.now().isoformat(),
            error_rate=2.0,  # Above 1.0% threshold
            avg_response_time=6.0,  # Above 5.0s threshold
            fallback_rate=8.0,  # Above 5.0% threshold
            compatibility_rate=90.0,  # Below 95.0% threshold
            total_requests=100,
            handler_requests=50,
            generator_requests=50,
            validation_failures=5,
        )

        with patch.object(self.monitor, "collect_metrics", return_value=unhealthy_metrics):
            health = self.monitor.check_health()

            assert health["overall_status"] in ["warning", "critical"]
            assert len(health["alerts"]) == 4  # All thresholds exceeded

            # Check alert types
            alert_types = [alert["type"] for alert in health["alerts"]]
            assert "error_rate" in alert_types
            assert "response_time" in alert_types
            assert "fallback_rate" in alert_types
            assert "compatibility_rate" in alert_types

    def test_check_alerts_error_rate(self):
        """Test error rate alert detection."""
        metrics = HealthMetrics(
            timestamp=datetime.now().isoformat(),
            error_rate=2.0,  # Above 1.0% threshold
            avg_response_time=1.0,
            fallback_rate=1.0,
            compatibility_rate=98.0,
            total_requests=100,
            handler_requests=50,
            generator_requests=50,
            validation_failures=0,
        )

        alerts = self.monitor._check_alerts(metrics)

        assert len(alerts) == 1
        assert alerts[0]["type"] == "error_rate"
        assert alerts[0]["severity"] in ["warning", "critical"]
        assert "2.00%" in alerts[0]["message"]

    def test_check_alerts_critical_vs_warning(self):
        """Test critical vs warning alert severity."""
        # Warning level (just above threshold)
        warning_metrics = HealthMetrics(
            timestamp=datetime.now().isoformat(),
            error_rate=1.5,  # 1.5x threshold = warning
            avg_response_time=1.0,
            fallback_rate=1.0,
            compatibility_rate=98.0,
            total_requests=100,
            handler_requests=50,
            generator_requests=50,
            validation_failures=0,
        )

        alerts = self.monitor._check_alerts(warning_metrics)
        assert alerts[0]["severity"] == "warning"

        # Critical level (2x threshold)
        critical_metrics = HealthMetrics(
            timestamp=datetime.now().isoformat(),
            error_rate=3.0,  # 3x threshold = critical
            avg_response_time=1.0,
            fallback_rate=1.0,
            compatibility_rate=98.0,
            total_requests=100,
            handler_requests=50,
            generator_requests=50,
            validation_failures=0,
        )

        alerts = self.monitor._check_alerts(critical_metrics)
        assert alerts[0]["severity"] == "critical"

    def test_is_warning_level(self):
        """Test warning level detection."""
        warning_alerts = [{"severity": "warning"}, {"severity": "warning"}]
        assert self.monitor._is_warning_level(warning_alerts) is True

        mixed_alerts = [{"severity": "warning"}, {"severity": "critical"}]
        assert self.monitor._is_warning_level(mixed_alerts) is False

    def test_get_trend_analysis_insufficient_data(self):
        """Test trend analysis with insufficient data."""
        trend = self.monitor.get_trend_analysis()

        assert trend["status"] == "insufficient_data"
        assert "Not enough data" in trend["message"]

    def test_get_trend_analysis_with_data(self):
        """Test trend analysis with sufficient data."""
        # Add some metrics to history
        metrics1 = HealthMetrics(
            timestamp=(datetime.now()).isoformat(),
            error_rate=1.0,
            avg_response_time=2.0,
            fallback_rate=1.0,
            compatibility_rate=96.0,
            total_requests=100,
            handler_requests=25,
            generator_requests=75,
            validation_failures=0,
        )

        metrics2 = HealthMetrics(
            timestamp=datetime.now().isoformat(),
            error_rate=1.5,
            avg_response_time=2.5,
            fallback_rate=2.0,
            compatibility_rate=95.0,
            total_requests=200,
            handler_requests=100,
            generator_requests=100,
            validation_failures=0,
        )

        self.monitor.metrics_history = [metrics1, metrics2]

        trend = self.monitor.get_trend_analysis()

        assert "trends" in trend
        assert trend["data_points"] == 2
        assert trend["trends"]["error_rate_trend"] == 0.5  # 1.5 - 1.0
        assert trend["trends"]["response_time_trend"] == 0.5  # 2.5 - 2.0
        assert trend["trends"]["handler_adoption_rate"] == 50.0  # 100/200 * 100

    def test_generate_trend_summary(self):
        """Test trend summary generation."""
        trends = {
            "error_rate_trend": 0.6,  # Increasing
            "response_time_trend": -0.2,  # Improving
            "fallback_rate_trend": 2.0,  # Increasing
            "handler_adoption_rate": 75.0,  # High adoption
        }

        summary = self.monitor._generate_trend_summary(trends)

        assert "Error rate increasing" in summary
        assert "Response time improving" in summary
        assert "Fallback rate increasing" in summary
        assert "Handler adoption at 75.0%" in summary

    def test_generate_trend_summary_stable(self):
        """Test trend summary when metrics are stable."""
        stable_trends = {
            "error_rate_trend": 0.1,  # Small change
            "response_time_trend": 0.05,  # Small change
            "fallback_rate_trend": 0.5,  # Small change
            "handler_adoption_rate": 30.0,  # Low adoption
        }

        summary = self.monitor._generate_trend_summary(stable_trends)
        assert "Metrics stable" in summary

    def test_export_metrics(self, tmp_path):
        """Test metrics export functionality."""
        # Add some test metrics
        test_metrics = HealthMetrics(
            timestamp=datetime.now().isoformat(),
            error_rate=1.0,
            avg_response_time=2.0,
            fallback_rate=1.0,
            compatibility_rate=96.0,
            total_requests=100,
            handler_requests=50,
            generator_requests=50,
            validation_failures=0,
        )
        self.monitor.metrics_history = [test_metrics]

        export_file = tmp_path / "test_metrics.json"
        self.monitor.export_metrics(str(export_file))

        assert export_file.exists()

        import json

        with open(export_file) as f:
            data = json.load(f)

        assert "export_timestamp" in data
        assert "total_metrics" in data
        assert "thresholds" in data
        assert "metrics" in data
        assert len(data["metrics"]) == 1

    def test_generate_health_report(self):
        """Test health report generation."""
        with (
            patch.object(self.monitor, "check_health") as mock_health,
            patch.object(self.monitor, "get_trend_analysis") as mock_trend,
        ):
            mock_health.return_value = {
                "overall_status": "healthy",
                "timestamp": "2024-01-01T00:00:00",
                "metrics": {
                    "error_rate": 0.5,
                    "avg_response_time": 2.0,
                    "fallback_rate": 1.0,
                    "total_requests": 100,
                    "handler_requests": 50,
                },
                "alerts": [],
                "configuration": {
                    "primary_implementation": "handler",
                    "handler_enabled": True,
                    "rollout_percentage": 50,
                    "fallback_enabled": True,
                },
            }

            mock_trend.return_value = {
                "status": "success",
                "window_minutes": 60,
                "summary": "Metrics stable",
            }

            report = self.monitor.generate_health_report()

            assert "MIGRATION HEALTH REPORT" in report
            assert "🟢 HEALTHY" in report
            assert "Error Rate: 0.50%" in report
            assert "✅ No active alerts" in report
            assert "Metrics stable" in report


class TestAlertThresholds:
    """Test AlertThresholds dataclass."""

    def test_default_thresholds(self):
        """Test default threshold values."""
        thresholds = AlertThresholds()

        assert thresholds.max_error_rate == 1.0
        assert thresholds.max_response_time == 5.0
        assert thresholds.max_fallback_rate == 5.0
        assert thresholds.min_compatibility_rate == 95.0

    def test_custom_thresholds(self):
        """Test custom threshold values."""
        thresholds = AlertThresholds(
            max_error_rate=0.5,
            max_response_time=3.0,
            max_fallback_rate=2.0,
            min_compatibility_rate=98.0,
        )

        assert thresholds.max_error_rate == 0.5
        assert thresholds.max_response_time == 3.0
        assert thresholds.max_fallback_rate == 2.0
        assert thresholds.min_compatibility_rate == 98.0


class TestHealthMetrics:
    """Test HealthMetrics dataclass."""

    def test_health_metrics_creation(self):
        """Test HealthMetrics creation and attribute access."""
        metrics = HealthMetrics(
            timestamp="2024-01-01T00:00:00",
            error_rate=1.0,
            avg_response_time=2.0,
            fallback_rate=1.5,
            compatibility_rate=96.0,
            total_requests=100,
            handler_requests=50,
            generator_requests=50,
            validation_failures=2,
        )

        assert metrics.timestamp == "2024-01-01T00:00:00"
        assert metrics.error_rate == 1.0
        assert metrics.avg_response_time == 2.0
        assert metrics.fallback_rate == 1.5
        assert metrics.compatibility_rate == 96.0
        assert metrics.total_requests == 100
        assert metrics.handler_requests == 50
        assert metrics.generator_requests == 50
        assert metrics.validation_failures == 2
