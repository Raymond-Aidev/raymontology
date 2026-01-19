#!/usr/bin/env python3
"""
추가 리스크 신호 생성

PRD 정의 패턴:
1. SERIAL_CB_INVESTOR - 반복 CB 투자자 (증권사 제외)
2. CONNECTED_LOSS_COMPANIES - 적자기업 연결
3. EXECUTIVE_HIGH_TURNOVER - 임원 고속 교체
"""
import asyncio
import asyncpg
import json
import logging
from datetime import date
import uuid

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

DB_URL = 'postgresql://postgres:dev_password@localhost:5432/raymontology_dev'

# 제외할 기관투자자 (증권사, 은행 등)
EXCLUDED_INVESTORS = ['증권', '은행', '캐피탈', '저축은행', '신탁', '자산운용', '투자조합']


async def generate_additional_signals():
    """추가 리스크 신호 생성"""
    conn = await asyncpg.connect(DB_URL)

    try:
        before_count = await conn.fetchval("SELECT COUNT(*) FROM risk_signals")
        logger.info(f"작업 전 risk_signals: {before_count}건")

        stats = {
            'serial_investor': 0,
            'loss_connection': 0,
            'turnover': 0,
            'errors': 0
        }

        # 1. SERIAL_CB_INVESTOR - 반복 CB 투자자 (개인/소규모 법인만)
        logger.info("패턴 1: SERIAL_CB_INVESTOR 탐지...")

        # 3개 이상 회사에 투자한 개인/소규모 투자자
        serial_investors = await conn.fetch("""
            WITH serial_investors AS (
                SELECT cs.subscriber_name, COUNT(DISTINCT cb.company_id) as company_count
                FROM cb_subscribers cs
                JOIN convertible_bonds cb ON cs.cb_id = cb.id
                WHERE cs.subscriber_name NOT LIKE '%증권%'
                AND cs.subscriber_name NOT LIKE '%은행%'
                AND cs.subscriber_name NOT LIKE '%캐피탈%'
                AND cs.subscriber_name NOT LIKE '%저축은행%'
                AND cs.subscriber_name NOT LIKE '%신탁%'
                AND cs.subscriber_name NOT LIKE '%자산운용%'
                AND cs.subscriber_name NOT LIKE '%투자조합%'
                AND cs.subscriber_name NOT LIKE '%펀드%'
                AND LENGTH(cs.subscriber_name) <= 20
                GROUP BY cs.subscriber_name
                HAVING COUNT(DISTINCT cb.company_id) >= 3
            )
            SELECT DISTINCT cb.company_id, c.name as company_name, c.corp_code,
                   cs.subscriber_name, si.company_count
            FROM serial_investors si
            JOIN cb_subscribers cs ON si.subscriber_name = cs.subscriber_name
            JOIN convertible_bonds cb ON cs.cb_id = cb.id
            JOIN companies c ON cb.company_id = c.id
        """)

        seen_companies = set()
        for row in serial_investors:
            if row['company_id'] in seen_companies:
                continue
            seen_companies.add(row['company_id'])

            try:
                await conn.execute("""
                    INSERT INTO risk_signals (
                        signal_id, target_company_id, pattern_type, severity, status,
                        risk_score, title, description, evidence, detected_at
                    )
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, NOW())
                    ON CONFLICT DO NOTHING
                """,
                    uuid.uuid4(),
                    row['company_id'],
                    'SERIAL_CB_INVESTOR',
                    'HIGH',
                    'DETECTED',
                    float(min(70 + row['company_count'] * 5, 100)),
                    f"반복 CB 투자자 감지",
                    f"{row['company_name']}에 {row['subscriber_name']}이(가) CB 투자. 해당 투자자는 {row['company_count']}개 회사에 CB 투자 이력 보유.",
                    json.dumps({
                        'investor_name': row['subscriber_name'],
                        'total_investments': row['company_count']
                    })
                )
                stats['serial_investor'] += 1
            except Exception as e:
                stats['errors'] += 1
                if stats['errors'] <= 3:
                    logger.error(f"SERIAL_CB_INVESTOR 오류: {e}")

        logger.info(f"  SERIAL_CB_INVESTOR: {stats['serial_investor']}건")

        # 2. CONNECTED_LOSS_COMPANIES - 적자기업 연결
        logger.info("패턴 2: CONNECTED_LOSS_COMPANIES 탐지...")

        # 적자 회사 목록
        loss_company_ids = await conn.fetch("""
            SELECT DISTINCT company_id
            FROM financial_statements
            WHERE net_income < 0
            AND fiscal_year >= 2023
        """)
        loss_ids = [r['company_id'] for r in loss_company_ids]
        logger.info(f"  적자 회사: {len(loss_ids)}개")

        if loss_ids:
            connected = await conn.fetch("""
                SELECT op1.company_id, c1.name as company_name, c1.corp_code,
                       COUNT(DISTINCT op2.company_id) as loss_connection_count
                FROM officer_positions op1
                JOIN companies c1 ON op1.company_id = c1.id
                JOIN officers o ON op1.officer_id = o.id
                JOIN officer_positions op2 ON o.id = op2.officer_id
                WHERE op1.company_id != op2.company_id
                AND op2.company_id = ANY($1::uuid[])
                AND (op1.term_end_date IS NULL OR op1.term_end_date >= '2024-01-01')
                GROUP BY op1.company_id, c1.name, c1.corp_code
                HAVING COUNT(DISTINCT op2.company_id) >= 2
                LIMIT 500
            """, loss_ids)

            logger.info(f"  적자기업 연결 회사: {len(connected)}개")

            for row in connected:
                try:
                    await conn.execute("""
                        INSERT INTO risk_signals (
                            signal_id, target_company_id, pattern_type, severity, status,
                            risk_score, title, description, evidence, detected_at
                        )
                        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, NOW())
                        ON CONFLICT DO NOTHING
                    """,
                        uuid.uuid4(),
                        row['company_id'],
                        'CONNECTED_LOSS_COMPANIES',
                        'HIGH' if row['loss_connection_count'] >= 3 else 'MEDIUM',
                        'DETECTED',
                        float(min(60 + row['loss_connection_count'] * 10, 100)),
                        f"적자기업 연결 ({row['loss_connection_count']}개사)",
                        f"{row['company_name']} 임원이 {row['loss_connection_count']}개의 적자기업에 재직 중입니다.",
                        json.dumps({
                            'loss_connection_count': row['loss_connection_count']
                        })
                    )
                    stats['loss_connection'] += 1
                except Exception as e:
                    stats['errors'] += 1
                    if stats['errors'] <= 3:
                        logger.error(f"LOSS_CONNECTION 오류: {e}")

        logger.info(f"  CONNECTED_LOSS_COMPANIES: {stats['loss_connection']}건")

        # 3. EXECUTIVE_HIGH_TURNOVER - 임원 고속 교체
        logger.info("패턴 3: EXECUTIVE_HIGH_TURNOVER 탐지...")

        turnover = await conn.fetch("""
            SELECT op.company_id, c.name as company_name, c.corp_code,
                   COUNT(DISTINCT op.officer_id) as turnover_count
            FROM officer_positions op
            JOIN companies c ON op.company_id = c.id
            WHERE op.term_end_date IS NOT NULL
            AND op.term_end_date >= '2022-01-01'
            AND op.term_end_date <= '2025-06-30'
            GROUP BY op.company_id, c.name, c.corp_code
            HAVING COUNT(DISTINCT op.officer_id) >= 10
            ORDER BY COUNT(DISTINCT op.officer_id) DESC
            LIMIT 500
        """)

        logger.info(f"  임원 교체 회사: {len(turnover)}개")

        for row in turnover:
            try:
                await conn.execute("""
                    INSERT INTO risk_signals (
                        signal_id, target_company_id, pattern_type, severity, status,
                        risk_score, title, description, evidence, detected_at
                    )
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, NOW())
                    ON CONFLICT DO NOTHING
                """,
                    uuid.uuid4(),
                    row['company_id'],
                    'EXECUTIVE_HIGH_TURNOVER',
                    'HIGH' if row['turnover_count'] >= 15 else 'MEDIUM',
                    'DETECTED',
                    float(min(50 + (row['turnover_count'] - 10) * 3, 100)),
                    f"임원 고속 교체 ({row['turnover_count']}명)",
                    f"{row['company_name']}에서 최근 3년간 {row['turnover_count']}명의 임원이 교체되었습니다.",
                    json.dumps({
                        'turnover_count': row['turnover_count'],
                        'period': '2022-2025'
                    })
                )
                stats['turnover'] += 1
            except Exception as e:
                stats['errors'] += 1
                if stats['errors'] <= 3:
                    logger.error(f"TURNOVER 오류: {e}")

        logger.info(f"  EXECUTIVE_HIGH_TURNOVER: {stats['turnover']}건")

        # 최종 결과
        after_count = await conn.fetchval("SELECT COUNT(*) FROM risk_signals")

        logger.info("\n" + "=" * 60)
        logger.info("추가 리스크 신호 생성 완료")
        logger.info("=" * 60)
        logger.info(f"SERIAL_CB_INVESTOR: {stats['serial_investor']}건")
        logger.info(f"CONNECTED_LOSS_COMPANIES: {stats['loss_connection']}건")
        logger.info(f"EXECUTIVE_HIGH_TURNOVER: {stats['turnover']}건")
        logger.info(f"오류: {stats['errors']}건")
        logger.info("-" * 60)
        logger.info(f"risk_signals: {before_count}건 → {after_count}건 (+{after_count - before_count}건)")
        logger.info("=" * 60)

        # 패턴별 분포
        dist = await conn.fetch("""
            SELECT pattern_type, severity, COUNT(*) as cnt
            FROM risk_signals
            GROUP BY pattern_type, severity
            ORDER BY pattern_type, severity
        """)
        logger.info("\n패턴별 분포:")
        for row in dist:
            logger.info(f"  {row['pattern_type']} ({row['severity']}): {row['cnt']}건")

    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(generate_additional_signals())
