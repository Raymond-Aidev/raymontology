#!/usr/bin/env python3
"""
Phase 4: 실패 기업 레이블링

Option C (Altman 방식) 실행을 위한 실패 기업 정의 및 레이블링

사용법:
    python -m scripts.analysis.label_failure_companies --scan
    python -m scripts.analysis.label_failure_companies --create-table
    python -m scripts.analysis.label_failure_companies --label
    python -m scripts.analysis.label_failure_companies --report
"""

import argparse
import asyncio
import logging
import os
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional

import asyncpg

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# 실패 기업 정의 기준
# ═══════════════════════════════════════════════════════════════════════════════

FAILURE_CRITERIA = {
    'EMBEZZLEMENT': {
        'name': '횡령/배임',
        'keywords': ['횡령', '배임', '검찰', '구속', '기소', '특경법'],
        'severity': 'HIGH',
        'confidence': 0.9,
    },
    'AUDIT_QUALIFIED': {
        'name': '감사의견 비적정',
        'keywords': ['감사의견', '한정', '부적정', '의견거절'],
        'severity': 'HIGH',
        'confidence': 0.85,
    },
    'MANAGED_STOCK': {
        'name': '관리종목 지정',
        'keywords': ['관리종목', '투자주의', '거래정지'],
        'severity': 'MEDIUM',
        'confidence': 0.95,
    },
    'CB_DEFAULT': {
        'name': 'CB 상환 실패',
        'keywords': ['전환사채', '상환', '연장', '불이행'],
        'severity': 'HIGH',
        'confidence': 0.8,
    },
    'CONTINUOUS_LOSS': {
        'name': '3년 연속 적자',
        'severity': 'MEDIUM',
        'confidence': 0.9,
    },
    'CAPITAL_EROSION': {
        'name': '자본잠식',
        'keywords': ['자본잠식', '완전자본잠식'],
        'severity': 'HIGH',
        'confidence': 0.95,
    },
}


@dataclass
class FailureCandidate:
    """실패 기업 후보"""
    company_id: str
    company_name: str
    ticker: str
    failure_type: str
    evidence: str
    disclosure_date: Optional[datetime]
    confidence: float


