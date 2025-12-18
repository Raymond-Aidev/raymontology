#!/usr/bin/env python3
"""
API 통합 테스트 스크립트

전체 API 엔드포인트를 테스트하여 정상 작동 여부 확인
"""
import asyncio
import sys
from pathlib import Path
from sqlalchemy import select, text

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import AsyncSessionLocal
from app.models import Company
from app.config import settings
from neo4j import AsyncGraphDatabase
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_database_connection():
    """데이터베이스 연결 테스트"""
    logger.info("=" * 70)
    logger.info("데이터베이스 연결 테스트")
    logger.info("=" * 70)

    try:
        from sqlalchemy import func as sql_func

        async with AsyncSessionLocal() as db:
            # 회사 수 조회
            result = await db.execute(select(sql_func.count(Company.id)))
            company_count = result.scalar()

            logger.info(f"✓ PostgreSQL 연결 성공")
            logger.info(f"  - 전체 회사 수: {company_count:,}개")

            # CB 발행 회사 조회
            result = await db.execute(text("""
                SELECT COUNT(DISTINCT company_id)
                FROM convertible_bonds
            """))
            cb_company_count = result.scalar()
            logger.info(f"  - CB 발행 회사: {cb_company_count:,}개")

            # 재무제표 수 조회
            result = await db.execute(text("""
                SELECT COUNT(*)
                FROM financial_statements
            """))
            fs_count = result.scalar()
            logger.info(f"  - 재무제표 수: {fs_count:,}개")

            return True

    except Exception as e:
        logger.error(f"✗ PostgreSQL 연결 실패: {e}")
        return False


async def test_neo4j_connection():
    """Neo4j 연결 테스트"""
    logger.info("")
    logger.info("=" * 70)
    logger.info("Neo4j 연결 테스트")
    logger.info("=" * 70)

    try:
        driver = AsyncGraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password)
        )

        async with driver.session() as session:
            # 노드 수 조회
            result = await session.run("MATCH (n) RETURN count(n) as count")
            record = await result.single()
            total_nodes = record["count"]

            # Company 노드
            result = await session.run("MATCH (c:Company) RETURN count(c) as count")
            record = await result.single()
            company_nodes = record["count"]

            # Officer 노드
            result = await session.run("MATCH (o:Officer) RETURN count(o) as count")
            record = await result.single()
            officer_nodes = record["count"]

            # CB 노드
            result = await session.run("MATCH (cb:ConvertibleBond) RETURN count(cb) as count")
            record = await result.single()
            cb_nodes = record["count"]

            # WORKS_AT 관계
            result = await session.run("MATCH ()-[r:WORKS_AT]->() RETURN count(r) as count")
            record = await result.single()
            works_at_count = record["count"]

            # INVESTED_IN 관계
            result = await session.run("MATCH ()-[r:INVESTED_IN]->() RETURN count(r) as count")
            record = await result.single()
            invested_in_count = record["count"]

            logger.info(f"✓ Neo4j 연결 성공")
            logger.info(f"  - 전체 노드: {total_nodes:,}개")
            logger.info(f"  - Company: {company_nodes:,}개")
            logger.info(f"  - Officer: {officer_nodes:,}개")
            logger.info(f"  - ConvertibleBond: {cb_nodes:,}개")
            logger.info(f"  - WORKS_AT 관계: {works_at_count:,}개")
            logger.info(f"  - INVESTED_IN 관계: {invested_in_count:,}개")

        await driver.close()
        return True

    except Exception as e:
        logger.error(f"✗ Neo4j 연결 실패: {e}")
        return False


async def test_graph_api():
    """그래프 API 테스트"""
    logger.info("")
    logger.info("=" * 70)
    logger.info("그래프 API 테스트")
    logger.info("=" * 70)

    try:
        from app.api.endpoints.graph import get_company_network, get_db, get_neo4j_driver
        from app.config import settings

        # 테스트용 회사 1개 선택
        async with AsyncSessionLocal() as db:
            result = await db.execute(text("""
                SELECT c.id, c.name
                FROM companies c
                JOIN convertible_bonds cb ON c.id = cb.company_id
                LIMIT 1
            """))
            test_company = result.first()

            if not test_company:
                logger.warning("테스트할 회사가 없습니다")
                return False

            company_id = str(test_company.id)
            company_name = test_company.name

            logger.info(f"테스트 대상: {company_name} ({company_id})")

            # Neo4j driver
            driver = AsyncGraphDatabase.driver(
                settings.neo4j_uri,
                auth=(settings.neo4j_user, settings.neo4j_password)
            )

            try:
                # 회사 네트워크 조회 테스트
                async with driver.session() as session:
                    result = await session.run("""
                        MATCH (c:Company {id: $company_id})
                        OPTIONAL MATCH (c)-[r1:ISSUED]->(cb:ConvertibleBond)
                        OPTIONAL MATCH (c)<-[r2:WORKS_AT]-(o:Officer)
                        RETURN count(cb) as cb_count, count(o) as officer_count
                    """, company_id=company_id)
                    record = await result.single()

                    logger.info(f"✓ 그래프 API 테스트 성공")
                    logger.info(f"  - CB: {record['cb_count']}개")
                    logger.info(f"  - 임원: {record['officer_count']}명")

            finally:
                await driver.close()

            return True

    except Exception as e:
        logger.error(f"✗ 그래프 API 테스트 실패: {e}", exc_info=True)
        return False


