#!/usr/bin/env python3
"""
PRD v3.2.1 기준 리스크 점수 계산 및 저장

- RaymondsRisk (50%): 인적 리스크 (25%) + CB 리스크 (25%)
- 재무건전성 (50%)
"""
import asyncio
import asyncpg
import json
import logging
import os
from datetime import date, datetime, timedelta
import uuid

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 환경변수에서 DB URL 읽기 (없으면 로컬 기본값)
DB_URL = os.environ.get('DATABASE_URL', 'postgresql://postgres:dev_password@localhost:5432/raymontology_dev')
# asyncpg는 postgresql:// 스킴만 지원 (postgresql+asyncpg:// 변환)
if DB_URL.startswith('postgresql+asyncpg://'):
    DB_URL = DB_URL.replace('postgresql+asyncpg://', 'postgresql://')

# 분석 기간 (PRD 정의)
ANALYSIS_YEAR = 2025
ANALYSIS_QUARTER = 2
BASE_PERIOD_START = date(2024, 4, 1)  # 최근 1년 시작
BASE_PERIOD_END = date(2025, 6, 30)   # 최근 1년 끝
HISTORY_START = date(2022, 1, 1)      # 전체 3.5년 시작


def calculate_human_risk(exec_count: int, total_other_companies: int) -> dict:
    """인적 리스크 점수 계산 (0-100점) - PRD 6.3"""

    # Step 1: 임원 수 점수
    if exec_count <= 10:
        exec_score = 1
    elif exec_count <= 20:
        exec_score = 3
    elif exec_count <= 25:
        exec_score = 6
    elif exec_count <= 29:
        exec_score = 10
    else:
        exec_score = 15

    # Step 2: 타사 재직 배수
    if total_other_companies <= 5:
        multiplier = 1
    elif total_other_companies <= 10:
        multiplier = 2
    elif total_other_companies <= 15:
        multiplier = 3
    else:
        multiplier = 4

    # Step 3: 원점수
    raw_score = exec_score * multiplier

    # Step 4: 정규화 (0-100)
    if raw_score < 30:
        normalized = (raw_score / 30) * 49
        level = 'LOW'
    elif raw_score <= 50:
        normalized = 50 + ((raw_score - 30) / 20) * 19
        level = 'MEDIUM'
    else:
        normalized = 70 + ((raw_score - 50) / 10) * 30
        level = 'HIGH'

    return {
        "score": round(min(normalized, 100), 1),
        "level": level,
        "raw_score": raw_score,
        "exec_count": exec_count,
        "total_other_companies": total_other_companies
    }


def calculate_subscriber_quality_score(subscriber_count: int) -> int:
    """인수대상자 수량 기반 품질 점수 (0-30점)

    CB 인수에 참여한 대상자(개인+법인) 수가 많을수록 위험 신호.
    - 다수 참여자 = CB 인수 네트워크 광범위 = 투자자 품질 리스크 증가

    점수 기준 (2026-02 개편):
    - 50명 이상: 30점 (초대규모 네트워크)
    - 20-49명: 25점 (대규모)
    - 10-19명: 20점 (중대규모)
    - 5-9명: 15점 (중규모)
    - 2-4명: 10점 (소규모)
    - 1명: 5점 (단독)
    - 0명: 0점 (CB 없음)
    """
    if subscriber_count >= 50:
        return 30  # 초대규모 네트워크
    elif subscriber_count >= 20:
        return 25  # 대규모
    elif subscriber_count >= 10:
        return 20  # 중대규모
    elif subscriber_count >= 5:
        return 15  # 중규모
    elif subscriber_count >= 2:
        return 10  # 소규모
    elif subscriber_count == 1:
        return 5   # 단독
    else:
        return 0   # CB 없음


