"""
CB 공시 문서 파싱 및 DB 저장

전환사채 공시 문서에서:
1. CB 발행 정보 추출
2. CB 인수자(발행 대상자) 정보 추출
3. PostgreSQL에 저장
"""
import asyncio
import aiohttp
import json
import logging
import re
import zipfile
import io
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from bs4 import BeautifulSoup
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import IntegrityError
import argparse

from app.database import AsyncSessionLocal
from app.models import Company, ConvertibleBond, CBSubscriber

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class CBDisclosureParser:
    """CB 공시 문서 다운로드 및 파싱"""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://opendart.fss.or.kr/api"
        self.session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def download_disclosure(self, rcept_no: str) -> Optional[str]:
        """공시 문서 다운로드 (XML)"""
        url = f"{self.base_url}/document.xml"
        params = {
            "crtfc_key": self.api_key,
            "rcept_no": rcept_no
        }

        try:
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    raw_content = await response.read()

                    # DART API returns ZIP-compressed XML
                    try:
                        # Try to extract XML from ZIP
                        with zipfile.ZipFile(io.BytesIO(raw_content)) as zf:
                            # Get the first file in the zip (should be the XML)
                            xml_filename = zf.namelist()[0]
                            xml_bytes = zf.read(xml_filename)

                            # Try different encodings for Korean text
                            try:
                                content = xml_bytes.decode('euc-kr')
                            except UnicodeDecodeError:
                                try:
                                    content = xml_bytes.decode('utf-8')
                                except UnicodeDecodeError:
                                    try:
                                        content = xml_bytes.decode('cp949')
                                    except UnicodeDecodeError:
                                        logger.error(f"공시 {rcept_no}: 인코딩 실패")
                                        return None
                    except zipfile.BadZipFile:
                        # Not a ZIP file, try direct decoding
                        try:
                            content = raw_content.decode('euc-kr')
                        except UnicodeDecodeError:
                            try:
                                content = raw_content.decode('utf-8')
                            except UnicodeDecodeError:
                                try:
                                    content = raw_content.decode('cp949')
                                except UnicodeDecodeError:
                                    logger.error(f"공시 {rcept_no}: 인코딩 실패")
                                    return None

                    # 에러 응답 체크
                    if "error" in content.lower() or ("status" in content.lower() and "message" in content.lower()):
                        logger.warning(f"공시 {rcept_no}: API 에러 응답")
                        return None

                    return content
                else:
                    logger.warning(f"공시 {rcept_no}: HTTP {response.status}")
                    return None

        except Exception as e:
            logger.error(f"공시 {rcept_no} 다운로드 실패: {e}")
            return None

    def parse_cb_info(self, xml_content: str, disclosure_info: Dict) -> Optional[Dict]:
        """CB 발행 정보 추출"""
        soup = BeautifulSoup(xml_content, 'xml')

        cb_data = {
            "bond_name": None,
            "bond_type": None,
            "issue_date": None,
            "maturity_date": None,
            "issue_amount": None,
            "interest_rate": None,
            "conversion_price": None,
            "conversion_ratio": None,
            "conversion_start_date": None,
            "conversion_end_date": None,
            "source_disclosure_id": disclosure_info.get("rcept_no"),
            "source_date": disclosure_info.get("rcept_dt"),
            "properties": {}
        }

        # 공시 제목에서 채권 유형 판단
        report_nm = disclosure_info.get("report_nm", "")
        if "전환사채" in report_nm or "CB" in report_nm:
            cb_data["bond_type"] = "CB"
        elif "신주인수권부사채" in report_nm or "BW" in report_nm:
            cb_data["bond_type"] = "BW"
        elif "교환사채" in report_nm or "EB" in report_nm:
            cb_data["bond_type"] = "EB"

        # 텍스트 전체 추출
        text_content = soup.get_text()

        # 채권명 추출 (예: "제1회 무보증 사모 전환사채")
        bond_name_patterns = [
            r'제\s*\d+\s*회[^,\n]*(?:전환사채|신주인수권부사채|교환사채)',
            r'제\s*\d+\s*회[^,\n]*(?:CB|BW|EB)',
        ]
        for pattern in bond_name_patterns:
            match = re.search(pattern, text_content)
            if match:
                cb_data["bond_name"] = match.group(0).strip()
                break

        # 발행금액 추출 (원 단위)
        amount_patterns = [
            r'발행.*?총액.*?[:\s]*([0-9,]+)\s*원',
            r'발행.*?금액.*?[:\s]*([0-9,]+)\s*원',
            r'권면.*?총액.*?[:\s]*([0-9,]+)\s*원',
        ]
        for pattern in amount_patterns:
            match = re.search(pattern, text_content)
            if match:
                amount_str = match.group(1).replace(',', '')
                try:
                    cb_data["issue_amount"] = float(amount_str)
                    break
                except ValueError:
                    pass

        # 이자율 추출 (%)
        interest_patterns = [
            r'이자율.*?[:\s]*([0-9.]+)\s*%',
            r'표면.*?이자.*?[:\s]*([0-9.]+)\s*%',
        ]
        for pattern in interest_patterns:
            match = re.search(pattern, text_content)
            if match:
                try:
                    cb_data["interest_rate"] = float(match.group(1))
                    break
                except ValueError:
                    pass

        # 전환가액 추출 (원)
        conversion_price_patterns = [
            r'전환.*?가액.*?[:\s]*([0-9,]+)\s*원',
            r'전환.*?가격.*?[:\s]*([0-9,]+)\s*원',
        ]
        for pattern in conversion_price_patterns:
            match = re.search(pattern, text_content)
            if match:
                price_str = match.group(1).replace(',', '')
                try:
                    cb_data["conversion_price"] = float(price_str)
                    break
                except ValueError:
                    pass

        # 날짜 추출 (발행일, 만기일, 전환청구 기간)
        date_patterns = {
            "issue_date": [r'발행일.*?[:\s]*(\d{4})[년.-](\d{1,2})[월.-](\d{1,2})'],
            "maturity_date": [r'만기일.*?[:\s]*(\d{4})[년.-](\d{1,2})[월.-](\d{1,2})'],
            "conversion_start_date": [r'전환.*?청구.*?개시일.*?[:\s]*(\d{4})[년.-](\d{1,2})[월.-](\d{1,2})'],
            "conversion_end_date": [r'전환.*?청구.*?종료일.*?[:\s]*(\d{4})[년.-](\d{1,2})[월.-](\d{1,2})'],
        }

        for field, patterns in date_patterns.items():
            for pattern in patterns:
                match = re.search(pattern, text_content)
                if match:
                    try:
                        year, month, day = match.groups()
                        date_str = f"{year}-{int(month):02d}-{int(day):02d}"
                        cb_data[field] = datetime.strptime(date_str, "%Y-%m-%d").date()
                        break
                    except (ValueError, AttributeError):
                        pass

        # 최소한 발행금액이나 채권명이 있어야 유효한 데이터
        if cb_data["issue_amount"] or cb_data["bond_name"]:
            return cb_data

        return None

    def parse_subscribers(self, xml_content: str, disclosure_info: Dict) -> List[Dict]:
        """CB 인수자 정보 추출"""
        soup = BeautifulSoup(xml_content, 'xml')
        subscribers = []

        # "특정인에 대한 대상자별 사채발행내역" 테이블 찾기
        # 여러 패턴으로 시도
        table_keywords = [
            "특정인에 대한 대상자별 사채발행내역",
            "대상자별 사채발행내역",
            "발행 대상자",
            "인수자",
        ]

        target_table = None
        for keyword in table_keywords:
            # 키워드가 포함된 제목 찾기
            title_tags = soup.find_all(text=re.compile(keyword))
            for title_tag in title_tags:
                # 제목 다음에 오는 TABLE 태그 찾기
                current = title_tag.parent
                for _ in range(10):  # 최대 10단계까지 탐색
                    if current is None:
                        break

                    table = current.find_next("TABLE")
                    if table:
                        target_table = table
                        break

                    current = current.parent

                if target_table:
                    break

            if target_table:
                break

        if not target_table:
            logger.debug(f"공시 {disclosure_info.get('rcept_no')}: 인수자 테이블 없음")
            return subscribers

        # 테이블 파싱
        rows = target_table.find_all("TR")
        if len(rows) < 2:  # 헤더 + 최소 1개 데이터
            return subscribers

        # 헤더 분석
        header_row = rows[0]
        headers = [th.get_text(strip=True) for th in header_row.find_all(["TH", "TD"])]

        # 컬럼 인덱스 찾기
        name_idx = None
        relationship_idx = None
        rationale_idx = None
        amount_idx = None
        history_idx = None
        notes_idx = None

        for i, header in enumerate(headers):
            if "대상자" in header or "인수자" in header or "성명" in header:
                name_idx = i
            elif "관계" in header:
                relationship_idx = i
            elif "선정" in header or "경위" in header:
                rationale_idx = i
            elif "금액" in header or "총액" in header:
                amount_idx = i
            elif "거래" in header or "내역" in header:
                history_idx = i
            elif "비고" in header:
                notes_idx = i

        if name_idx is None:
            logger.warning(f"공시 {disclosure_info.get('rcept_no')}: 인수자명 컬럼 없음")
            return subscribers

        # 데이터 행 파싱
        for row in rows[1:]:
            cells = row.find_all(["TD", "TE", "TH"])
            if len(cells) <= name_idx:
                continue

            subscriber_name = cells[name_idx].get_text(strip=True)
            if not subscriber_name or subscriber_name in ["-", ""]:
                continue

            subscriber_data = {
                "subscriber_name": subscriber_name,
                "relationship_to_company": cells[relationship_idx].get_text(strip=True) if relationship_idx is not None and len(cells) > relationship_idx else None,
                "selection_rationale": cells[rationale_idx].get_text(strip=True) if rationale_idx is not None and len(cells) > rationale_idx else None,
                "transaction_history": cells[history_idx].get_text(strip=True) if history_idx is not None and len(cells) > history_idx else None,
                "notes": cells[notes_idx].get_text(strip=True) if notes_idx is not None and len(cells) > notes_idx else None,
                "source_disclosure_id": disclosure_info.get("rcept_no"),
                "source_date": disclosure_info.get("rcept_dt"),
            }

            # 인수 금액 파싱
            if amount_idx is not None and len(cells) > amount_idx:
                amount_text = cells[amount_idx].get_text(strip=True)
                amount_text = amount_text.replace(',', '').replace('원', '').strip()
                try:
                    subscriber_data["subscription_amount"] = float(amount_text)
                except ValueError:
                    pass

            # 특수관계자 여부 판단
            relationship = subscriber_data.get("relationship_to_company", "")
            if relationship and relationship != "-":
                subscriber_data["is_related_party"] = "Y"
            else:
                subscriber_data["is_related_party"] = "N"

            subscribers.append(subscriber_data)

        return subscribers

    async def process_disclosure(
        self,
        disclosure_info: Dict,
        db: AsyncSession,
        rate_limit_delay: float = 1.0
    ) -> Tuple[bool, int]:
        """
        개별 공시 처리

        Returns:
            (성공 여부, 저장된 인수자 수)
        """
        rcept_no = disclosure_info.get("rcept_no")
        corp_code = disclosure_info.get("corp_code")
        corp_name = disclosure_info.get("corp_name")

        # 회사 조회
        result = await db.execute(
            select(Company).where(Company.corp_code == corp_code)
        )
        company = result.scalar_one_or_none()

        if not company:
            logger.warning(f"공시 {rcept_no}: 회사 {corp_name}({corp_code}) DB에 없음")
            return False, 0

        # 이미 처리된 공시인지 확인
        existing = await db.execute(
            select(ConvertibleBond).where(
                ConvertibleBond.source_disclosure_id == rcept_no
            )
        )
        if existing.scalar_one_or_none():
            logger.debug(f"공시 {rcept_no}: 이미 처리됨")
            return False, 0

        # 공시 문서 다운로드
        await asyncio.sleep(rate_limit_delay)
        xml_content = await self.download_disclosure(rcept_no)

        if not xml_content:
            logger.warning(f"공시 {rcept_no}: 다운로드 실패")
            return False, 0

        # CB 정보 파싱
        cb_data = self.parse_cb_info(xml_content, disclosure_info)
        if not cb_data:
            logger.debug(f"공시 {rcept_no}: CB 정보 파싱 실패")
            return False, 0

        # CB 저장
        cb_data["company_id"] = company.id
        cb_data["status"] = "active"
        cb_data["outstanding_amount"] = cb_data.get("issue_amount")

        try:
            # 중복 CB 체크 (company_id, bond_name, issue_date 기준)
            # 동일한 CB가 여러 공시에서 언급될 수 있음 (발행 결정, 전환가액 조정 등)
            bond_name = cb_data.get("bond_name")
            issue_date = cb_data.get("issue_date")

            if bond_name and issue_date:
                existing_cb_query = await db.execute(
                    select(ConvertibleBond).where(
                        and_(
                            ConvertibleBond.company_id == company.id,
                            ConvertibleBond.bond_name == bond_name,
                            ConvertibleBond.issue_date == issue_date
                        )
                    )
                )
                existing_cb = existing_cb_query.scalar_one_or_none()

                if existing_cb:
                    # 이미 존재하는 CB - 인수자 정보만 추가할지 확인
                    subscribers_data = self.parse_subscribers(xml_content, disclosure_info)
                    new_subscribers = 0

                    for subscriber_data in subscribers_data:
                        subscriber_data["cb_id"] = existing_cb.id
                        subscriber = CBSubscriber(**subscriber_data)
                        db.add(subscriber)
                        new_subscribers += 1

                    if new_subscribers > 0:
                        await db.commit()
                        logger.info(f"✓ {corp_name}: 기존 CB에 인수자 {new_subscribers}명 추가")
                        return True, new_subscribers
                    else:
                        logger.debug(f"공시 {rcept_no}: CB 이미 존재, 새로운 정보 없음")
                        return False, 0

            # 새로운 CB 저장
            cb = ConvertibleBond(**cb_data)
            db.add(cb)
            await db.flush()  # CB ID 생성

            # 인수자 정보 파싱
            subscribers_data = self.parse_subscribers(xml_content, disclosure_info)

            # 인수자 저장
            for subscriber_data in subscribers_data:
                subscriber_data["cb_id"] = cb.id
                subscriber = CBSubscriber(**subscriber_data)
                db.add(subscriber)

            await db.commit()

            logger.info(
                f"✓ {corp_name}: CB '{cb_data.get('bond_name', 'N/A')}' "
                f"저장 (금액: {cb_data.get('issue_amount', 0):,.0f}원, "
                f"인수자: {len(subscribers_data)}명)"
            )

            return True, len(subscribers_data)

        except IntegrityError as e:
            # 중복 키 오류 발생 시 롤백하고 계속 진행
            await db.rollback()
            logger.debug(f"공시 {rcept_no}: CB 중복 (IntegrityError) - 건너뜀")
            return False, 0
        except Exception as e:
            # 기타 오류 발생 시에도 롤백
            await db.rollback()
            logger.error(f"공시 {rcept_no} 처리 중 오류: {e}")
            raise


