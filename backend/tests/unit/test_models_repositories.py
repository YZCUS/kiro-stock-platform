#!/usr/bin/env python3
"""
模型庫 Repository 操作單元測試 - Updated for Clean Architecture
"""
import asyncio
import pytest
import sys
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from datetime import date, datetime, timedelta
from pathlib import Path

# 添加項目根目錄到 Python 路徑
sys.path.append(str(Path(__file__).parent.parent))

from infrastructure.persistence.stock_repository import StockRepository
from infrastructure.persistence.price_history_repository import PriceHistoryRepository
from infrastructure.persistence.technical_indicator_repository import TechnicalIndicatorRepository

# Import domain models for type hints in tests
from models.domain.stock import Stock
from models.domain.price_history import PriceHistory
from models.domain.technical_indicator import TechnicalIndicator


class TestStockRepository:
    """股票 Repository 測試類"""

    def setup_method(self):
        """測試前設置"""
        self.mock_session = AsyncMock()
        self.stock_repo = StockRepository(self.mock_session)

    async def test_get_by_symbol_success(self):
        """測試成功根據代號取得股票"""
        # Mock 股票數據
        mock_stock = Mock()
        mock_stock.symbol = '2330.TW'
        mock_stock.market = 'TW'

        # Mock 資料庫查詢結果
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_stock
        self.mock_session.execute.return_value = mock_result

        # 執行測試
        result = await self.stock_repo.get_by_symbol(
            self.mock_session, symbol='2330.TW', market='TW'
        )

        # 驗證結果
        assert result == mock_stock
        assert result.symbol == '2330.TW'
        assert result.market == 'TW'
        self.mock_session.execute.assert_called_once()

    async def test_get_by_symbol_not_found(self):
        """測試找不到股票"""
        # Mock 空結果
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        self.mock_session.execute.return_value = mock_result

        # 執行測試
        result = await self.stock_repo.get_by_symbol(
            self.mock_session, symbol='9999.TW', market='TW'
        )

        # 驗證結果
        assert result is None

    async def test_get_by_market_success(self):
        """測試成功根據市場取得股票清單"""
        # Mock 股票清單
        mock_stocks = [
            Mock(symbol='2330.TW', market='TW'),
            Mock(symbol='2317.TW', market='TW')
        ]

        # Mock 資料庫查詢結果
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = mock_stocks
        self.mock_session.execute.return_value = mock_result

        # 執行測試
        result = await self.stock_repo.get_by_market(
            self.mock_session, market='TW', skip=0, limit=100
        )

        # 驗證結果
        assert len(result) == 2
        assert all(stock.market == 'TW' for stock in result)

    async def test_search_stocks_by_symbol(self):
        """測試根據代號搜尋股票"""
        # Mock 搜尋結果
        mock_stocks = [
            Mock( symbol='2330.TW', name='台積電'),
            Mock( symbol='2337.TW', name='旺宏')
        ]

        # Mock 資料庫查詢結果
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = mock_stocks
        self.mock_session.execute.return_value = mock_result

        # 執行測試
        result = await self.stock_repo.search_stocks(
            self.mock_session, query='233', limit=20
        )

        # 驗證結果
        assert len(result) == 2
        assert all('233' in stock.symbol for stock in result)

    async def test_search_stocks_by_name(self):
        """測試根據名稱搜尋股票"""
        # Mock 搜尋結果
        mock_stocks = [
            Mock( symbol='2330.TW', name='台積電')
        ]

        # Mock 資料庫查詢結果
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = mock_stocks
        self.mock_session.execute.return_value = mock_result

        # 執行測試
        result = await self.stock_repo.search_stocks(
            self.mock_session, query='台積', limit=20
        )

        # 驗證結果
        assert len(result) == 1
        assert '台積' in result[0].name

    @patch('domain.models.stock.Stock.validate_symbol')
    @patch('domain.models.stock.Stock.normalize_symbol')
    async def test_create_stock_success(self, mock_normalize, mock_validate):
        """測試成功創建股票"""
        # Mock 驗證和標準化
        mock_validate.return_value = True
        mock_normalize.return_value = '2330.TW'

        # Mock 檢查不存在
        self.stock_repo.get_by_symbol = AsyncMock(return_value=None)

        # Mock 創建成功
        mock_created_stock = Mock()
        mock_created_stock.symbol = '2330.TW'
        mock_created_stock.market = 'TW'
        self.stock_repo.create = AsyncMock(return_value=mock_created_stock)

        # 執行測試
        result = await self.stock_repo.create_stock(
            self.mock_session, symbol='2330.tw', market='TW', name='台積電'
        )

        # 驗證結果
        assert result.symbol == '2330.TW'
        assert result.market == 'TW'
        mock_validate.assert_called_once_with('2330.tw', 'TW')
        mock_normalize.assert_called_once_with('2330.tw', 'TW')

    @patch('domain.models.stock.Stock.validate_symbol')
    async def test_create_stock_invalid_symbol(self, mock_validate):
        """測試創建無效代號的股票"""
        # Mock 驗證失敗
        mock_validate.return_value = False

        # 執行測試並期待異常
        with pytest.raises(ValueError, match="無效的股票代號格式"):
            await self.stock_repo.create_stock(
                self.mock_session, symbol='invalid', market='TW'
            )

    @patch('domain.models.stock.Stock.validate_symbol')
    @patch('domain.models.stock.Stock.normalize_symbol')
    async def test_create_stock_already_exists(self, mock_normalize, mock_validate):
        """測試創建已存在的股票"""
        # Mock 驗證和標準化
        mock_validate.return_value = True
        mock_normalize.return_value = '2330.TW'

        # Mock 股票已存在
        existing_stock = Mock()
        self.stock_repo.get_by_symbol = AsyncMock(return_value=existing_stock)

        # 執行測試並期待異常
        with pytest.raises(ValueError, match="股票已存在"):
            await self.stock_repo.create_stock(
                self.mock_session, symbol='2330.TW', market='TW'
            )

    async def test_get_with_latest_price_success(self):
        """測試取得股票及最新價格"""
        # Mock 帶價格的股票數據
        mock_stock = Mock()
        mock_stock.id = 1
        mock_stock.symbol = '2330.TW'
        mock_stock.price_history = [
            Mock(date=date.today(), close_price=100.0)
        ]

        # Mock 資料庫查詢結果
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_stock
        self.mock_session.execute.return_value = mock_result

        # 執行測試
        result = await self.stock_repo.get_with_latest_price(
            self.mock_session, stock_id=1
        )

        # 驗證結果
        assert result == mock_stock
        assert hasattr(result, 'price_history')
        assert len(result.price_history) > 0


