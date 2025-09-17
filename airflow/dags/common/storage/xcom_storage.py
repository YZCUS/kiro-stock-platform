"""
XCom 外部存儲管理器
解決 XCom 48KB 限制問題
"""
import json
import uuid
import redis
import logging
from typing import Any, Dict, Optional
from datetime import datetime, timedelta
import os

logger = logging.getLogger(__name__)


class XComStorageManager:
    """XCom 外部存儲管理器"""

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

        try:
            self.redis_client = redis.from_url(self.redis_url)
            # 測試連接
            self.redis_client.ping()
            logger.info("XCom 外部存儲初始化成功")
        except Exception as e:
            logger.error(f"Redis 連接失敗: {e}")
            self.redis_client = None

    def store_data(self, data: Any, reference_id: str = None) -> str:
        """
        存儲大數據到外部存儲

        Args:
            data: 要存儲的數據
            reference_id: 可選的自定義ID

        Returns:
            str: 數據引用ID
        """
        if not self.redis_client:
            raise RuntimeError("Redis 客戶端未初始化")

        # 生成唯一ID
        ref_id = reference_id or f"data_{uuid.uuid4().hex}"

        try:
            # 序列化數據
            serialized_data = json.dumps(data, ensure_ascii=False, default=str)

            # 檢查數據大小
            data_size = len(serialized_data.encode('utf-8'))
            logger.info(f"存儲數據大小: {data_size} bytes")

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
                'created_at': datetime.now().isoformat(),
                'data_size': data_size,
                'ttl_seconds': self.ttl_seconds
            }
            metadata_key = f"{storage_key}:meta"
            self.redis_client.setex(
                metadata_key,
                self.ttl_seconds,
                json.dumps(metadata)
            )

            logger.info(f"數據已存儲到外部存儲，引用ID: {ref_id}")
            return ref_id

        except Exception as e:
            logger.error(f"存儲數據失敗: {e}")
            raise

    def retrieve_data(self, reference_id: str) -> Any:
        """
        從外部存儲檢索數據

        Args:
            reference_id: 數據引用ID

        Returns:
            Any: 檢索到的數據
        """
        if not self.redis_client:
            raise RuntimeError("Redis 客戶端未初始化")

        try:
            storage_key = f"{self.key_prefix}{reference_id}"

            # 檢索數據
            serialized_data = self.redis_client.get(storage_key)

            if serialized_data is None:
                raise ValueError(f"無法找到引用ID為 {reference_id} 的數據")

            # 反序列化數據
            data = json.loads(serialized_data.decode('utf-8'))

            logger.info(f"成功檢索數據，引用ID: {reference_id}")
            return data

        except Exception as e:
            logger.error(f"檢索數據失敗: {e}")
            raise

    def delete_data(self, reference_id: str) -> bool:
        """
        刪除外部存儲的數據

        Args:
            reference_id: 數據引用ID

        Returns:
            bool: 是否成功刪除
        """
        if not self.redis_client:
            return False

        try:
            storage_key = f"{self.key_prefix}{reference_id}"
            metadata_key = f"{storage_key}:meta"

            # 刪除數據和元數據
            deleted_count = self.redis_client.delete(storage_key, metadata_key)

            logger.info(f"刪除數據，引用ID: {reference_id}, 刪除項目: {deleted_count}")
            return deleted_count > 0

        except Exception as e:
            logger.error(f"刪除數據失敗: {e}")
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
            for key in data_keys:
                size = self.redis_client.memory_usage(key)
                if size:
                    total_size += size

            return {
                'total_items': len(data_keys),
                'total_size_bytes': total_size,
                'total_size_mb': round(total_size / (1024 * 1024), 2),
                'metadata_items': len(meta_keys),
                'redis_connected': True
            }

        except Exception as e:
            logger.error(f"獲取存儲統計失敗: {e}")
            return {'error': str(e)}


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