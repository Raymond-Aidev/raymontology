#!/usr/bin/env python3
"""
거래정지 상태 업데이트 스크립트

DART 공시 기반으로 거래정지/정지해제 기업을 식별하여 DB 업데이트합니다.

사용법:
    # Dry-run (변경 내용 확인만)
    python update_trading_status.py --dry-run

    # 실제 업데이트
    python update_trading_status.py

    # 특정 종목만 업데이트
    python update_trading_status.py --ticker 008110 --status SUSPENDED

거래정지 유형:
    - SUSPENDED: 장기 거래정지 (개선기간, 회생절차, 실질심사 등)
    - TRADING_HALT: 일시 거래정지 (무상증자, 액면분할 등 - 보통 1~2일)
    - NORMAL: 정상 거래

v1.0 - 2026-01-24
"""

import os
import sys
import argparse
import asyncio
from datetime import datetime, timedelta
from typing import Optional

# 프로젝트 루트를 path에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker


# 장기 거래정지 키워드 (SUSPENDED로 분류)
SUSPENDED_KEYWORDS = [
    '개선기간',
    '회생절차',
    '파산',
    '상장폐지',
    '실질심사 대상',
    '지정자문인 계약해지',
    '자진상장폐지',
]

# 단기 거래정지 키워드 (해제 공시 확인 필요)
TRADING_HALT_KEYWORDS = [
    '무상증자',
    '액면분할',
    '액면병합',
    '주식의 병합',
    '단일판매공급계약',
    '영업양수도',
    'SPAC 소멸합병',
]

# 거래정지 해제 키워드
RELEASE_KEYWORDS = [
    '거래정지해제',
    '정지해제',
    '변경상장',
    '정리매매 개시',
    '사유발생 해소',
]


async def get_trading_status_from_disclosures(session: AsyncSession, days_back: int = 365):
    """
    DART 공시에서 거래정지/해제 정보를 추출합니다.

    Returns:
        dict: {stock_code: {'status': 'SUSPENDED'|'NORMAL', 'reason': str, 'date': str}}
    """
    cutoff_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y%m%d')

    query = text("""
        SELECT DISTINCT ON (d.stock_code)
            d.stock_code,
            d.corp_name,
            d.report_nm,
            d.rcept_dt
        FROM disclosures d
        WHERE d.stock_code IS NOT NULL
          AND d.stock_code != ''
          AND (d.report_nm LIKE '%매매거래정지%' OR d.report_nm LIKE '%거래정지%')
          AND d.rcept_dt >= :cutoff_date
        ORDER BY d.stock_code, d.rcept_dt DESC
    """)

    result = await session.execute(query, {'cutoff_date': cutoff_date})
    rows = result.fetchall()

    status_map = {}

    for row in rows:
        stock_code = row.stock_code
        report_nm = row.report_nm
        rcept_dt = row.rcept_dt

        # 해제 공시인지 확인
        is_released = any(kw in report_nm for kw in RELEASE_KEYWORDS)

        if is_released:
            status_map[stock_code] = {
                'status': 'NORMAL',
                'reason': f'거래정지 해제: {report_nm}',
                'date': rcept_dt,
                'corp_name': row.corp_name,
            }
        else:
            # 장기 거래정지인지 확인
            is_long_term = any(kw in report_nm for kw in SUSPENDED_KEYWORDS)

            status_map[stock_code] = {
                'status': 'SUSPENDED' if is_long_term else 'TRADING_HALT',
                'reason': report_nm,
                'date': rcept_dt,
                'corp_name': row.corp_name,
            }

    return status_map


async def get_current_trading_status(session: AsyncSession):
    """현재 DB의 trading_status 조회"""
    query = text("""
        SELECT ticker, name, trading_status
        FROM companies
        WHERE listing_status = 'LISTED'
          AND ticker IS NOT NULL
    """)
    result = await session.execute(query)
    return {row.ticker: {'name': row.name, 'status': row.trading_status} for row in result.fetchall()}


