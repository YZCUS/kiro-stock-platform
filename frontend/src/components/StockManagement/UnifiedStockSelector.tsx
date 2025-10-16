/**
 * 統一的股票選擇器組件
 * 整合清單選擇和視圖模式（清單股票/我的持倉/自選股）
 */
'use client';

import React, { useState, useEffect, useRef } from 'react';
import { useAppDispatch, useAppSelector } from '@/store';
import {
  fetchStockLists,
  setCurrentList,
  createStockList,
  deleteStockList
} from '@/store/slices/stockListSlice';
import { addToast } from '@/store/slices/uiSlice';
import { Plus, ChevronDown, Trash2, Check, Edit2, ArrowUpDown } from 'lucide-react';
import StockListModal from '../StockList/StockListModal';
import StockListEditModal from './StockListEditModal';
import StockListReorderModal from './StockListReorderModal';
import * as stockListApi from '@/services/stockListApi';

interface UnifiedStockSelectorProps {
  onListChange?: (listId: number | null) => void;
  viewMode: 'all' | 'portfolio';
  onViewModeChange: (mode: 'all' | 'portfolio') => void;
}

export default function UnifiedStockSelector({
  onListChange,
  viewMode,
  onViewModeChange
}: UnifiedStockSelectorProps) {
  const dispatch = useAppDispatch();
  const { lists, currentList, loading } = useAppSelector((state) => state.stockList);
  const { isAuthenticated } = useAppSelector((state) => state.auth);

  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [isReorderModalOpen, setIsReorderModalOpen] = useState(false);
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // 載入清單 - 只要已認證就載入
  useEffect(() => {
    if (isAuthenticated && lists.length === 0 && !loading) {
      dispatch(fetchStockLists());
    }
  }, [isAuthenticated, lists.length, loading, dispatch]);

  // 設置預設清單
  useEffect(() => {
    if (lists.length > 0 && !currentList && viewMode === 'all') {
      const defaultList = lists.find(l => l.is_default) || lists[0];
      dispatch(setCurrentList(defaultList));
      onListChange?.(defaultList.id);
    }
  }, [lists, currentList, dispatch, onListChange, viewMode]);

  // 點擊外部關閉下拉選單
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsDropdownOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleSelectList = (listId: number) => {
    const selectedList = lists.find(l => l.id === listId);
    if (selectedList) {
      dispatch(setCurrentList(selectedList));
      onListChange?.(listId);
      onViewModeChange('all');
      setIsDropdownOpen(false);
    }
  };

  const handleSelectViewMode = (mode: 'portfolio') => {
    onViewModeChange(mode);
    onListChange?.(null);
    setIsDropdownOpen(false);
  };

  const handleCreateList = () => {
    setIsModalOpen(true);
    setIsDropdownOpen(false);
  };

  const handleDeleteCurrentList = async () => {
    if (!currentList) return;

    if (lists.length === 1) {
      dispatch(addToast({
        type: 'warning',
        title: '無法刪除',
        message: '至少需要保留一個清單'
      }));
      return;
    }

    if (!confirm(`確定要刪除清單「${currentList.name}」嗎？`)) {
      return;
    }

    try {
      await dispatch(deleteStockList(currentList.id)).unwrap();

      dispatch(addToast({
        type: 'success',
        title: '成功',
        message: '已成功刪除清單'
      }));

      // 切換到另一個清單
      const remainingLists = lists.filter(l => l.id !== currentList.id);
      if (remainingLists.length > 0) {
        const nextList = remainingLists[0];
        dispatch(setCurrentList(nextList));
        onListChange?.(nextList.id);
      }
    } catch (error: any) {
      dispatch(addToast({
        type: 'error',
        title: '錯誤',
        message: error?.message || error?.toString() || '刪除清單失敗'
      }));
    }
  };

  const handleSaveList = async (data: { name: string; description?: string }) => {
    try {
      const newList = await dispatch(createStockList(data)).unwrap();

      dispatch(addToast({
        type: 'success',
        title: '成功',
        message: '已成功建立清單'
      }));

      // 自動切換到新建立的清單
      dispatch(setCurrentList(newList));
      onListChange?.(newList.id);
      onViewModeChange('all');
      setIsModalOpen(false);
    } catch (error: any) {
      dispatch(addToast({
        type: 'error',
        title: '錯誤',
        message: error?.message || error?.toString() || '建立清單失敗'
      }));
    }
  };

  const handleSaveReorder = async (reorderedLists: any[]) => {
    try {
      // 準備排序數據
      const list_orders = reorderedLists.map((list, index) => ({
        id: list.id,
        sort_order: index
      }));

      // 調用 API
      await stockListApi.reorderStockLists({ list_orders });

      // 重新載入清單
      await dispatch(fetchStockLists());

      dispatch(addToast({
        type: 'success',
        title: '成功',
        message: '清單順序已更新'
      }));

      setIsReorderModalOpen(false);
    } catch (error: any) {
      dispatch(addToast({
        type: 'error',
        title: '錯誤',
        message: error?.message || error?.toString() || '更新順序失敗'
      }));
    }
  };

  // 獲取當前顯示的標籤
  const getCurrentLabel = () => {
    if (viewMode === 'portfolio') return '我的持倉';
    if (currentList) {
      return `${currentList.name} (${currentList.stocks_count})${currentList.is_default ? ' ⭐' : ''}`;
    }
    return lists.length === 0 ? '暫無清單' : '請選擇清單';
  };

  if (!isAuthenticated) {
    return null;
  }

  return (
    <div className="flex items-center gap-2">
      {/* 統一下拉選單 */}
      <div className="relative" ref={dropdownRef}>
        <button
          onClick={() => setIsDropdownOpen(!isDropdownOpen)}
          className="flex items-center justify-between bg-white border border-gray-300 rounded-md pl-3 pr-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 min-w-[240px] hover:bg-gray-50"
          disabled={loading}
        >
          <span className="truncate">
            {loading ? '載入中...' : getCurrentLabel()}
          </span>
          <ChevronDown className={`w-4 h-4 ml-2 transition-transform ${isDropdownOpen ? 'transform rotate-180' : ''}`} />
        </button>

        {isDropdownOpen && (
          <div className="absolute z-50 mt-1 w-full bg-white border border-gray-300 rounded-md shadow-lg max-h-80 overflow-auto">
            {/* 固定視圖選項區域 */}
            <div className="py-1 border-b border-gray-200 bg-gray-50">
              <div className="px-3 py-1 text-xs font-semibold text-gray-500 uppercase tracking-wider">
                快速視圖
              </div>
              <button
                onClick={() => handleSelectViewMode('portfolio')}
                className={`w-full text-left px-3 py-2 text-sm hover:bg-blue-50 flex items-center justify-between ${
                  viewMode === 'portfolio' ? 'bg-blue-50 text-blue-600' : 'text-gray-700'
                }`}
              >
                <span>我的持倉</span>
                {viewMode === 'portfolio' && <Check className="w-4 h-4" />}
              </button>
            </div>

            {/* 自訂清單區域 */}
            <div className="py-1">
              <div className="px-3 py-1 text-xs font-semibold text-gray-500 uppercase tracking-wider">
                自訂清單
              </div>
              {lists.length > 0 ? (
                lists.map((list) => (
                  <button
                    key={list.id}
                    onClick={() => handleSelectList(list.id)}
                    className={`w-full text-left px-3 py-2 text-sm hover:bg-blue-50 flex items-center justify-between ${
                      viewMode === 'all' && currentList?.id === list.id
                        ? 'bg-blue-50 text-blue-600'
                        : 'text-gray-900'
                    }`}
                  >
                    <span className="truncate">
                      {list.name} ({list.stocks_count}){list.is_default ? ' ⭐' : ''}
                    </span>
                    {viewMode === 'all' && currentList?.id === list.id && (
                      <Check className="w-4 h-4 flex-shrink-0 ml-2" />
                    )}
                  </button>
                ))
              ) : (
                <div className="py-3 px-3 text-sm text-gray-500 text-center">
                  {loading ? '載入中...' : '暫無自訂清單'}
                </div>
              )}
            </div>

            {/* 新建清單和排序選項 */}
            {!loading && (
              <>
                <div className="border-t border-gray-200"></div>
                <button
                  onClick={handleCreateList}
                  className="w-full text-left px-3 py-2 text-sm text-blue-600 hover:bg-blue-50 flex items-center gap-2 font-medium"
                >
                  <Plus className="w-4 h-4" />
                  新建清單
                </button>
                {lists.length > 1 && (
                  <button
                    onClick={() => {
                      setIsReorderModalOpen(true);
                      setIsDropdownOpen(false);
                    }}
                    className="w-full text-left px-3 py-2 text-sm text-gray-700 hover:bg-gray-50 flex items-center gap-2"
                  >
                    <ArrowUpDown className="w-4 h-4" />
                    調整清單順序
                  </button>
                )}
              </>
            )}
          </div>
        )}
      </div>

      {/* 編輯和刪除按鈕 - 只在選擇自訂清單時顯示 */}
      {viewMode === 'all' && currentList && (
        <>
          <button
            onClick={() => setIsEditModalOpen(true)}
            className="p-2 text-blue-600 hover:bg-blue-50 rounded-md transition-colors"
            title="編輯清單"
          >
            <Edit2 className="w-4 h-4" />
          </button>
          {lists.length > 1 && (
            <button
              onClick={handleDeleteCurrentList}
              className="p-2 text-red-600 hover:bg-red-50 rounded-md transition-colors"
              title="刪除當前清單"
            >
              <Trash2 className="w-4 h-4" />
            </button>
          )}
        </>
      )}

      {/* 新建清單彈窗 */}
      <StockListModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onSave={handleSaveList}
        list={null}
      />

      {/* 編輯清單彈窗 */}
      {currentList && (
        <StockListEditModal
          isOpen={isEditModalOpen}
          onClose={() => setIsEditModalOpen(false)}
          list={currentList}
        />
      )}

      {/* 排序清單彈窗 */}
      <StockListReorderModal
        isOpen={isReorderModalOpen}
        onClose={() => setIsReorderModalOpen(false)}
        lists={lists}
        onSave={handleSaveReorder}
      />
    </div>
  );
}
