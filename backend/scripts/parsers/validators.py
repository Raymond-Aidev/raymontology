"""
DataValidator - DART 데이터 품질 검증

검증 항목:
- 재무 데이터: revenue, total_assets 유효성, 자산=부채+자본 균형
- 임원 데이터: 동일 회사 포지션 수, 임기 논리 검증, 출생년월 유효성
- CB 데이터: 중복 검사, 금액 유효성

사용법:
    from scripts.parsers import DataValidator

    validator = DataValidator()
    report = await validator.validate_all(conn)
    print(report.to_string())
"""

import asyncpg
import logging
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """검증 결과"""
    category: str
    table: str
    total_records: int = 0
    valid_records: int = 0
    warnings: List[Dict] = field(default_factory=list)
    errors: List[Dict] = field(default_factory=list)

    @property
    def valid_rate(self) -> float:
        if self.total_records == 0:
            return 0.0
        return (self.valid_records / self.total_records) * 100

    @property
    def has_issues(self) -> bool:
        return len(self.warnings) > 0 or len(self.errors) > 0


@dataclass
class QualityReport:
    """품질 보고서"""
    generated_at: datetime = field(default_factory=datetime.now)
    results: Dict[str, ValidationResult] = field(default_factory=dict)

    def add_result(self, key: str, result: ValidationResult):
        self.results[key] = result

    def to_string(self) -> str:
        """보고서 문자열 출력"""
        lines = [
            f"📊 데이터 품질 보고서 ({self.generated_at.strftime('%Y-%m-%d %H:%M')})",
            "=" * 50,
            ""
        ]

        for key, result in self.results.items():
            status = "✅" if not result.has_issues else "⚠️" if result.errors == [] else "❌"
            lines.append(f"{status} {result.category} ({result.table})")
            lines.append(f"   - 총 레코드: {result.total_records:,}")
            lines.append(f"   - 유효율: {result.valid_rate:.1f}%")

            if result.warnings:
                lines.append(f"   - 경고: {len(result.warnings)}건")
            if result.errors:
                lines.append(f"   - 오류: {len(result.errors)}건")
            lines.append("")

        # 요약
        total_warnings = sum(len(r.warnings) for r in self.results.values())
        total_errors = sum(len(r.errors) for r in self.results.values())

        lines.append("📈 개선 필요 항목:")
        if total_errors > 0:
            lines.append(f"   - 오류 {total_errors}건 수정 필요")
        if total_warnings > 0:
            lines.append(f"   - 경고 {total_warnings}건 검토 필요")
        if total_errors == 0 and total_warnings == 0:
            lines.append("   - 없음 (모든 검증 통과)")

        return "\n".join(lines)

    def to_dict(self) -> Dict[str, Any]:
        """보고서 딕셔너리 출력"""
        return {
            'generated_at': self.generated_at.isoformat(),
            'results': {
                key: {
                    'category': r.category,
                    'table': r.table,
                    'total_records': r.total_records,
                    'valid_records': r.valid_records,
                    'valid_rate': r.valid_rate,
                    'warnings_count': len(r.warnings),
                    'errors_count': len(r.errors),
                }
                for key, r in self.results.items()
            },
            'summary': {
                'total_warnings': sum(len(r.warnings) for r in self.results.values()),
                'total_errors': sum(len(r.errors) for r in self.results.values()),
            }
        }


