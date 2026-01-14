#!/usr/bin/env python3
"""
DRCR 기사 배치 저장 스크립트 - 6차 (무궁화신탁/바이오엑스/온코펩 시리즈)
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from news.storage.save_to_db import save_article, get_article_stats

PARSED_ARTICLES = [
    {
        "url": "https://www.drcr.co.kr/articles/582",
        "title": "회장님 기업사냥에 동원된 무궁화신탁",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2024-12-05",
        "summary": "무궁화신탁 경영개선명령. NCR 69%로 공시된 125% 대비 심각한 자산 악화. 오창석 회장 지분 매각 중.",
        "entities": [
            {"type": "company", "name": "무궁화신탁", "role": "주요 기업"},
            {"type": "company", "name": "현대자산운용", "role": "관련회사"},
            {"type": "company", "name": "국보", "role": "계열사"},
            {"type": "person", "name": "오창석", "role": "회장"},
        ],
        "relations": [],
        "risks": [
            {"type": "regulatory", "description": "자산 품질 악화, 규제 미준수", "severity": "critical"},
            {"type": "governance", "description": "회장 가족회사 위한 특관거래", "severity": "high"},
            {"type": "governance", "description": "신탁 자금의 가족회사 M&A 불법 활용", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/578",
        "title": "바이오엑스 창업자 이호준의 과거, 지스마트글로벌",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2024-11-21",
        "summary": "바이오엑스 창업자 이호준의 과거 사업 이력. 지스마트 인수와 구조조정, 워런트와 CB를 활용한 지배구조 전환.",
        "entities": [
            {"type": "company", "name": "바이오엑스", "role": "현재 회사"},
            {"type": "company", "name": "지스마트글로벌", "role": "전 회사"},
            {"type": "company", "name": "지스마트", "role": "자회사"},
            {"type": "person", "name": "이호준", "role": "창업자"},
            {"type": "person", "name": "이성락", "role": "이사"},
        ],
        "relations": [
            {"source": "이호준", "target": "지스마트글로벌", "type": "ownership", "detail": "인수 및 구조조정"},
        ],
        "risks": [
            {"type": "governance", "description": "워런트/CB를 통한 복잡한 지배구조 이전", "severity": "high"},
            {"type": "governance", "description": "지스마트-지스마트글로벌 간 특관거래 의존", "severity": "medium"},
            {"type": "legal", "description": "규제 조사 대상자와의 연결", "severity": "medium"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/577",
        "title": "온코펩·바이오엑스, 당황스러웠던 가격",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2024-11-18",
        "summary": "바이오엑스의 UCI(무궁화인포메이션테크놀로지) 인수 시 의문스러운 가치평가. 매출 0원에 6500억원 평가.",
        "entities": [
            {"type": "company", "name": "바이오엑스", "role": "피인수회사"},
            {"type": "company", "name": "온코펩", "role": "관련회사"},
            {"type": "company", "name": "무궁화인포메이션테크놀로지", "role": "인수주체"},
            {"type": "person", "name": "이호준", "role": "바이오엑스 창업자"},
            {"type": "person", "name": "김병양", "role": "UCI 회장"},
        ],
        "relations": [
            {"source": "무궁화인포메이션테크놀로지", "target": "바이오엑스", "type": "acquisition", "detail": "6500억원 가치평가"},
        ],
        "risks": [
            {"type": "financial", "description": "운영 실적 없이 극적인 가치평가 상승", "severity": "critical"},
            {"type": "governance", "description": "주요 거래 시 이사회 감독 부재", "severity": "high"},
            {"type": "financial", "description": "전임상 단계에서 19년 매출 예측", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/576",
        "title": "온코펩의 주인, 바이오닉스진에서 바이오엑스로",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2024-11-14",
        "summary": "온코펩의 복잡한 지배구조 변경. 바이오닉스진→서울생명공학→바이오엑스로 18개월간 전전.",
        "entities": [
            {"type": "company", "name": "온코펩", "role": "피인수회사"},
            {"type": "company", "name": "바이오닉스진", "role": "첫 인수"},
            {"type": "company", "name": "서울생명공학", "role": "중간 인수"},
            {"type": "company", "name": "바이오엑스", "role": "최종 인수"},
            {"type": "person", "name": "이호준", "role": "바이오엑스 창업자"},
        ],
        "relations": [
            {"source": "바이오닉스진", "target": "온코펩", "type": "acquisition", "detail": "2018년 인수"},
            {"source": "바이오엑스", "target": "온코펩", "type": "acquisition", "detail": "2020년 최종 인수"},
        ],
        "risks": [
            {"type": "governance", "description": "특수관계자 거래의 복잡성", "severity": "high"},
            {"type": "governance", "description": "연결된 법인을 통한 재무 조작", "severity": "high"},
            {"type": "governance", "description": "페이퍼컴퍼니 구조로 실소유자 불명확", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/575",
        "title": "온코펩의 첫 주인, 바이오닉스진의 배후",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2024-11-11",
        "summary": "온코펩 첫 인수자 바이오닉스진의 배후. 서울생명공학의 최소 자본 인수, 970억원 투자. 주가조작 연루자 연결.",
        "entities": [
            {"type": "company", "name": "온코펩", "role": "피인수회사"},
            {"type": "company", "name": "바이오닉스진", "role": "인수주체"},
            {"type": "company", "name": "서울생명공학", "role": "배후"},
            {"type": "company", "name": "바이오엑스", "role": "관련회사"},
            {"type": "person", "name": "이결", "role": "서울생명공학 대표"},
            {"type": "person", "name": "공현철", "role": "영풍제지 주가조작 연루"},
        ],
        "relations": [
            {"source": "서울생명공학", "target": "바이오닉스진", "type": "acquisition", "detail": "최소 자본 인수"},
            {"source": "바이오닉스진", "target": "온코펩", "type": "investment", "detail": "970억원 투자"},
        ],
        "risks": [
            {"type": "governance", "description": "미공개 대출자('타법인')를 통한 불투명 자금 조달", "severity": "high"},
            {"type": "financial", "description": "저축은행 고금리 단기 차입", "severity": "medium"},
            {"type": "legal", "description": "주가조작 사건 연루자와의 연결", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/570",
        "title": "매출 없는 흑자·자본잠식 기업의 생존법",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2024-10-28",
        "summary": "바이오엑스의 이상한 재무. 매출 8억원에 이익잉여금 76억원, 누적손실 1520억원. 투자증권 매각익으로 생존.",
        "entities": [
            {"type": "company", "name": "바이오엑스", "role": "주요 기업"},
            {"type": "company", "name": "온코렙", "role": "투자회사"},
            {"type": "company", "name": "캡티비전", "role": "투자회사"},
            {"type": "person", "name": "이호준", "role": "창업자"},
            {"type": "person", "name": "이성락", "role": "전 대표"},
        ],
        "relations": [],
        "risks": [
            {"type": "financial", "description": "미감사 프리레버뉴 바이오기업 포트폴리오 집중", "severity": "high"},
            {"type": "financial", "description": "보유 주식 미실현 손실 2430억원", "severity": "critical"},
            {"type": "operational", "description": "불확실한 상용화 일정의 최소 본업 매출", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/569",
        "title": "M&A 동지였던 무궁화신탁과 휴림로봇",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2024-10-24",
        "summary": "2017년 무궁화신탁과 DST로봇(휴림로봇)의 M&A 공조. 삼부토건, 현대자산운용 인수에 상호 참여.",
        "entities": [
            {"type": "company", "name": "무궁화신탁", "role": "인수 공조"},
            {"type": "company", "name": "휴림로봇", "role": "인수 공조"},
            {"type": "company", "name": "삼부토건", "role": "피인수회사"},
            {"type": "company", "name": "현대자산운용", "role": "피인수회사"},
            {"type": "person", "name": "오창석", "role": "무궁화신탁 회장"},
        ],
        "relations": [
            {"source": "무궁화신탁", "target": "휴림로봇", "type": "partnership", "detail": "M&A 공조"},
            {"source": "휴림로봇", "target": "삼부토건", "type": "acquisition", "detail": "PEF 주도 인수"},
        ],
        "risks": [
            {"type": "governance", "description": "거래 구조의 불투명성과 숨겨진 이해관계", "severity": "high"},
            {"type": "financial", "description": "휴림로봇의 자산 대비 의문스러운 인수 능력", "severity": "medium"},
            {"type": "governance", "description": "짧은 기간 내 다수 지배구조 변경의 불안정성", "severity": "medium"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/568",
        "title": "이용만의 무궁화신탁에서 오창석의 무궁화신탁으로",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2024-10-21",
        "summary": "무궁화신탁 창업자 이용만에서 오창석으로의 지배구조 변경. 주요 자산 매각과 급격한 확장 추적.",
        "entities": [
            {"type": "company", "name": "무궁화신탁", "role": "주요 기업"},
            {"type": "company", "name": "삼부토건", "role": "관련회사"},
            {"type": "person", "name": "이용만", "role": "전 회장"},
            {"type": "person", "name": "오창석", "role": "현 회장"},
            {"type": "person", "name": "권혁세", "role": "전 금융위원장"},
        ],
        "relations": [
            {"source": "이용만", "target": "무궁화신탁", "type": "ownership", "detail": "창업자에서 매각"},
            {"source": "오창석", "target": "무궁화신탁", "type": "ownership", "detail": "2016년 인수"},
        ],
        "risks": [
            {"type": "governance", "description": "불투명한 지배구조 이전과 불완전 공시", "severity": "high"},
            {"type": "regulatory", "description": "지연 공시로 규제 제재", "severity": "medium"},
            {"type": "financial", "description": "악화된 실적과 누적 부채", "severity": "high"},
        ]
    },
]


async def main():
    print("=== DRCR 기사 배치 저장 (6차) ===\n")

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
