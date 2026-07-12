from pathlib import Path

from airflow.models import DagBag
from airflow.utils.trigger_rule import TriggerRule

DAGS_DIR = Path(__file__).resolve().parents[2] / "dags"
EXPECTED_DAGS = {
    "daily_stock_collection_tw_api",
    "daily_stock_collection_us_api",
    "price_alert_monitoring",
    "qlib_cpu_model_training",
    "qlib_daily_prediction",
    "storage_monitoring",
    "strategy_weekly_evaluation",
}


def _dagbag() -> DagBag:
    return DagBag(dag_folder=str(DAGS_DIR), include_examples=False)


def test_all_production_dags_import_without_errors():
    dagbag = _dagbag()

    assert dagbag.import_errors == {}
    assert set(dagbag.dags) == EXPECTED_DAGS


def test_collection_fallback_runs_after_main_retries_are_exhausted():
    dagbag = _dagbag()

    for dag_id in (
        "daily_stock_collection_tw_api",
        "daily_stock_collection_us_api",
    ):
        dag = dagbag.dags[dag_id]
        branch = dag.get_task("decide_next_step")
        join = dag.get_task("collection_complete")
        assert branch.trigger_rule == TriggerRule.ALL_DONE
        assert join.trigger_rule == TriggerRule.NONE_FAILED_MIN_ONE_SUCCESS
        assert "execute_fallback_collection" in branch.downstream_task_ids


def test_both_collection_dags_validate_canonical_market_data():
    dagbag = _dagbag()

    for dag_id in (
        "daily_stock_collection_tw_api",
        "daily_stock_collection_us_api",
    ):
        dag = dagbag.dags[dag_id]
        pipeline = dag.get_task("run_market_data_pipeline")
        validation = dag.get_task("validate_data_quality")
        assert validation.task_id in pipeline.downstream_task_ids


def test_qlib_prediction_waits_for_validated_us_collection():
    dag = _dagbag().dags["qlib_daily_prediction"]
    sensor = dag.get_task("wait_for_us_collection_validation")

    assert sensor.external_dag_id == "daily_stock_collection_us_api"
    assert sensor.external_task_id == "verify_dependencies"
    assert "build_prediction_payload" in sensor.downstream_task_ids
