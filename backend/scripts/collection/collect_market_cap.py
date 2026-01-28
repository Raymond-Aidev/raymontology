#!/usr/bin/env python3
"""
시가총액/상장주식수 수집 스크립트

pykrx의 get_market_cap() 함수를 사용하여 KRX에서 직접 시가총액과 상장주식수를 수집합니다.

Usage:
    # 전체 기업 수집
    python -m scripts.collection.collect_market_cap --all

    # 샘플 테스트 (10개 기업)
    python -m scripts.collection.collect_market_cap --sample 10

    # 특정 날짜 기준 수집
    python -m scripts.collection.collect_market_cap --all --date 20250127

    # Dry-run (저장 안 함)
    python -m scripts.collection.collect_market_cap --sample 10 --dry-run

    # 수집 현황 조회
    python -m scripts.collection.collect_market_cap --status

환경변수:
    DATABASE_URL: PostgreSQL 연결 문자열
"""
import asyncio
import argparse
import logging
import os
import sys
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

# 프로젝트 루트 경로 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MarketCapCollector:
    """KRX 시가총액/상장주식수 수집기"""

    def __init__(self, db_url: str):
        self.db_url = db_url
        self.engine = create_async_engine(db_url, echo=False)
        self.async_session = sessionmaker(
            self.engine, class_=AsyncSession, expire_on_commit=False
        )
        self._pykrx_stock = None

    async def close(self):
        await self.engine.dispose()

    def _ensure_pykrx(self):
        """pykrx 지연 import"""
        if self._pykrx_stock is None:
            try:
                from pykrx import stock
                self._pykrx_stock = stock
                logger.info("pykrx 라이브러리 로드 완료")
            except ImportError as e:
                logger.error(f"pykrx 설치 필요: pip install pykrx - {e}")
                raise ImportError("pykrx 라이브러리가 설치되지 않았습니다.")
        return self._pykrx_stock

    def _get_market_cap_sync(self, target_date: str, market: str = "ALL") -> Dict[str, Dict[str, Any]]:
        """
        동기 방식으로 시가총액 데이터 수집

        Args:
            target_date: 조회 날짜 (YYYYMMDD)
            market: 시장 구분 (ALL, KOSPI, KOSDAQ)

        Returns:
            {ticker: {market_cap, listed_shares, volume, trading_value}} 딕셔너리
        """
        stock = self._ensure_pykrx()

        result = {}

        try:
            # 전체 시장 조회 시 KOSPI + KOSDAQ 개별 조회
            markets_to_query = ["KOSPI", "KOSDAQ"] if market == "ALL" else [market]

            for mkt in markets_to_query:
                logger.info(f"  {mkt} 시장 조회 중...")
                df = stock.get_market_cap(target_date, market=mkt)

                if df is None or df.empty:
                    logger.warning(f"  {mkt}: 데이터 없음")
                    continue

                for ticker in df.index:
                    row = df.loc[ticker]
                    # pykrx 1.2.3 컬럼명: 종가, 시가총액, 거래량, 거래대금, 상장주식수
                    result[ticker] = {
                        "close_price": int(row['종가']) if row['종가'] else None,
                        "market_cap": int(row['시가총액']) if row['시가총액'] else None,
                        "listed_shares": int(row['상장주식수']) if row['상장주식수'] else None,
                        "volume": int(row['거래량']) if row['거래량'] else None,
                        "trading_value": int(row['거래대금']) if row['거래대금'] else None,
                        "market": mkt,
                    }

                logger.info(f"  {mkt}: {len(df)}개 종목 조회")

            return result

        except Exception as e:
            logger.error(f"시가총액 조회 실패: {e}")
            return {}

    async def get_market_cap_data(self, target_date: str, market: str = "ALL") -> Dict[str, Dict[str, Any]]:
        """비동기 방식으로 시가총액 데이터 수집"""
        return await asyncio.to_thread(self._get_market_cap_sync, target_date, market)

    async def get_companies_ticker_map(self, session: AsyncSession, sample: Optional[int] = None) -> Dict[str, Dict[str, Any]]:
        """
        기업 티커 매핑 조회

        Returns:
            {ticker: {id, name, current_market_cap, current_shares}} 딕셔너리
        """
        query = text("""
            SELECT id, ticker, name, market, market_cap, shares_outstanding
            FROM companies
            WHERE ticker IS NOT NULL
              AND ticker != ''
              AND listing_status = 'LISTED'
              AND company_type IN ('NORMAL', 'SPAC', 'REIT')
            ORDER BY name
        """)

        if sample:
            query = text(f"""
                SELECT id, ticker, name, market, market_cap, shares_outstanding
                FROM companies
                WHERE ticker IS NOT NULL
                  AND ticker != ''
                  AND listing_status = 'LISTED'
                  AND company_type IN ('NORMAL', 'SPAC', 'REIT')
                ORDER BY name
                LIMIT {sample}
            """)

        result = await session.execute(query)
        rows = result.fetchall()

        return {
            row.ticker.zfill(6): {
                "id": str(row.id),
                "name": row.name,
                "market": row.market,
                "current_market_cap": row.market_cap,
                "current_shares": row.shares_outstanding,
            }
            for row in rows
        }

    async def collect_and_save(
        self,
        target_date: str = None,
        sample: Optional[int] = None,
        dry_run: bool = False
    ) -> Dict[str, int]:
        """
        시가총액/상장주식수 수집 및 저장

        Args:
            target_date: 조회 날짜 (YYYYMMDD, 기본값: 오늘 또는 최근 거래일)
            sample: 샘플 수 (None이면 전체)
            dry_run: True면 저장하지 않음

        Returns:
            수집 통계
        """
        stats = {
            "target_date": target_date,
            "krx_total": 0,
            "db_companies": 0,
            "matched": 0,
            "updated_market_cap": 0,
            "updated_shares": 0,
            "skipped": 0,
        }

        # 날짜 기본값: 오늘
        if not target_date:
            target_date = datetime.now().strftime("%Y%m%d")
        stats["target_date"] = target_date

        logger.info(f"=== 시가총액 수집 시작 ===")
        logger.info(f"조회 날짜: {target_date}")
        logger.info(f"샘플: {sample or '전체'}")
        logger.info(f"Dry-run: {dry_run}")

        # 1. KRX에서 시가총액 데이터 수집
        logger.info("\n[1/3] KRX 시가총액 조회 중...")
        krx_data = await self.get_market_cap_data(target_date)
        stats["krx_total"] = len(krx_data)
        logger.info(f"KRX 조회 결과: {len(krx_data)}개 종목")

        if not krx_data:
            logger.error("KRX 데이터 조회 실패 (휴장일이거나 네트워크 오류)")
            return stats

        # 2. DB 기업 조회
        async with self.async_session() as session:
            logger.info("\n[2/3] DB 기업 조회 중...")
            companies = await self.get_companies_ticker_map(session, sample)
            stats["db_companies"] = len(companies)
            logger.info(f"DB 기업: {len(companies)}개")

            # 3. 매칭 및 배치 업데이트
            logger.info("\n[3/3] 데이터 매칭 및 업데이트 중...")

            # 업데이트할 데이터 수집
            updates = []
            for ticker, company in companies.items():
                if ticker not in krx_data:
                    stats["skipped"] += 1
                    continue

                krx = krx_data[ticker]
                stats["matched"] += 1

                market_cap = krx["market_cap"]
                shares = krx["listed_shares"]

                if dry_run:
                    # 샘플 출력 (처음 5개만)
                    if stats["matched"] <= 5:
                        market_cap_억 = market_cap / 100000000 if market_cap else 0
                        shares_만 = shares / 10000 if shares else 0
                        logger.info(
                            f"  [DRY-RUN] {company['name']} ({ticker}): "
                            f"시가총액 {market_cap_억:,.0f}억원, "
                            f"상장주식수 {shares_만:,.0f}만주"
                        )
                    continue

                updates.append({
                    "company_id": company["id"],
                    "market_cap": market_cap,
                    "shares": shares,
                })

                if market_cap:
                    stats["updated_market_cap"] += 1
                if shares:
                    stats["updated_shares"] += 1

            # 배치 업데이트 실행
            if not dry_run and updates:
                logger.info(f"  {len(updates)}개 기업 배치 업데이트 중...")

                # 100개씩 배치 처리
                batch_size = 100
                for i in range(0, len(updates), batch_size):
                    batch = updates[i:i + batch_size]

                    # VALUES 절 생성
                    values_list = ", ".join([
                        f"('{u['company_id']}'::uuid, {u['market_cap'] or 'NULL'}, {u['shares'] or 'NULL'})"
                        for u in batch
                    ])

                    batch_update = text(f"""
                        UPDATE companies AS c
                        SET market_cap = v.market_cap,
                            shares_outstanding = v.shares,
                            shares_updated_at = NOW()
                        FROM (VALUES {values_list}) AS v(id, market_cap, shares)
                        WHERE c.id = v.id
                    """)

                    await session.execute(batch_update)

                    if (i + batch_size) % 500 == 0 or i + batch_size >= len(updates):
                        logger.info(f"  진행: {min(i + batch_size, len(updates))}/{len(updates)}")

                await session.commit()
                logger.info(f"  배치 업데이트 완료!")

        return stats

    async def get_status(self) -> Dict[str, Any]:
        """수집 현황 조회"""
        async with self.async_session() as session:
            result = await session.execute(text("""
                SELECT
                    COUNT(*) as total_companies,
                    COUNT(market_cap) as with_market_cap,
                    COUNT(shares_outstanding) as with_shares,
                    MAX(shares_updated_at) as last_updated,
                    AVG(market_cap) / 100000000 as avg_market_cap_억,
                    SUM(market_cap) / 1000000000000 as total_market_cap_조
                FROM companies
                WHERE listing_status = 'LISTED'
                  AND company_type IN ('NORMAL', 'SPAC', 'REIT')
            """))
            row = result.fetchone()

            return {
                "total_companies": row.total_companies,
                "with_market_cap": row.with_market_cap,
                "with_shares": row.with_shares,
                "market_cap_coverage": round(row.with_market_cap / row.total_companies * 100, 1) if row.total_companies else 0,
                "shares_coverage": round(row.with_shares / row.total_companies * 100, 1) if row.total_companies else 0,
                "last_updated": row.last_updated.isoformat() if row.last_updated else None,
                "avg_market_cap_억": round(row.avg_market_cap_억, 0) if row.avg_market_cap_억 else None,
                "total_market_cap_조": round(row.total_market_cap_조, 1) if row.total_market_cap_조 else None,
            }


