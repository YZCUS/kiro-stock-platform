#!/usr/bin/env python3
"""
數據驗證服務單元測試
"""
import asyncio
import pytest
import sys
from unittest.mock import Mock, patch, AsyncMock
from datetime import date, datetime, timedelta
from decimal import Decimal

# 添加項目根目錄到 Python 路徑
sys.path.append('/Users/zhengchy/Documents/projects/kiro-stock-platform/backend')

from services.data.validation import (
    PriceDataValidator,
    DataQualityAnalyzer,
    DataCleaningService,
    ValidationLevel,
    ValidationResult,
    DataQualityReport
)


class TestPriceDataValidator:
    """價格數據驗證器測試類"""

    def setup_method(self):
        """測試前設置"""
        self.validator = PriceDataValidator(ValidationLevel.STANDARD)
        self.valid_price_data = {
            'date': date.today(),
            'open_price': 100.0,
            'high_price': 105.0,
            'low_price': 98.0,
            'close_price': 103.0,
            'volume': 1000000
        }

    def test_validate_valid_price_record(self):
        """測試驗證有效的價格記錄"""
        result = self.validator.validate_price_record(self.valid_price_data)

        assert isinstance(result, ValidationResult)
        assert result.is_valid is True
        assert len(result.errors) == 0

    def test_validate_missing_required_fields(self):
        """測試缺少必要欄位"""
        invalid_data = {
            'open_price': 100.0,
            'high_price': 105.0,
            'low_price': 98.0,
            # 缺少 close_price 和 date
        }

        result = self.validator.validate_price_record(invalid_data)

        assert result.is_valid is False
        assert len(result.errors) > 0
        assert any("缺少必要的價格數據欄位" in error for error in result.errors)

    def test_validate_negative_prices(self):
        """測試負數價格"""
        invalid_data = self.valid_price_data.copy()
        invalid_data['close_price'] = -50.0

        result = self.validator.validate_price_record(invalid_data)

        assert result.is_valid is False
        assert any("價格不能為負數或零" in error for error in result.errors)

    def test_validate_high_low_price_logic(self):
        """測試高低價邏輯"""
        invalid_data = self.valid_price_data.copy()
        invalid_data['high_price'] = 95.0  # 最高價低於最低價
        invalid_data['low_price'] = 98.0

        result = self.validator.validate_price_record(invalid_data)

        assert result.is_valid is False
        assert any("最高價" in error and "不能低於最低價" in error for error in result.errors)

    def test_validate_open_close_price_range(self):
        """測試開收盤價範圍"""
        invalid_data = self.valid_price_data.copy()
        invalid_data['open_price'] = 110.0  # 開盤價高於最高價
        invalid_data['high_price'] = 105.0

        result = self.validator.validate_price_record(invalid_data)

        assert result.is_valid is False
        assert any("開盤價" in error and "不能高於最高價" in error for error in result.errors)

    def test_validate_negative_volume(self):
        """測試負成交量"""
        invalid_data = self.valid_price_data.copy()
        invalid_data['volume'] = -1000

        result = self.validator.validate_price_record(invalid_data)

        assert result.is_valid is False
        assert any("成交量不能為負數" in error for error in result.errors)

    def test_validate_zero_volume_warning(self):
        """測試零成交量警告"""
        data_with_zero_volume = self.valid_price_data.copy()
        data_with_zero_volume['volume'] = 0

        result = self.validator.validate_price_record(data_with_zero_volume)

        assert result.is_valid is True  # 零成交量是警告，不是錯誤
        assert any("成交量為零" in warning for warning in result.warnings)

    def test_validate_future_date(self):
        """測試未來日期"""
        invalid_data = self.valid_price_data.copy()
        invalid_data['date'] = date.today() + timedelta(days=1)

        result = self.validator.validate_price_record(invalid_data)

        assert result.is_valid is False
        assert any("不能是未來日期" in error for error in result.errors)

    def test_validate_weekend_date_warning(self):
        """測試週末日期警告"""
        # 找到下個週六
        today = date.today()
        days_ahead = 5 - today.weekday()  # 週六是 5
        if days_ahead <= 0:
            days_ahead += 7
        next_saturday = today + timedelta(days=days_ahead)

        weekend_data = self.valid_price_data.copy()
        weekend_data['date'] = next_saturday

        result = self.validator.validate_price_record(weekend_data)

        assert any("為週末" in warning for warning in result.warnings)

    def test_validate_excessive_price_volatility(self):
        """測試過度價格波動"""
        volatile_data = self.valid_price_data.copy()
        volatile_data['low_price'] = 50.0   # 50
        volatile_data['high_price'] = 150.0  # 150, 波動200%
        volatile_data['open_price'] = 60.0
        volatile_data['close_price'] = 140.0

        result = self.validator.validate_price_record(volatile_data)

        # 標準驗證模式下，過度波動是警告
        assert any("單日價格波動過大" in warning for warning in result.warnings)

    def test_validation_levels(self):
        """測試不同驗證等級"""
        volatile_data = self.valid_price_data.copy()
        volatile_data['low_price'] = 80.0
        volatile_data['high_price'] = 120.0  # 50% 波動

        # 基本驗證
        basic_validator = PriceDataValidator(ValidationLevel.BASIC)
        basic_result = basic_validator.validate_price_record(volatile_data)
        assert basic_result.is_valid is True

        # 嚴格驗證
        strict_validator = PriceDataValidator(ValidationLevel.STRICT)
        strict_result = strict_validator.validate_price_record(volatile_data)
        # 嚴格模式下，過度波動是錯誤
        assert any("單日價格波動過大" in error for error in strict_result.errors)

    def test_invalid_date_format(self):
        """測試無效日期格式"""
        invalid_data = self.valid_price_data.copy()
        invalid_data['date'] = "invalid-date"

        result = self.validator.validate_price_record(invalid_data)

        assert result.is_valid is False
        assert any("無效的日期格式" in error for error in result.errors)


