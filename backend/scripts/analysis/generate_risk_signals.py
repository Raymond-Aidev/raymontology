#!/usr/bin/env python3
"""
Priority 1-2: risk_signals 테이블 생성
온톨로지 기반 리스크 탐지 패턴 분석
- CB 발행 패턴 이상
- 대주주-CB 인수 연관성
- 재무 악화 시그널
- 임원 이동 패턴
"""
import asyncio
import asyncpg
import logging
import os
import uuid
import json
import re
from datetime import datetime
from typing import List, Dict, Any

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def sanitize_string(s: str) -> str:
    """문자열에서 JSON에 문제가 되는 문자 제거"""
    if s is None:
        return ""
    # null bytes와 제어 문자 제거
    s = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', s)
    return s

DB_URL = os.getenv('DATABASE_URL', 'postgresql://postgres:dev_password@localhost:5432/raymontology_dev')


class RiskDetector:
    """온톨로지 기반 리스크 탐지기"""

    def __init__(self, conn: asyncpg.Connection):
        self.conn = conn
        self.stats = {'detected': 0, 'saved': 0}

    async def detect_all_risks(self):
        """모든 리스크 패턴 탐지"""
        risks = []

        # 1. CB 관련 리스크
        risks.extend(await self.detect_cb_dilution_risk())
        risks.extend(await self.detect_repeated_cb_pattern())
        risks.extend(await self.detect_insider_cb_subscription())

        # 2. 재무 관련 리스크
        risks.extend(await self.detect_financial_deterioration())

        # 3. 임원 관련 리스크
        risks.extend(await self.detect_officer_exodus())

        self.stats['detected'] = len(risks)
        return risks

    async def detect_cb_dilution_risk(self) -> List[Dict]:
        """CB 대량 발행으로 인한 희석 리스크 탐지"""
        risks = []

        # 최근 2년 내 CB 발행 총액이 시가총액 대비 높은 경우
        results = await self.conn.fetch("""
            SELECT
                c.id as company_id,
                c.name,
                c.market,
                COUNT(cb.id) as cb_count,
                SUM(cb.issue_amount) as total_issue_amount,
                fs.total_equity
            FROM companies c
            JOIN convertible_bonds cb ON cb.company_id = c.id
            LEFT JOIN financial_statements fs ON fs.company_id = c.id
                AND fs.fiscal_year = 2024
            WHERE c.market IN ('KOSPI', 'KOSDAQ')
            AND cb.issue_date >= '2023-01-01'
            GROUP BY c.id, c.name, c.market, fs.total_equity
            HAVING COUNT(cb.id) >= 3
                OR SUM(cb.issue_amount) > COALESCE(fs.total_equity, 0) * 0.3
        """)

        for r in results:
            risk_score = min(100, (r['cb_count'] * 15) +
                           (50 if r['total_equity'] and r['total_issue_amount'] > r['total_equity'] * 0.5 else 0))

            risks.append({
                'company_id': r['company_id'],
                'pattern_type': 'CB_DILUTION_RISK',
                'severity': 'HIGH' if risk_score > 70 else 'MEDIUM',
                'risk_score': risk_score,
                'title': f"{r['name']} CB 희석 리스크",
                'description': f"최근 2년 내 {r['cb_count']}건의 CB 발행, 총 {r['total_issue_amount']:,.0f}원. 자본잠식 가능성 모니터링 필요.",
                'evidence': {
                    'cb_count': r['cb_count'],
                    'total_issue_amount': float(r['total_issue_amount']) if r['total_issue_amount'] else 0,
                    'total_equity': float(r['total_equity']) if r['total_equity'] else 0
                }
            })

        return risks

    async def detect_repeated_cb_pattern(self) -> List[Dict]:
        """반복적 CB 발행 패턴 탐지 (시세조종 의심)"""
        risks = []

        results = await self.conn.fetch("""
            WITH cb_gaps AS (
                SELECT
                    company_id,
                    issue_date,
                    LAG(issue_date) OVER (PARTITION BY company_id ORDER BY issue_date) as prev_date
                FROM convertible_bonds
                WHERE issue_date IS NOT NULL
            )
            SELECT
                c.id as company_id,
                c.name,
                COUNT(*) as short_gap_count
            FROM cb_gaps cg
            JOIN companies c ON c.id = cg.company_id
            WHERE cg.prev_date IS NOT NULL
            AND cg.issue_date - cg.prev_date < 90
            GROUP BY c.id, c.name
            HAVING COUNT(*) >= 2
        """)

        for r in results:
            risks.append({
                'company_id': r['company_id'],
                'pattern_type': 'REPEATED_CB_PATTERN',
                'severity': 'HIGH',
                'risk_score': min(100, 40 + r['short_gap_count'] * 20),
                'title': f"{r['name']} 반복적 CB 발행",
                'description': f"90일 이내 반복 CB 발행 {r['short_gap_count']}회 감지. 시세조종 또는 자금조달 압박 가능성.",
                'evidence': {'short_gap_count': r['short_gap_count']}
            })

        return risks

    async def detect_insider_cb_subscription(self) -> List[Dict]:
        """내부자/특수관계인 CB 인수 패턴 탐지"""
        risks = []

        results = await self.conn.fetch("""
            SELECT
                c.id as company_id,
                c.name,
                cb.id as cb_id,
                s.subscriber_name,
                s.subscription_amount,
                s.is_related_party
            FROM companies c
            JOIN convertible_bonds cb ON cb.company_id = c.id
            JOIN cb_subscribers s ON s.cb_id = cb.id
            WHERE s.is_related_party IS NOT NULL AND s.is_related_party != ''
            OR s.subscriber_name ILIKE '%대표%'
            OR s.subscriber_name ILIKE '%최대주주%'
            OR EXISTS (
                SELECT 1 FROM officers o
                JOIN officer_positions op ON o.id = op.officer_id
                WHERE op.company_id = c.id
                AND o.name = s.subscriber_name
            )
        """)

        # 회사별로 그룹화
        company_risks = {}
        for r in results:
            cid = str(r['company_id'])
            if cid not in company_risks:
                company_risks[cid] = {
                    'company_id': r['company_id'],
                    'name': r['name'],
                    'subscribers': [],
                    'total_amount': 0
                }
            company_risks[cid]['subscribers'].append(sanitize_string(r['subscriber_name']))
            company_risks[cid]['total_amount'] += r['subscription_amount'] or 0

        for cr in company_risks.values():
            risks.append({
                'company_id': cr['company_id'],
                'pattern_type': 'INSIDER_CB_SUBSCRIPTION',
                'severity': 'MEDIUM',
                'risk_score': min(80, 30 + len(cr['subscribers']) * 10),
                'title': f"{cr['name']} 내부자 CB 인수",
                'description': f"내부자/특수관계인 CB 인수 {len(cr['subscribers'])}건, 총 {cr['total_amount']:,.0f}원",
                'evidence': {
                    'subscribers': cr['subscribers'][:10],
                    'total_amount': cr['total_amount']
                }
            })

        return risks

    async def detect_financial_deterioration(self) -> List[Dict]:
        """재무 악화 시그널 탐지"""
        risks = []

        results = await self.conn.fetch("""
            WITH yearly_compare AS (
                SELECT
                    company_id,
                    fiscal_year,
                    net_income,
                    operating_profit,
                    total_equity,
                    LAG(net_income) OVER (PARTITION BY company_id ORDER BY fiscal_year) as prev_net_income,
                    LAG(operating_profit) OVER (PARTITION BY company_id ORDER BY fiscal_year) as prev_op_profit
                FROM financial_statements
            )
            SELECT
                c.id as company_id,
                c.name,
                c.market,
                yc.fiscal_year,
                yc.net_income,
                yc.prev_net_income,
                yc.operating_profit,
                yc.total_equity
            FROM yearly_compare yc
            JOIN companies c ON c.id = yc.company_id
            WHERE c.market IN ('KOSPI', 'KOSDAQ')
            AND yc.fiscal_year = 2024
            AND yc.prev_net_income IS NOT NULL
            AND (
                (yc.prev_net_income > 0 AND yc.net_income < 0)
                OR (yc.operating_profit < 0 AND yc.total_equity > 0 AND yc.operating_profit < -yc.total_equity * 0.3)
            )
        """)

        for r in results:
            severity = 'CRITICAL' if r['net_income'] < 0 and r['total_equity'] and r['net_income'] < -r['total_equity'] * 0.5 else 'HIGH'

            risks.append({
                'company_id': r['company_id'],
                'pattern_type': 'FINANCIAL_DETERIORATION',
                'severity': severity,
                'risk_score': 85 if severity == 'CRITICAL' else 65,
                'title': f"{r['name']} 재무 악화",
                'description': f"2024년 당기순이익 {r['net_income']:,.0f}원 (전년 {r['prev_net_income']:,.0f}원). 적자전환 또는 대규모 손실.",
                'evidence': {
                    'fiscal_year': r['fiscal_year'],
                    'net_income': float(r['net_income']) if r['net_income'] else 0,
                    'prev_net_income': float(r['prev_net_income']) if r['prev_net_income'] else 0
                }
            })

        return risks

    async def detect_officer_exodus(self) -> List[Dict]:
        """임원 대량 이탈 패턴 탐지"""
        risks = []

        results = await self.conn.fetch("""
            SELECT
                c.id as company_id,
                c.name,
                COUNT(DISTINCT op.officer_id) as current_officers,
                (
                    SELECT COUNT(DISTINCT officer_id)
                    FROM officer_positions op2
                    WHERE op2.company_id = c.id
                    AND op2.is_current = false
                ) as departed_officers
            FROM companies c
            JOIN officer_positions op ON op.company_id = c.id
            WHERE c.market IN ('KOSPI', 'KOSDAQ')
            AND op.is_current = true
            GROUP BY c.id, c.name
            HAVING (
                SELECT COUNT(DISTINCT officer_id)
                FROM officer_positions op2
                WHERE op2.company_id = c.id
                AND op2.is_current = false
            ) > COUNT(DISTINCT op.officer_id) * 0.5
        """)

        for r in results:
            risks.append({
                'company_id': r['company_id'],
                'pattern_type': 'OFFICER_EXODUS',
                'severity': 'MEDIUM',
                'risk_score': 55,
                'title': f"{r['name']} 임원 이탈",
                'description': f"현재 임원 {r['current_officers']}명, 퇴임 임원 {r['departed_officers']}명. 경영진 불안정 가능성.",
                'evidence': {
                    'current_officers': r['current_officers'],
                    'departed_officers': r['departed_officers']
                }
            })

        return risks

    async def save_risks(self, risks: List[Dict]):
        """리스크 시그널 저장"""
        saved = 0
        for risk in risks:
            try:
                await self.conn.execute("""
                    INSERT INTO risk_signals (
                        signal_id, target_company_id, pattern_type, severity, status,
                        risk_score, title, description, evidence, detected_at, created_at, updated_at
                    ) VALUES ($1, $2, $3, $4::riskseverity, 'DETECTED'::riskstatus, $5, $6, $7, $8, NOW(), NOW(), NOW())
                    ON CONFLICT (signal_id) DO UPDATE SET
                        risk_score = EXCLUDED.risk_score,
                        evidence = EXCLUDED.evidence,
                        updated_at = NOW()
                """,
                    uuid.uuid4(),
                    risk['company_id'],
                    risk['pattern_type'],
                    risk['severity'],
                    risk['risk_score'],
                    risk['title'],
                    risk['description'],
                    json.dumps(risk['evidence'], ensure_ascii=False)
                )
                saved += 1
            except Exception as e:
                logger.error(f"리스크 저장 실패: {e}")

        self.stats['saved'] = saved
        return saved