async def main():
    parser = argparse.ArgumentParser(description="KRX 시가총액/상장주식수 수집")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--all", action="store_true", help="전체 기업 수집")
    group.add_argument("--sample", type=int, help="샘플 수 (테스트용)")
    group.add_argument("--status", action="store_true", help="수집 현황 조회")

    parser.add_argument(
        "--date",
        type=str,
        help="조회 날짜 (YYYYMMDD, 기본값: 오늘)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="저장하지 않고 결과만 출력"
    )
    args = parser.parse_args()

    # 환경 변수
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        logger.error("DATABASE_URL 환경 변수가 설정되지 않았습니다")
        sys.exit(1)

    # asyncpg 드라이버
    if db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)

    collector = MarketCapCollector(db_url)

    try:
        if args.status:
            status = await collector.get_status()
            logger.info("=== 수집 현황 ===")
            logger.info(f"전체 기업: {status['total_companies']}개")
            logger.info(f"시가총액 보유: {status['with_market_cap']}개 ({status['market_cap_coverage']}%)")
            logger.info(f"상장주식수 보유: {status['with_shares']}개 ({status['shares_coverage']}%)")
            logger.info(f"마지막 업데이트: {status['last_updated'] or 'N/A'}")
            logger.info(f"평균 시가총액: {status['avg_market_cap_억']:,.0f}억원" if status['avg_market_cap_억'] else "평균 시가총액: N/A")
            logger.info(f"총 시가총액: {status['total_market_cap_조']:,.1f}조원" if status['total_market_cap_조'] else "총 시가총액: N/A")
        else:
            stats = await collector.collect_and_save(
                target_date=args.date,
                sample=args.sample,
                dry_run=args.dry_run
            )

            logger.info("\n=== 수집 결과 ===")
            logger.info(f"조회 날짜: {stats['target_date']}")
            logger.info(f"KRX 종목: {stats['krx_total']}개")
            logger.info(f"DB 기업: {stats['db_companies']}개")
            logger.info(f"매칭: {stats['matched']}개")
            logger.info(f"시가총액 업데이트: {stats['updated_market_cap']}개")
            logger.info(f"상장주식수 업데이트: {stats['updated_shares']}개")
            logger.info(f"스킵 (KRX 미존재): {stats['skipped']}개")

    finally:
        await collector.close()


if __name__ == "__main__":
    asyncio.run(main())