class TestDataQualityAnalyzer:
    """數據品質分析器測試類"""

    def setup_method(self):
        """測試前設置"""
        self.analyzer = DataQualityAnalyzer()

    @patch('services.data.validation.stock_crud')
    @patch('services.data.validation.price_history_crud')
    async def test_analyze_stock_data_quality_success(self, mock_price_crud, mock_stock_crud):
        """測試成功分析股票數據品質"""
        # Mock 股票數據
        mock_stock = Mock()
        mock_stock.symbol = "2330.TW"
        mock_stock.market = "TW"
        mock_stock_crud.get = AsyncMock(return_value=mock_stock)

        # Mock 價格數據
        mock_price_data = [
            Mock(
                date=date.today() - timedelta(days=1),
                open_price=Decimal('100.0'),
                high_price=Decimal('105.0'),
                low_price=Decimal('98.0'),
                close_price=Decimal('103.0'),
                volume=1000000,
                get_ohlc_data=lambda: {'open': 100.0, 'high': 105.0, 'low': 98.0, 'close': 103.0}
            ),
            Mock(
                date=date.today(),
                open_price=Decimal('103.0'),
                high_price=Decimal('108.0'),
                low_price=Decimal('101.0'),
                close_price=Decimal('106.0'),
                volume=1200000,
                get_ohlc_data=lambda: {'open': 103.0, 'high': 108.0, 'low': 101.0, 'close': 106.0}
            )
        ]
        mock_price_crud.get_stock_price_range = AsyncMock(return_value=mock_price_data)
        mock_price_crud.get_missing_dates = AsyncMock(return_value=[])

        # 執行測試
        db_session = Mock()
        report = await self.analyzer.analyze_stock_data_quality(db_session, stock_id=1, days=30)

        # 驗證結果
        assert isinstance(report, DataQualityReport)
        assert report.stock_symbol == "2330.TW"
        assert report.stock_market == "TW"
        assert report.total_records == 2
        assert report.valid_records == 2
        assert report.invalid_records == 0
        assert report.quality_score > 90  # 高品質分數

    @patch('services.data.validation.stock_crud')
    async def test_analyze_stock_not_found(self, mock_stock_crud):
        """測試分析不存在的股票"""
        mock_stock_crud.get = AsyncMock(return_value=None)

        db_session = Mock()

        with pytest.raises(ValueError, match="找不到股票 ID"):
            await self.analyzer.analyze_stock_data_quality(db_session, stock_id=999)

    def test_find_duplicate_dates(self):
        """測試找出重複日期"""
        price_data = [
            Mock(date=date(2024, 1, 1)),
            Mock(date=date(2024, 1, 2)),
            Mock(date=date(2024, 1, 1)),  # 重複
            Mock(date=date(2024, 1, 3)),
        ]

        duplicates = self.analyzer._find_duplicate_dates(price_data)

        assert len(duplicates) == 1
        assert date(2024, 1, 1) in duplicates

    def test_find_data_gaps(self):
        """測試找出數據間隙"""
        start_date = date(2024, 1, 1)
        end_date = date(2024, 1, 31)

        price_data = [
            Mock(date=date(2024, 1, 5)),   # 開始後5天
            Mock(date=date(2024, 1, 20)),  # 中間有15天間隙
        ]

        gaps = self.analyzer._find_data_gaps(price_data, start_date, end_date)

        assert len(gaps) >= 2  # 至少有開始和結束的間隙

    def test_calculate_quality_score(self):
        """測試計算品質分數"""
        # 完美數據
        score1 = self.analyzer._calculate_quality_score(
            total_records=100,
            valid_records=100,
            missing_count=0,
            price_anomaly_count=0,
            volume_anomaly_count=0
        )
        assert score1 == 100.0

        # 有問題的數據
        score2 = self.analyzer._calculate_quality_score(
            total_records=100,
            valid_records=80,
            missing_count=5,
            price_anomaly_count=3,
            volume_anomaly_count=2
        )
        assert score2 < 80.0  # 應該被扣分