async def main():
    logger.info("=" * 80)
    logger.info("온톨로지 기반 리스크 시그널 생성")
    logger.info("=" * 80)

    conn = await asyncpg.connect(DB_URL)

    try:
        detector = RiskDetector(conn)

        # 기존 리스크 시그널 정리 (옵션)
        await conn.execute("DELETE FROM risk_signals WHERE detected_at < NOW() - INTERVAL '7 days'")

        # 리스크 탐지
        risks = await detector.detect_all_risks()
        logger.info(f"\n탐지된 리스크: {len(risks)}개")

        # 패턴별 통계
        patterns = {}
        for r in risks:
            p = r['pattern_type']
            patterns[p] = patterns.get(p, 0) + 1

        for p, cnt in sorted(patterns.items()):
            logger.info(f"  - {p}: {cnt}개")

        # 저장
        await detector.save_risks(risks)

        # 결과
        logger.info("\n" + "=" * 80)
        logger.info("리스크 시그널 생성 완료")
        logger.info(f"탐지: {detector.stats['detected']}개")
        logger.info(f"저장: {detector.stats['saved']}개")

        # 현재 상태
        count = await conn.fetchval("SELECT COUNT(*) FROM risk_signals")
        logger.info(f"\n현재 risk_signals 테이블: {count:,}개")

        # 심각도별 분포
        severity_dist = await conn.fetch("""
            SELECT severity, COUNT(*) as cnt
            FROM risk_signals
            GROUP BY severity
            ORDER BY severity
        """)
        for row in severity_dist:
            logger.info(f"  - {row['severity']}: {row['cnt']}개")

    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
