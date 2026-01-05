#!/usr/bin/env python3
"""
분기별 데이터 파이프라인 통합 실행

DART 분기보고서 다운로드부터 RaymondsIndex 계산까지 전체 프로세스를 자동화합니다.

파이프라인 단계:
    1. 다운로드 - DART에서 분기보고서 다운로드
    2. 파싱 - 통합 파서로 데이터 추출
    3. 검증 - 데이터 품질 검증
    4. 적재 - DB UPSERT
    5. 계산 - RaymondsIndex 재계산
    6. 보고서 - 품질 보고서 생성

사용법:
    # 전체 파이프라인 실행
    python -m scripts.pipeline.run_quarterly_pipeline --quarter Q1 --year 2025

    # 특정 단계부터 실행
    python -m scripts.pipeline.run_quarterly_pipeline --quarter Q1 --year 2025 --start-from parse

    # 테스트 모드 (샘플만)
    python -m scripts.pipeline.run_quarterly_pipeline --quarter Q1 --year 2025 --sample 10

분기별 일정:
    Q1 (1분기): 5월 15일 마감 → 5월 20일 실행
    Q2 (반기):  8월 14일 마감 → 8월 20일 실행
    Q3 (3분기): 11월 14일 마감 → 11월 20일 실행
    Q4 (사업): 3월 31일 마감 → 4월 5일 실행

환경 변수:
    DART_API_KEY: DART OpenAPI 키
    DATABASE_URL: PostgreSQL 연결 URL
"""

import argparse
import asyncio
import logging
import os
import sys
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, Any, Optional, List

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [%(name)s] %(message)s'
)
logger = logging.getLogger(__name__)


class PipelineStep(Enum):
    """파이프라인 단계"""
    DOWNLOAD = 'download'
    PARSE = 'parse'
    VALIDATE = 'validate'
    LOAD = 'load'  # 파싱에 포함됨
    CALCULATE = 'calculate'
    REPORT = 'report'