class TestPriceHistoryRepository:
    """價格歷史 CRUD 測試類"""

    def setup_method(self):
        """測試前設置"""
        self.mock_session = AsyncMock()
        self.price_repo = PriceHistoryRepository(self.mock_session)

    async def test_get_by_stock_and_date_range_success(self):
        """測試成功取得指定期間的價格數據"""
        # Mock 價格數據
        mock_prices = [
            Mock(
                spec=PriceHistory,
                stock_id=1,
                date=date(2024, 1, 1),
                close_price=100.0
            ),
            Mock(
                spec=PriceHistory,
                stock_id=1,
                date=date(2024, 1, 2),
                close_price=102.0
            )
        ]

        # Mock 資料庫查詢結果
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = mock_prices
        self.mock_session.execute.return_value = mock_result

        # 執行測試
        start_date = date(2024, 1, 1)
        end_date = date(2024, 1, 2)
        result = await self.price_repo.get_by_stock_and_date_range(
            self.mock_session, stock_id=1, start_date=start_date, end_date=end_date
        )

        # 驗證結果
        assert len(result) == 2
        assert all(price.stock_id == 1 for price in result)

    async def test_get_latest_price_success(self):
        """測試成功取得最新價格"""
        # Mock 最新價格
        mock_latest_price = Mock(
            spec=PriceHistory,
            stock_id=1,
            date=date.today(),
            close_price=105.0
        )

        # Mock 資料庫查詢結果
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_latest_price
        self.mock_session.execute.return_value = mock_result

        # 執行測試
        result = await self.price_repo.get_latest_price(self.mock_session, stock_id=1)

        # 驗證結果
        assert result == mock_latest_price
        assert result.close_price == 105.0

    async def test_create_or_update_price_new_record(self):
        """測試創建新的價格記錄"""
        # Mock 價格不存在
        self.price_repo.get_by_stock_and_date = AsyncMock(return_value=None)

        # Mock 創建成功
        mock_created_price = Mock()
        self.price_repo.create = AsyncMock(return_value=mock_created_price)

        # 執行測試
        price_data = {
            'stock_id': 1,
            'date': date.today(),
            'open_price': 100.0,
            'high_price': 105.0,
            'low_price': 98.0,
            'close_price': 103.0,
            'volume': 1000000
        }

        result = await self.price_repo.create_or_update_price(
            self.mock_session, price_data
        )

        # 驗證結果
        assert result == mock_created_price
        self.price_repo.create.assert_called_once()

    async def test_create_or_update_price_existing_record(self):
        """測試更新既有的價格記錄"""
        # Mock 價格已存在
        existing_price = Mock()
        self.price_repo.get_by_stock_and_date = AsyncMock(return_value=existing_price)

        # Mock 更新成功
        mock_updated_price = Mock()
        self.price_repo.update = AsyncMock(return_value=mock_updated_price)

        # 執行測試
        price_data = {
            'stock_id': 1,
            'date': date.today(),
            'close_price': 103.0
        }

        result = await self.price_repo.create_or_update_price(
            self.mock_session, price_data
        )

        # 驗證結果
        assert result == mock_updated_price
        self.price_repo.update.assert_called_once()

    async def test_bulk_create_prices_success(self):
        """測試批次創建價格記錄"""
        # Mock 批次價格數據
        prices_data = [
            {
                'stock_id': 1,
                'date': date(2024, 1, 1),
                'close_price': 100.0
            },
            {
                'stock_id': 1,
                'date': date(2024, 1, 2),
                'close_price': 102.0
            }
        ]

        # Mock 創建成功
        self.price_repo.create_or_update_price = AsyncMock(return_value=Mock())

        # 執行測試
        result = await self.price_repo.bulk_create_prices(
            self.mock_session, prices_data
        )

        # 驗證結果
        assert result['success'] is True
        assert result['created_count'] == 2
        assert result['error_count'] == 0

    async def test_get_missing_dates_success(self):
        """測試找出缺失的交易日期"""
        # Mock 既有日期
        existing_dates = [
            date(2024, 1, 1),
            date(2024, 1, 3)  # 缺少 1/2
        ]

        # Mock 資料庫查詢結果
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = existing_dates
        self.mock_session.execute.return_value = mock_result

        # 執行測試
        start_date = date(2024, 1, 1)
        end_date = date(2024, 1, 3)
        result = await self.price_repo.get_missing_dates(
            self.mock_session, stock_id=1, start_date=start_date, end_date=end_date
        )

        # 驗證結果 - 應該找到缺失的 1/2
        assert date(2024, 1, 2) in result


