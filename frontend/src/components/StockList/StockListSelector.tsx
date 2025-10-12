/**
 * 股票清單選擇器組件
 */
'use client';

import React, { useState, useEffect, useRef } from 'react';
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
import { Plus, Edit2, Trash2, ChevronDown, Check } from 'lucide-react';
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
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

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
      setIsDropdownOpen(false);
    }
  };

  const handleCreateList = () => {
    setEditingList(null);
    setIsModalOpen(true);
    setIsDropdownOpen(false);
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
      {/* 自定義下拉選單 */}
      <div className="relative" ref={dropdownRef}>
        <button
          onClick={() => setIsDropdownOpen(!isDropdownOpen)}
          className="flex items-center justify-between bg-white border border-gray-300 rounded-md pl-3 pr-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 min-w-[220px] hover:bg-gray-50"
          disabled={loading}
        >
          <span className="truncate">
            {loading ? '載入中...' :
             currentList ? `${currentList.name} (${currentList.stocks_count})${currentList.is_default ? ' ⭐' : ''}` :
             lists.length === 0 ? '暫無清單' : '請選擇清單'}
          </span>
          <ChevronDown className={`w-4 h-4 ml-2 transition-transform ${isDropdownOpen ? 'transform rotate-180' : ''}`} />
        </button>

        {/* 下拉選單內容 */}
        {isDropdownOpen && (
          <div className="absolute z-50 mt-1 w-full bg-white border border-gray-300 rounded-md shadow-lg max-h-80 overflow-auto">
            {/* 清單列表 */}
            {lists.length > 0 ? (
              <div className="py-1">
                {lists.map((list) => (
                  <button
                    key={list.id}
                    onClick={() => handleSelectList(list.id)}
                    className={`w-full text-left px-3 py-2 text-sm hover:bg-gray-100 flex items-center justify-between ${
                      currentList?.id === list.id ? 'bg-blue-50 text-blue-600' : 'text-gray-900'
                    }`}
                  >
                    <span className="truncate">
                      {list.name} ({list.stocks_count})
                      {list.is_default && ' ⭐'}
                    </span>
                    {currentList?.id === list.id && (
                      <Check className="w-4 h-4 flex-shrink-0 ml-2" />
                    )}
                  </button>
                ))}
              </div>
            ) : (
              <div className="py-3 px-3 text-sm text-gray-500 text-center">
                {loading ? '載入中...' : '暫無清單'}
              </div>
            )}

            {/* 分隔線 */}
            {!loading && <div className="border-t border-gray-200"></div>}

            {/* 新建清單選項 */}
            {!loading && (
              <button
                onClick={handleCreateList}
                className="w-full text-left px-3 py-2 text-sm text-blue-600 hover:bg-blue-50 flex items-center gap-2 font-medium"
              >
                <Plus className="w-4 h-4" />
                新建清單
              </button>
            )}
          </div>
        )}
      </div>

      {/* 清單操作按鈕 */}
      {currentList && (
        <div className="flex items-center gap-2">
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
        </div>
      )}

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