async def main():
    parser = argparse.ArgumentParser(description="CB 공시 문서 파싱 및 DB 저장")
    parser.add_argument("--api-key", required=True, help="DART API 키")
    parser.add_argument("--input", required=True, help="입력 JSON 파일 (cb_disclosures_by_company_*.json)")
    parser.add_argument("--limit", type=int, help="처리할 공시 수 제한 (테스트용)")
    parser.add_argument("--rate-limit", type=float, default=1.0, help="API 요청 간격 (초)")

    args = parser.parse_args()

    # 입력 파일 로드
    input_file = Path(args.input)
    if not input_file.exists():
        logger.error(f"입력 파일 없음: {input_file}")
        return

    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # 파일 구조 확인 (list 또는 dict with "disclosures" key)
    if isinstance(data, list):
        disclosures = data
    else:
        disclosures = data.get("disclosures", [])

    logger.info(f"총 {len(disclosures)}건의 CB 공시 로드")

    if args.limit:
        disclosures = disclosures[:args.limit]
        logger.info(f"테스트 모드: {args.limit}건만 처리")

    # 파싱 시작
    async with CBDisclosureParser(args.api_key) as parser:
        async with AsyncSessionLocal() as db:
            total_processed = 0
            total_saved = 0
            total_subscribers = 0

            for i, disclosure in enumerate(disclosures, 1):
                try:
                    success, subscriber_count = await parser.process_disclosure(
                        disclosure,
                        db,
                        rate_limit_delay=args.rate_limit
                    )

                    total_processed += 1
                    if success:
                        total_saved += 1
                        total_subscribers += subscriber_count

                    if i % 50 == 0:
                        logger.info(
                            f"진행: {i}/{len(disclosures)} "
                            f"(저장: {total_saved}, 인수자: {total_subscribers})"
                        )

                except Exception as e:
                    logger.error(f"공시 {disclosure.get('rcept_no')} 처리 중 에러: {e}", exc_info=True)
                    continue

    logger.info("=" * 60)
    logger.info(f"완료: 처리 {total_processed}건, CB 저장 {total_saved}건, 인수자 저장 {total_subscribers}명")


if __name__ == "__main__":
    asyncio.run(main())
