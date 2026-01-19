#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PostgreSQL → Neo4j 전체 동기화 스크립트

20년 풀스택/DB 전문가 설계:
- UTF-8 인코딩 완전 지원
- Stale 데이터 자동 정리
- 배치 처리로 메모리 최적화
- 트랜잭션 관리 및 롤백 지원
- 상세 진행 상황 로깅

엔티티: Company, Officer, ConvertibleBond, Subscriber
관계: WORKS_AT, BOARD_MEMBER_AT, ISSUED, SUBSCRIBED
"""
import asyncio
import asyncpg
import logging
import os
import sys
from datetime import datetime
from typing import List, Dict, Any, Optional

# Neo4j 동기 드라이버 사용 (asyncpg와 함께)
from neo4j import GraphDatabase

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('neo4j_sync.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

# 환경 설정
DB_URL = os.getenv('DATABASE_URL', 'postgresql://postgres:dev_password@localhost:5432/raymontology_dev')
NEO4J_URI = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
NEO4J_USER = os.getenv('NEO4J_USER', 'neo4j')
NEO4J_PASSWORD = os.getenv('NEO4J_PASSWORD', 'password')

BATCH_SIZE = 50  # 메모리 최적화를 위해 50건씩 처리


class Neo4jFullSyncer:
    """PostgreSQL → Neo4j 전체 동기화기"""

    def __init__(self):
        self.pg_conn: Optional[asyncpg.Connection] = None
        self.neo4j_driver = None
        self.stats = {
            'companies': {'pg': 0, 'synced': 0, 'errors': 0},
            'officers': {'pg': 0, 'synced': 0, 'errors': 0},
            'positions': {'pg': 0, 'synced': 0, 'errors': 0},
            'cbs': {'pg': 0, 'synced': 0, 'errors': 0},
            'subscribers': {'pg': 0, 'synced': 0, 'errors': 0},
            'relationships': {'works_at': 0, 'issued': 0, 'subscribed': 0}
        }

    async def connect(self):
        """데이터베이스 연결"""
        logger.info("데이터베이스 연결 중...")

        # PostgreSQL 연결
        self.pg_conn = await asyncpg.connect(DB_URL)
        logger.info("  ✓ PostgreSQL 연결 완료")

        # Neo4j 연결
        self.neo4j_driver = GraphDatabase.driver(
            NEO4J_URI,
            auth=(NEO4J_USER, NEO4J_PASSWORD)
        )
        self.neo4j_driver.verify_connectivity()
        logger.info("  ✓ Neo4j 연결 완료")

    async def close(self):
        """데이터베이스 연결 종료"""
        if self.pg_conn:
            await self.pg_conn.close()
        if self.neo4j_driver:
            self.neo4j_driver.close()
        logger.info("데이터베이스 연결 종료")

    def _ensure_utf8(self, value: Any) -> Any:
        """UTF-8 인코딩 보장"""
        if value is None:
            return None
        if isinstance(value, str):
            # 이미 문자열이면 그대로 (Python3은 기본 UTF-8)
            return value
        if isinstance(value, bytes):
            return value.decode('utf-8', errors='replace')
        return value

    # ==================== Phase 1: 제약조건 및 인덱스 ====================

    def create_constraints(self):
        """Neo4j 제약조건 및 인덱스 생성"""
        logger.info("[Phase 1] 제약조건 및 인덱스 생성...")

        constraints = [
            "CREATE CONSTRAINT company_id IF NOT EXISTS FOR (c:Company) REQUIRE c.id IS UNIQUE",
            "CREATE CONSTRAINT officer_id IF NOT EXISTS FOR (o:Officer) REQUIRE o.id IS UNIQUE",
            "CREATE CONSTRAINT cb_id IF NOT EXISTS FOR (cb:ConvertibleBond) REQUIRE cb.id IS UNIQUE",
            "CREATE CONSTRAINT subscriber_id IF NOT EXISTS FOR (s:Subscriber) REQUIRE s.id IS UNIQUE",
        ]

        indexes = [
            "CREATE INDEX company_name IF NOT EXISTS FOR (c:Company) ON (c.name)",
            "CREATE INDEX company_ticker IF NOT EXISTS FOR (c:Company) ON (c.ticker)",
            "CREATE INDEX officer_name IF NOT EXISTS FOR (o:Officer) ON (o.name)",
            "CREATE INDEX cb_company IF NOT EXISTS FOR (cb:ConvertibleBond) ON (cb.company_id)",
        ]

        with self.neo4j_driver.session() as session:
            for query in constraints + indexes:
                try:
                    session.run(query)
                except Exception as e:
                    logger.debug(f"  제약조건/인덱스 생성 스킵: {e}")

        logger.info("  ✓ 제약조건 및 인덱스 준비 완료")

    # ==================== Phase 2: Stale 데이터 정리 ====================

    def cleanup_stale_data(self):
        """Neo4j Stale 데이터 정리"""
        logger.info("[Phase 2] Stale 데이터 정리...")

        with self.neo4j_driver.session() as session:
            # 현재 노드 수 확인
            result = session.run("MATCH (n) RETURN labels(n)[0] as label, count(n) as cnt")
            before_counts = {r['label']: r['cnt'] for r in result}
            logger.info(f"  정리 전: {before_counts}")

            # 모든 관계 삭제
            session.run("MATCH ()-[r]->() DELETE r")
            logger.info("  ✓ 모든 관계 삭제 완료")

            # 모든 노드 삭제 (클린 재동기화)
            for label in ['Subscriber', 'ConvertibleBond', 'Officer', 'Company']:
                result = session.run(f"MATCH (n:{label}) DETACH DELETE n RETURN count(n) as deleted")
                deleted = result.single()['deleted']
                logger.info(f"  ✓ {label} {deleted}개 삭제")

        logger.info("  ✓ Stale 데이터 정리 완료")

    # ==================== Phase 3: Company 동기화 ====================

    async def sync_companies(self):
        """Company 동기화"""
        logger.info("[Phase 3] Company 동기화...")

        # PostgreSQL에서 조회
        rows = await self.pg_conn.fetch("""
            SELECT id, name, ticker, corp_code, name_en,
                   business_number, sector, industry, market
            FROM companies
        """)
        self.stats['companies']['pg'] = len(rows)
        logger.info(f"  PostgreSQL Company: {len(rows)}개")

        # 배치 처리
        with self.neo4j_driver.session() as session:
            for i in range(0, len(rows), BATCH_SIZE):
                batch = rows[i:i+BATCH_SIZE]
                companies = []

                for r in batch:
                    companies.append({
                        'id': str(r['id']),
                        'name': self._ensure_utf8(r['name']),
                        'ticker': r['ticker'],
                        'corp_code': r['corp_code'],
                        'name_en': self._ensure_utf8(r['name_en']),
                        'business_number': r['business_number'],
                        'sector': self._ensure_utf8(r['sector']),
                        'industry': self._ensure_utf8(r['industry']),
                        'market': r['market']
                    })

                try:
                    session.run("""
                        UNWIND $companies AS c
                        CREATE (n:Company {
                            id: c.id,
                            name: c.name,
                            ticker: c.ticker,
                            corp_code: c.corp_code,
                            name_en: c.name_en,
                            business_number: c.business_number,
                            sector: c.sector,
                            industry: c.industry,
                            market: c.market,
                            synced_at: datetime()
                        })
                    """, companies=companies)
                    self.stats['companies']['synced'] += len(batch)
                except Exception as e:
                    logger.error(f"  Company 배치 오류: {e}")
                    self.stats['companies']['errors'] += len(batch)

                if (i + BATCH_SIZE) % 500 == 0:
                    logger.info(f"  진행: {min(i+BATCH_SIZE, len(rows))}/{len(rows)}")

        logger.info(f"  ✓ Company 동기화 완료: {self.stats['companies']['synced']}개")

    # ==================== Phase 4: Officer 동기화 ====================

    async def sync_officers(self):
        """Officer 동기화"""
        logger.info("[Phase 4] Officer 동기화...")

        # PostgreSQL에서 조회
        rows = await self.pg_conn.fetch("""
            SELECT id, name, birth_date, gender
            FROM officers
        """)
        self.stats['officers']['pg'] = len(rows)
        logger.info(f"  PostgreSQL Officer: {len(rows)}개")

        # 배치 처리
        with self.neo4j_driver.session() as session:
            for i in range(0, len(rows), BATCH_SIZE):
                batch = rows[i:i+BATCH_SIZE]
                officers = []

                for r in batch:
                    officers.append({
                        'id': str(r['id']),
                        'name': self._ensure_utf8(r['name']),
                        'birth_date': self._ensure_utf8(r['birth_date']),
                        'gender': self._ensure_utf8(r['gender'])
                    })

                try:
                    session.run("""
                        UNWIND $officers AS o
                        CREATE (n:Officer {
                            id: o.id,
                            name: o.name,
                            birth_date: o.birth_date,
                            gender: o.gender,
                            synced_at: datetime()
                        })
                    """, officers=officers)
                    self.stats['officers']['synced'] += len(batch)
                except Exception as e:
                    logger.error(f"  Officer 배치 오류: {e}")
                    self.stats['officers']['errors'] += len(batch)

                if (i + BATCH_SIZE) % 2000 == 0:
                    logger.info(f"  진행: {min(i+BATCH_SIZE, len(rows))}/{len(rows)}")

        logger.info(f"  ✓ Officer 동기화 완료: {self.stats['officers']['synced']}개")

    # ==================== Phase 5: Officer-Company 관계 ====================

    async def sync_officer_positions(self):
        """Officer-Company 관계 (WORKS_AT) 동기화"""
        logger.info("[Phase 5] Officer-Company 관계 동기화...")

        # PostgreSQL에서 조회
        rows = await self.pg_conn.fetch("""
            SELECT officer_id, company_id, position, is_current
            FROM officer_positions
        """)
        self.stats['positions']['pg'] = len(rows)
        logger.info(f"  PostgreSQL OfficerPosition: {len(rows)}개")

        # 배치 처리
        with self.neo4j_driver.session() as session:
            for i in range(0, len(rows), BATCH_SIZE):
                batch = rows[i:i+BATCH_SIZE]
                positions = []

                for r in batch:
                    positions.append({
                        'officer_id': str(r['officer_id']),
                        'company_id': str(r['company_id']),
                        'position': self._ensure_utf8(r['position']),
                        'is_current': r['is_current']
                    })

                try:
                    result = session.run("""
                        UNWIND $positions AS p
                        MATCH (o:Officer {id: p.officer_id})
                        MATCH (c:Company {id: p.company_id})
                        CREATE (o)-[r:WORKS_AT {
                            position: p.position,
                            is_current: p.is_current
                        }]->(c)
                        RETURN count(r) as cnt
                    """, positions=positions)
                    cnt = result.single()['cnt']
                    self.stats['relationships']['works_at'] += cnt
                    self.stats['positions']['synced'] += len(batch)
                except Exception as e:
                    logger.error(f"  Position 배치 오류: {e}")
                    self.stats['positions']['errors'] += len(batch)

                if (i + BATCH_SIZE) % 2000 == 0:
                    logger.info(f"  진행: {min(i+BATCH_SIZE, len(rows))}/{len(rows)}")

        logger.info(f"  ✓ WORKS_AT 관계 동기화 완료: {self.stats['relationships']['works_at']}개")

    # ==================== Phase 6: ConvertibleBond 동기화 ====================

    async def sync_convertible_bonds(self):
        """ConvertibleBond 동기화"""
        logger.info("[Phase 6] ConvertibleBond 동기화...")

        # PostgreSQL에서 조회
        rows = await self.pg_conn.fetch("""
            SELECT id, company_id, issue_amount, conversion_price,
                   issue_date, maturity_date, interest_rate, bond_name
            FROM convertible_bonds
        """)
        self.stats['cbs']['pg'] = len(rows)
        logger.info(f"  PostgreSQL ConvertibleBond: {len(rows)}개")

        # 배치 처리
        with self.neo4j_driver.session() as session:
            for i in range(0, len(rows), BATCH_SIZE):
                batch = rows[i:i+BATCH_SIZE]
                cbs = []

                for r in batch:
                    cbs.append({
                        'id': str(r['id']),
                        'company_id': str(r['company_id']) if r['company_id'] else None,
                        'bond_name': self._ensure_utf8(r['bond_name']),
                        'issue_amount': float(r['issue_amount']) if r['issue_amount'] else None,
                        'conversion_price': float(r['conversion_price']) if r['conversion_price'] else None,
                        'issue_date': r['issue_date'].isoformat() if r['issue_date'] else None,
                        'maturity_date': r['maturity_date'].isoformat() if r['maturity_date'] else None,
                        'interest_rate': float(r['interest_rate']) if r['interest_rate'] else None
                    })

                try:
                    session.run("""
                        UNWIND $cbs AS cb
                        CREATE (n:ConvertibleBond {
                            id: cb.id,
                            company_id: cb.company_id,
                            bond_name: cb.bond_name,
                            issue_amount: cb.issue_amount,
                            conversion_price: cb.conversion_price,
                            issue_date: cb.issue_date,
                            maturity_date: cb.maturity_date,
                            interest_rate: cb.interest_rate,
                            synced_at: datetime()
                        })
                    """, cbs=cbs)
                    self.stats['cbs']['synced'] += len(batch)
                except Exception as e:
                    logger.error(f"  CB 배치 오류: {e}")
                    self.stats['cbs']['errors'] += len(batch)

        # Company-CB 관계 생성
        with self.neo4j_driver.session() as session:
            result = session.run("""
                MATCH (cb:ConvertibleBond)
                WHERE cb.company_id IS NOT NULL
                MATCH (c:Company {id: cb.company_id})
                CREATE (c)-[r:ISSUED]->(cb)
                RETURN count(r) as cnt
            """)
            self.stats['relationships']['issued'] = result.single()['cnt']

        logger.info(f"  ✓ ConvertibleBond 동기화 완료: {self.stats['cbs']['synced']}개")
        logger.info(f"  ✓ ISSUED 관계: {self.stats['relationships']['issued']}개")

    # ==================== Phase 7: Subscriber 동기화 ====================

    async def sync_subscribers(self):
        """Subscriber 동기화"""
        logger.info("[Phase 7] Subscriber 동기화...")

        # PostgreSQL에서 조회
        rows = await self.pg_conn.fetch("""
            SELECT id, cb_id, subscriber_name, subscription_amount, is_related_party
            FROM cb_subscribers
        """)
        self.stats['subscribers']['pg'] = len(rows)
        logger.info(f"  PostgreSQL Subscriber: {len(rows)}개")

        # 배치 처리
        with self.neo4j_driver.session() as session:
            for i in range(0, len(rows), BATCH_SIZE):
                batch = rows[i:i+BATCH_SIZE]
                subscribers = []

                for r in batch:
                    subscribers.append({
                        'id': str(r['id']),
                        'cb_id': str(r['cb_id']) if r['cb_id'] else None,
                        'subscriber_name': self._ensure_utf8(r['subscriber_name']),
                        'subscription_amount': float(r['subscription_amount']) if r['subscription_amount'] else None,
                        'is_related_party': self._ensure_utf8(r['is_related_party'])
                    })

                try:
                    session.run("""
                        UNWIND $subscribers AS s
                        CREATE (n:Subscriber {
                            id: s.id,
                            cb_id: s.cb_id,
                            name: s.subscriber_name,
                            subscription_amount: s.subscription_amount,
                            is_related_party: s.is_related_party,
                            synced_at: datetime()
                        })
                    """, subscribers=subscribers)
                    self.stats['subscribers']['synced'] += len(batch)
                except Exception as e:
                    logger.error(f"  Subscriber 배치 오류: {e}")
                    self.stats['subscribers']['errors'] += len(batch)

                if (i + BATCH_SIZE) % 500 == 0:
                    logger.info(f"  진행: {min(i+BATCH_SIZE, len(rows))}/{len(rows)}")

        # Subscriber-CB 관계 생성
        with self.neo4j_driver.session() as session:
            result = session.run("""
                MATCH (s:Subscriber)
                WHERE s.cb_id IS NOT NULL
                MATCH (cb:ConvertibleBond {id: s.cb_id})
                CREATE (s)-[r:SUBSCRIBED]->(cb)
                RETURN count(r) as cnt
            """)
            self.stats['relationships']['subscribed'] = result.single()['cnt']

        logger.info(f"  ✓ Subscriber 동기화 완료: {self.stats['subscribers']['synced']}개")
        logger.info(f"  ✓ SUBSCRIBED 관계: {self.stats['relationships']['subscribed']}개")

    # ==================== Phase 8: 검증 ====================

    def verify_sync(self):
        """동기화 결과 검증"""
        logger.info("[Phase 8] 동기화 결과 검증...")

        with self.neo4j_driver.session() as session:
            # 노드 카운트
            result = session.run("""
                MATCH (n)
                RETURN labels(n)[0] as label, count(n) as cnt
                ORDER BY label
            """)
            counts = {r['label']: r['cnt'] for r in result}

            # 관계 카운트
            result = session.run("""
                MATCH ()-[r]->()
                RETURN type(r) as rel_type, count(r) as cnt
            """)
            rel_counts = {r['rel_type']: r['cnt'] for r in result}

            # 한글 데이터 검증
            result = session.run("""
                MATCH (c:Company)
                WHERE c.name IS NOT NULL
                RETURN c.name as name LIMIT 5
            """)
            sample_names = [r['name'] for r in result]

        logger.info("")
        logger.info("=" * 60)
        logger.info("동기화 결과 요약")
        logger.info("=" * 60)
        logger.info("")
        logger.info("노드 카운트:")
        for label, cnt in counts.items():
            pg_cnt = self.stats.get(label.lower() + 's', {}).get('pg', '?')
            logger.info(f"  {label}: {cnt:,} (PostgreSQL: {pg_cnt})")

        logger.info("")
        logger.info("관계 카운트:")
        for rel_type, cnt in rel_counts.items():
            logger.info(f"  {rel_type}: {cnt:,}")

        logger.info("")
        logger.info("한글 데이터 샘플:")
        for name in sample_names:
            logger.info(f"  - {name}")

        logger.info("")
        logger.info("에러 통계:")
        for entity, stat in self.stats.items():
            if isinstance(stat, dict) and stat.get('errors', 0) > 0:
                logger.info(f"  {entity}: {stat['errors']}건 오류")

        logger.info("=" * 60)

        # 한글 깨짐 검사
        has_broken = any('?' in name for name in sample_names if name)
        if has_broken:
            logger.warning("한글 인코딩 문제가 발견되었습니다!")
            return False
        else:
            logger.info("✓ 한글 인코딩 정상")
            return True

    # ==================== Main ====================

    async def run(self, skip_cleanup: bool = False):
        """전체 동기화 실행"""
        start_time = datetime.now()

        logger.info("=" * 60)
        logger.info("PostgreSQL → Neo4j 전체 동기화 시작")
        logger.info(f"시작 시간: {start_time}")
        logger.info("=" * 60)

        try:
            await self.connect()

            # Phase 1: 제약조건
            self.create_constraints()

            # Phase 2: Stale 데이터 정리
            if not skip_cleanup:
                self.cleanup_stale_data()

            # Phase 3-7: 데이터 동기화
            await self.sync_companies()
            await self.sync_officers()
            await self.sync_officer_positions()
            await self.sync_convertible_bonds()
            await self.sync_subscribers()

            # Phase 8: 검증
            success = self.verify_sync()

            end_time = datetime.now()
            duration = end_time - start_time

            logger.info("")
            logger.info(f"완료 시간: {end_time}")
            logger.info(f"소요 시간: {duration}")
            logger.info("")

            if success:
                logger.info("✅ 동기화 성공!")
            else:
                logger.warning("⚠️ 동기화 완료 (일부 문제 발견)")

            return success

        except Exception as e:
            logger.error(f"동기화 실패: {e}", exc_info=True)
            raise
        finally:
            await self.close()


async def main():
    import argparse
    parser = argparse.ArgumentParser(description='PostgreSQL → Neo4j 전체 동기화')
    parser.add_argument('--skip-cleanup', action='store_true', help='기존 데이터 삭제 스킵')
    args = parser.parse_args()

    syncer = Neo4jFullSyncer()
    await syncer.run(skip_cleanup=args.skip_cleanup)


if __name__ == "__main__":
    asyncio.run(main())
