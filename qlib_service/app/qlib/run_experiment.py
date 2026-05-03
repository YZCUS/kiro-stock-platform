from __future__ import annotations

from dataclasses import asdict, dataclass
import math
from statistics import pstdev


@dataclass(frozen=True)
class QlibModelConfig:
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


def _cpu_config(
    base_name: str,
    label: str,
    model_type: str,
    horizon: str,
    description: str,
    alias_1d: bool = False,
) -> QlibModelConfig:
    name = base_name if alias_1d and horizon == "1d" else f"{base_name}_{horizon}"
    return QlibModelConfig(
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


MODEL_REGISTRY: dict[str, QlibModelConfig] = {
    option.name: option
    for option in [
        *[
            _cpu_config(
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
            _cpu_config(
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
            _cpu_config(
                "catboost_alpha158",
                "CatBoost Alpha158",
                "catboost",
                horizon,
                "偏向穩定上漲天數與下行波動控制的樹模型配置。",
                alias_1d=True,
            )
            for horizon in SUPPORTED_HORIZONS
        ],
        QlibModelConfig(
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
        QlibModelConfig(
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
}


def list_model_configs() -> list[QlibModelConfig]:
    return list(MODEL_REGISTRY.values())


def get_model_config(model_name: str) -> QlibModelConfig:
    try:
        return MODEL_REGISTRY[model_name]
    except KeyError as exc:
        available = ", ".join(sorted(MODEL_REGISTRY))
        raise ValueError(
            f"Unsupported Qlib model '{model_name}'. Available: {available}"
        ) from exc


def score_price_window(
    closes: list[float],
    model_config: QlibModelConfig | None = None,
) -> float:
    """
    Bootstrap scorer used until the Qlib experiment runner is wired in.

    The service contract is intentionally the same as a Qlib inference output:
    higher score means stronger expected forward return. Each registered model
    currently maps to a distinct deterministic scoring profile so product code
    can exercise multiple model paths before pyqlib/qrun is enabled.
    """
    if len(closes) < 6:
        return 0.0

    config = model_config or get_model_config("lightgbm_alpha158")
    horizon_window = _horizon_window(config.horizon)
    short_return = _return_over_window(closes, min(5, horizon_window))
    medium_return = _return_over_window(closes, max(5, min(21, horizon_window)))
    horizon_return = _return_over_window(closes, horizon_window)
    long_return = closes[-1] / closes[0] - 1
    daily_returns = [
        closes[index] / closes[index - 1] - 1
        for index in range(1, len(closes))
        if closes[index - 1] > 0
    ]
    volatility = pstdev(daily_returns) if len(daily_returns) > 1 else 0.0
    positive_ratio = (
        sum(1 for value in daily_returns if value > 0) / len(daily_returns)
        if daily_returns
        else 0.5
    )

    if config.model_type == "lightgbm":
        raw_score = 0.45 * short_return + 0.35 * horizon_return + 0.2 * long_return
        return raw_score / (volatility + 0.01)

    if config.model_type == "xgboost":
        drawdown = _max_drawdown(closes)
        raw_score = 0.35 * short_return + 0.4 * horizon_return + 0.25 * medium_return
        return (raw_score - 0.25 * drawdown) / (volatility + 0.012)

    if config.model_type == "catboost":
        downside_returns = [value for value in daily_returns if value < 0]
        downside_volatility = (
            pstdev(downside_returns) if len(downside_returns) > 1 else volatility
        )
        stability = positive_ratio - 0.5
        raw_score = 0.35 * short_return + 0.35 * horizon_return + 0.3 * stability
        return raw_score / (downside_volatility + 0.015)

    if config.model_type == "mlp":
        raw_score = (
            3.0 * short_return
            + 1.8 * medium_return
            + 0.8 * long_return
            + positive_ratio
            - 0.5
            - 4.0 * volatility
        )
        return math.tanh(raw_score)

    if config.model_type == "lstm":
        weighted_trend = _weighted_recent_return(daily_returns, 30)
        raw_score = 0.65 * weighted_trend + 0.25 * medium_return + 0.1 * long_return
        return raw_score / (volatility + 0.01)

    return (0.7 * short_return + 0.3 * long_return) / (volatility + 0.01)


def _horizon_window(horizon: str) -> int:
    if horizon.endswith("d"):
        try:
            return max(1, int(horizon[:-1]))
        except ValueError:
            return 1
    return 1


def _return_over_window(closes: list[float], window: int) -> float:
    if len(closes) <= window:
        return closes[-1] / closes[0] - 1
    return closes[-1] / closes[-window - 1] - 1


def _max_drawdown(closes: list[float]) -> float:
    peak = closes[0]
    drawdown = 0.0
    for close in closes:
        peak = max(peak, close)
        if peak > 0 and close > 0:
            drawdown = max(drawdown, peak / close - 1)
    return drawdown


def _weighted_recent_return(daily_returns: list[float], window: int) -> float:
    recent_returns = daily_returns[-window:]
    if not recent_returns:
        return 0.0

    weight_total = 0
    weighted_total = 0.0
    for index, value in enumerate(recent_returns, start=1):
        weight_total += index
        weighted_total += value * index
    return weighted_total / weight_total
