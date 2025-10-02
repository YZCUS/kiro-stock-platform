"""
Airflow DAG 數據收集工作流模塊

處理主要收集流程、備援收集流程和策略決策
"""

def decide_collection_strategy(**context):
    """決定數據收集策略：優先嘗試主要路徑，失敗時選擇備援路徑"""
    return 'try_main_collection'  # 總是先嘗試主要路徑


# 嘗試主要收集流程的包裝函數
def try_main_collection_workflow(**context):
    """嘗試執行主要收集流程，失敗時標記需要備援"""
    from plugins.operators.api_operator import APICallOperator

    try:
        print("嘗試主要收集流程: 先獲取股票清單，再收集數據...")

        # 步驟1: 獲取活躍股票清單
        get_stocks_operator = APICallOperator(
            task_id=f"main_get_stocks",
            endpoint="/stocks/active",
            method="GET"
        )

        stocks_result = get_stocks_operator.execute(context)

        # 處理外部存儲的情況
        if isinstance(stocks_result, dict) and stocks_result.get('external_storage'):
            from plugins.services.storage_service import retrieve_large_data
            stocks_data = retrieve_large_data(stocks_result['reference_id'])
        else:
            stocks_data = stocks_result

        # 提取股票清單
        stocks_list = []
        if isinstance(stocks_data, dict):
            if 'items' in stocks_data:
                stocks_list = stocks_data['items']
            elif 'data' in stocks_data:
                stocks_list = stocks_data['data']
            else:
                stocks_list = stocks_data
        elif isinstance(stocks_data, list):
            stocks_list = stocks_data

        if not stocks_list:
            raise ValueError("獲取到的股票清單為空")

        stocks_count = len(stocks_list)
        print(f"獲取到 {stocks_count} 支活躍股票")

        # 轉換股票清單格式為 backend API 期望的格式
        # Backend API 期望: [{"symbol": "2330.TW", "market": "TW"}, ...]
        # 前端 API 回傳: [{"id": 1, "symbol": "2330.TW", "name": "台積電", "market": "TW"}, ...]
        formatted_stocks = [
            {"symbol": stock.get("symbol"), "market": stock.get("market")}
            for stock in stocks_list
        ]

        # 步驟2: 基於股票清單收集數據
        # 使用 /collect-batch 端點，針對特定股票清單進行收集
        collection_strategy = 'batch'  # 追蹤實際使用的收集策略
        actual_stocks_fetched = stocks_count  # 預設使用活躍股票數量

        try:
            # 嘗試使用批次端點
            collect_operator = APICallOperator(
                task_id=f"main_collect_stocks",
                endpoint="/stocks/collect-batch",
                method="POST",
                payload={
                    'stocks': formatted_stocks,
                    'use_stock_list': True
                }
            )
            collection_result = collect_operator.execute(context)
            print("成功使用批次收集策略")

        except Exception as batch_error:
            print(f"批次端點不可用，主要策略回退到collect-all: {batch_error}")
            collection_strategy = 'collect_all_fallback'

            # 回退到collect-all端點
            collect_operator = APICallOperator(
                task_id=f"main_collect_all_fallback",
                endpoint="/stocks/collect-all",
                method="POST"
            )
            collection_result = collect_operator.execute(context)

            # 更新 stocks_fetched 以反映 collect-all 的實際範圍
            # collect-all 不依賴活躍股票清單，而是處理所有市場股票
            actual_stocks_fetched = None  # 暫時設為 None，稍後從 API 響應中獲取
            print("已回退到全市場收集策略")

        # 處理外部存儲的情況
        if isinstance(collection_result, dict) and collection_result.get('external_storage'):
            from plugins.services.storage_service import retrieve_large_data
            collection_data = retrieve_large_data(collection_result['reference_id'])
        else:
            collection_data = collection_result

        # 提取統計信息（從API響應中獲取），處理dict和list兩種格式
        if isinstance(collection_data, dict):
            # 標準dict格式
            total_stocks = collection_data.get('total_stocks', 0)
            success_count = collection_data.get('success_count', 0)
            error_count = collection_data.get('error_count', 0)
            total_data_saved = collection_data.get('total_data_saved', 0)
            api_message = collection_data.get('message', '')
        elif isinstance(collection_data, list):
            # 舊版list格式（常見於collect-all端點）
            list_length = len(collection_data)
            total_stocks = list_length
            success_count = list_length  # 假設列表中的項目都是成功收集的
            error_count = 0
            total_data_saved = list_length  # 假設每個項目都保存了數據
            api_message = f'收集到 {list_length} 項數據（list格式）'
            print(f"檢測到list格式API響應，長度: {list_length}")
        else:
            # 意外的格式
            print(f"警告：API響應格式異常: {type(collection_data)}")
            total_stocks = 0
            success_count = 0
            error_count = 0
            total_data_saved = 0
            api_message = f'API響應格式異常: {type(collection_data)}'

        # 強健的成功判斷邏輯：不依賴單一success欄位，並檢查實際數據收集
        def determine_api_success(data, has_stats):
            """判斷API是否成功，使用多重檢查機制，避免空結果誤判為成功"""
            # 處理 list 格式響應（常見於 collect-all 端點）
            if isinstance(data, list):
                if len(data) > 0:
                    return True, f"成功收集 {len(data)} 項數據（list格式）"
                else:
                    return False, "空的list響應，無數據收集"

            # 處理非 dict 格式的其他類型
            if not isinstance(data, dict):
                return False, f"無效的響應格式: {type(data)}"

            # 方法1：檢查明確的success欄位
            explicit_success = data.get('success')
            if explicit_success is not None:
                return bool(explicit_success), data.get('message', '')

            # 方法2：檢查是否有錯誤欄位
            if 'error' in data or 'errors' in data:
                errors = data.get('error') or data.get('errors', [])
                if errors:  # 有錯誤內容
                    error_msg = str(errors) if not isinstance(errors, list) else f"{len(errors)} errors"
                    return False, f"檢測到錯誤: {error_msg}"

            # 方法3：檢查統計欄位是否合理（必要欄位存在且有意義）
            if has_stats:
                # 如果有統計數據，檢查是否有實際收集到數據
                if total_stocks > 0 or success_count > 0:
                    return True, f"成功處理 {total_stocks} 支股票（成功: {success_count}）"
                elif total_stocks == 0 and success_count == 0:
                    # 統計欄位存在但全為0，可能是空結果
                    return False, f"無數據收集（total_stocks={total_stocks}, success_count={success_count}）"

            # 方法4：檢查是否有資料內容（非空的主要欄位）
            data_fields = ['items', 'data', 'results', 'stocks']
            for field in data_fields:
                if field in data:
                    field_data = data[field]
                    if field_data and len(field_data) > 0:
                        return True, f"檢測到數據內容: {field} ({len(field_data)} 項)"
                    else:
                        # 欄位存在但為空
                        return False, f"數據欄位為空: {field}"

            # 方法5：檢查是否為"無數據"的成功響應（如系統正常但無可收集數據）
            no_data_indicators = ['message', 'info', 'status']
            for field in no_data_indicators:
                if field in data:
                    msg = str(data[field]).lower()

                    # 先檢查負面指示詞彙（排除偽成功訊息）
                    negative_patterns = [
                        '未成功', '不成功', '未完成', '不完成', '未達成', '不達成',
                        '失敗', '錯誤', '異常', '問題', 'failed', 'error', 'exception',
                        'unsuccessful', 'incomplete', 'not completed', 'not successful'
                    ]

                    has_negative_indicator = any(pattern in msg for pattern in negative_patterns)
                    if has_negative_indicator:
                        # 有負面指示，不進行成功判斷，繼續檢查無數據模式
                        pass
                    else:
                        # 沒有負面指示，再檢查成功指示的白名單
                        success_patterns = [
                            '沒有錯誤', '無錯誤', '沒有異常', '無異常', '沒有問題', '無問題',
                            '沒有失敗', '無失敗', '沒有error', '無error', 'no error', 'no exception',
                            'no problem', 'no issue', 'successfully', '成功', '完成', 'success',
                            'completed', 'finished'
                        ]

                        is_success_message = any(pattern in msg for pattern in success_patterns)
                        if is_success_message:
                            continue  # 跳過這個欄位，不視為失敗指示

                    # 檢查真正的無數據指示（完整關鍵字匹配）
                    no_data_patterns = [
                        '沒有資料', '沒有數據', '沒有股票', '沒有結果', '沒有可用',
                        '無資料', '無數據', '無股票', '無結果', '無可用',
                        'no data', 'no stocks', 'no results', 'empty result', 'not found',
                        'no available', '資料為空', '數據為空', '結果為空'
                    ]

                    has_no_data_indicator = any(pattern in msg for pattern in no_data_patterns)
                    if has_no_data_indicator:
                        return False, f"明確的無數據指示: {data[field]}"

            # 方法6：預設判斷 - 非空響應但需要檢查是否有意義
            if len(data) > 0:
                # 檢查是否所有統計數字都是0（可能是空結果）
                numeric_fields = ['total_stocks', 'success_count', 'total_data_saved', 'count', 'total']
                all_zero = True
                has_numeric = False
                for field in numeric_fields:
                    if field in data:
                        has_numeric = True
                        if data[field] != 0:
                            all_zero = False
                            break

                if has_numeric and all_zero:
                    return False, "所有統計數字為0，可能無實際數據"
                else:
                    return True, "預設成功（無明確錯誤指示且有非零數據）"

            return False, "空的或無效的響應"

        # 使用強健的成功判斷
        has_meaningful_stats = (total_stocks > 0 or success_count > 0 or
                               'total_stocks' in collection_data or 'success_count' in collection_data)
        api_success, success_reason = determine_api_success(collection_data, has_meaningful_stats)

        # 根據收集策略調整 stocks_fetched 統計，確保始終為整數
        if collection_strategy == 'collect_all_fallback':
            # collect-all 策略：從 API 響應獲取實際處理的股票數量
            # 由於 collect-all 處理所有市場股票，不限於活躍清單
            actual_stocks_fetched = max(total_stocks, 0)  # 確保為非負整數

            # 建構詳細的策略描述，包含統計數據品質信息
            strategy_components = ["回退策略(collect-all)", "全市場範圍"]

            # 檢查統計數據的完整性並添加說明
            if isinstance(collection_data, list):
                strategy_components.append(f"list格式響應({len(collection_data)}項)")
                strategy_components.append("統計數據從list長度推算")
            elif isinstance(collection_data, dict):
                # 檢查關鍵統計欄位的可用性
                missing_stats = []
                if 'success_count' not in collection_data:
                    missing_stats.append('成功數')
                if 'error_count' not in collection_data:
                    missing_stats.append('失敗數')
                if 'total_data_saved' not in collection_data:
                    missing_stats.append('保存數據點')

                if missing_stats:
                    strategy_components.append(f"部分統計不可用({', '.join(missing_stats)})")

            # 添加市場範圍說明
            if actual_stocks_fetched != stocks_count:
                strategy_components.append(f"實際範圍{actual_stocks_fetched}支 vs 活躍股票{stocks_count}支")

            strategy_info = " | ".join(strategy_components)
        else:
            # batch 策略：使用活躍股票清單
            actual_stocks_fetched = stocks_count
            strategy_info = f"主要策略(collect-batch): 基於活躍股票清單({stocks_count}支)"

        # 最終安全檢查：確保 actual_stocks_fetched 永遠不為 None
        if actual_stocks_fetched is None:
            actual_stocks_fetched = total_stocks if total_stocks > 0 else 0
            print(f"警告：actual_stocks_fetched 為 None，已設為 {actual_stocks_fetched}")

        print(f"主要收集完成: {strategy_info}")
        print(f"統計: 目標 {actual_stocks_fetched} 支，實際收集 {total_stocks} 支")
        print(f"API成功判斷: {api_success} - {success_reason}")

        # 檢查API是否成功
        if not api_success:
            error_msg = f"API收集失敗: {success_reason} | 原始消息: {api_message}"
            print(error_msg)
            raise Exception(error_msg)

        # 注意：避免將完整API響應存入XCom，以防超過48KB限制
        # 大數據已通過外部存儲處理，這裡只保留統計信息

        # 準備詳細的通知上下文
        notification_context = {
            'data_source_type': 'list' if isinstance(collection_data, list) else 'dict',
            'scope_description': '全市場股票' if collection_strategy == 'collect_all_fallback' else '活躍股票清單',
            'statistics_reliability': 'estimated' if isinstance(collection_data, list) else 'api_provided'
        }

        # 檢查統計數據的可信度
        if collection_strategy == 'collect_all_fallback':
            if success_count == 0 and error_count == 0 and total_stocks > 0:
                notification_context['warning'] = '成功/失敗數不可用，可能為舊版API格式'
            if isinstance(collection_data, list):
                notification_context['note'] = f'統計數據基於list長度({len(collection_data)})推算'

        # 返回標準化的成功狀態（與驗證邏輯兼容）
        return {
            'strategy': 'main',
            'status': 'success',
            'message': '主要收集流程完成',
            # 包含統計信息供後續驗證使用，確保數據一致性
            'stocks_fetched': actual_stocks_fetched,  # 反映實際收集範圍
            'total_stocks': total_stocks,
            'success_count': success_count,
            'error_count': error_count,
            'total_data_saved': total_data_saved,
            # 新增收集策略信息
            'collection_strategy': collection_strategy,
            'strategy_description': strategy_info,
            'notification_context': notification_context,  # 通知上下文信息
            # 只保留必要的API元數據，避免XCom大小超限
            'api_success': api_success,
            'api_message': api_message[:200] if api_message else '',  # 截斷消息以避免過長
            # 保留原始結果引用以便清理（外部存儲情況）
            'original_result': collection_result if isinstance(collection_result, dict) and collection_result.get('external_storage') else None
        }

    except Exception as e:
        error_msg = str(e)
        print(f"主要收集流程失敗: {error_msg}")

        # 分類錯誤類型以決定是否應該重試還是直接備援
        def classify_error(error_message):
            """分類錯誤類型，決定重試策略"""
            error_lower = error_message.lower()

            # 應該重試的暫態錯誤
            retry_keywords = [
                'timeout', '連線超時', 'connection', 'network', 'dns',
                'temporary', '暫時', '臨時', 'rate limit', 'too many requests',
                '503', '502', '504', 'service unavailable', 'bad gateway',
                'gateway timeout', 'read timeout', 'connect timeout'
            ]

            # 應該直接備援的結構性錯誤
            fallback_keywords = [
                'endpoint', '端點', 'not found', '404', 'method not allowed', '405',
                'unauthorized', '401', 'forbidden', '403', 'invalid', '無效',
                'malformed', '格式錯誤', 'schema', 'validation'
            ]

            for keyword in retry_keywords:
                if keyword in error_lower:
                    return 'retry_worthy'

            for keyword in fallback_keywords:
                if keyword in error_lower:
                    return 'fallback_needed'

            # 預設：未知錯誤先重試
            return 'retry_worthy'

        error_type = classify_error(error_msg)

        # 根據錯誤類型決定是否拋出異常（觸發重試）或返回失敗狀態（觸發備援）
        if error_type == 'retry_worthy':
            # 暫態錯誤：拋出異常讓 Airflow 重試
            print(f"檢測到暫態錯誤，將觸發 Airflow 重試機制: {error_msg}")
            raise Exception(f"主要收集暫時失敗: {error_msg}")
        else:
            # 結構性錯誤：返回失敗狀態，觸發備援
            print(f"檢測到結構性錯誤，將觸發備援機制: {error_msg}")
            return {
                'strategy': 'fallback_needed',
                'status': 'need_fallback',
                'error': error_msg,
                'error_type': error_type,
                'message': f'主要流程失敗，需要備援: {error_msg}'
            }

