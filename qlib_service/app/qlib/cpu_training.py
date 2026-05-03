from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import json
import pickle
from pathlib import Path
from typing import Any

import numpy as np

from app.qlib.features import (
    FEATURE_COLUMNS,
    build_feature_vector,
    close_value,
    row_date,
)
from app.qlib.run_experiment import QlibModelConfig


@dataclass(frozen=True)
class DatasetSplit:
    features: np.ndarray
    targets: np.ndarray


@dataclass(frozen=True)
class TrainingDataset:
    train: DatasetSplit
    valid: DatasetSplit
    test: DatasetSplit
    sample_counts: dict[str, int]


@dataclass(frozen=True)
class ModelArtifact:
    run_id: str
    model_name: str
    model_type: str
    feature_set: str
    horizon: str
    feature_columns: list[str]
    model: Any
    metadata: dict[str, Any]


def build_training_dataset(
    rows_by_stock: dict[int, list[dict[str, Any]]],
    *,
    horizon_days: int,
    train_start: date,
    train_end: date,
    valid_start: date,
    valid_end: date,
    test_start: date,
    test_end: date,
    lookback_days: int,
) -> TrainingDataset:
    split_features: dict[str, list[list[float]]] = {
        "train": [],
        "valid": [],
        "test": [],
    }
    split_targets: dict[str, list[float]] = {
        "train": [],
        "valid": [],
        "test": [],
    }

    for rows in rows_by_stock.values():
        if len(rows) <= lookback_days:
            continue

        for index in range(lookback_days - 1, len(rows) - horizon_days):
            current_date = row_date(rows[index])
            split_name = _split_for_date(
                current_date,
                train_start=train_start,
                train_end=train_end,
                valid_start=valid_start,
                valid_end=valid_end,
                test_start=test_start,
                test_end=test_end,
            )
            if split_name is None:
                continue

            current_close = close_value(rows[index])
            if current_close <= 0:
                continue

            future_close = close_value(rows[index + horizon_days])
            split_features[split_name].append(build_feature_vector(rows, index))
            split_targets[split_name].append(future_close / current_close - 1)

    dataset = TrainingDataset(
        train=_to_dataset_split(split_features["train"], split_targets["train"]),
        valid=_to_dataset_split(split_features["valid"], split_targets["valid"]),
        test=_to_dataset_split(split_features["test"], split_targets["test"]),
        sample_counts={
            split_name: len(features)
            for split_name, features in split_features.items()
        },
    )
    if dataset.sample_counts["train"] == 0:
        raise ValueError("No training samples were produced")
    if dataset.sample_counts["valid"] == 0:
        raise ValueError("No validation samples were produced")
    if dataset.sample_counts["test"] == 0:
        raise ValueError("No test samples were produced")
    return dataset


