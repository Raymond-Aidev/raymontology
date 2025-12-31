"""
Stock Price Collector Service

pykrx 라이브러리를 사용하여 KRX 월별 종가 데이터 수집
2022년 1월부터 현재까지 매월 말일 종가 저장
"""
import asyncio
import logging
from datetime import datetime, date
from typing import Optional
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert

from app.models.companies import Company
from app.models.stock_prices import StockPrice

logger = logging.getLogger(__name__)


class StockPriceCollector:
    """
    KRX 월별 종가 수집 서비스

    pykrx 라이브러리 사용 (동기 → asyncio.to_thread로 비동기 래핑)
    """

    # 수집 시작일 (2022년 1월)
    DEFAULT_START_DATE = "20220101"

    # Rate limiting: 요청 간 대기 시간 (초)
    REQUEST_DELAY = 0.5

    def __init__(self):
        self._pykrx_imported = False
        self._stock = None

    def _ensure_pykrx(self):
        """pykrx 지연 import (필요할 때만)"""
        if not self._pykrx_imported:
            try:
                from pykrx import stock
                self._stock = stock
                self._pykrx_imported = True
                logger.info("pykrx 라이브러리 로드 완료")
            except ImportError as e:
                logger.error(f"pykrx 설치 필요: pip install pykrx - {e}")
                raise ImportError("pykrx 라이브러리가 설치되지 않았습니다. pip install pykrx")
        return self._stock

    def _get_monthly_ohlcv_sync(
        self,
        ticker: str,
        start_date: str,
        end_date: str
    ) -> list[dict]:
        """
        동기 방식으로 월별 OHLCV 데이터 수집 (pykrx 호출)

        Args:
            ticker: 종목코드 (6자리, 예: "005930")
            start_date: 시작일 (YYYYMMDD)
            end_date: 종료일 (YYYYMMDD)

        Returns:
            월별 OHLCV 데이터 리스트
        """
        stock = self._ensure_pykrx()

        try:
            # pykrx의 월별 데이터 조회 (frequency="m")
            df = stock.get_market_ohlcv(start_date, end_date, ticker, "m")

            if df.empty:
                logger.warning(f"데이터 없음: {ticker} ({start_date}~{end_date})")
                return []

            results = []
            prev_close = None

            for idx, row in df.iterrows():
                # idx는 날짜 (월말 기준)
                price_date = idx.date() if hasattr(idx, 'date') else idx
                year_month = price_date.strftime("%Y-%m")

                close_price = float(row['종가']) if row['종가'] else None

                # 전월 대비 변동률 계산
                change_rate = None
                if prev_close and prev_close > 0 and close_price:
                    change_rate = ((close_price - prev_close) / prev_close) * 100

                results.append({
                    "price_date": price_date,
                    "year_month": year_month,
                    "open_price": float(row['시가']) if row['시가'] else None,
                    "high_price": float(row['고가']) if row['고가'] else None,
                    "low_price": float(row['저가']) if row['저가'] else None,
                    "close_price": close_price,
                    "volume": int(row['거래량']) if row['거래량'] else None,
                    "change_rate": round(change_rate, 2) if change_rate else None,
                })

                prev_close = close_price

            return results

        except Exception as e:
            logger.error(f"월별 데이터 수집 실패: {ticker} - {e}")
            return []

    async def collect_monthly_prices(
        self,
        ticker: str,
        start_date: str = None,
        end_date: str = None
    ) -> list[dict]:
        """
        비동기 방식으로 월별 종가 수집

        Args:
            ticker: 종목코드 (6자리)
            start_date: 시작일 (기본: 2022-01-01)
            end_date: 종료일 (기본: 오늘)

        Returns:
            월별 OHLCV 데이터 리스트
        """
        if start_date is None:
            start_date = self.DEFAULT_START_DATE
        if end_date is None:
            end_date = datetime.now().strftime("%Y%m%d")

        # 동기 함수를 비동기로 실행
        return await asyncio.to_thread(
            self._get_monthly_ohlcv_sync,
            ticker,
            start_date,
            end_date
        )

    async def save_prices_for_company(
        self,
        db: AsyncSession,
        company_id: UUID,
        ticker: str,
        start_date: str = None,
        end_date: str = None
    ) -> int:
        """
        특정 기업의 월별 종가 수집 및 저장

        Args:
            db: 데이터베이스 세션
            company_id: 기업 UUID
            ticker: 종목코드
            start_date: 시작일
            end_date: 종료일

        Returns:
            저장된 레코드 수
        """
        prices = await self.collect_monthly_prices(ticker, start_date, end_date)

        if not prices:
            return 0

        saved_count = 0

        for price_data in prices:
            # UPSERT: 이미 존재하면 업데이트, 없으면 삽입
            stmt = insert(StockPrice).values(
                company_id=company_id,
                price_date=price_data["price_date"],
                year_month=price_data["year_month"],
                close_price=price_data["close_price"],
                open_price=price_data["open_price"],
                high_price=price_data["high_price"],
                low_price=price_data["low_price"],
                volume=price_data["volume"],
                change_rate=price_data["change_rate"],
            ).on_conflict_do_update(
                constraint='uq_stock_price_company_month',
                set_={
                    'close_price': price_data["close_price"],
                    'open_price': price_data["open_price"],
                    'high_price': price_data["high_price"],
                    'low_price': price_data["low_price"],
                    'volume': price_data["volume"],
                    'change_rate': price_data["change_rate"],
                    'updated_at': func.now(),
                }
            )

            await db.execute(stmt)
            saved_count += 1

        await db.commit()
        logger.info(f"저장 완료: {ticker} - {saved_count}건")

        return saved_count

    async def batch_collect_all_companies(
        self,
        db: AsyncSession,
        start_date: str = None,
        end_date: str = None,
        limit: int = None,
        offset: int = 0
    ) -> dict:
        """
        전체 상장사 일괄 수집 (초기 적재용)

        Args:
            db: 데이터베이스 세션
            start_date: 시작일
            end_date: 종료일
            limit: 처리할 기업 수 제한 (None이면 전체)
            offset: 시작 위치 (이어서 수집할 때 사용)

        Returns:
            수집 결과 통계
        """
        # 상장사만 조회 (ticker가 있는 기업)
        query = select(Company).where(
            Company.ticker.isnot(None),
            Company.ticker != ''
        ).order_by(Company.name)

        if limit:
            query = query.limit(limit).offset(offset)

        result = await db.execute(query)
        companies = result.scalars().all()

        total = len(companies)
        success = 0
        failed = 0
        skipped = 0
        total_records = 0

        logger.info(f"수집 시작: {total}개 기업 (offset={offset})")

        for i, company in enumerate(companies):
            try:
                # 티커 정규화 (6자리 숫자)
                ticker = company.ticker.strip()
                if not ticker.isdigit():
                    logger.warning(f"유효하지 않은 티커 스킵: {company.name} ({ticker})")
                    skipped += 1
                    continue

                # 6자리로 패딩
                ticker = ticker.zfill(6)

                # 월별 종가 수집 및 저장
                count = await self.save_prices_for_company(
                    db, company.id, ticker, start_date, end_date
                )

                if count > 0:
                    success += 1
                    total_records += count
                else:
                    skipped += 1

                # Rate limiting
                await asyncio.sleep(self.REQUEST_DELAY)

                # 진행률 로그 (100개마다)
                if (i + 1) % 100 == 0:
                    logger.info(f"진행률: {i + 1}/{total} ({((i + 1) / total * 100):.1f}%)")

            except Exception as e:
                logger.error(f"수집 실패: {company.name} ({company.ticker}) - {e}")
                failed += 1
                continue

        stats = {
            "total_companies": total,
            "success": success,
            "failed": failed,
            "skipped": skipped,
            "total_records": total_records,
        }

        logger.info(f"수집 완료: {stats}")
        return stats

    async def update_latest_month(
        self,
        db: AsyncSession,
        year_month: str = None
    ) -> dict:
        """
        최신 월 데이터만 업데이트 (월간 스케줄러용)

        Args:
            db: 데이터베이스 세션
            year_month: 대상 월 (기본: 이번 달)

        Returns:
            업데이트 결과 통계
        """
        if year_month is None:
            year_month = datetime.now().strftime("%Y-%m")

        # 해당 월의 시작일과 종료일 계산
        year, month = map(int, year_month.split("-"))
        start_date = f"{year}{month:02d}01"

        # 다음 달 1일 계산
        if month == 12:
            end_date = f"{year + 1}0101"
        else:
            end_date = f"{year}{month + 1:02d}01"

        logger.info(f"월간 업데이트 시작: {year_month}")

        return await self.batch_collect_all_companies(
            db, start_date=start_date, end_date=end_date
        )

    async def get_company_price_count(
        self,
        db: AsyncSession,
        company_id: UUID
    ) -> int:
        """특정 기업의 저장된 가격 데이터 수 조회"""
        result = await db.execute(
            select(func.count(StockPrice.id)).where(
                StockPrice.company_id == company_id
            )
        )
        return result.scalar() or 0

    async def get_collection_status(
        self,
        db: AsyncSession
    ) -> dict:
        """전체 수집 현황 조회"""
        # 전체 상장사 수
        total_listed = await db.execute(
            select(func.count(Company.id)).where(
                Company.ticker.isnot(None),
                Company.ticker != ''
            )
        )
        total_listed_count = total_listed.scalar() or 0

        # 가격 데이터가 있는 기업 수
        companies_with_prices = await db.execute(
            select(func.count(func.distinct(StockPrice.company_id)))
        )
        companies_with_prices_count = companies_with_prices.scalar() or 0

        # 전체 가격 레코드 수
        total_prices = await db.execute(
            select(func.count(StockPrice.id))
        )
        total_prices_count = total_prices.scalar() or 0

        # 최신 데이터 월
        latest_month = await db.execute(
            select(func.max(StockPrice.year_month))
        )
        latest_month_value = latest_month.scalar()

        return {
            "total_listed_companies": total_listed_count,
            "companies_with_prices": companies_with_prices_count,
            "coverage_rate": round(
                (companies_with_prices_count / total_listed_count * 100)
                if total_listed_count > 0 else 0, 1
            ),
            "total_price_records": total_prices_count,
            "latest_data_month": latest_month_value,
        }


# 싱글톤 인스턴스
stock_price_collector = StockPriceCollector()
