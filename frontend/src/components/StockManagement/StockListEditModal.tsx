/**
 * 清單編輯 Modal
 * 支援修改清單名稱和調整股票順序
 */
'use client';

import React, { useState, useEffect } from 'react';
import { useAppDispatch, useAppSelector } from '@/store';
import { updateStockList, fetchListStocks } from '@/store/slices/stockListSlice';
import { addToast } from '@/store/slices/uiSlice';
import { X, GripVertical, Save } from 'lucide-react';

interface StockListEditModalProps {
  isOpen: boolean;
  onClose: () => void;
  list: {
    id: number;
    name: string;
    description?: string;
    stocks_count: number;
  };
}

interface StockInList {
  id: number;
  stock_id: number;
  list_id: number;
  position: number;
  stock: {
    id: number;
    symbol: string;
    name: string;
    market: string;
  };
}

export default function StockListEditModal({ isOpen, onClose, list }: StockListEditModalProps) {
  const dispatch = useAppDispatch();
  const { currentListStocks } = useAppSelector((state) => state.stockList);

  const [listName, setListName] = useState(list.name);
  const [description, setDescription] = useState(list.description || '');
  const [stocks, setStocks] = useState<StockInList[]>([]);
  const [draggedIndex, setDraggedIndex] = useState<number | null>(null);
  const [isSaving, setIsSaving] = useState(false);

  // 載入清單中的股票
  useEffect(() => {
    if (isOpen && list.id) {
      dispatch(fetchListStocks(list.id));
    }
  }, [isOpen, list.id, dispatch]);

  // 更新本地股票列表
  useEffect(() => {
    if (currentListStocks.length > 0) {
      const sortedStocks = [...currentListStocks].sort((a, b) =>
        (a.position || 0) - (b.position || 0)
      );
      setStocks(sortedStocks);
    }
  }, [currentListStocks]);

  // 重置表單
  useEffect(() => {
    if (isOpen) {
      setListName(list.name);
      setDescription(list.description || '');
    }
  }, [isOpen, list]);

  const handleDragStart = (index: number) => {
    setDraggedIndex(index);
  };

  const handleDragOver = (e: React.DragEvent, index: number) => {
    e.preventDefault();

    if (draggedIndex === null || draggedIndex === index) return;

    const newStocks = [...stocks];
    const draggedItem = newStocks[draggedIndex];

    // 移除被拖動的項目
    newStocks.splice(draggedIndex, 1);
    // 在新位置插入
    newStocks.splice(index, 0, draggedItem);

    setStocks(newStocks);
    setDraggedIndex(index);
  };

  const handleDragEnd = () => {
    setDraggedIndex(null);
  };

  const handleMoveUp = (index: number) => {
    if (index === 0) return;
    const newStocks = [...stocks];
    [newStocks[index - 1], newStocks[index]] = [newStocks[index], newStocks[index - 1]];
    setStocks(newStocks);
  };

  const handleMoveDown = (index: number) => {
    if (index === stocks.length - 1) return;
    const newStocks = [...stocks];
    [newStocks[index], newStocks[index + 1]] = [newStocks[index + 1], newStocks[index]];
    setStocks(newStocks);
  };

  const handleSave = async () => {
    if (!listName.trim()) {
      dispatch(addToast({
        type: 'warning',
        title: '警告',
        message: '清單名稱不能為空'
      }));
      return;
    }

    setIsSaving(true);

    try {
      // 更新清單名稱和描述
      await dispatch(updateStockList({
        id: list.id,
        data: {
          name: listName.trim(),
          description: description.trim() || undefined
        }
      })).unwrap();

      // TODO: 這裡需要後端 API 支援更新股票順序
      // 暫時先只更新清單名稱
      // 如果後端有 API，可以在這裡調用
      // await updateStockPositions(list.id, stocks.map((s, idx) => ({
      //   stock_id: s.stock_id,
      //   position: idx
      // })));

      dispatch(addToast({
        type: 'success',
        title: '成功',
        message: '清單已更新'
      }));

      onClose();
    } catch (error: any) {
      dispatch(addToast({
        type: 'error',
        title: '錯誤',
        message: error?.message || error?.toString() || '更新清單失敗'
      }));
    } finally {
      setIsSaving(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      <div className="flex items-center justify-center min-h-screen px-4 pt-4 pb-20 text-center sm:block sm:p-0">
        {/* 背景遮罩 */}
        <div
          className="fixed inset-0 transition-opacity bg-gray-500 bg-opacity-75"
          onClick={onClose}
        />

        {/* Modal 內容 */}
        <div className="inline-block align-bottom bg-white rounded-lg text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-2xl sm:w-full">
          {/* 標題列 */}
          <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
            <h3 className="text-lg font-medium text-gray-900">
              編輯清單
            </h3>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-500 focus:outline-none"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* 表單內容 */}
          <div className="px-6 py-4 max-h-[70vh] overflow-y-auto">
            {/* 清單名稱 */}
            <div className="mb-4">
              <label htmlFor="listName" className="block text-sm font-medium text-gray-700 mb-1">
                清單名稱 <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                id="listName"
                value={listName}
                onChange={(e) => setListName(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="請輸入清單名稱"
              />
            </div>

            {/* 清單描述 */}
            <div className="mb-6">
              <label htmlFor="description" className="block text-sm font-medium text-gray-700 mb-1">
                描述（可選）
              </label>
              <textarea
                id="description"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                rows={2}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="請輸入清單描述"
              />
            </div>

            {/* 股票列表 */}
            <div>
              <div className="flex items-center justify-between mb-3">
                <label className="block text-sm font-medium text-gray-700">
                  股票順序 ({stocks.length})
                </label>
                <p className="text-xs text-gray-500">
                  拖動或使用箭頭調整順序
                </p>
              </div>

              {stocks.length === 0 ? (
                <div className="text-center py-8 text-gray-500">
                  此清單暫無股票
                </div>
              ) : (
                <div className="space-y-2">
                  {stocks.map((item, index) => (
                    <div
                      key={item.id}
                      draggable
                      onDragStart={() => handleDragStart(index)}
                      onDragOver={(e) => handleDragOver(e, index)}
                      onDragEnd={handleDragEnd}
                      className={`flex items-center gap-2 p-3 bg-white border border-gray-200 rounded-md hover:border-blue-300 transition-colors ${
                        draggedIndex === index ? 'opacity-50 border-blue-400' : ''
                      }`}
                    >
                      {/* 拖動手柄 */}
                      <div className="cursor-move text-gray-400 hover:text-gray-600">
                        <GripVertical className="w-5 h-5" />
                      </div>

                      {/* 股票資訊 */}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="font-medium text-gray-900">
                            {item.stock.symbol}
                          </span>
                          <span className="text-sm text-gray-600 truncate">
                            {item.stock.name}
                          </span>
                          <span className={`text-xs px-2 py-0.5 rounded ${
                            item.stock.market === 'TW'
                              ? 'bg-blue-100 text-blue-700'
                              : 'bg-green-100 text-green-700'
                          }`}>
                            {item.stock.market}
                          </span>
                        </div>
                      </div>

                      {/* 上下移動按鈕 */}
                      <div className="flex flex-col gap-1">
                        <button
                          onClick={() => handleMoveUp(index)}
                          disabled={index === 0}
                          className="p-1 text-gray-400 hover:text-gray-600 disabled:opacity-30 disabled:cursor-not-allowed"
                          title="上移"
                        >
                          ▲
                        </button>
                        <button
                          onClick={() => handleMoveDown(index)}
                          disabled={index === stocks.length - 1}
                          className="p-1 text-gray-400 hover:text-gray-600 disabled:opacity-30 disabled:cursor-not-allowed"
                          title="下移"
                        >
                          ▼
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* 底部按鈕 */}
          <div className="px-6 py-4 bg-gray-50 border-t border-gray-200 flex justify-end gap-3">
            <button
              onClick={onClose}
              className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
            >
              取消
            </button>
            <button
              onClick={handleSave}
              disabled={isSaving || !listName.trim()}
              className="px-4 py-2 text-sm font-medium text-white bg-blue-600 border border-transparent rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:bg-gray-400 disabled:cursor-not-allowed flex items-center gap-2"
            >
              {isSaving ? (
                <>
                  <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                  </svg>
                  儲存中...
                </>
              ) : (
                <>
                  <Save className="w-4 h-4" />
                  儲存
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
