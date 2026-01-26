"""
KRX 일별 종가 수집 스크립트

KRX 정보데이터시스템에서 전일 종가 데이터를 수집하여
daily_stock_prices 테이블에 저장합니다.

Usage:
    python -m scripts.collection.collect_daily_prices
    python -m scripts.collection.collect_daily_prices --date 2026-01-24
    python -m scripts.collection.collect_daily_prices --dry-run

스케줄러 연동:
    매일 10:00 KST에 실행 (전일 종가 수집)
"""
import asyncio
import argparse
import logging
from datetime import date, datetime, timedelta
from typing import Optional, List, Dict, Any
import httpx
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

import os
import sys

# 프로젝트 루트 경로 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.models.daily_stock_price import DailyStockPrice
from app.models.companies import Company

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class KRXPriceCollector:
    """KRX 정보데이터시스템 일별 시세 수집기"""

    # KRX 데이터 조회 URL
    KRX_API_URL = "http://data.krx.co.kr/comm/bldAttendant/getJsonData.cmd"

    # 시장별 조회 코드
    MARKET_CODES = {
        "KOSPI": "STK",  # 유가증권
        "KOSDAQ": "KSQ",  # 코스닥
    }

    def __init__(self, db_url: str):
        self.db_url = db_url
        self.engine = create_async_engine(db_url, echo=False)
        self.async_session = sessionmaker(
            self.engine, class_=AsyncSession, expire_on_commit=False
        )
        self.client = httpx.AsyncClient(timeout=60.0)

    async def close(self):
        await self.client.aclose()
        await self.engine.dispose()

    async def fetch_krx_market_data(
        self, market_segment: str, target_date: date
    ) -> List[Dict[str, Any]]:
        """
        KRX에서 특정 시장의 일별 시세 조회

        Args:
            market_segment: 시장 구분 (STK: KOSPI, KSQ: KOSDAQ)
            target_date: 조회 일자

        Returns:
            종목별 시세 리스트
        """
        # KRX 날짜 형식 (YYYYMMDD)
        date_str = target_date.strftime("%Y%m%d")

        # 요청 파라미터
        params = {
            "bld": "dbms/MDC/STAT/standard/MDCSTAT01501",
            "locale": "ko_KR",
            "mktId": market_segment,
            "trdDd": date_str,
            "share": "1",
            "money": "1",
            "csvxls_is498hNo": "false",
        }

        try:
            response = await self.client.post(
                self.KRX_API_URL,
                data=params,
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    "Referer": "http://data.krx.co.kr/contents/MDC/MDI/mdiLoader/index.cmd?menuId=MDC0201020101",
                }
            )
            response.raise_for_status()

            data = response.json()
            return data.get("OutBlock_1", [])

        except Exception as e:
            logger.error(f"KRX API 호출 실패 ({market_segment}): {e}")
            return []

    def parse_krx_number(self, value: str) -> Optional[int]:
        """KRX 숫자 문자열을 정수로 변환 (쉼표 제거)"""
        if not value or value == "-":
            return None
        try:
            return int(value.replace(",", ""))
        except ValueError:
            return None

    async def get_company_ticker_map(self, session: AsyncSession) -> Dict[str, str]:
        """ticker -> company_id 매핑 조회"""
        result = await session.execute(
            select(Company.id, Company.ticker)
            .where(Company.ticker.isnot(None))
            .where(Company.listing_status == 'LISTED')
        )
        return {row.ticker: str(row.id) for row in result.fetchall()}

    async def collect_and_save(
        self,
        target_date: date,
        dry_run: bool = False
    ) -> Dict[str, int]:
        """
        KRX 데이터 수집 및 저장

        Args:
            target_date: 수집 대상 일자
            dry_run: True면 저장하지 않고 결과만 출력

        Returns:
            수집 통계 (kospi_count, kosdaq_count, saved_count, errors)
        """
        stats = {
            "kospi_count": 0,
            "kosdaq_count": 0,
            "matched_count": 0,
            "saved_count": 0,
            "errors": 0,
        }

        async with self.async_session() as session:
            # 회사 ticker 매핑 조회
            ticker_map = await self.get_company_ticker_map(session)
            logger.info(f"DB에서 {len(ticker_map)}개 상장사 ticker 로드")

            all_records = []

            # KOSPI 데이터 수집
            logger.info(f"KOSPI 시세 조회 중... ({target_date})")
            kospi_data = await self.fetch_krx_market_data("STK", target_date)
            stats["kospi_count"] = len(kospi_data)
            logger.info(f"KOSPI: {len(kospi_data)}개 종목")

            for item in kospi_data:
                record = self._parse_krx_item(item, ticker_map, target_date)
                if record:
                    all_records.append(record)

            # KOSDAQ 데이터 수집
            logger.info(f"KOSDAQ 시세 조회 중... ({target_date})")
            kosdaq_data = await self.fetch_krx_market_data("KSQ", target_date)
            stats["kosdaq_count"] = len(kosdaq_data)
            logger.info(f"KOSDAQ: {len(kosdaq_data)}개 종목")

            for item in kosdaq_data:
                record = self._parse_krx_item(item, ticker_map, target_date)
                if record:
                    all_records.append(record)

            stats["matched_count"] = len(all_records)
            logger.info(f"DB 매칭 완료: {len(all_records)}개 종목")

            if dry_run:
                logger.info("[DRY-RUN] 저장하지 않음")
                if all_records:
                    logger.info(f"샘플 데이터: {all_records[0]}")
                return stats

            # 저장
            for record in all_records:
                try:
                    # UPSERT (기존 데이터 있으면 업데이트)
                    stmt = text("""
                        INSERT INTO daily_stock_prices
                        (company_id, price_date, close_price, open_price, high_price, low_price,
                         volume, trading_value, market_cap, listed_shares)
                        VALUES (:company_id, :price_date, :close_price, :open_price, :high_price, :low_price,
                                :volume, :trading_value, :market_cap, :listed_shares)
                        ON CONFLICT (company_id, price_date)
                        DO UPDATE SET
                            close_price = EXCLUDED.close_price,
                            open_price = EXCLUDED.open_price,
                            high_price = EXCLUDED.high_price,
                            low_price = EXCLUDED.low_price,
                            volume = EXCLUDED.volume,
                            trading_value = EXCLUDED.trading_value,
                            market_cap = EXCLUDED.market_cap,
                            listed_shares = EXCLUDED.listed_shares
                    """)
                    await session.execute(stmt, record)
                    stats["saved_count"] += 1
                except Exception as e:
                    logger.error(f"저장 실패 (company_id={record['company_id']}): {e}")
                    stats["errors"] += 1

            await session.commit()
            logger.info(f"저장 완료: {stats['saved_count']}건")

        return stats

    def _parse_krx_item(
        self,
        item: Dict[str, Any],
        ticker_map: Dict[str, str],
        target_date: date
    ) -> Optional[Dict[str, Any]]:
        """KRX 응답 항목을 DB 레코드로 변환"""
        # 종목코드 (6자리)
        ticker = item.get("ISU_SRT_CD", "")

        # DB에 없는 종목은 스킵
        if ticker not in ticker_map:
            return None

        company_id = ticker_map[ticker]

        return {
            "company_id": company_id,
            "price_date": target_date,
            "close_price": self.parse_krx_number(item.get("TDD_CLSPRC")),
            "open_price": self.parse_krx_number(item.get("TDD_OPNPRC")),
            "high_price": self.parse_krx_number(item.get("TDD_HGPRC")),
            "low_price": self.parse_krx_number(item.get("TDD_LWPRC")),
            "volume": self.parse_krx_number(item.get("ACC_TRDVOL")),
            "trading_value": self.parse_krx_number(item.get("ACC_TRDVAL")),
            "market_cap": self.parse_krx_number(item.get("MKTCAP")),
            "listed_shares": self.parse_krx_number(item.get("LIST_SHRS")),
        }


