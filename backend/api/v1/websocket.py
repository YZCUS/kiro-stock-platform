"""
WebSocket 即時數據服務 - 支援多Worker環境
"""
from fastapi import WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, List, Set, Optional, Any
import json
import asyncio
import logging
from datetime import datetime, date

from core.database import get_db_session
from models.repositories.crud_stock import stock_crud
from models.repositories.crud_price_history import price_history_crud
from models.repositories.crud_technical_indicator import technical_indicator_crud
from models.repositories.crud_trading_signal import trading_signal_crud
from services.infrastructure.websocket_manager import enhanced_manager
from services.infrastructure.redis_pubsub import redis_broadcaster

logger = logging.getLogger(__name__)

# 使用增強版管理器替代原有的全局實例
manager = enhanced_manager


class WebSocketService:
    """WebSocket 服務類"""
    
    @staticmethod
    async def handle_message(websocket: WebSocket, message: dict, db: AsyncSession):
        """處理客戶端消息"""
        try:
            message_type = message.get("type")
            data = message.get("data", {})
            
            if message_type == "subscribe_stock":
                stock_id = data.get("stock_id")
                if stock_id:
                    await manager.subscribe_to_stock(websocket, stock_id)
                    # 發送初始數據
                    await WebSocketService.send_initial_stock_data(websocket, stock_id, db)
                    
            elif message_type == "unsubscribe_stock":
                stock_id = data.get("stock_id")
                if stock_id:
                    await manager.unsubscribe_from_stock(websocket, stock_id)
                    
            elif message_type == "subscribe_global":
                await manager.subscribe_to_global(websocket)
                
            elif message_type == "unsubscribe_global":
                await manager.unsubscribe_from_global(websocket)
                
            elif message_type == "get_stats":
                stats = manager.get_connection_stats()
                await manager.send_personal_message({
                    "type": "stats",
                    "data": stats
                }, websocket)
                
            elif message_type == "ping":
                await manager.send_personal_message({
                    "type": "pong",
                    "timestamp": datetime.now().isoformat()
                }, websocket)
                
            else:
                await manager.send_personal_message({
                    "type": "error",
                    "message": f"未知的消息類型: {message_type}"
                }, websocket)
                
        except Exception as e:
            logger.error(f"處理WebSocket消息失敗: {e}")
            await manager.send_personal_message({
                "type": "error",
                "message": str(e)
            }, websocket)
    
    @staticmethod
    async def send_initial_stock_data(websocket: WebSocket, stock_id: int, db: AsyncSession):
        """發送初始股票數據"""
        try:
            # 取得股票基本資訊
            stock = await stock_crud.get(db, stock_id)
            if not stock:
                await manager.send_personal_message({
                    "type": "error",
                    "message": f"股票不存在: {stock_id}"
                }, websocket)
                return
            
            # 取得最新價格數據
            latest_prices = await price_history_crud.get_by_stock(db, stock_id, limit=100)
            
            # 取得最新技術指標
            latest_indicators = await technical_indicator_crud.get_by_stock(db, stock_id, limit=50)
            
            # 取得最新交易信號
            latest_signals = await trading_signal_crud.get_by_stock(db, stock_id, limit=10)
            
            # 格式化數據
            price_data = [
                {
                    "date": price.date.isoformat(),
                    "open": float(price.open_price),
                    "high": float(price.high_price),
                    "low": float(price.low_price),
                    "close": float(price.close_price),
                    "volume": price.volume
                }
                for price in latest_prices
            ]
            
            indicators_data = {}
            for indicator in latest_indicators:
                indicator_type = indicator.indicator_type
                if indicator_type not in indicators_data:
                    indicators_data[indicator_type] = []
                
                indicators_data[indicator_type].append({
                    "date": indicator.date.isoformat(),
                    "value": float(indicator.value),
                    "parameters": indicator.parameters
                })
            
            signals_data = [
                {
                    "id": signal.id,
                    "signal_type": signal.signal_type,
                    "price": float(signal.price),
                    "confidence": float(signal.confidence),
                    "date": signal.date.isoformat(),
                    "description": signal.description
                }
                for signal in latest_signals
            ]
            
            # 發送初始數據
            await manager.send_personal_message({
                "type": "initial_data",
                "data": {
                    "stock": {
                        "id": stock.id,
                        "symbol": stock.symbol,
                        "market": stock.market,
                        "name": stock.name
                    },
                    "prices": price_data,
                    "indicators": indicators_data,
                    "signals": signals_data,
                    "timestamp": datetime.now().isoformat()
                }
            }, websocket)
            
        except Exception as e:
            logger.error(f"發送初始數據失敗: {e}")
            await manager.send_personal_message({
                "type": "error",
                "message": f"取得初始數據失敗: {str(e)}"
            }, websocket)
    
    @staticmethod
    async def broadcast_price_update(stock_id: int, price_data: dict):
        """廣播價格更新 - 使用Redis多Worker支援"""
        await redis_broadcaster.publish_price_update(stock_id, price_data)

    @staticmethod
    async def broadcast_indicator_update(stock_id: int, indicator_data: dict):
        """廣播技術指標更新 - 使用Redis多Worker支援"""
        await redis_broadcaster.publish_indicator_update(stock_id, indicator_data)

    @staticmethod
    async def broadcast_signal_update(stock_id: int, signal_data: dict):
        """廣播交易信號更新 - 使用Redis多Worker支援"""
        await redis_broadcaster.publish_signal_update(stock_id, signal_data)

    @staticmethod
    async def broadcast_market_status(status_data: dict):
        """廣播市場狀態更新 - 使用Redis多Worker支援"""
        await redis_broadcaster.publish_market_status(status_data)