def calculate_cb_risk(cb_count: int, issue_amount_billion: float,
                      subscriber_count: int, loss_company_count: int) -> dict:
    """CB 리스크 점수 계산 (0-100점) - PRD 6.4

    Components:
    - 발행 빈도 (25점): CB 발행 횟수
    - 발행 규모 (25점): 총 발행금액
    - 투자자 품질 (30점): 인수대상자 수량 (2026-02 개편)
    - 적자기업 연결 (20점): 관련 적자기업 수
    """

    # CB 없음 = 리스크 없음
    if cb_count == 0 and issue_amount_billion == 0:
        return {
            "score": 0, "level": "LOW", "cb_count": 0, "issue_amount": 0,
            "frequency_score": 0, "amount_score": 0, "quality_score": 0, "loss_score": 0,
            "subscriber_count": 0
        }

    # Component 1: 발행 빈도 (25점)
    if cb_count >= 4:
        frequency_score = 25
    elif cb_count == 3:
        frequency_score = 20
    elif cb_count == 2:
        frequency_score = 15
    elif cb_count == 1:
        frequency_score = 10
    else:
        frequency_score = 0

    # Component 2: 발행 규모 (25점)
    if issue_amount_billion >= 200:
        amount_score = 25
    elif issue_amount_billion >= 100:
        amount_score = 20
    elif issue_amount_billion >= 50:
        amount_score = 15
    elif issue_amount_billion >= 20:
        amount_score = 10
    elif issue_amount_billion >= 1:
        amount_score = 5
    else:
        amount_score = 0

    # Component 3: 투자자 품질 (30점) - 인수대상자 수량 기반 (2026-02 개편)
    quality_score = calculate_subscriber_quality_score(subscriber_count)

    # Component 4: 적자기업 연결 (20점)
    if loss_company_count >= 10:
        loss_score = 20
    elif loss_company_count >= 5:
        loss_score = 15
    elif loss_company_count >= 3:
        loss_score = 10
    else:
        loss_score = loss_company_count * 2

    total = frequency_score + amount_score + quality_score + loss_score

    if total >= 70:
        level = 'HIGH'
    elif total >= 40:
        level = 'MEDIUM'
    else:
        level = 'LOW'

    return {
        "score": total,
        "level": level,
        "cb_count": cb_count,
        "issue_amount": issue_amount_billion,
        "frequency_score": frequency_score,
        "amount_score": amount_score,
        "quality_score": quality_score,
        "loss_score": loss_score,
        "subscriber_count": subscriber_count
    }


def calculate_financial_health(fs_data: dict) -> dict:
    """재무건전성 점수 계산 (0-100점)"""
    if not fs_data:
        return {"score": 50, "level": "MEDIUM", "confidence": 0}

    score = 0
    components = {}

    # 부채비율 (25점)
    if fs_data.get('total_equity') and fs_data['total_equity'] > 0:
        debt_ratio = (fs_data.get('total_liabilities', 0) / fs_data['total_equity']) * 100
        if debt_ratio <= 100:
            debt_score = 25
        elif debt_ratio <= 200:
            debt_score = 20
        elif debt_ratio <= 300:
            debt_score = 15
        elif debt_ratio <= 500:
            debt_score = 10
        else:
            debt_score = 0
        score += debt_score
        components['debt_ratio'] = debt_ratio
        components['debt_score'] = debt_score

    # 영업이익 (25점)
    if fs_data.get('operating_profit') is not None:
        if fs_data['operating_profit'] > 0:
            op_score = 25
        elif fs_data['operating_profit'] == 0:
            op_score = 15
        else:
            op_score = 0
        score += op_score
        components['operating_profit'] = fs_data['operating_profit']
        components['op_score'] = op_score

    # 순이익 (25점)
    if fs_data.get('net_income') is not None:
        if fs_data['net_income'] > 0:
            ni_score = 25
        elif fs_data['net_income'] == 0:
            ni_score = 15
        else:
            ni_score = 0
        score += ni_score
        components['net_income'] = fs_data['net_income']
        components['ni_score'] = ni_score

    # 자산 규모 (25점)
    if fs_data.get('total_assets'):
        assets_billion = fs_data['total_assets'] / 1_000_000_000
        if assets_billion >= 1000:
            asset_score = 25
        elif assets_billion >= 100:
            asset_score = 20
        elif assets_billion >= 10:
            asset_score = 15
        else:
            asset_score = 10
        score += asset_score
        components['total_assets_billion'] = assets_billion
        components['asset_score'] = asset_score

    # 100점 만점으로 역산 (리스크 점수이므로 높을수록 위험)
    risk_score = 100 - score

    if risk_score <= 30:
        level = 'LOW'
    elif risk_score <= 60:
        level = 'MEDIUM'
    else:
        level = 'HIGH'

    return {
        "score": risk_score,
        "level": level,
        "components": components,
        "confidence": 1.0 if len(components) >= 3 else 0.5
    }


