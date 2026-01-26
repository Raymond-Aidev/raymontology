"""
DART 발행주식수 수집 스크립트

DART Open API의 stockTotqySttus (주식총수현황) API를 사용하여
발행주식수 데이터를 수집합니다.

Usage:
    python -m scripts.collection.collect_shares_outstanding
    python -m scripts.collection.collect_shares_outstanding --year 2024
    python -m scripts.collection.collect_shares_outstanding --sample 10 --dry-run

환경변수:
    DATABASE_URL: PostgreSQL 연결 문자열
    DART_API_KEY: DART Open API 키
"""
import asyncio
import argparse
import logging
import os
import sys
from datetime import datetime
from typing import Optional, List, Dict, Any
import httpx
from sqlalchemy import select, update, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

# 프로젝트 루트 경로 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.models.stock_info import StockInfo
from app.models.companies import Company

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DARTSharesCollector:
    """DART 발행주식수 수집기"""

    DART_API_BASE = "https://opendart.fss.or.kr/api"

    # 보고서 코드
    REPORT_CODES = {
        "11011": "사업보고서",
        "11012": "반기보고서",
        "11013": "1분기보고서",
        "11014": "3분기보고서",
    }

    def __init__(self, db_url: str, dart_api_key: str):
        self.db_url = db_url
        self.dart_api_key = dart_api_key
        self.engine = create_async_engine(db_url, echo=False)
        self.async_session = sessionmaker(
            self.engine, class_=AsyncSession, expire_on_commit=False
        )
        self.client = httpx.AsyncClient(timeout=30.0)

    async def close(self):
        await self.client.aclose()
        await self.engine.dispose()

    async def fetch_stock_totqy_status(
        self,
        corp_code: str,
        bsns_year: int,
        reprt_code: str = "11011"
    ) -> Optional[List[Dict[str, Any]]]:
        """
        DART 주식총수현황 API 호출

        Args:
            corp_code: 기업 고유번호 (8자리)
            bsns_year: 사업연도
            reprt_code: 보고서 코드 (11011: 사업보고서)

        Returns:
            주식총수현황 리스트 또는 None
        """
        url = f"{self.DART_API_BASE}/stockTotqySttus.json"

        params = {
            "crtfc_key": self.dart_api_key,
            "corp_code": corp_code,
            "bsns_year": str(bsns_year),
            "reprt_code": reprt_code,
        }

        try:
            response = await self.client.get(url, params=params)
            response.raise_for_status()

            data = response.json()

            if data.get("status") == "000":  # 성공
                return data.get("list", [])
            elif data.get("status") == "013":  # 데이터 없음
                return None
            else:
                logger.warning(
                    f"DART API 응답 오류 (corp_code={corp_code}): "
                    f"{data.get('status')} - {data.get('message')}"
                )
                return None

        except Exception as e:
            logger.error(f"DART API 호출 실패 (corp_code={corp_code}): {e}")
            return None

    def parse_dart_number(self, value: str) -> Optional[int]:
        """DART 숫자 문자열을 정수로 변환"""
        if not value or value == "-" or value == "":
            return None
        try:
            return int(value.replace(",", ""))
        except ValueError:
            return None

    def extract_shares_data(
        self,
        stock_data: List[Dict[str, Any]],
        company_id: str,
        fiscal_year: int,
        report_code: str
    ) -> Optional[Dict[str, Any]]:
        """
        DART 응답에서 주식수 데이터 추출

        Args:
            stock_data: DART API 응답 리스트
            company_id: 회사 ID (UUID)
            fiscal_year: 사업연도
            report_code: 보고서 코드

        Returns:
            stock_info 레코드 또는 None
        """
        common_shares = 0
        preferred_shares = 0
        treasury_common = 0
        treasury_preferred = 0

        for item in stock_data:
            stock_knd = item.get("se", "")  # 주식 종류

            if "보통주" in stock_knd:
                # 발행주식총수
                issued = self.parse_dart_number(item.get("istc_totqy"))
                if issued:
                    common_shares = issued

                # 자기주식수
                treasury = self.parse_dart_number(item.get("tesstk_co"))
                if treasury:
                    treasury_common = treasury

            elif "우선주" in stock_knd:
                issued = self.parse_dart_number(item.get("istc_totqy"))
                if issued:
                    preferred_shares = issued

                treasury = self.parse_dart_number(item.get("tesstk_co"))
                if treasury:
                    treasury_preferred = treasury

        total_shares = common_shares + preferred_shares
        treasury_shares = treasury_common + treasury_preferred
        outstanding_shares = total_shares - treasury_shares

        if total_shares == 0:
            return None

        return {
            "company_id": company_id,
            "fiscal_year": fiscal_year,
            "report_code": report_code,
            "common_shares": common_shares or None,
            "preferred_shares": preferred_shares or None,
            "total_shares": total_shares or None,
            "treasury_shares": treasury_shares or None,
            "outstanding_shares": outstanding_shares or None,
            "data_source": "DART",
        }

    async def get_companies_to_collect(
        self,
        session: AsyncSession,
        sample: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """수집 대상 기업 목록 조회"""
        query = (
            select(Company.id, Company.corp_code, Company.name, Company.ticker)
            .where(Company.corp_code.isnot(None))
            .where(Company.listing_status == 'LISTED')
            .where(Company.company_type.in_(['NORMAL', 'SPAC', 'REIT']))
            .order_by(Company.name)
        )

        if sample:
            query = query.limit(sample)

        result = await session.execute(query)
        return [
            {
                "id": str(row.id),
                "corp_code": row.corp_code,
                "name": row.name,
                "ticker": row.ticker,
            }
            for row in result.fetchall()
        ]

    async def collect_and_save(
        self,
        fiscal_year: int,
        report_code: str = "11011",
        sample: Optional[int] = None,
        dry_run: bool = False,
        update_companies: bool = True
    ) -> Dict[str, int]:
        """
        발행주식수 데이터 수집 및 저장

        Args:
            fiscal_year: 사업연도
            report_code: 보고서 코드
            sample: 샘플 수 (None이면 전체)
            dry_run: True면 저장하지 않음
            update_companies: True면 companies 테이블도 업데이트

        Returns:
            수집 통계
        """
        stats = {
            "total_companies": 0,
            "api_success": 0,
            "api_no_data": 0,
            "api_error": 0,
            "saved_count": 0,
            "companies_updated": 0,
        }

        async with self.async_session() as session:
            # 대상 기업 조회
            companies = await self.get_companies_to_collect(session, sample)
            stats["total_companies"] = len(companies)
            logger.info(f"수집 대상: {len(companies)}개 기업")

            for i, company in enumerate(companies, 1):
                corp_code = company["corp_code"]
                company_id = company["id"]
                company_name = company["name"]

                if i % 100 == 0:
                    logger.info(f"진행 중... {i}/{len(companies)}")

                # DART API 호출 (Rate limit 고려: 1초당 5회 제한)
                await asyncio.sleep(0.25)

                stock_data = await self.fetch_stock_totqy_status(
                    corp_code, fiscal_year, report_code
                )

                if stock_data is None:
                    stats["api_no_data"] += 1
                    continue

                if not stock_data:
                    stats["api_error"] += 1
                    continue

                stats["api_success"] += 1

                # 데이터 추출
                record = self.extract_shares_data(
                    stock_data, company_id, fiscal_year, report_code
                )

                if not record:
                    continue

                if dry_run:
                    if i <= 3:  # 샘플 출력
                        logger.info(f"[DRY-RUN] {company_name}: {record}")
                    continue

                # stock_info 테이블 저장 (UPSERT)
                try:
                    stmt = text("""
                        INSERT INTO stock_info
                        (company_id, fiscal_year, report_code, common_shares,
                         preferred_shares, total_shares, treasury_shares,
                         outstanding_shares, data_source)
                        VALUES (:company_id, :fiscal_year, :report_code, :common_shares,
                                :preferred_shares, :total_shares, :treasury_shares,
                                :outstanding_shares, :data_source)
                        ON CONFLICT (company_id, fiscal_year)
                        DO UPDATE SET
                            report_code = EXCLUDED.report_code,
                            common_shares = EXCLUDED.common_shares,
                            preferred_shares = EXCLUDED.preferred_shares,
                            total_shares = EXCLUDED.total_shares,
                            treasury_shares = EXCLUDED.treasury_shares,
                            outstanding_shares = EXCLUDED.outstanding_shares,
                            updated_at = NOW()
                    """)
                    await session.execute(stmt, record)
                    stats["saved_count"] += 1

                    # companies 테이블 업데이트
                    if update_companies and record["outstanding_shares"]:
                        update_stmt = text("""
                            UPDATE companies
                            SET shares_outstanding = :shares,
                                shares_updated_at = NOW()
                            WHERE id = :company_id
                        """)
                        await session.execute(update_stmt, {
                            "company_id": company_id,
                            "shares": record["outstanding_shares"]
                        })
                        stats["companies_updated"] += 1

                except Exception as e:
                    logger.error(f"저장 실패 ({company_name}): {e}")

            if not dry_run:
                await session.commit()

        return stats


async def main():
    parser = argparse.ArgumentParser(description="DART 발행주식수 수집")
    parser.add_argument(
        "--year",
        type=int,
        default=datetime.now().year - 1,
        help="사업연도 (기본값: 전년도)"
    )
    parser.add_argument(
        "--report-code",
        type=str,
        default="11011",
        choices=["11011", "11012", "11013", "11014"],
        help="보고서 코드 (기본값: 11011 사업보고서)"
    )
    parser.add_argument(
        "--sample",
        type=int,
        help="샘플 수 (테스트용)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="저장하지 않고 결과만 출력"
    )
    parser.add_argument(
        "--no-update-companies",
        action="store_true",
        help="companies 테이블 업데이트 안 함"
    )
    args = parser.parse_args()

    # 환경 변수
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        logger.error("DATABASE_URL 환경 변수가 설정되지 않았습니다")
        sys.exit(1)

    dart_api_key = os.environ.get("DART_API_KEY")
    if not dart_api_key:
        logger.error("DART_API_KEY 환경 변수가 설정되지 않았습니다")
        sys.exit(1)

    # asyncpg 드라이버
    if db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)

    logger.info("=== DART 발행주식수 수집 시작 ===")
    logger.info(f"사업연도: {args.year}")
    logger.info(f"보고서: {DARTSharesCollector.REPORT_CODES.get(args.report_code, args.report_code)}")
    logger.info(f"샘플: {args.sample or '전체'}")
    logger.info(f"Dry-run: {args.dry_run}")

    collector = DARTSharesCollector(db_url, dart_api_key)

    try:
        stats = await collector.collect_and_save(
            fiscal_year=args.year,
            report_code=args.report_code,
            sample=args.sample,
            dry_run=args.dry_run,
            update_companies=not args.no_update_companies
        )

        logger.info("=== 수집 결과 ===")
        logger.info(f"대상 기업: {stats['total_companies']}개")
        logger.info(f"API 성공: {stats['api_success']}개")
        logger.info(f"데이터 없음: {stats['api_no_data']}개")
        logger.info(f"API 오류: {stats['api_error']}개")
        logger.info(f"저장 완료: {stats['saved_count']}건")
        logger.info(f"companies 업데이트: {stats['companies_updated']}건")

    finally:
        await collector.close()


if __name__ == "__main__":
    asyncio.run(main())
