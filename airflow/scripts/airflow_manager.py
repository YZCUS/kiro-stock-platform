#!/usr/bin/env python3
"""
Airflow 管理腳本
"""
import os
import sys
import subprocess
import time
import logging
from pathlib import Path
from typing import List, Dict, Any

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AirflowManager:
    """Airflow 管理器"""
    
    def __init__(self):
        self.airflow_home = os.getenv('AIRFLOW_HOME', '/opt/airflow')
        self.dags_folder = os.path.join(self.airflow_home, 'dags')
        self.logs_folder = os.path.join(self.airflow_home, 'logs')
    
    def init_airflow(self):
        """初始化 Airflow"""
        try:
            logger.info("正在初始化 Airflow...")
            
            # 初始化資料庫
            result = subprocess.run(['airflow', 'db', 'init'], 
                                  capture_output=True, text=True)
            if result.returncode != 0:
                logger.error(f"初始化資料庫失敗: {result.stderr}")
                return False
            
            # 建立管理員用戶
            result = subprocess.run([
                'airflow', 'users', 'create',
                '--username', 'admin',
                '--firstname', 'Admin',
                '--lastname', 'User',
                '--role', 'Admin',
                '--email', 'admin@example.com',
                '--password', 'admin'
            ], capture_output=True, text=True)
            
            if result.returncode != 0 and "already exists" not in result.stderr:
                logger.error(f"建立管理員用戶失敗: {result.stderr}")
                return False
            
            logger.info("Airflow 初始化完成")
            return True
            
        except Exception as e:
            logger.error(f"初始化 Airflow 時發生錯誤: {str(e)}")
            return False
    
    def start_webserver(self, port: int = 8080):
        """啟動 Web 伺服器"""
        try:
            logger.info(f"正在啟動 Airflow Web 伺服器 (端口: {port})...")
            
            # 啟動 webserver
            process = subprocess.Popen([
                'airflow', 'webserver', '--port', str(port)
            ])
            
            logger.info(f"Airflow Web 伺服器已啟動，PID: {process.pid}")
            logger.info(f"訪問地址: http://localhost:{port}")
            
            return process
            
        except Exception as e:
            logger.error(f"啟動 Web 伺服器時發生錯誤: {str(e)}")
            return None
    
    def start_scheduler(self):
        """啟動排程器"""
        try:
            logger.info("正在啟動 Airflow 排程器...")
            
            # 啟動 scheduler
            process = subprocess.Popen(['airflow', 'scheduler'])
            
            logger.info(f"Airflow 排程器已啟動，PID: {process.pid}")
            
            return process
            
        except Exception as e:
            logger.error(f"啟動排程器時發生錯誤: {str(e)}")
            return None
    
    def list_dags(self) -> List[Dict[str, Any]]:
        """列出所有 DAG"""
        try:
            result = subprocess.run(['airflow', 'dags', 'list'], 
                                  capture_output=True, text=True)
            
            if result.returncode != 0:
                logger.error(f"列出 DAG 失敗: {result.stderr}")
                return []
            
            # 解析輸出
            lines = result.stdout.strip().split('\n')
            dags = []
            
            for line in lines:
                if line.startswith('dag_id'):  # 跳過標題行
                    continue
                if '|' in line:
                    parts = [part.strip() for part in line.split('|')]
                    if len(parts) >= 4:
                        dags.append({
                            'dag_id': parts[0],
                            'filepath': parts[1],
                            'owner': parts[2],
                            'paused': parts[3] == 'True'
                        })
            
            return dags
            
        except Exception as e:
            logger.error(f"列出 DAG 時發生錯誤: {str(e)}")
            return []
    
    def trigger_dag(self, dag_id: str, conf: Dict[str, Any] = None) -> bool:
        """觸發 DAG 執行"""
        try:
            logger.info(f"正在觸發 DAG: {dag_id}")
            
            cmd = ['airflow', 'dags', 'trigger', dag_id]
            
            if conf:
                import json
                cmd.extend(['--conf', json.dumps(conf)])
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                logger.error(f"觸發 DAG 失敗: {result.stderr}")
                return False
            
            logger.info(f"DAG {dag_id} 觸發成功")
            return True
            
        except Exception as e:
            logger.error(f"觸發 DAG 時發生錯誤: {str(e)}")
            return False
    
    def pause_dag(self, dag_id: str) -> bool:
        """暫停 DAG"""
        try:
            result = subprocess.run(['airflow', 'dags', 'pause', dag_id], 
                                  capture_output=True, text=True)
            
            if result.returncode != 0:
                logger.error(f"暫停 DAG 失敗: {result.stderr}")
                return False
            
            logger.info(f"DAG {dag_id} 已暫停")
            return True
            
        except Exception as e:
            logger.error(f"暫停 DAG 時發生錯誤: {str(e)}")
            return False
    
    def unpause_dag(self, dag_id: str) -> bool:
        """恢復 DAG"""
        try:
            result = subprocess.run(['airflow', 'dags', 'unpause', dag_id], 
                                  capture_output=True, text=True)
            
            if result.returncode != 0:
                logger.error(f"恢復 DAG 失敗: {result.stderr}")
                return False
            
            logger.info(f"DAG {dag_id} 已恢復")
            return True
            
        except Exception as e:
            logger.error(f"恢復 DAG 時發生錯誤: {str(e)}")
            return False
    
    def get_dag_runs(self, dag_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """取得 DAG 執行記錄"""
        try:
            result = subprocess.run([
                'airflow', 'dags', 'list-runs', 
                '--dag-id', dag_id,
                '--limit', str(limit)
            ], capture_output=True, text=True)
            
            if result.returncode != 0:
                logger.error(f"取得 DAG 執行記錄失敗: {result.stderr}")
                return []
            
            # 解析輸出（簡化版本）
            runs = []
            lines = result.stdout.strip().split('\n')
            
            for line in lines[2:]:  # 跳過標題行
                if '|' in line:
                    parts = [part.strip() for part in line.split('|')]
                    if len(parts) >= 4:
                        runs.append({
                            'dag_id': parts[0],
                            'run_id': parts[1],
                            'state': parts[2],
                            'execution_date': parts[3]
                        })
            
            return runs
            
        except Exception as e:
            logger.error(f"取得 DAG 執行記錄時發生錯誤: {str(e)}")
            return []
    
    def test_task(self, dag_id: str, task_id: str, execution_date: str) -> bool:
        """測試單個任務"""
        try:
            logger.info(f"正在測試任務: {dag_id}.{task_id}")
            
            result = subprocess.run([
                'airflow', 'tasks', 'test',
                dag_id, task_id, execution_date
            ], capture_output=True, text=True)
            
            if result.returncode != 0:
                logger.error(f"測試任務失敗: {result.stderr}")
                return False
            
            logger.info(f"任務測試成功: {dag_id}.{task_id}")
            return True
            
        except Exception as e:
            logger.error(f"測試任務時發生錯誤: {str(e)}")
            return False
    
    def validate_dags(self) -> bool:
        """驗證所有 DAG"""
        try:
            logger.info("正在驗證所有 DAG...")
            
            result = subprocess.run(['python', '-m', 'py_compile'] + 
                                  [str(f) for f in Path(self.dags_folder).glob('*.py')],
                                  capture_output=True, text=True)
            
            if result.returncode != 0:
                logger.error(f"DAG 驗證失敗: {result.stderr}")
                return False
            
            logger.info("所有 DAG 驗證通過")
            return True
            
        except Exception as e:
            logger.error(f"驗證 DAG 時發生錯誤: {str(e)}")
            return False
    
    def get_system_status(self) -> Dict[str, Any]:
        """取得系統狀態"""
        try:
            # 檢查 Airflow 版本
            version_result = subprocess.run(['airflow', 'version'], 
                                          capture_output=True, text=True)
            version = version_result.stdout.strip() if version_result.returncode == 0 else "Unknown"
            
            # 檢查資料庫連接
            db_result = subprocess.run(['airflow', 'db', 'check'], 
                                     capture_output=True, text=True)
            db_status = "Connected" if db_result.returncode == 0 else "Disconnected"
            
            # 統計 DAG 數量
            dags = self.list_dags()
            active_dags = len([dag for dag in dags if not dag['paused']])
            paused_dags = len([dag for dag in dags if dag['paused']])
            
            return {
                'airflow_version': version,
                'database_status': db_status,
                'total_dags': len(dags),
                'active_dags': active_dags,
                'paused_dags': paused_dags,
                'airflow_home': self.airflow_home,
                'dags_folder': self.dags_folder
            }
            
        except Exception as e:
            logger.error(f"取得系統狀態時發生錯誤: {str(e)}")
            return {}


def main():
    """主函數"""
    if len(sys.argv) < 2:
        print("使用方法:")
        print("  python airflow_manager.py init                    # 初始化 Airflow")
        print("  python airflow_manager.py start                   # 啟動 webserver 和 scheduler")
        print("  python airflow_manager.py webserver [port]        # 只啟動 webserver")
        print("  python airflow_manager.py scheduler               # 只啟動 scheduler")
        print("  python airflow_manager.py list                    # 列出所有 DAG")
        print("  python airflow_manager.py trigger <dag_id>        # 觸發 DAG")
        print("  python airflow_manager.py pause <dag_id>          # 暫停 DAG")
        print("  python airflow_manager.py unpause <dag_id>        # 恢復 DAG")
        print("  python airflow_manager.py test <dag_id> <task_id> <date>  # 測試任務")
        print("  python airflow_manager.py validate                # 驗證 DAG")
        print("  python airflow_manager.py status                  # 系統狀態")
        return
    
    manager = AirflowManager()
    command = sys.argv[1]
    
    if command == "init":
        manager.init_airflow()
    
    elif command == "start":
        manager.init_airflow()
        webserver = manager.start_webserver()
        scheduler = manager.start_scheduler()
        
        if webserver and scheduler:
            try:
                logger.info("Airflow 已啟動，按 Ctrl+C 停止")
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                logger.info("正在停止 Airflow...")
                webserver.terminate()
                scheduler.terminate()
    
    elif command == "webserver":
        port = int(sys.argv[2]) if len(sys.argv) > 2 else 8080
        process = manager.start_webserver(port)
        if process:
            try:
                process.wait()
            except KeyboardInterrupt:
                process.terminate()
    
    elif command == "scheduler":
        process = manager.start_scheduler()
        if process:
            try:
                process.wait()
            except KeyboardInterrupt:
                process.terminate()
    
    elif command == "list":
        dags = manager.list_dags()
        print(f"找到 {len(dags)} 個 DAG:")
        for dag in dags:
            status = "暫停" if dag['paused'] else "活躍"
            print(f"  - {dag['dag_id']} ({status}) - {dag['owner']}")
    
    elif command == "trigger":
        if len(sys.argv) < 3:
            print("請提供 DAG ID")
            return
        dag_id = sys.argv[2]
        manager.trigger_dag(dag_id)
    
    elif command == "pause":
        if len(sys.argv) < 3:
            print("請提供 DAG ID")
            return
        dag_id = sys.argv[2]
        manager.pause_dag(dag_id)
    
    elif command == "unpause":
        if len(sys.argv) < 3:
            print("請提供 DAG ID")
            return
        dag_id = sys.argv[2]
        manager.unpause_dag(dag_id)
    
    elif command == "test":
        if len(sys.argv) < 5:
            print("請提供 DAG ID、Task ID 和執行日期")
            return
        dag_id, task_id, execution_date = sys.argv[2:5]
        manager.test_task(dag_id, task_id, execution_date)
    
    elif command == "validate":
        manager.validate_dags()
    
    elif command == "status":
        status = manager.get_system_status()
        print("Airflow 系統狀態:")
        for key, value in status.items():
            print(f"  {key}: {value}")
    
    else:
        print(f"未知命令: {command}")


if __name__ == "__main__":
    main()