class TestTechnicalIndicatorRepository:
    """技術指標 Repository 測試類"""

    def setup_method(self):
        """測試前設置"""
        self.mock_session = AsyncMock()
        self.indicator_repo = TechnicalIndicatorRepository(self.mock_session)

    async def test_get_by_stock_and_indicator_type_success(self):
        """測試成功取得股票特定指標"""
        # Mock 指標數據
        mock_indicators = [
            Mock(
                spec=TechnicalIndicator,
                stock_id=1,
                indicator_type='RSI',
                value=65.5,
                date=date.today()
            ),
            Mock(
                spec=TechnicalIndicator,
                stock_id=1,
                indicator_type='RSI',
                value=70.2,
                date=date.today() - timedelta(days=1)
            )
        ]

        # Mock 資料庫查詢結果
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = mock_indicators
        self.mock_session.execute.return_value = mock_result

        # 執行測試
        result = await self.indicator_repo.get_by_stock_and_indicator_type(
            self.mock_session, stock_id=1, indicator_type='RSI'
        )

        # 驗證結果
        assert len(result) == 2
        assert all(indicator.indicator_type == 'RSI' for indicator in result)

    async def test_get_latest_indicator_success(self):
        """測試成功取得最新指標值"""
        # Mock 最新指標
        mock_latest_indicator = Mock(
            spec=TechnicalIndicator,
            stock_id=1,
            indicator_type='RSI',
            value=72.0,
            date=date.today()
        )

        # Mock 資料庫查詢結果
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_latest_indicator
        self.mock_session.execute.return_value = mock_result

        # 執行測試
        result = await self.indicator_repo.get_latest_indicator(
            self.mock_session, stock_id=1, indicator_type='RSI'
        )

        # 驗證結果
        assert result == mock_latest_indicator
        assert result.value == 72.0


