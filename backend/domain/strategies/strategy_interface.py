"""
策略抽象介面 - Strategy Interface

定義統一的策略介面規範，所有交易策略都必須實作此介面。
這確保了策略的可插拔性和擴展性。
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Tuple
from datetime import date
from enum import Enum
from dataclasses import dataclass, field
from sqlalchemy.ext.asyncio import AsyncSession


class SignalDirection(str, Enum):
    """
    信號方向枚舉

    定義交易信號的方向類型
    """

    LONG = "LONG"  # 做多（看漲）- 建議買入
    SHORT = "SHORT"  # 做空（看跌）- 建議賣出或放空
    NEUTRAL = "NEUTRAL"  # 中性 - 觀望或持有


class StrategyType(str, Enum):
    """
    策略類型枚舉

    定義系統支援的所有策略類型
    新增策略時需要在此添加新的類型
    """

    GOLDEN_CROSS = "golden_cross"  # 黃金交叉策略
    DEATH_CROSS = "death_cross"  # 死亡交叉策略
    RSI_REVERSAL = "rsi_reversal"  # RSI 反轉策略
    MACD_DIVERGENCE = "macd_divergence"  # MACD 背離策略
    BOLLINGER_BREAKOUT = "bollinger_breakout"  # 布林帶突破策略
    VOLUME_SPIKE = "volume_spike"  # 成交量異常策略
    PATTERN_RECOGNITION = "pattern_recognition"  # 型態辨識策略
    ML_PREDICTION = "ml_prediction"  # 機器學習預測策略


@dataclass
class TradingSignal:
    """
    標準化交易信號數據結構

    所有策略產生的信號都使用此統一格式，確保：
    1. 信號資訊完整且一致
    2. 方便前端展示
    3. 可追蹤和回測

    Attributes:
        stock_id: 股票資料庫 ID
        stock_symbol: 股票代號（如 AAPL, 2330.TW）
        strategy_type: 產生此信號的策略類型
        direction: 交易方向（LONG/SHORT/NEUTRAL）
        confidence: 信心度/機率 (0-100)，數值越高表示信號越強
        entry_zone: 建議進場區間 (最低價, 最高價)
        stop_loss: 停損價位
        take_profit: 止盈目標價位列表（可設定多個目標）
        signal_date: 信號產生日期
        valid_until: 信號有效期限（過期後自動失效）
        reason: 信號產生原因說明（給用戶看）
        extra_data: 額外元數據（策略特有的數據，如技術指標值）
    """

    stock_id: int
    stock_symbol: str
    strategy_type: StrategyType
    direction: SignalDirection
    confidence: float  # 0-100
    entry_zone: Tuple[float, float]  # (min_price, max_price)
    stop_loss: float
    take_profit: List[float]  # 可設定多個止盈目標
    signal_date: date
    valid_until: Optional[date] = None
    reason: str = ""
    extra_data: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """驗證數據完整性"""
        if not 0 <= self.confidence <= 100:
            raise ValueError(f"Confidence must be between 0-100, got {self.confidence}")

        if self.entry_zone[0] > self.entry_zone[1]:
            raise ValueError(f"Entry zone min must be <= max: {self.entry_zone}")

        if self.stop_loss < 0:
            raise ValueError(f"Stop loss must be positive, got {self.stop_loss}")

        if any(tp < 0 for tp in self.take_profit):
            raise ValueError("Take profit targets must be positive")


class IStrategyEngine(ABC):
    """
    策略引擎抽象介面

    所有交易策略都必須繼承此介面並實作所有抽象方法。
    這確保了策略的一致性和可互換性。

    實作步驟：
    1. 繼承此類
    2. 實作所有 @abstractmethod 方法
    3. 註冊到 StrategyRegistry

    範例：
        class MyStrategy(IStrategyEngine):
            @property
            def strategy_type(self) -> StrategyType:
                return StrategyType.GOLDEN_CROSS

            async def analyze(self, stock_id: int, db: AsyncSession, params: Dict = None):
                # 實作策略邏輯
                pass
    """

    @property
    @abstractmethod
    def strategy_type(self) -> StrategyType:
        """
        策略類型標識

        Returns:
            StrategyType: 策略的唯一識別類型
        """
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """
        策略顯示名稱

        Returns:
            str: 用於 UI 顯示的策略名稱（中文）
        """
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """
        策略說明

        Returns:
            str: 策略的詳細說明，包括：
                - 策略原理
                - 適用場景
                - 注意事項
        """
        pass

    @abstractmethod
    async def analyze(
        self, stock_id: int, db: AsyncSession, params: Optional[Dict[str, Any]] = None
    ) -> Optional[TradingSignal]:
        """
        分析單一股票並產生交易信號

        這是策略的核心方法，實作策略的分析邏輯。

        Args:
            stock_id: 要分析的股票 ID
            db: 資料庫 session
            params: 策略參數（可覆蓋預設參數）

        Returns:
            TradingSignal: 如果檢測到信號，返回信號物件
            None: 如果沒有檢測到信號

        實作要點：
        1. 獲取必要的技術指標數據
        2. 執行策略邏輯判斷
        3. 計算信心度
        4. 計算進場區間、停損、止盈
        5. 返回 TradingSignal 或 None
        """
        pass

    @abstractmethod
    async def batch_analyze(
        self,
        stock_ids: List[int],
        db: AsyncSession,
        params: Optional[Dict[str, Any]] = None,
    ) -> List[TradingSignal]:
        """
        批量分析多支股票

        效能優化方法：可批量獲取數據，避免多次查詢。

        Args:
            stock_ids: 要分析的股票 ID 列表
            db: 資料庫 session
            params: 策略參數

        Returns:
            List[TradingSignal]: 檢測到的所有信號列表

        預設實作：
        可以簡單地循環調用 analyze()，但建議優化為批量處理。
        """
        pass

    def get_default_params(self) -> Dict[str, Any]:
        """
        獲取策略的預設參數

        Returns:
            Dict[str, Any]: 預設參數字典

        範例：
            return {
                "short_period": 5,
                "long_period": 20,
                "volume_threshold": 1.5
            }
        """
        return {}

    def validate_params(self, params: Dict[str, Any]) -> bool:
        """
        驗證策略參數的有效性

        Args:
            params: 要驗證的參數

        Returns:
            bool: 參數是否有效

        可選實作：子類可以覆蓋此方法以添加自定義驗證邏輯
        """
        return True