class TestDataCleaningService:
    """數據清理服務測試類"""

    def setup_method(self):
        """測試前設置"""
        self.cleaning_service = DataCleaningService()

    @patch.object(DataQualityAnalyzer, 'analyze_stock_data_quality')
    async def test_clean_stock_data_no_issues(self, mock_analyze):
        """測試清理沒有問題的股票數據"""
        # Mock 品質報告 - 沒有問題
        mock_report = DataQualityReport(
            stock_symbol="2330.TW",
            stock_market="TW",
            total_records=100,
            valid_records=100,
            invalid_records=0,
            missing_dates=[],
            duplicate_dates=[],
            price_anomalies=[],
            volume_anomalies=[],
            data_gaps=[],
            quality_score=100.0
        )
        mock_analyze.return_value = mock_report

        # 執行測試
        db_session = Mock()
        result = await self.cleaning_service.clean_stock_data(db_session, stock_id=1)

        # 驗證結果
        assert result['success'] is True
        assert result['stock_id'] == 1
        assert result['quality_score_before'] == 100.0
        assert len(result['cleaning_actions']) == 0

    @patch.object(DataQualityAnalyzer, 'analyze_stock_data_quality')
    async def test_clean_stock_data_with_duplicates(self, mock_analyze):
        """測試清理有重複數據的股票"""
        # Mock 品質報告 - 有重複日期
        mock_report = DataQualityReport(
            stock_symbol="2330.TW",
            stock_market="TW",
            total_records=100,
            valid_records=98,
            invalid_records=2,
            missing_dates=[],
            duplicate_dates=[date(2024, 1, 1), date(2024, 1, 2)],
            price_anomalies=[],
            volume_anomalies=[],
            data_gaps=[],
            quality_score=85.0
        )
        mock_analyze.return_value = mock_report

        # 執行測試 - 不自動修復
        db_session = Mock()
        result = await self.cleaning_service.clean_stock_data(
            db_session, stock_id=1, auto_fix=False
        )

        # 驗證結果
        assert result['success'] is True
        assert any("重複日期" in action for action in result['cleaning_actions'])
        assert result['auto_fix_applied'] is False

    @patch.object(DataQualityAnalyzer, 'analyze_stock_data_quality')
    @patch('services.data.validation.price_history_crud')
    async def test_clean_stock_data_auto_fix(self, mock_price_crud, mock_analyze):
        """測試自動修復數據"""
        # Mock 品質報告 - 有重複日期
        mock_report = DataQualityReport(
            stock_symbol="2330.TW",
            stock_market="TW",
            total_records=100,
            valid_records=98,
            invalid_records=2,
            missing_dates=[],
            duplicate_dates=[date(2024, 1, 1)],
            price_anomalies=[{'date': date(2024, 1, 2), 'errors': ['price error']}],
            volume_anomalies=[],
            data_gaps=[],
            quality_score=85.0
        )
        mock_analyze.return_value = mock_report

        # Mock CRUD 操作
        mock_records = [Mock(id=1), Mock(id=2)]
        mock_price_crud.get_multi_by_field = AsyncMock(return_value=mock_records)
        mock_price_crud.remove = AsyncMock(return_value=True)

        # 執行測試 - 自動修復
        db_session = Mock()
        result = await self.cleaning_service.clean_stock_data(
            db_session, stock_id=1, auto_fix=True
        )

        # 驗證結果
        assert result['success'] is True
        assert any("移除了" in action and "重複記錄" in action for action in result['cleaning_actions'])
        assert any("修復了" in action and "價格異常" in action for action in result['cleaning_actions'])
        assert result['auto_fix_applied'] is True

    @patch('services.data.validation.price_history_crud')
    async def test_remove_duplicate_records(self, mock_price_crud):
        """測試移除重複記錄"""
        # Mock 重複記錄
        mock_records = [Mock(id=1), Mock(id=2), Mock(id=3)]
        mock_price_crud.get_multi_by_field = AsyncMock(return_value=mock_records)
        mock_price_crud.remove = AsyncMock(return_value=True)

        # 執行測試
        db_session = Mock()
        removed_count = await self.cleaning_service._remove_duplicate_records(
            db_session, stock_id=1, duplicate_dates=[date(2024, 1, 1)]
        )

        # 驗證結果
        assert removed_count == 2  # 保留第一筆，刪除其餘2筆
        assert mock_price_crud.remove.call_count == 2

    async def test_fix_price_anomalies(self):
        """測試修復價格異常"""
        anomalies = [
            {'date': date(2024, 1, 1), 'errors': ['price error 1']},
            {'date': date(2024, 1, 2), 'errors': ['price error 2']},
        ]

        # 執行測試
        db_session = Mock()
        fixed_count = await self.cleaning_service._fix_price_anomalies(
            db_session, stock_id=1, anomalies=anomalies
        )

        # 驗證結果
        assert fixed_count == 2


