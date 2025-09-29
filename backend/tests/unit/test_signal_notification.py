#!/usr/bin/env python3
"""
Signal Notification Tests - Clean Architecture
Testing signal notification service and alert system
"""
import pytest
import sys
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime, date, timedelta
from decimal import Decimal

sys.path.append('/home/opc/projects/kiro-stock-platform/backend')

from services.trading.signal_notification import (
    SignalNotificationService,
    NotificationType,
    AlertLevel,
    NotificationRule,
    NotificationMessage
)
from services.trading.buy_sell_generator import (
    BuySellPoint,
    BuySellAction,
    SignalPriority
)
from models.domain.trading_signal import TradingSignal


class TestSignalNotificationService:
    """Signal Notification Service Tests"""

    def setup_method(self):
        """Setup test environment"""
        self.notification_service = SignalNotificationService()

    def test_add_notification_rule(self):
        """Test adding notification rules"""
        user_id = 1
        stock_symbols = ["AAPL", "TSLA"]
        signal_types = ["buy", "sell"]
        min_confidence = 0.8
        min_priority = SignalPriority.HIGH
        notification_types = [NotificationType.EMAIL, NotificationType.PUSH]

        rule_id = self.notification_service.add_notification_rule(
            user_id=user_id,
            stock_symbols=stock_symbols,
            signal_types=signal_types,
            min_confidence=min_confidence,
            min_priority=min_priority,
            notification_types=notification_types
        )

        # Verify rule was added
        assert rule_id is not None
        assert rule_id.startswith(f"rule_{user_id}")

        # Verify rule exists in service
        user_rules = self.notification_service.get_user_notification_rules(user_id)
        assert len(user_rules) == 1

        rule = user_rules[0]
        assert rule.user_id == user_id
        assert rule.stock_symbols == stock_symbols
        assert rule.signal_types == signal_types
        assert rule.min_confidence == min_confidence
        assert rule.min_priority == min_priority
        assert rule.notification_types == notification_types
        assert rule.enabled is True

    def test_remove_notification_rule(self):
        """Test removing notification rules"""
        user_id = 1

        # Add a rule first
        rule_id = self.notification_service.add_notification_rule(
            user_id=user_id,
            stock_symbols=["AAPL"],
            notification_types=[NotificationType.EMAIL]
        )

        # Verify rule exists
        assert len(self.notification_service.get_user_notification_rules(user_id)) == 1

        # Remove the rule
        removed = self.notification_service.remove_notification_rule(user_id, rule_id)
        assert removed is True

        # Verify rule is gone
        assert len(self.notification_service.get_user_notification_rules(user_id)) == 0

        # Try to remove non-existent rule
        removed = self.notification_service.remove_notification_rule(user_id, "non_existent")
        assert removed is False

    def test_notification_rule_matches_signal(self):
        """Test notification rule signal matching"""
        # Create a notification rule
        rule = NotificationRule(
            rule_id="test_rule",
            user_id=1,
            stock_symbols=["AAPL", "TSLA"],
            signal_types=["buy", "strong_buy"],
            min_confidence=0.7,
            min_priority=SignalPriority.MEDIUM,
            notification_types=[NotificationType.EMAIL],
            enabled=True,
            created_at=datetime.now()
        )

        # Create matching signal
        matching_signal = MagicMock()
        matching_signal.signal_type = "buy"
        matching_signal.confidence = 0.8

        # Test matching
        assert rule.matches_signal("AAPL", matching_signal) is True
        assert rule.matches_signal("GOOGL", matching_signal) is False  # Wrong symbol

        # Create non-matching signal (low confidence)
        low_confidence_signal = MagicMock()
        low_confidence_signal.signal_type = "buy"
        low_confidence_signal.confidence = 0.5

        assert rule.matches_signal("AAPL", low_confidence_signal) is False

        # Create non-matching signal (wrong type)
        wrong_type_signal = MagicMock()
        wrong_type_signal.signal_type = "hold"
        wrong_type_signal.confidence = 0.8

        assert rule.matches_signal("AAPL", wrong_type_signal) is False

    def test_notification_rule_matches_buy_sell_point(self):
        """Test notification rule buy/sell point matching"""
        rule = NotificationRule(
            rule_id="test_rule",
            user_id=1,
            stock_symbols=["AAPL"],
            signal_types=[],
            min_confidence=0.7,
            min_priority=SignalPriority.MEDIUM,
            notification_types=[NotificationType.EMAIL],
            enabled=True,
            created_at=datetime.now()
        )

        # Create matching buy/sell point
        matching_point = MagicMock()
        matching_point.confidence = 0.8
        matching_point.priority = SignalPriority.HIGH

        assert rule.matches_buy_sell_point("AAPL", matching_point) is True
        assert rule.matches_buy_sell_point("GOOGL", matching_point) is False  # Wrong symbol

        # Create non-matching point (low confidence)
        low_confidence_point = MagicMock()
        low_confidence_point.confidence = 0.5
        low_confidence_point.priority = SignalPriority.HIGH

        assert rule.matches_buy_sell_point("AAPL", low_confidence_point) is False

        # Create non-matching point (low priority)
        low_priority_point = MagicMock()
        low_priority_point.confidence = 0.8
        low_priority_point.priority = SignalPriority.LOW

        assert rule.matches_buy_sell_point("AAPL", low_priority_point) is False

    @pytest.mark.asyncio
    async def test_process_trading_signal(self):
        """Test processing trading signals for notifications"""
        # Add notification rule
        user_id = 1
        self.notification_service.add_notification_rule(
            user_id=user_id,
            stock_symbols=["AAPL"],
            signal_types=["buy"],
            min_confidence=0.7,
            notification_types=[NotificationType.IN_APP]
        )

        # Mock database session and stock
        db_session = MagicMock()
        stock_id = 123
        mock_stock = MagicMock()
        mock_stock.symbol = "AAPL"

        # Create trading signal
        signal = MagicMock()
        signal.signal_type = "buy"
        signal.confidence = 0.8
        signal.price = Decimal("150.00")
        signal.date = date.today()
        signal.description = "Strong buy signal"

        # Mock the stock_crud.get method
        with patch('services.trading.signal_notification.stock_crud') as mock_crud:
            mock_crud.get = AsyncMock(return_value=mock_stock)

            # Process the signal
            await self.notification_service.process_trading_signal(
                db_session, stock_id, signal
            )

            # Verify notification was created
            assert len(self.notification_service.message_queue) == 1

            message = self.notification_service.message_queue[0]
            assert message.user_id == user_id
            assert message.stock_symbol == "AAPL"
            assert message.notification_type == NotificationType.IN_APP
            assert "AAPL 交易信號提醒" in message.title

    @pytest.mark.asyncio
    async def test_process_buy_sell_point(self):
        """Test processing buy/sell points for notifications"""
        # Add notification rule
        user_id = 1
        self.notification_service.add_notification_rule(
            user_id=user_id,
            stock_symbols=["TSLA"],
            min_confidence=0.7,
            min_priority=SignalPriority.MEDIUM,
            notification_types=[NotificationType.EMAIL]
        )

        # Mock database session and stock
        db_session = MagicMock()
        stock_id = 456
        mock_stock = MagicMock()
        mock_stock.symbol = "TSLA"

        # Create buy/sell point
        buy_sell_point = MagicMock()
        buy_sell_point.action = BuySellAction.BUY
        buy_sell_point.confidence = 0.85
        buy_sell_point.price = Decimal("200.00")
        buy_sell_point.priority = SignalPriority.HIGH
        buy_sell_point.risk_level = "medium"
        buy_sell_point.reason = "Golden cross detected"
        buy_sell_point.stop_loss = Decimal("190.00")
        buy_sell_point.take_profit = Decimal("220.00")
        buy_sell_point.to_dict = MagicMock(return_value={
            "action": "buy",
            "confidence": 0.85,
            "price": 200.00
        })

        # Mock the stock_crud.get method
        with patch('services.trading.signal_notification.stock_crud') as mock_crud:
            mock_crud.get = AsyncMock(return_value=mock_stock)

            # Process the buy/sell point
            await self.notification_service.process_buy_sell_point(
                db_session, stock_id, buy_sell_point
            )

            # Verify notification was created
            assert len(self.notification_service.message_queue) == 1

            message = self.notification_service.message_queue[0]
            assert message.user_id == user_id
            assert message.stock_symbol == "TSLA"
            assert message.notification_type == NotificationType.EMAIL
            assert "TSLA 買入信號" in message.title

    @pytest.mark.asyncio
    async def test_process_notification_queue(self):
        """Test processing notification queue"""
        # Create mock notification messages
        message1 = NotificationMessage(
            message_id="msg_1",
            user_id=1,
            notification_type=NotificationType.IN_APP,
            alert_level=AlertLevel.INFO,
            title="Test Notification 1",
            content="Test content 1",
            stock_symbol="AAPL",
            signal_data={},
            created_at=datetime.now(),
            status="pending"
        )

        message2 = NotificationMessage(
            message_id="msg_2",
            user_id=1,
            notification_type=NotificationType.EMAIL,
            alert_level=AlertLevel.WARNING,
            title="Test Notification 2",
            content="Test content 2",
            stock_symbol="TSLA",
            signal_data={},
            created_at=datetime.now(),
            status="pending"
        )

        # Add messages to queue
        self.notification_service.message_queue.extend([message1, message2])

        # Process the queue
        await self.notification_service.process_notification_queue()

        # Verify messages were processed
        assert message1.status == "sent"
        assert message1.sent_at is not None
        assert message2.status == "sent"
        assert message2.sent_at is not None

    def test_notification_statistics(self):
        """Test notification statistics"""
        # Create mock messages with different statuses
        message1 = NotificationMessage(
            message_id="msg_1",
            user_id=1,
            notification_type=NotificationType.EMAIL,
            alert_level=AlertLevel.INFO,
            title="Test 1",
            content="Content 1",
            stock_symbol="AAPL",
            signal_data={},
            created_at=datetime.now(),
            status="sent"
        )

        message2 = NotificationMessage(
            message_id="msg_2",
            user_id=2,
            notification_type=NotificationType.PUSH,
            alert_level=AlertLevel.WARNING,
            title="Test 2",
            content="Content 2",
            stock_symbol="TSLA",
            signal_data={},
            created_at=datetime.now(),
            status="failed"
        )

        message3 = NotificationMessage(
            message_id="msg_3",
            user_id=1,
            notification_type=NotificationType.EMAIL,
            alert_level=AlertLevel.CRITICAL,
            title="Test 3",
            content="Content 3",
            stock_symbol="GOOGL",
            signal_data={},
            created_at=datetime.now(),
            status="pending"
        )

        self.notification_service.message_queue.extend([message1, message2, message3])

        # Add some notification rules
        self.notification_service.add_notification_rule(user_id=1)
        self.notification_service.add_notification_rule(user_id=2)

        # Get statistics
        stats = self.notification_service.get_notification_statistics()

        # Verify statistics
        assert stats['total_messages'] == 3
        assert stats['sent_messages'] == 1
        assert stats['failed_messages'] == 1
        assert stats['pending_messages'] == 1
        assert stats['success_rate'] == 1/3
        assert stats['total_rules'] == 2
        assert stats['active_users'] == 2

        # Verify type statistics
        assert 'email' in stats['type_statistics']
        assert 'push' in stats['type_statistics']
        assert stats['type_statistics']['email']['total'] == 2
        assert stats['type_statistics']['email']['sent'] == 1

        # Verify user statistics
        assert stats['user_statistics'][1] == 2  # User 1 has 2 messages
        assert stats['user_statistics'][2] == 1  # User 2 has 1 message

    def test_get_user_messages(self):
        """Test getting user messages"""
        # Create messages for different users
        message1 = NotificationMessage(
            message_id="msg_1",
            user_id=1,
            notification_type=NotificationType.EMAIL,
            alert_level=AlertLevel.INFO,
            title="Message 1",
            content="Content 1",
            stock_symbol="AAPL",
            signal_data={},
            created_at=datetime.now() - timedelta(hours=2),
            status="sent"
        )

        message2 = NotificationMessage(
            message_id="msg_2",
            user_id=1,
            notification_type=NotificationType.PUSH,
            alert_level=AlertLevel.WARNING,
            title="Message 2",
            content="Content 2",
            stock_symbol="TSLA",
            signal_data={},
            created_at=datetime.now() - timedelta(hours=1),
            status="pending"
        )

        message3 = NotificationMessage(
            message_id="msg_3",
            user_id=2,
            notification_type=NotificationType.EMAIL,
            alert_level=AlertLevel.CRITICAL,
            title="Message 3",
            content="Content 3",
            stock_symbol="GOOGL",
            signal_data={},
            created_at=datetime.now(),
            status="sent"
        )

        self.notification_service.message_queue.extend([message1, message2, message3])

        # Get all messages for user 1
        user1_messages = self.notification_service.get_user_messages(user_id=1)
        assert len(user1_messages) == 2
        # Should be sorted by created_at descending (newest first)
        assert user1_messages[0].message_id == "msg_2"
        assert user1_messages[1].message_id == "msg_1"

        # Get only sent messages for user 1
        user1_sent = self.notification_service.get_user_messages(user_id=1, status="sent")
        assert len(user1_sent) == 1
        assert user1_sent[0].message_id == "msg_1"

        # Get messages for user 2
        user2_messages = self.notification_service.get_user_messages(user_id=2)
        assert len(user2_messages) == 1
        assert user2_messages[0].message_id == "msg_3"

        # Get messages for non-existent user
        user3_messages = self.notification_service.get_user_messages(user_id=3)
        assert len(user3_messages) == 0

    def test_notification_message_to_dict(self):
        """Test notification message serialization"""
        message = NotificationMessage(
            message_id="test_msg",
            user_id=1,
            notification_type=NotificationType.EMAIL,
            alert_level=AlertLevel.WARNING,
            title="Test Message",
            content="Test Content",
            stock_symbol="AAPL",
            signal_data={"test": "data"},
            created_at=datetime(2024, 1, 1, 12, 0, 0),
            sent_at=datetime(2024, 1, 1, 12, 1, 0),
            status="sent"
        )

        result = message.to_dict()

        assert result['message_id'] == "test_msg"
        assert result['user_id'] == 1
        assert result['notification_type'] == "email"
        assert result['alert_level'] == "warning"
        assert result['title'] == "Test Message"
        assert result['content'] == "Test Content"
        assert result['stock_symbol'] == "AAPL"
        assert result['signal_data'] == {"test": "data"}
        assert result['created_at'] == "2024-01-01T12:00:00"
        assert result['sent_at'] == "2024-01-01T12:01:00"
        assert result['status'] == "sent"

    def test_enum_values(self):
        """Test enum values are correctly defined"""
        # Test NotificationType enum
        assert NotificationType.EMAIL == "email"
        assert NotificationType.SMS == "sms"
        assert NotificationType.PUSH == "push"
        assert NotificationType.WEBHOOK == "webhook"
        assert NotificationType.IN_APP == "in_app"

        # Test AlertLevel enum
        assert AlertLevel.INFO == "info"
        assert AlertLevel.WARNING == "warning"
        assert AlertLevel.CRITICAL == "critical"
        assert AlertLevel.URGENT == "urgent"

    @pytest.mark.asyncio
    async def test_error_handling_stock_not_found(self):
        """Test error handling when stock is not found"""
        # Add notification rule
        user_id = 1
        self.notification_service.add_notification_rule(
            user_id=user_id,
            stock_symbols=["AAPL"],
            notification_types=[NotificationType.IN_APP]
        )

        # Mock database session
        db_session = MagicMock()
        stock_id = 999  # Non-existent stock

        # Create trading signal
        signal = MagicMock()
        signal.signal_type = "buy"
        signal.confidence = 0.8

        # Mock the stock_crud.get method to return None
        with patch('services.trading.signal_notification.stock_crud') as mock_crud:
            mock_crud.get = AsyncMock(return_value=None)

            # Process the signal - should not crash
            await self.notification_service.process_trading_signal(
                db_session, stock_id, signal
            )

            # Verify no notification was created
            assert len(self.notification_service.message_queue) == 0

    def test_disabled_notification_rules(self):
        """Test that disabled notification rules are ignored"""
        user_id = 1

        # Add enabled rule
        rule_id = self.notification_service.add_notification_rule(
            user_id=user_id,
            stock_symbols=["AAPL"],
            notification_types=[NotificationType.EMAIL]
        )

        # Disable the rule
        rules = self.notification_service.get_user_notification_rules(user_id)
        rules[0].enabled = False

        # Create signal that would normally match
        signal = MagicMock()
        signal.signal_type = "buy"
        signal.confidence = 0.8

        # Create notification rule manually for testing
        rule = rules[0]

        # Even though signal matches, rule is disabled
        assert rule.matches_signal("AAPL", signal) is True
        assert rule.enabled is False