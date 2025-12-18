"""
배치 작업 스케줄러

자동화된 데이터 업데이트 및 분석 작업
"""
import asyncio
import logging
from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select, func, text

from app.database import AsyncSessionLocal
from app.models import Company
from app.services.risk_detection import RiskDetectionEngine
from app.services.financial_metrics import FinancialMetricsCalculator
from app.config import settings
from neo4j import AsyncGraphDatabase

logger = logging.getLogger(__name__)

# 스케줄러 인스턴스
scheduler = AsyncIOScheduler()


async def daily_risk_analysis():
    """
    일일 위험도 재계산 작업

    - 매일 00:00 실행
    - CB 발행 회사 대상으로 위험도 분석
    - 결과를 로그에 기록 (향후 DB 저장 가능)
    """
    logger.info("=" * 70)
    logger.info("일일 위험도 분석 시작")
    logger.info(f"실행 시각: {datetime.now().isoformat()}")
    logger.info("=" * 70)

    try:
        # Neo4j driver
        driver = AsyncGraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password)
        )

        async with AsyncSessionLocal() as db:
            # CB 발행 회사 조회
            result = await db.execute(text("""
                SELECT DISTINCT c.id, c.name
                FROM companies c
                JOIN convertible_bonds cb ON c.id = cb.company_id
                ORDER BY c.name
            """))
            companies = result.all()

            logger.info(f"분석 대상: {len(companies)}개 회사")

            # 위험도 분석
            engine = RiskDetectionEngine(driver)
            high_risk_companies = []
            analysis_results = []

            for i, company in enumerate(companies, 1):
                company_id = str(company.id)
                company_name = company.name

                try:
                    analysis = await engine.analyze_company_risk(db, company_id)

                    result_data = {
                        "company_id": company_id,
                        "company_name": company_name,
                        "risk_score": analysis["risk_score"],
                        "risk_level": analysis["overall_risk_level"]
                    }
                    analysis_results.append(result_data)

                    # 고위험 회사 별도 기록
                    if analysis["overall_risk_level"] in ["high", "critical"]:
                        high_risk_companies.append(result_data)

                    if i % 100 == 0:
                        logger.info(f"진행률: {i}/{len(companies)} ({i/len(companies)*100:.1f}%)")

                except Exception as e:
                    logger.error(f"분석 실패 - {company_name}: {e}")

        await driver.close()

        # 결과 요약
        logger.info("")
        logger.info("=" * 70)
        logger.info("분석 완료")
        logger.info("=" * 70)
        logger.info(f"전체 분석: {len(analysis_results)}개 회사")
        logger.info(f"고위험 회사: {len(high_risk_companies)}개")

        # 고위험 회사 상위 10개 출력
        if high_risk_companies:
            high_risk_companies.sort(key=lambda x: x["risk_score"], reverse=True)
            logger.info("")
            logger.info("고위험 회사 TOP 10:")
            for i, company in enumerate(high_risk_companies[:10], 1):
                logger.info(f"  {i}. {company['company_name']}: {company['risk_score']:.1f}점 ({company['risk_level']})")

        logger.info("=" * 70)

        # 향후: 결과를 DB에 저장하거나 알림 발송
        # await save_risk_analysis_results(analysis_results)
        # await send_high_risk_alerts(high_risk_companies)

    except Exception as e:
        logger.error(f"일일 위험도 분석 실패: {e}", exc_info=True)


async def daily_financial_update():
    """
    일일 재무지표 업데이트 작업

    - 매일 01:00 실행
    - 재무제표가 있는 회사 대상으로 지표 재계산
    - 새로운 분기보고서 확인 (향후 구현)
    """
    logger.info("=" * 70)
    logger.info("일일 재무지표 업데이트 시작")
    logger.info(f"실행 시각: {datetime.now().isoformat()}")
    logger.info("=" * 70)

    try:
        async with AsyncSessionLocal() as db:
            # 재무제표가 있는 회사 조회
            result = await db.execute(text("""
                SELECT DISTINCT c.id, c.name
                FROM companies c
                JOIN financial_statements fs ON c.id = fs.company_id
                ORDER BY c.name
            """))
            companies = result.all()

            logger.info(f"업데이트 대상: {len(companies)}개 회사")

            # 재무지표 계산
            calculator = FinancialMetricsCalculator()
            updated_count = 0
            failed_count = 0

            for i, company in enumerate(companies, 1):
                company_id = str(company.id)
                company_name = company.name

                try:
                    # 재무지표 계산
                    metrics = await calculator.get_company_metrics(db, company_id)

                    # 건전성 분석
                    health = await calculator.analyze_company_health(db, company_id)

                    updated_count += 1

                    if i % 100 == 0:
                        logger.info(f"진행률: {i}/{len(companies)} ({i/len(companies)*100:.1f}%)")

                except Exception as e:
                    logger.error(f"업데이트 실패 - {company_name}: {e}")
                    failed_count += 1

        # 결과 요약
        logger.info("")
        logger.info("=" * 70)
        logger.info("업데이트 완료")
        logger.info("=" * 70)
        logger.info(f"성공: {updated_count}개 회사")
        logger.info(f"실패: {failed_count}개 회사")
        logger.info("=" * 70)

        # 향후: 최신 분기보고서 수집
        # await collect_latest_quarterly_reports()

    except Exception as e:
        logger.error(f"일일 재무지표 업데이트 실패: {e}", exc_info=True)