def get_investment_grade(score: float) -> str:
    """투자등급 산정 - 4등급 체계 (2026-01-28 개편)

    등급 체계:
    - LOW_RISK (저위험): 0-19점 - 안정적, 투자 적격
    - RISK (위험): 20-34점 - 모니터링 필요
    - MEDIUM_RISK (중위험): 35-49점 - 주의, 투자 신중
    - HIGH_RISK (고위험): 50점 이상 - 경고, 투자 회피
    """
    if score < 20:
        return 'LOW_RISK'      # 저위험
    elif score < 35:
        return 'RISK'          # 위험
    elif score < 50:
        return 'MEDIUM_RISK'   # 중위험
    else:
        return 'HIGH_RISK'     # 고위험


def get_risk_level(score: float) -> str:
    """리스크 레벨 산정"""
    if score < 20:
        return 'VERY_LOW'
    elif score < 40:
        return 'LOW'
    elif score < 60:
        return 'MEDIUM'
    elif score < 80:
        return 'HIGH'
    else:
        return 'CRITICAL'


async def calculate_risk_scores():
    """모든 회사의 리스크 점수 계산"""
    conn = await asyncpg.connect(DB_URL)

    try:
        # 시작 전 카운트
        before_count = await conn.fetchval("SELECT COUNT(*) FROM risk_scores")
        logger.info(f"작업 전 risk_scores: {before_count}건")

        # 모든 회사 가져오기
        companies = await conn.fetch("""
            SELECT id, corp_code, name FROM companies
            WHERE corp_code IS NOT NULL
        """)
        logger.info(f"대상 회사: {len(companies)}개")

        stats = {
            'processed': 0,
            'saved': 0,
            'errors': 0
        }

        batch_data = []
        total = len(companies)

        for idx, company in enumerate(companies):
            if idx % 100 == 0:
                logger.info(f"진행 중: {idx}/{total} ({idx*100//total}%)")
            company_id = company['id']
            corp_code = company['corp_code']

            try:
                # 1. 인적 리스크 데이터 수집
                exec_count = await conn.fetchval("""
                    SELECT COUNT(DISTINCT o.id)
                    FROM officers o
                    JOIN officer_positions op ON o.id = op.officer_id
                    WHERE op.company_id = $1
                    AND (op.term_end_date IS NULL OR op.term_end_date >= $2)
                """, company_id, BASE_PERIOD_START)
                exec_count = exec_count or 0

                total_other_companies = await conn.fetchval("""
                    SELECT COUNT(DISTINCT op2.company_id)
                    FROM officers o
                    JOIN officer_positions op ON o.id = op.officer_id
                    JOIN officer_positions op2 ON o.id = op2.officer_id
                    WHERE op.company_id = $1
                    AND op2.company_id != $1
                    AND (op.term_end_date IS NULL OR op.term_end_date >= $2)
                """, company_id, BASE_PERIOD_START)
                total_other_companies = total_other_companies or 0

                human_risk = calculate_human_risk(exec_count, total_other_companies)

                # 2. CB 리스크 데이터 수집
                cb_data = await conn.fetchrow("""
                    SELECT COUNT(*) as cb_count,
                           COALESCE(SUM(issue_amount), 0) / 100000000 as total_billion
                    FROM convertible_bonds
                    WHERE company_id = $1
                    AND (issue_date >= $2 OR issue_date IS NULL)
                """, company_id, BASE_PERIOD_START)

                cb_count = cb_data['cb_count'] if cb_data else 0
                total_billion = float(cb_data['total_billion']) if cb_data else 0

                subscriber_count = 0
                loss_company_count = 0

                if cb_count > 0:
                    # 인수대상자 수량 조회 (개인 + 법인 모두 포함)
                    subscriber_count = await conn.fetchval("""
                        SELECT COUNT(DISTINCT subscriber_name)
                        FROM cb_subscribers cs
                        JOIN convertible_bonds cb ON cs.cb_id = cb.id
                        WHERE cb.company_id = $1
                    """, company_id)
                    subscriber_count = subscriber_count or 0

                cb_risk = calculate_cb_risk(cb_count, total_billion, subscriber_count, loss_company_count)

                # 3. 재무건전성 데이터 수집
                fs_data = await conn.fetchrow("""
                    SELECT total_assets, total_liabilities, total_equity,
                           revenue, operating_profit, net_income
                    FROM financial_statements
                    WHERE company_id = $1
                    ORDER BY fiscal_year DESC, quarter DESC NULLS LAST
                    LIMIT 1
                """, company_id)

                financial_health = calculate_financial_health(dict(fs_data) if fs_data else {})

                # 4. 종합 점수 계산 (2026-01-28 비중 조정: RaymondsRisk 40%, 재무건전성 60%)
                raymondsrisk_score = human_risk['score'] * 0.5 + cb_risk['score'] * 0.5
                total_score = raymondsrisk_score * 0.4 + financial_health['score'] * 0.6

                risk_level = get_risk_level(total_score)
                investment_grade = get_investment_grade(total_score)

                confidence = 1.0
                if exec_count == 0:
                    confidence *= 0.7
                if not fs_data:
                    confidence *= 0.6

                score_breakdown = {
                    'human_risk': human_risk,
                    'cb_risk': cb_risk,
                    'financial_health': financial_health
                }

                batch_data.append((
                    uuid.uuid4(),
                    company_id,
                    ANALYSIS_YEAR,
                    ANALYSIS_QUARTER,
                    round(total_score, 2),
                    risk_level,
                    investment_grade,
                    round(confidence, 4),
                    round(raymondsrisk_score, 2),
                    round(human_risk['score'], 2),
                    round(cb_risk['score'], 2),
                    round(financial_health['score'], 2),
                    json.dumps(score_breakdown)
                ))

                stats['processed'] += 1

                if len(batch_data) >= 500:
                    saved = await insert_batch(conn, batch_data)
                    stats['saved'] += saved
                    logger.info(f"  {stats['saved']}건 저장 (처리: {stats['processed']})")
                    batch_data = []

            except Exception as e:
                stats['errors'] += 1
                if stats['errors'] <= 5:
                    logger.error(f"오류 {corp_code}: {e}")

        if batch_data:
            saved = await insert_batch(conn, batch_data)
            stats['saved'] += saved

        after_count = await conn.fetchval("SELECT COUNT(*) FROM risk_scores")

        logger.info("\n" + "=" * 60)
        logger.info("리스크 점수 계산 완료")
        logger.info("=" * 60)
        logger.info(f"처리: {stats['processed']:,}건")
        logger.info(f"저장: {stats['saved']:,}건")
        logger.info(f"오류: {stats['errors']:,}건")
        logger.info("-" * 60)
        logger.info(f"risk_scores: {before_count}건 → {after_count}건 (+{after_count - before_count}건)")
        logger.info("=" * 60)

        grade_dist = await conn.fetch("""
            SELECT investment_grade, COUNT(*) as cnt
            FROM risk_scores
            GROUP BY investment_grade
            ORDER BY investment_grade
        """)
        logger.info("\n투자등급 분포:")
        for row in grade_dist:
            logger.info(f"  {row['investment_grade']}: {row['cnt']}건")

    finally:
        await conn.close()


async def insert_batch(conn, batch_data):
    """배치 삽입"""
    saved = 0
    for row in batch_data:
        try:
            await conn.execute("""
                INSERT INTO risk_scores (
                    id, company_id, analysis_year, analysis_quarter,
                    total_score, risk_level, investment_grade, confidence,
                    raymondsrisk_score, human_risk_score, cb_risk_score,
                    financial_health_score, score_breakdown
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
                ON CONFLICT (company_id, analysis_year, analysis_quarter) DO UPDATE SET
                    total_score = EXCLUDED.total_score,
                    risk_level = EXCLUDED.risk_level,
                    investment_grade = EXCLUDED.investment_grade,
                    confidence = EXCLUDED.confidence,
                    raymondsrisk_score = EXCLUDED.raymondsrisk_score,
                    human_risk_score = EXCLUDED.human_risk_score,
                    cb_risk_score = EXCLUDED.cb_risk_score,
                    financial_health_score = EXCLUDED.financial_health_score,
                    score_breakdown = EXCLUDED.score_breakdown,
                    updated_at = NOW()
            """, *row)
            saved += 1
        except Exception as e:
            logger.error(f"삽입 오류: {e}")
    return saved


if __name__ == "__main__":
    asyncio.run(calculate_risk_scores())
