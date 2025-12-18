#!/usr/bin/env python3
"""
DART 공시 XML 파서

ZIP 파일에서 XML을 추출하고 필요한 데이터 파싱:
- 임원 정보
- 특수관계자/계열사 정보
- 전환사채(CB) 정보
"""
import xml.etree.ElementTree as ET
import zipfile
import re
from pathlib import Path
from typing import List, Dict, Optional, Any
import logging
from dataclasses import dataclass, asdict

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class Executive:
    """임원 정보"""
    name: str                    # 성명
    position: str                # 직위
    is_registered: bool          # 등기임원 여부
    is_fulltime: bool           # 상근 여부
    gender: Optional[str] = None           # 성별
    birth_year_month: Optional[str] = None # 출생년월
    stock_count: Optional[int] = None      # 보유주식수
    ownership_ratio: Optional[float] = None # 지분율


@dataclass
class Affiliate:
    """특수관계자/계열사"""
    name: str                    # 회사명/성명
    relation_type: str           # 관계 (계열사, 특수관계인 등)
    stock_count: Optional[int] = None      # 보유주식수
    ownership_ratio: Optional[float] = None # 지분율


@dataclass
class ConvertibleBond:
    """전환사채"""
    issue_date: Optional[str] = None       # 발행일
    maturity_date: Optional[str] = None    # 만기일
    issue_amount: Optional[int] = None     # 발행금액
    conversion_price: Optional[int] = None # 전환가액
    conversion_ratio: Optional[float] = None # 전환비율


