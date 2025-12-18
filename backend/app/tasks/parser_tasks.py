"""
Parser Background Tasks

보고서 파싱 백그라운드 작업
"""
import asyncio
from typing import Dict, Optional
from pathlib import Path
from datetime import datetime
from celery import Task
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from app.tasks.celery_app import celery_app
from app.nlp.report_parser import ReportParser
from app.database import async_session_maker
from app.models.disclosures import Disclosure, DisclosureParsedData

logger = logging.getLogger(__name__)


class DatabaseTask(Task):
    """데이터베이스 세션을 사용하는 Celery Task"""
    _db: Optional[AsyncSession] = None

    async def get_db(self) -> AsyncSession:
        """DB 세션 생성"""
        if self._db is None:
            self._db = async_session_maker()
        return self._db

    async def close_db(self):
        """DB 세션 종료"""
        if self._db is not None:
            await self._db.close()
            self._db = None


@celery_app.task(
    bind=True,
    base=DatabaseTask,
    name="app.tasks.parser_tasks.parse_report_task",
    max_retries=3,
    default_retry_delay=60
)
def parse_report_task(
    self,
    rcept_no: str,
    pdf_path: str,
    company_id: str,
    use_ocr: bool = False
) -> Dict:
    """
    보고서 파싱 작업 (비동기 래퍼)

    Args:
        rcept_no: 접수번호
        pdf_path: PDF 파일 경로
        company_id: 회사 ID
        use_ocr: OCR 사용 여부

    Returns:
        파싱 결과
    """
    return asyncio.run(
        _parse_report_async(self, rcept_no, pdf_path, company_id, use_ocr)
    )


async def _parse_report_async(
    task: DatabaseTask,
    rcept_no: str,
    pdf_path: str,
    company_id: str,
    use_ocr: bool
) -> Dict:
    """보고서 파싱 (비동기)"""
    db = await task.get_db()

    try:
        logger.info(f"Starting report parsing: rcept_no={rcept_no}, pdf_path={pdf_path}")

        # 파서 생성
        parser = ReportParser(use_ocr=use_ocr)

        # 파싱 실행
        parsed_report = await parser.parse_report(
            pdf_path=Path(pdf_path),
            company_id=company_id,
            rcept_no=rcept_no
        )

        # 파싱 데이터 저장
        parsed_data_record = DisclosureParsedData(
            rcept_no=rcept_no,
            parsed_data=parsed_report.to_dict(),
            parsed_at=datetime.utcnow(),
            parser_version="1.0.0",
            sections_count=len(parsed_report.sections),
            tables_count=0,  # TODO: 테이블 카운트
        )

        db.add(parsed_data_record)
        await db.commit()

        logger.info(f"Report parsing completed: rcept_no={rcept_no}")

        return {
            "status": "success",
            "rcept_no": rcept_no,
            "summary": await parser.get_parsing_summary(parsed_report),
        }

    except Exception as e:
        logger.error(f"Report parsing failed: rcept_no={rcept_no}, error={e}")

        # 재시도
        raise task.retry(exc=e)

    finally:
        await task.close_db()


@celery_app.task(
    bind=True,
    base=DatabaseTask,
    name="app.tasks.parser_tasks.parse_officer_section_task",
    max_retries=3,
    default_retry_delay=60
)
def parse_officer_section_task(
    self,
    rcept_no: str,
    pdf_path: str,
    company_id: str
) -> Dict:
    """
    임원 섹션만 파싱 (경량 작업)

    Args:
        rcept_no: 접수번호
        pdf_path: PDF 파일 경로
        company_id: 회사 ID

    Returns:
        임원 리스트
    """
    return asyncio.run(
        _parse_officer_section_async(self, rcept_no, pdf_path, company_id)
    )


async def _parse_officer_section_async(
    task: DatabaseTask,
    rcept_no: str,
    pdf_path: str,
    company_id: str
) -> Dict:
    """임원 섹션 파싱 (비동기)"""
    try:
        logger.info(f"Starting officer extraction: rcept_no={rcept_no}")

        # 파서 생성
        parser = ReportParser(use_ocr=False)

        # 임원만 추출
        officers = await parser.parse_officer_section_only(
            pdf_path=Path(pdf_path),
            company_id=company_id
        )

        logger.info(f"Officer extraction completed: rcept_no={rcept_no}, count={len(officers)}")

        return {
            "status": "success",
            "rcept_no": rcept_no,
            "officers": officers,
            "count": len(officers),
        }

    except Exception as e:
        logger.error(f"Officer extraction failed: rcept_no={rcept_no}, error={e}")
        raise task.retry(exc=e)

    finally:
        await task.close_db()


@celery_app.task(
    bind=True,
    base=DatabaseTask,
    name="app.tasks.parser_tasks.parse_cb_section_task",
    max_retries=3,
    default_retry_delay=60
)
def parse_cb_section_task(
    self,
    rcept_no: str,
    pdf_path: str,
    company_id: str
) -> Dict:
    """
    전환사채 섹션만 파싱 (경량 작업)

    Args:
        rcept_no: 접수번호
        pdf_path: PDF 파일 경로
        company_id: 회사 ID

    Returns:
        전환사채 리스트
    """
    return asyncio.run(
        _parse_cb_section_async(self, rcept_no, pdf_path, company_id)
    )


async def _parse_cb_section_async(
    task: DatabaseTask,
    rcept_no: str,
    pdf_path: str,
    company_id: str
) -> Dict:
    """전환사채 섹션 파싱 (비동기)"""
    try:
        logger.info(f"Starting CB extraction: rcept_no={rcept_no}")

        # 파서 생성
        parser = ReportParser(use_ocr=False)

        # CB만 추출
        cbs = await parser.parse_cb_section_only(
            pdf_path=Path(pdf_path),
            company_id=company_id
        )

        logger.info(f"CB extraction completed: rcept_no={rcept_no}, count={len(cbs)}")

        return {
            "status": "success",
            "rcept_no": rcept_no,
            "convertible_bonds": cbs,
            "count": len(cbs),
        }

    except Exception as e:
        logger.error(f"CB extraction failed: rcept_no={rcept_no}, error={e}")
        raise task.retry(exc=e)

    finally:
        await task.close_db()


@celery_app.task(
    bind=True,
    name="app.tasks.parser_tasks.batch_parse_reports_task",
    max_retries=1
)
def batch_parse_reports_task(
    self,
    rcept_nos: list[str],
    use_ocr: bool = False
) -> Dict:
    """
    배치 파싱 작업

    Args:
        rcept_nos: 접수번호 리스트
        use_ocr: OCR 사용 여부

    Returns:
        배치 파싱 결과
    """
    logger.info(f"Starting batch parsing: {len(rcept_nos)} reports")

    results = {
        "total": len(rcept_nos),
        "success": 0,
        "failed": 0,
        "errors": []
    }

    for rcept_no in rcept_nos:
        try:
            # 개별 파싱 작업 호출 (비동기)
            # TODO: DB에서 PDF 경로 조회
            # task = parse_report_task.delay(rcept_no, pdf_path, company_id, use_ocr)
            results["success"] += 1
        except Exception as e:
            logger.error(f"Failed to parse {rcept_no}: {e}")
            results["failed"] += 1
            results["errors"].append({
                "rcept_no": rcept_no,
                "error": str(e)
            })

    logger.info(f"Batch parsing completed: {results}")
    return results
