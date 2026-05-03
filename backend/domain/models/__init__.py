"""
Domain Models - SQLAlchemy實體定義
遷移自models/domain，保持原有結構但提供更清楚的組織
"""

# 重新導出所有模型，保持向後兼容性
from .stock import Stock
from .market_data_bar import MarketDataBar
from .technical_indicator import TechnicalIndicator
from .trading_signal import TradingSignal
from .system_log import SystemLog
from .user import User
from .user_portfolio import UserPortfolio
from .transaction import Transaction
from .user_stock_list import UserStockList, UserStockListItem
from .user_strategy_subscription import UserStrategySubscription
from .user_strategy_stock_list import UserStrategyStockList
from .strategy_signal import StrategySignal
from .strategy_evaluation import (
    StockCompositeScore,
    StrategyBacktestResult,
    StrategyBacktestRun,
    StrategyReliabilityScore,
    StrategyWeight,
    StrategyWeightVersion,
)
from .qlib_prediction import QlibBacktestResult, QlibModelRun, QlibPrediction
from .stock_symbol_mapping import StockSymbolMapping
from .price_alert import PriceAlert
from .broker import (
    BrokerAccount,
    BrokerCashBalance,
    BrokerConnection,
    BrokerContract,
    BrokerPositionSnapshot,
    BrokerSyncRun,
)
from .order_intent import BrokerOrder, OrderEvent, OrderExecution, OrderIntent
from .risk import RiskCheckResult, RiskProfile

__all__ = [
    "Stock",
    "MarketDataBar",
    "TechnicalIndicator",
    "TradingSignal",
    "SystemLog",
    "User",
    "UserPortfolio",
    "Transaction",
    "UserStockList",
    "UserStockListItem",
    "UserStrategySubscription",
    "UserStrategyStockList",
    "StrategySignal",
    "StockCompositeScore",
    "StrategyBacktestResult",
    "StrategyBacktestRun",
    "StrategyReliabilityScore",
    "StrategyWeight",
    "StrategyWeightVersion",
    "QlibBacktestResult",
    "QlibModelRun",
    "QlibPrediction",
    "StockSymbolMapping",
    "PriceAlert",
    "BrokerAccount",
    "BrokerCashBalance",
    "BrokerConnection",
    "BrokerContract",
    "BrokerOrder",
    "BrokerPositionSnapshot",
    "BrokerSyncRun",
    "OrderEvent",
    "OrderExecution",
    "OrderIntent",
    "RiskCheckResult",
    "RiskProfile",
]
