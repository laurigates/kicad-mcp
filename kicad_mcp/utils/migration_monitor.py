"""
Migration monitoring and health check utilities.

Provides real-time monitoring capabilities during the S-expression implementation
migration, including health checks, performance tracking, and alerting.
"""

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
import json
import logging
import time
from typing import Any

from kicad_mcp.utils.sexpr_service import get_sexpr_service


@dataclass
class HealthMetrics:
    """Health metrics for migration monitoring."""

    timestamp: str
    error_rate: float
    avg_response_time: float
    fallback_rate: float
    compatibility_rate: float
    total_requests: int
    handler_requests: int
    generator_requests: int
    validation_failures: int


@dataclass
class AlertThresholds:
    """Alert thresholds for migration monitoring."""

    max_error_rate: float = 1.0  # 1%
    max_response_time: float = 5.0  # 5 seconds
    max_fallback_rate: float = 5.0  # 5%
    min_compatibility_rate: float = 95.0  # 95%


class MigrationMonitor:
    """Monitor migration health and performance metrics."""

    def __init__(self, alert_thresholds: AlertThresholds | None = None):
        """Initialize the migration monitor."""
        self.logger = logging.getLogger(__name__)
        self.service = get_sexpr_service()
        self.thresholds = alert_thresholds or AlertThresholds()
        self.metrics_history: list[HealthMetrics] = []

    def collect_metrics(self) -> HealthMetrics:
        """Collect current health metrics."""
        stats = self.service.get_performance_stats()

        # Calculate totals
        total_requests = stats["generator"]["count"] + stats["handler"]["count"]
        total_errors = stats["generator"]["errors"] + stats["handler"]["errors"]
        total_time = stats["generator"]["total_time"] + stats["handler"]["total_time"]

        # Calculate rates
        error_rate = (total_errors / total_requests * 100) if total_requests > 0 else 0
        avg_response_time = (total_time / total_requests) if total_requests > 0 else 0
        fallback_rate = (stats["fallbacks"] / total_requests * 100) if total_requests > 0 else 0

        # Estimate compatibility rate (would need actual comparison data)
        compatibility_rate = 95.0  # Placeholder - would be calculated from real data

        metrics = HealthMetrics(
            timestamp=datetime.now().isoformat(),
            error_rate=error_rate,
            avg_response_time=avg_response_time,
            fallback_rate=fallback_rate,
            compatibility_rate=compatibility_rate,
            total_requests=total_requests,
            handler_requests=stats["handler"]["count"],
            generator_requests=stats["generator"]["count"],
            validation_failures=0,  # Would be tracked separately
        )

        self.metrics_history.append(metrics)

        # Keep only last 100 metrics to prevent memory growth
        if len(self.metrics_history) > 100:
            self.metrics_history = self.metrics_history[-100:]

        return metrics

    def check_health(self) -> dict[str, Any]:
        """Perform comprehensive health check."""
        metrics = self.collect_metrics()
        alerts = self._check_alerts(metrics)

        health_status = {
            "timestamp": metrics.timestamp,
            "overall_status": "healthy"
            if not alerts
            else "warning"
            if self._is_warning_level(alerts)
            else "critical",
            "metrics": asdict(metrics),
            "alerts": alerts,
            "thresholds": asdict(self.thresholds),
            "configuration": self.service.get_config_info(),
        }

        return health_status

    def _check_alerts(self, metrics: HealthMetrics) -> list[dict[str, Any]]:
        """Check for alert conditions."""
        alerts = []

        # Error rate alert
        if metrics.error_rate > self.thresholds.max_error_rate:
            alerts.append(
                {
                    "type": "error_rate",
                    "severity": "critical"
                    if metrics.error_rate > self.thresholds.max_error_rate * 2
                    else "warning",
                    "message": f"Error rate {metrics.error_rate:.2f}% exceeds threshold {self.thresholds.max_error_rate}%",
                    "current_value": metrics.error_rate,
                    "threshold": self.thresholds.max_error_rate,
                }
            )

        # Response time alert
        if metrics.avg_response_time > self.thresholds.max_response_time:
            alerts.append(
                {
                    "type": "response_time",
                    "severity": "critical"
                    if metrics.avg_response_time > self.thresholds.max_response_time * 2
                    else "warning",
                    "message": f"Average response time {metrics.avg_response_time:.3f}s exceeds threshold {self.thresholds.max_response_time}s",
                    "current_value": metrics.avg_response_time,
                    "threshold": self.thresholds.max_response_time,
                }
            )

        # Fallback rate alert
        if metrics.fallback_rate > self.thresholds.max_fallback_rate:
            alerts.append(
                {
                    "type": "fallback_rate",
                    "severity": "warning",  # Fallbacks are warnings, not critical
                    "message": f"Fallback rate {metrics.fallback_rate:.2f}% exceeds threshold {self.thresholds.max_fallback_rate}%",
                    "current_value": metrics.fallback_rate,
                    "threshold": self.thresholds.max_fallback_rate,
                }
            )

        # Compatibility rate alert
        if metrics.compatibility_rate < self.thresholds.min_compatibility_rate:
            alerts.append(
                {
                    "type": "compatibility_rate",
                    "severity": "critical"
                    if metrics.compatibility_rate < self.thresholds.min_compatibility_rate * 0.9
                    else "warning",
                    "message": f"Compatibility rate {metrics.compatibility_rate:.2f}% below threshold {self.thresholds.min_compatibility_rate}%",
                    "current_value": metrics.compatibility_rate,
                    "threshold": self.thresholds.min_compatibility_rate,
                }
            )

        return alerts

    def _is_warning_level(self, alerts: list[dict[str, Any]]) -> bool:
        """Check if alerts are only warning level."""
        return all(alert["severity"] == "warning" for alert in alerts)

    def get_trend_analysis(self, window_minutes: int = 60) -> dict[str, Any]:
        """Analyze trends over the specified time window."""
        cutoff_time = datetime.now() - timedelta(minutes=window_minutes)

        recent_metrics = [
            m for m in self.metrics_history if datetime.fromisoformat(m.timestamp) >= cutoff_time
        ]

        if len(recent_metrics) < 2:
            return {"status": "insufficient_data", "message": "Not enough data for trend analysis"}

        # Calculate trends
        first_metrics = recent_metrics[0]
        latest_metrics = recent_metrics[-1]

        trends = {
            "error_rate_trend": latest_metrics.error_rate - first_metrics.error_rate,
            "response_time_trend": latest_metrics.avg_response_time
            - first_metrics.avg_response_time,
            "fallback_rate_trend": latest_metrics.fallback_rate - first_metrics.fallback_rate,
            "request_volume_trend": latest_metrics.total_requests - first_metrics.total_requests,
            "handler_adoption_rate": (
                latest_metrics.handler_requests / latest_metrics.total_requests * 100
            )
            if latest_metrics.total_requests > 0
            else 0,
        }

        analysis = {
            "window_minutes": window_minutes,
            "data_points": len(recent_metrics),
            "trends": trends,
            "summary": self._generate_trend_summary(trends),
        }

        return analysis

    def _generate_trend_summary(self, trends: dict[str, float]) -> str:
        """Generate human-readable trend summary."""
        summaries = []

        if trends["error_rate_trend"] > 0.5:
            summaries.append("🔴 Error rate increasing")
        elif trends["error_rate_trend"] < -0.5:
            summaries.append("🟢 Error rate decreasing")

        if trends["response_time_trend"] > 0.1:
            summaries.append("🔴 Response time increasing")
        elif trends["response_time_trend"] < -0.1:
            summaries.append("🟢 Response time improving")

        if trends["fallback_rate_trend"] > 1.0:
            summaries.append("⚠️ Fallback rate increasing")

        if trends["handler_adoption_rate"] > 50:
            summaries.append(f"📈 Handler adoption at {trends['handler_adoption_rate']:.1f}%")

        if not summaries:
            summaries.append("📊 Metrics stable")

        return " | ".join(summaries)

    def export_metrics(self, file_path: str):
        """Export metrics history to JSON file."""
        try:
            metrics_data = {
                "export_timestamp": datetime.now().isoformat(),
                "total_metrics": len(self.metrics_history),
                "thresholds": asdict(self.thresholds),
                "metrics": [asdict(m) for m in self.metrics_history],
            }

            with open(file_path, "w") as f:
                json.dump(metrics_data, f, indent=2)

            self.logger.info(f"Metrics exported to {file_path}")

        except Exception as e:
            self.logger.error(f"Failed to export metrics: {e}")

    def generate_health_report(self) -> str:
        """Generate human-readable health report."""
        health = self.check_health()
        trend = self.get_trend_analysis()

        status_emoji = {"healthy": "🟢", "warning": "🟡", "critical": "🔴"}

        report = f"""
=== MIGRATION HEALTH REPORT ===
Status: {status_emoji.get(health["overall_status"], "❓")} {health["overall_status"].upper()}
Timestamp: {health["timestamp"]}

CURRENT METRICS:
• Error Rate: {health["metrics"]["error_rate"]:.2f}%
• Avg Response Time: {health["metrics"]["avg_response_time"]:.3f}s
• Fallback Rate: {health["metrics"]["fallback_rate"]:.2f}%
• Total Requests: {health["metrics"]["total_requests"]}
• Handler Requests: {health["metrics"]["handler_requests"]} ({health["metrics"]["handler_requests"] / max(health["metrics"]["total_requests"], 1) * 100:.1f}%)

CONFIGURATION:
• Implementation: {health["configuration"]["primary_implementation"]}
• Handler Enabled: {health["configuration"]["handler_enabled"]}
• Rollout Percentage: {health["configuration"]["rollout_percentage"]}%
• Fallback Enabled: {health["configuration"]["fallback_enabled"]}
"""

        if health["alerts"]:
            report += "\nALERTS:\n"
            for alert in health["alerts"]:
                severity_emoji = "🔴" if alert["severity"] == "critical" else "⚠️"
                report += f"• {severity_emoji} {alert['message']}\n"
        else:
            report += "\n✅ No active alerts\n"

        if trend["status"] != "insufficient_data":
            report += f"\nTREND ANALYSIS ({trend['window_minutes']} min):\n"
            report += f"• {trend['summary']}\n"

        return report


