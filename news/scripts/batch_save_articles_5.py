#!/usr/bin/env python3
"""
DRCR 기사 배치 저장 스크립트 - 5차 (무궁화신탁/국보/엑시온 심층 시리즈)
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from news.storage.save_to_db import save_article, get_article_stats

PARSED_ARTICLES = [
    {
        "url": "https://www.drcr.co.kr/articles/590",
        "title": "디에이테크놀로지-국보-엑시온그룹까지 모두 연결되어 있었다",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2025-01-02",
        "summary": "디에이테크놀로지, 국보, 엑시온그룹의 복잡한 투자 연결고리. 라임 스캔들 연루자들이 자회사와 투자기구를 통해 영향력 유지.",
        "entities": [
            {"type": "company", "name": "디에이테크놀로지", "role": "관련회사"},
            {"type": "company", "name": "국보", "role": "관련회사"},
            {"type": "company", "name": "엑시온그룹", "role": "관련회사"},
            {"type": "company", "name": "에스모", "role": "관련회사"},
            {"type": "company", "name": "무궁화신탁", "role": "관련회사"},
            {"type": "person", "name": "조원일", "role": "라임 스캔들 (20년 형)"},
            {"type": "person", "name": "이인광", "role": "에스모 전 회장"},
        ],
        "relations": [
            {"source": "디에이테크놀로지", "target": "국보", "type": "investment", "detail": "자산 인수"},
            {"source": "국보", "target": "엑시온그룹", "type": "related", "detail": "동시적 거래"},
        ],
        "risks": [
            {"type": "governance", "description": "관련 기업 간 조정된 자산 이전 가능성", "severity": "high"},
            {"type": "legal", "description": "스캔들 연루자들의 지속적 영향력", "severity": "high"},
            {"type": "governance", "description": "다수 페이퍼컴퍼니와 전환사채 구조 활용", "severity": "medium"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/589",
        "title": "엑시온그룹 인수는 오창석·최기보 합작품?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2024-12-30",
        "summary": "오창석과 최기보의 엑시온그룹 인수 공조 의혹. 주가 불일치와 유리한 조건의 지분 취득 추적.",
        "entities": [
            {"type": "company", "name": "무궁화신탁", "role": "관련회사"},
            {"type": "company", "name": "국보", "role": "관련회사"},
            {"type": "company", "name": "엑시온그룹", "role": "피인수회사"},
            {"type": "company", "name": "클라우스홀딩스", "role": "인수주체"},
            {"type": "person", "name": "오창석", "role": "무궁화신탁 회장"},
            {"type": "person", "name": "최기보", "role": "클라우스홀딩스 대표"},
        ],
        "relations": [
            {"source": "오창석", "target": "최기보", "type": "collaboration", "detail": "엑시온 인수 공조 의혹"},
        ],
        "risks": [
            {"type": "governance", "description": "거래 당사자 간 주가 불일치", "severity": "high"},
            {"type": "governance", "description": "인수 구조 내 미공개 공조 가능성", "severity": "high"},
            {"type": "financial", "description": "투자펀드 해산 시 미설명 자본", "severity": "medium"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/588",
        "title": "엑시온그룹 인수에 광무가 왜 등장하나",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2024-12-26",
        "summary": "엑시온그룹의 복잡한 지배구조 변경 추적. 오션뉴웨이브1호 펀드 인수와 광무그룹 연계.",
        "entities": [
            {"type": "company", "name": "엑시온그룹", "role": "주요 기업"},
            {"type": "company", "name": "광무", "role": "관련회사"},
            {"type": "company", "name": "오션뉴웨이브1호", "role": "투자펀드"},
            {"type": "company", "name": "무궁화신탁", "role": "관련회사"},
            {"type": "person", "name": "오창석", "role": "무궁화 회장"},
            {"type": "person", "name": "최기보", "role": "관련인물"},
        ],
        "relations": [
            {"source": "오션뉴웨이브1호", "target": "엑시온그룹", "type": "acquisition", "detail": "투자펀드 통한 인수"},
        ],
        "risks": [
            {"type": "governance", "description": "무자본 M&A (페이퍼컴퍼니 활용)", "severity": "high"},
            {"type": "governance", "description": "인수 주체와 거래 규모 불일치", "severity": "high"},
            {"type": "governance", "description": "명목상 지배구조의 잦은 경영진 교체", "severity": "medium"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/587",
        "title": "엑시온그룹 새 주인과 국보, 어떤 관계길래?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2024-12-23",
        "summary": "이노파이안의 엑시온그룹 경영권 인수. 잔금 9.8억원 미지급, 국보가 실질적 경영권 행사.",
        "entities": [
            {"type": "company", "name": "엑시온그룹", "role": "주요 기업"},
            {"type": "company", "name": "이노파이안", "role": "최대주주"},
            {"type": "company", "name": "국보", "role": "2대주주"},
            {"type": "company", "name": "무궁화신탁", "role": "관련회사"},
            {"type": "person", "name": "이승철", "role": "이노파이안 대표, 엑시온 대표"},
            {"type": "person", "name": "박찬하", "role": "이사"},
        ],
        "relations": [
            {"source": "이노파이안", "target": "엑시온그룹", "type": "acquisition", "detail": "45억원, 잔금 9.8억 미지급"},
        ],
        "risks": [
            {"type": "financial", "description": "잔금 미지급으로 지배구조 불확실", "severity": "high"},
            {"type": "financial", "description": "악화된 사업 기반에 200% 프리미엄 지급", "severity": "high"},
            {"type": "financial", "description": "3년 연속 영업손실, 매출 감소", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/586",
        "title": "무궁화신탁에 인수된 국보에서 벌어진 일",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2024-12-19",
        "summary": "무궁화신탁의 국보 인수 후 재앙적 투자. 이스라엘 레드힐 바이오파마 500만달러 투자 실패, 1.13억달러 소송.",
        "entities": [
            {"type": "company", "name": "무궁화신탁", "role": "인수주체"},
            {"type": "company", "name": "국보", "role": "피인수회사"},
            {"type": "company", "name": "레드힐바이오파마", "role": "투자대상"},
            {"type": "company", "name": "오션뉴웨이브", "role": "투자조합"},
            {"type": "person", "name": "오창석", "role": "무궁화신탁 회장"},
            {"type": "person", "name": "박찬하", "role": "국보 대표"},
        ],
        "relations": [
            {"source": "무궁화신탁", "target": "국보", "type": "acquisition", "detail": "2022년 11월 인수"},
            {"source": "국보", "target": "레드힐바이오파마", "type": "investment", "detail": "500만달러 투자 실패"},
        ],
        "risks": [
            {"type": "legal", "description": "1.13억달러 소송 계류 중", "severity": "critical"},
            {"type": "financial", "description": "상당한 자본 손실의 전략적 투자 실패", "severity": "high"},
            {"type": "governance", "description": "계열사 거래 관련 사기 의혹", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/585",
        "title": "국보, 보그인터내셔날 오창석 회사에 헐값 매각?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2024-12-16",
        "summary": "국보의 보그인터내셔날 지분을 천지인엠파트너스에 헐값 매각 의혹. 출자전환으로 실제 현금 유출 최소화.",
        "entities": [
            {"type": "company", "name": "국보", "role": "매각주체"},
            {"type": "company", "name": "보그인터내셔날", "role": "매각대상"},
            {"type": "company", "name": "천지인엠파트너스", "role": "인수주체"},
            {"type": "company", "name": "디에이테크놀로지", "role": "중간 인수"},
            {"type": "person", "name": "오창석", "role": "무궁화신탁 회장"},
            {"type": "person", "name": "박찬하", "role": "천지인엠파트너스 대표"},
        ],
        "relations": [
            {"source": "국보", "target": "보그인터내셔날", "type": "divestment", "detail": "헐값 매각 의혹"},
            {"source": "천지인엠파트너스", "target": "보그인터내셔날", "type": "acquisition", "detail": "출자전환 활용"},
        ],
        "risks": [
            {"type": "governance", "description": "특수관계자 거래로 자산 저평가", "severity": "high"},
            {"type": "governance", "description": "지배주주의 자기거래 가능성", "severity": "high"},
            {"type": "regulatory", "description": "자본잠식, 상장폐지 위기", "severity": "critical"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/584",
        "title": "무궁화신탁 계열사 국보의 과거",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2024-12-12",
        "summary": "국보의 수차례 지배구조 변경 이력. 흥아해운 자회사에서 사모펀드, 카리스로 전전. 5100억원 유상증자 미결.",
        "entities": [
            {"type": "company", "name": "국보", "role": "주요 기업"},
            {"type": "company", "name": "무궁화신탁", "role": "현 대주주"},
            {"type": "company", "name": "흥아해운", "role": "전 모회사"},
            {"type": "company", "name": "카리스", "role": "전 대주주"},
            {"type": "company", "name": "천지인엠파트너스", "role": "유상증자 예정"},
            {"type": "person", "name": "오창석", "role": "회장"},
            {"type": "person", "name": "박찬하", "role": "국보 대표"},
        ],
        "relations": [
            {"source": "천지인엠파트너스", "target": "국보", "type": "capital_increase", "detail": "5100억원 유상증자 예정"},
        ],
        "risks": [
            {"type": "regulatory", "description": "국보 상장폐지 위기", "severity": "critical"},
            {"type": "regulatory", "description": "무궁화신탁 부실 금융기관 지정, 매각 예정", "severity": "critical"},
            {"type": "financial", "description": "5100억원 유상증자 대금 지급 불확실", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/583",
        "title": "무궁화신탁 부실의 근원, 어쩌면 무자본 M&A",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2024-12-09",
        "summary": "오창석 회장의 사모펀드를 활용한 무자본 M&A로 상장사 인수. 인수 후 상장폐지 위기 연속.",
        "entities": [
            {"type": "company", "name": "무궁화신탁", "role": "주요 기업"},
            {"type": "company", "name": "무궁화인포메이션테크놀로지", "role": "계열사"},
            {"type": "company", "name": "국보", "role": "피인수/상장폐지 위기"},
            {"type": "company", "name": "천지인산업개발", "role": "계열사"},
            {"type": "company", "name": "나반홀딩스", "role": "계열사"},
            {"type": "person", "name": "오창석", "role": "회장"},
        ],
        "relations": [
            {"source": "무궁화신탁", "target": "국보", "type": "investment", "detail": "사모펀드 통한 무자본 M&A"},
        ],
        "risks": [
            {"type": "financial", "description": "저자본 인수의 구조적 부실", "severity": "critical"},
            {"type": "financial", "description": "자회사 투자기구 4000억원 부채 노출", "severity": "critical"},
            {"type": "financial", "description": "2024년 3분기 지분법손실 280억원", "severity": "high"},
        ]
    },
]


async def main():
    print("=== DRCR 기사 배치 저장 (5차) ===\n")

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
