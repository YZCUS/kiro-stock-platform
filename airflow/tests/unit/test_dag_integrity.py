#!/usr/bin/env python3
"""
Airflow DAG 測試腳本
"""
import sys
import os
from pathlib import Path
from datetime import datetime, timedelta
import logging

# 設定 Airflow 環境
os.environ['AIRFLOW_HOME'] = str(Path(__file__).parent)
os.environ['AIRFLOW__CORE__DAGS_FOLDER'] = str(Path(__file__).parent / 'dags')
os.environ['AIRFLOW__CORE__LOAD_EXAMPLES'] = 'False'


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_dag_import():
    """測試 DAG 匯入"""
    logger.info("測試 DAG 匯入...")
    
    try:
        # 測試匯入現有的 DAG
        from ...dags.stock_daily_collection import dag as daily_collection_dag
        
        if daily_collection_dag:
            logger.info("✅ daily_collection_api DAG 匯入成功")
            return True
        else:
            logger.error("❌ daily_collection_api DAG 匯入失敗")
            return False
        
    except Exception as e:
        logger.error(f"❌ DAG 匯入失敗: {str(e)}")
        return False


def test_dag_structure():
    """測試 DAG 結構"""
    logger.info("測試 DAG 結構...")
    
    try:
        from airflow.models import DagBag
        
        # 載入 DAG
        dagbag = DagBag(dag_folder=str(Path(__file__).parent.parent.parent / 'dags'))
        
        if dagbag.import_errors:
            logger.error("DAG 匯入錯誤:")
            for filename, error in dagbag.import_errors.items():
                logger.error(f"  {filename}: {error}")
            return False
        
        # 檢查預期的 DAG
        expected_dags = [
            'daily_stock_collection_api'
        ]
        
        found_dags = list(dagbag.dags.keys())
        logger.info(f"找到的 DAG: {found_dags}")
        
        for dag_id in expected_dags:
            if dag_id not in found_dags:
                logger.error(f"❌ 缺少 DAG: {dag_id}")
                return False
            
            dag = dagbag.get_dag(dag_id)
            if not dag:
                logger.error(f"❌ 無法載入 DAG: {dag_id}")
                return False
            
            logger.info(f"✅ DAG {dag_id} 結構正確，包含 {len(dag.tasks)} 個任務")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ DAG 結構測試失敗: {str(e)}")
        return False


def test_dag_tasks():
    """測試 DAG 任務"""
    logger.info("測試 DAG 任務...")
    
    try:
        from airflow.models import DagBag
        
        dagbag = DagBag(dag_folder=str(Path(__file__).parent.parent.parent / 'dags'))
        
        # 測試每個 DAG 的任務
        for dag_id in ['daily_stock_collection_api']:
            dag = dagbag.get_dag(dag_id)
            
            if not dag:
                logger.error(f"❌ 無法載入 DAG: {dag_id}")
                continue
            
            logger.info(f"測試 DAG: {dag_id}")
            
            # 檢查任務依賴
            for task in dag.tasks:
                logger.info(f"  任務: {task.task_id}")
                
                # 檢查上游任務
                upstream_tasks = task.upstream_task_ids
                if upstream_tasks:
                    logger.info(f"    上游任務: {upstream_tasks}")
                
                # 檢查下游任務
                downstream_tasks = task.downstream_task_ids
                if downstream_tasks:
                    logger.info(f"    下游任務: {downstream_tasks}")
            
            # 檢查 DAG 是否有循環依賴
            try:
                dag.test_cycle()
                logger.info(f"✅ DAG {dag_id} 無循環依賴")
            except Exception as e:
                logger.error(f"❌ DAG {dag_id} 存在循環依賴: {str(e)}")
                return False
        
        return True
        
    except Exception as e:
        logger.error(f"❌ DAG 任務測試失敗: {str(e)}")
        return False


