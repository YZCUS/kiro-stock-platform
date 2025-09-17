#!/usr/bin/env python3
"""
信號通知服務單元測試
"""
import asyncio
import pytest
import sys
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta
from decimal import Decimal

# 添加項目根目錄到 Python 路徑
sys.path.append('/Users/zhengchy/Documents/projects/kiro-stock-platform/backend')

from services.trading.signal_notification import (
    NotificationRule,
    NotificationType,
    AlertLevel,
    SignalNotificationService,
    NotificationChannel
)
from services.trading.buy_sell_generator import SignalPriority
from models.domain.trading_signal import TradingSignal


class TestNotificationRule:
    """通知規則測試類"""

    def setup_method(self):
        """測試前設置"""
        self.rule = NotificationRule(
            rule_id="rule_001",
            user_id=1,
            stock_symbols=["2330.TW", "AAPL"],
            signal_types=["BUY", "SELL"],
            min_confidence=0.7,
            min_priority=SignalPriority.MEDIUM,
            notification_types=[NotificationType.EMAIL, NotificationType.PUSH],
            enabled=True,
            created_at=datetime.now()
        )

    def test_matches_signal_success(self):
        """測試信號匹配成功"""
        # 創建匹配的信號
        signal = Mock(spec=TradingSignal)
        signal.signal_type = "BUY"
        signal.confidence = 0.8
        signal.priority = SignalPriority.HIGH

        # 執行測試
        result = self.rule.matches_signal("2330.TW", signal)

        # 驗證結果
        assert result is True

    def test_matches_signal_wrong_stock(self):
        """測試股票代號不匹配"""
        # 創建信號
        signal = Mock(spec=TradingSignal)
        signal.signal_type = "BUY"
        signal.confidence = 0.8
        signal.priority = SignalPriority.HIGH

        # 執行測試 - 不在規則中的股票
        result = self.rule.matches_signal("2317.TW", signal)

        # 驗證結果
        assert result is False

    def test_matches_signal_wrong_type(self):
        """測試信號類型不匹配"""
        # 創建信號
        signal = Mock(spec=TradingSignal)
        signal.signal_type = "HOLD"  # 不在規則中的類型
        signal.confidence = 0.8
        signal.priority = SignalPriority.HIGH

        # 執行測試
        result = self.rule.matches_signal("2330.TW", signal)

        # 驗證結果
        assert result is False

    def test_matches_signal_low_confidence(self):
        """測試信心度過低"""
        # 創建信號
        signal = Mock(spec=TradingSignal)
        signal.signal_type = "BUY"
        signal.confidence = 0.5  # 低於最低要求 0.7
        signal.priority = SignalPriority.HIGH

        # 執行測試
        result = self.rule.matches_signal("2330.TW", signal)

        # 驗證結果
        assert result is False

    def test_matches_signal_low_priority(self):
        """測試優先級過低"""
        # 創建信號
        signal = Mock(spec=TradingSignal)
        signal.signal_type = "BUY"
        signal.confidence = 0.8
        signal.priority = SignalPriority.LOW  # 低於最低要求 MEDIUM

        # 執行測試
        result = self.rule.matches_signal("2330.TW", signal)

        # 驗證結果
        assert result is False

    def test_matches_signal_empty_restrictions(self):
        """測試無限制規則"""
        # 創建無限制規則
        unrestricted_rule = NotificationRule(
            rule_id="rule_002",
            user_id=1,
            stock_symbols=[],  # 空列表表示所有股票
            signal_types=[],   # 空列表表示所有類型
            min_confidence=0.0,
            min_priority=SignalPriority.LOW,
            notification_types=[NotificationType.EMAIL],
            enabled=True,
            created_at=datetime.now()
        )

        # 創建信號
        signal = Mock(spec=TradingSignal)
        signal.signal_type = "ANY_TYPE"
        signal.confidence = 0.1
        signal.priority = SignalPriority.LOW

        # 執行測試
        result = unrestricted_rule.matches_signal("ANY_STOCK", signal)

        # 驗證結果
        assert result is True