class DARTXMLParser:
    """DART XML 파서"""

    def __init__(self, zip_path: Path):
        self.zip_path = zip_path
        self.xml_content: Optional[str] = None
        self.root: Optional[ET.Element] = None

    def extract_xml(self) -> bool:
        """ZIP에서 XML 추출"""
        try:
            with zipfile.ZipFile(self.zip_path, 'r') as zf:
                # ZIP 내 파일 목록
                files = zf.namelist()

                # 메인 XML 파일 찾기 (가장 큰 파일)
                main_xml = None
                max_size = 0

                for filename in files:
                    if filename.endswith('.xml'):
                        info = zf.getinfo(filename)
                        if info.file_size > max_size:
                            max_size = info.file_size
                            main_xml = filename

                if not main_xml:
                    logger.warning(f"No XML file found in {self.zip_path}")
                    return False

                # XML 읽기 (UTF-8 먼저 시도, 실패하면 EUC-KR)
                try:
                    self.xml_content = zf.read(main_xml).decode('utf-8')
                except:
                    self.xml_content = zf.read(main_xml).decode('euc-kr', errors='ignore')

                # XML 파싱 (HTML 태그 처리)
                # DART XML은 HTML 형식이므로 간단한 텍스트 파싱 사용
                return True

        except Exception as e:
            logger.error(f"Failed to extract XML from {self.zip_path}: {e}")
            return False

    def parse_executives(self) -> List[Executive]:
        """임원 정보 파싱"""
        if not self.xml_content:
            return []

        executives = []

        try:
            # "임원 현황" 테이블 찾기
            # TABLE-GROUP ACLASS="SH5_DRCT_STT" 패턴 찾기
            pattern = r'<TABLE-GROUP ACLASS="SH5_DRCT_STT".*?</TABLE-GROUP>'
            matches = re.findall(pattern, self.xml_content, re.DOTALL)

            if not matches:
                # 대체 패턴: "임원 현황" 텍스트 이후 테이블
                return []

            table_content = matches[0]

            # 데이터 행 추출 (TR 태그)
            # TBODY 내의 TR 중 ACOPY="Y" 있는 것들
            tr_pattern = r'<TR ACOPY="Y".*?</TR>'
            rows = re.findall(tr_pattern, table_content, re.DOTALL)

            for row in rows:
                exec_data = self._parse_executive_row(row)
                if exec_data:
                    executives.append(exec_data)

            logger.info(f"Parsed {len(executives)} executives")

        except Exception as e:
            logger.error(f"Failed to parse executives: {e}")

        return executives

    def _parse_executive_row(self, row_xml: str) -> Optional[Executive]:
        """임원 행 파싱"""
        try:
            # TE/TU 태그에서 데이터 추출
            # ACODE로 구분

            # 성명 (SH5_NM_T)
            name_match = re.search(r'ACODE="SH5_NM_T"[^>]*>([^<]+)</TE>', row_xml)
            name = name_match.group(1).strip() if name_match else None

            if not name:
                return None

            # 성별 (SH5_SEX)
            gender_match = re.search(r'AUNIT="SH5_SEX"[^>]*>([^<]+)</TU>', row_xml)
            gender = gender_match.group(1).strip() if gender_match else None

            # 출생년월 (SH5_BIH)
            birth_match = re.search(r'AUNIT="SH5_BIH"[^>]*>([^<]+)</TU>', row_xml)
            birth = birth_match.group(1).strip() if birth_match else None

            # 직위 (SH5_LEV)
            position_match = re.search(r'ACODE="SH5_LEV"[^>]*>([^<]+)</TE>', row_xml)
            position = position_match.group(1).strip() if position_match else "미상"

            # 등기임원 구분 (SH5_REG_DRCT) - 사내이사, 사외이사, 기타비상무이사 등
            registered_match = re.search(r'AUNIT="SH5_REG_DRCT"[^>]*>([^<]+)</TU>', row_xml)
            registered_type = registered_match.group(1).strip() if registered_match else "미등기"
            # "사내이사", "사외이사" 등은 등기임원
            is_registered = "이사" in registered_type or "감사" in registered_type

            # 상근 여부 (SH5_FUL)
            fulltime_match = re.search(r'AUNIT="SH5_FUL"[^>]*>([^<]+)</TU>', row_xml)
            is_fulltime_text = fulltime_match.group(1).strip() if fulltime_match else "비상근"
            is_fulltime = "상근" in is_fulltime_text

            # 보유주식수 (SH5_SHO_QTY)
            stock_match = re.search(r'AUNIT="SH5_SHO_QTY"[^>]*>([0-9,]+)</TU>', row_xml)
            stock_count = None
            if stock_match:
                stock_str = stock_match.group(1).replace(',', '')
                stock_count = int(stock_str) if stock_str.isdigit() else None

            # 지분율 (SH5_SHO_RT)
            ratio_match = re.search(r'AUNIT="SH5_SHO_RT"[^>]*>([0-9.]+)</TU>', row_xml)
            ownership_ratio = None
            if ratio_match:
                try:
                    ownership_ratio = float(ratio_match.group(1))
                except ValueError:
                    pass

            return Executive(
                name=name,
                position=position,
                is_registered=is_registered,
                is_fulltime=is_fulltime,
                gender=gender,
                birth_year_month=birth,
                stock_count=stock_count,
                ownership_ratio=ownership_ratio
            )

        except Exception as e:
            logger.error(f"Failed to parse executive row: {e}")
            return None

    def parse_affiliates(self) -> List[Affiliate]:
        """특수관계자/계열사 파싱"""
        if not self.xml_content:
            return []

        affiliates = []

        try:
            # 1. 계열회사 정보 (AFF_CMP)
            aff_pattern = r'<TABLE-GROUP ACLASS="AFF_CMP".*?</TABLE-GROUP>'
            aff_matches = re.findall(aff_pattern, self.xml_content, re.DOTALL)

            for aff_table in aff_matches:
                # 계열회사명 추출 (LST_NM)
                name_matches = re.findall(r'ACODE="LST_NM"[^>]*>([^<]+)</TE>', aff_table)
                for name in name_matches:
                    name = name.strip()
                    if name and name != '-':
                        affiliates.append(Affiliate(
                            name=name,
                            relation_type="affiliate"
                        ))

            # 2. 자회사 정보 (SUB_CMP)
            sub_pattern = r'<TABLE-GROUP ACLASS="SUB_CMP".*?</TABLE-GROUP>'
            sub_matches = re.findall(sub_pattern, self.xml_content, re.DOTALL)

            for sub_table in sub_matches:
                # 자회사명 추출 (PRT_PAY_SUB)
                name_matches = re.findall(r'ACODE="PRT_PAY_SUB"[^>]*>([^<]+)</TE>', sub_table)
                for name in name_matches:
                    name = name.strip()
                    if name and name != '-' and '합계' not in name:
                        affiliates.append(Affiliate(
                            name=name,
                            relation_type="subsidiary"
                        ))

            # 3. 주요 주주 (OWN_SHR, VOT_STK 등)
            # TODO: 필요 시 추가 구현

            logger.info(f"Parsed {len(affiliates)} affiliates")

        except Exception as e:
            logger.error(f"Failed to parse affiliates: {e}")

        return affiliates

    def parse_convertible_bonds(self) -> List[ConvertibleBond]:
        """전환사채 정보 파싱"""
        if not self.xml_content:
            return []

        bonds = []

        try:
            # 1. 전환사채 발행 현황 테이블 찾기
            # 패턴: "전환사채", "CB", "신주인수권부사채", "BW" 등이 포함된 섹션

            # 방법 1: 타이틀에서 전환사채 관련 섹션 찾기
            cb_section_pattern = r'<TITLE[^>]*>.*?(?:전환사채|신주인수권부사채|교환사채|CB|BW|EB).*?</TITLE>.*?(?=<TITLE|$)'
            cb_sections = re.findall(cb_section_pattern, self.xml_content, re.DOTALL | re.IGNORECASE)

            for section in cb_sections:
                # 테이블 그룹 추출
                table_pattern = r'<TABLE-GROUP.*?</TABLE-GROUP>'
                tables = re.findall(table_pattern, section, re.DOTALL)

                for table in tables:
                    bond_data = self._parse_cb_table(table)
                    if bond_data:
                        bonds.append(bond_data)

            # 방법 2: "전환사채 발행현황" 등의 특정 테이블 클래스 찾기
            # ACLASS가 있는 경우
            cb_table_pattern = r'<TABLE-GROUP ACLASS="[^"]*(?:CB|BOND|CONVERT)[^"]*".*?</TABLE-GROUP>'
            cb_tables = re.findall(cb_table_pattern, self.xml_content, re.DOTALL | re.IGNORECASE)

            for table in cb_tables:
                bond_data = self._parse_cb_table(table)
                if bond_data and bond_data not in bonds:
                    bonds.append(bond_data)

            logger.info(f"Parsed {len(bonds)} convertible bonds")

        except Exception as e:
            logger.error(f"Failed to parse convertible bonds: {e}")

        return bonds

    def _parse_cb_table(self, table_xml: str) -> Optional[ConvertibleBond]:
        """전환사채 테이블 파싱"""
        try:
            bond_data = {}

            # 발행일 추출 (다양한 패턴)
            issue_patterns = [
                r'발행일.*?(\d{4}[.-]\d{2}[.-]\d{2})',
                r'ACODE="[^"]*(?:ISSUE|ISS)[^"]*DATE[^"]*"[^>]*>([0-9.\-/]+)</T',
            ]
            for pattern in issue_patterns:
                match = re.search(pattern, table_xml, re.IGNORECASE)
                if match:
                    date_str = match.group(1).replace('.', '-').replace('/', '-')
                    bond_data['issue_date'] = date_str
                    break

            # 만기일 추출
            maturity_patterns = [
                r'만기일.*?(\d{4}[.-]\d{2}[.-]\d{2})',
                r'ACODE="[^"]*(?:MATURITY|MAT)[^"]*DATE[^"]*"[^>]*>([0-9.\-/]+)</T',
            ]
            for pattern in maturity_patterns:
                match = re.search(pattern, table_xml, re.IGNORECASE)
                if match:
                    date_str = match.group(1).replace('.', '-').replace('/', '-')
                    bond_data['maturity_date'] = date_str
                    break

            # 발행금액 추출 (억원, 백만원 등)
            amount_patterns = [
                r'발행금액.*?([0-9,]+)\s*(?:억|백만)?',
                r'ACODE="[^"]*(?:ISSUE|ISS)[^"]*(?:AMOUNT|AMT)[^"]*"[^>]*>([0-9,]+)</T',
            ]
            for pattern in amount_patterns:
                match = re.search(pattern, table_xml, re.IGNORECASE)
                if match:
                    amount_str = match.group(1).replace(',', '')
                    try:
                        amount = int(amount_str)
                        # 억원 단위면 100,000,000 곱하기
                        if '억' in table_xml[max(0, match.start()-20):match.end()+20]:
                            amount *= 100000000
                        elif '백만' in table_xml[max(0, match.start()-20):match.end()+20]:
                            amount *= 1000000
                        bond_data['issue_amount'] = amount
                    except ValueError:
                        pass
                    break

            # 전환가액 추출
            conversion_price_patterns = [
                r'전환가(?:액|격).*?([0-9,]+)\s*원',
                r'ACODE="[^"]*CONV[^"]*PRICE[^"]*"[^>]*>([0-9,]+)</T',
            ]
            for pattern in conversion_price_patterns:
                match = re.search(pattern, table_xml, re.IGNORECASE)
                if match:
                    price_str = match.group(1).replace(',', '')
                    try:
                        bond_data['conversion_price'] = int(price_str)
                    except ValueError:
                        pass
                    break

            # 전환비율 추출
            conversion_ratio_patterns = [
                r'전환비율.*?([0-9.]+)\s*%',
                r'ACODE="[^"]*CONV[^"]*(?:RATIO|RATE)[^"]*"[^>]*>([0-9.]+)</T',
            ]
            for pattern in conversion_ratio_patterns:
                match = re.search(pattern, table_xml, re.IGNORECASE)
                if match:
                    try:
                        bond_data['conversion_ratio'] = float(match.group(1))
                    except ValueError:
                        pass
                    break

            # 최소한 발행일이나 발행금액이 있어야 유효한 CB
            if bond_data.get('issue_date') or bond_data.get('issue_amount'):
                return ConvertibleBond(**bond_data)

            return None

        except Exception as e:
            logger.error(f"Failed to parse CB table: {e}")
            return None

    def parse(self) -> Dict[str, Any]:
        """전체 파싱"""
        if not self.extract_xml():
            return {
                'executives': [],
                'affiliates': [],
                'convertible_bonds': []
            }

        return {
            'executives': self.parse_executives(),
            'affiliates': self.parse_affiliates(),
            'convertible_bonds': self.parse_convertible_bonds()
        }


def parse_dart_file(zip_path: Path) -> Dict[str, Any]:
    """DART ZIP 파일 파싱 (헬퍼 함수)"""
    parser = DARTXMLParser(zip_path)
    return parser.parse()


if __name__ == "__main__":
    # 테스트
    import json

    test_file = Path("data/dart/batch_001/00480950/2024/20240321001153.zip")

    if test_file.exists():
        print(f"파싱 테스트: {test_file}")
        result = parse_dart_file(test_file)

        print(f"\n임원: {len(result['executives'])}명")
        for exec in result['executives']:
            print(f"  - {exec.name} ({exec.position})")
            print(f"    등기: {exec.is_registered}, 상근: {exec.is_fulltime}")
            if exec.stock_count:
                print(f"    보유주식: {exec.stock_count:,}주 ({exec.ownership_ratio}%)")

        print(f"\n특수관계자: {len(result['affiliates'])}개")
        print(f"전환사채: {len(result['convertible_bonds'])}건")
    else:
        print(f"테스트 파일 없음: {test_file}")
