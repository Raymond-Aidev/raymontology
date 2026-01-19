#!/usr/bin/env python3
"""
임원-회사 매칭 검증 스크립트

PostgreSQL의 officer_positions 데이터가 실제 DART 공시와 일치하는지 검증합니다.
동명이인 문제로 인한 잘못된 매칭을 찾아 수정합니다.

작동 방식:
1. 2개 이상 회사에 근무한 임원 조회
2. 각 회사의 원본 공시 XML에서 해당 임원 이름+생년월일 검색
3. 공시에 없으면 잘못된 데이터로 표시
4. --fix 옵션으로 잘못된 데이터 삭제

사용법:
    # 검증만 (삭제 없음)
    python scripts/verify_officer_company_match.py

    # 잘못된 데이터 삭제
    python scripts/verify_officer_company_match.py --fix

    # 특정 임원만 검증
    python scripts/verify_officer_company_match.py --officer-name "강근욱"
"""

import asyncio
import argparse
import logging
import os
import sys
import zipfile
import tempfile
import re
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from datetime import datetime
import json

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import AsyncSessionLocal
from app.config import settings

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# DART 공시 파일 경로
DART_DATA_PATH = Path("/Users/jaejoonpark/raymontology/backend/data/dart")


class OfficerCompanyVerifier:
    """임원-회사 매칭 검증기"""

    def __init__(self, fix_mode: bool = False, officer_name: str = None):
        self.fix_mode = fix_mode
        self.officer_name = officer_name
        self.stats = {
            "total_checked": 0,
            "verified_correct": 0,
            "verified_wrong": 0,
            "unable_to_verify": 0,
            "deleted_positions": 0,
            "deleted_neo4j_rels": 0,
        }
        self.wrong_matches = []

    async def get_multi_company_officers(self, db: AsyncSession) -> List[Dict]:
        """2개 이상 회사에 근무하는 임원 조회"""
        where_clause = ""
        if self.officer_name:
            where_clause = f"AND o.name = '{self.officer_name}'"

        query = text(f"""
            WITH officer_companies AS (
                SELECT
                    o.id as officer_id,
                    o.name,
                    o.birth_date,
                    c.id as company_id,
                    c.corp_code,
                    c.name as company_name,
                    op.id as position_id,
                    op.position,
                    op.is_current,
                    op.term_end_date
                FROM officers o
                JOIN officer_positions op ON o.id = op.officer_id
                JOIN companies c ON op.company_id = c.id
                WHERE o.birth_date IS NOT NULL
                    AND c.corp_code IS NOT NULL
                    {where_clause}
            ),
            multi_company AS (
                SELECT
                    officer_id,
                    name,
                    birth_date,
                    COUNT(DISTINCT company_id) as company_count
                FROM officer_companies
                GROUP BY officer_id, name, birth_date
                HAVING COUNT(DISTINCT company_id) >= 2
            )
            SELECT
                oc.*,
                mc.company_count
            FROM officer_companies oc
            JOIN multi_company mc ON oc.officer_id = mc.officer_id
            ORDER BY mc.company_count DESC, oc.name, oc.company_name
        """)

        result = await db.execute(query)
        rows = result.fetchall()

        # 그룹화
        officers = {}
        for row in rows:
            officer_id = row.officer_id
            if officer_id not in officers:
                officers[officer_id] = {
                    "officer_id": officer_id,
                    "name": row.name,
                    "birth_date": row.birth_date,
                    "company_count": row.company_count,
                    "companies": []
                }
            officers[officer_id]["companies"].append({
                "company_id": row.company_id,
                "corp_code": row.corp_code,
                "company_name": row.company_name,
                "position_id": row.position_id,
                "position": row.position,
                "is_current": row.is_current,
                "term_end_date": row.term_end_date,
            })

        return list(officers.values())

    def find_disclosure_file(self, corp_code: str, year: str = None) -> Optional[Path]:
        """회사의 가장 최근 사업보고서 ZIP 파일 찾기"""
        # batch_* 디렉토리 순회
        for batch_dir in DART_DATA_PATH.glob("batch_*"):
            corp_dir = batch_dir / corp_code
            if not corp_dir.exists():
                continue

            # 가장 최근 연도부터 검색 (또는 특정 연도)
            years = [corp_dir / year] if year else sorted(corp_dir.glob("*"), reverse=True)
            for year_dir in years:
                if not year_dir.is_dir():
                    continue

                # 사업보고서 메타 파일 찾기
                for meta_file in year_dir.glob("*_meta.json"):
                    try:
                        with open(meta_file, 'r') as f:
                            meta = json.load(f)
                            if "사업보고서" in meta.get("report_nm", ""):
                                zip_file = meta_file.parent / f"{meta['rcept_no']}.zip"
                                if zip_file.exists():
                                    return zip_file
                    except:
                        continue

        return None

    def search_officer_in_disclosure(self, zip_path: Path, officer_name: str, birth_date: str) -> bool:
        """공시 파일에서 임원 검색"""
        try:
            with tempfile.TemporaryDirectory() as tmp_dir:
                with zipfile.ZipFile(zip_path, 'r') as zf:
                    zf.extractall(tmp_dir)

                # XML 파일들 검색
                for xml_file in Path(tmp_dir).glob("*.xml"):
                    try:
                        # EUC-KR 인코딩으로 읽기
                        with open(xml_file, 'rb') as f:
                            content = f.read()

                        # EUC-KR → UTF-8 변환
                        try:
                            text = content.decode('euc-kr')
                        except:
                            try:
                                text = content.decode('utf-8')
                            except:
                                continue

                        # 이름 검색
                        if officer_name not in text:
                            continue

                        # 이름+생년월일 검색 (임원 현황 테이블에서)
                        # SH5_BIH 필드에 생년월일이 있음 (YYYYMM 형식)
                        # 패턴: 이름과 생년월일이 근처에 있는지 확인

                        # 생년월일 패턴 (YYYYMM 또는 YYYY년 MM월)
                        birth_year = birth_date[:4]
                        birth_month = birth_date[4:6] if len(birth_date) >= 6 else ""

                        # 여러 패턴으로 검색
                        patterns = [
                            f'AUNITVALUE="{birth_date}"',  # SH5_BIH 속성
                            f'{birth_year}년 {int(birth_month):02d}월' if birth_month else f'{birth_year}년',
                            f'{birth_year}.{birth_month}' if birth_month else birth_year,
                        ]

                        # 이름 주변에서 생년월일 확인
                        name_idx = text.find(officer_name)
                        while name_idx != -1:
                            # 이름 전후 2000자 범위 검색
                            context = text[max(0, name_idx-1000):name_idx+1000]

                            for pattern in patterns:
                                if pattern in context:
                                    return True

                            name_idx = text.find(officer_name, name_idx + 1)

                    except Exception as e:
                        continue

        except Exception as e:
            logger.warning(f"파일 검색 실패: {zip_path} - {e}")

        return False

    async def delete_wrong_position(self, db: AsyncSession, position_id: str,
                                     officer_id: str, company_id: str, corp_code: str):
        """잘못된 position 삭제"""
        # PostgreSQL에서 삭제
        await db.execute(
            text("DELETE FROM officer_positions WHERE id = :id"),
            {"id": position_id}
        )
        self.stats["deleted_positions"] += 1

    async def delete_neo4j_relationship(self, officer_id: str, corp_code: str):
        """Neo4j에서 관계 삭제"""
        try:
            from neo4j import AsyncGraphDatabase

            driver = AsyncGraphDatabase.driver(
                settings.neo4j_uri,
                auth=(settings.neo4j_user, settings.neo4j_password)
            )

            async with driver.session() as session:
                result = await session.run("""
                    MATCH (o:Officer {id: $officer_id})-[r:WORKS_AT|WORKED_AT]->(c:Company {corp_code: $corp_code})
                    DELETE r
                    RETURN count(r) as deleted
                """, {"officer_id": officer_id, "corp_code": corp_code})

                record = await result.single()
                if record and record["deleted"] > 0:
                    self.stats["deleted_neo4j_rels"] += record["deleted"]

            await driver.close()

        except Exception as e:
            logger.warning(f"Neo4j 관계 삭제 실패: {e}")

    async def verify_all(self, db: AsyncSession):
        """전체 검증 실행"""
        logger.info("임원-회사 매칭 검증 시작...")

        # 다중 회사 임원 조회
        officers = await self.get_multi_company_officers(db)
        logger.info(f"검증 대상: {len(officers)}명 (2개 이상 회사에 근무)")

        for officer in officers:
            officer_name = officer["name"]
            birth_date = officer["birth_date"]

            logger.info(f"\n검증 중: {officer_name} ({birth_date}) - {officer['company_count']}개 회사")

            for company in officer["companies"]:
                self.stats["total_checked"] += 1
                corp_code = company["corp_code"]
                company_name = company["company_name"]

                # 공시 파일 찾기
                zip_path = self.find_disclosure_file(corp_code)

                if not zip_path:
                    logger.warning(f"  - {company_name}: 공시 파일 없음 (검증 불가)")
                    self.stats["unable_to_verify"] += 1
                    continue

                # 공시에서 임원 검색
                found = self.search_officer_in_disclosure(zip_path, officer_name, birth_date)

                if found:
                    logger.info(f"  ✓ {company_name}: 공시에서 확인됨")
                    self.stats["verified_correct"] += 1
                else:
                    logger.warning(f"  ✗ {company_name}: 공시에 없음 (잘못된 데이터)")
                    self.stats["verified_wrong"] += 1

                    self.wrong_matches.append({
                        "officer_id": officer["officer_id"],
                        "officer_name": officer_name,
                        "birth_date": birth_date,
                        "company_id": company["company_id"],
                        "corp_code": corp_code,
                        "company_name": company_name,
                        "position_id": company["position_id"],
                    })

                    # fix 모드면 삭제
                    if self.fix_mode:
                        await self.delete_wrong_position(
                            db,
                            company["position_id"],
                            officer["officer_id"],
                            company["company_id"],
                            corp_code
                        )
                        await self.delete_neo4j_relationship(
                            officer["officer_id"],
                            corp_code
                        )
                        logger.info(f"    → 삭제 완료")

        if self.fix_mode:
            await db.commit()

    def print_summary(self):
        """검증 결과 요약 출력"""
        print("\n" + "=" * 60)
        print(" 임원-회사 매칭 검증 결과")
        print("=" * 60)
        print(f"  총 검증 건수:           {self.stats['total_checked']:,}건")
        print(f"  정상 확인:              {self.stats['verified_correct']:,}건")
        print(f"  잘못된 데이터:          {self.stats['verified_wrong']:,}건")
        print(f"  검증 불가 (공시 없음):  {self.stats['unable_to_verify']:,}건")

        if self.fix_mode:
            print(f"\n  [삭제 결과]")
            print(f"  PostgreSQL 삭제:        {self.stats['deleted_positions']:,}건")
            print(f"  Neo4j 관계 삭제:        {self.stats['deleted_neo4j_rels']:,}건")

        print("=" * 60)

        if self.wrong_matches and not self.fix_mode:
            print("\n잘못된 데이터 목록:")
            for match in self.wrong_matches[:20]:  # 상위 20개만
                print(f"  - {match['officer_name']} ({match['birth_date']}) → {match['company_name']}")
            if len(self.wrong_matches) > 20:
                print(f"  ... 외 {len(self.wrong_matches) - 20}건")
            print("\n--fix 옵션으로 삭제할 수 있습니다.")


async def main():
    parser = argparse.ArgumentParser(description="임원-회사 매칭 검증")
    parser.add_argument("--fix", action="store_true", help="잘못된 데이터 삭제")
    parser.add_argument("--officer-name", type=str, help="특정 임원만 검증")
    parser.add_argument("--limit", type=int, default=50, help="검증할 최대 임원 수")
    args = parser.parse_args()

    verifier = OfficerCompanyVerifier(
        fix_mode=args.fix,
        officer_name=args.officer_name
    )

    async with AsyncSessionLocal() as db:
        await verifier.verify_all(db)

    verifier.print_summary()


if __name__ == "__main__":
    asyncio.run(main())