class TestNotificationChannel:
    """通知渠道測試類"""

    def setup_method(self):
        """測試前設置"""
        self.channel = NotificationChannel(NotificationType.EMAIL)

    async def test_send_email_notification_success(self):
        """測試成功發送郵件通知"""
        # Mock 郵件發送
        with patch.object(self.channel, '_send_email') as mock_send_email:
            mock_send_email.return_value = True

            # 執行測試
            result = await self.channel.send_notification(
                recipient="test@example.com",
                subject="測試通知",
                content="這是一個測試通知",
                metadata={}
            )

            # 驗證結果
            assert result is True
            mock_send_email.assert_called_once()

    async def test_send_push_notification_success(self):
        """測試成功發送推送通知"""
        # 創建推送渠道
        push_channel = NotificationChannel(NotificationType.PUSH)

        # Mock 推送發送
        with patch.object(push_channel, '_send_push') as mock_send_push:
            mock_send_push.return_value = True

            # 執行測試
            result = await push_channel.send_notification(
                recipient="device_token_123",
                subject="測試推送",
                content="這是一個測試推送",
                metadata={}
            )

            # 驗證結果
            assert result is True
            mock_send_push.assert_called_once()

    async def test_send_webhook_notification_success(self):
        """測試成功發送 Webhook 通知"""
        # 創建 Webhook 渠道
        webhook_channel = NotificationChannel(NotificationType.WEBHOOK)

        # Mock Webhook 發送
        with patch.object(webhook_channel, '_send_webhook') as mock_send_webhook:
            mock_send_webhook.return_value = True

            # 執行測試
            result = await webhook_channel.send_notification(
                recipient="https://api.example.com/webhook",
                subject="測試 Webhook",
                content="這是一個測試 Webhook",
                metadata={"custom_field": "value"}
            )

            # 驗證結果
            assert result is True
            mock_send_webhook.assert_called_once()

    async def test_send_notification_failure(self):
        """測試發送通知失敗"""
        # Mock 發送失敗
        with patch.object(self.channel, '_send_email') as mock_send_email:
            mock_send_email.side_effect = Exception("發送失敗")

            # 執行測試
            result = await self.channel.send_notification(
                recipient="test@example.com",
                subject="測試通知",
                content="這是一個測試通知",
                metadata={}
            )

            # 驗證結果
            assert result is False

    def test_format_signal_message_buy_signal(self):
        """測試格式化買入信號消息"""
        # 創建買入信號
        signal = Mock(spec=TradingSignal)
        signal.signal_type = "BUY"
        signal.confidence = 0.85
        signal.price = Decimal('500.0')
        signal.description = "黃金交叉形成"

        # 執行測試
        subject, content = self.channel.format_signal_message("2330.TW", signal)

        # 驗證結果
        assert "買入" in subject
        assert "2330.TW" in subject
        assert "500.0" in content
        assert "85%" in content
        assert "黃金交叉形成" in content

    def test_format_signal_message_sell_signal(self):
        """測試格式化賣出信號消息"""
        # 創建賣出信號
        signal = Mock(spec=TradingSignal)
        signal.signal_type = "SELL"
        signal.confidence = 0.75
        signal.price = Decimal('480.0')
        signal.description = "死亡交叉出現"

        # 執行測試
        subject, content = self.channel.format_signal_message("2330.TW", signal)

        # 驗證結果
        assert "賣出" in subject
        assert "2330.TW" in subject
        assert "480.0" in content
        assert "75%" in content
        assert "死亡交叉出現" in content


