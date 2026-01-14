#!/usr/bin/env python3
"""
DRCR 기사 배치 저장 스크립트 - 7차 (퀀타피아/아이텍/샌드크래프트 시리즈)
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from news.storage.save_to_db import save_article, get_article_stats

PARSED_ARTICLES = [
    {
        "url": "https://www.drcr.co.kr/articles/567",
        "title": "닮은 꼴 퀀타피아-MIT, 누가 망쳤나?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2024-10-17",
        "summary": "UCI(MIT)의 바이오엑스 인수 분석. 2850억원 투자 후 자본잠식, 상장폐지. 퀀타피아와 유사한 패턴.",
        "entities": [
            {"type": "company", "name": "무궁화인포메이션테크놀로지", "role": "주요 기업"},
            {"type": "company", "name": "바이오엑스", "role": "피인수회사"},
            {"type": "company", "name": "퀀타피아", "role": "유사 사례"},
            {"type": "company", "name": "샌드크래프트", "role": "관련회사"},
            {"type": "person", "name": "김병양", "role": "회장"},
            {"type": "person", "name": "이호준", "role": "바이오엑스 창업자"},
            {"type": "person", "name": "이성락", "role": "핵심 투자자"},
        ],
        "relations": [
            {"source": "무궁화인포메이션테크놀로지", "target": "바이오엑스", "type": "acquisition", "detail": "2850억원 투자"},
        ],
        "risks": [
            {"type": "financial", "description": "자본잠식, 상장폐지 결정", "severity": "critical"},
            {"type": "governance", "description": "운영과 불일치한 자산 구성", "severity": "high"},
            {"type": "governance", "description": "위기 전 조정된 CB 투자자 이탈", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/566",
        "title": "상폐위기 MIT 최대주주 나반홀딩스, 엑시트? 잔류?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2024-10-14",
        "summary": "MIT 상장폐지 위기에서 나반홀딩스의 모순적 행보. 매각 발표와 동시에 광명전기 지분 200억원 인수 계획.",
        "entities": [
            {"type": "company", "name": "무궁화인포메이션테크놀로지", "role": "상장폐지 위기"},
            {"type": "company", "name": "나반홀딩스", "role": "최대주주"},
            {"type": "company", "name": "광명전기", "role": "인수 대상"},
            {"type": "company", "name": "무궁화신탁", "role": "관련회사"},
            {"type": "person", "name": "오창석", "role": "실질 지배자"},
        ],
        "relations": [
            {"source": "나반홀딩스", "target": "무궁화인포메이션테크놀로지", "type": "ownership", "detail": "최대주주"},
            {"source": "나반홀딩스", "target": "광명전기", "type": "acquisition_plan", "detail": "200억원 인수 계획"},
        ],
        "risks": [
            {"type": "regulatory", "description": "구조조정에도 상장폐지 가능성 높음", "severity": "critical"},
            {"type": "financial", "description": "인수 자금 위한 유동성 부족", "severity": "high"},
            {"type": "financial", "description": "관련 법인 간 순환 자본 구조", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/565",
        "title": "상폐위기 동병상련, MIT와 퀀타피아의 겹치는 인연",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2024-10-10",
        "summary": "상장폐지 위기의 MIT와 퀀타피아. 16년 연속 적자 MIT, 반복적 유상증자로 생존. 두 회사의 연결고리 추적.",
        "entities": [
            {"type": "company", "name": "무궁화인포메이션테크놀로지", "role": "상장폐지 위기"},
            {"type": "company", "name": "퀀타피아", "role": "상장폐지 위기"},
            {"type": "company", "name": "오렌지옐로우하임", "role": "관련회사"},
            {"type": "company", "name": "샌드크래프트", "role": "관련회사"},
            {"type": "person", "name": "김병양", "role": "MIT 회장"},
            {"type": "person", "name": "이성락", "role": "관련인물"},
        ],
        "relations": [],
        "risks": [
            {"type": "financial", "description": "만성적 영업손실과 자본잠식", "severity": "critical"},
            {"type": "governance", "description": "불안정성 시사하는 잦은 지배구조 변경", "severity": "high"},
            {"type": "financial", "description": "관련 법인 간 복잡한 전환사채 구조", "severity": "medium"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/564",
        "title": "퀀타피아 기존 대주주들은 어떻게 탈출했나",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2024-10-03",
        "summary": "퀀타피아 대주주 박상돈의 이탈 과정. 900억원 투자 후 라크나가조합, 샌드크래프트로 지분 이전하여 1000억원 회수.",
        "entities": [
            {"type": "company", "name": "퀀타피아", "role": "주요 기업"},
            {"type": "company", "name": "봄코리아", "role": "투자회사"},
            {"type": "company", "name": "샌드크래프트", "role": "인수회사"},
            {"type": "company", "name": "라크나가조합", "role": "중간 인수"},
            {"type": "person", "name": "박상돈", "role": "전 대주주"},
            {"type": "person", "name": "이성락", "role": "라크나가 대표"},
        ],
        "relations": [
            {"source": "박상돈", "target": "퀀타피아", "type": "investment", "detail": "900억원 투자"},
            {"source": "샌드크래프트", "target": "퀀타피아", "type": "acquisition", "detail": "지분 인수"},
        ],
        "risks": [
            {"type": "financial", "description": "반복적 유상증자로 주주가치 희석", "severity": "high"},
            {"type": "legal", "description": "경영권 분쟁과 소송", "severity": "medium"},
            {"type": "governance", "description": "투자 의도와 실제 지배 불일치", "severity": "medium"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/563",
        "title": "아이텍의 사람들, 퀀타피아의 사람들",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2024-09-30",
        "summary": "퀀타피아의 20년 역사. 약 1조원 자본 투입에도 매년 적자. 핵심사업 대신 지분투자와 M&A에 자금 사용.",
        "entities": [
            {"type": "company", "name": "퀀타피아", "role": "주요 기업"},
            {"type": "company", "name": "아이텍", "role": "관련회사"},
            {"type": "company", "name": "삼성메디코스", "role": "자회사"},
            {"type": "company", "name": "젬백스", "role": "관련회사"},
            {"type": "person", "name": "김형일", "role": "전 회장"},
            {"type": "person", "name": "김상재", "role": "젬백스 대표"},
        ],
        "relations": [
            {"source": "아이텍", "target": "삼성메디코스", "type": "acquisition", "detail": "퀀타피아 자회사 인수"},
        ],
        "risks": [
            {"type": "financial", "description": "수년간 영업손실로 체계적 자본잠식", "severity": "critical"},
            {"type": "governance", "description": "핵심사업 대신 투기적 지분투자로 자금 전용", "severity": "high"},
            {"type": "governance", "description": "유상증자 시점과 연동된 불투명한 경영진 교체", "severity": "medium"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/562",
        "title": "침몰 위기에서 최대주주 구하기?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2024-09-26",
        "summary": "퀀타피아가 최대주주 샌드크래프트 CB 70억원 상환. TEN엔터테인먼트→샌드크래프트 CB 이전 추적.",
        "entities": [
            {"type": "company", "name": "퀀타피아", "role": "주요 기업"},
            {"type": "company", "name": "샌드크래프트", "role": "최대주주"},
            {"type": "company", "name": "TEN엔터테인먼트", "role": "전 CB 보유"},
            {"type": "company", "name": "초록뱀컴퍼니", "role": "관련회사"},
            {"type": "person", "name": "원영식", "role": "초록뱀 창업자"},
        ],
        "relations": [
            {"source": "퀀타피아", "target": "샌드크래프트", "type": "debt_repayment", "detail": "CB 70억원 상환"},
            {"source": "TEN엔터테인먼트", "target": "샌드크래프트", "type": "bond_transfer", "detail": "CB 이전"},
        ],
        "risks": [
            {"type": "governance", "description": "특관거래를 통한 지배구조 남용", "severity": "high"},
            {"type": "governance", "description": "연결된 당사자 유리하게 연속적 CB 구조조정", "severity": "high"},
            {"type": "financial", "description": "회사 위기 중 대주주 유동성 추출", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/561",
        "title": "아이텍-젬백스-크리스에프앤씨의 관계",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2024-09-23",
        "summary": "아이텍, 젬백스, 크리스에프앤씨의 연결된 지배구조. 김상재가 다수 중개자를 통해 아이텍 간접 지배 의혹.",
        "entities": [
            {"type": "company", "name": "아이텍", "role": "주요 기업"},
            {"type": "company", "name": "젬백스", "role": "관련회사"},
            {"type": "company", "name": "크리스에프앤씨", "role": "관련회사"},
            {"type": "company", "name": "삼성메디코스", "role": "관련회사"},
            {"type": "person", "name": "김상재", "role": "젬백스 대표"},
            {"type": "person", "name": "최현식", "role": "아이텍 최대주주"},
        ],
        "relations": [
            {"source": "김상재", "target": "아이텍", "type": "indirect_control", "detail": "다수 중개자 통한 간접 지배"},
        ],
        "risks": [
            {"type": "governance", "description": "순환 지배구조로 실질 지배와 책임 불명확", "severity": "high"},
            {"type": "governance", "description": "전략적 관여보다 일시적 포지셔닝 시사하는 빠른 지분 이전", "severity": "medium"},
            {"type": "market", "description": "조정된 거래를 통한 시장조작 가능성", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/560",
        "title": "우선협상대상자 삼성메디코스의 정체",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2024-09-19",
        "summary": "퀀타피아 인수 우선협상대상자 삼성메디코스. 아이텍 100% 자회사. 2025년 코스닥 상장 목표이나 자본잠식 상태.",
        "entities": [
            {"type": "company", "name": "퀀타피아", "role": "피인수회사"},
            {"type": "company", "name": "삼성메디코스", "role": "우선협상대상"},
            {"type": "company", "name": "아이텍", "role": "모회사"},
            {"type": "company", "name": "젬백스", "role": "관련회사"},
            {"type": "person", "name": "김상재", "role": "관련인물"},
        ],
        "relations": [
            {"source": "아이텍", "target": "삼성메디코스", "type": "ownership", "detail": "100% 자회사"},
            {"source": "삼성메디코스", "target": "퀀타피아", "type": "acquisition_plan", "detail": "우선협상대상자"},
        ],
        "risks": [
            {"type": "financial", "description": "삼성메디코스 자본잠식", "severity": "high"},
            {"type": "governance", "description": "연결된 법인 간 의문스러운 지배구조", "severity": "high"},
            {"type": "governance", "description": "인수 과정의 이해충돌 가능성", "severity": "medium"},
        ]
    },
]


async def main():
    print("=== DRCR 기사 배치 저장 (7차) ===\n")

    before_stats = await get_article_stats()
    print(f"적재 전: Articles={before_stats['articles']}")

    success_count = 0
    for article in PARSED_ARTICLES:
        result = await save_article(**article)
        if result['success']:
            success_count += 1
            print(f"[OK] {article['title'][:35]}...")
        else:
            print(f"[FAIL] {article['title'][:35]}...")

    after_stats = await get_article_stats()
    print(f"\n적재 후: Articles={after_stats['articles']}, 성공: {success_count}건")


if __name__ == "__main__":
    asyncio.run(main())