async def run_all_tests():
    """執行所有測試"""
    print("開始執行數據驗證服務測試...")

    # 測試價格數據驗證器
    print("\n=== 測試 PriceDataValidator ===")
    test_validator = TestPriceDataValidator()

    try:
        test_validator.setup_method()

        test_validator.test_validate_valid_price_record()
        print("✅ 有效價格記錄驗證測試 - 通過")

        test_validator.test_validate_missing_required_fields()
        print("✅ 缺少必要欄位測試 - 通過")

        test_validator.test_validate_negative_prices()
        print("✅ 負數價格測試 - 通過")

        test_validator.test_validate_high_low_price_logic()
        print("✅ 高低價邏輯測試 - 通過")

        test_validator.test_validate_open_close_price_range()
        print("✅ 開收盤價範圍測試 - 通過")

        test_validator.test_validate_negative_volume()
        print("✅ 負成交量測試 - 通過")

        test_validator.test_validate_zero_volume_warning()
        print("✅ 零成交量警告測試 - 通過")

        test_validator.test_validate_future_date()
        print("✅ 未來日期測試 - 通過")

        test_validator.test_validate_weekend_date_warning()
        print("✅ 週末日期警告測試 - 通過")

        test_validator.test_validate_excessive_price_volatility()
        print("✅ 過度價格波動測試 - 通過")

        test_validator.test_validation_levels()
        print("✅ 驗證等級測試 - 通過")

        test_validator.test_invalid_date_format()
        print("✅ 無效日期格式測試 - 通過")

    except Exception as e:
        print(f"❌ PriceDataValidator 測試失敗: {str(e)}")
        return False

    # 測試數據品質分析器
    print("\n=== 測試 DataQualityAnalyzer ===")
    test_analyzer = TestDataQualityAnalyzer()

    try:
        test_analyzer.setup_method()

        await test_analyzer.test_analyze_stock_data_quality_success()
        print("✅ 股票數據品質分析成功測試 - 通過")

        await test_analyzer.test_analyze_stock_not_found()
        print("✅ 股票不存在測試 - 通過")

        test_analyzer.test_find_duplicate_dates()
        print("✅ 找出重複日期測試 - 通過")

        test_analyzer.test_find_data_gaps()
        print("✅ 找出數據間隙測試 - 通過")

        test_analyzer.test_calculate_quality_score()
        print("✅ 計算品質分數測試 - 通過")

    except Exception as e:
        print(f"❌ DataQualityAnalyzer 測試失敗: {str(e)}")
        return False

    # 測試數據清理服務
    print("\n=== 測試 DataCleaningService ===")
    test_cleaning = TestDataCleaningService()

    try:
        test_cleaning.setup_method()

        await test_cleaning.test_clean_stock_data_no_issues()
        print("✅ 清理無問題數據測試 - 通過")

        await test_cleaning.test_clean_stock_data_with_duplicates()
        print("✅ 清理重複數據測試 - 通過")

        await test_cleaning.test_clean_stock_data_auto_fix()
        print("✅ 自動修復數據測試 - 通過")

        await test_cleaning.test_remove_duplicate_records()
        print("✅ 移除重複記錄測試 - 通過")

        await test_cleaning.test_fix_price_anomalies()
        print("✅ 修復價格異常測試 - 通過")

    except Exception as e:
        print(f"❌ DataCleaningService 測試失敗: {str(e)}")
        return False

    print("\n🎉 所有數據驗證服務測試通過！")
    return True


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    exit(0 if success else 1)