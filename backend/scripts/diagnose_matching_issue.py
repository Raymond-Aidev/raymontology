#!/usr/bin/env python3
"""
임원-회사 매칭 실패 원인 진단
"""
import asyncio
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models.officers import Officer
from app.models.companies import Company


async def diagnose():
    """매칭 실패 원인 진단"""

    async with AsyncSessionLocal() as db:
        # 1. 임원 샘플에서 source_report 가져오기
        result = await db.execute(
            select(Officer.name, Officer.position, Officer.properties).limit(3)
        )
        officers = result.all()

        print("=" * 60)
        print("임원-회사 매칭 실패 원인 진단")
        print("=" * 60)

        for name, position, properties in officers:
            source_report = properties.get('source_report')
            if not source_report:
                continue

            print(f"\n임원: {name} ({position})")
            print(f"Source Report: {source_report}")

            # 해당 report의 메타데이터 찾기
            data_dir = Path("./data/dart")
            meta_files = list(data_dir.rglob(f"{source_report}*_meta.json"))

            if meta_files:
                meta_file = meta_files[0]
                print(f"Meta file: {meta_file.name}")

                with open(meta_file, 'r') as f:
                    meta_data = json.load(f)

                stock_code = meta_data.get("stock_code")
                corp_code = meta_data.get("corp_code")
                corp_name = meta_data.get("corp_name")

                print(f"  stock_code: {stock_code}")
                print(f"  corp_code: {corp_code}")
                print(f"  corp_name: {corp_name}")

                # ticker로 회사 찾기
                if stock_code:
                    result = await db.execute(
                        select(Company.id, Company.name, Company.ticker).where(Company.ticker == stock_code)
                    )
                    company = result.first()

                    if company:
                        print(f"  ✓ 회사 발견: {company.name} (ticker: {company.ticker})")
                    else:
                        print(f"  ✗ ticker={stock_code}로 회사 찾지 못함")

                        # ticker 샘플 확인
                        result = await db.execute(
                            select(Company.ticker, Company.name).limit(5)
                        )
                        sample_tickers = result.all()
                        print(f"  DB ticker 샘플: {[t[0] for t in sample_tickers]}")
                else:
                    print(f"  ✗ stock_code가 없음")
            else:
                print(f"  ✗ Meta file not found")

        print("\n" + "=" * 60)


if __name__ == "__main__":
    asyncio.run(diagnose())