def train_cpu_model(
    *,
    run_id: str,
    model_config: QlibModelConfig,
    dataset: TrainingDataset,
    artifact_dir: Path,
    metadata: dict[str, Any],
) -> tuple[str, dict[str, Any]]:
    model = _create_model(model_config)
    model.fit(dataset.train.features, dataset.train.targets)

    valid_predictions = model.predict(dataset.valid.features)
    test_predictions = model.predict(dataset.test.features)
    metrics = {
        "engine": "cpu_model_artifact",
        "model_type": model_config.model_type,
        "model_status": model_config.status,
        "feature_set": model_config.feature_set,
        "horizon": model_config.horizon,
        "feature_columns": FEATURE_COLUMNS,
        "sample_counts": dataset.sample_counts,
        "valid": _regression_metrics(dataset.valid.targets, valid_predictions),
        "test": _regression_metrics(dataset.test.targets, test_predictions),
    }

    artifact_dir.mkdir(parents=True, exist_ok=True)
    artifact_path = artifact_dir / "model.pkl"
    metadata_path = artifact_dir / "metadata.json"
    artifact = ModelArtifact(
        run_id=run_id,
        model_name=model_config.name,
        model_type=model_config.model_type,
        feature_set=model_config.feature_set,
        horizon=model_config.horizon,
        feature_columns=FEATURE_COLUMNS,
        model=model,
        metadata={**metadata, "metrics": metrics},
    )
    with artifact_path.open("wb") as file:
        pickle.dump(artifact, file)
    metadata_path.write_text(
        json.dumps(artifact.metadata, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return str(artifact_path), {**metrics, "metadata_uri": str(metadata_path)}


def load_model_artifact(artifact_uri: str) -> ModelArtifact:
    artifact_path = Path(artifact_uri)
    with artifact_path.open("rb") as file:
        artifact = pickle.load(file)
    if not isinstance(artifact, ModelArtifact):
        raise ValueError(f"Invalid model artifact at {artifact_uri}")
    return artifact


def predict_with_artifact(
    rows: list[dict[str, Any]],
    artifact: ModelArtifact,
) -> float:
    feature_vector = build_feature_vector(rows, len(rows) - 1)
    prediction = artifact.model.predict(np.asarray([feature_vector], dtype=float))
    return float(prediction[0])


def _create_model(model_config: QlibModelConfig):
    if model_config.model_type == "lightgbm":
        try:
            from lightgbm import LGBMRegressor
        except ImportError as exc:
            raise RuntimeError("lightgbm is not installed in qlib_service") from exc

        return LGBMRegressor(
            n_estimators=250,
            learning_rate=0.05,
            num_leaves=31,
            subsample=0.9,
            colsample_bytree=0.9,
            objective="regression",
            random_state=42,
            n_jobs=-1,
            verbose=-1,
        )

    if model_config.model_type == "xgboost":
        try:
            from xgboost import XGBRegressor
        except ImportError as exc:
            raise RuntimeError("xgboost is not installed in qlib_service") from exc

        return XGBRegressor(
            n_estimators=250,
            max_depth=4,
            learning_rate=0.05,
            subsample=0.9,
            colsample_bytree=0.9,
            objective="reg:squarederror",
            tree_method="hist",
            random_state=42,
            n_jobs=-1,
        )

    if model_config.model_type == "catboost":
        try:
            from catboost import CatBoostRegressor
        except ImportError as exc:
            raise RuntimeError("catboost is not installed in qlib_service") from exc

        return CatBoostRegressor(
            iterations=250,
            depth=6,
            learning_rate=0.05,
            loss_function="RMSE",
            random_seed=42,
            thread_count=-1,
            verbose=False,
        )

    raise ValueError(f"Model {model_config.name} is not CPU trainable")


def _split_for_date(
    current_date: date,
    *,
    train_start: date,
    train_end: date,
    valid_start: date,
    valid_end: date,
    test_start: date,
    test_end: date,
) -> str | None:
    if train_start <= current_date <= train_end:
        return "train"
    if valid_start <= current_date <= valid_end:
        return "valid"
    if test_start <= current_date <= test_end:
        return "test"
    return None


def _to_dataset_split(
    features: list[list[float]],
    targets: list[float],
) -> DatasetSplit:
    return DatasetSplit(
        features=np.asarray(features, dtype=float),
        targets=np.asarray(targets, dtype=float),
    )


def _regression_metrics(
    targets: np.ndarray,
    predictions: np.ndarray,
) -> dict[str, float]:
    errors = predictions - targets
    mae = float(np.mean(np.abs(errors)))
    rmse = float(np.sqrt(np.mean(errors * errors)))
    ic = _information_coefficient(targets, predictions)
    return {
        "mae": mae,
        "rmse": rmse,
        "ic": ic,
    }


def _information_coefficient(targets: np.ndarray, predictions: np.ndarray) -> float:
    if len(targets) < 2:
        return 0.0
    target_std = float(np.std(targets))
    prediction_std = float(np.std(predictions))
    if target_std == 0 or prediction_std == 0:
        return 0.0
    ic = float(np.corrcoef(targets, predictions)[0, 1])
    return ic if np.isfinite(ic) else 0.0