# 主要收集任務（智能重試版：暫態錯誤會重試，結構性錯誤返回備援指示）

# 決定下一步策略
def decide_next_step(**context):
    """根據主要收集的結果決定下一步"""
    ti = context['task_instance']
    main_result = ti.xcom_pull(task_ids='try_main_collection')

    # 檢查主要收集是否成功
    if main_result and main_result.get('status') == 'success':
        print("主要收集成功，進入後續處理")
        return 'collection_success'

    # 主要收集失敗或需要備援
    elif main_result and main_result.get('status') == 'need_fallback':
        error_msg = main_result.get('error', 'Unknown error')
        print(f"主要收集失敗，啟動備援機制: {error_msg}")
        return 'execute_fallback_collection'

    # 其他情況（包括主要任務重試後最終失敗）
    else:
        print("主要收集最終失敗，啟動備援機制")
        return 'execute_fallback_collection'


# 備援收集任務
def execute_fallback_collection(**context):
    """執行備援數據收集"""
    from plugins.operators.api_operator import APICallOperator

    try:
        print("執行備援數據收集流程: 直接收集所有活躍股票...")

        # 備援策略：直接調用collect-all API，無需先獲取股票清單
        collect_all_operator = APICallOperator(
            task_id=f"fallback_collect_all",
            endpoint="/stocks/collect-all",
            method="POST"
        )

        collection_result = collect_all_operator.execute(context)

        # 處理外部存儲的情況
        if isinstance(collection_result, dict) and collection_result.get('external_storage'):
            from plugins.services.storage_service import retrieve_large_data
            collection_data = retrieve_large_data(collection_result['reference_id'])
        else:
            collection_data = collection_result

        # 提取統計信息（從API響應中獲取），處理dict和list兩種格式
        if isinstance(collection_data, dict):
            # 標準dict格式
            total_stocks = collection_data.get('total_stocks', 0)
            success_count = collection_data.get('success_count', 0)
            error_count = collection_data.get('error_count', 0)
            total_data_saved = collection_data.get('total_data_saved', 0)
            api_message = collection_data.get('message', '')
        elif isinstance(collection_data, list):
            # 舊版list格式（常見於collect-all端點）
            list_length = len(collection_data)
            total_stocks = list_length
            success_count = list_length  # 假設列表中的項目都是成功收集的
            error_count = 0
            total_data_saved = list_length  # 假設每個項目都保存了數據
            api_message = f'收集到 {list_length} 項數據（list格式）'
            print(f"檢測到list格式API響應，長度: {list_length}")
        else:
            # 意外的格式
            print(f"警告：API響應格式異常: {type(collection_data)}")
            total_stocks = 0
            success_count = 0
            error_count = 0
            total_data_saved = 0
            api_message = f'API響應格式異常: {type(collection_data)}'

        # 強健的成功判斷邏輯：不依賴單一success欄位，並檢查實際數據收集
        def determine_api_success(data, has_stats):
            """判斷API是否成功，使用多重檢查機制，避免空結果誤判為成功"""
            # 處理 list 格式響應（常見於 collect-all 端點）
            if isinstance(data, list):
                if len(data) > 0:
                    return True, f"成功收集 {len(data)} 項數據（list格式）"
                else:
                    return False, "空的list響應，無數據收集"

            # 處理非 dict 格式的其他類型
            if not isinstance(data, dict):
                return False, f"無效的響應格式: {type(data)}"

            # 方法1：檢查明確的success欄位
            explicit_success = data.get('success')
            if explicit_success is not None:
                return bool(explicit_success), data.get('message', '')

            # 方法2：檢查是否有錯誤欄位
            if 'error' in data or 'errors' in data:
                errors = data.get('error') or data.get('errors', [])
                if errors:  # 有錯誤內容
                    error_msg = str(errors) if not isinstance(errors, list) else f"{len(errors)} errors"
                    return False, f"檢測到錯誤: {error_msg}"

            # 方法3：檢查統計欄位是否合理（必要欄位存在且有意義）
            if has_stats:
                # 如果有統計數據，檢查是否有實際收集到數據
                if total_stocks > 0 or success_count > 0:
                    return True, f"成功處理 {total_stocks} 支股票（成功: {success_count}）"
                elif total_stocks == 0 and success_count == 0:
                    # 統計欄位存在但全為0，可能是空結果
                    return False, f"無數據收集（total_stocks={total_stocks}, success_count={success_count}）"

            # 方法4：檢查是否有資料內容（非空的主要欄位）
            data_fields = ['items', 'data', 'results', 'stocks']
            for field in data_fields:
                if field in data:
                    field_data = data[field]
                    if field_data and len(field_data) > 0:
                        return True, f"檢測到數據內容: {field} ({len(field_data)} 項)"
                    else:
                        # 欄位存在但為空
                        return False, f"數據欄位為空: {field}"

            # 方法5：檢查是否為"無數據"的成功響應（如系統正常但無可收集數據）
            no_data_indicators = ['message', 'info', 'status']
            for field in no_data_indicators:
                if field in data:
                    msg = str(data[field]).lower()

                    # 先檢查負面指示詞彙（排除偽成功訊息）
                    negative_patterns = [
                        '未成功', '不成功', '未完成', '不完成', '未達成', '不達成',
                        '失敗', '錯誤', '異常', '問題', 'failed', 'error', 'exception',
                        'unsuccessful', 'incomplete', 'not completed', 'not successful'
                    ]

                    has_negative_indicator = any(pattern in msg for pattern in negative_patterns)
                    if has_negative_indicator:
                        # 有負面指示，不進行成功判斷，繼續檢查無數據模式
                        pass
                    else:
                        # 沒有負面指示，再檢查成功指示的白名單
                        success_patterns = [
                            '沒有錯誤', '無錯誤', '沒有異常', '無異常', '沒有問題', '無問題',
                            '沒有失敗', '無失敗', '沒有error', '無error', 'no error', 'no exception',
                            'no problem', 'no issue', 'successfully', '成功', '完成', 'success',
                            'completed', 'finished'
                        ]

                        is_success_message = any(pattern in msg for pattern in success_patterns)
                        if is_success_message:
                            continue  # 跳過這個欄位，不視為失敗指示

                    # 檢查真正的無數據指示（完整關鍵字匹配）
                    no_data_patterns = [
                        '沒有資料', '沒有數據', '沒有股票', '沒有結果', '沒有可用',
                        '無資料', '無數據', '無股票', '無結果', '無可用',
                        'no data', 'no stocks', 'no results', 'empty result', 'not found',
                        'no available', '資料為空', '數據為空', '結果為空'
                    ]

                    has_no_data_indicator = any(pattern in msg for pattern in no_data_patterns)
                    if has_no_data_indicator:
                        return False, f"明確的無數據指示: {data[field]}"

            # 方法6：預設判斷 - 非空響應但需要檢查是否有意義
            if len(data) > 0:
                # 檢查是否所有統計數字都是0（可能是空結果）
                numeric_fields = ['total_stocks', 'success_count', 'total_data_saved', 'count', 'total']
                all_zero = True
                has_numeric = False
                for field in numeric_fields:
                    if field in data:
                        has_numeric = True
                        if data[field] != 0:
                            all_zero = False
                            break

                if has_numeric and all_zero:
                    return False, "所有統計數字為0，可能無實際數據"
                else:
                    return True, "預設成功（無明確錯誤指示且有非零數據）"

            return False, "空的或無效的響應"

        # 使用強健的成功判斷
        has_meaningful_stats = (total_stocks > 0 or success_count > 0 or
                               'total_stocks' in collection_data or 'success_count' in collection_data)
        api_success, success_reason = determine_api_success(collection_data, has_meaningful_stats)

        print(f"備援收集完成: 收集 {total_stocks} 支股票")
        print(f"API成功判斷: {api_success} - {success_reason}")

        # 檢查API是否成功
        if not api_success:
            error_msg = f"API收集失敗: {success_reason} | 原始消息: {api_message}"
            print(error_msg)
            raise Exception(error_msg)

        # 注意：避免將完整API響應存入XCom，以防超過48KB限制
        # 大數據已通過外部存儲處理，這裡只保留統計信息

        # 返回標準化的成功狀態（與驗證邏輯兼容）
        return {
            'strategy': 'fallback',
            'status': 'success',
            'message': '備援收集流程完成',
            # 包含統計信息供後續驗證使用
            'stocks_fetched': total_stocks,  # 備援策略中，獲取的就是收集的
            'total_stocks': total_stocks,
            'success_count': success_count,
            'error_count': error_count,
            'total_data_saved': total_data_saved,
            # 只保留必要的API元數據，避免XCom大小超限
            'api_success': api_success,
            'api_message': api_message[:200] if api_message else '',  # 截斷消息以避免過長
            # 保留原始結果引用以便清理（外部存儲情況）
            'original_result': collection_result if isinstance(collection_result, dict) and collection_result.get('external_storage') else None
        }

    except Exception as e:
        print(f"備援收集也失敗: {e}")
        raise  # 備援失敗時才真正拋出異常


# 成功標記任務（當主要流程成功時）

# 聚合任務 - 匯合主要成功路徑和備援成功路徑
# 使用 NONE_FAILED_OR_SKIPPED 確保單一路徑成功即可繼續
# BranchPythonOperator 會跳過未選擇的路徑，因此總有一條路徑會是 skipped 狀態

# 數據品質驗證（簡化版本 - 只檢查前5支股票）