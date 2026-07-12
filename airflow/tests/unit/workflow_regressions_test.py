from datetime import date
from unittest.mock import Mock, patch

import pytest

from plugins.workflows.stock_collection.validators import (
    _get_trading_day_status,
    validate_data_quality,
    verify_task_dependencies,
)


class PullingTaskInstance:
    def __init__(self, values):
        self.values = values

    def xcom_pull(self, task_ids=None, key=None):
        return self.values.get(task_ids)


def test_data_quality_fails_on_incomplete_pipeline_report():
    ti = PullingTaskInstance(
        {
            "run_market_data_pipeline": {
                "success": False,
                "validation_success": False,
                "reports": [{"is_complete": False}],
            }
        }
    )

    with pytest.raises(ValueError, match="quality validation failed"):
        validate_data_quality(ti=ti)


def test_data_quality_returns_compact_summary_for_complete_pipeline():
    ti = PullingTaskInstance(
        {
            "run_market_data_pipeline": {
                "success": True,
                "validation_success": True,
                "reports": [{"is_complete": True}, {"is_complete": True}],
            }
        }
    )

    result = validate_data_quality(ti=ti)

    assert result["validation_completed"] is True
    assert result["reports_checked"] == 2
    assert "reports" not in result


def test_dependency_verifier_raises_instead_of_returning_false_green():
    ti = PullingTaskInstance(
        {
            "try_main_collection": {
                "status": "success",
                "stocks_fetched": 100,
                "total_stocks": 100,
                "success_count": 99,
                "error_count": 1,
                "api_success": True,
            },
            "execute_fallback_collection": None,
        }
    )

    with pytest.raises(ValueError, match="dependency chain is unhealthy"):
        verify_task_dependencies(ti=ti)


def test_trading_day_check_uses_backend_calendar_and_internal_token(monkeypatch):
    monkeypatch.setenv("INTERNAL_API_TOKEN", "service-secret")
    response = Mock()
    response.json.return_value = {
        "is_trading_day": False,
        "previous_trading_day": "2026-07-02",
    }

    with patch("requests.get") as request:
        request.return_value = response
        result = _get_trading_day_status("US", date(2026, 7, 3))

    response.raise_for_status.assert_called_once()
    assert result["is_trading_day"] is False
    assert request.call_args.kwargs["headers"] == {"X-Internal-Token": "service-secret"}
