"""建立資料表腳本"""
import asyncio
import sys
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from core.database import Base, engine
from domain.models.stock import Stock
from domain.models.price_history import PriceHistory
from domain.models.technical_indicator import TechnicalIndicator
from domain.models.trading_signal import TradingSignal


async def create_tables():
    """建立所有資料表"""
    print("開始建立資料表...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("資料表建立成功！")

    # 列出已建立的表
    async with engine.connect() as conn:
        result = await conn.execute(
            """
            SELECT tablename
            FROM pg_tables
            WHERE schemaname = 'public'
            AND tablename NOT LIKE 'ab_%'
            AND tablename NOT LIKE 'dag%'
            AND tablename NOT IN ('alembic_version', 'connection', 'callback_request',
                                  'import_error', 'job', 'log', 'log_template',
                                  'rendered_task_instance_fields', 'serialized_dag',
                                  'session', 'sla_miss', 'slot_pool', 'task_fail',
                                  'task_instance', 'task_instance_note', 'task_map',
                                  'task_outlet_dataset_reference', 'task_reschedule',
                                  'trigger', 'variable', 'xcom', 'dataset',
                                  'dataset_dag_run_queue', 'dataset_event',
                                  'dagrun_dataset_event')
            ORDER BY tablename;
            """
        )
        tables = [row[0] for row in result]
        print(f"\n業務相關資料表: {', '.join(tables) if tables else '無'}")


if __name__ == "__main__":
    asyncio.run(create_tables())
