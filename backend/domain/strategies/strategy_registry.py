"""
策略註冊器 - Strategy Registry

使用單例模式管理所有已註冊的策略引擎。
提供策略的註冊、查詢和資訊獲取功能。

使用方式：
    from domain.strategies.strategy_registry import strategy_registry
    from domain.strategies.my_strategy import MyStrategy

    # 註冊策略
    strategy_registry.register(MyStrategy())

    # 獲取策略
    strategy = strategy_registry.get_strategy(StrategyType.GOLDEN_CROSS)

    # 獲取所有策略資訊
    strategies_info = strategy_registry.get_strategies_info()
"""
import logging
from typing import Dict, List, Optional
from domain.strategies.strategy_interface import IStrategyEngine, StrategyType

logger = logging.getLogger(__name__)


class StrategyRegistry:
    """
    策略註冊器 - 單例模式

    管理系統中所有可用的交易策略引擎。
    確保每種策略類型只註冊一次，避免衝突。

    Attributes:
        _instance: 單例實例
        _strategies: 策略字典 {StrategyType: IStrategyEngine}
    """

    _instance: Optional['StrategyRegistry'] = None
    _strategies: Dict[StrategyType, IStrategyEngine] = {}

    def __new__(cls) -> 'StrategyRegistry':
        """
        實作單例模式

        確保整個應用只有一個註冊器實例
        """
        if cls._instance is None:
            cls._instance = super(StrategyRegistry, cls).__new__(cls)
            cls._instance._strategies = {}
            logger.info("StrategyRegistry singleton instance created")
        return cls._instance

    def register(self, strategy: IStrategyEngine) -> None:
        """
        註冊策略到註冊器

        Args:
            strategy: 策略引擎實例

        Raises:
            ValueError: 如果策略類型已被註冊

        Example:
            >>> registry = StrategyRegistry()
            >>> registry.register(GoldenCrossStrategy())
        """
        strategy_type = strategy.strategy_type

        if strategy_type in self._strategies:
            existing_strategy = self._strategies[strategy_type]
            logger.warning(
                f"Strategy type {strategy_type} is already registered "
                f"with {existing_strategy.__class__.__name__}. "
                f"Replacing with {strategy.__class__.__name__}"
            )

        self._strategies[strategy_type] = strategy
        logger.info(
            f"Registered strategy: {strategy.name} "
            f"(type={strategy_type}, class={strategy.__class__.__name__})"
        )

    def unregister(self, strategy_type: StrategyType) -> bool:
        """
        取消註冊策略

        Args:
            strategy_type: 要移除的策略類型

        Returns:
            bool: 是否成功移除（False 表示策略不存在）

        Example:
            >>> registry.unregister(StrategyType.GOLDEN_CROSS)
            True
        """
        if strategy_type in self._strategies:
            strategy = self._strategies.pop(strategy_type)
            logger.info(f"Unregistered strategy: {strategy.name} (type={strategy_type})")
            return True
        else:
            logger.warning(f"Strategy type {strategy_type} not found in registry")
            return False

    def get_strategy(self, strategy_type: StrategyType) -> Optional[IStrategyEngine]:
        """
        獲取已註冊的策略

        Args:
            strategy_type: 策略類型

        Returns:
            IStrategyEngine: 策略引擎實例，如果不存在返回 None

        Example:
            >>> strategy = registry.get_strategy(StrategyType.GOLDEN_CROSS)
            >>> if strategy:
            >>>     signal = await strategy.analyze(stock_id, db)
        """
        strategy = self._strategies.get(strategy_type)

        if strategy is None:
            logger.warning(f"Strategy type {strategy_type} not found in registry")

        return strategy

    def get_all_strategies(self) -> List[IStrategyEngine]:
        """
        獲取所有已註冊的策略

        Returns:
            List[IStrategyEngine]: 所有策略引擎實例列表

        Example:
            >>> strategies = registry.get_all_strategies()
            >>> for strategy in strategies:
            >>>     print(f"- {strategy.name}")
        """
        return list(self._strategies.values())

    def get_strategies_info(self) -> List[Dict]:
        """
        獲取所有策略的資訊（用於 API 響應）

        返回策略的基本資訊，包括類型、名稱、描述和預設參數。

        Returns:
            List[Dict]: 策略資訊列表，每個元素包含：
                - type: 策略類型
                - name: 策略名稱
                - description: 策略描述
                - default_params: 預設參數

        Example:
            >>> info = registry.get_strategies_info()
            >>> # [
            >>> #     {
            >>> #         "type": "golden_cross",
            >>> #         "name": "黃金交叉策略",
            >>> #         "description": "...",
            >>> #         "default_params": {"short_period": 5, "long_period": 20}
            >>> #     }
            >>> # ]
        """
        return [
            {
                "type": strategy.strategy_type.value,
                "name": strategy.name,
                "description": strategy.description,
                "default_params": strategy.get_default_params()
            }
            for strategy in self._strategies.values()
        ]

    def is_registered(self, strategy_type: StrategyType) -> bool:
        """
        檢查策略類型是否已註冊

        Args:
            strategy_type: 要檢查的策略類型

        Returns:
            bool: 是否已註冊
        """
        return strategy_type in self._strategies

    def get_registered_count(self) -> int:
        """
        獲取已註冊策略的數量

        Returns:
            int: 策略數量
        """
        return len(self._strategies)

    def clear(self) -> None:
        """
        清空所有已註冊的策略

        注意：此方法主要用於測試，生產環境慎用
        """
        count = len(self._strategies)
        self._strategies.clear()
        logger.warning(f"Cleared all strategies from registry (removed {count} strategies)")


# 全局單例實例
# 應用啟動時使用此實例註冊所有策略
strategy_registry = StrategyRegistry()