# WebSocket 端點
async def websocket_endpoint(websocket: WebSocket, stock_id: Optional[int] = None, client_id: Optional[str] = None):
    """
    WebSocket 端點處理函數 - 支援多Worker環境和降級模式
    """
    # 檢查服務狀態
    if websocket_service_state.degraded_mode:
        logger.warning(f"WebSocket服務處於降級模式，拒絕新連接: {client_id}")
        await websocket.close(code=1013, reason="Service temporarily unavailable")
        return

    # 取得資料庫連接
    db_gen = get_db_session()
    db = await db_gen.__anext__()

    try:
        # 確保管理器已初始化
        if not websocket_service_state.is_initialized:
            logger.error("WebSocket管理器未初始化，嘗試重新初始化...")
            success = await initialize_websocket_manager()
            if not success:
                await websocket.close(code=1011, reason="Service initialization failed")
                return

        # 檢查Redis廣播器連接
        if not redis_broadcaster.is_connected:
            try:
                await manager.initialize()
            except Exception as init_error:
                logger.error(f"初始化WebSocket管理器失敗: {init_error}")
                websocket_service_state.set_degraded_mode("管理器初始化失敗")
                await websocket.close(code=1011, reason="Service unavailable")
                return

        # 建立連接
        await manager.connect(websocket, client_id)

        # 如果指定了股票ID，自動訂閱
        if stock_id:
            await manager.subscribe_to_stock(websocket, stock_id)
            await WebSocketService.send_initial_stock_data(websocket, stock_id, db)

        # 發送歡迎消息
        connection_info = manager.active_connections.get(websocket, {})
        await manager.send_personal_message({
            "type": "welcome",
            "message": "WebSocket連接成功",
            "client_id": connection_info.get("client_id"),
            "worker_id": connection_info.get("worker_id"),
            "timestamp": datetime.now().isoformat()
        }, websocket)

        # 消息循環
        while True:
            try:
                # 接收消息
                data = await websocket.receive_text()
                message = json.loads(data)

                # 處理消息
                await WebSocketService.handle_message(websocket, message, db)

            except WebSocketDisconnect:
                logger.info(f"WebSocket客戶端正常斷開連接: {client_id}")
                break
            except json.JSONDecodeError as e:
                logger.warning(f"WebSocket收到無效JSON: {str(e)}")
                try:
                    await manager.send_personal_message({
                        "type": "error",
                        "message": f"JSON格式錯誤: {str(e)}"
                    }, websocket)
                except Exception:
                    # 如果無法發送錯誤消息，直接斷開連接
                    logger.error("無法發送錯誤消息，斷開連接")
                    break
            except ConnectionResetError:
                logger.info(f"WebSocket連接被重置: {client_id}")
                break
            except asyncio.CancelledError:
                logger.info(f"WebSocket任務被取消: {client_id}")
                break
            except Exception as e:
                logger.error(f"WebSocket處理消息時發生未預期錯誤: {e}")
                try:
                    await manager.send_personal_message({
                        "type": "error",
                        "message": f"處理消息失敗: {str(e)}"
                    }, websocket)
                    # 對於嚴重錯誤，考慮斷開連接
                    if isinstance(e, (OSError, IOError)):
                        logger.error("網絡錯誤，斷開WebSocket連接")
                        break
                except Exception as send_error:
                    logger.error(f"無法發送錯誤消息，斷開連接: {send_error}")
                    break

    except WebSocketDisconnect:
        logger.info(f"WebSocket連接已斷開: {client_id}")
    except Exception as e:
        logger.error(f"WebSocket連接發生嚴重錯誤: {e}")
        # 記錄詳細錯誤信息用於調試
        import traceback
        logger.error(f"WebSocket錯誤堆棧: {traceback.format_exc()}")

    finally:
        # 確保資源清理
        try:
            # 清理WebSocket連接
            await manager.disconnect(websocket)
            logger.debug(f"WebSocket連接已清理: {client_id}")
        except Exception as cleanup_error:
            logger.error(f"清理WebSocket連接時發生錯誤: {cleanup_error}")

        try:
            # 關閉資料庫連接
            await db.close()
            logger.debug("資料庫連接已關閉")
        except Exception as db_error:
            logger.error(f"關閉資料庫連接時發生錯誤: {db_error}")

        # 最後確保資料庫生成器正確關閉
        try:
            await db_gen.aclose()
        except Exception as gen_error:
            logger.error(f"關閉資料庫生成器時發生錯誤: {gen_error}")


