#!/usr/bin/env python3
"""
중복 CB(전환사채) 데이터 정리 스크립트

문제: 같은 회사의 같은 회차 CB가 여러 공시에서 파싱되어 중복 생성됨
해결: (company_id, bond_name) 기준으로 중복 제거, 최신 공시 데이터 유지

PostgreSQL 데이터 정리 후 Neo4j 재동기화 필요
"""
import asyncio
import asyncpg
import logging
from collections import defaultdict

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DB_URL = "postgresql://postgres:dev_password@localhost:5432/raymontology_dev"


async def main():
    logger.info("CB 중복 데이터 정리 시작...")

    conn = await asyncpg.connect(DB_URL)

    try:
        # 1. 중복 CB 그룹 찾기
        logger.info("[1/5] 중복 CB 그룹 검색...")
        duplicates = await conn.fetch("""
            SELECT company_id, bond_name,
                   array_agg(id ORDER BY source_disclosure_id DESC) as cb_ids,
                   array_agg(source_disclosure_id ORDER BY source_disclosure_id DESC) as disclosure_ids,
                   COUNT(*) as cnt
            FROM convertible_bonds
            WHERE bond_name IS NOT NULL AND bond_name != ''
            GROUP BY company_id, bond_name
            HAVING COUNT(*) > 1
            ORDER BY COUNT(*) DESC
        """)

        logger.info(f"  중복 그룹: {len(duplicates)}개")

        if not duplicates:
            logger.info("중복 CB 없음. 완료.")
            return

        # 2. 각 중복 그룹에서 하나만 남기고 나머지 삭제
        logger.info("[2/5] 중복 CB 정리 시작...")

        total_deleted_cb = 0
        total_deleted_subscribers = 0

        for dup in duplicates:
            company_id = dup['company_id']
            bond_name = dup['bond_name']
            cb_ids = dup['cb_ids']  # 최신 공시 순으로 정렬됨

            # 첫 번째(최신 공시)를 유지, 나머지 삭제
            keep_id = cb_ids[0]
            delete_ids = cb_ids[1:]

            if not delete_ids:
                continue

            # 삭제할 CB의 subscriber를 유지할 CB로 이전 (중복 아닌 것만)
            for del_id in delete_ids:
                # 해당 CB의 subscriber를 keep_id로 이전
                # 이미 같은 subscriber가 keep_id에 있으면 스킵
                await conn.execute("""
                    UPDATE cb_subscribers
                    SET cb_id = $1
                    WHERE cb_id = $2
                    AND subscriber_name NOT IN (
                        SELECT subscriber_name FROM cb_subscribers WHERE cb_id = $1
                    )
                """, keep_id, del_id)

                # 중복되는 subscriber 삭제
                deleted_subs = await conn.execute("""
                    DELETE FROM cb_subscribers WHERE cb_id = $1
                """, del_id)
                total_deleted_subscribers += int(deleted_subs.split()[-1])

                # CB 삭제
                await conn.execute("""
                    DELETE FROM convertible_bonds WHERE id = $1
                """, del_id)
                total_deleted_cb += 1

        logger.info(f"  삭제된 CB: {total_deleted_cb}건")
        logger.info(f"  삭제된 CB Subscriber: {total_deleted_subscribers}건")

        # 3. 결과 확인
        logger.info("[3/5] 정리 결과 확인...")

        remaining_dups = await conn.fetchval("""
            SELECT COUNT(*) FROM (
                SELECT company_id, bond_name
                FROM convertible_bonds
                WHERE bond_name IS NOT NULL AND bond_name != ''
                GROUP BY company_id, bond_name
                HAVING COUNT(*) > 1
            ) t
        """)
        logger.info(f"  남은 중복: {remaining_dups}개")

        # 4. 전체 통계
        logger.info("[4/5] 최종 통계...")

        cb_count = await conn.fetchval("SELECT COUNT(*) FROM convertible_bonds")
        sub_count = await conn.fetchval("SELECT COUNT(*) FROM cb_subscribers")

        logger.info(f"  총 CB: {cb_count}건")
        logger.info(f"  총 CB Subscriber: {sub_count}건")

        # 5. 나노캠텍 검증
        logger.info("[5/5] 나노캠텍 검증...")

        nano_cbs = await conn.fetch("""
            SELECT cb.bond_name, cb.issue_date, cb.source_disclosure_id
            FROM convertible_bonds cb
            JOIN companies c ON cb.company_id = c.id
            WHERE c.corp_code = '00542074'
            ORDER BY cb.bond_name
        """)

        logger.info(f"  나노캠텍 CB: {len(nano_cbs)}개")
        for cb in nano_cbs:
            logger.info(f"    - {cb['bond_name']} ({cb['issue_date']})")

    finally:
        await conn.close()

    logger.info("CB 중복 정리 완료!")
    logger.info("다음 단계: Neo4j 재동기화 필요 (scripts/sync_cb_to_neo4j.py)")


if __name__ == "__main__":
    asyncio.run(main())
