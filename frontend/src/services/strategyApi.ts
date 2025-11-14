/**
 * Strategy API Service
 */
import { get, post, put, del } from '@/lib/api';
import { API_ENDPOINTS } from '@/lib/api';
import type {
  StrategyListResponse,
  Subscription,
  SubscriptionCreateRequest,
  SubscriptionUpdateRequest,
  SubscriptionListResponse,
  SignalListResponse,
  SignalStatistics,
  TradingSignal,
  UpdateSignalStatusRequest,
  SignalQueryParams,
} from '@/types/strategy';

// ==================== 策略查詢 ====================

/**
 * 獲取所有可用策略列表
 */
export const getAvailableStrategies = async (): Promise<StrategyListResponse> => {
  return get<StrategyListResponse>(API_ENDPOINTS.STRATEGIES.AVAILABLE);
};

// ==================== 訂閱管理 ====================

/**
 * 獲取用戶所有訂閱
 */
export const getSubscriptions = async (
  activeOnly: boolean = false
): Promise<SubscriptionListResponse> => {
  return get<SubscriptionListResponse>(
    API_ENDPOINTS.STRATEGIES.SUBSCRIPTIONS.LIST,
    { active_only: activeOnly }
  );
};

/**
 * 創建新的策略訂閱
 */
export const createSubscription = async (
  data: SubscriptionCreateRequest
): Promise<Subscription> => {
  return post<Subscription>(
    API_ENDPOINTS.STRATEGIES.SUBSCRIPTIONS.CREATE,
    data
  );
};

/**
 * 更新訂閱配置
 */
export const updateSubscription = async (
  subscriptionId: number,
  data: SubscriptionUpdateRequest
): Promise<Subscription> => {
  return put<Subscription>(
    API_ENDPOINTS.STRATEGIES.SUBSCRIPTIONS.UPDATE(subscriptionId),
    data
  );
};

/**
 * 刪除訂閱
 */
export const deleteSubscription = async (
  subscriptionId: number,
  hardDelete: boolean = false
): Promise<void> => {
  return del<void>(
    `${API_ENDPOINTS.STRATEGIES.SUBSCRIPTIONS.DELETE(subscriptionId)}?hard_delete=${hardDelete}`
  );
};

/**
 * 切換訂閱啟用/停用狀態
 */
export const toggleSubscription = async (
  subscriptionId: number,
  isActive?: boolean
): Promise<Subscription> => {
  const url = isActive !== undefined
    ? `${API_ENDPOINTS.STRATEGIES.SUBSCRIPTIONS.TOGGLE(subscriptionId)}?is_active=${isActive}`
    : API_ENDPOINTS.STRATEGIES.SUBSCRIPTIONS.TOGGLE(subscriptionId);

  return post<Subscription>(url);
};

// ==================== 信號查詢 ====================

/**
 * 獲取用戶的交易信號
 */
export const getSignals = async (
  params: SignalQueryParams = {}
): Promise<SignalListResponse> => {
  return get<SignalListResponse>(
    API_ENDPOINTS.STRATEGIES.SIGNALS.LIST,
    params
  );
};

/**
 * 獲取信號統計資訊
 */
export const getSignalStatistics = async (
  dateFrom?: string,
  dateTo?: string
): Promise<SignalStatistics> => {
  const params: any = {};
  if (dateFrom) params.date_from = dateFrom;
  if (dateTo) params.date_to = dateTo;

  return get<SignalStatistics>(
    API_ENDPOINTS.STRATEGIES.SIGNALS.STATISTICS,
    params
  );
};

/**
 * 更新信號狀態
 */
export const updateSignalStatus = async (
  signalId: number,
  data: UpdateSignalStatusRequest
): Promise<TradingSignal> => {
  return put<TradingSignal>(
    API_ENDPOINTS.STRATEGIES.SIGNALS.UPDATE_STATUS(signalId),
    data
  );
};

/**
 * 手動觸發信號生成（批量）
 */
export const generateSignals = async (
  userId?: string
): Promise<{ message: string; subscriptions_processed: number; estimated_time: string }> => {
  const url = userId
    ? `${API_ENDPOINTS.STRATEGIES.SIGNALS.GENERATE}?user_id=${userId}`
    : API_ENDPOINTS.STRATEGIES.SIGNALS.GENERATE;

  return post<{ message: string; subscriptions_processed: number; estimated_time: string }>(url);
};
