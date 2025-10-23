"""
策略系統 - Domain Layer

提供可擴展的交易策略架構
"""
from domain.strategies.strategy_interface import (
    IStrategyEngine,
    TradingSignal,
    SignalDirection,
    StrategyType
)
from domain.strategies.strategy_registry import strategy_registry, StrategyRegistry
from domain.strategies.golden_cross_strategy import GoldenCrossStrategy

# 自動註冊所有策略
def register_all_strategies():
    """註冊所有策略到registry"""
    strategy_registry.register(GoldenCrossStrategy())

# 在模組載入時自動註冊
register_all_strategies()

__all__ = [
    'IStrategyEngine',
    'TradingSignal',
    'SignalDirection',
    'StrategyType',
    'StrategyRegistry',
    'strategy_registry',
    'GoldenCrossStrategy',
    'register_all_strategies'
]