class TestSignalNotificationService:
    """信號通知服務測試類"""

    def setup_method(self):
        """測試前設置"""
        self.service = SignalNotificationService()

    async def test_add_notification_rule_success(self):
        """測試成功添加通知規則"""
        # 創建規則
        rule = NotificationRule(
            rule_id="rule_001",
            user_id=1,
            stock_symbols=["2330.TW"],
            signal_types=["BUY"],
            min_confidence=0.7,
            min_priority=SignalPriority.MEDIUM,
            notification_types=[NotificationType.EMAIL],
            enabled=True,
            created_at=datetime.now()
        )

        # 執行測試
        await self.service.add_notification_rule(rule)

        # 驗證結果
        assert rule.rule_id in self.service.notification_rules
        assert self.service.notification_rules[rule.rule_id] == rule

    async def test_remove_notification_rule_success(self):
        """測試成功移除通知規則"""
        # 先添加規則
        rule = NotificationRule(
            rule_id="rule_001",
            user_id=1,
            stock_symbols=["2330.TW"],
            signal_types=["BUY"],
            min_confidence=0.7,
            min_priority=SignalPriority.MEDIUM,
            notification_types=[NotificationType.EMAIL],
            enabled=True,
            created_at=datetime.now()
        )
        await self.service.add_notification_rule(rule)

        # 執行測試
        result = await self.service.remove_notification_rule("rule_001")

        # 驗證結果
        assert result is True
        assert "rule_001" not in self.service.notification_rules

    async def test_remove_notification_rule_not_found(self):
        """測試移除不存在的通知規則"""
        # 執行測試
        result = await self.service.remove_notification_rule("nonexistent_rule")

        # 驗證結果
        assert result is False

    async def test_process_signal_with_matching_rules(self):
        """測試處理匹配規則的信號"""
        # 添加匹配規則
        rule = NotificationRule(
            rule_id="rule_001",
            user_id=1,
            stock_symbols=["2330.TW"],
            signal_types=["BUY"],
            min_confidence=0.7,
            min_priority=SignalPriority.MEDIUM,
            notification_types=[NotificationType.EMAIL],
            enabled=True,
            created_at=datetime.now()
        )
        await self.service.add_notification_rule(rule)

        # 創建匹配的信號
        signal = Mock(spec=TradingSignal)
        signal.signal_type = "BUY"
        signal.confidence = 0.8
        signal.priority = SignalPriority.HIGH
        signal.price = Decimal('500.0')
        signal.description = "買入信號"

        # Mock 發送通知
        self.service._send_notification_to_user = AsyncMock(return_value=True)

        # 執行測試
        await self.service.process_signal("2330.TW", signal)

        # 驗證結果
        self.service._send_notification_to_user.assert_called_once()

    async def test_process_signal_no_matching_rules(self):
        """測試處理不匹配規則的信號"""
        # 添加不匹配規則
        rule = NotificationRule(
            rule_id="rule_001",
            user_id=1,
            stock_symbols=["2317.TW"],  # 不同股票
            signal_types=["BUY"],
            min_confidence=0.7,
            min_priority=SignalPriority.MEDIUM,
            notification_types=[NotificationType.EMAIL],
            enabled=True,
            created_at=datetime.now()
        )
        await self.service.add_notification_rule(rule)

        # 創建信號
        signal = Mock(spec=TradingSignal)
        signal.signal_type = "BUY"
        signal.confidence = 0.8
        signal.priority = SignalPriority.HIGH

        # Mock 發送通知
        self.service._send_notification_to_user = AsyncMock()

        # 執行測試
        await self.service.process_signal("2330.TW", signal)

        # 驗證結果 - 不應該發送通知
        self.service._send_notification_to_user.assert_not_called()

    async def test_process_signal_disabled_rule(self):
        """測試處理已禁用規則的信號"""
        # 添加禁用規則
        rule = NotificationRule(
            rule_id="rule_001",
            user_id=1,
            stock_symbols=["2330.TW"],
            signal_types=["BUY"],
            min_confidence=0.7,
            min_priority=SignalPriority.MEDIUM,
            notification_types=[NotificationType.EMAIL],
            enabled=False,  # 禁用
            created_at=datetime.now()
        )
        await self.service.add_notification_rule(rule)

        # 創建匹配的信號
        signal = Mock(spec=TradingSignal)
        signal.signal_type = "BUY"
        signal.confidence = 0.8
        signal.priority = SignalPriority.HIGH

        # Mock 發送通知
        self.service._send_notification_to_user = AsyncMock()

        # 執行測試
        await self.service.process_signal("2330.TW", signal)

        # 驗證結果 - 不應該發送通知
        self.service._send_notification_to_user.assert_not_called()

    async def test_get_user_notification_rules_success(self):
        """測試成功取得用戶通知規則"""
        # 添加多個規則
        rule1 = NotificationRule(
            rule_id="rule_001",
            user_id=1,
            stock_symbols=["2330.TW"],
            signal_types=["BUY"],
            min_confidence=0.7,
            min_priority=SignalPriority.MEDIUM,
            notification_types=[NotificationType.EMAIL],
            enabled=True,
            created_at=datetime.now()
        )
        rule2 = NotificationRule(
            rule_id="rule_002",
            user_id=2,  # 不同用戶
            stock_symbols=["AAPL"],
            signal_types=["SELL"],
            min_confidence=0.8,
            min_priority=SignalPriority.HIGH,
            notification_types=[NotificationType.PUSH],
            enabled=True,
            created_at=datetime.now()
        )

        await self.service.add_notification_rule(rule1)
        await self.service.add_notification_rule(rule2)

        # 執行測試
        user1_rules = self.service.get_user_notification_rules(1)

        # 驗證結果
        assert len(user1_rules) == 1
        assert user1_rules[0].rule_id == "rule_001"

    async def test_update_notification_rule_success(self):
        """測試成功更新通知規則"""
        # 先添加規則
        rule = NotificationRule(
            rule_id="rule_001",
            user_id=1,
            stock_symbols=["2330.TW"],
            signal_types=["BUY"],
            min_confidence=0.7,
            min_priority=SignalPriority.MEDIUM,
            notification_types=[NotificationType.EMAIL],
            enabled=True,
            created_at=datetime.now()
        )
        await self.service.add_notification_rule(rule)

        # 準備更新數據
        updates = {
            "min_confidence": 0.8,
            "enabled": False
        }

        # 執行測試
        result = await self.service.update_notification_rule("rule_001", updates)

        # 驗證結果
        assert result is True
        updated_rule = self.service.notification_rules["rule_001"]
        assert updated_rule.min_confidence == 0.8
        assert updated_rule.enabled is False

    async def test_get_notification_stats_success(self):
        """測試取得通知統計"""
        # 添加一些規則
        rule1 = NotificationRule(
            rule_id="rule_001",
            user_id=1,
            stock_symbols=["2330.TW"],
            signal_types=["BUY"],
            min_confidence=0.7,
            min_priority=SignalPriority.MEDIUM,
            notification_types=[NotificationType.EMAIL],
            enabled=True,
            created_at=datetime.now()
        )
        rule2 = NotificationRule(
            rule_id="rule_002",
            user_id=1,
            stock_symbols=["AAPL"],
            signal_types=["SELL"],
            min_confidence=0.8,
            min_priority=SignalPriority.HIGH,
            notification_types=[NotificationType.PUSH],
            enabled=False,
            created_at=datetime.now()
        )

        await self.service.add_notification_rule(rule1)
        await self.service.add_notification_rule(rule2)

        # 執行測試
        stats = self.service.get_notification_stats()

        # 驗證結果
        assert stats["total_rules"] == 2
        assert stats["enabled_rules"] == 1
        assert stats["disabled_rules"] == 1
        assert NotificationType.EMAIL.value in stats["notification_types"]
        assert NotificationType.PUSH.value in stats["notification_types"]