def test_dag_scheduling():
    """測試 DAG 排程"""
    logger.info("測試 DAG 排程...")
    
    try:
        from airflow.models import DagBag
        
        dagbag = DagBag(dag_folder=str(Path(__file__).parent.parent.parent / 'dags'))
        
        # 檢查排程配置
        expected_schedules = {
            'daily_stock_fetch': '0 16 * * 1-5',      # 週一到週五下午4點
            'technical_analysis': '30 16 * * 1-5',    # 週一到週五下午4點30分
            'data_validation': '0 17 * * 1-5'         # 週一到週五下午5點
        }
        
        for dag_id, expected_schedule in expected_schedules.items():
            dag = dagbag.get_dag(dag_id)
            
            if not dag:
                logger.error(f"❌ 無法載入 DAG: {dag_id}")
                continue
            
            actual_schedule = dag.schedule_interval
            
            if str(actual_schedule) == expected_schedule:
                logger.info(f"✅ DAG {dag_id} 排程正確: {actual_schedule}")
            else:
                logger.warning(f"⚠️  DAG {dag_id} 排程不符預期: 實際={actual_schedule}, 預期={expected_schedule}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ DAG 排程測試失敗: {str(e)}")
        return False


def test_dag_configuration():
    """測試 DAG 配置"""
    logger.info("測試 DAG 配置...")
    
    try:
        from airflow.models import DagBag
        
        dagbag = DagBag(dag_folder=str(Path(__file__).parent.parent.parent / 'dags'))
        
        for dag_id in ['daily_stock_fetch', 'technical_analysis', 'data_validation']:
            dag = dagbag.get_dag(dag_id)
            
            if not dag:
                logger.error(f"❌ 無法載入 DAG: {dag_id}")
                continue
            
            # 檢查基本配置
            logger.info(f"DAG {dag_id} 配置:")
            logger.info(f"  描述: {dag.description}")
            logger.info(f"  擁有者: {dag.default_args.get('owner', 'N/A')}")
            logger.info(f"  開始日期: {dag.start_date}")
            logger.info(f"  排程間隔: {dag.schedule_interval}")
            logger.info(f"  最大活躍執行數: {dag.max_active_runs}")
            logger.info(f"  標籤: {dag.tags}")
            
            # 檢查重要配置
            if not dag.catchup:
                logger.info(f"✅ DAG {dag_id} 已禁用 catchup")
            else:
                logger.warning(f"⚠️  DAG {dag_id} 啟用了 catchup，可能導致大量歷史執行")
            
            if dag.max_active_runs == 1:
                logger.info(f"✅ DAG {dag_id} 限制同時執行數為 1")
            else:
                logger.warning(f"⚠️  DAG {dag_id} 允許多個同時執行")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ DAG 配置測試失敗: {str(e)}")
        return False


def main():
    """主測試函數"""
    logger.info("開始 Airflow DAG 測試...")
    
    tests = [
        ("DAG 匯入測試", test_dag_import),
        ("DAG 結構測試", test_dag_structure),
        ("DAG 任務測試", test_dag_tasks),
        ("DAG 排程測試", test_dag_scheduling),
        ("DAG 配置測試", test_dag_configuration),
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        try:
            logger.info(f"\n{'='*50}")
            logger.info(f"執行：{test_name}")
            logger.info(f"{'='*50}")
            
            result = test_func()
            results[test_name] = result
            
            if result:
                logger.info(f"✅ {test_name} - 通過")
            else:
                logger.error(f"❌ {test_name} - 失敗")
                
        except Exception as e:
            logger.error(f"❌ {test_name} - 異常：{str(e)}")
            results[test_name] = False
    
    # 總結
    logger.info(f"\n{'='*50}")
    logger.info("測試結果總結")
    logger.info(f"{'='*50}")
    
    passed = sum(1 for result in results.values() if result)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ 通過" if result else "❌ 失敗"
        logger.info(f"{test_name}: {status}")
    
    logger.info(f"\n總計：{passed}/{total} 個測試通過")
    
    if passed == total:
        logger.info("🎉 所有 DAG 測試都通過了！")
        return 0
    else:
        logger.error("⚠️  部分 DAG 測試失敗，請檢查配置")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)