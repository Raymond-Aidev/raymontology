#!/usr/bin/env python3
"""
코스닥/코스피 상장 기업 데이터 저장 상태 확인
- 10개 주요 테이블 검증
- 필수 필드 존재 여부 확인
- 데이터 품질 평가
"""
import asyncio
import asyncpg
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


async def main():
    conn = await asyncpg.connect('postgresql://postgres:dev_password@postgres:5432/raymontology_dev')

    try:
        logger.info('=' * 100)
        logger.info('코스닥/코스피 상장 기업 데이터 저장 상태 확인')
        logger.info(f'검증 시간: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
        logger.info('=' * 100)

        # 1. companies 테이블
        logger.info('\n[1] COMPANIES (회사)')
        logger.info('-' * 100)

        companies_stats = await conn.fetchrow('''
            SELECT
                COUNT(*) as total_companies,
                COUNT(DISTINCT ticker) as with_ticker,
                COUNT(DISTINCT corp_code) as with_corp_code,
                COUNT(*) FILTER (WHERE ticker IS NOT NULL) as listed_companies,
                COUNT(*) FILTER (WHERE ticker IS NULL) as unlisted_companies,
                COUNT(*) FILTER (WHERE market = 'KOSPI') as kospi_count,
                COUNT(*) FILTER (WHERE market = 'KOSDAQ') as kosdaq_count,
                COUNT(*) FILTER (WHERE market IS NULL) as no_market,
                COUNT(*) FILTER (WHERE market_cap IS NOT NULL) as with_market_cap,
                COUNT(*) FILTER (WHERE revenue IS NOT NULL) as with_revenue,
                COUNT(*) FILTER (WHERE net_income IS NOT NULL) as with_net_income
            FROM companies
        ''')

        total_comp = companies_stats['total_companies']
        logger.info(f'총 회사 수: {total_comp:,}')
        logger.info(f'상장 기업 (ticker 있음): {companies_stats["listed_companies"]:,} ({companies_stats["listed_companies"]/total_comp*100:.1f}%)')
        logger.info(f'비상장 기업 (ticker 없음): {companies_stats["unlisted_companies"]:,} ({companies_stats["unlisted_companies"]/total_comp*100:.1f}%)')
        logger.info(f'\n시장 구분:')
        logger.info(f'  KOSPI: {companies_stats["kospi_count"]:,}')
        logger.info(f'  KOSDAQ: {companies_stats["kosdaq_count"]:,}')
        logger.info(f'  시장구분 없음: {companies_stats["no_market"]:,}')
        logger.info(f'\n재무 데이터:')
        logger.info(f'  시가총액 있음: {companies_stats["with_market_cap"]:,} ({companies_stats["with_market_cap"]/total_comp*100:.1f}%)')
        logger.info(f'  매출 있음: {companies_stats["with_revenue"]:,} ({companies_stats["with_revenue"]/total_comp*100:.1f}%)')
        logger.info(f'  순이익 있음: {companies_stats["with_net_income"]:,} ({companies_stats["with_net_income"]/total_comp*100:.1f}%)')

        # 샘플 데이터
        sample_comp = await conn.fetch('''
            SELECT name, ticker, market, industry
            FROM companies
            WHERE ticker IS NOT NULL
            ORDER BY ticker
            LIMIT 5
        ''')

        logger.info(f'\n상장 기업 샘플:')
        for comp in sample_comp:
            logger.info(f'  - {comp["name"]} (티커: {comp["ticker"]}, 시장: {comp["market"]}, 업종: {comp["industry"]})')

        # 2. officers 테이블
        logger.info('\n[2] OFFICERS (임원)')
        logger.info('-' * 100)

        officers_stats = await conn.fetchrow('''
            SELECT
                COUNT(*) as total_officers,
                COUNT(DISTINCT name) as unique_names,
                COUNT(*) FILTER (WHERE current_company_id IS NOT NULL) as with_company,
                COUNT(*) FILTER (WHERE career_history IS NOT NULL) as with_career,
                COUNT(*) FILTER (WHERE influence_score IS NOT NULL) as with_influence_score,
                COUNT(*) FILTER (WHERE has_conflict_of_interest = TRUE) as with_conflicts,
                AVG(influence_score) as avg_influence_score
            FROM officers
        ''')

        total_off = officers_stats['total_officers']
        logger.info(f'총 임원 수: {total_off:,}')
        logger.info(f'고유 이름: {officers_stats["unique_names"]:,}')
        logger.info(f'소속 회사 있음: {officers_stats["with_company"]:,} ({officers_stats["with_company"]/total_off*100:.1f}%)')
        logger.info(f'경력 정보 있음: {officers_stats["with_career"]:,} ({officers_stats["with_career"]/total_off*100:.1f}%)')
        logger.info(f'영향력 점수 있음: {officers_stats["with_influence_score"]:,} ({officers_stats["with_influence_score"]/total_off*100:.1f}%)')
        logger.info(f'이해상충 플래그: {officers_stats["with_conflicts"]:,}')
        if officers_stats['avg_influence_score']:
            logger.info(f'평균 영향력 점수: {officers_stats["avg_influence_score"]:.2f}')

        # 3. officer_positions 테이블
        logger.info('\n[3] OFFICER_POSITIONS (임원 직책 이력)')
        logger.info('-' * 100)

        positions_stats = await conn.fetchrow('''
            SELECT
                COUNT(*) as total_positions,
                COUNT(DISTINCT officer_id) as unique_officers,
                COUNT(DISTINCT company_id) as unique_companies,
                COUNT(*) FILTER (WHERE is_current = TRUE) as current_positions,
                COUNT(*) FILTER (WHERE term_start_date IS NOT NULL) as with_start_date,
                COUNT(*) FILTER (WHERE source_disclosure_id IS NOT NULL) as with_source
            FROM officer_positions
        ''')

        total_pos = positions_stats['total_positions']
        logger.info(f'총 직책 레코드: {total_pos:,}')
        logger.info(f'고유 임원: {positions_stats["unique_officers"]:,}')
        logger.info(f'고유 회사: {positions_stats["unique_companies"]:,}')
        logger.info(f'현재 직책: {positions_stats["current_positions"]:,} ({positions_stats["current_positions"]/total_pos*100:.1f}%)')
        logger.info(f'시작일 있음: {positions_stats["with_start_date"]:,} ({positions_stats["with_start_date"]/total_pos*100:.1f}%)')
        logger.info(f'출처 추적: {positions_stats["with_source"]:,} ({positions_stats["with_source"]/total_pos*100:.1f}%)')

        # 4. convertible_bonds 테이블
        logger.info('\n[4] CONVERTIBLE_BONDS (전환사채)')
        logger.info('-' * 100)

        cb_stats = await conn.fetchrow('''
            SELECT
                COUNT(*) as total_bonds,
                COUNT(DISTINCT company_id) as unique_companies,
                COUNT(*) FILTER (WHERE issue_date IS NOT NULL) as with_issue_date,
                COUNT(*) FILTER (WHERE maturity_date IS NOT NULL) as with_maturity_date,
                COUNT(*) FILTER (WHERE issue_amount IS NOT NULL) as with_amount,
                COUNT(*) FILTER (WHERE conversion_price IS NOT NULL) as with_conversion_price,
                SUM(issue_amount) as total_amount
            FROM convertible_bonds
        ''')

        total_cb = cb_stats['total_bonds']
        logger.info(f'총 전환사채 수: {total_cb:,}')
        logger.info(f'발행 기업 수: {cb_stats["unique_companies"]:,}')
        logger.info(f'발행일 있음: {cb_stats["with_issue_date"]:,} ({cb_stats["with_issue_date"]/total_cb*100:.1f}%)')
        logger.info(f'만기일 있음: {cb_stats["with_maturity_date"]:,} ({cb_stats["with_maturity_date"]/total_cb*100:.1f}%)')
        logger.info(f'발행금액 있음: {cb_stats["with_amount"]:,} ({cb_stats["with_amount"]/total_cb*100:.1f}%)')
        logger.info(f'전환가액 있음: {cb_stats["with_conversion_price"]:,} ({cb_stats["with_conversion_price"]/total_cb*100:.1f}%)')
        if cb_stats['total_amount']:
            logger.info(f'총 발행금액: {cb_stats["total_amount"]:,.0f} 원')

        # 5. cb_subscribers 테이블
        logger.info('\n[5] CB_SUBSCRIBERS (CB 인수자)')
        logger.info('-' * 100)

        subs_stats = await conn.fetchrow('''
            SELECT
                COUNT(*) as total_subscribers,
                COUNT(DISTINCT subscriber_name) as unique_subscribers,
                COUNT(*) FILTER (WHERE subscriber_type IS NOT NULL) as with_type,
                COUNT(*) FILTER (WHERE is_related_party = 'Y') as related_parties,
                COUNT(*) FILTER (WHERE subscription_amount IS NOT NULL) as with_amount,
                SUM(subscription_amount) as total_subscribed
            FROM cb_subscribers
        ''')

        total_subs = subs_stats['total_subscribers']
        logger.info(f'총 인수자 레코드: {total_subs:,}')

        if total_subs > 0:
            logger.info(f'고유 인수자: {subs_stats["unique_subscribers"]:,}')
            logger.info(f'인수자 유형 있음: {subs_stats["with_type"]:,} ({subs_stats["with_type"]/total_subs*100:.1f}%)')
            logger.info(f'특수관계자: {subs_stats["related_parties"]:,}')
            logger.info(f'인수금액 있음: {subs_stats["with_amount"]:,} ({subs_stats["with_amount"]/total_subs*100:.1f}%)')
            if subs_stats['total_subscribed']:
                logger.info(f'총 인수금액: {subs_stats["total_subscribed"]:,.0f} 원')
        else:
            logger.info('  ✗ CB 인수자 데이터 없음')

        # 6. affiliates 테이블
        logger.info('\n[6] AFFILIATES (계열사)')
        logger.info('-' * 100)

        aff_stats = await conn.fetchrow('''
            SELECT
                COUNT(*) as total_relationships,
                COUNT(DISTINCT parent_company_id) as unique_parents,
                COUNT(DISTINCT affiliate_company_id) as unique_affiliates,
                COUNT(*) FILTER (WHERE ownership_ratio IS NOT NULL) as with_ownership,
                COUNT(*) FILTER (WHERE voting_rights_ratio IS NOT NULL) as with_voting_rights,
                AVG(ownership_ratio) as avg_ownership
            FROM affiliates
        ''')

        total_aff = aff_stats['total_relationships']
        logger.info(f'총 계열사 관계: {total_aff:,}')

        if total_aff > 0:
            logger.info(f'모회사 수: {aff_stats["unique_parents"]:,}')
            logger.info(f'계열사 수: {aff_stats["unique_affiliates"]:,}')
            logger.info(f'지분율 있음: {aff_stats["with_ownership"]:,} ({aff_stats["with_ownership"]/total_aff*100:.1f}%)')
            logger.info(f'의결권 비율 있음: {aff_stats["with_voting_rights"]:,} ({aff_stats["with_voting_rights"]/total_aff*100:.1f}%)')
            if aff_stats['avg_ownership']:
                logger.info(f'평균 지분율: {aff_stats["avg_ownership"]:.2f}%')
        else:
            logger.info('  ✗ 계열사 데이터 없음')

        # 7. financial_statements 테이블
        logger.info('\n[7] FINANCIAL_STATEMENTS (재무제표)')
        logger.info('-' * 100)

        fs_stats = await conn.fetchrow('''
            SELECT
                COUNT(*) as total_statements,
                COUNT(DISTINCT company_id) as unique_companies,
                MIN(fiscal_year) as earliest_year,
                MAX(fiscal_year) as latest_year,
                COUNT(*) FILTER (WHERE total_assets IS NOT NULL) as with_assets,
                COUNT(*) FILTER (WHERE total_liabilities IS NOT NULL) as with_liabilities,
                COUNT(*) FILTER (WHERE revenue IS NOT NULL) as with_revenue,
                COUNT(*) FILTER (WHERE net_income IS NOT NULL) as with_net_income
            FROM financial_statements
        ''')

        total_fs = fs_stats['total_statements']
        logger.info(f'총 재무제표 레코드: {total_fs:,}')

        if total_fs > 0:
            logger.info(f'재무제표 보유 기업: {fs_stats["unique_companies"]:,}')
            logger.info(f'회계연도 범위: {fs_stats["earliest_year"]} ~ {fs_stats["latest_year"]}')
            logger.info(f'자산 있음: {fs_stats["with_assets"]:,} ({fs_stats["with_assets"]/total_fs*100:.1f}%)')
            logger.info(f'부채 있음: {fs_stats["with_liabilities"]:,} ({fs_stats["with_liabilities"]/total_fs*100:.1f}%)')
            logger.info(f'매출 있음: {fs_stats["with_revenue"]:,} ({fs_stats["with_revenue"]/total_fs*100:.1f}%)')
            logger.info(f'순이익 있음: {fs_stats["with_net_income"]:,} ({fs_stats["with_net_income"]/total_fs*100:.1f}%)')
        else:
            logger.info('  ✗ 재무제표 데이터 없음')

        # 8. risk_signals 테이블
        logger.info('\n[8] RISK_SIGNALS (리스크 신호)')
        logger.info('-' * 100)

        risk_stats = await conn.fetchrow('''
            SELECT
                COUNT(*) as total_signals,
                COUNT(DISTINCT target_company_id) as unique_companies,
                COUNT(*) FILTER (WHERE severity = 'LOW') as low_severity,
                COUNT(*) FILTER (WHERE severity = 'MEDIUM') as medium_severity,
                COUNT(*) FILTER (WHERE severity = 'HIGH') as high_severity,
                COUNT(*) FILTER (WHERE severity = 'CRITICAL') as critical_severity,
                COUNT(*) FILTER (WHERE status = 'DETECTED') as detected,
                COUNT(*) FILTER (WHERE status = 'CONFIRMED') as confirmed,
                COUNT(*) FILTER (WHERE status = 'RESOLVED') as resolved
            FROM risk_signals
        ''')

        total_risk = risk_stats['total_signals']
        logger.info(f'총 리스크 신호: {total_risk:,}')
        logger.info(f'리스크 있는 기업: {risk_stats["unique_companies"]:,}')

        if total_risk > 0:
            logger.info(f'\n심각도별:')
            logger.info(f'  LOW: {risk_stats["low_severity"]:,} ({risk_stats["low_severity"]/total_risk*100:.1f}%)')
            logger.info(f'  MEDIUM: {risk_stats["medium_severity"]:,} ({risk_stats["medium_severity"]/total_risk*100:.1f}%)')
            logger.info(f'  HIGH: {risk_stats["high_severity"]:,} ({risk_stats["high_severity"]/total_risk*100:.1f}%)')
            logger.info(f'  CRITICAL: {risk_stats["critical_severity"]:,} ({risk_stats["critical_severity"]/total_risk*100:.1f}%)')

            logger.info(f'\n상태별:')
            logger.info(f'  DETECTED: {risk_stats["detected"]:,} ({risk_stats["detected"]/total_risk*100:.1f}%)')
            logger.info(f'  CONFIRMED: {risk_stats["confirmed"]:,} ({risk_stats["confirmed"]/total_risk*100:.1f}%)')
            logger.info(f'  RESOLVED: {risk_stats["resolved"]:,} ({risk_stats["resolved"]/total_risk*100:.1f}%)')

        # 9. disclosures 테이블
        logger.info('\n[9] DISCLOSURES (공시)')
        logger.info('-' * 100)

        disc_stats = await conn.fetchrow('''
            SELECT
                COUNT(*) as total_disclosures,
                COUNT(DISTINCT corp_code) as unique_companies,
                COUNT(DISTINCT report_nm) as unique_report_types,
                COUNT(*) FILTER (WHERE storage_url IS NOT NULL) as with_storage,
                MIN(rcept_dt) as earliest_date,
                MAX(rcept_dt) as latest_date
            FROM disclosures
        ''')

        total_disc = disc_stats['total_disclosures']
        logger.info(f'총 공시 수: {total_disc:,}')

        if total_disc > 0:
            logger.info(f'공시 기업 수: {disc_stats["unique_companies"]:,}')
            logger.info(f'공시 유형: {disc_stats["unique_report_types"]:,}개')
            logger.info(f'저장된 XML: {disc_stats["with_storage"]:,} ({disc_stats["with_storage"]/total_disc*100:.1f}%)')
            logger.info(f'공시 기간: {disc_stats["earliest_date"]} ~ {disc_stats["latest_date"]}')
        else:
            logger.info('  ✗ 공시 데이터 없음')

        # 10. disclosure_parsed_data 테이블
        logger.info('\n[10] DISCLOSURE_PARSED_DATA (파싱된 공시 데이터)')
        logger.info('-' * 100)

        parsed_stats = await conn.fetchrow('''
            SELECT
                COUNT(*) as total_parsed,
                COUNT(DISTINCT rcept_no) as unique_disclosures,
                COUNT(*) FILTER (WHERE parsed_data IS NOT NULL) as with_data,
                COUNT(*) FILTER (WHERE parser_version IS NOT NULL) as with_version
            FROM disclosure_parsed_data
        ''')

        total_parsed = parsed_stats['total_parsed']
        logger.info(f'총 파싱 레코드: {total_parsed:,}')

        if total_parsed > 0:
            logger.info(f'파싱된 공시: {parsed_stats["unique_disclosures"]:,}')
            logger.info(f'파싱 데이터 있음: {parsed_stats["with_data"]:,} ({parsed_stats["with_data"]/total_parsed*100:.1f}%)')
            logger.info(f'파서 버전 있음: {parsed_stats["with_version"]:,} ({parsed_stats["with_version"]/total_parsed*100:.1f}%)')
        else:
            logger.info('  ✗ 파싱된 공시 데이터 없음')

        # 전체 요약
        logger.info('\n' + '=' * 100)
        logger.info('전체 요약')
        logger.info('=' * 100)

        total_records = (
            total_comp + total_off + total_pos + total_cb + total_subs +
            total_aff + total_fs + total_risk + total_disc + total_parsed
        )

        logger.info(f'\n총 레코드 수: {total_records:,}')
        logger.info(f'\n주요 엔티티:')
        logger.info(f'  1. 회사: {total_comp:,}')
        logger.info(f'  2. 임원: {total_off:,}')
        logger.info(f'  3. 임원 직책: {total_pos:,}')
        logger.info(f'  4. 전환사채: {total_cb:,}')
        logger.info(f'  5. CB 인수자: {total_subs:,}')
        logger.info(f'  6. 계열사: {total_aff:,}')
        logger.info(f'  7. 재무제표: {total_fs:,}')
        logger.info(f'  8. 리스크 신호: {total_risk:,}')
        logger.info(f'  9. 공시: {total_disc:,}')
        logger.info(f' 10. 파싱된 공시: {total_parsed:,}')

        logger.info(f'\n코스닥/코스피 상장 기업 데이터:')
        if companies_stats['listed_companies'] > 0:
            logger.info(f'  ✓ {companies_stats["listed_companies"]:,}개 상장 기업 데이터 존재')
            logger.info(f'    - KOSPI: {companies_stats["kospi_count"]:,}개')
            logger.info(f'    - KOSDAQ: {companies_stats["kosdaq_count"]:,}개')
            logger.info(f'    - 시장구분 미지정: {companies_stats["no_market"]:,}개')
        else:
            logger.info(f'  ✗ 상장 기업 데이터 없음 (ticker가 모두 NULL)')

        logger.info('\n' + '=' * 100)
        logger.info('검증 완료')
        logger.info('=' * 100)

    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
