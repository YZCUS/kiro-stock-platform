from datetime import datetime
from unittest.mock import Mock, patch

import pytest

from plugins.operators.api_operator import APICallOperator


def _context():
    task_instance = Mock(
        dag_id="test_dag",
        task_id="call_api",
        execution_date=datetime(2026, 7, 12),
    )
    return {"task_instance": task_instance}


def _response(payload):
    response = Mock()
    response.json.return_value = payload
    response.raise_for_status.return_value = None
    return response


def test_get_uses_normalized_url_query_and_internal_token():
    operator = APICallOperator(
        task_id="call_api",
        base_url="http://backend:8000/api/v1/",
        endpoint="stocks/active",
        query_params={"market": "US"},
        internal_token="service-secret",
        use_external_storage=False,
    )

    with patch("plugins.operators.api_operator.requests.get") as request:
        request.return_value = _response({"items": []})
        assert operator.execute(_context()) == {"items": []}

    request.assert_called_once_with(
        "http://backend:8000/api/v1/stocks/active",
        params={"market": "US"},
        headers={"X-Internal-Token": "service-secret"},
        timeout=300,
    )


def test_post_sends_json_and_rejects_application_failure():
    operator = APICallOperator(
        task_id="call_api",
        endpoint="/stocks/collect-all",
        method="POST",
        payload={"market": "US"},
        internal_token="service-secret",
        use_external_storage=False,
    )

    with patch("plugins.operators.api_operator.requests.post") as request:
        request.return_value = _response(
            {"success": False, "message": "provider unavailable"}
        )
        with pytest.raises(Exception, match="provider unavailable"):
            operator.execute(_context())

    request.assert_called_once_with(
        "http://backend:8000/api/v1/stocks/collect-all",
        params=None,
        json={"market": "US"},
        headers={"X-Internal-Token": "service-secret"},
        timeout=300,
    )


def test_large_response_returns_external_storage_reference():
    operator = APICallOperator(
        task_id="call_api",
        endpoint="/stocks/active",
        max_xcom_size=10,
    )

    with (
        patch("plugins.operators.api_operator.requests.get") as request,
        patch(
            "plugins.operators.api_operator.store_large_data",
            return_value="stored-ref",
        ),
    ):
        request.return_value = _response({"items": [{"symbol": "AAPL"}]})
        result = operator.execute(_context())

    assert result["external_storage"] is True
    assert result["reference_id"] == "stored-ref"
    assert result["summary"]["items_count"] == 1


def test_unsupported_http_method_fails_before_network_call():
    operator = APICallOperator(
        task_id="call_api",
        endpoint="/stocks/active",
        method="PATCH",
    )

    with pytest.raises(ValueError, match="不支援的HTTP方法"):
        operator.execute(_context())