def get_previous_trading_day() -> date:
    """
    직전 거래일 계산 (주말/공휴일 제외)

    단순 구현: 토요일이면 금요일, 일요일이면 금요일 반환
    실제로는 공휴일 캘린더 필요
    """
    today = date.today()

    # 월요일이면 금요일 (3일 전)
    if today.weekday() == 0:
        return today - timedelta(days=3)
    # 일요일이면 금요일 (2일 전)
    elif today.weekday() == 6:
        return today - timedelta(days=2)
    # 그 외는 전일
    else:
        return today - timedelta(days=1)


async def main():
    parser = argparse.ArgumentParser(description="KRX 일별 종가 수집")
    parser.add_argument(
        "--date",
        type=str,
        help="수집 대상 일자 (YYYY-MM-DD). 기본값: 직전 거래일"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="저장하지 않고 결과만 출력"
    )
    args = parser.parse_args()

    # 환경 변수에서 DB URL 읽기
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        logger.error("DATABASE_URL 환경 변수가 설정되지 않았습니다")
        sys.exit(1)

    # asyncpg 드라이버 사용
    if db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)

    # 대상 일자 결정
    if args.date:
        target_date = datetime.strptime(args.date, "%Y-%m-%d").date()
    else:
        target_date = get_previous_trading_day()

    logger.info(f"=== KRX 일별 종가 수집 시작 ===")
    logger.info(f"대상 일자: {target_date}")
    logger.info(f"Dry-run: {args.dry_run}")

    collector = KRXPriceCollector(db_url)

    try:
        stats = await collector.collect_and_save(
            target_date=target_date,
            dry_run=args.dry_run
        )

        logger.info("=== 수집 결과 ===")
        logger.info(f"KOSPI: {stats['kospi_count']}개")
        logger.info(f"KOSDAQ: {stats['kosdaq_count']}개")
        logger.info(f"DB 매칭: {stats['matched_count']}개")
        logger.info(f"저장 완료: {stats['saved_count']}개")
        logger.info(f"오류: {stats['errors']}개")

    finally:
        await collector.close()


if __name__ == "__main__":
    asyncio.run(main())
