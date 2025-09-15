"""
信號通知和警報服務
"""
import asyncio
from typing import List, Dict, Any, Optional
from datetime import date, datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import logging
import json

from services.trading.buy_sell_generator import (
    BuySellPoint, 
    BuySellAction, 
    SignalPriority
)
from models.domain.trading_signal import TradingSignal
from models.repositories.crud_stock import stock_crud
from models.repositories.crud_trading_signal import trading_signal_crud

logger = logging.getLogger(__name__)


class NotificationType(str, Enum):
    """通知類型"""
    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"
    WEBHOOK = "webhook"
    IN_APP = "in_app"


class AlertLevel(str, Enum):
    """警報等級"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    URGENT = "urgent"


@dataclass
class NotificationRule:
    """通知規則"""
    rule_id: str
    user_id: int
    stock_symbols: List[str]
    signal_types: List[str]
    min_confidence: float
    min_priority: SignalPriority
    notification_types: List[NotificationType]
    enabled: bool
    created_at: datetime
    
    def matches_signal(self, stock_symbol: str, signal: TradingSignal) -> bool:
        """檢查信號是否符合規則"""
        # 檢查股票代號
        if self.stock_symbols and stock_symbol not in self.stock_symbols:
            return False
        
        # 檢查信號類型
        if self.signal_types and signal.signal_type not in self.signal_types:
            return False
        
        # 檢查信心度
        if signal.confidence < self.min_confidence:
            return False
        
        return True
    
    def matches_buy_sell_point(self, stock_symbol: str, point: BuySellPoint) -> bool:
        """檢查買賣點是否符合規則"""
        # 檢查股票代號
        if self.stock_symbols and stock_symbol not in self.stock_symbols:
            return False
        
        # 檢查信心度
        if point.confidence < self.min_confidence:
            return False
        
        # 檢查優先級
        priority_levels = {
            SignalPriority.LOW: 1,
            SignalPriority.MEDIUM: 2,
            SignalPriority.HIGH: 3,
            SignalPriority.CRITICAL: 4
        }
        
        if priority_levels.get(point.priority, 0) < priority_levels.get(self.min_priority, 0):
            return False
        
        return True


@dataclass
class NotificationMessage:
    """通知訊息"""
    message_id: str
    user_id: int
    notification_type: NotificationType
    alert_level: AlertLevel
    title: str
    content: str
    stock_symbol: str
    signal_data: Dict[str, Any]
    created_at: datetime
    sent_at: Optional[datetime] = None
    status: str = "pending"  # pending, sent, failed
    
    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典"""
        return {
            'message_id': self.message_id,
            'user_id': self.user_id,
            'notification_type': self.notification_type.value,
            'alert_level': self.alert_level.value,
            'title': self.title,
            'content': self.content,
            'stock_symbol': self.stock_symbol,
            'signal_data': self.signal_data,
            'created_at': self.created_at.isoformat(),
            'sent_at': self.sent_at.isoformat() if self.sent_at else None,
            'status': self.status
        }


