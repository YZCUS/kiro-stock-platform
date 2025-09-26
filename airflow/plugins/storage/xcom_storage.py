"""
XCom 外部存儲管理器
解決 XCom 48KB 限制問題
"""
import json
import uuid
import redis
import logging
import time
from typing import Any, Dict, Optional, List
from datetime import datetime, timedelta
import os
from contextlib import contextmanager

# 导入时区感知的时间工具
try:
    from ..utils.date_utils import get_taipei_now
    import pendulum  # 用于时间戳转换
except ImportError:
    # 备用方案：如果导入失败，使用 pendulum
    import pendulum
    def get_taipei_now():
        return pendulum.now('Asia/Taipei')

logger = logging.getLogger(__name__)

# 导入通知管理器
try:
    from ..utils.notification_manager import get_notification_manager
    NOTIFICATIONS_ENABLED = True
except ImportError:
    logger.warning("通知管理器未找到，将禁用通知功能")
    NOTIFICATIONS_ENABLED = False
    get_notification_manager = lambda: None


class XComStorageManager:
    """XCom 外部存儲管理器 - 增强版，包含监控和警示功能"""

    def __init__(self, redis_url: str = None, ttl_hours: int = 24):
        """
        初始化存儲管理器

        Args:
            redis_url: Redis 連接URL
            ttl_hours: 數據過期時間（小時）
        """
        self.redis_url = redis_url or os.getenv('REDIS_URL', 'redis://localhost:6379/1')
        self.ttl_seconds = ttl_hours * 3600
        self.key_prefix = "airflow:xcom:external:"
        self.metrics_key_prefix = "airflow:xcom:metrics:"

        # 监控配置
        self.enable_monitoring = os.getenv('XCOM_STORAGE_MONITORING', 'true').lower() == 'true'
        self.health_check_interval = int(os.getenv('REDIS_HEALTH_CHECK_INTERVAL', 300))  # 5分钟
        self.last_health_check = 0
        self.consecutive_failures = 0
        self.max_consecutive_failures = int(os.getenv('MAX_REDIS_FAILURES', 3))

        # 通知管理器
        self.notification_manager = get_notification_manager() if NOTIFICATIONS_ENABLED else None

        try:
            self.redis_client = redis.from_url(self.redis_url)
            # 測試連接
            self.redis_client.ping()
            logger.info("XCom 外部存儲初始化成功")
            self.consecutive_failures = 0

            # 记录初始化指标
            if self.enable_monitoring:
                self._record_metric('initialization', {'status': 'success', 'timestamp': get_taipei_now().isoformat()})

        except Exception as e:
            logger.error(f"Redis 連接失敗: {e}")
            self.redis_client = None
            self.consecutive_failures += 1

            # 发送初始化失败警报
            if self.notification_manager:
                self.notification_manager.send_storage_failure_alert(
                    operation='initialization',
                    error=str(e),
                    context={'redis_url': self.redis_url}
                )

    @contextmanager
    def _performance_monitor(self, operation: str, reference_id: str = None):
        """性能监控上下文管理器"""
        start_time = time.time()
        operation_success = False

        try:
            yield
            operation_success = True
        except Exception as e:
            # 记录失败指标
            if self.enable_monitoring:
                self._record_metric('operation_failure', {
                    'operation': operation,
                    'reference_id': reference_id,
                    'error': str(e),
                    'timestamp': get_taipei_now().isoformat()
                })

            # 发送失败通知
            if self.notification_manager:
                self.notification_manager.send_storage_failure_alert(
                    operation=operation,
                    reference_id=reference_id,
                    error=str(e),
                    context={'duration_seconds': time.time() - start_time}
                )

            self.consecutive_failures += 1
            raise
        finally:
            duration = time.time() - start_time

            # 记录性能指标
            if self.enable_monitoring:
                self._record_metric('operation_performance', {
                    'operation': operation,
                    'reference_id': reference_id,
                    'duration_seconds': duration,
                    'success': operation_success,
                    'timestamp': get_taipei_now().isoformat()
                })

            # 重置失败计数器（如果操作成功）
            if operation_success:
                self.consecutive_failures = 0

    def _record_metric(self, metric_type: str, data: Dict) -> None:
        """记录监控指标"""
        if not self.redis_client or not self.enable_monitoring:
            return

        try:
            metric_key = f"{self.metrics_key_prefix}{metric_type}:{get_taipei_now().strftime('%Y%m%d')}"
            metric_data = {
                'type': metric_type,
                'data': data,
                'recorded_at': get_taipei_now().isoformat()
            }

            # 使用 Redis List 存储指标（带过期时间）
            self.redis_client.lpush(metric_key, json.dumps(metric_data))
            self.redis_client.expire(metric_key, 7 * 24 * 3600)  # 保留7天

            # 限制列表长度
            self.redis_client.ltrim(metric_key, 0, 999)  # 保留最新1000条记录

        except Exception as e:
            logger.warning(f"记录监控指标失败: {e}")

    def check_redis_health(self) -> Dict[str, Any]:
        """检查 Redis 健康状态"""
        health_data = {
            'is_healthy': False,
            'last_check': get_taipei_now().isoformat(),
            'consecutive_failures': self.consecutive_failures,
            'error': None
        }

        try:
            if not self.redis_client:
                health_data['error'] = 'Redis client not initialized'
                return health_data

            # 执行健康检查
            start_time = time.time()
            self.redis_client.ping()
            response_time = time.time() - start_time

            # 获取 Redis 信息
            redis_info = self.redis_client.info()

            health_data.update({
                'is_healthy': True,
                'response_time_seconds': response_time,
                'redis_version': redis_info.get('redis_version'),
                'used_memory_human': redis_info.get('used_memory_human'),
                'connected_clients': redis_info.get('connected_clients'),
                'total_commands_processed': redis_info.get('total_commands_processed'),
                'uptime_in_seconds': redis_info.get('uptime_in_seconds')
            })

            # 重置失败计数
            self.consecutive_failures = 0

        except Exception as e:
            health_data['error'] = str(e)
            self.consecutive_failures += 1
            logger.error(f"Redis 健康检查失败: {e}")

        # 记录健康检查指标
        if self.enable_monitoring:
            self._record_metric('health_check', health_data)

        # 发送健康警报（如果需要）
        if not health_data['is_healthy'] and self.notification_manager:
            self.notification_manager.send_redis_health_alert(health_data)

        self.last_health_check = time.time()
        return health_data

    def _ensure_redis_health(self) -> None:
        """确保 Redis 连接健康"""
        current_time = time.time()

        # 检查是否需要执行健康检查
        if current_time - self.last_health_check < self.health_check_interval:
            return

        # 检查连续失败次数
        if self.consecutive_failures >= self.max_consecutive_failures:
            logger.warning(f"连续失败次数 ({self.consecutive_failures}) 达到阈值，尝试重新连接 Redis")

            try:
                self.redis_client = redis.from_url(self.redis_url)
                self.redis_client.ping()
                logger.info("Redis 重连成功")
                self.consecutive_failures = 0
            except Exception as e:
                logger.error(f"Redis 重连失败: {e}")

        # 执行健康检查
        self.check_redis_health()

    def store_data(self, data: Any, reference_id: str = None) -> str:
        """
        存儲大數據到外部存儲

        Args:
            data: 要存儲的數據
            reference_id: 可選的自定義ID

        Returns:
            str: 數據引用ID
        """
        # 确保 Redis 健康
        self._ensure_redis_health()

        if not self.redis_client:
            raise RuntimeError("Redis 客戶端未初始化")

        # 生成唯一ID
        ref_id = reference_id or f"data_{uuid.uuid4().hex}"

        with self._performance_monitor('store', ref_id):
            # 序列化數據
            serialized_data = json.dumps(data, ensure_ascii=False, default=str)

            # 檢查數據大小
            data_size = len(serialized_data.encode('utf-8'))
            logger.info(f"存儲數據大小: {data_size} bytes")

            # 检查数据大小警告阈值
            size_warning_threshold = int(os.getenv('STORAGE_SIZE_WARNING_MB', 10)) * 1024 * 1024
            if data_size > size_warning_threshold:
                logger.warning(f"存储数据大小 ({data_size} bytes) 超过警告阈值")
                if self.notification_manager:
                    self.notification_manager.send_notification(
                        message=f"Large data storage detected: {data_size} bytes for reference {ref_id}",
                        level=self.notification_manager.NotificationLevel.WARNING,
                        title="Large Data Storage Warning",
                        context={'reference_id': ref_id, 'data_size_bytes': data_size}
                    )

            # 構建存儲鍵
            storage_key = f"{self.key_prefix}{ref_id}"

            # 存儲到 Redis
            self.redis_client.setex(
                storage_key,
                self.ttl_seconds,
                serialized_data
            )

            # 存儲元數據
            metadata = {
                'created_at': get_taipei_now().isoformat(),
                'data_size': data_size,
                'ttl_seconds': self.ttl_seconds,
                'reference_id': ref_id
            }
            metadata_key = f"{storage_key}:meta"
            self.redis_client.setex(
                metadata_key,
                self.ttl_seconds,
                json.dumps(metadata)
            )

            logger.info(f"數據已存儲到外部存儲，引用ID: {ref_id}")

            # 记录存储成功指标
            if self.enable_monitoring:
                self._record_metric('store_success', {
                    'reference_id': ref_id,
                    'data_size': data_size,
                    'timestamp': get_taipei_now().isoformat()
                })

            return ref_id

    def retrieve_data(self, reference_id: str) -> Any:
        """
        從外部存儲檢索數據

        Args:
            reference_id: 數據引用ID

        Returns:
            Any: 檢索到的數據
        """
        # 确保 Redis 健康
        self._ensure_redis_health()

        if not self.redis_client:
            raise RuntimeError("Redis 客戶端未初始化")

        with self._performance_monitor('retrieve', reference_id):
            storage_key = f"{self.key_prefix}{reference_id}"

            # 檢索數據
            serialized_data = self.redis_client.get(storage_key)

            if serialized_data is None:
                # 记录数据不存在的情况
                if self.enable_monitoring:
                    self._record_metric('data_not_found', {
                        'reference_id': reference_id,
                        'timestamp': get_taipei_now().isoformat()
                    })
                raise ValueError(f"無法找到引用ID為 {reference_id} 的數據")

            # 反序列化數據
            data = json.loads(serialized_data.decode('utf-8'))

            logger.info(f"成功檢索數據，引用ID: {reference_id}")

            # 记录检索成功指标
            if self.enable_monitoring:
                self._record_metric('retrieve_success', {
                    'reference_id': reference_id,
                    'data_size': len(serialized_data),
                    'timestamp': get_taipei_now().isoformat()
                })

            return data

    def delete_data(self, reference_id: str) -> bool:
        """
        刪除外部存儲的數據

        Args:
            reference_id: 數據引用ID

        Returns:
            bool: 是否成功刪除
        """
        # 确保 Redis 健康
        self._ensure_redis_health()

        if not self.redis_client:
            return False

        try:
            with self._performance_monitor('delete', reference_id):
                storage_key = f"{self.key_prefix}{reference_id}"
                metadata_key = f"{storage_key}:meta"

                # 刪除數據和元數據
                deleted_count = self.redis_client.delete(storage_key, metadata_key)

                logger.info(f"刪除數據，引用ID: {reference_id}, 刪除項目: {deleted_count}")

                # 记录删除指标
                if self.enable_monitoring:
                    self._record_metric('delete_success' if deleted_count > 0 else 'delete_not_found', {
                        'reference_id': reference_id,
                        'deleted_count': deleted_count,
                        'timestamp': get_taipei_now().isoformat()
                    })

                return deleted_count > 0

        except Exception as e:
            logger.error(f"刪除數據失敗: {e}")
            # 记录删除失败指标
            if self.enable_monitoring:
                self._record_metric('delete_failure', {
                    'reference_id': reference_id,
                    'error': str(e),
                    'timestamp': get_taipei_now().isoformat()
                })
            return False

    def get_metadata(self, reference_id: str) -> Optional[Dict]:
        """
        獲取數據元數據

        Args:
            reference_id: 數據引用ID

        Returns:
            Dict: 元數據字典
        """
        if not self.redis_client:
            return None

        try:
            storage_key = f"{self.key_prefix}{reference_id}"
            metadata_key = f"{storage_key}:meta"

            metadata_str = self.redis_client.get(metadata_key)
            if metadata_str:
                return json.loads(metadata_str.decode('utf-8'))

            return None

        except Exception as e:
            logger.error(f"獲取元數據失敗: {e}")
            return None

    def cleanup_expired_data(self) -> int:
        """
        清理過期數據

        Returns:
            int: 清理的數據項目數量
        """
        if not self.redis_client:
            return 0

        try:
            # 獲取所有存儲鍵
            pattern = f"{self.key_prefix}*"
            keys = self.redis_client.keys(pattern)

            # 過濾出數據鍵（排除元數據鍵）
            data_keys = [key for key in keys if not key.decode().endswith(':meta')]

            cleanup_count = 0
            for key in data_keys:
                ttl = self.redis_client.ttl(key)
                if ttl == -2:  # 鍵已過期
                    cleanup_count += 1

            logger.info(f"清理過期數據完成，清理項目: {cleanup_count}")
            return cleanup_count

        except Exception as e:
            logger.error(f"清理過期數據失敗: {e}")
            return 0

    def get_storage_stats(self) -> Dict:
        """
        獲取存儲統計信息

        Returns:
            Dict: 統計信息
        """
        if not self.redis_client:
            return {'error': 'Redis 客戶端未初始化'}

        try:
            pattern = f"{self.key_prefix}*"
            all_keys = self.redis_client.keys(pattern)

            # 分類鍵
            data_keys = [key for key in all_keys if not key.decode().endswith(':meta')]
            meta_keys = [key for key in all_keys if key.decode().endswith(':meta')]

            total_size = 0
            expired_count = 0
            size_distribution = {'small': 0, 'medium': 0, 'large': 0}  # <1MB, 1-10MB, >10MB

            for key in data_keys:
                try:
                    size = self.redis_client.memory_usage(key)
                    if size:
                        total_size += size

                        # 大小分布统计
                        if size < 1024 * 1024:  # <1MB
                            size_distribution['small'] += 1
                        elif size < 10 * 1024 * 1024:  # 1-10MB
                            size_distribution['medium'] += 1
                        else:  # >10MB
                            size_distribution['large'] += 1

                    # 检查过期状态
                    ttl = self.redis_client.ttl(key)
                    if ttl == -2:  # 已过期
                        expired_count += 1

                except Exception as e:
                    logger.warning(f"检查键 {key} 失败: {e}")

            stats = {
                'total_items': len(data_keys),
                'total_size_bytes': total_size,
                'total_size_mb': round(total_size / (1024 * 1024), 2),
                'metadata_items': len(meta_keys),
                'expired_items': expired_count,
                'size_distribution': size_distribution,
                'redis_connected': True,
                'consecutive_failures': self.consecutive_failures,
                'last_health_check': pendulum.from_timestamp(self.last_health_check, 'Asia/Taipei').isoformat() if self.last_health_check else None,
                'monitoring_enabled': self.enable_monitoring,
                'check_timestamp': get_taipei_now().isoformat()
            }

            # 发送容量警报（如果需要）
            if self.notification_manager:
                self.notification_manager.send_storage_capacity_alert(stats)

            return stats

        except Exception as e:
            logger.error(f"獲取存儲統計失敗: {e}")
            return {'error': str(e), 'check_timestamp': get_taipei_now().isoformat()}


    def get_metrics_summary(self, days: int = 7) -> Dict:
        """
        获取指标汇总信息

        Args:
            days: 查询天数

        Returns:
            Dict: 指标汇总
        """
        if not self.redis_client or not self.enable_monitoring:
            return {'error': '监控未启用或 Redis 未连接'}

        try:
            summary = {
                'period_days': days,
                'operations': {'store': 0, 'retrieve': 0, 'delete': 0},
                'failures': {'store': 0, 'retrieve': 0, 'delete': 0},
                'performance': {'avg_store_time': 0, 'avg_retrieve_time': 0, 'avg_delete_time': 0},
                'data_volume': {'total_stored_mb': 0, 'avg_item_size_kb': 0},
                'health_checks': {'total': 0, 'failed': 0, 'avg_response_time': 0}
            }

            # 查询指定天数的数据
            end_date = get_taipei_now()
            for i in range(days):
                date_str = (end_date - timedelta(days=i)).strftime('%Y%m%d')

                # 获取各类指标
                for metric_type in ['operation_performance', 'operation_failure', 'health_check', 'store_success']:
                    metric_key = f"{self.metrics_key_prefix}{metric_type}:{date_str}"

                    try:
                        metrics_data = self.redis_client.lrange(metric_key, 0, -1)
                        for metric_json in metrics_data:
                            metric = json.loads(metric_json.decode('utf-8'))
                            self._aggregate_metric(summary, metric)
                    except Exception as e:
                        logger.warning(f"获取指标 {metric_key} 失败: {e}")

            # 计算平均值
            self._calculate_averages(summary)

            return summary

        except Exception as e:
            logger.error(f"获取指标汇总失败: {e}")
            return {'error': str(e)}

    def _aggregate_metric(self, summary: Dict, metric: Dict) -> None:
        """聚合单个指标数据"""
        metric_data = metric.get('data', {})
        metric_type = metric.get('type')

        if metric_type == 'operation_performance':
            operation = metric_data.get('operation')
            if operation in summary['operations']:
                summary['operations'][operation] += 1

                # 记录性能数据
                duration = metric_data.get('duration_seconds', 0)
                perf_key = f'avg_{operation}_time'
                if perf_key not in summary['_temp_performance']:
                    summary['_temp_performance'] = {}
                if perf_key not in summary['_temp_performance']:
                    summary['_temp_performance'][perf_key] = []
                summary['_temp_performance'][perf_key].append(duration)

        elif metric_type == 'operation_failure':
            operation = metric_data.get('operation')
            if operation in summary['failures']:
                summary['failures'][operation] += 1

        elif metric_type == 'store_success':
            data_size = metric_data.get('data_size', 0)
            if '_temp_sizes' not in summary:
                summary['_temp_sizes'] = []
            summary['_temp_sizes'].append(data_size)

        elif metric_type == 'health_check':
            summary['health_checks']['total'] += 1
            if not metric_data.get('is_healthy', True):
                summary['health_checks']['failed'] += 1

            response_time = metric_data.get('response_time_seconds', 0)
            if '_temp_response_times' not in summary:
                summary['_temp_response_times'] = []
            if response_time > 0:
                summary['_temp_response_times'].append(response_time)

    def _calculate_averages(self, summary: Dict) -> None:
        """计算平均值"""
        # 计算性能平均值
        if '_temp_performance' in summary:
            for key, times in summary['_temp_performance'].items():
                if times:
                    summary['performance'][key] = round(sum(times) / len(times), 3)
            del summary['_temp_performance']

        # 计算数据大小平均值
        if '_temp_sizes' in summary:
            sizes = summary['_temp_sizes']
            if sizes:
                total_mb = sum(sizes) / (1024 * 1024)
                avg_kb = (sum(sizes) / len(sizes)) / 1024
                summary['data_volume']['total_stored_mb'] = round(total_mb, 2)
                summary['data_volume']['avg_item_size_kb'] = round(avg_kb, 2)
            del summary['_temp_sizes']

        # 计算健康检查平均响应时间
        if '_temp_response_times' in summary:
            times = summary['_temp_response_times']
            if times:
                summary['health_checks']['avg_response_time'] = round(sum(times) / len(times), 3)
            del summary['_temp_response_times']

    def cleanup_metrics(self, older_than_days: int = 30) -> int:
        """
        清理过旧的指标数据

        Args:
            older_than_days: 清理多少天前的数据

        Returns:
            int: 清理的数据项数
        """
        if not self.redis_client or not self.enable_monitoring:
            return 0

        try:
            cleanup_count = 0
            cutoff_date = get_taipei_now() - timedelta(days=older_than_days)

            # 查找所有指标键
            pattern = f"{self.metrics_key_prefix}*"
            metric_keys = self.redis_client.keys(pattern)

            for key in metric_keys:
                key_str = key.decode('utf-8')
                # 提取日期部分
                date_part = key_str.split(':')[-1]
                try:
                    # 将字符串日期转换为时区感知的日期
                    key_date = get_taipei_now().replace(
                        year=int(date_part[:4]),
                        month=int(date_part[4:6]),
                        day=int(date_part[6:8]),
                        hour=0, minute=0, second=0, microsecond=0
                    )
                    if key_date < cutoff_date:
                        self.redis_client.delete(key)
                        cleanup_count += 1
                except ValueError:
                    # 非日期格式的键，跳过
                    continue

            logger.info(f"清理过旧指标数据完成，清理项目: {cleanup_count}")
            return cleanup_count

        except Exception as e:
            logger.error(f"清理指标数据失败: {e}")
            return 0


# 全局實例
_storage_manager = None


def get_storage_manager() -> XComStorageManager:
    """獲取全局存儲管理器實例"""
    global _storage_manager
    if _storage_manager is None:
        _storage_manager = XComStorageManager()
    return _storage_manager


def store_large_data(data: Any, reference_id: str = None) -> str:
    """
    存儲大數據的便捷函數

    Args:
        data: 要存儲的數據
        reference_id: 可選的自定義ID

    Returns:
        str: 數據引用ID
    """
    storage_manager = get_storage_manager()
    return storage_manager.store_data(data, reference_id)


def retrieve_large_data(reference_id: str) -> Any:
    """
    檢索大數據的便捷函數

    Args:
        reference_id: 數據引用ID

    Returns:
        Any: 檢索到的數據
    """
    storage_manager = get_storage_manager()
    return storage_manager.retrieve_data(reference_id)


def cleanup_large_data(reference_id: str) -> bool:
    """
    清理大數據的便捷函數

    Args:
        reference_id: 數據引用ID

    Returns:
        bool: 是否成功刪除
    """
    storage_manager = get_storage_manager()
    return storage_manager.delete_data(reference_id)