class QuarterlyPipeline:
    """분기별 데이터 파이프라인"""

    STEPS = [
        PipelineStep.DOWNLOAD,
        PipelineStep.PARSE,
        PipelineStep.VALIDATE,
        PipelineStep.CALCULATE,
        PipelineStep.REPORT,
    ]

    def __init__(
        self,
        quarter: str,
        year: int,
        database_url: Optional[str] = None,
        dart_api_key: Optional[str] = None
    ):
        self.quarter = quarter
        self.year = year
        self.database_url = database_url or os.getenv('DATABASE_URL')
        if not self.database_url:
            raise ValueError("DATABASE_URL 환경 변수가 설정되지 않았습니다")
        self.dart_api_key = dart_api_key or os.getenv('DART_API_KEY', '')

        self.results: Dict[str, Any] = {
            'quarter': quarter,
            'year': year,
            'started_at': None,
            'finished_at': None,
            'steps': {},
        }

    async def run(
        self,
        start_from: Optional[PipelineStep] = None,
        stop_after: Optional[PipelineStep] = None,
        skip_steps: Optional[List[PipelineStep]] = None,
        sample: Optional[int] = None,
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """파이프라인 실행

        Args:
            start_from: 시작 단계 (이전 단계 스킵)
            stop_after: 종료 단계 (이후 단계 스킵)
            skip_steps: 스킵할 단계 목록
            sample: 샘플 개수 (테스트용)
            dry_run: True면 실제 저장 없이 테스트

        Returns:
            실행 결과
        """
        self.results['started_at'] = datetime.now().isoformat()
        skip_steps = skip_steps or []

        logger.info("=" * 60)
        logger.info(f"분기별 파이프라인 시작: {self.quarter} {self.year}")
        logger.info("=" * 60)

        if dry_run:
            logger.info("[DRY-RUN 모드] 실제 저장 없이 테스트만 수행합니다")

        if sample:
            logger.info(f"[샘플 모드] {sample}개만 처리합니다")

        # 실행할 단계 결정
        start_idx = 0
        end_idx = len(self.STEPS)

        if start_from:
            for i, step in enumerate(self.STEPS):
                if step == start_from:
                    start_idx = i
                    break

        if stop_after:
            for i, step in enumerate(self.STEPS):
                if step == stop_after:
                    end_idx = i + 1
                    break

        steps_to_run = self.STEPS[start_idx:end_idx]

        # 각 단계 실행
        for step in steps_to_run:
            if step in skip_steps:
                logger.info(f"\n[SKIP] {step.value} 단계 스킵")
                self.results['steps'][step.value] = {'status': 'skipped'}
                continue

            logger.info(f"\n{'=' * 40}")
            logger.info(f"[{step.value.upper()}] 단계 시작")
            logger.info(f"{'=' * 40}")

            try:
                step_result = await self._run_step(step, sample=sample, dry_run=dry_run)
                self.results['steps'][step.value] = {
                    'status': 'success',
                    'result': step_result,
                }
                logger.info(f"[{step.value.upper()}] 완료")

            except Exception as e:
                logger.error(f"[{step.value.upper()}] 오류: {e}")
                self.results['steps'][step.value] = {
                    'status': 'error',
                    'error': str(e),
                }

                # 오류 발생 시 중단 여부 결정
                if step in [PipelineStep.DOWNLOAD, PipelineStep.PARSE]:
                    logger.error("필수 단계 오류로 파이프라인 중단")
                    break

        self.results['finished_at'] = datetime.now().isoformat()

        # 최종 결과 출력
        self._print_summary()

        return self.results

    async def _run_step(
        self,
        step: PipelineStep,
        sample: Optional[int] = None,
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """개별 단계 실행"""
        if step == PipelineStep.DOWNLOAD:
            return await self._step_download(sample=sample)

        elif step == PipelineStep.PARSE:
            return await self._step_parse(sample=sample, dry_run=dry_run)

        elif step == PipelineStep.VALIDATE:
            return await self._step_validate()

        elif step == PipelineStep.CALCULATE:
            return await self._step_calculate(sample=sample)

        elif step == PipelineStep.REPORT:
            return await self._step_report()

        else:
            raise ValueError(f"알 수 없는 단계: {step}")

    async def _step_download(self, sample: Optional[int] = None) -> Dict[str, Any]:
        """1단계: 다운로드"""
        if not self.dart_api_key:
            logger.warning("DART_API_KEY가 설정되지 않았습니다. 다운로드 스킵")
            return {'status': 'skipped', 'reason': 'no_api_key'}

        from .download_quarterly_reports import QuarterlyReportDownloader

        async with QuarterlyReportDownloader(self.dart_api_key) as downloader:
            stats = await downloader.download_all(
                quarter=self.quarter,
                year=self.year,
                limit=sample
            )
            return stats

    async def _step_parse(
        self,
        sample: Optional[int] = None,
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """2단계: 파싱"""
        from .run_unified_parser import QuarterlyParser

        parser = QuarterlyParser(self.database_url)
        stats = await parser.parse_quarterly(
            quarter=self.quarter,
            year=self.year,
            sample=sample,
            dry_run=dry_run
        )
        return stats

    async def _step_validate(self) -> Dict[str, Any]:
        """3단계: 검증"""
        from .validate_parsed_data import DataQualityChecker

        checker = DataQualityChecker(self.database_url)
        result = await checker.validate_quarter(self.quarter, self.year)
        return result

    async def _step_calculate(self, sample: Optional[int] = None) -> Dict[str, Any]:
        """4단계: RaymondsIndex 계산"""
        from .calculate_index import RaymondsIndexCalculator

        calculator = RaymondsIndexCalculator(self.database_url)
        stats = await calculator.calculate(year=self.year, sample=sample)
        return stats

    async def _step_report(self) -> Dict[str, Any]:
        """5단계: 보고서 생성"""
        from .generate_report import PipelineReporter

        reporter = PipelineReporter(self.database_url)
        report = await reporter.generate_quarterly_report(self.quarter, self.year)

        # 파일 저장
        saved_files = reporter.save_report(report)

        return {
            'report': report,
            'saved_files': {k: str(v) for k, v in saved_files.items()},
        }

    def _print_summary(self):
        """실행 결과 요약 출력"""
        logger.info("\n" + "=" * 60)
        logger.info("파이프라인 실행 완료")
        logger.info("=" * 60)

        for step_name, step_result in self.results['steps'].items():
            status = step_result.get('status', 'unknown')
            status_icon = {
                'success': '[OK]',
                'skipped': '[SKIP]',
                'error': '[FAIL]',
            }.get(status, '[?]')

            logger.info(f"  {status_icon} {step_name}")

            if status == 'error':
                logger.info(f"       오류: {step_result.get('error')}")

        # 소요 시간
        if self.results['started_at'] and self.results['finished_at']:
            start = datetime.fromisoformat(self.results['started_at'])
            end = datetime.fromisoformat(self.results['finished_at'])
            duration = (end - start).total_seconds()
            logger.info(f"\n총 소요 시간: {duration:.1f}초")


def parse_step(value: str) -> PipelineStep:
    """문자열을 PipelineStep으로 변환"""
    for step in PipelineStep:
        if step.value == value:
            return step
    raise argparse.ArgumentTypeError(f"알 수 없는 단계: {value}")


async def main():
    parser = argparse.ArgumentParser(
        description='분기별 데이터 파이프라인 통합 실행',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예시:
    # 전체 파이프라인 실행
    python -m scripts.pipeline.run_quarterly_pipeline --quarter Q1 --year 2025

    # 파싱부터 시작 (다운로드 스킵)
    python -m scripts.pipeline.run_quarterly_pipeline --quarter Q1 --year 2025 --start-from parse

    # 검증까지만 실행
    python -m scripts.pipeline.run_quarterly_pipeline --quarter Q1 --year 2025 --stop-after validate

    # 테스트 모드
    python -m scripts.pipeline.run_quarterly_pipeline --quarter Q1 --year 2025 --sample 10 --dry-run
"""
    )

    parser.add_argument('--quarter', choices=['Q1', 'Q2', 'Q3', 'Q4'], required=True,
                        help='분기 (Q1=1분기, Q2=반기, Q3=3분기, Q4=사업보고서)')
    parser.add_argument('--year', type=int, required=True, help='연도')

    parser.add_argument('--start-from', type=parse_step,
                        choices=[s.value for s in PipelineStep],
                        help='시작 단계 (download, parse, validate, calculate, report)')
    parser.add_argument('--stop-after', type=parse_step,
                        choices=[s.value for s in PipelineStep],
                        help='종료 단계')
    parser.add_argument('--skip', type=parse_step, nargs='+',
                        choices=[s.value for s in PipelineStep],
                        help='스킵할 단계')

    parser.add_argument('--sample', type=int, help='샘플 개수 (테스트용)')
    parser.add_argument('--dry-run', action='store_true', help='실제 저장 없이 테스트')

    args = parser.parse_args()

    pipeline = QuarterlyPipeline(
        quarter=args.quarter,
        year=args.year
    )

    await pipeline.run(
        start_from=args.start_from,
        stop_after=args.stop_after,
        skip_steps=args.skip,
        sample=args.sample,
        dry_run=args.dry_run
    )


if __name__ == '__main__':
    asyncio.run(main())