class FailureLabeler:
    """실패 기업 레이블링 도구"""

    def __init__(self, database_url: Optional[str] = None):
        self.database_url = database_url or os.getenv('DATABASE_URL')
        if not self.database_url:
            raise ValueError("DATABASE_URL 환경 변수가 설정되지 않았습니다")

        if self.database_url.startswith('postgresql+asyncpg://'):
            self.database_url = self.database_url.replace('postgresql+asyncpg://', 'postgresql://')

    async def create_labels_table(self):
        """company_labels 테이블 생성"""
        conn = await asyncpg.connect(self.database_url)
        try:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS company_labels (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
                    label_type VARCHAR(20) NOT NULL,
                    failure_reason VARCHAR(100),
                    evidence TEXT,
                    disclosure_id UUID,
                    label_date DATE,
                    confidence DECIMAL(3,2),
                    created_by VARCHAR(50) DEFAULT 'system',
                    created_at TIMESTAMP DEFAULT NOW(),

                    CONSTRAINT uq_company_label UNIQUE(company_id, failure_reason)
                );

                CREATE INDEX IF NOT EXISTS idx_label_type ON company_labels(label_type);
                CREATE INDEX IF NOT EXISTS idx_label_company ON company_labels(company_id);
            """)
            logger.info("company_labels 테이블 생성 완료")

        finally:
            await conn.close()

    async def scan_disclosures_for_failures(self) -> List[FailureCandidate]:
        """공시에서 실패 기업 후보 스캔"""
        conn = await asyncpg.connect(self.database_url)
        candidates = []

        try:
            # 횡령/배임 관련 공시 검색
            for failure_type, criteria in FAILURE_CRITERIA.items():
                if 'keywords' not in criteria:
                    continue

                keywords = criteria['keywords']
                keyword_conditions = " OR ".join([f"d.report_nm ILIKE '%{kw}%'" for kw in keywords])

                query = f"""
                    SELECT DISTINCT
                        c.id as company_id,
                        c.name as company_name,
                        c.ticker,
                        d.report_nm as evidence,
                        d.rcept_dt as submission_date
                    FROM disclosures d
                    JOIN companies c ON c.corp_code = d.corp_code
                    WHERE ({keyword_conditions})
                      AND c.listing_status = 'LISTED'
                    ORDER BY d.rcept_dt DESC
                """

                rows = await conn.fetch(query)

                for row in rows:
                    candidates.append(FailureCandidate(
                        company_id=str(row['company_id']),
                        company_name=row['company_name'],
                        ticker=row['ticker'],
                        failure_type=failure_type,
                        evidence=row['evidence'],
                        disclosure_date=row['submission_date'],
                        confidence=criteria['confidence'],
                    ))

            logger.info(f"공시 스캔 완료: {len(candidates)}개 후보 발견")

        finally:
            await conn.close()

        return candidates

    async def scan_financial_failures(self) -> List[FailureCandidate]:
        """재무제표 기반 실패 기업 스캔 (3년 연속 적자 등)"""
        conn = await asyncpg.connect(self.database_url)
        candidates = []

        try:
            # 3년 연속 적자 기업
            rows = await conn.fetch("""
                WITH yearly_income AS (
                    SELECT
                        company_id,
                        fiscal_year,
                        net_income,
                        ROW_NUMBER() OVER (PARTITION BY company_id ORDER BY fiscal_year DESC) as rn
                    FROM financial_details
                    WHERE fiscal_year >= 2022
                )
                SELECT
                    c.id as company_id,
                    c.name as company_name,
                    c.ticker,
                    COUNT(*) as loss_years
                FROM yearly_income yi
                JOIN companies c ON c.id = yi.company_id
                WHERE yi.rn <= 3
                  AND yi.net_income < 0
                  AND c.listing_status = 'LISTED'
                GROUP BY c.id, c.name, c.ticker
                HAVING COUNT(*) >= 3
            """)

            for row in rows:
                candidates.append(FailureCandidate(
                    company_id=str(row['company_id']),
                    company_name=row['company_name'],
                    ticker=row['ticker'],
                    failure_type='CONTINUOUS_LOSS',
                    evidence=f"{row['loss_years']}년 연속 적자",
                    disclosure_date=None,
                    confidence=0.9,
                ))

            # 자본잠식 기업
            rows = await conn.fetch("""
                SELECT
                    c.id as company_id,
                    c.name as company_name,
                    c.ticker,
                    fd.total_equity,
                    fd.fiscal_year
                FROM financial_details fd
                JOIN companies c ON c.id = fd.company_id
                WHERE fd.fiscal_year = 2024
                  AND fd.total_equity < 0
                  AND c.listing_status = 'LISTED'
            """)

            for row in rows:
                candidates.append(FailureCandidate(
                    company_id=str(row['company_id']),
                    company_name=row['company_name'],
                    ticker=row['ticker'],
                    failure_type='CAPITAL_EROSION',
                    evidence=f"자본총계: {row['total_equity']:,.0f}원",
                    disclosure_date=None,
                    confidence=0.95,
                ))

            logger.info(f"재무 스캔 완료: {len(candidates)}개 후보 발견")

        finally:
            await conn.close()

        return candidates

    async def scan_managed_stocks(self) -> List[FailureCandidate]:
        """관리종목 기업 스캔"""
        conn = await asyncpg.connect(self.database_url)
        candidates = []

        try:
            rows = await conn.fetch("""
                SELECT
                    id as company_id,
                    name as company_name,
                    ticker,
                    is_managed,
                    trading_status
                FROM companies
                WHERE (is_managed = 'Y' OR trading_status = 'SUSPENDED')
                  AND listing_status = 'LISTED'
            """)

            for row in rows:
                reason = []
                if row['is_managed'] == 'Y':
                    reason.append('관리종목')
                if row['trading_status'] == 'SUSPENDED':
                    reason.append('거래정지')

                candidates.append(FailureCandidate(
                    company_id=str(row['company_id']),
                    company_name=row['company_name'],
                    ticker=row['ticker'] or '',
                    failure_type='MANAGED_STOCK',
                    evidence=', '.join(reason),
                    disclosure_date=None,
                    confidence=0.95,
                ))

            logger.info(f"관리종목 스캔 완료: {len(candidates)}개 후보 발견")

        finally:
            await conn.close()

        return candidates

    async def save_labels(self, candidates: List[FailureCandidate]):
        """레이블 저장"""
        from datetime import date, datetime

        conn = await asyncpg.connect(self.database_url)
        saved = 0

        try:
            for candidate in candidates:
                try:
                    # disclosure_date 형식 변환 (문자열 → date)
                    label_date = None
                    if candidate.disclosure_date:
                        if isinstance(candidate.disclosure_date, str):
                            # 'YYYYMMDD' 형식
                            if len(candidate.disclosure_date) == 8:
                                label_date = date(
                                    int(candidate.disclosure_date[:4]),
                                    int(candidate.disclosure_date[4:6]),
                                    int(candidate.disclosure_date[6:8])
                                )
                            else:
                                label_date = date.today()
                        elif isinstance(candidate.disclosure_date, (date, datetime)):
                            label_date = candidate.disclosure_date if isinstance(candidate.disclosure_date, date) else candidate.disclosure_date.date()
                        else:
                            label_date = date.today()
                    else:
                        label_date = date.today()

                    await conn.execute("""
                        INSERT INTO company_labels (
                            company_id, label_type, failure_reason, evidence,
                            label_date, confidence
                        )
                        VALUES ($1, 'FAILURE', $2, $3, $4, $5)
                        ON CONFLICT (company_id, failure_reason) DO NOTHING
                    """,
                        candidate.company_id,
                        candidate.failure_type,
                        candidate.evidence[:500] if candidate.evidence else None,
                        label_date,
                        candidate.confidence,
                    )
                    saved += 1
                except Exception as e:
                    logger.warning(f"레이블 저장 실패 {candidate.company_name}: {e}")

            logger.info(f"레이블 저장 완료: {saved}/{len(candidates)}건")

        finally:
            await conn.close()

    async def get_label_report(self) -> Dict:
        """레이블링 현황 보고"""
        conn = await asyncpg.connect(self.database_url)

        try:
            # 타입별 분포
            type_dist = await conn.fetch("""
                SELECT failure_reason, COUNT(*) as count
                FROM company_labels
                WHERE label_type = 'FAILURE'
                GROUP BY failure_reason
                ORDER BY count DESC
            """)

            # 고신뢰도 레이블 수
            high_conf = await conn.fetchval("""
                SELECT COUNT(DISTINCT company_id)
                FROM company_labels
                WHERE label_type = 'FAILURE'
                  AND confidence >= 0.9
            """)

            # 전체 레이블된 기업 수
            total_labeled = await conn.fetchval("""
                SELECT COUNT(DISTINCT company_id)
                FROM company_labels
                WHERE label_type = 'FAILURE'
            """)

            return {
                'total_labeled': total_labeled,
                'high_confidence': high_conf,
                'by_type': {r['failure_reason']: r['count'] for r in type_dist},
            }

        finally:
            await conn.close()

    def print_report(self, report: Dict):
        """보고서 출력"""
        print("\n" + "=" * 60)
        print("실패 기업 레이블링 현황")
        print("=" * 60)

        print(f"\n총 레이블된 기업: {report['total_labeled']}개")
        print(f"고신뢰도 (≥0.9): {report['high_confidence']}개")

        print("\n### 유형별 분포")
        print("-" * 40)
        for reason, count in report['by_type'].items():
            criteria_name = FAILURE_CRITERIA.get(reason, {}).get('name', reason)
            print(f"  {criteria_name:<20}: {count}개")

        # Option C 조건 확인
        print("\n### Option C 실행 조건 확인")
        print("-" * 40)
        if report['high_confidence'] >= 50:
            print(f"✅ 고신뢰도 실패 기업 50개 이상 충족 ({report['high_confidence']}개)")
        else:
            print(f"❌ 고신뢰도 실패 기업 50개 미만 ({report['high_confidence']}개, 필요: 50개)")


async def main():
    parser = argparse.ArgumentParser(description='실패 기업 레이블링')
    parser.add_argument('--scan', action='store_true', help='실패 기업 후보 스캔')
    parser.add_argument('--create-table', action='store_true', help='레이블 테이블 생성')
    parser.add_argument('--label', action='store_true', help='레이블 저장')
    parser.add_argument('--report', action='store_true', help='현황 보고')

    args = parser.parse_args()

    labeler = FailureLabeler()

    if args.create_table:
        await labeler.create_labels_table()

    if args.scan:
        print("\n### 공시 기반 스캔")
        disc_candidates = await labeler.scan_disclosures_for_failures()
        for c in disc_candidates[:10]:
            print(f"  [{c.failure_type}] {c.company_name}: {c.evidence[:50]}...")

        print("\n### 재무제표 기반 스캔")
        fin_candidates = await labeler.scan_financial_failures()
        for c in fin_candidates[:10]:
            print(f"  [{c.failure_type}] {c.company_name}: {c.evidence}")

        print("\n### 관리종목 스캔")
        managed_candidates = await labeler.scan_managed_stocks()
        for c in managed_candidates[:10]:
            print(f"  [{c.failure_type}] {c.company_name}: {c.evidence}")

        all_candidates = disc_candidates + fin_candidates + managed_candidates
        print(f"\n총 {len(all_candidates)}개 후보 발견")

    if args.label:
        await labeler.create_labels_table()

        disc_candidates = await labeler.scan_disclosures_for_failures()
        fin_candidates = await labeler.scan_financial_failures()
        managed_candidates = await labeler.scan_managed_stocks()

        all_candidates = disc_candidates + fin_candidates + managed_candidates
        await labeler.save_labels(all_candidates)

    if args.report:
        report = await labeler.get_label_report()
        labeler.print_report(report)


if __name__ == '__main__':
    asyncio.run(main())
