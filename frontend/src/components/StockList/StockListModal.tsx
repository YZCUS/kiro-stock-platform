/**
 * 股票清單編輯 Modal
 */
'use client';

import React, { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { X } from 'lucide-react';
import type { StockList } from '@/types';

interface StockListModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSave: (data: { name: string; description?: string; is_default?: boolean }) => void;
  list?: StockList | null;
}

export default function StockListModal({ isOpen, onClose, onSave, list }: StockListModalProps) {
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    is_default: false
  });
  const [errors, setErrors] = useState<{ name?: string }>({});

  useEffect(() => {
    if (isOpen) {
      if (list) {
        // 編輯模式
        setFormData({
          name: list.name,
          description: list.description || '',
          is_default: list.is_default
        });
      } else {
        // 新建模式
        setFormData({
          name: '',
          description: '',
          is_default: false
        });
      }
      setErrors({});
    }
  }, [isOpen, list]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    // 驗證
    const newErrors: { name?: string } = {};
    if (!formData.name.trim()) {
      newErrors.name = '清單名稱不能為空';
    } else if (formData.name.length > 100) {
      newErrors.name = '清單名稱不能超過 100 個字符';
    }

    if (Object.keys(newErrors).length > 0) {
      setErrors(newErrors);
      return;
    }

    // 提交
    onSave({
      name: formData.name.trim(),
      description: formData.description.trim() || undefined,
      is_default: formData.is_default
    });
  };

  const handleChange = (field: string, value: any) => {
    setFormData(prev => ({ ...prev, [field]: value }));
    // 清除該欄位的錯誤
    if (errors[field as keyof typeof errors]) {
      setErrors(prev => ({ ...prev, [field]: undefined }));
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-md mx-4">
        {/* Header */}
        <div className="px-6 py-4 border-b flex justify-between items-center">
          <h2 className="text-xl font-bold">
            {list ? '編輯清單' : '新建清單'}
          </h2>
          <Button variant="ghost" size="sm" onClick={onClose}>
            <X className="w-4 h-4" />
          </Button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {/* 清單名稱 */}
          <div>
            <Label htmlFor="name">
              清單名稱 <span className="text-red-500">*</span>
            </Label>
            <Input
              id="name"
              type="text"
              value={formData.name}
              onChange={(e) => handleChange('name', e.target.value)}
              placeholder="例如：我的科技股"
              maxLength={100}
              required
              className={errors.name ? 'border-red-500' : ''}
            />
            {errors.name && (
              <p className="text-sm text-red-500 mt-1">{errors.name}</p>
            )}
          </div>

          {/* 清單描述 */}
          <div>
            <Label htmlFor="description">描述（選填）</Label>
            <textarea
              id="description"
              value={formData.description}
              onChange={(e) => handleChange('description', e.target.value)}
              placeholder="簡短描述這個清單的用途"
              maxLength={500}
              rows={3}
              className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          {/* 設為預設 */}
          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              id="is_default"
              checked={formData.is_default}
              onChange={(e) => handleChange('is_default', e.target.checked)}
              className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
            />
            <Label htmlFor="is_default" className="cursor-pointer">
              設為預設清單
            </Label>
          </div>

          {/* 按鈕 */}
          <div className="flex gap-3 pt-2">
            <Button
              type="button"
              variant="outline"
              onClick={onClose}
              className="flex-1"
            >
              取消
            </Button>
            <Button
              type="submit"
              className="flex-1"
            >
              {list ? '保存' : '創建'}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}
