#!/usr/bin/env python3
"""
임원-회사 매칭 상황 분석
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select, func
from app.database import AsyncSessionLocal
from app.models.officers import Officer
from app.models.companies import Company


async def analyze():
    """임원-회사 매칭 상태 분석"""

    async with AsyncSessionLocal() as db:
        # 1. 총 임원 수
        result = await db.execute(select(func.count()).select_from(Officer))
        total_officers = result.scalar()

        # 2. current_company_id가 있는 임원 수
        result = await db.execute(
            select(func.count()).select_from(Officer).where(Officer.current_company_id.isnot(None))
        )
        officers_with_company = result.scalar()

        # 3. 총 회사 수
        result = await db.execute(select(func.count()).select_from(Company))
        total_companies = result.scalar()

        # 4. ticker가 있는 회사 수
        result = await db.execute(
            select(func.count()).select_from(Company).where(Company.ticker.isnot(None))
        )
        companies_with_ticker = result.scalar()

        # 5. 샘플 회사 ticker 확인
        result = await db.execute(
            select(Company.ticker, Company.name).where(Company.ticker.isnot(None)).limit(5)
        )
        sample_companies = result.all()

        # 6. 샘플 임원 확인
        result = await db.execute(
            select(Officer.name, Officer.position, Officer.current_company_id, Officer.properties)
            .limit(5)
        )
        sample_officers = result.all()

        print("=" * 60)
        print("임원-회사 매칭 상태 분석")
        print("=" * 60)
        print(f"총 임원 수: {total_officers:,}명")
        print(f"company_id가 있는 임원: {officers_with_company:,}명 ({officers_with_company/total_officers*100:.1f}%)")
        print()
        print(f"총 회사 수: {total_companies:,}개")
        print(f"ticker가 있는 회사: {companies_with_ticker:,}개 ({companies_with_ticker/total_companies*100:.1f}%)")
        print()

        print("회사 ticker 샘플:")
        for ticker, name in sample_companies:
            print(f"  {ticker}: {name}")
        print()

        print("임원 샘플:")
        for name, position, company_id, properties in sample_officers:
            print(f"  {name} ({position})")
            print(f"    company_id: {company_id}")
            print(f"    properties: {properties}")
        print()

        # 7. 회사별 임원 수 (company_id가 있는 경우)
        if officers_with_company > 0:
            result = await db.execute(
                select(
                    Company.name,
                    func.count(Officer.id).label('officer_count')
                )
                .join(Officer, Company.id == Officer.current_company_id)
                .group_by(Company.name)
                .order_by(func.count(Officer.id).desc())
                .limit(10)
            )
            top_companies = result.all()

            print("임원이 많은 회사 TOP 10:")
            for company_name, count in top_companies:
                print(f"  {company_name}: {count}명")

        print("=" * 60)


if __name__ == "__main__":
    asyncio.run(analyze())
