/**
 * 訂閱管理器 - 管理策略訂閱
 */
"use client";

import React, { useCallback, useEffect, useMemo, useState } from "react";
import { useAppDispatch, useAppSelector } from "@/store";
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
} from "@/store/slices/strategySlice";
import { fetchStockLists } from "@/store/slices/stockListSlice";
import { addToast } from "@/store/slices/uiSlice";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { AlertCircle, Plus, RefreshCw, Search } from "lucide-react";
import SubscriptionCard from "./SubscriptionCard";
import SubscriptionModal from "./SubscriptionModal";
import {
  Subscription,
  SubscriptionCreateRequest,
  SubscriptionUpdateRequest,
} from "@/types/strategy";

type SubscriptionStatusFilter = "all" | "active" | "inactive";

const getErrorMessage = (error: unknown, fallback: string) =>
  typeof error === "string" ? error : fallback;

export default function SubscriptionManager() {
  const dispatch = useAppDispatch();
  const availableStrategies = useAppSelector(selectAvailableStrategies);
  const subscriptions = useAppSelector(selectSubscriptions);
  const loading = useAppSelector(selectSubscriptionsLoading);
  const stockLists = useAppSelector((state) => state.stockList.lists);

  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingSubscription, setEditingSubscription] =
    useState<Subscription | null>(null);
  const [searchTerm, setSearchTerm] = useState("");
  const [statusFilter, setStatusFilter] =
    useState<SubscriptionStatusFilter>("all");
  const [loadError, setLoadError] = useState<string | null>(null);

  const strategyNameByType = useMemo(() => {
    return new Map(
      availableStrategies.map((strategy) => [strategy.type, strategy.name]),
    );
  }, [availableStrategies]);

  const activeCount = subscriptions.filter(
    (subscription) => subscription.is_active,
  ).length;
  const filteredSubscriptions = useMemo(() => {
    const query = searchTerm.trim().toLowerCase();

    return subscriptions.filter((subscription) => {
      if (statusFilter === "active" && !subscription.is_active) return false;
      if (statusFilter === "inactive" && subscription.is_active) return false;
      if (!query) return true;

      const parameterText = Object.values(subscription.parameters || {})
        .map((value) => String(value))
        .join(" ");
      const listText = (subscription.stock_lists || [])
        .map((list) => list.name)
        .join(" ");
      const searchableText = [
        subscription.strategy_name,
        strategyNameByType.get(subscription.strategy_type),
        subscription.strategy_type,
        parameterText,
        listText,
      ]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();

      return searchableText.includes(query);
    });
  }, [searchTerm, statusFilter, strategyNameByType, subscriptions]);

  const loadSubscriptions = useCallback(async () => {
    setLoadError(null);
    try {
      await dispatch(fetchSubscriptions(false)).unwrap();
    } catch (error) {
      setLoadError(getErrorMessage(error, "無法載入策略訂閱"));
    }
  }, [dispatch]);

  useEffect(() => {
    dispatch(fetchAvailableStrategies());
    dispatch(fetchStockLists());
    void loadSubscriptions();
  }, [dispatch, loadSubscriptions]);

  // 刷新訂閱列表
  const handleRefresh = () => {
    void loadSubscriptions();
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
  const handleSubmit = async (
    data: SubscriptionCreateRequest | SubscriptionUpdateRequest,
  ) => {
    try {
      if (editingSubscription) {
        // 更新訂閱
        await dispatch(
          updateSubscription({
            id: editingSubscription.id,
            data: data as SubscriptionUpdateRequest,
          }),
        ).unwrap();

        dispatch(
          addToast({
            type: "success",
            title: "成功",
            message: "訂閱已更新",
          }),
        );
      } else {
        // 建立訂閱
        await dispatch(
          createSubscription(data as SubscriptionCreateRequest),
        ).unwrap();

        dispatch(
          addToast({
            type: "success",
            title: "成功",
            message: "訂閱已建立",
          }),
        );
      }

      // 刷新列表
      await loadSubscriptions();
    } catch (error: unknown) {
      dispatch(
        addToast({
          type: "error",
          title: "錯誤",
          message: getErrorMessage(error, "操作失敗"),
        }),
      );
      throw error;
    }
  };

  // 刪除訂閱
  const handleDelete = async (subscriptionId: number) => {
    if (!confirm("確定要刪除此訂閱嗎？")) {
      return;
    }

    try {
      await dispatch(deleteSubscription({ id: subscriptionId })).unwrap();

      dispatch(
        addToast({
          type: "success",
          title: "成功",
          message: "訂閱已刪除",
        }),
      );
    } catch (error: unknown) {
      dispatch(
        addToast({
          type: "error",
          title: "錯誤",
          message: getErrorMessage(error, "刪除失敗"),
        }),
      );
    }
  };

  // 切換訂閱狀態
  const handleToggle = async (subscriptionId: number) => {
    try {
      await dispatch(toggleSubscription({ id: subscriptionId })).unwrap();

      dispatch(
        addToast({
          type: "success",
          title: "成功",
          message: "訂閱狀態已更新",
        }),
      );
    } catch (error: unknown) {
      dispatch(
        addToast({
          type: "error",
          title: "錯誤",
          message: getErrorMessage(error, "切換失敗"),
        }),
      );
    }
  };

  return (
    <section className="space-y-4" aria-labelledby="subscription-manager-title">
      {/* Header */}
      <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <h2
            id="subscription-manager-title"
            className="text-lg font-semibold text-gray-950"
          >
            策略訂閱
          </h2>
          <p className="mt-1 text-sm text-gray-500">
            {subscriptions.length} 個訂閱，{activeCount} 個啟用
          </p>
        </div>
        <div className="flex shrink-0 gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={handleRefresh}
            disabled={loading}
          >
            <RefreshCw
              className={`mr-2 h-4 w-4 ${loading ? "animate-spin" : ""}`}
            />
            刷新
          </Button>
          <Button size="sm" onClick={handleOpenAdd}>
            <Plus className="mr-2 h-4 w-4" />
            新增策略
          </Button>
        </div>
      </div>

      <div className="rounded-lg border border-gray-200 bg-white p-3">
        <div className="flex flex-col gap-3 xl:flex-row xl:items-center xl:justify-between">
          <div className="flex flex-wrap items-center gap-3 text-sm text-gray-600">
            <span>
              全部{" "}
              <span className="font-semibold text-gray-900">
                {subscriptions.length}
              </span>
            </span>
            <span>
              啟用{" "}
              <span className="font-semibold text-emerald-700">
                {activeCount}
              </span>
            </span>
            <span>
              停用{" "}
              <span className="font-semibold text-gray-700">
                {subscriptions.length - activeCount}
              </span>
            </span>
          </div>

          <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
            <div className="relative sm:w-64">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
              <input
                aria-label="搜尋策略訂閱"
                value={searchTerm}
                onChange={(event) => setSearchTerm(event.target.value)}
                placeholder="搜尋策略、模型或清單"
                className="h-9 w-full rounded-md border border-gray-200 bg-white pl-9 pr-3 text-sm outline-none focus:border-gray-400"
              />
            </div>
            <div className="inline-flex rounded-md border border-gray-200 bg-gray-50 p-1">
              {[
                ["all", "全部"],
                ["active", "啟用"],
                ["inactive", "停用"],
              ].map(([value, label]) => (
                <button
                  key={value}
                  type="button"
                  onClick={() =>
                    setStatusFilter(value as SubscriptionStatusFilter)
                  }
                  aria-pressed={statusFilter === value}
                  className={`rounded px-3 py-1.5 text-xs font-medium ${
                    statusFilter === value
                      ? "bg-white text-gray-900 shadow-sm"
                      : "text-gray-500 hover:text-gray-900"
                  }`}
                >
                  {label}
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>

      {loadError && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <span>{loadError}</span>
            <Button variant="outline" size="sm" onClick={handleRefresh}>
              <RefreshCw className="h-4 w-4" />
              重試
            </Button>
          </AlertDescription>
        </Alert>
      )}

      {/* 訂閱列表 */}
      {loading && subscriptions.length === 0 ? (
        <div className="text-center py-12">
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900"></div>
          <p className="mt-2 text-gray-600">載入中...</p>
        </div>
      ) : loadError &&
        subscriptions.length === 0 ? null : subscriptions.length === 0 ? (
        <div className="text-center py-12 bg-gray-50 rounded-lg border-2 border-dashed">
          <p className="text-gray-600 mb-4">尚未訂閱任何策略</p>
          <Button onClick={handleOpenAdd}>
            <Plus className="mr-2 h-4 w-4" />
            開始訂閱
          </Button>
        </div>
      ) : filteredSubscriptions.length === 0 ? (
        <div className="rounded-lg border border-dashed bg-gray-50 py-10 text-center">
          <p className="text-sm text-gray-600">沒有符合條件的策略訂閱</p>
        </div>
      ) : (
        <div className="overflow-hidden rounded-lg border border-gray-200 bg-white">
          <div className="hidden grid-cols-[minmax(190px,1.2fr)_minmax(220px,1.4fr)_minmax(260px,1.5fr)_minmax(140px,auto)] border-b border-gray-100 bg-gray-50 px-4 py-2 text-xs font-medium text-gray-500 lg:grid">
            <div>策略</div>
            <div>參數</div>
            <div>監控範圍</div>
            <div className="text-right">操作</div>
          </div>
          <div className="divide-y divide-gray-100">
            {filteredSubscriptions.map((subscription) => (
              <SubscriptionCard
                key={subscription.id}
                subscription={subscription}
                strategies={availableStrategies}
                onEdit={handleOpenEdit}
                onDelete={handleDelete}
                onToggle={handleToggle}
              />
            ))}
          </div>
        </div>
      )}

      {/* Modal */}
      <SubscriptionModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        strategies={availableStrategies}
        stockLists={stockLists}
        subscription={editingSubscription}
        onSubmit={handleSubmit}
      />
    </section>
  );
}
