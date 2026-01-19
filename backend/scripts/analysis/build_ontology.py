#!/usr/bin/env python3
"""
온톨로지 객체 및 링크 생성

팔란티어 온톨로지 개념에 따라:
1. 모든 엔티티를 OntologyObject로 등록
2. 관계를 OntologyLink로 저장
3. 메타데이터와 출처 정보 포함
"""
import asyncio
import asyncpg
import logging
import sys
import os
import json
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
import uuid

sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# DB 설정
DB_URL = os.getenv('DATABASE_URL', 'postgresql://postgres:dev_password@localhost:5432/raymontology_dev')


class OntologyBuilder:
    """온톨로지 구축 클래스"""

    # 객체 타입 정의
    OBJECT_TYPES = {
        'COMPANY': 'Company',
        'OFFICER': 'Officer',
        'CB': 'ConvertibleBond',
        'CB_SUBSCRIBER': 'CBSubscriber',
        'AFFILIATE': 'Affiliate',
        'FINANCIAL': 'FinancialStatement',
        'RISK': 'RiskSignal'
    }

    # 링크 타입 정의
    LINK_TYPES = {
        'WORKS_AT': 'works_at',           # Officer → Company
        'ISSUED': 'issued',                # Company → CB
        'SUBSCRIBED': 'subscribed',        # CBSubscriber → CB
        'OWNS': 'owns',                    # Company → Affiliate
        'HAS_FINANCIAL': 'has_financial',  # Company → FinancialStatement
        'HAS_RISK': 'has_risk',            # Company → RiskSignal
        'RELATED_TO': 'related_to',        # CB → Officer (내부자 인수)
    }

    def __init__(self):
        self.stats = {
            'objects_created': 0,
            'links_created': 0,
            'objects_updated': 0,
            'links_updated': 0,
            'errors': 0
        }

    def _generate_object_id(self, prefix: str, source_id: str) -> str:
        """객체 ID 생성"""
        # UUID 기반의 고유 ID
        hash_input = f"{prefix}_{source_id}"
        short_hash = hashlib.md5(hash_input.encode()).hexdigest()[:12]
        return f"{prefix}_{short_hash}"

    def _generate_link_id(self, source_id: str, target_id: str, link_type: str) -> str:
        """링크 ID 생성"""
        hash_input = f"{source_id}_{target_id}_{link_type}"
        short_hash = hashlib.md5(hash_input.encode()).hexdigest()[:12]
        return f"LINK_{short_hash}"

    async def build_all(self, conn: asyncpg.Connection):
        """전체 온톨로지 구축"""
        logger.info("=" * 80)
        logger.info("온톨로지 구축 시작")
        logger.info("=" * 80)

        # 1. 회사 객체 생성
        await self.build_company_objects(conn)

        # 2. 임원 객체 및 링크 생성
        await self.build_officer_objects_and_links(conn)

        # 3. 전환사채 객체 및 링크 생성
        await self.build_cb_objects_and_links(conn)

        # 4. CB 인수자 객체 및 링크 생성
        await self.build_cb_subscriber_objects_and_links(conn)

        # 5. 계열사 링크 생성
        await self.build_affiliate_links(conn)

        # 최종 통계
        self.print_stats()

    async def build_company_objects(self, conn: asyncpg.Connection):
        """회사 객체 생성"""
        logger.info("\n[1/5] 회사 객체 생성")

        companies = await conn.fetch("""
            SELECT id, corp_code, ticker, name, name_en, sector, market,
                   market_cap, revenue, net_income, total_assets,
                   ownership_concentration, cb_issuance_count,
                   created_at
            FROM companies
        """)

        logger.info(f"대상 회사: {len(companies)}개")

        for company in companies:
            try:
                object_id = self._generate_object_id('COMP', str(company['id']))

                properties = {
                    'db_id': str(company['id']),
                    'name': company['name'],
                    'name_en': company['name_en'],
                    'corp_code': company['corp_code'],
                    'ticker': company['ticker'],
                    'sector': company['sector'],
                    'market': company['market'],
                    'market_cap': company['market_cap'],
                    'revenue': company['revenue'],
                    'net_income': company['net_income'],
                    'total_assets': company['total_assets'],
                    'ownership_concentration': company['ownership_concentration'],
                    'cb_issuance_count': company['cb_issuance_count']
                }

                # None 값 제거
                properties = {k: v for k, v in properties.items() if v is not None}

                await conn.execute("""
                    INSERT INTO ontology_objects (
                        object_id, object_type, version, confidence,
                        properties, source_documents, created_at, updated_at
                    )
                    VALUES ($1, $2, 1, 1.0, $3, $4, NOW(), NOW())
                    ON CONFLICT (object_id) DO UPDATE SET
                        properties = EXCLUDED.properties,
                        updated_at = NOW()
                """,
                    object_id,
                    self.OBJECT_TYPES['COMPANY'],
                    json.dumps(properties),
                    ['companies_table']
                )

                # companies 테이블에 ontology_object_id 업데이트
                await conn.execute("""
                    UPDATE companies SET ontology_object_id = $1 WHERE id = $2
                """, object_id, company['id'])

                self.stats['objects_created'] += 1

            except Exception as e:
                logger.error(f"회사 {company['name']} 객체 생성 실패: {e}")
                self.stats['errors'] += 1

        logger.info(f"  완료: {self.stats['objects_created']}개 생성")

    async def build_officer_objects_and_links(self, conn: asyncpg.Connection):
        """임원 객체 및 회사 연결 링크 생성"""
        logger.info("\n[2/5] 임원 객체 및 링크 생성")

        officers = await conn.fetch("""
            SELECT o.id, o.name, o.birth_date, o.gender, o.position,
                   o.board_count, o.network_centrality, o.influence_score,
                   o.has_conflict_of_interest, o.insider_trading_count,
                   o.career_history, o.education, o.created_at
            FROM officers o
        """)

        logger.info(f"대상 임원: {len(officers)}명")

        objects_created = 0
        links_created = 0

        for officer in officers:
            try:
                # 동명이인 구분을 위해 birth_date 포함
                unique_key = f"{officer['id']}"
                object_id = self._generate_object_id('OFFR', unique_key)

                properties = {
                    'db_id': str(officer['id']),
                    'name': officer['name'],
                    'birth_date': officer['birth_date'],
                    'gender': officer['gender'],
                    'position': officer['position'],
                    'board_count': officer['board_count'],
                    'network_centrality': officer['network_centrality'],
                    'influence_score': officer['influence_score'],
                    'has_conflict_of_interest': officer['has_conflict_of_interest'],
                    'insider_trading_count': officer['insider_trading_count'],
                    'education': officer['education']
                }

                # career_history는 별도 처리
                if officer['career_history']:
                    properties['career_history'] = officer['career_history']

                properties = {k: v for k, v in properties.items() if v is not None}

                await conn.execute("""
                    INSERT INTO ontology_objects (
                        object_id, object_type, version, confidence,
                        properties, source_documents, created_at, updated_at
                    )
                    VALUES ($1, $2, 1, 1.0, $3, $4, NOW(), NOW())
                    ON CONFLICT (object_id) DO UPDATE SET
                        properties = EXCLUDED.properties,
                        updated_at = NOW()
                """,
                    object_id,
                    self.OBJECT_TYPES['OFFICER'],
                    json.dumps(properties),
                    ['officers_table']
                )

                # officers 테이블에 ontology_object_id 업데이트
                await conn.execute("""
                    UPDATE officers SET ontology_object_id = $1 WHERE id = $2
                """, object_id, officer['id'])

                objects_created += 1

                # 회사 연결 링크 생성
                positions = await conn.fetch("""
                    SELECT op.company_id, op.position, op.term_start_date, op.term_end_date,
                           op.is_current, op.source_report_date, op.metadata,
                           c.ontology_object_id as company_ontology_id
                    FROM officer_positions op
                    JOIN companies c ON op.company_id = c.id
                    WHERE op.officer_id = $1
                """, officer['id'])

                for pos in positions:
                    if pos['company_ontology_id']:
                        link_id = self._generate_link_id(
                            object_id,
                            pos['company_ontology_id'],
                            self.LINK_TYPES['WORKS_AT']
                        )

                        link_properties = {
                            'position': pos['position'],
                            'term_start_date': str(pos['term_start_date']) if pos['term_start_date'] else None,
                            'term_end_date': str(pos['term_end_date']) if pos['term_end_date'] else None,
                            'is_current': pos['is_current'],
                            'source_report_date': str(pos['source_report_date']) if pos['source_report_date'] else None
                        }
                        link_properties = {k: v for k, v in link_properties.items() if v is not None}

                        # valid_from 설정 (임기 시작일 또는 현재)
                        valid_from = pos['term_start_date'] or datetime.now()

                        await conn.execute("""
                            INSERT INTO ontology_links (
                                link_id, link_type, source_object_id, target_object_id,
                                valid_from, valid_until, strength, confidence,
                                properties, created_at, updated_at
                            )
                            VALUES ($1, $2, $3, $4, $5, $6, 0.8, 1.0, $7, NOW(), NOW())
                            ON CONFLICT (link_id) DO UPDATE SET
                                properties = EXCLUDED.properties,
                                updated_at = NOW()
                        """,
                            link_id,
                            self.LINK_TYPES['WORKS_AT'],
                            object_id,
                            pos['company_ontology_id'],
                            valid_from,
                            pos['term_end_date'],
                            json.dumps(link_properties)
                        )

                        links_created += 1

            except Exception as e:
                logger.error(f"임원 {officer['name']} 객체/링크 생성 실패: {e}")
                self.stats['errors'] += 1

        self.stats['objects_created'] += objects_created
        self.stats['links_created'] += links_created
        logger.info(f"  완료: 객체 {objects_created}개, 링크 {links_created}개")

    async def build_cb_objects_and_links(self, conn: asyncpg.Connection):
        """전환사채 객체 및 회사 연결 링크 생성"""
        logger.info("\n[3/5] 전환사채 객체 및 링크 생성")

        cbs = await conn.fetch("""
            SELECT cb.id, cb.company_id, cb.bond_name, cb.issue_date, cb.maturity_date,
                   cb.issue_amount, cb.interest_rate, cb.conversion_price,
                   cb.status, cb.source_disclosure_id,
                   c.ontology_object_id as company_ontology_id
            FROM convertible_bonds cb
            JOIN companies c ON cb.company_id = c.id
        """)

        logger.info(f"대상 전환사채: {len(cbs)}개")

        objects_created = 0
        links_created = 0

        for cb in cbs:
            try:
                object_id = self._generate_object_id('CB', str(cb['id']))

                properties = {
                    'db_id': str(cb['id']),
                    'bond_name': cb['bond_name'],
                    'issue_date': str(cb['issue_date']) if cb['issue_date'] else None,
                    'maturity_date': str(cb['maturity_date']) if cb['maturity_date'] else None,
                    'issue_amount': cb['issue_amount'],
                    'interest_rate': cb['interest_rate'],
                    'conversion_price': cb['conversion_price'],
                    'status': cb['status'],
                    'source_disclosure_id': cb['source_disclosure_id']
                }
                properties = {k: v for k, v in properties.items() if v is not None}

                source_docs = []
                if cb['source_disclosure_id']:
                    source_docs.append(f"DART_{cb['source_disclosure_id']}")

                await conn.execute("""
                    INSERT INTO ontology_objects (
                        object_id, object_type, version, confidence,
                        properties, source_documents, created_at, updated_at
                    )
                    VALUES ($1, $2, 1, 1.0, $3, $4, NOW(), NOW())
                    ON CONFLICT (object_id) DO UPDATE SET
                        properties = EXCLUDED.properties,
                        updated_at = NOW()
                """,
                    object_id,
                    self.OBJECT_TYPES['CB'],
                    json.dumps(properties),
                    source_docs
                )

                objects_created += 1

                # 회사 → CB 링크 생성 (ISSUED)
                if cb['company_ontology_id']:
                    link_id = self._generate_link_id(
                        cb['company_ontology_id'],
                        object_id,
                        self.LINK_TYPES['ISSUED']
                    )

                    link_properties = {
                        'issue_amount': cb['issue_amount'],
                        'issue_date': str(cb['issue_date']) if cb['issue_date'] else None
                    }
                    link_properties = {k: v for k, v in link_properties.items() if v is not None}

                    await conn.execute("""
                        INSERT INTO ontology_links (
                            link_id, link_type, source_object_id, target_object_id,
                            valid_from, strength, confidence,
                            properties, created_at, updated_at
                        )
                        VALUES ($1, $2, $3, $4, COALESCE($5, NOW()), 0.9, 1.0, $6, NOW(), NOW())
                        ON CONFLICT (link_id) DO UPDATE SET
                            properties = EXCLUDED.properties,
                            updated_at = NOW()
                    """,
                        link_id,
                        self.LINK_TYPES['ISSUED'],
                        cb['company_ontology_id'],
                        object_id,
                        cb['issue_date'],
                        json.dumps(link_properties)
                    )

                    links_created += 1

            except Exception as e:
                logger.error(f"CB {cb['bond_name']} 객체/링크 생성 실패: {e}")
                self.stats['errors'] += 1

        self.stats['objects_created'] += objects_created
        self.stats['links_created'] += links_created
        logger.info(f"  완료: 객체 {objects_created}개, 링크 {links_created}개")

    async def build_cb_subscriber_objects_and_links(self, conn: asyncpg.Connection):
        """CB 인수자 객체 및 링크 생성"""
        logger.info("\n[4/5] CB 인수자 객체 및 링크 생성")

        subscribers = await conn.fetch("""
            SELECT s.id, s.cb_id, s.subscriber_name, s.subscriber_type,
                   s.subscription_amount, s.is_related_party, s.relationship_to_company,
                   s.selection_rationale, s.source_disclosure_id
            FROM cb_subscribers s
        """)

        logger.info(f"대상 인수자: {len(subscribers)}명")

        objects_created = 0
        links_created = 0

        # 인수자별 그룹핑 (동일 인수자가 여러 CB 인수 가능)
        subscriber_objects = {}

        for sub in subscribers:
            try:
                # 인수자 객체 (이름 기반으로 그룹핑)
                sub_key = f"{sub['subscriber_name']}_{sub['subscriber_type'] or 'unknown'}"

                if sub_key not in subscriber_objects:
                    object_id = self._generate_object_id('CBSUB', sub_key)

                    properties = {
                        'name': sub['subscriber_name'],
                        'type': sub['subscriber_type'],
                        'total_subscriptions': 0,
                        'total_amount': 0,
                        'is_related_party': sub['is_related_party'] == 'Y'
                    }

                    await conn.execute("""
                        INSERT INTO ontology_objects (
                            object_id, object_type, version, confidence,
                            properties, source_documents, created_at, updated_at
                        )
                        VALUES ($1, $2, 1, 1.0, $3, $4, NOW(), NOW())
                        ON CONFLICT (object_id) DO UPDATE SET
                            properties = EXCLUDED.properties,
                            updated_at = NOW()
                    """,
                        object_id,
                        self.OBJECT_TYPES['CB_SUBSCRIBER'],
                        json.dumps(properties),
                        []
                    )

                    subscriber_objects[sub_key] = object_id
                    objects_created += 1

                # CB 객체 ID 조회
                cb_object = await conn.fetchrow("""
                    SELECT o.object_id
                    FROM ontology_objects o
                    WHERE o.object_type = 'ConvertibleBond'
                    AND o.properties->>'db_id' = $1
                """, str(sub['cb_id']))

                if cb_object:
                    # 인수자 → CB 링크 생성
                    link_id = self._generate_link_id(
                        subscriber_objects[sub_key],
                        cb_object['object_id'],
                        self.LINK_TYPES['SUBSCRIBED']
                    )

                    link_properties = {
                        'subscription_amount': sub['subscription_amount'],
                        'is_related_party': sub['is_related_party'] == 'Y',
                        'relationship': sub['relationship_to_company'],
                        'selection_rationale': sub['selection_rationale']
                    }
                    link_properties = {k: v for k, v in link_properties.items() if v is not None}

                    await conn.execute("""
                        INSERT INTO ontology_links (
                            link_id, link_type, source_object_id, target_object_id,
                            valid_from, strength, confidence,
                            properties, created_at, updated_at
                        )
                        VALUES ($1, $2, $3, $4, NOW(), 0.8, 1.0, $5, NOW(), NOW())
                        ON CONFLICT (link_id) DO UPDATE SET
                            properties = EXCLUDED.properties,
                            updated_at = NOW()
                    """,
                        link_id,
                        self.LINK_TYPES['SUBSCRIBED'],
                        subscriber_objects[sub_key],
                        cb_object['object_id'],
                        json.dumps(link_properties)
                    )

                    links_created += 1

            except Exception as e:
                logger.error(f"인수자 {sub['subscriber_name']} 객체/링크 생성 실패: {e}")
                self.stats['errors'] += 1

        self.stats['objects_created'] += objects_created
        self.stats['links_created'] += links_created
        logger.info(f"  완료: 객체 {objects_created}개, 링크 {links_created}개")

    async def build_affiliate_links(self, conn: asyncpg.Connection):
        """계열사 링크 생성"""
        logger.info("\n[5/5] 계열사 링크 생성")

        affiliates = await conn.fetch("""
            SELECT a.id, a.parent_company_id, a.affiliate_company_id, a.affiliate_name,
                   a.ownership_ratio, a.voting_rights_ratio, a.total_assets,
                   a.revenue, a.net_income, a.source_date,
                   pc.ontology_object_id as parent_ontology_id,
                   ac.ontology_object_id as affiliate_ontology_id
            FROM affiliates a
            JOIN companies pc ON a.parent_company_id = pc.id
            JOIN companies ac ON a.affiliate_company_id = ac.id
        """)

        logger.info(f"대상 계열사 관계: {len(affiliates)}개")

        links_created = 0

        for aff in affiliates:
            try:
                if aff['parent_ontology_id'] and aff['affiliate_ontology_id']:
                    link_id = self._generate_link_id(
                        aff['parent_ontology_id'],
                        aff['affiliate_ontology_id'],
                        self.LINK_TYPES['OWNS']
                    )

                    link_properties = {
                        'ownership_ratio': aff['ownership_ratio'],
                        'voting_rights_ratio': aff['voting_rights_ratio'],
                        'total_assets': aff['total_assets'],
                        'revenue': aff['revenue'],
                        'net_income': aff['net_income'],
                        'source_date': aff['source_date']
                    }
                    link_properties = {k: v for k, v in link_properties.items() if v is not None}

                    # strength는 지분율에 비례
                    strength = min((aff['ownership_ratio'] or 0) / 100, 1.0)

                    await conn.execute("""
                        INSERT INTO ontology_links (
                            link_id, link_type, source_object_id, target_object_id,
                            valid_from, strength, confidence,
                            properties, created_at, updated_at
                        )
                        VALUES ($1, $2, $3, $4, NOW(), $5, 1.0, $6, NOW(), NOW())
                        ON CONFLICT (link_id) DO UPDATE SET
                            properties = EXCLUDED.properties,
                            strength = EXCLUDED.strength,
                            updated_at = NOW()
                    """,
                        link_id,
                        self.LINK_TYPES['OWNS'],
                        aff['parent_ontology_id'],
                        aff['affiliate_ontology_id'],
                        strength,
                        json.dumps(link_properties)
                    )

                    links_created += 1

            except Exception as e:
                logger.error(f"계열사 관계 {aff['affiliate_name']} 링크 생성 실패: {e}")
                self.stats['errors'] += 1

        self.stats['links_created'] += links_created
        logger.info(f"  완료: 링크 {links_created}개")

    def print_stats(self):
        """최종 통계 출력"""
        logger.info("\n" + "=" * 80)
        logger.info("온톨로지 구축 완료")
        logger.info("=" * 80)
        logger.info(f"객체 생성: {self.stats['objects_created']}개")
        logger.info(f"링크 생성: {self.stats['links_created']}개")
        logger.info(f"오류: {self.stats['errors']}건")


async def main():
    """메인 함수"""
    builder = OntologyBuilder()

    conn = await asyncpg.connect(DB_URL)

    try:
        await builder.build_all(conn)

        # 최종 현황 확인
        logger.info("\n" + "=" * 80)
        logger.info("온톨로지 현황")
        logger.info("=" * 80)

        # 객체 타입별 통계
        obj_stats = await conn.fetch("""
            SELECT object_type, COUNT(*) as cnt
            FROM ontology_objects
            GROUP BY object_type
            ORDER BY cnt DESC
        """)
        logger.info("\n객체 타입별:")
        for row in obj_stats:
            logger.info(f"  {row['object_type']}: {row['cnt']:,}개")

        # 링크 타입별 통계
        link_stats = await conn.fetch("""
            SELECT link_type, COUNT(*) as cnt
            FROM ontology_links
            GROUP BY link_type
            ORDER BY cnt DESC
        """)
        logger.info("\n링크 타입별:")
        for row in link_stats:
            logger.info(f"  {row['link_type']}: {row['cnt']:,}개")

    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
