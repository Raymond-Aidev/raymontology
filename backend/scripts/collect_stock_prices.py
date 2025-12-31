#!/usr/bin/env python3
"""
월별 주가 데이터 수집 스크립트

사용법:
    # 전체 기업 수집 (초기 적재)
    python scripts/collect_stock_prices.py --all

    # 특정 기업만 수집 (테스트)
    python scripts/collect_stock_prices.py --ticker 005930

    # 최근 N개 기업만 수집 (테스트)
    python scripts/collect_stock_prices.py --limit 10

    # 특정 월만 업데이트
    python scripts/collect_stock_prices.py --month 2024-12

    # 수집 현황 조회
    python scripts/collect_stock_prices.py --status

    # 이어서 수집 (offset 지정)
    python scripts/collect_stock_prices.py --all --offset 1000
"""
import asyncio
import argparse
import sys
import os
from datetime import datetime

# 프로젝트 루트를 path에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models.companies import Company
from app.services.stock_price_collector import stock_price_collector


async def collect_single_ticker(ticker: str, start_date: str = None, end_date: str = None):
    """단일 종목 수집"""
    print(f"\n=== 단일 종목 수집: {ticker} ===")

    async with AsyncSessionLocal() as db:
        # 해당 티커의 기업 조회
        result = await db.execute(
            select(Company).where(Company.ticker == ticker)
        )
        company = result.scalar_one_or_none()

        if not company:
            # 6자리 패딩해서 다시 시도
            padded_ticker = ticker.zfill(6)
            result = await db.execute(
                select(Company).where(Company.ticker == padded_ticker)
            )
            company = result.scalar_one_or_none()

        if not company:
            print(f"기업을 찾을 수 없습니다: {ticker}")
            return

        print(f"기업: {company.name} ({company.ticker})")

        count = await stock_price_collector.save_prices_for_company(
            db, company.id, company.ticker.zfill(6), start_date, end_date
        )

        print(f"저장된 레코드: {count}건")


async def collect_all_companies(
    limit: int = None,
    offset: int = 0,
    start_date: str = None,
    end_date: str = None
):
    """전체 상장사 수집"""
    print(f"\n=== 전체 상장사 수집 ===")
    print(f"시작일: {start_date or '2022-01-01'}")
    print(f"종료일: {end_date or '오늘'}")
    print(f"Limit: {limit or '전체'}, Offset: {offset}")
    print()

    async with AsyncSessionLocal() as db:
        stats = await stock_price_collector.batch_collect_all_companies(
            db,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
            offset=offset
        )

        print("\n=== 수집 결과 ===")
        print(f"전체 기업: {stats['total_companies']}개")
        print(f"성공: {stats['success']}개")
        print(f"실패: {stats['failed']}개")
        print(f"스킵: {stats['skipped']}개")
        print(f"총 레코드: {stats['total_records']}건")


async def update_month(year_month: str):
    """특정 월 데이터 업데이트"""
    print(f"\n=== 월간 업데이트: {year_month} ===")

    async with AsyncSessionLocal() as db:
        stats = await stock_price_collector.update_latest_month(db, year_month)

        print("\n=== 업데이트 결과 ===")
        print(f"성공: {stats['success']}개")
        print(f"실패: {stats['failed']}개")
        print(f"총 레코드: {stats['total_records']}건")


async def show_status():
    """수집 현황 조회"""
    print("\n=== 수집 현황 ===")

    async with AsyncSessionLocal() as db:
        status = await stock_price_collector.get_collection_status(db)

        print(f"전체 상장사: {status['total_listed_companies']}개")
        print(f"수집 완료: {status['companies_with_prices']}개")
        print(f"커버리지: {status['coverage_rate']}%")
        print(f"총 가격 레코드: {status['total_price_records']:,}건")
        print(f"최신 데이터 월: {status['latest_data_month'] or 'N/A'}")


async def main():
    parser = argparse.ArgumentParser(description="월별 주가 데이터 수집")

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--all", action="store_true", help="전체 상장사 수집")
    group.add_argument("--ticker", type=str, help="특정 종목 수집 (예: 005930)")
    group.add_argument("--month", type=str, help="특정 월 업데이트 (예: 2024-12)")
    group.add_argument("--status", action="store_true", help="수집 현황 조회")

    parser.add_argument("--limit", type=int, default=None, help="수집할 기업 수 제한")
    parser.add_argument("--offset", type=int, default=0, help="시작 위치 (이어서 수집)")
    parser.add_argument("--start-date", type=str, default=None, help="시작일 (YYYYMMDD)")
    parser.add_argument("--end-date", type=str, default=None, help="종료일 (YYYYMMDD)")

    args = parser.parse_args()

    start_time = datetime.now()
    print(f"시작 시간: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")

    try:
        if args.status:
            await show_status()
        elif args.ticker:
            await collect_single_ticker(
                args.ticker,
                args.start_date,
                args.end_date
            )
        elif args.month:
            await update_month(args.month)
        elif args.all:
            await collect_all_companies(
                limit=args.limit,
                offset=args.offset,
                start_date=args.start_date,
                end_date=args.end_date
            )

    except KeyboardInterrupt:
        print("\n\n수집이 중단되었습니다.")
    except Exception as e:
        print(f"\n오류 발생: {e}")
        raise

    end_time = datetime.now()
    duration = end_time - start_time
    print(f"\n종료 시간: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"소요 시간: {duration}")


if __name__ == "__main__":
    asyncio.run(main())
