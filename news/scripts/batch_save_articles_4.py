#!/usr/bin/env python3
"""
DRCR 기사 배치 저장 스크립트 - 4차 (글람/지스마트/무궁화신탁/엑시온 시리즈)
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from news.storage.save_to_db import save_article, get_article_stats

PARSED_ARTICLES = [
    {
        "url": "https://www.drcr.co.kr/articles/600",
        "title": "글람, 나스닥에 상장한 결손기업",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2025-02-13",
        "summary": "글람이 SPAC 합병으로 나스닥 상장. 연속 영업손실로 2023년 자본잠식 상태.",
        "entities": [
            {"type": "company", "name": "글람", "role": "주요 기업"},
            {"type": "company", "name": "지스마트글로벌", "role": "관련회사"},
            {"type": "company", "name": "바이오엑스", "role": "관련회사"},
            {"type": "person", "name": "이호준", "role": "전 대표"},
            {"type": "person", "name": "김형기", "role": "관련인물"},
        ],
        "relations": [
            {"source": "바이오엑스", "target": "글람", "type": "related", "detail": "자금/지분 연계"},
        ],
        "risks": [
            {"type": "financial", "description": "자본잠식 상태, 지속적 영업손실", "severity": "critical"},
            {"type": "financial", "description": "현금 고갈, 유동성 위기", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/599",
        "title": "지스마트글로벌 매각 후 꼬리에 꼬리를 무는 이야기",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2025-02-10",
        "summary": "지스마트글로벌 상장폐지 후 1200억원 규모 복잡한 거래. 전환사채와 지분 이전 추적.",
        "entities": [
            {"type": "company", "name": "지스마트글로벌", "role": "주요 기업"},
            {"type": "company", "name": "제이에스홀딩컴퍼니", "role": "관련회사"},
            {"type": "company", "name": "에이아이빗", "role": "관련회사"},
            {"type": "company", "name": "폭스브레인홀딩스", "role": "관련회사"},
            {"type": "person", "name": "이주석", "role": "이사"},
        ],
        "relations": [
            {"source": "이주석", "target": "지스마트글로벌", "type": "management", "detail": "이사"},
            {"source": "이주석", "target": "에이아이빗", "type": "management", "detail": "전 대표"},
        ],
        "risks": [
            {"type": "governance", "description": "전환사채 교환을 통한 빠른 지분 이전", "severity": "high"},
            {"type": "financial", "description": "순환 자금 흐름, 실제 가치 창출 불명확", "severity": "high"},
            {"type": "market", "description": "조직적 주식 이전을 통한 시장조작 가능성", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/598",
        "title": "스마트안경으로 떠올랐던 지스마트글로벌은 어떻게 무너졌나",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2025-02-06",
        "summary": "LED 스마트안경으로 코스닥 상장했던 지스마트글로벌. 매출 1000억에서 100억대로 급감, 2022년 상장폐지.",
        "entities": [
            {"type": "company", "name": "지스마트글로벌", "role": "주요 기업"},
            {"type": "company", "name": "지스마트", "role": "자회사"},
            {"type": "company", "name": "코리아네트웍스", "role": "주요 고객"},
            {"type": "company", "name": "바이오엑스", "role": "관련회사"},
            {"type": "person", "name": "이호준", "role": "전 대표"},
            {"type": "person", "name": "이기성", "role": "전 대표"},
        ],
        "relations": [
            {"source": "지스마트글로벌", "target": "코리아네트웍스", "type": "sales_dependency", "detail": "매출 61.3% 의존"},
        ],
        "risks": [
            {"type": "financial", "description": "매출채권 자산의 50% 초과, 외상매출 80%", "severity": "critical"},
            {"type": "operational", "description": "단일 고객 의존도 61.3%", "severity": "high"},
            {"type": "governance", "description": "특수관계자 거래 취약성", "severity": "medium"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/595",
        "title": "국보, MIT, 광명전기 등… 오창석 회사들의 운명은?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2025-01-20",
        "summary": "무궁화신탁 영업용순자본비율 69%로 기준 100% 미달. 오창석 회장 가족회사들 대규모 적자 위기.",
        "entities": [
            {"type": "company", "name": "무궁화신탁", "role": "주요 기업"},
            {"type": "company", "name": "국보", "role": "계열사"},
            {"type": "company", "name": "광명전기", "role": "계열사"},
            {"type": "company", "name": "무궁화인포메이션테크놀로지", "role": "계열사"},
            {"type": "person", "name": "오창석", "role": "회장/최대주주"},
        ],
        "relations": [
            {"source": "오창석", "target": "무궁화신탁", "type": "ownership", "detail": "최대주주"},
            {"source": "무궁화신탁", "target": "국보", "type": "investment", "detail": "400억원 담보대출"},
        ],
        "risks": [
            {"type": "regulatory", "description": "영업용순자본비율 69% (기준 100%→400% 필요)", "severity": "critical"},
            {"type": "financial", "description": "국보 상장폐지 시 400억원 담보 손실", "severity": "critical"},
            {"type": "governance", "description": "무자본 M&A를 통한 자본잠식", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/594",
        "title": "롱투코리아는 어떻게 스타코링크가 됐나",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2025-01-16",
        "summary": "엑시온그룹 배후 이노파이안과 유콘파트너스가 롱투코리아를 인수하여 스타코링크로 전환.",
        "entities": [
            {"type": "company", "name": "엑시온그룹", "role": "인수주체"},
            {"type": "company", "name": "롱투코리아", "role": "피인수회사"},
            {"type": "company", "name": "스타코링크", "role": "상호변경"},
            {"type": "company", "name": "유콘파트너스", "role": "투자자"},
            {"type": "company", "name": "이노파이안", "role": "투자자"},
            {"type": "person", "name": "오광배", "role": "스타코링크 대표"},
        ],
        "relations": [
            {"source": "엑시온그룹", "target": "롱투코리아", "type": "acquisition", "detail": "SH1 펀드 통한 인수"},
        ],
        "risks": [
            {"type": "governance", "description": "순환 지배구조로 실질 지배 불명확", "severity": "high"},
            {"type": "financial", "description": "티비비소프트 감사의견 거절", "severity": "high"},
            {"type": "governance", "description": "특수관계자 거래 공정가치 평가 우려", "severity": "medium"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/593",
        "title": "엑시온그룹 최대주주 변경의 내막",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2025-01-13",
        "summary": "이노파이안이 복잡한 거래를 통해 엑시온그룹 최대주주 등극. 재무 불안정과 의문스러운 자금 이동.",
        "entities": [
            {"type": "company", "name": "엑시온그룹", "role": "주요 기업"},
            {"type": "company", "name": "이노파이안", "role": "최대주주"},
            {"type": "company", "name": "국보", "role": "관련회사"},
            {"type": "company", "name": "유콘파트너스", "role": "관련회사"},
            {"type": "person", "name": "이승철", "role": "이노파이안 대표, 엑시온 대표"},
            {"type": "person", "name": "오창석", "role": "무궁화신탁 회장"},
        ],
        "relations": [
            {"source": "이노파이안", "target": "엑시온그룹", "type": "ownership", "detail": "최대주주"},
        ],
        "risks": [
            {"type": "financial", "description": "이노파이안 자산 7억원, 매출 미미, 자금력 부족", "severity": "critical"},
            {"type": "financial", "description": "298억원 연불대금 2025년 6월 만기 자금 불확실", "severity": "critical"},
            {"type": "financial", "description": "계열사 누적 손실 560억원 초과", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/592",
        "title": "국보, 한창, 유콘파트너스의 얽힌 관계",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2025-01-09",
        "summary": "유콘파트너스의 파멥신, 엑시온그룹 인수 시도 실패. 자금 조달 실패로 한창이 경영권 대체.",
        "entities": [
            {"type": "company", "name": "유콘파트너스", "role": "인수 시도"},
            {"type": "company", "name": "한창", "role": "경영권 인수"},
            {"type": "company", "name": "국보", "role": "관련회사"},
            {"type": "company", "name": "파멥신", "role": "피인수 시도"},
            {"type": "company", "name": "엑시온그룹", "role": "피인수회사"},
            {"type": "person", "name": "김대봉", "role": "유콘파트너스"},
            {"type": "person", "name": "최승환", "role": "한창 대표"},
        ],
        "relations": [
            {"source": "한창", "target": "국보", "type": "bond_purchase", "detail": "전환사채 인수"},
            {"source": "유콘파트너스", "target": "엑시온그룹", "type": "attempted_acquisition", "detail": "경영참여 선언 후 실패"},
        ],
        "risks": [
            {"type": "financial", "description": "M&A 자금 조달 구조 부실", "severity": "high"},
            {"type": "governance", "description": "회계 불규칙성, 의문스러운 거래 가치평가", "severity": "high"},
            {"type": "regulatory", "description": "감사의견 거절로 상장폐지 위험", "severity": "critical"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/591",
        "title": "한지붕 두가족 엑시온그룹, 그리고 새로운 인수세력",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2025-01-06",
        "summary": "엑시온그룹 경영권을 국보와 클라우스홀딩스가 공동 인수. 경영 불화로 잦은 임원 교체.",
        "entities": [
            {"type": "company", "name": "엑시온그룹", "role": "주요 기업"},
            {"type": "company", "name": "국보", "role": "공동 인수"},
            {"type": "company", "name": "클라우스홀딩스", "role": "공동 인수"},
            {"type": "company", "name": "유콘파트너스", "role": "신주인수 시도"},
            {"type": "company", "name": "이노파이안", "role": "새 최대주주"},
            {"type": "person", "name": "박찬하", "role": "국보 대표"},
            {"type": "person", "name": "최기보", "role": "클라우스홀딩스 대표"},
        ],
        "relations": [
            {"source": "국보", "target": "엑시온그룹", "type": "acquisition", "detail": "공동 인수"},
            {"source": "클라우스홀딩스", "target": "엑시온그룹", "type": "acquisition", "detail": "공동 인수"},
        ],
        "risks": [
            {"type": "governance", "description": "주주 간 경영권 분쟁 지속", "severity": "high"},
            {"type": "financial", "description": "유콘파트너스 1050억원 잔금 미지급", "severity": "critical"},
            {"type": "legal", "description": "주주 소송, 지배구조 갈등 지속", "severity": "high"},
        ]
    },
]


async def main():
    print("=== DRCR 기사 배치 저장 (4차) ===\n")

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