def monitor_migration(duration_minutes: int = 60, check_interval_seconds: int = 30):
    """
    Continuously monitor migration for specified duration.

    Args:
        duration_minutes: How long to monitor (minutes)
        check_interval_seconds: How often to check (seconds)
    """
    monitor = MigrationMonitor()

    start_time = datetime.now()
    end_time = start_time + timedelta(minutes=duration_minutes)

    print(f"Starting migration monitoring for {duration_minutes} minutes...")
    print(f"Check interval: {check_interval_seconds} seconds")
    print("=" * 50)

    try:
        while datetime.now() < end_time:
            health = monitor.check_health()

            # Print current status
            status_emoji = {"healthy": "🟢", "warning": "🟡", "critical": "🔴"}
            timestamp = datetime.now().strftime("%H:%M:%S")

            print(
                f"[{timestamp}] {status_emoji.get(health['overall_status'], '❓')} "
                f"Status: {health['overall_status']} | "
                f"Errors: {health['metrics']['error_rate']:.2f}% | "
                f"Resp: {health['metrics']['avg_response_time']:.3f}s | "
                f"Reqs: {health['metrics']['total_requests']}"
            )

            # Print alerts if any
            if health["alerts"]:
                for alert in health["alerts"]:
                    print(f"    ⚠️ {alert['message']}")

            time.sleep(check_interval_seconds)

    except KeyboardInterrupt:
        print("\nMonitoring stopped by user")

    # Final report
    print("\n" + "=" * 50)
    print("FINAL HEALTH REPORT:")
    print(monitor.generate_health_report())

    # Export metrics
    export_file = f"migration_metrics_{start_time.strftime('%Y%m%d_%H%M%S')}.json"
    monitor.export_metrics(export_file)
    print(f"\nMetrics exported to: {export_file}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Monitor S-expression migration health")
    parser.add_argument("--duration", type=int, default=60, help="Monitoring duration in minutes")
    parser.add_argument("--interval", type=int, default=30, help="Check interval in seconds")
    parser.add_argument("--report-only", action="store_true", help="Generate single health report")

    args = parser.parse_args()

    if args.report_only:
        monitor = MigrationMonitor()
        print(monitor.generate_health_report())
    else:
        monitor_migration(args.duration, args.interval)