class TestRepositoryIntegration:
    """Repository 整合測試類"""

    def setup_method(self):
        """測試前設置"""
        self.mock_session = AsyncMock()
        self.stock_repo = StockRepository(self.mock_session)
        self.price_repo = PriceHistoryRepository(self.mock_session)
        self.indicator_repo = TechnicalIndicatorRepository(self.mock_session)

    async def test_get_by_stock_and_indicator_type_success(self):
        """測試成功取得股票特定指標"""
        # Mock 指標數據
        mock_indicators = [
            Mock(
                spec=TechnicalIndicator,
                stock_id=1,
                indicator_type='RSI',
                value=65.5,
                date=date.today()
            ),
            Mock(
                spec=TechnicalIndicator,
                stock_id=1,
                indicator_type='RSI',
                value=70.2,
                date=date.today() - timedelta(days=1)
            )
        ]

        # Mock 資料庫查詢結果
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = mock_indicators
        self.mock_session.execute.return_value = mock_result

        # 執行測試
        result = await self.indicator_repo.get_by_stock_and_indicator_type(
            self.mock_session, stock_id=1, indicator_type='RSI'
        )

        # 驗證結果
        assert len(result) == 2
        assert all(indicator.indicator_type == 'RSI' for indicator in result)

    async def test_get_latest_indicator_success(self):
        """測試成功取得最新指標值"""
        # Mock 最新指標
        mock_latest_indicator = Mock(
            spec=TechnicalIndicator,
            stock_id=1,
            indicator_type='RSI',
            value=65.5,
            date=date.today()
        )

        # Mock 資料庫查詢結果
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_latest_indicator
        self.mock_session.execute.return_value = mock_result

        # 執行測試
        result = await self.indicator_repo.get_latest_indicator(
            self.mock_session, stock_id=1, indicator_type='RSI'
        )

        # 驗證結果
        assert result == mock_latest_indicator
        assert result.indicator_type == 'RSI'
        assert result.value == 65.5

    async def test_bulk_create_indicators_success(self):
        """測試批次創建指標"""
        # Mock 批次指標數據
        indicators_data = [
            {
                'stock_id': 1,
                'indicator_type': 'RSI',
                'value': 65.5,
                'date': date.today()
            },
            {
                'stock_id': 1,
                'indicator_type': 'SMA_20',
                'value': 100.2,
                'date': date.today()
            }
        ]

        # Mock 創建成功
        self.indicator_repo.create_or_update_indicator = AsyncMock(
            return_value=Mock(spec=TechnicalIndicator)
        )

        # 執行測試
        result = await self.indicator_repo.bulk_create_indicators(
            self.mock_session, indicators_data
        )

        # 驗證結果
        assert result['success'] is True
        assert result['created_count'] == 2
        assert result['error_count'] == 0

    async def test_create_or_update_indicator_new_record(self):
        """測試創建新的指標記錄"""
        # Mock 指標不存在
        self.indicator_repo.get_by_stock_date_and_type = AsyncMock(return_value=None)

        # Mock 創建成功
        mock_created_indicator = Mock(spec=TechnicalIndicator)
        self.indicator_repo.create = AsyncMock(return_value=mock_created_indicator)

        # 執行測試
        indicator_data = {
            'stock_id': 1,
            'indicator_type': 'RSI',
            'value': 65.5,
            'date': date.today()
        }

        result = await self.indicator_repo.create_or_update_indicator(
            self.mock_session, indicator_data
        )

        # 驗證結果
        assert result == mock_created_indicator
        self.indicator_repo.create.assert_called_once()

    async def test_get_stock_indicators_by_date_range_success(self):
        """測試取得指定期間的股票指標"""
        # Mock 指標數據
        mock_indicators = [
            Mock(
                spec=TechnicalIndicator,
                stock_id=1,
                indicator_type='RSI',
                value=65.5,
                date=date(2024, 1, 1)
            ),
            Mock(
                spec=TechnicalIndicator,
                stock_id=1,
                indicator_type='SMA_20',
                value=100.2,
                date=date(2024, 1, 1)
            )
        ]

        # Mock 資料庫查詢結果
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = mock_indicators
        self.mock_session.execute.return_value = mock_result

        # 執行測試
        start_date = date(2024, 1, 1)
        end_date = date(2024, 1, 31)
        result = await self.indicator_repo.get_stock_indicators_by_date_range(
            self.mock_session,
            stock_id=1,
            start_date=start_date,
            end_date=end_date,
            indicator_types=['RSI', 'SMA_20']
        )

        # 驗證結果
        assert len(result) == 2
        assert all(indicator.stock_id == 1 for indicator in result)


