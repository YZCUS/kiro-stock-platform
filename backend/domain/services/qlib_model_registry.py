"""
Qlib model options exposed to product surfaces.

This mirrors the prediction service registry so the backend can render stable
UI choices without coupling to the isolated qlib_service package.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class QlibModelOption:
    name: str
    label: str
    model_type: str
    feature_set: str
    horizon: str
    min_lookback_days: int
    description: str
    portfolio_strategy: str
    status: str = "bootstrap"
    config_uri: str | None = None

    def as_dict(self) -> dict:
        return asdict(self)


SUPPORTED_HORIZONS = ("1d", "5d", "20d", "60d")
HORIZON_LOOKBACK_DAYS = {"1d": 60, "5d": 80, "20d": 120, "60d": 180}


def _cpu_option(
    base_name: str,
    label: str,
    model_type: str,
    horizon: str,
    description: str,
    alias_1d: bool = False,
) -> QlibModelOption:
    name = base_name if alias_1d and horizon == "1d" else f"{base_name}_{horizon}"
    return QlibModelOption(
        name=name,
        label=f"{label} {horizon}",
        model_type=model_type,
        feature_set="alpha158",
        horizon=horizon,
        min_lookback_days=HORIZON_LOOKBACK_DAYS[horizon],
        description=description,
        portfolio_strategy="rank_percentile",
        status="cpu_trainable",
        config_uri=f"qlib://configs/{name}.yaml",
    )


MODEL_OPTIONS = [
    *[
        _cpu_option(
            "lightgbm_alpha158",
            "LightGBM Alpha158",
            "lightgbm",
            horizon,
            "多週期 momentum 與波動率調整的樹模型配置。",
            alias_1d=True,
        )
        for horizon in SUPPORTED_HORIZONS
    ],
    *[
        _cpu_option(
            "xgboost_alpha158",
            "XGBoost Alpha158",
            "xgboost",
            horizon,
            "較重視多週期 momentum 與回撤懲罰的樹模型配置。",
            alias_1d=True,
        )
        for horizon in SUPPORTED_HORIZONS
    ],
    *[
        _cpu_option(
            "catboost_alpha158",
            "CatBoost Alpha158",
            "catboost",
            horizon,
            "偏向穩定上漲天數與下行波動控制的樹模型配置。",
            alias_1d=True,
        )
        for horizon in SUPPORTED_HORIZONS
    ],
    QlibModelOption(
        name="mlp_alpha360",
        label="MLP Alpha360 1d",
        model_type="mlp",
        feature_set="alpha360",
        horizon="1d",
        min_lookback_days=120,
        description="使用較長視窗特徵，偏向非線性 momentum/volatility 組合。",
        portfolio_strategy="rank_percentile",
        status="planned_gpu",
        config_uri="qlib://configs/mlp_alpha360.yaml",
    ),
    QlibModelOption(
        name="lstm_alpha360",
        label="LSTM Alpha360 1d",
        model_type="lstm",
        feature_set="alpha360",
        horizon="1d",
        min_lookback_days=180,
        description="偏重近期序列趨勢延續性的長視窗模型配置。",
        portfolio_strategy="rank_percentile",
        status="planned_gpu",
        config_uri="qlib://configs/lstm_alpha360.yaml",
    ),
]


def list_qlib_model_options() -> list[QlibModelOption]:
    return MODEL_OPTIONS
