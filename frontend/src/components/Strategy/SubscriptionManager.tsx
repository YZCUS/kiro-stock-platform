/**
 * 訂閱管理器 - 管理策略訂閱
 */
'use client';

import React, { useState, useEffect } from 'react';
import { useAppDispatch, useAppSelector } from '@/store';
import {
  fetchAvailableStrategies,
  fetchSubscriptions,
  createSubscription,
  updateSubscription,
  deleteSubscription,
  toggleSubscription,
  selectAvailableStrategies,
  selectSubscriptions,
  selectSubscriptionsLoading,
} from '@/store/slices/strategySlice';
import { addToast } from '@/store/slices/uiSlice';
import { Button } from '@/components/ui/button';
import { Plus, RefreshCw } from 'lucide-react';
import SubscriptionCard from './SubscriptionCard';
import SubscriptionModal from './SubscriptionModal';
import { Subscription, SubscriptionCreateRequest, SubscriptionUpdateRequest } from '@/types/strategy';

export default function SubscriptionManager() {
  const dispatch = useAppDispatch();
  const availableStrategies = useAppSelector(selectAvailableStrategies);
  const subscriptions = useAppSelector(selectSubscriptions);
  const loading = useAppSelector(selectSubscriptionsLoading);

  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingSubscription, setEditingSubscription] = useState<Subscription | null>(null);

  // 載入數據
  useEffect(() => {
    dispatch(fetchAvailableStrategies());
    dispatch(fetchSubscriptions(false));
  }, [dispatch]);

  // 刷新訂閱列表
  const handleRefresh = () => {
    dispatch(fetchSubscriptions(false));
  };

  // 開啟新增 Modal
  const handleOpenAdd = () => {
    setEditingSubscription(null);
    setIsModalOpen(true);
  };

  // 開啟編輯 Modal
  const handleOpenEdit = (subscription: Subscription) => {
    setEditingSubscription(subscription);
    setIsModalOpen(true);
  };

  // 提交訂閱（新增或編輯）
  const handleSubmit = async (data: SubscriptionCreateRequest | SubscriptionUpdateRequest) => {
    try {
      if (editingSubscription) {
        // 更新訂閱
        await dispatch(updateSubscription({
          id: editingSubscription.id,
          data: data as SubscriptionUpdateRequest
        })).unwrap();

        dispatch(addToast({
          type: 'success',
          title: '成功',
          message: '訂閱已更新'
        }));
      } else {
        // 建立訂閱
        await dispatch(createSubscription(data as SubscriptionCreateRequest)).unwrap();

        dispatch(addToast({
          type: 'success',
          title: '成功',
          message: '訂閱已建立'
        }));
      }

      // 刷新列表
      dispatch(fetchSubscriptions(false));
    } catch (error: any) {
      dispatch(addToast({
        type: 'error',
        title: '錯誤',
        message: error || '操作失敗'
      }));
      throw error;
    }
  };

  // 刪除訂閱
  const handleDelete = async (subscriptionId: number) => {
    if (!confirm('確定要刪除此訂閱嗎？')) {
      return;
    }

    try {
      await dispatch(deleteSubscription({ id: subscriptionId })).unwrap();

      dispatch(addToast({
        type: 'success',
        title: '成功',
        message: '訂閱已刪除'
      }));
    } catch (error: any) {
      dispatch(addToast({
        type: 'error',
        title: '錯誤',
        message: error || '刪除失敗'
      }));
    }
  };

  // 切換訂閱狀態
  const handleToggle = async (subscriptionId: number) => {
    try {
      await dispatch(toggleSubscription({ id: subscriptionId })).unwrap();

      dispatch(addToast({
        type: 'success',
        title: '成功',
        message: '訂閱狀態已更新'
      }));
    } catch (error: any) {
      dispatch(addToast({
        type: 'error',
        title: '錯誤',
        message: error || '切換失敗'
      }));
    }
  };

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-gray-900">策略訂閱管理</h2>
        <div className="flex gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={handleRefresh}
            disabled={loading}
          >
            <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
            刷新
          </Button>
          <Button
            size="sm"
            onClick={handleOpenAdd}
          >
            <Plus className="h-4 w-4 mr-2" />
            新增策略
          </Button>
        </div>
      </div>

      {/* 訂閱列表 */}
      {loading && subscriptions.length === 0 ? (
        <div className="text-center py-12">
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900"></div>
          <p className="mt-2 text-gray-600">載入中...</p>
        </div>
      ) : subscriptions.length === 0 ? (
        <div className="text-center py-12 bg-gray-50 rounded-lg border-2 border-dashed">
          <p className="text-gray-600 mb-4">尚未訂閱任何策略</p>
          <Button onClick={handleOpenAdd}>
            <Plus className="h-4 w-4 mr-2" />
            開始訂閱
          </Button>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4">
          {subscriptions.map((subscription) => (
            <SubscriptionCard
              key={subscription.id}
              subscription={subscription}
              onEdit={handleOpenEdit}
              onDelete={handleDelete}
              onToggle={handleToggle}
            />
          ))}
        </div>
      )}

      {/* Modal */}
      <SubscriptionModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        strategies={availableStrategies}
        subscription={editingSubscription}
        onSubmit={handleSubmit}
      />
    </div>
  );
}
