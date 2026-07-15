/**
 * 確認對話框組件
 */
"use client";

import React, { useId } from "react";
import { Button } from "./button";
import { useDialogA11y } from "@/hooks/useDialogA11y";

export interface ConfirmDialogProps {
  isOpen: boolean;
  title: string;
  message: string;
  confirmText?: string;
  cancelText?: string;
  type?: "danger" | "warning" | "info";
  onConfirm: () => void;
  onCancel: () => void;
}

const ConfirmDialog: React.FC<ConfirmDialogProps> = ({
  isOpen,
  title,
  message,
  confirmText = "確認",
  cancelText = "取消",
  type = "danger",
  onConfirm,
  onCancel,
}) => {
  const titleId = useId();
  const messageId = useId();
  const dialogRef = useDialogA11y(isOpen, onCancel);

  if (!isOpen) return null;

  const iconColor = {
    danger: "text-red-600",
    warning: "text-yellow-600",
    info: "text-blue-600",
  }[type];

  const confirmVariant = {
    danger: "destructive",
    warning: "warning",
    info: "default",
  }[type] as "destructive" | "warning" | "default";

  return (
    <div className="fixed inset-0 z-[10000] overflow-y-auto">
      {/* 背景遮罩 */}
      <div
        className="fixed inset-0 bg-slate-950/45 backdrop-blur-[1px] transition-opacity"
        onClick={onCancel}
        aria-hidden="true"
      />

      {/* 對話框 */}
      <div className="flex min-h-full items-center justify-center p-4">
        <div
          ref={dialogRef}
          role="alertdialog"
          aria-modal="true"
          aria-labelledby={titleId}
          aria-describedby={messageId}
          tabIndex={-1}
          className="relative w-full max-w-md animate-scale-in rounded-xl border border-slate-200 bg-white p-6 shadow-xl outline-none"
        >
          {/* 圖標 */}
          <div className="mx-auto flex items-center justify-center h-12 w-12 rounded-full bg-red-100 mb-4">
            {type === "danger" && (
              <svg
                className={`h-6 w-6 ${iconColor}`}
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.268 16.5c-.77.833.192 2.5 1.732 2.5z"
                />
              </svg>
            )}
            {type === "warning" && (
              <svg
                className={`h-6 w-6 ${iconColor}`}
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.268 16.5c-.77.833.192 2.5 1.732 2.5z"
                />
              </svg>
            )}
            {type === "info" && (
              <svg
                className={`h-6 w-6 ${iconColor}`}
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                />
              </svg>
            )}
          </div>

          {/* 標題 */}
          <h3
            id={titleId}
            className="mb-2 text-center text-lg font-semibold text-slate-950"
          >
            {title}
          </h3>

          {/* 訊息 */}
          <p id={messageId} className="mb-6 text-center text-sm text-slate-600">
            {message}
          </p>

          {/* 按鈕 */}
          <div className="flex gap-3">
            <Button variant="outline" onClick={onCancel} className="flex-1">
              {cancelText}
            </Button>
            <Button
              variant={confirmVariant}
              onClick={onConfirm}
              className="flex-1"
            >
              {confirmText}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ConfirmDialog;