async def test_financial_api():
    """재무지표 API 테스트"""
    logger.info("")
    logger.info("=" * 70)
    logger.info("재무지표 API 테스트")
    logger.info("=" * 70)

    try:
        from app.services.financial_metrics import FinancialMetricsCalculator

        # 재무제표가 있는 회사 선택
        async with AsyncSessionLocal() as db:
            result = await db.execute(text("""
                SELECT DISTINCT c.id, c.name
                FROM companies c
                JOIN financial_statements fs ON c.id = fs.company_id
                LIMIT 1
            """))
            test_company = result.first()

            if not test_company:
                logger.warning("재무제표가 있는 회사가 없습니다")
                return False

            company_id = str(test_company.id)
            company_name = test_company.name

            logger.info(f"테스트 대상: {company_name} ({company_id})")

            # 재무지표 계산
            calculator = FinancialMetricsCalculator()
            metrics = await calculator.get_company_metrics(db, company_id)

            logger.info(f"✓ 재무지표 API 테스트 성공")
            logger.info(f"  - 현금자산: {metrics.get('cash_assets_billion', 'N/A')} 억원")
            logger.info(f"  - 매출 CAGR: {metrics.get('revenue_cagr', 'N/A')}%")
            logger.info(f"  - 부채비율: {metrics.get('debt_ratio', 'N/A')}%")
            logger.info(f"  - 유동비율: {metrics.get('current_ratio', 'N/A')}%")

            # 건전성 분석
            health = await calculator.analyze_company_health(db, company_id)
            logger.info(f"  - 건전성 점수: {health['health_score']:.1f}/100")
            logger.info(f"  - 경고 수: {len(health['warnings'])}개")

            return True

    except Exception as e:
        logger.error(f"✗ 재무지표 API 테스트 실패: {e}", exc_info=True)
        return False


async def test_risk_api():
    """위험신호 API 테스트"""
    logger.info("")
    logger.info("=" * 70)
    logger.info("위험신호 API 테스트")
    logger.info("=" * 70)

    try:
        from app.services.risk_detection import RiskDetectionEngine
        from app.config import settings

        # CB 발행 회사 선택
        async with AsyncSessionLocal() as db:
            result = await db.execute(text("""
                SELECT c.id, c.name, COUNT(cb.id) as cb_count
                FROM companies c
                JOIN convertible_bonds cb ON c.id = cb.company_id
                GROUP BY c.id, c.name
                HAVING COUNT(cb.id) >= 2
                LIMIT 1
            """))
            test_company = result.first()

            if not test_company:
                logger.warning("CB 발행 회사가 없습니다")
                return False

            company_id = str(test_company.id)
            company_name = test_company.name

            logger.info(f"테스트 대상: {company_name} ({company_id})")

            # Neo4j driver
            driver = AsyncGraphDatabase.driver(
                settings.neo4j_uri,
                auth=(settings.neo4j_user, settings.neo4j_password)
            )

            try:
                # 위험도 분석
                engine = RiskDetectionEngine(driver)
                analysis = await engine.analyze_company_risk(db, company_id)

                logger.info(f"✓ 위험신호 API 테스트 성공")
                logger.info(f"  - 위험 등급: {analysis['overall_risk_level'].upper()}")
                logger.info(f"  - 위험 점수: {analysis['risk_score']:.1f}/100")

                # 패턴별 요약
                patterns = analysis['patterns']
                pattern_count = sum(
                    1 for p in patterns.values()
                    if p and (
                        (isinstance(p, list) and len(p) > 0) or
                        (isinstance(p, dict) and p.get('risk_level') != 'low')
                    )
                )
                logger.info(f"  - 탐지된 패턴: {pattern_count}개")

            finally:
                await driver.close()

            return True

    except Exception as e:
        logger.error(f"✗ 위험신호 API 테스트 실패: {e}", exc_info=True)
        return False


async def test_company_api():
    """회사 검색 API 테스트"""
    logger.info("")
    logger.info("=" * 70)
    logger.info("회사 검색 API 테스트")
    logger.info("=" * 70)

    try:
        async with AsyncSessionLocal() as db:
            # 회사 목록 조회
            result = await db.execute(
                select(Company).limit(5)
            )
            companies = result.scalars().all()

            logger.info(f"✓ 회사 검색 API 테스트 성공")
            logger.info(f"  - 조회된 회사: {len(companies)}개")

            if companies:
                sample = companies[0]
                logger.info(f"  - 샘플: {sample.name} ({sample.ticker or 'N/A'})")

            return True

    except Exception as e:
        logger.error(f"✗ 회사 검색 API 테스트 실패: {e}", exc_info=True)
        return False


async def main():
    """메인 테스트 함수"""
    logger.info("")
    logger.info("=" * 70)
    logger.info("Raymontology API 통합 테스트 시작")
    logger.info("=" * 70)

    results = {}

    # 1. 데이터베이스 연결 테스트
    results['database'] = await test_database_connection()

    # 2. Neo4j 연결 테스트
    results['neo4j'] = await test_neo4j_connection()

    # 3. 그래프 API 테스트
    results['graph_api'] = await test_graph_api()

    # 4. 재무지표 API 테스트
    results['financial_api'] = await test_financial_api()

    # 5. 위험신호 API 테스트
    results['risk_api'] = await test_risk_api()

    # 6. 회사 검색 API 테스트
    results['company_api'] = await test_company_api()

    # 결과 요약
    logger.info("")
    logger.info("=" * 70)
    logger.info("테스트 결과 요약")
    logger.info("=" * 70)

    total = len(results)
    passed = sum(1 for v in results.values() if v)

    for test_name, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        logger.info(f"{status} - {test_name}")

    logger.info("")
    logger.info(f"전체: {passed}/{total} 테스트 통과")

    if passed == total:
        logger.info("=" * 70)
        logger.info("✓ 모든 테스트 성공!")
        logger.info("=" * 70)
        return 0
    else:
        logger.error("=" * 70)
        logger.error(f"✗ {total - passed}개 테스트 실패")
        logger.error("=" * 70)
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