# WebSocket服務狀態管理
class WebSocketServiceState:
    """WebSocket服務狀態管理器"""

    def __init__(self):
        self.is_initialized = False
        self.is_healthy = False
        self.initialization_error = None
        self.degraded_mode = False

    def set_initialized(self, success: bool = True, error: Exception = None):
        """設置初始化狀態"""
        self.is_initialized = success
        self.is_healthy = success
        self.initialization_error = error
        self.degraded_mode = not success

    def set_degraded_mode(self, reason: str):
        """設置降級模式"""
        self.degraded_mode = True
        self.is_healthy = False
        logger.warning(f"WebSocket服務進入降級模式: {reason}")

# 全域服務狀態
websocket_service_state = WebSocketServiceState()


# 管理器生命週期管理
async def initialize_websocket_manager():
    """初始化WebSocket管理器"""
    try:
        logger.info("開始初始化WebSocket管理器...")

        # 檢查Redis連接
        from core.redis import redis_client
        if not redis_client.is_connected:
            try:
                await redis_client.connect()
                logger.info("Redis連接已建立")
            except Exception as redis_error:
                logger.error(f"Redis連接失敗: {redis_error}")
                websocket_service_state.set_degraded_mode("Redis連接失敗")
                return False

        # 初始化WebSocket管理器
        await manager.initialize()

        # 驗證管理器功能
        stats = manager.get_connection_stats()
        logger.info(f"WebSocket管理器初始化成功，狀態: {stats}")

        websocket_service_state.set_initialized(True)
        return True

    except Exception as e:
        logger.error(f"WebSocket管理器初始化失敗: {e}")
        websocket_service_state.set_initialized(False, e)

        # 決定是否應該讓整個應用程式失敗
        if isinstance(e, (ConnectionError, OSError)):
            # 網絡相關錯誤，可以降級運行
            websocket_service_state.set_degraded_mode(f"初始化錯誤: {str(e)}")
            return False
        else:
            # 嚴重錯誤，重新拋出異常
            raise


async def shutdown_websocket_manager():
    """關閉WebSocket管理器"""
    try:
        logger.info("開始關閉WebSocket管理器...")

        if websocket_service_state.is_initialized:
            # 獲取最終統計信息
            try:
                final_stats = manager.get_connection_stats()
                logger.info(f"WebSocket管理器關閉前統計: {final_stats}")
            except Exception:
                pass  # 忽略統計錯誤

            # 關閉管理器
            await manager.shutdown()
            logger.info("WebSocket管理器已關閉")
        else:
            logger.info("WebSocket管理器未初始化，跳過關閉")

        # 重置狀態
        websocket_service_state.set_initialized(False)

    except Exception as e:
        logger.error(f"WebSocket管理器關閉失敗: {e}")
        # 關閉失敗不應該阻止應用程式正常退出


async def health_check_websocket_service() -> dict:
    """WebSocket服務健康檢查"""
    health_info = {
        "service": "websocket",
        "status": "healthy" if websocket_service_state.is_healthy else "degraded",
        "initialized": websocket_service_state.is_initialized,
        "degraded_mode": websocket_service_state.degraded_mode,
        "timestamp": datetime.now().isoformat()
    }

    if websocket_service_state.initialization_error:
        health_info["error"] = str(websocket_service_state.initialization_error)

    if websocket_service_state.is_initialized:
        try:
            stats = manager.get_connection_stats()
            health_info["connections"] = stats
        except Exception as e:
            health_info["stats_error"] = str(e)

    return health_info


# 叢集統計端點
async def get_websocket_cluster_stats():
    """取得WebSocket叢集統計資訊"""
    try:
        return await manager.get_cluster_stats()
    except Exception as e:
        logger.error(f"取得叢集統計失敗: {e}")
        return {
            "error": str(e),
            "local_worker": manager.get_connection_stats(),
            "timestamp": datetime.now().isoformat()
        }