async def run_all_tests():
    """執行所有測試"""
    print("開始執行信號通知服務測試...")

    # 測試通知規則
    print("\n=== 測試通知規則 ===")
    test_rule = TestNotificationRule()

    try:
        test_rule.setup_method()

        test_rule.test_matches_signal_success()
        print("✅ 信號匹配成功測試 - 通過")

        test_rule.test_matches_signal_wrong_stock()
        print("✅ 股票代號不匹配測試 - 通過")

        test_rule.test_matches_signal_wrong_type()
        print("✅ 信號類型不匹配測試 - 通過")

        test_rule.test_matches_signal_low_confidence()
        print("✅ 信心度過低測試 - 通過")

        test_rule.test_matches_signal_low_priority()
        print("✅ 優先級過低測試 - 通過")

        test_rule.test_matches_signal_empty_restrictions()
        print("✅ 無限制規則測試 - 通過")

    except Exception as e:
        print(f"❌ 通知規則測試失敗: {str(e)}")
        return False

    # 測試通知渠道
    print("\n=== 測試通知渠道 ===")
    test_channel = TestNotificationChannel()

    try:
        test_channel.setup_method()

        await test_channel.test_send_email_notification_success()
        print("✅ 發送郵件通知測試 - 通過")

        await test_channel.test_send_push_notification_success()
        print("✅ 發送推送通知測試 - 通過")

        await test_channel.test_send_webhook_notification_success()
        print("✅ 發送 Webhook 通知測試 - 通過")

        await test_channel.test_send_notification_failure()
        print("✅ 發送通知失敗測試 - 通過")

        test_channel.test_format_signal_message_buy_signal()
        print("✅ 格式化買入信號消息測試 - 通過")

        test_channel.test_format_signal_message_sell_signal()
        print("✅ 格式化賣出信號消息測試 - 通過")

    except Exception as e:
        print(f"❌ 通知渠道測試失敗: {str(e)}")
        return False

    # 測試信號通知服務
    print("\n=== 測試信號通知服務 ===")
    test_service = TestSignalNotificationService()

    try:
        test_service.setup_method()

        await test_service.test_add_notification_rule_success()
        print("✅ 添加通知規則測試 - 通過")

        await test_service.test_remove_notification_rule_success()
        print("✅ 移除通知規則測試 - 通過")

        await test_service.test_remove_notification_rule_not_found()
        print("✅ 移除不存在規則測試 - 通過")

        await test_service.test_process_signal_with_matching_rules()
        print("✅ 處理匹配規則信號測試 - 通過")

        await test_service.test_process_signal_no_matching_rules()
        print("✅ 處理不匹配規則信號測試 - 通過")

        await test_service.test_process_signal_disabled_rule()
        print("✅ 處理禁用規則信號測試 - 通過")

        await test_service.test_get_user_notification_rules_success()
        print("✅ 取得用戶通知規則測試 - 通過")

        await test_service.test_update_notification_rule_success()
        print("✅ 更新通知規則測試 - 通過")

        await test_service.test_get_notification_stats_success()
        print("✅ 取得通知統計測試 - 通過")

    except Exception as e:
        print(f"❌ 信號通知服務測試失敗: {str(e)}")
        return False

    print("\n🎉 所有信號通知服務測試通過！")
    return True


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    exit(0 if success else 1)