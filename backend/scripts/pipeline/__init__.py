"""
DART 분기별 데이터 파이프라인

분기별 보고서 수집부터 RaymondsIndex 계산까지 전체 프로세스 자동화.

파이프라인 단계:
1. download_quarterly_reports.py - DART에서 분기보고서 다운로드
2. run_unified_parser.py - 통합 파서로 데이터 추출
3. validate_parsed_data.py - 데이터 품질 검증
4. load_to_database.py - DB 적재 (UPSERT)
5. calculate_index.py - RaymondsIndex 재계산
6. generate_report.py - 품질 보고서 생성

사용법:
    # 개별 단계 실행
    python -m scripts.pipeline.download_quarterly_reports --quarter Q1 --year 2025

    # 전체 파이프라인 실행
    python -m scripts.pipeline.run_quarterly_pipeline --quarter Q1 --year 2025

분기별 일정:
    Q1 (1분기): 5월 15일 마감 → 5월 20일 파싱
    Q2 (반기):  8월 14일 마감 → 8월 20일 파싱
    Q3 (3분기): 11월 14일 마감 → 11월 20일 파싱
    Q4 (사업): 3월 31일 마감 → 4월 5일 파싱
"""

from .run_quarterly_pipeline import QuarterlyPipeline

__all__ = ['QuarterlyPipeline']
__version__ = '1.0.0'
