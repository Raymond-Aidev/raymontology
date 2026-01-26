"""
M&A 타겟 점수 계산 및 Financial Snapshot 생성 스크립트

매일 10:00 KST에 실행되어:
1. 전일 종가 데이터 (daily_stock_prices)
2. 발행주식수 (companies.shares_outstanding)
3. 재무 데이터 (financial_details)
를 결합하여 M&A 타겟 점수를 계산하고 financial_snapshots 테이블에 저장합니다.

Usage:
    python -m scripts.analysis.calculate_ma_target_score
    python -m scripts.analysis.calculate_ma_target_score --date 2026-01-24
    python -m scripts.analysis.calculate_ma_target_score --sample 10 --dry-run

M&A 타겟 점수 계산 기준:
1. 현금성 유동자산 / 시가총액 비율 (25점)
2. 유형자산 증가율 (20점)
3. 매출 증감율 (20점)
4. 영업이익 증감율 (20점)
5. 시가총액 규모 (15점) - 적정 인수 규모
"""
import asyncio
import argparse
import logging
import os
import sys
import json
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Optional, Dict, Any, List
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

# 프로젝트 루트 경로 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.models.financial_snapshot import FinancialSnapshot
from app.models.daily_stock_price import DailyStockPrice
from app.models.financial_details import FinancialDetails
from app.models.companies import Company

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MATargetScoreCalculator:
    """M&A 타겟 점수 계산기"""

    # 점수 가중치
    WEIGHTS = {
        "cash_ratio": 25,         # 현금성 자산 / 시가총액
        "tangible_growth": 20,    # 유형자산 증가율
        "revenue_growth": 20,     # 매출 증감율
        "op_profit_growth": 20,   # 영업이익 증감율
        "market_cap_size": 15,    # 시가총액 규모
    }

    # 시가총액 적정 범위 (억원)
    IDEAL_MARKET_CAP_MIN = 500    # 500억
    IDEAL_MARKET_CAP_MAX = 5000   # 5000억

    def __init__(self, db_url: str):
        self.db_url = db_url
        self.engine = create_async_engine(db_url, echo=False)
        self.async_session = sessionmaker(
            self.engine, class_=AsyncSession, expire_on_commit=False
        )

    async def close(self):
        await self.engine.dispose()

    def calculate_score_component(
        self,
        value: Optional[float],
        optimal_value: float,
        weight: int,
        higher_is_better: bool = True,
        max_value: Optional[float] = None
    ) -> float:
        """
        개별 점수 요소 계산

        Args:
            value: 실제 값
            optimal_value: 최적 값
            weight: 가중치 (최대 점수)
            higher_is_better: True면 높을수록 좋음
            max_value: 최대 값 (클리핑용)
        """
        if value is None:
            return 0

        if max_value and value > max_value:
            value = max_value

        if higher_is_better:
            # 0 ~ optimal_value 범위를 0 ~ weight로 매핑
            if optimal_value <= 0:
                return 0
            ratio = min(value / optimal_value, 1.0)
        else:
            # 역계산: 낮을수록 좋음
            if value <= 0:
                return weight
            ratio = max(1 - (value / optimal_value), 0)

        return ratio * weight

    def calculate_cash_ratio_score(
        self,
        total_liquid_assets: Optional[int],
        market_cap: Optional[int]
    ) -> Dict[str, Any]:
        """
        현금성 자산 / 시가총액 비율 점수

        높을수록 M&A 타겟으로 매력적 (자산 풍부, 저평가)
        최적: 50% 이상 (만점)
        """
        if not total_liquid_assets or not market_cap or market_cap <= 0:
            return {"score": 0, "ratio": None, "raw_value": None}

        ratio = (total_liquid_assets / market_cap) * 100  # 퍼센트
        # 50% 이상이면 만점, 0%면 0점
        score = self.calculate_score_component(
            ratio, 50, self.WEIGHTS["cash_ratio"], higher_is_better=True
        )

        return {"score": round(score, 2), "ratio": round(ratio, 2), "raw_value": ratio}

    def calculate_growth_score(
        self,
        growth_rate: Optional[float],
        weight: int,
        optimal_growth: float = 20
    ) -> Dict[str, Any]:
        """
        증감율 점수 계산

        YoY 20% 성장이면 만점
        마이너스 성장이면 점수 감소 (최저 0점)
        """
        if growth_rate is None:
            return {"score": 0, "growth": None, "raw_value": None}

        # -100% ~ +100% 범위로 클리핑
        growth = max(min(growth_rate, 100), -100)

        # 양수 성장: 0 ~ optimal_growth를 0 ~ weight로 매핑
        # 음수 성장: 마이너스면 (1 + growth/100) 비율로 감소
        if growth >= 0:
            score = self.calculate_score_component(
                growth, optimal_growth, weight, higher_is_better=True
            )
        else:
            # 예: -50%면 절반 점수
            score = max(0, weight * (1 + growth / 100))

        return {"score": round(score, 2), "growth": round(growth, 2), "raw_value": growth}

    def calculate_market_cap_size_score(
        self,
        market_cap: Optional[int]
    ) -> Dict[str, Any]:
        """
        시가총액 규모 점수

        적정 인수 규모 (500억 ~ 5000억) 범위 내면 만점
        너무 작거나 크면 점수 감소
        """
        if not market_cap or market_cap <= 0:
            return {"score": 0, "market_cap_bil": None, "raw_value": None}

        market_cap_bil = market_cap / 100_000_000  # 억원 단위

        weight = self.WEIGHTS["market_cap_size"]

        if self.IDEAL_MARKET_CAP_MIN <= market_cap_bil <= self.IDEAL_MARKET_CAP_MAX:
            score = weight  # 만점
        elif market_cap_bil < self.IDEAL_MARKET_CAP_MIN:
            # 너무 작음: 100억 미만이면 0점
            ratio = market_cap_bil / self.IDEAL_MARKET_CAP_MIN
            score = weight * ratio
        else:
            # 너무 큼: 2조 이상이면 0점
            if market_cap_bil >= 20000:
                score = 0
            else:
                # 5000억 ~ 2조: 선형 감소
                ratio = 1 - (market_cap_bil - self.IDEAL_MARKET_CAP_MAX) / (20000 - self.IDEAL_MARKET_CAP_MAX)
                score = weight * ratio

        return {
            "score": round(max(0, score), 2),
            "market_cap_bil": round(market_cap_bil, 2),
            "raw_value": market_cap_bil
        }

    def calculate_total_score(
        self,
        cash_ratio_result: Dict,
        tangible_growth_result: Dict,
        revenue_growth_result: Dict,
        op_profit_growth_result: Dict,
        market_cap_result: Dict
    ) -> Dict[str, Any]:
        """전체 M&A 타겟 점수 계산"""
        total = (
            cash_ratio_result["score"] +
            tangible_growth_result["score"] +
            revenue_growth_result["score"] +
            op_profit_growth_result["score"] +
            market_cap_result["score"]
        )

        # 등급 계산
        grade = self.calculate_grade(total)

        factors = {
            "cash_ratio": {
                "score": cash_ratio_result["score"],
                "max": self.WEIGHTS["cash_ratio"],
                "value": cash_ratio_result.get("ratio"),
            },
            "tangible_growth": {
                "score": tangible_growth_result["score"],
                "max": self.WEIGHTS["tangible_growth"],
                "value": tangible_growth_result.get("growth"),
            },
            "revenue_growth": {
                "score": revenue_growth_result["score"],
                "max": self.WEIGHTS["revenue_growth"],
                "value": revenue_growth_result.get("growth"),
            },
            "op_profit_growth": {
                "score": op_profit_growth_result["score"],
                "max": self.WEIGHTS["op_profit_growth"],
                "value": op_profit_growth_result.get("growth"),
            },
            "market_cap_size": {
                "score": market_cap_result["score"],
                "max": self.WEIGHTS["market_cap_size"],
                "value": market_cap_result.get("market_cap_bil"),
            },
        }

        return {
            "total_score": round(total, 2),
            "grade": grade,
            "factors": factors,
        }

    @staticmethod
    def calculate_grade(score: float) -> str:
        """점수에서 등급 계산"""
        if score >= 90:
            return "A+"
        elif score >= 80:
            return "A"
        elif score >= 70:
            return "B+"
        elif score >= 60:
            return "B"
        elif score >= 50:
            return "C+"
        elif score >= 40:
            return "C"
        else:
            return "D"

    async def get_latest_financial_data(
        self,
        session: AsyncSession,
        company_id: str
    ) -> Optional[Dict[str, Any]]:
        """최신 재무 데이터 조회 (2개년)"""
        query = text("""
            WITH ranked AS (
                SELECT
                    fiscal_year,
                    cash_and_equivalents,
                    short_term_investments,
                    tangible_assets,
                    revenue,
                    operating_income,
                    ROW_NUMBER() OVER (ORDER BY fiscal_year DESC) as rn
                FROM financial_details
                WHERE company_id = :company_id
                  AND report_type = 'annual'
                ORDER BY fiscal_year DESC
                LIMIT 2
            )
            SELECT * FROM ranked
        """)

        result = await session.execute(query, {"company_id": company_id})
        rows = result.fetchall()

        if not rows:
            return None

        current = dict(rows[0]._mapping) if rows else None
        previous = dict(rows[1]._mapping) if len(rows) > 1 else None

        if not current:
            return None

        # 현금성 유동자산 합계
        cash = current.get("cash_and_equivalents") or 0
        short_term = current.get("short_term_investments") or 0
        total_liquid = cash + short_term

        # YoY 증감율 계산 (DB 컬럼 NUMERIC(10,2) 제한으로 -9999 ~ +9999 범위 클리핑)
        def clip_growth(value: Optional[float]) -> Optional[float]:
            """증감율 값을 DB 저장 가능 범위로 클리핑"""
            if value is None:
                return None
            return max(-9999.99, min(9999.99, value))

        tangible_growth = None
        revenue_growth = None
        op_profit_growth = None

        if previous:
            if previous.get("tangible_assets") and current.get("tangible_assets"):
                prev_ta = previous["tangible_assets"]
                if prev_ta != 0:
                    tangible_growth = clip_growth(((current["tangible_assets"] - prev_ta) / abs(prev_ta)) * 100)

            if previous.get("revenue") and current.get("revenue"):
                prev_rev = previous["revenue"]
                if prev_rev != 0:
                    revenue_growth = clip_growth(((current["revenue"] - prev_rev) / abs(prev_rev)) * 100)

            if previous.get("operating_income") and current.get("operating_income"):
                prev_op = previous["operating_income"]
                if prev_op != 0:
                    op_profit_growth = clip_growth(((current["operating_income"] - prev_op) / abs(prev_op)) * 100)

        return {
            "fiscal_year": current.get("fiscal_year"),
            "cash_and_equivalents": current.get("cash_and_equivalents"),
            "short_term_investments": current.get("short_term_investments"),
            "total_liquid_assets": total_liquid if total_liquid > 0 else None,
            "tangible_assets": current.get("tangible_assets"),
            "revenue": current.get("revenue"),
            "operating_income": current.get("operating_income"),
            "tangible_assets_growth": tangible_growth,
            "revenue_growth": revenue_growth,
            "operating_income_growth": op_profit_growth,
        }

    async def create_snapshots(
        self,
        snapshot_date: date,
        sample: Optional[int] = None,
        dry_run: bool = False
    ) -> Dict[str, int]:
        """
        Financial Snapshot 생성

        Args:
            snapshot_date: 스냅샷 일자
            sample: 샘플 수
            dry_run: 저장 안 함

        Returns:
            처리 통계
        """
        stats = {
            "total_companies": 0,
            "price_found": 0,
            "financial_found": 0,
            "score_calculated": 0,
            "saved": 0,
            "errors": 0,
        }

        async with self.async_session() as session:
            # 먼저 daily_stock_prices 확인 후 없으면 stock_prices(월별) 사용
            check_daily = await session.execute(
                text("SELECT COUNT(*) FROM daily_stock_prices WHERE price_date = :price_date"),
                {"price_date": snapshot_date}
            )
            daily_count = check_daily.scalar()

            if daily_count and daily_count > 0:
                # daily_stock_prices 사용 (일별 데이터)
                logger.info(f"daily_stock_prices 사용 ({daily_count}건)")
                query = text("""
                    SELECT
                        c.id as company_id,
                        c.name,
                        c.ticker,
                        c.shares_outstanding,
                        dsp.close_price,
                        dsp.market_cap as market_cap_krx,
                        dsp.listed_shares
                    FROM companies c
                    INNER JOIN daily_stock_prices dsp ON c.id = dsp.company_id
                    WHERE dsp.price_date = :price_date
                      AND c.listing_status = 'LISTED'
                      AND c.company_type IN ('NORMAL', 'SPAC', 'REIT')
                    ORDER BY c.name
                """)
            else:
                # stock_prices(월별) 사용 - 최신 월말 데이터
                logger.info("stock_prices (월별 데이터) 사용 - 최신 월 기준")
                query = text("""
                    WITH latest_prices AS (
                        SELECT
                            sp.company_id,
                            sp.close_price,
                            sp.price_date,
                            ROW_NUMBER() OVER (PARTITION BY sp.company_id ORDER BY sp.price_date DESC) as rn
                        FROM stock_prices sp
                    )
                    SELECT
                        c.id as company_id,
                        c.name,
                        c.ticker,
                        c.shares_outstanding,
                        lp.close_price,
                        NULL::bigint as market_cap_krx,
                        NULL::bigint as listed_shares,
                        lp.price_date as actual_price_date
                    FROM companies c
                    INNER JOIN latest_prices lp ON c.id = lp.company_id AND lp.rn = 1
                    WHERE c.listing_status = 'LISTED'
                      AND c.company_type IN ('NORMAL', 'SPAC', 'REIT')
                    ORDER BY c.name
                """)

            if sample:
                query = text(str(query) + f" LIMIT {sample}")

            # daily_stock_prices 사용 시에만 price_date 파라미터 전달
            if daily_count and daily_count > 0:
                result = await session.execute(query, {"price_date": snapshot_date})
            else:
                result = await session.execute(query)
            companies = [dict(row._mapping) for row in result.fetchall()]

            stats["total_companies"] = len(companies)
            logger.info(f"대상 기업: {len(companies)}개 (종가 있는 기업)")

            for company in companies:
                company_id = str(company["company_id"])
                company_name = company["name"]
                close_price = company["close_price"]
                shares_outstanding = company["shares_outstanding"] or company["listed_shares"]
                market_cap_krx = company["market_cap_krx"]

                stats["price_found"] += 1

                # 시가총액 계산
                if close_price and shares_outstanding:
                    market_cap_calculated = close_price * shares_outstanding
                else:
                    market_cap_calculated = market_cap_krx

                # 재무 데이터 조회
                financial_data = await self.get_latest_financial_data(session, company_id)

                if financial_data:
                    stats["financial_found"] += 1

                # M&A 타겟 점수 계산
                cash_result = self.calculate_cash_ratio_score(
                    financial_data.get("total_liquid_assets") if financial_data else None,
                    market_cap_calculated
                )
                tangible_result = self.calculate_growth_score(
                    financial_data.get("tangible_assets_growth") if financial_data else None,
                    self.WEIGHTS["tangible_growth"]
                )
                revenue_result = self.calculate_growth_score(
                    financial_data.get("revenue_growth") if financial_data else None,
                    self.WEIGHTS["revenue_growth"]
                )
                op_profit_result = self.calculate_growth_score(
                    financial_data.get("operating_income_growth") if financial_data else None,
                    self.WEIGHTS["op_profit_growth"]
                )
                market_cap_result = self.calculate_market_cap_size_score(market_cap_calculated)

                score_result = self.calculate_total_score(
                    cash_result, tangible_result, revenue_result,
                    op_profit_result, market_cap_result
                )

                if score_result["total_score"] > 0:
                    stats["score_calculated"] += 1

                # 스냅샷 레코드 생성
                record = {
                    "company_id": company_id,
                    "snapshot_date": snapshot_date,
                    "close_price": close_price,
                    "market_cap_krx": market_cap_krx,
                    "shares_outstanding": shares_outstanding,
                    "market_cap_calculated": market_cap_calculated,
                    "cash_and_equivalents": financial_data.get("cash_and_equivalents") if financial_data else None,
                    "short_term_investments": financial_data.get("short_term_investments") if financial_data else None,
                    "total_liquid_assets": financial_data.get("total_liquid_assets") if financial_data else None,
                    "tangible_assets": financial_data.get("tangible_assets") if financial_data else None,
                    "revenue": financial_data.get("revenue") if financial_data else None,
                    "operating_profit": financial_data.get("operating_income") if financial_data else None,
                    "tangible_assets_growth": financial_data.get("tangible_assets_growth") if financial_data else None,
                    "revenue_growth": financial_data.get("revenue_growth") if financial_data else None,
                    "operating_profit_growth": financial_data.get("operating_income_growth") if financial_data else None,
                    "ma_target_score": score_result["total_score"],
                    "ma_target_grade": score_result["grade"],
                    "ma_target_factors": json.dumps(score_result["factors"]),
                    "fiscal_year": financial_data.get("fiscal_year") if financial_data else None,
                }

                if dry_run:
                    if stats["saved"] < 3:
                        logger.info(f"[DRY-RUN] {company_name}: {score_result['total_score']} ({score_result['grade']})")
                    stats["saved"] += 1
                    continue

                # 저장 (UPSERT)
                try:
                    stmt = text("""
                        INSERT INTO financial_snapshots (
                            company_id, snapshot_date, close_price, market_cap_krx,
                            shares_outstanding, market_cap_calculated,
                            cash_and_equivalents, short_term_investments, total_liquid_assets,
                            tangible_assets, revenue, operating_profit,
                            tangible_assets_growth, revenue_growth, operating_profit_growth,
                            ma_target_score, ma_target_grade, ma_target_factors, fiscal_year
                        ) VALUES (
                            :company_id, :snapshot_date, :close_price, :market_cap_krx,
                            :shares_outstanding, :market_cap_calculated,
                            :cash_and_equivalents, :short_term_investments, :total_liquid_assets,
                            :tangible_assets, :revenue, :operating_profit,
                            :tangible_assets_growth, :revenue_growth, :operating_profit_growth,
                            :ma_target_score, :ma_target_grade, CAST(:ma_target_factors AS jsonb), :fiscal_year
                        )
                        ON CONFLICT (company_id, snapshot_date)
                        DO UPDATE SET
                            close_price = EXCLUDED.close_price,
                            market_cap_krx = EXCLUDED.market_cap_krx,
                            shares_outstanding = EXCLUDED.shares_outstanding,
                            market_cap_calculated = EXCLUDED.market_cap_calculated,
                            cash_and_equivalents = EXCLUDED.cash_and_equivalents,
                            short_term_investments = EXCLUDED.short_term_investments,
                            total_liquid_assets = EXCLUDED.total_liquid_assets,
                            tangible_assets = EXCLUDED.tangible_assets,
                            revenue = EXCLUDED.revenue,
                            operating_profit = EXCLUDED.operating_profit,
                            tangible_assets_growth = EXCLUDED.tangible_assets_growth,
                            revenue_growth = EXCLUDED.revenue_growth,
                            operating_profit_growth = EXCLUDED.operating_profit_growth,
                            ma_target_score = EXCLUDED.ma_target_score,
                            ma_target_grade = EXCLUDED.ma_target_grade,
                            ma_target_factors = EXCLUDED.ma_target_factors,
                            fiscal_year = EXCLUDED.fiscal_year
                    """)
                    await session.execute(stmt, record)
                    stats["saved"] += 1

                    # 100건마다 커밋 (메모리/성능 최적화)
                    if stats["saved"] % 100 == 0:
                        await session.commit()
                        logger.info(f"진행: {stats['saved']}/{len(companies)} 저장 완료")
                except Exception as e:
                    logger.error(f"저장 실패 ({company_name}): {e}")
                    stats["errors"] += 1
                    await session.rollback()

            if not dry_run:
                await session.commit()  # 남은 건 최종 커밋

        return stats


