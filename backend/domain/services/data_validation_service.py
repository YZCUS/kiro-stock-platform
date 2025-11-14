"""
數據驗證業務服務 - Domain Layer
負責股票數據品質評估，依賴抽象的 Repository 與 Cache 介面
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from domain.policies.validation_rules import ValidationRules
from domain.repositories.price_history_repository_interface import (
    IPriceHistoryRepository,
)
from domain.repositories.stock_repository_interface import IStockRepository
from infrastructure.cache.redis_cache_service import ICacheService


@dataclass
class ValidationIssue:
    """單一驗證問題"""

    message: str
    context: Dict[str, Any]


@dataclass
class ValidationReport:
    """驗證報告摘要"""

    stock_id: int
    symbol: str
    market: str
    quality_score: int
    is_valid: bool
    total_records: int
    issues: List[ValidationIssue]
    recommendations: List[str]


class DataValidationService:
    """股票數據驗證業務服務"""

    def __init__(
        self,
        stock_repository: IStockRepository,
        price_repository: IPriceHistoryRepository,
        cache_service: ICacheService,
    ) -> None:
        self.stock_repo = stock_repository
        self.price_repo = price_repository
        self.cache = cache_service

        # 業務預設值
        self.max_price_change_ratio = 0.3  # 30%
        self.max_days_gap = 7
        self.min_volume = 0

    async def validate_stock_data(
        self,
        db: AsyncSession,
        stock_id: int,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> ValidationReport:
        """驗證指定股票數據品質"""

        stock = await self.stock_repo.get(db, stock_id)
        if not stock:
            raise ValueError(f"股票 ID {stock_id} 不存在")

        if (
            start_date
            and end_date
            and not ValidationRules.validate_date_range(start_date, end_date)
        ):
            raise ValueError("日期區間不合法或超過限制")

        start_date = start_date or (datetime.now().date() - timedelta(days=90))
        end_date = end_date or datetime.now().date()

        cache_key = self.cache.get_cache_key(
            "data_validation",
            stock_id=stock_id,
            start=start_date.isoformat(),
            end=end_date.isoformat(),
        )

        cached = await self.cache.get(cache_key)
        if cached:
            return ValidationReport(
                stock_id=stock_id,
                symbol=stock.symbol,
                market=stock.market,
                quality_score=cached["quality_score"],
                is_valid=cached["is_valid"],
                total_records=cached["total_records"],
                issues=[ValidationIssue(**issue) for issue in cached["issues"]],
                recommendations=cached["recommendations"],
            )

        price_records = await self.price_repo.get_stock_price_range(
            db,
            stock_id=stock_id,
            start_date=start_date,
            end_date=end_date,
            limit=5000,
        )

        issues: List[ValidationIssue] = []
        recommendations: List[str] = []

        if not price_records:
            report = ValidationReport(
                stock_id=stock_id,
                symbol=stock.symbol,
                market=stock.market,
                quality_score=0,
                is_valid=False,
                total_records=0,
                issues=[
                    ValidationIssue(
                        message="無可用價格記錄",
                        context={
                            "start_date": start_date.isoformat(),
                            "end_date": end_date.isoformat(),
                        },
                    )
                ],
                recommendations=["確認資料收集排程是否正常執行"],
            )
            await self.cache.set(cache_key, self._serialize_report(report), ttl=900)
            return report

        completeness_score, completeness_issues = self._check_completeness(
            price_records
        )
        issues.extend(completeness_issues)

        price_score, price_issues = self._check_price_consistency(price_records)
        issues.extend(price_issues)

        volume_score, volume_issues = self._check_volume_integrity(price_records)
        issues.extend(volume_issues)

        continuity_score, continuity_issues = self._check_continuity(price_records)
        issues.extend(continuity_issues)

        outlier_score, outlier_issues = self._detect_outliers(price_records)
        issues.extend(outlier_issues)

        missing_score, missing_issues = self._check_missing_days(
            price_records, start_date, end_date
        )
        issues.extend(missing_issues)

        weighted_score = int(
            completeness_score * 0.25
            + price_score * 0.25
            + volume_score * 0.15
            + continuity_score * 0.15
            + outlier_score * 0.1
            + missing_score * 0.1
        )

        is_valid = (
            weighted_score >= 75 and completeness_score >= 70 and price_score >= 70
        )

        if completeness_score < 70:
            recommendations.append("補齊缺失的價格欄位或補拷資料")
        if continuity_score < 70:
            recommendations.append("檢查排程失敗或停牌期間，必要時補下歷史資料")
        if outlier_score < 70:
            recommendations.append("調查異常波動來源，確認是否為資料品質問題")

        report = ValidationReport(
            stock_id=stock_id,
            symbol=stock.symbol,
            market=stock.market,
            quality_score=weighted_score,
            is_valid=is_valid,
            total_records=len(price_records),
            issues=issues,
            recommendations=recommendations,
        )

        await self.cache.set(cache_key, self._serialize_report(report), ttl=900)
        return report

    def _check_completeness(self, price_records) -> tuple[int, List[ValidationIssue]]:
        issues: List[ValidationIssue] = []
        required_fields = [
            "open_price",
            "high_price",
            "low_price",
            "close_price",
            "volume",
        ]

        total = len(price_records)
        complete = 0
        for record in price_records:
            missing = [
                field for field in required_fields if getattr(record, field) is None
            ]
            if missing:
                issues.append(
                    ValidationIssue(
                        message="價格欄位缺失",
                        context={
                            "date": record.date.isoformat(),
                            "missing_fields": missing,
                        },
                    )
                )
            else:
                complete += 1

        score = int((complete / total) * 100)
        return score, issues

    def _check_price_consistency(
        self, price_records
    ) -> tuple[int, List[ValidationIssue]]:
        issues: List[ValidationIssue] = []
        valid = 0

        for record in price_records:
            record_issues = []
            if record.high_price is not None and record.low_price is not None:
                if record.high_price < record.low_price:
                    record_issues.append("high_lt_low")
                if record.high_price < max(
                    record.open_price or 0, record.close_price or 0
                ):
                    record_issues.append("high_lt_open_close")
                if record.low_price > min(
                    record.open_price or 0, record.close_price or 0
                ):
                    record_issues.append("low_gt_open_close")

            for field in ["open_price", "high_price", "low_price", "close_price"]:
                value = getattr(record, field)
                if value is not None and (
                    value <= 0 or not ValidationRules.validate_price_range(float(value))
                ):
                    record_issues.append(f"invalid_{field}")

            if record_issues:
                issues.append(
                    ValidationIssue(
                        message="價格邏輯異常",
                        context={
                            "date": record.date.isoformat(),
                            "issues": record_issues,
                        },
                    )
                )
            else:
                valid += 1

        score = int((valid / len(price_records)) * 100)
        return score, issues

    def _check_volume_integrity(
        self, price_records
    ) -> tuple[int, List[ValidationIssue]]:
        issues: List[ValidationIssue] = []
        valid = 0

        for record in price_records:
            volume = record.volume
            if volume is None:
                issues.append(
                    ValidationIssue(
                        message="成交量缺失",
                        context={"date": record.date.isoformat()},
                    )
                )
            elif volume < self.min_volume:
                issues.append(
                    ValidationIssue(
                        message="成交量異常",
                        context={"date": record.date.isoformat(), "volume": volume},
                    )
                )
            else:
                valid += 1

        score = int((valid / len(price_records)) * 100)
        return score, issues

    def _check_continuity(self, price_records) -> tuple[int, List[ValidationIssue]]:
        issues: List[ValidationIssue] = []
        sorted_records = sorted(price_records, key=lambda r: r.date)
        gaps = 0

        for i in range(1, len(sorted_records)):
            prev_date = sorted_records[i - 1].date
            current_date = sorted_records[i].date
            days = (current_date - prev_date).days
            if days > self.max_days_gap:
                gaps += 1
                issues.append(
                    ValidationIssue(
                        message="資料間隔過大",
                        context={
                            "start": prev_date.isoformat(),
                            "end": current_date.isoformat(),
                            "gap_days": days,
                        },
                    )
                )

        total_possible = max(len(sorted_records) - 1, 1)
        score = int((1 - gaps / total_possible) * 100)
        return score, issues

    def _detect_outliers(self, price_records) -> tuple[int, List[ValidationIssue]]:
        issues: List[ValidationIssue] = []
        sorted_records = sorted(price_records, key=lambda r: r.date)
        outliers = 0

        for i in range(1, len(sorted_records)):
            current = sorted_records[i]
            previous = sorted_records[i - 1]
            if previous.close_price and current.close_price:
                change_ratio = abs(
                    float(current.close_price) - float(previous.close_price)
                ) / float(previous.close_price)
                if change_ratio > self.max_price_change_ratio:
                    outliers += 1
                    issues.append(
                        ValidationIssue(
                            message="價格波動異常",
                            context={
                                "date": current.date.isoformat(),
                                "previous_close": float(previous.close_price),
                                "current_close": float(current.close_price),
                                "change_ratio": change_ratio,
                            },
                        )
                    )

        score = int((1 - outliers / len(sorted_records)) * 100)
        return score, issues

    def _check_missing_days(
        self,
        price_records,
        start_date: date,
        end_date: date,
    ) -> tuple[int, List[ValidationIssue]]:
        issues: List[ValidationIssue] = []
        existing_dates = {record.date for record in price_records}

        expected_dates = set()
        current = start_date
        while current <= end_date:
            if current.weekday() < 5:
                expected_dates.add(current)
            current += timedelta(days=1)

        missing = expected_dates - existing_dates
        if missing:
            issues.append(
                ValidationIssue(
                    message="缺少部分交易日資料",
                    context={
                        "count": len(missing),
                        "sample": [d.isoformat() for d in sorted(list(missing))[:10]],
                    },
                )
            )

        score = int((len(existing_dates) / max(len(expected_dates), 1)) * 100)
        return score, issues

    def _serialize_report(self, report: ValidationReport) -> Dict[str, Any]:
        return {
            "stock_id": report.stock_id,
            "symbol": report.symbol,
            "market": report.market,
            "quality_score": report.quality_score,
            "is_valid": report.is_valid,
            "total_records": report.total_records,
            "issues": [
                {"message": issue.message, "context": issue.context}
                for issue in report.issues
            ],
            "recommendations": report.recommendations,
        }
