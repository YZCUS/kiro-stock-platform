"""
Top-level technical indicator metadata endpoints.
"""

from datetime import datetime
from typing import Any, Dict

from fastapi import APIRouter, HTTPException

from domain.services.technical_analysis_service import IndicatorType

router = APIRouter(prefix="/indicators", tags=["indicators"])


@router.get("/supported", response_model=Dict[str, Any])
async def get_supported_indicators():
    """Return indicator metadata used by the frontend controls."""
    defaults = {
        "RSI": 14,
        "SMA_5": 5,
        "SMA_20": 20,
        "SMA_60": 60,
        "EMA_12": 12,
        "EMA_26": 26,
        "MACD": 26,
        "BB_MIDDLE": 20,
        "BB_UPPER": 20,
        "BB_LOWER": 20,
        "KD_K": 14,
        "KD_D": 14,
        "ATR": 14,
        "CCI": 20,
        "WILLIAMS_R": 14,
        "VOLUME_SMA": 20,
    }

    return {
        "indicators": [
            {
                "type": indicator.value,
                "name": indicator.value,
                "description": indicator.value.replace("_", " "),
                "default_period": defaults.get(indicator.value, 14),
                "parameters": [
                    {
                        "name": "period",
                        "type": "number",
                        "default": defaults.get(indicator.value, 14),
                        "description": "Calculation period",
                    }
                ],
            }
            for indicator in IndicatorType
        ]
    }


@router.get("/tasks/{task_id}", response_model=Dict[str, Any])
async def get_indicator_task_status(task_id: str):
    """Compatibility status endpoint for synchronous recalculation responses."""
    if not task_id.startswith("sync-"):
        raise HTTPException(status_code=404, detail="指標計算任務不存在")

    now = datetime.now().isoformat()
    return {
        "task_id": task_id,
        "status": "completed",
        "progress": 100,
        "result": None,
        "created_at": now,
        "updated_at": now,
    }