def get_previous_trading_day() -> date:
    """직전 거래일 계산"""
    today = date.today()
    if today.weekday() == 0:
        return today - timedelta(days=3)
    elif today.weekday() == 6:
        return today - timedelta(days=2)
    else:
        return today - timedelta(days=1)


async def main():
    parser = argparse.ArgumentParser(description="M&A 타겟 점수 계산")
    parser.add_argument(
        "--date",
        type=str,
        help="스냅샷 일자 (YYYY-MM-DD). 기본값: 직전 거래일"
    )
    parser.add_argument(
        "--sample",
        type=int,
        help="샘플 수"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="저장하지 않고 결과만 출력"
    )
    args = parser.parse_args()

    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        logger.error("DATABASE_URL 환경 변수가 설정되지 않았습니다")
        sys.exit(1)

    if db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)

    if args.date:
        snapshot_date = datetime.strptime(args.date, "%Y-%m-%d").date()
    else:
        snapshot_date = get_previous_trading_day()

    logger.info("=== M&A 타겟 점수 계산 시작 ===")
    logger.info(f"스냅샷 일자: {snapshot_date}")
    logger.info(f"샘플: {args.sample or '전체'}")
    logger.info(f"Dry-run: {args.dry_run}")

    calculator = MATargetScoreCalculator(db_url)

    try:
        stats = await calculator.create_snapshots(
            snapshot_date=snapshot_date,
            sample=args.sample,
            dry_run=args.dry_run
        )

        logger.info("=== 계산 결과 ===")
        logger.info(f"대상 기업: {stats['total_companies']}개")
        logger.info(f"종가 있음: {stats['price_found']}개")
        logger.info(f"재무 있음: {stats['financial_found']}개")
        logger.info(f"점수 계산: {stats['score_calculated']}개")
        logger.info(f"저장 완료: {stats['saved']}건")
        logger.info(f"오류: {stats['errors']}개")

    finally:
        await calculator.close()


if __name__ == "__main__":
    asyncio.run(main())
