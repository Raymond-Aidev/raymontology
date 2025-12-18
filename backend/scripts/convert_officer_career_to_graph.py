#!/usr/bin/env python3
"""
임원 경력 이력 → Neo4j 그래프 관계 변환

현재 상태:
- Officer.current_company_id → WORKS_AT 관계로 저장됨
- Officer.career_history 필드는 비어있음 (향후 수집 필요)

이 스크립트의 목적:
1. 기존 WORKS_AT 관계에 is_current=True 속성 추가
2. 각 임원의 과거 경력을 파악하여 WORKED_AT 관계 생성 (데이터 수집 후)
3. career_count, influence_score 계산 및 업데이트
4. 임원 노드 색상 강도를 위한 career_count 속성 설정

향후 확장:
- 사업보고서에서 과거 임원 정보 수집
- properties.career → WORKED_AT 관계로 변환
"""
import asyncio
import logging
import sys
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent.parent))

from neo4j import AsyncGraphDatabase
from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.models.officers import Officer
from app.models.companies import Company
from app.config import settings

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class OfficerCareerGraphConverter:
    """임원 경력 이력 → 그래프 관계 변환기"""

    def __init__(self):
        self.driver = None
        self.stats = {
            "officers_processed": 0,
            "works_at_updated": 0,
            "worked_at_created": 0,
            "career_counts_updated": 0,
            "errors": 0,
        }

    async def __aenter__(self):
        self.driver = AsyncGraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password)
        )
        await self.driver.verify_connectivity()
        logger.info(f"✓ Neo4j 연결 성공: {settings.neo4j_uri}")
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.driver:
            await self.driver.close()

    async def step1_add_is_current_to_works_at(self):
        """기존 WORKS_AT 관계에 is_current=True 속성 추가"""
        logger.info("=" * 60)
        logger.info("Step 1: 기존 WORKS_AT 관계에 is_current 속성 추가")
        logger.info("=" * 60)

        async with self.driver.session() as session:
            # 기존 WORKS_AT 관계 확인
            result = await session.run("""
                MATCH ()-[r:WORKS_AT]->()
                RETURN COUNT(r) as count
            """)
            existing_count = (await result.single())["count"]
            logger.info(f"기존 WORKS_AT 관계: {existing_count:,}개")

            # is_current 속성 추가 (모두 현재 직장)
            result = await session.run("""
                MATCH (o:Officer)-[r:WORKS_AT]->(c:Company)
                SET r.is_current = true
                RETURN COUNT(r) as updated_count
            """)
            updated_count = (await result.single())["updated_count"]
            self.stats["works_at_updated"] = updated_count
            logger.info(f"✓ is_current=true 속성 추가: {updated_count:,}개")

    async def step2_create_index_for_worked_at(self):
        """WORKED_AT 관계를 위한 인덱스 생성"""
        logger.info("")
        logger.info("=" * 60)
        logger.info("Step 2: WORKED_AT 관계용 인덱스 생성")
        logger.info("=" * 60)

        async with self.driver.session() as session:
            # Officer의 career_count 인덱스
            try:
                await session.run("""
                    CREATE INDEX officer_career_count IF NOT EXISTS
                    FOR (o:Officer) ON (o.career_count)
                """)
                logger.info("✓ Officer.career_count 인덱스 생성")
            except Exception as e:
                logger.warning(f"인덱스 생성 실패 (이미 존재할 수 있음): {e}")

            # Officer의 influence_score 인덱스 (이미 있을 수도)
            try:
                await session.run("""
                    CREATE INDEX officer_influence IF NOT EXISTS
                    FOR (o:Officer) ON (o.influence_score)
                """)
                logger.info("✓ Officer.influence_score 인덱스 생성")
            except Exception as e:
                logger.warning(f"인덱스 생성 실패 (이미 존재할 수 있음): {e}")

    async def step3_calculate_career_count_from_current_data(self):
        """
        현재 데이터 기반 career_count 계산

        현재는 각 임원당 1개 회사만 있으므로 career_count = 1
        향후 과거 경력 데이터 수집 후 재계산 필요
        """
        logger.info("")
        logger.info("=" * 60)
        logger.info("Step 3: career_count 계산 (현재 데이터 기반)")
        logger.info("=" * 60)

        async with self.driver.session() as session:
            # 각 임원의 WORKS_AT + WORKED_AT 관계 개수 계산
            result = await session.run("""
                MATCH (o:Officer)
                OPTIONAL MATCH (o)-[:WORKS_AT]->(current:Company)
                OPTIONAL MATCH (o)-[:WORKED_AT]->(past:Company)
                WITH o,
                     COUNT(DISTINCT current) + COUNT(DISTINCT past) as career_count
                SET o.career_count = career_count
                RETURN COUNT(o) as officer_count,
                       AVG(career_count) as avg_career_count,
                       MAX(career_count) as max_career_count
            """)
            stats = await result.single()

            self.stats["career_counts_updated"] = stats["officer_count"]
            logger.info(f"✓ 임원 career_count 업데이트: {stats['officer_count']:,}명")
            logger.info(f"  평균 경력: {stats['avg_career_count']:.2f}개 회사")
            logger.info(f"  최대 경력: {stats['max_career_count']}개 회사")

    async def step4_calculate_influence_score(self):
        """
        influence_score 계산

        계산 방식:
        - career_count: 경력 회사 수 (가중치 0.4)
        - board_member_count: 이사회 멤버 수 (가중치 0.3)
        - position_score: 직책별 점수 (가중치 0.3)
          * 대표이사: 1.0
          * 사장/부사장: 0.8
          * 전무/상무: 0.6
          * 이사: 0.4
          * 기타: 0.2

        최종 점수: 0~1 사이로 정규화
        """
        logger.info("")
        logger.info("=" * 60)
        logger.info("Step 4: influence_score 계산")
        logger.info("=" * 60)

        async with self.driver.session() as session:
            # 직책별 점수 매핑
            result = await session.run("""
                MATCH (o:Officer)

                // Career count (최대 10개로 제한)
                WITH o, COALESCE(o.career_count, 1) as career_count

                // Board member count
                OPTIONAL MATCH (o)-[:BOARD_MEMBER_AT]->()
                WITH o, career_count, COUNT(*) as board_count

                // Position score
                WITH o, career_count, board_count,
                     CASE
                         WHEN o.position CONTAINS '대표이사' THEN 1.0
                         WHEN o.position CONTAINS '사장' OR o.position CONTAINS '부사장' THEN 0.8
                         WHEN o.position CONTAINS '전무' OR o.position CONTAINS '상무' THEN 0.6
                         WHEN o.position CONTAINS '이사' THEN 0.4
                         ELSE 0.2
                     END as position_score

                // Influence score 계산 (0~1 범위)
                WITH o,
                     career_count,
                     board_count,
                     position_score,
                     (
                         (CASE WHEN career_count > 10 THEN 10 ELSE career_count END * 0.04) +  // 0~0.4
                         (CASE WHEN board_count > 5 THEN 5 ELSE board_count END * 0.06) +     // 0~0.3
                         (position_score * 0.3)                                                 // 0~0.3
                     ) as influence_score

                SET o.influence_score = influence_score

                RETURN COUNT(o) as updated_count,
                       AVG(influence_score) as avg_score,
                       MAX(influence_score) as max_score,
                       MIN(influence_score) as min_score
            """)

            stats = await result.single()
            logger.info(f"✓ influence_score 업데이트: {stats['updated_count']:,}명")
            logger.info(f"  평균 점수: {stats['avg_score']:.3f}")
            logger.info(f"  최대 점수: {stats['max_score']:.3f}")
            logger.info(f"  최소 점수: {stats['min_score']:.3f}")

    async def step5_analyze_results(self):
        """결과 분석 및 통계"""
        logger.info("")
        logger.info("=" * 60)
        logger.info("Step 5: 결과 분석")
        logger.info("=" * 60)

        async with self.driver.session() as session:
            # Career count 분포
            result = await session.run("""
                MATCH (o:Officer)
                WITH o.career_count as career_count, COUNT(o) as officer_count
                RETURN career_count, officer_count
                ORDER BY career_count DESC
                LIMIT 10
            """)

            logger.info("\nCareer count 분포 (TOP 10):")
            async for record in result:
                logger.info(f"  {record['career_count']}개 회사: {record['officer_count']:,}명")

            # Influence score 분포 (구간별)
            result = await session.run("""
                MATCH (o:Officer)
                WITH
                    CASE
                        WHEN o.influence_score >= 0.8 THEN 'Very High (0.8-1.0)'
                        WHEN o.influence_score >= 0.6 THEN 'High (0.6-0.8)'
                        WHEN o.influence_score >= 0.4 THEN 'Medium (0.4-0.6)'
                        WHEN o.influence_score >= 0.2 THEN 'Low (0.2-0.4)'
                        ELSE 'Very Low (0-0.2)'
                    END as score_range,
                    COUNT(o) as count
                RETURN score_range, count
                ORDER BY score_range
            """)

            logger.info("\nInfluence score 분포:")
            async for record in result:
                logger.info(f"  {record['score_range']}: {record['count']:,}명")

            # 최고 영향력 임원 TOP 10
            result = await session.run("""
                MATCH (o:Officer)-[:WORKS_AT]->(c:Company)
                RETURN o.name as name,
                       o.position as position,
                       c.name as company,
                       o.career_count as career_count,
                       o.influence_score as influence_score
                ORDER BY o.influence_score DESC
                LIMIT 10
            """)

            logger.info("\n최고 영향력 임원 TOP 10:")
            rank = 1
            async for record in result:
                logger.info(
                    f"  {rank:2d}. {record['name']} ({record['position']}) - "
                    f"{record['company']} | "
                    f"경력: {record['career_count']}개 | "
                    f"영향력: {record['influence_score']:.3f}"
                )
                rank += 1

    async def step6_prepare_for_future_career_data(self):
        """향후 과거 경력 데이터 수집 준비"""
        logger.info("")
        logger.info("=" * 60)
        logger.info("Step 6: 향후 경력 데이터 수집 준비 사항")
        logger.info("=" * 60)

        logger.info("\n향후 작업:")
        logger.info("  1. 과거 사업보고서에서 임원 정보 수집 (2019~2024)")
        logger.info("  2. 동일 인물 매칭 (이름 + 생년월일)")
        logger.info("  3. WORKED_AT 관계 생성:")
        logger.info("     (Officer)-[:WORKED_AT {")
        logger.info("       start_date: '2020-01',")
        logger.info("       end_date: '2023-12',")
        logger.info("       position: '사장',")
        logger.info("       is_current: false")
        logger.info("     }]->(Company)")
        logger.info("  4. career_count 재계산")
        logger.info("  5. influence_score 재계산")

        logger.info("\n현재 상태:")
        logger.info("  - 모든 임원의 career_count = 1 (현재 회사만)")
        logger.info("  - 과거 경력 데이터 수집 후 재실행 필요")

    async def run(self):
        """전체 변환 프로세스 실행"""
        logger.info("=" * 60)
        logger.info("임원 경력 이력 → 그래프 관계 변환 시작")
        logger.info("=" * 60)
        logger.info("")

        try:
            await self.step1_add_is_current_to_works_at()
            await self.step2_create_index_for_worked_at()
            await self.step3_calculate_career_count_from_current_data()
            await self.step4_calculate_influence_score()
            await self.step5_analyze_results()
            await self.step6_prepare_for_future_career_data()

            logger.info("")
            logger.info("=" * 60)
            logger.info("✓ 변환 완료!")
            logger.info("=" * 60)
            logger.info(f"WORKS_AT 관계 업데이트: {self.stats['works_at_updated']:,}개")
            logger.info(f"WORKED_AT 관계 생성: {self.stats['worked_at_created']:,}개")
            logger.info(f"career_count 업데이트: {self.stats['career_counts_updated']:,}명")
            logger.info(f"에러: {self.stats['errors']:,}개")
            logger.info("")

        except Exception as e:
            logger.error(f"변환 중 오류 발생: {e}", exc_info=True)
            raise


async def main():
    """메인 함수"""
    async with OfficerCareerGraphConverter() as converter:
        await converter.run()


if __name__ == "__main__":
    asyncio.run(main())
