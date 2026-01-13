"""
News 관계 분석 시스템

뉴스 기사에서 기업/인물 관계를 추출하고 복잡도를 스코어링하는 모듈입니다.

사용법:
    1. Claude Code에서 URL 제공
    2. WebFetch로 기사 파싱
    3. save_to_db.py로 DB 저장

예시:
    "이 기사 파싱해서 DB에 저장해줘: https://www.drcr.co.kr/articles/647"

구조:
    news/
    ├── storage/          # DB 저장 스크립트
    │   └── save_to_db.py
    ├── analyzers/        # 복잡도 계산
    │   └── complexity_calculator.py
    ├── parsers/          # (향후) 파싱 유틸리티
    ├── matchers/         # (향후) 엔티티 매칭
    └── scripts/          # CLI 스크립트
"""

__version__ = "1.0.0"