async def run_all_tests():
    """執行所有測試"""
    print("開始執行模型庫 CRUD 測試...")

    # 測試股票 CRUD
    print("\n=== 測試股票 CRUD ===")
    test_stock_crud = TestStockRepository()

    try:
        test_stock_crud.setup_method()

        await test_stock_crud.test_get_by_symbol_success()
        print("✅ 根據代號取得股票測試 - 通過")

        await test_stock_crud.test_get_by_symbol_not_found()
        print("✅ 找不到股票測試 - 通過")

        await test_stock_crud.test_get_by_market_success()
        print("✅ 根據市場取得股票清單測試 - 通過")

        await test_stock_crud.test_search_stocks_by_symbol()
        print("✅ 根據代號搜尋股票測試 - 通過")

        await test_stock_crud.test_search_stocks_by_name()
        print("✅ 根據名稱搜尋股票測試 - 通過")

        await test_stock_crud.test_create_stock_success()
        print("✅ 成功創建股票測試 - 通過")

        await test_stock_crud.test_create_stock_invalid_symbol()
        print("✅ 創建無效代號股票測試 - 通過")

        await test_stock_crud.test_create_stock_already_exists()
        print("✅ 創建已存在股票測試 - 通過")

        await test_stock_crud.test_get_with_latest_price_success()
        print("✅ 取得股票及最新價格測試 - 通過")

    except Exception as e:
        print(f"❌ 股票 CRUD 測試失敗: {str(e)}")
        return False

    # 測試價格歷史 CRUD
    print("\n=== 測試價格歷史 CRUD ===")
    test_price_crud = TestPriceHistoryRepository()

    try:
        test_price_crud.setup_method()

        await test_price_crud.test_get_by_stock_and_date_range_success()
        print("✅ 取得指定期間價格數據測試 - 通過")

        await test_price_crud.test_get_latest_price_success()
        print("✅ 取得最新價格測試 - 通過")

        await test_price_crud.test_create_or_update_price_new_record()
        print("✅ 創建新價格記錄測試 - 通過")

        await test_price_crud.test_create_or_update_price_existing_record()
        print("✅ 更新既有價格記錄測試 - 通過")

        await test_price_crud.test_bulk_create_prices_success()
        print("✅ 批次創建價格記錄測試 - 通過")

        await test_price_crud.test_get_missing_dates_success()
        print("✅ 找出缺失交易日期測試 - 通過")

    except Exception as e:
        print(f"❌ 價格歷史 CRUD 測試失敗: {str(e)}")
        return False

    # 測試技術指標 CRUD
    print("\n=== 測試技術指標 CRUD ===")
    test_indicator_crud = TestTechnicalIndicatorRepository()

    try:
        test_indicator_crud.setup_method()

        await test_indicator_crud.test_get_by_stock_and_indicator_type_success()
        print("✅ 取得股票特定指標測試 - 通過")

        await test_indicator_crud.test_get_latest_indicator_success()
        print("✅ 取得最新指標值測試 - 通過")

        await test_indicator_crud.test_bulk_create_indicators_success()
        print("✅ 批次創建指標測試 - 通過")

        await test_indicator_crud.test_create_or_update_indicator_new_record()
        print("✅ 創建新指標記錄測試 - 通過")

        await test_indicator_crud.test_get_stock_indicators_by_date_range_success()
        print("✅ 取得指定期間股票指標測試 - 通過")

    except Exception as e:
        print(f"❌ 技術指標 CRUD 測試失敗: {str(e)}")
        return False

    print("\n🎉 所有模型庫 CRUD 測試通過！")
    return True


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    exit(0 if success else 1)