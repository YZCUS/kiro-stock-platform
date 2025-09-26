"""
通知管理器 - 用于发送各种类型的警示和通知
支持多种通知渠道：邮件、Slack、Webhook 等
"""
import json
import logging
import os
import smtplib
import requests
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, List, Optional, Any
from enum import Enum

# 导入时区感知的时间工具
try:
    from .date_utils import get_taipei_now
except ImportError:
    # 备用方案
    import pendulum
    def get_taipei_now():
        return pendulum.now('Asia/Taipei')  


logger = logging.getLogger(__name__)


class NotificationLevel(Enum):
    """通知级别"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class NotificationChannel(Enum):
    """通知渠道"""
    EMAIL = "email"
    SLACK = "slack"
    WEBHOOK = "webhook"
    LOG = "log"


class NotificationManager:
    """通知管理器"""

    def __init__(self):
        """初始化通知管理器"""
        self.email_config = self._load_email_config()
        self.slack_config = self._load_slack_config()
        self.webhook_config = self._load_webhook_config()

        # 默认通知配置
        self.default_channels = {
            NotificationLevel.INFO: [NotificationChannel.LOG],
            NotificationLevel.WARNING: [NotificationChannel.LOG, NotificationChannel.EMAIL],
            NotificationLevel.ERROR: [NotificationChannel.LOG, NotificationChannel.EMAIL, NotificationChannel.SLACK],
            NotificationLevel.CRITICAL: [NotificationChannel.LOG, NotificationChannel.EMAIL, NotificationChannel.SLACK, NotificationChannel.WEBHOOK]
        }

    def _load_email_config(self) -> Dict:
        """加载邮件配置"""
        return {
            'smtp_server': os.getenv('SMTP_SERVER', 'localhost'),
            'smtp_port': int(os.getenv('SMTP_PORT', 587)),
            'smtp_username': os.getenv('SMTP_USERNAME'),
            'smtp_password': os.getenv('SMTP_PASSWORD'),
            'from_email': os.getenv('FROM_EMAIL', 'airflow@company.com'),
            'to_emails': os.getenv('ALERT_EMAILS', '').split(',') if os.getenv('ALERT_EMAILS') else [],
            'use_tls': os.getenv('SMTP_USE_TLS', 'true').lower() == 'true'
        }

    def _load_slack_config(self) -> Dict:
        """加载 Slack 配置"""
        return {
            'webhook_url': os.getenv('SLACK_WEBHOOK_URL'),
            'channel': os.getenv('SLACK_CHANNEL', '#airflow-alerts'),
            'username': os.getenv('SLACK_USERNAME', 'Airflow Bot'),
            'icon_emoji': os.getenv('SLACK_ICON_EMOJI', ':warning:')
        }

    def _load_webhook_config(self) -> Dict:
        """加载 Webhook 配置"""
        return {
            'url': os.getenv('ALERT_WEBHOOK_URL'),
            'timeout': int(os.getenv('WEBHOOK_TIMEOUT', 10)),
            'headers': json.loads(os.getenv('WEBHOOK_HEADERS', '{}'))
        }

    def send_notification(
        self,
        message: str,
        level: NotificationLevel,
        title: str = None,
        context: Dict = None,
        channels: List[NotificationChannel] = None
    ) -> Dict[str, bool]:
        """
        发送通知

        Args:
            message: 通知消息
            level: 通知级别
            title: 通知标题
            context: 附加上下文信息
            channels: 指定通知渠道，None 时使用默认配置

        Returns:
            Dict[str, bool]: 各渠道发送结果
        """
        results = {}

        # 确定通知渠道
        if channels is None:
            channels = self.default_channels.get(level, [NotificationChannel.LOG])

        # 准备通知内容
        notification_data = {
            'message': message,
            'level': level.value,
            'title': title or f"Airflow Alert - {level.value.upper()}",
            'timestamp': get_taipei_now().isoformat(),
            'context': context or {}
        }

        # 发送到各个渠道
        for channel in channels:
            try:
                if channel == NotificationChannel.EMAIL:
                    results['email'] = self._send_email(notification_data)
                elif channel == NotificationChannel.SLACK:
                    results['slack'] = self._send_slack(notification_data)
                elif channel == NotificationChannel.WEBHOOK:
                    results['webhook'] = self._send_webhook(notification_data)
                elif channel == NotificationChannel.LOG:
                    results['log'] = self._send_log(notification_data)
            except Exception as e:
                logger.error(f"发送通知到 {channel.value} 失败: {e}")
                results[channel.value] = False

        return results

    def _send_email(self, data: Dict) -> bool:
        """发送邮件通知"""
        if not self.email_config['to_emails'] or not self.email_config['smtp_username']:
            logger.warning("邮件配置不完整，跳过邮件通知")
            return False

        try:
            # 构建邮件内容
            msg = MIMEMultipart()
            msg['From'] = self.email_config['from_email']
            msg['To'] = ', '.join(self.email_config['to_emails'])
            msg['Subject'] = data['title']

            # 邮件正文
            body = self._format_email_body(data)
            msg.attach(MIMEText(body, 'html'))

            # 发送邮件
            with smtplib.SMTP(self.email_config['smtp_server'], self.email_config['smtp_port']) as server:
                if self.email_config['use_tls']:
                    server.starttls()

                if self.email_config['smtp_username'] and self.email_config['smtp_password']:
                    server.login(self.email_config['smtp_username'], self.email_config['smtp_password'])

                server.send_message(msg)

            logger.info(f"邮件通知发送成功: {data['title']}")
            return True

        except Exception as e:
            logger.error(f"发送邮件通知失败: {e}")
            return False

    def _send_slack(self, data: Dict) -> bool:
        """发送 Slack 通知"""
        if not self.slack_config['webhook_url']:
            logger.warning("Slack Webhook URL 未配置，跳过 Slack 通知")
            return False

        try:
            # 构建 Slack 消息
            color_map = {
                'info': '#36a64f',
                'warning': '#ff9900',
                'error': '#ff0000',
                'critical': '#8B0000'
            }

            payload = {
                'channel': self.slack_config['channel'],
                'username': self.slack_config['username'],
                'icon_emoji': self.slack_config['icon_emoji'],
                'attachments': [{
                    'color': color_map.get(data['level'], '#36a64f'),
                    'title': data['title'],
                    'text': data['message'],
                    'fields': [
                        {'title': 'Level', 'value': data['level'].upper(), 'short': True},
                        {'title': 'Timestamp', 'value': data['timestamp'], 'short': True}
                    ],
                    'footer': 'Airflow Storage Monitor',
                    'ts': int(get_taipei_now().timestamp())
                }]
            }

            # 添加上下文字段
            if data['context']:
                for key, value in data['context'].items():
                    payload['attachments'][0]['fields'].append({
                        'title': key.replace('_', ' ').title(),
                        'value': str(value),
                        'short': True
                    })

            # 发送请求
            response = requests.post(
                self.slack_config['webhook_url'],
                json=payload,
                timeout=10
            )
            response.raise_for_status()

            logger.info(f"Slack 通知发送成功: {data['title']}")
            return True

        except Exception as e:
            logger.error(f"发送 Slack 通知失败: {e}")
            return False

    def _send_webhook(self, data: Dict) -> bool:
        """发送 Webhook 通知"""
        if not self.webhook_config['url']:
            logger.warning("Webhook URL 未配置，跳过 Webhook 通知")
            return False

        try:
            # 发送 POST 请求
            response = requests.post(
                self.webhook_config['url'],
                json=data,
                headers=self.webhook_config['headers'],
                timeout=self.webhook_config['timeout']
            )
            response.raise_for_status()

            logger.info(f"Webhook 通知发送成功: {data['title']}")
            return True

        except Exception as e:
            logger.error(f"发送 Webhook 通知失败: {e}")
            return False

    def _send_log(self, data: Dict) -> bool:
        """记录日志通知"""
        try:
            log_level = data['level'].upper()
            message = f"[{data['title']}] {data['message']}"

            if data['context']:
                context_str = ', '.join([f"{k}={v}" for k, v in data['context'].items()])
                message += f" | Context: {context_str}"

            if log_level == 'INFO':
                logger.info(message)
            elif log_level == 'WARNING':
                logger.warning(message)
            elif log_level in ['ERROR', 'CRITICAL']:
                logger.error(message)

            return True

        except Exception as e:
            logger.error(f"记录日志通知失败: {e}")
            return False

    def _format_email_body(self, data: Dict) -> str:
        """格式化邮件正文"""
        context_html = ""
        if data['context']:
            context_rows = ""
            for key, value in data['context'].items():
                context_rows += f"""
                    <tr>
                        <td style="padding: 5px; border: 1px solid #ddd; font-weight: bold;">{key.replace('_', ' ').title()}</td>
                        <td style="padding: 5px; border: 1px solid #ddd;">{value}</td>
                    </tr>
                """
            context_html = f"""
                <h3>Context Information:</h3>
                <table style="border-collapse: collapse; width: 100%;">
                    {context_rows}
                </table>
            """

        level_colors = {
            'info': '#d4edda',
            'warning': '#fff3cd',
            'error': '#f8d7da',
            'critical': '#d1ecf1'
        }

        return f"""
        <html>
        <body style="font-family: Arial, sans-serif;">
            <div style="background-color: {level_colors.get(data['level'], '#f8f9fa')}; padding: 15px; border-radius: 5px; margin-bottom: 20px;">
                <h2 style="margin: 0; color: #333;">{data['title']}</h2>
                <p style="margin: 5px 0; color: #666;">Level: {data['level'].upper()}</p>
                <p style="margin: 5px 0; color: #666;">Time: {data['timestamp']}</p>
            </div>

            <div style="margin: 20px 0;">
                <h3>Message:</h3>
                <p style="background-color: #f8f9fa; padding: 10px; border-radius: 3px;">{data['message']}</p>
            </div>

            {context_html}

            <hr style="margin: 30px 0;">
            <p style="font-size: 12px; color: #666;">
                This alert was generated by Airflow Storage Monitor.<br>
                Please check the Airflow UI for more details.
            </p>
        </body>
        </html>
        """

    def send_storage_failure_alert(
        self,
        operation: str,
        reference_id: str = None,
        error: str = None,
        context: Dict = None
    ) -> Dict[str, bool]:
        """
        发送存储失败警报

        Args:
            operation: 操作类型 (store, retrieve, delete)
            reference_id: 数据引用ID
            error: 错误信息
            context: 附加上下文

        Returns:
            Dict[str, bool]: 发送结果
        """
        message = f"Redis storage operation '{operation}' failed"
        if reference_id:
            message += f" for reference ID: {reference_id}"
        if error:
            message += f". Error: {error}"

        alert_context = {
            'operation': operation,
            'reference_id': reference_id or 'N/A',
            'error': error or 'Unknown error',
            'component': 'XCom External Storage'
        }

        if context:
            alert_context.update(context)

        return self.send_notification(
            message=message,
            level=NotificationLevel.ERROR,
            title="Storage Operation Failed",
            context=alert_context
        )

    def send_redis_health_alert(self, health_data: Dict) -> Dict[str, bool]:
        """
        发送 Redis 健康状态警报

        Args:
            health_data: 健康检查数据

        Returns:
            Dict[str, bool]: 发送结果
        """
        if health_data.get('is_healthy', True):
            return {}  # 健康状态正常，不发送警报

        message = "Redis health check failed. External storage may be unavailable."

        return self.send_notification(
            message=message,
            level=NotificationLevel.CRITICAL,
            title="Redis Health Check Failed",
            context=health_data
        )

    def send_storage_capacity_alert(self, stats: Dict) -> Dict[str, bool]:
        """
        发送存储容量警报

        Args:
            stats: 存储统计数据

        Returns:
            Dict[str, bool]: 发送结果
        """
        total_size_mb = stats.get('total_size_mb', 0)
        threshold_mb = float(os.getenv('STORAGE_WARNING_THRESHOLD_MB', 1000))

        if total_size_mb < threshold_mb:
            return {}  # 容量正常，不发送警报

        message = f"External storage usage ({total_size_mb} MB) exceeds warning threshold ({threshold_mb} MB)"

        level = NotificationLevel.WARNING
        if total_size_mb > threshold_mb * 2:
            level = NotificationLevel.ERROR
            message = f"External storage usage ({total_size_mb} MB) is critically high"

        return self.send_notification(
            message=message,
            level=level,
            title="Storage Capacity Warning",
            context=stats
        )


# 全局实例
_notification_manager = None


def get_notification_manager() -> NotificationManager:
    """获取全局通知管理器实例"""
    global _notification_manager
    if _notification_manager is None:
        _notification_manager = NotificationManager()
    return _notification_manager


def send_storage_alert(
    operation: str,
    reference_id: str = None,
    error: str = None,
    context: Dict = None
) -> Dict[str, bool]:
    """
    发送存储警报的便捷函数

    Args:
        operation: 操作类型
        reference_id: 数据引用ID
        error: 错误信息
        context: 附加上下文

    Returns:
        Dict[str, bool]: 发送结果
    """
    notification_manager = get_notification_manager()
    return notification_manager.send_storage_failure_alert(operation, reference_id, error, context)