class SignalNotificationService:
    """信號通知服務"""
    
    def __init__(self):
        self.notification_rules: Dict[int, List[NotificationRule]] = {}
        self.message_queue: List[NotificationMessage] = []
        self.notification_handlers = {
            NotificationType.EMAIL: self._send_email_notification,
            NotificationType.SMS: self._send_sms_notification,
            NotificationType.PUSH: self._send_push_notification,
            NotificationType.WEBHOOK: self._send_webhook_notification,
            NotificationType.IN_APP: self._send_in_app_notification
        }
    
    def add_notification_rule(
        self,
        user_id: int,
        stock_symbols: List[str] = None,
        signal_types: List[str] = None,
        min_confidence: float = 0.7,
        min_priority: SignalPriority = SignalPriority.MEDIUM,
        notification_types: List[NotificationType] = None
    ) -> str:
        """添加通知規則"""
        try:
            rule_id = f"rule_{user_id}_{datetime.now().timestamp()}"
            
            if notification_types is None:
                notification_types = [NotificationType.IN_APP]
            
            rule = NotificationRule(
                rule_id=rule_id,
                user_id=user_id,
                stock_symbols=stock_symbols or [],
                signal_types=signal_types or [],
                min_confidence=min_confidence,
                min_priority=min_priority,
                notification_types=notification_types,
                enabled=True,
                created_at=datetime.now()
            )
            
            if user_id not in self.notification_rules:
                self.notification_rules[user_id] = []
            
            self.notification_rules[user_id].append(rule)
            
            logger.info(f"添加通知規則: {rule_id} for user {user_id}")
            return rule_id
            
        except Exception as e:
            logger.error(f"添加通知規則時發生錯誤: {str(e)}")
            raise
    
    def remove_notification_rule(self, user_id: int, rule_id: str) -> bool:
        """移除通知規則"""
        try:
            if user_id in self.notification_rules:
                original_count = len(self.notification_rules[user_id])
                self.notification_rules[user_id] = [
                    rule for rule in self.notification_rules[user_id] 
                    if rule.rule_id != rule_id
                ]
                
                removed = len(self.notification_rules[user_id]) < original_count
                if removed:
                    logger.info(f"移除通知規則: {rule_id} for user {user_id}")
                
                return removed
            
            return False
            
        except Exception as e:
            logger.error(f"移除通知規則時發生錯誤: {str(e)}")
            return False
    
    def get_user_notification_rules(self, user_id: int) -> List[NotificationRule]:
        """獲取用戶的通知規則"""
        return self.notification_rules.get(user_id, [])
    
    async def process_trading_signal(
        self,
        db_session,
        stock_id: int,
        signal: TradingSignal
    ):
        """處理交易信號通知"""
        try:
            # 獲取股票資訊
            stock = await stock_crud.get(db_session, stock_id)
            if not stock:
                logger.warning(f"找不到股票 ID: {stock_id}")
                return
            
            # 檢查所有用戶的通知規則
            for user_id, rules in self.notification_rules.items():
                for rule in rules:
                    if not rule.enabled:
                        continue
                    
                    if rule.matches_signal(stock.symbol, signal):
                        await self._create_signal_notification(
                            user_id, stock.symbol, signal, rule
                        )
            
        except Exception as e:
            logger.error(f"處理交易信號通知時發生錯誤: {str(e)}")
    
    async def process_buy_sell_point(
        self,
        db_session,
        stock_id: int,
        buy_sell_point: BuySellPoint
    ):
        """處理買賣點通知"""
        try:
            # 獲取股票資訊
            stock = await stock_crud.get(db_session, stock_id)
            if not stock:
                logger.warning(f"找不到股票 ID: {stock_id}")
                return
            
            # 檢查所有用戶的通知規則
            for user_id, rules in self.notification_rules.items():
                for rule in rules:
                    if not rule.enabled:
                        continue
                    
                    if rule.matches_buy_sell_point(stock.symbol, buy_sell_point):
                        await self._create_buy_sell_notification(
                            user_id, stock.symbol, buy_sell_point, rule
                        )
            
        except Exception as e:
            logger.error(f"處理買賣點通知時發生錯誤: {str(e)}")
    
    async def _create_signal_notification(
        self,
        user_id: int,
        stock_symbol: str,
        signal: TradingSignal,
        rule: NotificationRule
    ):
        """建立信號通知"""
        try:
            # 決定警報等級
            alert_level = AlertLevel.INFO
            if signal.confidence >= 0.9:
                alert_level = AlertLevel.CRITICAL
            elif signal.confidence >= 0.8:
                alert_level = AlertLevel.WARNING
            
            # 生成通知內容
            title = f"{stock_symbol} 交易信號提醒"
            content = f"""
股票代號: {stock_symbol}
信號類型: {signal.signal_type}
信心度: {signal.confidence:.2f}
價格: {signal.price}
日期: {signal.date}
描述: {signal.description}
            """.strip()
            
            # 為每種通知類型建立訊息
            for notification_type in rule.notification_types:
                message = NotificationMessage(
                    message_id=f"msg_{datetime.now().timestamp()}_{user_id}",
                    user_id=user_id,
                    notification_type=notification_type,
                    alert_level=alert_level,
                    title=title,
                    content=content,
                    stock_symbol=stock_symbol,
                    signal_data={
                        'signal_type': signal.signal_type,
                        'confidence': signal.confidence,
                        'price': float(signal.price),
                        'date': signal.date.isoformat()
                    },
                    created_at=datetime.now()
                )
                
                self.message_queue.append(message)
                logger.info(f"建立信號通知: {message.message_id}")
            
        except Exception as e:
            logger.error(f"建立信號通知時發生錯誤: {str(e)}")
    
    async def _create_buy_sell_notification(
        self,
        user_id: int,
        stock_symbol: str,
        buy_sell_point: BuySellPoint,
        rule: NotificationRule
    ):
        """建立買賣點通知"""
        try:
            # 決定警報等級
            alert_level = AlertLevel.INFO
            if buy_sell_point.priority == SignalPriority.CRITICAL:
                alert_level = AlertLevel.URGENT
            elif buy_sell_point.priority == SignalPriority.HIGH:
                alert_level = AlertLevel.CRITICAL
            elif buy_sell_point.priority == SignalPriority.MEDIUM:
                alert_level = AlertLevel.WARNING
            
            # 生成通知內容
            action_text = "買入" if buy_sell_point.action == BuySellAction.BUY else "賣出"
            title = f"{stock_symbol} {action_text}信號"
            
            content = f"""
股票代號: {stock_symbol}
建議動作: {action_text}
優先級: {buy_sell_point.priority.value}
信心度: {buy_sell_point.confidence:.2f}
價格: {buy_sell_point.price}
風險等級: {buy_sell_point.risk_level}
理由: {buy_sell_point.reason}
            """.strip()
            
            if buy_sell_point.stop_loss:
                content += f"\n止損價: {buy_sell_point.stop_loss}"
            if buy_sell_point.take_profit:
                content += f"\n止盈價: {buy_sell_point.take_profit}"
            
            # 為每種通知類型建立訊息
            for notification_type in rule.notification_types:
                message = NotificationMessage(
                    message_id=f"msg_{datetime.now().timestamp()}_{user_id}",
                    user_id=user_id,
                    notification_type=notification_type,
                    alert_level=alert_level,
                    title=title,
                    content=content,
                    stock_symbol=stock_symbol,
                    signal_data=buy_sell_point.to_dict(),
                    created_at=datetime.now()
                )
                
                self.message_queue.append(message)
                logger.info(f"建立買賣點通知: {message.message_id}")
            
        except Exception as e:
            logger.error(f"建立買賣點通知時發生錯誤: {str(e)}")
    
    async def process_notification_queue(self):
        """處理通知隊列"""
        try:
            pending_messages = [msg for msg in self.message_queue if msg.status == "pending"]
            
            if not pending_messages:
                return
            
            logger.info(f"處理 {len(pending_messages)} 個待發送通知")
            
            for message in pending_messages:
                try:
                    handler = self.notification_handlers.get(message.notification_type)
                    if handler:
                        success = await handler(message)
                        if success:
                            message.status = "sent"
                            message.sent_at = datetime.now()
                        else:
                            message.status = "failed"
                    else:
                        logger.warning(f"未找到通知處理器: {message.notification_type}")
                        message.status = "failed"
                        
                except Exception as e:
                    logger.error(f"發送通知時發生錯誤: {str(e)}")
                    message.status = "failed"
            
            # 清理已處理的訊息（保留最近100條）
            self.message_queue = sorted(
                self.message_queue, 
                key=lambda x: x.created_at, 
                reverse=True
            )[:100]
            
        except Exception as e:
            logger.error(f"處理通知隊列時發生錯誤: {str(e)}")
    
    async def _send_email_notification(self, message: NotificationMessage) -> bool:
        """發送郵件通知"""
        try:
            # 這裡應該整合實際的郵件服務
            logger.info(f"發送郵件通知: {message.title} to user {message.user_id}")
            
            # 模擬發送
            await asyncio.sleep(0.1)
            return True
            
        except Exception as e:
            logger.error(f"發送郵件通知時發生錯誤: {str(e)}")
            return False
    
    async def _send_sms_notification(self, message: NotificationMessage) -> bool:
        """發送簡訊通知"""
        try:
            # 這裡應該整合實際的簡訊服務
            logger.info(f"發送簡訊通知: {message.title} to user {message.user_id}")
            
            # 模擬發送
            await asyncio.sleep(0.1)
            return True
            
        except Exception as e:
            logger.error(f"發送簡訊通知時發生錯誤: {str(e)}")
            return False
    
    async def _send_push_notification(self, message: NotificationMessage) -> bool:
        """發送推播通知"""
        try:
            # 這裡應該整合實際的推播服務
            logger.info(f"發送推播通知: {message.title} to user {message.user_id}")
            
            # 模擬發送
            await asyncio.sleep(0.1)
            return True
            
        except Exception as e:
            logger.error(f"發送推播通知時發生錯誤: {str(e)}")
            return False
    
    async def _send_webhook_notification(self, message: NotificationMessage) -> bool:
        """發送Webhook通知"""
        try:
            # 這裡應該發送HTTP請求到用戶指定的Webhook URL
            logger.info(f"發送Webhook通知: {message.title} to user {message.user_id}")
            
            # 模擬發送
            await asyncio.sleep(0.1)
            return True
            
        except Exception as e:
            logger.error(f"發送Webhook通知時發生錯誤: {str(e)}")
            return False
    
    async def _send_in_app_notification(self, message: NotificationMessage) -> bool:
        """發送應用內通知"""
        try:
            # 這裡應該將通知存儲到資料庫或快取中，供前端查詢
            logger.info(f"發送應用內通知: {message.title} to user {message.user_id}")
            
            # 模擬存儲
            await asyncio.sleep(0.1)
            return True
            
        except Exception as e:
            logger.error(f"發送應用內通知時發生錯誤: {str(e)}")
            return False
    
    def get_notification_statistics(self) -> Dict[str, Any]:
        """獲取通知統計"""
        try:
            total_messages = len(self.message_queue)
            sent_messages = len([msg for msg in self.message_queue if msg.status == "sent"])
            failed_messages = len([msg for msg in self.message_queue if msg.status == "failed"])
            pending_messages = len([msg for msg in self.message_queue if msg.status == "pending"])
            
            # 按通知類型統計
            type_stats = {}
            for msg in self.message_queue:
                msg_type = msg.notification_type.value
                if msg_type not in type_stats:
                    type_stats[msg_type] = {'total': 0, 'sent': 0, 'failed': 0}
                
                type_stats[msg_type]['total'] += 1
                if msg.status == "sent":
                    type_stats[msg_type]['sent'] += 1
                elif msg.status == "failed":
                    type_stats[msg_type]['failed'] += 1
            
            # 按用戶統計
            user_stats = {}
            for msg in self.message_queue:
                user_id = msg.user_id
                if user_id not in user_stats:
                    user_stats[user_id] = 0
                user_stats[user_id] += 1
            
            return {
                'total_messages': total_messages,
                'sent_messages': sent_messages,
                'failed_messages': failed_messages,
                'pending_messages': pending_messages,
                'success_rate': sent_messages / total_messages if total_messages > 0 else 0,
                'type_statistics': type_stats,
                'user_statistics': user_stats,
                'total_rules': sum(len(rules) for rules in self.notification_rules.values()),
                'active_users': len(self.notification_rules)
            }
            
        except Exception as e:
            logger.error(f"獲取通知統計時發生錯誤: {str(e)}")
            return {}
    
    def get_user_messages(
        self, 
        user_id: int, 
        limit: int = 50,
        status: str = None
    ) -> List[NotificationMessage]:
        """獲取用戶的通知訊息"""
        try:
            user_messages = [msg for msg in self.message_queue if msg.user_id == user_id]
            
            if status:
                user_messages = [msg for msg in user_messages if msg.status == status]
            
            # 按時間排序，最新的在前
            user_messages.sort(key=lambda x: x.created_at, reverse=True)
            
            return user_messages[:limit]
            
        except Exception as e:
            logger.error(f"獲取用戶訊息時發生錯誤: {str(e)}")
            return []


# 建立全域服務實例
signal_notification_service = SignalNotificationService()