async def weekly_data_collection():
    """
    주간 데이터 수집 작업

    - 매주 월요일 02:00 실행
    - 최신 CB 공시 수집
    - 신규 회사 정보 업데이트
    """
    logger.info("=" * 70)
    logger.info("주간 데이터 수집 시작")
    logger.info(f"실행 시각: {datetime.now().isoformat()}")
    logger.info("=" * 70)

    try:
        # 향후 구현: 최신 CB 공시 수집
        # await collect_recent_cb_disclosures()

        # 향후 구현: 신규 회사 정보 업데이트
        # await update_company_info()

        logger.info("주간 데이터 수집 완료")
        logger.info("=" * 70)

    except Exception as e:
        logger.error(f"주간 데이터 수집 실패: {e}", exc_info=True)


async def monthly_cleanup():
    """
    월간 정리 작업

    - 매월 1일 03:00 실행
    - 오래된 로그 정리
    - 임시 파일 정리
    - DB 최적화
    """
    logger.info("=" * 70)
    logger.info("월간 정리 작업 시작")
    logger.info(f"실행 시각: {datetime.now().isoformat()}")
    logger.info("=" * 70)

    try:
        # 향후 구현: 로그 정리, 임시 파일 정리, DB 최적화
        logger.info("월간 정리 작업 완료")
        logger.info("=" * 70)

    except Exception as e:
        logger.error(f"월간 정리 작업 실패: {e}", exc_info=True)


def setup_scheduler():
    """
    스케줄러 설정 및 작업 등록
    """
    # 일일 위험도 분석 - 매일 00:00
    scheduler.add_job(
        daily_risk_analysis,
        CronTrigger(hour=0, minute=0),
        id='daily_risk_analysis',
        name='일일 위험도 분석',
        replace_existing=True
    )
    logger.info("스케줄 등록: 일일 위험도 분석 (매일 00:00)")

    # 일일 재무지표 업데이트 - 매일 01:00
    scheduler.add_job(
        daily_financial_update,
        CronTrigger(hour=1, minute=0),
        id='daily_financial_update',
        name='일일 재무지표 업데이트',
        replace_existing=True
    )
    logger.info("스케줄 등록: 일일 재무지표 업데이트 (매일 01:00)")

    # 주간 데이터 수집 - 매주 월요일 02:00
    scheduler.add_job(
        weekly_data_collection,
        CronTrigger(day_of_week='mon', hour=2, minute=0),
        id='weekly_data_collection',
        name='주간 데이터 수집',
        replace_existing=True
    )
    logger.info("스케줄 등록: 주간 데이터 수집 (매주 월요일 02:00)")

    # 월간 정리 작업 - 매월 1일 03:00
    scheduler.add_job(
        monthly_cleanup,
        CronTrigger(day=1, hour=3, minute=0),
        id='monthly_cleanup',
        name='월간 정리 작업',
        replace_existing=True
    )
    logger.info("스케줄 등록: 월간 정리 작업 (매월 1일 03:00)")


def start_scheduler():
    """스케줄러 시작"""
    setup_scheduler()
    scheduler.start()
    logger.info("배치 스케줄러 시작됨")


def stop_scheduler():
    """스케줄러 종료"""
    scheduler.shutdown()
    logger.info("배치 스케줄러 종료됨")


async def run_job_now(job_name: str):
    """
    특정 작업을 즉시 실행 (테스트/수동 실행용)

    Args:
        job_name: 작업 이름 (daily_risk_analysis, daily_financial_update 등)
    """
    jobs = {
        'daily_risk_analysis': daily_risk_analysis,
        'daily_financial_update': daily_financial_update,
        'weekly_data_collection': weekly_data_collection,
        'monthly_cleanup': monthly_cleanup
    }

    if job_name not in jobs:
        logger.error(f"알 수 없는 작업: {job_name}")
        logger.info(f"사용 가능한 작업: {', '.join(jobs.keys())}")
        return

    logger.info(f"수동 실행: {job_name}")
    await jobs[job_name]()
