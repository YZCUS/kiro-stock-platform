/**
 * 交易 Modal - 買入/賣出股票
 */
"use client";

import React, { useState, useEffect, useId } from "react";
import { useAppDispatch, useAppSelector } from "@/store";
import {
  addTransaction,
  fetchPortfolioList,
} from "@/store/slices/portfolioSlice";
import { addToast } from "@/store/slices/uiSlice";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Stock, TransactionType } from "@/types";
import { X, AlertCircle } from "lucide-react";
import { formatLocalDateInput, formatMarketCurrency } from "@/lib/finance";
import { useDialogA11y } from "@/hooks/useDialogA11y";

interface TransactionModalProps {
  isOpen: boolean;
  onClose: () => void;
  stock: Stock | null;
  transactionType: TransactionType;
  onSuccess?: () => void;
}

export default function TransactionModal({
  isOpen,
  onClose,
  stock,
  transactionType,
  onSuccess,
}: TransactionModalProps) {
  const dispatch = useAppDispatch();
  const { portfolios } = useAppSelector((state) => state.portfolio);
  const titleId = useId();
  const dialogRef = useDialogA11y(isOpen, onClose);
  const [formData, setFormData] = useState({
    quantity: "",
    price: "",
    fee: "",
    tax: "",
    transaction_date: formatLocalDateInput(),
    note: "",
  });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [holdingStatus, setHoldingStatus] = useState<
    "idle" | "loading" | "ready" | "error"
  >("idle");

  // 獲取當前股票的持倉數量
  const currentHolding = stock
    ? portfolios.find((p) => p.stock_id === stock.id)
    : null;
  const availableQuantity = currentHolding?.quantity || 0;
  const isCheckingHolding =
    transactionType === "SELL" && holdingStatus === "loading";
  const holdingCheckFailed =
    transactionType === "SELL" && holdingStatus === "error";
  const sellUnavailable =
    transactionType === "SELL" &&
    holdingStatus === "ready" &&
    availableQuantity === 0;

  // 重置表單當 modal 開啟或股票變更時
  useEffect(() => {
    if (isOpen && stock) {
      setFormData({
        quantity: "",
        price: stock.latest_price?.close?.toString() || "",
        fee: "",
        tax: "",
        transaction_date: formatLocalDateInput(),
        note: "",
      });
    }
  }, [isOpen, stock]);

  useEffect(() => {
    if (!isOpen || !stock || transactionType !== "SELL") {
      setHoldingStatus("idle");
      return;
    }

    let cancelled = false;
    setHoldingStatus("loading");
    void dispatch(fetchPortfolioList())
      .unwrap()
      .then(() => {
        if (!cancelled) setHoldingStatus("ready");
      })
      .catch(() => {
        if (!cancelled) setHoldingStatus("error");
      });

    return () => {
      cancelled = true;
    };
  }, [dispatch, isOpen, stock, transactionType]);

  if (!isOpen || !stock) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    // 驗證
    if (!formData.quantity || !formData.price) {
      dispatch(
        addToast({
          type: "error",
          title: "錯誤",
          message: "請填寫數量和價格",
        }),
      );
      return;
    }

    const quantity = parseFloat(formData.quantity);
    const price = parseFloat(formData.price);
    const fee = formData.fee ? parseFloat(formData.fee) : 0;
    const tax = formData.tax ? parseFloat(formData.tax) : 0;

    if (
      !Number.isFinite(quantity) ||
      !Number.isFinite(price) ||
      quantity <= 0 ||
      price <= 0
    ) {
      dispatch(
        addToast({
          type: "error",
          title: "錯誤",
          message: "數量和價格必須大於 0",
        }),
      );
      return;
    }

    // 賣出時檢查庫存
    if (transactionType === "SELL") {
      if (holdingStatus !== "ready") {
        dispatch(
          addToast({
            type: "error",
            title: "無法確認持倉",
            message: "持倉資料尚未就緒，請稍後再試",
          }),
        );
        return;
      }

      if (availableQuantity === 0) {
        dispatch(
          addToast({
            type: "error",
            title: "無法賣出",
            message: `您尚未持有 ${stock.symbol}，無法進行賣出操作`,
          }),
        );
        return;
      }

      if (quantity > availableQuantity) {
        dispatch(
          addToast({
            type: "error",
            title: "庫存不足",
            message: `可賣出數量: ${availableQuantity} 股，您輸入了 ${quantity} 股`,
          }),
        );
        return;
      }
    }

    setIsSubmitting(true);

    try {
      await dispatch(
        addTransaction({
          stock_id: stock.id,
          transaction_type: transactionType,
          quantity,
          price,
          fee,
          tax,
          transaction_date: formData.transaction_date,
          note: formData.note || undefined,
        }),
      ).unwrap();

      void dispatch(fetchPortfolioList())
        .unwrap()
        .catch(() => undefined);

      dispatch(
        addToast({
          type: "success",
          title: "成功",
          message: `${transactionType === "BUY" ? "買入" : "賣出"}交易已記錄`,
        }),
      );

      // 重置表單
      setFormData({
        quantity: "",
        price: "",
        fee: "",
        tax: "",
        transaction_date: formatLocalDateInput(),
        note: "",
      });

      onSuccess?.();
      onClose();
    } catch (err: unknown) {
      dispatch(
        addToast({
          type: "error",
          title: "錯誤",
          message:
            typeof err === "string"
              ? err
              : err instanceof Error
                ? err.message
                : "交易記錄失敗",
        }),
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleChange = (field: string, value: string) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
  };

  const calculateTotal = () => {
    const quantity = parseFloat(formData.quantity) || 0;
    const price = parseFloat(formData.price) || 0;
    const fee = parseFloat(formData.fee) || 0;
    const tax = parseFloat(formData.tax) || 0;

    const subtotal = quantity * price;
    return transactionType === "BUY" ? subtotal + fee : subtotal - fee - tax;
  };

  const market = stock.market === "TW" ? "TW" : "US";

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/45 p-4 backdrop-blur-[1px]"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget && !isSubmitting) onClose();
      }}
    >
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        tabIndex={-1}
        className="flex max-h-[90vh] w-full max-w-md flex-col overflow-hidden rounded-xl border border-slate-200 bg-white shadow-xl outline-none"
      >
        {/* Header - 固定不滾動 */}
        <div className="flex-shrink-0 border-b border-slate-200 px-6 py-4">
          <div className="flex items-start justify-between gap-4">
            <div>
              <div className="mb-1 flex items-center gap-2">
                <span
                  className={`rounded-full px-2 py-0.5 text-xs font-semibold ${transactionType === "BUY" ? "bg-blue-50 text-blue-700" : "bg-red-50 text-red-700"}`}
                >
                  {transactionType === "BUY" ? "BUY" : "SELL"}
                </span>
                <span className="text-xs font-medium text-slate-500">
                  {market === "TW" ? "台股" : "美股"}
                </span>
              </div>
              <h2 id={titleId} className="text-lg font-semibold text-slate-950">
                {transactionType === "BUY" ? "買入股票" : "賣出股票"}
              </h2>
              <p className="mt-1 text-sm text-slate-600">
                {stock.symbol} - {stock.name}
              </p>
            </div>
            <Button
              variant="ghost"
              size="icon"
              onClick={onClose}
              aria-label="關閉交易視窗"
            >
              <X className="w-4 h-4" />
            </Button>
          </div>
        </div>

        {/* Form - 可滾動區域 */}
        <form onSubmit={handleSubmit} className="flex-1 overflow-y-auto">
          <div className="space-y-4 p-6">
            {/* 賣出時的庫存警告 */}
            {isCheckingHolding && (
              <div
                className="rounded-lg border border-blue-200 bg-blue-50 p-3 text-sm text-blue-800"
                role="status"
                aria-live="polite"
              >
                正在確認可賣出數量...
              </div>
            )}

            {holdingCheckFailed && (
              <div
                className="flex items-start gap-2 rounded-lg border border-red-200 bg-red-50 p-3"
                role="alert"
              >
                <AlertCircle className="mt-0.5 h-5 w-5 flex-shrink-0 text-red-600" />
                <div className="text-sm text-red-800">
                  <p className="font-semibold">無法確認持倉</p>
                  <p>持倉資料暫時無法載入，請稍後重新開啟視窗。</p>
                </div>
              </div>
            )}

            {sellUnavailable && (
              <div
                className="flex items-start gap-2 rounded-lg border border-red-200 bg-red-50 p-3"
                role="alert"
              >
                <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
                <div className="text-sm text-red-800">
                  <p className="font-semibold">無法賣出</p>
                  <p>您尚未持有 {stock.symbol}，請先買入後才能賣出。</p>
                </div>
              </div>
            )}

            {/* 數量 */}
            <div>
              <Label htmlFor="quantity">
                數量 <span className="text-red-500">*</span>
                {transactionType === "SELL" && availableQuantity > 0 && (
                  <span className="ml-2 text-sm font-normal text-slate-500">
                    （可賣出: {availableQuantity} 股）
                  </span>
                )}
              </Label>
              <Input
                id="quantity"
                type="number"
                min="0.0001"
                max={
                  transactionType === "SELL" && holdingStatus === "ready"
                    ? availableQuantity
                    : undefined
                }
                step="0.0001"
                value={formData.quantity}
                onChange={(e) => handleChange("quantity", e.target.value)}
                placeholder={
                  transactionType === "SELL"
                    ? isCheckingHolding
                      ? "正在確認持倉"
                      : `可賣出 ${availableQuantity} 股`
                    : "請輸入股數"
                }
                required
                disabled={
                  (transactionType === "SELL" && holdingStatus !== "ready") ||
                  sellUnavailable
                }
              />
            </div>

            {/* 價格 */}
            <div>
              <Label htmlFor="price">
                價格 <span className="text-red-500">*</span>
              </Label>
              <Input
                id="price"
                type="number"
                min="0"
                step="0.01"
                value={formData.price}
                onChange={(e) => handleChange("price", e.target.value)}
                placeholder="請輸入成交價格"
                required
              />
              {stock.latest_price?.close && (
                <p className="mt-1 text-xs text-slate-500">
                  最新價格：
                  {formatMarketCurrency(stock.latest_price.close, market)}
                </p>
              )}
            </div>

            {/* 手續費 */}
            <div>
              <Label htmlFor="fee">手續費</Label>
              <Input
                id="fee"
                type="number"
                min="0"
                step="0.01"
                value={formData.fee}
                onChange={(e) => handleChange("fee", e.target.value)}
                placeholder="選填（預設 0）"
              />
            </div>

            {/* 交易稅（僅賣出時顯示） */}
            {transactionType === "SELL" && (
              <div>
                <Label htmlFor="tax">交易稅</Label>
                <Input
                  id="tax"
                  type="number"
                  min="0"
                  step="0.01"
                  value={formData.tax}
                  onChange={(e) => handleChange("tax", e.target.value)}
                  placeholder="選填（預設 0）"
                />
              </div>
            )}

            {/* 交易日期 */}
            <div>
              <Label htmlFor="transaction_date">
                交易日期 <span className="text-red-500">*</span>
              </Label>
              <Input
                id="transaction_date"
                type="date"
                value={formData.transaction_date}
                onChange={(e) =>
                  handleChange("transaction_date", e.target.value)
                }
                required
              />
            </div>

            {/* 備註 */}
            <div>
              <Label htmlFor="note">備註</Label>
              <textarea
                id="note"
                value={formData.note}
                onChange={(e) => handleChange("note", e.target.value)}
                placeholder="選填"
                className="flex min-h-20 w-full rounded-md border border-input bg-background px-3 py-2 text-sm text-foreground shadow-none outline-none transition-colors placeholder:text-muted-foreground focus-visible:border-ring focus-visible:ring-2 focus-visible:ring-ring/20 disabled:cursor-not-allowed disabled:opacity-50"
                rows={2}
              />
            </div>

            {/* 總金額 */}
            <div className="rounded-lg border border-slate-200 bg-slate-50 p-4">
              <div className="flex justify-between items-center">
                <span className="text-sm font-medium text-slate-700">
                  {transactionType === "BUY" ? "總支出" : "總收入"}
                </span>
                <span className="text-xl font-semibold tabular-nums text-slate-950">
                  {formatMarketCurrency(calculateTotal(), market)}
                </span>
              </div>
              {formData.quantity && formData.price && (
                <p className="mt-2 text-xs text-slate-500">
                  {formData.quantity} 股 ×{" "}
                  {formatMarketCurrency(parseFloat(formData.price), market)}
                  {(parseFloat(formData.fee) > 0 ||
                    parseFloat(formData.tax) > 0) && (
                    <>
                      {transactionType === "BUY" ? " + " : " - "}
                      手續費{" "}
                      {formatMarketCurrency(
                        parseFloat(formData.fee || "0"),
                        market,
                      )}
                      {transactionType === "SELL" &&
                        parseFloat(formData.tax) > 0 && (
                          <>
                            {" "}
                            - 稅{" "}
                            {formatMarketCurrency(
                              parseFloat(formData.tax),
                              market,
                            )}
                          </>
                        )}
                    </>
                  )}
                </p>
              )}
            </div>

            {/* 按鈕 */}
            <div className="flex gap-3 pt-2">
              <Button
                type="button"
                variant="outline"
                onClick={onClose}
                disabled={isSubmitting}
                className="flex-1"
              >
                取消
              </Button>
              <Button
                type="submit"
                disabled={
                  isSubmitting ||
                  (transactionType === "SELL" && holdingStatus !== "ready") ||
                  sellUnavailable
                }
                variant={transactionType === "BUY" ? "default" : "destructive"}
                className="flex-1"
              >
                {isSubmitting
                  ? "處理中..."
                  : isCheckingHolding
                    ? "確認持倉中..."
                    : `確認${transactionType === "BUY" ? "買入" : "賣出"}`}
              </Button>
            </div>
          </div>
        </form>
      </div>
    </div>
  );
}
