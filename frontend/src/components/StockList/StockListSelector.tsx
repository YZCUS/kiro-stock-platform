/**
 * 股票清單選擇器組件
 */
'use client';

import React, { useState, useEffect } from 'react';
import { useAppDispatch, useAppSelector } from '@/store';
import {
  fetchStockLists,
  setCurrentList,
  createStockList,
  updateStockList,
  deleteStockList
} from '@/store/slices/stockListSlice';
import { addToast } from '@/store/slices/uiSlice';
import { Button } from '@/components/ui/button';
import { Plus, Edit2, Trash2, Check } from 'lucide-react';
import StockListModal from './StockListModal';

interface StockListSelectorProps {
  onListChange?: (listId: number | null) => void;
}

export default function StockListSelector({ onListChange }: StockListSelectorProps) {
  const dispatch = useAppDispatch();
  const { lists, currentList, loading } = useAppSelector((state) => state.stockList);
  const { isAuthenticated } = useAppSelector((state) => state.auth);

  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingList, setEditingList] = useState<any>(null);

  // 載入清單
  useEffect(() => {
    if (isAuthenticated) {
      dispatch(fetchStockLists());
    }
  }, [isAuthenticated, dispatch]);

  // 設置預設清單
  useEffect(() => {
    if (lists.length > 0 && !currentList) {
      const defaultList = lists.find(l => l.is_default) || lists[0];
      dispatch(setCurrentList(defaultList));
      onListChange?.(defaultList.id);
    }
  }, [lists, currentList, dispatch, onListChange]);

  const handleSelectList = (listId: number) => {
    const selectedList = lists.find(l => l.id === listId);
    if (selectedList) {
      dispatch(setCurrentList(selectedList));
      onListChange?.(listId);
    }
  };

  const handleCreateList = () => {
    setEditingList(null);
    setIsModalOpen(true);
  };

  const handleEditList = (list: any) => {
    setEditingList(list);
    setIsModalOpen(true);
  };

  const handleDeleteList = async (listId: number, listName: string) => {
    if (!confirm(`確定要刪除清單「${listName}」嗎？清單中的股票不會被刪除。`)) {
      return;
    }

    try {
      await dispatch(deleteStockList(listId)).unwrap();
      dispatch(addToast({
        type: 'success',
        title: '成功',
        message: '清單已刪除'
      }));

      // 如果刪除的是當前清單，切換到第一個清單
      if (currentList?.id === listId && lists.length > 1) {
        const nextList = lists.find(l => l.id !== listId);
        if (nextList) {
          dispatch(setCurrentList(nextList));
          onListChange?.(nextList.id);
        }
      }
    } catch (error: any) {
      dispatch(addToast({
        type: 'error',
        title: '錯誤',
        message: error || '刪除清單失敗'
      }));
    }
  };

  const handleSaveList = async (data: any) => {
    try {
      if (editingList) {
        // 更新
        await dispatch(updateStockList({
          listId: editingList.id,
          data
        })).unwrap();
        dispatch(addToast({
          type: 'success',
          title: '成功',
          message: '清單已更新'
        }));
      } else {
        // 創建
        const newList = await dispatch(createStockList(data)).unwrap();
        dispatch(addToast({
          type: 'success',
          title: '成功',
          message: '清單已創建'
        }));
        // 切換到新創建的清單
        dispatch(setCurrentList(newList));
        onListChange?.(newList.id);
      }
      setIsModalOpen(false);
    } catch (error: any) {
      dispatch(addToast({
        type: 'error',
        title: '錯誤',
        message: error || '操作失敗'
      }));
    }
  };

  if (!isAuthenticated) {
    return null;
  }

  return (
    <div className="flex items-center gap-3">
      {/* 清單選擇下拉選單 */}
      <div className="relative">
        <select
          value={currentList?.id || ''}
          onChange={(e) => handleSelectList(parseInt(e.target.value))}
          className="appearance-none bg-white border border-gray-300 rounded-md pl-3 pr-10 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 min-w-[200px]"
          disabled={loading}
        >
          {lists.length === 0 && (
            <option value="">載入中...</option>
          )}
          {lists.map((list) => (
            <option key={list.id} value={list.id}>
              {list.name} ({list.stocks_count})
              {list.is_default && ' ⭐'}
            </option>
          ))}
        </select>
        <div className="absolute inset-y-0 right-0 flex items-center pr-2 pointer-events-none">
          <svg className="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </div>
      </div>

      {/* 清單操作按鈕 */}
      <div className="flex items-center gap-2">
        <Button
          size="sm"
          variant="outline"
          onClick={handleCreateList}
          title="新建清單"
        >
          <Plus className="w-4 h-4 mr-1" />
          新建
        </Button>

        {currentList && (
          <>
            <Button
              size="sm"
              variant="outline"
              onClick={() => handleEditList(currentList)}
              title="編輯清單"
            >
              <Edit2 className="w-4 h-4" />
            </Button>

            {lists.length > 1 && (
              <Button
                size="sm"
                variant="outline"
                onClick={() => handleDeleteList(currentList.id, currentList.name)}
                title="刪除清單"
                className="text-red-600 hover:text-red-700 hover:border-red-300"
              >
                <Trash2 className="w-4 h-4" />
              </Button>
            )}
          </>
        )}
      </div>

      {/* 清單詳情提示 */}
      {currentList && currentList.description && (
        <div className="hidden lg:block text-sm text-gray-500 max-w-xs truncate">
          {currentList.description}
        </div>
      )}

      {/* 清單管理 Modal */}
      <StockListModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onSave={handleSaveList}
        list={editingList}
      />
    </div>
  );
}
