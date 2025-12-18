"""
재무지표 계산 엔진

7개 핵심 지표:
1. 현금자산총액 (억원)
2. 매출 CAGR (2022-2024, %)
3. 매출채권 회전율 (회)
4. 매입채무 회전율 (회)
5. 재고자산 회전율 (회)
6. 부채비율 (%)
7. 유동비율 (%)
"""
from typing import Dict, List, Optional, Tuple
from decimal import Decimal
from datetime import date
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Company, FinancialStatement
import logging

logger = logging.getLogger(__name__)


class FinancialMetricsCalculator:
    """재무지표 계산기"""

    @staticmethod
    def to_billion_won(amount: Optional[int]) -> Optional[float]:
        """
        원 단위를 억원 단위로 변환

        Args:
            amount: 원 단위 금액

        Returns:
            억원 단위 금액 (소수점 2자리)
        """
        if amount is None:
            return None
        return round(amount / 100_000_000, 2)

    @staticmethod
    def calculate_cagr(
        start_value: Optional[int],
        end_value: Optional[int],
        years: int
    ) -> Optional[float]:
        """
        CAGR (연평균 성장률) 계산

        Formula: CAGR = ((End Value / Start Value) ^ (1 / Years)) - 1

        Args:
            start_value: 시작 값
            end_value: 종료 값
            years: 기간 (년)

        Returns:
            CAGR (%), 소수점 2자리
        """
        if not start_value or not end_value or start_value <= 0:
            return None

        try:
            ratio = end_value / start_value
            cagr = (ratio ** (1 / years)) - 1
            return round(cagr * 100, 2)  # 퍼센트로 변환
        except (ValueError, ZeroDivisionError):
            return None

    @staticmethod
    def calculate_turnover_ratio(
        flow_amount: Optional[int],
        stock_amount: Optional[int]
    ) -> Optional[float]:
        """
        회전율 계산

        Formula: Turnover = Flow Amount / Stock Amount

        Args:
            flow_amount: 흐름 금액 (매출, 매출원가 등)
            stock_amount: 재고 금액 (매출채권, 재고자산 등)

        Returns:
            회전율 (회), 소수점 2자리
        """
        if not flow_amount or not stock_amount or stock_amount == 0:
            return None

        return round(flow_amount / stock_amount, 2)

    @staticmethod
    def calculate_debt_ratio(
        total_liabilities: Optional[int],
        total_equity: Optional[int]
    ) -> Optional[float]:
        """
        부채비율 계산

        Formula: Debt Ratio = (Total Liabilities / Total Equity) × 100

        Args:
            total_liabilities: 총 부채
            total_equity: 총 자본

        Returns:
            부채비율 (%), 소수점 2자리
        """
        if not total_liabilities or not total_equity or total_equity == 0:
            return None

        return round((total_liabilities / total_equity) * 100, 2)

    @staticmethod
    def calculate_current_ratio(
        current_assets: Optional[int],
        current_liabilities: Optional[int]
    ) -> Optional[float]:
        """
        유동비율 계산

        Formula: Current Ratio = (Current Assets / Current Liabilities) × 100

        Args:
            current_assets: 유동자산
            current_liabilities: 유동부채

        Returns:
            유동비율 (%), 소수점 2자리
        """
        if not current_assets or not current_liabilities or current_liabilities == 0:
            return None

        return round((current_assets / current_liabilities) * 100, 2)

    async def get_company_metrics(
        self,
        db: AsyncSession,
        company_id: str
    ) -> Dict[str, Optional[float]]:
        """
        특정 회사의 7개 핵심 재무지표 계산

        Args:
            db: Database session
            company_id: 회사 ID (UUID)

        Returns:
            {
                "cash_assets_billion": 31.72,  # 현금자산총액 (억원)
                "revenue_cagr": 15.5,          # 매출 CAGR (%)
                "ar_turnover": 8.5,            # 매출채권 회전율 (회)
                "ap_turnover": 12.3,           # 매입채무 회전율 (회)
                "inventory_turnover": 6.2,     # 재고자산 회전율 (회)
                "debt_ratio": 45.2,            # 부채비율 (%)
                "current_ratio": 150.3         # 유동비율 (%)
            }
        """
        metrics = {
            "cash_assets_billion": None,
            "revenue_cagr": None,
            "ar_turnover": None,
            "ap_turnover": None,
            "inventory_turnover": None,
            "debt_ratio": None,
            "current_ratio": None,
        }

        # 1. 최신 2025 Q2 재무제표 조회 (지표 3-7용)
        latest_stmt = await self._get_latest_statement(db, company_id)

        if latest_stmt:
            # 1. 현금자산총액 (억원)
            cash_total = (
                (latest_stmt.cash_and_equivalents or 0) +
                (latest_stmt.short_term_investments or 0)
            )
            metrics["cash_assets_billion"] = self.to_billion_won(cash_total)

            # 3. 매출채권 회전율
            metrics["ar_turnover"] = self.calculate_turnover_ratio(
                latest_stmt.revenue,
                latest_stmt.accounts_receivable
            )

            # 4. 매입채무 회전율
            metrics["ap_turnover"] = self.calculate_turnover_ratio(
                latest_stmt.cost_of_sales,
                latest_stmt.accounts_payable
            )

            # 5. 재고자산 회전율
            metrics["inventory_turnover"] = self.calculate_turnover_ratio(
                latest_stmt.cost_of_sales,
                latest_stmt.inventory
            )

            # 6. 부채비율
            metrics["debt_ratio"] = self.calculate_debt_ratio(
                latest_stmt.total_liabilities,
                latest_stmt.total_equity
            )

            # 7. 유동비율
            metrics["current_ratio"] = self.calculate_current_ratio(
                latest_stmt.current_assets,
                latest_stmt.current_liabilities
            )

        # 2. 매출 CAGR (2022-2024 사업보고서)
        revenue_2022 = await self._get_revenue_by_year(db, company_id, 2022)
        revenue_2024 = await self._get_revenue_by_year(db, company_id, 2024)

        if revenue_2022 and revenue_2024:
            metrics["revenue_cagr"] = self.calculate_cagr(
                revenue_2022,
                revenue_2024,
                2  # 2022 → 2024 = 2년
            )

        return metrics

    async def _get_latest_statement(
        self,
        db: AsyncSession,
        company_id: str
    ) -> Optional[FinancialStatement]:
        """최신 재무제표 조회 (2025 Q2 우선, 없으면 2024 연간)"""
        # 2025 Q2
        result = await db.execute(
            select(FinancialStatement).where(
                and_(
                    FinancialStatement.company_id == company_id,
                    FinancialStatement.fiscal_year == 2025,
                    FinancialStatement.quarter == "Q2"
                )
            )
        )
        stmt = result.scalar_one_or_none()

        if stmt:
            return stmt

        # Fallback: 2024 연간
        result = await db.execute(
            select(FinancialStatement).where(
                and_(
                    FinancialStatement.company_id == company_id,
                    FinancialStatement.fiscal_year == 2024,
                    FinancialStatement.quarter.is_(None)
                )
            )
        )
        return result.scalar_one_or_none()

    async def _get_revenue_by_year(
        self,
        db: AsyncSession,
        company_id: str,
        year: int
    ) -> Optional[int]:
        """특정 연도의 연간 매출 조회"""
        result = await db.execute(
            select(FinancialStatement.revenue).where(
                and_(
                    FinancialStatement.company_id == company_id,
                    FinancialStatement.fiscal_year == year,
                    FinancialStatement.quarter.is_(None)  # 연간 보고서
                )
            )
        )
        return result.scalar_one_or_none()

    async def get_batch_metrics(
        self,
        db: AsyncSession,
        company_ids: List[str]
    ) -> Dict[str, Dict[str, Optional[float]]]:
        """
        여러 회사의 재무지표를 배치로 계산

        Args:
            db: Database session
            company_ids: 회사 ID 리스트

        Returns:
            {
                "company_id_1": {...metrics...},
                "company_id_2": {...metrics...},
                ...
            }
        """
        results = {}

        for company_id in company_ids:
            try:
                metrics = await self.get_company_metrics(db, company_id)
                results[company_id] = metrics
            except Exception as e:
                logger.error(f"Error calculating metrics for {company_id}: {e}")
                results[company_id] = {
                    "cash_assets_billion": None,
                    "revenue_cagr": None,
                    "ar_turnover": None,
                    "ap_turnover": None,
                    "inventory_turnover": None,
                    "debt_ratio": None,
                    "current_ratio": None,
                }

        return results

    async def analyze_company_health(
        self,
        db: AsyncSession,
        company_id: str
    ) -> Dict[str, any]:
        """
        회사 재무 건전성 분석

        Returns:
            {
                "metrics": {...7개 지표...},
                "health_score": 75.5,  # 0-100
                "warnings": [
                    "높은 부채비율 (200%)",
                    "낮은 유동비율 (80%)"
                ],
                "strengths": [
                    "우수한 매출 성장 (CAGR 25%)",
                    "안정적 현금 보유 (500억원)"
                ]
            }
        """
        metrics = await self.get_company_metrics(db, company_id)

        warnings = []
        strengths = []
        score = 100.0

        # 부채비율 체크 (150% 이상 경고)
        if metrics["debt_ratio"] and metrics["debt_ratio"] > 150:
            warnings.append(f"높은 부채비율 ({metrics['debt_ratio']:.1f}%)")
            score -= 15

        # 유동비율 체크 (100% 미만 경고)
        if metrics["current_ratio"] and metrics["current_ratio"] < 100:
            warnings.append(f"낮은 유동비율 ({metrics['current_ratio']:.1f}%)")
            score -= 20

        # 매출 성장 체크
        if metrics["revenue_cagr"]:
            if metrics["revenue_cagr"] > 20:
                strengths.append(f"우수한 매출 성장 (CAGR {metrics['revenue_cagr']:.1f}%)")
                score += 10
            elif metrics["revenue_cagr"] < -10:
                warnings.append(f"매출 감소 추세 (CAGR {metrics['revenue_cagr']:.1f}%)")
                score -= 15

        # 현금자산 체크
        if metrics["cash_assets_billion"] and metrics["cash_assets_billion"] > 100:
            strengths.append(f"안정적 현금 보유 ({metrics['cash_assets_billion']:.0f}억원)")

        # 회전율 체크 (낮으면 경고)
        if metrics["ar_turnover"] and metrics["ar_turnover"] < 4:
            warnings.append(f"낮은 매출채권 회전율 ({metrics['ar_turnover']:.1f}회)")
            score -= 10

        if metrics["inventory_turnover"] and metrics["inventory_turnover"] < 4:
            warnings.append(f"낮은 재고자산 회전율 ({metrics['inventory_turnover']:.1f}회)")
            score -= 10

        return {
            "metrics": metrics,
            "health_score": max(0, min(100, score)),  # 0-100 범위
            "warnings": warnings,
            "strengths": strengths
        }
