/**
 * 股票清單排序模態窗口
 */
'use client';

import React, { useState, useEffect } from 'react';
import { StockList } from '@/types';
import { GripVertical, X } from 'lucide-react';

interface StockListReorderModalProps {
  isOpen: boolean;
  onClose: () => void;
  lists: StockList[];
  onSave: (reorderedLists: StockList[]) => Promise<void>;
}

export default function StockListReorderModal({
  isOpen,
  onClose,
  lists,
  onSave
}: StockListReorderModalProps) {
  const [orderedLists, setOrderedLists] = useState<StockList[]>([]);
  const [isSaving, setIsSaving] = useState(false);
  const [draggedIndex, setDraggedIndex] = useState<number | null>(null);

  // 當 modal 打開或 lists 變化時，重置排序
  useEffect(() => {
    if (isOpen) {
      setOrderedLists([...lists].sort((a, b) => a.sort_order - b.sort_order));
    }
  }, [isOpen, lists]);

  const handleDragStart = (index: number) => {
    setDraggedIndex(index);
  };

  const handleDragOver = (e: React.DragEvent, index: number) => {
    e.preventDefault();

    if (draggedIndex === null || draggedIndex === index) return;

    const newLists = [...orderedLists];
    const draggedItem = newLists[draggedIndex];

    // 移除被拖動的項目
    newLists.splice(draggedIndex, 1);
    // 插入到新位置
    newLists.splice(index, 0, draggedItem);

    setOrderedLists(newLists);
    setDraggedIndex(index);
  };

  const handleDragEnd = () => {
    setDraggedIndex(null);
  };

  const handleSave = async () => {
    setIsSaving(true);
    try {
      // 更新 sort_order
      const reorderedLists = orderedLists.map((list, index) => ({
        ...list,
        sort_order: index
      }));

      await onSave(reorderedLists);
      onClose();
    } catch (error) {
      console.error('儲存排序失敗:', error);
    } finally {
      setIsSaving(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-6 w-full max-w-md animate-scale-in">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-medium text-gray-900">調整清單順序</h3>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <p className="text-sm text-gray-600 mb-4">
          拖動清單以調整顯示順序
        </p>

        <div className="space-y-2 mb-6 max-h-96 overflow-y-auto">
          {orderedLists.map((list, index) => (
            <div
              key={list.id}
              draggable
              onDragStart={() => handleDragStart(index)}
              onDragOver={(e) => handleDragOver(e, index)}
              onDragEnd={handleDragEnd}
              className={`flex items-center gap-3 p-3 bg-gray-50 border border-gray-200 rounded-md cursor-move hover:bg-gray-100 transition-colors ${
                draggedIndex === index ? 'opacity-50' : ''
              }`}
            >
              <GripVertical className="w-5 h-5 text-gray-400 flex-shrink-0" />
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="font-medium text-gray-900 truncate">
                    {list.name}
                  </span>
                  {list.is_default && (
                    <span className="text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded-full">
                      預設
                    </span>
                  )}
                </div>
                <span className="text-sm text-gray-500">
                  {list.stocks_count} 支股票
                </span>
              </div>
              <span className="text-sm text-gray-400 flex-shrink-0">
                #{index + 1}
              </span>
            </div>
          ))}
        </div>

        <div className="flex justify-end gap-3">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
            disabled={isSaving}
          >
            取消
          </button>
          <button
            onClick={handleSave}
            className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
            disabled={isSaving}
          >
            {isSaving ? (
              <>
                <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                儲存中...
              </>
            ) : (
              '儲存'
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
