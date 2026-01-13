"""
DART 통합 파서 모듈 (v3.1)

모든 DART 데이터 파싱을 위한 통합 인터페이스 제공.
기존 시행착오를 모두 반영한 검증된 로직으로 구성.

v3.1 개선 (2026-01-13):
- ShareholderParser 추가: 최대주주 및 특수관계인 주식소유 현황 파싱
- 무효 주주명 필터링 (테이블 헤더, 주식 종류 등)

v3.0 개선 (2026-01-05):
- XBRLEnhancer 추가: IFRS ACODE 기반 누락 항목 보완
- 부채 세부 항목 추출 (단기차입금, 장기차입금, 매입채무, 사채 등)
- 자본 세부 항목 추출 (자본금, 자본잉여금, 이익잉여금, 자기주식)

사용법:
    from scripts.parsers import DARTUnifiedParser

    parser = DARTUnifiedParser()
    await parser.parse_all(target_year=2024)

모듈 구성:
    - base.py: 공통 기능 (ZIP 추출, 인코딩, 단위 감지)
    - financial.py: 재무제표 파싱 (v3.0 - XBRL Enhanced)
    - xbrl_enhancer.py: IFRS ACODE 기반 데이터 보완
    - officer.py: 임원정보 파싱 (개선된 UPSERT)
    - shareholder.py: 대주주 파싱 (v3.1 신규)
    - validators.py: 데이터 품질 검증
"""

from .base import BaseParser
from .financial import FinancialParser
from .xbrl_enhancer import XBRLEnhancer
from .officer import OfficerParser
from .shareholder import ShareholderParser
from .validators import DataValidator
from .unified import DARTUnifiedParser

__all__ = [
    'BaseParser',
    'FinancialParser',
    'XBRLEnhancer',
    'OfficerParser',
    'ShareholderParser',
    'DataValidator',
    'DARTUnifiedParser',
]

__version__ = '3.1.0'
