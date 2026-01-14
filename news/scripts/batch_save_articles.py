#!/usr/bin/env python3
"""
DRCR 기사 배치 저장 스크립트
파싱된 기사 데이터를 DB에 저장
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from news.storage.save_to_db import save_article, get_article_stats

# 파싱된 기사 데이터 (WebFetch 결과)
PARSED_ARTICLES = [
    {
        "url": "https://www.drcr.co.kr/articles/636",
        "title": "에이프로젠의 자금 조달처, 슈넬생명과학",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2025-09-29",
        "summary": "김재섭 회장이 2009년 슈넬생명과학의 최대주주가 된 후 3년간 229억원의 유상증자와 340억원의 신주인수권부사채를 발행하여 에이프로젠에 자금을 지원했습니다.",
        "entities": [
            {"type": "company", "name": "에이프로젠", "role": "계열사"},
            {"type": "company", "name": "슈넬생명과학", "role": "모회사"},
            {"type": "company", "name": "에이프로젠바이오로직스", "role": "계열사"},
            {"type": "company", "name": "청계제약", "role": "피인수회사"},
            {"type": "company", "name": "동양텔레콤", "role": "관련회사"},
            {"type": "person", "name": "김재섭", "role": "회장"},
        ],
        "relations": [
            {"source": "슈넬생명과학", "target": "에이프로젠", "type": "capital_injection", "detail": "3년간 229억원 유상증자"},
            {"source": "슈넬생명과학", "target": "청계제약", "type": "acquisition", "detail": "지분 50% 75억원 매각 후 회수"},
            {"source": "김재섭", "target": "슈넬생명과학", "type": "ownership", "detail": "최대주주"},
        ],
        "risks": [
            {"type": "financial", "description": "슈넬생명과학 2003년 이후 적자 지속", "severity": "high"},
            {"type": "governance", "description": "순환 출자 구조를 통한 간접 지분 통제", "severity": "high"},
            {"type": "governance", "description": "특수관계자 거래의 복잡한 구조", "severity": "medium"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/635",
        "title": "든든하지 못했던 모회사, 슈넬생명과학",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2025-09-29",
        "summary": "김재섭 회장이 2009년 슈넬생명과학의 최대주주가 되어 에이프로젠 등 계열사를 통합했으나, 모회사의 영업현금흐름 악화로 신약개발 자금 조달에 어려움을 겪었습니다.",
        "entities": [
            {"type": "company", "name": "슈넬생명과학", "role": "모회사"},
            {"type": "company", "name": "에이프로젠", "role": "계열사"},
            {"type": "company", "name": "에이프로젠바이오로직스", "role": "계열사"},
            {"type": "company", "name": "닛코제약", "role": "거래처"},
            {"type": "person", "name": "김재섭", "role": "회장"},
        ],
        "relations": [
            {"source": "슈넬생명과학", "target": "에이프로젠", "type": "capital_injection", "detail": "2011년 55억원, 120억원 유상증자"},
            {"source": "에이프로젠", "target": "닛코제약", "type": "sales_dependency", "detail": "일본향 매출 의존"},
        ],
        "risks": [
            {"type": "financial", "description": "모회사 지속적 영업적자로 지배구조 불안정", "severity": "high"},
            {"type": "operational", "description": "닛코제약 제재로 일본향 매출 급감", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/634",
        "title": "에이프로젠 특수관계회사 아이벤트러스의 정체",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2025-09-22",
        "summary": "팝인베스트먼트에서 아이벤트러스로 이름을 바꾼 회사의 설립 배경과 역할을 추적. 에이프로젠그룹의 복잡한 합병과 상호변경 과정을 분석.",
        "entities": [
            {"type": "company", "name": "에이프로젠", "role": "주요 기업"},
            {"type": "company", "name": "아이벤트러스", "role": "특수관계회사"},
            {"type": "company", "name": "팝인베스트먼트", "role": "전신"},
            {"type": "company", "name": "한국슈넬제약", "role": "피인수회사"},
            {"type": "company", "name": "슈넬생명과학", "role": "모회사"},
            {"type": "company", "name": "에이프로젠바이오로직스", "role": "합병회사"},
            {"type": "person", "name": "김재섭", "role": "회장"},
            {"type": "person", "name": "유원형", "role": "관계자"},
        ],
        "relations": [
            {"source": "팝인베스트먼트", "target": "아이벤트러스", "type": "name_change", "detail": "2013년 8월 사명 변경"},
            {"source": "아이벤트러스", "target": "에이프로젠바이오로직스", "type": "merger", "detail": "2014년 1월 합병"},
            {"source": "김재섭", "target": "한국슈넬제약", "type": "acquisition", "detail": "170억원 인수"},
        ],
        "risks": [
            {"type": "governance", "description": "복잡한 합병과 상호변경으로 지배구조 파악 어려움", "severity": "high"},
            {"type": "financial", "description": "장부상 회사 운영으로 실질적 사업활동 부재", "severity": "medium"},
            {"type": "governance", "description": "개인 자금이 법인 간 거래에 대여금 형태로 개입", "severity": "high"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/633",
        "title": "김재섭 부부는 어떻게 슈넬생명과학을 인수했나?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2025-09-15",
        "summary": "김재섭 회장이 신주인수권부사채를 활용하여 슈넬생명과학 지배권을 확보한 과정 분석.",
        "entities": [
            {"type": "company", "name": "제넥셀세인", "role": "인수주체"},
            {"type": "company", "name": "한국슈넬제약", "role": "피인수회사"},
            {"type": "company", "name": "슈넬생명과학", "role": "상호변경"},
            {"type": "company", "name": "팝인베스트먼트", "role": "자금조달처"},
            {"type": "company", "name": "오로라리조트홀딩스", "role": "투자목적회사"},
            {"type": "person", "name": "김재섭", "role": "회장"},
            {"type": "person", "name": "박미령", "role": "배우자"},
        ],
        "relations": [
            {"source": "제넥셀세인", "target": "한국슈넬제약", "type": "acquisition", "detail": "유상증자 100억원 + 장외매입 115억원"},
            {"source": "김재섭", "target": "팝인베스트먼트", "type": "ownership", "detail": "신주인수권 1008만주 취득"},
            {"source": "오로라리조트홀딩스", "target": "한국슈넬제약", "type": "investment", "detail": "전환사채 53억원 매입"},
        ],
        "risks": [
            {"type": "governance", "description": "투자목적 특수법인을 통한 간접 인수로 실소유자 불명확", "severity": "high"},
            {"type": "financial", "description": "인수 후 금융위기로 심각한 자금난", "severity": "high"},
            {"type": "governance", "description": "신주인수권부사채 조건 차별로 특정 투자자 우대", "severity": "medium"},
        ]
    },
    {
        "url": "https://www.drcr.co.kr/articles/632",
        "title": "제넥셀세인 인수자금 220억원의 정체는?",
        "author": "강종구 기자",
        "publisher": "DRCR",
        "publish_date": "2025-09-08",
        "summary": "2008년 금융위기 속에서 제넥셀세인이 한국기술산업에 220억원에 인수된 과정 추적. 팝인베스트먼트가 핵심 역할.",
        "entities": [
            {"type": "company", "name": "제넥셀세인", "role": "피인수회사"},
            {"type": "company", "name": "에이프로젠", "role": "관련회사"},
            {"type": "company", "name": "한국슈넬제약", "role": "모회사"},
            {"type": "company", "name": "한국기술산업", "role": "인수주체"},
            {"type": "company", "name": "팝인베스트먼트", "role": "자금조달처"},
            {"type": "company", "name": "피라루크펀드", "role": "채권자"},
            {"type": "person", "name": "김재섭", "role": "회장"},
            {"type": "person", "name": "유원형", "role": "관계자"},
        ],
        "relations": [
            {"source": "한국기술산업", "target": "제넥셀세인", "type": "acquisition", "detail": "220억원 인수"},
            {"source": "팝인베스트먼트", "target": "슈넬생명과학", "type": "bond_holding", "detail": "170억원 신주인수권부사채 보유"},
            {"source": "피라루크펀드", "target": "제넥셀세인", "type": "debt", "detail": "외화사채 300만 달러"},
        ],
        "risks": [
            {"type": "financial", "description": "극심한 유동성 위기 및 차입금 의존", "severity": "critical"},
            {"type": "financial", "description": "외화사채 상환 불능 사태", "severity": "critical"},
            {"type": "governance", "description": "개인 투자자를 통한 간접적 자금 흐름", "severity": "high"},
            {"type": "legal", "description": "김재섭 회장 배임 및 횡령 혐의 조사", "severity": "high"},
        ]
    },
]


async def main():
    print("=== DRCR 기사 배치 저장 ===\n")

    # 적재 전 통계
    before_stats = await get_article_stats()
    print(f"적재 전: Articles={before_stats['articles']}, Entities={before_stats['entities']}, Relations={before_stats['relations']}, Risks={before_stats['risks']}")
    print()

    success_count = 0
    fail_count = 0

    for article in PARSED_ARTICLES:
        result = await save_article(**article)

        if result['success']:
            success_count += 1
            print(f"[OK] {article['title'][:30]}... - {result['stats']}")
        else:
            fail_count += 1
            print(f"[FAIL] {article['title'][:30]}... - {result.get('error', 'Unknown error')}")

    print()

    # 적재 후 통계
    after_stats = await get_article_stats()
    print(f"적재 후: Articles={after_stats['articles']}, Entities={after_stats['entities']}, Relations={after_stats['relations']}, Risks={after_stats['risks']}")
    print()
    print(f"결과: 성공 {success_count}건, 실패 {fail_count}건")
    print(f"증가: Articles +{after_stats['articles'] - before_stats['articles']}, Entities +{after_stats['entities'] - before_stats['entities']}")


if __name__ == "__main__":
    asyncio.run(main())