async def update_trading_status(
    session: AsyncSession,
    ticker: str,
    status: str,
    dry_run: bool = True
):
    """기업의 trading_status 업데이트"""
    if dry_run:
        print(f"  [DRY-RUN] {ticker} -> {status}")
        return

    query = text("""
        UPDATE companies
        SET trading_status = :status
        WHERE ticker = :ticker
        RETURNING ticker, name, trading_status
    """)

    result = await session.execute(query, {'ticker': ticker, 'status': status})
    row = result.fetchone()

    if row:
        print(f"  [UPDATED] {row.ticker} ({row.name}) -> {row.trading_status}")
    else:
        print(f"  [NOT FOUND] {ticker}")


async def main(args):
    """메인 실행 함수"""
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("ERROR: DATABASE_URL 환경변수가 필요합니다.")
        sys.exit(1)

    # asyncpg 사용을 위해 URL 변환
    if database_url.startswith('postgresql://'):
        database_url = database_url.replace('postgresql://', 'postgresql+asyncpg://')

    engine = create_async_engine(database_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # 단일 종목 업데이트
        if args.ticker:
            if not args.status:
                print("ERROR: --status 옵션이 필요합니다. (NORMAL, SUSPENDED, TRADING_HALT)")
                sys.exit(1)

            await update_trading_status(session, args.ticker, args.status, args.dry_run)

            if not args.dry_run:
                await session.commit()
            return

        # 전체 스캔
        print("=" * 60)
        print("거래정지 상태 스캔")
        print("=" * 60)

        # 1. 현재 DB 상태 조회
        current_status = await get_current_trading_status(session)
        print(f"\n현재 상장 기업 수: {len(current_status)}")

        # 2. DART 공시에서 거래정지 정보 추출
        print(f"\n최근 {args.days}일 공시 스캔 중...")
        disclosure_status = await get_trading_status_from_disclosures(session, args.days)
        print(f"거래정지 관련 공시 발견: {len(disclosure_status)}건")

        # 3. 변경 필요한 기업 식별
        changes = []

        for ticker, info in disclosure_status.items():
            if ticker not in current_status:
                continue

            current = current_status[ticker]['status']
            new = info['status']

            if current != new:
                changes.append({
                    'ticker': ticker,
                    'name': info['corp_name'],
                    'current': current,
                    'new': new,
                    'reason': info['reason'],
                    'date': info['date'],
                })

        # 4. 변경 내용 출력
        if not changes:
            print("\n변경 필요한 기업이 없습니다.")
            return

        print(f"\n변경 필요: {len(changes)}건")
        print("-" * 60)

        for change in changes:
            print(f"\n{change['ticker']} {change['name']}")
            print(f"  현재: {change['current']} -> 변경: {change['new']}")
            print(f"  사유: {change['reason']} ({change['date']})")

        # 5. 업데이트 실행
        if args.dry_run:
            print("\n[DRY-RUN 모드] 실제 업데이트를 수행하려면 --dry-run 옵션을 제거하세요.")
        else:
            print("\n업데이트 실행 중...")
            for change in changes:
                await update_trading_status(
                    session,
                    change['ticker'],
                    change['new'],
                    dry_run=False
                )
            await session.commit()
            print("\n업데이트 완료!")

        # 6. 현재 거래정지 기업 목록 출력
        print("\n" + "=" * 60)
        print("현재 거래정지 기업 목록")
        print("=" * 60)

        query = text("""
            SELECT ticker, name, trading_status, market
            FROM companies
            WHERE trading_status != 'NORMAL'
              AND listing_status = 'LISTED'
            ORDER BY trading_status, market, name
        """)
        result = await session.execute(query)
        suspended = result.fetchall()

        if suspended:
            for row in suspended:
                print(f"  {row.ticker} {row.name} [{row.market}] - {row.trading_status}")
        else:
            print("  (없음)")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='거래정지 상태 업데이트')
    parser.add_argument('--dry-run', action='store_true', help='실제 업데이트 없이 확인만')
    parser.add_argument('--ticker', type=str, help='특정 종목 코드')
    parser.add_argument('--status', type=str, choices=['NORMAL', 'SUSPENDED', 'TRADING_HALT'],
                        help='설정할 상태')
    parser.add_argument('--days', type=int, default=365, help='스캔할 기간 (일)')

    args = parser.parse_args()
    asyncio.run(main(args))
