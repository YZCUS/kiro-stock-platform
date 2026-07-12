from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from plugins.services.storage_service import XComStorageManager
from plugins.workflows.storage_monitoring.health_checks import (
    check_storage_capacity,
    storage_health_check,
)


class ScanOnlyRedis:
    def __init__(self):
        self.scan_calls = []
        self.first_key_processed = False

    def scan_iter(self, *, match, count):
        self.scan_calls.append((match, count))
        yield b"airflow:xcom:external:one"
        assert self.first_key_processed, "scan results were materialized in memory"
        yield b"airflow:xcom:external:one:meta"

    def memory_usage(self, key):
        self.first_key_processed = True
        return 1024

    def ttl(self, key):
        self.first_key_processed = True
        return 60


def _storage_manager(redis_client):
    manager = object.__new__(XComStorageManager)
    manager.redis_client = redis_client
    manager.key_prefix = "airflow:xcom:external:"
    manager.metrics_key_prefix = "airflow:xcom:metrics:"
    manager.consecutive_failures = 0
    manager.last_health_check = 0
    manager.enable_monitoring = False
    manager.notification_manager = None
    return manager


def test_storage_stats_uses_incremental_scan_instead_of_keys():
    redis_client = ScanOnlyRedis()

    stats = _storage_manager(redis_client).get_storage_stats()

    assert redis_client.scan_calls == [("airflow:xcom:external:*", 500)]
    assert stats["total_items"] == 1
    assert stats["metadata_items"] == 1
    assert stats["redis_connected"] is True


def test_expired_cleanup_processes_scan_results_incrementally():
    redis_client = ScanOnlyRedis()

    cleaned = _storage_manager(redis_client).cleanup_expired_data()

    assert cleaned == 0
    assert redis_client.scan_calls == [("airflow:xcom:external:*", 500)]


def test_unhealthy_storage_check_fails_the_airflow_task():
    report = SimpleNamespace(
        is_healthy=False,
        total_items=0,
        total_size_mb=0,
        redis_connected=False,
        consecutive_failures=3,
        response_time_ms=0,
        issues=["Redis unavailable"],
        recommendations=[],
        timestamp="2026-07-12T00:00:00+08:00",
    )

    with (
        patch(
            "plugins.services.monitoring_service.run_health_check",
            return_value=report,
        ),
        patch(
            "plugins.services.monitoring_service.get_notification_manager",
            return_value=None,
        ),
    ):
        with pytest.raises(RuntimeError, match="Redis unavailable"):
            storage_health_check()


def test_capacity_check_fails_when_statistics_are_unavailable():
    dashboard = SimpleNamespace(
        storage_manager=Mock(
            get_storage_stats=Mock(return_value={"error": "Redis unavailable"})
        ),
        size_warning_threshold_mb=500,
        size_critical_threshold_mb=1000,
    )

    with patch(
        "plugins.services.monitoring_service.get_storage_dashboard",
        return_value=dashboard,
    ):
        with pytest.raises(RuntimeError, match="statistics unavailable"):
            check_storage_capacity()