class DataValidator:
    """DART 데이터 품질 검증기"""

    # 검증 기준
    THRESHOLDS = {
        'max_officer_positions': 3,  # 동일 회사 최대 포지션 수
        'birth_year_min': 1920,
        'birth_year_max': 2010,
        'max_amount': 100_000_000_000_000,  # 100조 (단위 오류 감지)
        'balance_tolerance': 0.01,  # 자산=부채+자본 오차 허용 (1%)
    }

    async def validate_all(self, conn: asyncpg.Connection) -> QualityReport:
        """전체 데이터 검증"""
        report = QualityReport()

        # 1. 재무 데이터 검증
        financial_result = await self.validate_financial_data(conn)
        report.add_result('financial', financial_result)

        # 2. 임원 데이터 검증
        officer_result = await self.validate_officer_data(conn)
        report.add_result('officers', officer_result)

        # 3. CB 데이터 검증
        cb_result = await self.validate_cb_data(conn)
        report.add_result('cb', cb_result)

        return report

    async def validate_financial_data(self, conn: asyncpg.Connection) -> ValidationResult:
        """재무 데이터 검증"""
        result = ValidationResult(
            category="재무 데이터",
            table="financial_details"
        )

        # 총 레코드 수
        result.total_records = await conn.fetchval("SELECT COUNT(*) FROM financial_details")

        # 1. revenue > 0 검증
        invalid_revenue = await conn.fetch("""
            SELECT fd.id, c.name as company_name, fd.fiscal_year, fd.revenue
            FROM financial_details fd
            JOIN companies c ON fd.company_id = c.id
            WHERE fd.revenue IS NOT NULL AND fd.revenue <= 0
            LIMIT 20
        """)
        for row in invalid_revenue:
            result.warnings.append({
                'type': 'invalid_revenue',
                'company': row['company_name'],
                'fiscal_year': row['fiscal_year'],
                'value': row['revenue'],
            })

        # 2. total_assets > 0 검증
        invalid_assets = await conn.fetch("""
            SELECT fd.id, c.name as company_name, fd.fiscal_year, fd.total_assets
            FROM financial_details fd
            JOIN companies c ON fd.company_id = c.id
            WHERE fd.total_assets IS NOT NULL AND fd.total_assets <= 0
            LIMIT 20
        """)
        for row in invalid_assets:
            result.warnings.append({
                'type': 'invalid_total_assets',
                'company': row['company_name'],
                'fiscal_year': row['fiscal_year'],
                'value': row['total_assets'],
            })

        # 3. 자산 = 부채 + 자본 균형 검증 (오차 1% 이내)
        unbalanced = await conn.fetch("""
            SELECT fd.id, c.name as company_name, fd.fiscal_year,
                   fd.total_assets, fd.total_liabilities, fd.total_equity,
                   ABS(fd.total_assets - (fd.total_liabilities + fd.total_equity)) as diff
            FROM financial_details fd
            JOIN companies c ON fd.company_id = c.id
            WHERE fd.total_assets IS NOT NULL
              AND fd.total_liabilities IS NOT NULL
              AND fd.total_equity IS NOT NULL
              AND fd.total_assets > 0
              AND ABS(fd.total_assets - (fd.total_liabilities + fd.total_equity)) > fd.total_assets * 0.01
            LIMIT 20
        """)
        for row in unbalanced:
            result.warnings.append({
                'type': 'balance_mismatch',
                'company': row['company_name'],
                'fiscal_year': row['fiscal_year'],
                'total_assets': row['total_assets'],
                'liabilities_plus_equity': row['total_liabilities'] + row['total_equity'],
                'diff': row['diff'],
            })

        # 4. 단위 이상값 감지 (100조 초과)
        suspicious_amounts = await conn.fetch(f"""
            SELECT fd.id, c.name as company_name, fd.fiscal_year,
                   fd.revenue, fd.total_assets
            FROM financial_details fd
            JOIN companies c ON fd.company_id = c.id
            WHERE fd.revenue > {self.THRESHOLDS['max_amount']}
               OR fd.total_assets > {self.THRESHOLDS['max_amount']}
            LIMIT 20
        """)
        for row in suspicious_amounts:
            result.errors.append({
                'type': 'suspicious_amount',
                'company': row['company_name'],
                'fiscal_year': row['fiscal_year'],
                'revenue': row['revenue'],
                'total_assets': row['total_assets'],
                'note': '단위 오류 의심 (100조 초과)',
            })

        # 유효 레코드 수 계산
        result.valid_records = result.total_records - len(result.errors)

        return result

    async def validate_officer_data(self, conn: asyncpg.Connection) -> ValidationResult:
        """임원 데이터 검증"""
        result = ValidationResult(
            category="임원 데이터",
            table="officer_positions"
        )

        # 총 레코드 수
        result.total_records = await conn.fetchval("SELECT COUNT(*) FROM officer_positions")

        # 1. 동일 회사 포지션 수 > 3 (중복 의심)
        high_position_count = await conn.fetch(f"""
            SELECT o.name, c.name as company, COUNT(*) as cnt
            FROM officer_positions op
            JOIN officers o ON op.officer_id = o.id
            JOIN companies c ON op.company_id = c.id
            GROUP BY o.name, c.name
            HAVING COUNT(*) > {self.THRESHOLDS['max_officer_positions']}
            ORDER BY cnt DESC
            LIMIT 20
        """)
        for row in high_position_count:
            result.warnings.append({
                'type': 'duplicate_positions',
                'officer': row['name'],
                'company': row['company'],
                'count': row['cnt'],
            })

        # 2. 임기 논리 오류 (start > end)
        invalid_tenure = await conn.fetch("""
            SELECT op.id, o.name, c.name as company,
                   op.term_start_date, op.term_end_date
            FROM officer_positions op
            JOIN officers o ON op.officer_id = o.id
            JOIN companies c ON op.company_id = c.id
            WHERE op.term_start_date IS NOT NULL
              AND op.term_end_date IS NOT NULL
              AND op.term_start_date > op.term_end_date
            LIMIT 20
        """)
        for row in invalid_tenure:
            result.errors.append({
                'type': 'invalid_tenure',
                'officer': row['name'],
                'company': row['company'],
                'term_start': str(row['term_start_date']),
                'term_end': str(row['term_end_date']),
            })

        # 3. 출생년월 유효성 (1920-2010)
        invalid_birth = await conn.fetch(f"""
            SELECT op.id, o.name, op.birth_date
            FROM officer_positions op
            JOIN officers o ON op.officer_id = o.id
            WHERE op.birth_date IS NOT NULL
              AND (
                CAST(SUBSTRING(op.birth_date FROM 1 FOR 4) AS INTEGER) < {self.THRESHOLDS['birth_year_min']}
                OR CAST(SUBSTRING(op.birth_date FROM 1 FOR 4) AS INTEGER) > {self.THRESHOLDS['birth_year_max']}
              )
            LIMIT 20
        """)
        for row in invalid_birth:
            result.errors.append({
                'type': 'invalid_birth_date',
                'officer': row['name'],
                'birth_date': row['birth_date'],
            })

        result.valid_records = result.total_records - len(result.errors)

        return result

    async def validate_cb_data(self, conn: asyncpg.Connection) -> ValidationResult:
        """CB 데이터 검증"""
        result = ValidationResult(
            category="CB 데이터",
            table="convertible_bonds"
        )

        # 총 레코드 수
        result.total_records = await conn.fetchval("SELECT COUNT(*) FROM convertible_bonds")

        # 1. 중복 검사 (company + bond_name)
        duplicates = await conn.fetch("""
            SELECT c.name as company, cb.bond_name, COUNT(*) as cnt
            FROM convertible_bonds cb
            JOIN companies c ON cb.company_id = c.id
            GROUP BY c.name, cb.bond_name
            HAVING COUNT(*) > 1
            ORDER BY cnt DESC
            LIMIT 20
        """)
        for row in duplicates:
            result.warnings.append({
                'type': 'duplicate_cb',
                'company': row['company'],
                'bond_name': row['bond_name'],
                'count': row['cnt'],
            })

        # 2. 발행액 유효성 (> 0)
        invalid_amount = await conn.fetch("""
            SELECT cb.id, c.name as company, cb.bond_name, cb.issue_amount
            FROM convertible_bonds cb
            JOIN companies c ON cb.company_id = c.id
            WHERE cb.issue_amount IS NOT NULL AND cb.issue_amount <= 0
            LIMIT 20
        """)
        for row in invalid_amount:
            result.warnings.append({
                'type': 'invalid_issued_amount',
                'company': row['company'],
                'bond_name': row['bond_name'],
                'amount': row['issue_amount'],
            })

        result.valid_records = result.total_records - len(result.errors)

        return result

    async def get_summary_stats(self, conn: asyncpg.Connection) -> Dict[str, Any]:
        """요약 통계"""
        stats = {}

        # 테이블별 레코드 수
        tables = [
            'companies', 'officers', 'officer_positions',
            'financial_details', 'convertible_bonds', 'cb_subscribers',
            'disclosures', 'risk_scores', 'raymonds_index'
        ]

        for table in tables:
            try:
                count = await conn.fetchval(f"SELECT COUNT(*) FROM {table}")
                stats[table] = count
            except:
                stats[table] = 0

        return stats
