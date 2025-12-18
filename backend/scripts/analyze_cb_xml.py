#!/usr/bin/env python3
"""
전환사채 XML 구조 상세 분석
"""
import zipfile
from pathlib import Path
import re

zipfile_path = list(Path('data/dart/batch_001').rglob('20250314000856.zip'))[0]

with zipfile.ZipFile(zipfile_path, 'r') as zf:
    xml_files = [f for f in zf.namelist() if f.endswith('.xml')]
    content = zf.read(xml_files[0]).decode('utf-8', errors='ignore')

    print(f"=== 파일: {zipfile_path} ===")
    print(f"XML 크기: {len(content):,} 문자\n")

    # 1. 전환사채 관련 모든 섹션 찾기
    cb_matches = list(re.finditer(r'(전환사채|신주인수권부사채|교환사채)', content))
    print(f"'전환사채' 관련 문자열 총 {len(cb_matches)}개 발견\n")

    # 2. 주요 키워드들과 함께 나오는 섹션 찾기
    keywords = ['발행', '만기', '전환가', '액면', '이자율', '상환']

    print("=== 주요 키워드와 함께 나타나는 전환사채 섹션 ===\n")
    for i, match in enumerate(cb_matches[:10]):  # 처음 10개만
        start = match.start()
        section = content[max(0, start-300):start+800]

        # 키워드 체크
        found_keywords = [kw for kw in keywords if kw in section]

        if len(found_keywords) >= 2:  # 2개 이상 키워드가 있으면
            print(f"--- 섹션 {i+1} (발견 키워드: {', '.join(found_keywords)}) ---")
            print(section)
            print("\n" + "="*80 + "\n")

    # 3. TABLE-GROUP 구조 분석
    print("\n=== TABLE-GROUP 구조 ===\n")
    table_groups = re.findall(r'<TABLE-GROUP[^>]*ACLASS="([^"]*)"', content)
    unique_classes = set(table_groups)
    print(f"총 TABLE-GROUP: {len(table_groups)}개")
    print(f"고유 ACLASS: {len(unique_classes)}개")
    print(f"ACLASS 목록: {sorted(unique_classes)[:20]}")
