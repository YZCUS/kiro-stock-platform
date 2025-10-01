"""
Airflow DAG 通知模塊

處理完成通知等通知功能
"""


def send_completion_notification(**context):
    """發送完成通知 - 使用台北時區"""
    from plugins.common.date_utils import get_taipei_now

    ti = context['ti']
    taipei_now = get_taipei_now()

    # 取得所有任務結果
    main_result = ti.xcom_pull(task_ids='try_main_collection')
    fallback_result = ti.xcom_pull(task_ids='execute_fallback_collection')

    # 確定使用的收集結果
    if main_result and main_result.get('status') == 'success':
        active_collection_result = main_result
        # 檢查是否有詳細的策略信息
        strategy_desc = main_result.get('strategy_description', '')
        collection_source = f"主要策略 ({strategy_desc})" if strategy_desc else "主要策略"
    elif fallback_result and fallback_result.get('status') == 'success':
        active_collection_result = fallback_result
        strategy_desc = fallback_result.get('strategy_description', '')
        collection_source = f"備援策略 ({strategy_desc})" if strategy_desc else "備援策略"
    else:
        active_collection_result = None
        collection_source = "無"

    validation_result = ti.xcom_pull(task_ids='validate_data_quality')
    dependency_result = ti.xcom_pull(task_ids='verify_dependencies')

    # 準備通知內容，包含詳細的上下文信息
    notification_context = active_collection_result.get('notification_context', {}) if active_collection_result else {}

    # 建構詳細的統計信息說明
    stats_explanation = []
    if notification_context.get('scope_description'):
        stats_explanation.append(f"範圍: {notification_context['scope_description']}")

    if notification_context.get('statistics_reliability') == 'estimated':
        stats_explanation.append("統計: 推算值")
    elif notification_context.get('statistics_reliability') == 'api_provided':
        stats_explanation.append("統計: API提供")

    stats_note = f" ({', '.join(stats_explanation)})" if stats_explanation else ""

    # 建構警告和注意事項
    warnings = []
    if notification_context.get('warning'):
        warnings.append(f"⚠️ {notification_context['warning']}")
    if notification_context.get('note'):
        warnings.append(f"📝 {notification_context['note']}")

    warning_section = "\n".join(warnings) + "\n" if warnings else ""

    message = f"""
每日股票數據收集完成

任務依賴驗證:
- 依賴鏈健康: {'是' if dependency_result and dependency_result.get('dependency_chain_healthy') else '否'}
- 獲取股票數: {dependency_result.get('stocks_fetched', 0) if dependency_result else 0}
- 收集股票數: {dependency_result.get('stocks_collected', 0) if dependency_result else 0}

收集結果 (來源: {collection_source}){stats_note}:
- 總股票數: {active_collection_result.get('total_stocks', 0) if active_collection_result else 0}
- 成功收集: {active_collection_result.get('success_count', 0) if active_collection_result else 0}
- 失敗數量: {active_collection_result.get('error_count', 0) if active_collection_result else 0}
- 數據點總數: {active_collection_result.get('total_data_saved', 0) if active_collection_result else 0}

{warning_section}數據驗證:
- 驗證完成: {'是' if validation_result else '否'}

執行時間: {taipei_now.format('YYYY-MM-DD HH:mm:ss')} (台北時間)
    """

    print(message)  # 實際使用時可以發送郵件或其他通知

    return {
        'notification_sent': True,
        'message': message,
        'completion_time': taipei_now.isoformat()
    }
